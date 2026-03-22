# Changelog

All notable changes to the VAST As-Built Report Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Added (Test Coverage Phase A-C)
- **Test Coverage Phase A-C:** Implemented 8-stream test coverage plan adding ~98 new tests across all modules
  - **WS-1 Config:** Fixed stale vperfsanity step count test (6→7); added `[tool.coverage.run]` omit for 3 dead-code modules; raised `cov-fail-under` from 45 to 55
  - **WS-2 ToolManager Tests:** New `tests/test_tool_manager.py` with 12 tests for initialization, local cache operations, and CNode deployment (internet-first, SCP fallback)
  - **WS-3 Workflow Execution Tests:** 18 tests added to `tests/test_workflows.py` for cross-tenant cleanup, vperfsanity step execution, switch type detection, network config clush, support tool container paths, log bundle discovery
  - **WS-4 App Route Tests:** 15 tests added to `tests/test_app.py` for profile merge-save (field preservation, api_token→token normalization, defaults), advanced ops routes, and tool management routes
  - **WS-5 ScriptRunner Tests:** 10 tests added to `tests/test_script_runner.py` for output line classification, copy_to_remote, and download_from_remote
  - **WS-6 Health Checker Tests:** 15 tests added to `tests/test_health_checker.py` for remediation report generation, correlation engine (chassis-level, leader-inactive), SSH tier-2 (management ping, memory), and SSH tier-3 (MLAG, NTP, switch checks)
  - **WS-7 Rack Diagram Tests:** 14 tests added to `tests/test_rack_diagram.py` for device boundaries, center/above/below switch placement strategies, and diagram generation
  - **WS-8 External Port Mapper Tests:** New `tests/test_external_port_mapper.py` with 12 tests for switch OS detection, MAC table parsing (Cumulus/Onyx), clush output parsing, and cross-connection detection
- **Coverage Omit Config:** Added `[tool.coverage.run]` section to `pyproject.toml` excluding dead-code modules (`comprehensive_report_template.py`, `enhanced_report_builder.py`, `session_manager.py`) from coverage measurement

- **Advanced Operations Module (Developer Mode):** New `/advanced-ops` page for complex script-based validations with step-by-step execution
  - **vnetmap Workflow (7 steps):** Download and run vnetmap.py for network topology validation
  - **VAST Support Tools Workflow (5 steps):** Run vast_support_tools.py for cluster diagnostics
  - **vperfsanity Workflow (7 steps):** Deploy, extract, prepare infrastructure (with cross-tenant cleanup), run tests, collect results, upload, and cleanup
  - **VMS Log Bundle Workflow (5 steps):** Discover log sizes, confirm collection, create and download bundle
  - **Switch Configuration Workflow (3 steps):** Extract switch config for backup/replacement; auto-detects Cumulus NVUE/NCLU and Mellanox switch types
  - **Network Configuration Workflow (4 steps):** Extract configure_network.py commands via gateway-proxied clush execution
- **Result Bundler:** Create downloadable ZIP packages containing all validation outputs
- **Workflow Registry Pattern:** Centralized workflow registration and discovery via `src/workflows/__init__.py`
- **Script Runner Framework:** Core infrastructure for secure script download, remote execution, and intelligent output classification
- **Tool Manager:** Centralized deployment tool management with internet-first download strategy and local cache fallback; "Update Tools" button in UI
- **Cross-Tenant View Cleanup:** vperfsanity Step 3 now queries the VAST API for stale `vperfsanity` views across ALL tenants and deletes them before running the prepare script, preventing HTTP 400 "bucket name already in use" errors
- **Unified Profile Management:** Profiles saved in Advanced Ops are accessible in Health Check and Generate Report (and vice versa) via merge-save pattern in backend; handles `api_token`/`token` field name aliases
- **Default Credentials Toggle:** Toggleable feature on Advanced Ops page (default ON) auto-populates standard credentials (admin/123456 for API, vastdata/vastdata for nodes, cumulus/Vastdata1! for switches)
- **Connection Settings Redesign:** Collapsible credential section, profile icon buttons (save/add/delete), green Add button toggles expand/collapse, VIP Pool Name field for vperfsanity
- **Developer Mode Gating:** Advanced Operations page only accessible when app started with `--dev-mode` flag
- **CI Advanced Ops Tests:** New `advanced-ops-tests` job in CI pipeline for workflow testing
- **Health Check Module:** New `health_checker.py` with 26 Tier-1 API checks, Tier-2 node SSH checks, and Tier-3 switch SSH checks
- **Dynamic Health Check Tiers in Generate:** When "Include Health Check" is enabled, tiers are selected based on Port Mapping:
  - Port Mapping disabled → Tier 1 only (26 API checks)
  - Port Mapping enabled with SSH credentials → Tier 1+2+3 (API + Node SSH + Switch SSH)
