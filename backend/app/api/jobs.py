import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.engine import Connection, Engine
from sqlmodel import Session, select
from pydantic import BaseModel, Field

from backend.app.core.database import get_session
from backend.app.models.entities import MontageJob, ReelExport
from backend.app.engine.compositor import MontageCompositor
from backend.app.detection.clip_analysis import EventSelection, HighlightTiming
from backend.app.watcher.process_guard import is_game_process_running

router = APIRouter(prefix="/api/jobs", tags=["Montage Jobs"])

class CreateJobRequest(BaseModel):
    clip_ids: list[str]
    preset_id: str = "valorant_1080p"
    vibe_id: str = "hype_montage"
    target_duration: int = Field(default=60, gt=0)
    output_format: str = "9:16"
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

def _run_montage_in_background(bind: Engine | Connection, job_id: str, payload: CreateJobRequest):
    with Session(bind) as session:
        try:
            job = session.get(MontageJob, job_id)
            if not job:
                return
            compositor = MontageCompositor(session)
            compositor.execute_job(
                job_id=job_id,
                output_format=payload.output_format,
                bgm_path=payload.bgm_path,
                timing=payload.timing,
                selections=payload.selections,
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
    if not payload.clip_ids:
        raise HTTPException(status_code=400, detail="Must select at least one clip.")
    if payload.selections.keys() - set(payload.clip_ids):
        raise HTTPException(status_code=400, detail="Event selections must belong to selected clips.")
    if is_game_process_running():
        raise HTTPException(status_code=409, detail="Game Process Guard is active. Close the game before rendering.")

    job = MontageJob(
        preset_id=payload.preset_id,
        vibe_id=payload.vibe_id,
        target_duration=payload.target_duration,
        selected_clips_json=json.dumps(list(dict.fromkeys(payload.clip_ids))),
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
    export = session.exec(select(ReelExport).where(ReelExport.job_id == job_id)).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export not ready or not found.")
    return {
        "id": export.id,
        "output_path": export.output_path,
        "actual_duration": export.actual_duration,
        "aspect_ratio": export.aspect_ratio,
        "chapters": export.chapters_txt,
        "ai_title": export.ai_title,
        "ai_description": export.ai_description
    }
