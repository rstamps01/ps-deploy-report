# VNetMap Test Results & Alternative Approach

**Date**: October 20, 2025
**Test Status**: ⚠️ **Execution Blocked - Design Limitation Identified**
**Finding**: Tool designed for cluster-internal execution, not external workstation

---

## 🔍 Test Execution Summary

### **Test Attempted**
```bash
python3 src/vnetmap.py \
  -s 10.143.11.153,10.143.11.154 \
  -i 172.16.3.4,172.16.3.5,172.16.3.104,172.16.3.105 \
  -user cumulus \
  -password 'Vastdata1!' \
  --compact-output
```

### **Result**: ❌ **Failed**

**Error**:
```
Exception: Failed to ssh using known keys, please check that the above ssh CMD params are correct
```

---

## 🎯 Root Cause Analysis

### **Design Assumption**
`vnetmap.py` is designed to run **FROM WITHIN** the VAST cluster:
- Assumes SSH keys are pre-configured in `/home/vastdata/.ssh/id_rsa`
- Expects passwordless SSH access to all cluster nodes
- Designed for VAST field engineers running from CNode/management node

### **Our Execution Environment**
We're running from **external Mac workstation**:
- ❌ No pre-configured SSH keys
- ❌ No direct network access to node management IPs (172.16.x.x may be internal-only)
- ❌ Tool doesn't support password-based SSH to nodes (only to switches)

###**Technical Details**

#### **What Worked** ✅
1. ✅ **sshpass installed successfully** (for switch authentication)
2. ✅ **Switch credentials accepted** (cumulus / Vastdata1!)
3. ✅ **Cluster API accessible** (got node IPs via REST API)

