---
name: OneShot Mode Aligned Plan
overview: Implement the One-Shot mode for Advanced Operations with full alignment to project rules, architecture guardrails, and tracking documents. Includes remediation for identified documentation and architectural gaps.
todos:
  - id: doc-tracking
    content: "Step 1: Update TODO-ROADMAP (AO-16), CHANGELOG, architecture-03.mdc, and testing-standards-06.mdc for gap remediation and progress tracking"
    status: completed
  - id: oneshot-runner
    content: "Step 2: Create src/oneshot_runner.py with OneShotRunner class (pre-validation, sequential execution, health checks, report generation, auto-bundling)"
    status: completed
  - id: flask-routes
    content: "Step 3: Add one-shot Flask routes to src/app.py (validate, start, status, cancel) with config keys"
    status: completed
  - id: frontend-toggle
    content: "Step 4: Add toggle switch and one-shot checkbox UI to frontend/templates/advanced_ops.html"
    status: completed
  - id: frontend-validation
    content: "Step 5: Add pre-validation results panel and proceed/stop flow to advanced_ops.html"
    status: completed
  - id: frontend-progress
    content: "Step 6: Add one-shot progress tracking (phase indicator, operation counter) to advanced_ops.html"
    status: completed
  - id: tests
    content: "Step 7: Create tests/test_oneshot_runner.py with pre-validation, sequencing, cancellation, and bundling tests"
    status: completed
  - id: user-docs
    content: "Step 8: Update ADVANCED-OPERATIONS.md and POST-INSTALL-VALIDATION.md with one-shot mode documentation"
    status: completed
  - id: lint-verify
    content: "Step 9: Run flake8, black check, and full test suite to verify no regressions"
    status: completed
isProject: false
---

# One-Shot Mode for Advanced Operations — Alignment-Verified Plan

## Alignment Assessment

### Gaps Identified

**GAP-1: Architecture Rule Drift ([architecture-03.mdc](.cursor/rules/architecture-03.mdc))**
The "Web UI Layer (app.py)" section lists page routes for Dashboard, Generate, Reports, Config, Library, and Health Check — but **does not list Advanced Operations** (`/advanced-ops`) or any of its 15+ sub-routes. The "Module Boundaries" section omits `advanced_ops.py`, `script_runner.py`, `tool_manager.py`, `session_manager.py`, `result_bundler.py`, and the `workflows/` package. Adding `oneshot_runner.py` without fixing this widens the drift.

**GAP-2: Missing Config Key (`DEVELOPER_MODE`)**
`architecture-03.mdc` lists Config keys but omits `DEVELOPER_MODE`, which gates all Advanced Ops access via the `before_request` guard at line 206 in [app.py](src/app.py).

**GAP-3: No Tracking Item for One-Shot Mode ([TODO-ROADMAP.md](docs/TODO-ROADMAP.md))**
The roadmap has AO-0 through AO-15 (hardening, in progress). There is no AO-16 for the one-shot feature. Per `todo-tracking-09.mdc`, all planned work must be tracked in this file.

**GAP-4: Testing Standards Rule Incomplete ([testing-standards-06.mdc](.cursor/rules/testing-standards-06.mdc))**
"What to Test for Each Layer" only documents `api_handler`, `data_extractor`, `report_builder`. It omits Advanced Ops modules (`advanced_ops`, `workflows`, `health_checker`, `script_runner`, `tool_manager`, `result_bundler`) and the planned `oneshot_runner`.

**GAP-5: ADVANCED-OPERATIONS.md Missing One-Shot Documentation ([ADVANCED-OPERATIONS.md](docs/ADVANCED-OPERATIONS.md))**
Currently documents only the step-by-step mode. One-shot mode needs a dedicated section describing the toggle, checkbox selection, pre-validation, execution flow, and auto-bundling.

**GAP-6: POST-INSTALL-VALIDATION.md Enhancement ([POST-INSTALL-VALIDATION.md](docs/POST-INSTALL-VALIDATION.md))**
The recommended post-install sequence (Health Tier 1 then 2+3 then Advanced Ops then Bundle) is exactly what one-shot automates. Should reference one-shot as the streamlined automated path.

**GAP-7: Coverage Threshold Inconsistency (informational)**

- `testing-standards-06.mdc`: "Minimum 80% line coverage"
- `ci-pipeline-13.mdc`: "Minimum 49% enforced... raise toward 80%"
- `TODO-ROADMAP.md` QG-3: "cov-fail-under=55"
- Not a blocker for this plan, but noted for future reconciliation.

### Consistency Patterns to Follow

