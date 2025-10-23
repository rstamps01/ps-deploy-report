# Mellanox Onyx Commands for Port Map Generation

## Date: October 23, 2025
## Purpose: Identify Onyx CLI commands equivalent to Cumulus for port mapping

---

## CURRENT IMPLEMENTATION (Cumulus Linux)

### Commands Used
1. **MAC Address Table**: `nv show bridge domain br_default mac-table`
2. **Interface Status**: `nv show interface`

### Data Extracted

#### From MAC Address Table
- **MAC Address**: Physical address of connected device
- **VLAN**: VLAN ID
- **Interface**: Switch port (e.g., `swp1`, `swp9`)
- **Entry Type**: Dynamic or permanent

**Example Output**:
```
entry-id  MAC address        vlan  interface   remote-dst  src-vni  entry-type  last-update        age
1         7c:8c:09:eb:ec:51  69    swp1                                         0:00:58            0:03:39
14        7c:8c:09:4d:75:7f  69    swp9                             0:00:42     13 days, 8:47:06
15        2c:5e:ab:24:a4:38  1     swp9        permanent             57 days, 5:52:02
```

#### From Interface Status
- **Interface Name**: Port identifier
- **State**: Up/Down
- **Speed**: Link speed (e.g., 100G, 50G)
- **MTU**: Maximum transmission unit
- **Remote Host**: LLDP neighbor (for IPL detection)

---

## MELLANOX ONYX EQUIVALENT COMMANDS

### 1. MAC Address Table

**Onyx Command**:
```bash
show mac-address-table
```

**Alternative Commands**:
```bash
# Show dynamic MAC entries only
show mac-address-table dynamic

# Show MAC table for specific VLAN
show mac-address-table vlan <vlan-id>

# Show MAC table for specific interface
show mac-address-table interface ethernet 1/1
```

**Expected Output Format**:
```
Vlan        Mac Address       Type        Interface
----        -----------       ----        ---------
69          7c8c.09eb.ec51    dynamic     Eth1/1
69          7c8c.094d.757f    dynamic     Eth1/9
1           2c5e.ab24.a438    static      Eth1/9
```

**Data to Extract**:
- VLAN ID
- MAC Address (convert format: `7c8c.09eb.ec51` → `7c:8c:09:eb:ec:51`)
- Type (dynamic/static) → maps to entry_type
- Interface (Eth1/X) → maps to port

---

### 2. Interface Status and Configuration

**Onyx Command**:
```bash
show interfaces ethernet status
```

**Alternative/Additional Commands**:
```bash
# Detailed interface information
show interfaces ethernet

# Brief interface status
show interfaces status

# Specific interface details
show interfaces ethernet 1/1
```

**Expected Output Format**:
```
Port        Description    Status  Speed      Duplex  Auto-Neg
----------- -------------- ------- ---------- ------- --------
Eth1/1      CNode-1-A      Up      100000     Full    Off
Eth1/2      CNode-1-B      Up      100000     Full    Off
Eth1/9      DNode-1-A      Up      100000     Full    Off
Eth1/10     DNode-1-B      Up      100000     Full    Off
Eth1/29     IPL-to-SW2     Up      200000     Full    Off
```

**Data to Extract**:
- Port/Interface name
- Status (Up/Down)
- Speed (convert to readable format: 100000 → 100G)
- Description (may contain device identifiers)

---

### 3. LLDP Neighbors (for IPL Detection)

**Onyx Command**:
```bash
show lldp interfaces ethernet remote
```

**Alternative Commands**:
```bash
# All LLDP neighbors
show lldp neighbors

# Detailed LLDP information
show lldp neighbors detail

# Specific interface
show lldp interfaces ethernet 1/29 remote
```

**Expected Output Format**:
```
Local Interface  Chassis ID         Port ID      System Name
---------------- ------------------ ------------ ---------------
Eth1/29          50:6b:4b:12:34:56  Eth1/29      rack6-2
Eth1/30          50:6b:4b:12:34:56  Eth1/30      rack6-2
```

**Data to Extract**:
- Local Interface (source port for IPL)
- System Name (remote switch hostname)
- Port ID (remote port for IPL)

---

### 4. VLAN Information

**Onyx Command**:
```bash
show vlan
```

**Expected Output Format**:
```
VLAN   Name         Status  Ports
------ ------------ ------- ----------------------------------
1      default      Active  Eth1/1-1/16, Eth1/25-1/32
69     data-vlan    Active  Eth1/1-1/24
```

**Data to Extract**:
- VLAN ID
- Associated ports

---

## COMPARISON: CUMULUS vs ONYX

