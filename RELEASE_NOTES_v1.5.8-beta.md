# Release Notes — v1.5.8-beta

**Date:** 2026-05-28
**Branch:** `feature/v1.5.8-batch`
**Status:** Beta — not yet promoted to latest release

> **Note:** This is a pre-release beta. It should NOT be linked as the latest
> version until the production v1.5.8 tag is cut after live validation.

---

## Highlights

- **Logical Network Diagram overhaul** — Complete rendering refresh with
  subnet-aware coloring, mis-cabling detection, bezier-curve link routing,
  and improved cross-rack connection visibility.
- **Intel macOS build support** — Release pipeline now produces separate
  `.dmg` artifacts for both Apple Silicon (arm64) and Intel (x86_64).
- **Tech-Port tunnel reliability** — Two-hop SSH architecture fixes the
  S3 gateway interception issue that blocked authentication on clusters
  using virtual-host routing.

---

## New Features

### Network Diagram Visualization (NET-2A through NET-5)

| ID | Feature |
|----|---------|
| NET-2A | Manual switch placements from saved profiles now honored in logical diagram |
| NET-2B | Cross-rack edges render with outer/inner exit-side rules and dashed styling |
| NET-3 | Subnet-based edge coloring (Network A = green, Network B = blue) with legend |
| NET-4 | Mis-cabling detection with red/orange highlighting and validation banner |
| NET-5 | Inter-rack IPL/MLAG connections restored (fixes regression from bezier refactor) |

### Link Routing

- Device-to-switch connections use smooth cubic bezier curves matching the
  approved mockup (`docs/issues/NET-2/mockup-target.svg.png`), replacing
  the previous orthogonal polyline style.
- Cross-rack connections use dashed lines at reduced opacity (0.40) and are
  drawn in a separate Z-order pass for visibility.

### Intel macOS Support

- `build-release.yml` matrix expanded with `macos-15-intel` runner.
- `build-mac.sh` appends architecture suffix (`-arm64` or `-x64`) to the
  `.dmg` filename automatically based on `uname -m`.
- Release assets: `VAST-Reporter-v1.5.8-mac-arm64.dmg` and
  `VAST-Reporter-v1.5.8-mac-x64.dmg`.
- Intel runner available until August 2027; universal2 binary approach
  documented as future fallback.

---

## Bug Fixes

| ID | Fix |
|----|-----|
| RPT-6 | Rack diagram device placement aligns with Discovery UI U-position convention |
| RPT-7 | Regenerated reports from Results tab preserve YAML-defined margins (deep-merge) |
| Tunnel | Two-hop SSH to VMS `localhost:443` bypasses S3 gateway virtual-host routing |
| Auth | Default VMS credentials corrected to `support`/`654321` for `use_default_creds` |

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
without virtual-host routing. Additionally, the HTTP `Host` header is set to
the management IP as a defensive fallback.

---

## Quality Metrics

| Metric | Value |
|--------|-------|
| Tests | 1279 passed |
| Coverage | 65.66% (threshold: 60%) |
| Flake8 | Clean |
| Black | Clean |

---

## Validation Checklist (Beta)

- [ ] Tech Port connection via `192.168.2.2` authenticates successfully
- [ ] Report generation completes end-to-end via Tech Port mode
- [ ] Network diagram renders with correct subnet coloring
- [ ] Mis-cabling detection fires on known mis-cabled cluster (if available)
- [ ] Cross-rack IPL/MLAG connections visible in multi-rack diagrams
- [ ] macOS ARM64 .dmg launches and generates a report
- [ ] macOS Intel .dmg launches and generates a report (CI artifact)
- [ ] Windows .zip launches and generates a report

---

## Known Limitations

- **SR-2 (deferred):** Onyx SSH pre-probe logs `[WARN]` for each rejected
  candidate password even on success runs. Cosmetic only.
- **RPT-VALIDATION-1/2:** Node User field rendering and password-clear UX
  issues on profile restore. Form submits correctly; cosmetic.
- **Intel runner sunset:** `macos-15-intel` available until August 2027.
  Post-sunset, a universal2 binary approach will be needed.

---

## Upgrade Notes

No breaking changes. Drop-in replacement for v1.5.7. Configuration files
are backward-compatible.
