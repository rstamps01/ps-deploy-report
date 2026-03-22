# Advanced Operations Guide

The Advanced Operations module provides step-by-step execution of complex validation workflows that require script downloads, remote SSH execution, and multi-stage processing. This is a developer/testing feature designed for post-install validation and troubleshooting.

## Prerequisites

### Developer Mode

Advanced Operations is only accessible when the application is started with the `--dev-mode` flag:

```bash
# Desktop application
open "VAST Reporter.app" --args --dev-mode

# From source
python3 -m src.main --dev-mode
```

When enabled, an **Advanced Ops** link (with gear icon) appears in the navigation bar.

### Credentials

| Credential | Required For | Default (when toggle ON) | Description |
|------------|--------------|--------------------------|-------------|
| **Cluster IP** | All workflows | — | VMS IP address or hostname |
| **API Username/Password** | All workflows | `admin` / `123456` | VAST API credentials with admin access |
| **Node SSH User/Password** | Most workflows | `vastdata` / `vastdata` | SSH credentials for CNodes |
| **Switch SSH User/Password** | Switch workflows | `cumulus` / `Vastdata1!` | SSH credentials for switches |
| **VIP Pool Name** | vperfsanity | `main` | VIP pool name for performance testing |

**Default Credentials Toggle:** A toggle switch in Connection Settings auto-populates standard credentials when enabled (default: ON). Disable to enter custom credentials for non-standard configurations.

---

## Available Workflows

### vnetmap Validation (7 steps)

Validates network topology using VAST's vnetmap.py script.

| Step | Name | Description |
|------|------|-------------|
| 1 | Download Scripts | Download vnetmap.py and mlnx_switch_api.py to laptop |
| 2 | Copy to CNode | SCP scripts to CNode and set permissions |
| 3 | Generate Environment | Capture switch IPs and cluster details for export commands |
| 4 | Execute Exports | Run cluster-specific export commands on CNode |
| 5 | Run vnetmap | Execute vnetmap.py with proper arguments |
| 6 | Validate Output | Parse and validate vnetmap results |
| 7 | Save Results | Save output to local laptop |

### VAST Support Tools (5 steps)

Runs VAST's diagnostic script inside the cluster container.

| Step | Name | Description |
|------|------|-------------|
| 1 | Download Script | Download vast_support_tools.py to CNode |
| 2 | Run in Container | Execute script inside VAST container |
| 3 | Validate Results | Check output for errors and warnings |
| 4 | Package Results | Create archive of diagnostic output |
| 5 | Download Archive | SCP archive to local laptop |

### vperfsanity Performance Test (7 steps)

User-initiated storage performance validation using the vperfsanity test suite. Includes automated cross-tenant cleanup to prevent bucket name conflicts.

| Step | Name | Description |
|------|------|-------------|
| 1 | Deploy Package | Download vperfsanity tarball to CNode via ToolManager (internet-first, local cache fallback) |
| 2 | Extract Package | Extract tarball to `/tmp/vast_scripts/vperfsanity` working directory |
| 3 | Prepare Infrastructure | Cross-tenant API cleanup of stale views, then create test user, view policy, view/bucket, and deploy elbencho |
| 4 | Run Performance Tests | Execute write (-w) and read (-r) tests against VIP pool |
| 5 | Collect Results | Run `vperfsanity_results.sh` and save summary locally |
| 6 | Upload Results | Upload results to VAST (requires cluster internet access; skipped gracefully if unavailable) |
| 7 | Cleanup | Delete test data, remove infrastructure (user, view, policy), and clean up package files |

**Environment variables:** `VAST_VMS` (cluster IP), `ADMIN_USER`, and `ADMIN_PASSWORD` are explicitly passed to all remote script executions.

**Cross-tenant cleanup:** Step 3 queries `GET /api/views/` to find any `vperfsanity` views across all tenants and deletes them before running the prepare script, preventing HTTP 400 "bucket name already in use" errors from prior runs in different tenant contexts.

### VMS Log Bundle (5 steps)

Collects VMS logs for support analysis.

| Step | Name | Description |
|------|------|-------------|
| 1 | Discover Sizes | Check log sizes before collection |
| 2 | Confirm Collection | Review sizes and confirm (skip large bundles) |
| 3 | Create Archive | Compress logs into tar.gz |
| 4 | Download Bundle | Transfer archive to laptop |
| 5 | Verify Contents | Check archive integrity |

### Switch Configuration Extraction (3 steps)

Extracts switch configuration for backup or replacement provisioning.

| Step | Name | Description |
|------|------|-------------|
| 1 | Connect to Switch | Establish SSH connection and detect type (Cumulus/Onyx) |
| 2 | Extract Configuration | Retrieve running config and interface info |
| 3 | Save Configuration | Save to local text and JSON files |