#### **What Failed** ❌
- ❌ **SSH to cluster nodes** - Tool requires SSH key, not password
- ❌ **Node access** - May require VPN or being on cluster management network
- ❌ **SSH key lookup** - Looks for `/home/vastdata/.ssh/id_rsa` (doesn't exist on Mac)

---

## 💡 Alternative Approaches

### **Option 1: Run from VAST Cluster** 🔶 **RECOMMENDED**

**Execute vnetmap.py from within the cluster**:

```bash
# SSH to a CNode or management node
ssh vastdata@172.16.3.4

# Copy vnetmap.py to the node
scp src/vnetmap.py vastdata@172.16.3.4:/tmp/

# Run from within cluster
ssh vastdata@172.16.3.4
cd /tmp
python3 vnetmap.py \
  -s 10.143.11.153,10.143.11.154 \
  -discover \
  -user cumulus \
  -password 'Vastdata1!' \
  --compact-output
```

**Benefits**:
- ✅ Tool works as designed
- ✅ All SSH keys pre-configured
- ✅ Direct network access to all nodes
- ✅ Complete port mapping generated

**Requirements**:
- Access to cluster node via SSH or console
- Network connectivity from CNode to switches

---

### **Option 2: Hybrid API + Inference** 🔷 **FALLBACK**

**Use available API data + intelligent inference**:

Since we can't get MAC-level port mapping externally, use what we have:

#### **Available Data from VAST API**:
1. ✅ Switch inventory (model, ports, IPs)
2. ✅ CNode/DNode inventory (IPs, hostnames)
3. ✅ Port states and speeds from `/api/v1/ports/`
4. ✅ Network configuration from `/api/v7/vms/1/network_settings/`

#### **Inference Logic**:
```python
# Based on port speed and patterns:
# - 200G ports (swp1-28): Data plane (CNode/DNode connections)
# - 100G ports (swp29-30): IPLs (inter-peer links)
# - 100G ports (swp31-32): Uplinks (spine connections)
# - Unconfigured: Unused/reserved

# Create inferred mapping:
port_mapping = {
    "se-var-1-1": {
        "swp1-14": "Data Plane (likely CNode connections)",
        "swp15-28": "Data Plane (likely DNode connections)",
        "swp29-30": "IPL to se-var-1-2",
        "swp31-32": "Uplink (spine or external)"
    }
}
```

**Benefits**:
- ✅ Can run from external workstation
- ✅ Uses only VAST REST API (no SSH required)
- ✅ Provides useful port classification

**Limitations**:
- ⚠️ Not port-specific (can't say "swp1 = cnode-3-4 eth0")
- ⚠️ Inference-based (educated guesses, not definitive)
- ⚠️ Requires manual verification

---

### **Option 3: Manual Documentation** 📝 **SIMPLE**

**Create `config/port_mapping.yaml`** during deployment:

```yaml
# Documented during cluster deployment
switches:
  se-var-1-1:
    hostname: se-var-1-1
    mgmt_ip: 10.143.11.153
    ports:
      swp1:
        connected_to: cnode-3-4
        interface: eth0
        purpose: data_plane
      swp2:
        connected_to: cnode-3-4
        interface: eth1
        purpose: data_plane
      swp3:
        connected_to: cnode-3-5
        interface: eth0
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

**Benefits**:
- ✅ 100% accurate
- ✅ Works from any location
- ✅ No SSH access required
- ✅ Easy to maintain

**Limitations**:
- ⚠️ Manual documentation required
- ⚠️ Must be updated when cabling changes

---

### **Option 4: Request from VAST Support** 🔷 **PROFESSIONAL**

**Ask VAST to run vnetmap.py and provide output**:

Since vnetmap.py is a VAST internal tool, VAST support can:
1. Run vnetmap.py from within the cluster
2. Generate complete port mapping
3. Provide output as JSON or text file
4. Include in cluster documentation

**Benefits**:
- ✅ Most accurate data
- ✅ Zero work for us
- ✅ Professional documentation

**Timeline**:
- ⚠️ Depends on VAST support responsiveness
- ⚠️ May require support ticket

---

## 🎯 Recommended Path Forward

### **Immediate: Option 2 (Hybrid API + Inference)** 🔶

**Implement intelligent port classification** in report:

```python
# In report_builder.py - Switch Configuration section

def classify_port_purpose(port_name: str, speed: str, switch_count: int) -> str:
    """
    Classify port purpose based on speed and position.

    Args:
        port_name: Port name (e.g., "swp1")
        speed: Port speed (e.g., "200G", "100G", None)
        switch_count: Total number of switches in cluster

    Returns:
        Port classification string
    """
    # Extract port number
    port_num = int(''.join(filter(str.isdigit, port_name)))

    if speed == "200G":
        if port_num <= 14:
            return "Data Plane (CNode)"
        elif port_num <= 28:
            return "Data Plane (DNode)"
        else:
            return "Data Plane (High-Speed)"

    elif speed == "100G":
        if port_num in [29, 30]:
            return "IPL (Inter-Peer Link)" if switch_count > 1 else "Reserved"
        elif port_num in [31, 32]:
            return "Uplink (Spine/Core)"
        else:
            return "Data Plane (Standard)"

    else:  # Unconfigured
        return "Unused/Reserved"
```

**Add to Report**:

| Switch | Port | Speed | Purpose | Status |
|--------|------|-------|---------|--------|
| se-var-1-1 | swp1 | 200G | Data Plane (CNode) | Up |
| se-var-1-1 | swp2 | 200G | Data Plane (CNode) | Up |
| ... | ... | ... | ... | ... |
| se-var-1-1 | swp29 | 100G | IPL (Inter-Peer Link) | Up |
| se-var-1-1 | swp31 | 100G | Uplink (Spine/Core) | Up |

**Value**:
- ✅ Provides useful port classification
- ✅ No additional credentials needed
- ✅ Works from external workstation
- ✅ Better than no port info at all

---

### **Future: Option 1 (Run from Cluster)** 🚀

**For detailed port mapping**:

Work with VAST support or customer to:
1. Execute vnetmap.py from cluster management node
2. Capture complete port-to-device mapping
3. Include in comprehensive documentation
4. Use for troubleshooting and validation

---

## 📊 Updated Report Section Design

### **Switch Configuration Section**

#### **1. Switch Inventory** (Current - Keep)
- Switch models, serial numbers
- Management IPs
- Firmware versions

#### **2. Port Configuration** (Current - Keep)
- Port speeds (200G, 100G, unconfigured)
- Port states (up/down)
- MTU settings

#### **3. Port Classification** (New - Add)
- Intelligent purpose classification
- Data plane vs IPL vs uplink
- Unused port identification

**Example Table**:
```
Port Classification Summary

Purpose               | Ports      | Total | Status
----------------------|------------|-------|--------
Data Plane (CNode)    | swp1-14    | 14    | All Up
Data Plane (DNode)    | swp15-28   | 14    | All Up
IPL (Inter-Peer)      | swp29-30   | 2     | All Up
Uplink (Spine)        | swp31-32   | 2     | All Up
Unused/Reserved       | swp3,4,... | 10    | Up
```

#### **4. Detailed Port Mapping** (Optional - Future)
- Only included if vnetmap.py output available
- Shows exact device-to-port connections
- MAC address correlation

---

## 💼 Business Impact

### **Current Capability (API Only)**
- ✅ Complete switch inventory
- ✅ Port speed and state information
- ✅ Port configuration summary
- ⚠️ **NO** specific device-to-port mapping
- ⚠️ **NO** MAC address correlation

### **With Option 2 (Inference)**
- ✅ Everything above
- ✅ **Port purpose classification**
- ✅ **IPL identification**
- ✅ **Uplink identification**
- ✅ **Capacity planning** (unused ports)
- ⚠️ Still no specific device-to-port mapping

### **With Option 1 (vnetmap from cluster)**
- ✅ Everything above
- ✅ **Complete port-to-device mapping**
- ✅ **MAC address correlation**
- ✅ **Exact connectivity documentation**
- ✅ **Full troubleshooting capability**

---

## 🎓 Lessons Learned

### **Tool Architecture Understanding**
`vnetmap.py` is an **internal cluster tool**, not an **external API tool**:
- Designed for field engineers with cluster access
- Requires pre-configured SSH infrastructure
- Expects to run from management/CNode
- Not meant for external report generation

### **Our Use Case Mismatch**
Report generator runs **externally** from workstation:
- Cannot assume cluster SSH access
- Must use VAST REST API only
- Should work without internal network access
- Should not require SSH keys

### **Correct Application**
`vnetmap.py` is valuable for:
- ✅ Field deployment validation
- ✅ Troubleshooting network issues
- ✅ One-time topology documentation
- ❌ **NOT** for automated external report generation

---

## 🎯 Conclusion & Recommendation

### **For Automated Report Generation**

**Implement Option 2: Hybrid API + Inference**

**Why**:
1. Works from external workstation ✅
2. Uses only VAST REST API (already working) ✅
3. No additional credentials needed ✅
4. Provides useful port classification ✅
5. Low implementation effort ✅

**Implementation Steps**:
1. Create port classification logic
2. Add "Port Classification" subsection to Switch Configuration
3. Identify IPLs, uplinks, and data plane ports
4. Document inference assumptions in report

### **For Detailed Port Mapping**

**Use Option 1 or 4: Run vnetmap.py from cluster**

**When**:
- Customer requests detailed connectivity documentation
- Troubleshooting network issues
- Validating deployment correctness

**How**:
- Ask VAST support to run vnetmap.py
- OR SSH to cluster and run manually
- Include output as supplemental documentation

---

**Status**: 🔶 **Path Forward Defined**
**Next Action**: Implement intelligent port classification (Option 2)
**Future Enhancement**: Support vnetmap.py output import (Optional)
**Priority**: **Medium** - Adds value without external dependencies
