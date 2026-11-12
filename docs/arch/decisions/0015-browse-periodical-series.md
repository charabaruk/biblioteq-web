# ADR-0015: Browse periodicals by series

- Status: Accepted
- Date: 2026-11-11
- Issue: [#38](https://github.com/charabaruk/biblioteq-web/issues/38)

## Context

Journal and magazine browse pages show individual issues. Readers also need to browse one card
per periodical and open its issues. An ISSN identifies a series when one is present, but not
every issue has an ISSN. [ADR-0014](0014-periodical-series-by-title.md) provides title-based
series pages for issues with a NULL ISSN and treats every non-NULL value as an identifier. The
title column is NOT NULL, and BiblioteQ's item editors do not accept blank titles.

## Decision

- Add `/browse/{type_key}/by-series` for journals and magazines, alongside the existing
  issue-browse pages. Series browsing does not filter by location.
- Group issues within their item type by their exact stored ISSN when it is nonblank. A NULL,
  empty or space-only ISSN is missing; group these issues by exact stored title instead. Do not
  combine missing-ISSN issues with an identified group, even when their titles match.
- This changes ADR-0014's distinction between NULL and non-NULL ISSNs: its title-based lookup
  must include empty and space-only ISSNs as missing. Preserve existing identifier-based URLs,
  including direct links to empty identifiers, for compatibility.
- Select the latest issue in each group using the existing descending issue order: volume,
  issue number, display number, then publication date, with the existing NULL ordering and
  primary-key tie-break. Do not compare titles when selecting within a group. Use that issue's
  title and front cover on the series card; if it has no front cover, show the normal placeholder.
- Sort cards by their representative titles using the configured title sort, with deterministic
  group-key tie-breaks, then paginate groups rather than issues.
- Keep existing ISSN and title series URLs. Add a typed query-based series URL for keys that
  cannot safely round-trip through those paths. The key type keeps an
  ISSN distinct from the same text used as a title. Series pages retain issue sorting and
  pagination. Additional links from individual issue pages are outside this decision.
- Fetch registry-approved fields without cover blobs, group and sort in the application, and
  load card data for the requested page. Continue to bind values, remain read-only and support
  SQLite and PostgreSQL without schema changes.

## Consequences

- A series card represents all of its issues, including issues whose titles changed under one
  ISSN. An unidentified issue cannot be inferred to belong to an identified series.
- Blank ISSNs now participate in title-based series lookup, unlike ADR-0014's original rule.
  Existing direct identifier URLs remain available, but title lookup for a mixed title can return
  unidentified issues instead of redirecting to a blank identifier.
- The latest issue can differ between database dialects when its ordering fields contain NULL,
  because the existing issue ordering follows database NULL ordering.
- Grouping and sorting require reading lightweight fields for all matching issues. The cost grows
  with the size of the periodical catalogue, as with application-side natural title sorting.

## Alternatives considered

- **Browse only by issue:** does not give readers a catalogue of periodical series.
- **Group every issue by title:** merges distinct ISSNs and separates issues whose title changed.
- **Treat every non-NULL ISSN as an identifier:** groups unrelated empty-ISSN records together.
- **Use the newest issue with a cover:** may show an older issue rather than the newest issue.
- **Group and sort with database-specific SQL:** complicates natural sorting and portability.
