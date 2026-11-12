# TP-4 tasks

- [x] T1 Failing-first regression tests: two `cluster_key` folders sharing `192.168.2.2` filtered apart (`tests/test_result_scanner.py`, `tests/test_validation_results_api.py`)
- [x] T2 `ResultScanner.scan_all(cluster_key=...)` scans only that folder; `__unassigned__` selects legacy flat files carrying only the Tech Port IP; `cluster_ip=192.168.2.2` maps to it
- [x] T3 `ResultScanner.get_filter_choices()`; `get_known_clusters` adds `cluster_name` and stops guessing a profile from the Tech Port IP
- [x] T4 `/validation-results` renders the choices; `/validation-results/api/results` accepts `cluster_key`; the template sends each option's `data-param`
- [x] T5 Tests: VMS-HTTPS IP filter unchanged, legacy Tech Port files only under Unassigned (legacy), `cluster_ip` still accepted, template escaping
- [x] T6 `docs/development/WEB-ROUTES.md`, changelog fragment
- [ ] T7 Full `quality-gate` and UI suite (parent)
- [ ] T8 Manual UI check on the Results page with two Tech Port clusters (owner)
