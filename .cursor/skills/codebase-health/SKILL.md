---
name: codebase-health
description: Run a periodic anti-bloat and structure sweep — detect orphan/unreferenced files, dead code, duplication, oversized modules, module-boundary violations, and content stored in inconsistent locations — and propose archival/consolidation with a diff for approval. Use on a cadence, before a release, or when the working tree feels cluttered.
disable-model-invocation: true
---

# codebase-health

Prevents bloat and structural drift over time. Produces a prioritized refactor/cleanup list, not silent deletions. Enforces `repo-structure-17` and `architecture-03`.

## Steps

1. **Dispatch parallel scan subagents** (`explore`/`generalPurpose`), each on one dimension:
   - **Orphans:** files not referenced by imports, templates, packaging spec, docs index, or tests.
   - **Dead code:** unused functions/classes/branches.
   - **Duplication:** near-duplicate modules or copy-pasted logic; same content in different locations (e.g. images under two dirs).
   - **Complexity/size:** oversized modules (flag > ~100 KB or high cyclomatic complexity) as refactor candidates.
   - **Boundary violations:** imports that break `architecture-03` layering.
   - **Structure drift:** files outside `repo-structure-17` (root clutter, release notes outside `docs/releases/`, generated artifacts staged).
2. **Run a code-review pass** (`bugbot` + `security-review`) for correctness/security-relevant findings.
3. **Consolidate findings** into a prioritized list; for each item propose: keep / archive to `.archive/` (gitignored) / consolidate / refactor — with a concrete diff or move plan.
4. **Present for approval.** Deletions/moves are surfaced as a reviewable batch; nothing is removed without sign-off (record approvals in `docs/DECISIONS.md`).
5. **File the work.** Add approved cleanups to `docs/TODO-ROADMAP.md` as small `refactor(...)`/`chore(...)` items — ship incrementally, never batch indefinitely.

## Subagents

`explore`, `generalPurpose` (parallel, partitioned by dimension), `bugbot`, `security-review`.

## Leverages

Rules: `repo-structure-17`, `architecture-03`. Skills: `dispatching-parallel-agents`, `review-bugbot`, `review-security`. Feeds: `update-tracker`.

## Completion checklist

- [ ] All six dimensions scanned (orphans/dead/dup/size/boundary/structure)
- [ ] Prioritized findings list produced with per-item action + diff
- [ ] Deletions/moves approved and recorded before applying
- [ ] Approved cleanups filed as tracked refactor/chore items
