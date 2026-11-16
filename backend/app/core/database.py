from sqlmodel import SQLModel, create_engine, Session
from backend.app.core.config import settings

# SQLite database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
    echo=False
)

def init_db() -> None:
    """Creates all database tables defined in SQLModel entities."""
    from backend.app.models import entities  # noqa: F401
    SQLModel.metadata.create_all(engine)

def get_session():
    """FastAPI dependency for obtaining a database session."""
    with Session(engine) as session:
        yield session
