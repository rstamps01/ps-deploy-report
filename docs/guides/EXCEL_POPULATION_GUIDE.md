# Excel Population Guide for VAST API Data

## Overview
This guide shows you how to use the generated curl commands to populate the empty columns in your API-Summary worksheet with specific VAST cluster data.

## Quick Start

### 1. Copy the Curl Commands
Use the `generate_curl_commands.py` script to get the exact commands:

```bash
python3 generate_curl_commands.py --cluster 10.143.11.204 --username admin --password password
```

### 2. Run Commands and Save Output
For each section, run the curl command and save to a CSV file:

```bash
# Cluster Basic Information
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.id, .name, .mgmt_vip, .url, .build, .psnt, .guid, .uptime, .online_start_time, .deployment_time] | @csv' > cluster_basic.csv

# Cluster State Information
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv' > cluster_state.csv

# Cluster Capacity Information
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.usable_capacity_tb, .free_usable_capacity_tb, .drr_text, .physical_space_tb, .physical_space_in_use_tb, .free_physical_space_tb, .physical_space_in_use_percent, .logical_space_tb, .logical_space_in_use_tb, .free_logical_space_tb, .logical_space_in_use_percent] | @csv' > cluster_capacity.csv

# Cluster Encryption Information
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.enable_encryption, .S3_ENABLE_ONLY_AES_CIPHERS, .encryption_type, .ekm_servers, .ekm_address, .ekm_port, .ekm_auth_domain, .secondary_ekm_address, .secondary_ekm_port] | @csv' > cluster_encryption.csv
```

### 3. Import into Excel

#### Method 1: Direct Paste
1. Open your Excel file
2. Go to the "ADD CURL COMMANDS HERE" column for each section
3. Run the curl command in terminal
4. Copy the output
5. Paste into Excel
6. Use "Text to Columns" with comma delimiter

#### Method 2: CSV Import
1. Save curl output to CSV files (as shown above)
2. In Excel: Data → Get Data → From Text/CSV
3. Select the CSV file
4. Choose comma delimiter
5. Import the data

## Detailed Section Mapping

### 1. Cluster Section

**Location in Excel:** Rows 5-50, Column 4 ("ADD CURL COMMANDS HERE")

**Commands to Use:**
```bash
# Basic cluster info (rows 5-15)
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.id, .name, .mgmt_vip, .url, .build, .psnt, .guid, .uptime, .online_start_time, .deployment_time] | @csv'

# State info (rows 16-35)
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv'

# Capacity info (rows 36-45)
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.usable_capacity_tb, .free_usable_capacity_tb, .drr_text, .physical_space_tb, .physical_space_in_use_tb, .free_physical_space_tb, .physical_space_in_use_percent, .logical_space_tb, .logical_space_in_use_tb, .free_logical_space_tb, .logical_space_in_use_percent] | @csv'

# Encryption info (rows 46-55)
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.enable_encryption, .S3_ENABLE_ONLY_AES_CIPHERS, .encryption_type, .ekm_servers, .ekm_address, .ekm_port, .ekm_auth_domain, .secondary_ekm_address, .secondary_ekm_port] | @csv'
```

### 2. Network Section - Cluster

**Location in Excel:** Rows 60-70, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '.[] | [.management_vips, .external_gateways, .dns, .ntp, .ext_netmask, .auto_ports_ext_iface, .b2b_ipmi, .eth_mtu, .ib_mtu, .ipmi_gateway, .ipmi_netmask] | @csv'
```

### 3. Network Section - CNodes

**Location in Excel:** Rows 75-85, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/vms/1/network_settings/" | jq -r '.[] | select(.node_type == "Cnode") | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .net_type] | @csv'
```

### 4. Network Section - DNodes

**Location in Excel:** Rows 90-100, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/vms/1/network_settings/" | jq -r '.[] | select(.node_type == "Dnode") | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .position, .net_type] | @csv'
```

### 5. CBoxes Section

**Location in Excel:** Rows 105-115, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v1/cboxes/" | jq -r '.[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state] | @csv'
```

### 6. CNodes Section

**Location in Excel:** Rows 120-140, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/cnodes/" | jq -r '.[] | [.id, .name, .hostname, .guid, .cluster, .cbox_id, .cbox, .box_vendor, .os_version, .build, .state, .display_state, .sync, .is_leader, .is_mgmt, .vlan, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv'
```

### 7. DBoxes Section

**Location in Excel:** Rows 145-155, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/dboxes/" | jq -r '.[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state, .sync, .hardware_type] | @csv'
```

### 8. DTrays Section

**Location in Excel:** Rows 160-175, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/dtrays/" | jq -r '.[] | [.id, .name, .url, .guid, .cluster, .dbox_id, .dbox, .position, .dnodes, .hardware_type, .state, .sync, .bmc_ip, .mcu_state, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv'
```

### 9. DNodes Section

**Location in Excel:** Rows 180-200, Column 4

**Command:**
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/dnodes/" | jq -r '.[] | [.id, .name, .hostname, .guid, .cluster, .dbox_id, .dbox, .position, .os_version, .build, .state, .sync, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv'
```

## Excel Import Process

### Step-by-Step Instructions

1. **Open Excel File**
   - Open `092825-api-calls.xlsx`
   - Go to the "API-Summary" worksheet

2. **For Each Section:**
   - Find the "ADD CURL COMMANDS HERE" column
   - Run the appropriate curl command
   - Copy the output
   - Paste into the first empty cell in that column

3. **Format the Data:**
   - Select the pasted data
   - Go to Data → Text to Columns
   - Choose "Delimited"
   - Select "Comma" as delimiter
   - Click "Finish"

4. **Repeat for All Sections**
   - Use the section mapping above
   - Each section has its specific curl command
   - Data will be properly formatted for Excel

## Troubleshooting

### SSL Certificate Issues
If you get SSL errors, add the `-k` flag (already included in commands above):
```bash
curl -k -u "admin:password" "https://10.143.11.204/api/v7/clusters/" | jq -r '...'
```

### Missing jq Command
Install jq if not available:
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq
```

### Authentication Issues
- Use the improved authentication sequence from the main application
- Check that credentials are correct
- Verify cluster IP address is accessible

## Expected Results

After running all commands and importing into Excel, you should have:

- ✅ **Cluster Information**: Complete cluster details, state, capacity, and encryption info
- ✅ **Network Configuration**: Cluster, CNode, and DNode network settings
- ✅ **Hardware Inventory**: CBoxes, CNodes, DBoxes, DTrays, and DNodes
- ✅ **Rack Positioning**: U-number assignments for all hardware
- ✅ **PSNT Integration**: Product Serial Number Tracking data

## Files Created

The process will create these CSV files for easy reference:
- `cluster_basic.csv` - Basic cluster information
- `cluster_state.csv` - Cluster state and configuration
- `cluster_capacity.csv` - Storage capacity information
- `cluster_encryption.csv` - Encryption configuration
- `network_cluster.csv` - Cluster network settings
- `network_cnodes.csv` - CNode network settings
- `network_dnodes.csv` - DNode network settings
- `cboxes.csv` - CBox hardware information
- `cnodes.csv` - CNode hardware information
- `dboxes.csv` - DBox hardware information
- `dtrays.csv` - DTray hardware information
- `dnodes.csv` - DNode hardware information

## Next Steps

1. **Run the curl commands** for your specific cluster
2. **Import the data** into Excel using the instructions above
3. **Verify the data** matches your cluster configuration
4. **Update the report generator** with any new fields discovered
5. **Generate the final report** using the populated data

This approach ensures you get exactly the data you need for each report section, formatted perfectly for Excel import and review.