| Purpose | Cumulus Linux | Mellanox Onyx |
|---------|--------------|---------------|
| **MAC Table** | `nv show bridge domain br_default mac-table` | `show mac-address-table` |
| **Interface Status** | `nv show interface` | `show interfaces ethernet status` |
| **LLDP Neighbors** | `nv show interface` (includes LLDP) | `show lldp interfaces ethernet remote` |
| **VLAN Info** | `nv show bridge domain` | `show vlan` |
| **Port Format** | `swp1`, `swp9` | `Eth1/1`, `Eth1/9` or `ethernet 1/1` |
| **MAC Format** | `7c:8c:09:eb:ec:51` | `7c8c.09eb.ec51` |

---

## IMPLEMENTATION REQUIREMENTS

### 1. Detect Switch Type

Before running commands, detect if the switch is running Cumulus or Onyx:

```python
def detect_switch_os(switch_ip: str, switch_user: str, switch_password: str) -> str:
    """
    Detect switch OS by running a test command.

    Returns:
        'cumulus' or 'onyx' or 'unknown'
    """
    # Try Cumulus command
    result = run_ssh_command(switch_ip, switch_user, switch_password, "nv show version")
    if result.returncode == 0 and "Cumulus" in result.stdout:
        return "cumulus"

    # Try Onyx command
    result = run_ssh_command(switch_ip, switch_user, switch_password, "show version")
    if result.returncode == 0 and ("Onyx" in result.stdout or "MLNX" in result.stdout):
        return "onyx"

    return "unknown"
```

### 2. Parse MAC Address Format

Onyx uses different MAC address format than Cumulus:

```python
def normalize_mac_address(mac: str) -> str:
    """
    Convert MAC address to standard format.

    Cumulus: 7c:8c:09:eb:ec:51 (already standard)
    Onyx: 7c8c.09eb.ec51 → 7c:8c:09:eb:ec:51

    Returns:
        MAC address in format: xx:xx:xx:xx:xx:xx
    """
    # Remove dots and convert to colon format
    mac = mac.replace(".", "")

    # Insert colons every 2 characters
    if len(mac) == 12:
        return ":".join([mac[i:i+2] for i in range(0, 12, 2)])

    # Already in colon format or invalid
    return mac
```

### 3. Parse Interface Names

Onyx uses different interface naming:

```python
def normalize_interface_name(interface: str, switch_os: str) -> str:
    """
    Normalize interface names for consistency.

    Cumulus: swp1, swp9 (already standard)
    Onyx: Eth1/1, ethernet 1/1 → Eth1/1

    Returns:
        Normalized interface name
    """
    if switch_os == "onyx":
        # Standardize Onyx interface names
        # ethernet 1/1 → Eth1/1
        # Eth1/1 → Eth1/1
        interface = interface.replace("ethernet", "Eth")
        interface = interface.replace(" ", "")
        return interface

    return interface
```

### 4. Update External Port Mapper

Add Onyx support to `src/external_port_mapper.py`:

```python
def _collect_switch_macs(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """
    Collect MAC addresses from switches (supports Cumulus and Onyx).
    """
    switch_macs = {}

    for switch_ip in self.switch_ips:
        try:
            # Detect switch OS
            switch_os = self._detect_switch_os(switch_ip)

            if switch_os == "cumulus":
                cmd_mac_table = "nv show bridge domain br_default mac-table"
                parser = self._parse_cumulus_mac_table
            elif switch_os == "onyx":
                cmd_mac_table = "show mac-address-table"
                parser = self._parse_onyx_mac_table
            else:
                self.logger.warning(f"Unknown switch OS for {switch_ip}, skipping")
                continue

            # Run command
            cmd = [
                "sshpass", "-p", self.switch_password,
                "ssh", "-o", "StrictHostKeyChecking=no",
                "-o", "UserKnownHostsFile=/dev/null",
                "-T",
                f"{self.switch_user}@{switch_ip}",
                cmd_mac_table,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                switch_macs[switch_ip] = parser(result.stdout)
                self.logger.info(
                    f"Collected {len(switch_macs[switch_ip])} MACs from {switch_ip} ({switch_os})"
                )

        except Exception as e:
            self.logger.error(f"Error collecting MACs from {switch_ip}: {e}")
            continue

    return switch_macs
```

### 5. Onyx MAC Table Parser

