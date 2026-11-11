# Context pack: FR-16

Terms: `sessionStorage`, `vperfsanity_run.sh`, `OutputPaneCtor.prototype.append`, `VperfsanityWorkflow._step_run_tests`, `_emit_run_output`, `frontend/templates/advanced_ops.html`, `frontend/templates/reporter.html`, `hydrateFromBackend`, `oneshot_10_143_11_203_20261023_100632_20261023_094600.jsonl`, `setItem`, `src/workflows/vperfsanity_workflow.py`, `sshpass`

## `sessionStorage` (16 hits)
- `frontend/templates/advanced_ops.html` L598
- `frontend/templates/advanced_ops.html` L606
- `frontend/templates/advanced_ops.html` L670
- `frontend/templates/advanced_ops.html` L703
- `frontend/templates/advanced_ops.html` L704
- `frontend/templates/advanced_ops.html` L709
- `frontend/templates/advanced_ops.html` L711
- `frontend/templates/advanced_ops.html` L712

## `OutputPaneCtor.prototype.append` (2 hits)
- `frontend/templates/advanced_ops.html` L662
- `frontend/templates/reporter.html` L1353

## `_emit_run_output` (5 hits)
- `scripts/context-pack.py` L13
- `src/workflows/vperfsanity_workflow.py` `VperfsanityWorkflow._emit_run_output` L454-465
- `src/workflows/vperfsanity_workflow.py` `VperfsanityWorkflow._step_run_tests` L467-564
- `tests/test_token_efficiency_scripts.py` `TestContextPack.test_build_pack_on_repo_is_capped` L91-97

## `frontend/templates/advanced_ops.html` (1 hits)
- `frontend/templates/advanced_ops.html` file

## `frontend/templates/reporter.html` (1 hits)
- `frontend/templates/reporter.html` file

## `hydrateFromBackend` (4 hits)
- `frontend/templates/advanced_ops.html` L591
- `frontend/templates/advanced_ops.html` L1448
- `frontend/templates/reporter.html` L1294
- `frontend/templates/reporter.html` L3167

## `setItem` (18 hits)
- `frontend/templates/advanced_ops.html` L488
- `frontend/templates/advanced_ops.html` L520
- `frontend/templates/advanced_ops.html` L606
- `frontend/templates/advanced_ops.html` L670
- `frontend/templates/advanced_ops.html` L703
- `frontend/templates/advanced_ops.html` L711
- `frontend/templates/dashboard.html` L660
- `frontend/templates/dashboard.html` L820

## `src/workflows/vperfsanity_workflow.py` (1 hits)
- `src/workflows/vperfsanity_workflow.py` file

## `sshpass` (39 hits)
- `src/external_port_mapper.py` `_subprocess_env` L46-60
- `src/external_port_mapper.py` `_has_sshpass` L63-66
- `src/external_port_mapper.py` `ExternalPortMapper._detect_switch_os` L392-557
- `src/main.py` `augment_process_path` L1174-1223
- `src/main.py` `main` L1226-1275
- `src/script_runner.py` `ScriptRunner._subprocess_scp` L387-432
- `src/script_runner.py` `ScriptRunner._subprocess_download` L942-986
- `src/utils/ssh_adapter.py` L5

## Files by relevance
- `frontend/templates/advanced_ops.html` (18 hits)
- `frontend/templates/reporter.html` (18 hits)
- `src/utils/ssh_adapter.py` (13 hits)
- `src/script_runner.py` (8 hits)
- `frontend/templates/dashboard.html` (6 hits)
- `src/workflows/vperfsanity_workflow.py` (4 hits)
- `src/external_port_mapper.py` (4 hits)
- `src/main.py` (2 hits)
- `scripts/context-pack.py` (1 hits)

## Tests to run
`python3 -m pytest tests/test_bundle_diagnostics.py tests/test_ssh_adapter.py tests/test_ssh_auth_rejection.py tests/test_ssh_transport_diagnostics.py tests/test_token_efficiency_scripts.py -x --lf`

## Recent commits on these files
- e381b29 2026-11-10 chore(tests): quiet test runs, one-call quality gate, CI failure summaries
- a09e3f1 2026-10-16 chore(release): prepare v1.6.2
- 2b167cb 2026-10-16 refactor(ui): rename the product to asbuilt-reporter in visible text
- 0ee8f11 2026-10-16 Merge remote-tracking branch 'origin/develop' into fix/v1.6.2-field-feedback
- 4c80a0e 2026-10-16 fix(report): health summary total, retire legacy table layout, FR-12, GOV-1 redaction list
- d2df808 2026-10-16 feat(ui): add interactive day-one checklist to Dashboard (#37)
