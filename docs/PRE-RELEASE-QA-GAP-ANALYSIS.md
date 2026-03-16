# Pre-Release QA Gap Analysis — 360° Test Suite Alignment

**Date:** 2026-03-15  
**Full suite run:** 267 tests (all passed)  
**Purpose:** Ensure the test suite supports full 360° pre-release QA in alignment with project rules and best practices.

---

## 1. Executive Summary

| Dimension | Status | Notes |
|-----------|--------|-------|
| **Test execution** | ✅ Pass | 267 tests (unit + integration + UI) all pass |
| **Unit tests** | ✅ | 235 tests across 11 modules; mirror `src/` for api_handler, app, data_extractor, main, port_mapper, report_builder, etc. |
| **Integration tests** | ✅ | 13 tests — full pipeline, graceful degradation, data consistency |
| **UI tests** | ✅ | 19 Playwright tests — pages, forms, profiles, reports, config, SSE, browse API |
| **Quality gates** | ⚠️ Gap | flake8, black, mypy currently fail (pre-existing); not run as part of “full test suite” |
| **Coverage** | ⚠️ Gap | ~50% line coverage vs 80% target; several modules 0–25% |
| **Security** | ⚠️ Gap | No dedicated security test suite; credential redaction covered in sse_logger |
| **Build & packaging** | ⚠️ Gap | Build smoke not part of default `pytest tests/`; separate step |
| **Accessibility** | ⚠️ Gap | UI tests do not assert a11y (ARIA, keyboard, focus) |
| **Report content** | ⚠️ Gap | Integration checks PDF exists and sections present; no assertions on EBox/Model column/content correctness |

**Conclusion:** The suite provides strong functional coverage (unit, integration, UI) and is suitable for pre-release validation of behavior. To align with **full 360° pre-release QA** and project CI standards, address the gaps below (quality gates, coverage, optional security/build/a11y/report-content checks).

---

## 2. What the Full Suite Covers

### 2.1 Unit tests (by module)

| `src/` module | Test file | Coverage (approx) | Notes |
|---------------|-----------|-------------------|--------|
| api_handler | test_api_handler.py | 64% | Auth, requests, cluster/cnode/dnode, capabilities, list normalization |
| app | test_app.py | 56% | Factory, dashboard, generate, config, reports, docs, SSE, helpers |
| data_extractor | test_data_extractor.py | 73% | Extract all, sections, hardware inventory, physical layout, errors |
| main | test_main.py | 68% | Report generator, credentials, args, config loading |
| port_mapper | test_port_mapper.py | 94% | Init, designations, cross-connection, vnetmap, enhanced/external import |
| report_builder | test_report_builder.py | 57% | Config, init, title page, PDF generation (mocked ReportLab) |
| rack_diagram | test_rack_diagram.py | 25% | Generic 1U/2U fallback only |
| utils/logger | test_logging.py | — | Logger setup, handlers, sensitive filter |
| utils/ssh_adapter | test_ssh_adapter.py | 90% | Subprocess, Paramiko, pexpect, fallback, routing |
| sse_logger (app) | test_sse_logger.py | — | SSE handler, queue, enable, redaction |
| launcher | test_launcher.py | — | GUI/CLI routing, run_gui, run_cli |

### 2.2 Modules without dedicated test files

- **comprehensive_report_template.py** — 0% coverage; used via report_builder
- **enhanced_report_builder.py** — 0% coverage
- **enhanced_port_mapper.py** — 44% (covered indirectly via port_mapper tests)
- **external_port_mapper.py** — 16%; only import/availability tested
- **network_diagram.py** — 56% (covered via integration/other paths)
- **brand_compliance.py** — 69% (covered via report_builder)
- **vnetmap_parser.py** — 82% (via port_mapper tests)

### 2.3 Integration tests

- Full pipeline: raw API data → extract → report → PDF (magic bytes, section presence).
- Hardware inventory counts match raw data.
- Cluster name and metadata preserved.
- Graceful degradation (missing sections, empty data).
- Data consistency (extracted structure validity).

### 2.4 UI tests (Playwright)

- Page loads: dashboard, generate, reports, config; nav links.
- Generate form: cluster IP field, auth options, switch placement toggle; submit without IP shows error.
- Cluster profiles: save/load, delete.
- Reports: list matching files, download, delete.
- Config: YAML content, reset.
- SSE stream content-type; browse API default and specific path.

---

## 3. Gap Analysis vs Best Practices & Project Rules

### 3.1 Quality gates (CI rule: must pass)

- **Lint (flake8):** Not run in “full test suite”; many pre-existing issues (F401, E501, E402, etc.).  
  **Gap:** Pre-release QA should either run `flake8 src/ tests/` and fix or document exceptions.
- **Format (black):** Same; `black --check` not part of default pytest run.  
  **Gap:** Run `black --check --line-length 120 src/ tests/` (or apply and commit) before release.
- **Type check (mypy):** 113+ pre-existing errors; not run in suite.  
  **Gap:** Run `mypy src/` and either fix or track in a known-issues list for pre-release.

