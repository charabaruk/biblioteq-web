"""Item detail sections and tabs (ADR-0006, ADR-0007)."""

import pytest

FETCH = {"X-Requested-With": "fetch"}


def _flat(html: str) -> str:
    return " ".join(html.split())


def test_description_is_a_text_section_above_the_fields(client):
    html = client.get("/item/book/1").text
    assert "<h3>Description</h3>" in html
    assert "<dt>Description</dt>" not in html
    assert html.index("A comic") < html.index("<dl>") < html.index("Douglas Adams")


def test_text_section_is_escaped(client):
    html = client.get("/item/book/1").text
    assert "&lt;i&gt;space&lt;/i&gt;" in html
    assert "<i>space</i>" not in html


def test_empty_text_section_is_omitted(client):
    html = client.get("/item/book/2").text
    assert "Description" not in html
    assert 'class="prose"' not in html


def test_na_placeholder_is_treated_as_empty(client):
    html = client.get("/item/book/3").text
    assert "Description" not in html
    assert "Edition" not in html
    assert ">N/A<" not in html
    assert "N/A Station" in html


def test_single_tab_shows_no_tab_list(client):
    html = client.get("/item/book/2").text
    assert "tab-title" not in html
    assert "data-tabs" not in html
    assert "tabs.js" not in html


def test_book_fields_are_split_across_main_and_details(client):
    html = client.get("/item/book/1").text
    assert 'href="#tab-main"' in html
    assert 'href="#tab-details"' in html
    main, details = html.split('id="tab-details"')
    assert "Douglas Adams" in main
    assert "Keywords" not in main
    assert "<dt>Keywords</dt><dd>comedy, towel</dd>" in details


def test_tab_without_content_for_the_item_is_omitted(client):
    html = client.get("/item/book/2").text
    assert 'id="tab-details"' not in html


def test_full_page_renders_main_and_placeholders_for_lazy_tabs(tabbed_client):
    r = tabbed_client.get("/item/book/1")
    assert r.status_code == 200
    assert "Douglas Adams" in r.text
    assert '<h2 class="tab-title">Notes</h2>' in r.text
    assert 'href="#tab-notes"' in r.text
    assert 'data-src="/item/book/1/notes"' in r.text
    assert "Show Notes" in r.text
    assert "Group 1" not in r.text
    assert "tabs.js" in r.text
    assert "vary" not in r.headers


def test_fragment_has_only_the_tab_body_in_order(tabbed_client):
    r = tabbed_client.get("/item/book/1/notes", headers=FETCH)
    assert r.status_code == 200
    assert "<html" not in r.text
    assert r.headers["vary"] == "X-Requested-With"
    assert r.text.index("Group 1") < r.text.index("One") < r.text.index("Two")
    assert r.text.index("Two") < r.text.index("Group 2") < r.text.index("Three")
    assert '<th scope="col">Note</th>' in r.text


def test_table_section_applies_row_limit(tabbed_client):
    html = tabbed_client.get("/item/book/1/notes", headers=FETCH).text
    assert "Three" in html
    assert "Four" not in html


def test_tab_route_without_header_is_a_full_page(tabbed_client):
    r = tabbed_client.get("/item/book/1/notes")
    assert r.status_code == 200
    assert "<html" in r.text
    assert "Group 1" in r.text
    assert "Show Notes" not in r.text
    assert r.headers["vary"] == "X-Requested-With"


def test_fragment_matches_tab_markup_in_full_page(tabbed_client):
    fragment = tabbed_client.get("/item/book/1/notes", headers=FETCH).text
    full = tabbed_client.get("/item/book/1/notes").text
    assert _flat(fragment) in _flat(full)


def test_item_without_rows_has_empty_table_tab(tabbed_client):
    r = tabbed_client.get("/item/book/2/notes", headers=FETCH)
    assert r.status_code == 200
    assert "<table" not in r.text


@pytest.mark.parametrize("headers", [{}, FETCH])
def test_unknown_tab_and_item_are_404(tabbed_client, headers):
    assert tabbed_client.get("/item/book/1/nope", headers=headers).status_code == 404
    assert tabbed_client.get("/item/book/9999/notes", headers=headers).status_code == 404
    assert tabbed_client.get("/item/nope/1/notes", headers=headers).status_code == 404
