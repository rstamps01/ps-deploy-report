---
name: Fix Pre-Release Bugs
overview: Fix 6 pre-release bugs in Advanced Ops state persistence, Validation Results report filtering, and One-Shot default credential routing. All bugs have clear root causes identified through code analysis.
todos:
  - id: bug1-profile-persist
    content: "BUG-1: Await fetchProfiles/loadWorkflows in DOMContentLoaded so dropdowns are populated before applying saved state"
    status: completed
  - id: bug2-checklist-persist
    content: "BUG-2: Save per-op checklist selections in localStorage; restore after populateOneShotChecklist completes"
    status: completed
  - id: bug3-clear-output
    content: "BUG-3: On output clear, set SYNC_CURSOR_KEY to current server output_count instead of removing it"
    status: completed
  - id: bug4-mode-persist
    content: "BUG-4: Fix mode restoration — add step-by-step restore path, remove forced one-shot for completed result, remove conflicting label init"
    status: completed
  - id: bug5-report-filter
    content: "BUG-5: Embed cluster_ip in JSON output and PDF sidecar at generation time; improve scanner with sidecar check and API-name-to-IP map"
    status: completed
  - id: bug6-cred-routing
    content: "BUG-6: Add per-phase credential routing — support/654321 for health checks and report, admin/<default-password> for vperfsanity when default creds active"
    status: completed
  - id: bug-tests
    content: Add tests for credential routing and report sidecar resolution
    status: completed
  - id: bug-roadmap-update
    content: Update TODO-ROADMAP.md to mark bugs as Done after fixes verified
    status: completed
isProject: false
---

# Fix Pre-Release Bugs (BUG-1 through BUG-6)

## BUG-1: Profile selection not persistent across refresh

**Root cause:** In `DOMContentLoaded`, `fetchProfiles()` is fire-and-forget (not awaited). When `applySavedUIState()` runs, the `<select>` options have not been populated yet, so setting `sel.value = saved.selectedProfile` silently fails (no matching `<option>` exists).

**Fix in [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html):**

1. Make `fetchProfiles()` return a Promise (it already is `async`)
2. `await fetchProfiles()` in `DOMContentLoaded` before calling `applySavedUIState`
3. Similarly `await loadWorkflows()` so the workflow dropdown is populated before restore

Change initialization from:

```javascript
loadWorkflows();
fetchProfiles();
```

to:

```javascript
await loadWorkflows();
await fetchProfiles();
```

This ensures dropdowns are populated before saved state is applied.

---

## BUG-2: One-Shot checklist resets to all-checked

**Root cause:** Two issues:

1. `saveUIState()` does **not** save per-operation checkbox selections (only `includeHealth` and `includeReport`)
2. `populateOneShotChecklist()` creates all checkboxes with `checked` attribute and has no hook to apply saved state afterward
3. `toggleOneShotMode()` calls `populateOneShotChecklist()` which overwrites any previously saved state

**Fix in [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html):**

1. Add `oneShotChecklist` (array of checked op IDs) to `saveUIState()`:

```javascript
var checks = [];
document.querySelectorAll('.oneshot-op-checkbox:checked').forEach(function(cb) { checks.push(cb.value); });
state.oneShotChecklist = checks;
```

1. Add a `change` event listener on one-shot checkboxes to call `saveUIState()` (in `populateOneShotChecklist`, after building each checkbox)
2. In `applySavedUIState()`, after the mode toggle restores (which triggers `populateOneShotChecklist`), apply saved checklist. Since `populateOneShotChecklist` is async, we need to **await** it and then apply:

```javascript
if (saved.oneShotChecklist && Array.isArray(saved.oneShotChecklist)) {
    document.querySelectorAll('.oneshot-op-checkbox').forEach(function(cb) {
        cb.checked = saved.oneShotChecklist.indexOf(cb.value) !== -1;
    });
}
```

1. Key timing issue: `toggleOneShotMode()` calls `populateOneShotChecklist()` but doesn't await it. Convert to `async` and await, or better — extract checklist restoration into a helper that runs after `populateOneShotChecklist` completes. The cleanest approach: make `populateOneShotChecklist` store a Promise, and `applySavedUIState` await it before restoring checkboxes.

---

## BUG-3: Cleared output repopulates on refresh

