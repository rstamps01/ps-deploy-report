# EBox Hardware Overview and Inventory — Implementation Plan

**Purpose:** Implement the specified logic for EBox-only clusters in the Hardware Overview table and Hardware Inventory table, and align EBox representation with CNode/DNode association and Rack Layout Diagram.

**Rules referenced:** design-guidelines-01 (project docs), report-branding-10 (section order, VAST styling), READ_ONLY_VAST_API_POLICY (data is read-only).

**Last updated:** 2026-03-19

---

## 1. Requirements Summary

### 1.1 General EBox rules (all clusters with EBoxes)

| # | Rule | Notes |
|---|------|--------|
| 1 | One physical EBox = 1 CNode + 2 DNodes | Association via EBox/Name and CNode/Box, DNode/Box (or ebox_id). |
| 2 | EBox clusters have **only** EBoxes | No CBoxes or DBoxes when EBoxes are present. |
| 3 | One EBox enclosure = **1U** by default | Used for Height and Rack Layout. |
| 4 | EBox/Name identifies nodes | Match CNode/Box and DNode/Box to EBox/Name (or ebox_id → ebox). |
| 5 | CNode/vendor → EBox hardware key | Example: `supermicro_gen5_ebox, two dual-port NICs` → key `supermicro_gen5_ebox`. |
| 6 | Model column = CNode/vendor shortened | Text before first comma (e.g. `supermicro_gen5_ebox`). |
| 7 | CNode vendor = EBox library image | Same key used for Rack Layout Diagram device image. |

### 1.2 Hardware Inventory table — EBox only

| # | Change | Details |
|---|--------|---------|
| 1 | Remove **Node** column | Headers become: Rack, Model, Name/Serial Number, Status, Height (5 columns). |
| 2 | Row order per EBox (lowest EBox/ID first) | For each EBox: 1 row EBox, 1 row CNode, 2 rows DNodes. |
| 3 | EBox row | Rack=EBox rack_name, Model=CNode vendor (shortened), Name/Serial=EBox name, Status=EBox state, Height=EBox rack_unit. |
| 4 | CNode row | Rack=EBox rack_name, Model=CNode vendor (shortened), Name/Serial=CNode name, Status=CNode state, Height=EBox rack_unit. |
| 5 | DNode rows (2) | Same pattern: Rack, Model (CNode vendor), Name/Serial=DNode name, Status=DNode state, Height=EBox rack_unit. |
| 6 | Switches | Appended at the bottom after all EBoxes and associated nodes. |

### 1.3 Hardware Overview table — EBox only

| # | Change | Details |
|---|--------|---------|
| 1 | CBoxes = 0 | When cluster has EBoxes (EBox-only cluster). |
| 2 | DBoxes = 0 | When cluster has EBoxes (EBox-only cluster). |
| 3 | CNodes / DNodes | Report actual discovered counts (unchanged). |

---

## 2. Detection: EBox-only cluster

- **Definition:** Cluster is “EBox-only” when `hardware_inventory.eboxes` is non-empty **and** we treat it as having no CBoxes/DBoxes for display.
- **Implementation:** In report_builder, define `is_ebox_only = bool(eboxes) and not cboxes and not dboxes`. If the product requirement is “clusters which include EBoxes will only include EBoxes,” then when `eboxes` is non-empty, force Overview CBoxes/DBoxes to 0 and use **only** the EBox inventory path for the Hardware Inventory table (no CBox/DBox rows).

---

## 3. Data flow and association

### 3.1 Node–to–EBox association

- **Current:** `hardware_inventory` has `cnodes`, `dnodes`, `eboxes` (eboxes keyed by name). CNodes/DNodes have `ebox_id` and optionally box name (e.g. `cbox`/`dbox` in API; may need `box_name` in processed node).
- **Required:** For each EBox (by name or id), determine:
  - 1 CNode where `cnode["ebox_id"] == ebox["id"]` or `cnode.get("box_name") == ebox_name` (if we add box_name from API `cbox`/`dbox`).
  - 2 DNodes where `dnode["ebox_id"] == ebox["id"]` or `dnode.get("box_name") == ebox_name`.
