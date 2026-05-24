"""Small generation helpers for use cases.

Kept here (not in domain) because *when* an id/timestamp is assigned is an
application concern. Centralized so tests can monkeypatch them deterministically.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4


def new_id() -> str:
    """Return a new unique identifier."""
    return str(uuid4())


def now_utc() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)