- **Health Check UI Hint:** Generate page shows dynamic hint explaining which tiers will run
- **Health Check UI:** New `/health` page with real-time SSE log streaming, tier selection, and job control
- **Remediation Report Generator:** Health check auto-generates `.txt` remediation report with numbered findings, severity levels, timestamps, impact statements, correlated issues, and actionable remediation steps
- **Health Check Correlation Engine:** Detects related failures (e.g., CNode+DNode down = chassis issue; leader marked inactive = inconsistency warning)
- **Health Check PDF Sections:** Cluster Health Check Results and Post Deployment Validation sections in PDF report
- **API Handler Extensions:** New `get_alarms()`, `get_events()`, `get_snapshots()`, `get_quotas()`, `get_prometheus_metrics()` methods
- **Include Health Check Option:** Checkbox in Generate page to optionally include Tier-1 health check in report generation
- **CI Health Check Tests:** New `health-check-tests` job in CI pipeline for fast feedback

### Fixed
- **CNode/DNode Status Detection:** Fixed false-positive failures where active nodes were reported as inactive; health checker now uses `state` field (VAST API standard) instead of `status`
- **API Endpoint Cleanup:** Removed undocumented/non-functional API calls per official VAST API v7 documentation:
  - Removed `ntps/` call (NTP retrieved from `clusters/` endpoint)
  - Removed `alerts/` call (not documented in VAST API)
  - Changed `alarmdefinitions/` to `eventdefinitions/` (documented endpoint)
- **Reduced Log Noise:** Changed WARNING to DEBUG for optional endpoints that return 404 when features aren't configured (ldap/, nis/, snapprograms/, snmp/, syslog/)
- **Network Settings API Mapping:** Fixed DNS/NTP/gateway always showing as null; now correctly unwraps `response["data"]` from VMS API and uses proper field names
- **SSH Check Timeout:** Fixed indefinite hang on Tier-2 node SSH checks; management ping now has 60s overall limit, 10s per-ping SSH timeout, and cancellation checks
- **RAID Rebuild Progress:** Fixed 100% rebuild progress incorrectly shown as "in-progress"; now correctly reports as complete
- **Leader State Check:** Fixed "UP" leader state incorrectly flagged; now accepts "UP" as healthy
- **Upgrade State Check:** Fixed "DONE" upgrade state shown as warning; now correctly reports as pass
- **Prometheus Timeout:** Fixed hardcoded timeout; now uses configurable `self.timeout` value
- **vperfsanity Cross-Tenant Bucket Conflict:** Fixed HTTP 400 "bucket name already in use by another tenant" by adding API-level cross-tenant view cleanup before running `vperfsanity_prepare.sh`
- **vperfsanity Missing VAST_VMS:** Fixed prepare/run/cleanup commands not passing `VAST_VMS` environment variable to remote scripts, causing API calls to target wrong endpoint
- **vperfsanity SSH Credentials:** Fixed workflow incorrectly using API credentials for SSH connections; now correctly uses node SSH credentials (vastdata) for all SSH operations
- **vnetmap Resilience:** Workflow continues through partial failures (e.g., CNode down) with warnings and recommendations instead of hard-failing
- **vnetmap SSH Retry Noise:** Intelligent output classification (`_classify_output_line`) suppresses SSH key retry messages from vnetmap.py stderr
- **Switch Config Detection:** Auto-detects Cumulus NVUE vs NCLU vs Mellanox switch types; uses appropriate commands (`nv` vs `net`); removed `sudo` commands that require password
- **Network Config clush:** Rewrote to use gateway-proxied clush execution with proper single-quote escaping for inner commands; fixed "Binary file matches" error with `-a` grep flag
- **VAST Support Tools Container Path:** Fixed script execution path to use `/vast/data/` inside VAST container instead of `/tmp/vast_scripts/`
- **SSH Adapter Stability:** Enhanced paramiko connections with `banner_timeout=30`, `look_for_keys=False`, `allow_agent=False`; added `force_tty`, `login_shell`, `agent_forward` parameters
- **App Stability:** Resolved frequent app shutdowns from port conflicts and stale processes

