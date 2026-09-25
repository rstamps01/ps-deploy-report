---
name: Nav DevMode and Log Levels
overview: Move Health Check and Configuration nav tabs to developer mode, add a three-tier log level selector (Status/Live/Debug) to the One-Shot output pane with per-check progress reporting, pipe internal logger output for Live mode, implement persistent log storage with 1GB capacity management, and add full window state persistence so the Advanced Ops page resumes its exact state after navigation or browser close/reopen.
todos:
  - id: nav-devmode
    content: Move Health Check and Configuration nav links into developer_mode block; extend route guard
    status: completed
  - id: log-tier-backend
    content: Add log_tier field to output entries; add _emit_live/_emit_debug to OneShotRunner; create _OneShotLogHandler for piping logger output
    status: completed
  - id: health-progress
    content: Emit per-check progress (1/N) and pass/fail/description for each health check result at Status tier
    status: completed
  - id: report-progress
    content: Add step-by-step Status tier progress messages for report generation phase
    status: completed
  - id: log-tier-frontend
    content: Add Status/Live/Debug selector buttons to output header; filter displayed lines by tier; add debug CSS
    status: completed
  - id: state-persistence
    content: Add full Advanced Ops state persistence -- backend state snapshot API, frontend hydration on page load, localStorage for cross-session survival
    status: completed
  - id: ops-log-manager
    content: Create src/utils/ops_log_manager.py with 1GB capacity management, auto-save on completion, purge oldest 25%
    status: completed
  - id: tests-log
    content: Add tests for log tier tagging, per-check progress, OpsLogManager capacity/purge, state snapshot
    status: completed
  - id: docs-log
    content: Update CHANGELOG.md, TODO-ROADMAP.md, ADVANCED-OPERATIONS.md with all completed, planned, and pending items
    status: completed
  - id: future-generate-page
    content: "FUTURE: Apply log level selector, persistent log storage, and window state persistence to the Generate Report page"
    status: pending
isProject: false
---

# Nav Dev-Mode Gating, Dynamic Log Levels, and State Persistence

## Action 1: Move Health Check and Configuration to Developer Mode

### Navigation (`frontend/templates/base.html`)

Move these two links inside the existing `{% if developer_mode %}` block, styled with `nav-link-dev`:

```html
<!-- Currently at lines 25 and 40, outside the dev-mode block -->
<a href="..." class="nav-link ...">Health Check</a>
<a href="..." class="nav-link ...">Configuration</a>
```

Both should be moved into the `{% if developer_mode %}` block alongside Advanced Ops and Validation Results.

### Route guard (`src/app.py`)

Extend `check_developer_mode_access()` (line ~213) to also gate `/health` and `/config`:

```python
if request.path.startswith(("/advanced-ops", "/validation-results", "/health", "/config")):
```

---

## Action 2: Three-Tier Log Level Buttons (Status / Live / Debug)

### Concept

Add a **log level selector** in the output header bar. All messages are always captured in the backend buffer (tagged with a `log_tier`), but the frontend **filters what is visible** based on the selected tier:

- **Status** (default): Operation start/complete banners, progress counters (e.g., "API check 5/28"), phase results summary (pass/fail/warn counts, short failure descriptions)
- **Live**: Everything in Status + all internal `logger.info/warning/error` output piped from `HealthChecker`, report pipeline, and workflow execution
- **Debug**: Everything in Live + `logger.debug` messages

### 2a. Backend: Tag output entries with `log_tier`

**File: `src/advanced_ops.py`** -- Modify `_emit_output()` to accept and store an optional `log_tier` field:

```python
def _emit_output(self, level, message, details=None, log_tier="status"):
    entry = {
        "timestamp": ...,
        "level": level,
        "message": message,
        "details": details,
        "log_tier": log_tier,  # "status" | "live" | "debug"
    }
```

**File: `src/oneshot_runner.py`** -- Add a `_emit_live()` and `_emit_debug()` helper alongside `_emit()`:

```python
def _emit(self, level, message, details=None):
    # Status-tier messages (high-level progress)
    self._output_callback(level, message, details, "status")

def _emit_live(self, level, message, details=None):
    self._output_callback(level, message, details, "live")

def _emit_debug(self, level, message, details=None):
    self._output_callback(level, message, details, "debug")
```

### 2b. Backend: Pipe HealthChecker per-check progress

