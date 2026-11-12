# Context pack: TP-4

Terms: `scan_all`, `get_known_clusters`, `cluster_key`, `validation-results`

## `scan_all` (24 hits)
- `src/app.py` `_register_routes.dashboard_status` L432-481
- `src/app.py` `_register_routes.validation_results_api` L1400-1418
- `src/result_scanner.py` `ResultScanner.scan_all` L256-282
- `src/result_scanner.py` `ResultScanner.get_known_clusters` L320-357
- `tests/test_qp2_read_discovery.py` `TestScannerSegmentedDiscovery.test_per_cluster_files_associated_to_marker_identity` L102-115
- `tests/test_qp2_read_discovery.py` `TestScannerSegmentedDiscovery.test_legacy_flat_files_still_discovered` L117-130
- `tests/test_qp2_read_discovery.py` `TestScannerSegmentedDiscovery.test_two_clusters_shared_tech_port_ip_kept_separate` L132-156
- `tests/test_qp2_read_discovery.py` `TestScannerSegmentedDiscovery.test_no_clusters_dir_is_pure_legacy` L181-190

## `get_known_clusters` (11 hits)
- `src/app.py` `_register_routes.validation_results_clusters` L1421-1427
- `src/result_scanner.py` `ResultScanner.get_known_clusters` L320-357
- `tests/test_qp2_read_discovery.py` `TestScannerSegmentedDiscovery.test_get_known_clusters_shared_ip_lists_two_clusters` L158-171
- `tests/test_qp2_read_discovery.py` `TestScannerSegmentedDiscovery.test_get_known_clusters_surfaces_real_identity` L173-179
- `tests/test_result_scanner.py` L5
- `tests/test_result_scanner.py` L451
- `tests/test_result_scanner.py` `TestGetKnownClusters.test_returns_unique_ips_with_counts` L456-466
- `tests/test_result_scanner.py` `TestGetKnownClusters.test_empty_dirs_return_no_clusters` L468-471

## `cluster_key` (61 hits)
- `src/app.py` `_register_routes.api_vnetmap_status` L2006-2065
- `src/app.py` `_run_report_job` L2542-3064
- `src/app.py` `_find_latest_vnetmap_output` L3198-3236
- `src/oneshot_runner.py` `OneShotRunner._run_report` L1728-2109
- `src/oneshot_runner.py` `OneShotRunner._persist_ops_log` L2249-2281
- `src/oneshot_runner.py` `OneShotRunner._find_latest_vnetmap_output` L2283-2321
- `src/result_scanner.py` `ResultEntry` L144-170
- `src/result_scanner.py` `ResultEntry.to_dict` L160-170

## `validation-results` (8 hits)
- `frontend/templates/validation_results.html` L448
- `frontend/templates/validation_results.html` L471
- `frontend/templates/validation_results.html` L498
- `src/app.py` `_register_routes` L403-2151

## Files by relevance
- `src/result_scanner.py` (30 hits)
- `src/app.py` (21 hits)
- `src/oneshot_runner.py` (9 hits)
- `frontend/templates/validation_results.html` (3 hits)

## Tests to run
`python3 -m pytest tests/test_qp2_read_discovery.py tests/test_qp2_write_segmentation.py tests/test_result_scanner.py tests/test_vnetmap_segmentation.py -x --lf`

## Recent commits on these files
- be4412a 2026-11-10 fix(web): stream vperfsanity Step 4 output and keep Output Results responsive (FR-16)
- b672773 2026-10-16 fix(report): mask credentials in saved ops logs; flag empty /vast/log copies
- 39648ac 2026-10-16 fix(report): mask credentials in the bundled operation log; review follow-ups
- a09e3f1 2026-10-16 chore(release): prepare v1.6.2
- 2b167cb 2026-10-16 refactor(ui): rename the product to asbuilt-reporter in visible text
- dc7ee14 2026-10-15 fix(report): v1.6.2 field-feedback fixes, wrapped report tables and grouped health details
