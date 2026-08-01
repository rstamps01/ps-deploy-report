# Pipeline Metrics

DORA-style delivery metrics + quality trend for the agentic CI/CD pipeline (pipeline §20). Refreshed by the `project-manager` (`PM: metrics`) each release from git history, CI runs (`gh run list`), the tracker, and the `remediate-failure` logs in `docs/DECISIONS.md`.

## How each metric is sourced

| Metric | Definition | Source |
| --- | --- | --- |
| **Lead time for change** | Median time from first commit on a branch to its release tag | `git log` (branch → tag) |
| **Deployment frequency** | Releases per month (tags `vX.Y.Z`) | `git tag --sort=creatordate` |
| **Change-failure rate** | % of releases needing a hotfix/rollback | `docs/DECISIONS.md` + hotfix tags |
| **MTTR** | Median time from a failed gate to green resolution | `remediate-failure` entries in `docs/DECISIONS.md` |
| **Coverage trend** | `--cov` line-coverage % per release | CI coverage artifact / `pyproject.toml` floor |
| **Test pass rate** | passing / total on the blocking gate | CI run summaries |
| **Escalation count** | Escalations sent (email/Slack) per period | `docs/DECISIONS.md` memlog |
| **Backlog velocity** | Items opened vs closed (`done`) per period | `docs/TODO-ROADMAP.md` state machine |

## Current snapshot

> Baseline established during the pipeline build (M0–M4). Populated automatically going forward; this first row is the reference point.

| Period | Releases | Lead time (median) | Change-failure rate | MTTR | Coverage floor | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-07 (baseline) | v1.5.8 shipped; v1.6.0 segmented on `develop` | — (pre-instrumentation) | — | — | 60% | Pipeline M0–M4 built; metrics instrumentation begins next release. |

## Targets (ratchet)

- Coverage floor: 60% → 75%+ (TSE items in `docs/TODO-ROADMAP.md`), upward-only.
- Change-failure rate: keep low via blocking release gates (§5) + post-release smoke test → rollback/hotfix (§18).
- MTTR: bounded by the 3-attempt `remediate-failure` loop before human escalation (§16).