**Recommendation:** Document a **pre-release checklist** that explicitly includes: (1) full pytest, (2) flake8, (3) black, (4) optional mypy. Run (1)–(3) for 360° alignment.

### 3.2 Coverage (CI rule: 80% minimum)

- Current total ~50%; many modules below 80%.  
  **Gap:** Suite does not meet stated 80% line-coverage requirement.

**Recommendation:** Either (a) add tests for low-coverage modules (e.g. comprehensive_report_template, enhanced_report_builder, external_port_mapper, rack_diagram) to move toward 80%, or (b) temporarily lower `--cov-fail-under` in CI/pyproject with a tracked plan to restore it, and still run coverage locally to monitor regressions.

### 3.3 Security

- **Credential redaction:** Covered in test_sse_logger (sensitive filter).
- **Secrets in repo:** gitleaks/pre-commit mentioned in CI rule; not part of pytest.  
  **Gap:** No in-suite security tests (e.g. no credential in logs, no secrets in report output).

**Recommendation:** Optional: add a small security test (e.g. “report PDF and JSON do not contain password/token literals from config”) for 360° security awareness.

### 3.4 Build and packaging

- Build smoke (e.g. `packaging/build-mac.sh`) is a separate step; not invoked by `pytest tests/`.  
  **Gap:** “Full” pre-release QA per CI includes build validation; it is outside the test suite.

**Recommendation:** Keep build as a separate step; document in pre-release checklist: “Run full test suite then run build smoke for target platform(s).”

### 3.5 Accessibility

- UI tests assert presence and basic behavior, not a11y.  
  **Gap:** No checks for ARIA, keyboard navigation, or focus management.

**Recommendation:** Optional: add one or two Playwright a11y checks (e.g. critical buttons have labels, form fields associated with labels) if the product has a11y requirements.

### 3.6 Report content and API contract

- Integration tests verify PDF exists and high-level section presence, not exact content (e.g. EBox section text, Hardware Inventory Model column format “dell_turin_cbox / serial”).  
  **Gap:** No snapshot or schema tests for report content or for VAST API response shapes.

**Recommendation:** Optional: add integration tests that assert specific report content (e.g. EBox block, Model column format) or API response schema for critical endpoints.

### 3.7 Library and docs

- **Docs:** Routes and link rewriting covered in test_app (TestDocsRoutes).  
- **Library:** `/library` route and device_library.json loading not explicitly tested.  
  **Gap:** Minor; app route tests could be extended to include `/library` 200 and basic content.

### 3.8 Error paths and edge cases

- Many modules have moderate coverage with missing lines in exception/edge branches (e.g. api_handler 64%, app 56%).  
  **Gap:** Systematic testing of failure paths (network errors, malformed API responses, missing files) could be expanded for critical paths.

**Recommendation:** Prioritize error-path tests for API handler, app (report job failure, cancel), and report_builder (missing data, invalid paths).

---

## 4. Pre-Release QA Checklist (360° Alignment)

Use this to align a release run with project rules and best practices:

| Step | Command / action | Required by |
|------|-------------------|-------------|
| 1. Full test suite | `pytest tests/ -v` | Release / CI |
| 2. Lint | `flake8 src/ tests/` | ci-pipeline-13 |
| 3. Format | `black --check --line-length 120 src/ tests/` (or apply) | ci-pipeline-13 |
| 4. Type check | `mypy src/ --ignore-missing-imports` (optional if failing) | ci-pipeline-13 |
| 5. Coverage | `pytest tests/ --cov=src --cov-report=term-missing` (monitor; 80% is target) | testing-standards-06 |
| 6. Build smoke | `bash packaging/build-mac.sh` or Windows equivalent | release-packaging-12 / CI |
| 7. Version consistency | APP_VERSION / CHANGELOG / tag match | release-packaging-12 |

**Current state:** Steps 1 (267 passed), 5 (run but below 80%), 6 (separate). Steps 2–4 and 7 are manual/CI and often failing pre-existing. Documenting them in this checklist completes the 360° pre-release view.

---

## 5. Summary Table: Suite vs 360° Pre-Release QA

| QA dimension | In full suite? | Aligned with best practice? |
|--------------|----------------|-----------------------------|
| Unit tests | ✅ Yes | ✅ Yes |
| Integration tests | ✅ Yes | ✅ Yes |
| UI tests | ✅ Yes | ✅ Yes |
| Lint (flake8) | ❌ No | ⚠️ Should be part of pre-release run |
| Format (black) | ❌ No | ⚠️ Should be part of pre-release run |
| Type check (mypy) | ❌ No | ⚠️ Optional until errors reduced |
| Coverage ≥80% | ❌ No (≈50%) | ⚠️ Target not met |
| Security (redaction/leaks) | Partial (SSE) | ⚠️ Optional dedicated tests |
| Build smoke | ❌ No | ⚠️ Separate step; document in checklist |
| Accessibility | ❌ No | ⚠️ Optional |
| Report content assertions | Partial | ⚠️ Optional enhancement |
| Version/config consistency | ❌ No | ⚠️ Manual/CI step |

