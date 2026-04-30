# TP-1 — Tech Port VMS Discovery fails on non-10/8 management plane

## Reproduction record

| | |
|---|---|
| **Date / time** | 2026-04-29 13:49:16 PT (20:49:16 UTC) |
| **Cluster** | `mammoth` — VAST OS 5.4.3 / build 12.13.18-1687799 |
| **Entry point** | Reporter page (`/reporter`) -> Switch Placement Editor modal -> "Run Discovery" |
| **Backend hit** | `POST /api/discover` -> `VMSTunnel.connect()` -> `discover_vms_management_ip()` |
| **Result** | HTTP 500 — `VMSDiscoveryError: Could not parse management IP from ip addr output: ''` |
| **Tester** | Reproduced live via cursor-ide-browser MCP against the running dev server (`python3 src/main.py --gui --dev-mode` on `127.0.0.1:5173`) |
| **Cluster reachability** | TCP/22 open, ICMP < 1 ms, ARP live, OpenSSH_8.0, motd healthy (`State: ONLINE`, RAIDs healthy, 70-day uptime) |

## Severity

**High.** Tech Port mode is the sole post-install entry path from a directly cabled CNode tech port — it is unusable on any cluster whose management plane is in `172.16/12` or `192.168/16`. Affects:

- `/api/discover` (Reporter Discover button) — *demonstrated here*
- `/generate` (Reporter, Tech Port on) — same `VMSTunnel.connect()` path
- `oneshot_runner.py` Tech Port branch (Test Suite tile) — same path

Not affected: CLI `python3 src/main.py --cluster <ip>`, or any path that uses Tech Port off + direct HTTPS.

## Root cause (two lines)

`vms_tunnel.py` Step 2 has `10.0.0.0/8` baked into both the SSH command and the parser:

```172:172:src/utils/vms_tunnel.py
    ip_cmd = "ip addr show | grep 'inet 10\\.' | head -5"
```

```90:90:src/utils/vms_tunnel.py
        match = re.match(r"inet\s+(10\.\d{1,3}\.\d{1,3}\.\d{1,3})/", stripped)
```

If the VMS CNode has no `10.x.x.x` address (true for `mammoth` and any `172.16/12`-managed cluster), the remote `grep` returns nothing and `parse_management_ip("")` returns `None`. `discover_vms_management_ip` then raises `VMSDiscoveryError("Could not parse management IP from ip addr output: ''")`.

For `mammoth`, the VMS CNode (`172.16.128.4`) carries no `10.x.x.x` anywhere — its management VIP lives on `bond0:m` at `172.16.128.4/18`. That's the same IP `/etc/motd` already reported as `VMS:`, so Step 2 isn't even necessary on this OS revision.

## Server-side trace (from 05-server-log.txt)

```
2026-04-29 13:49:16 - utils.vms_tunnel - INFO - Discovering VMS via SSH to 192.168.2.2 ...
2026-04-29 13:49:16 - utils.vms_tunnel - INFO - VMS internal IP: 172.16.128.4         <- Step 1 OK
2026-04-29 13:49:16 - paramiko.transport - INFO - Connected (version 2.0, client OpenSSH_8.0)
2026-04-29 13:49:16 - paramiko.transport - INFO - Authentication (password) successful!
2026-04-29 13:49:16 - paramiko.transport - INFO - Connected (version 2.0, client OpenSSH_8.0)
2026-04-29 13:49:16 - paramiko.transport - INFO - Authentication (password) successful!
2026-04-29 13:49:16 - utils.vms_tunnel - INFO - VMS API tunnel closed                  <- cleanup after raise
2026-04-29 13:49:16 - werkzeug - INFO - 127.0.0.1 - - "POST /api/discover HTTP/1.1" 500 -
```

Notable: there is no `INFO - VMS management IP: ...` line, which would only appear if Step 2 had succeeded. End-to-end latency from request to failure: ~1 second.

## What the user sees (from 02-post-click-error.png)

A red banner inside the Switch Placement Editor modal:

> Error: Could not parse management IP from ip addr output: ''

No console diagnostic, no toast outside the modal, no stack trace, no breadcrumb suggesting Tech Port discovery vs. credentials vs. cluster state. From the user's vantage, this is a black-box failure — they cannot tell whether:
- the tech-port cable is bad,
- the password is wrong,
- the cluster is not yet clustered,
- the VMS container hasn't come up,
- or the parser has a bug.

This UX gap is itself a finding worth tracking inside TP-1.

## Layered probes that ruled out everything except the parser

(Run from this host before opening the UI; reproducible via the harness in [src/utils/vms_tunnel.py](src/utils/vms_tunnel.py))

