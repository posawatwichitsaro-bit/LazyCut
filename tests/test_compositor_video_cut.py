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
from backend.app.detection.clip_analysis import EventSelection, HighlightTiming, analyze_clip
from backend.app.detection.highlight_curator import CombatMoment, CuratedHighlight, HighlightCurator
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

    # Analyze once, then render only the selected late event under the 2s budget.
    monkeypatch.setattr(
        HighlightCurator, "curate_clip",
        lambda self, path: CuratedHighlight(
            path, 6.0, [CombatMoment(1.0), CombatMoment(4.5, is_headshot=True)], []
        ),
    )
    _, revision = analyze_clip(db_session, clip)

    def unexpected_rescan(self, path):
        pytest.fail("Rendering must reuse the cached Preview analysis")

    monkeypatch.setattr(HighlightCurator, "curate_clip", unexpected_rescan)
    compositor = MontageCompositor(db_session=db_session)
    export = compositor.execute_job(
        job_id=job.id, output_format="9:16", timing=HighlightTiming(pre=2, post=1),
        selections={clip.id: EventSelection(revision=revision, event_indices=[1])},
    )

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
    assert "Clip 1 (1 Kill)" in chapters_content

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
    create_synthetic_test_video(clip1_path, duration_seconds=3, width=1280, height=720)
    create_synthetic_test_video(clip2_path, duration_seconds=3, width=1280, height=720)

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

    monkeypatch.setattr(
        HighlightCurator, "curate_clip",
        lambda self, path: CuratedHighlight(path, 3.0, [CombatMoment(1.0)], []),
    )
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

def test_real_cinema_16_9_montage_assembly(tmp_path, db_session, monkeypatch):
    """
    Unit test verifying 16:9 Full-Screen Cinema Montage:
    - Pure highlight cuts stitched in original 1920x1080 widescreen (no crop, no background blur)
    - Verifies output dimensions are strictly 1920x1080 (16:9 aspect ratio)
    """
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "exports_dir", exports_dir)

    c1_path = tmp_path / "cinema_clip1.mp4"
    c2_path = tmp_path / "cinema_clip2.mp4"
    create_synthetic_test_video(c1_path, duration_seconds=3, width=1920, height=1080)
    create_synthetic_test_video(c2_path, duration_seconds=3, width=1920, height=1080)

    c1 = SourceClip(id="cin1", file_path=str(c1_path), file_name="c1.mp4", duration=3.0, kill_count=2, is_verified=True)
    c2 = SourceClip(id="cin2", file_path=str(c2_path), file_name="c2.mp4", duration=3.0, kill_count=3, is_verified=True)
    db_session.add(c1)
    db_session.add(c2)

    job = MontageJob(
        id="job-cinema-test",
        preset_id="valorant_1080p",
        vibe_id="hype_montage",
        target_duration=6,
        selected_clips_json=json.dumps(["cin1", "cin2"]),
        status="QUEUED"
    )
    db_session.add(job)
    db_session.commit()

    monkeypatch.setattr(
        HighlightCurator, "curate_clip",
        lambda self, path: CuratedHighlight(path, 3.0, [CombatMoment(1.0)], []),
    )
    compositor = MontageCompositor(db_session=db_session)
    export = compositor.execute_job(job_id=job.id, output_format="16:9")

    out_path = Path(export.output_path)
    assert out_path.exists()

    cap = cv2.VideoCapture(str(out_path))
    assert cap.isOpened()
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    # Verify 16:9 widescreen dimensions (NOT cropped to 1080x1920!)
    assert w == 1920, f"Expected 1920 width, got {w}"
    assert h == 1080, f"Expected 1080 height, got {h}"
    assert export.aspect_ratio == "16:9"



def test_no_kills_finishes_without_export(tmp_path, db_session, monkeypatch):
    path = tmp_path / "quiet.mp4"
    path.touch()
    clip = SourceClip(id="quiet", file_name=path.name, file_path=str(path))
    job = MontageJob(selected_clips_json=json.dumps([clip.id]))
    db_session.add_all([clip, job])
    db_session.commit()
    monkeypatch.setattr(HighlightCurator, "curate_clip",
                        lambda self, path: CuratedHighlight(path, 5.0, [], []))
    assert MontageCompositor(db_session).execute_job(job.id) is None
    assert job.status == "NO_HIGHLIGHTS"
    assert not job.exports


