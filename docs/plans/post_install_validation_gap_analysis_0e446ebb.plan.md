---
name: Post Install Validation Gap Analysis
overview: Gap analysis comparing the Confluence Post Install Validations procedure against the current health check implementation, with a plan to bridge all identified gaps.
todos:
  - id: dev-mode-gating
    content: "Phase 0: Implement Developer Mode gating for Advanced Operations page"
    status: completed
  - id: advanced-ops-ui
    content: "Phase 1: Create Advanced Operations UI page with step-by-step workflow runner"
    status: completed
  - id: script-framework
    content: "Phase 2: Implement script framework with security and compatibility requirements"
    status: completed
  - id: workflow-registry
    content: "Phase 3: Implement workflow registry pattern and vnetmap workflow"
    status: completed
  - id: support-tool-steps
    content: "Phase 4: Implement vast_support_tools step-by-step workflow (5 discrete steps)"
    status: completed
  - id: vperfsanity-steps
    content: "Phase 5: Implement vperfsanity step-by-step workflow (6 discrete steps)"
    status: completed
  - id: log-bundle-steps
    content: "Phase 6: Implement VMS log bundle step-by-step workflow (5 discrete steps)"
    status: completed
  - id: status-checks
    content: "Phase 7: Implement status checks and reminders (Call Home, License, Rack/U-Height, Switches, etc.)"
    status: completed
  - id: switch-config-extract
    content: "Phase 8: Extract and save switch configuration for replacement switch provisioning"
    status: completed
  - id: network-config-extract
    content: "Phase 9: Extract configure_network.py commands for new node provisioning"
    status: completed
  - id: result-bundling
    content: "Phase 10: Implement result bundling (SB-1 aligned) for downloadable validation package"
    status: pending
  - id: testing-suite
    content: "Phase 11: Implement testing suite for all new modules (80% coverage target)"
    status: pending
  - id: ci-integration
    content: "Phase 12: Update CI pipeline for advanced-ops-tests job"
    status: pending
isProject: false
---

# Post Install Validation Gap Analysis and Implementation Plan

## Source Requirements (Confluence)

The Post Install Validations section defines 10 validation categories that must be performed after VAST cluster installation:

1. **Run vnetmap** - Network topology validation
2. **Run VAST Support Tool** - Cluster inspection
3. **Gather VMS log bundle** - Log collection
4. **Configure Call Home** - Cloud integration
5. **Check VMS Alarms/Events** - Report active alarms and events (Customer Handoff)
6. **Create VIP Pools** - Verify/recommend VIP pool creation (Customer Handoff)
7. **Test Failover Behaviors** - VMS, Leader, and VIP failover tests (Customer Handoff)
8. **License Activation** - License key validation
9. **C/D-Box Placement** - Physical location documentation
10. **Password Management** - Security hardening audit
11. **Switch Monitoring** - VMS switch configuration
12. **Run vperfsanity** - Cluster performance validation

---

## User Requirements and Considerations (Updated)

| Item                    | Requirement                          | Implementation Approach                                                                                                 |
| ----------------------- | ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| **VMS Log Bundle**      | Optional action; discover size first | Report log directory sizes, prompt user to confirm before tar/collect                                                   |
| **Call Home**           | Report status only                   | Check and report Cloud integration status, no configuration changes                                                     |
| **VIP Failover Test**   | Manual test only                     | Provide step-by-step instructions in report, do NOT automate                                                            |
| **License**             | Reminder only                        | Generate reminder to apply license key in VMS                                                                           |
| **Rack/U-Height**       | Check if configured                  | Check if Rack exists AND U-Height is set; if not, remind to configure and rerun Generate Report for Rack Layout diagram |
| **Switches in VMS**     | Check if added                       | Check if switches are added in VMS; if not, remind to add and rerun with Port Mapping for Port Map                      |
| **Password Management** | Reminder only                        | Generate security checklist reminder, do NOT attempt password validation                                                |
| **Switch Config**       | Extract for replacement              | Save switch configuration in reusable format for new switch provisioning                                                |
| **Network Config**      | Extract configure_network.py         | Capture last-run network commands for new CBox/DBox provisioning                                                        |
| **vperfsanity**         | User-initiated automated test        | User triggers test; automate full workflow (download, prepare, run, collect, cleanup)                                   |
| **VMS Alarms/Events**   | Collect and report                   | Query API for active alarms and recent events; report status                                                            |
| **VIP Pools**           | Check if configured                  | Check if VIP pools exist; if not, recommend creation with GUI/CLI steps                                                 |
| **Failover Tests**      | Manual test instructions             | Provide step-by-step procedures for VMS, Leader, and VIP failover tests                                                 |

