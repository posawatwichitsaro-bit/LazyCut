import pytest
from datetime import datetime, timezone
from backend.app.models.entities import SourceClip, MontageJob
from backend.app.engine.metadata_engine import ReelMetadataEngine, ReelMetadataResult

def test_zero_ai_fallback_metadata():
    # Arrange: 2 sample source clips and a montage job
    clip1 = SourceClip(
        id="c1",
        file_path="C:/videos/clip1.mp4",
        file_name="valorant_ace.mp4",
        duration=12.0,
        kill_count=3,
        is_verified=True
    )
    clip2 = SourceClip(
        id="c2",
        file_path="C:/videos/clip2.mp4",
        file_name="valorant_clutch.mp4",
        duration=8.0,
        kill_count=1,
        is_verified=True
    )
    job = MontageJob(
        id="job-12345678-abcd",
        preset_id="valorant_1080p",
        vibe_id="hype_montage",
        target_duration=60,
        created_at=datetime(2026, 11, 16, 12, 0, 0, tzinfo=timezone.utc)
    )

    # Act
    engine = ReelMetadataEngine()
    result: ReelMetadataResult = engine.generate_metadata(job=job, clips=[clip1, clip2])

    # Assert: Public interface contract
    assert isinstance(result, ReelMetadataResult)
    assert result.is_ai_generated is False
    assert "Valorant" in result.title
    assert "4 Kills" in result.title  # 3 + 1 kills
    assert "#Valorant" in result.tags
    assert "#Shorts" in result.tags
    
    # Chapters should be formatted for YouTube/Shorts
    assert "00:00" in result.chapters_txt
    assert "Clip 1 (3 Kills)" in result.chapters_txt
    assert "Clip 2 (1 Kill)" in result.chapters_txt
