---
name: EBox Label & Sort Fix
overview: Add EBox name/serial labels to rack diagram for consistency with CBox/DBox, and sort the EBox-only Hardware Inventory table by U Height (lowest to highest) with current sub-ordering preserved.
todos:
  - id: ebox-rack-label
    content: Add label_override=box_name for EBoxes in rack_diagram.py generate_rack_diagram()
    status: completed
  - id: ebox-table-sort
    content: Change ebox_sort_key in _create_ebox_only_inventory_table to sort by U Height ascending
    status: completed
  - id: regen-verify
    content: Regenerate blc1 PDF and verify both changes
    status: completed
isProject: false
---

# EBox Rack Diagram Label & Inventory Table Sort Fix

## Change 1: EBox Rack Diagram Labels (`src/rack_diagram.py`)

**Problem:** Line 941 — EBoxes are rendered without `label_override`, so they display generic "EBox-N" labels instead of their name/serial (e.g., `ebox-CH119KO30BV0477`) like CBox and DBox do.

**Fix:** Extract `name` from EBox data and pass as `label_override`, matching CBox (line 894) and DBox (line 921) pattern.

```python
# Line 924-941 — add box_name and pass label_override
for ebox in eboxes:
    ...
    box_name = ebox.get("name", "")
    ...
    self._create_device_representation(
        drawing, "ebox", device_id, u_position, u_height, model, status, label_override=box_name
    )
```

## Change 2: EBox Hardware Inventory Table Sort by U Height (`src/report_builder.py`)

**Problem:** `_create_ebox_only_inventory_table()` (line 1540) sorts EBoxes by numeric `id`, not by U Height. The user wants rows sorted by U position (lowest U number first), with current sub-ordering (EBox → CNode → DNodes per group) preserved.

**Fix:** Replace `ebox_sort_key` to parse `rack_unit` (e.g., "U2" → 2) and sort ascending.

```python
def ebox_sort_key(e: Dict[str, Any]) -> tuple:
    ru = e.get("rack_unit") or ""
    try:
        return (False, int(ru.upper().replace("U", "")))
    except (TypeError, ValueError):
        return (True, 0)
```

This keeps each EBox group (EBox row + CNode + DNodes) together while ordering the groups by physical rack position, lowest to highest.
