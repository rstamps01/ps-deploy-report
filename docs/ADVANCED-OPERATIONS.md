# Advanced Operations Guide

The Advanced Operations module provides step-by-step execution of complex validation workflows that require script downloads, remote SSH execution, and multi-stage processing. This is a developer/testing feature designed for post-install validation and troubleshooting.

## Reporter Page (Standard Mode)

The **Reporter** page (`/reporter`) is the primary user-facing interface for post-install validation workflows. It is accessible to all users without `--dev-mode` and combines:

- **Switch Placement Mode:** Auto/Manual toggle with rack and switch discovery, manual switch IP entry, and placed switches table
- **Reporter Checklist:** Pre-Validation (recommended), Run Reporter (as-built report generation), and optional Health Check with tier-based logic
- **One-Shot Mode:** Toggle to select multiple validation operations (vnetmap, support tools, vperfsanity, log bundle, switch config, network config) to run sequentially with auto-bundling
- **VAST Logo Progress Indicator:** Visual progress with fill animation, percentage, and stopwatch timer
- **Operation Badges:** Color-coded badges (Net Test, Sys Test, Perf Test, Pull Logs, Pull Config, Recommended, Optional) on each operation

The Advanced Operations page described below provides the same workflows in a step-by-step developer interface, accessible only with `--dev-mode`.

## Prerequisites

### Developer Mode

Advanced Operations is only accessible when the application is started with the `--dev-mode` flag:

```bash
# Desktop application
open "VAST Reporter.app" --args --dev-mode

# From source
python3 -m src.main --dev-mode
```

When enabled, the following links appear in the navigation bar:
- **Health Check** — Cluster health checks with tier selection
- **Advanced Ops** (gear icon) — Step-by-step and one-shot workflow runner
- **Validation Results** (checkmark icon) — Browse all operation results by cluster
- **Configuration** — Application settings

### Credentials

| Credential | Required For | Default (when toggle ON) | Description |
|------------|--------------|--------------------------|-------------|
| **Cluster IP** | All workflows | — | VMS IP address or hostname |
| **API Username/Password** | All workflows | `support` / `654321` | VAST API credentials (support account) |
| **Node SSH User/Password** | Most workflows | `vastdata` / `vastdata` | SSH credentials for CNodes |
| **Switch SSH User/Password** | Switch workflows | `cumulus` / `Vastdata1!` | SSH credentials for switches |
| **VIP Pool Name** | vperfsanity | `main` | VIP pool name for performance testing |

**Global Setting — Autofill Default Passwords:** A toggle in the Connection Settings bottom toolbar auto-populates standard credentials when set to Enable (default). Set to Disable to enter custom credentials for non-standard configurations. When default passwords are enabled, `support`/`654321` is used for all operations except vperfsanity, which is automatically overridden to `admin`/`123456` (the only operation requiring admin access). If the admin password has been changed on the cluster, disable the toggle and enter the current admin credentials manually.

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

The Connection Settings tile opens in a compact collapsed view and expands to reveal all options.

**Collapsed (default):**
- **Saved Profiles dropdown** with a **Create Cluster Profile** button (green +) — always visible
- **Collapse/Expand arrow** in the card header — click to expand or collapse the tile

**Expanded (arrow click or Create Cluster Profile):**
- All credential fields: Cluster IP / VMS, API Username/Password, Node SSH User/Password, Switch SSH User/Password, VIP Pool Name
- **Global Setting — Autofill Default Passwords** toggle at the bottom-left with Disable/Enable labels
- **Save** (checkmark) and **Delete** (trash) profile icons at the bottom-right

**Create Cluster Profile button:** Expands the tile, switches dropdown to "-- Create a profile --", clears Cluster IP, resets default credentials, and opens the form for entry.

**Profiles** are shared across Advanced Ops, Health Check, and Generate Report pages. The tile collapse/expand state is persisted across page navigation.

### Starting a Workflow

