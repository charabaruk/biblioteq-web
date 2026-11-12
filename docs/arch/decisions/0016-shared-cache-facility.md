# ADR-0016: Shared cache facility

- Status: Accepted
- Date: 2026-11-12

## Context

Some read-only data is expensive to derive from the BiblioteQ database, but can tolerate a delay
before changes become visible. Repeating the same work for every request, or simultaneously in
several workers, can put unnecessary load on the database. BiblioteQ can change the data independently
of this application, so the application cannot rely on write-time invalidation.

Deployments range from a single process to multiple workers and may not have a shared cache service.
The BiblioteQ database remains read-only ([ADR-0001](0001-read-only-fastapi-stack.md)); it must not
be used to store cache entries or coordination state.

## Decision

- Provide one reusable application cache facility for derived read-only data. Callers specify a
  cache key, a loader and a freshness policy; they do not depend on a particular backend.
- By default, use bounded in-memory storage local to each worker. An optional environment setting
  selects Redis for storage shared by workers; an empty setting selects worker-local storage.
  Redis writes are confined to cache data and coordination state, not the BiblioteQ database.
- Namespace keys by deployment and database identity, including the configured schema, and version
  cached formats. Do not include credentials in keys or logs. Separate deployments must not share
  entries unless explicitly configured to do so.
- Serialize shared entries in a versioned, validated format; do not deserialize executable objects.
  The local backend must provide equivalent value semantics, so callers cannot mutate a cached
  snapshot through a returned reference.
- Configure freshness and maximum stale periods through environment variables that operators can
  set in `.env`. A successful load publishes a complete snapshot atomically. During normal
  operation, source changes become visible on a successful refresh after the freshness period;
  the cache does not promise immediate invalidation.
- Coordinate concurrent loads for the same key: once per worker in local mode and across workers
  in Redis mode. Redis coordination uses bounded leases and ownership checks, including at publish
  time, so an expired loader cannot overwrite a newer snapshot. Different keys may load independently.
- While a refresh is in progress or after it fails, a previous successful snapshot may be served
  only within its maximum stale period. Apply bounded retry backoff and log refresh failures. If no
  usable snapshot exists, return an unavailable error rather than inventing an empty result.
- When Redis is unavailable, do not silently fall back to uncoordinated database scans. A worker may
  serve its last successful snapshot within the same stale limit; otherwise return an unavailable
  error until Redis is reachable. Bound Redis connection and operation timeouts.
- Bound local memory and Redis entry lifetime; eviction, restarts or cache loss can require a fresh
  load. A missing entry is not an empty result. Callers must tolerate the cache being unavailable.
- Cache only data suitable for the application's read-only public catalog. Never cache borrower
  personal data. Redis access, authentication and transport security are deployment responsibilities;
  it must not be exposed as a public service.

## Consequences

- Default deployments need no additional service, but each worker may perform its own refresh and
  hold a different snapshot. Redis reduces duplicate work across workers at the cost of another
  service, network calls and operational configuration.
- Snapshots can be stale, including longer than the freshness period during failures, but not beyond
  the configured maximum stale period. Cache loss or eviction can make stale data unavailable sooner.
- Refresh coordination limits duplicate loads during normal operation; lease expiry, process failure
  or network partitions can still cause overlapping work. Ownership checks prevent an expired loader
  from publishing over a newer one.
- Cached data consumes bounded local memory or Redis resources. Large snapshots and refresh costs
  must be measured, and the facility needs tests for concurrency, expiry, failure and both backends.

## Alternatives considered

- **No cache:** keeps data current but repeats expensive reads and allows concurrent requests to
  amplify database load.
- **Worker-local cache only:** avoids an external service but duplicates refreshes across workers.
- **Require Redis:** coordinates workers but adds a mandatory service to small deployments.
- **Store cache data in BiblioteQ:** violates the read-only database boundary and couples the cache
  to a schema owned by another application.
