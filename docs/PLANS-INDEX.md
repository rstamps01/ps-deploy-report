# Plans Index

Reconciliation of the prior Cursor plan files (in the shared `~/.cursor/plans/`) against the actual shipped state of this repository (release tags + `CHANGELOG.md`) — so there is one place that says which plans shipped, which were superseded, and which have genuinely open scope (pipeline §9).

## Method

Each related plan is validated against reality and sorted into one bucket:

- **A. Shipped, frontmatter stale** — work that shipped (confirmed via tags `v1.5.0/1.5.6/1.5.7/1.5.8` + CHANGELOG) but the plan still reads not-started/in-progress → mark Done, archive.
- **B. Superseded / duplicate / empty stub** — replaced by a later plan or empty (0/0) → annotate with the surviving plan; empties/dupes proposed for deletion.
- **C. Mostly shipped, minor tail** — e.g. 17/18 → validate the residual; close if done, else promote the tail into `docs/TODO-ROADMAP.md`.
- **D. Genuinely open** — real remaining scope → present a prioritized list for sign-off, then run through the delivery loop.

> **Guardrail:** plan-file deletions are surfaced as a **reviewable batch for approval** (they live in a shared directory); nothing is deleted without sign-off, and approvals are recorded in [`DECISIONS.md`](DECISIONS.md).

## Status

**Reconciliation in progress (M4).** A background inventory pass is cataloguing all related plans and their reconciled state; the categorized tables and the proposed deletion/annotation batch will be populated here and presented for approval. Genuinely-open (bucket D) items are promoted into [`docs/TODO-ROADMAP.md`](TODO-ROADMAP.md).

<!-- Buckets A–D tables populated from the reconciliation pass. -->
