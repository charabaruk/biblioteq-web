# ADR-0000: Record architecture decisions

- Status: Accepted
- Date: 2026-10-16

## Context

This project is intended for open-source release and will be maintained by people who were not present for
its early design. Decisions and their reasons need to survive beyond commit messages and chat history.

## Decision

- Architectural decisions are recorded as ADRs in `docs/arch/decisions/`, numbered sequentially
  (`NNNN-short-title.md`) with the sections Status, Date, Context, Decision and Consequences.
- Architecture documentation (overviews, diagrams, query approach) lives in `docs/arch/`.
- An ADR is committed together with the change it justifies. Accepted ADRs are not rewritten; a new ADR
  supersedes an old one.
- Commits follow Conventional Commits, one per rational unit of change.

## Consequences

- Reviewers can find the reasoning behind structural choices in one place.
- Contributors must add or update an ADR when changing an architectural decision.
