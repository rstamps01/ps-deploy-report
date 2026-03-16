# Port Mapping Discovery Analysis

## Issue Summary

The port mapping discovery IS collecting data from switches successfully, but node hostnames are showing as "Unknown" for several nodes.

## Data Collection Status (from 22:32:52 report)

✅ **Successfully Collected:**
- 4 nodes from API inventory
- 39 MACs from Switch 1 (10.143.11.153)
- 25 MACs from Switch 2 (10.143.11.154)  
- 16 port mappings generated

❌ **Problem:**
- Multiple nodes showing as "Unknown":
  - 172.16.3.8 (4 interfaces)
  - 172.16.3.109 (4 interfaces)
  - 172.16.3.108 (4 interfaces)
  - 172.16.3.7 (4 interfaces)

## Root Cause

The `_correlate_node_to_switch()` method in `external_port_mapper.py` was **skipping** nodes when:
1. `clush -a hostname` didn't return a hostname for that data IP
2. The hostname wasn't found in the API inventory

This meant those 16 connections were collected but not correlated to node names.

## Port Map Data Structure (from JSON)

```json
{
  "node_ip": "172.16.3.8",
  "node_hostname": "Unknown",
  "node_designation": "UNKNOWN-172.16.3.8",
  "node_type": "unknown",
  "interface": "enp129s0f0",
  "mac": "c4:70:bd:f9:c3:9a",
  "network": "A",
  "switch_ip": "10.143.11.153",
  "switch_hostname": "se-var-1-1",
  "switch_designation": "SWA-P24",
  "port": "swp24"
}
```

## Fix Applied

Modified `src/external_port_mapper.py` line 457-470:

**Before:**
- Skipped nodes without hostnames (`continue`)
- Skipped nodes without inventory (`continue`)

**After:**
- Uses `"Unknown-{data_ip}"` as hostname if not found
- Uses empty dict `{}` for node_info if not found
- Includes ALL connections in port_map, even if hostname unknown

## Why Hostnames Are Unknown

Possible reasons:
1. `clush -a hostname` may not reach all nodes (network/auth issues)
2. Data IPs returned by `clush -a 'ip link show'` may differ from those expected
3. Node hostname command may fail on some nodes
4. API inventory may use different identifiers

## Next Steps

To fully resolve, need to:

1. **Investigate clush connectivity:**
   - Run `clush -a hostname` manually to see what's actually returned
   - Compare with `clush -a 'ip link show'` IPs
   
2. **Check API inventory:**
   - Verify what hostnames/IPs are in the API response
   - Compare with actual node data IPs

3. **Alternative approach:**
   - Use API inventory IPs directly instead of relying on clush hostname
   - Match MAC addresses to API node inventory by other fields

## Expected Outcome After Fix

With the current fix, the port mappings will now include:
- All 16+ connections (not just the ones with known hostnames)
- "Unknown-172.16.3.X" as placeholder names
- Complete switch port information
- Correct MAC and interface data

The enhanced port mapper should then be able to match these to actual nodes using other methods (MAC, interface patterns, switch ports).

## Testing Required

Run report generation from user's terminal (not AI sandbox) to avoid PTY issues:

```bash
python3 -m src.main \
  --cluster-ip 10.143.11.203 \
  --username support \
  --password 654321 \
  --output-dir ./reports \
  --enable-port-mapping \
  --node-password vastdata \
  --switch-password Vastdata1!
```

Check logs for:
- Number of hostnames mapped
- Number of port mappings generated
- Whether "Unknown" nodes are included

