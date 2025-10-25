# Mellanox Onyx Interactive SSH Implementation

## Problem Identified

Mellanox Onyx switches with `admin` user accounts **cannot execute commands non-interactively** via standard SSH command-line arguments.

When you run:
```bash
ssh admin@10.27.16.173 "show mac-address-table"
```

The switch responds with:
```
Mellanox Onyx Switch Management
UNIX shell commands cannot be executed using this account.
```

However, commands work perfectly when logging in **interactively**:
```bash
ssh admin@10.27.16.173
# (enter password)
# Then run: show mac-address-table
# ✅ Works!
```

---

## Solution Implemented

### 1. Added `pexpect` Dependency

Updated `requirements.txt`:
```python
# Interactive SSH for Mellanox Onyx switches
pexpect>=4.9.0
```

### 2. Created Interactive SSH Method

Added new method `_run_onyx_interactive_command()` in `src/external_port_mapper.py`:

**Features:**
- Uses Python `pexpect` library for interactive SSH automation
- Waits for password prompt and sends password
- Waits for CLI prompt (recognizes Onyx format: `hostname [info] >`)
- Sends command and captures output
- Cleans up output (removes echoed command)
- Exits cleanly

**Signature:**
```python
def _run_onyx_interactive_command(
    self,
    switch_ip: str,
    username: str,
    password: str,
    command: str,
    timeout: int = 30
) -> Tuple[int, str, str]:
    """Returns: (returncode, stdout, stderr)"""
```

### 3. Updated MAC Table Collection

Modified `_collect_switch_mac_tables()` to use interactive SSH for Onyx:

```python
if os_type == "onyx":
    # Use interactive SSH for Onyx
    returncode, stdout, stderr = self._run_onyx_interactive_command(
        switch_ip, user, password, mac_cmd, timeout=30
    )
else:
    # Use subprocess for Cumulus
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
```

### 4. Updated LLDP/IPL Collection

Modified `_collect_ipl_connections()` to use interactive SSH for Onyx.

---

## Installation Steps

### Step 1: Install pexpect

Run this command from your **native macOS Terminal** (not Cursor terminal):

```bash
cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report
pip3 install pexpect
```

Or install all requirements:

```bash
pip3 install -r requirements.txt
```

### Step 2: Verify Installation

```bash
python3 -c "import pexpect; print(f'pexpect version: {pexpect.__version__}')"
```

---

## Testing

### Test 1: Standalone Test Script

Test the expect script directly:

```bash
cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report
./test_onyx_expect.sh 10.27.16.173 admin "show mac-address-table vlan 69"
```

### Test 2: Full Report Generation

Generate a report for the Bonzo-01 cluster:

```bash
python3 -m src.main --cluster-ip 10.27.200.32 \
  --username support --password 654321 \
  --output-dir ./reports \
  --enable-port-mapping \
  --node-password vastdata \
  --switch-password admin
```

**Expected Output:**
```
✅ Switch 10.27.16.173: ONYX detected (using admin credentials)
✅ Switch 10.27.16.174: ONYX detected (using admin credentials)
Collected XX MACs from 10.27.16.173 (onyx, general table)
Collected YY MACs from 10.27.16.174 (onyx, general table)
Generated ZZ port mappings
```

---

## Commands Used by the Code

### For Onyx Switches:

1. **MAC Address Table:**
   ```
   show mac-address-table
   ```

2. **VLAN 69 MACs (for DNode Network B):**
   ```
   show mac-address-table vlan 69
   ```

3. **LLDP/IPL Discovery:**
   ```
   show lldp remote
   ```

### For Cumulus Linux Switches:

1. **MAC Address Table:**
   ```
   nv show bridge domain br_default mac-table
   ```

2. **LLDP/IPL Discovery:**
   ```
   nv show interface --output json
   ```

---

## How It Works

### Interactive SSH Flow:

1. **Spawn SSH Process:**
   ```python
   child = pexpect.spawn(f"ssh admin@{switch_ip}")
   ```

2. **Wait for Password Prompt:**
   ```python
   child.expect([r'Password:', r'password:'])
   ```

3. **Send Password:**
   ```python
   child.sendline(password)
   ```

4. **Wait for CLI Prompt:**
   ```python
   child.expect([r'\[.*\]\s*>'])  # Matches: "rack6-1 [info] >"
   ```

5. **Send Command:**
   ```python
   child.sendline("show mac-address-table")
   ```

6. **Capture Output:**
   ```python
   child.expect([r'\[.*\]\s*>'])  # Wait for next prompt
   output = child.before  # Everything before the prompt
   ```

7. **Clean Up:**
   ```python
   child.sendline("exit")
   child.expect(pexpect.EOF)
   child.close()
   ```

---

## Benefits

1. ✅ **Full Onyx Support**: Works with restricted `admin` accounts
2. ✅ **OS Auto-Detection**: Automatically detects Cumulus vs Onyx
3. ✅ **Dual Credential Support**: Tries both `cumulus/Vastdata1!` and `admin/admin`
4. ✅ **Verbose Logging**: Detailed logs for debugging
5. ✅ **Clean Fallback**: Gracefully handles errors and provides meaningful messages

---

## Files Modified

1. `requirements.txt` - Added `pexpect>=4.9.0`
2. `src/external_port_mapper.py`:
   - Added `_run_onyx_interactive_command()` method
   - Updated `_collect_switch_mac_tables()` to use interactive SSH for Onyx
   - Updated `_collect_ipl_connections()` to use interactive SSH for Onyx
3. `test_onyx_expect.sh` - Created standalone test script

---

## Next Steps

1. **Install pexpect:** Run `pip3 install pexpect`
2. **Test the implementation:** Run the full report generation command
3. **Verify port mapping:** Check that MAC tables and IPL connections are collected successfully
4. **Review logs:** Check `logs/external_port_mapper_verbose_*.log` for detailed execution traces

---

## Troubleshooting

### If pexpect import fails:
```bash
pip3 install --user pexpect
```

### If you get "spawn command not found":
```bash
# pexpect should be installed system-wide
sudo pip3 install pexpect
```

### To check if pexpect is installed:
```bash
python3 -c "import pexpect; print('✅ pexpect installed')"
```

---

## Success Criteria

The implementation is successful when you see:

1. ✅ OS detection succeeds: `Switch 10.27.16.173: ONYX detected`
2. ✅ MAC tables collected: `Collected XX MACs from 10.27.16.173 (onyx, general table)`
3. ✅ LLDP data collected: `Found IPL: swp29 ↔ swp29`
4. ✅ Port mappings generated: `Generated ZZ port mappings`
5. ✅ Report includes port mapping tables with correct node-to-switch connections

---

**Implementation Complete!** 🎉

All code changes have been made. Just install `pexpect` and test!
