# Context pack: FR-11

Terms: `_step_verify_contents`, `_step_download_results`, `vast_log_bundle`, `support_tool_logs`

## `_step_verify_contents` (4 hits)
- `src/workflows/log_bundle_workflow.py` `LogBundleWorkflow.run_step` L104-126
- `src/workflows/log_bundle_workflow.py` `LogBundleWorkflow._step_verify_contents` L380-434
- `tests/test_workflows.py` `TestLogBundleSteps.test_verify_contents_success` L1611-1622
- `tests/test_workflows.py` `TestLogBundleStepsV2.test_verify_contents_success` L2056-2068

## `_step_download_results` (4 hits)
- `src/workflows/support_tool_workflow.py` `SupportToolWorkflow.run_step` L170-190
- `src/workflows/support_tool_workflow.py` `SupportToolWorkflow._step_download_results` L746-847
- `tests/test_workflows.py` `TestSupportToolSteps.test_download_results_success` L1727-1747
- `tests/test_workflows.py` `TestSupportToolStepsV2.test_download_results_success` L2167-2187

## `vast_log_bundle` (3 hits)
- `src/workflows/log_bundle_workflow.py` `LogBundleWorkflow` L24-434
- `tests/test_result_scanner.py` `TestVerificationClusterIp.test_tar_gz_verification` L260-265

## `support_tool_logs` (5 hits)
- `src/result_bundler.py` `ResultBundler.collect_results` L323-546
- `src/result_scanner.py` `ResultScanner._scan_support_tools` L475-483
- `src/workflows/support_tool_workflow.py` `SupportToolWorkflow._step_download_results` L746-847
- `tests/test_workflows.py` `TestSupportToolSteps.test_create_archive_dir_found` L1672-1681
- `tests/test_workflows.py` `TestSupportToolSteps.test_create_archive_find_fallback` L1684-1698

## Files by relevance
- `src/workflows/log_bundle_workflow.py` (3 hits)
- `src/workflows/support_tool_workflow.py` (3 hits)
- `src/result_bundler.py` (1 hits)
- `src/result_scanner.py` (1 hits)

## Tests to run
`python3 -m pytest tests/test_result_scanner.py tests/test_workflows.py -x --lf`

## Recent commits on these files
- b672773 2026-10-16 fix(report): mask credentials in saved ops logs; flag empty /vast/log copies
- 39648ac 2026-10-16 fix(report): mask credentials in the bundled operation log; review follow-ups
- 2b167cb 2026-10-16 refactor(ui): rename the product to asbuilt-reporter in visible text
- dc7ee14 2026-10-15 fix(report): v1.6.2 field-feedback fixes, wrapped report tables and grouped health details
- e48e581 2026-07-31 feat(release): v1.6.0 development baseline — Teleport tsh discovery + Settings UI, teleport-mode SSH routing, Onyx fixes, cross-cluster vnetmap segmentation
- 3808f48 2026-06-25 feat(release): v1.5.8 — Teleport beta, switch identity, diagram fixes, library + health-bundle fix
