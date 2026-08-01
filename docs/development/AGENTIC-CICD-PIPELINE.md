# Agentic CI/CD Pipeline

The end-to-end map of how work flows through this repository — from a raw request to a shipped release — the same way every time, driven by agents and subagents with human touchpoints only at **submission** and **approval**.

- **Entry point:** [`AGENTS.md`](../../AGENTS.md) (repo root) — read it first.
- **Standards (WHAT must be true):** [`.cursor/rules/*.mdc`](../../.cursor/rules).
- **Procedures (HOW work is done):** [`.cursor/skills/*/SKILL.md`](../../.cursor/skills) — indexed in [`.cursor/skills/CATALOG.md`](../../.cursor/skills/CATALOG.md).
- **Hard guardrails:** [`.cursor/hooks.json`](../../.cursor/hooks.json) + `.cursor/hooks/`.

## The golden path

```
intake-feature → start-work → implement-change → functional-validate
  → quality-gate → open-pr → prepare-release → ship-release
  → publish-docs → update-tracker
```

Orchestrated by the `project-manager` skill (`PM:` commands) and, for hands-off delivery, `deliver-autonomously`. Any failed gate routes to `remediate-failure` (bounded 3-attempt loop → SMTP + Slack escalation).

## Lifecycle stages → skill → rule

| Stage | Skill | Enforces |
| --- | --- | --- |
| Capture a request | `intake-feature` | `todo-tracking-09` |
| Branch off develop | `start-work` | `change-control-07` |
| Build it (TDD) | `implement-change` | `architecture-03`, `python-standards-04`, `testing-standards-06` |
| Verify behavior | `functional-validate` | `testing-standards-06` |
| Local CI gate | `quality-gate` | `ci-pipeline-13` |
| Open a PR | `open-pr` | `change-control-07` |
| Prep a release | `prepare-release` | `release-packaging-12` |
| Ship it | `ship-release` | `release-packaging-12` |
| Sync all docs | `publish-docs` | `documentation-08` |
| Keep the register current | `update-tracker` | `todo-tracking-09` |
| Anti-bloat / structure sweep | `codebase-health` | `repo-structure-17` |
| Orchestrate | `project-manager`, `deliver-autonomously` | `agentic-workflow-16` |
| Handle failures | `remediate-failure` | `ci-pipeline-13`, `config-security-11` |

## How to invoke it

- **A single change:** `PM: intake <request>` → approve → `PM: run <ID>` (autonomous) or step through the skills manually.
- **Status / next:** `PM: status`, `PM: next`, `PM: menu`.
- **Just the gate:** run `quality-gate` before any commit/PR/release.
- Prefer invoking the named skill over improvising; dispatch parallel subagents (`explore`/`bugbot`/`security-review`/`ci-investigator`) where work is independent.

## Non-negotiables

- Never commit to `main` directly — `feature/*`/`fix/*` off `develop`; releases merge `develop → main`.
- Gate before "done": version-sync, black, flake8 (+E722), mypy, pytest with the coverage floor.
- Every FEAT ships tests; every BUG ships a failing-first regression test; coverage ratchets upward only.
- Secrets never enter git (gitleaks pre-commit + `guard-git.sh`).
- Canonical version = `src/app.py` `APP_VERSION` (enforced by `scripts/check-version-sync.sh`).
- Pause for approval before destructive/irreversible actions (merge to `main`, tag/release, delete, force git).

## Sources of truth (precedence)

- **Instructions:** user > `AGENTS.md` > `.cursor/rules/*` > skills > defaults.
- **Project state:** [`docs/TODO-ROADMAP.md`](../TODO-ROADMAP.md) (live register) + [`docs/issues/<ID>/`](../issues) (per-item); [`CHANGELOG.md`](../../CHANGELOG.md) (shipped); [`docs/PROJECT-STATUS.md`](../PROJECT-STATUS.md) (snapshot); [`docs/DECISIONS.md`](../DECISIONS.md) (decisions + memlog); [`docs/PLANS-INDEX.md`](../PLANS-INDEX.md) (plan reconciliation). Each has one owner.

## Failure remediation + escalation

`remediate-failure` bounds each issue to 3 assess→fix→re-run attempts, then escalates a structured report (failure / assessment / actions / up to 4 ranked options) via SMTP (`src/utils/notifier.py`) and Slack (agent posts via the MCP and reads the reply to drive a scoped 2nd loop). Nondeterministic failures are quarantined (`@pytest.mark.flaky`), not remediated.

## Portability

Every asset is designed to be seeded into sibling repos (the future `bootstrap-pipeline` / ADF extraction, plan §26/§29–§35). Repo-specific details live in clearly marked blocks (`AGENTS.md` "Repo-specific" section, `REPO-STRUCTURE.md`); the rest is framework-generic.

## Rollout status

Built in milestones (see `.cursor/plans/` + [`docs/PROJECT-STATUS.md`](../PROJECT-STATUS.md)): M0 baseline, M1 foundation, M2 lifecycle skills, M3 orchestration, M4 tracking + docs consolidation. M5 (release hardening) and M6 (ADF extraction) follow.
