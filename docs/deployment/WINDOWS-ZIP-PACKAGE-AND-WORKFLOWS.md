# Windows ZIP Package Review and Installation/Uninstallation Workflows

**Applies to:** `VAST-Reporter-vX.Y.Z-win.zip` (e.g. `VAST-Reporter-v1.4.2-win.zip`) from [GitHub Releases](https://github.com/rstamps01/ps-deploy-report/releases).

---

## 1. Windows ZIP Package Contents

### What the ZIP contains

| Item | Description |
|------|-------------|
| **Single top-level folder** | `VAST Reporter/` |
| **Entry point** | `vast-reporter.exe` (PyInstaller one-folder bundle) |
| **Runtime** | Embedded Python runtime, DLLs, and dependencies (no separate Python install required) |
| **Bundled data** | `frontend/` (templates, static), `config/` (default YAML, device_library, cluster_profiles), `assets/` (diagrams, hardware_images), `docs/` (deployment, API-REFERENCE, EBOX_API_V7_DISCOVERY), `README.md`, `CHANGELOG.md` |
| **Writable data (created at first run)** | Stored **inside** the same `VAST Reporter` folder: `reports/`, `config/` (user config), `logs/`, and any cluster profiles / device library updates. See `get_data_dir()` in `src/utils/__init__.py`: on Windows frozen build it is the executable’s parent directory. |

### What the package does **not** do

- No MSI or installer; no registry keys, no Start Menu or Desktop shortcuts, no services.
- No system-wide install; the app is fully portable and self-contained in the extracted folder.

### Build source

- Produced by `packaging/build-windows.ps1`: PyInstaller runs `packaging/vast-reporter.spec`, then the script zips the `dist/VAST Reporter` directory as `VAST-Reporter-vX.Y.Z-win.zip` (version read from `src/app.py`).

---

## 2. Implemented Installation Workflow (ZIP Package)

**Reference:** [INSTALLATION-GUIDE.md — Windows Installation](INSTALLATION-GUIDE.md#windows-installation).

| Step | Action |
|------|--------|
| 1. Download | Get `VAST-Reporter-vX.Y.Z-win.zip` from GitHub Releases (latest or specific version). |
| 2. Extract | Right-click the ZIP → **Extract All…** and choose a destination (e.g. `C:\Program Files\VAST Reporter` or `%USERPROFILE%\VAST Reporter`). |
| 3. Launch | Double-click `vast-reporter.exe` inside the extracted `VAST Reporter` folder. If Windows Defender SmartScreen blocks it: **More info** → **Run anyway**. The app starts and opens the default browser at `http://127.0.0.1:5173`. |

**Prerequisites (from docs):** Windows 10 or later, x64, ~100 MB disk space.

**Post-install:** No further install steps. First run creates `reports/`, `config/`, `logs/` under the same `VAST Reporter` folder. Cluster profiles and configuration are stored there.

---

## 3. Implemented Uninstallation Workflow

### 3.1 ZIP package (extract-and-run) uninstall

There is **no dedicated uninstaller** for the ZIP package. Uninstall is manual:

| Step | Action |
|------|--------|
| 1. Exit the app | Close the browser tab and any console window, or stop the process (e.g. Task Manager → end `vast-reporter.exe`). |
| 2. Remove the folder | Delete the entire `VAST Reporter` folder (e.g. `C:\Program Files\VAST Reporter` or wherever it was extracted). This removes the app and all local data (reports, config, profiles, logs). |

Optional: remove shortcuts if the user created them (e.g. Start Menu or Desktop); the app does not create them by default.

### 3.2 Developer/source install uninstall

For a **source/developer** install (clone + venv + `pip install -r requirements.txt`), the project provides:

- **Automated:** [UNINSTALL-GUIDE.md — Windows Automated Uninstall](UNINSTALL-GUIDE.md#windows-automated-uninstall): run `docs/deployment/uninstall-windows.ps1`. It locates the install (default `%USERPROFILE%\vast-asbuilt-reporter` or current directory with `src\main.py`), offers backup, then removes the install directory and optionally cleans PATH, VAST_* env vars, Start Menu shortcuts, and scheduled tasks.
- **Manual:** [UNINSTALL-GUIDE.md — Windows Manual Uninstall](UNINSTALL-GUIDE.md#windows-manual-uninstall): stop processes, deactivate venv, remove install directory, optionally clean PATH/env vars, shortcuts, and scheduled tasks.

The scripts **install-windows.ps1** and **uninstall-windows.ps1** in `docs/deployment/` target this **developer/source** workflow (venv, `src/`, `requirements.txt`), not the ZIP package.

---

## 4. Summary Table

| Workflow | Installation | Uninstallation |
|----------|--------------|----------------|
| **ZIP package** | Download → Extract All → Run `vast-reporter.exe`. No registry/shortcuts. | Exit app → Delete the `VAST Reporter` folder. |
| **Developer/source** | Use `docs/deployment/install-windows.ps1` (or follow INSTALLATION-GUIDE developer section: clone, venv, pip). | Use `docs/deployment/uninstall-windows.ps1` or manual steps in UNINSTALL-GUIDE. |

---

## 5. References

- **Build:** `packaging/build-windows.ps1`, `packaging/vast-reporter.spec`
- **Install (ZIP):** [INSTALLATION-GUIDE.md — Windows Installation](INSTALLATION-GUIDE.md#windows-installation)
- **Uninstall (ZIP):** Delete install folder; no separate doc section for “ZIP uninstall”
- **Uninstall (source):** [UNINSTALL-GUIDE.md](UNINSTALL-GUIDE.md) (automated and manual Windows), `docs/deployment/uninstall-windows.ps1`
- **Data directory (frozen):** `src/utils/__init__.py` → `get_data_dir()` (Windows: same as exe parent)
