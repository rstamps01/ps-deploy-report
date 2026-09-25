---
name: CNode Management Status Check
overview: Update the `_check_cnode_status` health check in `health_checker.py` to recognize the Management CNode (VMS) as intentionally inactive, passing the check for that node while still failing for any other inactive CNodes.
todos:
  - id: cnode-mgmt-check
    content: Update _check_cnode_status to recognize Management CNode as intentionally inactive
    status: pending
  - id: cnode-mgmt-verify
    content: Run test suite to verify no regressions
    status: pending
isProject: false
---

# CNode Management Status Check Fix

## Problem

In `_check_cnode_status()` ([src/health_checker.py](src/health_checker.py) lines 1037-1098), any CNode with `state != ACTIVE` is treated as a failure. In larger clusters, the dedicated Management CNode (VMS) is intentionally inactive (`is_mgmt: True` in the API response). This causes a false-positive failure.

## Change

In the loop at line 1054-1060, when a CNode is inactive, check `node.get("is_mgmt", False)`. If `True`, exclude it from the `inactive` list and track it separately as `mgmt_inactive`. Adjust the result logic:

- If only the Management CNode is inactive and all others are active: **PASS**, with message `"All {total} CNodes healthy (VMS on {mgmt_name})"`
- If any non-management CNode is inactive: **FAIL**, listing only the non-management inactive CNodes in the message
- The `details` dict gets a new `"mgmt_cnode"` key with the management node name for transparency

## Code Location

```python
# src/health_checker.py, _check_cnode_status(), lines 1051-1068
# Current:
inactive = []
for node in data:
    name = node.get("name", node.get("id", "unknown"))
    state = str(node.get("state", node.get("status", ""))).upper()
    if state != "ACTIVE":
        inactive.append(name)

# Proposed:
inactive = []
mgmt_inactive = None
for node in data:
    name = node.get("name", node.get("id", "unknown"))
    state = str(node.get("state", node.get("status", ""))).upper()
    if state != "ACTIVE":
        if node.get("is_mgmt", False):
            mgmt_inactive = name
        else:
            inactive.append(name)
```

Then adjust the result messages to account for `mgmt_inactive` and include it in `details`.

## Files Changed

- [src/health_checker.py](src/health_checker.py) -- `_check_cnode_status()` method only
