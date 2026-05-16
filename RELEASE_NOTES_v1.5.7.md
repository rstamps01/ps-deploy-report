# Release Notes — v1.5.7

**Date:** 2026-05-15
**Branch:** develop → main
**Previous release:** v1.5.6 (2026-04-23)
**Artifacts:**
- [VAST-Reporter-v1.5.7-mac.dmg](https://github.com/rstamps01/ps-deploy-report/releases/download/v1.5.7/VAST-Reporter-v1.5.7-mac.dmg)
- [VAST-Reporter-v1.5.7-win.zip](https://github.com/rstamps01/ps-deploy-report/releases/download/v1.5.7/VAST-Reporter-v1.5.7-win.zip)

---

## Executive Summary

v1.5.7 is the **CNode Tech-Port discovery + InfiniBand cluster correctness** release. It closes a stack of seven items uncovered while validating Tech-Port mode end-to-end on an Ethernet cluster (`selab-var-202`) and an IB cluster (mammoth) — a workflow where the operator plugs a laptop directly into a CBox tech port at `192.168.2.2` and the app auto-discovers VMS, opens an SSH/443 tunnel, and runs the report pipeline against the cluster's true management IP without the operator ever needing to know the cluster's address.

The seven items break into three parallel themes:

1. **VMS auto-discovery** (TP-1, TP-2) — broaden management-IP parsing to all RFC1918 ranges and replace the single-pick name heuristic with empirical TCP/443 candidate probing, so the right management IP is selected on Ethernet, IPoIB, and CGNAT clusters alike.
2. **InfiniBand cluster correctness** (SR-1, SR-3, SR-4, SR-5) — route `/api/switches/` through the VMS tunnel, resolve IB switch GUIDs to their management IPs in port-mapping output, use the API as authoritative source for cluster network type, and wrap 60-character IB MAC GIDs inside fixed-width PDF table cells.
3. **Offline verification infrastructure** (DEV-1 partial) — new `--from-json` CLI flag for regenerating PDF reports from a saved `vast_data_*.json` intermediate without touching the API or Data Extractor layers.

The release also commits three new hardware library devices (Mellanox SN8700-HS2F IB switch, Cisco Nexus 9332D-GX2B switch, Cisco UCS C225 EBox) with their 1U rack images.

No breaking changes. No config file format changes. No removal of CLI options — only an addition (`--from-json`).

---

## Highlights

### TP-1 / TP-2 — VMS auto-discovery on any RFC1918 cluster

Pre-fix, `parse_management_ip()` was hard-coded to the `10.x.x.x` family with no interface-name filtering, so IPoIB clusters (`bond0:m 172.16.x.x`) and CGNAT clusters (`em3 100.64.x.x`) either failed parsing or selected the wrong IP. The single-pick name heuristic would also return the first match by interface-name priority — and on a cluster where multiple candidates parse but only one serves the API, the wrong IP was selected and `Connection refused` followed.

Two fixes in `src/utils/vms_tunnel.py`:

1. **TP-1 (`7b94453`):** `parse_management_ip()` widened to all RFC1918 ranges (`10/8 + 172.16/12 + 192.168/16`) plus CGNAT `100.64/10`, with `lo` / `bond` / `peer` interfaces excluded from the candidate sweep, `:m` aliases prioritised, and a TCP/443 short-circuit on the first responding candidate.
2. **TP-2 (`f49aa2b`):** New `parse_management_ip_candidates()` returns an ordered candidate list (Eth base IPs first, IB base IPs next, `:m`/bond aliases last), and `_first_443_reachable()` probes them in order until one responds on TCP/443 within a short timeout.

**Live-validated end-to-end on both clusters:**

| Cluster | Network | Winning candidate | Why |
|---|---|---|---|
| mammoth (IB) | IPoIB + CGNAT | `em3 100.64.44.2` | Beats `bond0:m 172.16.128.4` because em3 responds to TCP/443 first |
| selab-var-202 (Eth) | RFC1918 | `bond0:m 10.143.11.202` | Wins after `192.168.2.2` (laptop-side tech port) probes CLOSED on 443 |

**Coverage:** 60/60 tests in `tests/test_vms_tunnel.py`; module local coverage 88%.

### SR-1 — `/api/switches/` no longer bypasses the VMS tunnel on Tech-Port mode

Pre-fix, `vnetmap_workflow._get_switch_ips_from_api()` fell back to the user-entered cluster IP when `tunnel_address` wasn't threaded into `_credentials`. In Tech-Port mode the user-entered IP is a CNode tech-port IP that doesn't serve the management API, so the call hit `Connection refused` on TCP/443 and the workflow silently mis-classified the cluster as InfiniBand → ran `vnetmap.py … -ib` → `ibnetdiscover` failed → workflow fell back to whatever cached vnetmap existed locally. The report still completed only because of the fallback.

Fixed in `src/app.py::_run_report_job` (commit `8bba3aa`) by threading `tunnel_address` from `VMSTunnel.connect()` into the `vnetmap_creds` dict whenever the VMS tunnel is active. All cluster-API calls inside the workflow now flow through the tunnel.

**Impact:** Tech-Port mode runs against Ethernet clusters now correctly identify the cluster as Ethernet on the first attempt; no "Connection refused" red herring in the workflow log.

### SR-3 — IB cluster GUIDs resolve to switch designations in Port Mapping

On IB clusters, `vnetmap.py` writes a 16-byte hex GUID into the topology's `switch_ip` column instead of an IP address (because IB fabric devices are addressed by GUID, not IP). `EnhancedPortMapper._build_switch_map` keyed exclusively on the API-supplied `mgmt_ip`, so every IB row hit the `Unknown switch IP` warning branch and rendered as `SW?-<port>` in the PDF Port Mapping section.

Three coordinated changes (commit `b1cfde9`):

1. **`src/vnetmap_parser.py`** — new `_parse_ib_switch_headers()` extracts `guid` / `hostname` / `model` / `internal_subnet` from the per-switch `Switch MF0;…` anchor lines that `vnetmap` emits at the top of each IB output block, and exposes them as `parse()["ib_switch_headers"]`.
2. **`src/enhanced_port_mapper.py`** — new `_add_ib_guid_aliases()` resolves each IB header against `self.switches` by hostname (case-insensitive; tries `name` / `hostname` / `host_name`) and adds the GUID as a same-record alias key in `self.switch_map`, so a topology row keyed by GUID hits the same switch record as a row keyed by `mgmt_ip`.
3. **`src/data_extractor.py`** — plumbs `ib_switch_headers` from the parser into the `EnhancedPortMapper` constructor for both the live `vnetmap` workflow path and the static `vnetmap` file path.

**End-to-end on the mammoth IB fixture:** 40 topology rows, **0 "Unknown switch IP" warnings (was 40)**, all GUIDs resolved to `SWA/SWB-P<n>`. Ethernet back-compat: the `selab-var-202` fixture has 0 IB headers so behaviour is unchanged.

**Coverage:** 12 new tests (5 parser + 7 port-mapper); 397/397 SR-3 blast-radius regression.

### SR-4 — API `net_type` as authoritative source for cluster network type

Pre-fix, `vnetmap_workflow` used a "switches present → Ethernet" heuristic when deciding whether to invoke `vnetmap.py` in Ethernet or IB mode. But on IB clusters with a separate management network, `/api/switches/` returns the IB switches' management-net IPs and the heuristic misfired, sending the wrong `vnetmap.py` mode and either running `ibnetdiscover` against an Ethernet cluster or vice versa.

Three new helpers in `src/workflows/vnetmap_workflow.py` (commit `aae9ef7`):

- **`_normalize_net_type()`** — maps any VAST API spelling (`INFINIBAND` / `Ethernet` / `Eth` / etc.) to a canonical `"IB"` / `"ETH"` / `None`.
- **`_get_net_type_from_api()`** — probes `/api/v7/vms/1/network_settings/` (the same endpoint `api_handler.get_cluster_network_configuration` already walks for the report) and extracts `data.boxes[*].hosts[*].vast_install_info.net_type`.
- **`_resolve_network_type()`** — consults sources in priority order: (1) explicit `_credentials["net_type"]` override (for future override paths from `app.py` / `oneshot_runner.py`), (2) authoritative API probe, (3) legacy switches-list heuristic as a last-resort fallback.

`_step_generate_export_commands` now calls `_resolve_network_type` and emits an explicit decision line — `[API] net_type=IB — using InfiniBand mode despite switches in /api/switches/` — so the operator can see exactly why each mode was chosen.

**Coverage:** 14 new tests (5 normalization, 6 resolution, 3 API-probe shape); 176/176 workflows regression.

### SR-5 — IB MAC GIDs wrap inside fixed-width PDF table cells

InfiniBand MAC addresses are 20-byte port GIDs that render as ~60-character hex strings with colons (`fe:80:00:00:00:00:00:00:b8:cb:f7:03:00:fb:6a:60`). They wouldn't wrap in fixed-width Port Mapping table columns and rendered overlapping the adjacent Switch / Network columns in the PDF.

Fixed in `src/report_builder.py` (commit `78e1a19`) with a new module-level `_format_mac_cell` helper that splits MACs by colons in 7-byte chunks and joins with `<br/>` inside a `Paragraph`, then used by `_create_vnetmap_topology_tables` for both Full Topology and Per-switch tables. Ethernet MACs (17 chars) are unchanged; only IB GIDs wrap.

**Coverage:** 8 new tests in `tests/test_report_builder.py::TestSR5FormatMacCell`. Operator-verified visually on the mammoth fixture before this branch was committed.

### `--from-json` offline replay flag (DEV-1 partial)

A permanent CLI surface for regenerating PDF reports from a saved `vast_data_*.json` intermediate without touching the API or Data Extractor layers. Closes the offline-replay slice of DEV-1 ("Report from JSON") and provides durable verification infrastructure that compensates for the **permanent loss of live mammoth IB cluster access on 2026-05-15** — all SR-3 and SR-4 verification was performed against saved fixtures using this rail.

Implemented in `src/main.py` (commit `6ad3385`):

- **`_run_from_json(json_path, output_dir, logger)`** helper validates the path → `json.load` → ensures output dir exists → builds a deterministic `vast_asbuilt_report_<cluster>_<timestamp>_replay.pdf` filename → calls `VastReportBuilder.generate_pdf_report` → translates failure into `return 1`.
- **`run_from_json()`** argparse wrapper accepts `--from-json <path>`, `--output` / `--output-dir`, `--config` / `-c`, and `--verbose` / `-v`.
- **`main()`** routes `--from-json` to `run_from_json()` before the existing `--gui` / `--cli` dispatchers.

The full DEV-1 ("Report from JSON" UI tile under Developer mode) remains pending and tracked in `docs/TODO-ROADMAP.md`.

**Usage:**

```bash
python3 -m src.main --from-json import/Reporter-v-Tests-results/vast_data_selab-var-203_20260422_235751.json --output /tmp/replay
# Produces: /tmp/replay/vast_asbuilt_report_<cluster>_<timestamp>_replay.pdf
```

**Coverage:** 12 new tests in `tests/test_main_from_json.py`.

### Hardware library additions

Three new entries committed to the user device library (`config/device_library.json`) with their 1U rack images bundled into the `.dmg` / `.zip`:

| Identifier key | Type | U Height | Description |
|---|---|---|---|
| `mqm8700-hs2f` | switch | 1U | Mellanox SN8700-HS2F IB 200Gb 40-port |
| `nexus_c9332d_gx2b` | switch | 1U | Cisco Nexus C9332D-GX2B |
| `cisco_ebox` | EBox | 1U | Cisco UCS C225 EBox |

---

## Fixed

- **TP-1 (`src/utils/vms_tunnel.py`)** — `parse_management_ip()` now matches all RFC1918 ranges plus CGNAT 100.64/10, excludes `lo` / `bond` / `peer` interfaces from the candidate sweep, and short-circuits on the first TCP/443-reachable candidate.
- **TP-2 (`src/utils/vms_tunnel.py`)** — new `parse_management_ip_candidates()` and `_first_443_reachable()` replace the single-pick name heuristic with empirical TCP/443 probing.
- **SR-1 (`src/app.py::_run_report_job`)** — `tunnel_address` is now threaded into `vnetmap_creds` whenever the VMS tunnel is active, so `/api/switches/` and other workflow API calls flow through the tunnel instead of falling back to the user-entered cluster IP.
- **SR-3 (`src/vnetmap_parser.py`, `src/enhanced_port_mapper.py`, `src/data_extractor.py`)** — IB switch GUIDs in the topology now resolve to their API switch records via a hostname-keyed alias map, eliminating "Unknown switch IP" warnings and `SW?-<port>` rendering on IB clusters.
- **SR-4 (`src/workflows/vnetmap_workflow.py`)** — cluster network type now sourced from `/api/v7/vms/1/network_settings/` instead of the unreliable "switches present → Ethernet" heuristic; explicit decision logged at workflow time.
- **SR-5 (`src/report_builder.py`)** — IB MAC GIDs (~60 chars) now wrap inside fixed-width PDF Port Mapping table cells via a `_format_mac_cell` Paragraph helper, no longer overlapping adjacent columns.

---

## Added

- **`--from-json` CLI flag (`src/main.py`, DEV-1 partial)** — offline-replay rail for regenerating PDFs from saved `vast_data_*.json` intermediates. 12 new tests in `tests/test_main_from_json.py`.
- **`src/utils/vms_tunnel.py`** — `parse_management_ip_candidates()` and `_first_443_reachable()` helpers (TP-2). 60 tests pass on `tests/test_vms_tunnel.py`.
- **`src/vnetmap_parser.py`** — `_parse_ib_switch_headers()` and the `ib_switch_headers` key on `parse()` output (SR-3).
- **`src/enhanced_port_mapper.py`** — `_add_ib_guid_aliases()` and the `ib_switch_headers=` constructor parameter (SR-3).
- **`src/workflows/vnetmap_workflow.py`** — `_normalize_net_type()` / `_get_net_type_from_api()` / `_resolve_network_type()` helpers, plus `[API] net_type=…` decision logging (SR-4). 14 new tests in `tests/test_workflows.py::TestSR4NetTypeOverride`.
- **`src/report_builder.py`** — module-level `_format_mac_cell()` helper for IB GID wrapping (SR-5). 8 new tests in `tests/test_report_builder.py::TestSR5FormatMacCell`.
- **Hardware library devices** — `mqm8700-hs2f` (Mellanox SN8700-HS2F IB switch), `nexus_c9332d_gx2b` (Cisco Nexus C9332D-GX2B switch), `cisco_ebox` (Cisco UCS C225 EBox) in `config/device_library.json` with matching 1U PNG assets in `config/hardware_images/`.
- **`docs/issues/SR-1`, `docs/issues/SR-3`, `docs/issues/SR-4`, `docs/issues/SR-5`** — per-item summaries with symptom, root cause, fix design, acceptance criteria, and verification evidence.

---

## Changed

- **`src/data_extractor.py`** — both the live `vnetmap` workflow path and the static `vnetmap` file path now plumb `ib_switch_headers` into the `EnhancedPortMapper` constructor (SR-3).
- **`src/main.py`** — `main()` now routes `--from-json` to `run_from_json()` before the existing `--gui` / `--cli` dispatchers.
- **`docs/TODO-ROADMAP.md`** — new "Done — Tech-Port stack (v1.5.7, 2026-05-15)" section with all seven items and commit references; new "Planned — Tech-Port follow-ups (v1.5.7+)" section for SR-2 (deferred) and the two cosmetic UI defects (RPT-VALIDATION-1 / RPT-VALIDATION-2) surfaced during TP-1/TP-2 manual validation.

---

## Deferred

- **SR-2 — cosmetic "rejected candidate password" warning on Onyx switches.** The Onyx SSH pre-probe in `src/utils/switch_ssh_probe.py::probe_switch_password` correctly identifies the working password but logs a warning for each rejected candidate even on success runs. Cosmetic only — no functional or security impact. Tracked in `docs/TODO-ROADMAP.md` under Tech-Port follow-ups.
- **RPT-VALIDATION-1 / RPT-VALIDATION-2 — cosmetic UI defects.** Node User field's programmatic value not rendering after profile restore (RPT-VALIDATION-1); re-typing into Node User clears Node Password (RPT-VALIDATION-2). Cosmetic / UX only; documented for future cleanup.

---

## Test Coverage

- **Unit tests:** 1173 passing (up from 1110 in v1.5.6; +63 new tests across TP-1/TP-2, SR-3, SR-4, SR-5, and `--from-json`).
- **Integration tests:** 16 passing.
- **Full-suite coverage:** 65.34% (gate: 60%; up from 62.9% in v1.5.6).
- **Full CI pipeline green on `feature/tp-1-techport-discovery` ([run 25952806261](https://github.com/rstamps01/ps-deploy-report/actions/runs/25952806261)):** todo-list-check, quality-gate, integration-tests, advanced-ops-tests, health-check-tests, unit-tests (3.12). UI tests and build-smoke correctly skipped on the feature branch (gated to develop/main per `ci-pipeline-13.mdc`).

---

## Upgrade Notes

- **No breaking changes.** No config-file format changes, no removal of existing CLI options.
- Download `VAST-Reporter-v1.5.7-mac.dmg` or `VAST-Reporter-v1.5.7-win.zip` from the GitHub Release page and replace the existing `VAST Reporter.app` / `vast-reporter.exe`.
- **Tech-Port mode operators:** plug into a CBox tech port at `192.168.2.2` and run as normal — auto-discovery now works on Ethernet, IPoIB, and CGNAT clusters without operator intervention.
- **InfiniBand cluster operators:** rerun any older saved `vast_data_*.json` IB intermediates through the new `--from-json` flag to regenerate the PDF with corrected GUID-resolved Port Mapping rows and properly-wrapped IB MAC GIDs.
- **Heterogeneous-fleet RM-15/RM-16 fixes from v1.5.6 are preserved** — no regressions in switch credential handling.

---

## Known Limitations

- **SR-2 (cosmetic Onyx pre-probe rejection warning) deferred** to a future log-formatting pass. Operator may see one or two `[WARN]` lines per Onyx switch during pre-probe even on success runs. Cosmetic only.
- **DEV-1 UI tile pending** — `--from-json` is currently CLI-only. The full Developer-mode "Report from JSON" UI tile remains tracked as a future enhancement.
- **Mammoth IB cluster live access permanently lost on 2026-05-15.** All SR-3 and SR-4 verification was performed against saved fixtures via the new `--from-json` rail. Future IB-cluster correctness work will rely on the same offline-replay infrastructure until live IB access can be re-established.
- **Coverage target remains 60%;** roadmap target is 75%+ (see `docs/TODO-ROADMAP.md` TSE-9). Current 65.34% is a +2.4 ppt improvement over v1.5.6.

---

## Commit Map

| Commit | Subject | Stack item |
|---|---|---|
| `7b94453` | fix(vms-tunnel): support RFC1918 mgmt IPs + 443 short-circuit | TP-1 |
| `f49aa2b` | fix(vms-tunnel): empirically probe VMS mgmt IP candidates on 443 | TP-2 |
| `6f421ac` | docs(issues): track SR-1 — /api/switches direct-cluster-IP bypass | SR-1 docs |
| `8bba3aa` | fix(app): thread tunnel_address into vnetmap_creds in Reporter tile | SR-1 |
| `78e1a19` | fix(report): wrap IB MAC GIDs in Port Mapping tables | SR-5 |
| `6ad3385` | feat(cli): add --from-json offline replay flag | DEV-1 partial |
| `b1cfde9` | fix(port-mapping): resolve IB GUIDs to switch mgmt_ip via alias map | SR-3 |
| `aae9ef7` | fix(workflow): use API net_type as authoritative cluster type | SR-4 |
| `013a577` | docs(release): v1.5.7 candidate — TP-1/TP-2/SR-1/SR-3/SR-4/SR-5 + DEV-1 partial | docs |
| `bdab8ff` | release(v1.5.7): TP-1/TP-2/SR-1/SR-3/SR-4/SR-5 + DEV-1 partial | version bump |
| `0204362` | feat(library): add Mellanox SN8700-HS2F, Cisco Nexus 9332D-GX2B, and Cisco UCS C225 EBox | hardware library |
| `47c0560` | fix(release): sync README.md version badge to 1.5.7 | release prep |
