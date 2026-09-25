---
name: Node management map table
overview: Add a dedicated Node Management Map (VMS device name -> hostname -> mgmt IP) to the report's Network Configuration section as two compact CNode/DNode tables, and complete the pending port-mapping and diagram refinements.
todos:
  - id: node-map-tables
    content: Add CNode/DNode Management Map tables (Device Name (VMS) | Hostname | Mgmt IP) in _create_comprehensive_network_configuration after the cluster summary table, sourced from hardware_inventory cnodes/dnodes, sorted by mgmt IP; add TOC subsection labels
    status: pending
  - id: node-map-test
    content: TDD test in tests/test_report_builder.py asserting the new tables render with VMS name + hostname + mgmt IP together
    status: pending
  - id: portmap-tables
    content: "report_builder vnetmap topology tables: resolve GUID->hostname->mgmt IP from switch inventory; Full Topology shows mgmt IP; per-switch titles show name + GUID + mgmt IP"
    status: pending
  - id: diagram-labels
    content: "network_diagram_v2: replace SWA/SWB/SP1/SP2 with switch hostname primary + mgmt IP secondary"
    status: pending
  - id: diagram-width-fan
    content: "network_diagram_v2: dynamic switch width from max connections/switch, widen rack + device boxes, center the landing fan within the switch box"
    status: pending
  - id: switch-config-ports
    content: "api_handler get_switch_inventory: count active ports and derive switch MTU; defensive recompute in report_builder _create_switch_configuration for replayed JSON"
    status: pending
  - id: tests-regen-docs
    content: Add/adjust tests, regenerate <customer-site> report to verify, run flake8/black, update CHANGELOG.md
    status: pending
isProject: false
---

# Node Management Map + pending report/diagram fixes

## New: Node Management Map tables (current request)

Goal: map each node's VMS device name -> assigned hostname -> external mgmt IP, in a new dedicated table so no existing table is overpopulated.

- Confirmed data source: `processed_data["hardware_inventory"]["cnodes"]` and `["dnodes"]` carry `name` (VMS, e.g. `cnode-128-1`), `hostname` (e.g. `RackP01C01-CB6-U22-CN1`), and `mgmt_ip` (e.g. `<ip>`) for all 60 nodes. `sections.cnodes_network_configuration` is empty on this dataset, so `hardware_inventory` is the single reliable source.
- Placement (user choice): inside `_create_comprehensive_network_configuration` in [src/report_builder.py](src/report_builder.py), inserted after the cluster "Setting/Value" summary table at line 3538 and before the `# 1. CNodes Network Configuration` block at line 3540.
- Structure (user choice): two separate tables, 3 columns each: `Device Name (VMS) | Hostname | Mgmt IP`.

Implementation:

- Read nodes directly from `data.get("hardware_inventory", {}).get("cnodes"/"dnodes", [])` (do NOT reuse the `sections`-based lists, which lack `name`).
- Sort each by mgmt IP with existing `self._ip_sort_key`.
- Render via `self.brand_compliance.create_vast_hardware_table_with_pagination(rows, title, headers)` (DNode table = 40 rows, needs pagination) with titles `CNode Management Map` and `DNode Management Map`, plus a one-line intro paragraph.
- Add TOC subsection labels (`CNode Management Map`, `DNode Management Map`) under Network Configuration in the dynamic TOC block (~lines 1088-1131 in [src/report_builder.py](src/report_builder.py)).
- TDD: add a test in [tests/test_report_builder.py](tests/test_report_builder.py) asserting the new tables render with a row containing the VMS name, hostname, and mgmt IP together.

## Pending (carried from prior plan)

- portmap-tables: in `report_builder` vnetmap topology tables, resolve switch GUID -> hostname -> mgmt IP from the switch inventory; Full Topology "Switch IP" shows mgmt IP; per-switch titles show name primary + GUID + mgmt IP.
- diagram-labels: in [src/network_diagram_v2.py](src/network_diagram_v2.py), replace SWA/SWB/SP1/SP2 with switch hostname primary + mgmt IP secondary.
- diagram-width-fan: dynamic switch width from max connections/switch; widen rack + device boxes; center the landing fan so it fits within the switch box.
- switch-config-ports: in `api_handler.get_switch_inventory`, count active ports (state up/active, incl. IB "Active") and derive switch MTU from most-common non-zero port MTU; defensive recompute in `report_builder._create_switch_configuration` for replayed JSON.
- tests-regen-docs: add/adjust tests, regenerate the <customer-site> report to verify, run flake8/black, update [CHANGELOG.md](CHANGELOG.md).

## Verify

Regenerate the <customer-site> report via `--from-json` against [import/Assets-2026-05-15/vast_data_<cluster>_20260615_162738.json](import/Assets-2026-05-15/vast_data_<cluster>_20260615_162738.json) and confirm the two new tables appear under Network Configuration with name/hostname/mgmt IP populated for all 60 nodes.
