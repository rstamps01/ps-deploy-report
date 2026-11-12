### Changed
- **Active Alarms (HCF-3): unresolved CRITICAL alarms now fail the Active Alarms health check.** Unresolved MAJOR alarms are still a warning, and resolved alarms are ignored. Before, any number of critical or major alarms only produced a warning. Reports regenerated from saved JSON apply the same rule, so an older export that lists a CRITICAL alarm now shows the check as failed. To keep the old behavior (both severities warn), set `health_check.alarms.fail_on: none`.
- **Active Alarms details (HCF-3):** the check now reports separate `critical_unresolved` and `major_unresolved` counts, and the PDF's Alarms & Events table shows one row for each.

### Added
- **`health_check.alarms.fail_on` (HCF-3):** sets which unresolved alarms fail the Active Alarms check: `critical` (default), `major` (critical and major both fail) or `none` (both warn). An invalid value logs a warning and uses `critical`.
