# ADR-0009: Target WCAG 2.2 Level AA in biblioteq-web

- Status: Accepted
- Date: 2026-10-28

## Context

biblioteq-web is an independent, third-party web interface for BiblioteQ library collections.
It reads an existing BiblioteQ database and renders catalog pages for patrons and staff; it is
not BiblioteQ and does not ship with it. Accessibility has so far been handled per change —
landmarks, a labelled language selector, a search landmark, tabs that degrade without script —
without a stated target. That leaves two problems: reviewers cannot judge whether a change is
a regression, and contributors cannot tell how far the obligation extends (does it cover the
catalog data in the upstream database, the cover images, the deployment docs?).

A conformance level is a durable commitment. It determines what we test, what we may ship with
known defects, and what we may say publicly. It belongs in the architecture record, not only in
a contributor guide.

## Decision

- The biblioteq-web interface targets **WCAG 2.2 Level AA**, and no other standard. No
  EN 301 549 or Section 508 alignment is claimed; either may be added later by a superseding
  ADR if a procurement requirement appears.
- The **rules** that implement this target — semantics, keyboard, no-JS baseline, forms,
  scripted content, contrast and colour independence, images, motion, testing, known gaps —
  live in [`ACCESSIBILITY.md`](../../../ACCESSIBILITY.md) at the repository root. That file is
  the source of truth for accessibility requirements.
- This ADR records **why** and **how far**: the level, the scope boundary, and the process
  hooks. It does not restate the rules, so that the rules can change without a new ADR.
- Scope is the application's rendered UI and the assets that support it. Out of scope: the
  quality of catalog data in the BiblioteQ database, the cover images themselves, BiblioteQ
  and its desktop client, `vendor/`, and the operational and deployment surface.
- This decision makes no claim about the accessibility of BiblioteQ or of catalog data
  supplied to it. It covers only what biblioteq-web renders.
- Conformance is assessed per template and per state, not per site.
- Working without JavaScript is a normative requirement, because the interface is
  server-rendered and its core tasks can be completed without script today. Scripting is
  enhancement only.
- Enforcement is process-based: an accessibility item in the PR checklist, a checklist section
  in `CONTRIBUTING.md`, a dedicated issue template, and changelog entries in the existing
  Common Changelog groups.
- Automated accessibility testing in CI is **not** adopted by this decision. It is to be
  evaluated locally first; adopting it later is an operational change, not a change to the
  target.

## Consequences

- A change that breaks a rule in `ACCESSIBILITY.md` is a defect, not a style preference, and
  can be rejected on that basis.
- Known gaps are documented rather than hidden. They are defects with a named owner and a
  place in the changelog when fixed.
- New features carry an accessibility obligation: a widget is not done until its keyboard
  interaction, accessible name, state and no-JS fallback exist.
- Theming is not constrained, only the palettes: any added scheme must meet the same contrast
  and colour-independence rules.
- Deferring localization and CI tooling leaves two open items. Both are recorded in
  `ACCESSIBILITY.md` so they are not mistaken for settled.
- Targets are cheap to state and expensive to miss; reviewing against a named level is slower
  per pull request than not reviewing at all.
- An accessibility defect in a BiblioteQ record — a missing description, an untranslated
  title — cannot be fixed here. It is reported upstream or worked around in presentation, and
  is not counted against this project's conformance beyond the markup rules above.

## Alternatives considered

- **Keep accessibility as per-change judgement with no stated level.** No regression test, no
  way to answer a contributor question, and no basis for saying a known gap is a defect.
- **Aim at AAA.** Rules out common, legitimate design choices for little practical gain in a
  read-only catalog browser, and would be a commitment we could not verify.
- **Align to EN 301 549 / Section 508 as well.** Adds procurement weight but also obligations
  outside the web UI. Not needed for an internal engineering standard; revisit if a deploying
  library asks.
- **Put the full rules in this ADR.** ADRs are immutable records; the rules will change.
  Keeping the rules in `ACCESSIBILITY.md` lets them evolve without superseding the decision.
- **Defer to BiblioteQ's own accessibility position.** Not applicable: this is a separate
  project with its own interface and no shared UI code. The upstream project's choices can
  neither satisfy nor excuse ours.
