---
name: Health Check Full Build
overview: "Implement the Health Check module end-to-end: first establish pre-development guardrails (rules, CI/CD, MCP), then execute all 13 Work Packages sequentially on a feature branch with optimal model tier selection, culminating in a single user review before merge."
todos:
  - id: step-0a
    content: Create feature/health-check-setup branch from develop
    status: completed
  - id: step-0b
    content: Create .cursor/rules/health-check-14.mdc and health-check-api-15.mdc
    status: completed
  - id: step-0c
    content: Update architecture-03.mdc, testing-standards-06.mdc, report-branding-10.mdc with health check additions
    status: completed
  - id: step-0d
    content: Add health-check-tests CI job and temporarily lower coverage threshold to 44
    status: completed
  - id: step-0e
    content: Configure Confluence MCP sync (fetch page 6664028496, document workflow)
    status: completed
  - id: step-0f
    content: PR feature/health-check-setup to develop for user review and approval
    status: completed
  - id: wp-1
    content: "WP-1 [Standard]: Build HealthChecker core module with 23 API checks (src/health_checker.py)"
    status: completed
  - id: wp-2
    content: "WP-2 [Standard]: Add 5 new API handler methods -- alarms, events, snapshots, quotas, prometheus (src/api_handler.py)"
    status: completed
  - id: wp-3
    content: "WP-3 [Fast]: Add health check section extraction to data_extractor.py"
    status: completed
  - id: wp-4
    content: "WP-4 [Standard]: Add /health Flask routes with background job management (src/app.py)"
    status: completed
  - id: wp-5
    content: "WP-5 [Fast]: Create health.html template and add nav link to base.html"
    status: completed
  - id: wp-6
    content: "WP-6 [Standard]: Add _create_health_check_section and _create_post_deployment_validation_section to report_builder.py"
    status: completed
  - id: wp-7
    content: "WP-7 [Fast]: Add --health-only flag to scripts/regenerate_report.py"
    status: completed
  - id: wp-8
    content: "WP-8 [Fast]: Add Include Health Check checkbox to generate.html and wire into _run_report_job"
    status: completed
  - id: wp-9
    content: "WP-9 [Standard]: Implement SSH health checks (node + switch) in health_checker.py"
    status: completed
  - id: wp-10
    content: "WP-10 [Standard]: Implement Prometheus metrics parser and device health check"
    status: completed
  - id: wp-11
    content: "WP-11 [Fast]: Create tests/test_health_checker.py with 27+ test methods and add API endpoint tests"
    status: completed
  - id: wp-12
    content: "WP-12 [Fast]: Add integration tests for health routes and pipeline flow; restore coverage to 46+"
    status: completed
  - id: wp-13
    content: "WP-13 [Fast]: Update CHANGELOG.md, README.md, docs/TODO-ROADMAP.md for health check feature"
    status: completed
  - id: review
    content: "Post-execution: Full code review, functional verification, Confluence sync, user approval"
    status: completed
isProject: false
---

# Health Check Module -- Full Sequential Build Plan

## Pre-Development Setup (User-Initiated, Reviewed Before WP Execution Begins)

These steps create the foundation that enables safe Option C execution. All changes go on `feature/health-check-setup` branched from `develop`.

### Step 0A: Create Feature Branch

- Branch `feature/health-check-setup` from `develop`
- All pre-dev changes committed here, PR to `develop` for user review

### Step 0B: Create New Cursor Rules

Two new rule files, as specified in [HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md](docs/development/HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md) Section 14:

- `**.cursor/rules/health-check-14.mdc**` -- HealthChecker module guardrails (globs: `src/health_checker.py`)
  - Return HealthCheckResult from every check, never raise
  - try/except + timing on every check
  - cancel_event polling, config-driven thresholds
  - Module boundary: no imports from report_builder/data_extractor
  - SSH via ssh_adapter, read-only API, Prometheus text/plain handling
- `**.cursor/rules/health-check-api-15.mdc**` -- API handler extensions (globs: `src/api_handler.py`)
  - New endpoints: alarms/, events/, snapshots/, quotas/, prometheusmetrics/
  - Return empty on failure, text/plain for Prometheus
  - Update get_all_data() and export_swagger.py probe list

### Step 0C: Update Existing Rules

- **[architecture-03.mdc](.cursor/rules/architecture-03.mdc)**: Add HealthChecker to module diagram and module boundaries. Add `/health` routes to Web UI Layer. Add `health_checker.py` boundary: must not import report_builder or data_extractor.
- **[testing-standards-06.mdc](.cursor/rules/testing-standards-06.mdc)**: Add health checker test patterns (mock api_handler, mock ssh_adapter, test pass/fail/error/404/cancel).
- **[report-branding-10.mdc](.cursor/rules/report-branding-10.mdc)**: Add section 13 (Cluster Health Check Results) and 14 (Post Deployment Validation) to the section order list.

### Step 0D: CI/CD Adjustments

Modify [.github/workflows/ci.yml](.github/workflows/ci.yml):

- Add a **health-check-tests** job (parallel to unit-tests, after quality-gate):

