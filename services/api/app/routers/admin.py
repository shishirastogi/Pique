"""Admin route (docs/07 §4.14 subset). SLICE: dev-only, unauthenticated —
role gating arrives with admin accounts. Do not expose publicly."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db import get_db
from app.services import ingestion

router = APIRouter()


class IngestRunIn(BaseModel):
    topics: list[str] = Field(min_length=1, max_length=20)
    per_provider: int = Field(default=10, ge=1, le=50)


@router.post("/ingestion/run")
def ingestion_run(body: IngestRunIn, db: Session = Depends(get_db)):
    """Prefetch content for topics (docs/08 §8). Idempotent; provider failures
    are reported per-provider, never fatal."""
    return {"topics": {t: ingestion.ingest_topic(db, t.strip(), body.per_provider)
                       for t in body.topics if t.strip()}}
