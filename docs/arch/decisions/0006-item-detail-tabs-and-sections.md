# ADR-0006: Item detail tabs and sections

- Status: Accepted
- Date: 2026-10-19

## Context

The item page renders every `ItemType.detail_fields` entry as a label/value pair in one `<dl>`. That
fits short values but not long prose (`description`, `notes`, `about`), nor content that is not a
single value at all: CD track listings, file attachments, photograph galleries. A per-type
`detail_template` (commit b829876e) lets a type swap the whole page template, but gives that template
no richer data to render than the flat field list.

We also expect pages to be split into tabs (for example "Main", "Details", "Attachments", "Gallery"),
and a MARC Record tab remains out of scope ([ADR-0003](0003-defer-marc-sru-and-marc-tags.md)).

## Decision

- An item page is a list of **tabs**; a tab is an ordered list of **sections**; a section has a
  **kind** that selects the partial template used to render it.
- Kinds in this decision:
  - `fields`: label/value pairs in a `<dl>` (what `detail_fields` is today).
  - `text`: one prose column with a heading, rendered as escaped text with line breaks preserved.
  - `table`: rows from a related table joined on a foreign key to the item's primary key, with
    columns, ordering, an optional grouping column and a row limit.
- Kinds recorded for later, not built here: `files` and `gallery`. They carry metadata only; bytes are
  served by dedicated routes like covers, and binary columns are never selected into section data.
- The registry declares tabs on `ItemType` as `TabSpec` records holding section specs. A type that
  declares none gets a synthesized "Main" tab built from `detail_fields` and the text columns, so
  existing types need no migration. Every real type has only Main for now.
- Prose columns (`description`, `notes`, `about`) move out of `detail_fields` into `text` sections. On
  Main the description renders above the `fields` section.
- All table and column names, including those of related tables and foreign keys, come from the
  registry and go through `quote()`. `resolve()` drops columns, related tables, sections and tabs that
  the connected database cannot serve, so a missing grant or a schema difference degrades gracefully.
- A `TabSpec` may name a template. Template lookup is: per-type tab template, generic tab template,
  default. The page shell stays `item.html`. This supersedes `ItemType.detail_template`.
- Tabs may be marked lazy; their content is not loaded with the item page (see
  [ADR-0007](0007-in-page-tab-switching.md)).

## Consequences

- Prose and related-row content no longer have to be forced into a label/value list.
- Adding a tab or section is a registry edit plus, at most, a template partial.
- The view model is richer than a flat field list, and replaces the per-type whole-page template.
- The registry grows a second family of specs (tabs, sections) to keep consistent with `resolve()`.
- Related tables need `SELECT` granted to the read-only role, or the section is dropped.

## Alternatives considered

- **Keep `detail_template` and let templates query what they need:** puts data access in templates and
  bypasses the registry's identifier rules.
- **Flat `sections` list on `Item` with no tabs:** cannot express tabs and loads heavy content
  eagerly.
- **Render prose and tables as special-cased `detail_fields` entries:** keeps the flat model but
  needs per-field flags that grow into this design anyway.
