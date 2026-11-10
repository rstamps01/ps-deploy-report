# Web UI routes and config keys (`src/app.py`)

Reference list moved out of the always-loaded architecture rule. Update it in the same change that adds, renames, or removes a route.

- Page routes: Dashboard (/), Generate (/generate), Reports (/reports), Config (/config), Library (/library), Health Check (/health), Advanced Operations (/advanced-ops, Developer Mode only), Validation Results (/validation-results, Developer Mode only)
- API endpoints: /api/discover, /api/browse, /profiles, /stream/logs
- Job control: /generate/start (POST), /generate/status (GET), /generate/cancel (POST)
- Health check control: /health/run (POST), /health/status (GET), /health/cancel (POST), /health/results (GET)
- Library endpoints: /library/devices (GET/POST), /library/devices/<key> (DELETE), /library/images/<filename> (GET)
- Advanced Ops control: /advanced-ops/workflows (GET), /advanced-ops/start (POST), /advanced-ops/run-step (POST), /advanced-ops/run-all (POST), /advanced-ops/status (GET), /advanced-ops/cancel (POST), /advanced-ops/reset (POST), /advanced-ops/output (GET)
- Advanced Ops tools: /advanced-ops/tools (GET), /advanced-ops/tools/update (POST), /advanced-ops/tools/deploy (POST)
- Advanced Ops bundling: /advanced-ops/bundle/collect (POST), /advanced-ops/bundle/create (POST), /advanced-ops/bundle/download/<path> (GET), /advanced-ops/bundles (GET)
- Advanced Ops one-shot: /advanced-ops/oneshot/validate (POST), /advanced-ops/oneshot/start (POST), /advanced-ops/oneshot/status (GET), /advanced-ops/oneshot/cancel (POST)
- Validation Results: /validation-results (GET), /validation-results/api/results (GET), /validation-results/api/clusters (GET), /validation-results/api/file/<operation>/<filename> (GET/DELETE)
- Application control: /shutdown (POST) — graceful server termination via stored werkzeug server reference
- Config keys: DEFAULT_OUTPUT_DIR, OUTPUT_DIRS, CONFIG_PATH, PROFILES_PATH, DEVELOPER_MODE, JOB_RUNNING, JOB_RESULT, JOB_LOCK, JOB_CANCEL, HEALTH_JOB_RUNNING, HEALTH_JOB_RESULT, HEALTH_JOB_LOCK, HEALTH_JOB_CANCEL, ONESHOT_RUNNING, ONESHOT_RESULT, ONESHOT_LOCK, ONESHOT_CANCEL, _SERVER
