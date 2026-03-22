# TODO & Roadmap — Planned Features and Enhancements

**Purpose:** Canonical list for next steps, planned work, and release-related items. Kept in sync with development and validated in CI.

**Last updated:** 2026-03-22 (Test Coverage Phase A-C: +98 tests, 503 total, 56% coverage, cov-fail-under=55)  
**Reference:** [PRE-RELEASE-QA-GAP-ANALYSIS.md](PRE-RELEASE-QA-GAP-ANALYSIS.md) (feature coverage and recommendations)

---

## Status key

| Status   | Meaning |
|----------|--------|
| Planned  | Not started; agreed as next or future work |
| In progress | Actively being worked on |
| Done     | Completed (move to CHANGELOG / release notes and clear or archive here) |
| Deferred | Postponed; reason and target release noted |

---

## Planned — Test suite enhancements (pre-release QA)

*Source: PRE-RELEASE-QA-GAP-ANALYSIS.md §6.3*

| ID   | Item | Priority | Status   | Notes |
|------|------|----------|---------|--------|
| TSE-1 | **Library:** Unit tests for GET `/library`, GET/POST/DELETE `/api/library`, mocked _load_library/_save_library | High | Done | test_app.py |
| TSE-2 | **Generate cancel:** Unit test POST `/generate/cancel` (no job → 200/409; job running → cancel accepted, mock state) | High | Done | test_app.py |
| TSE-3 | **Reports dirs:** Unit tests GET `/reports/dirs`, POST with valid path (output-dir behavior) | High | Done | test_app.py |
| TSE-4 | **API discover:** Unit test POST `/api/discover` with mocked create_vast_api_handler + RackDiagram (400/401/success) | Medium | Done | test_app.py |
| TSE-5 | **Report content:** Integration test — EBox + dell_turin_cbox + serial in data; assert PDF/intermediate contains expected strings | Medium | Done | test_integration.py |
| TSE-6 | **Profiles API:** Unit tests GET/POST/DELETE `/profiles` and `/profiles/<name>` (mock _load_profiles/_save_profiles) | Medium | Done | test_app.py |
| TSE-7 | **Shutdown:** Optional unit test POST `/shutdown` (200, no crash) or document as manual check | Lower | Done | test_app.py |
| TSE-8 | **Coverage:** Add tests for external_port_mapper, rack_diagram, report_builder (EBox path, partial port mapping) toward 80% | Lower | Done | Coverage 53%+ (49%+ restored); further toward 80% in TSE-9 |
| TSE-9 | **Coverage — low-coverage modules:** Add tests for comprehensive_report_template.py, enhanced_report_builder.py (and expand external_port_mapper, rack_diagram, report_builder per TSE-8) to raise total coverage toward 80% | Lower | In progress | Phase A-C complete: +98 tests across 8 work streams; coverage 53%→56%; dead-code modules omitted; external_port_mapper, rack_diagram, health_checker, tool_manager, script_runner, workflows augmented |
| TSE-10 | **Coverage — omit config:** Optionally configure coverage omit for files not intended to be tested so cov-fail-under=80 applies only to in-scope code when threshold is raised | Lower | Done | pyproject.toml `[tool.coverage.run]` omit: comprehensive_report_template.py, enhanced_report_builder.py, session_manager.py |

---

## Planned — Quality gates and pre-release checklist

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| QG-1 | Run flake8 + black (and optionally mypy) as part of documented pre-release run | Done | README Development § Pre-release checklist |
| QG-2 | Fix or document flake8/black/mypy exceptions to achieve green quality gate | Done | Followed [MYPY_FIX_SUGGESTIONS.md](development/MYPY_FIX_SUGGESTIONS.md): types-paramiko, _MEIPASS, var annotations, return casts, api_handler session/optional, network_diagram Path/float, report_builder tuple/int/float; mypy passes. |
| QG-3 | Raise coverage toward 80% or formally set cov-fail-under with restoration plan | In progress | cov-fail-under=55 (raised from 45); total coverage 56%+ (503 tests); Phase A-C complete; track TSE-9 for 80% |

