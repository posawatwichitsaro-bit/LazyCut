import pytest
from unittest.mock import patch, MagicMock
from backend.app.models.entities import SourceClip, MontageJob
from backend.app.engine.ai_router import AIRouter, AIMetadataResponse

@pytest.fixture
def sample_clips():
    return [
        SourceClip(id="c1", file_path="c1.mp4", file_name="ace.mp4", duration=14.0, kill_count=4, is_verified=True),
        SourceClip(id="c2", file_path="c2.mp4", file_name="clutch.mp4", duration=10.0, kill_count=1, is_verified=True),
    ]

@pytest.fixture
def sample_job():
    return MontageJob(
        id="job-ai-1",
        preset_id="valorant_1080p",
        vibe_id="hype_montage",
        target_duration=60
    )

def test_ai_router_fallback_when_no_provider(sample_job, sample_clips):
    router = AIRouter(provider="none")
    result: AIMetadataResponse = router.generate(job=sample_job, clips=sample_clips)

    assert isinstance(result, AIMetadataResponse)
    assert result.is_fallback is True
    assert "Valorant" in result.title
    assert "5 Kills" in result.title
    assert "#Valorant" in result.tags

def test_ai_router_graceful_fallback_on_network_failure(sample_job, sample_clips):
    # When Ollama or Cloud API is unreachable / raises connection error
    router = AIRouter(provider="ollama", base_url="http://127.0.0.1:99999")
    with patch("httpx.Client.post", side_effect=Exception("Connection refused")):
        result: AIMetadataResponse = router.generate(job=sample_job, clips=sample_clips)
        assert result.is_fallback is True
        assert "Valorant" in result.title
        assert "#Shorts" in result.tags

def test_ai_router_successful_llm_response(sample_job, sample_clips):
    # Mocking successful LLM generation
    router = AIRouter(provider="ollama")
    mock_llm_json = (
        '{"title": "INSANE VALORANT ACE + CLUTCH! 🔥", '
        '"description": "Clean 5 kills montage rendered in 9:16 Shorts format.", '
        '"tags": ["#Valorant", "#Ace", "#Gaming", "#Montage"]}'
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"response": mock_llm_json}

    with patch("httpx.Client.post", return_value=mock_resp):
        result: AIMetadataResponse = router.generate(job=sample_job, clips=sample_clips)
        assert result.is_fallback is False
        assert "INSANE VALORANT ACE" in result.title
        assert "#Ace" in result.tags
