from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import create_engine, inspect, text

from app.database import Base, get_engine
from app.models import WorkflowRecord


def test_new_database_is_initialized_with_alembic(tmp_path, monkeypatch):
    database_path = tmp_path / "fresh.sqlite3"
    monkeypatch.setenv("N3RF_DB_PATH", str(database_path))

    engine = get_engine()

    assert set(inspect(engine).get_table_names()) == {
        "alembic_version",
        "model_profiles",
        "runs",
        "workflows",
    }
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0001_initial_schema"
        )


def test_existing_database_is_stamped_and_keeps_saved_workflows(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.sqlite3"
    legacy_engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(
            WorkflowRecord.__table__.insert().values(
                id="wf_legacy",
                name="Keep me",
                data='{"nodes":[],"edges":[]}',
            )
        )
    legacy_engine.dispose()
    monkeypatch.setenv("N3RF_DB_PATH", str(database_path))

    migrated_engine = get_engine()

    with migrated_engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT name FROM workflows WHERE id = 'wf_legacy'"))
            == "Keep me"
        )
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0001_initial_schema"
        )


def test_empty_alembic_version_is_stamped_for_existing_schema(tmp_path, monkeypatch):
    database_path = tmp_path / "empty-version.sqlite3"
    legacy_engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(legacy_engine)
    with legacy_engine.begin() as connection:
        connection.execute(
            WorkflowRecord.__table__.insert().values(
                id="wf_legacy",
                name="Keep me",
                data='{"nodes":[],"edges":[]}',
            )
        )
        connection.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)")
        )
    legacy_engine.dispose()
    monkeypatch.setenv("N3RF_DB_PATH", str(database_path))

    migrated_engine = get_engine()

    with migrated_engine.connect() as connection:
        assert connection.scalar(text("SELECT name FROM workflows WHERE id = 'wf_legacy'")) == (
            "Keep me"
        )
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == (
            "0001_initial_schema"
        )


def test_concurrent_first_access_initializes_database_once(tmp_path, monkeypatch):
    database_path = tmp_path / "concurrent.sqlite3"
    monkeypatch.setenv("N3RF_DB_PATH", str(database_path))

    with ThreadPoolExecutor(max_workers=8) as executor:
        engines = list(executor.map(lambda _: get_engine(), range(16)))

    assert all(engine is engines[0] for engine in engines)
    assert set(inspect(engines[0]).get_table_names()) == {
        "alembic_version",
        "model_profiles",
        "runs",
        "workflows",
    }


def test_incomplete_legacy_database_fails_with_actionable_error(tmp_path, monkeypatch):
    database_path = tmp_path / "incomplete.sqlite3"
    legacy_engine = create_engine(f"sqlite:///{database_path}")
    with legacy_engine.begin() as connection:
        connection.execute(text("CREATE TABLE workflows (id TEXT PRIMARY KEY)"))
    legacy_engine.dispose()
    monkeypatch.setenv("N3RF_DB_PATH", str(database_path))

    try:
        get_engine()
    except RuntimeError as error:
        assert "incomplete n3rf schema" in str(error)
    else:
        raise AssertionError("An incomplete legacy database should not be stamped.")