---

## Planned — Authentication and reporting access

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| AUTH-1 | **Automate token generation:** Consider automating API token creation (e.g. on first connect or when no valid token is provided) to simplify reporting access. Token generation enables read-only API access for the report tool only; it has no direct impact on cluster components, cluster functionality or operations, or resources used by the cluster to deliver data services. Align with [READ_ONLY_VAST_API_POLICY.md](development/READ_ONLY_VAST_API_POLICY.md) (auth POST allowed to establish access). | Planned | Current flow: prefer provided token or basic auth; create token only when needed (5-token limit). Automation could streamline this for unattended or scripted reporting. |

---

## Planned — Developer mode (hidden/secure)

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| DEV-1 | **Developer button:** Add a hidden/secure Developer control at the top of the UI, enableable by developers at launch (e.g. env flag or launch option). When enabled, expose: (1) **Configuration** — move existing Configuration section under Developer; (2) **Docs** — move Docs access under Developer; (3) **Live API Explorer** — expose API Explorer interface under Developer; (4) **Report from JSON** — new UI to generate reports directly from previously generated `.json` output files (e.g. `vast_data_*.json`) without reconnecting to the cluster. | Planned | Navbar/top-level; secure so only enabled at launch |

---

## Planned — EBox Hardware Overview & Inventory

*Source: [EBOX-HARDWARE-TABLE-IMPLEMENTATION-PLAN.md](development/EBOX-HARDWARE-TABLE-IMPLEMENTATION-PLAN.md)*

| ID    | Item | Status   | Notes |
|-------|------|----------|--------|
| EBOX-1 | **Hardware Overview (EBox-only):** CBoxes=0, DBoxes=0; CNodes/DNodes as discovered | Done | report_builder.py |
| EBOX-2 | **Hardware Inventory (EBox-only):** Remove Node column; EBox→CNode→2×DNodes order; Model from CNode vendor; switches at bottom | Done | report_builder.py _create_ebox_only_inventory_table; brand_compliance 5-col |
| EBOX-3 | **Rack Layout:** EBox model from CNode vendor for library image; 1U default | Done | report_builder.py racks_data ebox model from CNode; rack_diagram 1U already |
| EBOX-4 | **Port Mapping (EBox-only):** CNode/DNode names in Notes column; separate from standard CBox/DBox logic | Done | external_port_mapper.py, report_builder.py |
| EBOX-5 | **Network Diagram (EBox-only):** EB# labels, Green (Network A) / Blue (Network B) connections | Done | network_diagram.py |
| EBOX-6 | **Hardware Library:** msn4700-ws2rc switch and dell_genoa_ebox added as built-in devices | Done | app.py, rack_diagram.py, network_diagram.py |

---

## Planned — Support bundle workflow (offline / no direct cluster access)

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| SB-1 | **Support bundle–based report generation:** New function for clusters that cannot be directly accessed. Workflow: (1) Generate a support bundle for the cluster (customer/ops generates bundle); (2) Upload support bundle content into the app; (3) Analyze support bundle file content; (4) Generate `.json` file from bundle content (same schema as live-generated `vast_data_*.json`); (5) Generate report from the generated `.json` file (reuse existing report-from-data path). End-to-end: support bundle → JSON → PDF report without live API access. | Planned | New upload/analyze pipeline; document bundle format and required files |

---

## Done — Advanced Operations (Post-Install Validation)

*Source: Confluence Post-Install Validation procedures + Health Check Module Implementation Guide.*

