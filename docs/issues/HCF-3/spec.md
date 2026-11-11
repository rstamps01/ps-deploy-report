# HCF-3 — Critical alarms only warn

**Type:** Policy change (bug in effect) · **Priority:** P1 · **Target:** v1.6.3 (moved from v1.7.0 by the owner,
2026-11-11) · **Status:** Planned. Reverses the v1.5.0 HC-1 decision (reversal accepted 2026-09-25,
`docs/DECISIONS.md`).

## Observed

In one field run, 17 unresolved critical/major alarms produced a warning on Active Alarms, so the health check
looked clean enough to hand over.

## Root cause

- `HealthChecker._check_active_alarms` (`src/health_checker.py` L1452–1537) groups `CRITICAL` and `MAJOR`
  together and returns `warning` for any match (L1519–1528).
- `ReportBuilder._fixup_health_results` (`src/report_builder.py` L5328–5332) rewrites older `fail` results to
  `warning` when a saved JSON is re-rendered.
- `HealthChecker.__init__` (L108–123) takes only capacity/handle thresholds; no call site passes the
  `health_check` config section (`app.py` L2894–2908 and L3390–3456, `oneshot_runner.py` L1441–1446).

## Change

- New key `health_check.alarms.fail_on: critical` (`critical` / `major` / `none`) in
  `config/config.yaml.template` and `README.md`.
  - With `critical` (the default), unresolved critical alarms fail and major alarms warn.
  - With `major`, both fail.
  - With `none`, both warn (the old behavior).
- `HealthChecker` receives the alarm policy from the three call sites. Details split the counts into
  `critical_unresolved` and `major_unresolved`, keeping the `alarms[]` list that HCF-6 already renders
  (`utils/health_detail_groups.py` L394–441, `health.html` L406–421).
- The render-time fixup applies the configured policy to saved results that carry `details.alarms`, instead of
  always downgrading. Results without per-alarm severities keep their saved status.
- Remediation text that assumes alarms are warnings (`health_checker.py` ~L289–296, ~L510–515) is updated.

## Acceptance

- Failing-first: one unresolved CRITICAL alarm gives `fail` with the default config (today `warning`).
- MAJOR only gives `warning`; `fail_on: major` gives `fail`; `fail_on: none` gives `warning` for both; resolved
  alarms are ignored.
- Re-rendering a pre-HC-1 JSON and a v1.6.2 JSON with `details.alarms` follows the configured policy; a JSON
  without details keeps its status.
- The PDF summary counts and the Health page agree.
- Release notes state the behavior change and the `fail_on: none` opt-out.
