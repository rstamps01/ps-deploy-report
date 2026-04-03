# TODO & Roadmap — Planned Features and Enhancements

**Purpose:** Canonical list for next steps, planned work, and release-related items. Kept in sync with development and validated in CI.

**Last updated:** 2026-04-03 (v1.5.0-rc1: vnetmap integration, SVG diagrams, health check license/call-home fixes, rack diagram U-position fix, dedup_active cleanup, docs refresh)  
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
| TSE-9 | **Coverage — low-coverage modules:** Expand tests for external_port_mapper, rack_diagram, report_builder, health_checker, tool_manager, script_runner, workflows to raise total coverage toward 80% | Lower | In progress | Phase A-C complete: +98 tests across 8 work streams; coverage 53%→56%; dead-code modules archived; external_port_mapper, rack_diagram, health_checker, tool_manager, script_runner, workflows augmented |
| TSE-10 | **Coverage — omit config:** Configure coverage omit for files not intended to be tested so cov-fail-under=80 applies only to in-scope code when threshold is raised | Lower | Done | Dead-code modules (comprehensive_report_template.py, enhanced_report_builder.py) moved to archive/; session_manager.py restored to coverage; pyproject.toml omit list cleared |

---

## Planned — Quality gates and pre-release checklist

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| QG-1 | Run flake8 + black (and optionally mypy) as part of documented pre-release run | Done | README Development § Pre-release checklist |
| QG-2 | Fix or document flake8/black/mypy exceptions to achieve green quality gate | Done | Followed [MYPY_FIX_SUGGESTIONS.md](development/MYPY_FIX_SUGGESTIONS.md): types-paramiko, _MEIPASS, var annotations, return casts, api_handler session/optional, network_diagram Path/float, report_builder tuple/int/float; mypy passes. |
| QG-3 | Raise coverage toward 80% or formally set cov-fail-under with restoration plan | In progress | cov-fail-under=60 (raised from 55); total coverage 60%+; Phase A-C complete; track TSE-9 for 80% |

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
| AO-16 | One-Shot orchestration mode | Done | oneshot_runner.py, async pre-validation, optional health checks, auto-bundle |
| AO-17 | Bundle contents cluster-scoped overhaul | Done | PDF/support-tool/log-bundle filtering, sidecar .meta.json, all switch txts, placeholders |
| AO-18 | Validation Results page (dev mode) | Done | result_scanner.py, validation_results.html; 9 operation tabs with profile-based cluster filtering |
| AO-14 | Advanced Operations documentation | Done | ADVANCED-OPERATIONS.md, POST-INSTALL-VALIDATION.md |
| AO-21 | Connection Settings layout revision | Done | Collapse arrow in header; tile starts collapsed; two clean states (dropdown-only vs full); Default PW toggle + Save/Delete in bottom toolbar; Create Cluster Profile button |
| AO-22 | Default credentials unified to support/654321 | Done | Global default changed to `support`/`654321` across all pages; vperfsanity auto-injected with `admin`/`123456`; actionable 403 hint |
| AO-23 | Rack diagram auto-placement annotation | Done | "Unverified - Auto Switch Placement" notation rendered below switch label when auto-placement mode is used |
| AO-24 | Health checks consolidated into report phase | Done | Health checks no longer run as standalone phase; run within report generation when selected; checkbox moved to sub-item of report checkbox |
| AO-25 | Port mapping in one-shot report | Done | ExternalPortMapper runs inside `_run_report()` when node+switch credentials are present |
| AO-26 | Memory usage threshold to PASS | Done | >90% memory usage reports PASS (expected for VAST clusters) |
| AO-27 | Post Deployment Activities section | Done | Replaced SSH validation table with "Next Steps — Get Started Using VAST Data" checklist; word-wrapped Paragraph cells for clean table layout |

---

## Planned — Requests for Enhancement (from Confluence)

*Source: [VAST As-Built Report Generator - v1.3.0](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/6664028496/VAST+As-Built+Report+Generator+-+v1.3.0) — Requests for Enhancement table.*

