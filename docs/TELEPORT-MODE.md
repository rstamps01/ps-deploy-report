# Teleport Mode (Beta)

Teleport Mode lets the VAST As-Built Reporter generate a full as-built report — including `vnetmap`/port mapping — against a cluster that is reachable only through a [Teleport](https://goteleport.com/) proxy. It connects through the Teleport CLI (`tsh`), forwarding the cluster API (TCP 443) and CNode SSH (TCP 22) to local ephemeral ports at the same time.

> **Beta:** Teleport Mode is under active development. It is flagged as a Beta Feature in the UI. Behavior and configuration may change between releases.

---

## How it works

Selecting **Teleport Mode** launches a single `tsh ssh` subprocess against the chosen node with two `-L` forwards off the CNode's loopback:

```
tsh ssh -L <apiPort>:127.0.0.1:443 -L <sshPort>:127.0.0.1:22 -l <user> <node> <keepalive>
```

This exposes the VMS REST API (443) and the CNode's SSH (22) on local ephemeral ports simultaneously. The forwarded local API port feeds the API handler; the forwarded local SSH endpoint is used by every SSH-dependent workflow (vnetmap deploy/run, `clush`, and the switch proxy-jump).

---

## Prerequisites

1. **Install the Teleport CLI (`tsh`).** Download it from your Teleport cluster's web UI or from [goteleport.com/download](https://goteleport.com/download/). `tsh` is an external dependency — it is **not** bundled with the Reporter app.
2. **Log in.** Complete an SSO/MFA login from a terminal at least once:
   ```
   tsh login --proxy=<your-teleport-proxy>:443
   ```
   SSO/MFA is handled entirely by `tsh`; the Reporter never sees your credentials.
3. **Local port forwarding.** Your Teleport role must permit local port forwarding.

---

## tsh discovery (no PATH editing required)

Packaged desktop apps launched from Finder (macOS) or Explorer (Windows) inherit a **restricted `PATH`** that usually omits the directory where `tsh` is installed (e.g. `/usr/local/bin`). Earlier versions failed with:

```
Error: Teleport CLI 'tsh' not found on PATH.
```

The app now resolves `tsh` automatically, in this order:

1. An explicit path saved in `config.yaml` (`teleport.tsh_path`).
2. `tsh` on the current `PATH` (the app also augments `PATH` at startup with common bin directories).
3. Well-known install locations for your platform:
   - **macOS:** `/usr/local/bin/tsh`, `/opt/homebrew/bin/tsh`, `/opt/teleport/bin/tsh`, `~/.local/bin/tsh`
   - **Windows:** `%ProgramFiles%\Teleport\tsh.exe`, `%ProgramFiles(x86)%\Teleport\tsh.exe`, `%LOCALAPPDATA%\Programs\teleport\tsh.exe`, `%USERPROFILE%\scoop\shims\tsh.exe`
   - **Linux:** `/usr/local/bin/tsh`, `/usr/bin/tsh`, `~/.local/bin/tsh`

### Status pill

A status pill shows the current state in two places:

- **Reporter page** — above the Teleport Mode option in the Connection Settings tile.
- **Advanced Configuration -> Teleport Settings.**

| Pill | Meaning |
| --- | --- |
| Green **tsh Installed** | `tsh` was found (via config, PATH, or a known location). |
| Yellow **Install tsh** | `tsh` could not be found. Install it, or set a custom path (below). |

### Teleport Settings (Advanced Configuration)

Open **Advanced Configuration -> Teleport Settings** (the last section) to manage the path:

- **tsh Path** — shows the discovered path (blank if not found). Editable.
- **Run Discovery** — validates the current field value (or auto-discovers when blank) and, on success, saves the absolute path to `config.yaml` (`teleport.tsh_path`) for future connections.

If auto-discovery fails (non-standard install location), type the full path to the `tsh` binary into the field and click **Run Discovery** to validate and save it.

---

## Connecting

1. On the Reporter page, select **Teleport Mode**.
2. In **Cluster IP**, enter the cluster's VMS management VIP (e.g. `10.143.10.100`) — **not** `127.0.0.1` — so the API forward terminates on the VMS and is reachable from any node.
3. In **Teleport Node**, enter the target node (see formats below).
4. In **Teleport User**, keep the default `vastdata` unless your environment differs.
5. Run Pre-Validation or Generate the report as usual.

The tool runs a preflight check (`tsh` present + active session) before launching and reports an actionable error if either is missing.

### Teleport Node formats

The **Teleport Node** field accepts any of the following. The app resolves your input against the Teleport inventory (`tsh ls`) to a single node before dialing, and returns an actionable candidate list on no-match or ambiguity.

| Input | Example |
| --- | --- |
| Bare hostname | `Rack-DB3-U15-DN1` |
| Node ID (UUID) | `00b2a3f1-a211-4a48-952e-dc83ddca4cb0` |
| `user@host` | `vastdata@Rack-DB3-U15-DN1` |
| Single `key=value` label | `hostname=Rack-DB3-U15-DN1` |
| Multiple labels (comma-separated **AND**) | `cluster_name=SFO-Cisco-AI-Pod,hostname=Rack-DB3-U15-DN1` |

**Multiple labels are combined with AND** — every `key=value` pair must match the same node. If a combination matches nothing, one of the labels does not exist on the intended node. When in doubt, use the **bare unique hostname**, which is the simplest reliable input.

Common label keys in Teleport inventories include `hostname`, `cluster_name`, `cluster_psnt`, and `id`. Label names are environment-specific — check the candidate list in the error message (or `tsh ls --format=json`) to see which labels your nodes actually carry.

---

## Configuration reference (`config/config.yaml`)

```yaml
teleport:
  # Optional explicit path to the tsh binary. Leave blank to auto-discover.
  # Set automatically by Advanced Configuration -> Teleport Settings -> Run Discovery.
  tsh_path: ""

  # When true (default), if no active Teleport session is found at launch the
  # app runs `tsh login` so the SSO browser window opens for in-place re-auth.
  auto_login: true

  # Optional Teleport proxy (host:port) passed to `tsh login`. Leave blank to
  # reuse the proxy from your existing local tsh profile.
  proxy: ""
```

---

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Yellow **Install tsh** pill; "tsh not found" error | `tsh` is not installed or is in a non-standard location. Install Teleport, or enter the full path in **Teleport Settings** and click **Run Discovery**. |
| "No active Teleport session" | Your `tsh` session expired. The app attempts an interactive `tsh login` automatically (when `auto_login` is on); otherwise run `tsh login --proxy=<proxy>` in a terminal. |
| "No Teleport node matched ..." | Your node input didn't match a single node. Use the bare unique hostname, or verify label keys against the candidate list shown in the error. |
| API calls time out in Teleport Mode | Ensure **Cluster IP** is the VMS management VIP, not `127.0.0.1`, so the API forward reaches the VMS from any node. |

---

## See also

- [Advanced Operations Guide](ADVANCED-OPERATIONS.md) — Connection Settings and the full Reporter workflow.
- [Teleport documentation](https://goteleport.com/docs/) — installing and logging in with `tsh`.
