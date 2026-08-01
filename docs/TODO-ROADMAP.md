# TODO & Roadmap — Planned Features and Enhancements

**Purpose:** Canonical **live** register of planned and in-progress work. Completed history lives in [`ROADMAP-ARCHIVE.md`](ROADMAP-ARCHIVE.md); shipped detail is in [`../CHANGELOG.md`](../CHANGELOG.md); the current point-in-time snapshot is in [`PROJECT-STATUS.md`](PROJECT-STATUS.md). Validated in CI (todo-tracking-09).

**Last updated:** 2026-08-01 — **v1.6.0 released**; branch protection on `main`. Pipeline tails closed. **M6 Phase C done:** [`agentic-dev-framework` v0.2.0](https://github.com/rstamps01/agentic-dev-framework/releases/tag/v0.2.0) adds the bootstrap installer (`adf_bootstrap.py` — idempotent, non-destructive, dry-run, new/adopt), adoption tiers (`core/tiers.yml`, L1/L2/L3), and the `new-project`/`adopt-existing` skills; 20 core skills, 30 ADF tests green, Framework CI green. This repo is ADF's first adopter. Remaining M6 (Phase D–E): pilot `adopt-existing` on VAST Plan Analyzer, then `framework-doctor` + portfolio PM. See [`PROJECT-STATUS.md`](PROJECT-STATUS.md) for the full snapshot and [`DECISIONS.md`](DECISIONS.md) for the decision log.

**Reference:** [PRE-RELEASE-QA-GAP-ANALYSIS.md](PRE-RELEASE-QA-GAP-ANALYSIS.md) (feature coverage and recommendations)

---

## Status key

| Status   | Meaning |
|----------|--------|
| Planned  | Not started; agreed as next or future work |
| In progress | Actively being worked on |
| Done     | Completed (move to CHANGELOG / release notes and archive in `ROADMAP-ARCHIVE.md`) |
| Deferred | Postponed; reason and target release noted |

### Work-item state machine

The autonomous delivery loop (see `.cursor/skills/deliver-autonomously` + `project-manager`) drives each tracked item through a canonical lifecycle. The table statuses above are the human-facing summary; the machine states are:

```
draft ──▶ ready-for-dev ──▶ in-progress ──▶ in-review ──▶ done
                                │                │
                                └──────▶ blocked ◀┘
```

| State | Meaning | Enters via | Leaves via |
|-------|---------|------------|------------|
| `draft` | Captured, not yet scoped/agreed | `intake-feature` | scoped + approved → `ready-for-dev` |
| `ready-for-dev` | Scoped, prioritized, unblocked | approval | `start-work` → `in-progress` |
| `in-progress` | Branch open, implementation underway | `start-work` | gate + PR → `in-review` |
| `in-review` | PR open / review + quality gate running | `open-pr` | approve/merge → `done`; changes → `in-progress` |
| `done` | Merged (and released where applicable) | merge | archived to `ROADMAP-ARCHIVE.md` |
| `blocked` | Waiting on a dependency/decision/escalation | any state | resolution → prior state |

Mapping to the summary key: `draft`/`ready-for-dev` → **Planned**; `in-progress`/`in-review` → **In progress**; `done` → **Done**; `blocked` → **Deferred** (with reason).

---

## Planned — Pipeline & ops follow-ups (2026-07-31)

*Source: prior-plan reconciliation (see [`PLANS-INDEX.md`](PLANS-INDEX.md), Bucket D). Genuinely-open items surfaced from `~/.cursor/plans/` that are in-scope for this repo.*

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| SEC-2 | **Enable GitHub branch protection on `main`.** Aligns with `change-control-07`. | Medium | **Done** (2026-08-01) | Applied via API (admin-bypass policy): required checks `quality-gate`, `unit-tests (3.11/3.12)`, `integration-tests`; `enforce_admins:false` keeps the `develop`→`main` release merge working for admins; force-push + deletion disabled. From plan `protect_main_branch_1260e0f8`. |
| OPS-1 | **Remote access to the reporter app (Windows `netsh portproxy`).** Document/support exposing the local Flask UI to a remote operator via a Windows port-proxy hop, for field machines where the browser runs elsewhere. | Low | Planned (confirm need) | From plan `expose_asbuilt-reporter_remotely_8b7d907f`. Confirm this is still needed before implementing. |

---

## Planned — Queued implementation plans (2026-06-16)

*Plans drafted and queued for execution this session. One additional plan will be generated before execution begins. Plan files live in `.cursor/plans/`.*

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| QP-1 | **Report & diagram refinements (incl. Node Management Map).** Add a Node Management Map (VMS device name -> hostname -> external mgmt IP) as two compact CNode/DNode tables under Network Configuration; resolve Port Mapping switch GUID -> hostname -> mgmt IP (Full Topology "Switch IP" shows mgmt IP; per-switch titles show name + GUID + mgmt IP); replace diagram switch designations (SWA/SWB/SP1/SP2) with hostname + mgmt IP; dynamic switch width with centered landing fan; populate Switch Configuration Active Ports & Port MTU. | Medium | Done (2026-06-16) | Plan: `.cursor/plans/node_management_map_table_6c99be75.plan.md`. All five sub-items implemented with TDD and verified via LAX-01 replay/render (221 tests pass; flake8/black clean). CNode/DNode Management Map tables + TOC subsections; Full Topology shows switch mgmt IP and per-switch titles show name + mgmt IP + GUID; diagram switch labels now name + mgmt IP; dynamic `switch_w`/`device_w` centers the landing fan within each switch box (`_build_landing_slots` / `_fan_landing_x` / `_dynamic_switch_width`); Active Ports/MTU recomputed (count `up`/`active`, most-common non-zero MTU) in both `api_handler` and a defensive `report_builder` recompute. |
| QP-2 | **Per-cluster result segmentation by PSNT.** Write all generated artifacts (reports, vnetmap/workflow outputs, diagrams, health, bundles, ops logs) under per-cluster subdirectories keyed by a resolved cluster identifier (PSNT -> GUID -> name -> IP fallback) with a `cluster.json` marker; make discovery/scanning folder-scoped with a backward-compatible legacy read path. Eliminates cross-cluster data intermingling when every cluster shares tech-port IP `192.168.2.2`. | High | Done (2026-06-16) | Plan: `.cursor/plans/segment_results_by_psnt_739a98da.plan.md`. New `src/utils/cluster_paths.py` (+ `cluster_output.py` write helper); `cluster_key` threaded through app/one-shot/advanced-ops orchestration with **early** identity resolution in one-shot so operation artifacts segment before the report phase; folder-aware `_find_latest_vnetmap_output` / scanner / bundler with legacy-flat fallback. Read-side association keys on PSNT/GUID/name (never the shared tech-port IP), so two clusters on `192.168.2.2` stay separate. Gated by `output.segment_by_cluster` (default true); explicit CLI `--output-dir` honored verbatim. Code-reviewed (2 blockers found & fixed: ops-artifact segmentation + IP-based collapse). Verified: 1342 broad + 287 QP-2 + 119 app + 26 one-shot logic tests pass; flake8/black clean. |
| TPM-1 | **Teleport (tsh) connection mode + Connection Settings UI redesign.** Add a third connection method alongside Tech Port and VMS HTTPS that tunnels the cluster API (443) and CNode SSH (22) through `tsh ssh -L` dual port forwards so reports and `vnetmap`/port mapping work against Teleport-only clusters. Redesign the Connection Settings tile: three-way connection-mode radios (Tech Port / VMS Mgmt / Teleport) replacing the Advanced-menu Tech Port checkbox, Autofill Passwords promoted to a toggle (ON locks defaults / OFF keeps usernames + clears passwords), and Teleport node/user fields shown only in Teleport mode, persisted in profiles. | High | Done (2026-06-19) | New `src/utils/teleport_tunnel.py` (`TeleportTunnel` w/ preflight + dual `-L` forwards); `port`/`jump_port` threaded through `ssh_adapter`, `tool_manager`, `script_runner` (`set_ssh_port`); `ssh_host`/`ssh_port` honored by `vnetmap_workflow`, `external_port_mapper`, `switch_config_workflow`, `health_checker`, and one-shot (`_setup_teleport_tunnel`, `_validate_teleport_tunnel`). `app.py` `generate_start`/`_run_report_job`/`/api/discover` launch the right tunnel per mode. `frontend/templates/reporter.html` UI + CSS; `teleport` config block in `config.yaml.template`. Tests: `tests/test_teleport_tunnel.py` (new) + `tests/test_ssh_adapter.py` explicit-port cases. flake8/black clean. **Shipped as Beta for v1.5.8** — UI "Beta Feature" badge above the Teleport Mode option; flagged beta in CHANGELOG / `RELEASE_NOTES_v1.5.8-beta.md` / `README.md`. Beta exit criteria: end-to-end report + `vnetmap` validated against multiple live Teleport clusters and node-resolution input forms confirmed before the production v1.5.8 tag. |
| QP-3 | **UI & software management enhancements.** Four parts: (1) move Deployment Tools Status + Update Tools buttons into the global top nav with an orange "needs attention" dot when tools are missing or >=10 days old; (2) phased in-app auto-update for Mac/Windows (2a notify + manual download on stable channel with pre-release opt-in, 2b auto-apply/relaunch follow-up; ties to UPD-1); (3) auto-close the server when all browser windows close (heartbeat + idle watchdog, guarded against mid-job shutdown); (4) opt-in anonymous usage telemetry + local ROI surface, plus a central-receiver design spec. | Mixed (1 Medium/now, 2-4 Medium) | **Done** (2a only for item 2; 2b auto-apply/relaunch deferred) | Items 1, 3, 4, and 2a all shipped. (1) Global-nav tools control + `GET /api/tools/status` / `POST /api/tools/update`, `TOOL_FRESHNESS_WARN_DAYS` canonical in `tool_manager`. (3) Heartbeat (`POST /api/heartbeat`) + watchdog in `run_gui`, mid-job guard, `auto_shutdown` config. **Update 2026-06-19:** changed to OPT-IN / OFF by default — background-tab timer throttling could shut the app down while a tab was still open; enable via `auto_shutdown.enabled: true`. (4) `src/usage_metrics.py` (opt-in, anonymous, local-only) + dashboard "Usage & Privacy" card + `GET /api/telemetry/status` / `POST /api/telemetry/consent` + `telemetry` config + `docs/development/TELEMETRY.md` receiver spec. (2a) `src/updater.py` (GitHub Releases check, semver+channel) + `GET /api/update/status` + in-app banner + `updates` config. Verified: 1385 broad + targeted route/logic tests pass, flake8/black/mypy clean. **Deferred:** item 2b (auto-apply/relaunch — platform-specific, risky). |

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
| QG-2 | Fix or document flake8/black/mypy exceptions to achieve green quality gate | Done | Followed MYPY_FIX_SUGGESTIONS notes (retired in v1.5.8 cleanup; see `pre-1.5.8-cleanup` tag): types-paramiko, _MEIPASS, var annotations, return casts, api_handler session/optional, network_diagram Path/float, report_builder tuple/int/float; mypy passes. |
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

*Source: EBOX-HARDWARE-TABLE-IMPLEMENTATION-PLAN notes (retired in v1.5.8 cleanup; see `pre-1.5.8-cleanup` tag)*

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

## Planned — Tech-Port follow-ups (v1.5.7+)

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| SR-2 | **Cosmetic: "rejected candidate password" warning on Onyx switches.** Surfaced during selab-var-202 log review. The Onyx SSH pre-probe in `src/utils/switch_ssh_probe.py::probe_switch_password` correctly identifies the working password but logs a warning for each *rejected* candidate even on success runs ("rejected candidate password 1/3 for 10.x.x.x — trying next"). The warning fires as expected (it's an authentication-attempt message) but is misleading because the next candidate succeeds and the operator sees `[WARN]` lines in the log even though the probe is succeeding. Plan: demote each per-candidate rejection to `debug` level, keep a single `info` summary line on success ("authenticated 10.x.x.x with candidate 2/3"). Cosmetic only — no functional impact, no security impact. | Low | Deferred | Out of scope for v1.5.7 release; can be picked up alongside any future RM-* log-formatting pass. |
| RPT-VALIDATION-1 | **UI rendering bug: Node User field's programmatic value not rendering.** Surfaced during TP-1 / TP-2 manual validation. When the operator selects a saved profile or programmatically populates the Node User input via `value=...`, the visible text in the field stays empty until the operator clicks into it and types. The underlying form value is correct (form submission sends `vastdata`), but the rendered DOM doesn't reflect it. Likely a missing input-event dispatch in the profile-restore code path. Cosmetic / UX. | Low | Planned | Document only; no code change needed for v1.5.7. |
| RPT-VALIDATION-2 | **UI logic bug: Re-filling Node User clears Node Password.** Surfaced same session as RPT-VALIDATION-1. Re-typing into the Node User field after a profile restore clears the Node Password field, forcing the operator to re-enter both. Likely a stale `change` listener that resets the password when User changes. Cosmetic / UX. | Low | Planned | Document only; no code change needed for v1.5.7. |


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


## Next steps (current focus)

> **Execution status (2026-07-31):** **v1.6.0 development is segmented on `develop`** as baseline commit `e48e581` (M0 of the agentic CI/CD pipeline plan) — committed + documented but **not released** (no tag). Focus is now shifting to the CI/CD pipeline build (rules, AGENTS.md, hooks, GitHub scaffolding, lifecycle skills, then release hardening); the `v1.6.0` tag/release will run through the new prepare-release/ship-release path once M5 lands (or sooner if released standalone). Plans are in `.cursor/plans/`.
>
> **Prior execution status (2026-07-21):** Preparing **v1.6.0**. Added robust Teleport `tsh` auto-discovery (TPM-2): the app resolves `tsh` on PATH and well-known install locations, augments `PATH` at startup, and exposes a Teleport Settings section (path field + Run Discovery + persistence) plus a green/yellow install-status pill on the Reporter tile and in Advanced Configuration. New endpoints `GET /api/teleport/status` and `POST /api/teleport/discover`, new guide `docs/TELEPORT-MODE.md`. Version bumped `1.5.8 → 1.6.0`.

1. **v1.6.0 released (Done, 2026-08-01):** Shipped via prepare-release/ship-release — tag `v1.6.0`, `build-release.yml` (blocking gates) builds macOS arm64/Intel `.dmg` + Windows `.zip`. QA phase (cross-OS plan, `qa-cross-os` CI, update-pill staged dry-run) complete. M5 hardening (blocking gates, `hotfix`/`rollback`/`maintain`, `.cursor/pipeline.yml`) shipped.
2. **Post-release verification (in progress):** Confirm the `build-release` run is green and artifacts attach; then from a real 1.5.8 build online confirm the **UPDATE AVAILABLE** pill flips to 1.6.0 (QA §6b), and on packaged mac/win builds launched from Finder/Explorer confirm tsh pill state + Run Discovery persistence + Teleport preflight.
3. **M6 — ADF portability extraction:** Extract the portable core into a new `agentic-dev-framework` repo (manifest-driven adoption). Next milestone.
4. **Teleport beta exit (TPM-1/TPM-2 follow-up):** Complete live Teleport validation against multiple clusters before removing the Beta flag in a subsequent release.
5. **Documentation refresh (remaining):** DOC-13 (API reference Prometheus endpoints), DOC-14 (Confluence sync).
6. **UI Enhancement Phase (UI-1 through UI-9):** Remaining: Phase 1 foundation restyle (UI-5), enhanced checklist rows (UI-4), Phase 2/3 (UI-8, UI-9).
7. **Test suite:** TSE-9 (coverage toward 80%).
8. Before each release: update this file (status, Last updated, move completed items to Done).
9. CI validates this file exists and contains required sections (see todo-tracking rule and CI job).

---

## Planned — Port Mapper Integration (low priority)

*Source: Review of Jeff's Port Mapper (pm.py v5.6) — design-time switch port planning tool.*

| ID    | Item | Priority | Status  | Notes |
|-------|------|----------|---------|-------|
| PMI-1 | **Extract switch model metadata:** Extract `SWITCH_LAYOUTS` dictionary (11 switch models: SN3700, SN4600, SN5400, SN5600, Arista 7050DX4/7060DX5/7060X6, Cisco 9332D/9364D/9364E) into shared `src/switch_models.py` reference. Enriches rack diagrams, port mapping reports, and health checks with port counts, native speeds, and vendor names. | Low | Planned | Low effort; immediate value for `rack_diagram.py` and `health_checker.py` model awareness |
| PMI-2 | **Planned-vs-actual port validation health check:** Compare planned port assignments (from Port Mapper output or saved JSON) against actual MAC-to-port mapping collected by `ExternalPortMapper`. Detect wrong port assignments, missing connections, cross-cabled nodes, and reserved ports in use. New Tier 3 health check. | Low | Planned | Requires defining import format for planned port maps; high diagnostic value |
| PMI-3 | **Switch face-plate diagram in reports:** Port the `PortDrawer` class and switch face-plate PNG overlays into the PDF report's Switch Port Mapping section. Color-coded visual port diagrams supplement existing table-based data. | Low | Planned | Medium effort; depends on PMI-1 for model metadata; visually impactful for reports |
| PMI-4 | **Generalized LLDP walk for Mellanox Onyx switches:** `ExternalPortMapper._parse_onyx_lldp_for_ipl` still requires symmetric port numbers on `Eth1/29..Eth1/32`. Port the `switch_hostname_map` / `spine_ips` generalized walk (already live for Cumulus) onto the Onyx path so spine uplinks on arbitrary ports are discovered in Onyx-only deployments. | Low | **Done** | Generalized walk mirrors the Cumulus rewrite; reuses `_classify_edge` / `_resolve_neighbor_to_switch_ip`; legacy narrow scan preserved when no hostname map is supplied. 4 new tests under `TestOnyxLldpGeneralizedWalk`. |
| PMI-5 | **Capture `vnetmap` fabric-report for offline LLDP recovery:** `vnetmap.py` writes `/vast/log/vnetmap-…txt` on cnode-1 with a complete `LLDP neighbors on <IP>:` dump for every switch (leaves **and** spines). Extend `src/workflows/vnetmap_workflow.py` to retrieve that file and append its contents to the main `vnetmap_output_*.txt` the reporter consumes, so `vnetmap_parser._parse_lldp_neighbors` can recover real spine uplinks without any per-switch SSH call. | Low | **Done** | `_step_save_output` now fetches `/vast/log/vnetmap-*.txt` via SSH, appends it behind a delimiter to the saved output, and records `fabric_report_path` / `fabric_report_bytes` in the results JSON. 9 new tests under `TestVnetmapFabricReportCapture` (incl. end-to-end parseability by `VNetMapParser`). |

---

## RFE and other tracking

- **RFE:** Requests for Enhancement from Confluence (page 6664028496) are tracked as GitHub issues or referenced here when work begins.
- **Session-level work:** Use Cursor TODO tracking during sessions; promote agreed next steps to this roadmap.
