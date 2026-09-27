from sqlalchemy import select
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.errors import err
from app.core.security import get_current_user
from app.db import Content, ContentReport, User, get_db
from app.schemas import ContentReportIn

router = APIRouter()


@router.post("/report", status_code=201)
def report(body: ContentReportIn, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    content = db.scalar(select(Content).where(Content.id == body.content_id))
    if content is None:
        raise err(404, "NOT_FOUND", "Content not found")
    db.add(ContentReport(user_id=user.id, content_id=body.content_id,
                         session_id=body.session_id, reason=body.reason,
                         comment=body.comment))
    db.commit()
    # slice: replacement_item is null; reserve-swap arrives with real pools (05 §7)
    return {"report_id": "ok", "replacement_item": None}
