---
name: Dashboard Quick Start Revamp
overview: Redesign the Dashboard page from 3 generic cards into an intuitive Quick Start launch pad with a dynamic status panel and clickable step-by-step workflow cards that guide users from cluster connection through report/bundle generation.
todos:
  - id: backend-status-api
    content: Add GET /api/dashboard/status endpoint in src/app.py returning job state, last report, tool status, profile count
    status: completed
  - id: css-dashboard
    content: Add status-bar, status-tile, workflow-steps, and step-card CSS classes to app.css
    status: completed
  - id: template-rewrite
    content: Rewrite dashboard.html with status bar (4 tiles) and workflow steps (5 clickable cards)
    status: completed
  - id: js-status-polling
    content: Add inline JS in dashboard.html to fetch status on load and poll every 15s
    status: completed
  - id: verify-quality
    content: Run flake8, black, mypy, pytest to verify no regressions; update CHANGELOG
    status: completed
isProject: false
---

# Dashboard Quick Start Revamp

## Current State

The current Dashboard ([frontend/templates/dashboard.html](frontend/templates/dashboard.html)) is a minimal 66-line template with three generic cards (Generate Report, Browse Reports, Configuration) and a Recent Reports table. It provides no workflow guidance, no status visibility, and links to legacy pages rather than the primary Reporter workflow.

## Architecture

### Backend: New Status API Endpoint

Add a lightweight `GET /api/dashboard/status` endpoint in [src/app.py](src/app.py) that aggregates:

- **Active Jobs** -- check `app.config["JOB_RUNNING"]` and `app.config["HEALTH_JOB_RUNNING"]`
- **Last Report** -- use `_list_reports()` to get the most recent file name and timestamp
- **Tool Status** -- instantiate `ToolManager.get_all_tools_info()` and summarize cached/total
- **Saved Profiles** -- count profiles from `_load_profiles()`
- **Total Reports** -- count from `_list_reports()`

Returns a single JSON dict. The Dashboard JS will `fetch()` this on page load and populate the status widgets.

### Frontend: Template Rewrite

Replace the entire `dashboard.html` content with three sections:

```
+--------------------------------------------------+
|  Page Header: "Quick Start"                      |
|  Subtitle: "Your launch pad for cluster testing" |
+--------------------------------------------------+
|  Status Bar (4 compact indicator tiles)          |
|  [Job Status] [Last Report] [Tools] [Profiles]  |
+--------------------------------------------------+
|  Workflow Steps (numbered clickable cards)        |
|  [1. Prerequisites] [2. Connect] [3. Configure]  |
|  [4. Run]           [5. Results]                  |
+--------------------------------------------------+
```

### Section 1: Status Bar

Four compact tiles in a horizontal grid, each with an icon, label, and dynamic value:

- **Job Status** -- "Idle" / "Report Running" / "Health Check Running" (green/amber dot)
- **Last Report** -- filename + relative timestamp, or "No reports yet"
- **Tools** -- "3/3 Cached" or "Not Downloaded" with link to Reporter (Update Tools)
- **Saved Profiles** -- count, with link to Reporter connection settings

Values populated via `fetch('/api/dashboard/status')` on page load; a `setInterval` polls every 15 seconds for job status changes.

### Section 2: Workflow Steps (5 Clickable Cards)

Each card contains: step number badge, SVG icon, title, 2-3 line description of what to do, and a "Go" button linking to the relevant page.

**Step 1 -- What You Need**

- Icon: clipboard/checklist
- Description: "Gather your cluster IP (or VMS address), VMS credentials (support user), node SSH password, and switch SSH credentials. Tech port connections use 192.168.2.2."
- Link: `/docs` (docs page, or could be an anchor to a "Prerequisites" section if we add one)

**Step 2 -- Connect to Cluster**

- Icon: plug/link
- Description: "Open the Reporter page, select or create a Cluster Profile, and enter your connection settings. Enable 'Autofill Default Passwords' for quick setup."
- Link: `/reporter`

**Step 3 -- Configure Switches**

- Icon: server/network
- Description: "Choose Auto or Manual switch placement. Run Discovery to find rack switches, then assign positions or add switches manually from the Library."
- Link: `/reporter` (with a hash anchor or query param to scroll to switch section, or just the page)

**Step 4 -- Run Reporter**

- Icon: play/rocket
- Description: "Select your operations -- Pre-Validation (recommended), Run Reporter (generates the as-built PDF), and optional Health Check. Press Run and monitor progress."
- Link: `/reporter`

**Step 5 -- Review Results**

- Icon: document/download
- Description: "View or download your PDF and JSON reports. Browse all past results on the Results page, or download complete bundles from One-Shot runs."
- Link: `/validation-results`

### CSS Additions

Add Dashboard-specific styles to [frontend/static/css/app.css](frontend/static/css/app.css):

- `.status-bar` -- horizontal flex/grid container for 4 status tiles
- `.status-tile` -- compact card variant with icon, label, value; subtle border
- `.status-dot` -- small colored circle indicator (green idle, amber running)
- `.workflow-steps` -- grid container (3-col on desktop, 1-col on mobile)
- `.step-card` -- numbered card with step badge, hover effect, and accent border on hover
- `.step-number` -- circular badge with the step number (accent background, white text)
- `.step-card:hover` -- subtle lift/shadow effect for interactivity feedback

All styles use existing CSS variables (`--bg-surface`, `--accent`, `--text-primary`, `--border`, `--shadow`, `--radius`) for design consistency.

### JavaScript

Add a small inline `<script>` block in `dashboard.html` (via `{% block scripts %}`) that:

1. Calls `fetch('/api/dashboard/status')` on `DOMContentLoaded`
2. Populates status tile values from the JSON response
3. Sets up a 15-second polling interval for job status refresh
4. Handles error states gracefully (shows "Unavailable" if the API fails)

No changes to [frontend/static/js/app.js](frontend/static/js/app.js) needed.

### Files Changed

| File                                                                   | Action                                                                              |
| ---------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| [src/app.py](src/app.py)                                               | Add `/api/dashboard/status` route; update `dashboard()` to remove `reports` context |
| [frontend/templates/dashboard.html](frontend/templates/dashboard.html) | Full rewrite with status bar + workflow steps                                       |
| [frontend/static/css/app.css](frontend/static/css/app.css)             | Add status-bar, status-tile, workflow-steps, step-card classes                      |

### Design Principles

- **Consistent with existing UI** -- uses the same `card`, `btn`, `page-header` patterns from Reporter and other pages
- **Responsive** -- cards reflow to single column on narrow widths via CSS grid `auto-fit`
- **Dark theme native** -- all colors from CSS variables, no hardcoded colors
- **Minimal JS** -- single fetch on load + lightweight polling; no framework dependencies
- **Graceful degradation** -- if status API fails, cards still render with static content; status shows "Unavailable"
