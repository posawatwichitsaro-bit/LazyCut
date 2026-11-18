import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy.pool import StaticPool
from backend.app.main import app
from backend.app.core.database import get_session
from backend.app.models.entities import SourceClip, MontageJob, ReelExport

@pytest.fixture(name="client")
def client_fixture():
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
    SQLModel.metadata.create_all(test_engine)

    with Session(test_engine) as session:
        clip = SourceClip(
            id="clip-test-1",
            file_path="C:/videos/highlight.mp4",
            file_name="highlight.mp4",
            duration=12.0,
            kill_count=2,
            is_verified=True
        )
        session.add(clip)

        # Pre-seed a completed job with export
        completed_job = MontageJob(
            id="job-done-1",
            preset_id="valorant_1080p",
            vibe_id="hype_montage",
            target_duration=60,
            status="COMPLETED",
            progress=1.0
        )
        session.add(completed_job)

        export = ReelExport(
            id="export-1",
            job_id="job-done-1",
            output_path="D:/LazyCut/exports/reel_done.mp4",
            actual_duration=12.0,
            aspect_ratio="9:16",
            chapters_txt="00:00 - Clip 1 (2 Kills)",
            ai_title="Valorant Highlights - 2026-11-16 (2 Kills)"
        )
        session.add(export)
        session.commit()

        def get_test_session():
            with Session(test_engine) as s:
                yield s

        app.dependency_overrides[get_session] = get_test_session
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

def test_create_job_empty_clips_fails(client: TestClient):
    response = client.post("/api/jobs", json={"clip_ids": []})
    assert response.status_code == 400
    assert "Must select at least one clip" in response.json()["detail"]

def test_create_job_valid(client: TestClient):
    response = client.post(
        "/api/jobs",
        json={
            "clip_ids": ["clip-test-1"],
            "preset_id": "valorant_1080p",
            "vibe_id": "hype_montage",
            "target_duration": 60,
            "output_format": "9:16"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "QUEUED"
    assert data["preset_id"] == "valorant_1080p"
    assert data["target_duration"] == 60

def test_get_job_status(client: TestClient):
    response = client.get("/api/jobs/job-done-1")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["progress"] == 1.0

def test_get_job_not_found(client: TestClient):
    response = client.get("/api/jobs/non-existent-id")
    assert response.status_code == 404

def test_get_job_export(client: TestClient):
    response = client.get("/api/jobs/job-done-1/export")
    assert response.status_code == 200
    data = response.json()
    assert data["actual_duration"] == 12.0
    assert "2 Kills" in data["chapters"]
    assert "Valorant Highlights" in data["ai_title"]

def test_folder_job_snapshots_registered_files_in_current_folder(client, tmp_path, monkeypatch):
    import json
    from backend.app.api import jobs
    from backend.app.core.config import settings

    folder = tmp_path / "recordings"
    folder.mkdir()
    monkeypatch.setattr(settings, "watch_path", str(folder))
    def inspect_snapshot(bind, job_id, payload):
        with Session(bind) as session:
            assert json.loads(session.get(MontageJob, job_id).selected_clips_json) == ["ready"]
            assert payload.folder_queue

    monkeypatch.setattr(jobs, "_run_montage_in_background", inspect_snapshot)
    path = folder / "ready.mp4"
    path.touch()
    dependency = app.dependency_overrides[get_session]
    sessions = dependency()
    session = next(sessions)
    try:
        session.add(SourceClip(id="ready", file_name=path.name, file_path=str(path)))
        session.commit()
    finally:
        sessions.close()
    assert client.post("/api/jobs", json={"folder_queue": True}).status_code == 200

def test_reel_rating_replaces_previous_count_and_persists(client, tmp_path, monkeypatch):
    import json
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "exports_dir", tmp_path)
    url = "/api/jobs/reels/export-1/rating"
    assert client.put(url, json={"rating": "ดี"}).json()["counts"]["ดี"] == 1
    result = client.put(url, json={"rating": "ดีมาก"}).json()
    assert result["counts"] == {"ดีมาก": 1, "ดี": 0, "แย่": 0, "แย่มาก": 0}
    assert json.loads((tmp_path / "ratings.json").read_text(encoding="utf8")) == {"export-1": "ดีมาก"}
    assert client.get("/api/jobs/reels/history").json()["ratings"] == {"export-1": "ดีมาก"}
    assert client.get("/api/jobs/job-done-1/exports").json()[0]["filename"] == "reel_done.mp4"
