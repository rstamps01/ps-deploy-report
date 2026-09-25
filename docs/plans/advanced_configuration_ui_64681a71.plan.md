---
name: Advanced Configuration UI
overview: Create a form-based Advanced Configuration page that exposes all `config/config.yaml` settings with dropdowns, toggles, checkboxes, and grouped sections, plus a Report Tuning Tool for live-previewing report formatting changes by regenerating PDFs from existing JSON data. The raw YAML editor stays accessible in Developer mode only.
todos:
  - id: backend-config-routes
    content: Add /config/json (GET/POST), /config/template/json (GET), /config/advanced (GET) routes in app.py
    status: completed
  - id: backend-tune-routes
    content: "Add /config/advanced/tune-report (POST) route: accepts JSON source path + config overrides, regenerates PDF via ReportConfig + report_builder, returns download link. Add /config/advanced/json-files (GET) to list available JSON files from output dirs."
    status: completed
  - id: nav-update
    content: "Update base.html nav: add 'Configuration' link in hamburger menu visible to all; move raw YAML editor to Developer section as 'Config (YAML)'"
    status: completed
  - id: template-create
    content: "Create advanced_config.html: grouped config form sections (9 sections with toggles, dropdowns, info icons), Report Tuning Tool panel in Report section, Save/Cancel/Reset buttons"
    status: completed
  - id: css-additions
    content: Add CSS for config section headers, config form grid, info-icon tooltip, and report tuning panel styles
    status: completed
  - id: developer-guard
    content: Update app.py developer mode guard to include /config route behind developer_mode
    status: completed
  - id: lint-test
    content: Run linter and tests to verify no regressions
    status: completed
isProject: false
---

# Advanced Configuration UI + Report Tuning Tool

## Decisions

- **Layout: Option B — Sticky Top Toolbar**: The Report Tuning Tool is a compact horizontal bar pinned (`position: sticky`) below the navbar. Config sections get full page width as collapsible accordion cards below. The toolbar stays visible as the user scrolls through settings, enabling one-click regeneration after any config change.
- **Navigation**: Add "Configuration" link in the hamburger menu (visible to all users). Move the existing raw YAML editor link to the **Developer** section (visible only when `developer_mode` is true), renamed to "Config (YAML)".
- **Bidirectional sync**: The new page reads from and writes to `config/config.yaml` via new JSON API endpoints. Any save from the form UI updates the YAML file; any save from the raw editor is reflected when the form page reloads.
- **Reset Template**: Loads values from `config/config.yaml.template` into the form without saving. User must explicitly click Save.
- **Report Tuning Tool**: Sticky toolbar at top of page. Allows selecting an existing JSON file and regenerating the PDF with the current (or modified) report formatting settings. May be promoted to its own page later.

## Config Sections & Controls

Derived from `config/config.yaml.template` — 9 grouped sections:

- **API** — timeout (number), max_retries (number), retry_delay (number), verify_ssl (toggle), version (dropdown: v3–v7)
- **Logging** — level (dropdown: DEBUG/INFO/WARNING/ERROR/CRITICAL), format (text), file_path (text), rotation_size (number), backup_count (number), ops_log_dir (text), ops_log_max_bytes (number), ops_log_purge_fraction (number), console_colors (5 dropdowns)
- **Report** — organization (text), page_size (dropdown: A4/Letter), margins (4 numbers), include_toc (toggle), include_page_numbers (toggle), font_family (dropdown), font_size (number); **includes Report Tuning Tool panel** (see below)
- **Output** — default_directory (text), pdf_filename (text), json_filename (text), timestamp_format (text)
- **Data Collection** — 11 section toggles, concurrent_requests (number), validate_responses (toggle), graceful_degradation (toggle)
- **SSH** — proxy_jump (toggle), timeout (number), ping_timeout (number)
- **Health Check** — include_in_report (toggle), tiers: api/node_ssh/switch_ssh (3 toggles)
- **Advanced Operations** — default_mode (dropdown), default_switch_placement (dropdown), autofill_default_passwords (toggle), vperfsanity_default_selected (toggle)
- **Security** — prompt_for_credentials (toggle), session_timeout (number), sanitize_logs (toggle), mask_sensitive_data (toggle)

Each field gets an `info-icon` (`ℹ`) with a `title` tooltip describing the setting (pulled from the YAML comments).

## Report Tuning Tool (Sticky Top Toolbar)

A compact horizontal toolbar pinned below the navbar (`position: sticky; top: 60px; z-index: 90`). Single row layout:

```
[ Report Tuning Tool ]  [ Select JSON File ▼ ]  [ Browse... ]  [ Regenerate PDF ]  Status: Ready
```

- **JSON Source Selection** (inline in toolbar):
  - **Dropdown**: Populated by `GET /config/advanced/json-files`, lists `vast_data_*.json` files from all known output directories (reuses `_list_reports()` logic, filtered to JSON only)
  - **Browse button**: File input (`<input type="file" accept=".json">`) for local JSON files
- **Regenerate PDF button**: Sends the selected JSON file path (or uploaded content) plus the **current form values** (not just saved config) to `POST /config/advanced/tune-report` — this lets users tweak Report Formatting fields and immediately test without saving first
- **Status area**: Inline text showing "Ready", "Generating...", or "Done — [Download PDF]" link
- **Backend flow**:
  1. Load the JSON data (from server path or uploaded content)
  2. Build a `ReportConfig` from the submitted form values (overriding the saved config)
  3. Call `create_report_builder(config=report_config)` then `generate_pdf_report(data, output_path)`
  4. Output file named `*_REGEN.pdf` in the same directory as the source JSON (or default output dir for uploads)
  5. Return `{"status": "ok", "pdf_path": "...", "pdf_name": "..."}` for download link
- **Existing code reused**: `ReportConfig.from_yaml()`, `create_report_builder()`, `generate_pdf_report()`, `_list_reports()`

## Backend Changes (`src/app.py`)

- **`GET /config/json`** — returns current config as JSON dict (calls `_load_yaml`)
- **`POST /config/json`** — accepts JSON body, validates, writes YAML to `config.yaml`
- **`GET /config/template/json`** — returns template defaults as JSON
- **`GET /config/advanced`** — renders `advanced_config.html`
- **`GET /config/advanced/json-files`** — returns list of available JSON report files from output dirs
- **`POST /config/advanced/tune-report`** — accepts `{json_path, report_overrides}`, regenerates PDF, returns result
- Move raw YAML editor route guard: show "Config (YAML)" only in Developer mode

## Frontend Changes

- **New template**: `frontend/templates/advanced_config.html` — extends `base.html`, uses existing CSS classes (`.card`, `.form-group`, `.toggle-switch`, `.info-icon`, etc.)
- **Sticky toolbar**: Compact horizontal bar at the top of the page (below navbar) with JSON file dropdown, Browse button, Regenerate PDF button, and inline status — stays pinned while scrolling through config sections
- **Navigation** (`base.html`): Add "Configuration" as a hamburger menu link; move current "Configuration" to Developer section as "Config (YAML)"
- **Buttons**: Save (POST /config/json), Cancel (reload from server), Reset Template (GET /config/template/json then populate form)

## Files Changed

- `src/app.py` — new routes + developer guard update + tune-report endpoint
- `frontend/templates/advanced_config.html` — new file
- `frontend/templates/base.html` — nav updates
- `frontend/static/css/app.css` — minor additions for section headers, info-icon reuse, tuning panel
