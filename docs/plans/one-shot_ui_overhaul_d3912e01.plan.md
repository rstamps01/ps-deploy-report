---
name: One-Shot UI Overhaul
overview: "Overhaul the One-Shot tile on the Reporter page: convert pre-validation from button to checkbox, update badge system with new colors and placement, add tool status button, share manual switch placements with One-Shot report generation, and rename the start button."
todos:
  - id: switch-placement-sharing
    content: "Part A: Verify staged changes for forwarding manual switch placements to One-Shot report generation (reporter.html, app.py, oneshot_runner.py)"
    status: completed
  - id: badge-css
    content: "Part B6/C1: Add new badge CSS classes (badge-recommended, badge-required, badge-automated) and update badge-optional to blue"
    status: completed
  - id: reporter-badges
    content: "Part C1: Update Reporter checklist badge classes and text (Pre-Validation=Recommended, Run Reporter=Required, Health Check=Optional)"
    status: completed
  - id: oneshot-html-restructure
    content: "Part B1/B2/B4/B5: Add Pre-Validation checkbox, rename button to Run, add tool status button, reorder badge placement in One-Shot HTML"
    status: completed
  - id: oneshot-js-rework
    content: "Part B1/B8/B9/B10: Rework startOneShot() for inline validation, update populateOneShotChecklist() to add Automated Test badges, update save/restore state"
    status: completed
  - id: test-and-verify
    content: Run tests and verify no regressions
    status: completed
isProject: false
---

# One-Shot UI Overhaul & Switch Placement Sharing

All changes are in [frontend/templates/reporter.html](frontend/templates/reporter.html), [src/app.py](src/app.py), and [src/oneshot_runner.py](src/oneshot_runner.py).

## Part A: Share Manual Switch Placements with One-Shot Reports

**Problem:** Manual switch U-height assignments from the Reporter tile are not forwarded to One-Shot report generation.

### A1. Frontend payload ([reporter.html](frontend/templates/reporter.html) `startOneShot()`)

- Already staged: reads `rptManualPlacements`, `rptSwitchPlacement`, and `rptManualSwitchIps` and includes them in the JSON payload to `/advanced-ops/oneshot/start`.

### A2. Backend credential extraction ([src/app.py](src/app.py) `_extract_oneshot_credentials()`)

- Already staged: forwards `switch_placement`, `manual_placements`, `manual_switch_ips` from the request body.

### A3. Inject into processed data ([src/oneshot_runner.py](src/oneshot_runner.py) `_run_report()`)

- Already staged: mirrors `_run_report_job()` logic — sets `processed["manual_switch_placements"]` when `switch_placement == "manual"` and `manual_placements` is non-empty.

---

## Part B: One-Shot Tile UI Restructuring

All changes in [frontend/templates/reporter.html](frontend/templates/reporter.html).

### B1. Convert "Run Pre-Validation" button to checkbox

- Remove the `<button id="btnOneShotValidate">` from the button group (line 350).
- Add a new checkbox item at the **top** of the `#oneShotChecklist` div (before `#oneShotOpsContainer`):

```html
<label class="oneshot-item">
    <input type="checkbox" id="oneShotPreValidation" checked>
    <span class="oneshot-item-badge badge-recommended">Recommended</span>
    <span class="oneshot-item-name">Pre-Validation</span>
    <span class="oneshot-item-badge badge-automated">Automated Test</span>
</label>
```

- Modify `startOneShot()`: remove the `if (!oneShotValidated)` guard. Instead, if `#oneShotPreValidation` is checked, run validation inline (like Reporter mode does) before proceeding.
- Remove `oneShotValidated` gating — the "Run" button is always enabled.
- Remove `runOneShotValidation()`, `startOneShotValidationPolling()`, `stopOneShotValidationPolling()`, `resetOneShotValidationUI()`, `renderOneShotValidationResults()`, `proceedOneShot()`, `stopAndFix()` functions — replace with inline validation flow inside `startOneShot()` that mirrors `runReporterChecklist()`.
- Keep the `#oneShotValidationPanel` and `#oneShotValidationActions` HTML for displaying results during the inline flow.

### B2. Rename "Start One-Shot" button to "Run"

- Change `<button id="btnOneShotStart">` text from `Start One-Shot` to `Run`.
- Remove `disabled` attribute (no longer gated by validation button).

### B3. Download Bundle visibility

- Already only shown on `finalPhase === 'completed'` (line 1753-1755). Verify this is correct — no change needed.

### B4. Add "View Deployment Tool Status" button next to Update Tools

- Add an info-circle icon button after `#btnUpdateToolsOneshot`, matching the existing `#btnToolsInfo` from the Reporter panel:

```html
<button type="button" class="btn btn-outline-secondary" id="btnToolsInfoOneshot"
    onclick="showToolsStatus()" title="View deployment tools status">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
         width="16" height="16" style="vertical-align: middle;">
        <circle cx="12" cy="12" r="10"/>
        <line x1="12" y1="16" x2="12" y2="12"/>
        <line x1="12" y1="8" x2="12.01" y2="8"/>
    </svg>
</button>
```

### B5. Badge placement — move to left of operation name

- Current order: `[checkbox] [name] [badge]` (badge on the right via flex)
- New order: `[checkbox] [badge] [name] [badge]` — left badge is the category (Required/Recommended/Optional), right badge is "Automated Test" (green) where applicable.
- Update the HTML structure for all checklist items in both Reporter and One-Shot panels to place the category badge immediately after the checkbox, before the name span.

### B6. New badge CSS classes

- Add `.badge-recommended` with `background: #ff9800; color: #000;` (matching `.nav-badge-beta`)
- Add `.badge-required` with `background: #ff9800; color: #000;` (same orange)
- Update `.badge-optional` to `background: #2196f3; color: white;` (blue)
- Add `.badge-automated` with `background: #4caf50; color: white;` (green)
- Remove `.badge-health` (replaced by the new classes)

### B7. Apply badges to all items

**Reporter checklist:**

- Pre-Validation: `Recommended` (orange, left)
- Run Reporter: `Required` (orange, left)
- Health Check: `Optional` (blue, left)

**One-Shot checklist:**

- Pre-Validation (new checkbox): `Recommended` (orange, left) + `Automated Test` (green, right)
- Each dynamic workflow operation: `Automated Test` (green, right) — added in `populateOneShotChecklist()` JS
- Generate As-Built Report: `Recommended` (orange, left)
- Include Health Checks: `Optional` (blue, left)

### B8. JS updates for `populateOneShotChecklist()`

- When generating workflow operation labels, append an `Automated Test` green badge span after the name:

```javascript
label.innerHTML = '<input ...>' +
    '<span class="oneshot-item-name">' + wf.name + ' (' + wf.step_count + ' steps)</span>' +
    '<span class="oneshot-item-badge badge-automated">Automated Test</span>';
```

### B9. JS updates for `saveUIState()` / `applySavedUIState()`

- Persist `oneShotPreValidation` checkbox state.

### B10. JS updates for `resetOneShotUI()`

- Remove references to `btnOneShotValidate` (no longer exists).

---

## Part C: Reporter Checklist Badge Updates

### C1. Update Reporter badge text and classes

- Pre-Validation: change from `badge-optional` / "Optional" to `badge-recommended` / "Recommended"
- Run Reporter: change from `badge-health` / "Required" to `badge-required` / "Required"
- Health Check: change from `badge-optional` / "Optional" to `badge-optional` / "Optional" (stays same text, but CSS color changes to blue)
