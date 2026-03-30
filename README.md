# VAST As-Built Report Generator

Generate professional as-built reports for VAST Data clusters in minutes—no Python required. Download the app, connect to your cluster, and get a customer-ready PDF plus machine-readable JSON.

---

## Table of contents

- [Quick start](#quick-start)
- [Key features](#key-features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Output files](#output-files)
- [Health check](#health-check)
- [Reporter and post-install validation](#reporter-and-post-install-validation)
- [Building from source](#building-from-source)
- [Project structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Security](#security)
- [Support](#support)

---

## Quick start

**Desktop (recommended)** — three steps:

1. **Download** the [macOS .dmg](https://github.com/rstamps01/ps-deploy-report/releases/latest) or [Windows .zip](https://github.com/rstamps01/ps-deploy-report/releases/latest).
2. **Install** — drag **VAST Reporter** to Applications (macOS) or extract and run `vast-reporter.exe` (Windows).
3. **Run** — open the app; the web UI opens in your browser at `http://127.0.0.1:5173`. Enter your cluster IP and credentials, then click **Generate**.

No Python, pip, or virtual environment needed. Updates: download the latest release and replace the existing app.

---

## Key features

| Area | Features |
|------|----------|
| **Desktop app** | Single .dmg/.zip install, browser-based UI at localhost:5173, live progress via SSE, cancel anytime, cluster profiles (shared across pages), report browser, config editor, hardware device library, in-app documentation viewer, full CLI via `--cli` |
| **Reporter** | Unified workflow: switch placement (auto/manual), as-built report generation, optional pre-validation and health checks, VAST logo progress indicator with stopwatch timer, result bundling — all from a single page |
| **Report generation** | VAST REST API v7 (v1 fallback), rack U positioning, auto/manual switch placement, PSNT tracking, optional SSH-based port mapping and IPL detection, SSH proxy hop through CNode for field deployments, EBox cluster support |
| **Health check** | Tier 1 (26 API checks) and Tier 3 (6 switch SSH checks) — 32 total checks; correlation engine; auto-generated remediation report with severity levels and actionable guidance |
| **Post-install validation** | One-Shot mode runs selected operations sequentially with operation badges, pre-validation, auto-bundling; Developer-mode Advanced Ops for step-by-step execution |
| **Reports** | PDF (VAST-branded) + JSON; executive summary, hardware inventory, physical rack layout, network topology, security, optional health check results and post-deployment validation |
| **Reliability** | Secure auth (args, env, or prompt), fault tolerance with graceful degradation, sanitized logging, retries with backoff, read-only API policy (GET only) |

### Report highlights

- **Physical rack layout** — 42U rack diagrams with CBox, DBox, EBox, and switch positions with hardware images.
- **Network topology** — Logical diagram with port mapping and IPL/MLAG links; EBox clusters show EB# labels with color-coded Network A/B connections.
- **Health check sections** — Cluster Health Check Results (summary + detailed table) and Post Deployment Validation when health check is enabled.
- **Dual output** — Customer-ready PDF and machine-readable JSON for automation.

---

## Requirements

| Context | Requirements |
|---------|--------------|
| **Desktop app** | macOS 11+ (Apple Silicon or Intel) or Windows 10+; 512 MB RAM (1 GB recommended); ~100 MB disk. No Python. |
| **From source** | Python 3.10+ (3.12 tested); see `requirements.txt` and optional `requirements-dev.txt`. |
| **Network** | HTTPS (443) to VAST Management Service (VMS). |
| **Auth** | VAST credentials with read access (e.g., `support`). API v7 (cluster 5.3+). Optional: SSH for switch port mapping and node health checks. |

SSL: for self-signed certificates, set `api.verify_ssl: false` in config.

---

## Installation

### Desktop application (recommended)

Get the latest build from [GitHub Releases](https://github.com/rstamps01/ps-deploy-report/releases/latest).

**macOS**

1. Download **VAST-Reporter-vX.Y.Z-mac.dmg** (use [latest](https://github.com/rstamps01/ps-deploy-report/releases/latest)).
2. Open the .dmg and drag **VAST Reporter** to **Applications**.
3. Open **VAST Reporter** from Applications.  
   First time: if Gatekeeper blocks it, right-click the app → **Open**.
4. The UI opens at `http://127.0.0.1:5173`.

**Windows**

1. Download **VAST-Reporter-vX.Y.Z-win.zip** from the releases page.
2. Extract to a folder and run **vast-reporter.exe**.

No Python or package manager is required.

### Developer installation

For running or building from source:

```bash
git clone https://github.com/rstamps01/ps-deploy-report.git
cd ps-deploy-report

python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

pip install --upgrade pip
pip install -r requirements.txt
python3 src/main.py --version
```

Optional (tests and lint):

```bash
pip install -r requirements-dev.txt
```

### Automated install scripts

**macOS**

```bash
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/docs/deployment/install-mac.sh
chmod +x install-mac.sh
./install-mac.sh
```

**Windows**

```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"
.\install-windows.ps1
```

### Documentation

- [Installation Guide](docs/deployment/INSTALLATION-GUIDE.md)
- [Update Guide](docs/deployment/UPDATE-GUIDE.md)
- [Uninstall Guide](docs/deployment/UNINSTALL-GUIDE.md)
- [Permissions Guide](docs/deployment/PERMISSIONS-GUIDE.md)
- [Deployment Guide](docs/deployment/DEPLOYMENT.md)
- [Port Mapping Guide](docs/deployment/PORT-MAPPING-GUIDE.md)

---

## Configuration

**Quick setup:** use the **Advanced Configuration** page (`/config/advanced`) in the web UI — the recommended way to manage settings. Alternatively, copy the YAML template and edit manually.

```bash
cp config/config.yaml.template config/config.yaml
```

| File | Purpose |
|------|---------|
| `config/config.yaml` | API timeouts, logging, report options (not committed) |
| `config/config.yaml.template` | Default template (committed) |
| `config/cluster_profiles.json` | Saved cluster profiles (UI-managed, shared across Generate, Health Check, and Advanced Ops) |
| `config/device_library.json` | Custom hardware devices (UI-managed) |

**Advanced Configuration UI** provides form-based settings across 9 sections (Report Formatting, Report Sections, API Settings, Logging, Output, SSH, Health Check, Advanced Operations, Security). Changes are saved via deep-merge — only modified keys are updated, preserving all other config values. Use **Reset to Template** to restore defaults without saving.

**Report Tuning Tool** (on the Results page) lets you select a previously generated JSON report file and regenerate a customized PDF with section toggles and formatting overrides — no cluster access required.

**Report formatting options:** Organization name (PDF footer), margins (0.25"–1.5", default 0.5"), font family (Helvetica, Times-Roman, Courier), Include TOC toggle, Include Page Numbers toggle. Config keys: `report.organization`, `report.template.margin_*`, `report.pdf.font_family`, `report.pdf.include_page_numbers`, `report.pdf.include_toc`.

**Environment variables (optional):** `VAST_API_TOKEN`; `VAST_USERNAME` / `VAST_PASSWORD`; `VAST_NODE_USER` / `VAST_NODE_PASSWORD`; `VAST_SWITCH_USER` / `VAST_SWITCH_PASSWORD` for SSH-based port mapping.

---

## Usage

### Web UI (default)

**Desktop:** Double-click **VAST Reporter** (or run `open "/Applications/VAST Reporter.app"` on macOS).

**From source:**

```bash
python3 src/main.py
```

The app listens at `http://127.0.0.1:5173` and opens the browser automatically.

| Page | Purpose |
|------|---------|
| **Dashboard** | Quick Start launch pad with status bar and step-by-step workflow cards |
| **Reporter** | Combined workflow: switch placement, as-built report generation, pre-validation, health checks, one-shot operations with VAST logo progress indicator and granular per-operation progress tracking |
| **Results** | Browse validation results across 9 operation types with cluster profile filtering; Report Tuning Tool for PDF regeneration with section toggles |
| **Library** | Built-in and custom hardware devices (CBox, DBox, Switch, EBox) with images |
| **Docs** | In-app documentation viewer with searchable guides and references |
| **Advanced Configuration** | Form-based settings with 9 accordion sections, Report Tuning Tool for PDF regeneration from JSON with config overrides, deep-merge save |
| **Exit** (navbar) | Shut down the application |
| **More** (hamburger) | Legacy pages (Generate, Reports) and Developer pages (Advanced Ops, Health Check, Configuration — requires `--dev-mode`) |

### Command-line interface

For scripts or headless use:

```bash
# CLI mode (explicit)
python3 src/main.py --cli --cluster 10.143.11.204 --output ./reports

# Legacy: cluster + output imply CLI
python3 src/main.py --cluster 10.143.11.204 --output ./reports
```

**Common options**

| Option | Description |
|--------|-------------|
| `--cluster IP` | VAST Management Service IP |
| `--output DIR` | Output directory |
| `--username` / `--password` | Credentials (prompted if omitted) |
| `--token TOKEN` | API token instead of user/pass |
| `--enable-port-mapping` | Collect switch port mapping via SSH |
| `--switch-user` / `--switch-password` | SSH for switches |
| `--node-user` / `--node-password` | SSH for VAST nodes |
| `--config PATH` | Config file path |
| `--no-proxy-jump` | Disable SSH proxy hop through CNode for switch connections |
| `--dev-mode` | Enable developer mode (Advanced Operations, Health Check, Configuration pages) |
| `--cli` | Force CLI mode |
| `--gui` | Force GUI mode |
| `--verbose` | Debug logging |
| `--version` | Show version and exit |

**Examples**

```bash
# Interactive credentials
python3 src/main.py --cluster 10.143.11.204 --output ./reports

# With credentials
python3 src/main.py --cluster 10.143.11.204 --username support --password SECRET --output ./reports

# With port mapping
python3 src/main.py --cluster 10.143.11.204 --output ./reports \
  --enable-port-mapping --node-user vastdata --node-password NODE_PASS \
  --switch-user cumulus --switch-password SWITCH_PASS

# Developer mode (Advanced Operations)
python3 src/main.py --dev-mode
```

---

## Output files

| File | Description |
|------|-------------|
| `vast_asbuilt_report_{cluster}_{timestamp}.pdf` | VAST-branded PDF report |
| `vast_data_{cluster}_{timestamp}.json` | Structured data for automation |

**PDF contents:** Title; dynamic TOC; executive summary; cluster info; hardware summary and inventory (CBox, DBox, EBox); physical rack layout; network config; switch port mapping (if enabled); logical network diagram; logical config; security; health check results and post-deployment validation (if enabled).

### Regenerating PDF from JSON

Re-build a PDF from saved JSON (no cluster access):

```bash
python3 scripts/regenerate_report.py path/to/vast_data_CLUSTER_TIMESTAMP.json
python3 scripts/regenerate_report.py path/to/vast_data_CLUSTER_TIMESTAMP.json output/custom.pdf
```

---

## Health check

The Health Check module runs tiered cluster validation:
- **Tier 1 (API):** 26 read-only API checks (RAID, nodes, alarms, VIPs, license, capacity, firmware, etc.)
- **Tier 3 (Switch SSH):** 6 switch checks (MLAG status, NTP, config backup readability)

**Standalone Health Check:** Use the **Health** page in the web UI to run checks with real-time log streaming. A remediation report with correlated findings and resolution guidance is auto-generated.

**Include in Report:** Enable the **Include Health Check** toggle on the Generate page to add health check results to the PDF report:
- **Port Mapping disabled:** Runs Tier 1 only (26 API checks)
- **Port Mapping enabled with SSH credentials:** Runs Tier 1 + 3 (32 total checks)

**VIP Pools:** When no VIP pools are configured, the check returns `warning` (not `fail`) — an unconfigured VIP pool is informational. Reports regenerated from older JSON files automatically correct stale statuses.

### Health check report sections

When health check is included, the PDF report contains two additional sections:

| Section | Content |
|---------|---------|
| **Cluster Health Check Results** | Summary table (Pass/Fail/Warning/Skipped counts) and detailed results table with Check Name, Category, Status, and Message |
| **Post Deployment Activities** | "Next Steps — Get Started Using VAST Data" checklist (Call Home, VIP creation, failover testing, VIP movement/ARP, license activation, password changes) |

### Remediation report

Health checks auto-generate a `.txt` remediation report at `output/health/health_remediation_<cluster>_<timestamp>.txt` containing:
- Numbered findings with severity levels
- Impact statements and correlated issues (e.g., CNode + DNode down = chassis issue)
- Actionable remediation steps per finding

---

## Reporter and post-install validation

The **Reporter** page is the primary workflow interface, available to all users. It combines switch placement, as-built report generation, pre-validation, and optional health checks into a single page with VAST logo progress tracking.

The **Advanced Operations** page provides the same validation workflows in a step-by-step developer interface. Access requires the `--dev-mode` flag at startup (or `VAST_DEV_MODE=1` environment variable).

```bash
python3 src/main.py --dev-mode
```

### Available workflows

| Workflow | Steps | Description |
|----------|-------|-------------|
| **vnetmap** | 7 | Download and run vnetmap.py for network topology validation |
| **VAST Support Tools** | 5 | Run vast_support_tools.py for cluster diagnostics |
| **vperfsanity** | 7 | Deploy, extract, prepare (with cross-tenant view cleanup), run tests, collect results, upload, cleanup |
| **VMS Log Bundle** | 5 | Discover log sizes, confirm collection, create and download bundle |
| **Switch Configuration** | 3 | Extract switch config for backup/replacement; auto-detects Cumulus NVUE/NCLU and Mellanox switch types |
| **Network Configuration** | 4 | Extract configure_network.py commands via gateway-proxied clush execution |

### Features

- **Step-by-step execution** with persistent output pane and real-time feedback
- **Result bundler** creates downloadable ZIP packages containing all validation outputs
- **Tool manager** with internet-first download strategy and local cache fallback; "Update Tools" button in UI
- **Default credentials toggle** (default ON) auto-populates `support`/`654321` for all operations; `admin`/`123456` auto-injected for vperfsanity only
- **Unified profile management** — profiles saved here are accessible in Health Check and Generate (and vice versa)

See [Advanced Operations Guide](docs/ADVANCED-OPERATIONS.md) and [Post-Install Validation](docs/POST-INSTALL-VALIDATION.md) for detailed documentation.

---

## Building from source

### macOS (.app and .dmg)

```bash
# Prerequisites
pip install pyinstaller
brew install create-dmg   # optional, for .dmg

# From project root (activate venv so pyinstaller is on PATH)
source venv/bin/activate
bash packaging/build-mac.sh
```

**Output:** `dist/VAST Reporter.app` and, if `create-dmg` is installed, `dist/VAST-Reporter-vX.Y.Z-mac.dmg`.

### Windows (.exe)

```powershell
pip install pyinstaller
powershell -File packaging/build-windows.ps1
```

Build definition: `packaging/vast-reporter.spec`.

---

## Project structure

```
vast-asbuilt-reporter/
├── README.md                     # This file
├── CHANGELOG.md
├── pyproject.toml                # Black, pytest, mypy, coverage config
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # Dev/test (pytest, flake8, black, mypy, etc.)
├── Start Reporter.command        # macOS double-click launcher (from source)
├── .github/workflows/
│   ├── ci.yml                    # Push/PR quality gates and tests
│   ├── build-release.yml         # Tag-triggered cross-platform builds
│   └── security.yml              # Weekly pip-audit + bandit scans
├── assets/
│   ├── diagrams/                 # VAST logos, diagram assets
│   └── hardware_images/          # CBox, DBox, EBox, switch bezel images
├── config/
│   ├── config.yaml.template
│   ├── cluster_profiles.json
│   └── device_library.json
├── docs/
│   ├── deployment/               # Install, update, uninstall, permissions, port mapping
│   ├── development/              # Internal implementation docs, analysis, RCA
│   ├── api/                      # EBox API discovery docs
│   ├── confluence/               # 26 Confluence design/requirements pages (offline)
│   ├── ADVANCED-OPERATIONS.md
│   ├── POST-INSTALL-VALIDATION.md
│   ├── API-REFERENCE.md
│   └── TODO-ROADMAP.md           # Canonical roadmap and task tracking
├── frontend/
│   ├── templates/                # Jinja2 HTML: dashboard, reporter, generate,
│   │                             #   reports, validation_results, library, health,
│   │                             #   config, advanced_config, docs, advanced_ops
│   └── static/                   # CSS, JS, images
├── packaging/
│   ├── vast-reporter.spec        # PyInstaller spec
│   ├── build-mac.sh
│   ├── build-windows.ps1
│   └── icons/                    # .icns / .ico app icons
├── scripts/
│   ├── regenerate_report.py      # PDF from JSON
│   ├── export_swagger.py         # API schema export
│   ├── extract_pdf_info.py       # PDF metadata extraction
│   └── discover_api_fields.py    # API field discovery
├── src/
│   ├── main.py                   # Entry (GUI default / CLI via --cli)
│   ├── app.py                    # Flask web UI
│   ├── api_handler.py            # VAST API client (GET-only policy)
│   ├── data_extractor.py         # API → report sections
│   ├── report_builder.py         # PDF/JSON generation
│   ├── health_checker.py         # Tier 1 + Tier 3 health checks + remediation
│   ├── rack_diagram.py           # Physical rack layout
│   ├── network_diagram.py        # Network topology
│   ├── brand_compliance.py       # VAST styling
│   ├── hardware_library.py       # Consolidated device definitions
│   ├── external_port_mapper.py   # SSH-based port mapping
│   ├── advanced_ops.py           # Advanced Operations manager
│   ├── script_runner.py          # Secure script download/execution
│   ├── tool_manager.py           # Deployment tool management
│   ├── oneshot_runner.py          # One-Shot orchestration
│   ├── result_bundler.py         # ZIP bundle creation
│   ├── result_scanner.py         # Validation result scanner
│   ├── session_manager.py        # Session state management
│   ├── workflows/                # Workflow registry and implementations
│   │   ├── __init__.py           #   Registry pattern
│   │   ├── vnetmap_workflow.py
│   │   ├── vperfsanity_workflow.py
│   │   ├── support_tool_workflow.py
│   │   ├── log_bundle_workflow.py
│   │   ├── switch_config_workflow.py
│   │   └── network_config_workflow.py
│   └── utils/
│       ├── __init__.py           # Path helpers (bundle_dir, data_dir)
│       ├── logger.py             # Logging + SSE log handler
│       ├── ops_log_manager.py    # Persistent operation log storage
│       ├── ssh_adapter.py        # Cross-platform SSH (paramiko + pexpect)
│       └── vms_tunnel.py         # VMS tunnel for Tech Port auto-discovery
└── tests/                        # pytest suite
    ├── conftest.py               # Shared fixtures
    ├── test_app.py               # Flask route tests
    ├── test_api_handler.py
    ├── test_data_extractor.py
    ├── test_report_builder.py
    ├── test_health_checker.py
    ├── test_advanced_ops.py
    ├── test_workflows.py
    ├── test_script_runner.py
    ├── test_result_bundler.py
    ├── test_tool_manager.py
    ├── test_integration.py
    ├── test_main.py
    ├── test_rack_diagram.py
    ├── test_external_port_mapper.py
    ├── test_ssh_adapter.py
    ├── test_functional_validation.py
    └── ...
```

---

## Development

**Tests**

```bash
pytest tests/ -v
pytest tests/ --cov=src --cov-report=html
```

**Validating Windows and diagram behavior (before pushing)**
Run the functional validation suite so port-mapping charmap and diagram placeholder regressions are caught before commit. CI runs it with unit tests; locally:

```bash
pytest tests/test_functional_validation.py -v
```

This checks: ASCII-safe port mapping error logging (no `charmap` encode errors on Windows), and that the network diagram uses the PDF-to-PNG fallback (PyMuPDF) when renderPM fails, so the report does not use the placeholder image.

**Lint / format**

```bash
flake8 src/ tests/
black src/ tests/
```

**Pre-release checklist (quality gate)**
Before tagging a release or merging to `main`/`develop`, run the same checks as CI:

```bash
# Lint and format
flake8 src/ tests/
black --check --line-length 120 src/ tests/

# Type check
mypy src/ --ignore-missing-imports --no-strict-optional

# Unit tests with coverage (excludes UI and integration)
python -m pytest tests/ -v --ignore=tests/test_ui.py --ignore=tests/test_integration.py \
  --cov=src --cov-report=term-missing --cov-fail-under=60
```

Coverage threshold is currently 60% (`pyproject.toml`); target is 75%+ per roadmap item TSE-9.

See [docs/TODO-ROADMAP.md](docs/TODO-ROADMAP.md) for quality-gate items (QG-1 through QG-3).

**Branches:** `main` (releases); `develop` (integration); `feature/*`, `fix/*`. Commits: [Conventional Commits](https://www.conventionalcommits.org/).

Design and change-control docs live in `docs/confluence/` and `.cursor/rules/` (not published to GitHub).

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **403 / incomplete data** | Use `support` (or equivalent) with full read access. |
| **Connection timeout** | Increase `api.timeout` in `config.yaml`. |
| **SSL errors** | Set `api.verify_ssl: false` for self-signed certs. |
| **Port mapping fails** | Check SSH credentials and reachability of switch management IPs. Windows uses paramiko for SSH; macOS/Linux use sshpass. Ensure credentials work via direct SSH first. |
| **"A report is already being generated"** | Click **Cancel**, then retry; if stuck, restart the app. |
| **macOS Gatekeeper** | Right-click the .app → **Open** on first launch. |
| **Windows: PDF "Permission denied"** | Ensure the app can write to `%TEMP%`. If it persists, exclude the app folder from antivirus real-time scan or run from a directory with write access. |
| **Health check SSH hangs** | Check node/switch reachability; SSH checks have a 60s timeout with 10s per-ping limit. |
| **Advanced Ops not visible** | Start the app with `--dev-mode` or set `VAST_DEV_MODE=1`. |

**Debug:** `python3 src/main.py --cluster IP --output ./reports --verbose` and `python3 src/main.py --version`.

---

## Security

- Credentials are **not** stored in config or logs.
- Order: CLI args → environment variables → interactive prompt.
- Logs redact passwords, tokens, and secrets.
- All API traffic over HTTPS (configurable for self-signed).
- Reports contain configuration data only; no credentials in PDF or JSON.
- VAST API access is **read-only** (GET only); see [Read-Only API Policy](docs/development/READ_ONLY_VAST_API_POLICY.md).

---

## Support

1. Check logs and the [Troubleshooting](#troubleshooting) section.
2. Review [docs/deployment](docs/deployment/) and [GitHub Issues](https://github.com/rstamps01/ps-deploy-report/issues).
3. Open an issue with version, steps, and log excerpts.

**Repository:** [github.com/rstamps01/ps-deploy-report](https://github.com/rstamps01/ps-deploy-report)

---

**Version:** 1.5.0 · **VAST:** 5.3+ · **API:** v7 (v1 fallback) · **Python:** 3.10+ (3.12 tested) · **Tests:** 786 passing, 60%+ coverage threshold
