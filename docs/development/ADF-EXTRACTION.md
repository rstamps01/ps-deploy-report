# Agentic Dev Framework (ADF) — Extraction Spec & Handbook Outline

**Status:** Phase D **executed** (2026-08-01 — brownfield L1 adopt on
[`planalyzer`](https://github.com/rstamps01/planalyzer)). Phase C shipped ADF v0.2.0 (bootstrap
installer + tiers + adoption skills). Phase B extracted the portable core into
[`rstamps01/agentic-dev-framework`](https://github.com/rstamps01/agentic-dev-framework)
(private) at **v0.1.0** — core skills/hooks/adapter/conformance + templates + `HANDBOOK.md`,
dogfooding its own gate. This repo remains the **reference implementation** and ADF's first
adopter. This document defines *what* is portable, *how* the framework and a project instance
separate, and the *phased plan*; Phases C–E (bootstrap/adopt/doctor) remain.

Related: [`AGENTIC-CICD-PIPELINE.md`](AGENTIC-CICD-PIPELINE.md) (end-to-end map),
[`.cursor/pipeline.yml`](../../.cursor/pipeline.yml) (this repo's manifest),
[`scripts/pipeline_manifest.py`](../../scripts/pipeline_manifest.py) (the adapter),
`docs/DECISIONS.md` (rationale log).

---

## 1. Purpose

Extract the reusable "how we ship software with agents" layer built in M0–M5 into a
dedicated **Agentic Dev Framework (ADF)** repo so any project — regardless of stack —
can adopt the same lifecycle (intake → deliver → gate → release → maintain), the same
guardrails, and the same PM orchestration, by supplying a small per-project manifest
instead of re-authoring skills.

**Non-goal:** ADF is not a runtime library the app imports. It is a set of **agent-facing
assets** (skills, rules, hooks, templates, docs) + thin **scripts** (adapter, doctor,
bootstrap). Projects keep their own product code untouched.

## 2. Framework vs project-instance separation

| Layer | Owns | Lives in | Example |
| --- | --- | --- | --- |
| **Framework core** | Stack-agnostic procedures + guardrails + PM brain | ADF repo | `skills/quality-gate`, `skills/prepare-release`, `hooks/guard-git.sh`, rules |
| **Templates** | Files a project starts from, then customizes | ADF repo (`templates/`) | `AGENTS.md`, `.cursor/pipeline.yml`, `.github/*`, `.env.example`, `REPO-STRUCTURE.md` |
| **Project instance** | Repo-specific commands, versions, artifacts, product code | The adopting repo | `.cursor/pipeline.yml` values, `src/`, `CHANGELOG.md` |

The seam is already proven here: skills read commands from `.cursor/pipeline.yml` via the
adapter, so a skill never hardcodes `pytest`/`flake8`/`build-mac.sh`. Swapping the manifest
(Node/Go/Docker) makes the same skill work unchanged.

## 3. Precedence (drift prevention)

Identical to the in-repo rule (pipeline §25), extended for the framework:

```
user instruction  >  project overrides (.cursor/pipeline.yml + local rules/skills)
                   >  framework core (ADF skills/rules/hooks)
                   >  defaults
```

- A project may **override** any framework skill by placing a same-named skill locally.
- A project **must not** silently diverge on guardrails (branch protection, secrets-never-in-git,
  version-sync); `framework-doctor` flags divergence as a compliance gap.

## 4. Portable-asset inventory

What moves to ADF core, what becomes a template, what stays instance-only. Paths are
current locations in this repo.

| Asset | Disposition | Notes |
| --- | --- | --- |
| `.cursor/skills/*/SKILL.md` (14 lifecycle + orchestration) | **Core** | Already stack-agnostic; commands resolved via manifest |
| `.cursor/skills/CATALOG.md` | **Core** (regenerated per project) | Routing index |
| `.cursor/rules/*.mdc` (architecture, change-control, ci-pipeline, config-security, documentation, todo-tracking, release-packaging, repo-structure, agentic-workflow) | **Core → template** | Generic rules are core; product-specific rule bodies (e.g. VAST layered pipeline) stay instance-only |
| `.cursor/hooks.json` + `.cursor/hooks/guard-git.sh` | **Core** | Guardrails are universal |
| `scripts/pipeline_manifest.py` | **Core** | The adapter; unchanged across stacks |
| `scripts/check-skill-conformance.py` | **Core** | Validates skill structure |
| `scripts/check-version-sync.sh` | **Template** | Logic is generic; version locations differ per project |
| `src/utils/notifier.py` + `tests/test_notifier.py` | **Core (optional, L3)** | Escalation; stack-agnostic Python helper shipped as an ADF tool |
| `.github/workflows/ci.yml`, `build-release.yml`, `security.yml` | **Template** | Generic job shapes; commands/artifacts come from the manifest |
| `.github/` PR/issue templates, `CODEOWNERS`, `dependabot.yml`, `labels.yml` | **Template** | Seed values customized on adopt |
| `AGENTS.md` | **Template** | Entry point; project fills the specifics |
| `.cursor/pipeline.yml` | **Template** | The per-project manifest (values differ; schema is core) |
| `docs/development/REPO-STRUCTURE.md` | **Template** | Structure standard |
| `docs/{DECISIONS,TODO-ROADMAP,PIPELINE-METRICS,PLANS-INDEX,PROJECT-STATUS}.md` | **Template (empty scaffolds)** | Tracking surfaces |
| `docs/development/PIPELINE-SECRETS.md` | **Template** | Secrets registry skeleton |
| `~/.cursor/pm/projects.md` | **Core (global)** | Cross-project PM registry (already outside the repo) |
| `src/`, product tests, `packaging/`, `frontend/`, product docs | **Instance-only** | Never leaves this repo |

## 5. Adoption tiers (L1 → L3)

Declared per project as `adoption_tier` in the manifest; the installer targets a tier so
brownfield adoption is incremental.

| Tier | Adds | For |
| --- | --- | --- |
| **L1** | Gates (`quality-gate`) + release (`prepare-release`/`ship-release`) + hooks + version-sync | Any repo wanting safe, repeatable releases |
| **L2** | + PM/tracking (`update-tracker`, roadmap/state machine), docs consistency (`publish-docs`), codebase-health | Teams wanting project awareness + doc discipline |
| **L3** | + autonomy (`deliver-autonomously`), remediation + escalation (`remediate-failure`, notifier), metrics | Hands-off delivery with human escalation |

This repo is **L3**.

## 6. ADF versioning & update propagation

- ADF gets its **own** semver + `CHANGELOG.md` and **dogfoods its own pipeline** (ADF
  changes go through ADF's `quality-gate`/release).
- Each adopting project records the adopted core version in `adf_version` (manifest).
- `update-framework` skill: merges a newer core into an adopted project, **preserving local
  overrides**, presenting a **diff-for-approval** before writing. Never clobbers instance files.

## 7. Adoption flows

- **`new-project`** (greenfield): scaffold a repo at a chosen tier + stack from templates;
  fill the manifest; run the self-check.
- **`adopt-existing`** (brownfield): **idempotent, non-destructive, dry-run-first** migration
  that reconciles an existing repo's CI/docs/structure with ADF, reporting a plan before any
  change. Pilots on **VAST Plan Analyzer**.
- **`bootstrap-pipeline`**: the installer script/skill that copies portable assets into a
  target repo, parameterizes paths, and self-checks gates + version-sync.

## 8. Conformance doctor & portfolio PM

- **`framework-doctor`**: scores a repo's compliance (gates present? hooks installed?
  manifest valid? version-sync wired? secrets clean?) and emits a remediation list.
  Reuses `pipeline_manifest.py validate --strict` + `check-skill-conformance.py`.
- **Portfolio PM**: extends `~/.cursor/pm/projects.md` into a dashboard — per-project tier,
  compliance score, adopted ADF version, and a cross-project metrics roll-up
  (from each repo's `PIPELINE-METRICS.md`).

## 9. Extraction plan (phased)

Maps to the plan items in `agentic_cicd_pipeline_2eb2e257`.

| Phase | Item(s) | Deliverable | Gate to proceed |
| --- | --- | --- | --- |
| **A. Reference impl** | *(done, M0–M5)* | This repo runs the full pipeline; adapter proves the manifest seam | ✅ v1.6.0 shipped through the pipeline |
| **B. Extract core** | ✅ `adf-core-repo`, `framework-versioning`, `methodology-handbook` | [`agentic-dev-framework`](https://github.com/rstamps01/agentic-dev-framework) v0.1.0: 18 core skills (+`update-framework`), hooks, location-independent adapter, conformance check, `templates/`, `HANDBOOK.md`, own semver/CHANGELOG + dogfood CI | ✅ ADF self-gate green (format/lint/conformance/manifest-validate/tests) |
| **C. Bootstrap + tiers** | ✅ `bootstrap-installer`, `maturity-tiers`, `adoption-flows` | ADF v0.2.0: `scripts/adf_bootstrap.py` (idempotent, non-destructive, dry-run, new/adopt, self-check), `core/tiers.yml` (L1/L2/L3), `new-project` + `adopt-existing` skills, 12 installer tests | ✅ scratch-target install validated (44 files, idempotent re-run, self-check green) |
| **D. Pilot brownfield** | ✅ `rollout-sequence` (pilot) | L1 adopt-existing on **[`planalyzer`](https://github.com/rstamps01/planalyzer)** (Node/Next): dry-run → apply (33 create / 1 skip), Node manifest, GH Actions alongside GitLab; PR [#1](https://github.com/rstamps01/planalyzer/pull/1) | ✅ no instance files clobbered; validate/conformance/version-sync/lint/typecheck/test green |
| **E. Portfolio rollout** | `conformance-doctor`, `rollout-sequence` | Roll out to all projects + portfolio dashboard | Per-project compliance tracked |

**Done:** Phases A–D. Next is Phase E: `framework-doctor` + portfolio PM across adopters
(this repo + planalyzer).

## 10. HANDBOOK.md outline (to author in Phase B)

1. **Principles** — guardrailed autonomy, evidence-before-done, coverage ratchets upward,
   secrets never in git, docs move with code.
2. **Lifecycle** — intake → start-work → implement → validate → gate → PR → release → publish-docs → maintain.
3. **Roles** — PM (orchestrator), lifecycle skills (workers), doctor (auditor), notifier (escalation).
4. **Invocation & menu** — how to trigger each stage; the Pipeline Menu.
5. **Manifest reference** — every `.cursor/pipeline.yml` key + the adapter CLI.
6. **Adoption guides** — tiers (L1/L2/L3), greenfield (`new-project`), brownfield (`adopt-existing`).
7. **Golden path** — the end-to-end worked example.
8. **Governance** — ADF changes go through ADF's own pipeline; versioning + `update-framework`.

## 11. Open decisions

| Decision | Current call | Revisit when |
| --- | --- | --- |
| ADF repo location | `rstamps01/agentic-dev-framework`, **private** | Phase B kickoff |
| First brownfield pilot | VAST Plan Analyzer | Phase C |
| Notifier as ADF core vs project-local | Core (optional, L3) | Phase B inventory review |
| Rules split (generic core vs product body) | Split at extraction | Phase B |
