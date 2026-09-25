---
name: Switch Discovery Workflow
overview: Rework the Reporter page's Rack & Switch Discovery section to run discovery first, present fallback options when no switches are found, replace the manual IP "Name" field with a library switch dropdown, display manually-added switches in a consistent table, and apply styling fixes.
todos:
  - id: discovery-workflow
    content: "Rework discovery flow: run first, show fallback panel with Manual/VMS options when no switches found"
    status: completed
  - id: library-dropdown
    content: Replace Manual Switch IP 'Name' field with library switch model dropdown fetched from /api/library
    status: completed
  - id: manual-table
    content: Restyle manual switch IP table to match Placed Switches table format with Switch Model and Height columns
    status: completed
  - id: rack-integration
    content: Wire manual switch model_key through placement data so rack_diagram resolves correct switch image
    status: completed
  - id: field-styling
    content: Apply darker background field styling to Manual Switch IP inputs for consistency
    status: pending
  - id: hide-spinners
    content: Remove up/down arrows from Height (U position) number input via CSS
    status: completed
  - id: fix-port-mapping
    content: Fix Reporter page enable_port_mapping sending boolean true instead of string 'on' — port mapping never activates
    status: completed
isProject: false
---

# Switch Discovery Workflow Redesign

## Current State

The Reporter page (`frontend/templates/reporter.html`) has a "Switch Placement Mode" section with:

- A Discovery button that POSTs to `/api/discover` and populates `rptDiscoveredSwitches`
- Manual Switch IP entry with plain text fields (IP + Name)
- A Placed Switches table for assigned rack positions
- A Height (U position) `<input type="number">` with browser-default spinner arrows

## Changes

### 1. Discovery-first workflow with fallback options

After the user clicks Discovery, if zero switches are returned:

- Show a new `#rptNoSwitchesPanel` div with two option buttons:
  - **"Add Switches Manually"** -- reveals the Manual Switch IP entry fields
  - **"Add in VMS"** -- opens a link: `https://{cluster_ip}/#/crud/physical/switches` in a new tab, then shows a "Re-run Discovery" button

When switches ARE discovered, behavior remains the same (show assignment controls). The Manual Switch IP section is hidden by default and only shown after the "Add Switches Manually" choice (or when restoring from saved state that has manual IPs).

**Implementation in `reporter.html`:**

- Add `#rptNoSwitchesPanel` HTML (hidden by default) between the Discovery button row and `#rptAssignmentControls`
- Modify `rptDiscoverSwitches()`: after receiving the response, if `data.switches.length === 0`, show `#rptNoSwitchesPanel` instead of assignment controls
- New JS functions: `rptShowManualEntry()` (shows manual IP section + assignment controls), `rptOpenVmsSwitch()` (opens VMS link + shows re-run button)

### 2. Replace Manual Switch IP "Name" field with Library switch dropdown

Replace the text input `#rptManualSwitchIpName` with a `<select>` dropdown populated from `/api/library` filtered to `type === "switch"`.

- On page load (or when the manual section becomes visible), fetch `/api/library` and filter to switches only
- Populate `#rptManualSwitchIpModel` dropdown with options: each option's `value` = library key, text = `description` (e.g., "Mellanox SN2100 100Gb 16pt Switch")
- Store the selected library key, description, `height_u`, and `image_filename` with each manual switch IP entry
- Updated data shape: `{ ip, name, model_key, model_description, height_u }`

### 3. Move Manual Switch IP fields above and align with Rack/Switch/Height row

The Manual Switch IP entry row must be **above** the Rack/Switch/Height placement row and use the same layout:

- Use `.placement-controls` CSS class (same `form-row` grid as the Rack/Switch/Height row)
- Fields: **Switch IP** (text input, `.form-group.third`), **Switch Model** (library dropdown, `.form-group.third`), and the **Add** button uses the same circular icon button (`.btn-icon-add` with the plus-circle SVG) -- not the current `.btn.btn-accent.btn-sm` text button
- HTML order inside `#rptAssignmentControls`: Manual Switch IP row first, then Rack/Switch/Height row below it
- The `.rpt-manual-ip-section` wrapper is removed; the fields become a `.form-row.placement-controls` div directly inside `#rptAssignmentControls`

