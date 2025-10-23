# Mellanox Onyx MSN2100 Output Analysis

## Date: October 23, 2025
## Switch: MSN2100-CB2F (rack6-2, IP: 10.27.16.174)
## Purpose: Analyze actual command output for port mapping implementation

---

## CREDENTIALS

**Onyx Default**:
- **Username**: `admin`
- **Password**: `admin`

**Comparison with Cumulus**:
- Cumulus: `cumulus` / `Vastdata1!`
- Onyx: `admin` / `admin`

---

## COMMAND SEQUENCE FOR PORT MAPPING

### 1. MAC Address Table Command

**Command**: `show mac-address-table`

**Purpose**: Get MAC-to-port mappings for all VLANs

**Credentials**: `admin` / `admin`

---

### 2. Interface Status Command

**Command**: `show interfaces ethernet status`

**Purpose**: Get operational status and speed for each port

**Credentials**: `admin` / `admin`

---

### 3. LLDP Neighbors Command (for IPL)

**Command**: `show lldp interfaces ethernet remote` (not shown, but needed)

**Purpose**: Identify switch-to-switch connections

**Credentials**: `admin` / `admin`

---

## OUTPUT ANALYSIS

### MAC Address Table Format

```
-----------------------------------------------------------
Vlan    Mac Address         Type         Port\Next Hop
-----------------------------------------------------------
1       00:0C:29:03:A2:F1   Dynamic      Eth1/15
69      0C:42:A1:22:FB:4A   Dynamic      Eth1/1
69      0C:42:A1:22:FB:4B   Dynamic      Po1
4000    98:03:9B:F5:1A:08   Static       Po1
```

**Key Observations**:

1. **Column Format**: Fixed-width columns with headers
2. **VLAN**: Integer (1, 69, 4000)
3. **MAC Address**: Colon-separated format (already standard!) ✅
   - Example: `00:0C:29:03:A2:F1`
   - **NO CONVERSION NEEDED** (unlike documentation which showed dot format)
4. **Type**: `Dynamic` or `Static`
5. **Port**: Can be physical port (`Eth1/1`) or port-channel (`Po1`)

**Interface Types Found**:
- `Eth1/1` - Physical port (1U position, port 1)
- `Eth1/9/1` - Breakout port (port 9, subport 1)
- `Eth1/10/2` - Breakout port (port 10, subport 2)
- `Po1` - Port-channel (MLAG/LAG)

---

### Interface Status Format

```
Port                   Operational state           Speed                  Negotiation
----                   -----------------           -----                  -----------
Eth1/1                 Up                          100G                   Auto
Eth1/5/1               Up                          50G                    Auto
Eth1/15                Up                          100G                   Auto
```

**Key Observations**:

1. **Port**: Interface name (Eth1/X or Eth1/X/Y)
2. **Operational state**: `Up` or `Down`
3. **Speed**: `100G`, `50G`, `Unknown`
4. **Negotiation**: `Auto`

---

## DATA EXTRACTION STRATEGY

### Relevant Ports for Port Mapping

From the MAC table, we see:

**VLAN 69 (Data VLAN)**:
```
Vlan    Mac Address         Type         Port
69      0C:42:A1:22:FB:4A   Dynamic      Eth1/1      <- CNode or DNode
69      0C:42:A1:22:FB:4B   Dynamic      Po1         <- Same MAC on MLAG
69      0C:42:A1:3D:CD:C0   Dynamic      Eth1/2      <- CNode or DNode
69      0C:42:A1:3D:CD:C1   Dynamic      Po1         <- Same MAC on MLAG
69      98:03:9B:81:32:66   Dynamic      Eth1/10/2   <- Node interface
69      98:03:9B:81:32:67   Dynamic      Po1         <- Same MAC on MLAG
69      98:03:9B:8E:2B:D4   Dynamic      Eth1/9/1    <- Node interface
69      98:03:9B:8E:2B:D5   Dynamic      Po1         <- Same MAC on MLAG
69      98:03:9B:8E:2C:08   Dynamic      Eth1/10/1   <- Node interface
69      98:03:9B:8E:2C:09   Dynamic      Po1         <- Same MAC on MLAG
69      BE:EF:*             Dynamic      Various     <- Virtual/SR-IOV MACs
```

