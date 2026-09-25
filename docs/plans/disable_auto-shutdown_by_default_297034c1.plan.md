---
name: Disable auto-shutdown by default
overview: Make the QP-3 browser-close auto-shutdown opt-in and OFF by default, so switching away from the browser tab no longer tears down the app, while leaving the feature in place for anyone who explicitly enables it via config.
todos:
  - id: default-off
    content: Set AUTO_SHUTDOWN_DEFAULTS enabled=False in src/app.py and update comment
    status: completed
  - id: main-guard
    content: Change run_gui watchdog guard fallback to enabled=False in src/main.py
    status: completed
  - id: config
    content: "Set auto_shutdown.enabled: false + explanatory comment in config.yaml.template"
    status: completed
  - id: js-comment
    content: Update initHeartbeat comment in app.js to reflect opt-in/off-by-default
    status: completed
  - id: tests
    content: Update test_app heartbeat tests (default-off + enabled path) and revert test_launcher thread count to 1
    status: completed
  - id: docs
    content: Update CHANGELOG and TODO-ROADMAP to document opt-in/off-by-default
    status: completed
  - id: verify
    content: Run targeted pytest, flake8, black
    status: completed
isProject: false
---

# Disable Auto-Shutdown by Default

## Why

The client pings `/api/heartbeat` via `setInterval(ping, 5000)`. Browsers throttle/suspend timers in backgrounded tabs, so an open-but-inactive tab goes silent past the 20s grace window and `_auto_shutdown_watchdog` calls `server.shutdown()` prematurely. Interval-based liveness is fundamentally unreliable for distinguishing "tab closed" from "tab inactive," so we turn the feature off by default and keep it opt-in.

## Approach

Flip the default to disabled. The server then reports `auto_shutdown: false`, and the existing client logic in [frontend/static/js/app.js](frontend/static/js/app.js) (lines 41-45) already stops pinging after the first response. The watchdog already early-returns when disabled, and `main.run_gui` already guards thread start on `enabled`. No feature code is deleted; it remains usable via `auto_shutdown.enabled: true`.

## Changes

- [src/app.py](src/app.py): in `AUTO_SHUTDOWN_DEFAULTS` (line 56) set `"enabled": False`. Update the comment block (lines 50-54) to note it is opt-in and why.
- [src/main.py](src/main.py) (line 944): change the watchdog guard fallback from `.get("enabled", True)` to `.get("enabled", False)` so an app without the key never starts the watchdog (consistency with the new default).
- [config/config.yaml.template](config/config.yaml.template) (lines 269-272): set `enabled: false` and update the comment to explain that background-tab timer throttling can cause premature shutdown, so the feature is off by default and opt-in.
- [frontend/static/js/app.js](frontend/static/js/app.js) (lines 28-31): update the `initHeartbeat` comment to reflect opt-in/off-by-default. No functional JS change required (it already self-disables on `auto_shutdown: false`).

## Tests

- [tests/test_app.py](tests/test_app.py):
  - `test_heartbeat_marks_browser_seen_and_returns_ok` (line 2179): build the app with `create_flask_app(config={"auto_shutdown": {"enabled": True}})` so it still verifies the "browser seen" + `auto_shutdown: true` path; keep `BROWSER_SEEN`/`LAST_HEARTBEAT` assertions.
  - Add a small test asserting the default app (`create_flask_app()`) returns `auto_shutdown: false` from `/api/heartbeat`.
  - `TestEvaluateAutoShutdown` and `TestAnyJobRunning` are unchanged (pure-logic tests with explicit kwargs).
- [tests/test_launcher.py](tests/test_launcher.py) (line 97): revert `test_run_gui_starts_flask` from `self.assertEqual(mock_thread.start.call_count, 2)` back to `mock_thread.start.assert_called_once()` (watchdog no longer starts by default).

## Docs

- [CHANGELOG.md](CHANGELOG.md): under `[Unreleased]` add a `### Changed` (or `### Fixed`) entry: auto-shutdown on browser close is now OFF by default (opt-in via `auto_shutdown.enabled`), because background-tab timer throttling could shut the app down while the tab was still open.
- [docs/TODO-ROADMAP.md](docs/TODO-ROADMAP.md): note QP-3 item 3 changed to opt-in/off-by-default.

## Verification

- `python3 -m pytest tests/test_app.py tests/test_launcher.py -q` (targeted, fast).
- `flake8 src/ tests/` and `black --check --line-length 120 src/ tests/`.
- Optional manual smoke: launch GUI, switch away from the tab for >30s, confirm the server stays up; set `auto_shutdown.enabled: true` and confirm the watchdog still works when actually closing the tab.

## Effort

Low. ~5-6 files, mostly one-line changes plus two test tweaks and docs. No impact on the report/health/one-shot pipeline.