### 4. Display manually-added switches in a Placed-Switches-style table

Replace the current simple IP/Name table (`#rptManualSwitchIpTableContainer`) with a table matching the Placed Switches table styling (`.placed-switches-table`):

- Columns: **IP Address**, **Switch Model**, **Height**, **delete icon**
- Use `.placed-switches-table` CSS class for consistency
- The "Name" column becomes "Switch Model" showing the selected library description
- Position this table between the Manual IP row and the Rack/Switch/Height row

### 4. Integrate manual switches into rack placement and report

Currently manual switch IPs appear in the switch dropdown as pseudo-entries with `model: 'Manual'`. Update:

- When manual switches have a library model selected, use that model's `height_u` and key instead of defaulting to `1U / Manual`
- `rptRenderSwitchDropdown()`: show manual switches as `{ip} ({description}, {height_u}U)` instead of `{ip} (Manual, 1U)`
- When placed, store the `model_key` so `rack_diagram.py` can resolve the correct image via `_get_hardware_image_path(model_key)`
- Update `rptSyncManualPlacements()` to include model info in the serialized data

### 6. Styling consistency (fields + Manual IP row)

Since the Manual Switch IP row now uses `.placement-controls` (same class as the Rack/Switch/Height row), it automatically inherits the same darker background field styling. No extra CSS needed for field backgrounds -- the shared class handles it.

### 6. Remove up/down arrows from Height field

The `#rptUPositionInput` is `<input type="number">` which shows browser spinner arrows. Hide them with CSS:

```css
#rptUPositionInput::-webkit-inner-spin-button,
#rptUPositionInput::-webkit-outer-spin-button {
    -webkit-appearance: none;
    margin: 0;
}
#rptUPositionInput {
    -moz-appearance: textfield;
}
```

### 8. Fix: Reporter page port mapping never activates (BUG)

The Reporter page sends `enable_port_mapping: true` (boolean) via `URLSearchParams` in `runReporterGenerate()` (line 1264). The backend checks `form.get("enable_port_mapping") == "on"` (line 266 of `app.py`). The boolean `true` serializes to the string `"true"`, which never matches `"on"`, so port mapping is always disabled from the Reporter page.

**Fix in `reporter.html` line 1264:**

```javascript
// Before (broken):
enable_port_mapping: (creds.switch_password && creds.node_password) ? true : false,
// After (fixed):
enable_port_mapping: (creds.switch_password && creds.node_password) ? 'on' : '',
```

This is the direct cause of the "VNetMap output file not found" warning -- the external port mapper never runs, so `use_ext_port_mapping` stays `False`, and `extract_port_mapping()` falls through to looking for a `vnetmap_output.txt` file that doesn't exist.

## Files to modify

- `frontend/templates/reporter.html` -- HTML structure changes, JS workflow logic, inline CSS additions, port mapping fix
- Possibly `frontend/static/css/app.css` -- if global spinner-hide or field styling is preferred over inline

## Key code locations

- Discovery button + handler: `reporter.html` lines 137-142 (HTML), lines 938-971 (JS `rptDiscoverSwitches`)
- Manual Switch IP section: `reporter.html` lines 174-189 (HTML), lines 1067-1106 (JS)
- Switch dropdown builder: `reporter.html` lines 987-1003 (JS `rptRenderSwitchDropdown`)
- Placed Switches table: `reporter.html` lines 163-168 (HTML), lines 1033-1051 (JS `rptRenderPlacedTable`)
- Library API: `src/app.py` line 1141 (`GET /api/library`)
- Built-in switch catalog: `src/hardware_library.py` lines 126-203 (14 switch entries)
