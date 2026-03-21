# Health Check Module -- Agent Implementation Guide

**Purpose:** Complete implementation specification for the Cluster Deployment Health Check module. Designed for delegation to cost-efficient AI agents with minimal context overhead.

**Plan Reference:** `.cursor/plans/health_check_module_1c149000.plan.md`
**Last Updated:** 2026-03-19

---

## Table of Contents

1. [Agent Assignment Strategy](#1-agent-assignment-strategy)
2. [Work Packages](#2-work-packages)
3. [WP-1: HealthChecker Core Module](#wp-1-healthchecker-core-module)
4. [WP-2: API Handler Extensions](#wp-2-api-handler-extensions)
5. [WP-3: Data Extractor Integration](#wp-3-data-extractor-integration)
6. [WP-4: Flask Routes and Job Management](#wp-4-flask-routes-and-job-management)
7. [WP-5: Health Check UI Template](#wp-5-health-check-ui-template)
8. [WP-6: Report Builder -- Health Check Sections](#wp-6-report-builder-health-check-sections)
9. [WP-7: Standalone Report Generation](#wp-7-standalone-report-generation)
10. [WP-8: Generate Page Integration](#wp-8-generate-page-integration)
11. [WP-9: SSH Health Checks (Tier 2-3)](#wp-9-ssh-health-checks-tier-2-3)
12. [WP-10: Prometheus Metrics Parser](#wp-10-prometheus-metrics-parser)
13. [WP-11: Unit Tests](#wp-11-unit-tests)
14. [WP-12: Integration Tests](#wp-12-integration-tests)
15. [WP-13: Documentation and Release](#wp-13-documentation-and-release)
16. [Rules Recommendations](#14-rules-recommendations)
17. [MCP Integration Recommendations](#15-mcp-integration-recommendations)
18. [CI/CD Adjustments](#16-cicd-adjustments)
19. [Dependency Graph](#17-dependency-graph)
20. [Appendix: File Inventory](#18-appendix-file-inventory)

---

## 1. Agent Assignment Strategy

### Model Tiers

| Tier | Model Class | Cost | Use For | Token Budget |
|------|------------|------|---------|--------------|
| **T1 (Fast)** | Claude Haiku / GPT-4o-mini | ~$0.25/M input | Boilerplate, templates, CSS, simple functions, test scaffolding, documentation | 8K-15K output |
| **T2 (Standard)** | Claude Sonnet / GPT-4o | ~$3/M input | Business logic, API integration, data flow, Flask routes, report builder methods | 15K-30K output |
| **T3 (Advanced)** | Claude Opus / o1 | ~$15/M input | Architecture decisions, complex SSH orchestration, cross-module integration review, debugging | 5K-15K output |

### Assignment Principles

- **Minimize context window:** Each work package (WP) specifies exactly which files the agent must read. Never load the full codebase.
- **One WP per agent session:** Each WP is scoped to complete in a single agent turn (< 30K output tokens).
- **Explicit interfaces:** WPs define input/output contracts so agents don't need to read upstream/downstream code.
- **Test-alongside:** Each WP that produces code also produces its own tests (except WP-11/12 which are test-only).
- **Sequential gates:** WPs have explicit dependencies. Do not start a WP until its dependencies pass CI.

### Work Package Overview

| WP | Description | Model | Dependencies | Est. Tokens | Files Modified/Created |
|----|------------|-------|-------------|-------------|----------------------|
| WP-1 | HealthChecker core module | T2 | None | 20K | `src/health_checker.py` (new) |
| WP-2 | API handler extensions | T2 | None | 12K | `src/api_handler.py` |
| WP-3 | Data extractor integration | T1 | WP-1 | 8K | `src/data_extractor.py` |
| WP-4 | Flask routes + job management | T2 | WP-1, WP-2 | 15K | `src/app.py` |
| WP-5 | Health check UI template | T1 | WP-4 | 12K | `frontend/templates/health.html`, `frontend/templates/base.html` |
| WP-6 | Report builder sections | T2 | WP-1, WP-3 | 20K | `src/report_builder.py` |
| WP-7 | Standalone report generation | T1 | WP-6 | 8K | `scripts/regenerate_report.py` |
| WP-8 | Generate page integration | T1 | WP-1, WP-4, WP-6 | 8K | `src/app.py`, `frontend/templates/generate.html` |
| WP-9 | SSH health checks (Tier 2-3) | T2 | WP-1 | 18K | `src/health_checker.py` |
| WP-10 | Prometheus metrics parser | T2 | WP-2 | 10K | `src/api_handler.py`, `src/health_checker.py` |
| WP-11 | Unit tests | T1 | WP-1 through WP-10 | 20K | `tests/test_health_checker.py` (new), `tests/test_api_handler.py` |
| WP-12 | Integration tests | T1 | WP-11 | 10K | `tests/test_integration.py`, `tests/test_app.py` |
| WP-13 | Documentation + release prep | T1 | All | 10K | `docs/`, `CHANGELOG.md`, `README.md`, `docs/TODO-ROADMAP.md` |

---

## 2. Work Packages

Each WP below contains:
- **Context files** (what the agent MUST read before coding)
- **Interface contract** (inputs, outputs, types)
- **Implementation specification** (what to build)
- **Acceptance criteria** (how to verify)
- **Anti-patterns** (what NOT to do)

---

## WP-1: HealthChecker Core Module

**Model:** T2 (Standard)
**Creates:** `src/health_checker.py`
**Context files to read:**

- `.cursor/rules/python-standards-04.mdc` (coding standards)
- `.cursor/rules/architecture-03.mdc` (module boundaries)
- `.cursor/rules/config-security-11.mdc` (credential handling)
- `src/api_handler.py` lines 1-60 (VastClusterInfo, VastHardwareInfo dataclasses)
- `src/utils/ssh_adapter.py` lines 1-50 (run_ssh_command, run_interactive_ssh signatures)
- `src/utils/logger.py` lines 1-30 (get_logger usage)

### Interface Contract

```python
# src/health_checker.py

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple
import time
import logging

@dataclass
class HealthCheckResult:
    check_name: str
    category: str       # "api" | "node_ssh" | "switch_ssh" | "performance" | "custom"
    status: str         # "pass" | "fail" | "warning" | "skipped" | "error"
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    duration_seconds: float = 0.0

@dataclass
class HealthCheckReport:
    cluster_ip: str
    cluster_name: str
    cluster_version: str
    timestamp: str
    results: List[HealthCheckResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    manual_checklist: List[Dict[str, str]] = field(default_factory=list)
    tiers_run: List[int] = field(default_factory=list)

class HealthChecker:
    def __init__(
        self,
        api_handler: Any,
        ssh_config: Optional[Dict[str, str]] = None,
        switch_ssh_config: Optional[Dict[str, str]] = None,
        cancel_event: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None: ...

    def run_all_checks(self, tiers: Optional[List[int]] = None) -> HealthCheckReport: ...
    def run_api_checks(self) -> List[HealthCheckResult]: ...
    def run_node_ssh_checks(self) -> List[HealthCheckResult]: ...
    def run_switch_ssh_checks(self) -> List[HealthCheckResult]: ...
    def run_custom_scripts(self, scripts: List[Dict[str, str]]) -> List[HealthCheckResult]: ...
```

### Implementation Specification

**`run_api_checks()` must implement these checks (in order):**

1. `_check_cluster_raid_health` -- GET clusters/, check `ssd_raid_state`, `nvram_raid_state`, `memory_raid_state`, `mio_raid_state`, `rio_nvram_state` == "HEALTHY"
2. `_check_raid_rebuild_progress` -- GET clusters/, check `ssd_raid_rebuild_progress`, `nvram_raid_rebuild_progress`, `memory_raid_rebuild_progress` are 0 or null
3. `_check_leader_state` -- GET clusters/, check `leader_state`
4. `_check_cluster_state` -- GET clusters/, check `state` == "ONLINE", `enabled` == true
5. `_check_expansion_state` -- GET clusters/, `expansion_state`; pass if null/empty, warning if active
6. `_check_upgrade_state` -- GET clusters/, `upgrade_state`; pass if null/empty, warning if active
7. `_check_cnode_status` -- GET cnodes/, all `status` == "ACTIVE" and `enabled` == true
8. `_check_dnode_status` -- GET dnodes/, all `status` == "ACTIVE" and `enabled` == true
9. `_check_dbox_status` -- GET dboxes/, all `state` == "ACTIVE"
10. `_check_firmware_consistency` -- GET cnodes/, dnodes/, dtrays/, v1/switches/; group firmware versions by node type; flag mismatches
11. `_check_active_alarms` -- GET alarms/ (NEW); no unresolved critical/major alarms; graceful 404 → skip
12. `_check_events` -- GET events/ (NEW); no recent critical events; graceful 404 → skip
13. `_check_vip_pools` -- GET vippools/; at least 1 pool configured and enabled
14. `_check_network_settings` -- GET vms/1/network_settings/, dns/, ntps/; DNS + NTP + gateway populated
15. `_check_license` -- GET clusters/, `license` field present and active
16. `_check_capacity` -- GET clusters/, `physical_space_in_use_percent` < 80 (configurable)
17. `_check_handle_usage` -- GET clusters/, `used_handles_percent` < 80
18. `_check_performance_baseline` -- GET clusters/, capture `iops`, `latency`, `bw`, `rd_*`, `wr_*` (informational only, always "pass")
19. `_check_replication` -- GET clusters/ + protectionpolicies/; if DR enabled, verify healthy
20. `_check_snapshots` -- GET snapshots/ (NEW); no failed snapshots
21. `_check_quotas` -- GET quotas/ (NEW); no blocked users
22. `_check_data_protection` -- GET protectionpolicies/, snapprograms/; at least 1 active policy
23. `_check_monitoring_config` -- GET snmp/, syslog/; configured (warning if not)

**Each check method pattern:**

```python
def _check_cluster_raid_health(self) -> HealthCheckResult:
    start = time.time()
    try:
        cluster_data = self.api_handler._make_api_request("clusters/")
        if not cluster_data:
            return HealthCheckResult(
                check_name="Cluster RAID Health",
                category="api",
                status="error",
                message="Failed to retrieve cluster data",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        # Normalize list response
        if isinstance(cluster_data, list) and cluster_data:
            cluster_data = cluster_data[0]

        raid_fields = {
            "ssd_raid_state": cluster_data.get("ssd_raid_state", "Unknown"),
            "nvram_raid_state": cluster_data.get("nvram_raid_state", "Unknown"),
            "memory_raid_state": cluster_data.get("memory_raid_state", "Unknown"),
        }
        unhealthy = {k: v for k, v in raid_fields.items() if v != "HEALTHY"}
        if unhealthy:
            return HealthCheckResult(
                check_name="Cluster RAID Health",
                category="api",
                status="fail",
                message=f"Unhealthy RAID: {unhealthy}",
                details=raid_fields,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        return HealthCheckResult(
            check_name="Cluster RAID Health",
            category="api",
            status="pass",
            message="All RAID subsystems healthy",
            details=raid_fields,
            timestamp=self._now(),
            duration_seconds=time.time() - start,
        )
    except Exception as e:
        return HealthCheckResult(
            check_name="Cluster RAID Health",
            category="api",
            status="error",
            message=f"Check failed: {e}",
            timestamp=self._now(),
            duration_seconds=time.time() - start,
        )
```

**Manual checklist items (always appended to report):**

```python
MANUAL_CHECKLIST = [
    {"item": "Failover Testing", "description": "VMS migration and leader reboot test", "status": "Manual Verification Required"},
    {"item": "VIP Movement / ARP Validation", "description": "Mount from client, generate IO, disable CNode, verify recovery", "status": "Manual Verification Required"},
    {"item": "Password Management", "description": "Verify default passwords changed for root, vastdata, IPMI admin", "status": "Manual Verification Required"},
]
```

**Helper methods:**

- `_now()` -- returns ISO format timestamp
- `_summarize(results)` -- counts pass/fail/warning/skipped/error
- `_check_cancel()` -- raises if `cancel_event` is set
- `to_dict(report)` -- converts HealthCheckReport to JSON-serializable dict via `asdict()`
- `save_json(report, output_dir)` -- saves to `output/health/health_check_{cluster}_{timestamp}.json`

### Acceptance Criteria

- [ ] All 23 API check methods implemented with try/except and timing
- [ ] `run_api_checks()` calls each and returns List[HealthCheckResult]
- [ ] `run_all_checks(tiers=[1])` calls `run_api_checks()`; `tiers=[1,2]` also calls `run_node_ssh_checks()`; etc.
- [ ] `cancel_event` checked between each check
- [ ] No credentials in log output
- [ ] No imports from `report_builder` or `data_extractor` (module boundary rule)
- [ ] `black --line-length 120` passes; `flake8` passes; `mypy --ignore-missing-imports` passes
- [ ] Manual checklist appended to every report

### Anti-Patterns

- Do NOT import `report_builder` or call PDF generation from this module
- Do NOT use bare `except:` -- always `except Exception as e:`
- Do NOT log credentials or API tokens
- Do NOT make POST/PUT/DELETE API requests (read-only policy)
- Do NOT hardcode thresholds -- use config dict with defaults

---

## WP-2: API Handler Extensions

**Model:** T2 (Standard)
**Modifies:** `src/api_handler.py`
**Context files to read:**

- `src/api_handler.py` lines 751-830 (`_make_api_request` method)
- `src/api_handler.py` lines 1881-1925 (`get_monitoring_configuration` as pattern for 404 handling)
- `src/api_handler.py` lines 2174-2242 (`get_switches_detail` as pattern for v1 endpoint)
- `.cursor/rules/api-handler-05.mdc` (read-only policy)

### Implementation Specification

Add these new methods to `VastApiHandler` class:

```python
def get_alarms(self) -> List[Dict[str, Any]]:
    """GET /api/alarms/ -- active cluster alarms. Returns [] on 404."""

def get_events(self, limit: int = 100) -> List[Dict[str, Any]]:
    """GET /api/events/ -- event history. Returns [] on 404."""

def get_snapshots(self) -> List[Dict[str, Any]]:
    """GET /api/snapshots/ -- snapshot inventory. Returns [] on 404."""

def get_quotas(self) -> List[Dict[str, Any]]:
    """GET /api/quotas/ -- quota configuration. Returns [] on 404."""

def get_prometheus_metrics(self, metric_path: str = "devices") -> str:
    """GET /api/prometheusmetrics/{metric_path} -- returns raw text/plain.
    Uses requests.get directly (not _make_api_request) since response is text, not JSON.
    Returns empty string on failure."""
```

**Pattern for new list endpoints (follow `get_monitoring_configuration`):**

```python
def get_alarms(self) -> List[Dict[str, Any]]:
    try:
        self.logger.info("Collecting active alarms")
        data = self._make_api_request("alarms/")
        if data and isinstance(data, list):
            self.logger.info(f"Retrieved {len(data)} active alarms")
            return data
        elif data and isinstance(data, dict):
            return [data]
        self.logger.info("No active alarms or endpoint unavailable")
        return []
    except Exception as e:
        self.logger.warning(f"Failed to retrieve alarms: {e}")
        return []
```

**Prometheus metrics method (special -- text response):**

```python
def get_prometheus_metrics(self, metric_path: str = "devices") -> str:
    try:
        url = f"https://{self.cluster_ip}/api/prometheusmetrics/{metric_path}"
        self.logger.info(f"Fetching Prometheus metrics: {metric_path}")
        response = self.session.get(url, verify=self.verify_ssl, timeout=30)
        if response.status_code == 200:
            return response.text
        self.logger.warning(f"Prometheus metrics {metric_path} returned {response.status_code}")
        return ""
    except Exception as e:
        self.logger.warning(f"Failed to fetch Prometheus metrics {metric_path}: {e}")
        return ""
```

**Update `get_all_data()` to include new endpoints:**

Add to the `all_data` dict (after existing keys, before return):

```python
all_data["alarms"] = self.get_alarms()
all_data["events"] = self.get_events()
all_data["snapshots"] = self.get_snapshots()
all_data["quotas"] = self.get_quotas()
```

**Update `scripts/export_swagger.py` probe list:**

Add to the `endpoints` list: `"alarms"`, `"events"`, `"eventdefinitions"`, `"monitors"`, `"snapshots"`, `"quotas"`

### Acceptance Criteria

- [ ] 5 new methods added; all return empty list/string on failure (never raise)
- [ ] All use GET only (read-only policy)
- [ ] `get_prometheus_metrics` handles text/plain response
- [ ] `get_all_data()` includes new keys
- [ ] Existing tests still pass (no regressions)
- [ ] Passes `black`, `flake8`, `mypy`

---

## WP-3: Data Extractor Integration

**Model:** T1 (Fast)
**Modifies:** `src/data_extractor.py`
**Context files to read:**

- `src/data_extractor.py` lines 32-39 (ReportSection dataclass)
- `src/data_extractor.py` lines 1351-1439 (extract_all_data method)
- `src/health_checker.py` (from WP-1) -- HealthCheckReport, HealthCheckResult dataclasses

### Implementation Specification

Add to `extract_all_data()` -- after existing section extractions, before the return statement:

```python
# Health check data (optional -- only present when health check was run)
health_check_data = raw_data.get("health_check_results")
if health_check_data:
    sections["health_check"] = asdict(ReportSection(
        name="health_check",
        title="Cluster Health Check Results",
        data=health_check_data,
        completeness=100.0,
        status="complete",
    ))
    validation_data = health_check_data.get("validation_tests", health_check_data)
    sections["post_deployment_validation"] = asdict(ReportSection(
        name="post_deployment_validation",
        title="Post Deployment Validation",
        data=validation_data,
        completeness=100.0 if any(
            r.get("category") in ("node_ssh", "switch_ssh", "performance")
            for r in health_check_data.get("results", [])
        ) else 50.0,
        status="complete",
    ))
```

### Acceptance Criteria

- [ ] New sections only appear when `health_check_results` key exists in raw_data
- [ ] Existing extraction logic unchanged
- [ ] Passes `black`, `flake8`, `mypy`

---

## WP-4: Flask Routes and Job Management

**Model:** T2 (Standard)
**Modifies:** `src/app.py`
**Context files to read:**

- `src/app.py` lines 167-171 (JOB_RUNNING, JOB_RESULT, JOB_LOCK, JOB_CANCEL pattern)
- `src/app.py` lines 206-244 (POST /generate route as pattern)
- `src/app.py` lines 458-576 (_run_report_job function as pattern)
- `src/app.py` lines 245-280 (/generate/status and /generate/cancel as pattern)
- `.cursor/rules/config-security-11.mdc` (credential handling)

### Implementation Specification

**1. Add health job state (after existing JOB_* lines ~171):**

```python
app.config["HEALTH_JOB_RUNNING"] = False
app.config["HEALTH_JOB_RESULT"] = None
app.config["HEALTH_JOB_LOCK"] = threading.Lock()
app.config["HEALTH_JOB_CANCEL"] = threading.Event()
```

**2. Add routes:**

```python
@app.route("/health")
def health_page():
    """Health check page."""
    return render_template("health.html", version=APP_VERSION)

@app.route("/health/run", methods=["POST"])
def health_run():
    """Start a health check job."""
    with app.config["HEALTH_JOB_LOCK"]:
        if app.config["HEALTH_JOB_RUNNING"]:
            return jsonify({"status": "error", "message": "Health check already running"}), 409
        app.config["HEALTH_JOB_RUNNING"] = True
        app.config["HEALTH_JOB_RESULT"] = None
        app.config["HEALTH_JOB_CANCEL"].clear()

    params = {
        "cluster_ip": request.form.get("cluster_ip", "").strip(),
        "username": request.form.get("username", "").strip(),
        "password": request.form.get("password", ""),
        "api_token": request.form.get("api_token", "").strip(),
        "tiers": request.form.getlist("tiers", type=int) or [1],
        "node_user": request.form.get("node_user", "").strip(),
        "node_password": request.form.get("node_password", ""),
        "switch_user": request.form.get("switch_user", "").strip(),
        "switch_password": request.form.get("switch_password", ""),
    }
    if not params["cluster_ip"]:
        app.config["HEALTH_JOB_RUNNING"] = False
        return jsonify({"status": "error", "message": "Cluster IP required"}), 400

    thread = threading.Thread(
        target=_run_health_job, args=(app, params), daemon=True
    )
    thread.start()
    return jsonify({"status": "started"})

@app.route("/health/status")
def health_status():
    """Get health check job status."""
    return jsonify({
        "running": app.config["HEALTH_JOB_RUNNING"],
        "result": app.config["HEALTH_JOB_RESULT"],
    })

@app.route("/health/cancel", methods=["POST"])
def health_cancel():
    """Cancel running health check."""
    if app.config["HEALTH_JOB_RUNNING"]:
        app.config["HEALTH_JOB_CANCEL"].set()
        return jsonify({"status": "cancelled"})
    return jsonify({"status": "no_job"})

@app.route("/health/results")
def health_results():
    """Get the latest health check results JSON."""
    result = app.config.get("HEALTH_JOB_RESULT")
    if result and result.get("success"):
        return jsonify(result.get("report", {}))
    return jsonify({"error": "No results available"}), 404
```

**3. Add `_run_health_job` function (follow `_run_report_job` pattern):**

```python
def _run_health_job(app_ctx: Flask, params: Dict[str, Any]) -> None:
    with app_ctx.app_context():
        try:
            from src.health_checker import HealthChecker
            from src.api_handler import create_vast_api_handler

            config = _load_config()
            api_handler = create_vast_api_handler(
                params["cluster_ip"], params["username"],
                params["password"], params.get("api_token"), config,
            )
            if not api_handler.authenticate():
                raise RuntimeError("Authentication failed")

            ssh_config = None
            if params.get("node_user") and params.get("node_password"):
                ssh_config = {"username": params["node_user"], "password": params["node_password"]}
            switch_ssh_config = None
            if params.get("switch_user") and params.get("switch_password"):
                switch_ssh_config = {"username": params["switch_user"], "password": params["switch_password"]}

            checker = HealthChecker(
                api_handler=api_handler,
                ssh_config=ssh_config,
                switch_ssh_config=switch_ssh_config,
                cancel_event=app_ctx.config["HEALTH_JOB_CANCEL"],
            )
            report = checker.run_all_checks(tiers=params.get("tiers", [1]))
            report_dict = checker.to_dict(report)

            output_dir = config.get("output", {}).get("directory", "output")
            json_path = checker.save_json(report, output_dir)

            app_ctx.config["HEALTH_JOB_RESULT"] = {
                "success": True,
                "report": report_dict,
                "json_path": json_path,
                "cluster": report.cluster_name,
            }
        except Exception as e:
            app_ctx.config["HEALTH_JOB_RESULT"] = {
                "success": False,
                "error": str(e),
            }
        finally:
            app_ctx.config["HEALTH_JOB_RUNNING"] = False
```

### Acceptance Criteria

- [ ] 5 new routes added: `/health`, `/health/run`, `/health/status`, `/health/cancel`, `/health/results`
- [ ] Health job runs independently from report job (separate state vars)
- [ ] Credentials never logged
- [ ] 409 returned if health check already running
- [ ] Cancel event properly wired
- [ ] Passes `black`, `flake8`, `mypy`

---

## WP-5: Health Check UI Template

**Model:** T1 (Fast)
**Creates:** `frontend/templates/health.html`
**Modifies:** `frontend/templates/base.html`
**Context files to read:**

- `frontend/templates/base.html` (nav structure, block names)
- `frontend/templates/generate.html` (form pattern, profile selector, SSE stream, CSS classes)
- `frontend/static/css/app.css` lines 1-50 (CSS variables: --success, --danger, --warning, --vast-blue)

### Implementation Specification

**`base.html` change:** Add nav link after "Library":

```html
<a href="/health" class="nav-link{% if request.path == '/health' %} active{% endif %}">Health Check</a>
```

**`health.html` structure:** Extends `base.html`. Follow `generate.html` layout conventions exactly.

Sections (all inside a `<form id="healthForm">`):

1. **Cluster Connection** -- cluster_ip, username, password, api_token (same fields as generate.html)
2. **Check Selection** -- checkboxes: Tier 1 (API Checks, default checked), Tier 2 (Node SSH), Tier 3 (Switch SSH); grayed out if SSH creds empty
3. **SSH Credentials** (collapsible `<details>`) -- node_user, node_password, switch_user, switch_password
4. **Action Buttons** -- "Run Health Check" (POST to /health/run), "Cancel" (POST to /health/cancel)
5. **Results Panel** (hidden until results arrive):
   - Summary bar: pass/fail/warning/skipped/error counts with colored badges
   - Results table: check_name, category, status (colored), message, duration
   - Export button: "Download JSON"
6. **Log Stream** -- SSE panel (same pattern as generate.html)

**JavaScript:** Follow the `generate.html` pattern for:
- Form submission via fetch → POST /health/run
- Poll /health/status every 2 seconds
- SSE log stream from /stream/logs
- Render results table on completion
- JSON download via Blob URL

### Acceptance Criteria

- [ ] Page loads at /health with nav link active
- [ ] Form validates cluster_ip before submission
- [ ] Tier 2/3 checkboxes disabled when SSH fields empty
- [ ] Results panel renders pass/fail with correct CSS colors
- [ ] JSON export works via download button
- [ ] Follows VAST Admin dark theme (no custom colors -- use CSS variables)

---

## WP-6: Report Builder -- Health Check Sections

**Model:** T2 (Standard)
**Modifies:** `src/report_builder.py`
**Context files to read:**

- `src/report_builder.py` lines 216-339 (`_build_report_story` -- section order)
- `src/report_builder.py` lines 871-917 (`_create_table_of_contents_dynamic` -- TOC registration)
- `src/report_builder.py` lines 3010-3028 (`_safe_table_value` helper)
- `src/report_builder.py` any one existing section method (e.g., `_create_security_configuration`) for pattern
- `.cursor/rules/report-branding-10.mdc` (branding, section order, PageMarker)

### Implementation Specification

**1. Add to `_build_report_story()` after Security & Authentication, before any appendix:**

```python
# Health Check Results (optional)
health_data = sections.get("health_check", {}).get("data")
if health_data:
    story.extend(self._create_health_check_section(health_data))

# Post Deployment Validation (optional)
validation_data = sections.get("post_deployment_validation", {}).get("data")
if validation_data:
    story.extend(self._create_post_deployment_validation_section(validation_data))
```

**2. Add TOC entries in `_create_table_of_contents_dynamic()`:**

After `("Security & Authentication", 0, "security_config", True)`:

```python
("Cluster Health Check Results", 0, "health_check", True),
("Post Deployment Validation", 0, "post_deploy_validation", True),
```

**3. Implement `_create_health_check_section(self, health_data)`:**

Returns `List[Flowable]`. Structure:

- `PageBreak()`
- `PageMarker("health_check")`
- Section heading: "Cluster Health Check Results"
- Description paragraph
- **Summary Table:** Single row with pass/fail/warning/skipped/error counts (green/red/amber cells)
- **Results Table:** All check results with columns: Check Name, Category, Status, Message, Duration
  - Status cell color: green for pass, red for fail, amber for warning, gray for skipped/error
  - Use `_safe_table_value()` for all cell content
- **Firmware Inventory Sub-table** (if firmware data in details): CNode/DNode firmware versions
- **Active Alarms Sub-table** (if alarm data in details): severity, message, object, time

**4. Implement `_create_post_deployment_validation_section(self, validation_data)`:**

Returns `List[Flowable]`. Structure:

- `PageBreak()`
- `PageMarker("post_deploy_validation")`
- Section heading: "Post Deployment Validation"
- Description paragraph
- **Validation Results Table:** SSH check results (if present)
- **Manual Checklist Table:** Items requiring manual verification (always present)
  - Columns: Item, Description, Status
  - Status shows "Manual Verification Required" in amber

### Acceptance Criteria

- [ ] Both sections only render when data is present
- [ ] TOC entries appear only when sections are rendered
- [ ] PageMarker correctly registered for page number tracking
- [ ] Table styles follow `brand_compliance` patterns
- [ ] `_safe_table_value()` used for all cell content
- [ ] Passes `black`, `flake8`, `mypy`

---

## WP-7: Standalone Report Generation

**Model:** T1 (Fast)
**Modifies:** `scripts/regenerate_report.py`
**Context files to read:**

- `scripts/regenerate_report.py` (current implementation)

### Implementation Specification

Add `--health-only` flag to argparse. When provided with a `health_check_*.json` file:

1. Load the health check JSON
2. Wrap it in the `extract_all_data()` output structure (minimal cluster_summary + health sections)
3. Call `report_builder.generate_pdf_report()` to produce a health-check-only PDF

When provided with a full `vast_data_*.json` that contains `health_check_results`, include health sections in the normal report flow.

### Acceptance Criteria

- [ ] `python scripts/regenerate_report.py health_check_*.json --health-only` produces a PDF
- [ ] Normal regeneration still works unchanged
- [ ] Passes `black`, `flake8`

---

## WP-8: Generate Page Integration

**Model:** T1 (Fast)
**Modifies:** `src/app.py`, `frontend/templates/generate.html`
**Context files to read:**

- `frontend/templates/generate.html` (form fields)
- `src/app.py` lines 206-244 (POST /generate handler)
- `src/app.py` `_run_report_job` function

### Implementation Specification

**`generate.html`:** Add checkbox after port mapping section:

```html
<div class="fieldset-section">Include Health Check</div>
<label><input type="checkbox" name="include_health_check" value="1"> Run cluster health check before report generation</label>
```

**`app.py` POST /generate:** Read `include_health_check` from form params and pass to `_run_report_job`.

**`_run_report_job`:** If `include_health_check`:
1. Create `HealthChecker`, run `run_api_checks()` (Tier 1 only for embedded mode)
2. Add results to `raw_data["health_check_results"]` before calling `data_extractor.extract_all_data()`
3. Health check data flows into JSON output and PDF via existing WP-3/WP-6 integration

### Acceptance Criteria

- [ ] Checkbox visible on generate page
- [ ] When checked, health check runs before report and results appear in PDF
- [ ] When unchecked, no health check runs (no regression)
- [ ] Health check failure does not block report generation

---

## WP-9: SSH Health Checks (Tier 2-3)

**Model:** T2 (Standard)
**Modifies:** `src/health_checker.py` (created in WP-1)
**Context files to read:**

- `src/utils/ssh_adapter.py` (full file -- `run_ssh_command`, `run_interactive_ssh` signatures and behavior)
- `src/external_port_mapper.py` lines 320-410 (`_detect_switch_os` as pattern for switch SSH)
- `src/external_port_mapper.py` lines 930-1008 (`_collect_hostname_to_ip_mapping` as pattern for clush)
- `src/vnetmap_parser.py` (full file -- parser for vnetmap output)

### Implementation Specification

**`run_node_ssh_checks()` methods:**

1. `_check_panic_alert_logs` -- SSH to first CNode, run `clush -g cnodes '/vast/data/logdocker.sh | egrep "PANIC|ALERT|fail"' | grep $(date +%Y-%m-%d)`. Pass if empty output.
2. `_check_management_ping` -- SSH to first CNode, ping all IPMI/mgmt IPs from `vms/1/network_settings/`. Report reachability.
3. `_check_support_tool` -- SSH to CNode, download `vast_support_tools.py`, run inside VAST container, capture output. Parse for CRITICAL findings.
4. `_check_vms_log_bundle` -- SSH to CNode, `tar cvfz` VMS logs, report success/failure.
5. `_check_vnetmap` -- SSH to CNode, run `vnetmap.py` with switch IPs and node IPs. Parse output with `VNetMapParser`.

**`run_switch_ssh_checks()` methods:**

6. `_check_mlag_status` -- SSH to each switch, `nv show mlag`, parse for `peer-alive: True` and `backup-active: True`.
7. `_check_switch_ntp` -- SSH to each switch, `ntpq -p`, verify peers reachable.
8. `_check_switch_config_backup` -- SSH to each switch, `nv config show`, capture for documentation.

**SSH config structure:**

```python
ssh_config = {"username": "vastdata", "password": "...", "cnode_ip": "192.168.2.2"}
switch_ssh_config = {"username": "cumulus", "password": "...", "switch_ips": ["10.x.x.x", "10.x.x.y"]}
```

### Acceptance Criteria

- [ ] All SSH checks use `run_ssh_command` from `ssh_adapter` (cross-platform)
- [ ] Each check returns HealthCheckResult with captured stdout in details
- [ ] Timeout handling (30s default per command)
- [ ] Graceful failure if SSH connection fails
- [ ] No credentials in log output

---

## WP-10: Prometheus Metrics Parser

**Model:** T2 (Standard)
**Modifies:** `src/health_checker.py`, `src/api_handler.py`
**Context files to read:**

- Prometheus exposition format specification (simple: `metric_name{label="value"} numeric_value`)

### Implementation Specification

Add to `health_checker.py`:

```python
def _parse_prometheus_metrics(self, text: str) -> List[Dict[str, Any]]:
    """Parse Prometheus text format into list of {name, labels, value} dicts."""
    results = []
    for line in text.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Parse: metric_name{label1="val1",label2="val2"} value
        if "{" in line:
            name_part, rest = line.split("{", 1)
            labels_part, value_part = rest.rsplit("}", 1)
            labels = dict(
                item.split("=", 1) for item in labels_part.split(",")
                if "=" in item
            )
            labels = {k: v.strip('"') for k, v in labels.items()}
        else:
            parts = line.split()
            name_part = parts[0]
            value_part = parts[1] if len(parts) > 1 else "0"
            labels = {}
        try:
            value = float(value_part.strip())
        except ValueError:
            continue
        results.append({"name": name_part.strip(), "labels": labels, "value": value})
    return results

def _check_device_health(self) -> HealthCheckResult:
    """Check SSD/NVRAM device health via prometheusmetrics/devices."""
    text = self.api_handler.get_prometheus_metrics("devices")
    if not text:
        return HealthCheckResult(..., status="skipped", message="Prometheus devices endpoint unavailable")
    metrics = self._parse_prometheus_metrics(text)
    failed_devices = [m for m in metrics if "state" in m["name"].lower() and m["value"] != 1.0]
    media_errors = [m for m in metrics if "media_error" in m["name"].lower() and m["value"] > 0]
    ...
```

### Acceptance Criteria

- [ ] Parser handles standard Prometheus exposition format
- [ ] Skips comments (lines starting with #) and empty lines
- [ ] Device health check identifies failed devices and media errors
- [ ] Graceful handling of empty response or malformed data

---

## WP-11: Unit Tests

**Model:** T1 (Fast)
**Creates:** `tests/test_health_checker.py`
**Modifies:** `tests/test_api_handler.py`
**Context files to read:**

- `tests/conftest.py` (fixtures)
- `tests/test_api_handler.py` lines 1-50 (test patterns, mock setup)
- `.cursor/rules/testing-standards-06.mdc`

### Implementation Specification

**`tests/test_health_checker.py`:**

```python
class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""
    def test_create_pass_result(self): ...
    def test_create_fail_result(self): ...

class TestHealthChecker:
    """Test HealthChecker with mocked api_handler."""

    @pytest.fixture
    def mock_api_handler(self): ...
    @pytest.fixture
    def checker(self, mock_api_handler): ...

    def test_check_cluster_raid_health_pass(self, checker): ...
    def test_check_cluster_raid_health_fail(self, checker): ...
    def test_check_cluster_raid_health_error(self, checker): ...
    def test_check_cnode_status_all_active(self, checker): ...
    def test_check_cnode_status_inactive(self, checker): ...
    def test_check_alarms_no_alarms(self, checker): ...
    def test_check_alarms_critical(self, checker): ...
    def test_check_alarms_404(self, checker): ...
    def test_check_vip_pools_configured(self, checker): ...
    def test_check_vip_pools_empty(self, checker): ...
    def test_check_capacity_ok(self, checker): ...
    def test_check_capacity_warning(self, checker): ...
    def test_run_api_checks_all_pass(self, checker): ...
    def test_run_api_checks_cancel(self, checker): ...
    def test_run_all_checks_tier1(self, checker): ...
    def test_run_all_checks_tier12_no_ssh(self, checker): ...
    def test_save_json(self, checker, tmp_path): ...
    def test_manual_checklist_always_present(self, checker): ...

class TestPrometheusParser:
    def test_parse_simple_metric(self): ...
    def test_parse_metric_with_labels(self): ...
    def test_parse_comments_ignored(self): ...
    def test_parse_empty_input(self): ...
```

**`tests/test_api_handler.py` additions:**

```python
class TestHealthEndpoints:
    def test_get_alarms_success(self, handler): ...
    def test_get_alarms_404(self, handler): ...
    def test_get_events_success(self, handler): ...
    def test_get_snapshots_success(self, handler): ...
    def test_get_quotas_success(self, handler): ...
    def test_get_prometheus_metrics_success(self, handler): ...
    def test_get_prometheus_metrics_failure(self, handler): ...
```

### Acceptance Criteria

- [ ] Minimum 20 test methods for health_checker
- [ ] Minimum 7 test methods for new API handler methods
- [ ] All tests mock external dependencies (no live API calls)
- [ ] Tests cover success, failure, and edge cases (404, empty data, cancel)
- [ ] `pytest tests/test_health_checker.py -v` passes
- [ ] Coverage of health_checker.py > 80%

---

## WP-12: Integration Tests

**Model:** T1 (Fast)
**Modifies:** `tests/test_integration.py`, `tests/test_app.py`
**Context files to read:**

- `tests/test_integration.py` (existing integration test patterns)
- `tests/test_app.py` (Flask route test patterns)

### Implementation Specification

**`tests/test_app.py` additions:**

```python
class TestHealthRoutes:
    def test_health_page_loads(self, client): ...
    def test_health_run_missing_ip(self, client): ...
    def test_health_run_already_running(self, client): ...
    def test_health_status_no_job(self, client): ...
    def test_health_cancel_no_job(self, client): ...
    def test_health_results_no_data(self, client): ...
```

**`tests/test_integration.py` additions:**

```python
@pytest.mark.integration
class TestHealthCheckIntegration:
    def test_health_check_json_in_report_data(self): ...
    def test_health_check_report_section_present(self): ...
```

### Acceptance Criteria

- [ ] Flask route tests verify HTTP status codes and response structure
- [ ] Integration test verifies health data flows into report JSON
- [ ] All tests pass with `--no-cov`

---

## WP-13: Documentation and Release

**Model:** T1 (Fast)
**Modifies:** Multiple doc files
**Context files to read:**

- `CHANGELOG.md` (format)
- `README.md` (structure)
- `docs/TODO-ROADMAP.md` (tracking format)
- `.cursor/rules/documentation-08.mdc`
- `.cursor/rules/todo-tracking-09.mdc`

### Implementation Specification

**CHANGELOG.md:** Add new version entry with:
- Added: Cluster Deployment Health Check module, health check UI, report sections, new API endpoints
- List all new endpoints, check categories, report sections

**README.md:** Add to Features list. Add Health Check section to Usage.

**docs/TODO-ROADMAP.md:** Move RFE-4 and RFE-5 to "Done" or "In Progress".

**docs/deployment/INSTALLATION-GUIDE.md:** Add health check feature documentation.

### Acceptance Criteria

- [ ] CHANGELOG follows Keep a Changelog format
- [ ] README accurately describes the feature
- [ ] TODO-ROADMAP reflects current status
- [ ] No version bumps (done at release time)

---

## 14. Rules Recommendations

### New Rules to Create

**`health-check-14.mdc`** (globs: `src/health_checker.py`)

```
---
description: Health check module development guidelines
globs: src/health_checker.py
---

# Health Check Module Rules

- Every check method must return a HealthCheckResult (never raise exceptions to callers).
- Every check method must be wrapped in try/except with timing (time.time() for duration).
- Check cancel_event between every check in run_all_checks.
- Thresholds (capacity %, handle %) must come from a config dict with sensible defaults.
- Do NOT import report_builder or data_extractor (module boundary).
- SSH checks must use src/utils/ssh_adapter.py (run_ssh_command / run_interactive_ssh).
- New API calls follow the read-only policy (GET only).
- Prometheus metrics parsing handles text/plain responses (not JSON).
- Log check progress at INFO level; log failures at WARNING.
- Never log credentials, tokens, or passwords.
```

**`health-check-api-15.mdc`** (globs: `src/api_handler.py`)

```
---
description: Health check API extensions
globs: src/api_handler.py
---

# API Handler Health Check Extensions

- New endpoints: alarms/, events/, snapshots/, quotas/, prometheusmetrics/{path}
- All new methods must return empty list/string on failure (never raise).
- prometheusmetrics endpoints return text/plain (not JSON) -- use requests.get directly.
- Add new endpoints to get_all_data() return dict.
- Add new endpoints to scripts/export_swagger.py probe list.
- Follow existing graceful 404 pattern from get_monitoring_configuration().
```

### Existing Rules to Optimize

**`architecture-03.mdc`:** Add HealthChecker to the module diagram:

```
API Handler → Data Extractor → Report Builder
                ↑
Health Checker → (uses API Handler, SSH Adapter)
                ↓
              Data Extractor (optional health data injection)
```

**`testing-standards-06.mdc`:** Add health checker test patterns:

```
- tests/test_health_checker.py mirrors src/health_checker.py
- Mock api_handler for all API checks
- Mock ssh_adapter for all SSH checks
- Test each check: pass, fail, error, 404/skip cases
- Test cancel_event interruption
```

**`report-branding-10.mdc`:** Add health check section order:

```
Section order (updated):
  ...Security & Authentication → Cluster Health Check Results → Post Deployment Validation → Appendix
```

---

## 15. MCP Integration Recommendations

### Atlassian MCP (High Value)

| Integration | Tool | Benefit |
|---|---|---|
| **Auto-update Confluence** on release | `updateConfluencePage` | Update the VAST As-Built Report Generator page (6664028496) with new health check feature documentation |
| **Create Jira issues** for bugs found during development | `createJiraIssue` | Track implementation issues directly in Jira from agent sessions |
| **Pull health check definitions** from Confluence templates | `getConfluencePage` | Dynamically fetch the latest Installation/Expansion Plan validation steps rather than hardcoding |
| **Search for related issues** before creating new ones | `searchJiraIssuesUsingJql` | Avoid duplicate bug reports |

**Recommended workflow:** After completing each WP, use `searchAtlassian` to check if there are related Jira tickets. After final release, use `updateConfluencePage` to sync Confluence documentation.

#### Confluence Sync Configuration (Verified)

| Parameter | Value |
|---|---|
| cloudId | `vastdata.atlassian.net` |
| pageId | `6664028496` |
| spaceId | `5023203330` |
| Title | VAST As-Built Report Generator - v1.3.0 |
| Current version | 20 |
| contentFormat | `markdown` |

**Post-WP-13 sync command:**

```
CallMcpTool: plugin-atlassian-atlassian / updateConfluencePage
  cloudId: "vastdata.atlassian.net"
  pageId: "6664028496"
  contentFormat: "markdown"
  body: <updated markdown with Health Check feature section>
  versionMessage: "Add Health Check module feature documentation"
```

**Jira integration per WP:**

```
CallMcpTool: plugin-atlassian-atlassian / searchJiraIssuesUsingJql
  cloudId: "vastdata.atlassian.net"
  jql: "project = PS AND text ~ \"health check\" ORDER BY updated DESC"
```

### Slack MCP (Medium Value)

| Integration | Tool | Benefit |
|---|---|---|
| **Post build status** to dev channel | `slack_send_message` | Notify team when CI passes/fails for health check WPs |
| **Search for related discussions** | `slack_search_public` | Find prior team discussions about health check requirements |

### GitKraken MCP (High Value for Dev Workflow)

| Integration | Tool | Benefit |
|---|---|---|
| **Create feature branch** per WP | `git_branch` + `git_checkout` | Isolate each WP in its own branch for clean PRs |
| **Commit with conventional format** | `git_add_or_commit` | Enforce commit message standards |
| **Create PRs** per WP | `pull_request_create` | Automate PR creation with WP description |
| **Check PR status** | `gitlens_launchpad` | Monitor open PRs across all WPs |

**Recommended workflow:** Each agent session creates a feature branch (`feature/health-check-wp-N`), commits with conventional format (`feat(health): WP-N description`), and creates a PR. A T3 agent reviews PRs before merge.

### Google Workspace MCP (Low Value for this project)

Not directly useful unless documentation is maintained in Google Docs. Skip for this project.

---

## 16. CI/CD Adjustments

### Immediate Changes (Before Development Starts)

**1. Add `health_checker` to mypy and flake8 scope:**

No change needed -- CI already runs `flake8 src/` and `mypy src/` which will automatically include `src/health_checker.py`.

**2. Update coverage threshold anticipation:**

The new module will add ~600-800 lines of code. Plan to add proportional tests (WP-11, WP-12) to maintain coverage above 46%.

If coverage drops during development, temporarily lower `--cov-fail-under` in `pyproject.toml`:

```toml
# pyproject.toml -- temporary during health check development
addopts = "--cov=src --cov-report=term-missing --cov-report=xml --cov-fail-under=44"
```

Restore to 46% (or higher) after WP-11/WP-12 are merged.

**3. Add health checker to version sync check:**

No change needed -- `scripts/check-version-sync.sh` checks `src/__init__.py`, `src/app.py`, etc. The health checker module doesn't contain version strings.

### New CI Steps to Add

**4. Add Prometheus metrics mock test data:**

Create `tests/data/mock_prometheus_devices.txt` with sample Prometheus exposition format data for testing WP-10.

**5. Add health check integration test marker:**

Already configured -- `pyproject.toml` has `markers = ["integration"]`. Use `@pytest.mark.integration` for health check integration tests.

### Post-Development CI Enhancements

**6. Add a dedicated health-check-tests job (optional, for faster CI feedback):**

```yaml
# .github/workflows/ci.yml -- add after unit-tests job
health-check-tests:
  needs: quality-gate
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - run: pip install -r requirements.txt
    - run: pytest tests/test_health_checker.py -v --no-cov
```

This runs health checker tests independently for faster feedback during development.

**7. Update export_swagger.py probing (after WP-2):**

The swagger export script will probe new endpoints (`alarms/`, `events/`, `snapshots/`, `quotas/`). This produces updated API discovery docs automatically.

**8. Branch strategy for WP development:**

```
main
  └── develop
        ├── feature/health-check-wp-1  (HealthChecker core)
        ├── feature/health-check-wp-2  (API extensions)
        ├── feature/health-check-wp-3  (Data extractor)
        ├── ...
        └── feature/health-check-wp-13 (Docs)
```

Each WP merges into `develop` via PR. After all WPs merged, create release from `develop` → `main`.

---

## 17. Dependency Graph

```
WP-1 (Core) ──────┬──> WP-3 (Extractor) ──> WP-6 (Report) ──> WP-7 (Standalone)
                   │                                │
WP-2 (API) ───────┤                                └──> WP-8 (Generate Integration)
                   │
                   ├──> WP-4 (Routes) ──> WP-5 (UI Template)
                   │
                   ├──> WP-9 (SSH Checks)
                   │
                   └──> WP-10 (Prometheus)

WP-1 through WP-10 ──> WP-11 (Unit Tests) ──> WP-12 (Integration Tests)

All WPs ──> WP-13 (Documentation)
```

**Parallelization opportunities:**
- WP-1 and WP-2 can run in parallel (no dependencies on each other)
- WP-3 and WP-4 can run in parallel (both depend on WP-1 only)
- WP-5 depends on WP-4; WP-6 depends on WP-1 + WP-3
- WP-9 and WP-10 can run in parallel (both depend on WP-1 + WP-2)
- WP-11 should run after all code WPs to avoid rework

**Critical path:** WP-1 → WP-3 → WP-6 → WP-8 → WP-11 → WP-12 → WP-13

---

## 18. Appendix: File Inventory

### New Files

| File | Created By | Description |
|------|-----------|-------------|
| `src/health_checker.py` | WP-1, WP-9, WP-10 | Core health check module |
| `frontend/templates/health.html` | WP-5 | Health check UI page |
| `tests/test_health_checker.py` | WP-11 | Health checker unit tests |
| `tests/data/mock_prometheus_devices.txt` | WP-11 | Mock Prometheus metrics data |
| `.cursor/rules/health-check-14.mdc` | Pre-development | Health check coding rules |
| `.cursor/rules/health-check-api-15.mdc` | Pre-development | API extension rules |

### Modified Files

| File | Modified By | Changes |
|------|-----------|---------|
| `src/api_handler.py` | WP-2, WP-10 | 5 new methods, get_all_data update |
| `src/data_extractor.py` | WP-3 | Health section extraction in extract_all_data |
| `src/app.py` | WP-4, WP-8 | Health routes, job state, generate integration |
| `src/report_builder.py` | WP-6 | 2 new section methods, TOC entries, story update |
| `frontend/templates/base.html` | WP-5 | Nav link |
| `frontend/templates/generate.html` | WP-8 | Health check checkbox |
| `scripts/regenerate_report.py` | WP-7 | --health-only flag |
| `scripts/export_swagger.py` | WP-2 | New endpoints in probe list |
| `tests/test_api_handler.py` | WP-11 | New endpoint tests |
| `tests/test_app.py` | WP-12 | Health route tests |
| `tests/test_integration.py` | WP-12 | Health integration tests |
| `CHANGELOG.md` | WP-13 | New version entry |
| `README.md` | WP-13 | Feature description |
| `docs/TODO-ROADMAP.md` | WP-13 | RFE-4, RFE-5 status update |

### Context Files (Read-Only Reference for Agents)

| File | Referenced By | Purpose |
|------|-------------|---------|
| `.cursor/rules/*.mdc` | All WPs | Coding standards and guardrails |
| `src/utils/ssh_adapter.py` | WP-1, WP-9 | SSH function signatures |
| `src/utils/logger.py` | WP-1 | Logger setup |
| `src/external_port_mapper.py` | WP-9 | SSH patterns for switches |
| `src/vnetmap_parser.py` | WP-9 | vnetmap output parser |
| `frontend/static/css/app.css` | WP-5 | CSS variables and theme |
| `tests/conftest.py` | WP-11, WP-12 | Test fixtures |
