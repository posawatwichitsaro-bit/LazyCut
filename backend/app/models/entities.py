import uuid
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Relationship

def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)

class SourceClip(SQLModel, table=True):
    __tablename__ = "source_clips"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    file_path: str = Field(index=True, unique=True)
    file_name: str
    duration: float = Field(default=0.0)
    file_size: int = Field(default=0)
    kill_count: int = Field(default=0)
    is_verified: bool = Field(default=False)
    scanned_at: datetime | None = Field(default=None)
    created_at: datetime = Field(default_factory=get_utc_now)

    kill_events: list["KillEvent"] = Relationship(back_populates="clip", cascade_delete=True)


class KillEvent(SQLModel, table=True):
    __tablename__ = "kill_events"

    id: int | None = Field(default=None, primary_key=True)
    clip_id: str = Field(foreign_key="source_clips.id", index=True)
    timestamp_sec: float
    confidence: float = Field(default=1.0)
    event_type: str = Field(default="skull_banner")

    clip: SourceClip | None = Relationship(back_populates="kill_events")


class ClipAnalysis(SQLModel, table=True):
    __tablename__ = "clip_analyses"

    clip_id: str = Field(foreign_key="source_clips.id", primary_key=True)
    revision: str
    moments_json: str


class MontageJob(SQLModel, table=True):
    __tablename__ = "montage_jobs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    preset_id: str = Field(default="valorant_1080p")
    vibe_id: str = Field(default="hype_montage")
    target_duration: int = Field(default=60)
    selected_clips_json: str = Field(default="[]")
    status: str = Field(default="QUEUED", index=True)  # QUEUED, PROCESSING, COMPLETED, FAILED
    progress: float = Field(default=0.0)
    error_message: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=get_utc_now)

    exports: list["ReelExport"] = Relationship(back_populates="job", cascade_delete=True)


class ReelExport(SQLModel, table=True):
    __tablename__ = "reel_exports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="montage_jobs.id", index=True)
    output_path: str
    actual_duration: float = Field(default=0.0)
    aspect_ratio: str = Field(default="9:16")
    chapters_txt: str = Field(default="")
    ai_title: str | None = Field(default=None)
    ai_description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=get_utc_now)

    job: MontageJob | None = Relationship(back_populates="exports")