- **Credential dict structure**: Match the pattern used by existing Advanced Ops routes (lines 441-450 in `app.py`): `cluster_ip`, `username`, `password`, `api_token`, `node_user`, `node_password`, `switch_user`, `switch_password`, `vip_pool`
- **Cancellation**: Use `threading.Event` consistent with `AdvancedOpsManager._cancel_event`
- **Output callback**: Use `(level: str, message: str, details: Optional[str]) -> None` signature matching `AdvancedOpsManager._emit_output`
- **Report output path**: Save generated report to the same `reports/` directory as `_run_report_job` so the `/reports` page and `ResultBundler` both pick it up
- **Cluster scoping**: Pass `cluster_ip` to `ResultBundler.collect_results()` for auto-bundling, matching the existing cluster-scoped filtering

---

## Implementation Steps

### Step 1: Document Planned Enhancements for Progress Tracking

Update all tracking and governance files before writing code:

- **[TODO-ROADMAP.md](docs/TODO-ROADMAP.md)**: Add `AO-16` (One-Shot orchestration mode) as "In progress" with sub-items for backend, routes, UI, tests, and documentation
- **[CHANGELOG.md](CHANGELOG.md)**: Add one-shot entries under `[Unreleased] > Added`
- **[architecture-03.mdc](.cursor/rules/architecture-03.mdc)**: Remediate GAP-1 and GAP-2 by:
  - Adding Advanced Operations routes to the Web UI Layer section
  - Adding `oneshot_runner.py` to the module list
  - Adding module boundary rules: `oneshot_runner.py` may import `health_checker`, `advanced_ops`, `result_bundler`, and the report pipeline; it must NOT import `data_extractor` or `report_builder` directly (goes through the report pipeline helper)
  - Adding `DEVELOPER_MODE` to Config keys
- **[testing-standards-06.mdc](.cursor/rules/testing-standards-06.mdc)**: Add Advanced Ops and one-shot testing expectations to "What to Test for Each Layer"

### Step 2: Create `src/oneshot_runner.py`

New orchestrator class `OneShotRunner`:

- **Constructor**: Accepts selected operation IDs, credentials dict, flags (`include_report`, `include_health_tiers`), `threading.Event` for cancellation, output callback
- `**run_prevalidation()`**: Returns structured results (list of check dicts with `name`, `status` (pass/warn/fail/info), `message`):
  - Credentials completeness (cluster_ip, API creds required; SSH creds required if SSH-dependent ops selected)
  - Cluster API reachability (attempt `GET /api/clusters/` with timeout)
  - Node SSH reachability (if SSH ops selected, attempt SSH connect to one CNode) — warn with proceed/stop option on failure
  - Switch SSH reachability (if switch ops selected, attempt SSH connect to one switch) — warn with proceed/stop option on failure
  - Cluster outbound internet access (required if **vnetmap**, **vast support tools**, or **vperfsanity** is selected — these workflows download files directly to the cluster; test outbound HTTPS from cluster via SSH `curl -sI https://github.com`)
  - Tool freshness (check `ToolManager.get_all_tools_info()` for stale tools, **warn if >10 days old**)
  - vperfsanity duration warning (if selected, return info-level notice about ~30 min runtime)
- `**run_all()`**: Sequential execution with phase tracking:
  1. **Phase: Health Checks** — instantiate `HealthChecker`, run `run_all_checks(tiers=[1,2,3])`, save JSON result
  2. **Phase: Operations** — for each selected operation ID, get workflow instance from `WorkflowRegistry`, call each step sequentially (reuse the same credential-passing and step execution pattern from `AdvancedOpsManager.run_step`)
  3. **Phase: Report** — if `include_report` flag set, run the report pipeline (API handler, data extractor, report builder) following the same flow as `_run_report_job` in `app.py`
  4. **Phase: Bundle** — instantiate `ResultBundler`, collect cluster-scoped results, create ZIP
- **Progress tracking**: Expose `get_state()` returning current phase name, operation index, total operations, overall percent complete
- **Cancellation**: Check `cancel_event.is_set()` between each phase and between each workflow step

### Step 3: Add One-Shot Flask Routes to `src/app.py`

Under the existing Advanced Operations route section, add:

- `POST /advanced-ops/oneshot/validate` — calls `OneShotRunner.run_prevalidation()`, returns JSON check results
- `POST /advanced-ops/oneshot/start` — creates `OneShotRunner`, spawns background thread, stores runner in app config
- `GET /advanced-ops/oneshot/status` — returns runner state (phase, progress, running flag)
- `POST /advanced-ops/oneshot/cancel` — sets cancel event on the stored runner

