"""Cursor-pagination helpers.

Implements the `(timestamp, id)` composite-cursor scheme documented in
`docs/architecture/api-design.md` — stable under concurrent inserts,
unlike offset pagination, because a cursor identifies "everything strictly
before this exact row" rather than "skip N rows," which stays correct even
if new rows are inserted ahead of the current page while a client is
paging through.

Shared here (not duplicated per-resource) because every future paginated
list endpoint (applications, resumes, ...) needs the same scheme.
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime


class InvalidCursorError(ValueError):
    """Raised when a client-supplied cursor string can't be decoded.

    A subclass of `ValueError` (not a bare custom exception) so it's
    naturally catchable alongside other malformed-input errors at the API
    boundary, without callers needing to know this specific type exists.
    """


def encode_cursor(*, created_at: datetime, id_: uuid.UUID) -> str:
    """Encode a `(created_at, id)` pair into an opaque, URL-safe cursor string."""
    raw = f"{created_at.isoformat()}|{id_}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, uuid.UUID]:
    """Decode a cursor produced by `encode_cursor` back into its parts.

    Raises `InvalidCursorError` for anything malformed — a client hand-editing
    or truncating the opaque string should get a clear 4xx-worthy error at
    the API layer, not an unhandled exception from base64/UUID parsing.
    """
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at_raw, id_raw = raw.split("|", 1)
        return datetime.fromisoformat(created_at_raw), uuid.UUID(id_raw)
    except (ValueError, UnicodeDecodeError) as exc:
        msg = "Cursor is malformed or was not produced by this API."
        raise InvalidCursorError(msg) from exc
