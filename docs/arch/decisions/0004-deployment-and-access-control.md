# ADR-0004: Deployment model and access control

- Status: Accepted
- Date: 2026-10-16

## Context

The project targets home servers and small or medium organizational libraries. Library catalogs are
often public, but borrower data is personal and must stay private.

## Decision

- The app runs under Gunicorn with Uvicorn workers on a loopback address behind a reverse proxy
  (nginx example in `docs/deploy/`). Sub-path hosting uses `BIBLIOTEQ_ROOT_PATH`.
- The app has no authentication of its own. Operators who need access control put it in the proxy
  (basic auth, IP allow-list or an OIDC proxy). The catalog is read-only and exposes no borrower data.
- The database role is granted `SELECT` on item tables only, and column-level `SELECT (item_oid, type)`
  on `item_borrower`, so borrower identities are unreadable even if the app were compromised.
- A Dockerfile and example compose file are provided as an optional deployment.
- `/healthz` and `/readyz` support supervision and load balancers.

## Consequences

- No user or session management to maintain in the app.
- Authentication can be added later through a single dependency without changing routes.
- Operators are responsible for TLS and access control at the proxy.
