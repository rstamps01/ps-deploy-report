---
name: Teleport connection option
overview: Add a selectable "Teleport (tsh)" connection mode that auto-launches tsh port-forwards for both the VMS API (443) and a CNode's SSH (22) to local ports, then reuses the existing paramiko/vnetmap/switch-proxy stack over those ports so a full report plus fresh vnetmap port mapping run in one pass.
todos:
  - id: ssh-port
    content: Add port/jump_port params to run_ssh_command + _paramiko_exec and SCP helpers (tool_manager, script_runner)
    status: completed
  - id: tunnel-mgr
    content: "Create src/utils/teleport_tunnel.py: TeleportTunnel subprocess manager with preflight (tsh present + logged in) and dual -L port forwards"
    status: completed
  - id: plumb-creds
    content: Thread teleport/teleport_node/teleport_user + ssh_host/ssh_port through generate_start, _extract_oneshot_credentials, _run_report_job, oneshot _setup_tunnel
    status: completed
  - id: ssh-consumers
    content: Make vnetmap_workflow, external_port_mapper, switch_config_workflow, oneshot switch jump, and health checker honor ssh_host/ssh_port when present
    status: completed
  - id: ui-config
    content: "Redesign Connection Settings UI: 3-way connection-mode radio (Tech Port / VMS Mgmt / Teleport) replacing the Tech Port checkbox; move Autofill to a toggle above Advanced (ON=fill+lock all six, OFF=usernames default+passwords empty, editable); Teleport node/user fields shown on select; keep proxy_jump in Advanced; teleport config block + profile persistence"
    status: completed
  - id: tests-docs
    content: Add/extend tests (teleport_tunnel, ssh_adapter port, app/oneshot wiring) and update CHANGELOG, TODO-ROADMAP, ADVANCED-OPERATIONS, config template
    status: completed
isProject: false
---

# Add a Teleport (tsh) Connection Option

## Goal

A third selectable connection mode (alongside Tech Port and VMS Mgmt/Direct-HTTPS). When selected, the app starts a `tsh` tunnel and runs both report generation (HTTPS API) and `vnetmap`/port-mapping (SSH) in a single pass. All new behavior is gated to Teleport mode; Tech Port and VMS Mgmt are unchanged. This enhancement also reworks the Connection Settings UI: the connection method becomes a centered 3-way radio (Tech Port / VMS Mgmt / Teleport) instead of the Advanced-menu Tech Port checkbox, and Autofill Passwords becomes a toggle above the Advanced menu that fills + locks credentials when on and leaves default usernames with empty, editable passwords when off.

## Why the previous attempts failed

The app derives both the API target and the SSH target from one `cluster_ip` and always SSHes to `<cluster_ip>:22`. A single manual `tsh`/socat forward can expose only one port on `<ip>`, so you could get the API (443) OR SSH (22), never both at once. Teleport mode fixes this by forwarding both ports to distinct local ports and teaching the SSH layer to use a non-22 port.

## Approach

Reuse the proven attempt-2 path. One `tsh` subprocess with two `-L` forwards off the chosen CNode's loopback (matches your working `-L ...:127.0.0.1:443` method, no socat, no sudo):

```
tsh ssh -L <apiPort>:127.0.0.1:443 -L <sshPort>:127.0.0.1:22 <user>@<teleport-node>
```

- API: set existing `tunnel_address = 127.0.0.1:<apiPort>` (already decouples API host in [src/api_handler.py](src/api_handler.py) via `self._api_host = tunnel_address or cluster_ip`).
- SSH: new `ssh_host`/`ssh_port` credentials = `127.0.0.1:<sshPort>`; the existing paramiko stack (vnetmap deploy/run, clush, switch proxy-jump) targets that instead of `cluster_ip:22`.

```mermaid
flowchart LR
  App["Reporter app (paramiko + requests)"] -->|"127.0.0.1:apiPort"| Tap["tsh -L forwards"]
  App -->|"127.0.0.1:sshPort"| Tap
  Tap -->|tsh proxy| CNode["CNode node (localhost:443 + :22)"]
  CNode -->|proxy_jump direct-tcpip :22| Switches["Leaf/Spine switches"]
```

## Changes