| Layer | Status | Evidence |
|---|---|---|
| L1 — Tech port reachability | OK | `en20: 192.168.2.254/24`; ARP live; ICMP < 1 ms; TCP/22 open |
| L2 — SSH transport | OK | `OpenSSH_8.0`, password auth as `vastdata` succeeds |
| L3a — Cluster health | OK | motd: `mammoth ONLINE`, RAIDs healthy, 70-day uptime |
| L3b — motd "VMS:" parse | OK | `parse_find_vms_output` returns `172.16.128.4` |
| L3c — clush fallback | OK | confirms `vast_vms` runs on `172.16.128.4` only |
| L3d — Cluster topology | OK | `local.cfg`: `cnodesub0 172.16.128.[1-12]` / `dnodesub0 172.16.128.[100-107]` |
| L4 — SSH-jump 192.168.2.2 -> 172.16.128.4 | OK | paramiko channel established; full `ip addr` payload returned |
| **L4 parse** | FAIL | `grep 'inet 10\.'` strips everything -> parser sees `''` |

## Why CI didn't catch it

`tests/test_vms_tunnel.py` only fixtures a `10/8` `ip addr` payload. There is no `172.16/12` or `192.168/16` reference data anywhere in the repo, so the regression doesn't fire in CI. Adding a `mammoth`-derived fixture closes that gap.

## Proposed fix (TP-1, scoped, backward-compatible)

1. Drop the remote `grep 'inet 10\.'` pre-filter; pass full `ip addr show` output to the parser.
2. Widen `parse_management_ip` to all RFC1918 (`10/8`, `172.16/12`, `192.168/16`) with deterministic selection priority — `<iface>:m` alias first, then `scope global` non-secondary, then first match.
3. **Step-2 short-circuit:** before SSH-hopping, probe TCP/443 to the discovered internal IP through the existing SSH transport. If 443 is open, reuse it as the management IP and skip the `ip addr` hop. Resolves `mammoth` directly with the motd-discovered IP.
4. Replace the empty-string error message with one listing candidates seen and rejected.
5. *(Optional)* `config/config.yaml.template` -> `network.management_subnets:` operator override (defaults: the three RFC1918 ranges).
6. *(Optional, ship independently for telemetry)* INFO-log the motd VMS line, candidate set, selected mgmt IP, and short-circuit decision so future field failures resolve from one screenshot.

Tests:
- New fixture `IP_ADDR_172_16_NO_10` derived from `mammoth`'s captured payload.
- Unit tests pinning selection priority across `10/8`, `172.16/12`, `192.168/16`, `:m` alias, secondary, docker0.
- Mocked-paramiko test for the 443 short-circuit and its fallback.
- Mocked `VMSTunnel.connect` test in `tests/test_app.py` asserting `/api/discover?tech_port=true` returns 200 on the new payload.

## Field workaround today

None clean from the tech port — the laptop physically cannot route to `172.16.128.0/18` from `192.168.2.0/24` without the tunnel. Off-tech-port runs from a host already on the management network work as long as Tech Port is off. Until TP-1 ships, post-install validation on `mammoth` blocks first-contact via the tech port.

## Artifacts in this folder

| File | Description |
|---|---|
| `01-pre-click.png` | Reporter form filled with all custom values, Tech Port on, Autofill off. Final state required one MCP refill of Node User and one of Node Password — see `07-ui-behavior-note.md`. |
| `02-post-click-error.png` | Switch Placement Editor modal showing the `VMSDiscoveryError` text. |
| `03-network-request.json` | `/api/discover` POST -> 500 + preceding session requests. |
| `04-console.txt` | Browser console (no errors raised by the UI itself; MCP-instrumentation noise only). |
| `05-server-log.txt` | 9-line Flask + paramiko + `vms_tunnel` log delta covering the failure. |
| `06-summary.md` | This file. |
| `07-ui-behavior-note.md` | Two side-finding UI defects observed during the repro (programmatic value not rendering; password cleared when user-field re-typed). Independent of TP-1 root cause. |

## Side-findings (not TP-1, but observed during this reproduction)

During the MCP-driven form fill, the tester observed (and intervened to fix) two UI-layer issues separate from the parser bug:

1. **Node User field's DOM `value` was set programmatically (snapshot confirmed `value: vastdata`) but did not visibly render until a focus/input event** — making it look empty in screenshots.
2. **Re-filling Node User cleared the previously populated Node Password field** — likely a side effect of an autofill change-listener at [frontend/templates/reporter.html](frontend/templates/reporter.html) ~L985. The tester took manual control mid-run to repopulate both fields.

Neither affects the TP-1 reproduction (paramiko authenticated successfully twice in `05-server-log.txt`, confirming the credentials reached the cluster). Both warrant separate tickets — see [07-ui-behavior-note.md](07-ui-behavior-note.md) for full detail and proposed RPT-VALIDATION-1 / RPT-VALIDATION-2 follow-ups.

## Open follow-ups

1. **Release vehicle** — patch as `v1.5.7` now, or fold into `v1.6.0`?
2. **Scope** — minimal (items 1-4) or full (1-6)?
3. **Diagnostic logging (item 6) on its own** — ship independently of the fix? Safe; would have made this a 30-second triage.
4. **Track-as** — open Jira `TP-1` linked to roadmap, or roadmap-only?
5. **UI side-findings** — file RPT-VALIDATION-1 and RPT-VALIDATION-2 from `07-ui-behavior-note.md`? Both are separately fixable and should not block v1.5.7.
