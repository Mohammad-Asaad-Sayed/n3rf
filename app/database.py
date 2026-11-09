from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from threading import Lock

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "n3rf.sqlite3"
PROJECT_DIR = Path(__file__).resolve().parents[1]
LEGACY_BASELINE_REVISION = "0001_initial_schema"
APPLICATION_TABLES = frozenset({"workflows", "runs", "model_profiles"})
_ENGINE_LOCK = Lock()


def database_url() -> str:
    configured_url = os.environ.get("N3RF_DATABASE_URL")
    if configured_url:
        return configured_url
    configured_path = os.environ.get("N3RF_DB_PATH")
    path = Path(configured_path).expanduser() if configured_path else DEFAULT_DB_PATH
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{path}"


def _alembic_config(connection: Connection) -> Config:
    config = Config(str(PROJECT_DIR / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url().replace("%", "%%"))
    config.attributes["connection"] = connection
    return config


def _migrate(engine: Engine) -> None:
    from sqlalchemy import inspect

    with engine.begin() as connection:
        tables = set(inspect(connection).get_table_names())
        app_tables = tables & APPLICATION_TABLES
        has_version = False
        if "alembic_version" in tables:
            has_version = (
                connection.scalar(text("SELECT version_num FROM alembic_version LIMIT 1"))
                is not None
            )
        if not has_version and app_tables:
            if app_tables != APPLICATION_TABLES:
                missing = ", ".join(sorted(APPLICATION_TABLES - app_tables))
                raise RuntimeError(
                    "The existing database has an incomplete n3rf schema "
                    f"(missing tables: {missing}); refusing to stamp it as migrated."
                )
            command.stamp(_alembic_config(connection), LEGACY_BASELINE_REVISION)
        command.upgrade(_alembic_config(connection), "head")


@lru_cache(maxsize=8)
def _engine_for_url(database_url: str) -> Engine:
    url = make_url(database_url)
    connect_args = (
        {"check_same_thread": False, "timeout": 10} if url.drivername.startswith("sqlite") else {}
    )
    engine = create_engine(url, connect_args=connect_args)
    _migrate(engine)
    return engine


def get_engine() -> Engine:
    with _ENGINE_LOCK:
        return _engine_for_url(database_url())
