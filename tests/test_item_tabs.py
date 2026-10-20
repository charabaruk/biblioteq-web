"""Item detail sections and tabs (ADR-0006, ADR-0007)."""


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


def test_single_tab_shows_no_tab_heading(client):
    assert "tab-title" not in client.get("/item/book/1").text


def test_every_tab_is_rendered_with_a_heading(tabbed_client):
    html = tabbed_client.get("/item/book/1").text
    assert '<h2 class="tab-title">Main</h2>' in html
    assert '<h2 class="tab-title">Notes</h2>' in html
    assert "Douglas Adams" in html


def test_table_section_groups_and_orders_rows(tabbed_client):
    html = tabbed_client.get("/item/book/1").text
    assert html.index("Group 1") < html.index("One") < html.index("Two")
    assert html.index("Two") < html.index("Group 2") < html.index("Three")
    assert '<th scope="col">Note</th>' in html


def test_table_section_applies_row_limit(tabbed_client):
    html = tabbed_client.get("/item/book/1").text
    assert "Three" in html
    assert "Four" not in html


def test_item_without_rows_omits_table_section(tabbed_client):
    html = tabbed_client.get("/item/book/2").text
    assert "<table" not in html
    assert "Group" not in html
