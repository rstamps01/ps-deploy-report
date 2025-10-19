# Switch Port API Analysis: `/api/v1/ports/`

**Date**: October 18, 2025  
**Cluster**: 10.143.11.202  
**API Endpoint**: `/api/v1/ports/`  
**Status**: ✅ Successfully Retrieved  

---

## 📊 Executive Summary

The `/api/v1/ports/` endpoint provides comprehensive information about **all switch ports** across all VAST-managed switches in the cluster. This is valuable data for network topology, connectivity mapping, and switch configuration documentation.

**Key Findings**:
- **2 switches detected** in this cluster
- **64 total ports** (32 ports per switch)
- All ports showing **"up" state** (fully operational)
- Mix of **100G and 200G** port speeds
- Standard **MTU of 9216** (jumbo frames enabled)
- Model: **Mellanox MSN3700-VS2FC** switches

---

## 🔍 Cluster Configuration

### **Detected Switches**

| Switch # | Name | Model | Serial Number | Total Ports |
|----------|------|-------|---------------|-------------|
| 1 | `se-var-1-1` | MSN3700-VS2FC | MT2450J01JQ7 | 32 |
| 2 | `se-var-1-2` | MSN3700-VS2FC | MT2450J01JPY | 32 |

**Switch Naming Pattern**: `se-var-1-[1-2]`

---

## 📋 Available Data Points (Per Port)

Each port entry provides the following information:

| Field | Description | Example | Availability |
|-------|-------------|---------|--------------|
| `id` | Unique port identifier | `1` | ✅ Always |
| `guid` | Globally unique identifier | `16e23ede-ad85-53ad-ab9e-346784fde5cc` | ✅ Always |
| `name` | Port name/number | `swp1` | ✅ Always |
| `state` | Port operational state | `up` | ✅ Always |
| `sn` | Port serial number | `null` | ❌ Not populated |
| `model` | Port type | `PORT` | ✅ Always (generic) |
| `cluster` | Associated cluster | `null` | ❌ Not populated |
| `title` | Port full title | `PORT Port swp1` | ✅ Always |
| `display_name` | Display name | `swp1` | ✅ Always |
| `fw_version` | Firmware version | `null` | ❌ Not populated |
| `cluster_id` | Cluster ID | `null` | ❌ Not populated |
| `switch` | Parent switch info | `se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)` | ✅ Always |
| `mtu` | Maximum transmission unit | `9216` | ✅ Always |
| `speed` | Port speed | `200G`, `100G`, or `null` | ⚠️ Partial |

---

## 🔌 Port Speed Distribution

### **Switch 1 (se-var-1-1: MT2450J01JQ7)**

| Speed | Port Count | Percentage | Port Numbers |
|-------|------------|------------|--------------|
| **200G** | 18 ports | 56% | swp1, 2, 5, 6, 9, 10, 13, 14, 17-21, 23, 24, 26-28 |
| **100G** | 4 ports | 13% | swp29-32 |
| **null** | 10 ports | 31% | swp3, 4, 7, 8, 11, 12, 15, 16, 22, 25 |

### **Switch 2 (se-var-1-2: MT2450J01JPY)**

| Speed | Port Count | Percentage | Port Numbers |
|-------|------------|------------|--------------|
| **200G** | 18 ports | 56% | swp1, 2, 5, 6, 9, 10, 13, 14, 17-21, 23, 24, 26-28 |
| **100G** | 4 ports | 13% | swp29-32 |
| **null** | 10 ports | 31% | swp3, 4, 7, 8, 11, 12, 15, 16, 22, 25 |

**Pattern**: Both switches have **identical port speed configurations** (likely MLAG pair)

---

## 🌐 Network Configuration Insights

### **MTU Configuration**
- ✅ All ports: **9216 bytes** (Jumbo frames enabled)
- Standard for VAST storage networks
- Optimal for high-throughput workloads

### **Port States**
- ✅ All 64 ports: **"up"** (operational)
- ❌ No ports down or disabled
- Indicates fully active/healthy network

### **Port Speed Observations**
1. **18 ports @ 200G** per switch (likely data plane connections)
2. **4 ports @ 100G** per switch (swp29-32, possibly uplinks or spine connections)
3. **10 ports with null speed** (may be unused or speed negotiation in progress)

---