| ID    | Item | Status   | Notes |
|-------|------|----------|--------|
| RFE-1 | Support Bundle Integration | Planned | |
| RFE-2 | Jeff's Port Mapper Integration | Planned | |
| RFE-3 | Render Logical Net Diagram only with Port Map option enabled | Planned | |
| RFE-4 | Health Report Summary | Done | Health Check Module with Tier 1 (API) & Tier 3 (Switch SSH), PDF sections, remediation reports |
| RFE-5 | Integrate/Automate Post Deployment Tests | Done | Advanced Operations with 6 workflows (vnetmap, support tools, vperfsanity, log bundle, switch config, network config) |
| RFE-6 | Container deployment option | Planned | |
| RFE-7 | Update deployment procedures | Planned | |
| RFE-8 | Package as Mac.app / Win.msi | Planned | |
| RFE-9 | Add recommended next steps | Planned | |
| RFE-10 | Add Alert Summary | Planned | |
| RFE-11 | Create .json export database | Planned | |
| RFE-12 | Fix DC/DBox Rack naming | Deferred | Needs concrete bug report; depends on RFE-13 (now fixed) |
| RFE-13 | Fix Rack API Call | Done | get_racks() now uses _normalize_list_response() for paginated API support |
| RFE-14 | Check capacity calculations | Deferred | No local calculations (API pass-through); needs specific discrepancy report |

---

## In progress

*(Move items here when work starts; move to Done when complete.)*

| ID | Item | Notes |
|------|------|--------|
| UI-5 | **Full application UI restyle (Phase 1 — Foundation):** Update app.css :root tokens, shared component classes; affects all pages | Planned; ~2 hours estimated |

## Fixed Issues — State Persistence and One-Shot (pre-release)

| ID | Issue | Priority | Status | Fix |
|------|-------|----------|--------|-----|
| BUG-1 | **Profile selection not persistent:** Selected Saved Profile reverted on refresh. | High | Done | `await loadWorkflows()` and `await fetchProfiles()` in DOMContentLoaded before applying saved state |
| BUG-2 | **One-Shot checklist resets to all-checked:** Selections lost on refresh. | High | Done | Added `oneShotChecklist` array to `saveUIState()`; restore after `populateOneShotChecklist()` completes; change listeners on checkboxes |
| BUG-3 | **Cleared output repopulates on refresh:** Manual clear did not persist. | Medium | Done | `clear()` now sets `SYNC_CURSOR_KEY` to current server output count instead of removing it |
| BUG-4 | **Mode toggle resets to One-Shot on refresh:** Step-by-step not remembered. | High | Done | Added step-by-step restore path in `applySavedUIState`; removed forced one-shot for completed result; removed conflicting label init |
| BUG-5 | **As-Built reports filter into Unsaved Cluster Results:** PDF/JSON not linked to cluster. | Medium | Done | Embed `cluster_ip` in JSON output; write PDF sidecar `.meta.json`; scanner checks sidecar and builds API-name-to-IP map from existing JSON |
| BUG-6 | **One-Shot default creds use single user for all operations:** admin used everywhere. | High | Done | Global default changed to `support`/`654321`; per-phase credential routing injects `admin`/`123456` only for vperfsanity when default creds active; actionable 403 hint added |
| BUG-7 | **As-Built report/JSON missing from bundle:** Bundler matched by `cluster_name` in filename but received IP instead. | High | Done | Match via `.meta.json` sidecar `cluster_ip`; collect `asbuilt_json`; auto-resolve cluster name from report JSON; one-shot passes resolved API name |

---