| ID    | Item | Status | Notes |
|-------|------|--------|-------|
| AO-0 | Developer Mode gating for Advanced Operations page | Done | `--dev-mode` flag required; routes/UI hidden otherwise |
| AO-1 | Advanced Operations UI page | Done | Step-by-step workflow runner with persistent output pane |
| AO-2 | Script framework (security, compatibility) | Done | `script_runner.py` with SSH/SCP operations |
| AO-3 | Workflow registry pattern + vnetmap workflow | Done | `src/workflows/__init__.py` with 7-step vnetmap |
| AO-4 | vast_support_tools workflow | Done | 5-step workflow for cluster diagnostics |
| AO-5 | vperfsanity workflow | Done | 7-step performance testing workflow (deploy, extract, prepare, run tests, collect, upload, cleanup) |
| AO-6 | VMS log bundle workflow | Done | 5-step workflow with size discovery |
| AO-7 | Status checks and reminders | Done | Call Home, License, Rack/U-Height, Switches |
| AO-8 | Switch configuration extraction | Done | 3-step workflow for backup/replacement |
| AO-9 | Network configuration extraction | Done | 4-step workflow for configure_network.py commands |
| AO-10 | Result bundler | Done | ZIP archive with all validation outputs |
| AO-11 | Testing suite (80% coverage) | Done | test_advanced_ops.py, test_script_runner.py, test_workflows.py, test_result_bundler.py |
| AO-12 | CI integration | Done | `advanced-ops-tests` job in CI pipeline |
| AO-13 | WP-13 documentation verification | Done | CHANGELOG, README, TODO-ROADMAP updates |
| AO-14 | Advanced Operations documentation | Done | ADVANCED-OPERATIONS.md, POST-INSTALL-VALIDATION.md |

---

## Planned — Requests for Enhancement (from Confluence)

*Source: [VAST As-Built Report Generator - v1.3.0](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/6664028496/VAST+As-Built+Report+Generator+-+v1.3.0) — Requests for Enhancement table.*

| ID    | Item | Status   | Notes |
|-------|------|----------|--------|
| RFE-1 | Support Bundle Integration | Planned | |
| RFE-2 | Jeff's Port Mapper Integration | Planned | |
| RFE-3 | Render Logical Net Diagram only with Port Map option enabled | Planned | |
| RFE-4 | Health Report Summary | Done | Health Check Module with Tiers 1-3, PDF sections, remediation reports |
| RFE-5 | Integrate/Automate Post Deployment Tests | Done | Advanced Operations with 6 workflows (vnetmap, support tools, vperfsanity, log bundle, switch config, network config) |
| RFE-6 | Container deployment option | Planned | |
| RFE-7 | Update deployment procedures | Planned | |
| RFE-8 | Package as Mac.app / Win.msi | Planned | |
| RFE-9 | Add recommended next steps | Planned | |
| RFE-10 | Add Alert Summary | Planned | |
| RFE-11 | Create .json export database | Planned | |
| RFE-12 | Fix DC/DBox Rack naming | Planned | |
| RFE-13 | Fix Rack API Call | Planned | |
| RFE-14 | Check capacity calculations | Planned | |

---

## In progress

*(Move items here when work starts; move to Done when complete.)*

| ID | Item | Notes |
|------|------|--------|
| AO-15 | **Advanced Ops hardening:** Cross-tenant vperfsanity cleanup, unified profile management, SSH adapter stability, UI refinements | vperfsanity_workflow.py, app.py, ssh_adapter.py, advanced_ops.html |

---

## Done

*(Items completed this release cycle; archive or clear periodically.)*