## 📊 Example Port Entry (Detailed)

```json
{
    "id": 1,
    "guid": "16e23ede-ad85-53ad-ab9e-346784fde5cc",
    "name": "swp1",
    "state": "up",
    "sn": null,
    "model": "PORT",
    "cluster": null,
    "title": "PORT Port swp1",
    "display_name": "swp1",
    "fw_version": null,
    "cluster_id": null,
    "switch": "se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)",
    "mtu": "9216",
    "speed": "200G"
}
```

---

## 🎯 Use Cases for As-Built Report

### **1. Switch Inventory Section**
**Data Available**:
- ✅ Switch model: `MSN3700-VS2FC`
- ✅ Switch serial numbers: `MT2450J01JQ7`, `MT2450J01JPY`
- ✅ Switch names: `se-var-1-1`, `se-var-1-2`
- ✅ Total port count per switch: 32

**Report Addition**:
```
Hardware Overview:
  Switches: 2
  Switch Model: Mellanox MSN3700-VS2FC
```

### **2. Network Topology/Port Mapping**
**Data Available**:
- ✅ All port names (swp1-32)
- ✅ Port states (all up)
- ✅ Port speeds (100G/200G)
- ✅ MTU configuration

**Report Addition**:
- Network port status table
- Port speed distribution
- Active vs inactive ports

### **3. Switch Configuration Details**
**Data Available**:
- ✅ Total ports: 64 (32 per switch)
- ✅ Active ports: 64 (100%)
- ✅ Port speeds: Mixed 100G/200G
- ✅ MTU: 9216 (jumbo frames)

### **4. Connectivity Mapping**
**Potential Use**:
- Map CNode connections to switch ports
- Map DNode connections to switch ports
- Identify uplink ports (100G ports 29-32)
- Document MLAG pair configuration

---

## 🔧 Extraction Strategy

### **Switch-Level Summary**
```python
def extract_switch_inventory(ports_data):
    switches = {}
    for port in ports_data:
        switch_info = port.get("switch", "")
        # Parse: "se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)"
        # Extract: name, model, serial
        if switch_info not in switches:
            switches[switch_info] = {
                "ports": [],
                "port_count": 0,
                "active_ports": 0,
                "speeds": {}
            }
        switches[switch_info]["ports"].append(port)
        switches[switch_info]["port_count"] += 1
        if port.get("state") == "up":
            switches[switch_info]["active_ports"] += 1
        speed = port.get("speed", "unknown")
        switches[switch_info]["speeds"][speed] = \
            switches[switch_info]["speeds"].get(speed, 0) + 1
    return switches
```

### **Port-Level Details**
```python
def extract_port_details(ports_data):
    return [
        {
            "port_name": port.get("name"),
            "switch": parse_switch_name(port.get("switch")),
            "state": port.get("state"),
            "speed": port.get("speed", "Unknown"),
            "mtu": port.get("mtu")
        }
        for port in ports_data
    ]
```

---

## 📈 Report Integration Recommendations

### **Add to Hardware Overview**
```
Hardware Overview:
  CBoxes: 3
  CNodes: 3
  DBoxes: 2
  DNodes: 2
  Switches: 2          <-- ADD THIS
  Switch Model: Mellanox MSN3700-VS2FC  <-- ADD THIS
```

### **Add New Section: "Switch Inventory"**

**Table: Switch Configuration**

| Switch | Model | Serial Number | Total Ports | Active Ports | Status |
|--------|-------|---------------|-------------|--------------|--------|
| se-var-1-1 | MSN3700-VS2FC | MT2450J01JQ7 | 32 | 32 | HEALTHY |
| se-var-1-2 | MSN3700-VS2FC | MT2450J01JPY | 32 | 32 | HEALTHY |

**Table: Port Speed Distribution**

| Switch | 200G Ports | 100G Ports | Unconfigured | MTU |
|--------|------------|------------|--------------|-----|
| se-var-1-1 | 18 | 4 | 10 | 9216 |
| se-var-1-2 | 18 | 4 | 10 | 9216 |

### **Add to Network Configuration Section**
```
Network Configuration:
  MTU: 9216 bytes (Jumbo Frames)
  Switch Interconnect: MLAG (dual switch design)
  Port Configuration: Mixed 100G/200G
  Total Network Ports: 64 (32 per switch)
  Active Ports: 64 (100% uptime)
```