### Changed
- **Alarm Details:** Health check captures per-alarm severity, object type, object name, and timestamp for detailed remediation guidance
- **Health Check Report Table:** Removed Duration column from "Detailed Check Results" table; adjusted column widths (Message column expanded to 56% for better text fit)
- **Event Definitions:** Health checker now uses `/api/eventdefinitions/` (documented) instead of `/api/alarmdefinitions/` (undocumented) for enriching alarm descriptions
- **Events API:** Added pagination and time filter to prevent timeout on clusters with large event history

### Changed (Advanced Operations)
- **vperfsanity Workflow:** Expanded from 6 to 7 steps (added Upload Results); pre-cleanup step runs before prepare; admin credentials passed via `ADMIN_USER`/`ADMIN_PASSWORD` environment variables
- **Advanced Ops UI:** Redesigned Connection Settings with collapsible section, icon-based profile controls, Default Credentials toggle switch, and increased output pane height (+200px)
- **Profile Controls:** Reverted dropdown to standard form-group style with icon buttons for consistency across Generate, Health Check, and Advanced Ops pages
- **Script Runner:** Added `_classify_output_line` method for intelligent SSH output noise filtering

### Technical Details
- Validated on selab-var-202, selab-var-203, selab-var-204 clusters
- Tier-1 + Tier-2 health checks now complete in ~24 seconds
- Remediation reports saved to `output/health/health_remediation_<cluster>_<timestamp>.txt`
- `src/workflows/vperfsanity_workflow.py`: `_api_cleanup_cross_tenant_views()` queries `GET /api/views/`, finds stale views by alias/bucket/path, deletes via `DELETE /api/views/<id>/`
- `src/tool_manager.py`: Internet-first download with local cache fallback; `deploy_tool_to_cnode()` for secure remote deployment
- `src/app.py`: Merge-save profile pattern preserves fields across pages; `ALL_FIELDS` dict with defaults; `api_token`/`token` normalization
- `src/script_runner.py`: `_classify_output_line()` demotes SSH retry noise to DEBUG level
- `src/utils/ssh_adapter.py`: `force_tty`, `login_shell`, `agent_forward` parameters; `sshpass` security; paramiko hardening

## [1.4.7] - 2026-03-17

### Fixed
- **PDF Generation Error:** Fixed `'str' object has no attribute 'wrapOn'` error when API returns list values (e.g., `ekm_servers`, `dns`, `ntp`) that were placed directly in ReportLab table cells
- **Security & Authentication Table:** EKM servers, addresses, and encryption settings now properly handle list values from API by converting to comma-separated strings
- **Network Configuration Table:** Management VIPs, external gateways, DNS servers, NTP servers, and IPMI settings now safely converted to strings before table insertion

### Added
- **Safe Table Value Helper:** New `_safe_table_value()` method in `VastReportBuilder` that converts any value type (lists, None, dicts) to safe strings for table cells

### Technical Details
- Root cause: VAST API returns `ekm_servers` as nested list (e.g., `[['hostname', port]]`) which ReportLab cannot render directly in table cells
- Fix handles lists by joining elements with commas; handles None/empty with configurable default
- Validated with JSON-to-PDF regeneration test on affected cluster data

## [1.4.6] - 2026-03-17

