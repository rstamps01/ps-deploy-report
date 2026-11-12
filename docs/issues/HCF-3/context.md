# Context pack: HCF-3

Terms: `_check_active_alarms`, `_fixup_health_results`, `HealthChecker`

## `_check_active_alarms` (5 hits)
- `src/health_checker.py` `HealthChecker.run_api_checks` L667-725
- `src/health_checker.py` `HealthChecker._check_active_alarms` L1452-1557
- `tests/test_health_checker.py` `TestHealthChecker.test_check_alarms_no_alarms` L139-143
- `tests/test_health_checker.py` `TestHealthChecker.test_check_alarms_critical` L145-151
- `tests/test_health_checker.py` `TestHealthChecker.test_check_alarms_404` L153-157

## `_fixup_health_results` (2 hits)
- `src/report_builder.py` `VastReportBuilder._fixup_health_results` L5272-5360
- `src/report_builder.py` `VastReportBuilder._create_health_check_section` L5362-5569

## `HealthChecker` (78 hits)
- `src/app.py` `_run_report_job` L2542-3064
- `src/app.py` `_run_health_job` L3390-3527
- `src/health_checker.py` `HealthChecker` L75-3530
- `src/oneshot_runner.py` `OneShotRunner._run_health_checks` L1363-1483
- `src/oneshot_runner.py` `OneShotRunner._run_report` L1728-2109
- `src/utils/switch_password_candidates.py` L10
- `src/utils/switch_ssh_probe.py` L18
- `src/utils/switch_ssh_probe.py` L27

## Files by relevance
- `src/app.py` (9 hits)
- `src/oneshot_runner.py` (5 hits)
- `src/utils/switch_ssh_probe.py` (4 hits)
- `src/health_checker.py` (3 hits)
- `src/report_builder.py` (2 hits)
- `src/utils/switch_password_candidates.py` (1 hits)

## Tests to run
`python3 -m pytest tests/test_app.py tests/test_health_checker.py tests/test_integration.py tests/test_oneshot_runner.py tests/test_utils_switch_ssh_probe.py -x --lf`

## Recent commits on these files
- be4412a 2026-11-10 fix(web): stream vperfsanity Step 4 output and keep Output Results responsive (FR-16)
- b672773 2026-10-16 fix(report): mask credentials in saved ops logs; flag empty /vast/log copies
- 39648ac 2026-10-16 fix(report): mask credentials in the bundled operation log; review follow-ups
- a09e3f1 2026-10-16 chore(release): prepare v1.6.2
- 2b167cb 2026-10-16 refactor(ui): rename the product to asbuilt-reporter in visible text
- a1ae0bc 2026-10-16 fix(report): list generic placeholder images as fallbacks in rack validation
