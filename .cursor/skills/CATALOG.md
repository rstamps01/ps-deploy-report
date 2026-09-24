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
| [`hotfix`](hotfix/SKILL.md) | A shipped release has an urgent user-affecting defect | Patch release | `release-packaging-12`, `testing-standards-06` |
| [`rollback`](rollback/SKILL.md) | A just-shipped release is broken; restore last good | Release recovery | `release-packaging-12` |
| [`maintain`](maintain/SKILL.md) | Dependabot triage, success comms, config migration | Maintenance | `ci-pipeline-13`, `config-security-11`, `documentation-08` |
| [`publish-docs`](publish-docs/SKILL.md) | Docs may drift across GitHub/in-app/Confluence | Docs | `documentation-08` |
| [`update-tracker`](update-tracker/SKILL.md) | A work item changes state; session end | Tracking | `todo-tracking-09` |
| [`codebase-health`](codebase-health/SKILL.md) | Periodic anti-bloat / structure sweep | Hygiene | `repo-structure-17`, `architecture-03` |

## Orchestration & failure handling

| Skill | Invoke when | Role | Enforces |
| --- | --- | --- | --- |
| [`project-manager`](project-manager/SKILL.md) | Any `PM:` command; drive multi-item work end-to-end | Orchestrator | `agentic-workflow-16`, `todo-tracking-09` |
| [`deliver-autonomously`](deliver-autonomously/SKILL.md) | An approved item is cleared for hands-off delivery | Delivery loop | all pipeline rules |
| [`remediate-failure`](remediate-failure/SKILL.md) | A gate fails and needs bounded auto-remediation + escalation | Failure handling | `ci-pipeline-13`, `config-security-11` |

## Project manifest

- [`.cursor/pipeline.yml`](../pipeline.yml) — the project capability profile (§30): commands, version locations, coverage floor, release artifacts, doc surfaces, notification channels, tracking files, autonomy budgets. Skills read it so they stay stack-agnostic; keep repo-specific commands there, not hardcoded in skills.
- **Adapter:** [`scripts/pipeline_manifest.py`](../../scripts/pipeline_manifest.py) resolves the manifest for skills/CI — `get <name>` (one command), `gate` (blocking-gate commands in order), `show`, `validate --strict` (CI-enforced). A non-Python project ships its own `commands:`/`artifacts:` under the same schema and every skill keeps working.

## Planned (later milestones)

- M6/ADF portability: `bootstrap-pipeline`, `new-project`, `adopt-existing`, `update-framework`, `framework-doctor`.

## Skill-authoring standard

- **Location:** `.cursor/skills/<name>/SKILL.md`; deep reference content in `<name>/references/` (kept one level deep).
- **Frontmatter (required):** `name` (lowercase/hyphen/digit, matches the directory, ≤64 chars) and `description` (third person; WHAT + WHEN; ≤1024 chars). Lifecycle skills set `disable-model-invocation: true` (invoked explicitly by name / PM / menu).
- **Body:** ≤500 lines, concise; at least one `##` section; end with a **Completion checklist**. State which rules/subagents/MCPs the skill leverages. Keep repo-specific paths in a clearly marked block for portability.
- **Conformance:** `scripts/check-skill-conformance.py` validates the above (credential-free) and runs in CI. New skills are added to this catalog.