**File: `src/oneshot_runner.py` `_run_health_checks()`** -- After `checker.run_all_checks()`, iterate the returned results and emit each check at the correct tier:

Currently the code calls `report = checker.run_all_checks(tiers=tiers)` and only emits the summary. Change to:

1. Before `run_all_checks()`: emit status "Running health checks (Tier 1, 2, 3)..."
2. After `run_all_checks()`: iterate `report.results` and for each result:

- Emit **Status** tier: progress counter + result status icon + check name
  - Format: `"  [PASS] Cluster RAID Health (1/28)"` or `"  [FAIL] Active Alarms: 3 critical alarms detected (5/28)"`
- Failed/warning checks also emit to **Status** with the failure message

1. Final Status summary: `"Health checks complete: 25 pass, 2 fail, 1 warning"`

### 2c. Backend: Pipe internal logger for Live mode

**File: `src/oneshot_runner.py`** -- Create a custom logging handler that routes to `_emit_live()`:

```python
class _OneShotLogHandler(logging.Handler):
    def __init__(self, emit_fn):
        super().__init__(logging.DEBUG)
        self._emit = emit_fn
    def emit(self, record):
        tier = "debug" if record.levelno <= logging.DEBUG else "live"
        level_map = {logging.DEBUG: "info", logging.INFO: "info",
                     logging.WARNING: "warn", logging.ERROR: "error",
                     logging.CRITICAL: "error"}
        self._emit(level_map.get(record.levelno, "info"),
                   f"[{record.name}] {record.getMessage()}", log_tier=tier)
```

Attach this handler to the root logger at the start of `run_all()` and remove it at the end:

```python
def run_all(self):
    handler = _OneShotLogHandler(self._emit_raw)
    logging.getLogger().addHandler(handler)
    try:
        # ... existing run logic ...
    finally:
        logging.getLogger().removeHandler(handler)
```

This captures all `logger.info(...)` calls from `HealthChecker`, `api_handler`, `report_builder`, etc. as "live" tier, and `logger.debug(...)` as "debug" tier.

### 2d. Backend: Report generation progress

**File: `src/oneshot_runner.py` `_run_report()`** -- Add status-tier progress between existing steps:

- `"Authenticating with cluster API..."` -> `"Collecting cluster data..."` -> `"Processing data..."` -> `"Generating PDF..."` -> result

### 2e. Frontend: Log level selector buttons

**File: `frontend/templates/advanced_ops.html`**

Add three pill-style buttons in the output header, between the title and the menu button:

```html
<div class="output-header">
    <span class="output-title">OUTPUT RESULTS</span>
    <div class="log-level-selector">
        <button class="log-level-btn active" data-tier="status" onclick="setLogTier('status')">Status</button>
        <button class="log-level-btn" data-tier="live" onclick="setLogTier('live')">Live</button>
        <button class="log-level-btn" data-tier="debug" onclick="setLogTier('debug')">Debug</button>
    </div>
    <div class="output-menu">...</div>
</div>
```

CSS for the buttons (pill group, dark theme, active state with accent color).

### 2f. Frontend: Filter rendering by tier

Modify `OutputPaneCtor`:

- Store `currentTier` property (default `"status"`)
- `_renderEntry()`: add `data-tier` attribute to each `div.output-line`
- `setLogTier(tier)`: update `currentTier`, show/hide lines based on tier hierarchy:
  - `status`: only show `data-tier="status"`
  - `live`: show `status` + `live`
  - `debug`: show all (`status` + `live` + `debug`)
- Use CSS visibility (`display: none` on filtered lines) for instant switching without re-rendering
- Add `.output-line.debug` CSS rule (dim gray color)

### 2g. Frontend: Persist selected tier in sessionStorage

Store as `advanced_ops_log_tier` alongside existing `advanced_ops_output`.

---

## Action 3: Persistent Log Storage with 1GB Capacity

### 3a. Backend log storage

**File: `src/utils/ops_log_manager.py`** (new) -- Module for managing One-Shot operation logs on disk:

```python
class OpsLogManager:
    MAX_LOG_DIR_BYTES = 1_073_741_824  # 1 GB
    PURGE_FRACTION = 0.25

    def __init__(self, log_dir: Path):
        self.log_dir = log_dir

    def save_session_log(self, entries: List[Dict], session_id: str, cluster_ip: str):
        """Write operation log as JSON Lines file."""
        # filename: oneshot_{cluster_ip}_{timestamp}_{session_id}.jsonl

    def check_capacity(self) -> Dict:
        """Return {total_bytes, file_count, over_limit: bool}."""

    def purge_oldest(self) -> Dict:
        """Delete oldest 25% of log files, return purge stats."""

    def list_logs(self) -> List[Dict]:
        """List all saved logs with metadata."""
```

