"""Test fixtures. Integration tests run on SQLite always, and on PostgreSQL when
BIBLIOTEQ_TEST_DB_URL points at an empty, disposable database."""

import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

HERE = Path(__file__).parent
TEST_DB_URL = os.environ.get("BIBLIOTEQ_TEST_DB_URL")
os.environ.setdefault("BIBLIOTEQ_DB_URL", TEST_DB_URL or "sqlite:////nonexistent/library.db")


@pytest.fixture(scope="session", params=["sqlite", "postgresql"])
def db_url(request, tmp_path_factory) -> str:
    if request.param == "sqlite":
        path = tmp_path_factory.mktemp("sqlite") / "library.db"
        with sqlite3.connect(path) as conn:
            conn.executescript((HERE / "schema_sqlite.sql").read_text())
        return f"sqlite:///{path}"
    if not TEST_DB_URL:
        pytest.skip("BIBLIOTEQ_TEST_DB_URL not set")
    engine = create_engine(TEST_DB_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public"))
        conn.execute(text((HERE / "schema.sql").read_text()))
    engine.dispose()
    return TEST_DB_URL


@pytest.fixture
def configured(db_url, monkeypatch):
    """Point the app at the test database and reset cached state."""
    from app import config, db, deps

    monkeypatch.setenv("BIBLIOTEQ_DB_URL", db_url)
    for cached in (config.get_settings, db.get_engine):
        cached.cache_clear()
    deps._catalog = None
    yield
    for cached in (config.get_settings, db.get_engine):
        cached.cache_clear()


@pytest.fixture
def client(configured):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def tabbed_types():
    """Registry whose book type has a lazy second tab backed by the test-only book_note table."""
    from dataclasses import replace

    from app.item_types import (
        ITEM_TYPES,
        FieldsSection,
        TableSection,
        TabSpec,
        TextSection,
    )

    book = next(t for t in ITEM_TYPES if t.key == "book")
    notes = TableSection(
        label="Notes",
        table="book_note",
        fk="item_oid",
        columns=(("seq", "No."), ("note", "Note")),
        order_by=("grp", "seq"),
        group_by="grp",
        group_label="Group",
        limit=3,
    )
    tabbed = replace(
        book,
        tabs=(
            TabSpec(
                "main",
                "Main",
                (TextSection("description", "Description"), FieldsSection((("author", "Author"),))),
            ),
            TabSpec("notes", "Notes", (notes,), lazy=True),
        ),
    )
    return (tabbed,)


@pytest.fixture
def tabbed_client(configured, monkeypatch, tabbed_types):
    from fastapi.testclient import TestClient

    from app import repository
    from app.main import app

    monkeypatch.setattr(repository, "ITEM_TYPES", tabbed_types)
    with TestClient(app) as c:
        yield c
