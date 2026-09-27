"""Pydantic in/out schemas (slice mirrors packages/shared-types contract)."""
from typing import Any, Literal
from pydantic import BaseModel, Field

# ---------- shared ----------

TaskLevel = Literal["beginner", "intermediate", "advanced"]
Duration = Literal[5, 10, 15, 20]


class TaskObject(BaseModel):
    goal: str
    category: str
    subject: str | None = None
    topic: str
    subtopics: list[str] = []
    level: TaskLevel | None = None
    urgency: str | None = None
    duration_minutes: int | None = None
    language: str = "en"
    confidence: float = 0.0


class ClarifyingQuestion(BaseModel):
    field: str
    question: str
    options: list[str]


class ProfileOut(BaseModel):
    language: str
    knowledge_default: str
    content_preferences: list[str]
    humor_preference: str | None
    interests: list[str]
    study_areas: list[str]
    region: str | None
    lock_minutes: int
    default_duration_minutes: int
    personalization_enabled: bool
    auto_advance: bool


# ---------- auth ----------

class AuthSessionIn(BaseModel):
    device_fp: str = Field(min_length=8, max_length=128)


class AuthSessionOut(BaseModel):
    access_token: str
    user_id: str
    is_new_user: bool


# ---------- tasks ----------

class TaskParseIn(BaseModel):
    raw_text: str = Field(min_length=3, max_length=500)


class TaskParseOut(BaseModel):
    task_id: str
    task: TaskObject
    clarification: ClarifyingQuestion | None = None


class TaskClarifyIn(BaseModel):
    answer: str = Field(min_length=1, max_length=100)


# ---------- sessions ----------

class SessionCreateIn(BaseModel):
    task_id: str
    duration_minutes: Duration


class MediaRef(BaseModel):
    kind: Literal["image", "gif", "svg", "none"] = "none"
    url: str | None = None


class Interaction(BaseModel):
    kind: Literal["none", "poll", "question", "challenge", "reveal", "finish"] = "none"
    question: str | None = None
    options: list[str] | None = None
    hint: str | None = None
    answer: str | None = None
    reveal: str | None = None


class ContentCard(BaseModel):
    content_id: str
    position: int
    phase: str
    planned_seconds: int
    type: str
    title: str | None = None
    body: str
    media: MediaRef | None = None
    attribution: dict | None = None
    interaction: Interaction | None = None


class SessionOut(BaseModel):
    session_id: str
    status: str
    task: TaskObject
    duration_minutes: int
    planned_items: int
    started_at: str
    ends_at: str


class SessionItemsOut(BaseModel):
    items: list[ContentCard]


class SessionEventIn(BaseModel):
    type: Literal["item_shown", "item_done", "heartbeat", "initiation_reported"]
    content_id: str | None = None
    position: int | None = None
    dwell_ms: int | None = None
    skipped: bool | None = None
    engagement: dict[str, Any] | None = None
    started: bool | None = None  # for initiation_reported
    client_now: str | None = None


class SessionEventsIn(BaseModel):
    events: list[SessionEventIn]


class SessionEventsOut(BaseModel):
    server_now: str
    force_complete: bool


class SessionCompleteIn(BaseModel):
    started_work_confirmed: bool | None = None
    abandoned: bool = False
    abandon_reason: str | None = None


class SessionCompleteOut(BaseModel):
    status: str
    lock: dict


# ---------- lock ----------

class LockStatusOut(BaseModel):
    locked: bool
    lock_until: str | None = None
    remaining_seconds: int = 0
    session_id: str | None = None


class EmergencyUnlockIn(BaseModel):
    confirm: str


# ---------- profile ----------

class ProfilePatchIn(BaseModel):
    language: str | None = None
    knowledge_default: TaskLevel | None = None
    content_preferences: list[str] | None = None
    humor_preference: str | None = None
    interests: list[str] | None = None
    study_areas: list[str] | None = None
    region: str | None = None
    lock_minutes: int | None = Field(default=None, ge=15, le=480)
    default_duration_minutes: Duration | None = None
    personalization_enabled: bool | None = None
    auto_advance: bool | None = None


# ---------- content ----------

class ContentReportIn(BaseModel):
    content_id: str
    session_id: str | None = None
    reason: Literal["inappropriate", "wrong", "copyright", "off_topic", "other"]
    comment: str | None = Field(default=None, max_length=1000)
