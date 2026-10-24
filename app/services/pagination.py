# app/services/pagination.py — cursor pagination helper (Section 6.3.7)
import base64
from datetime import datetime, timezone
from uuid import UUID

from app.core.errors import ApiError


def encode_cursor(dt: datetime, entity_id: UUID) -> str:
    """Encode cursor as URL-safe base64 of '<createdAt ISO>|<id>'."""
    iso = dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    raw = f"{iso}|{entity_id}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """Decode cursor. Raises VALIDATION_ERROR on bad cursor."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode()).decode()
        parts = raw.split("|", 1)
        dt_str, id_str = parts[0], parts[1]
        dt = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        uid = UUID(id_str)
        return dt, uid
    except Exception:
        raise ApiError(422, "VALIDATION_ERROR", "Request validation failed",
                       {"fields": [{"field": "cursor", "message": "Invalid cursor value", "type": "value_error"}]})


def paginate(query, model, limit: int, cursor: str | None, sort_field="created_at", ascending=False):
    """Apply cursor pagination to a SQLAlchemy query.

    Returns (items, next_cursor).
    sort_field is the column name used for cursor comparison (default: created_at).
    For telemetry, use sort_field='recorded_at' and ascending=True.
    """
    from sqlalchemy import asc, desc

    sort_col = getattr(model, sort_field)
    id_col = model.id

    if ascending:
        order = [asc(sort_col), asc(id_col)]
    else:
        order = [desc(sort_col), desc(id_col)]

    if cursor:
        cursor_dt, cursor_id = decode_cursor(cursor)
        if ascending:
            query = query.filter(
                (sort_col > cursor_dt) |
                ((sort_col == cursor_dt) & (id_col > cursor_id))
            )
        else:
            query = query.filter(
                (sort_col < cursor_dt) |
                ((sort_col == cursor_dt) & (id_col < cursor_id))
            )

    query = query.order_by(*order)
    rows = query.limit(limit + 1).all()

    if len(rows) > limit:
        items = rows[:limit]
        last = items[-1]
        next_cursor = encode_cursor(getattr(last, sort_field), last.id)
    else:
        items = rows
        next_cursor = None

    return items, next_cursor