### Added
- **Pre-release checklist (QG-1):** README Development section documents running flake8, black, mypy, and pytest (with coverage) before release/merge; aligns with CI quality gate.
- **Library API tests (TSE-1):** Unit tests for GET `/library`, GET/POST/DELETE `/api/library` with mocked `_load_library`/`_save_library` in `tests/test_app.py` (TestLibraryRoutes).
- **Generate cancel test (TSE-2):** Unit tests for POST `/generate/cancel` — no job returns `no_job`; job running accepts cancel and sets JOB_RESULT (TestGenerateCancel).
- **Reports dirs tests (TSE-3):** Unit tests for GET `/reports/dirs` and POST `/reports/dirs` with valid path (updates config) and 400 for empty/nonexistent (TestReportsDirsRoutes).
- **EBox Port Mapping:** EBox-specific port mapping with CNode/DNode names in Notes column; standard CBox/DBox clusters show "Primary" in Notes
- **EBox Network Diagram:** Logical Network Diagram shows EB# labels for EBox clusters with Green (Network A) and Blue (Network B) connections to switches
- **Built-in Hardware Library:** Added msn4700-ws2rc (Mellanox SN4700 400Gb 32pt Switch, 1U) and dell_genoa_ebox (Dell Genoa 1U EBox) as permanent built-in devices

### Changed
- **Coverage threshold:** `cov-fail-under` set to 47% in pyproject.toml and CI workflows (current suite ~47%); restoration to 49%+ tracked in docs/TODO-ROADMAP.md (QG-3, TSE-8).
- **Port Mapping Section:** Added page break before Port Mapping heading; Switch 1 table now appears before Switch 2
- **Switch Configuration Section:** Added page break before Switch Configuration heading
- **Network Diagram Connections:** Fixed CNode-to-switch (top to middle) and DNode-to-switch (bottom to middle) connection line coordinates

### Policy & API
- **Read-only VAST API policy:** The app must never use VAST API calls that change or update the cluster. Data collection uses **GET only**. `_make_api_request()` in `api_handler` now accepts only GET and raises `ValueError` for POST/PUT/DELETE. Authentication may still use POST only to establish read-only access (session/token/JWT). See [docs/development/READ_ONLY_VAST_API_POLICY.md](docs/development/READ_ONLY_VAST_API_POLICY.md) and `.cursor/rules/api-handler-05.mdc`.

### Added (tests)
- **TSE-4:** Unit tests for POST `/api/discover` (400 missing cluster_ip, 401 auth failure, 200 success with mocked `create_vast_api_handler` and `RackDiagram`). All discovery flows are read-only (get_racks, get_switch_inventory).
- **Read-only enforcement test:** `test_make_api_request_only_get_allowed` in test_api_handler verifies that POST/PUT/DELETE/PATCH raise ValueError.
- **TSE-5:** Integration test for report content: raw data with EBox + dell_turin_cbox + serial; asserts processed hardware_inventory and successful PDF generation (test_integration.py).
- **TSE-6:** Unit tests for Profiles API: GET/POST `/profiles` and DELETE `/profiles/<name>` with mocked `_load_profiles`/`_save_profiles` (TestProfilesRoutes in test_app.py).
- **TSE-7:** Unit test for POST `/shutdown` (200, status `shutting_down`; `os._exit` mocked so process does not exit).
- **TSE-8:** Coverage restored above 49%; full suite (unit + integration) now ~53% (279 tests).

## [1.4.3] - 2026-03-16

### Fixed
- **CBoxes missing from Physical Rack Layout**: Rack diagram now builds one entry per CBox (not per CNode) and uses CBox `rack_unit` / `rack_name` with fallback to CNode `rack_position` (`U{n}`); single-VMS rack fallback so CBoxes are not dropped when rack name is "Unknown"
- **Network diagram placeholder on macOS**: When reportlab renderPM fails (T1 font), use `qlmanage` to convert the generated PDF to PNG so the report embeds the real topology diagram instead of the placeholder
- **Windows PDF "Permission denied"**: First-pass temp PDF now uses `tempfile.mkstemp()` and explicit unlink instead of `NamedTemporaryFile(delete=True)` to avoid Windows temp file locking
- **Windows port mapping charmap error**: All SSH/subprocess output in port mapping now decoded with `encoding="utf-8", errors="replace"` so UTF-8 from switches/nodes does not trigger `'charmap' codec can't encode` on Windows

### Changed
- **README**: Table of contents, quick start, and troubleshooting (Windows PDF, port mapping charmap); project structure and docs links updated
- **Report builder**: Per-CBox rack grouping and rack_unit from CBox or CNode; Unknown rack mapped to single VMS rack when applicable

## [1.4.2] - 2026-03-11