---

## Gap Analysis Matrix (Updated)

| Validation                | Confluence Requirement                    | Current Implementation        | Gap Status          | Action Type               |
| ------------------------- | ----------------------------------------- | ----------------------------- | ------------------- | ------------------------- |
| **vnetmap.py**            | Download, configure, run, validate output | Basic placeholder check       | **MAJOR GAP**       | Automated                 |
| **vast_support_tools.py** | Download, run in container, parse results | Basic placeholder check       | **MAJOR GAP**       | Automated                 |
| **VMS Log Bundle**        | Tar and collect logs                      | Not implemented               | **NOT IMPLEMENTED** | Optional (User-triggered) |
| **Call Home**             | Verify Cloud integration                  | Not implemented               | **NOT IMPLEMENTED** | Status Report Only        |
| **VIP Failover Test**     | Test HA failover                          | Not implemented               | **NOT IMPLEMENTED** | Manual Instructions       |
| **License**               | Apply license key                         | `_check_license` exists       | **PARTIAL**         | Reminder Only             |
| **Rack/U-Height**         | Configure rack positions                  | API data available            | **PARTIAL**         | Check + Reminder          |
| **Switches in VMS**       | Add switches for monitoring               | Partial checks exist          | **PARTIAL**         | Check + Reminder          |
| **Password Management**   | Change default passwords                  | Not implemented               | **NOT IMPLEMENTED** | Reminder Only             |
| **Switch Config**         | Backup for replacement                    | Not implemented               | **NOT IMPLEMENTED** | Config Extraction         |
| **Network Config**        | Save configure_network.py                 | Not implemented               | **NOT IMPLEMENTED** | Config Extraction         |
| **vperfsanity**           | Download, run, collect results            | Not implemented               | **NOT IMPLEMENTED** | User-Initiated Automated  |
| **VMS Alarms/Events**     | Report active alarms and events           | `_check_active_alarms` exists | **PARTIAL**         | Automated Report          |
| **VIP Pools**             | Verify VIP pools configured               | `_check_vip_pools` exists     | **PARTIAL**         | Check + Recommendation    |
| **Failover Tests**        | Test VMS, Leader, VIP failover            | Not implemented               | **NOT IMPLEMENTED** | Manual Instructions       |

---

## Implementation Phases

### Phase 0: Developer Mode Gating (NEW)

Implement Developer Mode toggle to gate Advanced Operations access.

**Reference:** TODO-ROADMAP DEV-1

**Implementation:**

- Add `DEVELOPER_MODE` environment variable or `--dev-mode` CLI flag
- Store in Flask app config: `app.config["DEVELOPER_MODE"]`
- Conditionally render "Advanced Operations" nav link in `base.html`
- Return 403 if accessing `/advanced-ops` without Developer Mode enabled

**Files to modify:**

- [src/main.py](src/main.py) - Add `--dev-mode` argument parsing
- [src/app.py](src/app.py) - Add `DEVELOPER_MODE` config and route guard
- [frontend/templates/base.html](frontend/templates/base.html) - Conditional nav link

```python
# src/app.py
@app.before_request
def check_developer_mode():
    if request.path.startswith("/advanced-ops"):
        if not app.config.get("DEVELOPER_MODE"):
            return jsonify({"error": "Developer mode required"}), 403
```

---

### Phase 1: Advanced Operations UI Page

Create a dedicated UI page for running complex script-based operations with step-by-step execution.

**Files to create:**

- [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html) - Advanced Operations UI
- [src/advanced_ops.py](src/advanced_ops.py) - Backend orchestration module

**UI Design:**

```
+------------------------------------------------------------------+
|  Advanced Operations                          [Developer Mode]    |
+------------------------------------------------------------------+
|  Select Operation:  [vnetmap v]                                   |
|                                                                   |
|  +---------------------------------------------------------------+
|  | Step 1: Download Scripts to Laptop          [Run] [Done]      |
|  | Step 2: Copy to CNode                       [Run] [Pending]   |
|  | Step 3: Generate Export Commands            [Run] [Pending]   |
|  | Step 4: Execute Export Commands             [Run] [Pending]   |
|  | Step 5: Run vnetmap.py                      [Run] [Pending]   |
|  | Step 6: Validate Results                    [Run] [Pending]   |
|  | Step 7: Save Output to Laptop               [Run] [Pending]   |
|  +---------------------------------------------------------------+
|                                                                   |
|  Step Output:                                                     |
|  +---------------------------------------------------------------+
|  | (Real-time log output from current step)                      |
|  +---------------------------------------------------------------+
|                                                                   |
|  [Run All Steps]  [Reset]  [Download Results]                     |
+------------------------------------------------------------------+
```

