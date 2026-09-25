---
name: Confluence Update v1.5.0
overview: Overhaul the Confluence project page tree (parent page 6664028496 + key sub-pages) to reflect v1.5.0 capabilities, transform the parent into an internal landing page, update or archive stale sub-pages, and create new pages for features added since v1.3.0.
todos:
  - id: parent-page
    content: "Rewrite parent page (6664028496): rename title to v1.5.0, add quick access links, What's New, feature matrix, updated RFE table, strip verbose README content"
    status: completed
  - id: status-page
    content: "Rewrite Status page (5.0 / 6671401030): current release, test status, CI/CD, release history, upcoming work"
    status: completed
  - id: install-page
    content: "Rewrite Installation page (8.0 / 6671401043): desktop app install, link to Quick Start Guide, from-source fallback"
    status: completed
  - id: webui-page
    content: "Create new page 15.0 - Web UI and Reporter: Flask app overview, Reporter workflow, navigation, Advanced Ops, One-Shot"
    status: completed
  - id: health-page
    content: "Create new page 16.0 - Health Check Module: 32 checks, tiers, correlation engine, remediation report"
    status: completed
  - id: roadmap-page
    content: "Create new page 17.0 - Roadmap and Planned Work: mirror TODO-ROADMAP.md"
    status: completed
  - id: archive-banners
    content: Add historical-document banner to 10+ original design/planning sub-pages (1.0-4.0, 6.0-7.0, 10.0-13.0)
    status: completed
isProject: false
---

# Confluence Update Plan -- v1.5.0

## Gap Analysis

The Confluence page tree is frozen at **v1.3.0 / v1.1.0** (last updated Oct 2025). The product is now at **v1.5.0** (released 2026-04-04) with a web UI, desktop packaging, health checks, advanced ops, and a GitHub Pages marketing site. The delta is massive.

### Key Discrepancies

- **Title**: "v1.3.0" -- should be "v1.5.0"
- **Installation**: Python/pip/venv instructions -- product ships as `.dmg` / `.zip` (no Python required)
- **Architecture**: CLI-only tool described -- product is now a Flask web app with 11 pages (Dashboard, Reporter, Results, Library, Docs, Health, Advanced Ops, etc.)
- **Features**: No mention of Reporter page, Health Check (32 checks), One-Shot orchestration, SSH Proxy, vnetmap, VAST logo progress, GitHub Pages, or desktop packaging
- **RFE table**: Many items now complete but still shown as blank/pending
- **Status page (5.0)**: Says "READY FOR DEVELOPMENT IMPLEMENTATION" from Sep 2025
- **Installation page (8.0)**: Contains a manual `vi requirements.txt` workflow
- **Version references**: All doc links point to `v1.1.0` branch on GitHub

### Confluence Metadata

- **Cloud ID**: `56a82c73-952b-49bd-b893-8f41ed772d57`
- **Space ID**: `5023203330`
- **Parent page ID**: `6664028496`

---

## Execution Plan

### Phase 1: Update the Parent Page (Landing Page Overhaul)

**Target**: Page `6664028496` -- rename to "VAST asbuilt-reporter -- v1.5.0"

Transform from a verbose README clone into a concise **internal landing page**:

1. **Header / Branding** -- title updated to "VAST asbuilt-reporter -- v1.5.0", tagline: "Generate professional as-built reports for VAST Data clusters in minutes -- no Python required."
2. **Quick Access Links** -- table with 4 links:

- [Product Overview](https://rstamps01.github.io/ps-deploy-report/se-one-pager.html) (GitHub Pages one-pager)
- [Quick Start Guide](https://rstamps01.github.io/ps-deploy-report/quick-start-guide.html) (macOS/Windows install with screenshots)
- [Download Latest Release](https://github.com/rstamps01/ps-deploy-report/releases/latest) (.dmg + .zip)
- [GitHub Repository](https://github.com/rstamps01/ps-deploy-report)

1. **What's New in v1.5.0** -- bullet summary sourced from `RELEASE_NOTES_v1.5.0.md` highlights (Reporter page, Health Check, SSH Proxy, One-Shot, VAST logo progress, GitHub Pages marketing site, etc.)
2. **Key Capabilities Table** -- 6-row feature matrix from README "Key features" table (Desktop app, Reporter, Report generation, Health check, Post-install validation, Reports, Reliability)
3. **RFE Table Update** -- mark completed items with status:

- Support Bundle Integration -- **Done** (result_bundler.py)
- Health Report Summary -- **Done** (health_checker.py, 32 checks)
- Integrate/Automate Post Deployment Tests -- **Done** (One-Shot mode, Reporter Test Suite)
- Package as Mac.app / Win.msi -- **Done** (.dmg + .zip, PyInstaller)
- Update deployment procedures -- **Done** (Quick Start Guide, GitHub Pages)
- Fix DC/DBox Rack naming -- **Done** (rack_diagram.py)
- Fix Rack API Call -- **Done** (api_handler.py)
- Other items: leave as-is or mark status as appropriate

1. **Project Resources Table** -- keep the 14 sub-page links (1.0--14.0) and add new entries for 15.0, 16.0, 17.0
2. **Footer** -- version: 1.5.0, last updated: 2026-04-04, status: Production

**Remove** the verbose README-style content currently below the RFE table (installation instructions, CLI usage, troubleshooting, project structure, development, etc.) -- that content is now served by the GitHub README and the Quick Start Guide.

### Phase 2: Update Status Page (5.0)

**Target**: Page `6671401030`

Rewrite from the Sep 2025 "Ready for Development" content to reflect production status:

- **Current version**: v1.5.0 (released 2026-04-04)
- **Release history summary**: v1.0.0 through v1.5.0 with key milestone dates
- **Test status**: 876 tests passing, 62% coverage, CI/CD with GitHub Actions
- **Infrastructure**: CI pipeline (lint, format, type check, 5 test layers, cross-platform build smoke), GitHub Pages auto-deploy
- **Upcoming work**: Pull from `docs/TODO-ROADMAP.md` -- TSE-9 (coverage toward 80%), AUTH-1 (token automation), AO-15/AO-19 (Advanced Ops hardening), container deployment option
- **Known limitations**: Coverage target 60% (roadmap 75%+), no signed code certificate yet

### Phase 3: Update Installation Page (8.0)

**Target**: Page `6671401043`

Replace the manual Python/pip/vi workflow with the desktop app installation:

- **Desktop App (Recommended)** -- 3-step: Download .dmg/.zip, Install, Run
- Link to [Visual Quick Start Guide](https://rstamps01.github.io/ps-deploy-report/quick-start-guide.html) for screenshot walkthroughs
- **macOS notes**: Gatekeeper workaround (Privacy and Security > Open Anyway)
- **Windows notes**: SmartScreen bypass (More info > Run anyway)
- **From Source (Developers)** -- brief: `git clone`, `python3 -m venv`, `pip install -r requirements.txt`, `python3 src/main.py`
- **Requirements**: macOS 11+ or Windows 10+, 512 MB RAM, HTTPS access to VMS, VAST credentials with read access

### Phase 4: Create New Sub-Pages

#### 15.0 - Web UI and Reporter

New page under parent `6664028496`:

- **Web UI Overview**: Flask app at localhost:5173, 11 pages (Dashboard, Reporter, Results, Library, Docs, Health, Generate, Reports, Advanced Ops, Config, Validation Results)
- **Reporter Workflow**: 3-step (Enter IP, Discovery, Run) with optional vnetmap, health check, pre-validation
- **Navigation Structure**: Standard nav vs. hamburger menu vs. Developer Mode pages
- **Advanced Operations** (Developer Mode): Step-by-step workflows (vnetmap, support tool, vperfsanity, log bundle, switch config, network config)
- **One-Shot Mode**: Sequential multi-operation execution with auto-bundling

#### 16.0 - Health Check Module

New page under parent `6664028496`:

- **Overview**: Tier 1 (27 API checks) + Tier 3 (6 per-switch SSH checks) = 32+ total checks
- **Check categories**: Cluster, Licensing, Call Home, Hardware, Network, Storage, Security, Performance
- **Correlation engine**: Cross-check findings that amplify severity
- **Remediation report**: Auto-generated with severity levels and actionable guidance
- **Integration**: Optional in Reporter workflow, standalone on Health page, CLI via `--health-check`

#### 17.0 - Roadmap and Planned Work

New page under parent `6664028496`:

- Mirror content from `docs/TODO-ROADMAP.md`
- Active items: TSE-9 (coverage), AUTH-1 (token automation), container deployment
- Completed items summary
- Links to GitHub Issues for tracking

### Phase 5: Archive Marker on Historical Pages

For sub-pages that are historical design/planning documents (1.0 Concept, 2.0 PRD, 3.0 Project Plan, 4.0 Tasks, 6.0 Design, 7.0 AI Guardrails and children, 10.0-13.0 technical analysis):

- Add a short banner at the top of each: "**Historical Document** -- This page reflects the original v1.0 design phase (Sep 2025). For current product documentation, see the [parent page](link)."
- Do NOT delete or restructure these pages -- they serve as project history

---

## Content Sources

All content will be sourced from the codebase (no fabrication):

- **README.md** -- feature matrix, requirements, quick start
- **RELEASE_NOTES_v1.5.0.md** -- v1.5.0 highlights and feature list
- **CHANGELOG.md** -- release history
- **docs/TODO-ROADMAP.md** -- roadmap and planned work
- **docs/marketing/se-one-pager.html** -- product overview (linked, not duplicated)
- **docs/marketing/quick-start-guide.html** -- installation guide (linked, not duplicated)

## Execution Order

Pages will be updated/created in this order to avoid broken links:

1. Create new pages (15.0, 16.0, 17.0) as drafts first
2. Update parent page with new links and content
3. Update Status page (5.0)
4. Update Installation page (8.0)
5. Publish new pages
6. Add archive banners to historical pages (batch)
