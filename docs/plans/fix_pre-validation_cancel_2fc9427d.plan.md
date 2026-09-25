---
name: Fix Pre-Validation Cancel
overview: "Fix two issues with one-shot pre-validation: (1) SSL certificate verification hangs from default verify_ssl=true in the API handler created during switch validation, and (2) no way to cancel a running pre-validation. Solution: fix SSL config in backend checks, add cancel_event support to prevalidation, make the validate route async with polling, and add a Cancel button on the frontend."
todos:
  - id: fix-ssl
    content: Fix SSL verify and timeout in _validate_switch_ssh, _run_health_checks, _run_report; add cancel checks between validation steps
    status: completed
  - id: fix-route
    content: Make /advanced-ops/oneshot/validate async with background thread, reusing cancel/status endpoints
    status: completed
  - id: fix-frontend
    content: Add Cancel button during validation, switch to fire-and-poll pattern instead of blocking fetch
    status: completed
  - id: verify
    content: Run tests and flake8 to confirm no regressions
    status: completed
isProject: false
---

# Fix Pre-Validation SSL Hang and Add Cancel Support

## Root Causes

1. **SSL hang** in `_validate_switch_ssh()` at [src/oneshot_runner.py](src/oneshot_runner.py) line 267: `create_vast_api_handler()` is called without config, so `verify_ssl` defaults to `True` (see [src/api_handler.py](src/api_handler.py) line 2701). The handler retries 3x against the self-signed cert, blocking ~30+ seconds.
2. **No cancel** on the frontend: `runOneShotValidation()` in [advanced_ops.html](frontend/templates/advanced_ops.html) does a synchronous `await fetch(...)` with no `AbortController`, and no Cancel button is shown during validation.

## Fix 1: SSL and Timeout in Backend Validation Checks

In [src/oneshot_runner.py](src/oneshot_runner.py), update `_validate_switch_ssh()`:

- Pass config `{"api": {"verify_ssl": False, "timeout": 10, "max_retries": 1}}` to `create_vast_api_handler()`
- This prevents SSL retries against self-signed cluster certs
- Same pattern should apply to `_run_health_checks()` and `_run_report()` for consistency

Also add `self._check_cancel()` calls between each validation check in `run_prevalidation()`.

## Fix 2: Make Validate Route Async with Cancel

In [src/app.py](src/app.py), change the `/advanced-ops/oneshot/validate` route:

- Run `runner.run_prevalidation()` in a background thread (matching the existing `/oneshot/start` pattern)
- Store the runner in `app.config["ONESHOT_RUNNER"]` during validation
- Return immediately with `{"status": "validating"}`
- Reuse `/advanced-ops/oneshot/status` to poll for validation completion (state will show `phase: "validating"` with `validation_results` populated when done)
- Reuse `/advanced-ops/oneshot/cancel` to cancel

## Fix 3: Frontend Cancel Button During Validation

In [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html):

- Show the Cancel button when validation starts
- Switch `runOneShotValidation()` from a blocking `await fetch` to a fire-and-poll pattern using the existing `startOneShotPolling()` mechanism
- When validation completes (polled status shows `validation_results` populated), call `renderValidationResults()`
- Cancel button calls `/advanced-ops/oneshot/cancel` and resets UI
