---
name: Relocate Report Tuning UI
overview: Reorganize toggle controls within Advanced Configuration, then relocate the Report Tuning Tool bar and Report Sections bar from Advanced Configuration to the Validation Results page, integrating the Cluster Filter and replacing the Output Directory bar.
todos:
  - id: toggle-rearrange
    content: "Phase 1: Move Validate Responses to API Settings; move Include TOC and Include Page Numbers to Report Sections (advanced_config.html)"
    status: completed
  - id: tune-alignment
    content: "Phase 2: Left-align Download/Preview/status after PDF regeneration so Download right edge matches Regenerate right edge"
    status: completed
  - id: vr-tune-bar
    content: "Phase 3A: Replace Validation Results Output Directory bar with Report Tuning Tool bar + Cluster Filter dropdown"
    status: completed
  - id: vr-sections-bar
    content: "Phase 3B: Add Report Sections collapsible bar below Report Tuning Tool on Validation Results"
    status: completed
  - id: vr-js-port
    content: "Phase 3C-D: Port Report Tuning JS + collectForm/loadConfig to Validation Results; add required CSS"
    status: completed
  - id: cleanup-adv-config
    content: "Phase 4: Remove Report Tuning Tool and Report Sections from Advanced Configuration; keep Processing items"
    status: completed
  - id: update-tests
    content: "Phase 5: Update test assertions for both pages"
    status: completed
isProject: false
---

# Relocate Report Tuning Tool and Report Sections to Validation Results

## Phase 1 — Rearrange Toggles in Advanced Configuration

File: [frontend/templates/advanced_config.html](frontend/templates/advanced_config.html)

### 1A. Move "Validate Responses" from Report Sections → API Settings

- **Remove** the "Validate Responses" toggle (lines 187-192) from the "Processing" sub-section inside the Report Sections bar (`data-section="data_collection"`).
- **Add** it to the API Settings bar (`data-section="api"`, lines 205-240), after the existing "Verify SSL" toggle (line 237). Keep `data-key="data_collection.validate_responses"`.
- The remaining Processing sub-section retains "Concurrent Requests" and "Graceful Degradation".

### 1B. Move "Include TOC" and "Include Page Numbers" from Report Formatting → Report Sections

- **Remove** the "Include TOC" toggle (lines 76-81) and "Include Page Numbers" toggle (lines 83-88) from the Report Formatting bar (`data-section="report"`).
- **Add** both as a new sub-heading group within the Report Sections bar, below the 11 section toggles and above the "Processing" sub-heading (before line 181). Keep their `data-key` attributes (`report.pdf.include_toc`, `report.pdf.include_page_numbers`).

## Phase 2 — Report Tuning Tool: Left-Align Result Buttons

File: [frontend/templates/advanced_config.html](frontend/templates/advanced_config.html) (and later [validation_results.html](frontend/templates/validation_results.html))

Currently after regeneration, the Preview/Download buttons and status text appear **to the right** of the "Regenerate PDF" button (with `tuneStatus` having `margin-left: auto` pushing it right). The user wants them repositioned so:

- **Download** button's right edge aligns with **Regenerate PDF** button's right edge
- **Preview** button and **output text (tuneStatus)** are to the left of Download
- Order (left to right): `tuneStatus` | `Preview` | `Download`

Implementation:

- In the `showResultButtons()` JS function, reverse the button order to **Preview, then Download** (currently Preview then Download — already correct order, just need alignment change).
- Change the `tuneStatus` span from `margin-left: auto` to `margin-left: 0` (or remove the auto). Instead, add a spacer/wrapper that right-aligns the group (status + Preview + Download) so Download's right edge lands where Regenerate PDF's right edge is.
- Wrap `tuneStatus` + `tuneResultBtns` in a container that uses `flex` with `justify-content: flex-end`, positioned relative to the Regenerate button. When result buttons appear, hide the Regenerate button and show the result group in the same right-aligned space, or use absolute positioning keyed to the Regenerate button's right edge.

CSS changes in [frontend/static/css/app.css](frontend/static/css/app.css):

- Add a `.tune-result-group` wrapper style: `display: inline-flex; gap: 6px; align-items: center; margin-left: auto;`
- Adjust `tuneStatus` to remove `margin-left: auto` (the wrapper handles it).

## Phase 3 — Relocate Report Tuning Tool + Report Sections to Validation Results

### 3A. Add Report Tuning Tool bar to Validation Results

File: [frontend/templates/validation_results.html](frontend/templates/validation_results.html)

