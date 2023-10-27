"""``pytest`` configuration."""

import os

import psycopg
import pytest
import pytest_pgsql
from pypgstac.db import PgstacDB
from pypgstac.load import Loader
from pypgstac.migrate import Migrate
from starlette.testclient import TestClient

DATA_DIR = os.path.join(os.path.dirname(__file__), "fixtures")
collection = os.path.join(DATA_DIR, "noaa-emergency-response.json")
items = os.path.join(DATA_DIR, "noaa-eri-nashville2020.json")

test_db = pytest_pgsql.TransactedPostgreSQLTestDB.create_fixture(
    "test_db", scope="session", use_restore_state=False
)


@pytest.fixture(scope="session")
def database_url(test_db):
    """
    Session scoped fixture to launch a postgresql database in a separate process.  We use psycopg2 to ingest test data
    because pytest-asyncio event loop is a function scoped fixture and cannot be called within the current scope.  Yields
    a database url which we pass to our application through a monkeypatched environment variable.
    """
    with PgstacDB(dsn=str(test_db.connection.engine.url)) as db:
        print("Running to PgSTAC migration...")
        migrator = Migrate(db)
        version = migrator.run_migration()
        assert version
        assert test_db.has_schema("pgstac")
        print(f"PgSTAC version: {version}")

        print("Load items and collection into PgSTAC")
        loader = Loader(db=db)
        loader.load_collections(collection)
        loader.load_items(items)

    # Make sure we have 1 collection and 163 items in pgstac
    with psycopg.connect(str(test_db.connection.engine.url)) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM pgstac.collections")
            val = cur.fetchone()[0]
            assert val == 2

            cur.execute("SELECT COUNT(*) FROM pgstac.items")
            val = cur.fetchone()[0]
            assert val == 40

            # Add CONTEXT=ON
            pgstac_settings = """
            INSERT INTO pgstac.pgstac_settings (name, value)
            VALUES ('context', 'on')
            ON CONFLICT ON CONSTRAINT pgstac_settings_pkey DO UPDATE SET value = excluded.value;"""
            cur.execute(pgstac_settings)

    return test_db.connection.engine.url


@pytest.fixture(autouse=True)
def app(database_url, monkeypatch):
    """Create app with connection to the pytest database."""
    monkeypatch.setenv("TIPG_PGSTAC_CACHE_DISABLE", "TRUE")

    monkeypatch.setenv("DATABASE_URL", str(database_url))

    from tipgstac.main import app

    # Remove middlewares https://github.com/encode/starlette/issues/472
    app.user_middleware = []
    app.middleware_stack = app.build_middleware_stack()

    with TestClient(app) as app:
        yield app
