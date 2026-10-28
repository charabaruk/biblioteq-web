# Accessibility

This document is the source of truth for accessibility requirements in biblioteq-web, a
read-only web interface for BiblioteQ library collections. It is an engineering standard, not
a public conformance statement: it binds contributors and reviewers, and is cited by
[ADR-0009](docs/arch/decisions/0009-wcag-22-aa-conformance.md).

Where this document and any other document disagree, this one wins. If a rule here proves
wrong, change this document in the same pull request that changes the behaviour.

## Terms

- **biblioteq-web** is this project: an independent, third-party, read-only web browser for
  BiblioteQ collections. It is not BiblioteQ, and it is not part of BiblioteQ.
- **BiblioteQ** is the upstream cataloging and library management suite that owns the database
  schema this project reads. It is a separate project, maintained separately. Its desktop
  client and its own interface are outside the scope of this document.
- **The interface**, **the web app** and **the application** mean biblioteq-web's rendered UI.
- **Catalog data** means the records, cover images and metadata stored in the BiblioteQ
  database and supplied by whoever catalogued them.

Requirements in this document apply to biblioteq-web only. Nothing here is a claim about
BiblioteQ, about its accessibility, or about the accessibility of data it holds.

## Conformance target

The biblioteq-web interface targets **WCAG 2.2 Level AA**: every Level A and AA success
criterion in WCAG 2.2, with no claimed conformance to any other standard.

- Conformance is assessed per page template and per state, not once for the site as a whole.
  A template that passes on a populated database but fails on an empty result set is not
  conformant.
- Success criterion 4.1.1 Parsing is obsolete in WCAG 2.2 and is not tested.
- Nothing in this document lowers a WCAG requirement. Rules marked **(project rule)** are
  additional requirements chosen for this product; they are not claimed as WCAG conformance.
- We do not claim conformance in public materials. If a conformance statement is ever
  published, it is a separate decision with a dated audit behind it, and it would cover
  biblioteq-web only.

## Scope

In scope — everything biblioteq-web renders:

- All templates and their states: index, search results, browse, item detail (every tab,
  including lazy-loaded and empty states), pagination, language switcher, error pages.
- The static assets that support them: `static/style.css`, `static/tabs.js`.
- Content the application chooses to present, including generated alt text and the wording of
  status messages.

Out of scope:

- The quality and completeness of catalog data in the BiblioteQ database — titles,
  descriptions, subject terms and any alt text recorded there.
- Cover images and other media files as files, and the BiblioteQ schema that stores them.
- BiblioteQ itself, including its desktop client and any other interface to the same data.
- `vendor/` and other third-party code.
- Operational surface: Docker, systemd units, nginx configuration, `docs/deploy/`.
- Deployment documentation and the README.

