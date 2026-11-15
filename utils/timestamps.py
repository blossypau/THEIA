from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def to_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat() if value.tzinfo else value.replace(tzinfo=timezone.utc).isoformat()


def utc_now() -> datetime:
    """UTC wall time compatible with existing timezone-naive SQLite columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
