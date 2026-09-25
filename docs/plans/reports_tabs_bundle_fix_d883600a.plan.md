---
name: Reports Tabs Bundle Fix
overview: Create a new developer-mode Validation Results page with operation tabs and profile-based cluster filtering, fix the result bundler for exclusive cluster scoping, and make Health Checks optional in one-shot mode. The existing production Reports page remains untouched.
todos:
  - id: workflow-metadata
    content: Add cluster_ip to log_bundle verification JSON and support_tool sidecar .meta.json
    status: completed
  - id: result-scanner
    content: Create src/result_scanner.py with ResultScanner class for operation-aware result scanning
    status: completed
  - id: bundler-fix
    content: "Fix ResultBundler: PDF filtering, all switch txts, health remediation, vnetmap output, sidecar matching, placeholders"
    status: completed
  - id: validation-results-routes
    content: "Add Flask routes: /validation-results (page), /validation-results/api/* (data, view, download, delete)"
    status: completed
  - id: validation-results-template
    content: Create new frontend/templates/validation_results.html with operation tabs, profile dropdown filter, per-tab tables
    status: completed
  - id: health-optional
    content: "Make Health Checks selectable in one-shot: frontend checkbox, backend include_health param, conditional execution"
    status: completed
  - id: tests
    content: "Add tests: test_result_scanner.py, extend test_result_bundler.py and test_oneshot_runner.py"
    status: completed
  - id: docs-changelog
    content: Update CHANGELOG.md, TODO-ROADMAP.md, and docs/ADVANCED-OPERATIONS.md
    status: completed
isProject: false
---

# Validation Results Page, Bundle Fix, and Health Check Toggle

## Design Decision: Separate Developer-Mode Page

The existing Reports page (`/reports`, `reports.html`) is production-released in v1.4.7 and must remain untouched. Since these enhancements are tied to the unreleased Post Deployment Validation functionality, a **new page** will be created:

- **Route:** `/validation-results` (developer mode only, same gating as `/advanced-ops`)
- **Template:** `frontend/templates/validation_results.html` (new file)
- **Nav entry:** "Validation Results" in the top navbar, visible only when `developer_mode` is true, styled with `nav-link-dev` (same as Advanced Ops)
- **Future:** When Post Deployment Validation is fully released, this page replaces the existing Reports page

The existing `/reports` route and `reports.html` are **not modified**.

## Problem Summary

1. **Bundle includes wrong-cluster results** -- PDF reports are unfiltered, support tools/log bundles have no cluster metadata, switch txt files only keep one
2. **No way to browse operation results** -- only As-Built PDFs/JSONs are visible on the current Reports page
3. **No cluster filtering in the UI** -- no profile-based filtering for results
4. **Health Checks are forced** in one-shot mode (checkbox is disabled)

---

## Part 1: Result Scanner Backend

Create a new `src/result_scanner.py` module that scans all output directories and returns structured result metadata, grouped by operation and tagged with `cluster_ip`. This provides data for both the new Validation Results page and the improved bundler.

**File:** [src/result_scanner.py](src/result_scanner.py) (new)

- **Class `ResultScanner`** with method `scan_all() -> Dict[str, List[ResultEntry]]`
- Reuses cluster-matching helpers from `ResultBundler` (refactor to shared standalone functions in a new `src/utils/cluster_match.py` or keep in `result_bundler.py` and import)
- **Operations scanned** (one per tab):

| Tab Key           | Directory                         | File Patterns                                                                                                             | cluster_ip Source                                                             |
| ----------------- | --------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| `asbuilt_reports` | `reports/`                        | `vast_asbuilt_report_*.pdf`, `vast_data_*.json`                                                                           | cluster_name from filename; cross-ref with profiles to resolve cluster_ip     |
| `health_checks`   | `output/health/`                  | `health_check_*.json`, `health_remediation_*.txt`                                                                         | JSON `cluster_ip` field; remediation shares same `{cluster_name}_{timestamp}` |
| `network_config`  | `output/scripts/network_configs/` | `network_summary_*.json`, `configure_network_*.txt`, `interface_config_*.txt`, `routing_table_*.txt`, `bond_config_*.txt` | JSON `cluster_ip`; text files share timestamp with the JSON                   |
| `switch_config`   | `output/scripts/switch_configs/`  | `switch_configs_*.json`, `switch_*.txt`                                                                                   | JSON `cluster_ip`                                                             |
| `vnetmap`         | `output/scripts/`                 | `vnetmap_results_*.json`, `vnetmap_output_*.txt`                                                                          | JSON `cluster_ip` or IP in filename                                           |
| `vperfsanity`     | `output/scripts/`                 | `vperfsanity_results_*.txt`                                                                                               | IP in filename                                                                |
| `support_tools`   | `output/scripts/`                 | `*support_tool_logs.tgz`                                                                                                  | sidecar `.meta.json` (new, see Part 3)                                        |
| `log_bundles`     | `output/scripts/`                 | `vast_log_bundle_*.tar.gz`                                                                                                | verification JSON `cluster_ip` field (updated, see Part 3)                    |
| `bundles`         | `output/bundles/`                 | `*.zip`                                                                                                                   | manifest `cluster_ip`                                                         |

