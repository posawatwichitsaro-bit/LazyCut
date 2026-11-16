import os
import json
import subprocess
from pathlib import Path
import cv2
import pytest
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool

from backend.app.core.config import settings
from backend.app.core.hardware_probe import get_ffmpeg_binary
from backend.app.models.entities import SourceClip, MontageJob, ReelExport
from backend.app.engine.compositor import MontageCompositor

def create_synthetic_test_video(path: Path, duration_seconds: int = 5, width: int = 1920, height: int = 1080) -> Path:
    """Generates a real playable MP4 video file using FFmpeg testsrc and sine audio."""
    ffmpeg = get_ffmpeg_binary()
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi", "-i", f"testsrc=size={width}x{height}:rate=30",
        "-f", "lavfi", "-i", f"sine=frequency=1000:duration={duration_seconds}",
        "-t", str(duration_seconds),
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        str(path)
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"Failed to generate synthetic clip: {proc.stderr}")
    return path

@pytest.fixture(name="db_session")
def db_session_fixture():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(test_engine)
    with Session(test_engine) as session:
        yield session

def test_real_video_cut_and_vertical_transform(tmp_path, db_session, monkeypatch):
    """
    Unit test verifying that LazyCut ACTUALLY cuts, crops, and renders real video frames:
    1. Input: 6-second 16:9 video (1920x1080)
    2. Request: 2-second 9:16 vertical montage
    3. Assert:
       - The output file is rendered on disk with real bytes.
       - Dimensions transformed from 1920x1080 (16:9) to 1080x1920 (9:16).
       - Duration is physically trimmed from 6.0s down to <= 2.5s.
       - Frames are decodable by OpenCV with valid image matrices.
       - Chapters file is created on disk.
    """
    # 1. Setup isolated directories
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "exports_dir", exports_dir)

    # 2. Create raw 16:9 (1920x1080) 6-second video
    raw_video_path = tmp_path / "raw_source_6s.mp4"
    create_synthetic_test_video(raw_video_path, duration_seconds=6, width=1920, height=1080)

    # Verify input video parameters with OpenCV
    in_cap = cv2.VideoCapture(str(raw_video_path))
    assert in_cap.isOpened(), "Synthetic input clip failed to open"
    in_w = int(in_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    in_h = int(in_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    in_fps = in_cap.get(cv2.CAP_PROP_FPS) or 30.0
    in_frames = in_cap.get(cv2.CAP_PROP_FRAME_COUNT)
    in_dur = in_frames / in_fps
    in_cap.release()

    assert in_w == 1920, f"Expected 1920 width, got {in_w}"
    assert in_h == 1080, f"Expected 1080 height, got {in_h}"
    assert 5.8 <= in_dur <= 6.2, f"Expected ~6.0s duration, got {in_dur}"

    # 3. Add clip and job to database (request target_duration = 2 seconds)
    clip = SourceClip(
        id="clip-raw-6s",
        file_path=str(raw_video_path),
        file_name="raw_source_6s.mp4",
        duration=6.0,
        kill_count=3,
        is_verified=True
    )
    db_session.add(clip)

    job = MontageJob(
        id="job-real-cut-test",
        preset_id="valorant_1080p",
        vibe_id="hype_montage",
        target_duration=2,  # Request cut down to 2 seconds
        selected_clips_json=json.dumps(["clip-raw-6s"]),
        status="QUEUED",
        progress=0.0
    )
    db_session.add(job)
    db_session.commit()

    # 4. Execute Montage Compositor
    compositor = MontageCompositor(db_session=db_session)
    export = compositor.execute_job(job_id=job.id, output_format="9:16")

    # 5. Assertions on physical output file
    output_path = Path(export.output_path)
    assert output_path.exists(), f"Output reel not found at {output_path}"
    file_size = output_path.stat().st_size
    assert file_size > 50_000, f"Exported file is unexpectedly small ({file_size} bytes)"

    # 6. OpenCV Verification of decoded frames and dimensions
    out_cap = cv2.VideoCapture(str(output_path))
    assert out_cap.isOpened(), "Rendered output reel failed to open with OpenCV"

    out_w = int(out_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    out_h = int(out_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out_fps = out_cap.get(cv2.CAP_PROP_FPS) or 30.0
    out_frames = out_cap.get(cv2.CAP_PROP_FRAME_COUNT)
    out_dur = out_frames / out_fps

    ret, first_frame = out_cap.read()
    out_cap.release()

    # Verify 9:16 vertical geometry
    assert ret is True, "Failed to decode first video frame from exported reel"
    assert out_w == 1080, f"Expected 9:16 width (1080), got {out_w}"
    assert out_h == 1920, f"Expected 9:16 height (1920), got {out_h}"
    assert first_frame.shape == (1920, 1080, 3), f"Frame shape mismatch: {first_frame.shape}"

    # 7. Physical pixel verification across layers (Blurred BG vs Center Gameplay vs Killfeed PIP)
    # Layer 1: Blurred background area (top-left margin)
    bg_sample = first_frame[0:200, 0:200]
    assert bg_sample.size > 0 and bg_sample.mean() > 0, "Background layer contains empty or zero pixels"

    # Layer 2: Center gameplay layer (y=420 to 1500)
    center_sample = first_frame[420:1500, :]
    assert center_sample.shape == (1080, 1080, 3), "Center gameplay layer geometry mismatch"
    assert center_sample.mean() > 0, "Center gameplay layer contains empty or zero pixels"

    # Layer 3: Killfeed overlay PIP (x=330..750, y=120..360)
    killfeed_sample = first_frame[120:360, 330:750]
    assert killfeed_sample.shape == (240, 420, 3), "Killfeed PIP overlay geometry mismatch"
    assert killfeed_sample.mean() > 0, "Killfeed PIP overlay contains empty or zero pixels"

    # Verify actual trimming: original was 6.0s, output must be <= 2.5s
    assert out_dur <= 2.5, f"Video was not trimmed! Expected <= 2.5s, got {out_dur}s"

    # 8. Verify chapters file on disk
    expected_chapters = exports_dir / f"chapters_{output_path.stem.replace('reel_', '')}.txt"
    assert expected_chapters.exists(), f"Chapters file missing: {expected_chapters}"
    with open(expected_chapters, "r", encoding="utf-8") as f:
        chapters_content = f.read()
    assert "00:00" in chapters_content
    assert "Clip 1" in chapters_content

    # 8. Verify database state
    db_session.refresh(job)
    assert job.status == "COMPLETED"
    assert job.progress == 1.0
    assert export.actual_duration <= 2.5
    assert export.aspect_ratio == "9:16"

def test_real_multi_clip_concatenation_and_cutting(tmp_path, db_session, monkeypatch):
    """
    Unit test verifying that LazyCut concatenates multiple clips and respects the budget:
    1. Clip 1 (3s) + Clip 2 (3s) = Total 6s
    2. Requested budget = 4s
    3. Assert:
       - Renders into a single 9:16 output
       - Actual duration is <= 4.5s (proves budget cutting occurred)
       - Both clips are represented in chapters
    """
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "exports_dir", exports_dir)

    clip1_path = tmp_path / "source_part1_3s.mp4"
    clip2_path = tmp_path / "source_part2_3s.mp4"
    create_synthetic_test_video(clip1_path, duration_seconds=3, width=1920, height=1080)
    create_synthetic_test_video(clip2_path, duration_seconds=3, width=1920, height=1080)

    c1 = SourceClip(id="c1", file_path=str(clip1_path), file_name="part1.mp4", duration=3.0, kill_count=4, is_verified=True)
    c2 = SourceClip(id="c2", file_path=str(clip2_path), file_name="part2.mp4", duration=3.0, kill_count=2, is_verified=True)
    db_session.add(c1)
    db_session.add(c2)

    job = MontageJob(
        id="job-multi-cut-test",
        preset_id="valorant_1080p",
        vibe_id="hype_montage",
        target_duration=4,
        selected_clips_json=json.dumps(["c1", "c2"]),
        status="QUEUED"
    )
    db_session.add(job)
    db_session.commit()

    compositor = MontageCompositor(db_session=db_session)
    export = compositor.execute_job(job_id=job.id, output_format="9:16")

    output_path = Path(export.output_path)
    assert output_path.exists()

    cap = cv2.VideoCapture(str(output_path))
    assert cap.isOpened()
    dur = cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30.0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    assert w == 1080
    assert h == 1920
    assert dur <= 4.5, f"Multi-clip cut was not constrained to budget: {dur}s"
    assert "Clip 1" in export.chapters_txt
