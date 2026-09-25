---
name: Test Coverage Extension Plan
overview: Extend automated test coverage for Health Check, Advanced Ops, and Workflow modules, targeting the 1,987 uncovered lines that represent 36% of all uncovered code, aiming to raise overall coverage from 54% to ~62-65%.
todos:
  - id: ws-a
    content: "WS-A: Add ~20 tests for advanced_ops.py orchestration (lifecycle, run_step, helpers)"
    status: completed
  - id: ws-b
    content: "WS-B: Add ~25 tests for health_checker.py API check branches and SSH node checks"
    status: completed
  - id: ws-c
    content: "WS-C: Add ~12 tests for health_checker.py switch checks and remediation edge cases"
    status: completed
  - id: ws-d
    content: "WS-D: Add ~35 tests for workflow step execution and parsing logic across 6 modules"
    status: completed
  - id: ws-e
    content: "WS-E: Run full suite, verify 0 failures, measure coverage, raise threshold if warranted"
    status: completed
isProject: false
---

# Test Coverage Extension: Health Check, Advanced Ops, Workflows

Current: 470 tests, 54.1% overall coverage. Target: ~62-65% overall (+8-11pp).

The work is organized into 5 parallel work streams targeting the highest-impact, most testable code paths. Each stream is self-contained and can be developed independently.

---

## WS-A: Advanced Ops Orchestration (~20 tests)

**File:** [tests/test_advanced_ops.py](tests/test_advanced_ops.py) (append)
**Target:** [src/advanced_ops.py](src/advanced_ops.py) -- 51% -> ~80%

Key test classes to add:

- **TestWorkflowLifecycle** (~8 tests): `start_workflow` success, duplicate start blocked, `run_all_steps` success/cancel/error, `cancel()` when not running, `reset()` clears state
- **TestRunStep** (~7 tests): no active workflow, invalid step ID, cancel before step, success path, failure path, no instance fallback, exception in step
- **TestAdvancedOpsHelpers** (~5 tests): `get_workflow_steps` unknown ID, `get_current_state` when idle, `get_output` slicing, `register_output_callback`, import fallback path

All tests mock the workflow `_instance.run_step()` return value and `_emit_output`.

---

## WS-B: Health Checker -- API Check Branches (~25 tests)

**File:** [tests/test_health_checker.py](tests/test_health_checker.py) (append)
**Target:** [src/health_checker.py](src/health_checker.py) API checks -- 60% -> ~72%

Key test classes to add:

- **TestResolveIPs** (~5 tests): `_resolve_cnode_ip` (config, API fallback, API error), `_resolve_switch_ips` (config, switches/ endpoint, v1 fallback, CNode nic_nodes fallback)
- **TestAPICheckBranches** (~12 tests): `_check_replication` (no DR, DR no policies, unhealthy policies), `_check_snapshots` (None, failed, 404 exception), `_check_quotas` (None, blocked, 404), `_check_call_home_status` (enabled/disabled/None), `_check_switches_registered` (None, empty, populated), `_check_device_health` (no metrics, empty, failures)
- **TestSSHNodeChecks** (~8 tests): `_check_panic_alert_logs` (found/clean/error), `_check_memory_usage` (normal/high/error), `_check_disk_space` (normal/high), `_check_network_interfaces` (DOWN with virtual filtering), `_check_vast_services` (failed/clean)

Mocks: `_make_api_request`, `_get_cluster_data`, `run_ssh_command`, `get_prometheus_metrics`.

---

## WS-C: Health Checker -- Switch Checks + Remediation (~12 tests)

**File:** [tests/test_health_checker.py](tests/test_health_checker.py) (append)
**Target:** Switch tier-3 and remediation paths

- **TestSwitchCheckDispatch** (~4 tests): `run_switch_ssh_checks` no config, no IPs, with IPs dispatching to check functions
- **TestSwitchChecks** (~4 tests): `_check_mlag_status` (healthy/unhealthy/no MLAG/error), `_check_switch_ntp` (peers/no peers/unavailable)
- **TestRemediationEdgeCases** (~4 tests): `_format_finding` with alarms list, events list, unknown check name; `_correlate_findings` with CNode+DNode+leader inactive combo; `generate_remediation_report` with all-pass results

---

## WS-D: Workflow Step Execution (~35 tests)

**File:** [tests/test_workflows.py](tests/test_workflows.py) (append)
**Target:** 6 workflow modules -- 33% -> ~55%

Focus on parsing logic and step orchestration (not raw SSH):

- **TestVnetmapParsing** (~8 tests): `_convert_ip_format` (range, single, empty), `_parse_local_cfg` (groups, @refs, missing), `_filter_vnetmap_output` (tracebacks, SSH noise, clean), `_step_validate_results` error/warning/recommendation branches
- **TestSwitchConfigSteps** (~6 tests): `_get_switch_ips_from_api` (success, v1 fallback, exception), `_detect_switch_type` (ONYX model, Cumulus nv/net, Spectrum), `_step_discover_switches` partial success
- **TestNetworkConfigParsing** (~8 tests): `_parse_local_cfg` (comments, @refs, range expansion), `_run_on_all_nodes` (clush parsing, gateway-only, mixed), `_step_collect_configure_network` empty/non-empty
- **TestLogBundleSteps** (~6 tests): `_step_discover_sizes` (G/M/K parsing, ValueError), `_step_confirm_collection` (under/over 5GB threshold), `_step_verify_contents` (success/timeout/missing)
- **TestSupportToolSteps** (~7 tests): `_step_run_support_tools` output classification, `_step_create_archive` (dir found/find fallback/no dir/tar failure), `_step_download_results` success/failure

All mock `run_ssh_command`, `ToolManager`, `ScriptRunner`.

---

## WS-E: Validation and Coverage Gate

After WS-A through WS-D, run the full test suite and:

- Verify 0 failures
- Measure coverage and raise `cov-fail-under` if coverage exceeds 60%
- Update `pyproject.toml` and `ci.yml` if threshold changes
- Run quality gates (black, flake8, mypy)

---

## Estimated Impact

| Stream    | New Tests | Lines Recovered | Module Coverage Delta    |
| --------- | --------- | --------------- | ------------------------ |
| WS-A      | ~20       | ~65 of 93       | 51% -> ~85%              |
| WS-B      | ~25       | ~250 of 549     | 60% -> ~78%              |
| WS-C      | ~12       | ~80 of 549      | (included in HC above)   |
| WS-D      | ~35       | ~500 of 1,137   | 33% -> ~62%              |
| **Total** | **~92**   | **~895**        | **Overall: 54% -> ~62%** |
