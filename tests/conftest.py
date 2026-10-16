"""Test fixtures. Integration tests need BIBLIOTEQ_TEST_DB_URL (an empty, disposable database)."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

TEST_DB_URL = os.environ.get("BIBLIOTEQ_TEST_DB_URL")
os.environ.setdefault("BIBLIOTEQ_DB_URL", TEST_DB_URL or "postgresql+psycopg://x:x@localhost/x")


@pytest.fixture(scope="session")
def db_url() -> str:
    if not TEST_DB_URL:
        pytest.skip("BIBLIOTEQ_TEST_DB_URL not set")
    engine = create_engine(TEST_DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
        conn.execute(text((Path(__file__).parent / "schema.sql").read_text()))
    engine.dispose()
    return TEST_DB_URL


@pytest.fixture
def client(db_url):
    from fastapi.testclient import TestClient

    from app import deps
    from app.main import app

    deps._catalog = None
    with TestClient(app) as c:
        yield c
