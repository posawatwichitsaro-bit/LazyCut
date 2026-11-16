import pytest
from datetime import datetime, timezone
from sqlmodel import Session, create_engine, SQLModel
from backend.app.models.entities import SourceClip, MontageJob, ReelExport
from backend.app.engine.metadata_engine import ReelMetadataEngine

def test_metadata_engine_with_single_clip():
    clip = SourceClip(
        id="single-clip",
        file_path="C:/videos/ace.mp4",
        file_name="ace.mp4",
        duration=15.0,
        kill_count=5,
        is_verified=True
    )
    job = MontageJob(
        id="job-ace",
        preset_id="valorant_1080p",
        vibe_id="hype_montage",
        target_duration=60,
        created_at=datetime(2026, 11, 16, 15, 30, 0, tzinfo=timezone.utc)
    )

    engine = ReelMetadataEngine()
    meta = engine.generate_metadata(job=job, clips=[clip])

    assert "5 Kills" in meta.title
    assert "Clip 1 (5 Kills)" in meta.chapters_txt
    assert "#Shorts" in meta.tags
    assert "#Valorant" in meta.tags