**Root cause:** `clear()` removes `SYNC_CURSOR_KEY` (resets cursor to 0). On next page load, `hydrateFromBackend()` sees `snap.output_count > 0` and cursor is 0, so it re-fetches the entire server buffer.

**Fix in [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html):**

In `OutputPaneCtor.prototype.clear()`, instead of removing `SYNC_CURSOR_KEY`, **set it to the current server output count** so hydration knows not to re-fetch old entries:

```javascript
OutputPaneCtor.prototype.clear = function() {
    if (confirm('Clear all output?')) {
        this.entries = [];
        this.container.innerHTML = '<div class="output-placeholder"><p>Output cleared.</p></div>';
        sessionStorage.removeItem(OUTPUT_STORAGE_KEY);
        // Set cursor to current server count so hydration doesn't re-fetch
        fetch('/advanced-ops/state-snapshot').then(function(r) { return r.json(); }).then(function(snap) {
            sessionStorage.setItem(SYNC_CURSOR_KEY, String(snap.output_count || 0));
        }).catch(function() {});
    }
};
```

This way, on next load, `hydrateFromBackend()` only fetches entries **newer** than the clear point. If an operation is actively running, new entries will still appear.

---

## BUG-4: Mode toggle resets to One-Shot on refresh

**Root cause:** Three issues:

1. `hydrateFromBackend()` has a branch for `snap.oneshot.result` (completed, not running) that forces one-shot mode even when the user switched to step-by-step afterward
2. `applySavedUIState()` only handles switching **to** one-shot — it never switches **back** to step-by-step
3. `DOMContentLoaded` has `labelStepByStep.classList.add('active')` at the end, which can conflict with already-applied mode

**Fix in [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html):**

1. Remove the `snap.oneshot.result` branch from `hydrateFromBackend()` — a completed one-shot result should not force mode. The saved UI state will handle mode restoration:

```javascript
// REMOVE this block:
if (snap.oneshot && snap.oneshot.result) {
    if (!oneShotMode) { document.getElementById('modeToggle').checked = true; toggleOneShotMode(); }
}
```

1. In `applySavedUIState()`, add explicit step-by-step restoration:

```javascript
if (saved.mode === 'step-by-step' && oneShotMode) {
    document.getElementById('modeToggle').checked = false;
    toggleOneShotMode();
}
```

1. Remove the unconditional `labelStepByStep.classList.add('active')` at the end of `DOMContentLoaded` — mode labels are already set correctly by `toggleOneShotMode()` or the default state.

---

## BUG-5: As-Built reports filter into Unsaved Cluster Results

**Root cause:** PDF filenames use `cluster_summary.name` from the VAST API (e.g., `vast_asbuilt_report_vast-cluster-1_20260323_120000.pdf`). `_resolve_report_cluster_ip()` tries to match this against **saved profile names** (e.g., "My Lab Cluster"), which are user-chosen strings that rarely match the API cluster name. When no match is found, `cluster_ip` is `""`, which always falls into "Unsaved".

Additionally, `vast_data_*.json` files do not have a top-level `cluster_ip` field, so `json_cluster_ip()` also returns `None`.

**Fix — two-part approach:**

### Part A: Embed `cluster_ip` at generation time (prevents future mismatches)

**File: [src/app.py](src/app.py)** (report generation job `_run_report_job`):

- After generating the JSON, add `cluster_ip` to the top-level of `processed_data` before saving:

```python
processed_data["cluster_ip"] = cluster_ip  # from the job args
```

- After generating the PDF, write a sidecar `.meta.json`:

```python
meta = {"cluster_ip": cluster_ip, "cluster_name": cluster_name, "timestamp": timestamp}
(pdf_path.parent / (pdf_path.stem + ".meta.json")).write_text(json.dumps(meta))
```

**File: [src/oneshot_runner.py](src/oneshot_runner.py)** (`_run_report`):

- Same changes: add `cluster_ip` to the JSON data dict and write PDF sidecar `.meta.json`.

### Part B: Improve scanner to resolve existing reports

**File: [src/result_scanner.py](src/result_scanner.py):**

1. In `__init`__, build a **secondary** lookup map `api_cluster_name → cluster_ip` by scanning existing `vast_data_*.json` files that **do** have a `cluster_summary.name` and a profile-matched IP:

```python
# Also map cluster API names to IPs from existing JSON data
for jf in (self._data_dir / "reports").glob("vast_data_*.json"):
    try:
        data = json.loads(jf.read_text(encoding="utf-8"))
        api_name = data.get("cluster_summary", {}).get("name", "")
        cip = data.get("cluster_ip", "")
        if api_name and cip:
            self._cluster_name_to_ip[api_name.lower()] = cip
    except Exception:
        pass
```

1. In `_resolve_report_cluster_ip`, also check for a sidecar `.meta.json`:

```python
meta_path = filepath.with_suffix(".meta.json")
if not meta_path.exists():
    meta_path = filepath.parent / (filepath.stem + ".meta.json")
if meta_path.exists():
    cip = json_cluster_ip(meta_path)
    if cip:
        return cip
```

1. For paired JSON+PDF with the same cluster name and timestamp, cross-reference: if a `vast_data_{name}_{ts}.json` has `cluster_ip`, use it for the matching `vast_asbuilt_report_{name}_{ts}.pdf`.

---

## BUG-6: One-Shot default creds use single user for all operations

**Root cause:** The frontend sends one `username`/`password` pair (`admin`/`<default-password>` when defaults are ON). vperfsanity needs `admin`/`<default-password>` (correct), but Report Generator and Health Checks need `support`/`654321` (not provided).

**Fix — credential-per-phase routing:**

**File: [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html):**

- Pass a `use_default_creds` flag in the One-Shot start payload:

```javascript
payload.use_default_creds = document.getElementById('useDefaultCreds').checked;
```

**File: [src/app.py](src/app.py):**

- Pass `use_default_creds` through to `OneShotRunner`:

```python
use_default_creds = data.get("use_default_creds", False)
runner = OneShotRunner(..., use_default_creds=use_default_creds)
```

**File: [src/oneshot_runner.py](src/oneshot_runner.py):**

1. Add `use_default_creds: bool = False` parameter to `__init`__ and store as `self._use_default_creds`
2. Add a `SUPPORT_CREDENTIALS` constant:

```python
_SUPPORT_CREDS = {"username": "support", "password": "654321"}
```

1. Add a helper method `_get_api_creds(phase)`:

```python
def _get_api_creds(self, phase: str) -> Dict[str, str]:
    """Return API credentials appropriate for the given phase."""
    if self._use_default_creds and phase in ("health_checks", "report"):
        return {"username": "support", "password": "654321"}
    return {"username": self._credentials.get("username", ""),
            "password": self._credentials.get("password", "")}
```

1. In `_run_health_checks()` and `_run_report()`, use `self._get_api_creds("health_checks")` / `self._get_api_creds("report")` instead of `self._credentials.get("username")` / `self._credentials.get("password")`:

```python
api_creds = self._get_api_creds("health_checks")
api = create_vast_api_handler(
    cluster_ip=self._credentials["cluster_ip"],
    username=api_creds["username"],
    password=api_creds["password"],
    token=self._credentials.get("api_token"),
    config=config,
)
```

1. `_run_operations()` continues using `self._credentials` as-is (admin/<default-password> works for vperfsanity).

---

## File Change Summary

| File                                                             | Changes                                                                                                                                                                       |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `frontend/templates/advanced_ops.html`                           | BUG-1: await fetchProfiles/loadWorkflows; BUG-2: save/restore per-op checklist; BUG-3: set cursor on clear; BUG-4: fix mode restore logic; BUG-6: pass use_default_creds flag |
| `src/oneshot_runner.py`                                          | BUG-5: write sidecar meta + embed cluster_ip in JSON; BUG-6: add per-phase credential routing                                                                                 |
| `src/app.py`                                                     | BUG-5: embed cluster_ip in JSON + write PDF sidecar; BUG-6: pass use_default_creds to runner                                                                                  |
| `src/result_scanner.py`                                          | BUG-5: check sidecar meta, build API-name-to-IP map from existing JSON                                                                                                        |
| `tests/test_oneshot_runner.py`                                   | BUG-6: test credential routing per phase                                                                                                                                      |
| `tests/test_result_scanner.py` or `tests/test_result_bundler.py` | BUG-5: test sidecar resolution and API-name mapping                                                                                                                           |
| `docs/TODO-ROADMAP.md`                                           | Move BUG-1–6 to Done when fixed                                                                                                                                               |
