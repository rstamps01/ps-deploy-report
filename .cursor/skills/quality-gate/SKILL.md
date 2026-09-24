---
name: quality-gate
description: Run the local equivalent of CI (version-sync, black, flake8, mypy, pytest with the coverage floor) and iterate until green before committing or opening a PR. Use before open-pr, before any release, and whenever verifying a change is ready.
disable-model-invocation: true
---

# quality-gate

Mirrors `.github/workflows/ci.yml` locally so nothing reaches a PR red. Enforces `ci-pipeline-13`.

## Command source of truth

The concrete commands and the blocking-gate order are declared in the project manifest [`.cursor/pipeline.yml`](../../pipeline.yml) (`commands:` + `quality.blocking_gate`), so this skill is portable across projects. Resolve them via the adapter rather than assuming a stack:

- `python3 scripts/pipeline_manifest.py gate` — prints the blocking-gate commands in order (run each; stop on first failure).
- `python3 scripts/pipeline_manifest.py get <name>` — one command (e.g. `test_cov`, `format_fix`).

The steps below are the resolved commands for **this** (Python) repo; if they ever drift from the manifest, the manifest wins (CI validates it with `pipeline_manifest.py validate --strict`).

## Steps (run in order; stop and fix on first failure)

1. **Version sync:** `bash scripts/check-version-sync.sh` (canonical = `src/app.py` `APP_VERSION`).
2. **Format:** `black --check --line-length 120 src/ tests/` (run `black` without `--check` to fix).
3. **Lint:** `flake8 src/ tests/` and `flake8 src/ tests/ --select=E722 --extend-ignore=` (no bare `except`).
4. **Types:** `mypy src/ --ignore-missing-imports --no-strict-optional`.
5. **Tests + coverage:** `python3 -m pytest tests/ --ignore=tests/test_ui.py --ignore=tests/test_integration.py -m "not flaky"` with the coverage floor (`--cov-fail-under=60`, per `pyproject.toml`). A global `--timeout=300` backstop (pyproject `addopts`) + the `tests/conftest.py` network guard keep the suite hang-proof; `-m "not flaky"` excludes quarantined tests, mirroring CI.

## Iterate-until-green

On any failure: fix the root cause, re-run that step, then continue. If the same step fails 3 times, hand off to `remediate-failure` (bounded loop + escalation) instead of thrashing. Compose the local `iterative-improvement-loop` for the bounded retries.

## Coverage ratchet

Coverage is **upward-only**: never lower `--cov-fail-under`. A FEAT that drops coverage needs more tests; a BUG needs its failing-first regression test. When coverage rises comfortably above the floor, raise the floor (toward 80%, TSE items) in `pyproject.toml` + `ci-pipeline-13`.

## Test reliability (hang-proofing + flaky quarantine)

- **Network guard (fixed the old hang):** `tests/conftest.py` makes non-loopback socket connects fail fast with `ConnectionRefusedError`, so tests that would otherwise open a real socket to a cluster IP (e.g. some `tests/test_oneshot_runner.py` cases) behave like CI (instant refusal) instead of blocking on a machine that blackholes `10.0.0.0/8`. Integration tests and `VAST_TEST_ALLOW_NETWORK=1` opt out.
- **Timeout backstop:** a global `--timeout=300` (pyproject `addopts`, via `pytest-timeout`) guarantees no single test can stall the run on any OS.
- **Flaky quarantine:** a failure that passes on re-run is marked `@pytest.mark.flaky`, excluded from the blocking gate (`-m "not flaky"` in CI + local), and filed as a BUG — `remediate-failure` never burns attempts on nondeterminism.

## Leverages

Rules: `ci-pipeline-13`, `testing-standards-06`. Skills: `iterative-improvement-loop`, `verification-before-completion`, `remediate-failure`.

## Completion checklist

- [ ] version-sync, black, flake8 (+E722), mypy all pass
- [ ] pytest green; coverage >= floor
- [ ] Any 3x-failing step escalated to `remediate-failure`, not force-passed
