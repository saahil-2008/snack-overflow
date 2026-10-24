# app/db/session.py — SQLAlchemy engine and session factory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.core.config import DATABASE_URL
from app.db.models import Base

_connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_connect_args, echo=False)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