**Key Findings**:

1. **Physical Node Ports**: `Eth1/1`, `Eth1/2` contain node MACs (VLAN 69)
2. **Breakout Ports**: `Eth1/9/1`, `Eth1/10/1`, `Eth1/10/2` contain node MACs
3. **MLAG/Po1**: Many MACs appear on both physical port AND `Po1`
4. **Virtual MACs**: `BE:EF:*` prefix indicates SR-IOV/virtual functions
5. **Management VLAN**: VLAN 1 has tons of MACs on `Eth1/15` (uplink/management)

---

### Port Usage Pattern

**From Interface Status**:
```
Eth1/1         Up   100G    <- Node connection (VLAN 69)
Eth1/2         Up   100G    <- Node connection (VLAN 69)
Eth1/5/1       Up   50G     <- Node connection (breakout)
Eth1/5/2       Up   50G     <- Node connection (breakout)
Eth1/6/1       Up   50G     <- Node connection (breakout)
Eth1/6/2       Up   50G     <- Node connection (breakout)
Eth1/7/1       Up   50G     <- Node connection (breakout)
Eth1/7/2       Up   50G     <- Node connection (breakout)
Eth1/8/1       Up   50G     <- Node connection (breakout)
Eth1/8/2       Up   50G     <- Node connection (breakout)
Eth1/9/1       Up   50G     <- Node connection (breakout, VLAN 69)
Eth1/9/2       Up   50G     <- Node connection (breakout)
Eth1/10/1      Up   50G     <- Node connection (breakout, VLAN 69)
Eth1/10/2      Up   50G     <- Node connection (breakout, VLAN 69)
Eth1/13        Up   100G    <- IPL? (needs LLDP check)
Eth1/14        Up   100G    <- IPL? (needs LLDP check)
Eth1/15        Up   100G    <- Uplink/Management (VLAN 1 MACs)
```

**Port Naming Convention**:
- **Full ports**: `Eth1/1` through `Eth1/16`
- **Breakout ports**: `Eth1/5/1`, `Eth1/5/2` (port 5 split into 2x50G)
- **Total**: 16 ports, some broken out to 2x50G

---

## PARSING REQUIREMENTS

### 1. MAC Address Table Parser

```python
def _parse_onyx_mac_table(self, output: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse Mellanox Onyx MAC table output.

    Format:
    Vlan    Mac Address         Type         Port\Next Hop
    1       00:0C:29:03:A2:F1   Dynamic      Eth1/15
    69      0C:42:A1:22:FB:4A   Dynamic      Eth1/1

    Returns:
        Dict mapping MACs to {port, vlan, entry_type}
    """
    mac_table = {}

    for line in output.split("\n"):
        # Skip header, separator, and summary lines
        if (line.startswith("Vlan") or
            line.startswith("---") or
            line.startswith("Number of") or
            not line.strip()):
            continue

        # Parse MAC table entries
        parts = line.split()
        if len(parts) >= 4:
            try:
                vlan = parts[0]
                mac = parts[1]  # Already in colon format!
                entry_type = parts[2]  # Dynamic or Static
                port = parts[3]  # Eth1/1 or Po1

                # Validate MAC format (colon-separated)
                if re.match(r"^[0-9A-F:]{17}$", mac, re.IGNORECASE):
                    # Only include physical Ethernet ports for port mapping
                    # Exclude Po1 (port-channel) as these are redundant
                    if port.startswith("Eth"):
                        mac_table[mac.lower()] = {
                            "port": port,
                            "vlan": vlan,
                            "entry_type": "permanent" if entry_type == "Static" else None,
                        }
            except (IndexError, ValueError):
                continue

    return mac_table
```

