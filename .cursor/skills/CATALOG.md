# Capabilities Catalog

Routing index of every repo-local skill under `.cursor/skills/`. `AGENTS.md` and the PM orchestrator use this to pick the right skill per task. This file is a catalog, not a skill (no `SKILL.md`), so the conformance check ignores it.

## Lifecycle skills (golden path)

| Skill | Invoke when | Stage | Enforces |
| --- | --- | --- | --- |
| [`intake-feature`](intake-feature/SKILL.md) | A new request/bug/RFE needs to enter the pipeline | Capture | `todo-tracking-09` |
| [`start-work`](start-work/SKILL.md) | An approved item is ready to build | Branch | `change-control-07` |
| [`implement-change`](implement-change/SKILL.md) | Writing/modifying code on a branch | Build (TDD) | `architecture-03`, `python-standards-04`, `testing-standards-06` |
| [`functional-validate`](functional-validate/SKILL.md) | A UI/behavior/report change needs end-to-end proof | Validate | `testing-standards-06` |
| [`quality-gate`](quality-gate/SKILL.md) | Before commit / PR / release | Gate | `ci-pipeline-13` |
| [`open-pr`](open-pr/SKILL.md) | Change is green and ready for review | Review | `change-control-07` |
| [`prepare-release`](prepare-release/SKILL.md) | `develop` is ready to become a release | Release prep | `release-packaging-12` |
| [`ship-release`](ship-release/SKILL.md) | A prepared release is approved to ship | Release | `release-packaging-12` |
| [`publish-docs`](publish-docs/SKILL.md) | Docs may drift across GitHub/in-app/Confluence | Docs | `documentation-08` |
| [`update-tracker`](update-tracker/SKILL.md) | A work item changes state; session end | Tracking | `todo-tracking-09` |
| [`codebase-health`](codebase-health/SKILL.md) | Periodic anti-bloat / structure sweep | Hygiene | `repo-structure-17`, `architecture-03` |

## Planned (later milestones)

- `remediate-failure` (M3) — bounded assess→fix→re-run loop + SMTP/Slack escalation.
- `project-manager` / `PM:` commands (M3) — cross-project orchestrator (global skill).
- `hotfix` / rollback (M5); `bootstrap-pipeline`, `new-project`, `adopt-existing`, `update-framework`, `framework-doctor` (M6/ADF).

## Skill-authoring standard

- **Location:** `.cursor/skills/<name>/SKILL.md`; deep reference content in `<name>/references/` (kept one level deep).
- **Frontmatter (required):** `name` (lowercase/hyphen/digit, matches the directory, ≤64 chars) and `description` (third person; WHAT + WHEN; ≤1024 chars). Lifecycle skills set `disable-model-invocation: true` (invoked explicitly by name / PM / menu).
- **Body:** ≤500 lines, concise; at least one `##` section; end with a **Completion checklist**. State which rules/subagents/MCPs the skill leverages. Keep repo-specific paths in a clearly marked block for portability.
- **Conformance:** `scripts/check-skill-conformance.py` validates the above (credential-free) and runs in CI. New skills are added to this catalog.
