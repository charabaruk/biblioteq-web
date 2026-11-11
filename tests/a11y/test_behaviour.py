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


def test_periodical_series_navigation_without_javascript(live_url, nojs_page):
    nojs_page.goto(live_url + "/item/journal/1")
    nojs_page.get_by_role("link", name="View series").click()
    assert nojs_page.url.endswith("/series/journal/by-title/Hidden%20Journal%20Values")
    assert nojs_page.get_by_role("heading", name="Hidden Journal Values").is_visible()

    nojs_page.goto(live_url + "/series/journal/by-title/Shared%20Journal")
    nojs_page.get_by_role("link", name="Shared Journal: ISSN ISSN-A").click()
    assert nojs_page.url.endswith("/series/journal/ISSN-A")


def test_periodical_series_sort_with_encoded_title(live_url, nojs_page):
    nojs_page.goto(live_url + "/item/journal/9006")
    nojs_page.get_by_role("link", name="View series").click()
    assert nojs_page.get_by_role("heading", name="Science / News & Notes").is_visible()
    form = nojs_page.locator(".sort-form")
    form.get_by_label("Issue order").select_option("desc")
    form.get_by_role("button", name="Apply").click()
    assert nojs_page.url.endswith(
        "/series/journal/by-title/Science%20%2F%20News%20%26%20Notes?sort=desc"
    )
    assert nojs_page.get_by_role("heading", name="Science / News & Notes").is_visible()


@pytest.mark.parametrize("width", [320, 1280])
def test_periodical_series_pages_reflow(live_url, browser, width):
    context = browser.new_context(viewport={"width": width, "height": 800})
    page = context.new_page()
    try:
        for path in (
            "/series/journal/by-title/Hidden%20Journal%20Values",
            "/series/journal/by-title/Shared%20Journal",
            "/series/journal/by-title/" + "A" * 180,
            "/series/journal/by-title/" + "B" * 180,
        ):
            page.goto(live_url + path)
            assert page.evaluate(
                "document.documentElement.scrollWidth <= document.documentElement.clientWidth"
            )
    finally:
        context.close()


def test_search_query_and_button_stay_above_filters_when_narrow(live_url, browser):
    context = browser.new_context(viewport={"width": 320, "height": 640})
    page = context.new_page()
    try:
        page.goto(live_url + "/search?q=dune")
        form = page.locator(".search-form")
        controls = [
            form.locator('input[name="q"]'),
            form.locator("#search-type"),
            form.locator("#search-location"),
            form.get_by_role("button", name="Search"),
        ]
        boxes = [control.bounding_box() for control in controls]
        assert all(box is not None for box in boxes)
        input_box, type_box, location_box, button_box = boxes
        form_box = form.bounding_box()
        assert form_box is not None
        assert abs(input_box["y"] - button_box["y"]) < 1
        assert abs(input_box["x"] - form_box["x"]) < 1
        assert abs(button_box["x"] + button_box["width"] - form_box["x"] - form_box["width"]) < 1
        assert input_box["x"] < button_box["x"]
        assert abs(type_box["y"] - location_box["y"]) < 1
        assert type_box["y"] >= button_box["y"] + button_box["height"]
        assert type_box["x"] < location_box["x"]
    finally:
        context.close()


@pytest.mark.parametrize("width", [712, 834, 900])
def test_search_controls_stay_ordered_when_they_fit(live_url, browser, width):
    context = browser.new_context(viewport={"width": width, "height": 800})
    page = context.new_page()
    try:
        page.goto(live_url + "/search?q=dune")
        form = page.locator(".search-form")
        controls = [
            form.locator('input[name="q"]'),
            form.locator("#search-type"),
            form.locator("#search-location"),
            form.get_by_role("button", name="Search"),
        ]
        boxes = [control.bounding_box() for control in controls]
        assert all(box is not None for box in boxes)
        input_box, type_box, location_box, button_box = boxes
        assert all(abs(box["y"] - input_box["y"]) < 1 for box in boxes[1:])
        assert input_box["x"] < type_box["x"] < location_box["x"] < button_box["x"]
    finally:
        context.close()


def test_search_form_stays_on_one_row_on_desktop(live_url, browser):
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    try:
        page.goto(live_url + "/search?q=dune")
        form = page.locator(".search-form")
        controls = [
            form.locator('input[name="q"]'),
            form.locator("#search-type"),
            form.locator("#search-location"),
            form.get_by_role("button", name="Search"),
        ]
        boxes = [control.bounding_box() for control in controls]
        assert all(box is not None for box in boxes)
        input_box, type_box, location_box, button_box = boxes
        assert all(abs(box["y"] - input_box["y"]) < 1 for box in boxes[1:])
        assert input_box["x"] < type_box["x"] < location_box["x"] < button_box["x"]
    finally:
        context.close()


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


def test_mobile_header_sticks_to_top_when_scrolling(live_url, browser):
    context = browser.new_context(viewport={"width": 390, "height": 640})
    page = context.new_page()
    try:
        page.goto(live_url + "/")
        page.evaluate("document.body.style.minHeight = '200vh'")
        page.evaluate("window.scrollTo(0, 200)")
        assert page.evaluate("window.scrollY") > 0
        assert (
            page.locator(".site-header").evaluate("el => getComputedStyle(el).position") == "sticky"
        )
        assert page.locator(".site-header").evaluate(
            "el => Math.abs(el.getBoundingClientRect().top) < 1"
        )
    finally:
        context.close()


