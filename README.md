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
| **Desktop app** | Single .dmg/.zip install, browser-based UI at localhost:5173, live progress, cancel anytime, cluster profiles, report browser, config editor, hardware device library, full CLI via `--cli` |
| **Automation** | VAST REST API v7 (v1 fallback), rack U positioning, auto/manual switch placement, PSNT tracking, optional SSH-based port mapping and IPL detection |
| **Reports** | PDF (VAST-branded) + JSON; executive summary, hardware inventory, rack diagrams, network topology, security, and more |
| **Reliability** | Secure auth (args, env, or prompt), fault tolerance, sanitized logging, retries with backoff |

### Report highlights

- **Physical rack layout** — 42U rack diagrams with CBox, DBox, and switch positions and hardware images.
- **Network topology** — Logical diagram with port mapping and IPL/MLAG links (PDF + PNG where supported).
- **Dual output** — Customer-ready PDF and machine-readable JSON for automation.

---

## Requirements

| Context | Requirements |
|---------|--------------|
| **Desktop app** | macOS 11+ (Apple Silicon or Intel) or Windows 10+; 512 MB RAM (1 GB recommended); ~100 MB disk. No Python. |
| **From source** | Python 3.10+ (3.12 tested); see `requirements.txt` and optional `requirements-dev.txt`. |
| **Network** | HTTPS (443) to VAST Management Service (VMS). |
| **Auth** | VAST credentials with read access (e.g. `support`). API v7 (cluster 5.3+). Optional: SSH for switch port mapping. |

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

**Quick setup:** copy the template and edit as needed, or use the **Configuration** page in the web UI.

```bash
cp config/config.yaml.template config/config.yaml
```

| File | Purpose |
|------|---------|
| `config/config.yaml` | API timeouts, logging, report options (not committed) |
| `config/config.yaml.template` | Default template (committed) |
| `config/cluster_profiles.json` | Saved cluster profiles (UI-managed) |
| `config/device_library.json` | Custom hardware devices (UI-managed) |

**Environment variables (optional):** `VAST_API_TOKEN`; `VAST_USERNAME` / `VAST_PASSWORD`; `VAST_NODE_USER` / `VAST_NODE_PASSWORD`; `VAST_SWITCH_USER` / `VAST_SWITCH_PASSWORD` for SSH-based port mapping.

---

## Usage

### Web UI (default)

**Desktop:** Double-click **VAST Reporter** (or run `open "/Applications/VAST Reporter.app"` on macOS).

**From source:**

```bash
python3 src/main.py
```

The app listens at `http://127.0.0.1:5173` and can open the browser automatically.

