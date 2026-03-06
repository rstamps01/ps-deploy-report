# Mellanox Onyx Support Implementation Summary

## Overview
Full Onyx support has been successfully implemented for the external port mapper. The system now automatically detects and supports both **Cumulus Linux** and **Mellanox Onyx** switch operating systems.

---

## Features Implemented

### 1. **Automatic OS Detection**
- **Method**: `_detect_switch_os(switch_ip)`
- **Logic**:
  - Tries both credential sets (Cumulus and Onyx)
  - Tests with OS-specific commands:
    - Cumulus: `nv show system`
    - Onyx: `show version`
  - Identifies OS from command output
  - Stores OS type and working credentials for each switch

### 2. **Dual Credential Support**
- **Cumulus Linux**: `cumulus/Vastdata1!`
- **Mellanox Onyx**: `admin/admin`
- Automatically uses correct credentials based on detected OS
- Stored per-switch in `self.switch_credentials`

### 3. **MAC Address Table Collection**
#### Cumulus Commands:
- General: `nv show bridge domain br_default mac-table`
- VLAN 69: `nv show bridge domain br_default vlan 69 mac-table`

#### Onyx Commands:
- General: `show mac-address-table`
- VLAN 69: `show mac-address-table vlan 69`

#### Onyx MAC Table Parser:
- **Method**: `_parse_onyx_mac_table(output)`
- **Format Support**:
  ```
  VID    MAC Address           Port              Type
  ----   -------------------   ---------------   -----------
  1      00:00:5E:00:01:01     Eth1/1            Dynamic
  69     7c:8c:09:eb:ec:51     Eth1/5            Dynamic
  ```
- **Port Conversion**: Converts Onyx port naming (`Eth1/5`) to standardized `swp5` format
- **MAC Normalization**: Converts MACs to lowercase for consistency

### 4. **IPL/LLDP Discovery**
#### Cumulus Commands:
- `nv show interface --output json`

#### Onyx Commands:
- `show lldp remote`

#### Onyx LLDP Parser:
- **Method**: `_parse_onyx_lldp_for_ipl(lldp_output, switch_ip)`
- **Format Support**:
  ```
  Local Interface     Chassis ID          Port ID             System Name
  -----------------   -----------------   -----------------   -----------
  Eth1/29             f4:02:70:c1:22:00   Eth1/29             switch-2
  Eth1/30             f4:02:70:c1:22:00   Eth1/30             switch-2
  ```
- **IPL Detection**: Identifies ports 29-32 as typical IPL connections
- **Port Conversion**: Converts to standardized `swp` naming

---

## Files Modified

### `src/external_port_mapper.py`
1. **Updated Documentation**:
   - Added Onyx credentials and supported OS list to module docstring

2. **Enhanced `__init__` Method**:
   - Added `self.switch_os_map` dictionary
   - Added `self.switch_credentials` dictionary

3. **New Methods**:
   - `_detect_switch_os(switch_ip)` - Auto-detect OS type
   - `_parse_onyx_mac_table(output)` - Parse Onyx MAC table
   - `_parse_onyx_lldp_for_ipl(lldp_output, switch_ip)` - Parse Onyx LLDP

4. **Modified Methods**:
   - `collect_port_mapping()` - Added OS detection step at start
   - `_collect_switch_mac_tables()` - Added OS-based command selection
   - `_collect_ipl_connections()` - Added OS-based command selection

---

## How It Works

### Execution Flow:
```
1. Initialize ExternalPortMapper
   ├── Clear SSH known_hosts
   └── Create empty OS maps

2. collect_port_mapping()
   ├── Step 0: Detect switch OS types
   │   ├── Try Cumulus credentials (cumulus/password)
   │   ├── Try Onyx credentials (admin/admin)
   │   └── Store detected OS and working credentials
   │
   ├── Step 1: Collect node inventory (API)
   ├── Step 2: Collect hostname-to-IP mapping (clush)
   ├── Step 3: Collect node MACs (clush)
   │
   ├── Step 4: Collect switch MAC tables
   │   ├── Get OS type for switch
   │   ├── Use OS-specific command
   │   └── Use OS-specific parser
   │
   ├── Step 5: Collect IPL connections
   │   ├── Get OS type for switch
   │   ├── Use OS-specific command
   │   └── Use OS-specific parser
   │
   └── Step 6: Correlate and return port map
```