### Phase 1 - SSH port support (foundation)

- [src/utils/ssh_adapter.py](src/utils/ssh_adapter.py): add `port: int = 22` and `jump_port: int = 22` to `run_ssh_command` and thread into `_paramiko_exec` (the direct `client.connect(host, port=...)`, the jump `jump_client.connect(jump_host, port=jump_port, ...)`, and the OpenSSH `-p` path). Switch direct-tcpip target stays `(switch_ip, 22)`.
- [src/tool_manager.py](src/tool_manager.py) (`deploy_tool_to_cnode`) and [src/script_runner.py](src/script_runner.py) (paramiko SCP/download): add optional `port=22` on their `connect()` calls.

### Phase 2 - Teleport tunnel manager

- New `src/utils/teleport_tunnel.py`: `TeleportTunnel` class mirroring `VMSTunnel`'s lifecycle (`connect()`, `api_local_address`, `ssh_local_address`, `close()`). It launches the `tsh ssh -L ... -L ...` subprocess, waits for both local ports to accept TCP, and terminates the process on close.
- Preflight (actionable errors like existing pre-validation): verify `tsh` is on PATH and a session is active (`tsh status`); else raise "Run `tsh login` first". Allocate ephemeral local ports.

### Phase 3 - Credentials plumbing + tunnel wiring

- [src/app.py](src/app.py): in `generate_start` (~L483) and `_extract_oneshot_credentials` (~L2008) add `teleport` (bool), `teleport_node` (str), `teleport_user` (default `vastdata`). In `_run_report_job` (~L2446, where `VMSTunnel` is created) and [src/oneshot_runner.py](src/oneshot_runner.py) `_setup_tunnel` (~L1128): when `teleport` is set, create `TeleportTunnel`, set `tunnel_address = api_local_address`, and inject `ssh_host`/`ssh_port` from `ssh_local_address` into the credentials dict.
- Pin the CNode endpoint for port mapping to the tunnel (same pattern as the Tech-Port one-shot `cnode_ips = [cluster_ip]` at oneshot_runner ~L1650): in Teleport mode use the local SSH endpoint.

### Phase 4 - Honor ssh_host/ssh_port in SSH consumers (gated)

When `ssh_host`/`ssh_port` are present in credentials, use them instead of `cluster_ip`/22:

- [src/workflows/vnetmap_workflow.py](src/workflows/vnetmap_workflow.py): `host = self._credentials.get("cluster_ip")` (~L183) and the deploy/copy/run steps -> use ssh endpoint + pass `port`.
- [src/external_port_mapper.py](src/external_port_mapper.py): `_jump_kwargs()` (~L352) and the CNode clush `run_ssh_command(self.cnode_ip, ...)` (~L1092) -> jump/host become the local ssh endpoint with `jump_port`/`port`.
- [src/workflows/switch_config_workflow.py](src/workflows/switch_config_workflow.py) `_jump_kwargs()` (~L92), [src/oneshot_runner.py](src/oneshot_runner.py) `_switch_jump_kwargs()` (~L620), and the health checker `switch_ssh_config` jump -> same override.

### Phase 5 - UI + config

Applies to [frontend/templates/reporter.html](frontend/templates/reporter.html) and mirrored in [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html).

**5a. Connection-mode radio group (replaces the Tech Port checkbox).**

