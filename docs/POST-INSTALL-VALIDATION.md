# Post-Install Validation Guide

This guide maps VAST cluster post-installation validation procedures to the As-Built Report Generator's automated checks and Advanced Operations workflows.

## Validation Overview

The VAST installation template includes a comprehensive post-install validation checklist. This document shows how each validation item is addressed by the As-Built Report Generator.

---

## Health Check Validations (Automated)

These checks run automatically via the **Health Check** module.

### Tier 1: API Checks (26 checks)

| Validation | Health Check | Status |
|------------|--------------|--------|
| **RAID Health** | `_check_raid_health()` | Automated |
| **Node Status** | `_check_cnode_status()`, `_check_dnode_status()` | Automated |
| **DBox Status** | `_check_dbox_status()` | Automated |
| **CBox Status** | `_check_cbox_status()` | Automated |
| **Active Alarms** | `_check_active_alarms()` | Automated |
| **VIP Status** | `_check_vip_status()` | Automated |
| **License Status** | `_check_license_status()` | Automated + Reminder |
| **Capacity** | `_check_capacity()` | Automated |
| **Firmware** | `_check_firmware_consistency()` | Automated |
| **Leader Election** | `_check_leader_state()` | Automated |
| **Upgrade State** | `_check_upgrade_status()` | Automated |
| **Call Home** | `_check_call_home_status()` | Automated + Reminder |
| **Rack/U-Height** | `_check_rack_uheight_config()` | Automated + Reminder |
| **Switches Registered** | `_check_switches_registered()` | Automated + Reminder |

### Tier 2: Node SSH Checks (10 checks)

| Validation | Health Check | Status |
|------------|--------------|--------|
| **Management Ping** | `_check_management_reachability()` | Automated |
| **Memory/Disk** | `_check_node_memory()` | Automated |
| **Services Running** | `_check_node_services()` | Automated |
| **Network Interfaces** | `_check_node_interfaces()` | Automated |

### Tier 3: Switch SSH Checks (6 checks)

| Validation | Health Check | Status |
|------------|--------------|--------|
| **MLAG Status** | `_check_switch_mlag()` | Automated |
| **NTP Status** | `_check_switch_ntp()` | Automated |
| **Config Backup** | `_check_switch_config()` | Automated |

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

1. Download script
2. Run in VAST container
3. Validate results
4. Package output
5. Download archive

### vperfsanity Performance Validation

**Confluence Procedure:** Run performance sanity tests

**Advanced Ops Workflow:** `vperfsanity` (6 steps)

1. Download vperfsanity package
2. Prepare environment
3. Run write test
4. Run read test
5. Collect results
6. Cleanup

### VMS Log Bundle Collection

**Confluence Procedure:** Collect VMS logs for support

**Advanced Ops Workflow:** `log_bundle` (5 steps)

1. Discover log sizes
2. Confirm collection (based on size)
3. Create archive
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

### Recommended Sequence

1. **Run Health Check (Tier 1)** - Generate → Include Health Check
2. **Run Health Check (Tier 2+3)** - Enable Port Mapping with SSH credentials
3. **Review PDF Report** - Check Health Check Results section
4. **Address Failures** - Follow remediation report guidance
5. **Run Advanced Operations** - Execute vnetmap, support tools workflows
6. **Download Results Bundle** - Create validation package
7. **Complete Manual Checks** - VIP failover, password changes

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
| **Infrastructure** | RAID | API Check | Health Check |
| | Nodes | API Check | Health Check |
| | DBoxes/CBoxes | API Check | Health Check |
| | Firmware | API Check | Health Check |
| **Network** | Management IPs | SSH Check | Health Check |
| | Interfaces | SSH Check | Health Check |
| | MLAG | SSH Check | Health Check |
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

## Confluence Reference

This guide implements validations from:

- [VAST Installation Template - Post-Install Validations](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/7391248523/Copy+of+VAST+Installation+Template)

For additional details, refer to the VAST Operations Guide and support documentation.
