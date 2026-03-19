# VAST As-Built Report Generator

A self-contained application that automatically generates professional "as-built" reports for VAST Data clusters following deployment by Professional Services. Features a browser-based GUI with live progress streaming, a hardware device library, cluster profile management, and a full CLI — packaged as a standalone macOS `.app` / `.dmg` (or Windows `.exe`) with no Python installation required.

## Overview

The VAST As-Built Report Generator connects to VAST Data clusters via the REST API v7, extracts comprehensive configuration and status information, and generates both professional PDF reports and machine-readable JSON data files. It is designed to streamline the post-deployment documentation process for VAST Professional Services engineers while providing enhanced automation and professional reporting capabilities.

## Key Features

### Desktop Application with Web UI
- **Self-Contained Package**: Download the `.dmg` (macOS) or `.zip` (Windows), install, and run — no Python or pip required
- **Browser-Based GUI**: Modern dark-themed web interface at `localhost:5173` matching the VAST Admin UI
- **Live Progress**: Real-time log streaming via Server-Sent Events during report generation
- **Job Cancellation**: Cancel a running report generation at any time via the Cancel button
- **Exit Button**: Gracefully shut down the application from the navbar
- **Cluster Profiles**: Save, load, and delete cluster connection profiles (IP, credentials, settings)
- **Report Browser**: View, download, and manage previously generated reports
- **Configuration Editor**: Edit YAML configuration directly from the GUI
- **Hardware Device Library**: Browse built-in device definitions, add custom devices (CBox, DBox, EBox, Switch) with image upload; unknown models fall back to generic 1U/2U shapes in rack diagrams
- **Health Check**: Cluster deployment health checks (API, node SSH, switch SSH) with real-time log streaming and optional PDF report sections
- **CLI Preserved**: Full command-line interface available via `--cli` flag

### Enhanced Automation (80% Target Achieved)
- **Automated Data Collection**: Comprehensive cluster data extraction with 80% automation
- **Enhanced API Integration**: Support for VAST REST API v7 with v1 fallback for older clusters
- **Rack Positioning**: Automated U-number generation and physical layout visualization
- **Auto/Manual Switch Placement**: Cascading placement logic with manual override via UI
- **PSNT Tracking**: Cluster Product Serial Number integration for support systems
- **Port Mapping**: Optional SSH-based switch port mapping collection with IPL detection

### Professional Reporting
- **Dual Output Formats**: Professional PDF reports and machine-readable JSON files
- **Comprehensive Sections**: Executive summary, hardware inventory, rack diagrams, network topology, security settings, and more
- **Rack Layout Diagrams**: Visual 42U rack diagrams with hardware bezel images
- **Network Topology Diagrams**: Logical network diagrams with port mapping connections
- **VAST Branding**: Customer-ready PDF documents with VAST brand compliance

### Security and Reliability
- **Secure Authentication**: Multiple credential methods (CLI args, environment variables, interactive prompts)
- **Fault Tolerance**: Handles network failures, API errors, and missing data gracefully
- **Comprehensive Logging**: Detailed logging with sensitive data filtering
- **Error Recovery**: Graceful degradation and retry mechanisms with exponential backoff

## Requirements

### For Desktop Application (Recommended)
- **Operating System**: macOS 11+ (Apple Silicon or Intel) or Windows 10+
- **Memory**: Minimum 512MB RAM (1GB recommended)
- **Disk Space**: 100MB for installation, additional space for output files
- **No Python installation required** — the runtime is fully bundled

### For Developer Installation
- **Python**: 3.10 or higher (tested with Python 3.12)
- **Operating System**: Linux, macOS, or Windows
- Runtime dependencies in `requirements.txt`; dev/test dependencies in `requirements-dev.txt`

### Network Requirements
- **Network Access**: Direct access to VAST Management Service (VMS)
- **Ports**: HTTPS (443) to VAST cluster management interface
- **SSL/TLS**: Configurable for self-signed certificates (`api.verify_ssl: false`)

