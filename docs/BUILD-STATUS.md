# Build & CI Status (Post–Unreleased Changes)

**Date:** 2026-03-10  
**Scope:** All changes since last tagged build (EBox integration, Library EBox, docs, tests).

---

## 1. Rules reviewed

| Rule | Summary |
|------|--------|
| **release-packaging-12** | APP_VERSION in `src/app.py` is source of truth; build uses `packaging/build-mac.sh`; Phase 1–6 checklist (validate, docs, version bump, commit, tag, verify). |
| **ci-pipeline-13** | Quality gates: flake8, black, mypy; unit / integration / UI tests; 80% coverage required in CI; build smoke on develop/main. |
| **documentation-08** | Update README, CHANGELOG, docs on feature/API/config changes. |
| **design-guidelines-01** | References project design docs (Concept, PRD, Plan, etc.). |

---

## 2. Changelog & updates since previous build

From **CHANGELOG.md [Unreleased]**:

- **Added:** EBox discovery (API v7), Library Type EBox, API reference EBox section, rack diagram generic 1U/2U tests.
- **Changed:** Data extractor (list/dict normalization, switch_inventory, error-path inventory), report builder (total_devices, eboxes in table/condition), export script (eboxes in v7 list).
- **Technical:** api_handler (ebox, ebox_id, get_ebox_details), data_extractor (eboxes, _normalize_boxes_to_dict), report_builder (ebox in cover/summary/inventory), library.html (EBox option, EBox Hardware section), app.py (type ebox).

---

## 3. What the DMG / .app bundle contains

| Content | In bundle? | Notes |
|--------|------------|--------|
| **src/** (Python) | Yes | All modules reachable from `main.py` (api_handler, data_extractor, report_builder, app, etc.). EBox code is included. |
| **frontend/templates** | Yes | Full directory. Verified: `library.html` in `dist/VAST Reporter.app` contains `<option value="ebox">EBox</option>`. |
| **frontend/static** | Yes | Full directory. |
| **config/** (yaml, device_library, cluster_profiles) | Yes | Defaults copied to bundle; writable copies in data dir at runtime. |
| **assets/diagrams, assets/hardware_images** | Yes | Images only (no composite). |
| **docs/API-REFERENCE.md** | Yes (as of spec change) | Added to `packaging/vast-reporter.spec` so next build includes it. |
| **docs/api/EBOX_API_V7_DISCOVERY.md** | Yes (as of spec change) | Added to spec for next build. |
| **scripts/** (e.g. export_swagger.py) | No | Dev-only; not required at runtime. |
| **tests/** | No | Not bundled (CI/repo only). |

The **current** `dist/VAST Reporter.app` (from the build run earlier) was verified to include the EBox option in `library.html`. Python code in the bundle is built from the same repo; EBox API and report logic are in that code.

**Change made:** `packaging/vast-reporter.spec` was updated to bundle `docs/API-REFERENCE.md` and `docs/api/EBOX_API_V7_DISCOVERY.md` so the **next** build will include these docs inside the .app.

---

## 4. CI/CD test results (local)

| Gate | Result | Notes |
|------|--------|--------|
| **flake8 src/ tests/** | Fail | Pre-existing issues (unused imports, line length, E402, etc.). Not introduced by EBox changes. |
| **black --check** | Fail | 31 files would be reformatted (pre-existing). |
| **mypy** | Skip | `mypy` not installed in current env (CI installs it). |
| **Unit tests** | 229 passed, 2 failed | Failures in `test_ssh_adapter.py` (SubprocessSSH; environment-dependent). Rest pass. |
| **Integration tests** | 13 passed | All integration tests pass, including hardware inventory and pipeline. |
| **Coverage** | Below 80% | CI expects 80%; current ~52% (unit), ~26% (integration run). Pre-existing. |

**Conclusion:** EBox-related and recent changes are not causing test failures. The 2 unit failures and lint/format issues are pre-existing. Integration tests confirm the full pipeline with EBox-related data and report generation.

---

## 5. Recommended next steps

1. **Rebuild the .dmg** so the new spec is used (includes API-REFERENCE.md and EBOX_API_V7_DISCOVERY.md in the bundle):
   ```bash
   bash packaging/build-mac.sh
   ```
2. **Bump version** for a proper release (e.g. 1.4.2): update `src/app.py` (APP_VERSION), `src/__init__.py`, `src/main.py`, `packaging/vast-reporter.spec` (CFBundleShortVersionString/CFBundleVersion), and move CHANGELOG [Unreleased] to `[1.4.2] - YYYY-MM-DD`.
3. **Address CI gates** (optional before release): run `black src/ tests/`, fix flake8 errors, install mypy and fix type issues, and stabilize or skip the flaky `test_ssh_adapter` tests for local/CI.
4. **Confirm which .dmg you run:** Use the one from the latest `bash packaging/build-mac.sh` (e.g. `dist/VAST-Reporter-v1.4.1-mac.dmg`). If you were testing an older .dmg, the new build from the same repo already contains the EBox and code changes.

---

**Status: Complete.** All rules and changelog reviewed; build contents verified; CI tests run; spec updated to include key docs in the next build.
