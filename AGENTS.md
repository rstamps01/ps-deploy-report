# AGENTS.md — Agentic Pipeline Entry Point

This is the single discoverable entry point for working in this repository the same way every time. It indexes the end-to-end lifecycle, the golden path, where canonical files live, the Pipeline Menu, and the precedence rules. Start here for any non-trivial task.

> **Rollout status (M0–M6 complete; v1.6.0 shipped):** foundation + lifecycle skills (M1/M2), orchestration (M3), tracking/docs (M4), release hardening (M5), and **ADF portability extraction (M6)** — core extracted to [`agentic-dev-framework`](https://github.com/rstamps01/agentic-dev-framework) through v0.3.0 (bootstrap, tiers, adopt-existing pilot on planalyzer, framework-doctor + portfolio). **v1.6.0 was shipped through this pipeline**. Skills are indexed in [`.cursor/skills/CATALOG.md`](.cursor/skills/CATALOG.md). See `docs/PROJECT-STATUS.md` and `docs/development/ADF-EXTRACTION.md`.

## How this fits together

- **Rules** (`.cursor/rules/*.mdc`) — the standards (WHAT must be true). Always applied.
- **Skills** (`.cursor/skills/<name>/SKILL.md`) — the repeatable procedures (HOW work is done).
- **Hooks** (`.cursor/hooks.json`) — hard, deterministic guardrails (non-bypassable).
- **AGENTS.md** (this file) — the index that composes them into one flow.

## Golden path (intake → ship)

```
intake-feature → start-work → implement-change → functional-validate
  → quality-gate → open-pr → prepare-release → ship-release
  → publish-docs → update-tracker
```

Only two required human touchpoints: **submission** and **approval**. The agent + parallel subagents run the rest. Pause for approval before anything destructive/irreversible (merge to `main`, tag/release, delete files, force git).

## Lifecycle stages → skill to invoke

| Stage | Skill (`.cursor/skills/`) | Enforces (rule) |
| --- | --- | --- |
| Capture a request | `intake-feature` | `todo-tracking-09` |
| Start a branch | `start-work` | `change-control-07` |
| Build it (TDD) | `implement-change` | `architecture-03`, `python-standards-04`, `testing-standards-06` |
| Verify behavior | `functional-validate` | `testing-standards-06` |
| Local CI gate | `quality-gate` | `ci-pipeline-13` |
| Open a PR | `open-pr` | `change-control-07` |
| Prep a release | `prepare-release` | `release-packaging-12` |
| Ship it | `ship-release` | `release-packaging-12` |
| Patch a shipped release | `hotfix` | `release-packaging-12`, `testing-standards-06` |
| Recover a bad release | `rollback` | `release-packaging-12` |
| Routine upkeep (deps/comms/migration) | `maintain` | `ci-pipeline-13`, `config-security-11` |
| Sync docs everywhere | `publish-docs` | `documentation-08` |
| Keep the register current | `update-tracker` | `todo-tracking-09` |
| Anti-bloat / structure sweep | `codebase-health` | `repo-structure-17` |
| Failure remediation | `remediate-failure` | `ci-pipeline-13` |

## Canonical file locations

| Purpose | Location |
| --- | --- |
| This entry point | `AGENTS.md` (repo root) |
| Standards | `.cursor/rules/*.mdc` |
| Procedures | `.cursor/skills/<name>/SKILL.md` |
| Project manifest (§30) | `.cursor/pipeline.yml` (commands, gates, artifacts, toggles) |
| Guardrails | `.cursor/hooks.json` + `.cursor/hooks/` |
| Live work register | `docs/TODO-ROADMAP.md` |
| Per-item detail | `docs/issues/<ID>/` (spec/plan/tasks/evidence) |
| Shipped history | `CHANGELOG.md` |
| Status snapshot | `docs/PROJECT-STATUS.md` |
| Plan reconciliation | `docs/PLANS-INDEX.md` |
| Decisions (ADR-lite) | `docs/DECISIONS.md` |
| Release notes | `docs/releases/RELEASE_NOTES_vX.Y.Z.md` |
| Repo structure standard | `docs/development/REPO-STRUCTURE.md` |
| Secrets registry | `docs/development/PIPELINE-SECRETS.md` |
| Canonical version | `src/app.py` `APP_VERSION` (enforced by `scripts/check-version-sync.sh`) |

## Non-negotiables

- **Never commit to `main` directly.** Work on `feature/*` / `fix/*` off `develop`; releases merge `develop → main` (`change-control-07`).
- **Gate before done.** Run `quality-gate` (version-sync, black, flake8 +E722, mypy, pytest with the 60% floor) before opening a PR or releasing.
- **Every FEAT ships tests; every BUG ships a failing-first regression test.** Coverage ratchets upward only.
- **Secrets never enter git.** The gitleaks pre-commit hook + `.cursor/hooks/guard-git.sh` enforce it.
- **Docs move with code.** User-facing changes update `CHANGELOG.md`; version/feature text stays consistent across GitHub, in-app docs, and Confluence (`publish-docs`).

## Precedence (prevents drift)

- **Instructions:** user > `AGENTS.md` > `.cursor/rules/*` > skills > defaults.
- **Project state:** `docs/TODO-ROADMAP.md` (live register) + `docs/issues/<ID>/` (per-item), `CHANGELOG.md` (shipped), `docs/PROJECT-STATUS.md` (snapshot), `docs/PLANS-INDEX.md` (plans). Each has one owner.
- The pipeline governs itself: changes to rules/skills/hooks/`AGENTS.md` go through branch → PR → review → gate like any code.

## Pipeline Menu (invokable options)

Grouped by function. All skills below are live under `.cursor/skills/`.

- **Intake & planning:** `intake-feature`, `brainstorming`, `writing-plans`, `PM: intake <request>`, `PM: status`, `PM: next`.
- **Develop:** `start-work`, `implement-change` (TDD), `using-git-worktrees`, parallel `explore` research.
- **Validate & QA:** `functional-validate`, `quality-gate`, coverage ratchet, `verification-before-completion`.
- **Review & change-control:** `open-pr`, `review-bugbot`, `review-security`, `requesting/receiving-code-review`, branch protection.
- **Release:** `prepare-release`, `ship-release`, `hotfix`, `rollback`, `finishing-a-development-branch`.
- **Docs & consistency:** `publish-docs`, docs-drift audit, `generate-status-report`.
- **Tracking:** `update-tracker`, `triage-issue`, `spec-to-backlog`, plan-inventory reconciliation.
- **Hygiene & health:** `codebase-health`, `maintain` (deps/comms/migration), `continual-learning` (AGENTS.md refresh).
- **Failure handling:** `remediate-failure` (bounded loop) + SMTP/Slack escalation.
- **Orchestration:** `project-manager` (`PM:` commands), `deliver-autonomously`, `orchestrating-subagents`, `dispatching-parallel-agents`, `subagent-driven-development`.

## Leveraged resources

Rules (`architecture-03`, `change-control-07`, `documentation-08`, `todo-tracking-09`, `config-security-11`, `release-packaging-12`, `ci-pipeline-13`, `agentic-workflow-16`, `repo-structure-17`); Superpowers skills (subagent-driven-development, dispatching-parallel-agents, TDD, systematic-debugging, verification-before-completion, code-review, finishing-a-development-branch); subagents (`explore`, `generalPurpose`, `bugbot`, `security-review`, `ci-investigator`, `agents-memory-updater`); MCPs (Atlassian/Confluence, Slack, GitLens). Compose these — do not rebuild them.

<!-- PORTABLE-HEADER-END: everything above is framework-generic; the section below is repo-specific. -->

## Repo-specific

- **Product:** VAST As-Built Report Generator — a Flask app that connects to a VAST cluster (API + SSH/Teleport/Tech-Port), extracts configuration, and renders PDF/JSON as-built reports plus advanced post-install validation workflows.
- **Layers (`architecture-03`):** `api_handler` → `data_extractor` → `report_builder`; `health_checker` and `oneshot_runner` orchestrate; workflows under `src/workflows/`.
- **Run tests:** `python3 -m pytest tests/ --ignore=tests/test_ui.py --ignore=tests/test_integration.py` (add `--no-cov` for a subset). UI tests need Playwright; some `test_oneshot_runner` cases require CI-like fast connection refusal (see `docs/PROJECT-STATUS.md`).
- **Release build:** tag `vX.Y.Z` → `.github/workflows/build-release.yml` builds the macOS `.dmg` + Windows `.zip` from that tagged commit.
- **Tracking home:** `docs/TODO-ROADMAP.md`; Confluence page `6664028496` is the external project home (via Atlassian MCP).
