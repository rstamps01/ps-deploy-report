# SR-4: vnetmap_workflow uses "switches present → ETH" heuristic, mis-classifies IB clusters

**Status:** Resolved — fixed by `VnetmapWorkflow._resolve_network_type` + `_get_net_type_from_api` (this branch). 
**Severity:** Medium — does not block report generation in normal flow (the report falls back to a cached vnetmap), but on InfiniBand clusters with management-network switches the live-vnetmap step is invoked with `-s <ip,ip>` instead of `-ib`, producing a confusing log message ("Network type: ETH") and ultimately failing on `ibnetdiscover` because the cluster fabric is IB. Pre-SR-1 the issue was masked because `/api/switches/` failed entirely; post-SR-1 the API succeeds and surfaces this latent miscategorization. 
**Discovered:** 2026-04-30 (cluster202 Ethernet log review uncovered the heuristic's brittleness; mammoth IB cluster fixtures confirmed misclassification post-SR-1). 
**Related:** SR-1 (`8bba3aa`) — same Tech-Port / IB cluster pipeline; SR-1 makes `/api/switches/` succeed, which is what newly exposes SR-4. 
**Out of scope for:** SR-1 (tunnel routing), SR-3 (GUID aliasing in port mapper).

---

## Symptom

Pre-SR-4, on an IB cluster where switches expose a management VLAN visible to the VAST API:

```
[INFO]  $ curl -k https://127.0.0.1:56789/api/switches/
[INFO]  [API] Found 2 switch(es): 10.247.2.135, 10.247.2.137
[INFO]  Network type: ETH
[INFO]  python3 vnetmap.py -s 10.247.2.135,10.247.2.137 -i $cnodes_ips -u cumulus -p '...'
[ERROR] Authentication failed on 10.247.2.135 (switch is IB, not Cumulus)
```

The fabric is InfiniBand; the API-reported switches are MQM8700 IB switches that happen to publish a 10.247.2.x mgmt-net IP. The legacy heuristic ("any switches in `/api/switches/` ⇒ Ethernet") misfires because the switches' presence in the API doesn't tell us whether the cluster fabric is Ethernet or InfiniBand — only the cluster-level `net_type` does.

## Root cause

`src/workflows/vnetmap_workflow.py::_step_generate_export_commands`, lines 471/479 (pre-fix):

```python
if switch_ips:
    network_type = "ETH"   # <-- naive: switches in /api/switches/ ≠ Ethernet fabric
else:
    network_type = "IB"
```

The cluster's authoritative `net_type` is exposed at `/api/v7/vms/1/network_settings/` → `data.boxes[*].hosts[*].vast_install_info.net_type` — the same path `api_handler.get_cluster_network_configuration()` uses — but the workflow never queried it.

## Fix design (this branch)

Three new helpers on `VnetmapWorkflow` keep the change scoped to the workflow itself, so no plumbing changes were required in `app.py` or `oneshot_runner.py`. The override path (consuming an explicit `net_type` from `_credentials`) is tested and ready for future callers that want to skip the API probe.

1. **`_normalize_net_type(value: Any) -> Optional[str]`** — pure mapping helper. Recognises `INFINIBAND` / `InfiniBand` / `ib` → `"IB"`, `ETHERNET` / `Ethernet` / `Eth` / `ETH` → `"ETH"`, anything else → `None`. Case-insensitive, whitespace-tolerant.

2. **`_get_net_type_from_api() -> Optional[str]`** — issues a GET against `https://<tunnel_or_cluster_ip>/api/v7/vms/1/network_settings/`, walks `data.boxes[*].hosts[*].vast_install_info.net_type` for the first non-empty value, returns it through `_normalize_net_type`. Any HTTP / JSON / shape error returns `None` so the caller can fall back gracefully without aborting. Reuses the existing `requests` + `verify=False` + InsecureRequestWarning silencing pattern that `_get_switch_ips_from_api` already established.

3. **`_resolve_network_type(switch_ips: List[str]) -> str`** — the new dispatch. Resolution order:
   1. Explicit `_credentials["net_type"]` (caller-supplied override; bypasses API).
   2. API probe of `/api/v7/vms/1/network_settings/`.
   3. Legacy switches-list heuristic (preserves backward compat for fleets that don't expose `net_type`).

`_step_generate_export_commands` now calls `_resolve_network_type(switch_ips)` instead of inlining the heuristic. The result is logged ("Network type: ETH" / "Network type: IB") and drives both the `mlx_ips` value and the `-ib` vs `-s <ips>` choice in the generated vnetmap command.

## Acceptance criteria

1. IB cluster with mgmt-net switches in `/api/switches/`: `_resolve_network_type` returns `"IB"`, vnetmap command includes `-ib` and omits `-s`. 
2. Eth cluster with switches in `/api/switches/`: `_resolve_network_type` returns `"ETH"`, vnetmap command includes `-s <ips>`, switch password validation continues to fire. 
3. Any cluster with no `net_type` in API and no switches: returns `"IB"` (legacy heuristic preserved). 
4. Any cluster with no `net_type` in API and switches present: returns `"ETH"` (legacy heuristic preserved — the only honest fallback when the API doesn't tell us). 
5. Explicit `_credentials["net_type"]` always wins, skipping the API call entirely (faster + tested for future override threading from `app.py` / `oneshot_runner.py`). 
6. API probe failure (HTTP error, malformed JSON, missing `data` field, empty `boxes`) silently returns `None` — never crashes the workflow.

## Verification

* `tests/test_workflows.py::TestSR4NetTypeOverride` (14 cases): 5 normalization, 6 resolution-order, 3 API-probe shape. 
* Full workflow regression: 176/176 in `tests/test_workflows.py` (8.3s); 260/260 across SR-4 blast-radius (workflows + vnetmap_pipeline + enhanced_port_mapper_sr3 + vnetmap_status + e2e_vnetmap_diagram + data_extractor + main_from_json). 
* Black + flake8 clean on `src/workflows/vnetmap_workflow.py` and `tests/test_workflows.py`. 
* No new mypy errors introduced (workflow file was already mypy-clean modulo pre-existing unrelated warnings elsewhere in tree).

## Scope notes

* The plan originally also called for threading `net_type` into `vnetmap_creds` from `app.py::_run_report_job` and `oneshot_runner._get_workflow_credentials` so the workflow could skip its own API probe. That threading is **deferred** because:
  - The workflow-level fix is sufficient for correctness (`_resolve_network_type` handles all cases).
  - At the point `vnetmap_creds` is built in `app.py`, `api_handler.get_cluster_network_configuration()` has not yet been called, so threading would require an early dedicated API call that duplicates work later in the data-extractor flow.
  - Pre-fetching + caching `cluster_network_config` on `api_handler` is cleaner and tracked for a future refactor (DEV-2 candidate).
* The override path (`_credentials["net_type"]`) is fully tested and ready, so the future enhancement is a one-line change at each caller.

## Evidence

* `src/api_handler.py:1510-1561` — canonical `net_type` extraction path. 
* `output/scripts/vnetmap_output_192.168.2.2_*.txt` — IB mammoth fixture used to validate IB code path. 
* `import/cluster202/output-logs-043026` — Eth selab-var-202 log used to validate Eth back-compat path. 
* `tests/test_workflows.py::TestSR4NetTypeOverride` — full SR-4 unit coverage.