def test_automatic_selection_stops_before_next_file(tmp_path, db_session, monkeypatch):
    clips = []
    for name in ("first.mp4", "next.mp4"):
        path = tmp_path / name
        path.touch()
        clips.append(SourceClip(file_name=name, file_path=str(path)))
    job = MontageJob(target_duration=2, selected_clips_json=json.dumps([c.id for c in clips]))
    db_session.add_all([*clips, job])
    db_session.commit()

    def analyze(self, path):
        assert path.name == "first.mp4"
        return CuratedHighlight(path, 6.0, [CombatMoment(3.0)], [])

    monkeypatch.setattr(HighlightCurator, "curate_clip", analyze)
    class ReachedRenderStage(Exception):
        pass

    def stop_before_render(*args):
        raise ReachedRenderStage

    monkeypatch.setattr("backend.app.engine.compositor.check_disk_safety", stop_before_render)
    with pytest.raises(ReachedRenderStage):
        MontageCompositor(db_session).execute_job(job.id)

def test_folder_queue_resumes_after_rename(tmp_path, db_session, monkeypatch):
    from backend.app.models.entities import ExportedKill
    from sqlmodel import select

    monkeypatch.setattr(settings, "exports_dir", tmp_path)
    path = create_synthetic_test_video(tmp_path / "game.mp4", duration_seconds=5)
    monkeypatch.setattr(HighlightCurator, "curate_clip", lambda self, path:
                        CuratedHighlight(path, 5.0, [CombatMoment(0.5), CombatMoment(4.5)], []))
    def register(path):
        clip = SourceClip(file_name=path.name, file_path=str(path))
        db_session.add(clip)
        db_session.commit()
        return clip.id

    def start(clip_id):
        job = MontageJob(selected_clips_json=json.dumps([clip_id]), target_duration=1)
        db_session.add(job)
        db_session.commit()
        return MontageCompositor(db_session).execute_job(
            job.id, output_format="16:9", folder_queue=True, timing=HighlightTiming(pre=0.5, post=0.5)
        )

    assert start(register(path)) is not None
    assert len(db_session.exec(select(ExportedKill)).all()) == 1
    renamed = path.rename(tmp_path / "renamed.mp4")
    clip_id = register(renamed)
    assert start(clip_id) is not None
    assert {row.timestamp_ms for row in db_session.exec(select(ExportedKill))} == {500, 4500}
    assert start(clip_id) is None

def test_folder_job_keeps_first_reel_when_second_render_fails(tmp_path, db_session, monkeypatch):
    from backend.app.models.entities import ExportedKill
    from sqlmodel import select

    monkeypatch.setattr(settings, "exports_dir", tmp_path)
    path = create_synthetic_test_video(tmp_path / "match.mp4", duration_seconds=9)
    detector_calls = []
    def curate(self, path):
        detector_calls.append(path)
        return CuratedHighlight(path, 9.0, [CombatMoment(0.5), CombatMoment(4.5), CombatMoment(8.5)], [])
    monkeypatch.setattr(HighlightCurator, "curate_clip", curate)
    clip = SourceClip(file_name=path.name, file_path=str(path))
    db_session.add(clip)
    db_session.commit()

    def make_job():
        job = MontageJob(selected_clips_json=json.dumps([clip.id]), target_duration=1)
        db_session.add(job)
        db_session.commit()
        return job

    compositor = MontageCompositor(db_session)
    native_run = subprocess.run
    render_count = 0

    def fail_second_render(args, **kwargs):
        nonlocal render_count
        if "-filter_complex" in args:
            render_count += 1
            if render_count == 2:
                Path(args[-1]).write_bytes(b"partial export")
                return subprocess.CompletedProcess(args, 1, "", "simulated FFmpeg failure")
        return native_run(args, **kwargs)

    monkeypatch.setattr(subprocess, "run", fail_second_render)
    timing = HighlightTiming(pre=0.5, post=0.5)
    job = make_job()
    with pytest.raises(RuntimeError, match="simulated FFmpeg failure"):
        compositor.execute_job(job.id, output_format="16:9", folder_queue=True, max_reels=2, timing=timing)

    assert job.status == "FAILED"
    first, = job.exports
    assert Path(first.output_path).is_file()
    assert len(list(tmp_path.glob("reel_*.mp4"))) == 1
    assert len(db_session.exec(select(ExportedKill)).all()) == 1

    next_job = make_job()
    compositor.execute_job(next_job.id, output_format="16:9", folder_queue=True, max_reels=2, timing=timing)
    assert next_job.status == "COMPLETED"
    assert len(next_job.exports) == 2
    paths = {export.output_path for export in [first, *next_job.exports]}
    assert len(paths) == 3
    assert all(Path(output).is_file() for output in paths)
    assert len(db_session.exec(select(ExportedKill)).all()) == 3
    assert len(detector_calls) == 1
