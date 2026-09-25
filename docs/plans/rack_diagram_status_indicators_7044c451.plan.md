---
name: Rack Diagram Status Indicators
overview: Implement a comprehensive status indicator system in the rack diagram with color-coded dots and squares for CBoxes, EBoxes, DBoxes, and Switches, plus a legend tile next to each diagram.
todos:
  - id: color-constants
    content: Add STATUS_INACTIVE (orange) and STATUS_MGMT (blue) color constants to rack_diagram.py
    status: completed
  - id: indicator-method
    content: Create _draw_status_indicators method for multi-shape indicator rendering
    status: completed
  - id: refactor-device-repr
    content: Refactor _create_device_representation to accept indicators list and delegate to new method
    status: completed
  - id: build-status-map
    content: In report_builder.py, build node_status_map from CNode/DNode data and pass to generate_rack_diagram
    status: completed
  - id: update-generate
    content: Update generate_rack_diagram to accept node_status_map and build indicator specs per device
    status: completed
  - id: legend-tile
    content: Create _draw_status_legend method and call it from generate_rack_diagram
    status: completed
  - id: verify-regenerate
    content: Regenerate both test PDFs (blc1 EBox + <customer> CBox/DBox) and run test suite
    status: completed
isProject: false
---

# Rack Diagram Status Indicators

## Data Available

From the JSON, each device type provides status through these fields:

- **CBox**: `state=UNKNOWN` (not useful); derive from associated CNode `status` (ACTIVE/INACTIVE) via `cbox_id`
- **CNode**: `status=ACTIVE|INACTIVE`, `is_mgmt=True|False`, linked to CBox via `cbox_id` or EBox via `ebox_id`
- **DBox**: `state=ACTIVE` (direct)
- **DNode**: `status=ACTIVE|INACTIVE`, linked to DBox via `dbox_id` or EBox via `ebox_id`
- **EBox**: `state=ACTIVE` (direct); contains 1 CNode + 2 DNodes linked via `ebox_id`
- **Switch**: `state` field from hardware inventory

Management CNode identified by `is_mgmt: True` on CNode data, or `cluster_summary.mgmt_cnode` name.

## Color Scheme

| Color  | Meaning                           | Hex                                  |
| ------ | --------------------------------- | ------------------------------------ |
| Green  | Active                            | `#06d69f` (existing `STATUS_ACTIVE`) |
| Orange | Inactive                          | `#FF9800` (new `STATUS_INACTIVE`)    |
| Blue   | Inactive — Management CNode (VMS) | `#1A6FB5` (existing `ACCENT_BLUE`)   |

## Indicator Shapes

- **Dot (circle)**: CNode status
- **Square (rect)**: DNode status
- For **CBox**: 1 circle per CNode (1x to 4x CNodes per CBox) — color per CNode status
- For **DBox**: 1 square per DNode (2x or 4x DNodes per DBox) — color per DNode status
- For **EBox**: 1 circle (CNode) + 2 squares (DNodes) in a horizontal line
- For **Switch**: Single dot — green if state is ACTIVE/ONLINE/OK, orange otherwise. No dot for manually-added switches not present in Hardware Inventory.
- All indicators drawn in a horizontal line at the left edge of the device, centered vertically, with small spacing

## Changes

### 1. `src/rack_diagram.py` — New color constants and status data

Add new color constants:

```python
STATUS_INACTIVE = HexColor("#FF9800")   # Orange for inactive
STATUS_MGMT = HexColor("#1A6FB5")       # Blue for management CNode (VMS)
```

### 2. `src/rack_diagram.py` — Refactor `_create_device_representation` status indicators

Replace the single green-dot block (lines 462-472) with a new method `_draw_status_indicators` that:

- Accepts a list of indicator specs: `[{"shape": "dot"|"square", "color": HexColor}, ...]`
- Draws them in a horizontal line at the left edge of the device, centered vertically, with small spacing
- For CBox: receives 1-4 dots (one per CNode; color from each CNode status)
- For DBox: receives 2-4 squares (one per DNode; color from each DNode status)
- For EBox: receives 1 dot (CNode) + 2 squares (DNodes)
- For Switch: receives 1 dot (green if active)

### 3. `src/rack_diagram.py` — Update `generate_rack_diagram` to pass node status data

The method signature already accepts `cboxes`, `dboxes`, `eboxes`. Add a new parameter `node_status_map` (dict) that provides:

```python
node_status_map = {
    "cnodes_by_cbox": {cbox_id: [{"status": "ACTIVE", "is_mgmt": False}, ...], ...},
    "cnode_by_ebox": {ebox_id: {"status": "ACTIVE", "is_mgmt": True}, ...},
    "dnodes_by_dbox": {dbox_id: [{"status": "ACTIVE"}, ...], ...},
    "dnodes_by_ebox": {ebox_id: [{"status": "ACTIVE"}, {"status": "ACTIVE"}], ...},
    "switch_in_inventory": {switch_name: True, ...},
}
```

Note: `cnodes_by_cbox` is a list (1-4 CNodes per CBox); `dnodes_by_dbox` is a list (2-4 DNodes per DBox). `switch_in_inventory` tracks which switches came from the Hardware Inventory API vs. manually added.

Each device placement block (CBox, DBox, EBox, Switch) will build the indicator spec list from this map and pass it to `_create_device_representation`.

Switch indicator logic:

- If switch name is in `switch_in_inventory`: green dot if state is ACTIVE/ONLINE/OK, orange dot otherwise
- If switch name is NOT in `switch_in_inventory` (manually added): no dot

### 4. `src/report_builder.py` — Build `node_status_map` and pass to rack diagram

In `_build_report_story` where rack diagrams are generated (around line 2570), build the `node_status_map` from `hw_cnodes` and `hw_dnodes` data already available in scope, then pass it to `rack_gen.generate_rack_diagram(...)`.

Key logic for CNode indicator color:

- CNode `status=ACTIVE` -> Green
- CNode `is_mgmt=True` and `status=INACTIVE` -> Blue (dedicated VMS)
- CNode `status=INACTIVE` and `is_mgmt=False` -> Orange

Key logic for DNode indicator color:

- DNode `status=ACTIVE` -> Green
- DNode `status=INACTIVE` (or other) -> Orange

### 5. `src/rack_diagram.py` — Add legend tile method `_draw_status_legend`

New method that draws a small bordered tile to the right or below the rack diagram with:

```
Status Indicators
-----------------
● Green  = Active
● Orange = Inactive
● Blue   = Management (VMS)
■ Green  = Active
■ Orange = Inactive
```

Circle (●) represents CNode or Switch status. Square (■) represents DNode status. Manually-added switches (not in Hardware Inventory) have no indicator.

Call this from `generate_rack_diagram` after all devices are placed, positioned in the available space beside the rack (right side, below labels).

### 6. `src/rack_diagram.py` — Update `_create_device_representation` signature

Add `indicators` parameter (optional list of dicts). When provided, replaces the old single-dot logic.

## Files Changed

- `src/rack_diagram.py` — Colors, indicator drawing, legend, updated device representation
- `src/report_builder.py` — Build node_status_map, pass to rack diagram generator
