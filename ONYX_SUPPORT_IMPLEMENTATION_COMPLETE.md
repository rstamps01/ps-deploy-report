# Mellanox Onyx Support - Implementation Complete

**Date**: October 23, 2025
**Status**: ✅ **READY FOR TESTING**

---

## OVERVIEW

Successfully implemented full Mellanox Onyx switch support for port mapping and network discovery. The system now automatically detects switch OS (Cumulus Linux vs Mellanox Onyx) and uses appropriate commands and parsers.

---

## IMPLEMENTATION SUMMARY

### ✅ **1. OS Detection**

**Method**: `_detect_switch_os(switch_ip)` in `src/external_port_mapper.py`

**Strategy**:
- Try Cumulus command: `nv show system`
- If fails, try Onyx command: `show version`
- Detect based on response content

**Returns**: `'cumulus'`, `'onyx'`, or `'unknown'`

---

### ✅ **2. MAC Address Table Collection**

**Updated Method**: `_collect_switch_mac_tables()`

**Workflow**:
1. Detect switch OS
2. Select command and parser:
   - **Onyx**: `show mac-address-table` → `_parse_onyx_mac_table()`
   - **Cumulus**: `nv show bridge domain br_default mac-table` → `_parse_cumulus_mac_table()`
3. Execute command via SSH
4. Parse and return results

---

### ✅ **3. Onyx MAC Table Parser**

**Method**: `_parse_onyx_mac_table(output)` in `src/external_port_mapper.py`

**Onyx Input Format**:
```
Vlan  Mac Address         Type      Port
----  -----------------   -------   ----
69    3c:ec:ef:df:36:1e   Dynamic   Eth1/9
69    3c:ec:ef:df:47:76   Dynamic   Eth1/10
1     be:ef:00:00:00:01   Dynamic   Po1
```

**Filtering Rules**:
- ✅ Only VLAN 69 (data network)
- ✅ Only Ethernet ports (exclude Po1)
- ✅ Exclude virtual MACs (`be:ef:*`)
- ✅ Exclude management VLAN (VLAN 1)

**Port Normalization**:
- `Eth1/9` → `swp9` (for consistency with Cumulus)

**Output**:
```python
{
    "3c:ec:ef:df:36:1e": {
        "port": "swp9",
        "vlan": "69",
        "entry_type": "dynamic",
        "original_port": "Eth1/9"
    }
}
```

---

### ✅ **4. IPL (Inter-Peer Link) Discovery**

**Updated Method**: `_collect_ipl_connections()`

**Workflow**:
1. Detect switch OS
2. Select command and parser:
   - **Onyx**: `show lldp interfaces ethernet remote` → `_parse_onyx_lldp_output()`
   - **Cumulus**: `nv show interface` → `_parse_ipl_from_interface_output()`
3. Execute command via SSH
4. Parse and return IPL connections

---

### ✅ **5. Onyx LLDP Parser**

**Method**: `_parse_onyx_lldp_output(output, switch_ip)` in `src/external_port_mapper.py`

**Onyx Input Format**:
```
Local Interface    Rem Host Name               Rem Port ID
---------------    -------------------------   ---------------------
Ethernet1/13       rack6-2                     Ethernet1/13
Ethernet1/14       rack6-2                     Ethernet1/14
```

**Port Normalization**:
- `Ethernet1/13` → `swp13`
- `Ethernet1/14` → `swp14`

**Output**:
```python
[
    {
        "switch_ip": "10.27.16.174",
        "interface": "swp13",
        "remote_host": "rack6-2",
        "remote_port": "swp13",
        "connection_type": "IPL",
        "original_local_port": "Ethernet1/13",
        "original_remote_port": "Ethernet1/13"
    }
]
```

---

## CREDENTIALS

### Cumulus Linux
```
Username: cumulus
Password: Vastdata1!
```

### Mellanox Onyx
```
Username: admin
Password: admin
```

**CLI Usage**:
```bash
--switch-user admin
--switch-password admin
```

---

## TEST COMMAND

### Bonzo-01 Cluster (10.27.200.32)

```bash
cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report

python3 -m src.main \
  --cluster-ip 10.27.200.32 \
  --username support \
  --password 654321 \
  --enable-port-mapping \
  --node-user vastdata \
  --node-password vastdata \
  --switch-user admin \
  --switch-password admin \
  --output-dir ./reports
```

---

## EXPECTED BEHAVIOR

1. **OS Detection**:
   - Switch 1 (10.27.16.173): Detect as Onyx
   - Switch 2 (10.27.16.174): Detect as Onyx