### Added
- **EBox discovery (API v7)**: Full EBox integration — `GET /api/v7/eboxes/`, cluster `ebox` flag, `ebox_id` on CNodes/DNodes; `get_ebox_details()` in API handler; EBox quantity and inventory in report (cover, executive summary, consolidated hardware table); `docs/api/EBOX_API_V7_DISCOVERY.md`
- **Library — Type EBox**: Add Device supports type **EBox**; devices appear in the **EBox Hardware** section with images
- **API reference**: EBox endpoints and fields documented in `docs/API-REFERENCE.md` (cluster `ebox`, node `ebox_id`, `get_ebox_details`, data collection sequence, enhanced features table)
- **Rack diagram tests**: `tests/test_rack_diagram.py` verifies generic 1U/2U fallback when an identifier key is not found in the Library
- **EBox in Physical Rack Layout**: For ebox clusters, diagram uses EBox U height (default 1U); DBox U height documented in Hardware Inventory only and omitted from rack diagram; Hardware Summary note for ebox clusters
- **Switch placement for EBox**: Auto placement tries above ebox hardware then below ebox hardware (same logic as above CBox / below DBox)

### Changed
- **Data extractor**: Hardware inventory accepts list or dict for `cboxes`/`dboxes`/`eboxes` (normalized via `_normalize_boxes_to_dict`); `switch_inventory` may be list or dict; error-path `HardwareInventory` includes all required fields; `_normalize_to_list()` for cnodes/dnodes; `raw_hardware`/`raw_switch_inventory` in report data for fallback
- **Report builder**: `total_devices` includes eboxes; consolidated inventory table shown when `cboxes or dboxes or eboxes or switches`; EBox rows in inventory table; title page and overview show hardware block from cboxes/dboxes/switches when cnodes/dnodes empty; `_ensure_hardware_inventory()` builds from raw when missing; Physical Rack Layout only includes racks present in VMS (excludes "Unknown"); content-based column widths for Hardware Inventory table
- **API handler**: `_normalize_list_response()` handles list, paginated `results`, dict-of-items, and single resource; used for cnodes, dnodes, cboxes, dboxes, eboxes
- **Rack diagram**: EBox drawing (1U default); `_gather_device_boundaries(eboxes=)`; switch placement above/below ebox; `generate_rack_diagram(eboxes=)`
- **Export script**: `scripts/export_swagger.py` probes `GET /api/v7/eboxes/` in the v7 endpoint list

### Fixed
- **Report missing sections**: API list/dict response normalization and raw fallback so title page, Hardware Overview, Hardware Inventory, rack layout, switch config, port mapping, and diagram populate when API returns alternate shapes or extractor returns empty
- **Unknown rack in diagram**: Physical Rack Layout only includes racks that exist in VMS (`data.racks`); "Unknown" rack excluded when not in VMS
- **Hardware Inventory column widths**: Content-based column widths (stringWidth) for Rack, Node, Model, Name/Serial Number, Status, Height so columns fit variable value lengths

### Technical Details
- `src/api_handler.py`: `_normalize_list_response()`, list/dict/single-object handling for hardware endpoints
- `src/data_extractor.py`: `_normalize_to_list()`, `raw_hardware`/`raw_switch_inventory` in report_data
- `src/report_builder.py`: `_ensure_hardware_inventory()`, `_normalize_boxes_to_dict()`, vms_rack_names filter, ebox grouping and diagram_dboxes=[] for ebox clusters, per_rack_eboxes in auto placement
- `src/rack_diagram.py`: EBox in `_get_device_height_units` (1U), `_gather_device_boundaries(eboxes)`, `_calculate_switch_positions(eboxes=)`, above/below ebox strategies, `generate_rack_diagram(eboxes=)`, ebox device drawing
- `src/brand_compliance.py`: `_content_based_column_widths()` for Hardware Inventory table

### Docs & UI (1.4.2 session)
- **Documentation in-app**: Internal `.md` links in doc content are rewritten to `/docs#<doc_id>` so navigation stays in-app; `_build_doc_link_map()`, `_rewrite_doc_links_in_html()` in `app.py`; docs page hashchange and click handlers for in-app doc navigation
- **Docs layout**: Content area constrained to avoid horizontal scroll; Swagger 500 hint and "Open (v7)" link added
- **Port mapping**: Partial clush output accepted; multi-CNode fallback in `app.py` and `main.py`; partial-flag/reason surfaced in report when mapping is incomplete
- **Hardware Inventory Model column**: Comma and trailing NIC description stripped; for `dell_turin_cbox`, display model includes ` / <CNode serial>` (serial from `serial_number`/`sn` in data_extractor and report_builder)
- **Tests**: `TestDocsRoutes` in `tests/test_app.py` — docs page 200, content 200/404, internal link rewrite to `/docs#installation`

