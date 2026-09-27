"""ORM models — vertical-slice subset of docs/06-database.md.

Slice deltas vs the full schema (deliberate, resolved in later phases):
- sqlite storage: JSON columns stand in for jsonb/arrays; no vector column yet
- feedback/analytics/moderation_queue/experiment tables land with their phases
- content.embedding omitted until pgvector swap
Names/columns otherwise match the doc so the swap is mechanical.
"""
import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.core.time import now_utc


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=_uuid)
    device_fp: Mapped[str] = mapped_column(sa.String, unique=True, index=True)
    email: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)
    deleted_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[str] = mapped_column(sa.ForeignKey("users.id"), primary_key=True)
    language: Mapped[str] = mapped_column(sa.String, default="en")           # en|hi|hinglish
    knowledge_default: Mapped[str] = mapped_column(sa.String, default="beginner")
    content_preferences: Mapped[list] = mapped_column(sa.JSON, default=list)  # format checkboxes
    humor_preference: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    interests: Mapped[list] = mapped_column(sa.JSON, default=list)
    study_areas: Mapped[list] = mapped_column(sa.JSON, default=list)
    region: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    lock_minutes: Mapped[int] = mapped_column(sa.Integer, default=120)
    default_duration_minutes: Mapped[int] = mapped_column(sa.Integer, default=10)
    personalization_enabled: Mapped[bool] = mapped_column(sa.Boolean, default=True)
    auto_advance: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc, onupdate=now_utc)

    user: Mapped[User] = relationship(back_populates="profile")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(sa.ForeignKey("users.id"), index=True)
    raw_text: Mapped[str] = mapped_column(sa.Text)
    goal: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    category: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    subject: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    topic: Mapped[str] = mapped_column(sa.String)
    subtopics: Mapped[list] = mapped_column(sa.JSON, default=list)
    level: Mapped[str | None] = mapped_column(sa.String, nullable=True)  # beginner|intermediate|advanced
    urgency: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    language: Mapped[str] = mapped_column(sa.String, default="en")
    confidence: Mapped[float] = mapped_column(sa.Float, default=0.0)
    clarified: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)


# Session states per docs/04 §2 (slice persists the server-side subset)
SESSION_ACTIVE = "SESSION_ACTIVE"
COMPLETED = "COMPLETED"
ABANDONED = "ABANDONED"


class SessionModel(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(sa.ForeignKey("users.id"), index=True)
    task_id: Mapped[str] = mapped_column(sa.ForeignKey("tasks.id"))
    status: Mapped[str] = mapped_column(sa.String, default=SESSION_ACTIVE)
    duration_minutes: Mapped[int] = mapped_column(sa.Integer)
    planned_items: Mapped[int] = mapped_column(sa.Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)
    ends_at: Mapped[datetime] = mapped_column(sa.DateTime)  # server-authoritative
    completed_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    abandon_reason: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    started_work_confirmed: Mapped[bool | None] = mapped_column(sa.Boolean, nullable=True)
    initiation_reported_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    offline: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)

    items: Mapped[list["SessionItem"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="SessionItem.position"
    )


# Content types per docs/00 conventions (16 MVP types) + book_excerpt
# (docs/14 plan registry "later types", promoted now — Gutenberg excerpts need it)
CONTENT_TYPES = (
    "meme", "interesting_fact", "quote", "visual_explanation", "analogy", "joke",
    "poll", "question", "mini_story", "trivia", "historical_context", "diagram",
    "reaction_gif", "micro_lesson", "challenge", "first_work_action", "book_excerpt",
)


class Content(Base):
    __tablename__ = "content"
    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=_uuid)
    type: Mapped[str] = mapped_column(sa.String, index=True)
    title: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    body: Mapped[str] = mapped_column(sa.Text)
    language: Mapped[str] = mapped_column(sa.String, default="en")
    topic: Mapped[str] = mapped_column(sa.String, index=True)
    subtopics: Mapped[list] = mapped_column(sa.JSON, default=list)
    tags: Mapped[list] = mapped_column(sa.JSON, default=list)
    difficulty: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    tone: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    humor_style: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    media: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)     # {kind,url,...}|None
    interaction: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)  # {kind, ...}
    scores: Mapped[dict] = mapped_column(sa.JSON, default=dict)
    embedding: Mapped[list | None] = mapped_column(sa.JSON, nullable=True)  # vector; pgvector col in 11-formal
    status: Mapped[str] = mapped_column(sa.String, default="active")  # active|quarantined|removed
    generated_by: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)


class ContentSource(Base):
    """Provenance — every external asset needs a row (docs/06, docs/11 S2)."""
    __tablename__ = "content_sources"
    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=_uuid)
    content_id: Mapped[str] = mapped_column(sa.ForeignKey("content.id"), index=True)
    provider: Mapped[str] = mapped_column(sa.String)      # generated|openverse|wikimedia|...
    source_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    source_url: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    creator: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    license: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    license_url: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    attribution_required: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    attribution_text: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    fetchable: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    fetched_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)


class SessionItem(Base):
    __tablename__ = "session_items"
    __table_args__ = (sa.UniqueConstraint("session_id", "position"),)
    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(sa.ForeignKey("sessions.id"), index=True)
    content_id: Mapped[str] = mapped_column(sa.ForeignKey("content.id"))
    position: Mapped[int] = mapped_column(sa.Integer)
    phase: Mapped[str] = mapped_column(sa.String)  # entertainment|curiosity|understanding|activation
    planned_seconds: Mapped[int] = mapped_column(sa.Integer, default=45)
    shown_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    dwell_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    skipped: Mapped[bool] = mapped_column(sa.Boolean, default=False)
    engagement: Mapped[dict | None] = mapped_column(sa.JSON, nullable=True)

    session: Mapped[SessionModel] = relationship(back_populates="items")
    content: Mapped[Content] = relationship()


class ContentReport(Base):
    __tablename__ = "content_reports"
    id: Mapped[str] = mapped_column(sa.String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(sa.ForeignKey("users.id"), index=True)
    content_id: Mapped[str] = mapped_column(sa.ForeignKey("content.id"))
    session_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    reason: Mapped[str] = mapped_column(sa.String)
    comment: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    status: Mapped[str] = mapped_column(sa.String, default="open")
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)


class LockState(Base):
    __tablename__ = "lock_state"
    user_id: Mapped[str] = mapped_column(sa.ForeignKey("users.id"), primary_key=True)
    lock_until: Mapped[datetime] = mapped_column(sa.DateTime)
    session_id: Mapped[str | None] = mapped_column(sa.String, nullable=True)
    broken_at: Mapped[datetime | None] = mapped_column(sa.DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime, default=now_utc)