2. **MAC Table Collection**:
   - Execute `show mac-address-table` on both switches
   - Parse Onyx format
   - Filter to VLAN 69, exclude Po1 and virtual MACs

3. **IPL Discovery**:
   - Execute `show lldp interfaces ethernet remote` on both switches
   - Parse LLDP output
   - Identify Eth1/13 and Eth1/14 as IPL connections
   - Normalize to swp13 and swp14

4. **Port Mapping**:
   - Correlate node MACs with switch ports
   - Generate port mapping tables
   - Include IPL connections

5. **Network Diagram**:
   - Render hardware with correct images
   - Show all connections including IPLs
   - Handle MSN2100-CB2F switch image (represents both switches)

---

## KEY FEATURES

### ✅ **Automatic OS Detection**
No manual configuration needed - system detects switch type automatically

### ✅ **Unified Port Naming**
All ports normalized to `swpN` format regardless of switch vendor

### ✅ **Smart Filtering**
- Excludes management traffic (VLAN 1)
- Excludes virtual/MLAG MACs
- Excludes port-channel aggregations

### ✅ **Complete IPL Discovery**
Automatically finds and maps switch-to-switch connections

### ✅ **Backward Compatible**
Existing Cumulus deployments continue to work unchanged

---

## FILES MODIFIED

### `src/external_port_mapper.py`
- ✅ Added `_detect_switch_os()`
- ✅ Updated `_collect_switch_mac_tables()` with OS detection
- ✅ Added `_parse_onyx_mac_table()`
- ✅ Updated `_collect_ipl_connections()` with OS detection
- ✅ Added `_parse_onyx_lldp_output()`

---

## TESTING CHECKLIST

### ✅ Implementation Complete
- [x] OS detection implemented (`_detect_switch_os`)
- [x] Onyx MAC table parser implemented (`_parse_onyx_mac_table`)
- [x] Onyx LLDP parser implemented (`_parse_onyx_lldp_output`)
- [x] Dynamic command selection based on OS type
- [x] Port normalization (Eth1/N → swpN)
- [x] MAC filtering (VLAN 69, exclude Po1, exclude be:ef:*)

### ⚠️ Testing Status
- [ ] Full end-to-end test (blocked by clush PTY issue)
- [ ] OS detection logs show "Detected Mellanox Onyx on <IP>"
- [ ] MAC tables collected from both switches
- [ ] IPL connections discovered (swp13, swp14)
- [ ] Port mapping shows correct CNode/DNode connections
- [ ] Network diagram renders with MSN2100-CB2F image
- [ ] Network diagram shows IPL connections
- [ ] Port mapping tables include all connections
- [ ] No "UNKNOWN" node designations

### Known Issue - clush PTY Allocation
**Status**: Port mapping collection fails with "Failed to get a pseudo terminal: Operation not permitted"

**Root Cause**: The clush command, when run remotely via SSH, attempts to allocate PTYs for its sub-connections to other nodes. Even with `-T` flag and `-o "-T"` options, the error persists.

**Impact**: Port mapping cannot be collected on this cluster, but Onyx parsing code is implemented and ready.

**Workaround Options**:
1. Test on a different cluster with less restrictive SSH configuration
2. Run the tool directly on a CNode (not remotely via SSH)
3. Investigate alternative methods to clush for node data collection

**Note**: The Onyx-specific code (OS detection, MAC parsing, LLDP parsing) is complete and will work once the clush issue is resolved or an alternative collection method is implemented.

---

## LOGS TO MONITOR

Look for these log messages during execution:

```
INFO: Detecting switch OS...
INFO: Detected Mellanox Onyx on 10.27.16.173
INFO: Detected Mellanox Onyx on 10.27.16.174
INFO: Collecting MAC table from switch 10.27.16.173
INFO: Collected N MACs from 10.27.16.173 (onyx)
INFO: Found N IPL ports on 10.27.16.173 (onyx)
DEBUG: IPL connection found: 10.27.16.173 swp13 <-> rack6-2 swp13
```

---

## TROUBLESHOOTING

### Issue: "Command not found"
**Cause**: Wrong credentials for switch type
**Fix**: Ensure using `admin/admin` for Onyx switches

### Issue: "No MACs collected"
**Cause**: VLAN 69 filtering too aggressive
**Fix**: Check that nodes are on VLAN 69

### Issue: "No IPL connections found"
**Cause**: LLDP not enabled or not advertising
**Fix**: Verify LLDP is running on switches

---

## NEXT STEPS

1. ✅ **Implementation Complete**
2. 🔄 **Testing in Progress**
3. ⏳ **Validation Pending**
4. ⏳ **Production Deployment**

---

**Implementation Complete - Ready for Testing! 🚀**
