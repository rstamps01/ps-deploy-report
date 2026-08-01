# Release Notes — v1.5.8

**Date:** 2026-06-25
**Status:** Released

Production release promoting the prior `1.5.8-beta`. It delivers the Teleport
(Beta) connection mode, switch-identity disambiguation, a logical
network-diagram rendering overhaul, Reporter Library built-in device additions,
a health-check bundle fix, QP-1/2/3 report and UI enhancements, Intel macOS
build support, and the Tech-Port tunnel reliability fix.

> Supersedes `RELEASE_NOTES_v1.5.8-beta.md`, which is retained as historical
> record of the beta cut.

---

## Highlights

- **Logical Network Diagram overhaul** — Complete rendering refresh with
  subnet-aware coloring, mis-cabling detection, bezier-curve link routing,
  spine/IPL classification, affinity-based rack pagination, and improved
  cross-rack connection visibility.
- **Switch-identity disambiguation** — Switches are keyed by a stable
  `switch_id` (mgmt IP / GUID) with human-readable `display_name`, so
  identically named switches no longer collide in the UI, reports, or diagrams.
- **Teleport (tsh) connection mode — Beta** — New third connection method that
  tunnels the cluster API (443) and CNode SSH (22) through a Teleport proxy so
  reports and `vnetmap` work against Teleport-only clusters. Shipped as a
  **Beta feature** (flagged in the UI) pending further field validation.
- **Reporter Library built-in devices** — `mqm8700-hs2f`, `nexus_c9332d_gx2b`,
  and `cisco_ebox` ship as built-in devices with bundled bezel images; missing
  built-in image references reconciled so rack diagrams stop falling back to a
  generic bezel.
- **Health-check bundle fix** — Cluster Health Check Results now land in the
  per-cluster bundle path and report OK/SKIPPED in `SUMMARY.md` instead of
  "MISSING".
- **Intel macOS build support** — Release pipeline produces separate `.dmg`
  artifacts for Apple Silicon (arm64) and Intel (x86_64).
- **Tech-Port tunnel reliability** — Two-hop SSH architecture fixes the S3
  gateway interception that blocked authentication on clusters using
  virtual-host routing.

---

## New Features

### Teleport (tsh) Connection Mode — Beta

> **Beta:** This feature is functional and shipped in v1.5.8, but is still
> undergoing field validation and hardening. The Reporter UI marks it with a
> "Beta Feature" badge above the Teleport Mode option. Report any issues
> against the v1.5.8 milestone.

- Third connection mode in the Reporter's Connection Settings tile (alongside
  Tech Port Mode and VMS Mgmt Mode), backed by `src/utils/teleport_tunnel.py`.
- A single `tsh ssh` subprocess opens dual `-L` forwards off the chosen CNode —
  API (443) and CNode SSH (22) — so the VMS REST API and CNode SSH are both
  available locally at once. Full reports including `vnetmap`/port mapping work
  against Teleport-only clusters.
- The Teleport Node field accepts any unique identifier (hostname, node ID,
  `cluster_name`, `cluster_psnt`, `key=value` label, or `user@…`) and resolves
  it against `tsh ls --format=json`; ambiguous cluster targets auto-pick an
  online CNode, and unresolvable input fails fast with the candidate nodes
  listed.
- Auto-runs `tsh login` (opening the SSO window) when the session has expired.
- Configurable via a new `teleport` config block (`enabled`, `ssh_user`,
  `tsh_path`, `auto_login`, `proxy`, `login_timeout`). Requires `tsh` on PATH.

### Network Diagram Visualization (NET-2A through NET-5)

| ID | Feature |
|----|---------|
| NET-2A | Manual switch placements from saved profiles now honored in logical diagram |
| NET-2B | Cross-rack edges render with outer/inner exit-side rules and dashed styling |
| NET-3 | Subnet-based edge coloring (Network A = green, Network B = blue) with legend |
| NET-4 | Mis-cabling detection with red/orange highlighting and validation banner |
| NET-5 | Inter-rack IPL/MLAG connections restored (fixes regression from bezier refactor) |

Additional diagram fixes in this release: spine/IPL classification recognizes
"SS"-named spines and topological evidence; affinity-based rack pagination keeps
connected racks on the same page so node-to-switch edges are not dropped after
manual placement.

### Reporter Library

- `mqm8700-hs2f`, `nexus_c9332d_gx2b`, and `cisco_ebox` promoted to built-in
  devices in `src/hardware_library.py` with images bundled under
  `assets/hardware_images/`, so they ship in the frozen build without
  first-launch seeding.
- Missing built-in image references (`broadwell`, `cascadelake`,
  `arista_7060dx5`) reconciled to existing assets so rack diagrams no longer
  silently fall back to a generic bezel.

### Intel macOS Support

- `build-release.yml` matrix expanded with the `macos-15-intel` runner.
- `build-mac.sh` appends an architecture suffix (`-arm64` or `-x64`) to the
  `.dmg` filename automatically based on `uname -m`.
- Release assets: `VAST-Reporter-v1.5.8-mac-arm64.dmg` and
  `VAST-Reporter-v1.5.8-mac-x64.dmg`.

---

## Bug Fixes

| ID | Fix |
|----|-----|
| HC-BUNDLE | Health Check Results saved to the per-cluster bundle path; `SUMMARY.md` shows OK/SKIPPED instead of MISSING |
| RPT-6 | Rack diagram device placement aligns with Discovery UI U-position convention |
| RPT-7 | Regenerated reports from Results tab preserve YAML-defined margins (deep-merge) |
| Tunnel | Two-hop SSH to VMS `localhost:443` bypasses S3 gateway virtual-host routing |
| Auth | Default VMS credentials corrected to `support`/`654321` for `use_default_creds` |
| CI | Security-audit workflow no longer false-positives or fails on a missing `security` label |

---

## Technical Details — Tunnel Fix

**Problem:** When connecting via Tech Port (`192.168.2.2`), the SSH tunnel
forwarded traffic from the CNode directly to the management VIP
(`10.138.101.139:443`). The VMS nginx routes requests by `Host` header —
unrecognized hosts are intercepted by the S3 gateway, which returns
`CredentialsNotSupported` XML errors.

**Fix:** The tunnel now establishes a nested SSH hop:

```
local:port → SSH(192.168.2.2) → SSH(172.16.3.3/VMS) → direct-tcpip(127.0.0.1:443)
```

By terminating on the VMS loopback, the management API is reached directly
without virtual-host routing. The HTTP `Host` header is set to the management
IP as a defensive fallback.

---

## Known Limitations

- **Teleport Mode is Beta.** The Teleport (tsh) connection mode is shipped for
  early use but is still being validated and hardened in the field; it is
  flagged with a "Beta Feature" badge in the Reporter UI. It requires `tsh` on
  PATH and an authenticated `tsh` session (auto-login handles expiry). Expect
  iterative fixes in subsequent releases.
- **SR-2 (deferred):** Onyx SSH pre-probe logs `[WARN]` for each rejected
  candidate password even on success runs. Cosmetic only.
- **Intel runner sunset:** `macos-15-intel` is available until August 2027.
  Post-sunset, a universal2 binary approach will be needed.

---

## Upgrade Notes

No breaking changes. Drop-in replacement for v1.5.7. Configuration files are
backward-compatible.
