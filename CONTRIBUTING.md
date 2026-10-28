# Contributing

## Ground rules

- The application is strictly read-only. Do not add code paths that write to the database.
- Use parameterized SQL only. Table and column names come from the item type registry, never from user input.
- Never expose borrower personal data.

## Accessibility

`ACCESSIBILITY.md` is the source of truth for accessibility requirements. Before opening a
pull request that touches templates, CSS or script:

- Everything you changed is reachable and operable by keyboard, with a visible focus indicator.
- The task still completes with JavaScript disabled.
- New or changed colours meet 4.5:1 for text and 3:1 for non-text, and colour is never the only
  signal.
- New controls have an accessible name and expose their state programmatically.
- Images added to a page are either marked decorative (`alt=""`) or given a generated
  description.

Fixing an accessibility problem is a normal change: list it under `Changed`, `Added` or
`Fixed` in `CHANGELOG.md` per Common Changelog, never in a separate accessibility section.

## Commits

- Follow [Conventional Commits](https://www.conventionalcommits.org/).
- Make one commit per rational unit of change.

## Architecture

- Architecture documentation lives in `docs/arch/`.
- Architectural decisions are recorded as ADRs in `docs/arch/decisions/`.

## Development

Run `ruff check .` and `pytest` before opening a pull request.
