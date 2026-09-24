# VAST As-Built Report Generator - Update & Upgrade Guide

**For VAST Professional Services Engineers**

## Table of Contents

1. [Overview](#overview)
2. [Before You Start: Quit the App](#before-you-start-quit-the-app)
3. [Knowing an Update Is Available](#knowing-an-update-is-available)
4. [Updating on macOS](#updating-on-macos)
5. [Gatekeeper After an Update](#gatekeeper-after-an-update)
6. [Updating on Windows](#updating-on-windows)
7. [Verifying the Update](#verifying-the-update)
8. [What Is Preserved Across Updates](#what-is-preserved-across-updates)
9. [Rolling Back to a Previous Version](#rolling-back-to-a-previous-version)
10. [Troubleshooting](#troubleshooting)
11. [Updating a Source (Git) Installation](#updating-a-source-git-installation)

---

## Overview

VAST As-Built Report Generator is a desktop application. Updating means downloading
a new release artifact and replacing the copy you already have — there is no
in-place auto-updater, no package manager, and no server to restart.

Installing for the first time rather than updating? See the
[Installation Guide](INSTALLATION-GUIDE.md) instead.

Each release publishes exactly three artifacts:

| Platform | Artifact | Use when |
|----------|----------|----------|
| macOS (Apple Silicon) | `{{MAC_ARM64_DMG}}` | Your Mac reports a **Chip** (M-series) |
| macOS (Intel) | `{{MAC_X64_DMG}}` | Your Mac reports a **Processor** (Intel) |
| Windows | `{{WIN_ZIP}}` | Windows 10 or later, x64 |

All three are published on the releases page: [{{RELEASES_URL}}]({{RELEASES_URL}}).

The whole update is four steps:

1. Confirm an update exists (the header tells you).
2. Download the artifact that matches your machine.
3. **Quit the application.**
4. Replace the old copy and relaunch.

Step 3 is the one people skip, and it is the single most common cause of a
failed upgrade. It has its own section, immediately below.

---

## Before You Start: Quit the App

**An installer cannot replace a copy of the application that is still running.**

- **macOS:** dragging the new `VAST Reporter.app` onto `/Applications` while the
  old one is running **fails** — Finder reports that the item is in use and the
  copy is refused. You are left on the old version even though the download
  succeeded.
- **Windows:** the running `vast-reporter.exe` is locked by the operating
  system. Extracting the new ZIP over the old folder fails on that file (and
  frequently on its supporting libraries too), leaving a half-updated folder
  that may not start.

The application gives you two ways to shut down cleanly:

1. **Exit & Upgrade** — inside the **Download** dropdown in the header. This
   button exists specifically for this situation: it stops the local server so
   the new version can be installed. Let the download finish first, then click it.
2. **Exit** — in the navigation bar, available on every page. Use this any time
   you want to stop the application.

Both prompt for confirmation, shut down the local server, and replace the page
with a "you may close this window" message. Once the browser tab shows that
message, the application is stopped and it is safe to install.

> **Note:** Closing the browser tab alone does **not** stop the application. The
> local server keeps running in the background unless auto-shutdown has been
> enabled in configuration (it is off by default). Always use **Exit** or
> **Exit & Upgrade**.

---

## Knowing an Update Is Available

The application checks GitHub Releases shortly after launch and caches the
result. The outcome is shown as a pill next to the version number in the header:

| Pill | Meaning |
|------|---------|
| `LATEST VERSION` | You are on the newest published stable release. |
| `UPDATE AVAILABLE` | A newer release exists. A **Download** control appears next to the pill. |
| `PRE-RELEASE` | You are running a beta/RC build. |
| *(no pill)* | The check could not complete — offline, or update checks are disabled. |

### The Download dropdown

When the pill reads `UPDATE AVAILABLE`, a **Download** button appears in the
header. Clicking it starts the download that matches your operating system.
Clicking the caret next to it opens a dropdown containing:

- The new version number and the version you are currently running
- A **Release notes** link to that release on GitHub
- Three explicit download links: **macOS — Apple Silicon**, **macOS — Intel**,
  and **Windows**
- A reminder that the app must be quit before installing
- The **Exit & Upgrade** button

Use the explicit links rather than the one-click **Download** button when you
want to be certain which macOS build you get — browsers other than
Chromium-based ones do not report CPU architecture, so the one-click button
cannot always tell Apple Silicon from Intel on macOS.

> Older releases offered a single, architecture-agnostic macOS link. Current
> releases split macOS by architecture, so pick deliberately.

### If no pill appears

Update checking can be turned off (`updates.enabled: false` in `config.yaml`),
and it fails silently when the machine has no route to GitHub — common on
customer sites. In that case, check [{{LATEST_RELEASE_URL}}]({{LATEST_RELEASE_URL}})
manually and compare against the version shown in the header.

---

## Updating on macOS

### Step 1 — Identify your Mac's architecture

1. Open the **Apple menu** > **About This Mac**.
2. Read the hardware line:
   - A line labelled **Chip** (for example, "Apple M2 Pro") means **Apple Silicon** — download `{{MAC_ARM64_DMG}}`.
   - A line labelled **Processor** (for example, "2.6 GHz 6-Core Intel Core i7") means **Intel** — download `{{MAC_X64_DMG}}`.

Downloading the wrong build is not destructive, but the app will not launch.

### Step 2 — Download the DMG

Use the **macOS — Apple Silicon** or **macOS — Intel** link in the update
dropdown, or download it from [{{LATEST_RELEASE_URL}}]({{LATEST_RELEASE_URL}}).

Wait for the download to finish before continuing.

### Step 3 — Quit the application

Click **Exit & Upgrade** in the update dropdown, or **Exit** in the navigation
bar. Wait for the page to show that the application has stopped.

### Step 4 — Install

1. Double-click the downloaded `.dmg` to mount it.
2. Drag **VAST Reporter** onto the **Applications** shortcut in the DMG window.
3. When Finder asks what to do about the existing item, choose **Replace**.
   Do **not** choose "Keep Both" — that leaves you with two copies and it is
   easy to keep launching the old one.
4. Eject the DMG once the copy completes.

> **Do not run the app from the mounted DMG.** The application writes its
> configuration and reports into the folder that contains the app bundle, and a
> mounted DMG is read-only and disappears when ejected. Always copy to
> `/Applications` first.

### Step 5 — Launch

Open **VAST Reporter** from Applications. macOS will re-run its Gatekeeper
checks — see the next section.

---

## Gatekeeper After an Update

**Expect Gatekeeper to challenge you on every update, not just the first
install.**

The application is not signed with an Apple Developer certificate. After you
replace the bundle, the app on disk is new content that macOS has not approved
before, so it re-runs the same checks it ran on first install. This is normal
and is not a sign that the download is damaged.

The sequence is:

1. You launch the app and macOS shows a dialog saying the application
   **"was not opened"** because Apple could not verify it is free of malware.
2. Open **System Settings** > **Privacy & Security**.
3. Scroll to the **Security** section. A message names **VAST Reporter** as
   having been blocked, with an **Open Anyway** button. Click it.
4. Confirm at the follow-up prompt.
5. Authenticate with **Touch ID** or your macOS password.

The application then launches and opens your browser.

This approval applies to the specific copy of the app on disk. Replace that copy
with a newer release and you will do it again. There is currently no way to
avoid it short of Apple Developer signing and notarisation, which this project
does not do.

---

## Updating on Windows

### Step 1 — Download the ZIP

Use the **Windows** link in the update dropdown, or download `{{WIN_ZIP}}` from
[{{LATEST_RELEASE_URL}}]({{LATEST_RELEASE_URL}}). There is no installer — the
release is a ZIP you extract and run.

### Step 2 — Quit the application

Click **Exit & Upgrade** in the update dropdown, or **Exit** in the navigation
bar. Wait for the page to confirm the application has stopped. The running
`vast-reporter.exe` holds a lock on itself and its libraries, so extraction will
fail if you skip this.

### Step 3 — Extract

The ZIP contains a single top-level `VAST Reporter` folder. You have two
options:

- **Extract over the existing installation** (recommended). Extract to the
  parent of your current `VAST Reporter` folder and allow the files to be
  replaced. Your `config`, `reports`, `clusters`, and `logs` subfolders are left
  alone because they are not in the ZIP.
- **Extract to a new location.** This gives you a clean folder, but it starts
  with empty configuration. See
  [What Is Preserved Across Updates](#what-is-preserved-across-updates) for the
  folders to copy across from the old installation.

Delete or rename the old folder afterwards so you do not launch it by mistake.

### Step 4 — Launch

Run `vast-reporter.exe` from the updated folder.

Windows Defender SmartScreen may block it with "Windows protected your PC".
Click **More info** > **Run anyway**. As with macOS Gatekeeper, this can
reappear after an update because the executable is new, unsigned content — it is
not specific to first install.

---

## Verifying the Update

1. Relaunch the application. Your browser opens the dashboard automatically.
2. Check the version number in the header — it should read the version you just
   installed.
3. Check the pill beside it. Once the update check completes it should read
   `LATEST VERSION`.

If the header still shows the old version, you are almost certainly running the
old copy:

- **macOS:** confirm you chose **Replace** rather than "Keep Both", and that you
  launched from `/Applications` rather than a copy in `~/Downloads` or a still-
  mounted DMG.
- **Windows:** confirm you launched `vast-reporter.exe` from the folder you just
  extracted, not from an older copy or an old shortcut.

You can also confirm the version from a terminal:

```bash
# macOS
"/Applications/VAST Reporter.app/Contents/MacOS/vast-reporter" --version
```

```powershell
# Windows
& "C:\Program Files\VAST Reporter\vast-reporter.exe" --version
```

---

## What Is Preserved Across Updates

The application keeps all of its writable data **outside** the program itself,
in a data directory it creates next to the application:

| Platform | Data directory |
|----------|----------------|
| macOS | The folder that contains `VAST Reporter.app` — normally `/Applications` |
| Windows | The extracted `VAST Reporter` folder that contains `vast-reporter.exe` |

Inside that directory:

| Path | Contents |
|------|----------|
| `config/config.yaml` | Your runtime configuration |
| `config/cluster_profiles.json` | Saved cluster profiles |
| `config/device_library.json` | Custom entries in the hardware device library |
| `config/hardware_images/` | Hardware images you have uploaded to the library |
| `reports/` | Generated PDF and JSON reports (flat layout) |
| `clusters/<cluster>/` | Per-cluster reports, workflow output, and operation logs |
| `logs/` | Application log files |

### macOS

Everything above survives an update. Replacing `VAST Reporter.app` in
`/Applications` does not touch the sibling `config`, `reports`, `clusters`, and
`logs` folders, because none of that data lives inside the app bundle.

### Windows

Everything above survives **if you extract over the existing folder**, because
the ZIP contains only program files and does not include those subfolders.

If you extract to a **new** folder instead, the new installation starts empty.
Copy these from the old folder into the new one before launching:

```powershell
# Run from the parent folder containing both installations
Copy-Item ".\VAST Reporter.old\config"   ".\VAST Reporter\" -Recurse -Force
Copy-Item ".\VAST Reporter.old\reports"  ".\VAST Reporter\" -Recurse -Force
Copy-Item ".\VAST Reporter.old\clusters" ".\VAST Reporter\" -Recurse -Force
```

> **Windows caveat:** because the data directory *is* the installation folder,
> deleting the old folder deletes your configuration, profiles, and generated
> reports along with it. Copy anything you want to keep out first.

### First launch after an update

If `config/config.yaml` is missing, the application recreates it from the
template bundled with the new release. An existing `config.yaml` is never
overwritten, so settings you changed are kept — but new configuration keys added
by a release will not appear in it. To see what is new, compare your file
against the defaults shown on the **Advanced Configuration** page.

---

## Rolling Back to a Previous Version

Every published release stays available, so rolling back is just installing an
older artifact.

1. Go to [{{RELEASES_URL}}]({{RELEASES_URL}}) and expand the release you want.
2. Download the artifact for your platform and architecture from that release's
   **Assets** list.
3. **Quit the running application** — the same rule applies in both directions.
4. Install it exactly as described for
   [macOS](#updating-on-macos) or [Windows](#updating-on-windows), choosing
   **Replace** on macOS.
5. Expect Gatekeeper or SmartScreen to challenge the older build too; it is new
   content on disk as far as the operating system is concerned.

Your configuration, profiles, and reports are untouched by a rollback. Reports
already generated by the newer version remain readable — they are plain PDF and
JSON files.

---

## Troubleshooting

### "The item cannot be moved because it is in use" (macOS)

The old application is still running.

1. Switch to the browser tab and click **Exit** in the navigation bar.
2. If that tab is gone or unresponsive, open **Activity Monitor**, search for
   `VAST Reporter` (also check for `vast-reporter`), select it, and click the
   stop button to quit the process.
3. From a terminal, the equivalent is:

```bash
pkill -f "VAST Reporter"
```

4. Retry the drag to Applications.

### "The file is open in another program" / access denied (Windows)

The old `vast-reporter.exe` is still running.

1. Click **Exit** in the application's navigation bar.
2. If it is unresponsive, open **Task Manager**, find `vast-reporter.exe` on the
   **Details** tab, and end the task.
3. Retry the extraction.

### Gatekeeper keeps asking, or Open Anyway does not appear

- Make sure you are looking at **System Settings** > **Privacy & Security**,
  scrolled to the **Security** section. The **Open Anyway** button only shows up
  after you have attempted to launch the app and been blocked, and it can
  disappear after a while — attempt the launch again to bring it back.
- If you are prompted repeatedly for the *same* installed copy, confirm you are
  launching the copy in `/Applications` each time and not a second copy left in
  `~/Downloads` or on a mounted DMG. Each distinct copy is approved separately.
- Being asked again after each update is expected and not a fault. See
  [Gatekeeper After an Update](#gatekeeper-after-an-update).

### The browser page is blank, spinning, or shows "connection refused"

The tab is pointing at a server that is no longer running — usually a tab left
open from the version you just replaced.

1. Close the stale tab.
2. Launch the application again. It opens a fresh browser tab itself.

### "Port 5173 already in use" / the app opens on a different port

The application binds a local web server on port `5173` by default. If that port
is taken it automatically tries `5174` through `5180`, then `8080`, then `9090`,
and opens the browser on whichever it obtained — so the URL may not be the one
you expect. The console window prints the address it is running at.

Common cause during an update: the previous version is still running and holding
the port. Quit it first.

To find and stop whatever holds the port:

```bash
# macOS
lsof -ti:5173 | xargs kill
```

```powershell
# Windows
netstat -ano | findstr :5173
taskkill /PID <pid> /F
```

You can also choose a port explicitly:

```bash
vast-reporter --port 8888
```

If no port can be bound at all, the application prints the full list it tried
and exits; on Windows this is usually a Hyper-V or WSL2 reserved port range.

### The update pill never changes

The update check is cached in memory for about an hour after a successful check,
and it is skipped entirely when `updates.enabled` is `false`. Restart the
application to force a fresh check, or check
[{{LATEST_RELEASE_URL}}]({{LATEST_RELEASE_URL}}) directly.

---

## Updating a Source (Git) Installation

This section applies **only** if you run the application from a cloned
repository rather than from a released `.dmg` or `.zip`. Most users should not
be here.

1. Stop the running application (**Exit** in the navigation bar, or `Ctrl+C` in
   the terminal that launched it).
2. Pull the latest code:

```bash
cd <repository-root>
git pull
```

3. Reinstall dependencies, since releases add and update packages:

```bash
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install --upgrade -r requirements.txt
```

4. Verify and relaunch:

```bash
python3 src/main.py --version
python3 src/main.py
```

In a source checkout the data directory is the repository root, so `config/`,
`reports/`, `clusters/`, and `logs/` are already outside anything `git pull`
rewrites. `config/config.yaml` is not tracked by git and will not be overwritten.

---

**Version**: {{APP_VERSION}}
