"""Rendered-DOM WCAG 2.2 AA scan with axe-core, one case per template and state."""

import pytest

axe_mod = pytest.importorskip("axe_playwright_python.sync_playwright")

WCAG_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]

# Known gaps from ACCESSIBILITY.md; each entry is a defect to fix, not an exemption.
KNOWN_GAPS: dict[str, str] = {}

PAGES = {
    "home": "/",
    "search-empty-query": "/search",
    "search-results": "/search?q=dune",
    "search-no-results": "/search?q=zzzznothing",
    "browse": "/browse/book",
    "location": "/location/Shelf%20A",
    "location-unknown": "/location/UNKNOWN",
    "location-empty": "/location/Reading%20Room",
    "item": "/item/book/1",
    "item-no-description": "/item/book/2",
    "not-found-item": "/item/book/9999",
    "not-found-type": "/browse/nope",
}


def _violations(page) -> list[dict]:
    results = axe_mod.Axe().run(page, options={"runOnly": {"type": "tag", "values": WCAG_TAGS}})
    return [v for v in results.response["violations"] if v["id"] not in KNOWN_GAPS]


def _describe(violations: list[dict]) -> str:
    lines = []
    for v in violations:
        lines.append(f"{v['id']} ({v['impact']}): {v['help']}")
        lines.extend(f"    {n['target']}" for n in v["nodes"])
    return "\n".join(lines)


@pytest.mark.parametrize("name", PAGES)
def test_page_has_no_wcag_violations(live_url, page, name):
    page.goto(live_url + PAGES[name])
    found = _violations(page)
    assert not found, _describe(found)


def test_item_page_with_lazy_tab_loaded(live_url, page):
    page.goto(live_url + "/item/book/1")
    page.get_by_role("tab", name="Notes").click()
    page.wait_for_selector("#tab-notes .tab-body table")
    found = _violations(page)
    assert not found, _describe(found)