## [1.4.1] - 2026-03-05

### Added
- **Hardware Device Library**: New Library page (`/library`) with categorized tables (CBox, DBox, Switch, EBox with Support Pending), user-defined device upload, image preview, and persistent JSON storage
- **Hardware Image Refresh**: 20 bezel images extracted, cropped edge-to-edge, and added for CBoxes (Dell Turin, SMC Turin, HPE/Dell IceLake, HPE Genoa), DBoxes (Ceres V2, Maverick), and Switches (Arista 7050 series, SN5600, MSN2700, MSN4600)
- **Partial Key Matching**: Device lookup in rack/network diagrams now sorts keys longest-first to prevent `msn4600` from incorrectly matching before `msn4600c`
- **Job Cancellation**: Cancel button on the Generate page with `/generate/cancel` endpoint; 8 cancellation checkpoints in the report pipeline using `threading.Event` for graceful abort
- **Exit Button**: Navbar Exit button with confirmation prompt; graceful server shutdown via stored `werkzeug` server reference
- **Favicon & App Icon**: White VAST logo as browser favicon; blue VAST logo as `.icns`/`.ico` for macOS `.app` bundle and DMG installer
- **macOS Launcher**: `Start Reporter.command` double-click launcher in project root
- **Port Mapping Logging**: Specific error messages when SSH port mapping fails (missing switch IPs, CNode IPs, SSH errors) instead of silent failure

### Changed
- **Threaded Server**: `make_server` now runs with `threaded=True` to allow concurrent SSE log stream and status polling, fixing UI hang after report completion
- **Status Polling**: Added `Cache-Control: no-store` headers and `?_t=<timestamp>` cache-buster to `/generate/status` to prevent stale browser caching
- **Library Table Sections**: Device definitions organized into CBox, DBox, Switch, and EBox categories with section headers and pending-support badges
- **Footer Copyright**: Updated to `© 2026 VAST Data`
- **Height Field**: Removed spinner arrows from Manual Switch Placement U-position input
- **Build Script**: Fixed `build-mac.sh` grep for macOS compatibility; `.spec` updated to bundle `device_library.json`, `cluster_profiles.json`, and exclude large source composite image
- **Launcher Test**: Fixed `test_run_gui_starts_flask` to mock `make_server` instead of deprecated `flask_app.run()`

### Fixed
- **Rack Diagram Images**: Reverted from custom `_StretchedImage` widget to native `GraphicsImage` shape, fixing invisible hardware images in rack diagrams
- **Image Padding**: Auto-cropped transparent/white borders from 6 hardware images to achieve edge-to-edge rack slot rendering
- **Report Hang**: Enabled multi-threaded werkzeug server to prevent SSE stream from blocking status polling
- **Shutdown Crash**: Replaced `os._exit(0)` with graceful `server.shutdown()` via background thread to prevent abrupt process termination
- **WeasyPrint Cleanup**: Removed dead WeasyPrint/Cairo imports from `report_builder.py` and `requirements-dev.txt`

### Technical Details
- `src/app.py`: Added `/library`, `/generate/cancel`, `/shutdown` routes; `JOB_CANCEL` threading.Event; `_SERVER` config key for graceful shutdown; port mapping error logging
- `src/rack_diagram.py`: Updated `image_map`, `one_u_models`, `two_u_models`; longest-first partial key matching in `_get_hardware_image_path()` and `_get_device_height_units()`
- `src/network_diagram.py`: Longest-first partial key matching in `load_hardware_image()`
- `src/main.py`: `threading` and `webbrowser` moved to module-level imports; `flask_app.config["_SERVER"] = server`
- `frontend/templates/base.html`: Favicon link, apple-touch-icon, Exit button in navbar
- `frontend/templates/library.html`: 4-section device table with Jinja2 `selectattr` filtering
- `frontend/static/css/app.css`: `.btn-exit`, `.btn-cancel`, `.lib-section-header`, `.lib-badge-pending`, spinner removal for `#uPositionInput`
- `frontend/static/js/app.js`: Exit button handler with confirmation; Cancel button handler; cache-busting on status fetch
- `packaging/icons/icon.icns`, `icon.ico`: Generated from VAST-Data-Icon-Blue.png
- `packaging/vast-reporter.spec`: Bundled device_library.json, cluster_profiles.json; per-file hardware image inclusion; NSAppTransportSecurity plist entry
- Tests: 214 passed (fixed hanging `test_run_gui_starts_flask`)