| ID   | Item | Notes |
|------|------|--------|
| QG-2 | Fix flake8/black/mypy exceptions to achieve green quality gate | mypy: 97→0 errors; see [MYPY_FIX_SUGGESTIONS.md](development/MYPY_FIX_SUGGESTIONS.md). |
| QG-1 | Document pre-release run (flake8, black, mypy, pytest) | README Development § Pre-release checklist. |
| TSE-1 | Library API unit tests | GET /library, GET/POST/DELETE /api/library (mocked _load_library/_save_library). |
| TSE-2 | Generate cancel unit test | POST /generate/cancel (no job → no_job; job running → cancelled). |
| TSE-3 | Reports dirs unit tests | GET /reports/dirs, POST valid path + 400 for empty/nonexistent. |
| TSE-4 | API discover unit tests | POST /api/discover (400/401/success) with mocked handler + RackDiagram. |
| — | Read-only VAST API policy | Data collection GET-only; [READ_ONLY_VAST_API_POLICY.md](development/READ_ONLY_VAST_API_POLICY.md); _make_api_request enforces GET. |
| EBOX-1 | Hardware Overview (EBox-only) | CBoxes=0, DBoxes=0 when eboxes present and no cboxes/dboxes; CNodes/DNodes as discovered. |
| TSE-5 | Report content integration test | EBox + dell_turin_cbox + serial in data; intermediate + PDF generation asserted (test_integration.py). |
| TSE-6 | Profiles API unit tests | GET/POST/DELETE /profiles and /profiles/<name> with mocked _load_profiles/_save_profiles (TestProfilesRoutes). |
| TSE-7 | Shutdown unit test | POST /shutdown returns 200 and status (TestShutdown; os._exit mocked). |
| TSE-8 | Coverage 49%+ restored | New tests raised total coverage to 53%+; cov-fail-under=47 retained. |
| EBOX-2 | Hardware Inventory (EBox-only) | 5-col table, EBox→CNode→2×DNodes per EBox, model from CNode, switches at bottom; brand_compliance 5-col. |
| EBOX-3 | Rack Layout EBox model | EBox model/hardware_type from CNode box_vendor for library image; 1U in rack_diagram. |
| EBOX-4 | Port Mapping (EBox-only) | CNode/DNode names in Notes column; standard CBox/DBox shows "Primary". |
| EBOX-5 | Network Diagram (EBox-only) | EB# labels, Green/Blue connections to switches; standard CBox/DBox connections fixed. |
| EBOX-6 | Hardware Library additions | msn4700-ws2rc switch and dell_genoa_ebox added as built-in devices. |
| HC-1 | **CNode/DNode state fix:** Use `state` field instead of `status` for node status detection | health_checker.py; fixes false-positive inactive nodes |
| HC-2 | **Network settings API fix:** Unwrap `response["data"]`, use correct field names (`dns`, `ntp`, `external_gateways`) | health_checker.py; fixes null DNS/NTP/gateway |
| HC-3 | **SSH timeout fix:** 60s overall limit, 10s per-ping, cancellation checks between IPs | health_checker.py; fixes indefinite SSH hangs |
| HC-4 | **Remediation report generator:** Human-readable `.txt` with numbered findings, correlation engine, actionable guidance | health_checker.py `generate_remediation_report()` |
| HC-5 | **RAID/Leader/Upgrade fixes:** 100% rebuild = complete; UP = healthy; DONE = pass | health_checker.py check logic |
| HC-6 | **Alarm details:** Per-alarm severity, object type, name, timestamp | health_checker.py `_check_active_alarms()` |
| HC-7 | **Events pagination:** Time filter + pagination to prevent timeout | health_checker.py `_check_events()` |
| HC-8 | **Dynamic health check tiers in Generate:** Tier selection based on Port Mapping toggle | app.py `_run_report_job()` |
| HC-9 | **API endpoint cleanup:** Removed undocumented endpoints (ntps/, alerts/); changed alarmdefinitions/ to eventdefinitions/ | api_handler.py, health_checker.py |
| HC-10 | **Reduced log noise:** WARNING→DEBUG for optional 404 endpoints (ldap, nis, snapprograms, snmp, syslog) | api_handler.py |
| HC-11 | **Health check report table:** Removed Duration column; expanded Message column to 56% | report_builder.py |

---

## Next steps (current focus)

1. **Test suite (next):** TSE-9 (coverage toward 80%: comprehensive_report_template, enhanced_report_builder, external_port_mapper, rack_diagram, report_builder); TSE-10 (optional coverage omit). “all features validated” before next release.
2. Before each release: update this file (status, Last updated, move completed items to Done).
3. CI validates this file exists and contains required sections (see todo-tracking rule and CI job).
4. Restore cov-fail-under to 49%+ when adding tests per TSE-8 (QG-3).

---

## RFE and other tracking

- **RFE:** Requests for Enhancement from Confluence (page 6664028496) are tracked as GitHub issues or referenced here when work begins.
- **Session-level work:** Use Cursor TODO tracking during sessions; promote agreed next steps to this roadmap.
