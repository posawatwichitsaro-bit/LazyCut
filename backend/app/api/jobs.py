import json
from pathlib import Path
from threading import Lock
from tempfile import NamedTemporaryFile
from typing import Literal, get_args
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.engine import Connection, Engine
from sqlmodel import Session, select
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.database import get_session
from backend.app.models.entities import MontageJob, ReelExport, ReelRenderDetails, RecordingMove, SourceClip
from backend.app.engine.compositor import MontageCompositor
from backend.app.detection.clip_analysis import EventSelection, HighlightTiming
from backend.app.watcher.process_guard import is_game_process_running

router = APIRouter(prefix="/api/jobs", tags=["Montage Jobs"])

class CreateJobRequest(BaseModel):
    folder_queue: bool = False
    max_reels: int = Field(default=3, ge=1)
    duration_profile: Literal["short", "long"] = "long"
    clip_ids: list[str] = Field(default_factory=list)
    preset_id: str = "valorant_1080p"
    vibe_id: str = "hype_montage"
    target_duration: int = Field(default=60, gt=0)
    output_format: str = "9:16"
    resolution: Literal[480, 720, 1080] = 1080
    bgm_path: str | None = None
    timing: HighlightTiming = Field(default_factory=HighlightTiming)
    selections: dict[str, EventSelection] = Field(default_factory=dict)

class JobResponse(BaseModel):
    id: str
    preset_id: str
    vibe_id: str
    target_duration: int
    status: str
    progress: float
    error_message: str | None

render_lock = Lock()


def _run_montage_in_background(bind: Engine | Connection, job_id: str, payload: CreateJobRequest):
    with render_lock, Session(bind) as session:
        try:
            job = session.get(MontageJob, job_id)
            if not job:
                return
            compositor = MontageCompositor(session)
            compositor.execute_job(
                job_id=job_id,
                output_format=payload.output_format,
                resolution=payload.resolution,
                bgm_path=payload.bgm_path,
                timing=payload.timing,
                selections=payload.selections,
                folder_queue=payload.folder_queue,
                max_reels=payload.max_reels if payload.folder_queue else 1,
            )
        except Exception as exc:
            session.rollback()
            job = session.get(MontageJob, job_id)
            if job and job.status != "FAILED":
                job.status = "FAILED"
                job.error_message = str(exc)
                session.commit()