1. Navigate to **Advanced Ops** in the navigation bar
2. Select or create a profile in **Connection Settings**; verify credentials
3. Select a workflow from the **Select Operation** dropdown
4. Review the workflow steps that appear
5. Click **Start Workflow** to begin

### Execution Modes

The Select Operation card has a **Step-by-Step / One-Shot** toggle at the top right.

#### Step-by-Step Mode (default)

| Action | Description |
|--------|-------------|
| **Step-by-Step** | Click individual **Run** buttons to execute each step |
| **Run All** | Click **Run All Steps** to execute all steps sequentially |
| **Cancel** | Click **Cancel** to stop the current workflow |
| **Reset** | Click **Reset** to clear state and start over |

#### One-Shot Mode

Run multiple operations sequentially in a single pass with automated pre-validation.

1. Toggle the switch to **One-Shot**
2. Check/uncheck operations to include. **Health Checks** are checked by default ("Recommended") but can be unchecked if not needed.
3. Optionally check **Generate As-Built Report** to auto-generate a report after all operations complete
4. Click **Run Pre-Validation** to check environment readiness. Validation runs asynchronously; a **Cancel** button is available to stop it at any point.
5. Review validation results; if warnings appear, choose **Proceed Anyway** or **Stop & Fix**
6. Click **Start One-Shot** to begin sequential execution
7. Monitor progress via the phase indicator: Operations -> Report -> Bundling.
8. On completion, click **Download Bundle** to get the cluster-scoped ZIP of all results

**Execution Order:**
- Selected operations run in checklist order
- As-Built report generation (if selected) runs after all operations; health checks (Tiers 1-3) run within the report phase when the Health Checks checkbox is selected
- Results are automatically bundled into a cluster-scoped ZIP

**Pre-Validation Checks:**
- Credential completeness (cluster IP, API credentials, SSH credentials for selected operations)
- Cluster API reachability
- Node SSH connectivity (warn with proceed/stop option on failure)
- Switch SSH connectivity (warn with proceed/stop option on failure)
- Cluster outbound internet access (required when vnetmap, support tools, or vperfsanity is selected)
- Tool freshness (warn if any cached tools are >10 days old)
- vperfsanity duration notice (~30 minutes)

**Cancellation:** Cancel at any point between phases. The current phase completes its in-progress step before stopping.

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

The bundle is **cluster-scoped**: only files matching the selected cluster's IP are included. For each operation category, the most recent matching file is selected. If an operation hasn't been run for the cluster, the bundle includes a placeholder note.

The bundle contains (when available):
- Health check JSON results and remediation reports
- Network configuration summaries and text backups
- Switch configuration JSON and all per-switch text backups
- vnetmap results and raw output
- vperfsanity performance results
- Support tool archives (matched via sidecar `.meta.json`)
- Log bundles (matched via verification JSON)
- As-Built report PDF (matched via sidecar `.meta.json` cluster_ip)
- As-Built report JSON data file (matched via `cluster_ip` field)
- SUMMARY.md and manifest.json

---

## Validation Results Page

The **Validation Results** page (`/validation-results`) provides a browser for all operation results across clusters. Like Advanced Ops, it is only visible in Developer Mode.

### Features

- **Operation Tabs:** 9 tabs for each operation type (As-Built Reports, Health Checks, Network Config, Switch Config, vnetmap, vperfsanity, Support Tools, Log Bundles, Bundles)
- **Profile Filter Dropdown:** Filter all tabs by a saved cluster profile, view all clusters at once, or view only "Unsaved Cluster Results"
- **Per-Tab Tables:** Each tab shows file name, type, size, cluster IP, generation date, and View/Download/Delete actions
- **Tab Badges:** Each tab shows the count of results for the active filter

### Cluster Identification

