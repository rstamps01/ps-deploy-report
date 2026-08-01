---
name: update-framework
description: Merge a newer Agentic Dev Framework (ADF) core version into an already-adopted project, preserving all local overrides and presenting a diff-for-approval before writing. Use when a project on ADF core vX wants to pull the improvements in core vY without clobbering its customizations.
disable-model-invocation: true
---

# update-framework

Propagates ADF core improvements into an adopting repo **non-destructively**. The
project's `.cursor/pipeline.yml`, local skills, and product code are the source of
truth for anything customized; the framework only updates untouched core assets and
proposes the rest as a reviewable diff.

## Preconditions

- The target repo already adopted ADF (has `.cursor/pipeline.yml` with an `adf_version`).
- Working tree is clean (or changes are committed) so the diff is legible.
- You know the target ADF version (a tag/branch of `agentic-dev-framework`).

## Steps

1. **Read both versions.** Note the repo's current `adf_version` and the target core
   version. Skim the ADF `CHANGELOG.md` between them for breaking changes.
2. **Classify each core asset** (skills, hooks, `pipeline_manifest.py`,
   `check-skill-conformance.py`):
   - **Unchanged locally** → safe to update in place.
   - **Locally overridden** (project edited it or shadowed it with a same-named local
     skill) → never overwrite; surface the upstream diff for the human to merge.
3. **Compute the diff.** For each asset, show old → new. Group as: *auto-updatable*,
   *needs-manual-merge* (local override), *new* (added in the target core).
4. **Present diff-for-approval.** Summarize the three groups. **Pause for approval**
   before writing anything (autonomy: `pause_before` includes framework updates).
5. **Apply approved changes.** Copy auto-updatable + new core assets into place. Leave
   overridden assets untouched; leave the manifest's project-specific values intact.
6. **Bump `adf_version`** in `.cursor/pipeline.yml` to the target version.
7. **Self-check.** Run `pipeline_manifest.py validate --strict`, the skill-conformance
   check, and the project `quality-gate`. Fix drift before finishing.
8. **Record.** Add a `docs/DECISIONS.md` entry (from vX → vY, what merged, what was
   deferred) and update `CHANGELOG.md` if adopter-visible.

## Guardrails

- Never overwrite a locally overridden asset or the project's manifest values.
- Never delete project files. Additions/updates only, all after approval.
- Precedence holds: user > project overrides > framework core > defaults.

## Completion checklist

- [ ] Current vs target ADF version identified; CHANGELOG delta reviewed
- [ ] Assets classified (auto / manual-merge / new); diff presented and **approved**
- [ ] Approved core assets applied; overrides + manifest values preserved
- [ ] `adf_version` bumped; manifest-validate + skill-conformance + quality-gate green
- [ ] `docs/DECISIONS.md` (and CHANGELOG if adopter-visible) updated
