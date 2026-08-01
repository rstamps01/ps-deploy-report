---
name: publish-docs
description: Keep documentation consistent across GitHub (README/CHANGELOG/docs), the in-app documentation section, and Confluence page 6664028496 via the Atlassian MCP, drafting then pausing for confirmation before publishing externally. Use when docs may drift from the product, and during prepare-release.
disable-model-invocation: true
---

# publish-docs

Multi-surface documentation consistency. Ensures version, feature list, and operational-workflow text agree everywhere. Enforces `documentation-08`.

## Surfaces

1. **GitHub** — `README.md`, `CHANGELOG.md`, `docs/` (deployment/development/api).
2. **In-app** — the documentation section rendered from `frontend/templates/` (docs modal/tab content) and any doc guides bundled in `packaging/vast-reporter.spec`.
3. **Confluence** — page `6664028496` via Atlassian MCP (`getConfluencePage` / `updateConfluencePage`).

## Steps

1. **Determine the delta.** What changed (feature, CLI, config key, workflow, version)? List every surface it touches.
2. **Update GitHub surfaces** directly (in the branch): README usage/badge, CHANGELOG entry, affected `docs/` pages. Confirm `config/config.yaml.template` documents any new config key.
3. **Update in-app docs.** Edit the relevant `frontend/templates/` content so the in-app section matches; if a new guide was added, register it in the docs viewer and the PyInstaller spec.
4. **Draft the Confluence update.** Fetch the current page, prepare the diff (version references, RFE table, feature list). **PAUSE and present the draft for user confirmation** — Confluence is customer/exec-facing; do not publish without approval.
5. **Cross-check.** Verify all three surfaces state the same version, feature set, and workflow. Flag and fix any residual drift.
6. On a successful release, add the Confluence release page + Slack announcement (draft-then-confirm), not only failure escalations.

## Subagents / MCPs

Atlassian MCP (`getConfluencePage`/`updateConfluencePage`, adapted `generate-status-report`); `explore` to find in-app doc content locations.

## Leverages

Rules: `documentation-08`. Skills: `generate-status-report`, `search-company-knowledge`.

## Completion checklist

- [ ] GitHub README/CHANGELOG/docs updated for the delta
- [ ] In-app documentation section matches
- [ ] Confluence draft prepared and confirmed before publishing
- [ ] All three surfaces agree on version/features/workflow
