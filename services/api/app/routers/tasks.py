from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import err
from app.core.security import get_current_user
from app.db import get_db, Task, User
from app.schemas import TaskClarifyIn, TaskObject, TaskParseIn, TaskParseOut
from app.services import task_parser

router = APIRouter()


def _out(task: Task) -> TaskObject:
    return TaskObject(
        goal=task.goal or "learn", category=task.category or "education", subject=task.subject,
        topic=task.topic, subtopics=task.subtopics or [], level=task.level,
        urgency=task.urgency, duration_minutes=task.duration_minutes,
        language=task.language, confidence=task.confidence)


@router.post("/parse", response_model=TaskParseOut)
def parse(body: TaskParseIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    obj = task_parser.parse_task(body.raw_text, profile_language=user.profile.language if user.profile else "en")
    task = Task(user_id=user.id, raw_text=body.raw_text.strip(), **obj.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    clarification = task_parser.needs_clarification(obj)
    # slice: create the task as the answerable entity; clarify answers enrich it
    return TaskParseOut(task_id=task.id, task=_out(task), clarification=clarification)


@router.post("/{task_id}/clarify", response_model=TaskParseOut)
def clarify(task_id: str, body: TaskClarifyIn, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    task = db.scalar(select(Task).where(Task.id == task_id, Task.user_id == user.id))
    if task is None:
        raise err(404, "NOT_FOUND", "Task not found")
    refined = task_parser.refine_with_answer(_out(task), body.answer)
    for k, v in refined.model_dump().items():
        setattr(task, k, v)
    task.clarified = True
    db.commit()
    return TaskParseOut(task_id=task.id, task=_out(task), clarification=task_parser.needs_clarification(refined))
