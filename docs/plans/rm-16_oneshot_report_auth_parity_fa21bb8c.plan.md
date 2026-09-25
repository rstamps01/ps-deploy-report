---
name: RM-16 oneshot report auth parity
overview: Fix the Test Suite tile's report-embedded health check so it mirrors the successful Reporter-tile / standalone-health-phase auth path by threading the pre-validated `switch_password_by_ip` map (and `switch_password_candidates` list) into the `HealthChecker` invoked from `OneShotRunner._run_report`.
todos:
  - id: tdd-rm16
    content: Write 4 failing tests in tests/test_oneshot_runner.py::TestRM16ReportHealthAuthParity covering password_by_ip, password_candidates, empty-map, and proxy_jump combinations
    status: completed
  - id: impl-rm16
    content: Thread self._switch_password_by_ip and self._switch_password_candidates into sw_cfg in OneShotRunner._run_report (src/oneshot_runner.py lines ~1467-1478)
    status: completed
  - id: doc-rm16
    content: Add RM-16 entry to CHANGELOG.md and docs/TODO-ROADMAP.md
    status: completed
  - id: qa-rm16
    content: Run black, flake8, and full pytest; confirm 0 regressions
    status: completed
  - id: release-v156
    content: "Bundle RM-15 + Windows crash fix + RM-16 as v1.5.6: bump APP_VERSION, update CHANGELOG, commit, tag v1.5.6, push to develop + main"
    status: completed
isProject: false
---

## Root cause

The Test Suite's `switch_ssh` category prints `error / warning / warning` while the Reporter tile prints `Pass` because the HealthChecker invoked from `OneShotRunner._run_report` is built with a `sw_cfg` that only contains the single UI-entered `switch_password`. The OneShotRunner has already pre-validated switches and populated `self._switch_password_by_ip` (which is why `vnetmap` and `switch_config` succeeded in the same run), but `_run_report` throws that map away when constructing the HealthChecker.

### Asymmetry (all three siblings thread the map; `_run_report` does not)

- `OneShotRunner._run_health` (Phase 2 standalone) — [src/oneshot_runner.py](src/oneshot_runner.py) L1252: `switch_ssh_config["password_by_ip"] = dict(self._switch_password_by_ip)` (RM-2).
- `_run_report_job` (Reporter tile) — [src/app.py](src/app.py) L2267–L2274: injects both `password_candidates` and `password_by_ip` (RM-13 + RM-15).
- `OneShotRunner._get_workflow_credentials` — [src/oneshot_runner.py](src/oneshot_runner.py) L270–L271: hands the map to every switch-touching workflow.
- `OneShotRunner._run_report` — [src/oneshot_runner.py](src/oneshot_runner.py) L1467–L1478: **does not thread either value** and this is the bug.

### Evidence from the user's 00:14:14 log

```
Authentication (password) successful!   <- jump to CNode with node_pw OK
Auth banner: Welcome to NVIDIA Cumulus
Authentication (password) failed.       <- switch_pw is wrong for .153 / .154
```

`vnetmap_output_..._20260423_000137.txt` and `switch_configs_20260423_001247.json` from the same run confirm that a working per-IP credential does exist in `self._switch_password_by_ip`; it is simply discarded at report time.

## Change (single file, single block)

Track as **RM-16** in `docs/TODO-ROADMAP.md` and `CHANGELOG.md`.

Edit `OneShotRunner._run_report` in [src/oneshot_runner.py](src/oneshot_runner.py) — the `if switch_pw:` block around lines 1467–1478:

```python
if switch_pw:
    sw_cfg = {
        "username": self._credentials.get("switch_user", "cumulus"),
        "password": switch_pw,
    }
    # RM-16: match _run_health + _run_report_job parity — thread the
    # pre-validated per-IP map and candidate list so HealthChecker uses
    # the working credential for each switch instead of mis-authenticating
    # every switch with the single UI-entered password.
    if self._switch_password_by_ip:
        sw_cfg["password_by_ip"] = dict(self._switch_password_by_ip)
    if self._switch_password_candidates:
        sw_cfg["password_candidates"] = list(self._switch_password_candidates)
    if self._tunnel_address:
        sw_cfg["proxy_jump"] = {
            "host": self._credentials.get("cluster_ip"),
            "username": self._credentials.get("node_user", "vastdata"),
            "password": self._credentials.get("node_password"),
        }
    tiers.append(3)
```

No other files require behavior changes. `HealthChecker` already consumes both keys (`password_by_ip` via `run_switch_ssh_checks`; `password_candidates` via its RM-13 probe fallback).

## Tests (TDD)

Add to `tests/test_oneshot_runner.py` — a new `TestRM16ReportHealthAuthParity` class alongside the existing `_run_report` tests:

- `test_run_report_threads_switch_password_by_ip_into_healthchecker` — seed `runner._switch_password_by_ip = {"<ip>": "pw1", "<ip>": "pw2"}`, mock `HealthChecker` ctor, call `_run_report`, assert `switch_ssh_config["password_by_ip"] == {"<ip>": "pw1", "<ip>": "pw2"}`.
- `test_run_report_threads_switch_password_candidates_into_healthchecker` — seed `runner._switch_password_candidates = ["a", "b"]`, assert `switch_ssh_config["password_candidates"] == ["a", "b"]`.
- `test_run_report_omits_password_by_ip_when_empty` — assert the key is absent when the map is empty (avoid handing HealthChecker an empty dict).
- `test_run_report_preserves_proxy_jump_with_new_keys` — combined scenario: tunnel + map + candidates all present; assert all three keys land together.

Pattern should mirror the existing `_run_health` tests in `tests/test_oneshot_runner.py` (search for `password_by_ip` uses already asserted in `_run_health`).

## Quality gates

- `black --check --line-length 120 src/oneshot_runner.py tests/test_oneshot_runner.py`
- `flake8 src/ tests/`
- `python3 -m pytest tests/test_oneshot_runner.py -v`
- `python3 -m pytest tests/ -q` (full suite — expect 1096+ pass)

## Release (per release-packaging-12.mdc)

RM-16 bundles with the already-staged RM-15 + Windows crash fix as v1.5.6 patch release. Version bumps, CHANGELOG section, and tag push happen together in a single v1.5.6 commit once RM-16 is green.