| Page | Purpose |
|------|---------|
| **Dashboard** | Recent reports; download, view, delete |
| **Generate** | Cluster IP, credentials, options; live log; **Cancel** to abort |
| **Reports** | Browse, download, preview, delete |
| **Library** | Built-in and custom hardware devices (CBox, DBox, Switch, EBox) |
| **Configuration** | Edit `config.yaml` in the browser |
| **Exit** (navbar) | Shut down the application |

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
| `--cluster IP` | VAST Management Service IP (required) |
| `--output DIR` | Output directory (required) |
| `--username` / `--password` | Credentials (prompted if omitted) |
| `--token TOKEN` | API token instead of user/pass |
| `--enable-port-mapping` | Collect switch port mapping via SSH |
| `--switch-user` / `--switch-password` | SSH for switches |
| `--node-user` / `--node-password` | SSH for VAST nodes |
| `--config PATH` | Config file path |
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
```

---

## Output files

| File | Description |
|------|-------------|
| `vast_asbuilt_report_{cluster}_{timestamp}.pdf` | VAST-branded PDF report |
| `vast_data_{cluster}_{timestamp}.json` | Structured data for automation |

**PDF contents:** Title; dynamic TOC; executive summary; cluster info; hardware summary and inventory; physical rack layout; network config; switch port mapping (if enabled); logical network diagram; logical config; security.

### Regenerating PDF from JSON

Re-build a PDF from saved JSON (no cluster access):

```bash
python3 scripts/regenerate_report.py path/to/vast_data_CLUSTER_TIMESTAMP.json
python3 scripts/regenerate_report.py path/to/vast_data_CLUSTER_TIMESTAMP.json output/custom.pdf
```

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
├── README.md                 # This file
├── CHANGELOG.md
├── requirements.txt          # Runtime dependencies
├── requirements-dev.txt      # Dev/test (pytest, flake8, etc.)
├── Start Reporter.command    # macOS double-click launcher (from source)
├── .github/workflows/        # CI (e.g. build-release.yml)
├── assets/
│   ├── diagrams/            # VAST logos, diagram assets
│   └── hardware_images/      # CBox, DBox, switch images
├── config/
│   ├── config.yaml.template
│   ├── cluster_profiles.json
│   └── device_library.json
├── docs/deployment/          # Install, update, uninstall, permissions, port mapping
├── frontend/
│   ├── templates/            # HTML (dashboard, generate, reports, library, config)
│   └── static/               # CSS, JS, images
├── packaging/
│   ├── vast-reporter.spec    # PyInstaller spec
│   ├── build-mac.sh
│   ├── build-windows.ps1
│   └── icons/
├── scripts/
│   └── regenerate_report.py  # PDF from JSON
├── src/
│   ├── main.py               # Entry (GUI/CLI)
│   ├── app.py                # Flask UI
│   ├── api_handler.py        # VAST API client
│   ├── data_extractor.py     # API → report sections
│   ├── report_builder.py     # PDF/JSON generation
│   ├── rack_diagram.py       # Physical rack layout
│   ├── network_diagram.py    # Network topology
│   ├── brand_compliance.py   # VAST styling
│   ├── external_port_mapper.py
│   └── utils/                # Logger, paths, SSH
└── tests/                    # pytest suite
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

This checks: ASCII-safe port mapping error logging (no `charmap` encode errors on Windows), and that the network diagram uses the PDF→PNG fallback (PyMuPDF) when renderPM fails, so the report does not use the placeholder image.

**Lint / format**

```bash
flake8 src/ tests/
black src/ tests/
```

**Branches:** `main` (releases); `develop` (integration); `feature/*`, `fix/*`. Commits: [Conventional Commits](https://www.conventionalcommits.org/).

Design and change-control docs live in `docs/confluence/` and `.cursor/rules/` (not published to GitHub).

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| **403 / incomplete data** | Use `support` (or equivalent) with full read access. |
| **Connection timeout** | Increase `api.timeout` in `config.yaml`. |
| **SSL errors** | Set `api.verify_ssl: false` for self-signed certs. |
| **Port mapping fails** | Check SSH credentials and reachability of switch management IPs. On Windows, port mapping uses UTF-8 for SSH output; if you see charmap errors, update to the latest build. |
| **"A report is already being generated"** | Click **Cancel**, then retry; if stuck, restart the app. |
| **macOS Gatekeeper** | Right-click the .app → **Open** on first launch. |
| **Windows: PDF "Permission denied"** | Ensure the app can write to `%TEMP%`. If it persists, exclude the app folder from antivirus real-time scan or run from a directory with write access. |

**Debug:** `python3 src/main.py --cluster IP --output ./reports --verbose` and `python3 src/main.py --version`.

---

## Security

- Credentials are **not** stored in config or logs.
- Order: CLI args → environment variables → interactive prompt.
- Logs redact passwords, tokens, and secrets.
- All API traffic over HTTPS (configurable for self-signed).
- Reports contain configuration data only; no credentials in PDF or JSON.

---

## Support

1. Check logs and the [Troubleshooting](#troubleshooting) section.
2. Review [docs/deployment](docs/deployment/) and [GitHub Issues](https://github.com/rstamps01/ps-deploy-report/issues).
3. Open an issue with version, steps, and log excerpts.

**Repository:** [github.com/rstamps01/ps-deploy-report](https://github.com/rstamps01/ps-deploy-report)

---

**Version:** 1.4.4 · **VAST:** 5.3+ · **API:** v7 (v1 fallback) · **Tests:** `pytest tests/ -v`
