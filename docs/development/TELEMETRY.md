# Usage Telemetry — Spec & Receiver Contract (QP-3 Item 4)

Status: **Local-only** in the current release. Nothing is transmitted anywhere.
This document specifies the event schema, privacy guarantees, and the future
central-receiver contract so the existing local events become the payload when
(and only when) a receiver is stood up.

## Goals

- Give operators a **local** "return on investment" surface (time saved by the
  tool) without sending anything off-box.
- Keep the door open for **opt-in**, anonymous, aggregate usage reporting to a
  central endpoint later — with zero schema churn for installs that already
  recorded events locally.

## Privacy guarantees (enforced in `src/usage_metrics.py`)

1. **Opt-in.** Recording is OFF by default. Events are only written after the
   operator opts in via the dashboard toggle (`POST /api/telemetry/consent`),
   persisted to `<data_dir>/telemetry/telemetry.json`.
2. **Anonymous.** The only identity stored is a random `install_id`
   (`uuid4().hex`), generated locally on first run. No hostname, username,
   cluster IP/name/PSNT, or credential is ever recorded.
3. **Allowlisted properties.** Event `properties` are filtered through a strict
   allowlist (`_ALLOWED_PROPS`). Any key not on the list is dropped before the
   event is written, so identifying fields cannot leak even if a caller passes
   them by mistake.
4. **Local-only transport.** `roi_summary()["transmitted"]` is always `False`
   in this release. No network egress exists in `usage_metrics.py`.

## Storage layout

```
<data_dir>/telemetry/
  telemetry.json   # consent state: {install_id, enabled, created, consent_at}
  usage.jsonl      # append-only event log, one JSON object per line
```

## Event schema (one JSON object per line in `usage.jsonl`)

```json
{
  "ts": "2026-06-16T18:41:16.123456+00:00",
  "install_id": "9f3c…",
  "app_version": "1.5.8-beta",
  "event": "report_generated",
  "properties": { "operation": "report", "success": true }
}
```

| Field         | Type   | Notes                                                            |
| ------------- | ------ | ---------------------------------------------------------------- |
| `ts`          | string | ISO-8601 UTC timestamp.                                          |
| `install_id`  | string | Anonymous random id; stable per install.                        |
| `app_version` | string | `APP_VERSION` at record time.                                   |
| `event`       | string | One of the event names below.                                   |
| `properties`  | object | Allowlisted keys only (see below).                              |

### Event names

| Event              | Recorded when                          | ROI minutes/event |
| ------------------ | -------------------------------------- | ----------------- |
| `report_generated` | An As-Built report completes.          | 45                |
| `health_check`     | A health check completes.              | 20                |
| `oneshot_run`      | A one-shot run completes.              | 30                |
| `vnetmap_run`      | A vnetmap topology run completes.      | 15                |
| `switch_config`    | A switch config capture completes.     | 15                |
| `support_bundle`   | A support/log bundle completes.        | 20                |

ROI minutes are coarse, conservative "vs. doing it by hand" estimates used
**only** for the local surface; they are not part of the wire contract.

### Allowlisted `properties` keys (`_ALLOWED_PROPS`)

`operation`, `duration_seconds`, `sections`, `success`, `tier_count`,
`tool_count`. Anything else is silently dropped.

## Local ROI surface

`GET /api/telemetry/status` returns `UsageMetrics.roi_summary()`:

```json
{
  "enabled": true,
  "install_id": "9f3c…",
  "total_events": 12,
  "counts": { "report_generated": 5, "health_check": 7 },
  "estimated_minutes_saved": 365,
  "estimated_hours_saved": 6.1,
  "first_event": "…",
  "last_event": "…",
  "transmitted": false
}
```

The dashboard "Usage & Privacy" card renders this and exposes the opt-in toggle.

## Future central-receiver contract (NOT yet implemented)

When a receiver is added, transmission MUST remain opt-in and MUST reuse the
event schema above verbatim (so already-recorded local events upload without
transformation). Proposed contract:

- **Transport:** HTTPS `POST` to a configurable endpoint
  (`updates`/`telemetry` config, e.g. `telemetry.endpoint`). TLS verification on
  by default.
- **Batching:** Upload an array of unsent event objects:
  `{ "schema_version": 1, "events": [ {…}, … ] }`. Track a high-water mark
  locally so events are sent at-most-once.
- **Auth:** Optional bearer token from config/env; never logged.
- **Response:** `200` with `{ "accepted": <n> }`; on non-2xx, keep events
  locally and retry later with backoff.
- **Receiver privacy:** The receiver MUST treat `install_id` as opaque and MUST
  NOT attempt re-identification. Reject payloads containing any non-allowlisted
  property key.
- **Flip the flag:** Once transmission ships, `roi_summary()["transmitted"]`
  reflects real upload state.

Until that endpoint exists, do not add network egress to `usage_metrics.py`.
