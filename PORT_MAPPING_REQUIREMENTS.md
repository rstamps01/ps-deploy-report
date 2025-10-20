# Port Mapping Table Requirements Analysis

**Date**: October 20, 2025
**Purpose**: Define requirements for comprehensive switch port-to-device mapping
**Target**: Enhanced Switch Configuration section in As-Built Report

---

## 🎯 Objective

Create a detailed port mapping table that identifies which switch ports connect to:
- **CNodes** (Compute nodes)
- **DNodes** (Data nodes)
- **IPLs** (Inter-Peer Links between switches)
- **MLAGs** (Multi-Chassis Link Aggregation Groups)
- **Uplinks** (Spine/Core connections)
- **Unused Ports**

---

## ✅ Currently Available Data

### **From `/api/v1/ports/` Endpoint**
✅ **Port Name**: `swp1`, `swp2`, etc.
✅ **Port State**: `up` or `down`
✅ **Port Speed**: `200G`, `100G`, or `null` (unconfigured)
✅ **MTU**: `9216` (jumbo frames)
✅ **Parent Switch**: Which switch the port belongs to

**Example**:
```json
{
  "id": 1,
  "name": "swp1",
  "state": "up",
  "speed": "200G",
  "mtu": "9216",
  "switch": "se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)"
}
```

### **From `/api/v7/cnodes/` Endpoint**
✅ **CNode ID**: `1`, `2`
✅ **CNode Name**: `cnode-3-4`, `cnode-3-5`
✅ **CNode IP**: `172.16.3.4`, `172.16.3.5`
✅ **Serial Number**: `S929986X4A20495`
✅ **Hardware Model**: `supermicro_gen5_cbox, two dual-port NICs`

### **From `/api/v7/dnodes/` Endpoint**
✅ **DNode ID**: `1`, `2`
✅ **DNode Name**: `dnode-3-104`, `dnode-3-105`
✅ **DNode IPs**: `ip`, `ip1`, `ip2` (multiple data plane IPs)
✅ **Serial Number**: `C15-25032600200322`

### **From `/api/v1/switches/` Endpoint**
✅ **Switch Hostname**: `se-var-1-1`, `se-var-1-2`
✅ **Management IP**: `10.143.11.153`, `10.143.11.154`
✅ **Switch Model**: `MSN3700-VS2FC`
✅ **Serial Number**: `MT2450J01JQ7`
✅ **Firmware Version**: `5.13.1.1001`

---

## ❌ Missing Data Required for Port Mapping

### **Critical Missing Information**

#### 1. **Port-to-Device MAC Address Mapping**
❌ **What's Missing**: Which MAC address is learned on each switch port
❌ **Why It's Needed**: To identify which device is connected to each port
❌ **Typical Source**: Switch MAC address table (FDB - Forwarding Database)
❌ **VAST API**: Not exposed in current `/api/v1/ports/` or `/api/v1/switches/`

**Expected Data Structure**:
```json
{
  "port": "swp1",
  "mac_addresses": ["00:11:22:33:44:55"],
  "vlan": 100
}
```

#### 2. **LLDP Neighbor Discovery**
❌ **What's Missing**: LLDP neighbor information (directly connected devices)
❌ **Why It's Needed**: To identify device name, type, and interface connected to each port
❌ **Typical Source**: LLDP/CDP tables on switches
❌ **VAST API**: Not exposed via API

**Expected Data Structure**:
```json
{
  "local_port": "swp1",
  "neighbor_hostname": "cnode-3-4",
  "neighbor_interface": "eth0",
  "neighbor_mac": "00:11:22:33:44:55",
  "neighbor_ip": "172.16.3.4"
}
```

#### 3. **CNode/DNode Network Interface Details**
❌ **What's Missing**: MAC addresses of CNode/DNode network interfaces
❌ **Why It's Needed**: To correlate switch port MAC tables with specific nodes
❌ **Typical Source**: Node network interface configuration
❌ **VAST API**: Not exposed in `/api/v7/cnodes/` or `/api/v7/dnodes/`

**Expected Data Structure**:
```json
{
  "node": "cnode-3-4",
  "interfaces": [
    {"name": "eth0", "mac": "00:11:22:33:44:55", "ip": "172.16.3.4"},
    {"name": "eth1", "mac": "00:11:22:33:44:56", "ip": "172.16.2.4"}
  ]
}
```

#### 4. **Bond/LAG Configuration**
❌ **What's Missing**: Which ports are bonded together (MLAG, LAG, Port-Channel)
❌ **Why It's Needed**: To identify IPLs, peer links, and aggregated uplinks
❌ **Typical Source**: Switch bond/lag configuration
❌ **VAST API**: Not exposed via API