## Planned — UI Enhancement & Restyle (phased)

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| UI-1 | **Switch Placement Editor Modal:** Refactor Discovery/Manual Add into modal with Save to Profile, Cancel, snapshot/restore, Escape/click-outside close | High | Done | Implemented in reporter.html; modal with full Discovery, Manual Add, assignment, Save to Profile / Cancel |
| UI-2 | **5-step stepper action bar:** Sequential workflow bar (Discovery → Run → View → Download PDF → Download JSON) with dot indicators, connecting line, ghosted/active button states | High | Done | CSS grid stepper with 18px dots, chevron separators, ghosted/active states |
| UI-3 | **Remove Switch Placement Mode toggle:** Default Manual, fallback Auto if no placements; remove toggle HTML/JS/CSS | High | Done | Toggle removed; default Manual with Auto fallback |
| UI-4 | **Enhanced checklist rows:** Card-style elevated container, right-aligned status tags, post-completion green Passed indicators | Medium | Planned | Part of Phase 1 foundation |
| UI-5 | **Phase 1 — Foundation restyle:** Update app.css :root tokens, shared components (cards, buttons, forms, tables, toggles, badges); pill segmented controls; cascades to all pages | Medium | Planned | ~2 hours; highest ROI |
| UI-6 | **VAST Logo Progress Tracker enhancement:** Dedicated right column (always visible, dimmed at rest); granular progress; brand gradient fill on completion (navy → teal) | Medium | Done | Backend phase-level progress (7 weighted phases for report, per-check for health); frontend weighted segment mapping; smooth `_animateTo` animation; both Reporter and Test Suite tiles |
| UI-7 | **Relocate Update Tools:** Move to card header with orange badge indicator for update-needed state | Medium | Done | Icon-only button with orange notification dot in card header |
| UI-8 | **Phase 2 — Advanced Ops restyle:** Apply stepper/checklist/modal patterns from Reporter to Advanced Ops page | Low | Planned | ~1-2 hours; largely copy-paste from Reporter |
| UI-9 | **Phase 3 — Remaining pages:** Polish Dashboard, Results, Library, Docs, Config, Generate, Health pages with foundation styles | Low | Planned | ~2-3 hours; most benefit from Phase 1 automatically |

---

## Planned — Future enhancements

