# Project Status — Baseline Snapshot

**Purpose:** A concise, point-in-time record of the repository's known state. Updated at meaningful checkpoints (baseline captures, releases, milestone completions). For the live roadmap and per-item status, see [docs/TODO-ROADMAP.md](TODO-ROADMAP.md); for user-facing change history, see [CHANGELOG.md](../CHANGELOG.md).

---

## 2026-07-31 — Pre-CI/CD-pipeline baseline (M0)

Established a known, documented baseline before starting the agentic CI/CD pipeline build.

### State

- **Branch:** `develop` at `e48e581` — a self-contained baseline commit that segments the in-flight **v1.6.0** development work. This is a commit + documentation checkpoint only; it is **not** a release (no `v1.6.0` tag pushed).
- **Version strings:** `1.6.0` across all locations (`src/app.py` `APP_VERSION` is canonical; `src/__init__.py`, `src/main.py`, `packaging/vast-reporter.spec`, README badge all in sync — version-sync check passes).
- **Branch topology:** `develop` was fast-forwarded to `main` (`52d4560`, the released `v1.5.8` + one-pager docs) before the baseline commit, so `develop` now contains all released history plus the 1.6.0 segment. `develop` is ahead of `origin/develop` (baseline + released commits to be pushed).

### What the 1.6.0 baseline contains

- **Teleport:** `tsh` auto-discovery (PATH + well-known install locations) + startup PATH augmentation; Teleport Settings UI (editable path, Run Discovery, persistence) and green/yellow install-status pill; `GET /api/teleport/status`, `POST /api/teleport/discover`; `docs/TELEPORT-MODE.md`.
- **Teleport-mode SSH routing:** `network_config`, `support_tool`, `log_bundle`, and `vperfsanity` now route SSH/SCP through the forwarded tunnel endpoint.
- **Onyx/MLNX-OS switches:** vnetmap authenticates as the discovered `-u admin`; per-IP `(user, password)` propagated to health checks; switch-config backup filenames sanitized of ANSI/terminal escapes; clearer web-API failure messaging.
- **Cross-cluster vnetmap segmentation:** authoritative per-cluster lookup (no shared flat-file fallback when a cluster key is known) plus an identity guard, in both `app.py` and `oneshot_runner.py`.
- **Fixes:** `/api/vnetmap-status` string-format error; blank bundle `SUMMARY.md` version.

### Not yet folded (release step)

Two fixes remain under CHANGELOG `[Unreleased]` and will fold into `[1.6.0]` at release time:
- vnetmap authenticated to Onyx switches as the wrong user.
- Teleport-mode VMS Log Bundle and vperfsanity SSH routing.

### Quality gate (recorded)

| Gate | Result |
| --- | --- |
| version-sync (`scripts/check-version-sync.sh`) | PASS (1.6.0) |
| `black --check --line-length 120 src/ tests/` | PASS (89 files) |
| `flake8 src/ tests/` | PASS |
| `mypy src/ --ignore-missing-imports --no-strict-optional` | PASS (no issues, 43 files) |
| Deterministic unit suite | GREEN (1582 passing) |

**Known local-env artifacts (not regressions):** 5 `tests/test_oneshot_runner.py` cases (`TestOneShotPrevalidation::test_cluster_api_unreachable`, `TestOneShotIncludeHealth::{test_run_all_phases_ops_and_bundling, test_run_all_with_report_calls_run_report, test_total_operations_with_report, test_total_operations_without_report}`) time out on this development Mac. Cause: `run_all()`'s pre-existing switch-probe safety net calls `_validate_switch_ssh()`, which opens a real socket to the test's cluster IP (`10.0.0.1`). This host is blackholed on the local network, so the connect hits the 60s `pytest-timeout` kill; CI refuses the connection quickly and the tests pass. Hermeticity is tracked as pipeline test-reliability work (plan §21).

### Next

Proceed with the agentic CI/CD pipeline milestones (M1 foundation onward) per the pipeline plan in `.cursor/plans/`.