**Expected Data Structure**:
```json
{
  "bond_name": "bond0",
  "bond_type": "MLAG",
  "member_ports": ["swp1", "swp2"],
  "peer_switch": "se-var-1-2",
  "peer_ports": ["swp1", "swp2"]
}
```

#### 5. **IPL Identification**
❌ **What's Missing**: Which ports are Inter-Peer Links (IPLs) between MLAG switches
❌ **Why It's Needed**: To identify switch interconnect topology
❌ **Typical Source**: Switch MLAG configuration
❌ **VAST API**: Not exposed via API

**Typical Pattern**: Ports like `swp29-32` connecting two switches directly

#### 6. **Spine/Leaf Uplink Identification**
❌ **What's Missing**: Which ports connect leaf switches to spine switches
❌ **Why It's Needed**: To document network fabric topology
❌ **Typical Source**: Network topology configuration or LLDP
❌ **VAST API**: Not exposed via API

---

## 🔍 Potential Data Collection Methods

### **Option 1: Enhanced VAST API** (Requires VAST Engineering)
Request VAST to expose additional API endpoints:
- `/api/v1/ports/{port_id}/mac_table` - MAC addresses learned on each port
- `/api/v1/ports/{port_id}/lldp_neighbors` - LLDP neighbor information
- `/api/v7/cnodes/{node_id}/network_interfaces` - CNode MAC addresses
- `/api/v7/dnodes/{node_id}/network_interfaces` - DNode MAC addresses
- `/api/v1/switches/{switch_id}/bonds` - Bond/LAG configuration

### **Option 2: Direct Switch Access via SSH** (Cumulus Linux)
If VAST allows direct switch SSH access:

```bash
# Get LLDP neighbors
ssh cumulus@<switch-ip> 'sudo lldpctl -f json'

# Get MAC address table
ssh cumulus@<switch-ip> 'sudo bridge fdb show'

# Get bond configuration
ssh cumulus@<switch-ip> 'cat /etc/network/interfaces'

# Get port channel info
ssh cumulus@<switch-ip> 'sudo clagctl'
```

### **Option 3: Manual Documentation**
During cluster deployment, document:
- Physical cable connections (port-to-device mapping)
- MLAG peer link configuration
- IPL port assignments
- Uplink port assignments

Store in configuration file or database accessible by report generator.

### **Option 4: Inference from Available Data** (Limited)
Make educated guesses based on port patterns:

**Port Speed-Based Inference**:
- **200G ports** (swp1-28): Likely CNode/DNode data plane connections
- **100G ports** (swp29-32): Likely IPLs, uplinks, or management
- **Unconfigured ports**: Unused or reserved

**IP Address Correlation** (Partial):
- Match CNode/DNode IPs to switch management network
- Requires ARP table from switches (not available via API)

**Naming Pattern Analysis**:
- Switch naming: `se-var-1-1`, `se-var-1-2` → MLAG pair
- CNode naming: `cnode-3-4`, `cnode-3-5` → Rack 3, sequential
- DNode naming: `dnode-3-104`, `dnode-3-105` → Rack 3, sequential

---

## 📊 Proposed Port Mapping Table (Target Format)

### **Table Structure**

| Switch | Port | Speed | State | Connected To | Device Type | Device IP | MAC Address | Purpose |
|--------|------|-------|-------|--------------|-------------|-----------|-------------|---------|
| se-var-1-1 | swp1 | 200G | up | cnode-3-4 | CNode | 172.16.3.4 | 00:11:22:33:44:55 | Data Plane |
| se-var-1-1 | swp2 | 200G | up | cnode-3-4 | CNode | 172.16.2.4 | 00:11:22:33:44:56 | Data Plane |
| se-var-1-1 | swp3 | null | up | dnode-3-104 | DNode | 172.16.3.104 | 00:11:22:33:44:57 | Data Plane |
| se-var-1-1 | swp29 | 100G | up | se-var-1-2 | Switch | 10.143.11.154 | 00:11:22:33:44:AA | IPL |
| se-var-1-1 | swp30 | 100G | up | se-var-1-2 | Switch | 10.143.11.154 | 00:11:22:33:44:AB | IPL |
| se-var-1-1 | swp31 | 100G | up | spine-switch-1 | Uplink | 10.143.11.200 | 00:11:22:33:44:FF | Spine Uplink |
| se-var-1-1 | swp32 | 100G | up | spine-switch-2 | Uplink | 10.143.11.201 | 00:11:22:33:44:FE | Spine Uplink |

### **Color-Coded Purpose Legend**
- 🟦 **CNode Data Plane**: Ports connected to compute nodes
- 🟪 **DNode Data Plane**: Ports connected to data nodes
- 🟨 **IPL**: Inter-Peer Link between MLAG switches
- 🟩 **Uplink**: Connections to spine/core switches
- ⬜ **Unused**: Unconfigured or disconnected ports