| ID | Item | Priority | Notes |
|------|------|----------|--------|
| AO-18 | **Validation Results page (dev mode):** Browse all operation results with tabs and profile-based cluster filtering. Will replace production Reports page when Post Deployment Validation is fully released. | Medium | result_scanner.py, app.py, validation_results.html — implemented, needs polish |
| AO-20 | **Generate Report page enhancements:** Apply log level selector (Status/Live/Debug), persistent log storage with 1GB capacity, and window state persistence to the Generate Report page. Align Generate page UX with Advanced Ops improvements. | Low | Future work — apply patterns from AO-19 to generate.html and report generation pipeline |
| NET-1 | **Add nb_eth_mtu to network configuration:** Collect `nb_eth_mtu` (non-blocking Ethernet MTU) from `/api/v7/vms/1/network_settings/` response `data` field. Add to `VastClusterInfo` dataclass, `get_network_config()` extraction, `data_extractor.py` network section, and report output (PDF Network Configuration table and JSON export) alongside existing `eth_mtu` and `ib_mtu` fields. | Medium | Done — v1.5.0; collected from both clusters/ and network_settings endpoints |
| REL-1 | **Remove Beta badge before v1.5.0 release:** Remove the `nav-badge-beta` span from `base.html` and its CSS from `app.css` prior to tagging the production release. | High | Done — removed in v1.5.0 release prep |
| PM-1 | **SSH proxy hop for field deployments:** Tunnel switch SSH through CNode via paramiko nested transport (`direct-tcpip` channel) so port mapping and Tier 3 health checks work when switches are only reachable from the cluster internal network. Default on. UI toggle, CLI `--no-proxy-jump`, profile persistence. Hot-fix candidate for v1.4.8 (ssh_adapter + external_port_mapper subset). | High | Done — v1.5.0; hot-fix cherry-pick available for v1.4.8 |
| UPD-1 | **In-app self-update mechanism:** Add ability for the application to check for, download, and apply updates (hot-fixes and new versions) from GitHub Releases. Workflow: (1) Check current version against latest GitHub Release tag; (2) Display update notification with release notes when newer version available; (3) User-initiated download of platform-appropriate artifact (.dmg / .zip); (4) Apply update and restart. Consider: auto-check on launch (configurable), manual check via UI button, rollback capability, update channel (stable vs pre-release), signature verification for downloaded artifacts. | Medium | Future enhancement; reduces manual update friction for field-deployed instances |
| CFG-1 | **Configuration template refresh:** Update `config/config.yaml.template` to reflect all settings, features, and enhancements added since last update. Ensure parity between template and runtime config keys. Document new keys (ops_log settings, SSH proxy defaults, reporter defaults) in README Configuration section. | High | v1.5.0 release; template has drifted from runtime capabilities |
| CFG-2 | **Report section toggles:** Per-section true/false toggles under `data_collection.sections` controlling PDF rendering (headings, descriptions, tables, images, TOC entries). Covers all 11 report sections. JSON export unaffected. | High | Done — v1.5.0 |
| RPT-1 | **Rack diagram serial labels:** CBox/DBox labels replaced with Hardware Inventory Name/Serial Number; DBox deduplication at same U position for Ceres V1 (4x dnodes → 1 label). | Medium | Done — v1.5.0 |
| RPT-2 | **Post Deployment Activities dynamic status:** Status column auto-resolves to Completed (green), Optional (accent blue), or Pending (orange) from health check results and cluster data. Render-time fallback for existing JSON files. | Medium | Done — v1.5.0 |
| HWL-1 | **Hardware library additions:** `supermicro_turin_cbox` and `bluefield` entries added to BUILTIN_DEVICES for VMS API model matching. | Low | Done — v1.5.0 |
| RPT-3 | **Rack diagram status indicators:** Per-device color-coded indicators (CBox: 1–4 CNode dots, DBox: 1–4 DNode squares, EBox: 1 dot + 2 squares, Switch: 1 dot if in HW Inventory). Green=Active, Orange=Inactive, Blue=Management VMS. Dark pill background, legend tile. | Medium | Done — v1.5.0 |
| HC-1 | **Health check tuning & Tier 2 removal:** Active Alarms→warning, CNode Status management pass-through, Switches in VMS→skipped, Monitoring Config removed (no SNMP/syslog API), Tier 2 node SSH checks removed (redundant with One-Shot `vast_support_tools.py`). Render-time fixups for old JSON. | High | Done — v1.5.0 |
| DOC-1 | **README.md — Health check tier model:** Removed Tier 2, updated to 2-tier model (26 API + 6 Switch SSH = 32 checks) | High | Done |
| DOC-2 | **README.md — Advanced Configuration page:** Added row to Web UI table; described 9 sections, Report Tuning Tool, deep-merge save | High | Done |
| DOC-3 | **README.md — Configuration section update:** Rewrote Configuration section with Advanced Config UI as primary interface, Report Tuning Tool, formatting options | Medium | Done |
| DOC-4 | **README.md — Report formatting options:** Documented organization, margins, font family, Include TOC/Page Numbers with config keys | Medium | Done |
| DOC-5 | **README.md — VIP Pools health check behavior:** Added warning status note and render-time fixup description | Low | Done |
| DOC-6 | **POST-INSTALL-VALIDATION.md — Remove Tier 2 Node SSH section:** Removed Tier 2 table, updated Recommended Sequence, Summary Matrix, and One-Shot section | High | Done |
| DOC-7 | **POST-INSTALL-VALIDATION.md — Add Advanced Configuration reference:** Added config note to Recommended Sequence with Report Tuning Tool cross-reference | Low | Done |
| DOC-8 | **ADVANCED-OPERATIONS.md — Tier 2 removal and config page:** Updated Tiers 1-3 → Tier 1 + Tier 3; added Configuration section with Advanced Config and Report Tuning Tool cross-references | Medium | Done |
| DOC-9 | **RELEASE_NOTES_v1.5.0.md — Add recent changes:** Add to Highlights and New Features: (1) Advanced Configuration UI with Report Tuning Tool; (2) Report formatting fixes (organization, margins, page numbers, font family, blank page on page 9); (3) VIP Pools status changed from fail to warning with render-time fixup; (4) Reporter UI config wiring (SSH, health check, advanced ops settings initialized from config.yaml); (5) Advanced Config deep-merge save prevents config key loss; (6) Prometheus diagnostics script for future metric evaluation. Update Known Limitations: remove AO-15/AO-19 if complete; note pending font-family troubleshooting task. | High | Planned |
| DOC-10 | **docs/deployment/PORT-MAPPING-GUIDE.md — SSH proxy hop:** Added SSH Proxy Hop section with CNode tunneling details, CLI flag, UI toggle; updated Network Access requirements | Medium | Done |
| DOC-11 | **docs/development/HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md — Tier 2 removal:** Updated WP-9 to Tier 3 only; marked Tier 2 checks as removed; added post-HC-1 state note with VIP Pools warning and fixup mechanism | Medium | Done |
| DOC-12 | **docs/deployment/DEPLOYMENT.md — Version and config updates:** Updated Python 3.8+ → 3.10+, added Advanced Config reference, updated footer to v1.5.0 | Low | Done |
| DOC-13 | **docs/API-REFERENCE.md — Prometheus and monitoring endpoints:** Verify Prometheus metric endpoints (`/api/prometheusmetrics/{path}`) are documented with available paths (devices, cnodes, cluster, network, etc.). Check if monitoring endpoints section references removed SNMP/syslog endpoints and remove if present. Confirm `nb_eth_mtu` field reference in network settings. Update "Last updated" date. | Low | Planned |
| DOC-14 | **Confluence docs sync (`docs/confluence/`):** Refresh local copies of Confluence design/requirements pages (page 6664028496) before v1.5.0 release using Atlassian MCP tools. Ensure RFE table and version references reflect current state. Directory currently empty — requires initial download or re-sync from Confluence. | Medium | Planned |
| DOC-15 | **CHANGELOG.md — Verify completeness:** Review v1.5.0 changelog entries against all modified files and features. Ensure no changes from recent sessions (Advanced Configuration, report formatting, VIP Pools, config wiring, Prometheus diagnostics) are missing before release tag. | Low | Done — v1.5.0-rc1 |
| TP-1 | **Tech Port Auto-Discovery and API Proxy Tunnel:** Enable the app to connect to any CBox Tech Port (192.168.2.2) and automatically discover and tunnel API calls to VMS, eliminating manual CBox identification. **Feasibility validated on selab-var-202 (2026-03-28):** (1) `find-vms` returns VMS internal IP (172.16.3.4) from any CNode; (2) SSH hop from non-VMS CNode to VMS internal IP works; (3) `ip addr` on VMS CNode returns management IP (10.143.11.202); (4) API calls to management IP from any CNode return HTTP 403 (auth required = reachable); (5) VMS internal IP does NOT serve HTTPS (000) — must use management IP for API tunnel. **Discovery chain:** SSH Tech Port → `find-vms` → SSH hop to VMS internal IP → extract management IP from `ip addr` → paramiko tunnel to management IP:443. Builds on existing `ssh_adapter.py` proxy hop infrastructure (`direct-tcpip` channels). Diagnostic script at `tests/diag_vms_proxy_feasibility.py`. | High | Planned |
| AO-28 | **Switch config backup in Network Configuration Extraction:** Add a full switch config backup step to the One-Shot Network Configuration Extraction workflow (`src/workflows/network_config_workflow.py`). Run `nv config show` (full output, not head-50) on each switch and save the complete config to a file in the output directory (e.g. `switch_config_<ip>.txt`). Include in the result bundle. The existing Tier 3 health check `_check_switch_config_backup` (now renamed to `Switch Config Readability`) only captures a 50-line snippet for verification — the workflow step should capture the full config for backup/reference purposes. | Medium | Planned |
| PROM-1 | **Enhanced Prometheus device metrics capture:** Enrich the Device Health (Prometheus) health check to capture per-device structured data in the JSON details: endurance %, temperature, media errors, power-on hours, power cycles, and active/inactive/failed state for all SSDs and NVRAMs. Add warning thresholds (endurance <80%, temperature >55°C SSD / >65°C NVRAM). Currently only aggregate counts are stored; individual device data is discarded after scanning. Diagnostic script at `tests/diag_prometheus_metrics.py`. | Medium | Planned |
| PROM-2 | **Probe additional Prometheus metric paths (CNode and cluster):** Discover and integrate additional `/api/prometheusmetrics/` paths beyond `devices` (e.g. `cnodes`, `cluster`, `network`, `protocols`, `capacity`). The `devices` path only returns DBox SSD/NVRAM data. CNode metrics (CPU, memory, NIC) may be available at other paths. Use `tests/diag_prometheus_metrics.py` to probe available paths per cluster version. | Low | Planned |