Results are tagged with a cluster IP using multiple strategies:
- **JSON files:** `cluster_ip` field in the JSON content
- **Text files:** IP address in the first 10 lines of the file header
- **Filenames:** IP address embedded in the filename (with dots or underscores)
- **Sidecar files:** `.meta.json` (support tools, As-Built PDFs) or `.verification.json` (log bundles) alongside the file
- **As-Built reports:** Matched by sidecar `.meta.json` cluster_ip first, then filename IP, then cluster name in filename as fallback
- **Cluster name resolution:** When only the IP is known, the bundler scans existing `vast_data_*.json` files to resolve the real API cluster name for manifest metadata

---

## Output Pane Log Levels

The output pane includes a **log level selector** (Status / Live / Debug) that controls the verbosity of displayed messages:

| Level | Content |
|-------|---------|
| **Status** (default) | Operation start/complete banners, progress counters (e.g., "API check 5/28"), phase results summary with pass/fail/warn counts |
| **Live** | Everything in Status plus all internal logger output (info/warning/error) from HealthChecker, report pipeline, and workflows |
| **Debug** | Everything in Live plus debug-level messages for deep troubleshooting |

All messages are always captured in the backend buffer regardless of the selected level. Switching levels filters the display instantly without re-fetching.

### Health Check Progress

During health checks, each individual check result is reported in the output:

```
  [PASS] Cluster RAID Health (1/28)
  [PASS] Leader State (2/28)
  [FAIL] Active Alarms (5/28)
        3 critical alarms detected
  ...
  Health checks complete: 25 pass, 2 fail, 1 warning
```

### Report Generation Progress

Report generation shows step-by-step status:

```
Authenticating with cluster API...
Collecting cluster data...
Data collected: 42 sections
Processing and extracting report data...
Generating PDF report...
```

---

## Persistent Operation Logs

One-Shot operation logs are automatically saved to disk on completion (success, failure, or cancellation). Logs are stored as JSON Lines files under `logs/operations/`.

### Capacity Management

- **Default limit:** 1 GB total log storage
- **Auto-purge:** When the limit is exceeded, the oldest 25% of log files are automatically deleted with a user warning
- **Manual purge:** Available via `POST /advanced-ops/logs/purge`
- **Capacity check:** `GET /advanced-ops/logs/capacity` returns storage stats

---

## Window State Persistence

The Advanced Operations page preserves its state across navigation and browser close/reopen:

- **Running operations:** If a One-Shot or step-by-step workflow is running in the background, the page automatically detects this on reload and resumes the progress UI and polling
- **UI preferences:** Mode toggle, selected profile, workflow selection, checklist selections, default credentials toggle, and log tier are saved in browser `localStorage`
- **Output buffer:** Output entries are preserved across tab switches via `sessionStorage`, with delta-sync from the server on page reload to avoid gaps

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
├── advanced_ops.py       # Workflow orchestration and state management (step-by-step mode)
├── oneshot_runner.py     # One-shot orchestrator: pre-validation, sequential multi-op execution, auto-bundling
├── script_runner.py      # Script download, copy, execution, and output classification
├── result_bundler.py     # Cluster-scoped result collection and ZIP creation
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
└── advanced_ops.html     # UI page with step-by-step/one-shot toggle, output pane, and connection settings
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

## SSH Proxy Hop

Switch SSH connections tunnel through the CNode via paramiko nested transport (`direct-tcpip` channel) by default. This enables port mapping and Tier 3 health checks when switches are only reachable from inside the cluster network.

- **Default:** ON — switch SSH goes through the CNode
- **UI Toggle:** "Proxy through CNode" toggle on Generate and Reporter pages; persists in profiles
- **CLI:** `--no-proxy-jump` flag disables proxy hop for direct-connection environments
- **Profile Persistence:** Proxy hop setting saved with cluster profiles

---

## Security Considerations

- Credentials are never logged or persisted
- SSH connections use standard paramiko/pexpect
- Downloaded scripts are verified before execution
- All operations are read-only on the cluster
- Developer Mode gating prevents accidental access
