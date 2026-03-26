# VAST As-Built Report Generator - Installation Guide

**For VAST Professional Services Engineers**

## Table of Contents

1. [Quick Start — Desktop Application](#quick-start--desktop-application)
2. [macOS Installation](#macos-installation)
3. [Windows Installation](#windows-installation)
4. [Post-Installation Setup](#post-installation-setup)
5. [Updating](#updating)
6. [Developer Installation](#developer-installation)
7. [Troubleshooting](#troubleshooting)
8. [Uninstallation](#uninstallation)

---

## Quick Start — Desktop Application

The fastest way to get started. No Python, package managers, or terminal commands required.

**macOS:**
1. Download **[VAST-Reporter-v1.5.0-mac.dmg](https://github.com/rstamps01/ps-deploy-report/releases/latest/download/VAST-Reporter-v1.5.0-mac.dmg)**
2. Open the `.dmg` and drag **VAST Reporter** to **Applications**
3. Launch from Applications

**Windows:**
1. Download **VAST-Reporter-v1.5.0-win.zip** from [GitHub Releases](https://github.com/rstamps01/ps-deploy-report/releases/latest)
2. Extract the `.zip` to a folder (e.g. `C:\Program Files\VAST Reporter`)
3. Run `vast-reporter.exe`

The application opens a browser window at `http://127.0.0.1:5173` with the full web UI. No additional setup is needed.

---

## macOS Installation

### Prerequisites

- **macOS**: 11 (Big Sur) or later
- **Architecture**: Intel or Apple Silicon (M1/M2/M3)
- **Disk Space**: ~100 MB

### Step-by-Step

1. **Download the DMG installer:**

   Go to [github.com/rstamps01/ps-deploy-report/releases/latest](https://github.com/rstamps01/ps-deploy-report/releases/latest) and download `VAST-Reporter-v1.5.0-mac.dmg`.

   Or from the terminal:
   ```bash
   curl -LO https://github.com/rstamps01/ps-deploy-report/releases/latest/download/VAST-Reporter-v1.5.0-mac.dmg
   ```

2. **Install the application:**

   - Double-click the downloaded `.dmg` file to mount it
   - Drag **VAST Reporter** into the **Applications** folder shortcut
   - Eject the DMG after copying completes

3. **First launch — bypass Gatekeeper:**

   Since the app is not signed with an Apple Developer ID, macOS will block it on first launch:
   - Open **Applications** in Finder
   - **Right-click** (or Control-click) **VAST Reporter** > **Open**
   - Click **Open** in the confirmation dialog
   - This only needs to be done once; subsequent launches work normally

4. **Verify:**

   The app will:
   - Start a local web server on port 5173
   - Open your default browser to `http://127.0.0.1:5173`
   - Display the VAST As-Built Reporter dashboard

### What Gets Installed

| Component | Location |
|-----------|----------|
| Application | `/Applications/VAST Reporter.app` |
| Reports | Saved to the directory you choose in the UI (default: `~/reports`) |
| Logs | Inside the app bundle (temporary) |

The application is fully self-contained — it bundles Python, all libraries, and assets inside the `.app` bundle. Nothing else is installed on your system.

---

## Windows Installation

### Prerequisites

- **Windows**: 10 or later
- **Architecture**: x64
- **Disk Space**: ~100 MB

### Step-by-Step

1. **Download the ZIP package:**

   Go to [github.com/rstamps01/ps-deploy-report/releases/latest](https://github.com/rstamps01/ps-deploy-report/releases/latest) and download `VAST-Reporter-v1.5.0-win.zip`.

2. **Extract and install:**

   - Right-click the `.zip` file > **Extract All...**
   - Choose a location (e.g. `C:\Program Files\VAST Reporter` or `%USERPROFILE%\VAST Reporter`)
   - Open the extracted folder

3. **Launch:**

   - Double-click `vast-reporter.exe`
   - If Windows Defender SmartScreen blocks it, click **More info** > **Run anyway**
   - The browser opens to `http://127.0.0.1:5173`

### What Gets Installed

The `.zip` contains a single folder with the self-contained application. No registry entries, services, or system-level changes are made.

---

## Post-Installation Setup

### First Report

1. Open the application (if not already running)
2. Navigate to the **Generate** page
3. Enter your cluster details:
   - **Cluster IP**: The VAST Management Service IP address
   - **Username**: `support` (recommended for full API access)
   - **Password**: Your cluster password
4. Click **Generate**
5. Monitor progress in the live log window
6. Download the PDF and JSON files when complete

### Cluster Profiles

Save frequently-used cluster connections as profiles to avoid re-entering credentials:

1. Fill in the cluster IP, username, and password on the Generate page
2. Enter a profile name and click **Save**
3. Next time, select the profile from the dropdown to auto-fill all fields

### Configuration

Most settings can be managed directly in the web UI via the **Configuration** page. Advanced users can also edit `config.yaml` directly if running from source.

### Environment Variables (Optional)

For automated or scripted usage, credentials can be passed via environment variables:

| Variable | Purpose |
|----------|---------|
| `VAST_USERNAME` / `VAST_PASSWORD` | Cluster credentials |
| `VAST_API_TOKEN` | API token (alternative to user/pass) |
| `VAST_NODE_USER` / `VAST_NODE_PASSWORD` | SSH credentials for port mapping (nodes) |
| `VAST_SWITCH_USER` / `VAST_SWITCH_PASSWORD` | SSH credentials for port mapping (switches) |

---

## Updating

To update to the latest version:

1. Go to [github.com/rstamps01/ps-deploy-report/releases/latest](https://github.com/rstamps01/ps-deploy-report/releases/latest)
2. Download the latest `.dmg` (macOS) or `.zip` (Windows)
3. Install as described above — the new version replaces the old one

Your saved cluster profiles and configuration are stored outside the application bundle and will persist across updates.

---

## Developer Installation

For contributors or users who want to run from source.

### Prerequisites

- **Python**: 3.10 or higher (tested with 3.12)
- **Git**: For cloning the repository
- **OS**: macOS, Linux, or Windows

### Setup

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

4. **Verify:**
   ```bash
   python3 src/main.py --version
   ```

5. **Launch the web UI:**
   ```bash
   python3 src/main.py
   ```

6. **(Optional) Install dev/test dependencies:**
   ```bash
   pip install -r requirements-dev.txt
   ```

### Running from Source

```bash
# Web UI (default)
python3 src/main.py

# CLI mode
python3 src/main.py --cli --cluster 10.143.11.204 --output ./reports

# macOS double-click launcher (from project root)
./Start\ Reporter.command
```

---

## Troubleshooting

### macOS Issues

**Gatekeeper blocks the app ("cannot be opened because the developer cannot be verified")**
- Right-click the app > Open > click Open in the dialog (first launch only)

**App closes immediately after opening**
- Open a terminal and run: `/Applications/VAST\ Reporter.app/Contents/MacOS/vast-reporter`
- Check the output for error messages

**Port 5173 already in use**
- Another instance may be running; check Activity Monitor for `vast-reporter`
- Or kill it: `lsof -ti:5173 | xargs kill`

### Windows Issues

**SmartScreen blocks the application**
- Click **More info** > **Run anyway**

**"VCRUNTIME140.dll was not found"**
- Install the [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### General Issues

**403 Forbidden / incomplete data in report**
- Use the `support` username (or equivalent with full read permissions)
- Standard accounts may lack API access to some endpoints

**Connection timeout**
- Verify network connectivity to the VAST Management Service
- Check that port 443 (HTTPS) is accessible

**Port mapping not working**
- Verify SSH access to switches and nodes
- Check that SSH credentials are correct
- See [Port Mapping Guide](PORT-MAPPING-GUIDE.md) for detailed setup

### Getting Help

1. Check the application logs (visible in the Progress window during generation)
2. Review the [main README](../../README.md) for additional troubleshooting
3. Open an issue at [github.com/rstamps01/ps-deploy-report/issues](https://github.com/rstamps01/ps-deploy-report/issues)

When reporting issues, include:
- Operating system and version
- Application version (shown in the footer)
- Error messages or screenshots
- Steps to reproduce

---

## Uninstallation

### macOS

1. Drag **VAST Reporter** from Applications to Trash
2. Empty the Trash

### Windows

1. Delete the extracted `VAST Reporter` folder
2. No registry entries or services to clean up

### Developer Installation

```bash
rm -rf ps-deploy-report/
```

---

**Version**: 1.5.0
**Last Updated**: March 17, 2026
**Compatibility**: macOS 11+, Windows 10+