- Remove the `Tech Port Mode` checkbox from the Advanced menu (`#advancedMenu`, ~L94-98). `SSH Proxy Mode` (`proxy_jump`) stays in Advanced, unchanged (per decision).
- Add a centered 3-option radio group at the bottom of the Connection Settings tile (inside `#connSettingsDetails`, below the action bar): `Tech Port Mode`, `VMS Mgmt Mode`, `Teleport Mode` (name `conn_mode`; ids `modeTechPort` / `modeVmsMgmt` / `modeTeleport`). Default = `Tech Port Mode` (matches today's `tech_port` default-on). Semantics: Tech Port = existing SSH tunnel path; VMS Mgmt = direct HTTPS path; Teleport = the new method.
- Client-side mapping (no new backend field needed): in `getCredentials()` (~L1409) and the Run form body (~L2270) translate the selected radio to the existing booleans -- Tech Port -> `tech_port=true, teleport=false`; VMS Mgmt -> `tech_port=false, teleport=false`; Teleport -> `teleport=true, tech_port=false`. Backend keeps consuming `tech_port`/`teleport` (Phase 3).
- Teleport fields: when `Teleport Mode` is selected, reveal a Teleport node-target field (e.g. `PDX02-Vast01-c-128-4`) and a Teleport user field (default `vastdata`); hidden otherwise. Thread `teleport_node`/`teleport_user` through `getCredentials()` and the Run body.
- Update the help/info text (~L23-24, L39) to describe the three modes instead of "Advanced Menu -> Tech Port"; map config `ssh.tech_port_mode` (app.js ~L2886) to seed the default radio.

**5b. Autofill Passwords toggle (moves out of Advanced).**

- Remove `Autofill Passwords` from the Advanced menu (~L99-103). Add a labeled toggle switch directly above the `Advanced` button in the action bar, keeping the `#useDefaultCreds` id so existing profile/state wiring (~L1293, L2168, L2890) stays valid. Default ON (per decision).
- Rework `toggleDefaultCredentials()` (~L977):
  - ON: fill all six fields from `DEFAULT_CREDENTIALS`, then lock them (greyed/read-only).
  - OFF: set the three username fields to defaults (`support` / `vastdata` / `cumulus`), clear the three password fields, and unlock all six so the operator can edit then Save. (Change from today, which clears usernames too.)
- Locking mechanism: use `readonly` + a `locked` CSS class for the grey look (not `disabled`), because `disabled` inputs are dropped from `new FormData(form)` used by the legacy `/generate` path in [frontend/static/js/app.js](frontend/static/js/app.js) (~L284). The Reporter Run path builds its body from `getCredentials()` `.value` reads, so it is unaffected either way; `readonly` keeps both paths correct.

**5c. Config.**

- [config/config.yaml.template](config/config.yaml.template): add a `teleport:` block (`enabled: false`, `ssh_user: vastdata`, optional `tsh_path`); keep defaults off. Persist `teleport`/`teleport_node`/`teleport_user` and the selected mode in profiles `ALL_FIELDS` ([src/app.py](src/app.py) ~L1587) and profile load/save (`reporter.html` ~L1293-1357).

### Phase 6 - Tests + docs

- Tests: `tests/test_teleport_tunnel.py` (subprocess launch mocked, port-wait, preflight failure, close); extend [tests/test_ssh_adapter.py](tests/test_ssh_adapter.py)/`test_ssh_adapter_proxy.py` for `port`/`jump_port`; add Teleport-mode wiring tests to [tests/test_app.py](tests/test_app.py) and [tests/test_oneshot_runner.py](tests/test_oneshot_runner.py) (tunnel_address + ssh_host/ssh_port threaded; vnetmap/switch jump uses local endpoint).
- Docs: [CHANGELOG.md](CHANGELOG.md), [docs/TODO-ROADMAP.md](docs/TODO-ROADMAP.md), [docs/ADVANCED-OPERATIONS.md](docs/ADVANCED-OPERATIONS.md) (Teleport prerequisites: `tsh login` first, node target, behavior).

## Assumptions

- Operator has an authenticated `tsh` session; `tsh` is on PATH. The app shells out to `tsh` (no SSO/MFA handling).
- Operator supplies the CNode Teleport node target; SSH user defaults to `vastdata`, node password entered as today.
- Forwarding both `127.0.0.1:443` and `127.0.0.1:22` off the CNode (your working method) avoids needing the VMS VIP separately and avoids sudo/socat.

## Verification

- Unit: `python3 -m pytest tests/test_teleport_tunnel.py tests/test_ssh_adapter.py tests/test_app.py tests/test_oneshot_runner.py -q`; `flake8 src/ tests/`; `black --check --line-length 120 src/ tests/`.
- Manual smoke (requires `tsh login`): select Teleport, enter the CNode node target, run the reporter checklist with vnetmap enabled; confirm the report generates and `vnetmap` deploys + runs (no `port 22: Connection refused`).

## Out of scope

- App-driven `tsh login` / SSO. Auto node discovery via `tsh ls --search`. Forwarding to the VMS VIP from non-CNode node types.