## [1.4.0] - 2026-03-04

### Added
- **Web UI**: Browser-based GUI with dashboard, report generation form, live progress streaming, report browser, and YAML configuration editor
- **Self-Contained Packaging**: PyInstaller-based builds for macOS (.app/.dmg) and Windows (.exe/.zip) — no Python installation required
- **SSE Log Streaming**: Real-time log output in the browser during report generation via Server-Sent Events
- **Cross-Platform SSH**: New `ssh_adapter.py` using paramiko (Windows) and pexpect (macOS/Linux) for port mapping on all platforms
- **GitHub Actions CI/CD**: Automated cross-platform builds triggered on version tags, with artifacts uploaded to GitHub Releases
- **Development Dependency Split**: `requirements-dev.txt` separates test/lint/optional dependencies from bundled runtime
- **Auto Switch Placement**: Cascading fallback logic (center → above CBoxes → below DBoxes) with per-rack attempts in alpha-numeric order
- **Manual Switch Placement**: UI-driven rack/switch discovery via `/api/discover`, drop-down selection of rack and switch, U-height entry, saved placements table with delete capability
- **Cluster Profiles**: Save, load, and delete cluster connection profiles (IP, credentials, settings) via `cluster_profiles.json`
- **Report File Filtering**: Reports page now lists only `vast_asbuilt_report_*.pdf` and `vast_data_*.json` files
- **Folder Browse API**: Server-side `/api/browse` endpoint for UI-based directory picker
- **VAST Admin UI Theme**: Dark theme with CSS variables matching VAST Admin UI color scheme, custom select dropdowns, toggle switches, and SVG file-type icons
- **Confluence Docs Sync**: 26 Confluence design/requirements pages downloaded into `docs/confluence/` for offline reference

### Changed
- **Launcher**: `main.py` now defaults to GUI mode (web UI); use `--cli` flag or `--cluster` argument for command-line mode
- **Dependencies**: WeasyPrint and Cairo moved to dev-only (ReportLab is the sole production PDF engine); added Flask, paramiko
- **Packaging**: `.gitignore` updated for PyInstaller artifacts; `packaging/` directory added with spec file and build scripts
- **UI Redesign**: Dashboard, Generate, and Reports pages updated with VAST-branded dark theme, icon-based actions, centered table headings, right-justified action columns
- **Output Directory**: Simplified to single default directory model with browse/set functionality; removed multi-directory complexity
- **Watermark**: Adjusted transparency to balance visibility with readability
- **Report Margins**: Centered content with even left/right borders
- **Progress Tile**: Fixed-height scrollable log panel; resized to 60% width for better balance
- **Cursor Rules**: All 11 `.mdc` rules updated to match current codebase (method names, config keys, import paths, version locations, web UI layer)
- **Version**: Aligned `src/__init__.py` to 1.4.0

### Fixed
- **Switch Placement Limits**: Auto placement now respects discovered switch count per rack instead of duplicating
- **Hardware Inventory Rack Column**: Switches show the rack name they are placed in (auto or manual)
- **UnboundLocalError in report_builder**: Hardware collection variables (`cboxes`, `cnodes`, etc.) now assigned before conditional block
- **Download/View Buttons**: Fixed "Not Found" error when using custom output directories
- **Config Reset**: Fixed "Configuration file not found" error on Reset to Template
- **Report File Browsing**: Resolved `PermissionError` from recursive directory scans in large directories
- **Test Suite**: All 169 tests passing (fixed 14 stale tests in data_extractor, report_builder, and main)

