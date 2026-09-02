# VAST As-Built Report Generator - Installation Guide

**For VAST Professional Services Engineers**

## Table of Contents

1. [Quick Start — Desktop Application](#quick-start-desktop-application)
2. [macOS Installation](#macos-installation)
3. [Windows Installation](#windows-installation)
4. [Post-Installation Setup](#post-installation-setup)
   - [Prerequisites](#prerequisites_2)
   - [Generating Your First Report](#generating-your-first-report)
   - [Cluster Profiles](#cluster-profiles)
5. [Updating](#updating)
6. [Developer Installation](#developer-installation)
7. [Troubleshooting](#troubleshooting)
8. [Uninstallation](#uninstallation)

---

## Quick Start — Desktop Application

The fastest way to get started. No Python, package managers, or terminal commands required.

**macOS:**
1. Download the DMG for your Mac from [GitHub Releases]({{LATEST_RELEASE_URL}}) — **{{MAC_ARM64_DMG}}** for Apple Silicon, **{{MAC_X64_DMG}}** for Intel
2. Open the `.dmg` and drag **VAST Reporter** to **Applications**
3. Launch from Applications

**Windows:**
1. Download **{{WIN_ZIP}}** from [GitHub Releases]({{LATEST_RELEASE_URL}})
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

   Go to [GitHub Releases]({{LATEST_RELEASE_URL}}) and download the DMG matching your Mac:

   | Mac | Download |
   |-----|----------|
   | Apple Silicon (M1/M2/M3/M4) | `{{MAC_ARM64_DMG}}` |
   | Intel | `{{MAC_X64_DMG}}` |

   Not sure which you have? Apple menu > **About This Mac**. A **Chip** line means Apple Silicon; a **Processor** line means Intel.

   Or from the terminal:
   ```bash
   curl -LO {{LATEST_RELEASE_URL}}/download/{{MAC_ARM64_DMG}}
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

   Go to [GitHub Releases]({{LATEST_RELEASE_URL}}) and download `{{WIN_ZIP}}`.

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

### Prerequisites

Work through these before generating a report. The first is about the
application; the rest are about the cluster, and skipping them produces a report
that is missing sections rather than one that fails outright.

#### 1. Update the deployment tools

The validation tools are fetched separately from the application, so a fresh
install has either nothing cached or copies from whenever the build was made.

Click **Update Tools** in the top-right of the header. The dropdown lists each
tool with its description, cached size, and last-updated date, and the heading
shows how many are cached — `4/4 cached` means you are ready. Tools older than a
week carry an age badge such as `12D OLD`; they still work, but results are only
as current as the tool that produced them. Click **Update Tools** at the bottom
of the dropdown to refresh.

> Updating needs outbound network access. On an air-gapped site, do this before
> you travel — the cached copies are what you will be running on.

#### 2. Install `tsh` if you will use Teleport Mode (optional)

Only needed if you reach the cluster through Teleport. Install the Teleport
client, then open the **&#9776;** menu in the header, choose **Configuration**,
and expand **Teleport Settings**. The pill
beside that heading reads `Install tsh` until the client is found, and
`tsh Installed` once it is. The same pill appears next to **Teleport Mode** on
the Reporter page. See [Teleport Mode (Beta)](../TELEPORT-MODE.md) for the full
setup, including `tsh login` and the identifiers the Teleport fields accept.

#### 3. Add racks in VMS and assign U-heights to the chassis

The rack diagram is drawn from what VMS reports. Racks must exist there, and
each CBox, DBox, and EBox must be assigned a U-height within its rack. Chassis
with no assigned position cannot be placed, so the rack diagram will be empty or
partial no matter what you do in the application.

#### 4. Add switches in VMS

Discovery finds switches through VMS, so switches VMS does not know about will
not appear for U-height assignment. Switches the customer manages independently
can still be added by hand — see [Adding a switch VMS does not manage](#adding-a-switch-vms-does-not-manage)
below — but anything VMS manages is far quicker to discover.

---

### Generating Your First Report

Open the application if it is not already running, then click **Reporter** in
the navigation bar.

#### Step 1 — Choose a connection mode and enter the IP

The mode determines which address goes in the **Tech Port IP / VMS VIP** field:

| Mode | What it does | What to enter |
|---|---|---|
| **Tech Port Mode** (default) | Connects via the CBox tech port and tunnels API calls over SSH, discovering VMS automatically | The tech port address, normally `192.168.2.2` |
| **VMS Mgmt Mode** | Connects straight to VMS over HTTPS, with no SSH tunnel | The VMS management VIP, for example `10.143.10.100` |
| **Teleport Mode** (Beta) | Forwards the cluster API and SSH through Teleport | The cluster's VMS management VIP — **not** `127.0.0.1`, so the API is forwarded to VMS and reachable from any node |

Teleport Mode reveals two extra fields, **Teleport Node** and **Teleport User**.
Both are covered in [Teleport Mode (Beta)](../TELEPORT-MODE.md).

#### Step 2 — Enter credentials

Three sets are collected: **VMS User** / **VMS Password** for the API,
**Node User** / **Node Password** for CNode SSH, and **Switch User** /
**Switch Password** for switch SSH. VMS access requires a `support`-level
account.

The **Autofill Passwords** toggle is **on by default** and fills the factory
defaults for all three, locking the fields so they cannot be edited by mistake.

- **New cluster still on default passwords** — leave the toggle on.
- **Any password has been changed** — turn the toggle off. The fields unlock,
  the usernames stay populated, and the password fields are cleared for you to
  enter the real values.

Node and switch credentials drive port mapping, the vnetmap topology collection,
and the Tier 3 switch health checks. Get them wrong and the report still
generates, but those sections come back empty.

#### Step 3 — Discover racks and switches

This is what places switches in the rack diagram. Without it the chassis appear
but the switches do not.

1. Click **Discovery** in the stepper to open the **Switch Placement Editor**.
2. Click **Run Discovery**. The application connects with the credentials from
   Step 2 and lists the racks and switches VMS knows about.
3. Select the **Rack**.
4. Select the **Switch**.
5. Type the U-height into **Height**.
6. Press **Enter**, or click the **+** button, to record the placement. It
   appears in the **Placed Switches** table below.
7. Repeat for each switch, then click **Save to Profile**.

> **For 2U switches, enter the top U.** A switch occupying U41–U42 is entered as
> `42`. The editor stores the highest unit the device occupies and works
> downward from there, so entering the bottom unit places the switch one unit
> too low.

#### Adding a switch VMS does not manage

Customer-managed switches, and anything else absent from VMS, will not be found
by discovery. Add them by hand so they still render in the rack diagram:

1. Under **Add non-VMS Switch**, click **+ Switch**.
2. Enter a **Switch Name** — a name or description, such as `Spine-A` or
   `Rack1-TOR`.
3. Choose the **Switch Model**. The list comes from the device Library and shows
   each model's height, which is what determines how the switch is drawn.
4. Press **Enter**, or click the **+** button. The switch is added to the
   **Switch** dropdown.
5. Assign its placement exactly as in the numbered steps above — the same
   top-U rule applies.
6. Click **Save to Profile** when you are finished.

#### Step 4 — Choose what to run

The **Reporter Checklist** controls which stages run. Everything is selected by
default:

| Item | What it does |
|---|---|
| **Pre-Validation** | Checks credentials, VMS access, rack and switch configuration, and SSH access before doing any work |
| **Run Vnetmap** | Runs the VAST vnetmap topology tool for fresh port-mapping data. **Required for the Port Map and the Logical Network Diagram** — clear it and the report is generated without them. Needs node SSH credentials |
| **Generate As-Built Report** | The report itself. Required |
| **Health Check** | Tier 1 API checks always; adds Tier 3 switch checks when switch credentials are supplied |

#### Step 5 — Click Run

Progress streams into the **OUTPUT RESULTS** terminal at the bottom of the page.
**Run** becomes **Cancel** while a run is in progress, so a run that is going
wrong can be stopped without restarting the application.

#### Step 6 — View and download the output

When the run finishes, three controls become active in the stepper bar:
**View PDF**, **Download PDF**, and **Download JSON**. View opens the report in
a new browser tab; the download links save the files locally.

Everything is also written to disk and listed under the **Results** tab, so a
report can be retrieved later without regenerating it.

### Cluster Profiles

Save frequently-used connections as profiles to avoid re-entering details:

1. Fill in the connection settings on the Reporter page.
2. Enter a profile name and click **Save** in the Connection Settings toolbar.
3. Next time, pick the profile from the dropdown to restore the fields.

Switch placements are saved separately, via **Save to Profile** inside the
Switch Placement Editor, so U-height assignments survive between runs and do not
need re-entering on each visit.

> Profiles are stored unencrypted, including passwords and API tokens. Treat the
> machine as holding cluster credentials, and prefer a profile per cluster you
> genuinely revisit rather than saving every one-off connection.

### Configuration

Most settings are managed in the web UI via the **Advanced Configuration** page,
which also holds **Teleport Settings**. It is not one of the main navigation
tabs — open the **&#9776;** menu at the right of the header and choose
**Configuration**.

The page groups settings into collapsible sections: Report Formatting (open by
default), API Settings, Logging, Output, SSH, Health Check, Advanced Operations,
and Security. Edit what you need and click **Save**; **Reset Template** restores
the shipped defaults.

If you run from source, `config.yaml` can be edited directly.

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

> **Quit the application first.** An installer cannot replace a copy that is
> still running. On macOS the drag into **Applications** fails outright; on
> Windows the running `.exe` is locked. This is the most common cause of a
> failed upgrade.

1. **Check for an update.** The app header shows a version pill reading
   `LATEST VERSION` or `UPDATE AVAILABLE`. When an update is available, a
   **Download** dropdown appears offering macOS — Apple Silicon, macOS — Intel,
   and Windows.
2. **Download** the build for your machine and wait for it to finish.
3. **Quit the app.** Use **Exit & Upgrade** in the Download dropdown, or the
   **Exit** button in the navbar. Closing the browser tab is not enough — the
   local server keeps running.
4. **Install** as described above. On macOS choose **Replace** when prompted,
   not "Keep Both".
5. **Relaunch** and confirm the version pill reads `LATEST VERSION`.

Because the app is unsigned, macOS treats the replaced bundle as new software
and re-runs Gatekeeper. Expect the **Open Anyway** sequence after every update,
not just the first install. See [Update & Upgrade](UPDATE-GUIDE.md) for the
full walkthrough.

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

**Version**: {{APP_VERSION}}
**Last Updated**: March 17, 2026
**Compatibility**: macOS 11+, Windows 10+
