---
name: IB Diagram Rack Switch Placement
overview: "Drive the Logical Network Diagram's rack placement from the engineer-assigned hardware inventory (CBox/DBox racks) and its switch placement from switch discovery (manual_switch_placements + LF/SP naming): place all leaf switches in their assigned racks, center each spine above its installed rack, replace leaf-leaf IPL with inferred leaf-to-spine ISLs, and remove the 2 legacy per-switch port-mapping tables."
todos:
  - id: node-rack
    content: Fix _enrich_devices to assign node rack_name from parent box via cbox_id/dbox_id (hardware inventory reference)
    status: completed
  - id: switch-role
    content: Classify leaf/spine by LF/SP naming (not port-map membership) so all 4 leaves go through rack grouping
    status: completed
  - id: spine-pos
    content: Center each spine above its assigned rack in _render_page using manual_switch_placements
    status: completed
  - id: isl-mesh
    content: Suppress leaf-leaf IPL when spines present; draw inferred leaf-to-spine ISL mesh + update legend
    status: completed
  - id: remove-tables
    content: Remove the 2 legacy per-switch 'Switch N Port-to-Device Mapping' tables in report_builder; keep vnetmap tables
    status: completed
  - id: dnode-type
    content: Fix DNode node_type misclassification for IB (enhanced_port_mapper builds dnode_map for IB; re-derive node_type from hostname DB/DN at table render as a safety net)
    status: completed
  - id: tests-verify
    content: Add/adjust TDD tests and verify via --from-json replay against the <customer-site> JSON
    status: completed
isProject: false
---

# Fix IB Diagram Rack & Switch Placement

## Status of prior tasks (reassessed against the NEW `import/Assets-2026-06-09/` vnetmap)

- **Switch GUID join: DONE.** `_build_switch_ip_alias` + normalization already in [src/network_diagram_v2.py](src/network_diagram_v2.py) `generate()`; resolves 60/60 switch GUIDs to mgmt_ip and enables subnet coloring. Covered by `TestIBSwitchGuidAlias`.
- **Node join: UNBLOCKED.** The new capture has clean identity (all 30 captured C02 hostnames match hardware inventory exactly), so 60/60 edges will draw once rack/switch placement is fixed. The earlier "blocked" status reflected the stale 152345 JSON (10/30 overlap).
- **Rack distribution: NOT done** (task `node-rack`).
- **DNode capture: captured but mislabeled.** Raw vnetmap includes DB1-DB5/DN1-4; the parsed port map labels all 40 DNode rows `node_type=cnode` (task `dnode-type`).
- **Switch capture gap (4 of 6 switches absent): out of scope** — vnetmap only reached the C02 half (SSH failures + `jsonrpclib`/VMS-container warning in the raw output). Diagram degrades gracefully; placement stays correct via inventory + `manual_switch_placements`.

## Root causes (confirmed against `import/Assets-2026-06-09/` data)

- **Nodes collapse into one rack:** `_enrich_devices` in [src/network_diagram_v2.py](src/network_diagram_v2.py) inherits `rack_name` via the node's `rack_id`, but cnodes/dnodes have `rack_id=None`. The fallback grabs `boxes[0].rack_name` (`RackP01C01`) for every node. The correct reference exists in hardware inventory: `cnode.cbox_id == cbox.id` (1-20) and `dnode.dbox_id == dbox.id` (1-10), and each box carries the engineer-assigned `rack_name` (10/10 C01/C02 for cboxes; 5/5 for dboxes).
- **Leaf switches misplaced / spines in one tier:** `generate()` classifies leaf vs spine by port-map membership. Only `SW-LF-03`/`SW-LF-04` (the 2 vnetmap-captured switches) are treated as leaves; `SW-LF-01` and `<customer-site>-SW-LF-02` fall into the upstream/spine tier. `manual_switch_placements` already gives the correct rack+role for all 6 switches (LF-01/LF-02/SP-01 -> C01; LF-03/LF-04/SP-02 -> C02).
- **Redundant tables:** the Port Mapping section renders new vnetmap Topology Detail tables (`_create_vnetmap_topology_tables`) plus legacy per-leaf-switch `Switch N Port-to-Device Mapping` tables (the loop at [src/report_builder.py](src/report_builder.py) ~4341-4480).

## Assumptions (adjustable)

- Remove only the 2 legacy `Switch N Port-to-Device Mapping` tables; keep the vnetmap Topology Detail tables.
- Represent ISLs as an inferred full leaf-to-spine mesh (schematic intended topology) and suppress leaf-leaf IPL lines whenever spines are present. (vnetmap captured no inter-switch links, so nothing is discoverable.)

## Changes

### 1. Node rack placement from hardware inventory ([src/network_diagram_v2.py](src/network_diagram_v2.py))

