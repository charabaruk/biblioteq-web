"""Browser fixtures for accessibility tests. Opt in with `pytest -m a11y`; see docs/testing.md."""

import socket
import threading
import time

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")


def pytest_collection_modifyitems(items):
    for item in items:
        if "/tests/a11y/" in str(item.path).replace("\\", "/"):
            item.add_marker(pytest.mark.a11y)


@pytest.fixture(scope="session")
def live_url(tmp_path_factory, tabbed_types) -> str:
    """Serve the app on a local port over a SQLite fixture with a lazy second tab."""
    import sqlite3
    from pathlib import Path

    import uvicorn

    from app import config, db, deps, repository

    path = tmp_path_factory.mktemp("a11y") / "library.db"
    with sqlite3.connect(path) as conn:
        conn.executescript((Path(__file__).parent.parent / "schema_sqlite.sql").read_text())

    patch = pytest.MonkeyPatch()
    patch.setenv("BIBLIOTEQ_DB_URL", f"sqlite:///{path}")
    patch.setattr(repository, "ITEM_TYPES", tabbed_types)
    for cached in (config.get_settings, db.get_engine):
        cached.cache_clear()
    deps._catalog = None

    from app.main import app

    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", lifespan="on")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        if time.monotonic() > deadline:
            raise RuntimeError("test server did not start")
        time.sleep(0.05)

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=10)
    patch.undo()
    for cached in (config.get_settings, db.get_engine):
        cached.cache_clear()
    deps._catalog = None


@pytest.fixture(scope="session")
def browser():
    with playwright_sync.sync_playwright() as p:
        try:
            b = p.chromium.launch()
        except playwright_sync.Error as exc:
            pytest.skip(f"Chromium unavailable (run `playwright install chromium`): {exc}")
        yield b
        b.close()


@pytest.fixture
def page(browser):
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    p = context.new_page()
    yield p
    context.close()


@pytest.fixture
def nojs_page(browser):
    context = browser.new_context(java_script_enabled=False)
    p = context.new_page()
    yield p
    context.close()
