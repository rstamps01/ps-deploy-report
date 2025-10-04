# 🚀 Autonomous Excel Populator Guide

## Overview

The Autonomous Excel Populator systematically generates filtered API calls to populate the Excel spreadsheet with real data from your VAST cluster. It includes curl commands for easy testing and troubleshooting.

## 🎯 Features

- **Systematic Data Collection**: Automatically collects all required data sections
- **Curl Commands Integration**: Each data section includes its corresponding curl command
- **Excel Output**: Creates comprehensive Excel files with multiple sheets
- **CSV Export**: Generates individual CSV files for each data section
- **Testing Tools**: Includes curl command tester for validation
- **Troubleshooting**: Easy identification of API call issues

## 📋 Prerequisites

```bash
# Install required packages
pip install pandas openpyxl

# Ensure you have jq installed for curl commands
# macOS: brew install jq
# Ubuntu: sudo apt-get install jq
```

## 🚀 Quick Start

### 1. Run the Autonomous Populator

```bash
# Using your token
python3 autonomous_excel_populator.py 10.143.11.204 PILpmpLs.SyIMdS1Z67NxEmCXDYU0l09sRdakLZs3

# Using username/password
python3 autonomous_excel_populator.py 10.143.11.204 "" admin 123456
```

### 2. Generated Files

The script creates several files in the `excel_data/` directory:

- **`vast_data_summary_YYYYMMDD_HHMMSS.xlsx`** - Main Excel file with all data
- **`curl_commands_YYYYMMDD_HHMMSS.txt`** - All curl commands in text format
- **`vast_data_raw_YYYYMMDD_HHMMSS.json`** - Raw JSON data
- **Individual CSV files** for each data section

## 📊 Excel File Structure

### Sheet 1: Cluster_Basic_Info
- Basic cluster information (name, version, state, etc.)
- **Includes curl command** for testing

### Sheet 2: Cluster_State_Info
- Detailed cluster state and configuration
- **Includes curl command** for testing

### Sheet 3: Cluster_Capacity_Info
- Capacity and utilization metrics
- **Includes curl command** for testing

### Sheet 4: Cluster_Encryption_Info
- Encryption configuration
- **Includes curl command** for testing

### Sheet 5: CNodes_Info
- Control node hardware details
- **Includes curl command** for testing

### Sheet 6: DNodes_Info
- Data node hardware details
- **Includes curl command** for testing

### Sheet 7: Network_Info
- Network configuration (cluster, cnode, dnode)
- **Includes curl commands** for all network types

### Sheet 8: Curl_Commands
- **Dedicated sheet with all curl commands**
- Test status and notes for each command
- Easy copy-paste for testing

## 🧪 Testing Curl Commands

### Test All Commands
```bash
python3 curl_command_tester.py vast_data_summary_20250929_123456.xlsx
```

### Test Individual Section
```bash
python3 curl_command_tester.py vast_data_summary_20250929_123456.xlsx "Cluster Basic Info"
```

### Manual Testing
Copy any curl command from the Excel file and run it directly:

```bash
curl -k -H 'Authorization: Api-Token YOUR_TOKEN' 'https://10.143.11.204/api/v1/clusters/' | jq -r '.[0] | [.name, .guid, .version, .state, .psnt, .uptime, .build, .license] | @csv'
```

## 🔧 Troubleshooting

### Common Issues

1. **SSL Certificate Errors**
   - Commands include `-k` flag to bypass SSL verification
   - For production, install proper certificates

2. **Authentication Failures**
   - Verify your token is valid and not expired
   - Check cluster IP address

3. **API Endpoint Not Found**
   - Some endpoints may not be available in all API versions
   - Check the test report for specific errors

4. **jq Command Not Found**
   - Install jq: `brew install jq` (macOS) or `sudo apt-get install jq` (Ubuntu)

### Debugging Steps

1. **Check Authentication**
   ```bash
   curl -k -H 'Authorization: Api-Token YOUR_TOKEN' 'https://10.143.11.204/api/v1/clusters/'
   ```

2. **Test Without jq**
   ```bash
   curl -k -H 'Authorization: Api-Token YOUR_TOKEN' 'https://10.143.11.204/api/v1/clusters/'
   ```

3. **Check API Version**
   ```bash
   curl -k -H 'Authorization: Api-Token YOUR_TOKEN' 'https://10.143.11.204/api/v1/'
   ```

## 📈 Data Sections Covered

| Section | API Endpoint | Description |
|---------|--------------|-------------|
| Cluster Basic Info | `/api/v1/clusters/` | Name, version, state, PSNT |
| Cluster State Info | `/api/v1/clusters/` | RAID states, leadership, features |
| Cluster Capacity Info | `/api/v1/clusters/` | Capacity metrics, utilization |
| Cluster Encryption Info | `/api/v1/encryption/` | Encryption configuration |
| CNodes Info | `/api/v1/cnodes/` | Control node hardware |
| DNodes Info | `/api/v1/dnodes/` | Data node hardware |
| Cluster Network | `/api/v1/cluster_network/` | Cluster network config |
| CNode Network | `/api/v1/cnode_network/` | Control node network |
| DNode Network | `/api/v1/dnode_network/` | Data node network |

## 🎯 Benefits

1. **Systematic Approach**: Covers all required data sections
2. **Easy Testing**: Curl commands ready for copy-paste testing
3. **Troubleshooting**: Clear identification of API issues
4. **Excel Integration**: Data ready for spreadsheet import
5. **Automation**: No manual API call construction needed
6. **Validation**: Built-in testing tools for verification

## 📝 Usage Examples

### Generate Data for New Cluster
```bash
python3 autonomous_excel_populator.py 192.168.1.100 YOUR_TOKEN
```

### Test Specific API Section
```bash
python3 curl_command_tester.py vast_data_summary_20250929_123456.xlsx "CNodes Info"
```

### Generate Report with Data
```bash
# First generate Excel data
python3 autonomous_excel_populator.py 10.143.11.204 YOUR_TOKEN

# Then generate report
python3 src/main.py --cluster 10.143.11.204 --token YOUR_TOKEN --output ./reports --config config/test_config.yaml
```

## 🔄 Workflow

1. **Run Autonomous Populator** → Generates Excel with curl commands
2. **Test Curl Commands** → Validate API responses
3. **Review Data** → Check Excel sheets for completeness
4. **Generate Report** → Use data for final report generation
5. **Troubleshoot Issues** → Use curl commands to debug problems

## 🎉 Success Indicators

- ✅ All curl commands return valid CSV data
- ✅ Excel file contains all expected sheets
- ✅ Data completeness > 80% in each section
- ✅ No authentication or SSL errors
- ✅ All API endpoints responding correctly

**Your autonomous Excel population system is ready to use!** 🚀
