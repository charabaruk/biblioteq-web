# ADR-0001: Read-only FastAPI stack with synchronous SQLAlchemy

- Status: Accepted (PostgreSQL-only parts superseded by ADR-0005)
- Date: 2026-10-16

## Context

BiblioteQ is a desktop application that owns its PostgreSQL schema. This project is a separate web
front end that must never alter that data. Target deployments range from a home server to small and
medium organizational libraries.

## Decision

- FastAPI with Jinja2 server-rendered pages; Uvicorn workers under Gunicorn behind a reverse proxy.
- SQLAlchemy 2.0 Core with psycopg 3, using synchronous connections. FastAPI runs sync handlers in a
  threadpool, which is simple and sufficient at this scale. Pool size and worker count are configurable.
- Raw parameterized `text()` SQL, no ORM models, because the schema belongs to BiblioteQ and varies
  between versions.
- The application connects with a dedicated read-only PostgreSQL role and additionally sets
  `default_transaction_read_only=on` and a `statement_timeout` on every connection.
- The schema defaults to `public` and is configurable via `BIBLIOTEQ_DB_SCHEMA`; it is validated as an
  identifier and applied through `search_path`.
- The `marc_tags` column is out of scope: it is never selected or displayed (see ADR-0003).

## Consequences

- Simple to run and contribute to; no async driver complexity.
- If load grows beyond what threads handle, an async engine can replace `app/db.py` and the repository.
- Schema differences between BiblioteQ versions must be handled in the item type registry.
