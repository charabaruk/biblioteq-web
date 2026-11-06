"""Page title, display title and subtitle per item type (ADR-0012)."""

import pytest

from app.item_titles import TitleValues, build_item_texts
from app.item_types import ITEM_TYPES

SPECS = {spec.key: spec for spec in ITEM_TYPES}
TITLE = "Wired"


def _texts(key, language="en", **values):
    return build_item_texts(SPECS[key], TITLE, TitleValues(**values), str, language)


@pytest.mark.parametrize(
    ("values", "page_title", "display_title"),
    [
        (
            {"display_number": "42", "volume": "3", "issue": "4"},
            "Wired 42 (vol. 3 no. 4)",
            "Wired 42",
        ),
        ({"display_number": "42", "issue": "4"}, "Wired 42 (no. 4)", "Wired 42"),
        ({"display_number": "42", "volume": "3"}, "Wired 42 (vol. 3)", "Wired 42"),
        ({"display_number": "42"}, "Wired 42", "Wired 42"),
        ({"volume": "3", "issue": "4"}, "Wired vol. 3 no. 4", "Wired vol. 3 no. 4"),
        ({"issue": "4"}, "Wired no. 4", "Wired no. 4"),
        ({"volume": "3"}, "Wired", "Wired"),
        ({}, "Wired", "Wired"),
    ],
)
@pytest.mark.parametrize("key", ["magazine", "journal"])
def test_periodical_page_and_display_titles(key, values, page_title, display_title):
    texts = _texts(key, **values)
    assert texts.page_title == page_title
    assert texts.display_title == display_title


@pytest.mark.parametrize("key", ["magazine", "journal"])
def test_periodical_empty_sentinels_are_ignored(key):
    texts = _texts(key, display_number="-1", volume="0", issue="0")
    assert (texts.page_title, texts.display_title, texts.subtitle) == (TITLE, TITLE, None)


def test_subtitle_repeats_volume_and_issue_when_display_title_shows_the_display_number():
    texts = _texts("magazine", display_number="42", volume="3", issue="4", published="03/15/2024")
    assert texts.subtitle == "March 2024 (vol. 3 no. 4)"


def test_subtitle_leaves_out_volume_and_issue_the_display_title_already_shows():
    texts = _texts("magazine", volume="3", issue="4", published="03/15/2024")
    assert texts.subtitle == "March 2024"


def test_subtitle_without_a_date_shows_only_volume_and_issue():
    texts = _texts("journal", display_number="42", issue="4")
    assert texts.subtitle == "(no. 4)"


def test_subtitle_is_unset_without_a_date_or_volume_and_issue():
    assert _texts("journal", display_number="42").subtitle is None


@pytest.mark.parametrize(
    ("published", "expected"),
    [
        ("03/15/2024", "March 2024"),
        ("2024-03-15", "March 2024"),
        ("Spring 2024", "Spring 2024"),
        ("  ", None),
        (None, None),
    ],
)
def test_publication_date_formats(published, expected):
    assert _texts("magazine", published=published).subtitle == expected


def test_month_and_year_are_formatted_for_the_language():
    assert _texts("magazine", language="fr", published="03/15/2024").subtitle == "mars 2024"


def test_unknown_language_falls_back_to_english():
    assert _texts("magazine", language="xx", published="03/15/2024").subtitle == "March 2024"


@pytest.mark.parametrize(
    ("values", "subtitle"),
    [
        ({"series_title": "Dune Chronicles", "volume_number": "1"}, "Dune Chronicles volume 1"),
        ({"series_title": "Dune Chronicles"}, "Dune Chronicles"),
        ({"volume_number": "1"}, None),
        ({}, None),
    ],
)
def test_book_subtitle_comes_from_the_series(values, subtitle):
    texts = _texts("book", **values)
    assert texts.subtitle == subtitle
    assert (texts.page_title, texts.display_title) == (TITLE, TITLE)


def test_other_types_keep_the_item_title():
    texts = _texts("dvd", display_number="42", series_title="Ignored")
    assert (texts.page_title, texts.display_title, texts.subtitle) == (TITLE, TITLE, None)
