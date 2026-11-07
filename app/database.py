from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "n3rf.sqlite3"


@lru_cache(maxsize=8)
def _engine_for_url(database_url: str) -> Engine:
    url = make_url(database_url)
    connect_args = (
        {"check_same_thread": False, "timeout": 10} if url.drivername.startswith("sqlite") else {}
    )
    engine = create_engine(
        url,
        connect_args=connect_args,
    )
    from app import models  # noqa: F401

    Base.metadata.create_all(engine)
    return engine


def get_engine() -> Engine:
    database_url = os.environ.get("N3RF_DATABASE_URL")
    if database_url:
        return _engine_for_url(database_url)
    configured_path = os.environ.get("N3RF_DB_PATH")
    path = Path(configured_path).expanduser() if configured_path else DEFAULT_DB_PATH
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return _engine_for_url(f"sqlite:///{path}")
