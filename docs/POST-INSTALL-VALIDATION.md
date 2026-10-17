# Post-Install Validation Guide

This guide maps VAST cluster post-installation validation procedures to the As-Built Report Generator's automated checks and Advanced Operations workflows.

## Validation Overview

The VAST installation template includes a comprehensive post-install validation checklist. This document shows how each validation item is addressed by the As-Built Report Generator.

## Prerequisites

### SSH Proxy Hop

By default, switch SSH connections tunnel through the CNode for field deployments where switches are only reachable from inside the cluster network. The "Proxy through CNode" toggle (default: ON) is available on Generate and Reporter pages. Use `--no-proxy-jump` on the CLI to disable.

---

## Health Check Validations (Automated)

These checks run automatically via the **Health Check** module.

### Tier 1: API Checks (27 checks)

| Validation | Health Check | Status |
|------------|--------------|--------|
| **RAID Health / Rebuild** | `_check_cluster_raid_health()`, `_check_raid_rebuild_progress()` | Automated |
| **Leader, Cluster and Expansion State** | `_check_leader_state()`, `_check_cluster_state()`, `_check_expansion_state()` | Automated |
| **Node Status** | `_check_cnode_status()`, `_check_dnode_status()` | Automated |
| **Enclosure Status** | `_check_dbox_status()`, `_check_cbox_status()`, `_check_ebox_status()` | Automated |
| **Firmware** | `_check_firmware_consistency()` | Automated |
| **Alarms and Events** | `_check_active_alarms()`, `_check_events()` | Automated |
| **VIP Pools and Network Settings** | `_check_vip_pools()`, `_check_network_settings()` | Automated |
| **License** | `_check_license()` | Automated + Reminder |
| **Capacity and Handles** | `_check_capacity()`, `_check_handle_usage()` | Automated |
| **Performance Baseline** | `_check_performance_baseline()` | Automated |
| **Replication, Snapshots, Quotas, Data Protection** | `_check_replication()`, `_check_snapshots()`, `_check_quotas()`, `_check_data_protection()` | Automated |
| **Device Health** | `_check_device_health()` | Automated |
| **Call Home** | `_check_call_home_status()` | Automated + Reminder |
| **Rack/U-Height** | `_check_rack_uheight_config()` | Automated + Reminder |
| **Switches Registered** | `_check_switches_registered()` | Automated + Reminder |

Checks that do not apply are reported as **skipped** with the reason, for example CBox Status on a
converged EBox cluster. In the PDF, the results are grouped by functional area under Health Check Details.

### Tier 3: Switch SSH Checks (6 checks)

> **Note:** Tier 2 node SSH checks (10 checks) were removed in v1.5.0 — they are redundant with diagnostics run by `vast_support_tools.py` in the One-Shot test suite and produced false-positive results when SSH targeted the Management CNode.

| Validation | Health Check | Status |
|------------|--------------|--------|
| **MLAG Status** | `_check_mlag_status()` (Onyx and Cumulus) | Automated |
| **NTP Status** | `_check_switch_ntp()` (Onyx and Cumulus) | Automated |
| **Config Backup** | `_check_switch_config_backup()` | Automated |

---

## Advanced Operations (Manual Workflows)

These validations require user-initiated workflows via **Advanced Operations** (Developer Mode).

### vnetmap Network Topology Validation

**Confluence Procedure:** Run vnetmap.py to validate network topology

**Advanced Ops Workflow:** `vnetmap` (7 steps)

1. Download vnetmap.py and mlnx_switch_api.py
2. Copy to CNode
3. Generate environment variables
4. Execute export commands
5. Run vnetmap.py
6. Validate results
7. Save output

### VAST Support Tools Diagnostics

**Confluence Procedure:** Run vast_support_tools.py for system diagnostics

**Advanced Ops Workflow:** `support_tool` (5 steps)

1. Download script to the CNode, beside the VMS container wrapper (on EBox clusters, `/vast/data/C-*/vms.sh`)
2. Set permissions
3. Run `vast_support_tools.py inspect` in the VAST container
4. Create archive
5. Download results

### vperfsanity Performance Validation

**Confluence Procedure:** Run performance sanity tests

**Advanced Ops Workflow:** `vperfsanity` (7 steps)

1. Deploy
2. Extract
3. Prepare
4. Run tests
5. Collect
6. Upload
7. Cleanup (also runs after a failed or cancelled run)

### VMS Log Bundle Collection

**Confluence Procedure:** Collect VMS logs for support

**Advanced Ops Workflow:** `log_bundle` (5 steps)

1. Discover log sizes
2. Confirm collection (based on size)
3. Create archive (`/var/log` sources plus `/vast/log` files from the last 24 hours, capped at 2 GB; marked partial if a source is missing)
4. Download bundle
5. Verify contents

### Switch Configuration Backup

**Confluence Procedure:** Extract and save switch configuration

