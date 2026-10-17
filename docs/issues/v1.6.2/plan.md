# v1.6.2 — Implementation plan

## DIAG-1

`scripts/discover_api_fields.py` already exists but targets multi-rack keywords and does **not** probe `ssds/`, `nvrams/`, `licenses/`, or `clusters/` upgrade/license fields. Follow the `tests/diag_prometheus_metrics.py` pattern (local/gitignored sibling), but ship the committed probe as `scripts/diag_api_fields.py` so operators can run it from a clone: authenticate via `VastApiHandler`, GET each endpoint, dump keys, highlight MAC/serial/firmware/license/upgrade candidates, write JSON under `reports/` (gitignored).

## HCF-1 → HCF-2 → HCF-5 → HCF-6 → INV-1

1. **HCF-1** — unit tests on `_check_upgrade_state` with mocked cluster data; then widen idle set + fail set.
2. **HCF-2** — unit tests for CBox/DBox messaging when `eboxes/` non-empty; detect once (cache on checker).
3. **HCF-5** — unit test: empty metrics → `skipped`; non-empty → pass with details.
4. **HCF-6** — PDF (`_create_health_check_section`) + `health.html` render details; tests for builder helper and/or template presence.
5. **INV-1** — report_builder inventory + node management map columns; extractor already has serial if present in structured data — verify data path.

## Order rationale

DIAG-1 unblocks later releases (HCF-4/INV-2/DRV-1) but HCF-1+ do not depend on live probe results. Ship the diag script first so a lab run can proceed in parallel with HCF work.