**Key Differences from Documentation**:
- ✅ **MAC format is already colon-separated** (not dot-separated as expected)
- Port column can contain `Po1` which should be filtered out (MLAG)
- Virtual MACs (`BE:EF:*`) should be filtered in correlation logic

---

### 2. Interface Status Parser

```python
def _parse_onyx_interface_status(self, output: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse Onyx interface status output.

    Format:
    Port                   Operational state           Speed                  Negotiation
    Eth1/1                 Up                          100G                   Auto

    Returns:
        Dict mapping ports to {state, speed}
    """
    interface_status = {}

    for line in output.split("\n"):
        # Skip header and separator lines
        if (line.startswith("Port") or
            line.startswith("----") or
            not line.strip()):
            continue

        # Parse interface entries
        parts = line.split()
        if len(parts) >= 3:
            try:
                port = parts[0]  # Eth1/1 or Eth1/9/1
                state = parts[1]  # Up or Down
                speed = parts[2]  # 100G, 50G, Unknown

                # Only include Up interfaces
                if state == "Up" and speed != "Unknown":
                    interface_status[port] = {
                        "state": state,
                        "speed": speed,
                    }
            except (IndexError, ValueError):
                continue

    return interface_status
```

---

## PORT MAPPING CORRELATION

### Filter Strategy

**For Port Mapping, we want**:
1. **VLAN 69 MACs** (data network)
2. **Physical ports only** (not `Po1`)
3. **Non-virtual MACs** (exclude `BE:EF:*` prefix)
4. **Exclude management VLAN 1** (unless needed)

**Example Filtering**:
```python
def _filter_node_macs(self, mac_table: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Filter MAC table to only include node connections."""
    filtered = {}

    for mac, entry in mac_table.items():
        # Only VLAN 69 (data network)
        if entry["vlan"] != "69":
            continue

        # Only physical Ethernet ports (not Po1)
        if not entry["port"].startswith("Eth"):
            continue

        # Skip virtual MACs (BE:EF:* indicates SR-IOV)
        if mac.startswith("be:ef:"):
            continue

        filtered[mac] = entry

    return filtered
```

---

## PORT CHANNEL (MLAG) HANDLING

**Observation**: Many MACs appear twice:
```
69      0C:42:A1:22:FB:4A   Dynamic      Eth1/1
69      0C:42:A1:22:FB:4B   Dynamic      Po1
```

**Issue**: These are MLAG pairs:
- MAC ending in `:4A` on physical port `Eth1/1`
- MAC ending in `:4B` on port-channel `Po1`

**Solution**:
1. **Filter out `Po1` entries** (use only physical ports)
2. **Recognize MAC pairs** (`:4A`/`:4B` pattern indicates MLAG pair)
3. **Use physical port** for port mapping (ignore Po1)

---

## IPL DETECTION

**Expected Ports for IPL** (based on Up status and typical usage):
- `Eth1/13` - Up, 100G (likely IPL)
- `Eth1/14` - Up, 100G (likely IPL)

**Need LLDP command**:
```bash
show lldp interfaces ethernet remote
```

Expected output to identify that `Eth1/13` and `Eth1/14` connect to the other switch.

---

## IMPLEMENTATION CHECKLIST

### ✅ Command Sequence
1. `show mac-address-table` - Get MAC-to-port mappings
2. `show interfaces ethernet status` - Get port status and speeds
3. `show lldp interfaces ethernet remote` - Get IPL connections

### ✅ Parsing Requirements
1. Parse Onyx MAC table format
2. **No MAC address conversion needed** (already colon-separated)
3. Parse interface status format
4. Filter out `Po1` (port-channel) entries
5. Filter out virtual MACs (`BE:EF:*`)
6. Filter to VLAN 69 only (data network)
7. Parse LLDP output for IPL detection