```yaml
  health-check-tests:
    needs: quality-gate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements-dev.txt
      - run: pytest tests/test_health_checker.py -v --no-cov


```

  (This job will be a no-op until WP-11 creates the test file, but having it ready avoids CI changes mid-development.)

- Temporarily lower coverage threshold in [pyproject.toml](pyproject.toml) from 46 to 44 with a comment explaining it will be restored after WP-11/12:

```toml
  addopts = "--cov=src --cov-report=term-missing --cov-report=xml --cov-fail-under=44"


```

### Step 0E: Configure Confluence MCP Sync

- Use `getConfluencePage` to fetch page 6664028496 (VAST As-Built Report Generator) to confirm cloudId and current content
- Document the Confluence sync workflow in a new section of the implementation guide:
  - After WP-13, call `updateConfluencePage` with cloudId, pageId 6664028496, and updated markdown body including Health Check feature docs
  - For Jira integration: after each WP, use `searchJiraIssuesUsingJql` to check for related tickets before creating new ones via `createJiraIssue`

### Step 0F: User Review Checkpoint

- PR `feature/health-check-setup` to `develop`
- User reviews rules, CI/CD changes, MCP config
- Once approved and merged, WP execution begins

---

## WP Execution Phase (Sequential, Single Review at End)

After Step 0F approval, create `feature/health-check` from `develop`. All 13 WPs execute sequentially on this branch. The dependency graph dictates execution order:

### Execution Order with Model Tiers

| Order | WP    | Description                            | Model    | Rationale                                |
| ----- | ----- | -------------------------------------- | -------- | ---------------------------------------- |
| 1     | WP-1  | HealthChecker core (23 API checks)     | Standard | Complex business logic, 20K tokens       |
| 2     | WP-2  | API handler extensions (5 new methods) | Standard | API integration pattern matching         |
| 3     | WP-3  | Data extractor integration             | Fast     | Simple conditional insertion, 8K tokens  |
| 4     | WP-4  | Flask routes + job management          | Standard | Concurrency, threading, state management |
| 5     | WP-5  | Health check UI template               | Fast     | HTML/CSS/JS following existing patterns  |
| 6     | WP-6  | Report builder sections                | Standard | ReportLab table rendering, TOC wiring    |
| 7     | WP-7  | Standalone report generation           | Fast     | argparse flag + thin wrapper             |
| 8     | WP-8  | Generate page integration              | Fast     | Checkbox + simple plumbing               |
| 9     | WP-9  | SSH health checks (Tier 2-3)           | Standard | SSH orchestration, command parsing       |
| 10    | WP-10 | Prometheus metrics parser              | Standard | Text parsing, device health logic        |
| 11    | WP-11 | Unit tests (27+ test methods)          | Fast     | Test scaffolding with mocks              |
| 12    | WP-12 | Integration tests                      | Fast     | Route tests, pipeline verification       |
| 13    | WP-13 | Documentation + release prep           | Fast     | CHANGELOG, README, ROADMAP updates       |

**Cost optimization**: 7 WPs on Fast model, 6 on Standard. No T3 (Opus) needed for individual WPs -- T3 is reserved for the final review.

### Automated Validation Between WPs

After each WP completes:

1. Run `black --check --line-length 120 src/ tests/` and `flake8 src/ tests/`
2. Run `mypy src/ --ignore-missing-imports`
3. Run `pytest tests/ -v --no-cov` (catches regressions)
4. Only proceed to next WP if all pass

### Coverage Restoration

After WP-12 (integration tests), restore [pyproject.toml](pyproject.toml) `--cov-fail-under` to 46 (or higher if coverage improved).

---

## Post-Execution Review (Single Checkpoint)

After WP-13 completes:

1. **Code review**: Full diff of `feature/health-check` vs `develop` -- all 13 WPs in one PR
2. **Functional verification**: User can run the health check UI locally to validate
3. **Confluence sync**: Execute `updateConfluencePage` for page 6664028496
4. **User approves or requests revisions** -- revisions addressed on the same branch
5. **Merge**: PR `feature/health-check` into `develop`

---

## Key Files Inventory

### New Files (6)

- `src/health_checker.py` (WP-1, WP-9, WP-10)
- `frontend/templates/health.html` (WP-5)
- `tests/test_health_checker.py` (WP-11)
- `tests/data/mock_prometheus_devices.txt` (WP-11)
- `.cursor/rules/health-check-14.mdc` (Step 0B)
- `.cursor/rules/health-check-api-15.mdc` (Step 0B)

### Modified Files (14)

- `src/api_handler.py`, `src/data_extractor.py`, `src/app.py`, `src/report_builder.py`
- `frontend/templates/base.html`, `frontend/templates/generate.html`
- `scripts/regenerate_report.py`, `scripts/export_swagger.py`
- `tests/test_api_handler.py`, `tests/test_app.py`, `tests/test_integration.py`
- `CHANGELOG.md`, `README.md`, `docs/TODO-ROADMAP.md`
- `.cursor/rules/architecture-03.mdc`, `testing-standards-06.mdc`, `report-branding-10.mdc`
- `.github/workflows/ci.yml`, `pyproject.toml`