---

## ⚠️ Limitations & Notes

### **Missing Data**
- ❌ **Port serial numbers**: All `null`
- ❌ **Firmware version**: All `null`
- ❌ **Cluster association**: All `null`
- ⚠️ **Port speed**: 31% of ports show `null` (may be unused or negotiating)

### **API Observations**
1. **Generic model type**: All ports show `model: "PORT"` (not specific port type)
2. **Consistent formatting**: Switch field includes name, model, and serial
3. **No port-to-device mapping**: Cannot directly map which port connects to which CNode/DNode
4. **No VLAN info**: Port VLAN assignments not in this endpoint

### **Switch Model Info**
- **MSN3700-VS2FC**: Mellanox Spectrum-2 based switch
- **32 ports**: QSFP28/QSFP56 (supports 100G/200G)
- **VAST Validated**: Standard VAST switch model

---

## 🎯 Data Completeness Impact

### **Current Missing Data (from previous analysis)**
This API endpoint can help address:

✅ **Customer Integration** section:
- Network topology (switch model, count)
- Active port inventory

✅ **Performance Metrics** (partial):
- Port speed capabilities
- Network fabric configuration

**Estimated Completeness Improvement**: +1-2%
- Adds switch hardware inventory
- Provides network port details
- Completes hardware summary section

---

## 🔄 Recommended API Integration

### **Add to `api_handler.py`**

```python
def get_switch_ports(self) -> List[Dict[str, Any]]:
    """
    Get switch port information.
    
    Returns:
        List[Dict[str, Any]]: List of all switch ports
    """
    try:
        self.logger.info("Collecting switch port information")
        ports_data = self._make_api_request("ports/")
        
        if ports_data:
            self.logger.info(f"Retrieved {len(ports_data)} port entries")
            return ports_data
        else:
            self.logger.warning("No switch port data available")
            return []
            
    except Exception as e:
        self.logger.error(f"Error collecting switch port data: {e}")
        return []

def get_switch_inventory(self) -> Dict[str, Any]:
    """
    Get aggregated switch inventory from port data.
    
    Returns:
        Dict[str, Any]: Switch inventory summary
    """
    try:
        ports_data = self.get_switch_ports()
        
        # Aggregate by switch
        switches = {}
        for port in ports_data:
            switch_str = port.get("switch", "")
            if switch_str not in switches:
                switches[switch_str] = {
                    "name": self._parse_switch_name(switch_str),
                    "model": self._parse_switch_model(switch_str),
                    "serial": self._parse_switch_serial(switch_str),
                    "total_ports": 0,
                    "active_ports": 0,
                    "port_speeds": {},
                    "mtu": port.get("mtu", "Unknown")
                }
            
            switches[switch_str]["total_ports"] += 1
            if port.get("state") == "up":
                switches[switch_str]["active_ports"] += 1
            
            speed = port.get("speed") or "unconfigured"
            switches[switch_str]["port_speeds"][speed] = \
                switches[switch_str]["port_speeds"].get(speed, 0) + 1
        
        return {
            "switch_count": len(switches),
            "switches": list(switches.values()),
            "total_ports": sum(s["total_ports"] for s in switches.values()),
            "total_active_ports": sum(s["active_ports"] for s in switches.values())
        }
        
    except Exception as e:
        self.logger.error(f"Error processing switch inventory: {e}")
        return {}
```

---

## ✅ Summary & Recommendations

### **What This API Provides**
✅ Complete switch inventory (model, serial numbers)  
✅ All port states and speeds  
✅ Network configuration (MTU, port count)  
✅ Switch health status (all ports up)  

### **Recommended Actions**
1. ✅ **Add to report**: Switch inventory section
2. ✅ **Enhance**: Hardware Overview with switch count
3. ✅ **Integrate**: Network configuration with port details
4. ⚠️ **Future**: Port-to-device mapping (requires additional API)

### **Report Impact**
- **Completeness**: +1-2% (fills switch inventory gap)
- **Value**: High (completes hardware inventory)
- **Complexity**: Low (simple data extraction)

---

**Status**: ✅ **Ready for integration into report generator**  
**Priority**: **Medium** (completes hardware inventory, not critical for MVP)  
**Effort**: **Low** (straightforward API, simple data extraction)