**Features:**

- Each step can run independently
- Step status tracking (Pending, Running, Done, Error)
- Real-time log streaming via SSE
- Results persist between steps
- "Run All Steps" for automated execution
- Download results bundle when complete

**Persistent Output Results Pane (NEW):**

The output pane is a critical UI component that fills the browser window like a terminal and retains results across page navigation.

**Updated UI Design with Output Pane:**

```
+==================================================================+
|  Advanced Operations                          [Developer Mode]    |
+==================================================================+
|  Select Operation:  [vnetmap v]                                   |
|                                                                   |
|  +---------------------------------------------------------------+
|  | Step 1: Download Scripts to Laptop          [Run] [Done]      |
|  | Step 2: Copy to CNode                       [Run] [Pending]   |
|  | Step 3: Generate Export Commands            [Run] [Pending]   |
|  +---------------------------------------------------------------+
|                                                                   |
|  [Run All Steps]  [Reset]  [Download Results]                     |
+==================================================================+
|  OUTPUT RESULTS                                          [Menu v] |
+------------------------------------------------------------------+
|  10:15:32 [INFO] Step 1: Downloading vnetmap.py...               |
|  10:15:33 [INFO] Downloaded to output/scripts/                   |
|  10:15:35 [WARN] Step 2: SSH timeout, retrying...                |
|  10:15:40 [INFO] Step 2: Files copied successfully               |
|  10:15:45 [FAIL] Step 5: vnetmap returned error:                 |
|    > Switch MLX1 unreachable at <ip>                      |
|    > Check switch credentials and network connectivity           |
|  10:15:50 [INFO] Script output:                                  |
|    > Full topology: 4 CNodes, 8 DNodes detected                  |
|    > Network A: 172.16.1.0/24 - OK                               |
|  ...                                                (auto-scroll) |
+------------------------------------------------------------------+

Dropdown Menu Contents:
  +------------------+
  | Copy to Clipboard|
  | Expand / Minimize|
  | Toggle Auto-scroll|
  | Filter: All      >|  --> [All | Errors | Warnings | Info]
  | ---------------  |
  | Clear Output     |
  +------------------+
```

**Output Pane Requirements:**

| Requirement                       | Implementation                                                                   |
| --------------------------------- | -------------------------------------------------------------------------------- |
| **Terminal-like display**         | Monospace font, dark background, scrollable, fills full browser width and height |
| **Persistent across navigation**  | Results stored in `sessionStorage`, restored when returning to page              |
| **Detailed failure/warning info** | Shows full error messages, stack traces, and remediation hints                   |
| **Script output capture**         | Displays raw script output (vnetmap, support tool, vperfsanity)                  |
| **Color-coded severity**          | INFO (white), WARN (yellow), FAIL/ERROR (red), SUCCESS (green)                   |
| **Dropdown menu controls**        | Single compact [Menu] dropdown for all output actions (maximizes terminal width) |
| **Expand/Minimize toggle**        | Maximize to full browser or minimize to fixed height (via dropdown)              |
| **Filter by severity**            | Dropdown submenu to show: All, Errors only, Warnings, Info                       |
| **Auto-scroll toggle**            | Enable/disable auto-scroll via dropdown menu                                     |
| **Clear with confirmation**       | Clears output history (separated in dropdown with divider)                       |
| **Copy to clipboard**             | Copy entire output for sharing/debugging (via dropdown)                          |
| **Timestamp prefix**              | Each line prefixed with timestamp for correlation                                |

**Implementation:**

```javascript
// static/js/advanced_ops.js - Output persistence
const OUTPUT_STORAGE_KEY = 'advanced_ops_output';

class OutputPane {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.autoScroll = true;
        this.restore();  // Restore from sessionStorage on page load
    }

    append(level, message, details = null) {
        const timestamp = new Date().toISOString().slice(11, 19);
        const entry = { timestamp, level, message, details };
        this.renderEntry(entry);
        this.persist(entry);
        if (this.autoScroll) {
            this.container.scrollTop = this.container.scrollHeight;
        }
    }

    restore() {
        const stored = sessionStorage.getItem(OUTPUT_STORAGE_KEY);
        if (stored) {
            JSON.parse(stored).forEach(entry => this.renderEntry(entry));
        }
    }

    clear() {
        if (confirm('Clear all output?')) {
            this.container.innerHTML = '';
            sessionStorage.removeItem(OUTPUT_STORAGE_KEY);
        }
    }
}
```

