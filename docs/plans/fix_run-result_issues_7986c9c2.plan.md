---
name: Fix run-result issues
overview: "Resolve the tool-side defects surfaced by the 2026-07-28 VAST-PI-01 run log and validation bundle: Teleport node-SSH not routed through the tunnel (network_config + support_tool failures), garbled switch-config filenames, Onyx health-check auth, a vnetmap-status format bug, and a blank bundle version."
todos:
  - id: teleport-ssh-routing
    content: "Route node-SSH through the Teleport tunnel in network_config_workflow.py and support_tool_workflow.py (+ tool_manager port threading): add _ssh_host()/_ssh_port(), use host=ssh_host or cluster_ip and pass port=ssh_port on all run_ssh_command/deploy calls."
    status: completed
  - id: strip-ansi-escapes
    content: Strip ANSI/terminal control sequences centrally in run_interactive_ssh (ssh_adapter.py) and sanitize the derived switch hostname into a safe filename slug in switch_config_workflow.py (lines 377/639).
    status: completed
  - id: onyx-health-creds
    content: Make health_checker switch checks use build_switch_credential_combos (admin/admin fallback) and reuse the winning (user,password) for MLAG/NTP/config-readability checks.
    status: completed
  - id: vnetmap-status-format
    content: Diagnose and fix the '/api/vnetmap-status' 'not all arguments converted during string formatting' error (app.py ~2033); add exc_info to locate, correct the format call, add regression test.
    status: completed
  - id: bundle-version
    content: Populate the detected cluster version into the validation bundle SUMMARY/manifest in result_bundler.py.
    status: completed
  - id: onyx-vnetmap-messaging
    content: Emit a clear, actionable message when the Onyx switch web/JSON API is unavailable/rejects creds (instead of raw tracebacks) and document the web-API credential requirement.
    status: completed
  - id: validation
    content: Run quality gates (pytest/flake8/black/mypy), add regression tests, and re-run a Teleport-mode one-shot against an Onyx cluster to confirm fixes.
    status: completed
isProject: false
---

## Fix run-result issues (VAST-PI-01, 2026-07-28)

Analysis of [result-output.txt](import/Assets-2026-07-28/result-output.txt) and `validation_bundle_VAST-PI-01_20260728_130442.zip` (`SUMMARY.md`: 4 categories FAILED/degraded; health 23P/1F/5W/1E). Root causes traced to specific files/lines below. Scope = tool defects only; genuine cluster findings (inactive cnodes, alarms, firmware mismatch, missing policies) are working as intended and excluded.

### 1. Route Teleport node-SSH through the tunnel (HIGH — fixes 2 FAILED categories)

Both workflows dial the real cluster IP instead of the forwarded tunnel endpoint (`ssh_host`/`ssh_port` supplied by oneshot at [oneshot_runner.py:286-288](src/oneshot_runner.py)):

- [network_config_workflow.py:265](src/workflows/network_config_workflow.py) and its other `run_ssh_command(host, ...)` calls (`host = cluster_ip`, no `port`/jump) → "SSH command timed out after 15s".
- [support_tool_workflow.py:264-284](src/workflows/support_tool_workflow.py) → `tool_manager.deploy_tool_to_cnode(...)` → [tool_manager.py:199-205](src/tool_manager.py) `mkdir` with no tunnel port → "Failed to create directory: SSH command timed out after 30s".

Fix: add `_ssh_host()/_ssh_port()` helpers (mirroring [vnetmap_workflow.py:129-138](src/workflows/vnetmap_workflow.py)) to both workflows; resolve `host = ssh_host or cluster_ip` and pass `port=ssh_port` on every `run_ssh_command`, and thread `port` into `deploy_tool_to_cnode`/`_ensure_remote_dir`.

### 2. Strip terminal escapes from interactive SSH output (MEDIUM — fixes garbled filenames + parse)

Bundle filenames like `switch_^[[?1h^[=_10_6_160_7_...txt` come from raw Onyx `show version` output used as hostname at [switch_config_workflow.py:377](src/workflows/switch_config_workflow.py) then in the filename at [:639](src/workflows/switch_config_workflow.py). `run_interactive_ssh` ([ssh_adapter.py:206](src/utils/ssh_adapter.py)) never strips escapes.

Fix: strip ANSI/terminal control sequences (`\x1b[...`, `\x1b=`, `\x1b[?..h/l`) centrally in `run_interactive_ssh` output; additionally sanitize the derived hostname into a safe filename slug (fallback to IP) at line 377/639.

### 3. Use full credential combos for Onyx health checks (HIGH — clears 1 ERROR + 2 WARN)

`health_checker` probes only `username` (default `cumulus`) × candidates ([health_checker.py:2807/2857](src/health_checker.py)) and never tries `admin`, so MLAG/NTP/Config-Readability fail on Onyx even though `switch_config` connected. Fix: drive the probe from `build_switch_credential_combos(username, candidate_list)` ([ssh_adapter.py:58](src/utils/ssh_adapter.py)) so `admin/admin` is attempted; store the winning `(user, password)` in `password_by_ip` and reuse it for MLAG/NTP/config checks.

### 4. Fix `/api/vnetmap-status` string-format error (LOW)

Log line 79 `not all arguments converted during string formatting`; handler at [app.py:2033](src/app.py) hides the location. Fix: temporarily add `exc_info=True`, run the status path to capture the traceback, correct the offending `%`/format call, then add a regression test in `tests/`.

### 5. Populate cluster version in the bundle SUMMARY (LOW)

`SUMMARY.md` shows blank `**Version:**` although the run detected `<ip>...`. Fix: thread the detected cluster version into the bundle summary/manifest in [result_bundler.py](src/result_bundler.py).

### 6. Clear messaging for Onyx vnetmap web-API blocker (MEDIUM — messaging only)

vnetmap "Unable to determine suitable switch API" for `<ip>/.8` causes vnetmap FAILED and the ~70 "MAC not found in any switch table" warnings. This is a switch-side web/JSON API credential/HTTP-disabled condition, not a code bug. Fix: detect web-API unavailability and emit one clear, actionable message (verify web-API user/password, HTTPS enabled) instead of raw Python tracebacks; note the requirement in `docs/`.

### Validation

- `python3 -m pytest tests/ -v` (with existing `--timeout`), `flake8 src/ tests/`, `black --check --line-length 120 src/ tests/`, `mypy src/ --ignore-missing-imports`.
- Add regression tests: tunnel-routing kwargs for network_config/support_tool, escape-stripping in `run_interactive_ssh`, Onyx combo usage in health_checker, and the vnetmap-status format fix.
- Re-run a Teleport-mode one-shot against an Onyx cluster; confirm network_config + support_tool succeed, bundle filenames are clean, health MLAG/NTP/config pass, and SUMMARY version is populated.

### Out of scope (no code change)

Inactive CNodes (128-14/15/16), critical/major alarms, firmware `cnode.os_version` mismatch, missing protection policies, DNS/AD/LDAP not configured — all correctly reported cluster conditions.
