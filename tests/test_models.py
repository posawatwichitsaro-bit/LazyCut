import pytest
from sqlmodel import Session, create_engine, SQLModel, select
from backend.app.models.entities import SourceClip, KillEvent, MontageJob

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session

def test_source_clip_and_kills(test_db: Session):
    clip = SourceClip(
        file_path="C:/videos/clip1.mp4",
        file_name="clip1.mp4",
        duration=25.0,
        kill_count=2,
        is_verified=True
    )
    test_db.add(clip)
    test_db.commit()
    test_db.refresh(clip)

    ke1 = KillEvent(clip_id=clip.id, timestamp_sec=10.5, confidence=0.95)
    ke2 = KillEvent(clip_id=clip.id, timestamp_sec=12.0, confidence=0.92)
    test_db.add(ke1)
    test_db.add(ke2)
    test_db.commit()

    fetched = test_db.exec(select(SourceClip).where(SourceClip.id == clip.id)).first()
    assert fetched is not None
    assert fetched.file_name == "clip1.mp4"
    assert len(fetched.kill_events) == 2