### Authentication Requirements
- **VAST Credentials**: Valid cluster credentials with elevated read access
- **Recommended**: `support` user or equivalent with full read permissions
- **API Access**: VAST REST API v7 (VAST cluster version 5.3+)
- **Optional**: SSH credentials for switch port mapping collection

## Installation

### Desktop Application (Recommended)

Download the latest installer from [GitHub Releases](https://github.com/rstamps01/ps-deploy-report/releases/latest).

**macOS:**
1. Download **[VAST-Reporter-v1.4.2-mac.dmg](https://github.com/rstamps01/ps-deploy-report/releases/latest/download/VAST-Reporter-v1.4.2-mac.dmg)**
2. Open the downloaded `.dmg` file
3. Drag **VAST Reporter** into the **Applications** folder
4. Launch from Applications (first launch: right-click > **Open** to bypass Gatekeeper)
5. The web UI opens automatically in your default browser at `http://127.0.0.1:5173`

To update, download the latest `.dmg` and repeat the steps above — the new version replaces the old one in Applications.

**Windows:**
1. Download `VAST-Reporter-vX.Y.Z-win.zip` from the releases page
2. Extract to a folder of your choice
3. Run `vast-reporter.exe`

No Python installation, virtual environment, or package management required.

### Developer Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rstamps01/ps-deploy-report.git
   cd ps-deploy-report
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate        # macOS/Linux
   # venv\Scripts\activate         # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Verify installation:**
   ```bash
   python3 src/main.py --version
   ```

5. **(Optional) Install dev/test dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

### Automated Installation Scripts (PS Engineers)

**macOS:**
```bash
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/docs/deployment/install-mac.sh
chmod +x install-mac.sh
./install-mac.sh
```

**Windows:**
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/main/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"
.\install-windows.ps1
```

### Documentation

- [Installation Guide](docs/deployment/INSTALLATION-GUIDE.md) — complete installation instructions
- [Update Guide](docs/deployment/UPDATE-GUIDE.md) — update existing installations
- [Uninstall Guide](docs/deployment/UNINSTALL-GUIDE.md) — complete removal procedures
- [Permissions Guide](docs/deployment/PERMISSIONS-GUIDE.md) — API permissions and support user requirements
- [Deployment Guide](docs/deployment/DEPLOYMENT.md) — production deployment and configuration
- [Port Mapping Guide](docs/deployment/PORT-MAPPING-GUIDE.md) — SSH-based switch port mapping setup

## Configuration

### Initial Setup

```bash
cp config/config.yaml.template config/config.yaml
```

Or edit configuration directly in the web UI via the **Configuration** page.

### Configuration Files

| File | Purpose |
|------|---------|
| `config/config.yaml` | Runtime settings (API timeouts, logging, report options) |
| `config/config.yaml.template` | Default template (committed, no secrets) |
| `config/cluster_profiles.json` | Saved cluster connection profiles (auto-managed by UI) |
| `config/device_library.json` | User-defined hardware device definitions (auto-managed by UI) |

### Key Configuration Sections

```yaml
api:              # timeout, max_retries, retry_delay, verify_ssl, version
logging:          # level, format, file_path, rotation_size, console_colors
report:           # organization, template, pdf formatting
output:           # default_directory, filename patterns
data_collection:  # sections, concurrent_requests, graceful_degradation
security:         # prompt_for_credentials, session_timeout, sanitize_logs
```

### Environment Variables

| Variable | Purpose |
|----------|---------|
| `VAST_API_TOKEN` | API token authentication |
| `VAST_USERNAME` / `VAST_PASSWORD` | Cluster credentials |
| `VAST_NODE_USER` / `VAST_NODE_PASSWORD` | SSH node credentials (port mapping) |
| `VAST_SWITCH_USER` / `VAST_SWITCH_PASSWORD` | SSH switch credentials (port mapping) |

## Usage

### Web UI (Default)

Launch the application with no arguments:

```bash
# Desktop app: double-click VAST Reporter.app, or from terminal:
open "/Applications/VAST Reporter.app"

# Developer mode:
python3 src/main.py

# macOS launcher (from project root):
./Start\ Reporter.command
```

The web server starts at `http://127.0.0.1:5173` and opens your default browser. Pages:

- **Dashboard** — overview of recent reports with download/view/delete actions
- **Generate** — enter cluster IP and credentials, select options, click Generate, watch live progress; Cancel button to abort
- **Reports** — browse, download, preview, and delete generated reports
- **Library** — view built-in hardware device definitions (CBox, DBox, Switch, EBox); add custom devices with image upload
- **Health** — run cluster deployment health checks (API, node SSH, switch SSH); view real-time logs; optionally include results in reports
- **Configuration** — edit `config.yaml` settings directly in the browser
- **Exit** button (top-right) — gracefully stops the application

### Command-Line Interface

Use `--cli` or pass `--cluster` directly for scripted/headless usage:

```bash
# Explicit CLI mode
python3 src/main.py --cli --cluster 10.143.11.204 --output ./reports

# Legacy syntax (auto-detected)
python3 src/main.py --cluster 10.143.11.204 --output ./reports
```

#### CLI Options

| Option | Description |
|--------|-------------|
| `--cluster IP` / `--cluster-ip IP` | VAST Management Service IP (required) |
| `--output DIR` / `--output-dir DIR` | Output directory for reports (required) |
| `--username USER` / `-u` | VAST username (prompts if omitted) |
| `--password PASS` / `-p` | VAST password (prompts if omitted) |
| `--token TOKEN` / `-t` | API token (alternative to user/pass) |
| `--enable-port-mapping` | Collect switch port mapping via SSH |
| `--switch-user USER` | SSH username for switches (default: `cumulus`) |
| `--switch-password PASS` | SSH password for switches |
| `--node-user USER` | SSH username for VAST nodes (default: `vastdata`) |
| `--node-password PASS` | SSH password for VAST nodes |
| `--config PATH` / `-c` | Path to configuration file |
| `--verbose` / `-v` | Enable debug-level logging |
| `--version` | Show version and exit |

#### Examples

```bash
# Interactive credentials (recommended)
python3 src/main.py --cluster 10.143.11.204 --output ./reports

# With explicit credentials
python3 src/main.py --cluster 10.143.11.204 --username support --password SECRET --output ./reports

# With API token
python3 src/main.py --cluster 10.143.11.204 --token YOUR_TOKEN --output ./reports

# With port mapping
python3 src/main.py --cluster 10.143.11.204 --output ./reports \
  --enable-port-mapping \
  --node-user vastdata --node-password NODE_PASS \
  --switch-user cumulus --switch-password SWITCH_PASS

# Verbose debugging
python3 src/main.py --cluster 10.143.11.204 --output ./reports --verbose

# Health-check-only PDF (no full report)
python3 src/main.py --cli --cluster 10.143.11.204 --output ./reports --health-only
```

### Health Check

The Health Check module runs tiered cluster validation: Tier-1 API checks (RAID, nodes, alarms, VIPs, license, capacity, firmware, etc.), Tier-2 node SSH checks (PANIC/ALERT logs, management ping, support tool, vnetmap), and Tier-3 switch SSH checks (MLAG status, NTP sync, config backup). Use the **Health** page in the web UI to run checks with real-time log streaming, or enable "Include Health Check" on the Generate page to add Health Check Results and Post Deployment Validation sections to the PDF report. The `--health-only` flag generates a standalone health-check PDF without the full as-built report.

### Output Files

| File | Description |
|------|-------------|
| `vast_asbuilt_report_{cluster}_{timestamp}.pdf` | Professional customer-facing PDF with VAST branding |
| `vast_data_{cluster}_{timestamp}.json` | Machine-readable structured data for automation |

**PDF Report Sections:**
1. Title Page (cluster name, PSNT, date, organization)
2. Table of Contents (dynamic, auto-generated)
3. Executive Summary (cluster overview, hardware counts)
4. Cluster Information (version, features, configuration)
5. Hardware Summary (capacity metrics, storage)
6. Hardware Inventory (CBox/DBox tables with node-level detail)
7. Physical Rack Layout (42U rack diagrams with hardware images)
8. Network Configuration (interfaces, VIPs, DNS, NTP)
9. Switch Port Mapping (when enabled)
10. Logical Network Diagram (topology visualization)
11. Logical Configuration (tenants, views, policies)
12. Security & Authentication

### Regenerating Reports from JSON

Re-render PDF reports from saved JSON data without cluster access:

```bash
python3 scripts/regenerate_report.py output/vast_data_CLUSTER_TIMESTAMP.json
python3 scripts/regenerate_report.py output/vast_data_CLUSTER_TIMESTAMP.json output/custom.pdf
python3 scripts/regenerate_report.py output/vast_data_CLUSTER_TIMESTAMP.json --output-dir ./test_reports
```

## Building from Source

### macOS (.app and .dmg)

```bash
# Prerequisites
pip install pyinstaller
brew install create-dmg

# Build
bash packaging/build-mac.sh
# Output: dist/VAST Reporter.app and dist/VAST-Reporter-vX.Y.Z-mac.dmg
```

### Windows (.exe)

```powershell
pip install pyinstaller
powershell -File packaging/build-windows.ps1
```

Build configuration is in `packaging/vast-reporter.spec`.

## Project Structure

```
vast-asbuilt-reporter/
├── README.md                        # This file
├── CHANGELOG.md                     # Version history (Keep a Changelog format)
├── requirements.txt                 # Runtime dependencies
├── requirements-dev.txt             # Dev/test dependencies (pytest, flake8, etc.)
├── Start Reporter.command           # macOS double-click launcher
├── .github/workflows/
│   └── build-release.yml            # CI/CD: cross-platform builds on version tags
├── assets/
│   ├── diagrams/                    # VAST logos, network diagram assets
│   └── hardware_images/             # Hardware bezel images (CBox, DBox, Switch)
├── config/
│   ├── config.yaml                  # Runtime configuration (not committed)
│   ├── config.yaml.template         # Default config template (committed)
│   ├── cluster_profiles.json        # Saved cluster profiles (auto-managed)
│   └── device_library.json          # User-defined hardware devices (auto-managed)
├── docs/
│   ├── confluence/                  # Internal only (not published to GitHub)
│   └── deployment/                  # Installation, update, uninstall, permissions guides
├── frontend/
│   ├── templates/                   # Jinja2 HTML templates
│   │   ├── base.html                # Base layout (navbar, footer, favicon)
│   │   ├── dashboard.html           # Dashboard page
│   │   ├── generate.html            # Report generation page
│   │   ├── reports.html             # Report browser page
│   │   ├── library.html             # Hardware device library page
│   │   └── config.html              # Configuration editor page
│   └── static/
│       ├── css/app.css              # VAST-themed dark UI stylesheet
│       ├── js/app.js                # Frontend JS (SSE, profiles, discovery, cancel)
│       └── img/                     # Logos, favicon, apple-touch-icon
├── packaging/
│   ├── vast-reporter.spec           # PyInstaller build spec
│   ├── build-mac.sh                 # macOS build script (.app + .dmg)
│   ├── build-windows.ps1            # Windows build script
│   └── icons/                       # App icons (.icns, .ico)
├── scripts/
│   └── regenerate_report.py         # Re-render PDF from saved JSON data
├── src/
│   ├── main.py                      # Entry point (GUI + CLI routing)
│   ├── app.py                       # Flask web UI (routes, SSE, job management)
│   ├── api_handler.py               # VAST API client (auth, retry, version detection)
│   ├── data_extractor.py            # Raw API data → structured report sections
│   ├── report_builder.py            # PDF/JSON report generation (ReportLab)
│   ├── rack_diagram.py              # Physical rack layout diagram generator
│   ├── network_diagram.py           # Logical network topology diagram generator
│   ├── brand_compliance.py          # VAST brand colors, fonts, styling
│   ├── external_port_mapper.py      # SSH-based switch port mapping collection
│   ├── enhanced_port_mapper.py      # Port mapping enrichment and correlation
│   ├── port_mapper.py               # Port mapping data structures
│   ├── vnetmap_parser.py            # VNetMap output file parser
│   └── utils/
│       ├── __init__.py              # Bundle/data path resolution helpers
│       ├── logger.py                # Logging, SSE handler, sensitive data filter
│       └── ssh_adapter.py           # Cross-platform SSH (paramiko + pexpect)
└── tests/
    ├── test_api_handler.py          # API client tests
    ├── test_app.py                  # Flask route and helper tests
    ├── test_data_extractor.py       # Data processing tests
    ├── test_report_builder.py       # Report generation tests
    ├── test_launcher.py             # GUI/CLI mode routing tests
    ├── test_main.py                 # CLI workflow tests
    ├── test_logging.py              # Logging infrastructure tests
    ├── test_sse_logger.py           # SSE log handler tests
    ├── test_ssh_adapter.py          # SSH adapter tests
    ├── test_rack_diagram.py          # Rack diagram generic 1U/2U fallback tests
    ├── test_ui.py                   # Playwright browser UI tests
    └── data/                        # Test fixtures and mock API responses
```

## Development

### Testing

```bash
# Run all tests (e.g. 260+)
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html

# Run a specific module
python3 -m pytest tests/test_app.py -v
```

### Code Quality

```bash
flake8 src/ tests/
black src/ tests/
mypy src/
```

### Git Workflow

- `main` — protected, production-ready releases (tagged)
- `develop` — primary development branch; all features merge here first
- `feature/<name>` — feature branches off `develop`
- `fix/<name>` — bugfix branches off `develop`

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `feat(scope): description`, `fix(scope): description`, etc.

### Design Reference

Project design documents are synced from Confluence into `docs/confluence/` on developer machines (not published to GitHub). Cursor workspace rules in `.cursor/rules/` enforce architecture, coding standards, and change control conventions.

## Troubleshooting

### Connection Issues

| Symptom | Solution |
|---------|----------|
| `403 Forbidden` / incomplete data | Use `support` user or equivalent with full read permissions |
| Connection timeout | Increase `api.timeout` in `config.yaml` (default: 30s) |
| SSL certificate errors | Set `api.verify_ssl: false` in `config.yaml` for self-signed certs |
| Port mapping fails | Check SSH credentials, verify network access to switch management IPs |

### Application Issues

| Symptom | Solution |
|---------|----------|
| "A report is already being generated" | Click **Cancel**, then retry. If stuck, restart the app. |
| App hangs after report completes | Ensure `threaded=True` in server config (default in v1.4.0+) |
| macOS Gatekeeper blocks app | Right-click the `.app` > Open (first launch only) |

### Debug Mode

```bash
# Verbose logging (CLI)
python3 src/main.py --cluster IP --output ./reports --verbose

# Check version
python3 src/main.py --version

# Verify environment
python3 -c "import reportlab; print(f'ReportLab {reportlab.Version}')"
```

## Security

- **Credentials are never stored** in configuration files or logs
- **Credential flow**: CLI args → environment variables → interactive `getpass` prompt
- **Log sanitization**: Automatic redaction of passwords, tokens, and secrets
- **SSL/TLS**: HTTPS for all API communication (configurable for self-signed certs)
- **Reports contain configuration data only** — no credentials in PDF or JSON output

## Support

For issues, questions, or contributions, refer to the project's [GitHub repository](https://github.com/rstamps01/ps-deploy-report).

1. Check the logs for error messages
2. Review `config.yaml` for common misconfigurations
3. Consult the troubleshooting section above
4. Check GitHub issues for known problems
5. Create a new issue with detailed information

## License

[License information to be added]

---

**Version**: 1.4.2
**Target VAST Version**: 5.3+
**API Version**: v7 (with v1 fallback)
**Test Suite**: 267 tests (run `pytest tests/ -v`)
**Last Updated**: March 2026
