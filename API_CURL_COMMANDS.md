# VAST API Curl Commands for Report Generation

## Overview
This document provides curl commands that return only the specific information needed for each report section, formatted for easy import into spreadsheets or Word documents.

## Authentication
All commands assume you have valid credentials. Replace `<USERNAME>` and `<PASSWORD>` with your actual credentials.

---

## 1. Cluster Information

### Basic Cluster Details
```bash
# Get cluster basic information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | [.id, .name, .mgmt_vip, .url, .build, .psnt, .guid, .uptime, .online_start_time, .deployment_time] | @csv'

# Get cluster state information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv'

# Get cluster capacity information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | [.usable_capacity_tb, .free_usable_capacity_tb, .drr_text, .physical_space_tb, .physical_space_in_use_tb, .free_physical_space_tb, .physical_space_in_use_percent, .logical_space_tb, .logical_space_in_use_tb, .free_logical_space_tb, .logical_space_in_use_percent] | @csv'

# Get cluster encryption information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | [.enable_encryption, .S3_ENABLE_ONLY_AES_CIPHERS, .encryption_type, .ekm_servers, .ekm_address, .ekm_port, .ekm_auth_domain, .secondary_ekm_address, .secondary_ekm_port] | @csv'
```

### Human-Readable Format
```bash
# Get cluster information in human-readable format
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | "Cluster ID: \(.id)\nName: \(.name)\nManagement VIP: \(.mgmt_vip)\nBuild: \(.build)\nPSNT: \(.psnt)\nGUID: \(.guid)\nUptime: \(.uptime)\nState: \(.state)\nUsable Capacity: \(.usable_capacity_tb) TB\nFree Capacity: \(.free_usable_capacity_tb) TB\nDRR: \(.drr_text)\n---"'
```

---

## 2. Network Configuration

### Cluster Network Settings
```bash
# Get cluster network configuration (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | [.management_vips, .external_gateways, .dns, .ntp, .ext_netmask, .auto_ports_ext_iface, .b2b_ipmi, .eth_mtu, .ib_mtu, .ipmi_gateway, .ipmi_netmask] | @csv'
```

### CNode Network Settings
```bash
# Get CNode network settings (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/vms/1/network_settings/" \
  | jq -r '.[] | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .net_type] | @csv'
```

### DNode Network Settings
```bash
# Get DNode network settings (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/vms/1/network_settings/" \
  | jq -r '.[] | select(.node_type == "Dnode") | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .position, .net_type] | @csv'
```

### Human-Readable Format
```bash
# Get network configuration in human-readable format
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | "Management VIPs: \(.management_vips)\nExternal Gateways: \(.external_gateways)\nDNS: \(.dns)\nNTP: \(.ntp)\nExternal Netmask: \(.ext_netmask)\nEthernet MTU: \(.eth_mtu)\nInfiniBand MTU: \(.ib_mtu)\n---"'
```

---

## 3. CBoxes Information

### CBox Details
```bash
# Get CBox information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v1/cboxes/" \
  | jq -r '.[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state] | @csv'

# Get specific CBox details by ID
for id in 1 3 4; do
  curl -k -u "<USERNAME>:<PASSWORD>" \
    "https://10.143.11.204/api/v1/cboxes/$id" \
    | jq -r '[.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state] | @csv'
done
```

### Human-Readable Format
```bash
# Get CBox information in human-readable format
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v1/cboxes/" \
  | jq -r '.[] | "CBox ID: \(.id)\nName: \(.name)\nRack Unit: \(.rack_unit)\nRack Name: \(.rack_name)\nState: \(.state)\nGUID: \(.guid)\n---"'
```

---

## 4. CNodes Information

### CNode Details
```bash
# Get CNode information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/cnodes/" \
  | jq -r '.[] | [.id, .name, .hostname, .guid, .cluster, .cbox_id, .cbox, .box_vendor, .os_version, .build, .state, .display_state, .sync, .is_leader, .is_mgmt, .vlan, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv'

# Get specific CNode details by ID
for id in 3 2 6; do
  curl -k -u "<USERNAME>:<PASSWORD>" \
    "https://10.143.11.204/api/v7/cnodes/$id" \
    | jq -r '[.id, .name, .hostname, .guid, .cluster, .cbox_id, .cbox, .box_vendor, .os_version, .build, .state, .display_state, .sync, .is_leader, .is_mgmt, .vlan, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv'
done
```

