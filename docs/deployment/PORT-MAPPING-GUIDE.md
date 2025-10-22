# Port Mapping Collection Guide

## Overview

The VAST As-Built Report Generator can automatically collect port mapping data by connecting to switches via SSH. This feature provides detailed information about which node interfaces are connected to which switch ports.

## Requirements

### Credentials Required

To enable port mapping collection, you need SSH access to:

1. **VAST Nodes** (default: `vastdata/vastdata`)
   - Used to collect MAC addresses from all nodes via `clush`
   - SSH access to at least one CNode is required

2. **Switches** (default: `cumulus/Vastdata1!`)
   - Used to collect MAC address tables
   - SSH access to all switches is required

### Network Access

- SSH connectivity from your workstation to:
  - At least one VAST CNode
  - All cluster switches

## Usage

### Basic Usage with Port Mapping

```bash
python3 -m src.main \
  --cluster-ip <CLUSTER_IP> \
  --output-dir ./reports \
  --enable-port-mapping
```

The script will prompt for:
1. VAST API credentials (support user/password)
2. Node SSH password (for user: vastdata)
3. Switch SSH password (for user: cumulus)

### With Custom Usernames

```bash
python3 -m src.main \
  --cluster-ip <CLUSTER_IP> \
  --output-dir ./reports \
  --enable-port-mapping \
  --node-user vastdata \
  --switch-user cumulus
```

### With Environment Variables

```bash
export VAST_USERNAME=support
export VAST_PASSWORD=<password>
export VAST_NODE_PASSWORD=vastdata
export VAST_SWITCH_PASSWORD=<switch_password>

python3 -m src.main \
  --cluster-ip <CLUSTER_IP> \
  --output-dir ./reports \
  --enable-port-mapping
```

### Complete Example

```bash
python3 -m src.main \
  --cluster-ip 10.143.11.202 \
  --username support \
  --output-dir ./reports \
  --enable-port-mapping \
  --node-user vastdata \
  --node-password vastdata \
  --switch-user cumulus \
  --switch-password Vastdata1!
```

## What Gets Collected

When port mapping is enabled, the generator collects:

1. **Node Inventory**
   - All CNodes and DNodes
   - IP addresses and hostnames

2. **Node MAC Addresses**
   - Interface MAC addresses from all nodes
   - Collected via clush from a single CNode

3. **Switch MAC Tables**
   - MAC address tables from all switches
   - Port associations for each MAC

4. **Port Mappings**
   - Correlates node interfaces to switch ports
   - Network type identification (ipl0, vip0, data)
   - Cross-connection detection

5. **Enhanced Designations**
   - Node side: CB1-CN1-R (CBox-1/CNode-1/Port-A)
   - Switch side: SWA-P12 (Switch-1/Port-12)
   - IPL/MLAG port identification

## Report Output

With port mapping enabled, the report includes:

1. **Logical Network Diagram**
   - Visual topology with connection lines
   - Shows all node-to-switch connections
   - IPL connections between switches

2. **Port Mapping Section**
   - Detailed tables of all connections
   - Per-switch port-to-device mapping
   - Network type and designation for each port

3. **Switch Configuration**
   - Port summary tables with usage details
   - Port speed and breakout information

## Without Port Mapping

If you run without `--enable-port-mapping`:

- Report generates successfully
- Network diagram shows devices but no connections
- Port Mapping section shows: "Port mapping data not available. Use --enable-port-mapping to collect."
- All other sections generate normally

## Troubleshooting

### SSH Connection Failures

**Symptom**: "Failed to collect port mapping: SSH connection error"

**Solutions**:
- Verify SSH connectivity: `ssh vastdata@<cnode_ip>`
- Check firewall rules
- Ensure correct credentials

### No Switches Found

**Symptom**: "No switches found - skipping port mapping"

**Solution**:
- Verify switches are configured in VAST cluster
- Check switch management IPs are reachable
- Ensure switches have been discovered by the cluster

### MAC Address Collection Fails

**Symptom**: "Failed to collect node MACs"

**Solutions**:
- Verify clush is installed on CNodes
- Check node SSH credentials
- Ensure nodes are accessible from the target CNode

### Switch MAC Table Empty

**Symptom**: "Collected MAC tables from X switches" but no mappings

**Solutions**:
- Verify switch MAC aging time hasn't expired
- Generate some traffic on the cluster
- Check switch MAC table: `net show bridge macs`

## Security Notes

1. **Credential Handling**
   - Passwords are never stored or logged
   - Use environment variables for automation
   - Consider using SSH keys where possible

2. **SSH Access**
   - Port mapping requires SSH access to nodes and switches
   - Ensure proper network segmentation
   - Use jump hosts if required

3. **Minimal Permissions**
   - Read-only access is sufficient
   - No configuration changes are made
   - Only `show` and `get` commands are used

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--enable-port-mapping` | Enable port mapping collection | Disabled |
| `--node-user` | SSH username for nodes | `vastdata` |
| `--node-password` | SSH password for nodes | Prompted |
| `--switch-user` | SSH username for switches | `cumulus` |
| `--switch-password` | SSH password for switches | Prompted |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VAST_NODE_PASSWORD` | SSH password for VAST nodes |
| `VAST_SWITCH_PASSWORD` | SSH password for switches |

## FAQ

### Q: Is port mapping required?

**A**: No, it's optional. The report generates successfully without it, but the network diagram will show devices without connections.

### Q: Can I use SSH keys instead of passwords?

**A**: Currently, the external port mapper uses password authentication. SSH key support is planned for a future release.

### Q: How long does port mapping collection take?

**A**: Typically 10-30 seconds depending on:
- Number of switches
- Number of nodes
- Network latency

### Q: What if I only have one switch?

**A**: Port mapping works with any number of switches (1 or more).

### Q: Does this work with non-Cumulus switches?

**A**: Currently, the port mapper is optimized for Cumulus Linux switches. Support for other switch OSes may be added in the future.

## Examples

### Development/Testing (No Port Mapping)

```bash
python3 -m src.main \
  --cluster-ip 10.143.11.202 \
  --username support \
  --output-dir ./reports
```

### Production (With Port Mapping)

```bash
python3 -m src.main \
  --cluster-ip 10.143.11.202 \
  --username support \
  --output-dir ./reports \
  --enable-port-mapping \
  --node-password vastdata \
  --switch-password Vastdata1!
```

### Automation Script

```bash
#!/bin/bash

# Set credentials
export VAST_USERNAME=support
export VAST_PASSWORD=$(cat /secure/vast-password.txt)
export VAST_NODE_PASSWORD=vastdata
export VAST_SWITCH_PASSWORD=$(cat /secure/switch-password.txt)

# Generate report with port mapping
python3 -m src.main \
  --cluster-ip "$1" \
  --output-dir ./reports \
  --enable-port-mapping \
  --verbose

echo "Report generated in ./reports/"
```

## See Also

- [Installation Guide](INSTALLATION-GUIDE.md)
- [Deployment Guide](DEPLOYMENT.md)
- [Permissions Guide](PERMISSIONS-GUIDE.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)