### Network Configuration Extraction (4 steps)

Extracts network configuration commands for new node provisioning.

| Step | Name | Description |
|------|------|-------------|
| 1 | Connect to CNode | Establish SSH connection |
| 2 | Search History | Find configure_network.py commands in bash history |
| 3 | Extract network.ini | Read current network.ini configuration |
| 4 | Save Output | Save commands and config to local files |

---

## Using Advanced Operations

### Connection Settings

The Connection Settings section provides:

- **Saved Profiles:** Dropdown with save/add/delete icon buttons; profiles are shared across Advanced Ops, Health Check, and Generate Report pages
- **Upper fields (always visible):** Cluster IP / VMS, API Username, API Password
- **Lower fields (collapsible):** Node SSH User/Password, Switch SSH User/Password, VIP Pool Name
- **Add button (green +):** Toggles the lower credential fields open/closed; clears fields when expanding for a new profile
- **Default Credentials toggle:** Located at the far right; auto-populates standard credentials when enabled
- **Update Tools button:** Downloads latest versions of deployment tools (vnetmap.py, mlnx_switch_api.py, vast_support_tools.py)

### Starting a Workflow

1. Navigate to **Advanced Ops** in the navigation bar
2. Select or create a profile in **Connection Settings**; verify credentials
3. Select a workflow from the **Select Operation** dropdown
4. Review the workflow steps that appear
5. Click **Start Workflow** to begin

### Execution Modes

| Mode | Description |
|------|-------------|
| **Step-by-Step** | Click individual **Run** buttons to execute each step |
| **Run All** | Click **Run All Steps** to execute all steps sequentially |
| **Cancel** | Click **Cancel** to stop the current workflow |
| **Reset** | Click **Reset** to clear state and start over |

### Output Pane

The output pane at the bottom of the page shows:

- **Timestamps** for each message
- **Log levels** (info, success, warning, error)
- **Detailed output** from script execution

**Controls (via dropdown menu):**

- **Copy to Clipboard** - Copy all output text
- **Expand/Minimize** - Toggle full-screen output
- **Toggle Auto-scroll** - Enable/disable auto-scroll to bottom
- **Clear Output** - Clear all output messages

Output persists when navigating to other pages and returning.

### Downloading Results

After completing workflows, click **Download Results** to:

1. Collect all generated files
2. Create a timestamped ZIP bundle
3. Download to your local system

The bundle contains:
- Health check JSON results
- Network configurations
- Switch configurations
- vnetmap output
- Performance results
- Support tool archives
- Summary markdown

---

## Troubleshooting

### Workflow Won't Start

- Verify credentials are entered
- Check that cluster IP is reachable
- Ensure Developer Mode is enabled (`--dev-mode`)

### SSH Connection Fails

- Verify SSH credentials are correct
- Check that port 22 is accessible from your network
- Confirm the SSH user has required permissions

### Script Download Fails

- Check internet connectivity
- Verify firewall allows HTTPS to script sources
- Try running the step again

### Step Fails with Error

1. Check the output pane for error details
2. Click **Reset** and retry the workflow
3. Review SSH/API credentials
4. Check cluster availability

---

## Architecture

### File Structure

```
src/
├── advanced_ops.py       # Workflow orchestration and state management
├── script_runner.py      # Script download, copy, execution, and output classification
├── result_bundler.py     # Result collection and ZIP creation
├── tool_manager.py       # Centralized tool download, local caching, and CNode deployment
├── session_manager.py    # SSH session lifecycle management
└── workflows/
    ├── __init__.py       # Workflow registry
    ├── vnetmap_workflow.py
    ├── support_tool_workflow.py
    ├── vperfsanity_workflow.py
    ├── log_bundle_workflow.py
    ├── switch_config_workflow.py
    └── network_config_workflow.py

frontend/templates/
└── advanced_ops.html     # UI page with step runner, output pane, and connection settings
```

### Workflow Registry Pattern

Workflows are registered in `src/workflows/__init__.py`:

```python
from workflows import WorkflowRegistry

# Get all available workflows
workflows = WorkflowRegistry.list_all()

# Get a specific workflow
vnetmap = WorkflowRegistry.get("vnetmap")
```

### Adding New Workflows

1. Create a new workflow class in `src/workflows/`
2. Implement required methods: `get_steps()`, `run_step()`, `validate_prerequisites()`
3. Register in `src/workflows/__init__.py`
4. Add tests in `tests/test_workflows.py`

---

## Security Considerations

- Credentials are never logged or persisted
- SSH connections use standard paramiko/pexpect
- Downloaded scripts are verified before execution
- All operations are read-only on the cluster
- Developer Mode gating prevents accidental access