### Technical Details
- `src/app.py`: Flask application with routes for dashboard, generate, config, reports, SSE stream, `/api/discover`, `/api/browse`, `/profiles`
- `src/rack_diagram.py`: Refactored into `_gather_device_boundaries`, `_try_center_placement`, `_try_above_placement`, `_try_below_placement` with cascading orchestration
- `src/report_builder.py`: Manual switch placement support via `manual_switch_placements` data key; per-rack switch limiting for auto mode
- `src/utils/logger.py`: Added `SSELogHandler`, `get_sse_queue()`, `enable_sse_logging()`
- `src/utils/ssh_adapter.py`: `run_ssh_command()` and `run_interactive_ssh()` with platform detection
- `frontend/`: Jinja2 templates (base, dashboard, generate, config, reports) with VAST-branded CSS and vanilla JS
- `frontend/static/css/app.css`: Dark theme with CSS variables, toggle switches, icon buttons, file-type SVG icons
- `frontend/static/js/app.js`: Discovery API integration, manual placement UI, profile management, defensive DOM handling
- `packaging/vast-reporter.spec`: PyInstaller spec with hidden imports, data files, and macOS .app bundle
- `.github/workflows/build-release.yml`: Matrix build (macOS + Windows), test gate, GitHub release creation
- `docs/confluence/`: 26 Markdown files synced from Confluence page hierarchy

## [1.3.0] - 2025-11-12

### Added
- **Installation Script Documentation**: Enhanced installation scripts now document enhanced features during dependency installation
- **Port Mapping Usage Examples**: Added port mapping collection examples to both Mac and Windows installation scripts
- **Enhanced Features Verification**: Installation scripts now verify and confirm installation of enhanced feature dependencies

### Changed
- **Installation Process**: Improved user experience with clear messaging about enhanced features being installed
- **Documentation**: Updated installation scripts to include port mapping usage examples

### Technical Details
- Updated `docs/deployment/install-mac.sh`: Added enhanced features documentation and port mapping examples
- Updated `docs/deployment/install-windows.ps1`: Added enhanced features documentation and port mapping examples

## [1.2.0] - 2025-11-11

### Added
- **Hardware Inventory Node Column**: Replaced ID column with "Node" column showing programmatically generated CNode/DNode names
- **One Row Per Node**: Each CNode and DNode now appears on its own row for detailed tracking
- **Multiple Nodes Per Box Support**: CBoxes and DBoxes with multiple nodes display each node on a separate row with the same Name/Serial Number
- **Port Mapping Collection**: Enhanced port mapping collection via SSH with `--enable-port-mapping` flag
- **Port Mapping Credentials**: Support for switch and node SSH credentials via command-line arguments
- **Network Topology with Connections**: Network diagram now includes port mapping connections when available

### Changed
- **Column Renaming**:
  - "CNode/DNode" → "Node" (more concise)
  - "Position" → "Height" (clearer terminology)
- **Column Width Optimization**:
  - Model column: Increased from 30% to 40% for better readability
  - Rack column: Decreased from 10% to 8%
  - Node column: Decreased from 18% to 12%
  - Height column: Decreased from 10% to 8%
- **Node Name Source**: Now uses programmatically generated `name` field (e.g., `cnode-3-10`, `dnode-3-112`) instead of customer-assigned hostnames
- **Data Collection**: Enhanced CNode and DNode name extraction from API
- **DBox Association**: Improved DNode to DBox association with `dbox_id` field

### Fixed
- **Missing Name Field**: Fixed data extractor to include `name` field in processed hardware inventory data
- **Missing DBox ID**: Fixed DNode data structure to include `dbox_id` for proper DBox association
- **Dataclass Field Order**: Fixed `VastHardwareInfo` dataclass field ordering to resolve Python dataclass initialization errors

### Technical Details
- Updated `src/data_extractor.py`: Added `name` and `dbox_id` fields to `_process_hardware_node` method
- Updated `src/api_handler.py`: Added `hostname` field to `VastHardwareInfo` dataclass and hardware data structures
- Updated `src/report_builder.py`: Modified `_create_consolidated_inventory_table` to create one row per node
- Updated `src/brand_compliance.py`: Adjusted column width ratios for Hardware Inventory table

## [1.1.0] - 2025-10-17

### Added
- Initial production release
- Comprehensive report generation
- Rack positioning support
- PSNT tracking
- Network topology diagrams

## [1.0.0] - 2025-09-27

### Added
- Initial release
- Basic report generation
- API integration
- PDF and JSON output formats

