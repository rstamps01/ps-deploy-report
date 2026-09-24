# VAST As-Built Report Generator - Deployment Guide

**For VAST Professional Services Engineers**

This guide describes how the application is actually deployed and operated: what
runs where, what it stores, what it needs to reach on the network, and what its
security posture is. For step-by-step install instructions see the
[Installation Guide](INSTALLATION-GUIDE.md); for upgrades see the
[Update & Upgrade Guide](UPDATE-GUIDE.md).

## Table of Contents

1. [Deployment Model](#deployment-model)
2. [What Runs and Where](#what-runs-and-where)
3. [Runtime Data Locations](#runtime-data-locations)
4. [Network Requirements](#network-requirements)
5. [Security Posture](#security-posture)
6. [Running from Source](#running-from-source)
7. [Developer Mode](#developer-mode)
8. [Multi-User and Shared Hosts](#multi-user-and-shared-hosts)
9. [Not Supported](#not-supported)
10. [Operational Notes](#operational-notes)

---

## Deployment Model

There is exactly one supported deployment model: **a desktop application, run by
one engineer, on that engineer's own laptop or workstation.**

- You download a release artifact from [{{RELEASES_URL}}]({{RELEASES_URL}}) and
  run it. Nothing is installed system-wide — no services, no registry entries,
  no daemons, no scheduled tasks.
- On launch the application starts a **local** web server and opens your default
  browser to it. The web UI is the interface; the server exists only to serve
  that browser session.
- All connections to the VAST cluster are **outbound** from your machine. The
  application never listens for cluster traffic and never needs to be reachable
  from anywhere.
- When you are finished you click **Exit** in the navigation bar and the process
  ends. Nothing keeps running afterwards.

This is a field engineering tool, not a service. It is designed to be carried to
a customer site on a laptop, connected to a cluster, run once or twice, and shut
down.

---

## What Runs and Where

### The application process

A single self-contained process, packaged with PyInstaller. It bundles its own
Python runtime, libraries, templates, and assets — there is no dependency on a
Python installation on the host.

| Platform | Executable |
|----------|------------|
| macOS | `/Applications/VAST Reporter.app` |
| Windows | `vast-reporter.exe` inside the extracted `VAST Reporter` folder |

### The local web server

| Property | Value |
|----------|-------|
| Bind address | `127.0.0.1` (loopback only) |
| Default port | `5173` |
| Fallback ports | `5174`–`5180`, then `8080`, then `9090` |
| Override | `--port <number>` |

The server binds to loopback, so it is **not reachable from other machines** —
this is deliberate and there is no supported way to expose it. If the default
port is unavailable the application walks the fallback list and opens the
browser on whichever port it obtained; the console window prints the address it
is actually serving. If none can be bound it prints the list it tried and exits.

### Shutdown

Clicking **Exit** in the navigation bar (or **Exit & Upgrade** in the update
dropdown) posts to a shutdown endpoint that stops the server. `Ctrl+C` in the
launching console does the same.

An optional auto-shutdown watchdog can stop the server shortly after the browser
closes. It is **off by default** (`auto_shutdown.enabled` in `config.yaml`)
because browsers throttle timers in background tabs, which can make an
open-but-idle tab look closed. It never shuts down while a job is running.

---

## Runtime Data Locations

The application keeps all writable data in a **data directory** that it resolves
at startup, outside the program files themselves.

| Platform | Data directory |
|----------|----------------|
| macOS (packaged) | The folder containing `VAST Reporter.app` — normally `/Applications` |
| Windows (packaged) | The extracted `VAST Reporter` folder containing `vast-reporter.exe` |
| Running from source | The repository root |

Inside the data directory:

| Path | Contents |
|------|----------|
| `config/config.yaml` | Runtime configuration |
| `config/cluster_profiles.json` | Saved cluster connection profiles |
| `config/device_library.json` | Custom hardware device library entries |
| `config/hardware_images/` | Hardware images uploaded through the Library page |
| `reports/` | Generated PDF and JSON reports (flat layout) |
| `clusters/<cluster-key>/` | Per-cluster `reports/`, `output/`, and `logs/operations/` |
| `logs/vast_report_generator.log` | Rotating application log (10 MB, 5 backups) |

Notes:

- `config/config.yaml` is created from the bundled template on first launch if it
  does not exist. An existing file is never overwritten by an update.
- Report artifacts are segmented per cluster by default
  (`output.segment_by_cluster: true`). Because field clusters are frequently
  reached over the same tech-port address, a flat shared layout would
  intermingle artifacts from different clusters. Set the key to `false` to
  restore the legacy flat layout.
- Log paths in `config.yaml` are relative to the data directory unless you give
  an absolute path.
- On Windows the data directory *is* the installation folder. Deleting that
  folder deletes your configuration, profiles, and reports along with the
  program. See the [Update & Upgrade Guide](UPDATE-GUIDE.md) before replacing an
  installation.

---

## Network Requirements

### What the application needs to reach (all outbound)

| Destination | Protocol / Port | Purpose |
|-------------|-----------------|---------|
| VAST Management Service | HTTPS / 443 | Cluster configuration data collection |
| VAST CNodes / DNodes | SSH / 22 | Port mapping, health checks, script execution |
| Fabric switches | SSH / 22 | Switch configuration and topology collection |
| A CBox tech port | HTTPS + SSH | Tech Port mode: discovers the VMS address and tunnels API traffic over SSH |
| A Teleport proxy | HTTPS | Teleport mode: `tsh` forwards cluster API and SSH to local ports |
| `api.github.com` | HTTPS / 443 | Update check against the project's Releases |
| VAST support tool hosts | HTTPS / HTTP | Downloading deployment tools (Advanced Operations) |

Deployment tools (`vnetmap.py`, the Mellanox switch API helper, the VAST support
diagnostics tool, and `vperfsanity`) are downloaded from VAST-hosted support
storage — not from GitHub. GitHub is contacted only for the update check.

### What it does not need

- **No inbound network access.** Nothing connects *to* your machine.
- **No firewall rules, port forwarding, or reverse proxy.** The web server is
  loopback-only.
- **No DNS entries, certificates, or load balancers.** There is no hostname to
  publish.
- **No server, VM, or container infrastructure.**

### Working offline or air-gapped

The application works without internet access. The update check fails silently
(the version pill simply does not appear), and Advanced Operations cannot
download deployment tools — pre-cache those on a connected network first if you
need them on site.

---

## Security Posture

### Read-only cluster access

The application is a reporting tool and never modifies a cluster. The generic
API request helper in `api_handler` accepts **GET only** and raises on any other
method, so no data-collection path can issue a `POST`, `PUT`, `PATCH`, or
`DELETE`. The only writes to the cluster API are the authentication calls needed
to obtain a session or token. The full policy, including what is and is not
permitted, is documented in the repository at
`docs/development/READ_ONLY_VAST_API_POLICY.md`.

### Credential handling

- Credentials are supplied per run — through the web UI, environment variables
  (`VAST_USERNAME` / `VAST_PASSWORD` / `VAST_API_TOKEN`, and the `VAST_NODE_*`
  and `VAST_SWITCH_*` pairs for SSH), or an interactive prompt in CLI mode.
- During a run they are held in memory and passed to the API and SSH layers.
  They are not written into generated PDF or JSON reports.
- **Saved cluster profiles are the exception.** If you use the profile feature,
  the profile — including the cluster password, SSH passwords, and any API token
  — is written in plain text to `config/cluster_profiles.json`. That file is
  protected only by the file permissions of your user account. Treat the data
  directory as sensitive, do not save profiles on a shared machine, and delete
  profiles you no longer need.

### Log sanitization

A logging filter redacts credential-shaped content before it reaches the console
or the log file: a recognised key (`password`, `token`, `secret`, `auth`,
`credential`, and similar) followed by a separator and a value is replaced with a
`KEY_[REDACTED]` marker. Narrative text that merely mentions those words is left
readable. Sanitization is controlled by `security.sanitize_logs` and
`security.mask_sensitive_data` in `config.yaml`.

### TLS to the cluster

`api.verify_ssl` controls certificate verification for cluster API calls. The
shipped template sets it to `false`, because VAST clusters are routinely
deployed with self-signed management certificates and verification would fail on
most field engagements. Set it to `true` where the cluster presents a
certificate your machine trusts.

### Code signing

Release artifacts are **not** signed. macOS Gatekeeper and Windows SmartScreen
will challenge the application on first launch and again after every update.
Approving it is expected; see the
[Update & Upgrade Guide](UPDATE-GUIDE.md#gatekeeper-after-an-update).

### Telemetry

Local-only usage metrics exist for a "time saved" dashboard figure. They are
**opt-in and off by default**, store only an anonymous install identifier and
coarse event counts, and are not transmitted anywhere in this release.

---

## Running from Source

For contributors, or when you need a build that is not yet released.

### Prerequisites

- Python 3.10 or later
- Git

### Setup

1. Clone the repository and enter it:

```bash
git clone https://github.com/rstamps01/ps-deploy-report.git
cd ps-deploy-report
```

2. Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4. Launch the web UI:

```bash
python3 src/main.py
```

### Other entry points

| Command | Behaviour |
|---------|-----------|
| `python3 src/main.py` | Web UI (default) |
| `python3 src/main.py --gui` | Web UI, explicitly |
| `python3 src/main.py --cli --cluster <ip> --output ./reports` | Command-line report generation |
| `python3 src/main.py --from-json <path>` | Rebuild a PDF from a saved JSON intermediate, with no cluster access |
| `python3 src/main.py --version` | Print the version and exit |
| `python3 src/main.py --port <number>` | Override the web UI port |

In a source checkout the data directory is the repository root, so `config/`,
`reports/`, `clusters/`, and `logs/` live there. `config/config.yaml` is not
tracked by git.

---

## Developer Mode

Passing `--dev-mode` at launch unlocks the **Advanced Operations** surface:
step-by-step SSH workflows, deployment-tool management and remote deployment,
result bundling, and the one-shot orchestrator.

Three pages are gated behind the flag — **Advanced Ops**, **Health Check**, and
**Config (YAML)**. Without it they are hidden from the navigation menu and
return `403` if requested directly.

```bash
# From source
python3 src/main.py --dev-mode

# Packaged macOS build
"/Applications/VAST Reporter.app/Contents/MacOS/vast-reporter" --dev-mode
```

```powershell
# Packaged Windows build
& ".\VAST Reporter\vast-reporter.exe" --dev-mode
```

These workflows run scripts on cluster nodes over SSH. They are gated behind the
flag deliberately — enable it only when you intend to use them.

---

## Multi-User and Shared Hosts

The application is **single-user per machine**. It has no user accounts, no
authentication on the web UI, and no per-user data separation: whoever can reach
the loopback port has full access to the running instance, and everything is
stored in one data directory owned by whoever installed it.

If more than one engineer needs the tool, each installs their own copy on their
own machine.

Two consequences worth stating plainly for shared or multi-admin hosts:

- Anyone with a local account on the machine that can read the data directory
  can read saved cluster profiles, including their plaintext passwords.
- Two instances cannot share a port. A second instance launched on the same
  machine will fall back to the next available port rather than fail, so it is
  easy to end up with two servers running and a browser tab pointed at the wrong
  one.

---

## Not Supported

These come up regularly. None of them exist today, and none are partially
implemented:

| Request | Status |
|---------|--------|
| Docker / container image | Not supported. There is no Dockerfile or Compose file for the application. |
| systemd service / Windows service / launchd daemon | Not supported. There is no unit file, and the application is not designed to run headless and unattended. |
| Hosting the web UI for a team | Not supported. The server binds loopback only and has no authentication or authorization. |
| Multi-tenant or multi-user hosting | Not supported. No user model exists. |
| Reverse proxy / nginx front end | Not supported and not needed. |
| Scheduled or unattended report runs | Not supported as a product feature. CLI mode exists and can be scripted, but credential handling, prompts, and error recovery assume an operator is present. |
| Centralized log shipping, Prometheus metrics, alerting | Not supported. Logs are local files; no metrics endpoint is exposed. |
| Signed / notarized installers | Not currently produced. Expect Gatekeeper and SmartScreen prompts. |

If you need something in this table, raise it as an enhancement request rather
than building around it — the loopback binding and the absence of
authentication mean the workarounds are genuinely unsafe.

---

## Operational Notes

### Backing up

Everything worth keeping is in the data directory. Copy `config/`, `reports/`,
and `clusters/` to preserve configuration, profiles, and generated output. There
is no database and no state outside the filesystem.

### Log growth

The application log rotates at 10 MB with 5 backups
(`logging.rotation_size` and `logging.backup_count`). Advanced Operations logs
are capped separately (`logging.ops_log_max_bytes`, default 1 GB); when the cap
is reached the oldest are purged automatically, dropping the fraction set by
`logging.ops_log_purge_fraction`.

### Uninstalling

Remove the application bundle or folder. See the
[Uninstall Guide](UNINSTALL-GUIDE.md) — and note that on Windows the data
directory is inside the installation folder, so save anything you want to keep
before deleting it.

---

**Version**: {{APP_VERSION}}
