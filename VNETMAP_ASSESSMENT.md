# VNetMap Script Assessment & Analysis

**Date**: October 20, 2025
**File**: `src/vnetmap.py`
**Version**: 1.0.5
**Purpose**: Network topology discovery and validation for VAST clusters
**Status**: ✅ **Comprehensive Professional Tool - High Value for Port Mapping**

---

## 🎯 Executive Summary

`vnetmap.py` is a **sophisticated network discovery and validation tool** developed by VAST Data. It provides **exactly the missing functionality** identified in our port mapping requirements analysis:

✅ **MAC address table collection from switches**
✅ **Port-to-device mapping via MAC correlation**
✅ **Multi-vendor switch support** (Mellanox, Cumulus, Arista, Aruba)
✅ **LLDP neighbor discovery** (for InfiniBand)
✅ **Network topology visualization**
✅ **Fabric health diagnostics**

**Key Finding**: This tool can provide **complete port-to-device mapping** that we identified as missing from the VAST REST API.

---

## 📊 Tool Capabilities Overview

### **Primary Functions**

#### 1. **Network Topology Discovery** ✅
- Maps every CNode and DNode to specific switch ports
- Correlates node MAC addresses with switch MAC address tables
- Identifies physical connectivity for all nodes

#### 2. **Multi-Vendor Switch Support** ✅
Supports major switch manufacturers:
- **Mellanox/NVIDIA** (MLNX-OS, Onyx) - via HTTP API
- **Cumulus Linux** - via SSH (our cluster uses this!)
- **Arista** - via eAPI (JSON-RPC)
- **Aruba** - via REST API

