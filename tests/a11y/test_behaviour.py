"""Keyboard, focus and no-JS behaviour that axe cannot judge."""

import pytest

FOCUSABLE_STOPS = 12


def test_item_tabs_without_javascript_show_every_section(live_url, nojs_page):
    nojs_page.goto(live_url + "/item/book/1")
    assert nojs_page.locator("[role=tablist]").count() == 0
    assert nojs_page.locator("#tab-main").is_visible()
    assert nojs_page.locator("#tab-notes").is_visible()
    assert nojs_page.get_by_role("link", name="Show Notes").is_visible()


def test_lazy_tab_is_reachable_without_javascript(live_url, nojs_page):
    nojs_page.goto(live_url + "/item/book/1")
    nojs_page.get_by_role("link", name="Show Notes").click()
    assert nojs_page.url.endswith("/item/book/1/notes")
    assert nojs_page.locator("table").count() > 0


def test_search_works_without_javascript(live_url, nojs_page):
    nojs_page.goto(live_url + "/")
    nojs_page.get_by_role("searchbox").first.fill("dune")
    nojs_page.keyboard.press("Enter")
    nojs_page.wait_for_url("**/search?q=dune")
    assert nojs_page.get_by_text("Dune").first.is_visible()


def test_tabs_use_roving_tabindex(live_url, page):
    page.goto(live_url + "/item/book/1")
    tabs = page.get_by_role("tab")
    assert tabs.count() == 2
    assert [tabs.nth(i).get_attribute("tabindex") for i in range(2)] == ["0", "-1"]
    assert tabs.nth(0).get_attribute("aria-selected") == "true"
    assert page.locator("#tab-notes").is_hidden()


def test_arrow_keys_switch_tabs_and_move_focus(live_url, page):
    page.goto(live_url + "/item/book/1")
    first, second = page.get_by_role("tab").nth(0), page.get_by_role("tab").nth(1)
    first.focus()
    page.keyboard.press("ArrowRight")
    assert second.evaluate("el => el === document.activeElement")
    assert second.get_attribute("aria-selected") == "true"
    assert page.locator("#tab-notes").is_visible()
    assert page.locator("#tab-main").is_hidden()
    page.keyboard.press("ArrowRight")
    assert first.evaluate("el => el === document.activeElement")
    assert page.locator("#tab-main").is_visible()


def test_lazy_tab_content_loads_in_page(live_url, page):
    page.goto(live_url + "/item/book/1")
    history_before = page.evaluate("history.length")
    page.get_by_role("tab", name="Notes").click()
    page.wait_for_selector("#tab-notes .tab-body table")
    assert page.url.endswith("#tab=notes")
    assert page.evaluate("history.length") == history_before


def test_deep_link_selects_tab(live_url, page):
    page.goto(live_url + "/item/book/1#tab=notes")
    assert page.get_by_role("tab", name="Notes").get_attribute("aria-selected") == "true"
    page.wait_for_selector("#tab-notes .tab-body table")


@pytest.mark.parametrize("path", ["/", "/search?q=dune", "/browse/book", "/item/book/1"])
def test_keyboard_focus_is_always_visible(live_url, page, path):
    page.goto(live_url + path)
    for _ in range(FOCUSABLE_STOPS):
        page.keyboard.press("Tab")
        info = page.evaluate(
            """() => {
                const el = document.activeElement;
                if (!el || el === document.body) return null;
                const s = getComputedStyle(el);
                return {
                    tag: el.tagName,
                    outline: s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0,
                    shadow: s.boxShadow !== "none",
                };
            }"""
        )
        if info is None:
            break  # focus left the document (browser chrome); nothing more to check
        assert info["outline"] or info["shadow"], f"no visible focus indicator on {info['tag']}"


def test_page_reflows_at_320px(live_url, browser):
    context = browser.new_context(viewport={"width": 320, "height": 640})
    page = context.new_page()
    try:
        for path in ("/", "/search?q=dune", "/browse/book", "/item/book/1"):
            page.goto(live_url + path)
            overflow = page.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth"
            )
            assert overflow <= 0, f"{path} scrolls horizontally by {overflow}px"
    finally:
        context.close()
