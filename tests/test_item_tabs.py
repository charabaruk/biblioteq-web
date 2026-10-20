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
