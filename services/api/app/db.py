"""DB wiring — slice runs on sqlite; models stay portable for the
Postgres+pgvector swap planned in docs/06 (JSON cols -> JSONB, add vector).
Run the API from services/api so ./data resolves here."""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_db_url = settings.database_url
if _db_url.startswith("postgres://"):
    _db_url = _db_url.replace("postgres://", "postgresql+psycopg://", 1)
elif _db_url.startswith("postgresql://") and not _db_url.startswith("postgresql+"):
    _db_url = _db_url.replace("postgresql://", "postgresql+psycopg://", 1)

if _db_url.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)

engine = create_engine(
    _db_url,
    connect_args={"check_same_thread": False} if _db_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Import models so create_all sees them
from app.models import Base  # noqa: E402


def init_db() -> None:
    Base.metadata.create_all(engine)
    _ensure_column("content", "embedding", "JSON")  # dev-DB migration shim (alembic: 11-formal)


def _ensure_column(table: str, column: str, ddl: str) -> None:
    """CREATE TABLE IF NOT EXISTS won't add columns to existing sqlite files."""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if table not in insp.get_table_names():
        return
    if column not in [c["name"] for c in insp.get_columns(table)]:
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Re-export model classes for convenient imports (app.db.User etc.)
from app.models import (  # noqa: E402,F401
    User,
    UserProfile,
    Task,
    SessionModel,
    SessionItem,
    Content,
    ContentSource,
    ContentReport,
    LockState,
    SESSION_ACTIVE,
    COMPLETED,
    ABANDONED,
    CONTENT_TYPES,
)
