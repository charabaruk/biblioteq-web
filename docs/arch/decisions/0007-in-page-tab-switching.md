# ADR-0007: In-page tab switching

- Status: Accepted
- Date: 2026-10-19

## Context

[ADR-0006](0006-item-detail-tabs-and-sections.md) lets an item page have several tabs. Switching tabs
should not navigate to another page, and `/item/{type_key}/{item_id}` must keep working for clients
without JavaScript and for plain links.

## Decision

- `/item/{type_key}/{item_id}` renders every non-lazy tab as a `<section id="tab-{key}">` with a
  heading. Without JavaScript the page is complete and reads top to bottom, with anchor links
  (`#tab-{key}`) at the top.
- A small script turns the anchors into an ARIA tablist and shows one panel at a time. The active
  tab is kept in the URL fragment as `#tab={key}`; the path and query never change. Tab switches use
  `history.replaceState`, so they add no history entries.
- A tab may be lazy: the item page renders a placeholder with a link to
  `/item/{type_key}/{item_id}/{tab}` instead of its content. The script fetches that URL the first
  time the tab is activated and swaps the response into the panel.
- `/item/{type_key}/{item_id}/{tab}` serves both audiences:
  - With the request header `X-Requested-With: fetch`, it returns only the tab's HTML fragment.
  - Without it, it returns the full item page with that tab's content, so the link works without
    JavaScript.
  - The response carries `Vary: X-Requested-With`, so caches do not mix the two bodies.
  - An unknown tab key returns 404. Tab keys are looked up in the registry and never used in SQL.
- The fragment and the full page render a tab through the same partial, so they cannot diverge.
- Types with a single tab show no tab list.

## Consequences

- No-JavaScript clients get a complete page and a working fallback route for lazy tabs.
- Lazy tabs keep heavy content (galleries, file lists) off the main page query.
- The tab route has two representations, so it needs `Vary` and tests for both.
- The script is a progressive enhancement and the only client-side code besides the stylesheet.

## Alternatives considered

- **Query flag such as `?fragment=1`:** simpler but puts presentation state in URLs and caches.
- **`Accept` negotiation:** a custom media type for a fragment is heavier than one explicit header.
- **Separate URL per tab with full navigation:** meets the no-JavaScript need but changes the
  location on every switch, which is what we want to avoid.
- **`location.hash` updates:** would make back and forward move between tabs, which is not wanted.