### Human-Readable Format
```bash
# Get CNode information in human-readable format
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/cnodes/" \
  | jq -r '.[] | "CNode ID: \(.id)\nName: \(.name)\nHostname: \(.hostname)\nCBox: \(.cbox)\nOS Version: \(.os_version)\nState: \(.state)\nManagement IP: \(.mgmt_ip)\nIPMI IP: \(.ipmi_ip)\nIs Leader: \(.is_leader)\nIs Management: \(.is_mgmt)\n---"'
```

---

## 5. DBoxes Information

### DBox Details
```bash
# Get DBox information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/dboxes/" \
  | jq -r '.[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state, .sync, .hardware_type] | @csv'
```

### Human-Readable Format
```bash
# Get DBox information in human-readable format
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/dboxes/" \
  | jq -r '.[] | "DBox ID: \(.id)\nName: \(.name)\nRack Unit: \(.rack_unit)\nRack Name: \(.rack_name)\nState: \(.state)\nHardware Type: \(.hardware_type)\nGUID: \(.guid)\n---"'
```

---

## 6. DTrays Information

### DTray Details
```bash
# Get DTray information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/dtrays/" \
  | jq -r '.[] | [.id, .name, .url, .guid, .cluster, .dbox_id, .dbox, .position, .dnodes, .hardware_type, .state, .sync, .bmc_ip, .mcu_state, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv'
```

### Human-Readable Format
```bash
# Get DTray information in human-readable format
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/dtrays/" \
  | jq -r '.[] | "DTray ID: \(.id)\nName: \(.name)\nDBox: \(.dbox)\nPosition: \(.position)\nState: \(.state)\nHardware Type: \(.hardware_type)\nBMC IP: \(.bmc_ip)\nMCU State: \(.mcu_state)\n---"'
```

---

## 7. DNodes Information

### DNode Details
```bash
# Get DNode information (CSV format)
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/dnodes/" \
  | jq -r '.[] | [.id, .name, .hostname, .guid, .cluster, .dbox_id, .dbox, .position, .os_version, .build, .state, .sync, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv'
```

### Human-Readable Format
```bash
# Get DNode information in human-readable format
curl -k -u "<USERNAME>:<PASSWORD>" \
  "https://10.143.11.204/api/v7/dnodes/" \
  | jq -r '.[] | "DNode ID: \(.id)\nName: \(.name)\nHostname: \(.hostname)\nDBox: \(.dbox)\nPosition: \(.position)\nOS Version: \(.os_version)\nState: \(.state)\nManagement IP: \(.mgmt_ip)\nIPMI IP: \(.ipmi_ip)\n---"'
```

---

## Usage Instructions

### For Spreadsheet Import
1. Run the CSV format commands
2. Copy the output
3. Paste into Excel/Google Sheets
4. Use "Text to Columns" with comma delimiter

### For Word Document Import
1. Run the human-readable format commands
2. Copy the output
3. Paste into Word document
4. Format as needed

### For JSON Processing
1. Remove the `| jq -r '...'` part from commands
2. Get raw JSON output
3. Process with your preferred JSON tool

### Authentication Options
- Replace `<USERNAME>:<PASSWORD>` with actual credentials
- Use API tokens: `-H "Authorization: Api-Token <TOKEN>"`
- Use basic auth: `-u "username:password"`

### SSL Certificate Issues
- Add `-k` flag to ignore SSL certificate verification
- For production, use proper SSL certificates

---

## Example Usage

```bash
# Get cluster information and save to file
curl -k -u "admin:password" \
  "https://10.143.11.204/api/v7/clusters/" \
  | jq -r '.[] | [.id, .name, .mgmt_vip, .build, .state, .usable_capacity_tb] | @csv' \
  > cluster_info.csv

# Get all CBox information in human-readable format
curl -k -u "admin:password" \
  "https://10.143.11.204/api/v1/cboxes/" \
  | jq -r '.[] | "CBox ID: \(.id)\nName: \(.name)\nRack Unit: \(.rack_unit)\nState: \(.state)\n---"' \
  > cboxes_info.txt
```

This approach provides clean, structured data that can be easily imported into spreadsheets or Word documents for review and updating.