**CSS Styling:**

```css
.output-pane {
    background: #1a1a2e;
    color: #e0e0e0;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    line-height: 1.4;
    padding: 12px;
    overflow-y: auto;
    overflow-x: auto;
    width: 100%;                      /* Full width of container */
    min-height: 200px;
    max-height: calc(100vh - 400px);  /* Fills remaining browser height */
    border: 1px solid #333;
    border-radius: 4px;
    box-sizing: border-box;
}

.output-pane.expanded {
    position: fixed;
    top: 60px;                        /* Below navbar */
    left: 0;
    right: 0;
    bottom: 0;
    width: 100vw;                     /* Full viewport width */
    max-height: calc(100vh - 60px);   /* Full height minus navbar */
    border-radius: 0;
    z-index: 1000;
}

.output-line.info { color: #e0e0e0; }
.output-line.warn { color: #ffc107; }
.output-line.fail, .output-line.error { color: #ff5252; }
.output-line.success { color: #4caf50; }
```

---

### Phase 2: Script Download and Execution Framework

Core infrastructure for script operations with security and compatibility requirements.

**Files to modify:** [src/advanced_ops.py](src/advanced_ops.py), [src/script_runner.py](src/script_runner.py)

**Security Requirements (AI Guardrails section 2.3, PRD NFR-5):**

- Credentials passed via secure memory, never stored to disk
- SSH sessions use existing `ssh_adapter.py` patterns
- No credentials logged, even at DEBUG level
- Session-based credential passing (not persisted between steps)

**API Compatibility Requirements (PRD NFR-2):**

- Pre-flight capability checks before workflow execution
- Skip steps with warnings when prerequisites unavailable
- Version detection for VAST OS feature availability
- Graceful degradation for missing cluster data

```python
class ScriptRunner:
    """Manages script download, copy, and execution."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    def check_prerequisites(self, workflow: str, cluster_data: dict) -> List[str]:
        """Check if all prerequisites are met for a workflow."""
        # Returns list of missing prerequisites

    def download_to_local(self, url: str, local_path: str) -> StepResult:
        """Download script from URL to local machine."""

    def copy_to_remote(self, local_path: str, host: str, remote_path: str,
                       username: str, password: str) -> StepResult:
        """Copy file to remote host via SCP. Credentials not stored."""

    def set_permissions(self, host: str, remote_path: str, permissions: str,
                        username: str, password: str) -> StepResult:

    def execute_remote(self, host: str, command: str,
                       username: str, password: str,
                       in_container: bool = False) -> StepResult:
        """Execute command on remote host. Password cleared after use."""

    def download_from_remote(self, host: str, remote_path: str, local_path: str,
                             username: str, password: str) -> StepResult:
```

---

### Phase 3: Workflow Registry and vnetmap Workflow

Implement modular workflow registry pattern and vnetmap workflow.

**Modularity Pattern (User Requirement):**
Enable/disable workflows without impacting core functionality.

```python
# src/workflows/__init__.py
REGISTERED_WORKFLOWS = {
    "vnetmap": {
        "enabled": True,
        "display_name": "vnetmap Validation",
        "module": "vnetmap_workflow",
        "steps": 7,
        "min_vast_os": "5.0",  # Compatibility
    },
    "support_tool": {
        "enabled": True,
        "display_name": "VAST Support Tools",
        "module": "support_tool_workflow",
        "steps": 5,
        "min_vast_os": "5.0",
    },
    # ... other workflows
}

def get_enabled_workflows() -> List[str]:
    """Return list of enabled workflow names."""
    return [k for k, v in REGISTERED_WORKFLOWS.items() if v["enabled"]]

def get_workflow_info(workflow_name: str) -> dict:
    """Get workflow metadata including step count and compatibility."""
    return REGISTERED_WORKFLOWS.get(workflow_name, {})
```

**vnetmap Workflow - 7 Discrete Steps:**

| Step | Name                     | Action                                               | Input                                  | Output            |
| ---- | ------------------------ | ---------------------------------------------------- | -------------------------------------- | ----------------- |
| 1    | Download Scripts         | Download vnetmap.py and mlnx_switch_api.py to laptop | URLs                                   | Local files       |
| 2    | Copy to CNode            | SCP files to /vast/data on CNode, chmod +x           | Local files, CNode IP                  | Remote files      |
| 3    | Generate Export Commands | Build export commands from cluster API data          | CNode IPs, DNode IPs, Switch IPs/creds | Command strings   |
| 4    | Execute Exports          | Run export commands on CNode                         | Command strings                        | Environment set   |
| 5    | Run vnetmap.py           | Execute vnetmap with parameters                      | Switch IPs, credentials                | Raw output        |
| 6    | Validate Results         | Parse output, check topology                         | Raw output                             | Validation report |
| 7    | Save Output              | Download output file to laptop                       | Remote path                            | Local file        |

