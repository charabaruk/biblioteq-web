# Testing

## Setup

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pip install -r requirements-a11y.txt   # only for accessibility tests
.venv/bin/playwright install chromium            # only for accessibility tests
```

## Regular tests

```sh
.venv/bin/pytest -q
```

- Lives in `tests/`. Plain `pytest` skips tests marked `a11y`.
- Integration tests run against SQLite always, and against PostgreSQL when
  `BIBLIOTEQ_TEST_DB_URL` points at an empty, disposable database. That database is dropped and
  recreated (`DROP SCHEMA public CASCADE`), so never point it at real data.
- Schemas for the fixtures are `tests/schema_sqlite.sql` and `tests/schema.sql`; keep them in
  step.
- Useful fixtures (`tests/conftest.py`): `client` (default registry), `tabbed_client` and
  `tabbed_types` (book type with a lazy second tab backed by the test-only `book_note` table).
- Before committing: `ruff check .`, `ruff format .` and `pytest`. The VS Code task
  "Check (lint, format, test)" runs all three.
- CI runs `pytest` with coverage. It does not run accessibility tests.

## Accessibility tests

```sh
.venv/bin/pytest -m a11y
```

Opt-in, local only. They target WCAG 2.2 AA (see [ACCESSIBILITY.md](../ACCESSIBILITY.md) and
[ADR-0009](arch/decisions/0009-wcag-22-aa-conformance.md)). They start the real app with uvicorn
on a free local port over a temporary SQLite database, and drive headless Chromium with
Playwright. If Chromium is not installed, the tests skip with a hint.

| File | Layer | Covers |
| --- | --- | --- |
| `tests/a11y/test_axe.py` | Rendered-DOM rules | axe-core scan (tags `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, `wcag22aa`) of each template and state: home, search (empty, results, none), browse, item, error pages, and the item page with the lazy tab loaded |
| `tests/a11y/test_behaviour.py` | Scripted behaviour | Tabs without JavaScript, roving tabindex and arrow keys, in-page lazy loading without extra history entries, deep links, visible focus indicators, reflow at 320 px |

### Adding a page or state

Add an entry to `PAGES` in `test_axe.py`. Pages that need interaction before scanning get their
own test that drives the page, then calls `_violations(page)`.

### Known gaps

`KNOWN_GAPS` in `test_axe.py` maps an axe rule id to the reason it is tolerated. It is meant to
stay empty or short; each entry is a defect listed in `ACCESSIBILITY.md`, removed when fixed.

### What this does not cover

Automated checks find only part of what WCAG requires. Still done by hand, per the checklist in
`ACCESSIBILITY.md`: screen reader behaviour, reading order and wording, contrast of states axe
cannot reach, 200% zoom, and forced-colors mode.

### CI

Not enabled. Adopting it is an operational change that needs its own ADR (see ADR-0009).
