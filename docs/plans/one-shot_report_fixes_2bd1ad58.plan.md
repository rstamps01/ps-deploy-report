---
name: One-Shot Report Fixes
overview: "Fix five issues: add port mapping to one-shot reports, eliminate duplicate health check runs, adjust memory usage threshold, replace duplicate SSH section with Post Deployment Activities checklist, and restructure the one-shot health check UI/flow."
todos:
  - id: fix-port-mapping
    content: Add port mapping collection to oneshot_runner._run_report() when node+switch credentials are present
    status: completed
  - id: fix-health-double-run
    content: Remove standalone _run_health_checks() phase; gate health inside _run_report() on include_health flag
    status: completed
  - id: fix-ui-health-checkbox
    content: Move Health Check checkbox next to Report checkbox in one-shot UI; remove health_checks from progress phases
    status: completed
  - id: fix-memory-threshold
    content: Change _check_memory_usage() to PASS for >90% (expected for VAST clusters)
    status: completed
  - id: fix-post-deploy-section
    content: Replace Post Deployment Validation SSH table with Post Deployment Activities Next Steps checklist
    status: completed
  - id: update-tests
    content: Update affected tests for health checker, oneshot runner, and report builder changes
    status: completed
isProject: false
---

# One-Shot Report and Health Check Fixes

## Issue 1: Port Mapping Missing from One-Shot Report

**Root cause:** `_run_report()` in [src/oneshot_runner.py](src/oneshot_runner.py) calls `api.get_all_data()` and `data_extractor.extract_all_data(raw_data)` but never collects port mapping data via `ExternalPortMapper`. The standard report flow in [src/app.py](src/app.py) (`_run_report_job`) calls `_collect_port_mapping_web()` to populate `raw_data["port_mapping_external"]` and passes `use_external_port_mapping=True` to the extractor.

**Fix:** In `_run_report()` (~line 796), after `raw_data = api.get_all_data()`, add port mapping collection when both `node_password` and `switch_password` are present in credentials. Reuse the same `_collect_port_mapping_web` pattern (import `ExternalPortMapper`, extract switch IPs from `raw_data`, iterate CNode IPs, call `mapper.collect_port_mapping()`). Then pass `use_external_port_mapping=True` to `extract_all_data()`.

**Files:**

- `src/oneshot_runner.py` — add port mapping collection in `_run_report()`

---

## Issue 2: Health Check Runs Twice (Standalone + Inside Report)

**Root cause:** The one-shot flow runs `_run_health_checks()` as Phase 1, then `_run_report()` as Phase 3 which *always* runs `HealthChecker.run_all_checks()` again internally (lines 803-830 in oneshot_runner.py). This causes health checks to execute twice.

**Fix:**

- **Remove the standalone `_run_health_checks()` phase** from `run_all()`. Health checks should only run as part of the Report Generator workflow.
- **Move the Health Check checkbox** in the UI to be next to the Report checkbox (not at the top of the checklist).
- **Gate health check execution inside `_run_report()`** on the `include_health` flag: when `include_health` is false, skip the `HealthChecker` block so `raw_data["health_check_results"]` is never set and the report omits health sections.
- **Update the progress phases** in the frontend: remove the "Health Checks" phase from the progress tracker since it's no longer a standalone phase.
- **Update `total_operations` counter** in `run_all()` to no longer count health checks as a separate operation.
- **Update pre-validation**: `needs_node_ssh` and `needs_switch_ssh` should still check `include_health` to validate SSH credentials when health is selected.

**Files:**

- `src/oneshot_runner.py` — remove `_run_health_checks()` call from `run_all()`, gate health inside `_run_report()` on `self._include_health`
- `frontend/templates/advanced_ops.html` — move Health Check checkbox below ops list near Report checkbox, remove `health_checks` from progress phases, update `resetOneShotPhases` and `updateOneShotPhases`

---

## Issue 3: Memory Usage >90% Should Be PASS

**Root cause:** In [src/health_checker.py](src/health_checker.py) `_check_memory_usage()` (line ~2953), any node with `pct > 90` is flagged as `status="warning"`.

**Fix:** Change the condition so `pct > 90` returns `status="pass"` with a message like "Memory usage within expected range (>90% is normal for VAST clusters)". VAST clusters are expected to use >90% memory. Only flag a warning at a much higher threshold or remove the threshold entirely.

Simplest approach: remove the `high_usage_nodes` check entirely and always return `status="pass"` since >90% is expected, or raise the warning threshold to something like >98%.

**Files:**

- `src/health_checker.py` — modify `_check_memory_usage()` (~line 2953)

---

## Issue 4: Duplicate SSH Results in Report + New Post Deployment Activities Section

**Root cause:** Both `_create_health_check_section()` and `_create_post_deployment_validation_section()` in [src/report_builder.py](src/report_builder.py) render SSH connectivity results. The health check section shows all results (including SSH) in "Detailed Check Results", and the post-deployment section filters to `node_ssh`/`switch_ssh` categories for "SSH Connectivity Validation".

**Fix:**

- **Rename** the section from "Post Deployment Validation" to "Post Deployment Activities"
- **Remove** the SSH Connectivity Validation table from this section (it's already in Health Check Results above)
- **Replace** with a "Next Steps" checklist table. Each row has: Item, Description, Status ("Pending"). Items sourced from the VAST Installation Template (Confluence page 7391248523):

| Item                                     | Description                                                                                                                                                                                                |
| ---------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Configure Call Home w/ Cloud Integration | Configure cloud integration to enable remote monitoring and proactive support. Ensure Cloud VMS fields match Salesforce records exactly. Outbound traffic requires *.cloud.vastdata.com:443.               |
| Create VIP                               | Create Virtual IP Pool(s) via VMS GUI or CLI. Verify VIPs are setup and listening using `showmount -e <VIP>`.                                                                                              |
| Test Fail-over Behavior                  | Identify the VMS host node and intentionally reboot it. Verify VMS migrates and cluster stays healthy. Repeat for the leader node.                                                                         |
| Confirm VIP Movement and ARP Updates     | After MLAG is confirmed, validate that gratuitous ARP updates propagate correctly when VIPs move between CNodes. Mount from a client and test during a controlled fail-over.                               |
| Activate License                         | Locate the PSNT asset record in Salesforce and click "Activate Cluster". Configure the license key in VMS via GUI or CLI. License start date is the last day of cluster install.                           |
| Change Default Passwords                 | Change all default passwords: Linux root, vastdata, and IPMI admin via VCLI (`cluster set-password`). Change VMS admin, support, and root passwords via VMS UI. Change switch admin and monitor passwords. |

**Files:**

- `src/report_builder.py` — rewrite `_create_post_deployment_validation_section()` to render checklist instead of SSH table
- `src/data_extractor.py` — update the `post_deployment_validation` section to include a `next_steps` checklist instead of/alongside raw health data

---

## Issue 5: Frontend Phase Tracker Updates

The progress phase tracker currently shows: `Health Checks -> Operations -> Report -> Bundling`. Since health checks are no longer a standalone phase, update to: `Operations -> Report -> Bundling`.

**Files:**

- `frontend/templates/advanced_ops.html` — HTML for `#oneShotPhases`, JS for `showOneShotProgress`, `resetOneShotPhases`, `updateOneShotPhases`