- **Recommendation:** Prefer `ebox_id` for matching (already in processed nodes). Build `ebox_id → ebox` from `eboxes` (value has `id`). For each ebox, find cnodes/dnodes with matching `ebox_id`. CNode’s `box_vendor` (before comma) = model key and library image key.

### 3.2 Model string (CNode vendor shortened)

- From CNode: `box_vendor` (e.g. `"supermicro_gen5_ebox, two dual-port NICs"`).
- **Model column and library key:** `model = box_vendor.split(",")[0].strip()` (e.g. `supermicro_gen5_ebox`). Use same value for Hardware Inventory Model column and for Rack Layout Diagram EBox device image lookup.

### 3.3 EBox default 1U

- In `rack_diagram.py`, `_get_device_height_units()` already treats ebox/enclosure as 1U when not in library. Ensure EBox entries passed to the diagram have `model` (or `hardware_type`) set to the CNode vendor key so the library image is used and height remains 1U per spec.

---

## 4. Implementation tasks (by component)

### 4.1 Data extractor (`src/data_extractor.py`)

| Task | Description |
|------|-------------|
| D1 | **Optional:** Add `box_name` to `_process_hardware_node()` for cnode/dnode so report can match by EBox name if needed: e.g. `box_name = cnode.get("cbox") or cnode.get("box_name")` (and dnode `dbox`). Not strictly required if matching by `ebox_id` only. |
| D2 | Ensure EBox entries in `extract_hardware_inventory` retain `id`, `name`, `rack_name`, `rack_unit`, `state` (already present from API). No change if already so. |

### 4.2 Report builder — Hardware Overview (`src/report_builder.py`)

| Task | Description |
|------|-------------|
| R1 | In the section that builds **Hardware Overview** (around 1334–1371): compute `is_ebox_only = bool(hardware.get("eboxes")) and not (hardware.get("cboxes") or hardware.get("dboxes"))`. |
| R2 | When `is_ebox_only`: set Overview row values for **CBoxes** and **DBoxes** to `"0"` (string for display). Leave **CNodes** and **DNodes** as current counts (`len(cnodes)`, `len(dnodes)`). |
| R3 | When not EBox-only, keep existing Overview logic (current cboxes/dboxes/eboxes counts). |

### 4.3 Report builder — Hardware Inventory table (`src/report_builder.py`)

| Task | Description |
|------|-------------|
| R4 | **Branch:** In `_create_consolidated_inventory_table()`, if `eboxes` is non-empty and `not cboxes and not dboxes` (EBox-only), use a **separate code path** that builds only EBox + associated CNode/DNode rows + switches. |
| R5 | **EBox-only path:** Build ordered list of EBoxes by ascending `id` (handle None/non-numeric: sort key `(id is None, int(id) if id is not None and str(id).isdigit() else 0)`). |
| R6 | For each EBox in that order: (1) Find 1 CNode with `cnode.get("ebox_id") == ebox.get("id")` (or match by box_name if present). (2) Find 2 DNodes with `dnode.get("ebox_id") == ebox.get("id")`. (3) Model string = CNode’s `box_vendor` split on first comma, stripped. (4) Append 1 row: EBox (Rack=ebox rack_name, Model=model, Name/Serial=ebox name, Status=ebox state, Height=ebox rack_unit or "1U"). (5) Append 1 row: CNode (same Rack, Model, Name/Serial=cnode name, Status=cnode status, Height=ebox rack_unit). (6) Append 2 rows: DNodes (same Rack, Model, Name/Serial=dnode name, Status=dnode status, Height=ebox rack_unit). |
| R7 | **EBox-only headers:** Use 5 columns: `["Rack", "Model", "Name/Serial Number", "Status", "Height"]` (no Node column). |
| R8 | **EBox-only switches:** Append switch rows at the end (same columns: Rack, Model, Name/Serial, Status, Height). Reuse existing switch data and rack assignment logic where possible. |
| R9 | **Pagination/branding:** Call the same VAST table helper with the new 5-column headers and row list. Ensure `brand_compliance.create_vast_hardware_table_with_pagination` (or equivalent) supports 5-column hardware table; add a branch or new helper if it currently assumes 6 columns. |

