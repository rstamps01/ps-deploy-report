# HCF-3 tasks

- [x] T1 Failing-first: one unresolved CRITICAL alarm gives `fail` with the default config (was `warning`; `test_check_alarms_critical`)
- [x] T2 Shared pure helper `src/utils/alarm_policy.py` (normalize `fail_on`, read it from config, count by severity, status from counts or saved details)
- [x] T3 `HealthChecker(alarm_fail_on=...)`; `_check_active_alarms` splits `critical_unresolved` / `major_unresolved` and applies the policy; `alarms[]` unchanged
- [x] T4 Call sites pass the policy: `app.py` `_run_report_job` (both branches) and `_run_health_job`; `oneshot_runner.py` `_run_health_checks` and `_run_report`
- [x] T5 `ReportConfig.alarm_fail_on` from `health_check.alarms.fail_on`; `_fixup_health_results` applies it to saved results with per-alarm severities and moves the summary bucket with the status
- [x] T6 Remediation guidance and the alarm/inactive-node correlation no longer assume alarms are warnings; Alarms & Events detail group shows split counts
- [x] T7 `config/config.yaml.template` and `README.md` document the key
- [x] T8 Tests: MAJOR only, `fail_on: major`, `fail_on: none`, resolved ignored, invalid value, pre-HC-1 and v1.6.2 JSON re-render, JSON without details, call sites (OneShot both sites, `_run_health_job`), live JSON re-render matches the Health page summary
- [x] T9 Changelog fragment
- [ ] T10 `quality-gate`, review and PR (parent)
- [ ] T11 Release notes for v1.6.3 name the behavior change and the `fail_on: none` opt-out (release)
- [ ] T12 Optional follow-up: expose `health_check.alarms.fail_on` in the Advanced Configuration UI Health Check section (not in this change)
