# Contributing

## Ground rules

- The application is strictly read-only. Do not add code paths that write to the database.
- Use parameterized SQL only. Table and column names come from the item type registry, never from user input.
- Never expose borrower personal data.

## Commits

- Follow [Conventional Commits](https://www.conventionalcommits.org/).
- Make one commit per rational unit of change.

## Architecture

- Architecture documentation lives in `docs/arch/`.
- Architectural decisions are recorded as ADRs in `docs/arch/decisions/`.

## Development

Run `ruff check .` and `pytest` before opening a pull request.