**Advanced Ops Workflow:** `switch_config` (3 steps)

1. Connect to switch
2. Extract configuration
3. Save to local files

### Network Configuration Extraction

**Confluence Procedure:** Document configure_network.py commands for node replacement

**Advanced Ops Workflow:** `network_config` (4 steps)

1. Connect to CNode
2. Search bash history for configure_network.py
3. Extract network.ini
4. Save commands and config

---

## Manual Validations (Reminders)

These items require manual verification. The tool generates reminders.

### Customer Handoff

| Item | Tool Behavior |
|------|---------------|
| **VIP Failover Test** | Reminder with manual test steps |
| **VIP Movement Test** | Reminder with manual test steps |
| **Password Management** | Reminder to change default passwords |
| **Documentation Handoff** | Reports generated for customer |

### License Activation

| Item | Tool Behavior |
|------|---------------|
| **License Key Applied** | API check + reminder if missing |
| **Features Enabled** | Reported in Executive Summary |

### Storage Configuration

| Item | Tool Behavior |
|------|---------------|
| **Capacity Allocation** | Automated in Tier 1 checks |
| **Quota Configuration** | Automated in Tier 1 checks |

---

## Validation Workflow

The **Reporter** page is the primary web interface for standard users (report generation and health checks). **Advanced Operations**, workflow bundles, and One-Shot validation require launching the app with `--dev-mode`.

### Recommended Sequence

1. **Run Health Check (Tier 1)** — Reporter or Generate → Include Health Check
2. **Run Health Check (Tier 3 — Switch SSH)** — Enable Port Mapping with SSH credentials
3. **Review PDF Report** — Check Health Check Results section
4. **Address Failures** — Follow remediation report guidance
5. **Run Advanced Operations** — Execute vnetmap, support tools workflows
6. **Download Results Bundle** — Create validation package
7. **Complete Manual Checks** — VIP failover, password changes

> **Configuration:** Health check tiers, SSH proxy settings, and default credentials are configurable via the **Advanced Configuration** page (`/config/advanced`) or `config.yaml`. Use the **Report Tuning Tool** on the Results page to regenerate reports with different section or formatting settings.

### Output Artifacts

| Artifact | Location |
|----------|----------|
| **As-Built PDF Report** | `reports/vast_asbuilt_report_*.pdf` |
| **Health Check JSON** | `output/health/health_check_*.json` |
| **Remediation Report** | `output/health/health_remediation_*.txt` |
| **Validation Bundle** | `output/bundles/validation_bundle_*.zip` |
| **Network Configs** | `output/advanced_ops/network_configs/` |
| **Switch Configs** | `output/advanced_ops/switch_configs/` |
| **vnetmap Output** | `output/advanced_ops/vnetmap/` |

---

## Validation Summary Matrix

| Category | Validation | Method | Location |
|----------|------------|--------|----------|
| **Infrastructure** | RAID | API Check (Tier 1) | Health Check |
| | Nodes | API Check (Tier 1) | Health Check |
| | DBoxes/CBoxes | API Check (Tier 1) | Health Check |
| | Firmware | API Check (Tier 1) | Health Check |
| **Network** | MLAG | Switch SSH (Tier 3) | Health Check |
| | NTP | Switch SSH (Tier 3) | Health Check |
| | Topology | Advanced Ops | vnetmap workflow |
| **Configuration** | License | API Check | Health Check |
| | Call Home | API Check | Health Check |
| | Rack Layout | API Check | Health Check |
| | Switches | API Check | Health Check |
| **Performance** | vperfsanity | Advanced Ops | vperfsanity workflow |
| **Diagnostics** | Support Tools | Advanced Ops | support_tool workflow |
| | Log Bundle | Advanced Ops | log_bundle workflow |
| **Documentation** | Config Backup | Advanced Ops | switch_config, network_config |
| **Handoff** | VIP Failover | Manual | Reminder |
| | Passwords | Manual | Reminder |

---

## One-Shot Mode: Automated Full Validation

For comprehensive post-install validation in a single pass, use **One-Shot Mode** in Advanced Operations:

1. Navigate to Advanced Ops (requires `--dev-mode`)
2. Toggle the mode switch to **One-Shot**
3. Select all validation workflows and check **Generate As-Built Report**
4. Run **Pre-Validation** to verify credentials, connectivity, and tool readiness
5. Click **Start One-Shot** to execute:
   - Health Checks (Tier 1 + Tier 3)
   - All selected operations (vnetmap, support tools, vperfsanity, log bundle, switch config, network config)
   - As-Built Report generation
   - Automatic bundling of all results
6. Download the bundle for handoff documentation

This is the recommended path for complete post-install validation when all credentials and network access are available.

---

## Confluence Reference

This guide implements validations from:

- [VAST Installation Template - Post-Install Validations](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/7391248523/Copy+of+VAST+Installation+Template)

For additional details, refer to the VAST Operations Guide and support documentation.
