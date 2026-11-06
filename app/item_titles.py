"""Page title, display title and subtitle of an item page (ADR-0012)."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from babel import UnknownLocaleError
from babel.dates import format_skeleton

from app.item_types import ItemType

EMPTY_DISPLAY_NUMBER = "-1"
EMPTY_COUNTER = "0"
PUBLICATION_DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d")  # BiblioteQ writes the first
MONTH_AND_YEAR_SKELETON = "yMMMM"
FALLBACK_LANGUAGE = "en"


@dataclass(frozen=True)
class TitleValues:
    """Raw column values the titles are built from; absent or empty values are None or sentinels."""

    display_number: str | None = None
    volume: str | None = None
    issue: str | None = None
    published: str | None = None
    series_title: str | None = None
    volume_number: str | None = None


@dataclass(frozen=True)
class ItemTexts:
    """The `<title>`, `<h1>` and optional `<h2>` texts; the title excludes the site name."""

    page_title: str
    display_title: str
    subtitle: str | None = None


def _clean(value: str | None, empty: str | None = None) -> str | None:
    """The stripped value, or None when blank or equal to the type's empty sentinel."""
    stripped = (value or "").strip()
    return None if not stripped or stripped == empty else stripped


def _volume_and_issue(
    gettext: Callable[[str], str], volume: str | None, issue: str | None
) -> str | None:
    if volume and issue:
        return gettext("vol. %(volume)s no. %(issue)s") % {"volume": volume, "issue": issue}
    if issue:
        return gettext("no. %(issue)s") % {"issue": issue}
    if volume:
        return gettext("vol. %(volume)s") % {"volume": volume}
    return None


def _month_and_year(published: str | None, language: str) -> str | None:
    """The date as month and year in the language; unparsable text is returned as written."""
    if published is None:
        return None
    for date_format in PUBLICATION_DATE_FORMATS:
        try:
            parsed = datetime.strptime(published, date_format)
        except ValueError:
            continue
        locale = language.replace("-", "_")
        try:
            return format_skeleton(MONTH_AND_YEAR_SKELETON, parsed, locale=locale)
        except (UnknownLocaleError, ValueError):
            return format_skeleton(MONTH_AND_YEAR_SKELETON, parsed, locale=FALLBACK_LANGUAGE)
    return published


def _periodical_texts(
    title: str, values: TitleValues, gettext: Callable[[str], str], language: str
) -> ItemTexts:
    number = _clean(values.display_number, EMPTY_DISPLAY_NUMBER)
    volume = _clean(values.volume, EMPTY_COUNTER)
    issue = _clean(values.issue, EMPTY_COUNTER)
    counters = _volume_and_issue(gettext, volume, issue)

    # With a display number, volume and issue follow in parentheses; without, they trail the title.
    if number:
        page_title = f"{title} {number}" + (f" ({counters})" if counters else "")
        display_title = f"{title} {number}"
    elif issue:
        page_title = display_title = f"{title} {counters}"
    else:
        page_title = display_title = title

    # The subtitle repeats the volume and issue unless the display title already shows them.
    shown_in_display_title = not number and issue is not None
    parts = [
        _month_and_year(_clean(values.published), language),
        None if shown_in_display_title or not counters else f"({counters})",
    ]
    subtitle = " ".join(part for part in parts if part) or None
    return ItemTexts(page_title, display_title, subtitle)


def build_item_texts(
    spec: ItemType,
    title: str,
    values: TitleValues,
    gettext: Callable[[str], str],
    language: str,
) -> ItemTexts:
    """Titles for an item; types without a rule keep the item title and have no subtitle."""
    if spec.issue:
        return _periodical_texts(title, values, gettext, language)

    if spec.series:
        series = _clean(values.series_title)
        volume = _clean(values.volume_number)
        if series and volume:
            subtitle = gettext("%(series)s volume %(volume)s") % {
                "series": series,
                "volume": volume,
            }
            return ItemTexts(title, title, subtitle)
        return ItemTexts(title, title, series)

    return ItemTexts(title, title)