- **Remove** the existing "Output Directory + Cluster Filter" card (lines 204-226: `<div class="card dir-management-card">...</div>`).
- **Insert** the Report Tuning Tool bar HTML (`<div class="cfg-tune-bar" id="tuneBar">...</div>`) in its place, with the **Cluster Filter** dropdown appended to the right side of the bar.
- The bar will contain (left to right):
  - `tune-label` ("Report Tuning Tool")
  - JSON file select dropdown
  - "or" + Browse button + hidden file input
  - Regenerate PDF button
  - Status text + Preview/Download result buttons
  - **Cluster Filter** dropdown (right-aligned, using the existing `profileFilter` select with `onchange="applyFilter()"`, populated via Jinja2 `profiles`)
- Remove the Output Directory-related JavaScript (`setDir()`, `openBrowse()`, `closeBrowse()`, `selectBrowsed()`, `browseUp()`, `browseTo()`) and the Browse Modal HTML (lines 228-269).

### 3B. Add Report Sections collapsible bar to Validation Results

- **Insert** the Report Sections collapsible bar (`<div class="cfg-section" data-section="data_collection">...</div>`) directly below the Report Tuning Tool bar.
- Include only the **section toggles** (11 toggles) and the two newly added toggles (**Include TOC**, **Include Page Numbers**).
- Do NOT include the "Processing" sub-section (Concurrent Requests, Graceful Degradation) — these stay on Advanced Config.
- Add the `toggleSection()` JS function to the Validation Results page script block.

### 3C. Port Report Tuning JavaScript to Validation Results

Move the following functions from `advanced_config.html` to `validation_results.html`:

- `loadJsonFiles()` — fetches `/config/advanced/json-files`
- `tuneFileInput` change handler — uploads via `/config/advanced/upload-json`
- `tuneJsonSelect` change handler
- `setTuneStatus()` / `showResultButtons()` / `regeneratePdf()`
- `collectForm()` — adapted to only collect `data-key` elements present on the Validation Results page (section toggles + TOC/page numbers)
- `loadConfig()` — fetch `/config/json` and populate the section toggle states
- Call `loadJsonFiles()` and `loadConfig()` on page init

The existing API routes (`/config/advanced/json-files`, `/config/advanced/tune-report`, `/config/advanced/download`, `/config/advanced/upload-json`) remain unchanged in [src/app.py](src/app.py) — no backend changes needed.

### 3D. Add required CSS to Validation Results

- Copy the `.cfg-tune-bar` styles from [frontend/static/css/app.css](frontend/static/css/app.css) (lines 1401-1460) or reference them (they are already in `app.css` which is loaded globally).
- Copy the `.cfg-section`, `.cfg-section-header`, `.cfg-section-body`, `.cfg-form-grid`, `.cfg-toggle-row`, `.toggle-switch`, `.toggle-slider` styles — verify these exist in `app.css` globally; if not, add them to the Validation Results `<style>` block.

## Phase 4 — Remove from Advanced Configuration

File: [frontend/templates/advanced_config.html](frontend/templates/advanced_config.html)

- **Remove** the Report Tuning Tool sticky bar (lines 15-27).
- **Remove** the Report Sections accordion (lines 94-203), EXCEPT keep the "Processing" sub-section. Move it into a standalone collapsible section ("Data Collection Processing") or merge its remaining items (Concurrent Requests, Graceful Degradation) into the API Settings bar.
- **Remove** the Report Tuning JavaScript (lines 715-820: `loadJsonFiles`, file input handler, `setTuneStatus`, `showResultButtons`, `regeneratePdf`).
- Keep `loadConfig()` and `collectForm()` on Advanced Config since it still needs them for save/reset.

## Phase 5 — Update Tests

File: [tests/test_app.py](tests/test_app.py)

- Update any tests that assert on the Advanced Config page for Report Tuning Tool or Report Sections content.
- Update tests for the Validation Results page to expect the new Report Tuning Tool bar and absence of Output Directory.
- Ensure the backend routes remain tested (they are unchanged).

## Files Changed

- [frontend/templates/advanced_config.html](frontend/templates/advanced_config.html) — toggle rearrangement, remove Report Tuning Tool + Report Sections
- [frontend/templates/validation_results.html](frontend/templates/validation_results.html) — add Report Tuning Tool bar (with Cluster Filter), add Report Sections bar, port JS, remove Output Directory
- [frontend/static/css/app.css](frontend/static/css/app.css) — tune-result alignment CSS adjustments
- [tests/test_app.py](tests/test_app.py) — update assertions
- [src/app.py](src/app.py) — potentially pass `profiles` context to Validation Results route (already done, line 948-953)
