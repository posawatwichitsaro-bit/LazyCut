import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

def test_home_page_returns_modern_dashboard():
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text

    # Verify 3 core screens/tabs from Round 3 Q5
    assert "Studio Feed" in html
    assert "Reel Inspector" in html
    assert "Settings" in html

    # Verify key interactive controls
    assert "filterPills" in html or "filterClips" in html
    assert "Generate 9:16 Reel" in html
    assert "videoPlayer" in html or "video" in html
