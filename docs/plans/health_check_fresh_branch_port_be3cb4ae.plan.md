---
name: Health Check Fresh Branch Port
overview: Port the modular health check feature from feature/health-check to a fresh branch based on origin/main (v1.4.7+), ensuring all code, tests, documentation, and CI changes are properly integrated without legacy merge issues.
todos:
  - id: phase-1-setup
    content: Create feature/health-check-v2 branch from origin/main and copy standalone files
    status: completed
  - id: phase-2-api
    content: Add 5 health check methods to api_handler.py and update get_all_data()
    status: completed
  - id: phase-3-extractor
    content: Add health check section extraction to data_extractor.py
    status: completed
  - id: phase-4-routes
    content: Add Flask routes, config keys, and _run_health_job() to app.py
    status: completed
  - id: phase-5-report
    content: Add health check PDF sections to report_builder.py
    status: completed
  - id: phase-6-frontend
    content: Update base.html, generate.html, and app.css for health UI
    status: completed
  - id: phase-7-scripts
    content: Update regenerate_report.py and export_swagger.py
    status: completed
  - id: phase-8-ci
    content: Add health-check-tests job to ci.yml
    status: completed
  - id: phase-9-tests
    content: Add TestHealthEndpoints, TestHealthRoutes, and integration tests
    status: completed
  - id: phase-10-docs
    content: Update rules, README, CHANGELOG, TODO-ROADMAP, and create missing docs
    status: completed
  - id: phase-11-validate
    content: Run quality gates, tests, and manual smoke test
    status: completed
  - id: phase-12-pr
    content: Commit changes and create PR to develop
    status: completed
isProject: false
---

# Health Check Feature - Fresh Branch Port Plan

## Context

The `feature/health-check` branch was started from v1.4.2 and later merged with v1.4.7, causing potential integrity issues. Analysis confirms the health check code is **highly modular** (17,475 lines added, 22 deleted) and can be cleanly ported to a fresh branch.

**Branch:** `feature/health-check-v2` from `origin/main`

---

## Phase 1: Branch Setup and Standalone Files

### 1.1 Create Fresh Branch

```bash
git fetch origin
git checkout -b feature/health-check-v2 origin/main
```

### 1.2 Copy Standalone Files (Direct Copy)

These files have no dependencies on changed code and can be copied as-is:

| Source                                                         | Destination | Lines  |
| -------------------------------------------------------------- | ----------- | ------ |
| `src/health_checker.py`                                        | Same        | 2,709  |
| `frontend/templates/health.html`                               | Same        | 375    |
| `tests/test_health_checker.py`                                 | Same        | 350    |
| `tests/data/mock_prometheus_devices.txt`                       | Same        | 9      |
| `start_server.py`                                              | Same        | 17     |
| `.cursor/rules/health-check-14.mdc`                            | Same        | 17     |
| `.cursor/rules/health-check-api-15.mdc`                        | Same        | 13     |
| `docs/development/HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md` | Same        | ~1,200 |

---

## Phase 2: API Handler Extensions

### 2.1 Add Health Check Methods to api_handler.py

Add 5 new methods at end of `VastApiHandler` class (before `get_all_data()`):

- `get_alarms()` - GET /api/alarms/
- `get_events(limit=100)` - GET /api/events/
- `get_snapshots()` - GET /api/snapshots/
- `get_quotas()` - GET /api/quotas/
- `get_prometheus_metrics(metric_path)` - GET /api/prometheusmetrics/{path}

### 2.2 Update get_all_data()

Add to the return dict:

```python
all_data["alarms"] = self.get_alarms()
all_data["events"] = self.get_events()
all_data["snapshots"] = self.get_snapshots()
all_data["quotas"] = self.get_quotas()
```

---

## Phase 3: Data Extractor Integration

### 3.1 Add Health Check Section to extract_all_data()

Insert after existing sections, before return statement:

```python
health_check_data = raw_data.get("health_check_results")
if health_check_data:
    report_data["sections"]["health_check"] = asdict(ReportSection(...))
    report_data["sections"]["post_deployment_validation"] = asdict(ReportSection(...))
```

---

## Phase 4: Flask App Routes

### 4.1 Add Config Keys in create_flask_app()

```python
app.config["HEALTH_JOB_RUNNING"] = False
app.config["HEALTH_JOB_RESULT"] = None
app.config["HEALTH_JOB_LOCK"] = threading.Lock()
app.config["HEALTH_JOB_CANCEL"] = threading.Event()
```

