import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.core.database import get_session
from backend.app.models.entities import SourceClip

@pytest.fixture(name="client")
def client_fixture():
    # In-memory test SQLite engine with StaticPool so all connections share the same memory DB
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        # Seed test clips
        # Clip A: 15s, 3 kills, verified
        clip_a = SourceClip(
            id="clip-a",
            file_path="C:/videos/triple_kill.mp4",
            file_name="triple_kill.mp4",
            duration=15.0,
            kill_count=3,
            is_verified=True
        )
        # Clip B: 30s, 0 kills, unverified
        clip_b = SourceClip(
            id="clip-b",
            file_path="C:/videos/running.mp4",
            file_name="running.mp4",
            duration=30.0,
            kill_count=0,
            is_verified=False
        )
        # Clip C: 3s (too short), 1 kill, verified
        clip_c = SourceClip(
            id="clip-c",
            file_path="C:/videos/too_short.mp4",
            file_name="too_short.mp4",
            duration=3.0,
            kill_count=1,
            is_verified=True
        )
        # Clip D: 60s (too long), 2 kills, verified
        clip_d = SourceClip(
            id="clip-d",
            file_path="C:/videos/too_long.mp4",
            file_name="too_long.mp4",
            duration=60.0,
            kill_count=2,
            is_verified=True
        )
        session.add(clip_a)
        session.add(clip_b)
        session.add(clip_c)
        session.add(clip_d)
        session.commit()

        def get_test_session():
            with Session(test_engine) as s:
                yield s

        app.dependency_overrides[get_session] = get_test_session
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

def test_list_clips_filter_has_kills(client: TestClient):
    response = client.get("/api/clips?has_kills=true")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert all(c["kill_count"] > 0 for c in data)

def test_list_clips_filter_duration_range(client: TestClient):
    # Filter between 5.0s and 45.0s (excludes Clip C [3s] and Clip D [60s])
    response = client.get("/api/clips?min_duration=5.0&max_duration=45.0")
    assert response.status_code == 200
    data = response.json()
    file_names = [c["file_name"] for c in data]
    assert "triple_kill.mp4" in file_names
    assert "running.mp4" in file_names
    assert "too_short.mp4" not in file_names
    assert "too_long.mp4" not in file_names

def test_list_clips_filter_verified_kills_within_duration(client: TestClient):
    # Combined filter: verified + has kills + within 5-45s duration
    response = client.get("/api/clips?has_kills=true&is_verified=true&min_duration=5.0&max_duration=45.0")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["file_name"] == "triple_kill.mp4"

def test_clip_thumbnail_404_when_clip_not_found(client: TestClient):
    response = client.get("/api/clips/nonexistent-id/thumbnail")
    assert response.status_code == 404

def test_clip_analyze_404_when_clip_not_found(client: TestClient):
    response = client.get("/api/clips/nonexistent-id/analyze")
    assert response.status_code == 404