---

## Done

*(Items completed this release cycle; archive or clear periodically.)*

| ID   | Item | Notes |
|------|------|--------|
| AO-15 | Advanced Ops hardening | Cross-tenant vperfsanity cleanup in Step 7; reporter profile save includes rpt_* checklist fields; ALL_FIELDS extended for profile round-trip |
| AO-19 | Dynamic log levels, state persistence | Tier UI on Adv Ops + Reporter; ops_log_manager 1GB/25% purge; YAML config wired to OpsLogManager factory; state snapshot API + hydration; localStorage persistence |
| CFG-1 | Configuration template refresh | Template verified in sync with runtime config; all new keys present (SSH proxy, ops_log, section toggles, advanced operations) |
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
| HC-12 | **License detection multi-source:** `_resolve_license()` checks 5 cluster fields + `licenses/` endpoint fallback | health_checker.py; fixes null license on many clusters |
| HC-13 | **Call Home via `callhomeconfigs/`:** Dedicated endpoint with cloud/log/bundle status; fallback to cluster booleans | health_checker.py; enriched status message |
| DOC-15 | CHANGELOG verification | v1.5.0-rc1 entries verified against all modified files |
| RPT-4 | **Dedup field cleanup:** Removed phantom `dedup_active` (not in VAST API); "Similarity Enabled" row is the correct dedup indicator | api_handler.py, data_extractor.py, report_builder.py |
| RPT-5 | **Rack diagram U-position fix:** Bottom-based positioning; device extends upward from base U | rack_diagram.py |
| VNET-1 | **Vnetmap integration:** Run Vnetmap checkbox, `/api/vnetmap-status`, hardware fingerprint comparison, three-source port mapping priority, LLDP IPL parsing | app.py, data_extractor.py, vnetmap_parser.py, reporter.html |
| SVG-1 | **SVG diagram support:** svgwrite + cairosvg deps, landscape page template, macOS libcairo path | requirements.txt, report_builder.py, app.py, main.py |

