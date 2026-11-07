"""Item page `<title>`, `<h1>` and `<h2>` (ADR-0012)."""


def test_periodical_page_title_h1_and_subtitle(client):
    html = client.get("/item/journal/2").text
    assert "<title>Visible Journal Values 42 (vol. 2025 no. 3) - " in html
    assert "<h1>Visible Journal Values 42</h1>" in html
    assert '<h2 class="subtitle">March 2024 (vol. 2025 no. 3)</h2>' in html


def test_periodical_with_only_sentinels_has_plain_titles_and_no_subtitle(client):
    html = client.get("/item/magazine/1").text
    assert "<title>Hidden Magazine Values - " in html
    assert "<h1>Hidden Magazine Values</h1>" in html
    assert 'class="subtitle"' not in html


def test_book_with_series_and_volume_has_a_subtitle(client):
    html = client.get("/item/book/2").text
    assert "<title>Dune - " in html
    assert "<h1>Dune</h1>" in html
    assert '<h2 class="subtitle">Dune Chronicles volume 1</h2>' in html


def test_book_with_series_only_shows_the_series(client):
    html = client.get("/item/book/1").text
    assert '<h2 class="subtitle">Hitchhiker Series</h2>' in html


def test_book_without_series_has_no_subtitle(client):
    assert 'class="subtitle"' not in client.get("/item/book/3").text


def test_repeated_issue_number_is_shown_once(client):
    html = client.get("/item/journal/3").text
    assert "<title>Repeated Journal Number 7 - " in html
    assert "<h1>Repeated Journal Number 7</h1>" in html
    assert "<dt>Issue Number</dt><dd>7</dd>" in html
    assert "<dt>Volume</dt>" not in html
    assert "<dt>Issue</dt>" not in html


def test_issue_without_display_number_becomes_the_display_number(client):
    html = client.get("/item/journal/4").text
    assert "<h1>Issue Only Journal Number 8</h1>" in html
    assert "<dt>Issue Number</dt><dd>8</dd>" in html
    assert "<dt>Issue</dt>" not in html


def test_cards_use_the_normalised_numbers(client):
    html = client.get("/browse/journal").text
    assert "Issue 7" in html and "Issue 8" in html
    assert "Vol. 0" not in html
