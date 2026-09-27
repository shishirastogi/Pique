"""Time helpers. Server is the clock authority (docs/04 §3, docs/07).

Slice stores naive UTC datetimes in sqlite; API serializes with an explicit 'Z'.
"""
from datetime import datetime, timezone


def now_utc() -> datetime:
    """Naive UTC now (consistent storage in sqlite)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_z(dt: datetime | None) -> str | None:
    """Naive-UTC datetime -> ISO-8601 with Z suffix for clients."""
    if dt is None:
        return None
    return dt.replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
