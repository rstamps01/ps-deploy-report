# Switches API Analysis: `/api/v1/switches/`

**Date**: October 20, 2025  
**Cluster**: 10.143.11.202  
**API Endpoint**: `/api/v1/switches/`  
**Status**: ✅ Successfully Retrieved  

---

## 📊 Executive Summary

The `/api/v1/switches/` endpoint provides comprehensive switch-level information including management IPs, firmware versions, switch types, hostnames, and configuration status. This endpoint is superior to the `/api/v1/ports/` endpoint for getting switch metadata.

**Key Findings**:
- **2 switches detected** (same as ports endpoint)
- **Firmware version available**: 5.13.1.1001 (both switches)
- **Management IP addresses**: 10.143.11.153, 10.143.11.154
- **Switch type**: Cumulus Linux
- **Configuration status**: Mixed (one configured, one not)
- **Model**: Mellanox MSN3700-VS2FC

---

## 🔍 Available Data Points (Per Switch)

| Field | Description | Example | Availability | Notes |
|-------|-------------|---------|--------------|-------|
| **Basic Info** |
| `id` | Unique switch identifier | `3` | ✅ Always | Internal ID |
| `guid` | Globally unique identifier | `0bdab119-e1c9-461f-bd3f-30fd87560b69` | ✅ Always | UUID format |
| `name` | Full switch name | `se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)` | ✅ Always | Includes hostname, model, serial |
| `hostname` | Switch hostname | `se-var-1-1` | ✅ Always | Short name |
| `display_name` | Display name | `se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)` | ✅ Always | Same as name |
| `title` | Switch title | `se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)` | ✅ Always | Same as name |
| **Hardware Info** |
| `model` | Switch model | `MSN3700-VS2FC` | ✅ Always | Mellanox model |
| `sn` | Serial number | `MT2450J01JQ7` | ✅ Always | Hardware serial |
| `state` | Operational state | `OK` | ✅ Always | OK, ERROR, etc. |
| **Network Info** |
| `ip` | IP address | `10.143.11.153` | ✅ Always | Switch IP |
| `mgmt_ip` | Management IP | `10.143.11.153` | ✅ Always | Same as ip |
| `ipv6` | IPv6 address | `null` | ❌ Not configured | IPv6 support |
| `mgmt_subnet` | Management subnet | `null` | ❌ Not configured | Subnet mask |
| `mgmt_gateway` | Management gateway | `null` | ❌ Not configured | Default gateway |
| `mtu` | MTU setting | `null` | ❌ Not configured | Port MTU |
| **Firmware & Software** |
| `fw_version` | Firmware version | `5.13.1.1001` | ✅ Always | Cumulus version |
| `switch_type` | Switch OS type | `cumulus` | ✅ Always | Cumulus Linux |
| **Configuration** |
| `configured` | Configuration status | `true`/`false` | ✅ Always | Setup complete |
| `username` | Login username | `cumulus` | ✅ Always | Admin user |
| `password` | Password (masked) | `*********` | ✅ Always | Masked in API |
| `install` | Install flag | `true` | ✅ Always | Installation status |
| **Role & Clustering** |
| `role` | Switch role | `switch` | ⚠️ Partial | May be null |
| `cluster` | Associated cluster | `null` | ❌ Not set | Cluster association |
| `cluster_id` | Cluster ID | `null` | ❌ Not set | Cluster reference |
| `peer_switch` | MLAG peer switch | `null` | ❌ Not configured | MLAG pairing |
| `pair_id` | MLAG pair ID | `null` | ❌ Not configured | Pair identifier |
| `switch_id` | Switch identifier | `null` | ❌ Not set | Additional ID |
| `configuration_file` | Config file path | `null` | ❌ Not set | Configuration reference |

---

## 📊 Comparison: Switches vs Ports Endpoint

### **What Ports Endpoint Provides** (`/api/v1/ports/`)
- ✅ Individual port details (64 ports)
- ✅ Port names (swp1, swp2, etc.)
- ✅ Port states (up/down)
- ✅ Port speeds (100G, 200G)
- ✅ Port MTU values
- ❌ No firmware version
- ❌ No management IP
- ❌ No switch-level state

### **What Switches Endpoint Provides** (`/api/v1/switches/`)
- ✅ Switch-level metadata
- ✅ Firmware version
- ✅ Management IP addresses
- ✅ Configuration status
- ✅ Switch type/OS
- ✅ Hostnames
- ✅ Overall switch state
- ❌ No individual port details
- ❌ No port-level statistics

### **Recommendation**: Use **BOTH** endpoints
- Use `/api/v1/switches/` for switch metadata
- Use `/api/v1/ports/` for port-level details

---

## 📋 Detailed Switch Data

### **Switch 1: se-var-1-1**

```json
{
    "id": 3,
    "hostname": "se-var-1-1",
    "model": "MSN3700-VS2FC",
    "sn": "MT2450J01JQ7",
    "state": "OK",
    "fw_version": "5.13.1.1001",
    "mgmt_ip": "10.143.11.153",
    "switch_type": "cumulus",
    "configured": true,
    "role": "switch"
}
```

**Status**: ✅ Fully configured and operational

---

### **Switch 2: se-var-1-2**

```json
{
    "id": 7,
    "hostname": "se-var-1-2",
    "model": "MSN3700-VS2FC",
    "sn": "MT2450J01JPY",
    "state": "OK",
    "fw_version": "5.13.1.1001",
    "mgmt_ip": "10.143.11.154",
    "switch_type": "cumulus",
    "configured": false,
    "role": null
}
```

