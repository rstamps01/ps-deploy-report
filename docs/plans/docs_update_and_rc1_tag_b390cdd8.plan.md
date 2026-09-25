---
name: Docs update and RC1 tag
overview: Update CHANGELOG.md, TODO-ROADMAP.md, README.md, and related documentation to reflect all uncommitted changes since commit 402c895, then commit everything, push, and create the v1.5.0-rc1 tag to trigger the CI build.
todos:
  - id: update-changelog
    content: Add all uncommitted change entries to CHANGELOG.md [Unreleased] section
    status: completed
  - id: update-todo-roadmap
    content: Update docs/TODO-ROADMAP.md statuses, Next Steps, and Last Updated date
    status: completed
  - id: update-readme
    content: "Update README.md: new dependencies, vnetmap mention, test count if changed"
    status: completed
  - id: commit-changes
    content: Stage all relevant files (exclude diagnostics/output/DS_Store) and commit with conventional message
    status: completed
  - id: push-and-tag
    content: Push branch, create annotated v1.5.0-rc1 tag, push tag to trigger CI build
    status: completed
  - id: verify-ci
    content: Verify CI build-release workflow was triggered by the tag push
    status: completed
isProject: false
---

# Documentation Update, Commit, and v1.5.0-rc1 Tag

## Current State

- Branch: `feature/health-check-v2` (tracking `origin/feature/health-check-v2`)
- Last commit: `402c895` — "docs: fix stale content across 5 deployment and operational docs"
- **37 modified files** (all unstaged) + **14 untracked items**
- CHANGELOG.md, README.md, and TODO-ROADMAP.md are at HEAD (no pending edits) — need new content added

## Uncommitted Changes to Document

Analysis of `git diff HEAD` reveals these feature groups since last commit:

**Vnetmap Integration (largest feature)**

- "Run Vnetmap" checkbox on Reporter page + Advanced Config default toggle
- `/api/vnetmap-status` endpoint with hardware change detection (fingerprint comparison across reports)
- Three-source port mapping priority: vnetmap -> external SSH -> static file ([data_extractor.py](src/data_extractor.py))
- VNetMap parser now extracts LLDP neighbor data for switch-to-switch IPL connections ([vnetmap_parser.py](src/vnetmap_parser.py))
- IPL formatting from LLDP neighbors or inference from switch pairs

**SVG Diagram and Landscape Support**

- New deps: `svgwrite>=1.4.0`, `cairosvg>=2.7.0` in [requirements.txt](requirements.txt)
- Landscape `PageTemplate` in [report_builder.py](src/report_builder.py)
- macOS `DYLD_FALLBACK_LIBRARY_PATH` for Homebrew libcairo in [app.py](src/app.py) and [main.py](src/main.py)

**Health Checker Improvements**

- `_resolve_license()`: Multi-field license detection + `licenses/` endpoint fallback ([health_checker.py](src/health_checker.py))
- Call Home check refactored to use `callhomeconfigs/` endpoint (VAST v5.x+)

**Port Mapping and Diagrams**

- Enhanced port mapper: Refactored node classification (hostname, interface prefix, node_type)
- Network diagram: Additional DNode interface patterns (ens3, ens14, enp65s0, enp94s0, enp3s0)
- Rack diagram: U-position fix (top-based -> bottom-based calculation)

**UI and Brand**

- Reporter step badges (3-step workflow replacing 4-step)
- Brand compliance: `col_widths` and `compact` parameters for `create_vast_table()`
- Script runner: `_classify_stderr_line()` for intelligent stderr classification
- Tech Port discovery probe uses port 22 (not 443)

**Tests**

- New `test_port_mapper.py`; updated health_checker, rack_diagram, external_port_mapper, SSH adapter tests

## Phase 1: Update CHANGELOG.md

Add entries under `[Unreleased]` section (insert after existing unreleased entries, before the `[1.5.0]` section at line 88):

- **Added**: Vnetmap integration (Reporter checkbox, `/api/vnetmap-status`, hardware fingerprint detection, LLDP IPL parsing)
- **Added**: SVG diagram dependencies (`svgwrite`, `cairosvg`) and landscape page template
- **Added**: New `test_port_mapper.py` test file
- **Changed**: Port mapping three-source priority system
- **Changed**: Enhanced port mapper node classification refactor
- **Changed**: Brand compliance table `col_widths`/`compact` parameters
- **Changed**: Network diagram DNode interface detection expansion
- **Changed**: Reporter UI simplified to 3 numbered step badges
- **Changed**: Advanced Config "Run Vnetmap" default toggle
- **Fixed**: Rack diagram U-position calculation (bottom-based)
- **Fixed**: Health check license detection via `_resolve_license()` multi-source
- **Fixed**: Health check Call Home using `callhomeconfigs/` endpoint
- **Fixed**: Script runner stderr classification and emit deduplication
- **Fixed**: Tech Port discovery probe (port 22 vs 443)
- **Fixed**: macOS cairosvg library path setup

## Phase 2: Update docs/TODO-ROADMAP.md

- Mark DOC-15 (CHANGELOG verify completeness) as Done
- Add any new planned items arising from the vnetmap integration work
- Update "Next steps" section to reflect current state
- Update "Last updated" date

## Phase 3: Update README.md

- Add `svgwrite` and `cairosvg` to the "From source" requirements note or dependencies mention
- Mention vnetmap integration in the Reporter/key features sections if appropriate
- Update test count if changed (currently "786 passing")
- Update version footer line if test count or coverage threshold changed

## Phase 4: Commit All Changes

**What to commit (37 modified + selected untracked):**

- All 37 modified files (source, templates, tests, config, requirements)
- Untracked files to include: `tests/test_port_mapper.py` (if not already tracked), `tests/test_vnetmap_*.py`, `tests/test_e2e_vnetmap_diagram.py`, `tests/test_network_diagram_v2.py`, `src/network_diagram_v2.py`
- Untracked files to EXCLUDE: `.DS_Store` files, `logs/`, `output/bundles/`, `reports/diag_`*, `tests/diag_`*, `docs/marketing/`, `docs/superpowers/`, `frontend/static/odometer_preview.html`, `tools/`

**Commit message:**

```
feat(release): vnetmap integration, SVG diagrams, health check improvements, and docs refresh
```

## Phase 5: Push and Tag v1.5.0-rc1

```bash
git push origin feature/health-check-v2
git tag -a v1.5.0-rc1 -m "Release v1.5.0-rc1 — pre-release candidate for deployment testing"
git push origin v1.5.0-rc1
```

This triggers `.github/workflows/build-release.yml` which builds macOS .dmg and Windows .zip artifacts.

## Files to Exclude from Commit

These should NOT be committed (diagnostic scripts, output artifacts, experimental):

- `docs/marketing/`, `docs/superpowers/` — non-project docs
- `output/bundles/`, `reports/diag_prometheus_devices_raw.txt` — runtime output
- `tests/diag_prometheus_metrics.py`, `tests/diag_vms_proxy_feasibility.py`, `tests/diag_vms_tunnel_integration.py` — diagnostic scripts (not tests)
- `frontend/static/odometer_preview.html` — prototype/preview file
- `tools/` — external tooling
- `.DS_Store` files, `logs/` — OS/runtime artifacts
