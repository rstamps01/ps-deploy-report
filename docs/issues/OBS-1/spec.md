# OBS-1 — Artifact filenames mix UTC and local time

**Type:** Bug · **Priority:** P3 · **Size:** S · **Target:** v1.6.3 · **Status:** Planned.

## Observed

Health check files are named in UTC (`..._20260926_013125`): `src/health_checker.py` L252 and L454 use
`datetime.now(tz=timezone.utc)`. Every other artifact uses local time (`datetime.now()`), including the report,
bundle, workflow outputs and ops logs (about 15 call sites). A run's files therefore sort apart, and an engineer
can't match them by name.

## Change

- New helper `utils/timestamps.py::file_timestamp() -> str` (local time, `%Y%m%d_%H%M%S`). Health checker uses
  it, and the other call sites move to it so the convention lives in one place.
- Timestamps inside files stay ISO 8601 with an offset (unchanged).
- Readers that parse timestamps from filenames are checked and keep working: `/api/vnetmap-status`
  (`tests/test_vnetmap_status.py`), `result_scanner`, and the "latest file" lookups.
- The HUB-2 run recorder (v1.7.0) may adopt UTC later; that would be one change in the helper.

## Acceptance

- Failing-first: with a fake clock where UTC and local dates differ, the health JSON/PDF filenames match the
  report filename's local timestamp (today they differ).
- Results-page sorting and the vnetmap-status timestamp tests stay green.