### OS Detection Logic:
```python
For each switch:
  Try credentials: [(cumulus, password), (admin, admin)]

  For each credential pair:
    - SSH with test command (nv show system or show version)
    - Check output for OS-specific strings:
      - Cumulus: "cumulus", "hostname"
      - Onyx: "onyx", "mellanox", "product name"
    - If match found:
      - Store OS type (cumulus or onyx)
      - Store working credentials
      - Move to next switch
```

---

## Output Examples

### Console Output:
```
✅ Verbose logging enabled: logs/external_port_mapper_verbose_20251024_120000.log
✅ SSH known_hosts file created: .ssh_workspace/known_hosts

✅ Switch 10.27.16.174: ONYX detected (using admin credentials)
✅ Switch 10.27.16.175: CUMULUS detected (using cumulus credentials)
```

### Verbose Log Output:
```
[2025-10-24 12:00:01.234] >>> OPERATION: Detecting OS type for switch 10.27.16.174
[2025-10-24 12:00:01.567] Trying onyx credentials (admin/***) on 10.27.16.174
[2025-10-24 12:00:02.123] ✓ Detected Mellanox Onyx on 10.27.16.174
[2025-10-24 12:00:03.456] >>> OPERATION: Collecting MAC table from 10.27.16.174
[2025-10-24 12:00:03.789] 🔧 General MAC table query (onyx)
[2025-10-24 12:00:04.234] ✓ General MAC table: 156 entries
```

---

## Compatibility

### Supported Switch Models:
- **Cumulus Linux**: Mellanox MSN3700, MSN2100, and all Cumulus-capable switches
- **Mellanox Onyx**: MSN2100, MSN2700, MSN3700, and all Onyx-capable switches

### Port Naming Standardization:
| OS Type | Native Format | Standardized Format |
|---------|---------------|---------------------|
| Cumulus | `swp5`        | `swp5`              |
| Onyx    | `Eth1/5`      | `swp5`              |

This ensures consistent port mapping regardless of switch OS.

---

## Testing Recommendations

### Test Scenarios:
1. **Cumulus-only cluster** (existing functionality)
2. **Onyx-only cluster** (new)
3. **Mixed cluster** (Cumulus Switch 1 + Onyx Switch 2)
4. **Wrong credentials** (verify fallback works)

### Test Commands:
```bash
# Test with Cumulus switches
python3 -m src.main --cluster-ip 10.143.15.203 \
  --username support --password <password> \
  --enable-port-mapping \
  --node-password vastdata \
  --switch-password Vastdata1!

# Test with Onyx switches
python3 -m src.main --cluster-ip 10.27.200.208 \
  --username support --password <password> \
  --enable-port-mapping \
  --node-password vastdata \
  --switch-password admin
```

---

## Notes

### Credential Priority:
- If `--switch-user admin` is provided, Onyx credentials are tried first
- Otherwise, Cumulus credentials are tried first
- Both are attempted regardless of initial failure

### Verbose Logging:
- All operations are logged with detailed color-coded output
- MAC tables, LLDP data, and OS detection results are fully captured
- Logs are saved to `logs/external_port_mapper_verbose_TIMESTAMP.log`

### Error Handling:
- If neither credential set works, an exception is raised with a clear error message
- Individual switch failures don't stop the entire collection process
- All errors are logged to both standard logs and verbose logs

---

## Future Enhancements (Optional)

1. **Additional OS Support**: Could add support for other switch OSes (e.g., Cisco IOS, Arista EOS)
2. **Credential Configuration**: Could read from a config file for non-standard credentials
3. **Custom Port Ranges**: Could make IPL port ranges (29-32) configurable
4. **SSH Key Support**: Could add SSH key authentication as an alternative to passwords

---

## Implementation Status: ✅ COMPLETE

All TODOs have been completed:
- ✅ Implement OS detection for Mellanox switches (Cumulus vs Onyx)
- ✅ Add Onyx command support for MAC table collection
- ✅ Add Onyx command support for IPL/LLDP discovery
- ✅ Implement dual credential handling (Cumulus vs Onyx)
- ✅ Add Onyx MAC table output parser

The port mapper now provides full, transparent support for both Cumulus Linux and Mellanox Onyx switches.
