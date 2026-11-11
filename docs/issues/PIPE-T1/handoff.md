# PIPE-T1 handoff (2026-11-10, 12:40 PT)

**Update 2026-11-10, 15:00 PT:** #39 and #44 are merged to `develop` (`3c82bf6`, `1b61fd3`). Next agent actions 1 and 2 are done: PIPE-T1 is archived and the KPI re-measure is tracked as PIPE-T4 (due 2026-11-24). Owner actions are all resolved (see below). Next: action 3 at the v1.6.3 release, action 4 on 2026-11-24, and FR-16 (action 5) now.

Continue from this file. Code and git outrank it. Spec, baseline and quality tripwires: [`spec.md`](spec.md). Project state: [`../../BRIEF.md`](../../BRIEF.md).

## State at handoff

- **Branch:** `chore/token-efficiency` (pushed), cut from `docs/v1.6.2-shipped`.
- **PR:** [#44 chore: token-efficiency workflow (PIPE-T1)](https://github.com/rstamps01/ps-deploy-report/pull/44) targets `develop`. CI is all green: quality-gate, unit-tests 3.11/3.12, integration, UI, build-smoke mac/win, qa-cross-os ×3, todo-list-check.
- **Depends on:** [#39 docs(docs): record v1.6.2 as shipped](https://github.com/rstamps01/ps-deploy-report/pull/39), which now also carries commit `82f7677` (FR-16 logged as a v1.6.3 blocker). Merge #39 first; #44's diff then shrinks to its own commits.
- **Commits on #44:**
  - `a35537e` rules and `AGENTS.md`
  - `b09a233` archives, `BRIEF.md`, `DECISIONS.md`, PIPE-T1 tracking
  - `e381b29` pytest defaults, `quality-gate.sh`, CI JUnit summaries, black hook, `context-pack.py`
  - `f17dfd5` model tiers, budgets, skills
  - plus the handoff commit that adds this file
- **Local gate:** `bash scripts/quality-gate.sh` passes all steps; 2,047 tests; 73.3% coverage (floor 60%).
- **Roadmap:** PIPE-T1 is In progress (In review once #44 is approved). Follow-ups PIPE-T2 (optional pytest-xdist) and PIPE-T3 (split large modules) are Planned.

## What changed

| Area | Outcome |
| --- | --- |
| Always-on context | About 7 KB (was about 45 KB): `AGENTS.md`, `change-control-07` and `config-security-11` only |
| State files | `CHANGELOG.md` 30 KB (was 187 KB), `TODO-ROADMAP.md` 39 KB (was 70 KB), `docs/BRIEF.md` 1.6 KB |
| Tests | Plain pytest runs without coverage; floor enforced by `scripts/quality-gate.sh`, `pipeline.yml` `test_cov` and both workflows |
| CI | JUnit failure summary per job; duplicate health-check and advanced-ops jobs removed |
| Hooks (repo) | `afterFileEdit` runs black on edited `src/` and `tests/` Python files |
| Skills | `project-manager` pre-flight; `implement-change` targeted tests, one review, hub-and-worker; changelog fragments assembled at release; `publish-docs` once per release |
| User level | `~/.cursor/hooks.json` (`sessionStart` brief, `preCompact` handoff nudge, MCP size log), personal-store `skills/handoff`. The skills dedupe was reverted: other projects (Planalyzer) load skills from `~/.cursor/skills`, so all six stay there. |
| Budget report | Five interventions logged in `~/vast-repos/cursor-budget-report/config/interventions.yml` (uncommitted, alongside the owner's own uncommitted changes) |

## Owner actions (decided 2026-11-10, 18:00 PT)

1. **Merge #39 and #44.** Done (`3c82bf6`, `1b61fd3`); tracker close-out in #45 (`3090153`).
2. **Baseline (`make report`).** Owned by the cursor-budget-report project, including its uncommitted `config/interventions.yml`.
3. **Rotate the exposed MCP keys.** Done by the owner.
4. **Turn off unused MCP servers and plugins.** Declined: they stay available. MCP tool schemas already load on demand (each chat carries only the server and tool names, about 2 KB for the four servers in question), and plugin skills add one description line each until used. The remaining always-on plugin cost is the Superpowers `sessionStart` injection (about 3.4 KB).
5. **Add the three User Rule lines.** Declined. They repeat what `AGENTS.md` already says for this repo and would wrongly constrain other projects, which have no `docs/BRIEF.md`, context-pack script or `quality-gate.sh`.
6. **`generating-orion-bugs` copies.** No action. Cursor mirrors the personal store into `~/.cursor/skills` on its own schedule. The store copy is the newer superset, and it is the one orion-generator vendors.
7. **`rtk`.** Declined: it rewrites agent shell commands and filters their output, which can hide failure detail, change output that pipes parse, and stop command-text guards such as `guard-git.sh` from matching.

## Next agent actions

1. `gh pr view 44 --json state,mergeable,reviewDecision` and `gh pr view 39 --json state`. After #39 merges, rebase or update #44 if GitHub reports conflicts.
2. After #44 merges: set PIPE-T1 to Done in `docs/TODO-ROADMAP.md` (move the row to `ROADMAP-ARCHIVE.md`), refresh `docs/BRIEF.md`, and append a memlog line to `docs/DECISIONS.md`.
3. On the first `prepare-release` (v1.6.3), fold `docs/issues/PIPE-T1/changelog.md` into `CHANGELOG.md`.
4. Two weeks after merge: run `make report` and compare against the KPI and tripwire tables in [`spec.md`](spec.md). If a tripwire worsens by more than 10%, revert the latest intervention.
5. Product work resumes with **FR-16** (v1.6.3 P0 blocker): `python3 scripts/context-pack.py FR-16`, then `implement-change`.

## User Rule additions

```text
- Start from docs/BRIEF.md. Grep first or read with offset/limit; never read whole changelogs, roadmaps or decision logs.
- Plans with more than 3 independent to-dos: run each as a subagent with the brief, the to-do and the file list; keep this chat for integration, review and the final gate.
- While coding run targeted tests only; run the full gate once before a PR; read CI failures with `gh run view --log-failed`.
```

## Thread-length policy (applied from this handoff on)

Hand off at the first clean boundary (after a commit, PR or green gate) once **any** of these is true:

- context is at about 120K tokens or more
- 40 user turns
- about 600 KB of transcript
- any compaction
- a new workstream starts

Before handing off: update this file (or the workstream's own `docs/issues/<ID>/handoff.md`) and `docs/BRIEF.md`, commit, then give the one-line starter prompt.
