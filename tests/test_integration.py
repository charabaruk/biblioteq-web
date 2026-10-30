"""Integration tests run against SQLite and PostgreSQL (see conftest.py)."""

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


def test_home_lists_recent(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Dune" in r.text


def test_search_matches_title_and_author(client):
    assert "Dune" in client.get("/search", params={"q": "dune"}).text
    assert "Frank Herbert" in client.get("/search", params={"q": "herbert"}).text


def test_search_multiple_terms_are_anded(client):
    r = client.get("/search", params={"q": "dune adams"})
    assert "0 results" in r.text


def test_search_by_isbn(client):
    assert "Dune" in client.get("/search", params={"q": "9780441172719"}).text


def test_search_escapes_like_wildcards(client):
    r = client.get("/search", params={"q": "100%"})
    assert "1 result" in r.text
    assert "0 results" in client.get("/search", params={"q": "%%%zzz"}).text


def test_search_injection_attempt_is_inert(client):
    r = client.get("/search", params={"q": "'; DROP TABLE book; --"})
    assert r.status_code == 200
    assert "Dune" in client.get("/search", params={"q": "dune"}).text


def test_unknown_type_in_search_is_ignored(client):
    assert client.get("/search", params={"q": "dune", "type": "nope"}).status_code == 200


def test_browse_and_pagination(client, monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_PAGE_SIZE", "1")
    from app import config

    config.get_settings.cache_clear()
    try:
        r = client.get("/browse/book")
        assert "Page 1 of 3" in r.text
        assert "/browse/book?page=2" in r.text
        assert client.get("/browse/book", params={"page": 99}).status_code == 200
    finally:
        config.get_settings.cache_clear()


def test_browse_unknown_type_404(client):
    assert client.get("/browse/nope").status_code == 404


def test_item_detail_and_availability(client):
    r = client.get("/item/book/1")
    assert r.status_code == 200
    assert "Douglas Adams" in r.text
    assert "Available: 1 of 2" in r.text
    assert "SECRET-MARC" not in r.text
    assert "M1" not in r.text


def test_item_all_checked_out(client):
    assert "checked out" in client.get("/item/book/2").text


def test_item_not_found(client):
    assert client.get("/item/book/9999").status_code == 404
    assert client.get("/item/nope/1").status_code == 404
    assert client.get("/item/book/abc").status_code == 422


def test_cover_served_with_caching(client):
    r = client.get("/cover/book/1")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    cached = client.get("/cover/book/1", headers={"If-None-Match": r.headers["etag"]})
    assert cached.status_code == 304


def test_cover_missing_404(client):
    assert client.get("/cover/book/2").status_code == 404
    assert client.get("/cover/book/1", params={"side": "back"}).status_code == 404


def test_health(client):
    assert client.get("/healthz").json() == {"status": "ok"}
    assert client.get("/readyz").json() == {"status": "ready"}


def test_connection_is_read_only(configured):
    from app.db import get_engine

    with get_engine().connect() as conn:
        try:
            conn.execute(text("DELETE FROM book"))
            raise AssertionError("write unexpectedly succeeded")
        except DBAPIError:
            pass


def test_location_page_lists_items_of_registered_types(client):
    r = client.get("/location/Shelf A")
    assert r.status_code == 200
    assert "Location: Shelf A" in r.text
    assert "Hitchhiker" in r.text and "Hidden Journal Values" in r.text
    assert "Dune" not in r.text and "Visible Journal Values" not in r.text
    assert "/browse/book?location=Shelf%20A" in r.text


def test_location_names_are_exact(client):
    off = {"follow_redirects": False}
    assert client.get("/location/SHELF A", **off).status_code == 307
    assert client.get("/location/Shelf A ", **off).status_code == 307
    r = client.get("/location/shelf a", **off)
    assert r.status_code == 200 and "No items at this location." in r.text


def test_unregistered_location_redirects_to_the_landing_page(client):
    for name in ("Orphan Room", "Nowhere", ""):
        r = client.get(f"/location/{name}", follow_redirects=False)
        assert (r.status_code, r.headers["location"]) == (307, "/")


def test_registered_location_without_items_shows_an_empty_page(client):
    r = client.get("/location/Reading Room")
    assert r.status_code == 200 and "No items at this location." in r.text


def test_location_names_may_contain_slashes(client):
    assert "Location: Ghost/Annex" in client.get("/location/Ghost/Annex").text


def test_unknown_location_page_lists_items_without_a_location(client):
    r = client.get("/location/UNKNOWN")
    assert r.status_code == 200 and "Unknown location" in r.text
    assert "Wild_Cards" in r.text and "Visible Journal Values" in r.text
    assert "Hidden Magazine Values" in r.text
    assert "Hitchhiker" not in r.text and "Dune" not in r.text
    assert "/browse/journal?location=UNKNOWN" in r.text