### ✅ Port Naming
- Physical: `Eth1/1` through `Eth1/16`
- Breakout: `Eth1/5/1`, `Eth1/9/1`, etc.
- Port-channel: `Po1` (filter out)

### ✅ Speed Mapping
- `100G` → 100 Gbps
- `50G` → 50 Gbps
- `Unknown` → Skip

---

## EXAMPLE DATA FROM THIS SWITCH

### Node Connections on VLAN 69

```
Port      MAC                Speed   Notes
-------   ----------------   -----   -----
Eth1/1    0C:42:A1:22:FB:4A  100G    CNode or DNode, Network A or B
Eth1/2    0C:42:A1:3D:CD:C0  100G    CNode or DNode, Network A or B
Eth1/9/1  98:03:9B:8E:2B:D4  50G     Node interface (breakout)
Eth1/9/2  (status Up)        50G     Node interface (breakout)
Eth1/10/1 98:03:9B:8E:2C:08  50G     Node interface (breakout)
Eth1/10/2 98:03:9B:81:32:66  50G     Node interface (breakout)
Eth1/7/1  BE:EF:48:09:2A:8A  50G     Virtual MAC (SR-IOV) - filter out
Eth1/7/2  BE:EF:BF:44:F6:18  50G     Virtual MAC (SR-IOV) - filter out
```

### Total Summary

```
Number of unicast(local): 858
Number of NVE:        0
```

**858 total MAC addresses** on this switch!
- Most are on `Eth1/15` (management/uplink)
- ~10-20 are actual node connections on VLAN 69

---

## COMPARISON: CUMULUS vs ONYX (ACTUAL)

| Feature | Cumulus | Onyx (MSN2100 Actual) |
|---------|---------|----------------------|
| **MAC Table Command** | `nv show bridge domain br_default mac-table` | `show mac-address-table` ✅ |
| **MAC Format** | `7c:8c:09:eb:ec:51` | `0C:42:A1:22:FB:4A` ✅ **Already colon format!** |
| **Port Names** | `swp1`, `swp9` | `Eth1/1`, `Eth1/9/1` ✅ |
| **Entry Type** | `permanent` | `Static` or `Dynamic` ✅ |
| **Port Channel** | N/A | `Po1` (filter out) ⚠️ |
| **Breakout Ports** | N/A | `Eth1/9/1`, `Eth1/9/2` ✅ |
| **Interface Status** | `nv show interface` | `show interfaces ethernet status` ✅ |
| **Speed Format** | N/A | `100G`, `50G` ✅ |

---

## NEXT STEPS

1. ✅ **Documentation complete** (this file)
2. ⏳ Implement Onyx MAC table parser
3. ⏳ Implement Onyx interface status parser
4. ⏳ Add VLAN filtering (VLAN 69)
5. ⏳ Add Po1 filtering
6. ⏳ Add virtual MAC filtering (`BE:EF:*`)
7. ⏳ Add OS detection (Cumulus vs Onyx)
8. ⏳ Test with actual MSN2100 switch
9. ⏳ Implement LLDP parser for IPL detection

---

## ADDITIONAL NOTES

### Breakout Port Handling

MSN2100 supports breaking out 100G ports into 2x50G:
- `Eth1/5` → `Eth1/5/1` + `Eth1/5/2`
- `Eth1/9` → `Eth1/9/1` + `Eth1/9/2`

**Port Mapping Implication**:
- Use full port name including subport: `Eth1/9/1`
- Each subport is independent for MAC correlation

### Management VLAN (VLAN 1)

Most MACs are on VLAN 1 via `Eth1/15`:
- This is likely an uplink or management port
- Should be **excluded** from port mapping tables
- Focus on VLAN 69 (data network)

---

**Generated**: October 23, 2025
**Switch**: MSN2100-CB2F (rack6-2, 10.27.16.174)
**Status**: Analysis Complete, Ready for Implementation
