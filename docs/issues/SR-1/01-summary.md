# SR-1: `/api/switches/` direct-cluster-IP call bypasses VMS tunnel on Tech-Port mode

**Status:** Open — pre-existing, surfaced during TP-2 validation on `selab-var-202` (Ethernet cluster, Cumulus switches).
**Severity:** Medium — does not block report generation (graceful fallback to cached vnetmap exists), but causes incorrect cluster type detection (Eth misidentified as IB) and unnecessary live-vnetmap failure.
**Discovered:** 2026-04-30, in `import/cluster202/output-logs-043026`.
**Related:** TP-1 (`7b94453`), TP-2 (`f49aa2b`) — both fixes are about VMS discovery; this is a downstream consumer of the established tunnel.
**Out of scope for:** TP-1, TP-2.

---

## Symptom

In `selab-var-202` end-to-end report run (Ethernet cluster, Tech-Port mode via `10.143.11.63`):

```
22:19:23 [INFO] $ curl -k https://10.143.11.63/api/switches/
22:19:23 [ERROR] Failed to get switch IPs from API: HTTPSConnectionPool(host='10.143.11.63', port=443):
                 Max retries exceeded with url: /api/switches/ (Caused by NewConnectionError(...:
                 Failed to establish a new connection: [Errno 61] Connection refused))
22:19:23 [WARN]  [API] No switches found - assuming InfiniBand cluster
22:19:23 [INFO] python3 vnetmap.py -i $cnodes_ips,$dnodes_ips -ib
...
22:19:45 [ERROR] Exception: Failed running ibnetdiscover on local system. Aborting...
22:19:45 [ERROR] vnetmap exited with return code: 1
22:19:45 [WARN]  Vnetmap step 4 failed: vnetmap failed with rc=1 — continuing without fresh vnetmap
22:20:33 [INFO] Found vnetmap output: vnetmap_output_10.143.11.63_20260330_030728.txt — using as port mapping source
```

Cascading effect:
1. `/api/switches/` query fails on TCP/443 because `10.143.11.63` is a CNode (not the VMS API endpoint).
2. Workflow assumes the cluster is InfiniBand → builds `vnetmap.py … -ib` command.
3. `vnetmap.py -ib` invokes `ibnetdiscover` on a CNode that has no IB fabric → fails with rc=1.
4. Workflow falls back to a **stale cached vnetmap from 2026-03-30** (~1 month old) and continues. Report still completes.

The VMS API tunnel was already established at this point (`127.0.0.1:56249 → 10.143.11.202:443`, log line 83), so the call should have been routed through it.

## Root cause (preliminary)

`src/workflows/vnetmap_workflow.py` line 367:

```python
url = f"https://{api_host}/api/switches/"
```

Where `api_host = self._credentials.get("tunnel_address") or host` (line 463). Hypothesis: in Tech-Port mode, `tunnel_address` is not populated in the credentials dict that the vnetmap workflow receives, so it falls back to `host` (the user-entered cluster IP, which is actually a CNode tech-port IP).

Locations to verify:
- `src/workflows/vnetmap_workflow.py:367, :462-466` — the call site.
- `src/app.py` and `src/script_runner.py` — wiring of `tunnel_address` into the credentials passed to workflows.
- `src/utils/vms_tunnel.py` — `connect()` returns `(internal_ip, mgmt_ip, tunnel_addr)`; confirm caller stores `tunnel_addr` in the workflow credentials.

## Acceptance criteria for fix

1. When VMS tunnel is active (`tunnel_address` is set), `_get_switch_ips_from_api` MUST use it. It must NOT fall back to a cluster CNode IP that isn't serving 443.
2. When no tunnel is active and the cluster IP itself doesn't serve 443, fail loudly rather than silently mis-classify the cluster as IB.
3. Add a unit test against the credentials/tunnel wiring that asserts `tunnel_address` propagates from `VMSTunnel.connect()` → workflow `_credentials`.
4. Add a regression test fixture from the `selab-var-202` log (Eth cluster, Tech-Port mode) that exercises the workflow with a populated `tunnel_address` and verifies `/api/switches/` is queried at `127.0.0.1:<port>`, not the cluster CNode IP.

## Workaround (operator-side, no code change)

When running Tech-Port mode against an Ethernet cluster, ensure a recent vnetmap output is available locally so the fallback in the report flow has fresh data. (Already happened in the `selab-var-202` run via the cached `vnetmap_output_10.143.11.63_20260330_030728.txt`.)

## Evidence

- `import/cluster202/output-logs-043026` — full `selab-var-202` run, lines 56, 62, 83, 182–183, 191, 252, 478.
- TP-2 commit `f49aa2b` validated VMS discovery + tunnel are correct; this issue is downstream of that.
