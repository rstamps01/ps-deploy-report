---
name: Post-Deploy Status Updates
overview: Add logic to dynamically update the Post Deployment Activities table status column from "Pending" to "Completed" (green) based on health check results and raw cluster data available at report generation time.
todos:
  - id: extractor-status
    content: Add _resolve_post_deploy_status() to data_extractor.py that maps health check results + cluster data to per-item Completed/Pending status
    status: completed
  - id: builder-render
    content: Update report_builder.py to read step['status'] and apply green/orange conditional cell coloring
    status: completed
  - id: verify-test
    content: Run tests, regenerate PDF from <customer> JSON, verify green/orange status rendering
    status: completed
isProject: false
---

# Post Deployment Activities — Dynamic Status Updates

## Current State

The Post Deployment Activities table in the PDF report has 6 rows, all hardcoded to "Pending" (orange). The data is assembled in `[src/data_extractor.py](src/data_extractor.py)` (lines 1985-2042) and rendered in `[src/report_builder.py](src/report_builder.py)` (lines 4902-5045).

Meanwhile, both **health check results** and **raw cluster data** already contain the signals needed to determine completion for 4 of the 6 items. Two items (failover testing, VIP/ARP validation) are inherently manual and cannot be auto-detected.

## Status Mapping

Each post-deployment item maps to a data signal:

- **Configure Call Home w/ Cloud Integration** --> Health check `Call Home Status`: pass = Completed; otherwise Pending. Alternatively, `cluster_summary.call_home_enabled` if no health check was run.
- **Create VIP** --> Health check `VIP Pools`: pass = Completed (at least one enabled VIP pool exists). Alternatively, check for non-empty `vippools` data in network config section.
- **Activate License** --> Health check `License`: pass = Completed; warning/fail = Pending. Alternatively, `cluster_summary.license` is present and not "Unknown"/"None"/empty.
- **Change Default Passwords** --> Cannot be auto-detected via API. Status remains "Pending" (orange).
- **Test Fail-over Behavior** --> Cannot be auto-detected. Status shows "Optional" (blue).
- **Confirm VIP Movement and ARP Updates** --> Cannot be auto-detected. Status shows "Optional" (blue).

## Implementation

### 1. Add `status` field to each next_steps item in data_extractor.py

In `[src/data_extractor.py](src/data_extractor.py)`, after building the `next_steps` list (line 2033), add a resolution function that:

- Looks for `health_check` results in `report_data["sections"]` (already populated earlier in `extract_all_data`)
- Falls back to `cluster_summary` fields from raw data
- Sets `step["status"]` to `"Completed"` or `"Pending"` for each item

The mapping logic:

```python
def _resolve_post_deploy_status(self, next_steps, report_data, raw_data):
    """Resolve status for post-deployment items from health check results and cluster data."""
    hc_results = {}
    hc_section = report_data.get("sections", {}).get("health_check", {})
    for r in hc_section.get("data", {}).get("results", []):
        hc_results[r["check_name"]] = r["status"]

    cluster = raw_data.get("clusters", [{}])[0] if isinstance(raw_data.get("clusters"), list) else {}

    STATUS_MAP = {
        "Configure Call Home w/ Cloud Integration": (
            lambda: hc_results.get("Call Home Status") == "pass"
            or cluster.get("call_home_enabled") is True
        ),
        "Create VIP": (
            lambda: hc_results.get("VIP Pools") == "pass"
        ),
        "Activate License": (
            lambda: hc_results.get("License") == "pass"
            or (cluster.get("license") and str(cluster.get("license", "")).lower()
                not in ("", "none", "unknown"))
        ),
    }

    for step in next_steps:
        checker = STATUS_MAP.get(step["item"])
        step["status"] = "Completed" if checker and checker() else "Pending"
```

### 2. Update report_builder.py to render dynamic status with green/orange coloring

In `[src/report_builder.py](src/report_builder.py)` `_create_post_deployment_activities_section` (line 4993):

- Read `step.get("status", "Pending")` instead of hardcoded `"Pending"`
- Apply **green** background for "Completed" rows, **orange** for "Pending" rows (per-row conditional styling already exists at lines 5024-5030)

### 3. Pass raw cluster data through for resolution

In `data_extractor.py`, the `extract_all_data` method already has access to `raw_data` (the full API response dict). The health check section is populated before the post-deployment section, so `report_data["sections"]["health_check"]` is available.

Need to also check `cluster_summary` which is assembled from `raw_data.get("clusters", ...)` earlier in the same method.

## Files Changed

- `[src/data_extractor.py](src/data_extractor.py)` -- Add `_resolve_post_deploy_status()` method; call it after building `next_steps` list; add `status` field to each step dict
- `[src/report_builder.py](src/report_builder.py)` -- Read `step["status"]` for the Status column text; conditionally apply green (#4CAF50) background for "Completed" and orange for "Pending"
