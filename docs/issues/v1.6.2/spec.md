# v1.6.2 Field-feedback patch — Spec

**Branch:** `fix/v1.6.2-field-feedback`  
**Target:** patch release after v1.6.1  
**Source:** [`plans/field_feedback_triage_1d3ae704.plan.md`](../../plans/field_feedback_triage_1d3ae704.plan.md); decision 2026-09-25

## Scope (this release)

| ID | Acceptance |
|----|------------|
| DIAG-1 | `scripts/diag_api_fields.py` dumps keys from `cnodes/`, `dnodes/`, `ssds/`, `nvrams/`, `licenses/`, `clusters/` (upgrade + license fields). Manual lab run; does not block unit CI. |
| HCF-1 | `_check_upgrade_state`: `UNKNOWN` → pass (idle); `FAILED`/`ABORTED` → fail; other active states → warning. Failing-first regression tests. |
| HCF-2 | EBox topology: detect non-empty `eboxes/`; CBox message "Not applicable — converged EBox cluster…"; DBox message mentions EBox storage enclosures. Status values unchanged. |
| HCF-5 | `_check_performance_baseline` returns `skipped` when no metrics captured; captured metrics rendered via HCF-6. |
| HCF-6 | Non-empty `HealthCheckResult.details` rendered in PDF health section and `health.html`, with row caps. |
| INV-1 | Serial column in Hardware Inventory and CNode/DNode Management Map; box chassis serials where available. Data already collected in `api_handler`. |
| FR-1–6 | EBox field report fixes (support tools wrapper, vperfsanity budget, cleanup contract, switch-op skips, log bundle sources, bundle diagnostics). See the roadmap rows. |
| NET-6 | `local.cfg` groups resolve as ClusterShell does: repeated keys union, `@a,@b` references and `[1-3,5]`/`[5]` ranges expand. On the field `local.cfg`, Network Extraction discovers all 12 hosts and vnetmap's `cnodes`/`dnodes` are `172.16.128.[1-12]`. |
| HCF-7 | Firmware Consistency passes when values differ only in format (`2.90` vs `A56 v2.90 (01/09/2026)`) and still warns on real version or kernel-build differences. |
| HCF-8 | No `[????]` in Output Results: skipped checks print `[SKIP]` with their reason; unknown statuses print their name. |

## Out of scope (v1.7.0+)

HCF-3, HCF-4, INV-2, DRV-1/2, SW-1 (awaiting logs).

## Non-negotiables

- TDD for every bug (failing-first).
- No module-boundary violations (`health_checker` ↛ `report_builder`/`data_extractor`).
- No secrets in git; diag script accepts credentials only via CLI/env/prompt.
