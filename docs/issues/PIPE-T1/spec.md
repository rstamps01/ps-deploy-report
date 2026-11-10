# PIPE-T1 — Token-efficiency workflow

**Type:** CHG (pipeline) · **Priority:** High · **Status:** In progress (branch `chore/token-efficiency`) · **Approved:** owner, 2026-11-10 (plan *Token efficiency workflow*)

## Why

Billing data for this project (Sep 10 – Oct 13, 2026 pull in `~/vast-repos/cursor-budget-report`): 1,552 requests, $2,734 charged ($667 Cursor token fee), 2.99B input-side tokens, of which 2.77B were cache re-reads. One chat (`920c7c9d`) used 1.84B cache reads and $2,195. Average context per step in the large chats was about 343K tokens.

Root causes found in transcripts and config:

- Long chats: context grows on every step and is re-read each time.
- Test output: 918 pytest runs (248 full-suite). `pyproject.toml` `addopts` forced a coverage table on every run, and a targeted run "failed" the coverage floor.
- Whole-file reads: `TODO-ROADMAP.md` (70 KB) was read 133 times and `CHANGELOG.md` (187 KB) 106 times.
- Always-on context: 11 rules plus `AGENTS.md`, about 45 KB per step.

The always-on `@`-references to the 25 local Confluence docs (330 KB) were *not* expanded into prompts. A fresh chat's first request writes only 23K–53K tokens to the cache. So that fix is small, contrary to the Confluence Gap Analysis estimate.

## What changed

| Area | Change |
| --- | --- |
| Always-on context | Only `AGENTS.md` (about 4.8 KB), `change-control-07` and `config-security-11` remain always-applied (about 7 KB total, from about 45 KB). `architecture-03`, `ci-pipeline-13`, `documentation-08` and `release-packaging-12` are glob-scoped. `agentic-workflow-16`, `todo-tracking-09`, `repo-structure-17` and `design-guidelines-01` are agent-requested. `ai-develop-guidelines-02` is deleted (it duplicated rules 03–11). The route list moved to `docs/development/WEB-ROUTES.md`. |
| State files | CHANGELOG v1.5.x moved to `docs/CHANGELOG-ARCHIVE.md` (187 KB to 30 KB). 83 Done roadmap rows moved to `ROADMAP-ARCHIVE.md` (70 KB to 39 KB). `DECISIONS.md` has a reading guide. `docs/BRIEF.md` (under 2.5 KB) is the start-of-chat state. |
| Tests | `addopts` is `-q -rfE --timeout=300`, with no coverage by default. The coverage floor is explicit in `scripts/quality-gate.sh`, `pipeline.yml` `test_cov`, `ci.yml` and `build-release.yml`. The session-start full pytest run was removed. `implement-change` runs targeted tests and one review. |
| Gate | `scripts/quality-gate.sh`: one call, logs to `test_output/quality-gate/`, one line per step plus the failing tail. |
| CI | The duplicate `health-check-tests` and `advanced-ops-tests` jobs were removed (both already run in `unit-tests`; neither is a required check). JUnit XML plus a `GITHUB_STEP_SUMMARY` failure list (`scripts/junit_summary.py`), with no `-v` in the logs. |
| Hooks | `afterFileEdit` runs `black` on edited `src/` and `tests/` Python files (`.cursor/hooks/format-python.sh`). |
| Orchestration | `pipeline.yml` `models:` tiers and numeric `autonomy` budgets. `project-manager` pre-flight covers batching, area grouping, context packs and CI-first verification. `scripts/context-pack.py`. Changelog fragments (`docs/issues/<ID>/changelog.md`) are assembled by `prepare-release`. `publish-docs` runs once per release and reads Confluence outline-first. |
| User level | User Rule, `~/.cursor/hooks.json` (`sessionStart` brief, `preCompact` nudge, MCP output-size log), `/handoff` skill, plugin and MCP cleanup. These live outside this repo; see the PR description. |

Unchanged: CI and `build-release` blocking gates, the 60% coverage floor (upward-only), the gitleaks pre-commit hook, `guard-git.sh`, and the approval pauses.

## Baseline and targets (re-measure two weeks after merge with `make report` in cursor-budget-report)

| KPI | Baseline | Target |
| --- | ---: | ---: |
| Always-on context per step | about 45 KB | under 15 KB (now about 7 KB) |
| Average context per step (large chats) | about 343K tokens | under 120K |
| Spend share of the top chat | 80% | under 30% |
| Full-suite pytest runs per merged PR | 248 full-suite runs across all transcripts (per-PR rate set at the pre-merge `make report`) | 2 or fewer |
| Cost per merged PR (`kpis.py`) | $39.71 (Jul 19 – Sep 10) | down 40% or more |

The 2026-11-10 refresh failed with `not_authenticated` (the Cursor web session token in `state.vscdb` has expired). Sign in to cursor.com, then run `make report` to record the pre-merge row.

## Quality tripwires (equal or better outcomes)

Track these per release next to the cost KPIs: CI first-pass rate, gate-failure loops per item, change-failure rate (hotfixes and rollbacks), field-reported bugs per release, and review findings per PR. If any one worsens by more than 10% against the pre-merge baseline, revert the most recent intervention logged in `cursor-budget-report/config/interventions.yml` and re-measure.

## Follow-ups

PIPE-T2 (optional `pytest-xdist`) and PIPE-T3 (split the largest modules) in `docs/TODO-ROADMAP.md`.