### 3b. Save logs on One-Shot completion

**File: `src/oneshot_runner.py`** -- At the end of `run_all()` (in the `finally` block), call `OpsLogManager.save_session_log()` with the full output buffer. Before saving, call `check_capacity()` and if over limit, `purge_oldest()` and emit a warning.

### 3c. Flask route for capacity check

**File: `src/app.py`** -- Add `/advanced-ops/logs/capacity` (GET) to return current log storage stats, and `/advanced-ops/logs/purge` (POST) for manual purge.

### 3d. Config

**File: `config/config.yaml.template`** -- Add under `logging:`:

```yaml
  ops_log_dir: "logs/operations"
  ops_log_max_bytes: 1073741824  # 1GB
  ops_log_purge_fraction: 0.25
```

---

## Action 4: Advanced Operations Window State Persistence

### Problem

Currently when a user navigates away from the Advanced Ops page (to another tab like Reports or Dashboard) or closes/reopens the browser, they return to a **fresh screen** with no visibility into tests running in the background. The backend retains all state (`AdvancedOpsManager` singleton, `app.config` one-shot keys, output buffer), but the frontend does not rehydrate from it.

### Current state analysis

| Item                                   | Persisted today?       | Storage                                  |
| -------------------------------------- | ---------------------- | ---------------------------------------- |
| Output log lines                       | Yes (tab session only) | `sessionStorage` (`advanced_ops_output`) |
| One-shot running/phase/progress        | Server-side only       | `app.config` + `OneShotRunner._state`    |
| Step-by-step workflow running          | Server-side only       | `AdvancedOpsManager._state`              |
| Mode toggle (step-by-step vs one-shot) | No                     | JS variable `oneShotMode`                |
| Selected profile                       | No                     | Dropdown resets on load                  |
| Credential form values                 | No                     | Default creds applied on load            |
| One-shot checklist selections          | No                     | Lost on reload                           |
| Validation results panel               | No                     | Lost on reload                           |
| Log tier selection                     | No (new feature)       | Will be added                            |

### Solution: Two-layer persistence

**Layer 1 -- Backend state snapshot API** (handles "what is actually running right now"):

New route `GET /advanced-ops/state-snapshot` returns a JSON snapshot of the complete backend state:

```python
{
    "oneshot": {
        "running": true,
        "state": { "status": "running", "phase": "health_checks",
                   "operation_index": 1, "total_operations": 5,
                   "current_operation": "Health Checks (Tiers 1-3)", ... },
        "validated": true,
        "validation_results": [...],
        "result": null
    },
    "workflow": {
        "running": true/false,
        "workflow_id": "switch_config",
        "steps": [...],
        "state": {...}
    },
    "output_count": 247  // total entries in server buffer
}
```

**File: `src/app.py`** -- New route that queries `app.config` and `AdvancedOpsManager`:

```python
@app.route("/advanced-ops/state-snapshot")
def advanced_ops_state_snapshot():
    manager = get_advanced_ops_manager()
    runner = app.config.get("ONESHOT_RUNNER")
    return jsonify({
        "oneshot": {
            "running": app.config.get("ONESHOT_RUNNING", False),
            "state": runner.get_state() if runner else None,
            "result": app.config.get("ONESHOT_RESULT"),
        },
        "workflow": {
            "running": manager.is_running() if hasattr(manager, 'is_running') else False,
            "workflow_id": manager.current_workflow_id if hasattr(manager, 'current_workflow_id') else None,
            "state": manager.get_state() if hasattr(manager, 'get_state') else None,
        },
        "output_count": len(manager._output_buffer),
    })
```

**Layer 2 -- Frontend `localStorage` persistence** (survives browser close/reopen):

Store **UI preferences and selections** in `localStorage` under key `advanced_ops_ui_state`:

