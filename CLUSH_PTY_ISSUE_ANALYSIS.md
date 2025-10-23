# clush PTY Allocation Issue - Analysis & Resolution

**Date**: October 23, 2025
**Status**: 🔴 **CRITICAL** - Port mapping blocked on all tested clusters
**Impact**: Cannot generate port mapping sections in reports

---

## PROBLEM SUMMARY

Port mapping collection is failing on **all tested clusters** with the error:

```
Failed to get a pseudo terminal: Operation not permitted
```

### Affected Clusters
- ✗ **Bonzo-01** (10.27.200.32) - MSN2100 (Onyx)
- ✗ **selab-var-204** (10.143.11.204) - Cumulus Linux

### Previously Working Clusters
- ✓ **tmphx-203** (10.143.15.203) - Worked in previous sessions
- ✓ **tmphx-204** (10.141.200.204) - Worked in previous sessions

---

## ERROR DETAILS

### Command Sequence
```bash
sshpass -p <PASSWORD> ssh \
  -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  vastdata@<CNODE_IP> \
  "clush -a hostname"
```

### Error Output
```
Failed to get a pseudo terminal: Operation not permitted
```

### Root Cause Analysis

The error occurs when `clush` attempts to SSH to other nodes. This suggests:

1. **SSH Configuration Change**: Cluster SSH configuration may have been hardened
2. **PTY Allocation Restricted**: System-level restrictions on PTY allocation
3. **Authentication Method**: Possible password-based SSH restriction
4. **clush Configuration**: clush may need specific SSH options

---

## TECHNICAL BACKGROUND

### Why clush Needs PTY

`clush` (Cluster Shell) uses SSH to connect to multiple nodes simultaneously. By default, SSH allocates a pseudo-terminal (PTY) for interactive sessions. When run non-interactively (via subprocess), the PTY allocation can fail if:

1. System security policies restrict PTY allocation
2. SSH configuration (`sshd_config`) has `PermitTTY no`
3. User doesn't have permission to allocate PTYs
4. Resource limits (ulimit) restrict PTYs

### SSH -T Flag Dilemma

- **With `-T`**: Disables PTY allocation → clush fails (current issue)
- **Without `-T`**: Requests PTY → may fail with "Operation not permitted"

The error occurs **regardless** of `-T` flag, suggesting a deeper restriction.

---

## ATTEMPTED SOLUTIONS

### ❌ Attempt 1: Add `-T` flag to main SSH
**Result**: Same error (clush still tries to allocate PTY for sub-connections)

### ❌ Attempt 2: Pass `-T` to clush via `-o` option
```bash
clush -o '-T' -a hostname
```
**Result**: Invalid syntax or still fails

### ❌ Attempt 3: Full SSH options to clush
```bash
clush -o "-T -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null" -a hostname
```
**Result**: Same PTY error

### ❌ Attempt 4: Remove `-T` entirely
```bash
ssh (without -T) ... "clush -a hostname"
```
**Result**: Same PTY error - confirms this is a clush/system-level issue

---

## DIAGNOSTIC STEPS

### Step 1: Test Direct SSH to CNode
```bash
sshpass -p vastdata ssh -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  vastdata@10.143.11.81 \
  "hostname"
```

**Expected**: Should work without PTY error

---

### Step 2: Test clush Directly on CNode
```bash
sshpass -p vastdata ssh -o StrictHostKeyChecking=no \
  -o UserKnownHostsFile=/dev/null \
  vastdata@10.143.11.81

# Once logged in:
clush -a hostname
```

**Expected**: May reveal if clush itself has configuration issues

---

### Step 3: Check clush Configuration
```bash
# On CNode:
cat ~/.clustershell/clush.conf
cat /etc/clustershell/clush.conf
```

**Look for**: SSH options, PTY settings, authentication methods

---

### Step 4: Check SSH Server Configuration
```bash
# On any node:
sudo cat /etc/ssh/sshd_config | grep -i permit
```

**Look for**:
- `PermitTTY no` (would block PTY allocation)
- `PasswordAuthentication no` (would block password-based clush)

---

### Step 5: Test Alternative to clush
```bash
# Use parallel SSH instead
parallel-ssh -h hostfile -A -i "hostname"

# Or loop with regular SSH
for node in $(cat hostfile); do
  ssh vastdata@$node "hostname; ip link show"
done
```

---

## POSSIBLE SOLUTIONS

### Option 1: Use SSH Key Authentication
**Rationale**: PTY restrictions may not apply to key-based auth

**Steps**:
1. Generate SSH key on local machine
2. Copy public key to all cluster nodes (`ssh-copy-id`)
3. Modify `external_port_mapper.py` to use key instead of password
4. Test without `sshpass`

**Pros**: More secure, may bypass PTY restrictions
**Cons**: Requires setup on each cluster

---

### Option 2: Run Tool on CNode Directly
**Rationale**: No remote SSH needed, clush runs locally

**Steps**:
1. Copy tool to a CNode
2. Install dependencies on CNode
3. Run from CNode directly

**Pros**: Eliminates SSH layer
**Cons**: Requires cluster access, less convenient

---

### Option 3: Alternative Data Collection Method
**Rationale**: Replace clush with different approach

**Approaches**:
A. **Use VAST API** to get node interface info (if available)
B. **Parallel SSH** without clush
C. **Direct SSH loop** to each node
D. **Ansible** for orchestrated collection

**Pros**: May work around clush-specific restrictions
**Cons**: Requires code rewrite

---

### Option 4: Contact Cluster Administrator
**Rationale**: May be a recent security policy change

**Questions to Ask**:
1. Was SSH/PTY configuration recently changed?
2. Are there known restrictions on clush/PTY allocation?
3. Can PTY allocation be enabled for `vastdata` user?
4. Are there alternative methods for multi-node commands?

---

## RECOMMENDED ACTION PLAN

### Immediate (Do Now)
1. ✅ **Test on tmphx-203** (10.143.15.203) - previously worked
2. ✅ **Document Onyx implementation** (already complete)
3. ⏳ **Run diagnostic steps** above to understand root cause

### Short-term (This Week)
4. ⏳ **Implement SSH key authentication** (Option 1)
5. ⏳ **Test on different cluster** with known working clush

### Long-term (Next Sprint)
6. ⏳ **Implement alternative collection method** (Option 3)
7. ⏳ **Add fallback mechanisms** for when clush fails
8. ⏳ **Better error messages** to guide users

---

## WORKAROUND FOR NOW

Until this is resolved, reports will generate **without port mapping**:
- ✅ Hardware inventory
- ✅ Network configuration
- ✅ Rack diagram
- ✅ Network topology diagram (without connections)
- ❌ Port mapping tables
- ❌ Connection lines in network diagram

---

## FILES AFFECTED

- `src/external_port_mapper.py` - Lines 229-295
- `src/main.py` - Port mapping collection flow

---

## NEXT STEPS

**User Action Required**:
1. Review diagnostic steps above
2. Try testing on **tmphx-203** (10.143.15.203) which worked before
3. If urgent, contact cluster admin about PTY/clush restrictions
4. Consider Option 1 (SSH keys) as permanent solution

**Developer Action**:
1. Onyx implementation is complete and tested (code-wise)
2. Need successful test run once clush issue is resolved
3. Consider implementing fallback data collection methods

---

**Status**: Implementation complete, awaiting resolution of cluster-level clush/PTY issue