Config keys to add: `ONESHOT_RUNNING`, `ONESHOT_RESULT`, `ONESHOT_LOCK`, `ONESHOT_CANCEL`

Guard: These routes must also be gated by `DEVELOPER_MODE` (already handled by the existing `before_request` guard on `/advanced-ops` prefix).

### Step 4: Add Toggle Switch and One-Shot Checkbox UI

In [advanced_ops.html](frontend/templates/advanced_ops.html):

- Add a toggle switch at the top of the "Select Operation" tile: "Step-by-Step | One-Shot"
- When toggled to One-Shot:
  - Hide the current workflow dropdown and step-by-step controls
  - Show a checkbox list of all available operations (fetched from `/advanced-ops/workflows`)
  - Show a "Health Checks (Tiers 1-3)" checkbox (checked by default, not removable)
  - Show an "Include As-Built Report" checkbox
  - Show a "Run Pre-Validation" button and a "Start One-Shot" button (disabled until validation passes or user acknowledges warnings)

### Step 5: Add Pre-Validation Results Panel and Proceed/Stop Flow

In `advanced_ops.html`:

- When "Run Pre-Validation" is clicked, POST to `/advanced-ops/oneshot/validate`
- Display results as a checklist with pass (green check), warn (yellow triangle), fail (red X), info (blue i) icons
- **Health Check connectivity warnings**: If node or switch SSH reachability fails, show a targeted warning: "SSH connectivity issue detected — some health check tiers may be skipped. Proceed anyway or stop to fix credentials/network." with "Proceed Anyway" and "Stop & Fix" buttons
- **Internet access failure**: If outbound access check fails and download-dependent ops are selected (vnetmap, support tools, vperfsanity), show: "Cluster cannot reach external resources — selected operations require internet to download tools. Proceed anyway (will likely fail) or deselect these operations."
- **Tool freshness warning**: If tools are >10 days old, show: "Deployment tools are N days old. Consider updating before running."
- General flow: "Proceed Anyway" acknowledges all warnings and enables the "Start One-Shot" button; "Stop & Fix" keeps the button disabled

### Step 6: Add One-Shot Progress Tracking UI

In `advanced_ops.html`:

- Phase indicator showing: "Health Checks" then "Operations (2/4)" then "Generating Report" then "Bundling Results"
- Reuse the existing output pane for live output streaming (poll `/advanced-ops/output`)
- On completion, auto-show download button for the bundle (reuse existing bundle download flow)
- Cancel button sends POST to `/advanced-ops/oneshot/cancel`

### Step 7: Create `tests/test_oneshot_runner.py`

Unit tests covering:

- Pre-validation: all-pass scenario, missing credentials, unreachable cluster, SSH connectivity failures (node and switch), outbound internet failure when download-dependent ops selected, tool freshness >10 days warning, vperfsanity duration info notice
- Pre-validation: internet check skipped when no download-dependent ops are selected
- Sequential execution: health checks run first, then selected ops in order, then report, then bundle
- Cancellation: cancel mid-health-check, cancel between operations
- Bundle: verify auto-bundling passes cluster_ip to ResultBundler
- Progress: verify phase and operation tracking state transitions
- Error handling: workflow step failure stops sequence, reports error state

### Step 8: Update User-Facing Documentation

- **[ADVANCED-OPERATIONS.md](docs/ADVANCED-OPERATIONS.md)**: Add "One-Shot Mode" section covering toggle, operation selection, pre-validation checks, execution order, auto-bundling, and cancellation
- **[POST-INSTALL-VALIDATION.md](docs/POST-INSTALL-VALIDATION.md)**: Add note in the "Recommended Sequence" section that One-Shot mode automates the full Health Check then Operations then Report then Bundle sequence

### Step 9: Lint, Format, and Test Verification

- `flake8 src/ tests/`
- `black --check --line-length 120 src/ tests/`
- `python3 -m pytest tests/ -v --cov=src`
- Confirm no regressions in existing test suite

---

## Separate Effort: Bundle Contents and summary.md Definition

**Not in scope for this plan.** As a follow-up task (to be tracked as AO-17 or similar in TODO-ROADMAP.md):

- Audit all workflow output file types and determine which should be included in the validation bundle
- Define the structure and parsed data to include in a `summary.md` file generated inside the bundle
- Determine which result data (health check pass/fail counts, operation outcomes, report metadata, timestamps) should be formatted into the summary
- This effort will inform enhancements to `ResultBundler.create_bundle()` and may add a new `_generate_summary_markdown()` method