### 4.4 Report builder — Physical Rack Layout (EBox model for library image)

| Task | Description |
|------|-------------|
| R10 | Where `racks_data[rack_name]["eboxes"]` is built (around 2196–2203): for each EBox, resolve the **associated CNode** (same ebox_id or box_name). Set `model` and `hardware_type` to the CNode’s `box_vendor` shortened (text before first comma), not the literal `"ebox"`. So the rack diagram’s `_get_device_height_units()` and image lookup use the same key (e.g. `supermicro_gen5_ebox`). |
| R11 | Ensure EBox default height is 1U in `rack_diagram.py` when the model key is present (already 1U for ebox/enclosure in `_get_device_height_units`; confirm and keep). |

### 4.5 Rack diagram (`src/rack_diagram.py`)

| Task | Description |
|------|-------------|
| RD1 | Confirm EBox entries with `model` (or `hardware_type`) set to a key like `supermicro_gen5_ebox` resolve to 1U and to the correct library image. Adjust `_get_device_height_units()` and image lookup for type `ebox` if needed so CNode vendor key is used. |

### 4.6 Brand compliance / table styling (`src/brand_compliance.py`)

| Task | Description |
|------|-------------|
| B1 | Support **5-column** Hardware Inventory table when Node column is omitted: headers `["Rack", "Model", "Name/Serial Number", "Status", "Height"]`. Ensure column widths and pagination still work (e.g. content-based widths for 5 columns or a dedicated ratio set). |

---

## 5. Order of implementation

1. **R1–R3** — Hardware Overview (CBoxes/DBoxes = 0 for EBox-only; CNodes/DNodes unchanged).
2. **R4–R9** — Hardware Inventory EBox-only path (no Node column; EBox → CNode → 2× DNode ordering; switches at bottom; 5-column headers and table).
3. **B1** — Brand compliance 5-column hardware table support.
4. **R10–R11** — Rack Layout: EBox model from CNode vendor; 1U default.
5. **RD1** — Rack diagram: confirm 1U and library image for EBox model key.
6. **D1–D2** — Data extractor: optional `box_name` and EBox field checks.

---

## 6. Testing

| Area | What to test |
|------|----------------|
| Unit | Mock hardware_inventory with eboxes only (no cboxes/dboxes); assert Overview shows CBoxes=0, DBoxes=0; assert Inventory has 5 columns and EBox→CNode→2×DNode order per EBox, then switches. |
| Unit | Mock EBox + 1 CNode + 2 DNodes per EBox; assert Model column is CNode box_vendor before comma. |
| Integration | End-to-end report with EBox-only fixture: Overview and Inventory and Rack Layout match spec. |
| Regression | Mixed cluster (CBoxes/DBoxes, no EBoxes): Overview and Inventory unchanged; 6-column table still used. |

---

## 7. Edge cases

- **Missing CNode or DNode for an EBox:** If an EBox has no matching CNode, model can fall back to "Unknown" and omit or mark the CNode row; if only one DNode, add one row. Document chosen behavior.
- **EBox without rack_unit:** Use "1U" or "N/A" for Height.
- **Non-numeric EBox id:** Sort with None/low values last so ordering remains deterministic.

---

## 8. Files to touch (summary)

| File | Changes |
|------|---------|
| `src/report_builder.py` | Hardware Overview EBox-only CBoxes/DBoxes = 0; EBox-only Inventory path (5 columns, row order, model from CNode); EBox model in racks_data for diagram. |
| `src/brand_compliance.py` | 5-column Hardware Inventory table support. |
| `src/rack_diagram.py` | Confirm EBox model key and 1U/library image. |
| `src/data_extractor.py` | Optional box_name on nodes. |

---

**Next step:** Implement in the order of Section 5 and add/run tests per Section 6.
