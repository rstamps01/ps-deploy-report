# SSH Key Setup Required for Port Mapping

**Date**: October 23, 2025
**Status**: Port mapping now requires SSH keys to be configured

---

## SUMMARY

Based on your feedback that you use `ssh` without `sshpass`, I've updated the tool to use SSH **without password authentication**. This means the tool now relies on SSH keys being configured.

---

## CHANGES MADE

### Removed `sshpass` from ALL SSH commands

**Before (password auth with sshpass)**:
```bash
sshpass -p <PASSWORD> ssh -o StrictHostKeyChecking=no \
  -o "UserKnownHostsFile /dev/null" vastdata@<IP> "clush -a hostname"
```

**After (SSH key auth)**:
```bash
ssh -o StrictHostKeyChecking=no \
  -o "UserKnownHostsFile /dev/null" vastdata@<IP> "clush -a hostname"
```

---

## SSH KEY SETUP REQUIRED

For port mapping to work, you need SSH keys configured for:

### 1. **VAST Nodes** (vastdata user)
```bash
# Generate SSH key (if you don't have one)
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa

# Copy key to a CNode (you'll be prompted for password once)
ssh-copy-id vastdata@<CNODE_IP>

# Example:
ssh-copy-id vastdata@10.143.11.81

# Verify it works without password
ssh vastdata@10.143.11.81 hostname
```

### 2. **Switches** (cumulus or admin user)
```bash
# For Cumulus Linux switches
ssh-copy-id cumulus@<SWITCH_IP>

# For Mellanox Onyx switches
ssh-copy-id admin@<SWITCH_IP>

# Verify
ssh cumulus@10.143.11.153 "nv show system"
```

---

## ALTERNATIVE: Revert to Password Authentication

If SSH keys are not desired, we can revert to using `sshpass` with passwords.

### To Revert:
1. Restore `sshpass` commands in `src/external_port_mapper.py`
2. Re-enable credential validation in `src/main.py`
3. Provide `--node-password` and `--switch-password` on command line

---

## CURRENT STATUS

The code changes are complete, but SSH authentication is failing because:
- SSH keys are not configured on the target nodes/switches, OR
- The SSH key setup is incomplete

---

## TESTING STEPS

### 1. Verify SSH Key Access to Nodes
```bash
# Test direct SSH (should work without password prompt)
ssh -o StrictHostKeyChecking=no vastdata@10.143.11.81 hostname
```

**Expected**: Hostname prints without password prompt

### 2. Verify clush Works
```bash
# Test clush from a CNode
ssh -o StrictHostKeyChecking=no vastdata@10.143.11.81 "clush -a hostname"
```

**Expected**: Lists all node hostnames with their IPs

### 3. Run Report Generation
```bash
python3 -m src.main \
  --cluster-ip 10.143.11.204 \
  --username support \
  --password 654321 \
  --enable-port-mapping \
  --output-dir ./reports
```

**Expected**: Port mapping succeeds and report includes connections

---

## QUESTIONS FOR YOU

1. **Do you have SSH keys set up** for the `vastdata` user on cluster nodes?

2. **When you run the command that works**, are you using:
   - SSH keys (no password prompt)?
   - OR password-based auth that's somehow cached?
   - OR some other authentication method?

3. **Would you prefer**:
   - Option A: Set up SSH keys (more secure, no passwords)
   - Option B: Revert to sshpass with passwords (simpler, less secure)

---

## FILES MODIFIED

- `src/external_port_mapper.py`
  - Removed `sshpass` from node SSH commands (lines ~231, ~279)
  - Removed `sshpass` from switch SSH commands (lines ~355, ~375, ~431, ~485)

- `src/main.py`
  - Disabled credential validation for port mapping (lines ~376-381)

---

##  NEXT STEPS

Please let me know:
1. Your authentication setup (SSH keys vs passwords)
2. Whether you want to proceed with SSH keys or revert to passwords
3. Any SSH errors you see when testing manually