Out-of-scope material does not excuse an inaccessible presentation of it. A cover image with
no usable description still has to be marked up as described under [Images](#images).

## Baseline: works without JavaScript

The application is server-rendered and must stay usable with JavaScript disabled. This is a
**normative requirement**, not best effort.

- Every core task — search, browse, view an item and all of its tabs, change language,
  paginate — MUST be completable with JavaScript disabled.
- Scripting is progressive enhancement only. It MUST NOT be the sole means of reaching
  content, submitting a form, or navigating.
- Content hidden by default and revealed by script MUST be reachable without script. Tabs
  follow this: without script all panels render in the document.
- A feature that cannot meet this baseline is either redesigned or does not ship.

## Semantics and structure

- Every page MUST have a `<title>` that identifies the page and the site, and describes the
  current view — for example the query or the item title. The site title is the configured
  `BIBLIOTEQ_SITE_TITLE`, which defaults to "Library Collection"; the page title carries both
  it and the view, never the site title alone.
- Every page MUST have exactly one `<main>`, and a `<header>` and `<nav>` as appropriate.
- The `<html>` element MUST carry a `lang` attribute reflecting the language actually served.
- Headings MUST form a logical outline with no skipped levels used for visual effect.
- Repeated navigation regions MUST be distinguishable by accessible name when more than one
  exists on a page.
- Link text MUST make sense out of context. "More" or "View" alone is not acceptable; the
  item title is part of the link name or its accessible name.
- Current location in navigation and in pagination MUST be exposed programmatically, not only
  visually (for example `aria-current="page"`).
- Data that is a table MUST be marked up as a table with header cells, not as a grid of
  `<div>`s. Label/value data uses `<dl>`.
- Status and availability counts MUST be conveyed in text. Their accessible names MUST read
  as complete statements, not as bare numbers.

## Keyboard and focus

- Everything operable MUST be operable by keyboard alone, with no keyboard trap.
- Focus order MUST follow a meaningful reading order.
- The keyboard focus indicator MUST be visible on every focusable element and MUST NOT be
  removed. Overriding the user agent default is allowed only if the replacement is at least
  as visible **(project rule: at least a 2 px indicator, with 3:1 contrast against both the
  component and the adjacent background)**.
- Focus MUST NOT be moved on page load, and MUST NOT be moved without the user's action
  except to a region the user just caused to appear.
- Focused elements MUST NOT be entirely hidden by sticky or fixed overlays
  (WCAG 2.4.11).
- A page-level skip mechanism to the main content is required whenever a header or navigation
  block precedes the main content **(project rule)**.
- Custom widgets MUST implement the keyboard interaction pattern of their ARIA role. For
  tabs: Left/Right arrows move between tabs, Home/End move to the first and last tab, and the
  tab list is a single tab stop.
- Pointer gestures MUST NOT require dragging (WCAG 2.5.7). If a drag interaction is added, a
  single-pointer alternative is required in the same view.
- Pointer targets MUST be at least 24 × 24 CSS px, or spaced so that a 24 px circle centred
  on each target does not intersect another (WCAG 2.5.8).

## Forms and search

- Every form control MUST have a programmatically associated label. Placeholder text is not
  a label.
- The search form MUST be exposed as a search landmark with an accessible name.
- The language selector MUST keep its visible `<label>`; a `<select>` alone is not sufficient.
- Errors MUST be identified in text, associated with the field, and MUST NOT be conveyed by
  colour or an icon alone.
- Instructions and required-field expectations MUST be stated before the field, not only on
  failure.
- Search must not require re-entering information already provided in the same process
  (WCAG 3.3.7).

## Progressive enhancement and scripted content

Rules for `static/tabs.js` and anything like it:

- Script MUST NOT overwrite or replace server-rendered content; it adds behaviour.
- ARIA roles and states MUST only be applied when the behaviour they describe exists.
  `role="tablist"`, `role="tab"` and `aria-selected` must not be present in the served HTML.
- The tab list MUST reference its panels (`aria-controls`) and each panel MUST be labelled by
  its tab (`aria-labelledby`).
- Loading and failure of lazily loaded content MUST be announced in a live region
  (`aria-live="polite"` for loading, `assertive` only for failures that block the task).
- Failure MUST leave the page usable: the user can retry, and other tabs still work.
- No string in script may be hard-coded in English once the string is user-visible. Until the
  localization gap below is closed, new user-visible strings in script are not added.
- Timed behaviour MUST NOT be introduced for content the user is reading; if it ever is, it
  must be pausable, stoppable or adjustable (WCAG 2.2.2).

## Visual presentation

- Text contrast MUST be at least 4.5:1; large text and non-text indicators (borders of
  controls, focus rings, icons that carry meaning) at least 3:1 (WCAG 1.4.3, 1.4.11).
- Colour MUST NEVER be the only means of conveying information, indicating an action,
  prompting a response, or distinguishing a visual element. Availability, errors, required
  fields, and the selected tab MUST each also carry text, an icon with a text alternative,
  or a programmatic state.
- Content MUST reflow to a 320 CSS px wide viewport without two-dimensional scrolling
  (WCAG 1.4.10), and MUST remain usable at 200% zoom (1.4.4).
- No content may be lost when text spacing is increased to the WCAG 1.4.12 minimums.
- Text must not be presented as images.

### Theming and colour schemes

The product ships one light palette today. Adding a dark scheme, a high-contrast mode, or
user-selectable themes is permitted and is not constrained by this document — but any palette
added MUST satisfy the contrast and colour-independence rules above in every scheme it
defines. A theme is not complete until it has been checked against these rules.

Colour values MUST be defined once (custom properties or equivalent) rather than repeated
inline, so that a new scheme can meet these rules without rewriting templates.

## Images

- A decorative image MUST have an empty `alt` attribute (`alt=""`) and MUST NOT be given a
  role or title that reintroduces it to assistive technology.
- A functional image (a link or button containing only an image) MUST have an alt text that
  describes its function.
- Cover images and thumbnails are decorative when the title and creator are already adjacent
  text, and MUST use `alt=""` in that case.
- Where they are not accompanied by that text, an alt text MUST be generated rather than left
  empty or filled with a filename: `"<title> — cover"`, or `"<title> by <creator> — cover"`
  when a creator is available. Follow the localization and formatting rules for the rest of
  the UI when composing it.
- If the database supplies a usable description for the image, use it. If it supplies none,
  generate one as above. Never invent content that is not in the record.
- The same rules apply to photographs in collection galleries when those are built.

## Motion

No animation, autoplaying media or moving content is present today, and none is required.
This section is not applicable to the current product.

If motion is introduced later, it MUST respect `prefers-reduced-motion` and MUST NOT
autoplay. This is a forward constraint on future work, not a description of current behaviour.

## Open items

Deliberately deferred. Recorded so that the gaps are visible rather than assumed closed.

- **Localization.** Rules for `lang` on translated segments, `lang` on catalog-sourced
  foreign-language titles, and a prohibition on string concatenation in templates are not yet
  specified. `docs/localization.md` covers the process; accessibility requirements for it are
  still to be written.
- **Automated testing.** No accessibility tooling runs in CI. See [Testing](#testing).

## Testing

Automated tooling is not a gate yet. Verification is currently manual and descriptive; it is
not a fixed matrix, and it is expected to change as tooling is tried.

Before merging a change that touches templates, CSS or script, the author should:

1. Tab through every affected page. Confirm the focus indicator is visible at each stop, the
   order is sensible, and the task can be completed without a mouse.
2. Complete the task with JavaScript disabled.
3. Check the changed elements' contrast against their actual backgrounds.
4. Zoom to 200%, and to a 320 px wide viewport, and confirm nothing is lost or clipped.
5. Run a browser accessibility audit or a screen reader spot check on the changed page if the
   change is structural (landmarks, headings, ARIA, forms, live regions).

Contributors are not expected to own a screen reader setup. Reviewers should ask for evidence
rather than assume a change is fine because it "looks the same".

## Current known gaps

Honest state as of this document's date. Each of these is a defect against the rules above,
not an exemption.

- No skip link; only one focus style, inherited from the user agent; links are not underlined
  at rest.
- Navigation landmarks are not labelled; there is more than one region of navigation on some
  pages.
- Tabs lack `aria-controls` and `aria-labelledby`, and do not support Home/End.
- The tab load-failure message is hard-coded in English.
- Only a light colour scheme exists; contrast of the existing palette has not been verified
  against every pairing used.
- No accessibility tooling in CI.

## How this is enforced

- **Pull requests.** The PR checklist includes an accessibility item referencing this
  document.
- **Contributing.** `CONTRIBUTING.md` carries a short pre-PR accessibility checklist.
- **Issues.** `.github/ISSUE_TEMPLATE/accessibility.md` is the template for accessibility
  defects and improvements.
- **Changelog.** Accessibility fixes and improvements are listed in the existing
  `Changed` / `Added` / `Fixed` groups of `CHANGELOG.md` under Common Changelog, in the
  imperative mood, with a reference — never in a separate accessibility section.
- **Architecture.** The conformance target is recorded in
  [ADR-0009](docs/arch/decisions/0009-wcag-22-aa-conformance.md). Changing the target level
  requires a superseding ADR; the rules themselves are changed here.

## Revision history

| Version | Date | Change |
| --- | --- | --- |
| 0.1 | 2026-10-28 | Initial standard: WCAG 2.2 AA, no-JS baseline, scope, known gaps |