@router.post("", response_model=JobResponse)
def create_job(
    payload: CreateJobRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    clip_ids = payload.clip_ids
    if payload.folder_queue:
        if clip_ids or payload.selections:
            raise HTTPException(status_code=400, detail="Folder queue cannot include manual selections.")
        if not settings.watch_path or not Path(settings.watch_path).is_dir():
            raise HTTPException(status_code=400, detail="Choose a recording folder first.")
        folder = Path(settings.watch_path).resolve()
        recordings = session.exec(select(SourceClip).order_by(SourceClip.created_at, SourceClip.id))
        clip_ids = [clip.id for clip in recordings if Path(clip.file_path).parent == folder
                    and Path(clip.file_path).is_file()]
        if not clip_ids:
            raise HTTPException(status_code=400, detail="No ready recordings in the selected folder.")
    duration_limit = settings.max_montage_duration_seconds
    if payload.duration_profile == "short":
        duration_limit = min(duration_limit, 180)
    if payload.folder_queue and payload.target_duration > duration_limit:
        raise HTTPException(status_code=400, detail="Duration exceeds the maximum per Reel.")
    if not clip_ids:
        raise HTTPException(status_code=400, detail="Must select at least one clip.")
    if payload.selections.keys() - set(payload.clip_ids):
        raise HTTPException(status_code=400, detail="Event selections must belong to selected clips.")
    if is_game_process_running():
        raise HTTPException(status_code=409, detail="Game Process Guard is active. Close the game before rendering.")

    job = MontageJob(
        preset_id=payload.preset_id,
        vibe_id=payload.vibe_id,
        target_duration=payload.target_duration,
        selected_clips_json=json.dumps(list(dict.fromkeys(clip_ids))),
        status="QUEUED",
        progress=0.0
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Dispatch to background task
    background_tasks.add_task(
        _run_montage_in_background,
        session.get_bind(),
        job.id,
        payload,
    )

    return JobResponse(
        id=job.id,
        preset_id=job.preset_id,
        vibe_id=job.vibe_id,
        target_duration=job.target_duration,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message
    )

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str, session: Session = Depends(get_session)):
    job = session.get(MontageJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JobResponse(
        id=job.id,
        preset_id=job.preset_id,
        vibe_id=job.vibe_id,
        target_duration=job.target_duration,
        status=job.status,
        progress=job.progress,
        error_message=job.error_message
    )

@router.get("/{job_id}/export")
def get_job_export(job_id: str, session: Session = Depends(get_session)):
    export = session.exec(job_exports_query(job_id)).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not ready or not found.")
    return serialize_export(export, session)


def job_exports_query(job_id: str):
    return select(ReelExport).where(ReelExport.job_id == job_id).order_by(ReelExport.created_at, ReelExport.id)


@router.get("/{job_id}/exports")
def list_job_exports(job_id: str, session: Session = Depends(get_session)):
    if session.get(MontageJob, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found.")
    return [serialize_export(export, session) for export in session.exec(job_exports_query(job_id))]


def serialize_export(export: ReelExport, session: Session):
    details = session.get(ReelRenderDetails, export.id)
    return {
        "created_at": export.created_at,
        "style": export.job.vibe_id if export.job else None,
        "resolution": [details.width, details.height] if details else None,
        "sources": json.loads(details.sources_json) if details else [],
        "id": export.id,
        "output_path": export.output_path,
        "filename": Path(export.output_path.replace("\\", "/")).name,
        "actual_duration": export.actual_duration,
        "aspect_ratio": export.aspect_ratio,
        "chapters": export.chapters_txt,
        "ai_title": export.ai_title,
        "ai_description": export.ai_description
    }


Rating = Literal["ดีมาก", "ดี", "แย่", "แย่มาก"]
ratings_lock = Lock()


class RatingRequest(BaseModel):
    rating: Rating


def load_ratings() -> dict[str, Rating]:
    try:
        return json.loads((settings.exports_dir / "ratings.json").read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def rating_counts(ratings: dict[str, Rating]) -> dict[str, int]:
    return {level: sum(rating == level for rating in ratings.values()) for level in get_args(Rating)}


@router.get("/reels/history")
def export_history(session: Session = Depends(get_session)):
    exports = session.exec(select(ReelExport).order_by(ReelExport.created_at.desc(), ReelExport.id)).all()
    with ratings_lock:
        ratings = load_ratings()
    return {
        "exports": [serialize_export(export, session) for export in exports],
        "jobs": session.exec(select(MontageJob).order_by(MontageJob.created_at.desc()).limit(100)).all(),
        "moves": session.exec(select(RecordingMove).order_by(RecordingMove.id.desc()).limit(100)).all(),
        "ratings": ratings,
        "counts": rating_counts(ratings),
    }


@router.put("/reels/{export_id}/rating")
def set_export_rating(export_id: str, payload: RatingRequest, session: Session = Depends(get_session)):
    if session.get(ReelExport, export_id) is None:
        raise HTTPException(status_code=404, detail="Reel not found.")
    with ratings_lock:
        ratings = load_ratings()
        ratings[export_id] = payload.rating
        temp = None
        try:
            with NamedTemporaryFile(mode="w", encoding="utf-8", dir=settings.exports_dir, delete=False) as stream:
                temp = Path(stream.name)
                json.dump(ratings, stream, ensure_ascii=False, indent=2)
            temp.replace(settings.exports_dir / "ratings.json")
        finally:
            if temp is not None:
                temp.unlink(missing_ok=True)
    return {"rating": payload.rating, "counts": rating_counts(ratings)}
