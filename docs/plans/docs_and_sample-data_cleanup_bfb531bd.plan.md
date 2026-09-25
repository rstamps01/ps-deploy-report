---
name: docs and sample-data cleanup
overview: Retire deprecated docs, stale sample reports, and committed generated artifacts (import/logs) ahead of v1.5.8, keeping everything wired into the app, tests, and rules intact. All removals are recoverable via the pre-1.5.8-cleanup tag.
todos:
  - id: docs-import-rm
    content: git rm --cached the two tracked import/*.pdf debugging artifacts (import/ already gitignored)
    status: completed
  - id: docs-logs-rm
    content: Untrack logs/api_responses/, logs/api_field_discovery.json, logs/vast_report_generator.log.1; keep .gitkeep + script; extend .gitignore
    status: completed
  - id: docs-reports-rm
    content: git rm reports/latest-reports/ and reports/version_1.1/; KEEP reports/MVP/ fixture; fix stale reports/README.md references
    status: completed
  - id: docs-retire
    content: "Retire historical docs: docs/api/CLUSTER_10.143.11.202..., 15 docs/development one-off notes, docs/issues SR-3/4/5 + TP-1 (incl live-cluster data); re-grep each before rm"
    status: completed
  - id: docs-root-tidy
    content: Reconcile Reporter.command vs Start Reporter.command launcher duplication
    status: completed
  - id: docs-verify
    content: "Verify: in-app Docs registry intact, grep removed paths, run flake8/black + test_main_from_json (MVP fixture) + unit suite + fresh-checkout sim"
    status: completed
isProject: false
---

# Docs and Sample-Data Cleanup (v1.5.8 pre-release)

Extends the existing `pre-release cleanup` plan. Phase 0 recovery tag (`pre-1.5.8-cleanup`) must exist before any `git rm`. All deletions are recoverable from that tag; this is a documented cleanup commit (industry best practice), not a local-archive move.

## Guardrails (do NOT remove)

- In-app Docs viewer registry `_DOC_REGISTRY` in [src/app.py](src/app.py) (lines 100-153): keep `docs/deployment/{INSTALLATION,PERMISSIONS,PORT-MAPPING,UPDATE,DEPLOYMENT,UNINSTALL}-GUIDE.md`, `docs/ADVANCED-OPERATIONS.md`, `docs/POST-INSTALL-VALIDATION.md`, `docs/API-REFERENCE.md`, `docs/api/EBOX_API_V7_DISCOVERY.md`.
- Code/test/rule-referenced docs: `docs/development/READ_ONLY_VAST_API_POLICY.md`, `docs/development/TELEMETRY.md`, `docs/development/HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md`, `docs/issues/NET-2/*`, `docs/issues/SR-1/01-summary.md`.
- Test fixture: `reports/MVP/**` (used by [tests/test_main_from_json.py](tests/test_main_from_json.py) and [src/main.py](src/main.py):1030). KEEP.
- Already gitignored, untouched: `docs/confluence/`, `docs/superpowers/`, `docs/JeffsPortMapperReview/`.

## A. import/ (verified not needed)

- `git rm --cached import/latest-report-missing-sections.pdf import/previous-report-includes-all-sections.pdf` (also delete from disk). `import/` is already in `.gitignore`.

## B. logs/ generated artifacts (verified regenerable)

- `git rm --cached -r logs/api_responses/` and `git rm --cached logs/api_field_discovery.json logs/vast_report_generator.log.1`.
- Keep `logs/.gitkeep` and `scripts/discover_api_fields.py` (regenerates these).
- Ensure `.gitignore` covers `logs/api_responses/`, `logs/api_field_discovery.json`, and `logs/*.log.[0-9]*` (rotated logs).

## C. reports/ stale samples

- `git rm -r reports/latest-reports/ reports/version_1.1/` (Oct-2025 / down-rev, no references).
- KEEP `reports/MVP/**`. Update [reports/README.md](reports/README.md) to drop stale `.archive/development_reports/` and `current_version/` references and reflect the surviving structure.

## D. docs/ retirements (retire-all, per decision)

- `docs/api/CLUSTER_10.143.11.202_API_DISCOVERY.md` (cluster-specific dump, unreferenced).
- `docs/development/`: `MYPY_FIX_SUGGESTIONS.md`, `RCA_ANALYSIS_SUMMARY.md`, `RCA_<customer-cluster>_DBox_Unresponsive_Issue.md`, `RCA_Slack_Thread_Analysis_Template.md`, `ONYX_INTERACTIVE_SSH_IMPLEMENTATION.md`, `ONYX_SUPPORT_SUMMARY.md`, `PORT_MAPPING_ANALYSIS.md`, `PORT_MAPPING_ISSUE_ANALYSIS.md`, `MULTI_RACK_FINDINGS_10.143.11.204.md`, `MULTI_RACK_IDENTIFICATION_ANALYSIS.md`, `MULTI_RACK_QUICK_START.md`, `API_DISCOVERY_MULTI_RACK.md`, `DYNAMIC-TOC-IMPLEMENTATION.md`, `TOC-IMPLEMENTATION-GUIDE.md`, `EBOX-HARDWARE-TABLE-IMPLEMENTATION-PLAN.md`.
- `docs/issues/`: `SR-3/`, `SR-4/`, `SR-5/`, `TP-1/` (the latter also removes live-cluster network data `mammoth_ip_addr_live_2026-04-29.txt` from the tracked repo).
- Before each `git rm`: re-grep the path across tracked files; any surviving reference (e.g. a roadmap/release-note link) is left as historical text (the file's content lives in git history + the tag), no live link breaks since these are not in `_DOC_REGISTRY`.

## E. Root tidy (light)

- Reconcile launcher duplication: tracked `Start Reporter.command` vs on-disk `Reporter.command` — keep one (prefer the tracked `Start Reporter.command`).
- No tracked root log/coverage/.DS_Store files remain (handled by existing cleanup plan's stray-artifacts task); on-disk `app.log`, `web_app.log`, `coverage.xml`, `.coverage` are untracked — optional local delete only.

## F. Verify

- `git grep` the removed paths return nothing live-breaking; in-app Docs page still lists all registry entries.
- Run quality gate: `flake8 src/ tests/`, `black --check --line-length 120 src/ tests/`, and `pytest tests/test_main_from_json.py -v` (proves `reports/MVP/` fixture intact) plus the broader unit suite.
- Fresh-checkout simulation to confirm nothing app-critical was removed.