**Bottom line:** The test suite **does** cover functional pre-release QA (unit, integration, UI) and all 267 tests pass. For **full 360° alignment** with project rules and best practices, add the quality gates (lint, format, type) and coverage to the pre-release run or checklist, keep build smoke as a documented separate step, and consider optional additions (security, a11y, report content) as needed for policy or risk.

---

## 6. Feature & function coverage — should the suite be augmented?

**Short answer: yes.** For release-grade validation of **all** features and functions, the suite should be augmented in targeted areas. Current tests validate the main user journeys and core pipeline well; several app features and code paths have no or minimal direct tests.

### 6.1 App routes: tested vs not tested (unit level)

| Route / endpoint | Unit test (test_app) | UI test |
|------------------|----------------------|--------|
| `/` (dashboard) | ✅ | ✅ |
| `/generate` GET/POST | ✅ | ✅ |
| `/generate/status` | ✅ | — |
| `/generate/cancel` POST | ❌ | — |
| `/shutdown` POST | ❌ | — |
| `/config` GET/POST, `/config/reset` | ✅ | ✅ |
| `/reports`, download, view, delete | ✅ | ✅ |
| `/reports/dirs` GET/POST | ❌ | — |
| `/stream/logs` | ✅ | ✅ |
| `/docs`, `/docs/content/<id>` | ✅ | — |
| `/profiles` GET/POST, `/profiles/<name>` DELETE | ❌ | ✅ (via browser) |
| `/api/browse` | ❌ | ✅ |
| `/api/discover` POST | ❌ | — |
| `/library` | ❌ | — |
| `/api/library` GET/POST | ❌ | — |
| `/api/library/<key>` DELETE | ❌ | — |
| `/api/library/unrecognized` GET | ❌ | — |
| `/library/images/<path>`, `/library/builtin-images/<path>` | ❌ | — |

**Gaps:** Library (page + full API), generate/cancel, shutdown, reports/dirs, api/discover, and profiles have no **unit** tests; profiles and browse are covered only by UI tests.

### 6.2 Core logic and report content

| Area | Current validation | Gap |
|------|--------------------|-----|
| Report PDF generation | Integration: PDF exists, sections present | No assertion on EBox block, Model column format, port-mapping partial flag |
| Rack diagram | Generic 1U/2U fallback only | EBox placement, switch above/below ebox, device boundaries not unit-tested |
| External port mapper | Import only (~16% coverage) | No tests for multi-CNode fallback, partial output handling |
| comprehensive_report_template | 0% | All rendering paths untested at unit level |
| enhanced_report_builder | 0% | Unused or alternate path; clarify and test or document |

### 6.3 Recommendation: what to add before release

**High priority (validate features that can regress without UI)**  
1. **Library:** Add unit tests in `test_app.py`: GET `/library` returns 200; GET `/api/library` returns JSON; POST/DELETE with mocked `_load_library`/`_save_library` so the Library feature is validated without Playwright.  
2. **Generate cancel:** One unit test: POST `/generate/cancel` when no job running returns 200 or 409; when job running, cancel is accepted (mock job state).  
3. **Reports dirs:** One or two tests: GET `/reports/dirs` returns current dirs; POST with valid path updates config (or returns success) so output-dir behavior is covered.

**Medium priority (improve coverage and critical paths)**  
4. **API discover:** Unit test with mocked `create_vast_api_handler` and `RackDiagram`: POST `/api/discover` with valid payload returns racks/switches; missing IP returns 400; auth failure returns 401.  
5. **Report content:** In `test_integration.py`, add one test that builds report with EBox + dell_turin_cbox + serial in hardware data and asserts the generated PDF or intermediate data contains expected strings (e.g. "EBox", "dell_turin_cbox /", or section headings).  
6. **Profiles API:** Unit tests for GET/POST/DELETE `/profiles` and `/profiles/<name>` (mock `_load_profiles`/`_save_profiles`) so profile CRUD is validated at the API level.

**Lower priority (optional for “all features”)**  
7. **Shutdown:** Optional test that POST `/shutdown` returns 200 and does not crash the process (or skip in CI; document as manual check).  
8. **Coverage:** Add tests for high-value branches in `external_port_mapper`, `rack_diagram`, or `report_builder` (e.g. EBox path, partial port mapping) to move toward 80% where practical.

### 6.4 Summary

- **Should the suite be augmented for release?** **Yes**, if the goal is to validate **all** features and functions before release.  
- **Minimum for “all features validated”:** Add unit tests for **Library** (page + API), **generate/cancel**, and **reports/dirs**; optionally **api/discover** and **profiles** API.  
- **For stronger release QA:** Add report-content assertion (EBox/Model) and API discover + profiles unit tests; then rely on existing integration + UI for the rest.  
- **Quality gates:** Running flake8 and black (and optionally mypy) as part of pre-release remains necessary for 360° alignment; augmenting tests does not replace them.
