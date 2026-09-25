---
name: Fix One-Shot Route Guard
overview: Change the developer-mode route guard from prefix matching to exact page-route matching, so the Reporter page can access /advanced-ops/* and /health/* API endpoints in standard mode.
todos:
  - id: fix-guard
    content: Change route guard from startswith to exact match (in) for dev-only page routes
    status: completed
isProject: false
---

# Fix One-Shot Route Guard for Reporter Page

## Problem

The route guard in [src/app.py](src/app.py) line 214 uses `startswith`, which blocks ALL sub-routes:

```python
if request.path.startswith(("/advanced-ops", "/health", "/config")):
```

This prevents the Reporter page (standard UI) from calling:

- `/advanced-ops/workflows` — populates One-Shot checklist
- `/advanced-ops/oneshot/*` — validation, start, status, cancel
- `/advanced-ops/output` — log output polling
- `/advanced-ops/state-snapshot` — backend state hydration
- `/advanced-ops/tools`, `/advanced-ops/tools/update` — deployment tools
- `/advanced-ops/bundle/*` — result bundling/download
- `/health/run`, `/health/status`, `/health/cancel`, `/health/results` — health check execution

## Fix

Change the guard to only protect the exact **page** routes, not the API sub-routes:

```python
# Before:
if request.path.startswith(("/advanced-ops", "/health", "/config")):

# After:
if request.path in ("/advanced-ops", "/health", "/config"):
```

This means:

- `/advanced-ops` (the page) still requires dev mode
- `/advanced-ops/workflows`, `/advanced-ops/oneshot/start`, etc. are accessible from the Reporter page
- `/health` (the page) still requires dev mode
- `/health/run`, `/health/status`, etc. are accessible from the Reporter page
- `/config` (the page) still requires dev mode

The API endpoints themselves are safe to expose because they require valid cluster credentials to perform any action.
