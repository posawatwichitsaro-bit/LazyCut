from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select
from pydantic import BaseModel

from backend.app.core.database import get_session
from backend.app.models.entities import SourceClip, KillEvent
from backend.app.detection.killfeed_detector import ValorantKillDetector

router = APIRouter(prefix="/api/clips", tags=["Clips"])

class ClipResponse(BaseModel):
    id: str
    file_path: str
    file_name: str
    duration: float
    file_size: int
    kill_count: int
    is_verified: bool

class ImportClipRequest(BaseModel):
    file_path: str

@router.get("", response_model=list[ClipResponse])
def list_clips(
    has_kills: bool | None = Query(default=None),
    is_verified: bool | None = Query(default=None),
    min_duration: float | None = Query(default=None),
    max_duration: float | None = Query(default=None),
    session: Session = Depends(get_session)
):
    query = select(SourceClip).order_by(SourceClip.created_at.desc())
    if has_kills is True:
        query = query.where(SourceClip.kill_count > 0)
    elif has_kills is False:
        query = query.where(SourceClip.kill_count == 0)

    if is_verified is not None:
        query = query.where(SourceClip.is_verified == is_verified)

    if min_duration is not None:
        query = query.where(SourceClip.duration >= min_duration)

    if max_duration is not None:
        query = query.where(SourceClip.duration <= max_duration)
    
    clips = session.exec(query).all()
    return [
        ClipResponse(
            id=c.id,
            file_path=c.file_path,
            file_name=c.file_name,
            duration=c.duration,
            file_size=c.file_size,
            kill_count=c.kill_count,
            is_verified=c.is_verified
        )
        for c in clips
    ]

@router.get("/{clip_id}/thumbnail")
def get_clip_thumbnail(clip_id: str, session: Session = Depends(get_session)):
    """Generates and serves a thumbnail image from the middle of a source clip."""
    clip = session.get(SourceClip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    video_path = Path(clip.file_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk.")

    from backend.app.core.config import settings
    thumbs_dir = settings.exports_dir / "thumbnails"
    thumbs_dir.mkdir(parents=True, exist_ok=True)

    # Use clip id as stable cache key
    thumb_path = thumbs_dir / f"{clip_id}.jpg"
    if thumb_path.exists():
        return FileResponse(str(thumb_path), media_type="image/jpeg")

    # Extract a frame from middle of clip using FFmpeg
    import subprocess
    from backend.app.core.hardware_probe import get_ffmpeg_binary
    ffmpeg = get_ffmpeg_binary()
    seek_time = max(0.5, clip.duration / 2.0) if clip.duration > 0 else 1.0

    cmd = [
        ffmpeg, "-y",
        "-ss", f"{seek_time:.2f}",
        "-i", str(video_path),
        "-vframes", "1",
        "-vf", "scale=320:-1",
        "-q:v", "4",
        str(thumb_path)
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
    if proc.returncode != 0 or not thumb_path.exists():
        raise HTTPException(status_code=500, detail="Thumbnail generation failed.")

    return FileResponse(str(thumb_path), media_type="image/jpeg")

@router.get("/{clip_id}/analyze")
def analyze_clip_highlights(clip_id: str, session: Session = Depends(get_session)):
    """Runs the HighlightCurator on a single clip, returning kill moments and action windows."""
    clip = session.get(SourceClip, clip_id)
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found.")

    video_path = Path(clip.file_path)
    if not video_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk.")

    from backend.app.detection.highlight_curator import HighlightCurator
    curator = HighlightCurator()
    result = curator.curate_clip(video_path)

    # Update clip kill_count if curator found more
    if result.has_highlights and len(result.moments) > clip.kill_count:
        clip.kill_count = len(result.moments)
        clip.is_verified = True
        session.commit()

    return result.to_dict()

@router.post("/import", response_model=ClipResponse)
def import_clip(
    payload: ImportClipRequest,
    session: Session = Depends(get_session)
):
    p = Path(payload.file_path)
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=400, detail="File does not exist.")

    # Check if already imported
    existing = session.exec(select(SourceClip).where(SourceClip.file_path == str(p))).first()
    if existing:
        return ClipResponse(
            id=existing.id,
            file_path=existing.file_path,
            file_name=existing.file_name,
            duration=existing.duration,
            file_size=existing.file_size,
            kill_count=existing.kill_count,
            is_verified=existing.is_verified
        )

    # Scan with OpenCV
    detector = ValorantKillDetector()
    result = detector.analyze_clip(p)

    clip = SourceClip(
        file_path=str(p),
        file_name=p.name,
        file_size=p.stat().st_size,
        duration=result.duration,
        kill_count=result.kill_count,
        is_verified=result.is_verified
    )
    session.add(clip)
    session.commit()
    session.refresh(clip)

    for t in result.kill_timestamps:
        ke = KillEvent(
            clip_id=clip.id,
            timestamp_sec=t,
            confidence=0.9,
            event_type="skull_banner"
        )
        session.add(ke)
    session.commit()

    return ClipResponse(
        id=clip.id,
        file_path=clip.file_path,
        file_name=clip.file_name,
        duration=clip.duration,
        file_size=clip.file_size,
        kill_count=clip.kill_count,
        is_verified=clip.is_verified
    )

@router.post("/scan")
def scan_watch_directory(session: Session = Depends(get_session)):
    """Scans the configured watch path and imports all discovered video files."""
    from backend.app.core.config import settings
    from backend.app.watcher.folder_watcher import watcher_service
    if not settings.watch_path or not Path(settings.watch_path).exists():
        raise HTTPException(status_code=400, detail="Watch path is not configured or does not exist.")

    registered = watcher_service.scan_existing_clips(Path(settings.watch_path))
    total_clips = len(session.exec(select(SourceClip)).all())
    return {"registered_new": registered, "total_clips": total_clips}
