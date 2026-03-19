# TODO & Roadmap — Planned Features and Enhancements

**Purpose:** Canonical list for next steps, planned work, and release-related items. Kept in sync with development and validated in CI.

**Last updated:** 2026-03-19  
**Reference:** [PRE-RELEASE-QA-GAP-ANALYSIS.md](PRE-RELEASE-QA-GAP-ANALYSIS.md) (feature coverage and recommendations)

---

## Status key

| Status   | Meaning |
|----------|--------|
| Planned  | Not started; agreed as next or future work |
| In progress | Actively being worked on |
| Done     | Completed (move to CHANGELOG / release notes and clear or archive here) |
| Deferred | Postponed; reason and target release noted |

---

## Planned — Test suite enhancements (pre-release QA)

*Source: PRE-RELEASE-QA-GAP-ANALYSIS.md §6.3*

| ID   | Item | Priority | Status   | Notes |
|------|------|----------|---------|--------|
| TSE-1 | **Library:** Unit tests for GET `/library`, GET/POST/DELETE `/api/library`, mocked _load_library/_save_library | High | Planned | test_app.py |
| TSE-2 | **Generate cancel:** Unit test POST `/generate/cancel` (no job → 200/409; job running → cancel accepted, mock state) | High | Planned | test_app.py |
| TSE-3 | **Reports dirs:** Unit tests GET `/reports/dirs`, POST with valid path (output-dir behavior) | High | Planned | test_app.py |
| TSE-4 | **API discover:** Unit test POST `/api/discover` with mocked create_vast_api_handler + RackDiagram (400/401/success) | Medium | Planned | test_app.py |
| TSE-5 | **Report content:** Integration test — EBox + dell_turin_cbox + serial in data; assert PDF/intermediate contains expected strings | Medium | Planned | test_integration.py |
| TSE-6 | **Profiles API:** Unit tests GET/POST/DELETE `/profiles` and `/profiles/<name>` (mock _load_profiles/_save_profiles) | Medium | Planned | test_app.py |
| TSE-7 | **Shutdown:** Optional unit test POST `/shutdown` (200, no crash) or document as manual check | Lower | Planned | test_app.py or manual |
| TSE-8 | **Coverage:** Add tests for external_port_mapper, rack_diagram, report_builder (EBox path, partial port mapping) toward 80% | Lower | Planned | per-module |

---

## Planned — Quality gates and pre-release checklist

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| QG-1 | Run flake8 + black (and optionally mypy) as part of documented pre-release run | Planned | See PRE-RELEASE-QA-GAP-ANALYSIS.md §5 |
| QG-2 | Fix or document flake8/black/mypy exceptions to achieve green quality gate | Planned | Pre-existing issues |
| QG-3 | Raise coverage toward 80% or formally set cov-fail-under with restoration plan | Planned | Track with TSE-8 |

---

## Planned — Developer mode (hidden/secure)

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| DEV-1 | **Developer button:** Add a hidden/secure Developer control at the top of the UI, enableable by developers at launch (e.g. env flag or launch option). When enabled, expose: (1) **Configuration** — move existing Configuration section under Developer; (2) **Docs** — move Docs access under Developer; (3) **Live API Explorer** — expose API Explorer interface under Developer; (4) **Report from JSON** — new UI to generate reports directly from previously generated `.json` output files (e.g. `vast_data_*.json`) without reconnecting to the cluster. | Planned | Navbar/top-level; secure so only enabled at launch |

---

## Planned — Support bundle workflow (offline / no direct cluster access)

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| SB-1 | **Support bundle–based report generation:** New function for clusters that cannot be directly accessed. Workflow: (1) Generate a support bundle for the cluster (customer/ops generates bundle); (2) Upload support bundle content into the app; (3) Analyze support bundle file content; (4) Generate `.json` file from bundle content (same schema as live-generated `vast_data_*.json`); (5) Generate report from the generated `.json` file (reuse existing report-from-data path). End-to-end: support bundle → JSON → PDF report without live API access. | Planned | New upload/analyze pipeline; document bundle format and required files |

---

## Planned — Requests for Enhancement (from Confluence)

*Source: [VAST As-Built Report Generator - v1.3.0](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/6664028496/VAST+As-Built+Report+Generator+-+v1.3.0) — Requests for Enhancement table.*

| ID    | Item | Status   | Notes |
|-------|------|----------|--------|
| RFE-1 | Support Bundle Integration | Planned | |
| RFE-2 | Jeff's Port Mapper Integration | Planned | |
| RFE-3 | Render Logical Net Diagram only with Port Map option enabled | Planned | |
| RFE-4 | Health Report Summary | Done | Health Check module, PDF sections |
| RFE-5 | Integrate/Automate Post Deployment Tests | Done | Health Check module, tiered checks |
| RFE-6 | Container deployment option | Planned | |
| RFE-7 | Update deployment procedures | Planned | |
| RFE-8 | Package as Mac.app / Win.msi | Planned | |
| RFE-9 | Add recommended next steps | Planned | |
| RFE-10 | Add Alert Summary | Planned | |
| RFE-11 | Create .json export database | Planned | |
| RFE-12 | Fix DC/DBox Rack naming | Planned | |
| RFE-13 | Fix Rack API Call | Planned | |
| RFE-14 | Check capacity calculations | Planned | |

---

## In progress

*(Move items here when work starts; move to Done when complete.)*

*None.*

---

## Done

*(Items completed this release cycle; archive or clear periodically.)*

| ID    | Item | Notes |
|-------|------|-------|
| RFE-4 | Health Report Summary | Health Check module, PDF sections |
| RFE-5 | Integrate/Automate Post Deployment Tests | Health Check module, tiered checks |

---

## Next steps (current focus)

1. Prioritize TSE-1–TSE-3 for “all features validated” before next release.
2. Before each release: update this file (status, Last updated, move completed items to Done).
3. CI validates this file exists and contains required sections (see todo-tracking rule and CI job).

---

## RFE and other tracking

- **RFE:** Requests for Enhancement from Confluence (page 6664028496) are tracked as GitHub issues or referenced here when work begins.
- **Session-level work:** Use Cursor TODO tracking during sessions; promote agreed next steps to this roadmap.
