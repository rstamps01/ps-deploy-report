# Release Notes — v1.5.6

**Date:** 2026-04-23
**Branch:** develop → main
**Previous release:** v1.5.5 (2026-03-21)
**Artifacts:**
- [VAST-Reporter-v1.5.6-mac.dmg](https://github.com/rstamps01/ps-deploy-report/releases/download/v1.5.6/VAST-Reporter-v1.5.6-mac.dmg)
- [VAST-Reporter-v1.5.6-win.zip](https://github.com/rstamps01/ps-deploy-report/releases/download/v1.5.6/VAST-Reporter-v1.5.6-win.zip)

---

## Executive Summary

v1.5.6 is a stability and parity release that closes the remaining gaps where the Reporter tile and Test Suite tile produced different results for the same cluster because they threaded switch credentials through different code paths. It also adds Windows launch crash-resilience so the app no longer silently exits when its default port is unavailable, seeds the hardware library with two new Milan EBox models, and cleans up CI so builds stay green on fresh runners after `config/config.yaml` became gitignored in v1.5.3.

No breaking changes. No config file format changes. No CLI changes.

---

## Highlights

### RM-15 — Heterogeneous-fleet `vnetmap` parity (Reporter tile)

The Reporter tile (`/generate → _run_report_job`) previously populated `switch_password_candidates` but not `switch_password_by_ip`, so `VnetmapWorkflow`'s Fast path (`vnetmap.py --multiple-passwords` with a per-switch IP→password heredoc map) never engaged and heterogeneous fleets fell back to the Legacy candidate-sweep path. When two leaves ran on `cumulus/Vastdata1!` and a spare ran on `cumulus/VastData1!`, `vnetmap` would either cycle through candidates or fail outright.

The fix extracts the probe logic into a shared utility (`src/utils/switch_ssh_probe.py`) with two functions — `probe_switch_password()` for a single IP and `build_switch_password_by_ip()` for a list — and wires a new `_preprobe_switch_passwords_for_job()` helper into `_run_report_job` so the Reporter tile builds the same `switch_password_by_ip` map the Test Suite tile already constructs. `HealthChecker._probe_switch_password` is now a thin delegator to the shared utility.

**Impact:** Reporter-tile `vnetmap` runs cleanly on heterogeneous fleets with a single pass; no more candidate-sweep retries visible in the logs.

### RM-16 — Test-Suite report-embedded health-check auth parity

On the same cluster (`selab-var-203`) and the same heterogeneous fleet, the Reporter-tile `switch_ssh` health category showed Pass while the Test-Suite-tile category showed `[ERR] MLAG Status` / `[WARN] Switch NTP` / `[WARN] Switch Config Readability` — even though the same one-shot run's `vnetmap_output_*.txt` and `switch_configs_*.json` confirmed a working credential. Root cause: `OneShotRunner._run_report` was building its `switch_ssh_config` for the report-embedded `HealthChecker` from only the single UI-entered `switch_password`, silently discarding the pre-validated `self._switch_password_by_ip` map and the resolved `self._switch_password_candidates` list that every other auth path (`_run_health` RM-2, `_get_workflow_credentials`, `_run_report_job` RM-13 + RM-15) already threaded.

`_run_report` now mirrors the `_run_health` RM-2 threading and passes `password_by_ip`, `password_candidates`, and the existing `proxy_jump` block into `switch_ssh_config`.

**Impact:** Reporter-tile and Test-Suite-tile `switch_ssh` categories now report identical results on heterogeneous fleets.

### Windows launch crash resilience

Fixes a silent launch crash on Windows when port 5173 is reserved by Hyper-V / WSL2 or held by another process — `vast-reporter.exe` would raise `OSError (WSAEACCES 10013)` and the console window would close instantly, leaving no diagnostic breadcrumb for the operator.

Three changes in `src/main.py`:

1. **Port fallback ladder.** `run_gui()` iterates through `_FALLBACK_PORTS = [5173, 8080, 8081, 8082, 8888, 9090]` on `OSError`, printing a diagnostic line for each attempt and pausing with `input()` if all ports fail when running as a frozen (PyInstaller) executable.
2. **Top-level crash handler.** The `if __name__ == "__main__":` block is wrapped in `try/except Exception` so any fatal error prints `FATAL ERROR: {exc}` plus a full traceback and pauses with `input()` on a frozen build.
3. **`--port` CLI argument.** A new `_extract_port_from_argv()` helper parses and consumes `--port <number>` from `sys.argv`, passing it to `run_gui()` so operators can skip the fallback ladder entirely.

**Impact:** The Windows client now exits gracefully with a visible diagnostic instead of crashing silently.

### Hardware library additions

Two new Milan-generation EBoxes added to the built-in device library:

| Identifier key | Type | U Height | Description |
|----------------|------|----------|-------------|
| `supermicro_milan_ebox` | EBox | 2U | Supermicro Milan EBox |
| `smc_milan_ebox`        | EBox | 2U | SMC Milan EBox        |

Both ship with `2U` rack images bundled into the `.dmg` / `.zip` via the PyInstaller spec.

---

## Fixed

- **RM-15** — Reporter tile pre-probes switches and threads `switch_password_by_ip` into `VnetmapWorkflow` + `HealthChecker` so heterogeneous fleets no longer cycle through candidate sweeps.
- **RM-16** — `OneShotRunner._run_report` now preserves the pre-validated per-IP password map and candidate list when instantiating the report-embedded `HealthChecker`, eliminating the Reporter/Test-Suite `switch_ssh` category discrepancy.
- **Windows launch crash** — port fallback ladder, top-level crash handler with visible traceback, and `--port` CLI flag all added so `vast-reporter.exe` no longer silently exits on `OSError`.
- **CI quality-gate** — 7 mypy `no-any-return` / `var-annotated` errors in `src/utils/switch_ssh_probe.py`, `src/app.py`, `src/oneshot_runner.py`, and `src/health_checker.py` resolved with type-only adjustments (no runtime behaviour change).
- **CI build-release** — `build-release.yml` and `ci.yml` build-smoke jobs now seed `config/config.yaml` from the committed template before running PyInstaller, matching the application bootstrap behaviour (RM-1 Supplementary untracked the file in v1.5.3).
- **UI test fixture** — `tests/test_ui.py::flask_server` falls back to `config.yaml.template` when `config.yaml` is absent, keeping the UI test suite green on fresh CI runners.

---

## Added

- `src/utils/switch_ssh_probe.py` — shared SSH credential probing utility (`probe_switch_password`, `build_switch_password_by_ip`) with 17 unit tests in `tests/test_utils_switch_ssh_probe.py`.
- `src/app.py::_preprobe_switch_passwords_for_job` — Reporter-tile helper that builds the `switch_password_by_ip` map once after authentication and fans it out to `VnetmapWorkflow` and `HealthChecker`. 8 new tests in `tests/test_app.py::TestRM15SwitchPreProbe`.
- `tests/test_oneshot_runner.py::TestRM16ReportHealthAuthParity` — 4 new tests pinning the `_run_report` threading of `password_by_ip`, `password_candidates`, empty-map handling, and `proxy_jump` preservation.
- `_FALLBACK_PORTS` list and `_extract_port_from_argv()` in `src/main.py`.
- Two new built-in EBox entries (`supermicro_milan_ebox`, `smc_milan_ebox`) in `src/hardware_library.py` plus the matching 2U PNG assets in `assets/hardware_images/`.

---

## Changed

- `HealthChecker._probe_switch_password` is now a thin delegator to `utils.switch_ssh_probe.probe_switch_password` — SSH I/O moved into the shared utility so tests that simulate probe responses must patch `utils.switch_ssh_probe.run_ssh_command` / `run_interactive_ssh` rather than the `health_checker.*` module-level names.
- `OneShotRunner._run_report` now mirrors `_run_health`'s RM-2 + `_run_report_job`'s RM-13 / RM-15 credential threading when building `switch_ssh_config`.
- Build-release and CI workflows now seed `config/config.yaml` from the template before invoking `packaging/build-mac.sh` / `packaging/build-windows.ps1`.

---

## Test Coverage

- Unit tests: 1110 passing (up from 1106 in v1.5.5; +25 new tests across RM-15 / RM-16 / ci).
- Integration tests: 16 passing.
- Full-suite coverage: 62.9% (gate: 60%).
- Full CI pipeline green on `main`: todo-list-check, quality-gate, ui-tests, advanced-ops-tests, health-check-tests, integration-tests, unit-tests (3.11 + 3.12), build-smoke (macOS + Windows).
- Full build-release pipeline green on tag `v1.5.6`: quality-gate, build (macOS), build (Windows), release — `.dmg` and `.zip` artifacts attached to the GitHub Release.

---

## Upgrade Notes

- **No breaking changes.** No CLI changes, no config file format changes.
- Download `VAST-Reporter-v1.5.6-mac.dmg` or `VAST-Reporter-v1.5.6-win.zip` from the GitHub Release page and replace the existing `VAST Reporter.app` / `vast-reporter.exe`.
- Windows operators who previously worked around port-5173 conflicts by restarting Hyper-V can now pass `--port 8080` (or any other free port) on the command line.
- Heterogeneous-fleet customers (switches on a mix of `Vastdata1!` / `VastData1!` / site-specific passwords) should see identical Reporter and Test-Suite `switch_ssh` results for the first time.

---

## Known Limitations

- Coverage target remains 60%; roadmap target is 75%+ (see `docs/TODO-ROADMAP.md` TSE-9).
- The `--version` CLI flag does not early-exit before Flask server startup; running `--version` on a machine with port 5173 in use will surface the port binding error. Harmless when using the packaged `.dmg` / `.exe`.