---

## Next steps (current focus)

1. **v1.5.0-rc1 deployment testing:** RC1 tag pushed to trigger CI build-release workflow. Validate macOS .dmg and Windows .zip artifacts, then run smoke tests on both platforms.
2. **v1.5.0 release:** After RC1 validation, merge feature branch to develop, then to main, tag v1.5.0. Release notes (DOC-9) to be finalized.
3. **Documentation refresh (remaining):** DOC-9 (release notes), DOC-13 (API reference Prometheus endpoints), DOC-14 (Confluence sync).
4. **UI Enhancement Phase (UI-1 through UI-9):** Switch Placement Editor modal, stepper action bar, and progress tracker complete. Remaining: Phase 1 foundation restyle (UI-5), enhanced checklist rows (UI-4), Phase 2/3 (UI-8, UI-9).
5. **Generate page enhancements (AO-20):** Apply log level selector, persistent log storage, and state persistence to the Generate Report page (future — post-v1.5.0).
6. **Test suite:** TSE-9 (coverage toward 80%); 876 tests pass at 62% coverage currently.
7. Before each release: update this file (status, Last updated, move completed items to Done).
8. CI validates this file exists and contains required sections (see todo-tracking rule and CI job).

---

## Planned — Port Mapper Integration (low priority)

*Source: Review of Jeff's Port Mapper (pm.py v5.6) — design-time switch port planning tool.*

| ID    | Item | Priority | Status  | Notes |
|-------|------|----------|---------|-------|
| PMI-1 | **Extract switch model metadata:** Extract `SWITCH_LAYOUTS` dictionary (11 switch models: SN3700, SN4600, SN5400, SN5600, Arista 7050DX4/7060DX5/7060X6, Cisco 9332D/9364D/9364E) into shared `src/switch_models.py` reference. Enriches rack diagrams, port mapping reports, and health checks with port counts, native speeds, and vendor names. | Low | Planned | Low effort; immediate value for `rack_diagram.py` and `health_checker.py` model awareness |
| PMI-2 | **Planned-vs-actual port validation health check:** Compare planned port assignments (from Port Mapper output or saved JSON) against actual MAC-to-port mapping collected by `ExternalPortMapper`. Detect wrong port assignments, missing connections, cross-cabled nodes, and reserved ports in use. New Tier 3 health check. | Low | Planned | Requires defining import format for planned port maps; high diagnostic value |
| PMI-3 | **Switch face-plate diagram in reports:** Port the `PortDrawer` class and switch face-plate PNG overlays into the PDF report's Switch Port Mapping section. Color-coded visual port diagrams supplement existing table-based data. | Low | Planned | Medium effort; depends on PMI-1 for model metadata; visually impactful for reports |

---

## RFE and other tracking

- **RFE:** Requests for Enhancement from Confluence (page 6664028496) are tracked as GitHub issues or referenced here when work begins.
- **Session-level work:** Use Cursor TODO tracking during sessions; promote agreed next steps to this roadmap.
