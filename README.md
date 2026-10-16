# biblioteq-web

A read-only web browser for [BiblioteQ](https://github.com/textbrowser/biblioteq) library collections.

It connects to an existing BiblioteQ PostgreSQL database using a dedicated read-only role and lets users
search and browse books, DVDs, CDs, journals, magazines, video games, grey literature and photograph
collections, view item details and availability, and see cover images.

It is intended for anything from a home media server to a small or medium organizational library, and is
designed to run behind a reverse proxy such as nginx.

## Scope

- Read-only: the application never writes to the database.
- Borrower personal data is never read or displayed; availability uses counts only.
- The `marc_tags` column is not used (see [ADR-0003](docs/arch/decisions/0003-defer-marc-sru-and-marc-tags.md)).

## Quick start

Requires Python 3.11+ and a BiblioteQ PostgreSQL database.

1. Create the read-only role: adapt and run [docs/deploy/readonly-role.sql](docs/deploy/readonly-role.sql).
2. Install and configure:

   ```sh
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   cp .env.example .env   # edit BIBLIOTEQ_DB_URL
   ```

3. Run:

   ```sh
   set -a; . ./.env; set +a
   .venv/bin/uvicorn app.main:app --port 8000
   ```

   Open <http://127.0.0.1:8000/>.

## Configuration

All settings are environment variables; see [.env.example](.env.example).

| Variable | Default | Purpose |
| --- | --- | --- |
| `BIBLIOTEQ_DB_URL` | required | SQLAlchemy URL, e.g. `postgresql+psycopg://user:pw@host/db` |
| `BIBLIOTEQ_DB_SCHEMA` | `public` | Schema containing the BiblioteQ tables |
| `BIBLIOTEQ_PAGE_SIZE` | `24` | Results per page (max 100) |
| `BIBLIOTEQ_DB_POOL_SIZE` / `BIBLIOTEQ_DB_MAX_OVERFLOW` | `5` / `5` | Connection pool per worker |
| `BIBLIOTEQ_DB_STATEMENT_TIMEOUT_MS` | `5000` | Per-statement timeout |
| `BIBLIOTEQ_SITE_TITLE` | `Library Collection` | Title shown in the UI |
| `BIBLIOTEQ_LOG_LEVEL` | `INFO` | Python log level |
| `BIBLIOTEQ_ROOT_PATH` | empty | URL prefix when served under a sub-path |

## Endpoints

| Path | Description |
| --- | --- |
| `/` | Search form and recently added items |
| `/search?q=&type=&page=` | Search across item types |
| `/browse/{type}` | Browse one item type |
| `/item/{type}/{id}` | Item details and availability |
| `/cover/{type}/{id}?side=front\|back` | Cover image from the database |
| `/healthz`, `/readyz` | Liveness and database readiness |

## Production

- systemd unit: [docs/deploy/biblioteq-web.service](docs/deploy/biblioteq-web.service)
- nginx: [docs/deploy/nginx.conf](docs/deploy/nginx.conf)
- Docker: [Dockerfile](Dockerfile) and [docker-compose.example.yml](docker-compose.example.yml)

The app has no authentication; restrict access in the reverse proxy if the catalog is not public
([ADR-0004](docs/arch/decisions/0004-deployment-and-access-control.md)).

## Development

```sh
.venv/bin/ruff check .
BIBLIOTEQ_TEST_DB_URL=postgresql+psycopg://user:pw@localhost/scratch_db .venv/bin/pytest
```

The integration tests drop and recreate the `public` schema of `BIBLIOTEQ_TEST_DB_URL`; use a disposable
database. Without that variable they are skipped.

Architecture documentation is in [docs/arch/](docs/arch/).

## License

[MIT](LICENSE)
