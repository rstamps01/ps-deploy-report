# v1.6.3 — Spec (release scope)

**Target:** v1.6.3, after v1.6.2 (2026-10-17). **Decided:** 2026-11-11 by the owner (planning chat for critical
fixes + NET-7). **Plan:** [`plan.md`](plan.md). **Tasks:** [`tasks.md`](tasks.md).

v1.6.3 deliberately carries features and one policy change alongside the fixes (the owner chose one release over a
v1.6.3 patch plus v1.7.0). The release notes must call out the two behavior changes: HCF-3 (critical alarms now
fail) and NET-7 (new port-map source selector).

## Scope

| ID | Type | Acceptance (summary) | Detail |
| --- | --- | --- | --- |
| FR-16 | Bug, P0 | Merged (PR #49). Lab re-run with a full Step 4 (T8) passes. | [`../FR-16/`](../FR-16/) |
| TP-4 | Bug, P2 | Results filter by `cluster_key`; two Tech Port clusters never mix. | [`../TP-4/spec.md`](../TP-4/spec.md) |
| FR-10 | Bug, P2 | Paramiko non-streaming path honours an overall deadline and keeps partial output. | [`../FR-10/spec.md`](../FR-10/spec.md) |
| FR-11 | Bug, P3 | Log bundle and Support Tools archives are removed from the cluster after a verified download. | [`../FR-11/spec.md`](../FR-11/spec.md) |
| OBS-1 | Bug, P3 | All artifact filenames use one timestamp convention (local time). | [`../OBS-1/spec.md`](../OBS-1/spec.md) |
| TP-3 | Bug, P3 | Tech Port discovery never reports the Tech Port address as the VMS management IP; no double gateway. | [`../TP-3/spec.md`](../TP-3/spec.md) |
| HCF-3 | Policy, P1 | Critical alarms fail, major alarms warn; `health_check.alarms.fail_on`. | [`../HCF-3/spec.md`](../HCF-3/spec.md) |
| FR-7 | Enhancement, P1 | vperfsanity runs detached with heartbeat, stall warning, effective Cancel, Quick/Full. | [`../FR-7/spec.md`](../FR-7/spec.md) |
| NET-7 | Feature | Port map and logical network diagram from node-side LLDP (`vnetmap_lldp.py`), selectable per run. | [`../NET-7/spec.md`](../NET-7/spec.md), [`../NET-7/plan.md`](../NET-7/plan.md) |

## Out of scope (stay v1.7.0 or later)

FR-8, FR-9, FR-13, FR-14, FR-15, HUB-1–9, DATA-1, HCF-4, INV-2, DRV-1/2, RCS-1–5, SW-1 (awaiting logs), NET-7
tcpdump / `nw_check.sh` enrichment (new follow-up item).

## Release gates

- Every item merged to `develop` with its tests; `bash scripts/quality-gate.sh` green; CI green.
- Lab: FR-16 T8, FR-7 multi-hour run with Cancel, NET-7 on a cluster with LLDP active on the nodes, TP-3 repro
  (or TP-3 moved out with a recorded reason).
- Changelog fragments in each `docs/issues/<ID>/changelog.md`; release notes name the HCF-3 and NET-7 behavior
  changes.

## Non-negotiables

- Every bug ships a failing-first regression test; every feature ships tests.
- No customer identifiers in fixtures (ACME, documentation-range IPs; GOV-1).
- NET-7 guardrails in [`../NET-7/spec.md`](../NET-7/spec.md) are enforced by a test.
