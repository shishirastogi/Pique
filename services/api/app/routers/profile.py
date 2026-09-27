from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.db import get_db, User, UserProfile
from app.schemas import ProfileOut, ProfilePatchIn

router = APIRouter()

_FIELDS = ("language", "knowledge_default", "content_preferences", "humor_preference",
           "interests", "study_areas", "region", "lock_minutes",
           "default_duration_minutes", "personalization_enabled", "auto_advance")


def _out(p: UserProfile) -> ProfileOut:
    return ProfileOut(**{f: getattr(p, f) for f in _FIELDS})


@router.get("", response_model=ProfileOut)
def get_profile(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if user.profile is None:
        user.profile = UserProfile(user_id=user.id)
        db.add(user.profile)
        db.commit()
        db.refresh(user)
    return _out(user.profile)


@router.patch("", response_model=ProfileOut)
def patch_profile(body: ProfilePatchIn, db: Session = Depends(get_db),
                  user: User = Depends(get_current_user)):
    if user.profile is None:
        user.profile = UserProfile(user_id=user.id)
        db.add(user.profile)
    for k, v in body.model_dump(exclude_none=True).items():
        setattr(user.profile, k, v)
    db.add(user.profile)
    db.commit()
    db.refresh(user.profile)
    return _out(user.profile)