**Step Implementation:** See [src/workflows/vnetmap_workflow.py](src/workflows/vnetmap_workflow.py)

---

### Phase 4: vast_support_tools Step-by-Step Workflow

**5 Discrete Steps:**

| Step | Name               | Action                             | Input         | Output            |
| ---- | ------------------ | ---------------------------------- | ------------- | ----------------- |
| 1    | Download Script    | wget to CNode /vast/data, chmod +x | URL, CNode IP | Remote script     |
| 2    | Run in Container   | Execute via vms.sh inspect         | Script path   | Raw output        |
| 3    | Validate Results   | Parse output for issues            | Raw output    | Validation report |
| 4    | Package Output     | tar cvfz support-checks            | Output dir    | tar.gz file       |
| 5    | Download to Laptop | SCP tar file to local              | Remote path   | Local file        |

**Step Implementation:** See [src/workflows/support_tool_workflow.py](src/workflows/support_tool_workflow.py)

---

### Phase 5: vperfsanity Step-by-Step Workflow

**6 Discrete Steps:**

| Step | Name                   | Action                        | Input         | Output                 |
| ---- | ---------------------- | ----------------------------- | ------------- | ---------------------- |
| 1    | Download Package       | wget tar.gz to CNode, extract | URL, CNode IP | Extracted dir          |
| 2    | Prepare Infrastructure | Run vperfsanity_prepare.sh    | VIP pool name | Infrastructure ready   |
| 3    | Run Write Test         | Run vperfsanity_run.sh -w     | VIP pool name | Write results          |
| 4    | Run Read Test          | Run vperfsanity_run.sh -r     | VIP pool name | Read results           |
| 5    | Collect Results        | Run vperfsanity_results.sh    | -             | Results summary        |
| 6    | Cleanup                | Run cleanup scripts           | -             | Infrastructure removed |

**Step Implementation:** See [src/workflows/vperfsanity_workflow.py](src/workflows/vperfsanity_workflow.py)

---

### Phase 6: VMS Log Bundle Step-by-Step Workflow

**5 Discrete Steps:**

| Step | Name               | Action                      | Input       | Output            |
| ---- | ------------------ | --------------------------- | ----------- | ----------------- |
| 1    | Discover Sizes     | du -sh on log directories   | CNode IP    | Size report       |
| 2    | Confirm Collection | User approves based on size | Sizes       | User confirmation |
| 3    | Create Archive     | tar cvfz logs               | Log paths   | tar.gz file       |
| 4    | Download to Laptop | SCP tar file                | Remote path | Local file        |
| 5    | Verify Contents    | List archive contents       | Local file  | Content list      |

**Step Implementation:** See [src/workflows/log_bundle_workflow.py](src/workflows/log_bundle_workflow.py)

---

### Phase 7: Status Checks and Reminders

Implement automated checks in [src/health_checker.py](src/health_checker.py):

| Check             | Method                              | Action                                  |
| ----------------- | ----------------------------------- | --------------------------------------- |
| Call Home Status  | _check_call_home_status()           | Report configuration status             |
| License Reminder  | _check_license_reminder()           | Remind to verify license applied        |
| Rack/U-Height     | _check_rack_and_uheight()           | Check placement, recommend if missing   |
| Switches in VMS   | _check_switches_in_vms()            | Check if added, recommend if missing    |
| Password Reminder | _check_password_reminder()          | Remind to change default passwords      |
| VMS Alarms/Events | _check_vms_alarms_events()          | Report active alarms and recent events  |
| VIP Pools         | _check_vip_pools()                  | Verify configured, recommend if missing |
| Failover Tests    | _check_failover_test_instructions() | Provide manual test instructions        |

---

### Phase 8: Switch Configuration Extraction

Extract switch configuration for replacement provisioning.

**Implementation:** Add step to Advanced Operations

| Step | Name              | Action                                                                            |
| ---- | ----------------- | --------------------------------------------------------------------------------- |
| 1    | Connect to Switch | SSH to switch management IP                                                       |
| 2    | Extract Config    | Run `net show configuration commands` (Cumulus) or `show running-config` (NVIDIA) |
| 3    | Save Config       | Store to output/switch_configs/_config.txt                                        |

---

### Phase 9: Network Configuration Extraction

