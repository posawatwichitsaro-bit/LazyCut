import json
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from pydantic import BaseModel

from backend.app.core.database import get_session, engine
from backend.app.models.entities import MontageJob, ReelExport
from backend.app.engine.compositor import MontageCompositor

router = APIRouter(prefix="/api/jobs", tags=["Montage Jobs"])

class CreateJobRequest(BaseModel):
    clip_ids: list[str]
    preset_id: str = "valorant_1080p"
    vibe_id: str = "hype_montage"
    target_duration: int = 60
    output_format: str = "9:16"
    bgm_path: str | None = None

class JobResponse(BaseModel):
    id: str
    preset_id: str
    vibe_id: str
    target_duration: int
    status: str
    progress: float
    error_message: str | None

def _run_montage_in_background(job_id: str, output_format: str, bgm_path: str | None):
    with Session(engine) as session:
        compositor = MontageCompositor(session)
        try:
            compositor.execute_job(
                job_id=job_id,
                output_format=output_format,
                bgm_path=bgm_path
            )
        except Exception:
            pass

@router.post("", response_model=JobResponse)
def create_job(
    payload: CreateJobRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    if not payload.clip_ids:
        raise HTTPException(status_code=400, detail="Must select at least one clip.")

    job = MontageJob(
        preset_id=payload.preset_id,
        vibe_id=payload.vibe_id,
        target_duration=payload.target_duration,
        selected_clips_json=json.dumps(payload.clip_ids),
        status="QUEUED",
        progress=0.0
    )
    session.add(job)
    session.commit()
    session.refresh(job)

    # Dispatch to background task
    background_tasks.add_task(
        _run_montage_in_background,
        job.id,
        payload.output_format,
        payload.bgm_path
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