---

## 🎯 Recommendations

### **Phase 1: Current Capabilities** (Immediate)
✅ **Report Basic Port Inventory**:
- List all ports by switch
- Show port speed, state, MTU
- Group by configured speed (200G, 100G, unconfigured)
- Flag potentially unused ports

**Value**: Provides foundation for troubleshooting and capacity planning
**Limitation**: No device-to-port correlation

---

### **Phase 2: Inference-Based Mapping** (Short-Term)
⚠️ **Add Intelligent Port Classification**:
- **200G ports**: Label as "Data Plane (CNode/DNode)"
- **100G ports swp29-30**: Label as "Likely IPL"
- **100G ports swp31-32**: Label as "Likely Uplink"
- **Unconfigured ports**: Label as "Unused/Reserved"

**Value**: Provides educated guesses useful for planning
**Limitation**: Not definitive, requires manual verification

**Example Report Section**:
```
Port Classification (Inferred):
- Ports swp1-28 (200G): Data Plane Connections
- Ports swp29-30 (100G): Inter-Peer Links (IPL)
- Ports swp31-32 (100G): Spine Uplinks
- Ports swp3,4,7,8,etc (null): Unused/Reserved
```

---

### **Phase 3: Manual Configuration File** (Medium-Term)
📝 **Create Deployment Configuration File**:

**File**: `config/port_mapping.yaml`
```yaml
switches:
  se-var-1-1:
    ports:
      swp1:
        connected_to: cnode-3-4
        interface: eth0
        purpose: data_plane
      swp2:
        connected_to: cnode-3-4
        interface: eth1
        purpose: data_plane
      swp29:
        connected_to: se-var-1-2
        interface: swp29
        purpose: ipl
      swp31:
        connected_to: spine-1
        interface: swp1
        purpose: uplink
```

Report generator reads this file and merges with API data.

**Value**: Accurate, complete port mapping
**Limitation**: Requires manual documentation during deployment

---

### **Phase 4: API Enhancement Request** (Long-Term)
🚀 **Request VAST Engineering to Expose**:
1. MAC address tables per port
2. LLDP neighbor information
3. Node network interface MAC addresses
4. Bond/LAG configuration
5. MLAG peer link identification

**Value**: Fully automated, always accurate port mapping
**Limitation**: Requires VAST product enhancement

---

## 📋 Implementation Priority

### **Priority 1: Basic Port Inventory** ✅ **COMPLETE**
- Already implemented in report
- Shows port states, speeds, counts

### **Priority 2: Intelligent Classification** 🔶 **RECOMMENDED**
- Add inference logic to classify ports by purpose
- Low effort, medium value
- No new API calls required

### **Priority 3: Manual Configuration Support** 🔷 **OPTIONAL**
- Add support for `port_mapping.yaml` config file
- High effort, high value for detailed documentation
- Requires deployment team documentation workflow

### **Priority 4: API Enhancement** 🔵 **FUTURE**
- Engage VAST product team
- Request exposure of switch MAC tables and LLDP data
- Timeline depends on VAST engineering priorities

---

## 🎓 Technical Deep Dive: Why This Data Is Missing

### **VAST API Design Philosophy**
VAST's REST API is designed for:
- ✅ Cluster management and configuration
- ✅ Storage provisioning and monitoring
- ✅ Hardware health and status
- ❌ **NOT for** deep network topology discovery

### **Network Data Abstraction**
VAST abstracts low-level networking:
- Customers manage network fabric independently
- Switches may be customer-owned (not VAST-managed)
- VAST focuses on application-layer connectivity
- Network topology is deployment-specific

### **Security & Access Control**
Direct switch access may be restricted:
- Switches run Cumulus Linux (separate from VAST OS)
- SSH access may require separate credentials
- MAC/LLDP tables may contain sensitive network info

---

## 💡 Conclusion

### **Current State**
✅ We can report **switch inventory** and **port configuration**
✅ We can identify **port speeds** and **states**
❌ We **CANNOT** automatically map ports to specific devices without additional data

### **Recommended Approach**
1. ✅ **Keep current port inventory section** (already valuable)
2. 🔶 **Add intelligent port classification** (infer purpose from speed/pattern)
3. 📝 **Document option for manual port mapping file** (for detailed deployments)
4. 🚀 **Engage VAST for API enhancements** (long-term automation goal)

### **Workaround for Immediate Need**
If a specific customer requires detailed port mapping:
1. Perform physical audit during deployment
2. Document in `port_mapping.yaml` configuration file
3. Report generator merges manual config with API data
4. Deliver comprehensive port map in report

---

**Document Status**: ✅ Analysis Complete
**Next Steps**: Review with user to determine priority for implementation
**Questions**: Should we implement Phase 2 (inference) or Phase 3 (manual config)?