Extract configure_network.py commands for new node provisioning.

**Implementation:** Add step to Advanced Operations

| Step | Name             | Action                                      |
| ---- | ---------------- | ------------------------------------------- |
| 1    | Connect to CNode | SSH to CNode                                |
| 2    | Search History   | grep configure_network ~/.bash_history      |
| 3    | Extract INI      | cat /etc/vast/network.ini                   |
| 4    | Save Output      | Store to output/network_config/_network.txt |

---

### Phase 10: Result Bundling and Storage

Bundle all validation outputs for download.

**Support Bundle Alignment (TODO-ROADMAP SB-1):**
Structure output for future support bundle import compatibility.

**Output Structure:**

```
output/post_install_validation_<timestamp>/
  ├── manifest.json                    # Bundle metadata (NEW)
  ├── cluster_info.json                # Cluster identification (NEW)
  ├── vnetmap/
  │   └── vnetmap_output.txt
  ├── support_tool/
  │   └── <hostname>-support_tool_logs.tgz
  ├── vperfsanity/
  │   └── results_summary.txt
  ├── vms_logs/
  │   └── <hostname>-vms_logs.tgz
  ├── switch_configs/
  │   └── <switch_ip>_config.txt
  ├── network_config/
  │   └── <hostname>_network.txt
  └── validation_report.json
```

**Manifest Schema:**

```json
{
  "version": "1.0",
  "created": "2026-03-21T12:00:00Z",
  "cluster_name": "<lab-cluster>",
  "cluster_psnt": "XXXXX",
  "workflows_run": ["vnetmap", "support_tool"],
  "files": [
    {"path": "vnetmap/vnetmap_output.txt", "size": 12345, "checksum": "..."}
  ]
}
```

---

### Phase 11: Testing Suite (NEW)

**Reference:** AI Guardrails section 8.1 (80% coverage target), TODO-ROADMAP TSE-9

Implement comprehensive tests for all new modules.

**Files to create:**

- [tests/test_advanced_ops.py](tests/test_advanced_ops.py)
- [tests/test_script_runner.py](tests/test_script_runner.py)
- [tests/test_workflows.py](tests/test_workflows.py)

**Test Coverage Requirements:**

| Module                     | Test Focus                              | Mocking           |
| -------------------------- | --------------------------------------- | ----------------- |
| `advanced_ops.py`          | Routes, step execution, SSE             | Flask test client |
| `script_runner.py`         | Download, copy, execute, error handling | Mock SSH/SCP      |
| `vnetmap_workflow.py`      | Each step function                      | Mock ScriptRunner |
| `support_tool_workflow.py` | Each step function                      | Mock ScriptRunner |
| `vperfsanity_workflow.py`  | Each step function                      | Mock ScriptRunner |
| `log_bundle_workflow.py`   | Each step function, size discovery      | Mock SSH          |

**Integration Tests:**

- End-to-end workflow execution with mocked external calls
- SSE streaming verification
- Result bundling structure validation

---

### Phase 12: CI Integration (NEW)

**Reference:** CHANGELOG CI Health Check Tests pattern

Update CI pipeline for new workflow modules.

**Files to modify:** [.github/workflows/ci.yml](.github/workflows/ci.yml)

**New CI Steps:**

```yaml
advanced-ops-tests:
  name: Advanced Operations Tests
  runs-on: ubuntu-latest
  steps:
    - name: Run workflow tests
      run: |
        python -m pytest tests/test_advanced_ops.py tests/test_script_runner.py tests/test_workflows.py -v

    - name: Type check workflows
      run: |
        mypy src/advanced_ops.py src/script_runner.py src/workflows/ --ignore-missing-imports
```

---

## Priority Matrix (Updated)

| Phase    | Name                        | Priority | Effort | Impact                            | Action Type       |
| -------- | --------------------------- | -------- | ------ | --------------------------------- | ----------------- |
| Phase 0  | Developer Mode Gating       | HIGH     | Low    | Security/UX for advanced features | Infrastructure    |
| Phase 1  | Advanced Operations UI      | HIGH     | Medium | Enables step-by-step testing      | UI Infrastructure |
| Phase 2  | Script Framework            | HIGH     | Medium | Core script execution + security  | Infrastructure    |
| Phase 3  | Workflow Registry + vnetmap | HIGH     | Medium | Modularity + cabling validation   | 7-Step Workflow   |
| Phase 4  | Support Tool Workflow       | HIGH     | Medium | Comprehensive inspection          | 5-Step Workflow   |
| Phase 5  | vperfsanity Workflow        | MEDIUM   | Medium | Performance baseline              | 6-Step Workflow   |
| Phase 6  | Log Bundle Workflow         | MEDIUM   | Low    | Optional support data             | 5-Step Workflow   |
| Phase 7  | Status Checks               | MEDIUM   | Low    | Reminders and recommendations     | Automated Checks  |
| Phase 8  | Switch Config               | MEDIUM   | Medium | Disaster recovery prep            | 3-Step Workflow   |
| Phase 9  | Network Config              | MEDIUM   | Medium | New node provisioning             | 4-Step Workflow   |
| Phase 10 | Result Bundling             | MEDIUM   | Medium | SB-1 aligned packaging            | Automated         |
| Phase 11 | Testing Suite               | HIGH     | Medium | Quality gate (80% coverage)       | Tests             |
| Phase 12 | CI Integration              | MEDIUM   | Low    | Automated validation              | CI/CD             |

