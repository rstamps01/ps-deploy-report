---
name: Advanced Ops Final Phases
overview: "Complete the remaining phases for Advanced Operations: result bundling, testing, CI integration, and documentation updates aligned with WP-13 from the implementation guide."
todos:
  - id: result-bundling
    content: "Phase 10: Implement result bundling (SB-1 aligned) for downloadable validation package"
    status: completed
  - id: testing-suite
    content: "Phase 11: Implement testing suite for all new modules (80% coverage target)"
    status: completed
  - id: ci-integration
    content: "Phase 12: Update CI pipeline for advanced-ops-tests job"
    status: completed
  - id: wp13-verification
    content: "Phase 13: Verify WP-13 documentation (CHANGELOG, README, TODO-ROADMAP for Health Check features)"
    status: completed
  - id: advanced-ops-docs
    content: "Phase 14: Create Advanced Operations documentation (ADVANCED-OPERATIONS.md, POST-INSTALL-VALIDATION.md)"
    status: completed
isProject: false
---

# Advanced Operations - Remaining Phases Plan

## Current State

All 6 workflows are implemented and registered:

- `vnetmap` (7 steps)
- `support_tool` (5 steps)
- `vperfsanity` (6 steps)
- `log_bundle` (5 steps)
- `switch_config` (3 steps)
- `network_config` (4 steps)

---

## Phase 10: Result Bundling

Create a downloadable validation package aligned with SB-1 documentation requirements.

### Implementation

**New File:** `src/result_bundler.py`

- Collect outputs from all completed workflows
- Package into timestamped ZIP archive containing:
  - Health check results JSON
  - Network topology validation
  - Switch configurations
  - Network configurations
  - vperfsanity performance results
  - Log bundle (if collected)
  - Summary report (Markdown)

**UI Integration:**

- Add "Download Results" button in Advanced Ops page
- Button enabled when any workflow completes
- Download triggers ZIP creation and browser download

**Key Methods:**

```python
class ResultBundler:
    def collect_results() -> Dict[str, Path]
    def create_bundle(results: Dict) -> Path
    def generate_summary() -> str
```

---

## Phase 11: Testing Suite

Target 80% code coverage for new modules.

### Test Files to Create

| File | Coverage Target |
|------|-----------------|
| `tests/test_advanced_ops.py` | `AdvancedOpsManager` class |
| `tests/test_script_runner.py` | `ScriptRunner` class |
| `tests/test_workflows.py` | All 6 workflow classes |
| `tests/test_result_bundler.py` | `ResultBundler` class |

### Test Strategy

- Unit tests with mocked SSH/HTTP calls
- Integration tests for workflow step sequencing
- Fixtures for credentials and mock API responses
- Parameterized tests for each workflow type

**Example Structure:**

```python
# tests/test_workflows.py
class TestVnetmapWorkflow:
    def test_get_steps_returns_7_steps(self)
    def test_validate_prerequisites_missing_creds(self)
    def test_run_step_1_connect(self, mock_ssh)

class TestSupportToolWorkflow:
    def test_get_steps_returns_5_steps(self)
    # ...
```

---

## Phase 12: CI Integration

Update CI pipeline for advanced-ops-tests job.

### Changes to `.github/workflows/ci.yml`

```yaml
advanced-ops-tests:
  runs-on: ubuntu-latest
  needs: test
  steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -e ".[test]"
    - name: Run Advanced Ops Tests
      run: |
        pytest tests/test_advanced_ops.py \
               tests/test_script_runner.py \
               tests/test_workflows.py \
               tests/test_result_bundler.py \
               --cov=src/advanced_ops \
               --cov=src/script_runner \
               --cov=src/workflows \
               --cov-report=xml
    - name: Upload coverage
      uses: codecov/codecov-action@v4
```

### Coverage Requirements

- Add coverage threshold to `pyproject.toml`:

  ```toml
  [tool.coverage.report]
  fail_under = 80
  ```

---

## Phase 13: WP-13 Documentation Verification

Verify Health Check module documentation is complete per guide WP-13.

### Files to Verify/Update

| File | Required Content |
|------|-----------------|
| `CHANGELOG.md` | Health Check module entry with features list |
| `README.md` | Health Check feature in Features section |
| `docs/TODO-ROADMAP.md` | RFE-4, RFE-5 status updated |
| `docs/confluence/` | Health Check sections synced |

### Verification Checklist

- CHANGELOG follows Keep a Changelog format
- README accurately describes Health Check feature
- TODO-ROADMAP reflects current completion status
- No duplicate or outdated entries

---

## Phase 14: Advanced Operations Documentation

Create comprehensive documentation for Advanced Operations workflows.

### New Files to Create

**`docs/ADVANCED-OPERATIONS.md`**

- Developer Mode activation (`--dev-mode` flag)
- UI page overview and navigation
- Workflow descriptions (all 6 workflows)
- Step-by-step execution guide
- Output pane usage and persistence
- Troubleshooting common issues

**`docs/POST-INSTALL-VALIDATION.md`**

- Mapping to Confluence post-install procedures
- Automated vs manual validation steps
- Script download sources and requirements
- Expected results and remediation guidance
- Customer handoff checklist

### Content Structure

```markdown
# Advanced Operations Guide

## Prerequisites
- Developer Mode enabled
- SSH credentials for CNodes
- Switch credentials (for switch workflows)

## Available Workflows
1. vnetmap Validation (7 steps)
2. VAST Support Tools (5 steps)
3. vperfsanity Performance Test (6 steps)
4. VMS Log Bundle (5 steps)
5. Switch Configuration Extraction (3 steps)
6. Network Configuration Extraction (4 steps)

## Usage
...
```

---

## Execution Order

1. **Phase 10**: Result bundling (enables complete validation packages)
2. **Phase 11**: Testing suite (ensures code quality before merge)
3. **Phase 12**: CI integration (automates test execution)
4. **Phase 13**: WP-13 verification (ensures Health Check docs complete)
5. **Phase 14**: Advanced Ops documentation (comprehensive user guide)