- `**ResultEntry` dataclass**: `filename`, `path`, `size`, `modified`, `cluster_ip`, `file_type` (pdf/json/txt/tgz/tar.gz/zip)
- `**scan_all(cluster_ip=None)`**: when `cluster_ip` provided, filters; when `None`, returns everything
- `**get_known_clusters() -> List[Dict]`**: scans all results and returns unique cluster_ip values found, with counts per operation

---

## Part 2: Validation Results Page (Developer Mode)

### 2a. Navigation in [frontend/templates/base.html](frontend/templates/base.html)

Add a new nav link inside the existing `{% if developer_mode %}` block (after the Advanced Ops link):

```html
<a href="{{ url_for('validation_results_page') }}"
   class="nav-link nav-link-dev {% if request.endpoint == 'validation_results_page' %}active{% endif %}"
   title="Developer Mode">
    <svg ...><!-- clipboard/results icon --></svg>
    Validation Results
</a>
```

### 2b. Route guard in [src/app.py](src/app.py)

Extend the existing `before_request` guard to also cover `/validation-results`:

```python
if request.path.startswith("/advanced-ops") or request.path.startswith("/validation-results"):
    if not app.config.get("DEVELOPER_MODE", False):
        ...
```

### 2c. New Flask Routes in [src/app.py](src/app.py)

- `**GET /validation-results**` -- renders `validation_results.html` with `profiles=_load_profiles(PROFILES_PATH)`
- `**GET /validation-results/api/results**` -- returns JSON `{ operations: { "health_checks": [...], ... } }` with optional `?cluster_ip=x` filter and `?profile=Unsaved` for unsaved-cluster results
- `**GET /validation-results/api/file/<operation>/<path:filename>**` -- serve file for view/download (path traversal protection)
- `**DELETE /validation-results/api/file/<operation>/<path:filename>**` -- delete an operation result file

### 2d. Frontend Template [frontend/templates/validation_results.html](frontend/templates/validation_results.html) (new)

**Header area:**

- Page title "Validation Results"
- Subtitle "Browse and manage Post Deployment Validation results by operation and cluster"
- **Profile filter dropdown** (right-aligned in header): "All Clusters" (default) | each saved profile name (showing `name -- cluster_ip`) | "Unsaved Cluster Results"
- Dropdown populated from `{{ profiles | tojson }}` server-side

**Tab bar** (horizontal pills, styled in `app.css` as reusable `.results-tab-bar` / `.results-tab`):

- As-Built Reports | Health Checks | Network Config | Switch Config | vnetmap | vperfsanity | Support Tools | Log Bundles | Bundles
- Active tab uses accent color (consistent with existing `nav-link.active` / `docs-nav-link.active` patterns)

**Each tab panel** contains:

- A `data-table` with columns: File Name, Type (icon), Size, Cluster, Generated, Actions (View/Download/Delete)
- Empty state: "No [operation] results found for this cluster." (or link to Advanced Ops)
- Results sorted newest-first

**Behavior:**

- On page load: fetch `/validation-results/api/results` (all clusters), populate all tabs
- On profile dropdown change: re-fetch with `?cluster_ip=<profile.cluster_ip>` or `?profile=Unsaved`
- Tab switching is client-side show/hide
- Delete: `fetch(..., { method: 'DELETE' })`, remove row on success

### 2e. Tab Bar Styles in [frontend/static/css/app.css](frontend/static/css/app.css)

Add reusable tab component classes:

- `.results-tab-bar` -- horizontal flex container with bottom border
- `.results-tab` -- individual tab pill (padding, border-radius top, cursor pointer)
- `.results-tab.active` -- accent background, white text (matches `nav-link.active` colors)
- `.results-tab-panel` -- content panel, hidden by default
- `.results-tab-panel.active` -- displayed

---

## Part 3: Workflow Metadata Improvements

Embed `cluster_ip` in output files that currently lack it:

### 3a. [src/workflows/log_bundle_workflow.py](src/workflows/log_bundle_workflow.py)

- In the verification step, add `"cluster_ip": self._credentials.get("cluster_ip")` to the verification JSON written to disk

### 3b. [src/workflows/support_tool_workflow.py](src/workflows/support_tool_workflow.py)

- After downloading the `.tgz`, write a sidecar `{archive_name}.meta.json` containing `{"cluster_ip": host, "timestamp": ..., "hostname": ...}`
- `ResultScanner` and `ResultBundler` will look for `*.meta.json` to determine cluster association

---

## Part 4: ResultBundler Fixes

Update [src/result_bundler.py](src/result_bundler.py) `collect_results()`:

1. **PDF reports**: filter by cluster_name in filename, cross-referenced with cluster_ip from profiles or from the metadata passed to `set_metadata()`. The `cluster_name` can be extracted from the filename pattern `vast_asbuilt_report_{cluster_name}_{timestamp}.pdf`.
2. **Support tools**: match via sidecar `.meta.json` `cluster_ip` field (new from Part 3), fall back to `_text_header_has_ip` for legacy files
3. **Log bundles**: match via verification JSON `cluster_ip` field (new from Part 3)
4. **Switch txt files**: change `setdefault` to collect ALL `switch_*_{timestamp}.txt` files into separate keys (`switch_config_txt_0`, `switch_config_txt_1`, etc.) or use a list
5. **Health remediation**: collect `health_remediation_*.txt` matching the same cluster/timestamp as the health JSON
6. **vnetmap output**: collect `vnetmap_output_*.txt` matching the same cluster IP
7. **Missing operations**: for each expected category, if no file was found, add a placeholder entry. In `create_bundle()`, write a small `{category}_NOT_FOUND.txt` placeholder: "No [operation] results found for cluster [cluster_ip]."
8. **Best-coverage logic**: for each category, `_pick_latest` already returns the newest matching file. This naturally provides "latest from all past runs" per category. No structural change needed -- the fix is ensuring ALL categories are properly cluster-filtered (items 1-3 above) so each returns its own latest independently.

---

## Part 5: Health Checks Optional in One-Shot

### 5a. Frontend [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html)

- Change Health Checks row from `<input type="checkbox" checked disabled>` to `<input type="checkbox" id="oneShotIncludeHealth" checked>` (enabled, checked by default, user can uncheck)
- Remove `oneshot-item-fixed` class, change badge from "Always" to "Recommended"
- Update `startOneShot()` to include `include_health: document.getElementById('oneShotIncludeHealth').checked` in the payload
- Update pre-validation: if health is unchecked, skip node/switch SSH connectivity checks that are only relevant to health

### 5b. Flask route [src/app.py](src/app.py)

- In `/advanced-ops/oneshot/start`, extract `include_health` from the payload (default `True`), pass to `OneShotRunner`

### 5c. Backend [src/oneshot_runner.py](src/oneshot_runner.py)

- Add `include_health: bool = True` to `__init`__
- In `run_all()`: only call `self._run_health_checks()` if `self._include_health`
- Adjust `total_operations` count accordingly (don't add 1 for health if skipped)
- In `run_prevalidation()`: skip node/switch SSH checks if health is not selected AND no selected ops need SSH

### 5d. Progress UI

- Update phase indicators: if health not included, skip the health_checks phase dot or mark it as "Skipped"

---

## Part 6: Test Updates

### [tests/test_result_bundler.py](tests/test_result_bundler.py)

- Add tests for: health_remediation collection, vnetmap_output collection, all-switch-txt collection, PDF cluster filtering, support tool sidecar matching, log bundle verification JSON matching, missing-operation placeholders

### [tests/test_oneshot_runner.py](tests/test_oneshot_runner.py)

- Add tests for: `include_health=False` skips health phase, total_operations count adjusts, pre-validation skips SSH when only API ops selected

### New: [tests/test_result_scanner.py](tests/test_result_scanner.py)

- Tests for scan_all with/without cluster_ip filter, get_known_clusters, unsaved cluster detection

---

## File Change Summary

| File                                         | Change                                                                                             |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| `src/result_scanner.py`                      | **New** -- operation-aware result scanner                                                          |
| `src/result_bundler.py`                      | Fix cluster filtering, add missing categories, placeholder notes                                   |
| `src/app.py`                                 | New `/validation-results` page route + API routes, extend dev-mode guard, oneshot `include_health` |
| `src/oneshot_runner.py`                      | Add `include_health` parameter, conditional health execution                                       |
| `src/workflows/log_bundle_workflow.py`       | Add `cluster_ip` to verification JSON                                                              |
| `src/workflows/support_tool_workflow.py`     | Write sidecar `.meta.json` with `cluster_ip`                                                       |
| `frontend/templates/validation_results.html` | **New** -- developer-mode page with operation tabs, profile dropdown, per-tab result tables        |
| `frontend/templates/base.html`               | Add "Validation Results" nav link inside `{% if developer_mode %}` block                           |
| `frontend/templates/reports.html`            | **Untouched** -- production page remains as-is                                                     |
| `frontend/templates/advanced_ops.html`       | Health checkbox selectable, `include_health` in payload                                            |
| `frontend/static/css/app.css`                | Reusable tab bar styles (`.results-tab-bar`, `.results-tab`, `.results-tab-panel`)                 |
| `tests/test_result_scanner.py`               | **New** -- scanner tests                                                                           |
| `tests/test_result_bundler.py`               | Extended for new categories and placeholders                                                       |
| `tests/test_oneshot_runner.py`               | Extended for `include_health`                                                                      |
| `docs/TODO-ROADMAP.md`                       | Update AO-16/AO-17 status, add AO-18 for Validation Results page                                   |
| `CHANGELOG.md`                               | Document new features                                                                              |
| `.cursor/rules/architecture-03.mdc`          | Add Validation Results routes to Web UI Layer docs                                                 |