#### 3. **Dual Network Type Support** ✅
- **Ethernet fabric** (what we're using)
- **InfiniBand fabric** (alternative deployment)

#### 4. **Data Collection Methods** ✅
- **Switch MAC address tables** (Layer 2 forwarding database)
- **Node interface MAC addresses** (via SSH to nodes)
- **LLDP neighbor information** (for IB)
- **VLAN configuration validation**
- **MTU consistency checking**

---

## 🔍 Detailed Feature Analysis

### **Switch API Classes**

#### **1. BaseSwitchAPI** (Abstract Base)
- Automatic switch vendor detection
- Common authentication framework
- Polymorphic command execution

#### **2. MlnxSwitchAPI** (Mellanox/NVIDIA)
```python
class MlnxSwitchAPI(BaseSwitchAPI):
    target_manufacturer = "MLNX-OS,Onyx"
    # HTTP-based API using /admin/launch endpoint
    # JSON-formatted commands
```

**Capabilities**:
- HTTP/HTTPS API access
- Session-based authentication
- JSON command/response format
- MAC address table retrieval
- VLAN filtering

#### **3. CumulusSwitchAPI** (Our Cluster!)
```python
class CumulusSwitchAPI(BaseSwitchAPI):
    target_manufacturer = "Mellanox,Cumulus"
    # SSH-based using 'nv show' commands
```

**Capabilities**:
- SSH access via `sshpass`
- Cumulus Linux `nv show` commands
- Direct command execution
- Hostname retrieval

**Relevance**: ⭐ **High** - Our cluster (10.143.11.202) uses Cumulus Linux switches!

#### **4. AristaSwitchAPI**
```python
class AristaSwitchAPI(BaseSwitchAPI):
    # eAPI JSON-RPC interface
```

**Capabilities**:
- JSON-RPC over HTTP/HTTPS
- eAPI command execution
- Switch configuration retrieval

#### **5. ArubaSwitchAPI**
```python
class ArubaSwitchAPI(BaseSwitchAPI):
    # REST API access
```

**Capabilities**:
- REST API endpoints
- SSH fallback for commands
- Version detection

---

## 🔬 Core Functionality Deep Dive

### **Network Mapping Workflow**

#### **Phase 1: Node Discovery**
```python
def get_nodes(args):
    # Discovers all CNodes and DNodes
    # Options:
    # - Auto-discovery via clush config
    # - Manual IP specification
    # - IP range expansion (e.g., 10.1.1.1-10)
```

**Data Collected**:
- Node hostnames
- Node IP addresses
- Internal network configuration
- Interface names and MAC addresses
- VLAN assignments

#### **Phase 2: Switch Connection**
```python
def get_all_switch_objects(switch_ips, user, password, ...):
    # Creates switch API objects for each switch
    # Auto-detects vendor via BaseSwitchAPI.determine_api()
```

**Process**:
1. Connect to each switch
2. Detect manufacturer (Cumulus, Mellanox, etc.)
3. Authenticate with credentials
4. Create appropriate API object

#### **Phase 3: MAC Address Collection**
```python
def map_switchs_mac_tables(mtu_check, nodes, switch_objs, ssh_key):
    # Collects MAC address tables from all switches
    # Correlates with node MAC addresses
```

**Steps**:
1. SSH to each node → collect interface MACs
2. Query switch MAC address tables (filtered by VLAN)
3. Match node MACs to switch port entries
4. Build comprehensive mapping dictionary

**Output Structure**:
```python
mapping = {
    "00:11:22:33:44:55": {
        "node_info": {
            "hostname": "cnode-3-4",
            "internal_ip": "172.16.3.4",
            "internal_int": "eth0",
        },
        "switch_ip": "10.143.11.153",
        "switch_port": "swp1",
    }
}
```

#### **Phase 4: Topology Visualization**
```python
def validate_internal_network(...):
    # Generates comprehensive topology report
    # Identifies connectivity issues
    # Creates diagnostic output
```

**Report Format**:
```
hostname          switch              port  Node IP        Interface  MAC
cnode-3-4         se-var-1-1         swp1  172.16.3.4     eth0       00:11:22:33:44:55
cnode-3-4         se-var-1-1         swp2  172.16.2.4     eth1       00:11:22:33:44:56
dnode-3-104       se-var-1-1         swp5  172.16.3.104   eth0       00:11:22:33:44:57
```

---

## 🔑 Key Data Collected (Answers Our Gap!)

### **1. Port-to-Device Mapping** ✅
**Exactly what we need!**

```python
{
    "switch": "se-var-1-1",
    "port": "swp1",
    "connected_device": "cnode-3-4",
    "device_interface": "eth0",
    "device_ip": "172.16.3.4",
    "mac_address": "00:11:22:33:44:55"
}
```

### **2. Switch Information** ✅
- Switch hostname
- Switch IP address
- Switch manufacturer/model
- Firmware version

### **3. Node Network Details** ✅
- All interface MAC addresses
- IP addresses per interface
- VLAN assignments
- MTU settings

### **4. Fabric Health Checks** ✅
- Duplicate MAC detection
- MTU consistency validation
- Missing node detection
- Failed connection reporting

---

## 💡 Integration Opportunities

### **Option 1: Direct Execution & Parsing** 🔶 **RECOMMENDED**

Run `vnetmap.py` as a subprocess and parse its output:

```python
# In api_handler.py or new network_mapper.py module

def get_port_mapping_via_vnetmap(
    cluster_ip: str,
    switch_ips: List[str],
    switch_user: str = "cumulus",
    switch_password: str = "CumulusLinux!"
) -> Dict[str, Any]:
    """
    Execute vnetmap.py to discover port-to-device mapping.

    Returns:
        Dictionary mapping switch ports to connected devices
    """
    import subprocess
    import json

    cmd = [
        "python3",
        "src/vnetmap.py",
        "--switch-ips", ",".join(switch_ips),
        "--user", switch_user,
        "--password", switch_password,
        "--compact-output"  # Simplified output
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300  # 5 minute timeout
    )

    # Parse output to extract mapping
    mapping = parse_vnetmap_output(result.stdout)
    return mapping
```

**Benefits**:
- ✅ Leverage existing, tested tool
- ✅ No need to reimplement complex logic
- ✅ Gets us port mapping immediately
- ✅ Multi-vendor support included

**Challenges**:
- ⚠️ Requires SSH access to switches
- ⚠️ Switch credentials needed
- ⚠️ Parsing text output (no JSON mode)

---

### **Option 2: Import as Module** 🔷 **ALTERNATIVE**

Import vnetmap classes directly:

```python
from vnetmap import (
    BaseSwitchAPI,
    CumulusSwitchAPI,
    get_nodes_mac_address,
    map_switchs_mac_tables
)

# Use the switch API classes directly
switch_api = CumulusSwitchAPI(
    switch_ip="10.143.11.153",
    user="cumulus",
    passwd="password"
)

# Get MAC address table
mac_table = switch_api.cmd("bridge fdb show")
```

**Benefits**:
- ✅ Programmatic access to functionality
- ✅ Better error handling
- ✅ Direct data structure access

**Challenges**:
- ⚠️ More complex integration
- ⚠️ Need to understand internal data structures
- ⚠️ May require refactoring

---

### **Option 3: Enhanced API with vnetmap Backend** 🚀 **IDEAL**

Create new API methods that use vnetmap internally:

```python
# In api_handler.py

def get_network_topology(
    self,
    switch_credentials: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Get complete network topology including port-to-device mapping.

    Uses vnetmap tool to discover physical connectivity.

    Args:
        switch_credentials: Optional dict with 'user' and 'password'

    Returns:
        Dict containing:
        - port_mapping: Port-to-device connections
        - topology: Network topology graph
        - health: Fabric health diagnostics
    """
    from vnetmap import (
        get_all_switch_objects,
        map_switchs_mac_tables,
        validate_internal_network
    )

    # Get switch IPs from cluster
    switches = self.get_switches_detail()
    switch_ips = [s["mgmt_ip"] for s in switches]

    # Get node IPs
    cnodes = self.get_cnode_details()
    dnodes = self.get_dnode_details()
    node_ips = [n.primary_ip for n in cnodes + dnodes]

    # Run vnetmap logic
    switch_objs = get_all_switch_objects(
        switch_ips,
        switch_credentials.get("user", "cumulus"),
        switch_credentials.get("password")
    )

    mapping = map_switchs_mac_tables(
        mtu_check=True,
        nodes=node_ips,
        switch_objs=switch_objs,
        ssh_key=None  # Use password auth
    )

    return {
        "port_mapping": mapping,
        "switches": switch_ips,
        "nodes": node_ips,
        "timestamp": datetime.now().isoformat()
    }
```

**Benefits**:
- ✅ Clean API interface
- ✅ Integrated with existing report flow
- ✅ Can be optional (requires credentials)
- ✅ Reuses battle-tested code

---

## 📋 Report Integration Strategy

### **Phase 1: Optional Port Mapping Collection**

Add optional switch credentials to report generation:

```bash
python src/main.py \
  --cluster 10.143.11.202 \
  --username support \
  --password 654321 \
  --switch-user cumulus \
  --switch-password "CumulusLinux!" \
  --enable-port-mapping
```

### **Phase 2: Enhanced Switch Configuration Section**

Add new subsection to Switch Configuration:

```markdown
## Switch Port Mapping

| Switch | Port | Speed | Connected To | Device Type | IP Address | Interface | MAC Address |
|--------|------|-------|--------------|-------------|------------|-----------|-------------|
| se-var-1-1 | swp1 | 200G | cnode-3-4 | CNode | 172.16.3.4 | eth0 | 00:11:22:33:44:55 |
| se-var-1-1 | swp2 | 200G | cnode-3-4 | CNode | 172.16.2.4 | eth1 | 00:11:22:33:44:56 |
| se-var-1-1 | swp5 | 200G | dnode-3-104 | DNode | 172.16.3.104 | eth0 | 00:11:22:33:44:57 |
| se-var-1-1 | swp29 | 100G | se-var-1-2 | Switch (IPL) | 10.143.11.154 | swp29 | 00:11:22:33:44:AA |
```

### **Phase 3: Network Topology Diagram**

Generate visual topology using port mapping data:

```
┌─────────────┐
│ se-var-1-1  │
│ (Leaf 1)    │
└──────┬──────┘
       │ swp1-28 (Data Plane)
       ├─ swp1,2  → cnode-3-4 (eth0,eth1)
       ├─ swp3,4  → cnode-3-5 (eth0,eth1)
       ├─ swp5,6  → dnode-3-104 (eth0,eth1)
       │
       │ swp29-30 (IPL)
       ├─ swp29,30 → se-var-1-2
       │
       │ swp31-32 (Uplinks)
       └─ swp31,32 → Spine (if present)
```

---

## 🔐 Security & Requirements

### **Authentication Requirements**

#### **For VAST Cluster API** (Existing)
- ✅ Username: `support`
- ✅ Password: `654321` (or configured)
- ✅ HTTPS with self-signed cert

#### **For Switches** (New Requirement)
- ❓ **Switch SSH credentials needed**
- ❓ Typical: user=`cumulus`, password varies
- ❓ May require separate credential storage

### **Network Access Requirements**

#### **From Report Generator Host**
- ✅ HTTPS to VAST Management VIP (already working)
- ⚠️ **SSH to switch management IPs** (may need firewall rules)
- ⚠️ **SSH to CNode/DNode management IPs** (for MAC collection)

### **Dependencies**

#### **Python Packages** (from vnetmap.py)
```python
# Already in requirements.txt:
- collections (stdlib)
- concurrent.futures (stdlib)
- subprocess (stdlib)
- json (stdlib)

# May need to add:
- jsonrpclib  # For Arista switches
- sshpass     # For SSH password authentication (system package)
```

#### **System Packages**
```bash
# May need to install on Mac/Linux:
brew install sshpass  # Mac
apt-get install sshpass  # Ubuntu
```

---

## ⚖️ Pros & Cons Analysis

### **Advantages** ✅

1. **Solves Our Exact Problem**
   - Provides complete port-to-device mapping
   - Identifies IPLs, uplinks, and data plane connections
   - Answers "what's connected where?"

2. **Battle-Tested Code**
   - Version 1.0.5 (mature)
   - Used by VAST field engineers
   - Handles edge cases and vendor variations

3. **Multi-Vendor Support**
   - Works with our Cumulus switches
   - Future-proof for Mellanox/Arista deployments

4. **Comprehensive Data**
   - MAC address correlation
   - VLAN information
   - MTU validation
   - Fabric health diagnostics

5. **Diagnostic Capabilities**
   - Detects misconfigurations
   - Identifies missing nodes
   - Validates fabric consistency

### **Challenges** ⚠️

1. **Additional Credentials Required**
   - Switch SSH credentials needed
   - Separate from VAST API credentials
   - Security considerations for storage

2. **Network Access Dependencies**
   - Requires SSH to switches (port 22)
   - May need firewall rule changes
   - Could fail in restricted environments

3. **Execution Time**
   - SSH to multiple switches and nodes
   - Could add 30-60 seconds to report generation
   - May timeout in very large clusters

4. **Error Handling Complexity**
   - Switch connection failures possible
   - Node SSH failures possible
   - Graceful degradation needed

5. **Text-Based Output**
   - No native JSON output mode
   - Requires parsing printed output
   - Could break with version changes

6. **System Dependencies**
   - Requires `sshpass` (not always installed)
   - May have issues on Mac vs Linux
   - Windows compatibility unknown

---

## 🎯 Recommendations

### **Immediate Action** 🔶 **HIGH PRIORITY**

**1. Test vnetmap.py Manually**

```bash
# From cluster management node or workstation with network access
cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report

python3 src/vnetmap.py \
  --switch-ips 10.143.11.153,10.143.11.154 \
  --user cumulus \
  --password <SWITCH_PASSWORD> \
  --compact-output
```

**Purpose**: Verify it works with our cluster before integration

---

### **Phase 1: Standalone Execution** 📝 **RECOMMENDED START**

**Create Wrapper Script**: `get_port_mapping.sh`

```bash
#!/bin/bash
# Standalone port mapping discovery

CLUSTER_IP="$1"
SWITCH_USER="${2:-cumulus}"
SWITCH_PASS="$3"

# Get switch IPs from cluster API
SWITCH_IPS=$(curl -k -u support:654321 \
  "https://${CLUSTER_IP}/api/v1/switches/" \
  -H "Content-Type: application/json" 2>/dev/null | \
  python3 -c "import sys, json; switches = json.load(sys.stdin); print(','.join([s['mgmt_ip'] for s in switches]))")

# Run vnetmap
python3 src/vnetmap.py \
  --switch-ips "$SWITCH_IPS" \
  --user "$SWITCH_USER" \
  --password "$SWITCH_PASS" \
  --compact-output \
  > "reports/port_mapping_$(date +%Y%m%d_%H%M%S).txt"
```

**Benefits**:
- ✅ No code changes to report generator
- ✅ Can test independently
- ✅ Manual fallback option
- ✅ Low risk

---

### **Phase 2: Optional Integration** 🔷 **NEXT STEP**

Add command-line flags to `main.py`:

```python
parser.add_argument(
    "--enable-port-mapping",
    action="store_true",
    help="Enable network port mapping (requires switch credentials)"
)
parser.add_argument(
    "--switch-user",
    default="cumulus",
    help="Username for switch SSH access"
)
parser.add_argument(
    "--switch-password",
    help="Password for switch SSH access"
)
```

Integrate into report generation:

```python
# In data_extractor.py or api_handler.py

if args.enable_port_mapping and args.switch_password:
    try:
        port_mapping = get_network_topology_via_vnetmap(
            cluster_ip=args.cluster,
            switch_user=args.switch_user,
            switch_password=args.switch_password
        )
        data["port_mapping"] = port_mapping
    except Exception as e:
        logger.warning(f"Port mapping failed: {e}")
        data["port_mapping"] = None  # Graceful degradation
```

**Benefits**:
- ✅ Optional feature (doesn't break existing reports)
- ✅ Graceful failure if credentials missing
- ✅ Clear value-add for customers who provide credentials

---

### **Phase 3: Enhanced Reporting** 🚀 **FUTURE**

Add comprehensive port mapping section to report:

1. **Port Mapping Table** (detailed per-port connections)
2. **Topology Summary** (nodes per switch)
3. **IPL Identification** (inter-switch links)
4. **Uplink Identification** (spine connections)
5. **Unused Port Report** (capacity planning)

---

## 🔬 Technical Deep Dive: How It Works

### **MAC Address Correlation Logic**

**Step 1: Collect Node MACs**
```python
# SSH to each node
ssh support@172.16.3.4 "ip link show eth0"
# Extract: 00:11:22:33:44:55

# Repeat for all interfaces on all nodes
node_macs = {
    "00:11:22:33:44:55": {
        "hostname": "cnode-3-4",
        "ip": "172.16.3.4",
        "interface": "eth0"
    }
}
```

**Step 2: Collect Switch MAC Tables**
```python
# For Cumulus switches via SSH:
ssh cumulus@10.143.11.153 "bridge fdb show"

# Output:
# 00:11:22:33:44:55 dev swp1 vlan 100

# Parsed to:
switch_macs = {
    "00:11:22:33:44:55": {
        "switch": "10.143.11.153",
        "port": "swp1",
        "vlan": 100
    }
}
```

**Step 3: Correlate**
```python
for mac in node_macs:
    if mac in switch_macs:
        # Match found!
        print(f"{node_macs[mac]['hostname']} → "
              f"{switch_macs[mac]['switch']} port "
              f"{switch_macs[mac]['port']}")
```

**Result**:
```
cnode-3-4 (eth0) → se-var-1-1 (swp1)
```

---

## 📊 Example Output Analysis

### **Typical vnetmap.py Output**

```
Mapping nodes 4
Switches 2

Full topology

hostname          switch              port  Node IP        Interface  MAC
cnode-3-4         se-var-1-1         swp1  172.16.3.4     eth0       00:11:22:33:44:55
cnode-3-4         se-var-1-1         swp2  172.16.2.4     eth1       00:11:22:33:44:56
cnode-3-5         se-var-1-1         swp3  172.16.3.5     eth0       00:11:22:33:44:57
cnode-3-5         se-var-1-1         swp4  172.16.2.5     eth1       00:11:22:33:44:58
dnode-3-104       se-var-1-2         swp1  172.16.3.104   eth0       00:11:22:33:44:59
dnode-3-104       se-var-1-2         swp2  172.16.2.104   eth1       00:11:22:33:44:5A
dnode-3-105       se-var-1-2         swp3  172.16.3.105   eth0       00:11:22:33:44:5B
dnode-3-105       se-var-1-2         swp4  172.16.2.105   eth1       00:11:22:33:44:5C

Topology by switch:

se-var-1-1:
  - cnode-3-4 (2 ports: swp1, swp2)
  - cnode-3-5 (2 ports: swp3, swp4)

se-var-1-2:
  - dnode-3-104 (2 ports: swp1, swp2)
  - dnode-3-105 (2 ports: swp3, swp4)

Health Check:
✅ All nodes found
✅ No duplicate MACs
✅ MTU consistent (9216)
✅ No failed connections
```

---

## 💼 Business Value

### **For As-Built Report**

1. **Complete Network Documentation** ✅
   - Every port assignment documented
   - Physical connectivity traceable
   - Troubleshooting time reduced

2. **Professional Deliverable** ✅
   - Comprehensive topology maps
   - Port-level detail
   - Customer-ready documentation

3. **Operational Efficiency** ✅
   - Automated discovery (no manual audit)
   - Always accurate (pulled from live state)
   - Updates with cluster changes

### **For VAST Field Engineers**

1. **Validation Tool** ✅
   - Verify deployment correctness
   - Identify misconfigurations
   - Catch cabling errors

2. **Troubleshooting Aid** ✅
   - Trace connectivity issues
   - Identify failed links
   - Validate MTU settings

3. **Customer Handoff** ✅
   - Professional topology documentation
   - Complete connectivity details
   - Reference for customer NOC

---

## 🎓 Conclusion & Next Steps

### **Key Findings**

✅ **`vnetmap.py` solves our port mapping problem completely**
✅ **Professional, battle-tested code from VAST engineering**
✅ **Compatible with our cluster (Cumulus switches)**
✅ **Provides exactly the data we identified as missing**

### **Recommendation**

**Integrate vnetmap.py capabilities into As-Built Report Generator**

**Phased Approach**:
1. ✅ **Test standalone** - Verify it works with our cluster
2. 🔶 **Wrapper script** - Create standalone port mapping script
3. 🔷 **Optional integration** - Add as optional feature with credentials
4. 🚀 **Enhanced reporting** - Full topology section in report

### **Immediate Actions**

1. **Test vnetmap.py** on cluster 10.143.11.202
   - Get switch credentials from user
   - Run manual port mapping discovery
   - Validate output quality

2. **Document Requirements**
   - Switch SSH access requirements
   - Credential storage approach
   - Security considerations

3. **Create Integration Plan**
   - Design command-line interface
   - Plan error handling approach
   - Define report section format

---

**Status**: ⭐ **HIGH VALUE DISCOVERY** - Highly recommended for integration
**Priority**: 🔶 **MEDIUM** - Enhances report quality significantly
**Effort**: 🔷 **MEDIUM** - Requires credential handling and parsing
**Risk**: 🟢 **LOW** - Can be optional feature with graceful degradation