- Change `_enrich_devices(nodes, boxes, prefix)` to accept a `box_id_field` (`"cbox_id"` / `"dbox_id"`), build `box_by_id = {box["id"]: box}`, and set each node's `rack_name` from its parent box (`node[box_id_field]` -> `box.id` -> `box.rack_name`). Keep the old sibling/`Default` path only as a last resort.
- Update the two call sites in `generate()` to pass `"cbox_id"` / `"dbox_id"`.

### 2. Switch role classification by naming, not port-map membership ([src/network_diagram_v2.py](src/network_diagram_v2.py) `generate()`)

- Add `_classify_switch_role(sw) -> "leaf"|"spine"` using hostname/name regex (`-SP-`/`SW-SP` => spine; `-LF-`/`SW-LF` => leaf; default leaf).
- Replace the `leaf_switches = [in port_map]` / `upstream_switches` block so `leaf_switches` = all role==leaf, `spine_switches` = all role==spine. All leaves now flow through `_build_rack_groups` -> `_assign_switches_to_racks` (already honors `manual_switch_placements`).

### 3. Spine placement centered above its assigned rack ([src/network_diagram_v2.py](src/network_diagram_v2.py) `_render_page` ~1286-1333)

- Resolve each spine's rack via `manual_switch_placements` (reuse `_extract_manual_switch_to_rack`) / its `_assigned_rack`.
- Position each spine centered above its rack's column x (instead of one centered shared row). Spines without a rack match fall back to current centered behavior.

### 4. Leaf/spine ISL instead of leaf-leaf IPL ([src/network_diagram_v2.py](src/network_diagram_v2.py) `_render_page`)

- When spines are present, skip leaf-leaf IPL rendering (the `ipl_conns` "IPL (inferred)" rows) and instead draw inferred ISLs: a `COLOR_SPINE_FABRIC` line from each leaf (top edge) to each spine (bottom edge).
- Update the legend: replace/add an "ISL (leaf-spine)" entry; keep IPL only for non-spine topologies.

### 5. Remove 2 legacy per-switch port tables ([src/report_builder.py](src/report_builder.py) `_create_port_mapping_section`)

- Remove the per-leaf-switch table loop that emits `f"Switch {switch_num} Port-to-Device Mapping"` (~4341-4480). Keep the vnetmap Topology Detail tables, spine tables, and diagnostic summary. Prune now-unused locals (e.g. `switch_port_speed_lookup`) as needed.

### 6. Fix DNode node_type misclassification for IB ([src/enhanced_port_mapper.py](src/enhanced_port_mapper.py))

- `generate_node_designation` ([src/enhanced_port_mapper.py:386](src/enhanced_port_mapper.py)) returns `cnode` for every IB node because IB DNode IPs (e.g. `<ip>-119`) are not landing in `self.dnode_map`. Fix the IB `cnode_map`/`dnode_map` construction so DNodes (last-octet >= 100, or hostname `-DN`/`DB`) populate `dnode_map`. Benefits future live captures.
- Safety net for regeneration from already-saved JSON: when rendering the vnetmap Topology Detail tables (and any node_type-dependent logic), re-derive node_type from the node hostname (`-DB`/`-DN` => dnode, `-CB`/`-CN` => cnode) since the saved port map's `node_type` is unreliable for IB.

### 7. Tests + verification

- TDD in [tests/test_network_diagram_v2.py](tests/test_network_diagram_v2.py): node->box->rack assignment by `cbox_id`/`dbox_id`; `_classify_switch_role`; all 4 leaves placed by manual placements; spine-per-rack positioning; inferred ISL mesh + IPL suppression when spines present.
- DNode node_type re-derivation from hostname (task `dnode-type`).
- Update/trim [tests/test_report_builder.py](tests/test_report_builder.py) (or equivalent) to assert the legacy `Switch N Port-to-Device Mapping` titles are no longer emitted while vnetmap tables remain.
- Verify via `--from-json` replay against `import/Assets-2026-06-09/vast_data_<cluster>_20260609_162644.json`: CBoxes/DBoxes split across C01/C02, leaf switches in both racks, spines above their racks, and the regenerated diagram/section reflect the new schema.

## Out of scope (vnetmap capture limitation, deferred)

- vnetmap reached only the RackP01C02 half (10 CNodes + 20 DNodes) on the 2 C02 leaf switches; the C01 leaf switches and both spines were not discovered (SSH failures to the C01 nodes; `jsonrpclib`/VMS-container warnings in the raw output). Drawn connection edges therefore remain limited to that captured C02 subset. Full connectivity across all 6 switches requires a more complete vnetmap capture (run inside the VMS container reaching all nodes); rack/switch PLACEMENT is unaffected because it is driven by hardware inventory + `manual_switch_placements`.