```javascript
var UI_STATE_KEY = 'advanced_ops_ui_state';

function saveUIState() {
    var state = {
        mode: oneShotMode ? 'oneshot' : 'step-by-step',
        selectedProfile: document.getElementById('profileSelect').value,
        selectedWorkflow: document.getElementById('operationSelect').value,
        oneShotChecklist: getOneShotChecklist(),  // array of checked op IDs
        includeHealth: document.getElementById('oneShotIncludeHealth').checked,
        includeReport: document.getElementById('oneShotIncludeReport').checked,
        logTier: currentLogTier,
        useDefaultCreds: document.getElementById('useDefaultCreds').checked,
    };
    localStorage.setItem(UI_STATE_KEY, JSON.stringify(state));
}
```

### Frontend hydration on page load (`DOMContentLoaded`)

**File: `frontend/templates/advanced_ops.html`** -- Replace the current static init with a hydration sequence:

```
DOMContentLoaded
  |
  +-- 1. Initialize OutputPane (restore from sessionStorage -- existing)
  |
  +-- 2. Fetch /advanced-ops/state-snapshot
  |       |
  |       +-- If oneshot.running == true:
  |       |     - Switch to one-shot mode
  |       |     - Show one-shot progress UI with current phase/progress
  |       |     - Sync output from server (fetch /advanced-ops/output?since=<localCount>)
  |       |     - Start oneShotPolling()
  |       |
  |       +-- If workflow.running == true:
  |       |     - Switch to step-by-step mode
  |       |     - Load workflow steps for workflow.workflow_id
  |       |     - Update step statuses from workflow.state.steps
  |       |     - Sync output from server
  |       |     - Start polling()
  |       |
  |       +-- If nothing running:
  |             - Restore UI state from localStorage (mode, profile, etc.)
  |
  +-- 3. Restore localStorage UI prefs (profile selection, mode, etc.)
  |
  +-- 4. loadWorkflows(), fetchProfiles() (existing)
```

### Output buffer de-duplication

When the page reloads, `sessionStorage` has entries from before the reload, and the server buffer has entries from the entire session. To avoid duplicates:

- Track `output_sync_cursor` (index into server buffer) in `sessionStorage`
- On hydration: fetch `/advanced-ops/output?since=<cursor>` to get only NEW entries since last sync
- Append only the delta to the output pane

### Credential persistence

Credentials are sensitive, so they are NOT stored in browser storage. Instead:

- If a profile was selected (stored in `localStorage`), auto-load it on hydration via `loadProfile(profileName)`
- Default credentials toggle state is stored in `localStorage` and restored

### `saveUIState()` triggers

Call `saveUIState()` on:

- Mode toggle change
- Profile selection change
- Workflow selection change
- One-shot checklist change
- Default creds toggle change
- Log tier change
- Before `window.unload` (catch browser close)

### One-shot phase UI restoration

When a one-shot is running and the page reloads:

1. `state-snapshot` returns `oneshot.state.phase` (e.g., `"health_checks"`, `"operations"`)
2. Frontend shows the one-shot progress panel with phase dots updated to reflect current state
3. `operation_index` / `total_operations` updates the progress counter
4. Phase dots before the current phase are marked "completed"
5. Polling resumes to get live updates from that point

### Step-by-step restoration

When a step-by-step workflow is running:

1. `state-snapshot` returns `workflow.workflow_id` and step statuses
2. Frontend selects the workflow in the dropdown, loads steps, updates their status badges
3. Polling resumes

---

## File Change Summary

- `frontend/templates/base.html` -- Move Health Check + Configuration links inside dev-mode block
- `src/app.py` -- Extend route guard for `/health` and `/config`; add log capacity routes; add `/advanced-ops/state-snapshot` route
- `src/advanced_ops.py` -- Add `log_tier` field to output entries; expose state for snapshot (ensure `current_workflow_id` and `is_running()` are accessible)
- `src/oneshot_runner.py` -- Add `_emit_live`/`_emit_debug`, per-check health progress, log handler pipe, report progress, save logs on completion
- `frontend/templates/advanced_ops.html` -- Log level selector buttons, tier-based filtering, debug CSS; full state hydration on `DOMContentLoaded`; `localStorage` save/restore of UI state; output de-duplication; one-shot and workflow UI resume
- `src/utils/ops_log_manager.py` -- New module for persistent operation log storage with 1GB cap
- `config/config.yaml.template` -- Add ops log settings
- `tests/test_oneshot_runner.py` -- Add tests for log tier emission, log handler
- `tests/test_ops_log_manager.py` -- New tests for capacity check, purge
- `tests/test_app.py` -- Add test for `/advanced-ops/state-snapshot` route