@pytest.mark.parametrize("width", [712, 834])
def test_tablet_header_uses_mobile_flyout(live_url, browser, width):
    context = browser.new_context(viewport={"width": width, "height": 1138})
    page = context.new_page()
    try:
        page.goto(live_url + "/")
        assert page.locator(".menu-toggle").is_visible()
        assert not page.locator(".header-menu").evaluate("el => el.open")
        assert (
            page.locator(".site-header").evaluate("el => getComputedStyle(el).position") == "sticky"
        )
    finally:
        context.close()


def test_mobile_header_flyout_contains_navigation_and_language(live_url, browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        page.goto(live_url + "/")
        menu = page.locator(".header-menu")
        toggle = page.locator(".menu-toggle")
        assert not menu.evaluate("el => el.open")
        assert toggle.is_visible()
        assert toggle.get_attribute("aria-label") == "Menu"
        assert toggle.inner_text().strip() == ""
        icon = toggle.locator("img.menu-icon[aria-hidden=true]")
        assert icon.get_attribute("src").endswith("/static/menu.svg")
        assert icon.get_attribute("alt") == ""
        assert icon.evaluate("el => el.complete && el.naturalWidth > 0")
        assert toggle.evaluate("el => getComputedStyle(el).borderWidth") == "0px"
        assert toggle.evaluate("el => el.offsetWidth >= 44 && el.offsetHeight >= 44")
        main_top = page.locator("main").evaluate("el => el.getBoundingClientRect().top")

        toggle.click()
        assert page.locator("main").evaluate("el => el.getBoundingClientRect().top") == main_top
        assert page.get_by_role("link", name="Books").is_visible()
        assert (
            page.locator(".menu-panel nav").evaluate("el => getComputedStyle(el).flexDirection")
            == "column"
        )
        assert page.locator(".menu-panel nav a").evaluate_all(
            "links => links.every(link => link.getBoundingClientRect().height >= 44)"
        )
        assert (
            page.locator(".search-page-link").evaluate("el => getComputedStyle(el).borderTopStyle")
            == "solid"
        )
        assert page.get_by_role("link", name="Search").is_visible()
        assert page.get_by_label("Language").is_visible()

        page.keyboard.press("Escape")
        assert not menu.evaluate("el => el.open")
        assert toggle.evaluate("el => el === document.activeElement")
    finally:
        context.close()


def test_mobile_header_flyout_scrolls_independently(live_url, browser):
    context = browser.new_context(viewport={"width": 390, "height": 480})
    page = context.new_page()
    try:
        page.goto(live_url + "/")
        page.locator(".menu-toggle").click()
        page.locator(".menu-panel nav").evaluate(
            """nav => {
                for (let index = 0; index < 20; index += 1) {
                    const link = document.createElement("a");
                    link.href = "#";
                    link.textContent = `Extra type ${index}`;
                    nav.append(link);
                }
            }"""
        )
        panel = page.locator(".menu-panel")
        dimensions = panel.evaluate(
            """el => ({
                overflowY: getComputedStyle(el).overflowY,
                clientHeight: el.clientHeight,
                scrollHeight: el.scrollHeight,
            })"""
        )
        assert dimensions["overflowY"] == "auto"
        assert dimensions["scrollHeight"] > dimensions["clientHeight"]

        panel.evaluate("el => el.scrollTop = 120")
        assert panel.evaluate("el => el.scrollTop") > 0
        assert page.evaluate("window.scrollY") == 0
    finally:
        context.close()


def test_mobile_header_flyout_closes_on_outside_click(live_url, browser):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    page = context.new_page()
    try:
        page.goto(live_url + "/")
        page.locator(".menu-toggle").click()
        assert page.locator(".header-menu").evaluate("el => el.open")
        page.mouse.click(10, 800)
        assert not page.locator(".header-menu").evaluate("el => el.open")
    finally:
        context.close()


def test_mobile_header_flyout_works_without_javascript(live_url, nojs_page):
    nojs_page.set_viewport_size({"width": 390, "height": 844})
    nojs_page.goto(live_url + "/")
    menu = nojs_page.locator(".header-menu")
    assert menu.evaluate("el => el.open")
    assert nojs_page.get_by_role("link", name="Books").is_visible()
    nojs_page.locator(".menu-toggle").click()
    assert not menu.evaluate("el => el.open")
    nojs_page.locator(".menu-toggle").click()
    assert nojs_page.get_by_role("link", name="Books").is_visible()
    assert nojs_page.get_by_role("link", name="Search").is_visible()
    assert nojs_page.get_by_label("Language").is_visible()


def test_desktop_header_keeps_navigation_and_search_visible(live_url, page):
    page.goto(live_url + "/")
    assert (
        page.locator(".site-header").evaluate("el => getComputedStyle(el).position") == "relative"
    )
    assert page.locator(".menu-toggle").is_hidden()
    assert page.get_by_role("link", name="Books").is_visible()
    assert page.locator(".search-mini input").is_visible()
    assert page.locator(".search-page-link").is_hidden()
