"""SQLite engine + session helper."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import get_settings

_url = get_settings().database_url
_is_sqlite = _url.startswith("sqlite")
_is_memory = _url in ("sqlite://", "sqlite:///:memory:")

_kwargs: dict = {"echo": False}
if _is_sqlite:
    _kwargs["connect_args"] = {"check_same_thread": False}
if _is_memory:
    # one shared in-memory DB for the whole process (used by tests)
    _kwargs["poolclass"] = StaticPool

engine = create_engine(_url, **_kwargs)


def init_db() -> None:
    """Create any missing tables. Safe to call on every startup."""
    from app.db import models  # noqa: F401  (registers the table classes)

    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