**Status**: ⚠️ Not configured (configured: false, role: null)

---

## 🎯 Value for As-Built Report

### **New Data Available** (Not in Ports Endpoint):

1. **Firmware Version**: `5.13.1.1001`
   - Critical for documentation
   - Needed for compliance and support
   - Version tracking for upgrades

2. **Management IP Addresses**: `10.143.11.153`, `10.143.11.154`
   - Essential for remote management
   - Troubleshooting access
   - Network documentation

3. **Configuration Status**: `configured: true/false`
   - Shows setup completion
   - Identifies potential issues
   - Deployment validation

4. **Switch Type**: `cumulus`
   - Operating system information
   - Management method (Cumulus Linux)
   - Configuration approach

5. **Operational State**: `OK`
   - High-level health indicator
   - Different from port-level state
   - Overall switch status

---

## 📈 Recommended Report Enhancements

### **Current Switch Configuration Section**:
```
Switch 1 Details
  se-var-1-1 Configuration
    - Switch Name: se-var-1-1
    - Model: MSN3700-VS2FC
    - Serial Number: MT2450J01JQ7
    - Total Ports: 32
    - Active Ports: 32
    - MTU: 9216
```

### **Enhanced Switch Configuration Section**:
```
Switch 1 Details
  se-var-1-1 Configuration
    - Switch Name: se-var-1-1
    - Hostname: se-var-1-1                  ← NEW
    - Model: MSN3700-VS2FC
    - Serial Number: MT2450J01JQ7
    - Firmware Version: 5.13.1.1001         ← NEW
    - Management IP: 10.143.11.153          ← NEW
    - Switch Type: Cumulus Linux            ← NEW
    - State: OK                             ← NEW
    - Configuration Status: Configured      ← NEW
    - Total Ports: 32
    - Active Ports: 32
    - Port MTU: 9216
```

---

## 🔧 Implementation Recommendations

### **1. Update API Handler** (`src/api_handler.py`)

Add new method:
```python
def get_switches_detail(self) -> List[Dict[str, Any]]:
    """
    Get detailed switch information from VAST cluster.
    
    Returns:
        List[Dict[str, Any]]: List of switches with detailed info
    """
    try:
        self.logger.info("Collecting detailed switch information")
        
        base_url = f"https://{self.cluster_ip}/api/v1"
        switches_url = f"{base_url}/switches/"
        
        response = self.session.get(
            switches_url,
            verify=False,
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            switches_data = response.json()
            if switches_data:
                self.logger.info(f"Retrieved {len(switches_data)} switch details")
                return switches_data
            else:
                self.logger.warning("No switch detail data available")
                return []
        else:
            self.logger.warning(f"Failed to retrieve switches: HTTP {response.status_code}")
            return []
            
    except Exception as e:
        self.logger.error(f"Error collecting switch details: {e}")
        return []
```

### **2. Merge Switches and Ports Data**

Combine data from both endpoints:
```python
def get_switch_inventory(self) -> Dict[str, Any]:
    # Get detailed switch info
    switches_detail = self.get_switches_detail()
    
    # Get port info
    ports_data = self.get_switch_ports()
    
    # Merge data by matching serial numbers or hostnames
    # Add firmware, mgmt_ip, state, etc. to switch inventory
```

### **3. Update Report Builder**

Add new fields to switch configuration tables:
- Hostname
- Firmware Version
- Management IP
- Switch Type
- State
- Configuration Status

---

## 🐛 Observations & Notes

### **Configuration Status Discrepancy**:
- **Switch 1**: `configured: true`, `role: "switch"`
- **Switch 2**: `configured: false`, `role: null`

**Implications**:
- Switch 2 may not be fully set up
- Role assignment incomplete
- Possible deployment issue to investigate

### **MLAG Configuration**:
- Both switches show `peer_switch: null` and `pair_id: null`
- No MLAG pairing detected in API
- May be configured at switch level but not tracked by VAST

### **Network Fields Empty**:
- `mgmt_subnet`, `mgmt_gateway`, `ipv6` all null
- Basic management working (has mgmt_ip)
- Additional network config may be needed

### **Switch Name Format**:
- Switch 1: `"se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)"`
- Switch 2: `"se-var-1-2: -MSN3700-VS2FC (MT2450J01JPY)"`
- Note: Switch 2 has `-MSN` instead of `switch-MSN`
- Parsing logic should handle both formats

---

## ✅ Summary & Recommendations

### **Key Findings**:
1. ✅ `/api/v1/switches/` provides rich switch metadata
2. ✅ Firmware version available (5.13.1.1001)
3. ✅ Management IPs available (10.143.11.153, 10.143.11.154)
4. ✅ Configuration status trackable
5. ⚠️ One switch shows as "not configured"

### **Recommended Actions**:
1. **Implement** `/api/v1/switches/` collection in API handler
2. **Merge** switches and ports data for complete view
3. **Enhance** report with firmware version and management IPs
4. **Add** configuration status indicators
5. **Document** switch type (Cumulus Linux)
6. **Investigate** why Switch 2 shows as not configured

### **Report Improvements**:
- **Priority**: Add firmware version and management IP (high value, low effort)
- **Configuration Status**: Show configured/not configured
- **Switch State**: Add overall state indicator
- **Switch Type**: Document OS/management method

---

**Status**: ✅ **Analysis Complete - Ready for Implementation**  
**Impact**: High value addition to switch documentation  
**Effort**: Low (single API endpoint, straightforward data merge)

