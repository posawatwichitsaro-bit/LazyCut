import pytest
from unittest.mock import patch, MagicMock
from backend.app.models.entities import ReelExport, MontageJob
from backend.app.engine.notifier import WebhookNotifier, NotificationPayload

@pytest.fixture
def sample_export():
    return ReelExport(
        id="export-test-1",
        job_id="job-1",
        output_path="D:/LazyCut/exports/reel_test.mp4",
        actual_duration=45.2,
        aspect_ratio="9:16",
        chapters_txt="00:00 - Clip 1 (3 Kills)\n00:15 - Clip 2 (1 Kill)",
        ai_title="VALORANT ACE HIGHLIGHTS! 🔥"
    )

def test_build_discord_payload(sample_export):
    notifier = WebhookNotifier()
    payload = notifier.build_discord_payload(sample_export)

    assert "embeds" in payload
    embed = payload["embeds"][0]
    assert embed["title"] == "VALORANT ACE HIGHLIGHTS! 🔥"
    assert "45.2s" in embed["description"]
    assert "00:00" in embed["description"]
    assert embed["color"] == 0xF97316  # LazyCut orange accent

def test_send_discord_webhook_success(sample_export):
    notifier = WebhookNotifier()
    mock_resp = MagicMock()
    mock_resp.status_code = 204

    with patch("httpx.Client.post", return_value=mock_resp):
        success = notifier.send_discord("https://discord.com/api/webhooks/test/123", sample_export)
        assert success is True

def test_send_discord_webhook_graceful_on_error(sample_export):
    notifier = WebhookNotifier()
    with patch("httpx.Client.post", side_effect=Exception("Network Timeout")):
        success = notifier.send_discord("https://discord.com/api/webhooks/test/123", sample_export)
        assert success is False
