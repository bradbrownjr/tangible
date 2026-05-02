"""SQLAlchemy engine, session, and base."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tangible.config import Settings


def _apply_sqlite_pragmas(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
    """Enable WAL + foreign keys for SQLite (safe, recommended defaults)."""
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA temp_store=MEMORY")
    finally:
        cursor.close()


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def init_engine(settings: Settings) -> Engine:
    """Create (or return) the global SQLAlchemy engine."""
    global _engine, _SessionLocal
    url = settings.resolved_database_url()
    connect_args: dict[str, Any] = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
        engine = create_engine(url, future=True, connect_args=connect_args)
        event.listen(engine, "connect", _apply_sqlite_pragmas)
    else:
        engine = create_engine(
            url,
            future=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_pool_max_overflow,
            pool_pre_ping=True,
        )
    _engine = engine
    _SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Engine not initialized; call init_engine() first")
    return _engine


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a session."""
    if _SessionLocal is None:
        raise RuntimeError("Sessionmaker not initialized; call init_engine() first")
    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()
