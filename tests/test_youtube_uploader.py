import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from backend.app.models.entities import ReelExport
from backend.app.engine.youtube_uploader import YouTubeUploader, YouTubeUploadResult

@pytest.fixture
def sample_export(tmp_path: Path):
    dummy_video = tmp_path / "reel_youtube.mp4"
    dummy_video.write_bytes(b"\x00\x00\x00\x18ftypmp42")

    return ReelExport(
        id="export-yt-1",
        job_id="job-yt",
        output_path=str(dummy_video),
        actual_duration=55.0,
        aspect_ratio="9:16",
        chapters_txt="00:00 - Intro\n00:10 - Kill 1",
        ai_title="VALORANT ACE COMPILATION #1",
        ai_description="Awesome highlights montage created with LazyCut."
    )

def test_youtube_upload_unconfigured_credentials(sample_export, tmp_path: Path):
    # When credentials file does not exist
    non_existent = tmp_path / "missing_secrets.json"
    uploader = YouTubeUploader(credentials_file=non_existent)
    result = uploader.upload_reel(sample_export)

    assert isinstance(result, YouTubeUploadResult)
    assert result.success is False
    assert result.is_configured is False
    assert "not found" in result.error.lower()

def test_youtube_upload_success_mocked(sample_export, tmp_path: Path):
    creds_file = tmp_path / "client_secrets.json"
    creds_file.write_text('{"installed": {"client_id": "test"}}', encoding="utf-8")

    uploader = YouTubeUploader(credentials_file=creds_file)

    # Mock the internal YouTube API build & insert execution
    mock_service = MagicMock()
    mock_request = MagicMock()
    mock_request.execute.return_value = {"id": "yt_video_12345"}
    mock_service.videos().insert.return_value = mock_request

    with patch.object(uploader, "_get_authenticated_service", return_value=mock_service):
        result = uploader.upload_reel(sample_export, privacy_status="unlisted")

        assert result.success is True
        assert result.is_configured is True
        assert result.video_id == "yt_video_12345"
        assert result.video_url == "https://youtu.be/yt_video_12345"

def test_youtube_upload_quota_exceeded_handled(sample_export, tmp_path: Path):
    creds_file = tmp_path / "client_secrets.json"
    creds_file.write_text('{"installed": {"client_id": "test"}}', encoding="utf-8")

    uploader = YouTubeUploader(credentials_file=creds_file)

    mock_service = MagicMock()
    mock_service.videos().insert.side_effect = Exception("quotaExceeded: The request cannot be completed")

    with patch.object(uploader, "_get_authenticated_service", return_value=mock_service):
        result = uploader.upload_reel(sample_export)

        assert result.success is False
        assert "quotaExceeded" in result.error
