"""Auth for the slice — anonymous device accounts (docs/07 §2).

Stateless HMAC-signed token:  base64url(user_id).exp.base64url(sig)
Proper JWT rotation/reuse-detection arrives with email linking (post-MVP).
"""
import base64
import hashlib
import hmac
import time

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import err
from app.db import get_db, User


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def create_token(user_id: str) -> str:
    exp = int(time.time()) + settings.token_ttl_seconds
    uid_b64 = _b64e(user_id.encode())
    msg = f"{uid_b64}.{exp}".encode()
    sig = hmac.new(settings.secret_key.encode(), msg, hashlib.sha256).digest()
    return f"{uid_b64}.{exp}.{_b64e(sig)}"


def verify_token(token: str) -> str:
    try:
        uid_b64, exp_s, sig_b64 = token.split(".")
        msg = f"{uid_b64}.{exp_s}".encode()
        expected = hmac.new(settings.secret_key.encode(), msg, hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            raise ValueError("bad signature")
        if int(exp_s) < time.time():
            raise ValueError("expired")
        return _b64d(uid_b64).decode()
    except Exception:
        raise err(401, "AUTH", "Invalid or expired token")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise err(401, "AUTH", "Missing bearer token")
    user_id = verify_token(auth.removeprefix("Bearer ").strip())
    user = db.scalar(select(User).where(User.id == user_id, User.deleted_at.is_(None)))
    if user is None:
        raise err(401, "AUTH", "Unknown user")
    return user
