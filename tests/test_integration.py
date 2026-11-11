"""Integration tests run against SQLite and PostgreSQL (see conftest.py)."""

from urllib.parse import quote

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError


def test_home_lists_recent(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Dune" in r.text


def test_periodical_cards_show_issue(client):
    r = client.get("/browse/journal")
    assert "Issue 42" in r.text
    assert "Issue 42 (vol. 2025 no. 3)" in r.text
    assert "Issue 42 (vol. 2025 no. 3)" in client.get("/browse/magazine").text
    assert "Issue -1" not in r.text
    assert "Vol. 0" not in r.text
    assert "Issue " not in client.get("/browse/book").text


def test_periodical_series_groups_and_orders_issues(configured):
    from app import repository
    from app.db import get_engine

    with get_engine().connect() as conn:
        catalog = repository.load_catalog(conn, "public")
        for type_key, series_id, title, issue_ids in (
            ("journal", "ISSN-JOURNAL", "Series Journal", [6, 5]),
            ("magazine", "ISSN-MAGAZINE", "Series Magazine", [4, 3]),
        ):
            series = repository.get_series(conn, catalog, catalog.types[type_key], series_id, 1, 10)
            assert series is not None
            assert series.title == title
            assert [item["id"] for item in series.items.items] == issue_ids
            assert (
                repository.get_series(conn, catalog, catalog.types[type_key], "missing", 1, 10)
                is None
            )


def test_periodical_series_page_renders_issue_cover(client):
    response = client.get("/series/journal/ISSN-JOURNAL")
    assert response.status_code == 200
    assert 'src="/cover/journal/5"' in response.text


def test_periodical_series_page_paginates_in_issue_order(client, monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_PAGE_SIZE", "1")
    from app import config

    config.get_settings.cache_clear()
    try:
        first = client.get("/series/journal/ISSN-JOURNAL")
        assert "Page 1 of 2" in first.text
        assert 'data-id="6"' in first.text
        assert "/series/journal/ISSN-JOURNAL?sort=asc&amp;page=2" in first.text

        second = client.get("/series/journal/ISSN-JOURNAL", params={"page": 2})
        assert "Page 2 of 2" in second.text
        assert 'data-id="5"' in second.text

        newest = client.get("/series/journal/ISSN-JOURNAL", params={"sort": "desc"})
        assert 'data-id="5"' in newest.text
    finally:
        config.get_settings.cache_clear()


def test_periodical_issn_links_to_series(client):
    for type_key, item_id, series_id in (
        ("journal", 5, "ISSN-JOURNAL"),
        ("magazine", 3, "ISSN-MAGAZINE"),
    ):
        response = client.get(f"/item/{type_key}/{item_id}")
        assert response.status_code == 200
        assert f'href="/series/{type_key}/{series_id}"' in response.text


@pytest.fixture(params=["journal", "magazine"])
def title_series_type(client, db_url, request):
    type_key = request.param
    engine = create_engine(db_url)
    rows = [
        {"oid": 9001, "title": "Shared / Title & More", "identifier": None, "issue": 1},
        {"oid": 9002, "title": "Shared / Title & More", "identifier": "ISSN-X", "issue": 2},
        {"oid": 9003, "title": "Shared / Title & More", "identifier": None, "issue": 3},
        {"oid": 9004, "title": "One Identifier", "identifier": "ISSN/ONE", "issue": 1},
        {"oid": 9005, "title": "One Identifier", "identifier": "ISSN/ONE", "issue": 2},
        {"oid": 9006, "title": "Many Identifiers", "identifier": "ISSN-A", "issue": 1},
        {"oid": 9007, "title": "Many Identifiers", "identifier": "ISSN-B", "issue": 2},
        {"oid": 9008, "title": "Many Identifiers", "identifier": "ISSN-A", "issue": 3},
        {"oid": 9009, "title": "Empty Identifier", "identifier": "", "issue": 1},
        {"oid": 9010, "title": "shared / title & more", "identifier": None, "issue": 1},
        {"oid": 9011, "title": "<Title ' & % / é ? #>", "identifier": None, "issue": 1},
        {"oid": 9012, "title": "", "identifier": None, "issue": 1},
        {"oid": 9013, "title": "Mixed Empty", "identifier": "", "issue": 1},
        {"oid": 9014, "title": "Mixed Empty", "identifier": "ISSN-C", "issue": 2},
        {"oid": 9015, "title": "Other", "identifier": "by-title/Shared / Title & More", "issue": 1},
        {"oid": 9016, "title": "/Leading", "identifier": None, "issue": 1},
        {"oid": 9017, "title": "Trailing/", "identifier": None, "issue": 1},
        {"oid": 9018, "title": "/", "identifier": None, "issue": 1},
    ]
    with engine.begin() as conn:
        conn.execute(
            text(
                f"INSERT INTO {type_key} (myoid, title, id, display_number) "
                "VALUES (:oid, :title, :identifier, :issue)"
            ),
            rows,
        )
    yield type_key
    with engine.begin() as conn:
        conn.execute(
            text(f"DELETE FROM {type_key} WHERE myoid BETWEEN :first AND :last"),
            {"first": 9001, "last": 9018},
        )
    engine.dispose()


def test_title_series_uses_reserved_path(client, title_series_type):
    response = client.get(f"/series/{title_series_type}/by-title/Shared%20%2F%20Title%20%26%20More")
    assert response.status_code == 200
    assert 'data-id="9001"' in response.text
    assert 'data-id="9002"' not in response.text
    assert 'data-id="9015"' not in response.text


def _title_series_path(type_key, title):
    return f"/series/{type_key}/by-title/{quote(title, safe='')}"


def test_title_series_shows_only_null_identifiers(client, title_series_type, monkeypatch):
    from app import config

    monkeypatch.setenv("BIBLIOTEQ_PAGE_SIZE", "1")
    config.get_settings.cache_clear()
    try:
        url = _title_series_path(title_series_type, "Shared / Title & More")
        response = client.get(url)
        assert response.status_code == 200
        assert "Page 1 of 2" in response.text
        assert 'data-id="9001"' in response.text
        assert 'data-id="9002"' not in response.text
        second = client.get(url, params={"page": 2})
        assert 'data-id="9003"' in second.text
        assert 'data-id="9010"' not in second.text
        assert f'action="{url}"' in response.text
        assert f"{url}?sort=asc&amp;page=2" in response.text
        assert 'name="title"' not in response.text
        newest = client.get(url, params={"sort": "desc"})
        assert 'data-id="9003"' in newest.text
        item = client.get(f"/item/{title_series_type}/9001")
        assert url in item.text
        assert "/by-title/" not in client.get(f"/item/{title_series_type}/9002").text
    finally:
        config.get_settings.cache_clear()


@pytest.mark.parametrize(
    "title,identifier", [("One Identifier", "ISSN%2FONE"), ("Empty Identifier", "")]
)
def test_title_series_redirects_single_identifier(client, title_series_type, title, identifier):
    response = client.get(_title_series_path(title_series_type, title), follow_redirects=False)
    assert response.status_code in (302, 303, 307, 308)
    assert response.headers["location"].startswith(f"/series/{title_series_type}/{identifier}")
    assert client.get(response.headers["location"]).status_code == 200


def test_title_series_offers_each_distinct_identifier(client, title_series_type):
    response = client.get(_title_series_path(title_series_type, "Many Identifiers"))
    assert response.status_code == 200
    assert response.text.count(f'href="/series/{title_series_type}/ISSN-A"') == 1
    assert response.text.count(f'href="/series/{title_series_type}/ISSN-B"') == 1
    assert "Many Identifiers" in response.text
    assert client.get(f"/series/{title_series_type}/ISSN-A").status_code == 200
    empty = client.get(_title_series_path(title_series_type, "Mixed Empty"))
    assert f'href="/series/{title_series_type}/"' in empty.text
    assert "(empty)" in empty.text


def test_title_series_rejects_missing_matches_and_other_types(client, title_series_type):
    response = client.get(_title_series_path(title_series_type, "missing"))
    assert response.status_code == 404
    assert client.get("/series/book/by-title/Dune").status_code == 404


@pytest.mark.parametrize(
    "title,item_id",
    [
        ("<Title ' & % / é ? #>", 9011),
        ("", 9012),
        ("/Leading", 9016),
        ("Trailing/", 9017),
        ("/", 9018),
    ],
)
def test_title_series_preserves_raw_titles(client, title_series_type, title, item_id):
    from html import unescape

    url = _title_series_path(title_series_type, title)
    item = client.get(f"/item/{title_series_type}/{item_id}")
    assert url in unescape(item.text)
    response = client.get(url)
    assert response.status_code == 200
    assert f'data-id="{item_id}"' in response.text
    assert "<Title ' & % / é ? #>" not in response.text


def test_title_series_respects_root_path(client, title_series_type):
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app, root_path="/library") as mounted:
        response = mounted.get(
            "/library" + _title_series_path(title_series_type, "One Identifier"),
            params={"sort": "desc", "page": 2},
            follow_redirects=False,
        )
        assert response.headers["location"] == (
            f"/library/series/{title_series_type}/ISSN%2FONE?sort=desc&page=2"
        )
        item = mounted.get(f"/library/item/{title_series_type}/9001")
        title_url = "/library" + _title_series_path(title_series_type, "Shared / Title & More")
        assert title_url in item.text
        page = mounted.get(title_url)
        assert f'action="{title_url}"' in page.text


def test_title_series_requires_identifier_column(configured, title_series_type):
    from dataclasses import replace

    from app import repository
    from app.db import get_engine

    with get_engine().connect() as conn:
        catalog = repository.load_catalog(conn, "public")
        spec = replace(catalog.types[title_series_type], identifier=None)
        result = repository.get_series_by_title(conn, catalog, spec, "Shared / Title & More", 1, 10)
        assert result is None
        assert repository.get_item(conn, catalog, spec, 9001).series_url is None


def test_search_matches_title_and_author(client):
    assert "Dune" in client.get("/search", params={"q": "dune"}).text
    assert "Frank Herbert" in client.get("/search", params={"q": "herbert"}).text


def test_search_without_query_shows_heading_and_skips_search(client, monkeypatch):
    from app import repository

    def unexpected_search(*args, **kwargs):
        raise AssertionError("search should not run when q is absent")

    monkeypatch.setattr(repository, "search", unexpected_search)
    response = client.get("/search")

    assert response.status_code == 200
    assert "<h1>Search the collection</h1>" in response.text
    assert response.text.index("<h1>") < response.text.index('class="search-form')
    assert 'class="count"' not in response.text


def test_search_with_explicit_empty_query_runs_search(client, monkeypatch):
    from app import repository

    queries = []
    original_search = repository.search

    def recording_search(*args, **kwargs):
        queries.append(args[2])
        return original_search(*args, **kwargs)

    monkeypatch.setattr(repository, "search", recording_search)
    response = client.get("/search?q=")

    assert response.status_code == 200
    assert queries == [""]
    assert 'class="count"' in response.text


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


def test_periodical_browse_offers_and_preserves_issue_order(client, monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_PAGE_SIZE", "1")
    from app import config

    config.get_settings.cache_clear()
    try:
        default = client.get("/browse/journal")
        assert '<option value="asc" selected>' in default.text
        assert "/browse/journal?sort=asc&amp;page=2" in default.text

        descending = client.get("/browse/journal", params={"sort": "desc", "location": "UNKNOWN"})
        assert '<option value="desc" selected>' in descending.text
        assert '<input type="hidden" name="location" value="UNKNOWN">' in descending.text

        all_descending = client.get("/browse/journal", params={"sort": "desc"})
        assert "/browse/journal?sort=desc&amp;page=2" in all_descending.text
        assert 'name="sort"' not in client.get("/browse/book").text
        assert client.get("/browse/journal", params={"sort": "sideways"}).status_code == 422
        french = client.get("/browse/journal", headers={"accept-language": "fr"})
        assert "Ordre des numéros" in french.text
    finally:
        config.get_settings.cache_clear()


def test_periodical_browse_passes_direction_to_repository(client, monkeypatch):
    from app import repository

    directions = []
    original_search = repository.search

    def recording_search(*args, **kwargs):
        directions.append(kwargs.get("issue_direction"))
        return original_search(*args, **kwargs)

    monkeypatch.setattr(repository, "search", recording_search)
    response = client.get("/browse/journal", params={"sort": "desc"})
    assert response.status_code == 200
    assert directions == ["desc"]


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


def test_browse_filters_by_exact_location(client):
    r = client.get("/browse/book", params={"location": "Orphan Room"})
    assert "Dune" in r.text and "Hitchhiker" not in r.text
    assert "Location: Orphan Room" in r.text and "Clear filter" in r.text
    assert "1 item" in r.text
    assert "0 items" in client.get("/browse/book", params={"location": "shelf A"}).text


def test_browse_unknown_location_includes_items_without_one(client):
    r = client.get("/browse/book", params={"location": "UNKNOWN"})
    assert "Wild_Cards" in r.text and "Dune" not in r.text
    assert "Unknown location" in r.text


def test_search_filters_by_location_and_terms(client):
    r = client.get("/search", params={"q": "", "location": "Shelf A"})
    assert "Hitchhiker" in r.text and "Hidden Journal Values" in r.text
    assert "Dune" not in r.text
    assert "0 results" in client.get("/search", params={"q": "dune", "location": "Shelf A"}).text
    r = client.get("/search", params={"q": "", "location": "UNKNOWN", "type": "journal"})
    assert "Visible Journal Values" in r.text and "Hidden Journal Values" not in r.text


def test_search_form_offers_registered_locations(client):
    r = client.get("/search")
    for name in ("Shelf A", "shelf a", "Reading Room", "Ghost/Annex"):
        assert f'<option value="{name}"' in r.text
    assert '<option value="UNKNOWN"' in r.text
    assert "Orphan Room" not in r.text


def test_search_form_keeps_an_unlisted_location_selected(client):
    r = client.get("/search", params={"location": "Orphan Room"})
    assert '<option value="Orphan Room" selected>' in r.text


def test_location_filter_survives_pagination(client, monkeypatch):
    monkeypatch.setenv("BIBLIOTEQ_PAGE_SIZE", "1")
    from app import config

    config.get_settings.cache_clear()
    try:
        r = client.get("/search", params={"q": "", "location": "UNKNOWN"})
        assert "location=UNKNOWN&amp;page=2" in r.text
        r = client.get("/browse/magazine", params={"location": "UNKNOWN"})
        assert "/browse/magazine?sort=asc&amp;location=UNKNOWN&amp;page=2" in r.text
    finally:
        config.get_settings.cache_clear()


def test_item_links_a_registered_location_to_its_page(client):
    html = client.get("/item/book/1").text
    assert '<dt>Location</dt><dd><a href="/location/Shelf%20A">Shelf A</a></dd>' in html


def test_item_links_an_unregistered_location_to_the_browse_filter(client):
    html = client.get("/item/book/2").text
    assert '<a href="/browse/book?location=Orphan+Room">Orphan Room</a>' in html


def test_item_hides_a_missing_or_unknown_location(client):
    assert "Location" not in client.get("/item/book/3").text
    assert "Location" not in client.get("/item/journal/2").text