```python
def _parse_onyx_mac_table(self, output: str) -> Dict[str, Dict[str, Any]]:
    """
    Parse Mellanox Onyx MAC table output.

    Expected format:
    Vlan        Mac Address       Type        Interface
    ----        -----------       ----        ---------
    69          7c8c.09eb.ec51    dynamic     Eth1/1
    69          7c8c.094d.757f    dynamic     Eth1/9
    1           2c5e.ab24.a438    static      Eth1/9

    Returns:
        Dict mapping MACs to {port, vlan, entry_type}
    """
    mac_table = {}

    for line in output.split("\n"):
        # Skip header and separator lines
        if line.startswith("Vlan") or line.startswith("----"):
            continue

        # Parse MAC table entries
        parts = line.split()
        if len(parts) >= 4:
            try:
                vlan = parts[0]
                mac_onyx = parts[1]  # Format: 7c8c.09eb.ec51
                entry_type = parts[2]  # dynamic or static
                interface = parts[3]   # Eth1/1

                # Normalize MAC address format
                mac = self._normalize_mac_address(mac_onyx)

                # Validate MAC format (after normalization)
                if re.match(r"^[0-9a-f:]{17}$", mac):
                    # Only include Ethernet interfaces
                    if interface.startswith("Eth"):
                        mac_table[mac] = {
                            "port": interface,
                            "vlan": vlan,
                            "entry_type": "permanent" if entry_type == "static" else None,
                        }
            except (IndexError, ValueError):
                continue

    return mac_table
```

---

## TESTING APPROACH

### 1. Manual Command Testing

Before implementing, manually test commands on actual Onyx switches:

```bash
# SSH to Onyx switch
ssh <username>@<switch-ip>

# Test MAC table command
show mac-address-table

# Test interface status
show interfaces ethernet status

# Test LLDP neighbors
show lldp interfaces ethernet remote

# Test VLAN info
show vlan
```

### 2. Capture Output Examples

Save actual output to files for parser development:

```bash
# From Onyx switch
show mac-address-table > onyx_mac_table.txt
show interfaces ethernet status > onyx_interface_status.txt
show lldp interfaces ethernet remote > onyx_lldp_neighbors.txt
```

### 3. Parser Unit Tests

Create unit tests with captured output:

```python
def test_parse_onyx_mac_table():
    sample_output = """
Vlan        Mac Address       Type        Interface
----        -----------       ----        ---------
69          7c8c.09eb.ec51    dynamic     Eth1/1
69          7c8c.094d.757f    dynamic     Eth1/9
1           2c5e.ab24.a438    static      Eth1/9
"""

    result = _parse_onyx_mac_table(sample_output)

    assert len(result) == 3
    assert result["7c:8c:09:eb:ec:51"]["port"] == "Eth1/1"
    assert result["7c:8c:09:eb:ec:51"]["vlan"] == "69"
```

---

## CREDENTIALS

### Onyx Default Credentials

- **Username**: `admin`
- **Password**: `admin`

### VAST Configuration

For VAST deployments with Mellanox switches running Onyx:
- **Username**: `admin`
- **Password**: `admin`

**CLI Arguments**:
```bash
--switch-user admin
--switch-password admin
```

### Comparison: Cumulus vs Onyx Credentials

| Switch OS | Username | Password |
|-----------|----------|----------|
| **Cumulus Linux** | `cumulus` | `Vastdata1!` |
| **Mellanox Onyx** | `admin` | `admin` |

---

## SUMMARY

### Commands Needed

| Data | Cumulus Command | Onyx Command |
|------|----------------|--------------|
| **MAC Addresses** | `nv show bridge domain br_default mac-table` | `show mac-address-table` |
| **Interface Status** | `nv show interface` | `show interfaces ethernet status` |
| **LLDP/IPL** | `nv show interface` | `show lldp interfaces ethernet remote` |
| **VLANs** | `nv show bridge domain` | `show vlan` |

### Implementation Steps

1. ✅ Document Onyx commands (this file)
2. ⏳ Add OS detection to `external_port_mapper.py`
3. ⏳ Add Onyx MAC table parser
4. ⏳ Add Onyx interface status parser
5. ⏳ Add Onyx LLDP parser
6. ⏳ Add MAC address normalization
7. ⏳ Add interface name normalization
8. ⏳ Update CLI to support different switch credentials
9. ⏳ Test with actual Onyx switches
10. ⏳ Update documentation

---

## NEXT STEPS

1. **Obtain Access**: Get credentials for Onyx switch in test environment
2. **Capture Output**: Run commands manually and save output samples
3. **Implement Parsers**: Write parsing functions for Onyx output format
4. **Test Integration**: Verify port mapping works end-to-end with Onyx
5. **Document**: Update user documentation with Onyx support

---

## REFERENCES

- Mellanox Onyx Operating System Documentation
- VAST Data As-Built Report Project
- `src/external_port_mapper.py` (current Cumulus implementation)

**Generated**: October 23, 2025
**Status**: Documentation Complete, Implementation Pending
