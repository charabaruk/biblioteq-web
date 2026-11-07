# ADR-0012: Page title, display title and subtitle

- Status: Accepted (volume and issue handling updated by ADR-0013)
- Date: 2026-11-06

## Context

Magazines and journals share one title across many issues, so browser tabs and history entries
are indistinguishable between issues. Books in a series carry the series in separate columns. The
issue columns (`display_number`, `issuevolume`, `issueno`), `pdate` and the series columns
(`series_title`, `volume_number`) already belong to the tables of the item type registry
([ADR-0002](0002-registry-driven-item-types.md)).

## Decision

Each item page has three texts:

- **Page title:** the HTML `<title>` element, followed by ` - {site title}`.
- **Display title:** the `<h1>`.
- **Subtitle:** an optional `<h2>` after the `<h1>`, rendered only when set.

By default the page title and display title equal the item title and there is no subtitle.
Item types override them through registry data (`issue`, `series`), never by type name in
templates. Cover alt text and browse cards keep the item title.

"Empty" means a `display_number` of `-1` or NULL, and an `issuevolume` or `issueno` of `0` or NULL.

### Magazines and journals

Page title, in order of precedence:

| Data present | Page title |
|---|---|
| display number, volume and issue | `{title} {display_number} (vol. {issuevolume} no. {issueno})` |
| display number, issue only | `{title} {display_number} (no. {issueno})` |
| display number, volume only | `{title} {display_number} (vol. {issuevolume})` |
| display number only | `{title} {display_number}` |
| volume and issue | `{title} vol. {issuevolume} no. {issueno}` |
| issue only | `{title} no. {issueno}` |
| none | `{title}` |

- **Display title:** `{title} {display_number}` when a display number exists, otherwise the
  volume and issue form from the table (`{title} vol. {v} no. {n}`, `{title} no. {n}`), otherwise
  `{title}`.
- **Subtitle:** the publication month and year from `pdate`, followed by ` (vol. {v} no. {n})`
  only when the display title shows the display number, so the volume and issue are shown once
  between the two. Empty volume or issue values are left out. Without a date, only the
  parenthesised part is shown; with neither, there is no subtitle.
- **Dates:** `pdate` is free text. MM/DD/YYYY (as BiblioteQ writes it) and ISO YYYY-MM-DD are
  parsed; any other value is shown as it is.
- **Formatting:** month and year are formatted for the request language with Babel's locale data
  (`yMMMM`), not with gettext. The "vol." and "no." wording is translatable through gettext;
  translations are supplied through Crowdin.

### Books

- Page title and display title are the item title.
- Subtitle: `{series_title} volume {volume_number}` when both exist, `{series_title}` when there is
  no volume number, none when there is no series title.

## Consequences

- `get_item()` also selects the issue, series and `pdate` columns.
- A database lacking those columns behaves as before: plain titles and no subtitle.
- Babel becomes a runtime dependency (`requirements.txt`), where it was development-only.
- No schema change; SQL stays dialect-neutral with identifiers from the registry only.
- Until translated, non-English locales show the English wording of the new strings.

## Alternatives considered

- **Month names through gettext:** each locale would need twelve translated strings that Babel
  already ships, and untranslated locales would fall back to English.
- **`strftime` or the `locale` module:** depends on the locales installed on the host, which
  containers and minimal servers often lack.
- **Composing titles in SQL:** needs dialect-specific concatenation and cannot be translated.
- **Hard-coding type names in templates:** bypasses the registry.
