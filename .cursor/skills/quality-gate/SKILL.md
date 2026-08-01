---
name: quality-gate
description: Run the local equivalent of CI (version-sync, black, flake8, mypy, pytest with the coverage floor) and iterate until green before committing or opening a PR. Use before open-pr, before any release, and whenever verifying a change is ready.
disable-model-invocation: true
---

# quality-gate

Mirrors `.github/workflows/ci.yml` locally so nothing reaches a PR red. Enforces `ci-pipeline-13`.

## Steps (run in order; stop and fix on first failure)

1. **Version sync:** `bash scripts/check-version-sync.sh` (canonical = `src/app.py` `APP_VERSION`).
2. **Format:** `black --check --line-length 120 src/ tests/` (run `black` without `--check` to fix).
3. **Lint:** `flake8 src/ tests/` and `flake8 src/ tests/ --select=E722 --extend-ignore=` (no bare `except`).
4. **Types:** `mypy src/ --ignore-missing-imports --no-strict-optional`.
5. **Tests + coverage:** `python3 -m pytest tests/ --ignore=tests/test_ui.py --ignore=tests/test_integration.py --timeout=60 --timeout-method=signal` with the coverage floor (`--cov-fail-under=60`, per `pyproject.toml`).

## Iterate-until-green

On any failure: fix the root cause, re-run that step, then continue. If the same step fails 3 times, hand off to `remediate-failure` (bounded loop + escalation) instead of thrashing. Compose the local `iterative-improvement-loop` for the bounded retries.

## Coverage ratchet

Coverage is **upward-only**: never lower `--cov-fail-under`. A FEAT that drops coverage needs more tests; a BUG needs its failing-first regression test. When coverage rises comfortably above the floor, raise the floor (toward 80%, TSE items) in `pyproject.toml` + `ci-pipeline-13`.

## Known local-env note

Some `tests/test_oneshot_runner.py` cases open a real socket to a test cluster IP and hang on machines that blackhole it (60s timeout) while passing in CI (fast connection refusal). Treat these as environment artifacts, not regressions (see `docs/PROJECT-STATUS.md`); flaky/nondeterministic failures are quarantined per the test-reliability policy, not retried by `remediate-failure`.

## Leverages

Rules: `ci-pipeline-13`, `testing-standards-06`. Skills: `iterative-improvement-loop`, `verification-before-completion`, `remediate-failure`.

## Completion checklist

- [ ] version-sync, black, flake8 (+E722), mypy all pass
- [ ] pytest green; coverage >= floor
- [ ] Any 3x-failing step escalated to `remediate-failure`, not force-passed