### 4.2 Add Routes in _register_routes()

- `GET /health` - health_page()
- `POST /health/run` - health_run()
- `GET /health/status` - health_status()
- `POST /health/cancel` - health_cancel()
- `GET /health/results` - health_results()

### 4.3 Add _run_health_job() Function

Background job runner (~75 lines)

### 4.4 Update _run_report_job()

Add optional health check integration when `include_health_check` param is set

---

## Phase 5: Report Builder Sections

### 5.1 Add Health Check PDF Sections

- `_create_health_check_section()` - Summary table + results grid
- `_create_post_deployment_validation_section()` - Validation checklist
- `_safe_table_value()` - Helper for table cell sanitization

### 5.2 Update _build_story()

Add calls to health check sections after Security & Authentication

### 5.3 Update _build_table_of_contents()

Add TOC entries and dot leader lengths for new sections

---

## Phase 6: Frontend Templates

### 6.1 Update base.html

Add nav link:

```html
<a href="{{ url_for('health_page') }}" class="nav-link ...">Health Check</a>
```

### 6.2 Update generate.html

Add health check toggle checkbox (~11 lines)

### 6.3 Update app.css

Add status badges and health-specific styles (~29 lines)

---

## Phase 7: Scripts

### 7.1 Update scripts/regenerate_report.py

- Add `--health-only` argument
- Add health-only PDF generation logic (~55 lines)

### 7.2 Update scripts/export_swagger.py

Add new endpoints to probe list:

```python
"alarms", "events", "eventdefinitions", "monitors", "snapshots", "quotas"
```

---

## Phase 8: CI/CD

### 8.1 Update .github/workflows/ci.yml

Add `health-check-tests` job (~34 lines) after quality-gate

---

## Phase 9: Tests

### 9.1 Add API Handler Tests

`tests/test_api_handler.py` - Add `TestHealthEndpoints` class (~80 lines)

### 9.2 Add App Route Tests

`tests/test_app.py` - Add `TestHealthRoutes` class (~38 lines)

### 9.3 Add Integration Tests

`tests/test_integration.py` - Add health check integration tests (~82 lines)

---

## Phase 10: Rules and Documentation

### 10.1 Update Architecture Rule

`.cursor/rules/architecture-03.mdc` - Add Health Checker module documentation

### 10.2 Update Report Branding Rule

`.cursor/rules/report-branding-10.mdc` - Add section order entries

### 10.3 Update README.md

- Add Health row to page table
- Add Health Check section in Usage

### 10.4 Update CHANGELOG.md

Add [Unreleased] section with all health check changes

### 10.5 Update docs/TODO-ROADMAP.md

- Add HC-1 through HC-7 completed items
- Add ARCH items for future work

### 10.6 Create Missing Documentation

- `docs/API-REFERENCE.md` - Add 5 new endpoint docs
- `docs/deployment/INSTALLATION-GUIDE.md` - Mention Health Check feature

---

## Phase 11: Validation

### 11.1 Run Quality Gates

```bash
flake8 src/ tests/
black --check --line-length 120 src/ tests/
mypy src/ --ignore-missing-imports
```

### 11.2 Run Tests

```bash
pytest tests/ -v --ignore=tests/test_ui.py
pytest tests/test_health_checker.py -v
```

### 11.3 Manual Smoke Test

- Start app with `python start_server.py`
- Navigate to Health page
- Run Tier-1 check against test cluster
- Verify remediation report generation

---

## Phase 12: Commit and PR

### 12.1 Commit Structure

Use conventional commits matching original WP structure:

- `feat(health): WP-1 HealthChecker core module`
- `feat(health): WP-2 API handler extensions`
- ... through WP-13

Or single commit:

- `feat(health): port health check module from feature/health-check`

### 12.2 Create PR

Target: `develop` branch
Include: Summary of ported features, test results, validation notes

---

## Files Summary

| Category    | New   | Modified |
| ----------- | ----- | -------- |
| Core Source | 1     | 4        |
| Templates   | 1     | 2        |
| Styles      | 0     | 1        |
| Scripts     | 1     | 2        |
| Tests       | 1     | 3        |
| CI          | 0     | 1        |
| Rules       | 2     | 3        |
| Docs        | 1     | 4        |
| **Total**   | **7** | **20**   |