---

## Files to Create/Modify

### Core Infrastructure

| File                                                                         | Action | Description                                                                           |
| ---------------------------------------------------------------------------- | ------ | ------------------------------------------------------------------------------------- |
| [src/main.py](src/main.py)                                                   | Modify | Add `--dev-mode` argument parsing                                                     |
| [src/app.py](src/app.py)                                                     | Modify | Add Developer Mode config, route guard, /advanced-ops routes                          |
| [src/advanced_ops.py](src/advanced_ops.py)                                   | Create | Backend orchestration for Advanced Operations page, step runner, SSE streaming        |
| [src/script_runner.py](src/script_runner.py)                                 | Create | Core infrastructure for script download, copy, execution (secure credential handling) |
| [frontend/templates/base.html](frontend/templates/base.html)                 | Modify | Conditional nav link for Advanced Operations (Developer Mode)                         |
| [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html) | Create | Advanced Operations UI with step-by-step workflow runner                              |
| [static/js/advanced_ops.js](static/js/advanced_ops.js)                       | Create | Frontend JavaScript for step execution, status tracking, SSE handling                 |

### Workflow Modules

| File                                                                                 | Action | Description                                                  |
| ------------------------------------------------------------------------------------ | ------ | ------------------------------------------------------------ |
| [src/workflows/**init**.py](src/workflows/__init__.py)                               | Create | Workflow registry with enable/disable, version compatibility |
| [src/workflows/vnetmap_workflow.py](src/workflows/vnetmap_workflow.py)               | Create | 7-step vnetmap validation workflow                           |
| [src/workflows/support_tool_workflow.py](src/workflows/support_tool_workflow.py)     | Create | 5-step vast_support_tools workflow                           |
| [src/workflows/vperfsanity_workflow.py](src/workflows/vperfsanity_workflow.py)       | Create | 6-step vperfsanity performance workflow                      |
| [src/workflows/log_bundle_workflow.py](src/workflows/log_bundle_workflow.py)         | Create | 5-step VMS log bundle collection workflow                    |
| [src/workflows/switch_config_workflow.py](src/workflows/switch_config_workflow.py)   | Create | 3-step switch configuration extraction workflow              |
| [src/workflows/network_config_workflow.py](src/workflows/network_config_workflow.py) | Create | 4-step network configuration extraction workflow             |

### Status Checks and Health

| File                                           | Action | Description                                                                |
| ---------------------------------------------- | ------ | -------------------------------------------------------------------------- |
| [src/health_checker.py](src/health_checker.py) | Modify | Add status checks and reminders (License, Rack, Switches, Passwords, etc.) |

### Testing (NEW - Phase 11)

| File                                                       | Action | Description                                      |
| ---------------------------------------------------------- | ------ | ------------------------------------------------ |
| [tests/test_advanced_ops.py](tests/test_advanced_ops.py)   | Create | Route tests, step execution, SSE streaming tests |
| [tests/test_script_runner.py](tests/test_script_runner.py) | Create | Mock SSH/SCP operations, error handling tests    |
| [tests/test_workflows.py](tests/test_workflows.py)         | Create | Each workflow step function with mocked calls    |

### CI/CD (NEW - Phase 12)

| File                                                 | Action | Description                                        |
| ---------------------------------------------------- | ------ | -------------------------------------------------- |
| [.github/workflows/ci.yml](.github/workflows/ci.yml) | Modify | Add advanced-ops-tests job, workflow type checking |

### Documentation

| File                                                               | Action | Description                                              |
| ------------------------------------------------------------------ | ------ | -------------------------------------------------------- |
| [docs/ADVANCED-OPERATIONS.md](docs/ADVANCED-OPERATIONS.md)         | Create | Documentation for Advanced Operations page and workflows |
| [docs/POST-INSTALL-VALIDATION.md](docs/POST-INSTALL-VALIDATION.md) | Create | Documentation for post-install validation process        |

---

## Reminder Messages Summary

| Check               | Trigger Condition            | Reminder Message                                                                                    |
| ------------------- | ---------------------------- | --------------------------------------------------------------------------------------------------- |
| **License**         | Always                       | "Apply the cluster license key in VMS"                                                              |
| **Rack/U-Height**   | No racks OR missing U-Height | "Create Rack(s) and assign C/DBox U-Height, then run Generate Report again for Rack Layout diagram" |
| **Switches in VMS** | No switches found            | "Add switches in VMS, then rerun with Port Mapping enabled to generate Port Map"                    |
| **Passwords**       | Always                       | "Verify all default passwords have been changed"                                                    |
| **VIP Failover**    | Always                       | "Perform manual VIP failover test" (with step-by-step procedure)                                    |

---

## User-Initiated Actions Summary (Advanced Operations Page)

| Operation              | Steps | Description                                                                     |
| ---------------------- | ----- | ------------------------------------------------------------------------------- |
| **vnetmap Validation** | 7     | Download scripts, copy to CNode, generate exports, execute, run, validate, save |
| **vast_support_tools** | 5     | Download to CNode, run in container, validate, package, download                |
| **vperfsanity**        | 6     | Download/extract, prepare, write test, read test, collect results, cleanup      |
| **VMS Log Bundle**     | 5     | Discover sizes, confirm, archive, download, verify                              |
| **Switch Config**      | 3     | Connect, extract config, save                                                   |
| **Network Config**     | 4     | Connect to CNode, search history, extract INI, save                             |

Each operation can be run step-by-step for testing, or "Run All Steps" for automated execution.

---

## Validation Report Sections

The final validation report will include:

1. **Executive Summary** - Overall pass/fail/warning counts
2. **Automated Validations** - vnetmap, support tool results
3. **Status Checks** - Call Home status
4. **Configuration Backups** - Switch configs, network commands
5. **Performance Baseline** - vperfsanity results (if run)
6. **Reminders** - License, Rack/U-Height, Switches, Password checklist, VIP failover procedure
7. **Optional Attachments** - VMS logs (if collected)

---

## RFE and TODO-ROADMAP Alignment

This plan directly addresses or contributes to the following tracked items:

| ID         | Description                              | Alignment                                                              |
| ---------- | ---------------------------------------- | ---------------------------------------------------------------------- |
| **RFE-5**  | Integrate/Automate Post Deployment Tests | **Primary objective** of this plan                                     |
| **DEV-1**  | Developer button (hidden/secure)         | Advanced Operations gated under Developer Mode                         |
| **SB-1**   | Support bundle workflow                  | Result bundling structure compatible with future support bundle import |
| **RFE-11** | Create .json export database             | Validation bundle includes structured JSON manifest                    |
| **TSE-9**  | Coverage toward 80%                      | Phase 11 adds tests for new modules                                    |

---

## Security Requirements Summary

**Reference:** AI Guardrails section 2.3, PRD NFR-5

| Requirement                  | Implementation                                                |
| ---------------------------- | ------------------------------------------------------------- |
| Credentials never stored     | SSH credentials passed in memory, not persisted between steps |
| No credentials in logs       | `script_runner.py` masks credentials in all log output        |
| Secure environment variables | Credentials can be passed via env vars if needed              |
| Session-based auth           | Uses existing `ssh_adapter.py` patterns                       |

---

## Logging Standards Summary

**Reference:** AI Guardrails section 7

All workflow modules must follow the established logging format:

```
YYYY-MM-DD HH:MM:SS,mmm - [LEVEL] - [MODULE] - MESSAGE
```

| Level   | Usage                                                     |
| ------- | --------------------------------------------------------- |
| INFO    | Step start, step complete, workflow milestones            |
| WARNING | Non-critical issues, skipped steps, missing optional data |
| ERROR   | Step failures, SSH errors, validation failures            |
| DEBUG   | Command details (no credentials), API responses           |

---

## API Compatibility Matrix

| Feature              | Min VAST OS | Fallback               |
| -------------------- | ----------- | ---------------------- |
| vnetmap built-in     | 12.3.2      | Download from GitHub   |
| eventdefinitions API | 5.0         | Skip alarm enrichment  |
| eboxes API           | 7.0         | EBox features disabled |
| switches API         | 5.0         | Skip switch discovery  |
| racks API            | 5.0         | Use default rack       |

Workflows must check version compatibility and skip/warn when features unavailable.
