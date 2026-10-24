# app/db/types.py — portable column types for PostgreSQL and SQLite (SQLAlchemy 2.x)
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, TypeDecorator, Uuid
from sqlalchemy.dialects.postgresql import JSONB


class UTCDateTime(TypeDecorator):
    """Stores UTC; always returns timezone-aware UTC datetimes (SQLite drops tzinfo otherwise)."""

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value: datetime | None, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime passed to the database; use datetime.now(timezone.utc)")
        return value.astimezone(timezone.utc)

    def process_result_value(self, value: datetime | None, dialect):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


UUIDType = Uuid(as_uuid=True)                       # UUID on Postgres, CHAR(32) on SQLite
JSONType = JSON().with_variant(JSONB(), "postgresql")
