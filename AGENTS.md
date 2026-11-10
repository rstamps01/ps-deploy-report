# AGENTS.md — Agentic Pipeline Entry Point

Single entry point for working in this repo. **Current state: read `docs/BRIEF.md` first.** Rules (`.cursor/rules/*.mdc`) are the standards, skills (`.cursor/skills/<name>/SKILL.md`, indexed in [`CATALOG.md`](.cursor/skills/CATALOG.md)) are the procedures, hooks (`.cursor/hooks.json`) are hard guardrails, and `.cursor/pipeline.yml` holds commands, gates, model tiers and budgets.

## Golden path

`intake-feature → start-work → implement-change → functional-validate → quality-gate → open-pr → prepare-release → ship-release → publish-docs → update-tracker`. Also: `hotfix`, `rollback`, `maintain`, `codebase-health`, `remediate-failure`, `project-manager` (`PM:` commands), `deliver-autonomously`. Human touchpoints: submission and approval.

## Non-negotiables

- Never commit to `main`; branch `feature/*`, `fix/*` or `chore/*` off `develop`.
- Pause for approval before merging to `main`, tagging/releasing, deleting files, or force/destructive git.
- CI and the `build-release.yml` gates decide pass/fail; the coverage floor only ratchets up.
- Every FEAT ships tests; every BUG ships a failing-first regression test.
- Secrets never enter git (gitleaks pre-commit + `.cursor/hooks/guard-git.sh`).
- Canonical version is `src/app.py` `APP_VERSION` (`scripts/check-version-sync.sh`).

## Read budget (token efficiency)

- Start from `docs/BRIEF.md` (under 2.5 KB). Grep, or read with offset/limit, for `docs/TODO-ROADMAP.md`, `docs/DECISIONS.md`, `README.md` and any `src/` module over 1,000 lines (`report_builder.py`, `app.py`, `health_checker.py`, `api_handler.py`).
- Never read `CHANGELOG.md` whole. Per-item changes go in `docs/issues/<ID>/changelog.md` and are assembled at release.
- Product and design reference (`docs/confluence/`) is on demand via `design-guidelines-01`; read single files or sections.
- Confluence MCP: fetch `detail: "outline"` first, then full bodies only for pages being edited.
- Logs and large outputs stay on disk: write them to `test_output/` and read the summary or the failing tail.

## Working efficiently

- **Tests:** while coding, run only targeted tests (`pytest tests/test_<module>.py -x --lf`). The full suite runs once via `bash scripts/quality-gate.sh` before a PR or tag, and CI runs it on every push. Read CI failures with `gh run view --log-failed` or the job step summary.
- **Plans with more than 3 to-dos:** build a context pack (`python3 scripts/context-pack.py <ID>`), then run each to-do as a subagent on the fast model tier with the brief, the to-do and the file list. The parent chat integrates, reviews and runs the final gate. Keep tightly coupled edits in the parent.
- **Group work** by code area before high-token stages (see `project-manager` pre-flight).
- **Sessions:** keep one model per chat (switching rewrites the prompt cache). After a compaction or a task switch, run `/handoff` and continue in a new chat.
- **Superpowers skills:** use `brainstorming` only for new features or behavior changes. Questions, docs, refreshes, runbook runs, and one- or two-file fixes skip the mandatory skill reads.

## Canonical files

| Purpose | Location |
| --- | --- |
| Current-state brief | `docs/BRIEF.md` |
| Live register / archive | `docs/TODO-ROADMAP.md` / `docs/ROADMAP-ARCHIVE.md` |
| Per-item detail | `docs/issues/<ID>/` (spec, plan, tasks, context, changelog, evidence) |
| Shipped history | `CHANGELOG.md` (recent) / `docs/CHANGELOG-ARCHIVE.md` |
| Status, plans, decisions | `docs/PROJECT-STATUS.md`, `docs/PLANS-INDEX.md`, `docs/DECISIONS.md` |
| Release notes | `docs/releases/RELEASE_NOTES_vX.Y.Z.md` |
| Structure, secrets, routes | `docs/development/REPO-STRUCTURE.md`, `PIPELINE-SECRETS.md`, `WEB-ROUTES.md` |

## Precedence

Instructions: user > `AGENTS.md` > `.cursor/rules/*` > skills > defaults. Code and git outrank `docs/BRIEF.md`. Changes to rules, skills, hooks and this file go through branch → PR → review → gate.

<!-- PORTABLE-HEADER-END: everything above is framework-generic; the section below is repo-specific. -->

## Repo-specific

- **Product:** asbuilt-reporter — a Flask app that connects to a VAST cluster (API + SSH/Teleport/Tech-Port), extracts configuration, and renders PDF/JSON as-built reports plus post-install validation workflows.
- **Layers (`architecture-03`):** `api_handler` → `data_extractor` → `report_builder`; `health_checker` and `oneshot_runner` orchestrate; workflows under `src/workflows/`.
- **Release build:** tag `vX.Y.Z` → `.github/workflows/build-release.yml` builds the macOS `.dmg` (arm64, x64) and Windows `.zip` from the tagged commit.
- **Tracking home:** `docs/TODO-ROADMAP.md`; Confluence page `6664028496` is the external project home (Atlassian MCP).
