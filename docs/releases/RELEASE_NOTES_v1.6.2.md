# asbuilt-reporter — v1.6.2

**Focus:** fixes from the first EBox field run of the Test Suite, report readability (grouped health
details, wrapped tables, titles kept with their tables), and rack diagrams for 45U to 52U racks.

> Patch release. No config-key or data migration. Existing cluster profiles, Library entries and
> `config.yaml` carry forward unchanged.

## Highlights

- **The Test Suite works on EBox clusters.** Support Tools finds the EBox VMS wrapper, Network
  Extraction and vnetmap see every node, and switch operations are skipped (not failed) when VMS has
  no switches.
- **vperfsanity runs to completion and always cleans up.** Step 4 allows for the script's 2-hour
  burst-recovery wait, handles the S3 part limit on large clusters, and cleanup runs even after a
  failure or Cancel.
- **Bundles explain their own failures.** Placeholders and `SUMMARY.md` name the failing step and
  error, and the session's Output Results log ships inside the bundle.
- **Easier-to-read reports.** Health Check details are grouped into nine functional tables, table
  text wraps inside its cells, and a table's title always starts on the same page as the table.
- **Rack diagrams for 42U, 45U, 48U, 50U and 52U racks**, with every U labelled and all racks drawn
  at one scale.
- **New name on screen:** the report title, app, CLI and guides now read **asbuilt-reporter**.

## Added

- Supermicro Turin 2U EBox (`supermicro_turin_ebox24`) in the built-in hardware library.
- 45U, 48U, 50U and 52U rack heights (RACK-1) and a rack validation report script (RACK-2).
- Node serial numbers in Hardware Inventory and the CNode/DNode Management Map (INV-1).
- Health Check details in the PDF and on the Health Check page (HCF-6), grouped by functional area.
- Day-one checklist on the Dashboard and a 13-step Field Procedure in the Quick Start Guide.
- `scripts/diag_api_fields.py` for lab API field discovery (DIAG-1).

## Changed

- New report title page in Fira Sans Bold (RPT-TITLE-1).
- Physical Rack Layout labels every U and drops the duplicate rack caption.
- Teleport Mode is no longer labelled Beta.
- The Upgrade State health check is removed (HCF-1); VMS reports `UNKNOWN` on idle clusters.
- In-app guides updated for the workflow changes below.

## Fixed

- Support Tools failed on every EBox cluster (FR-1).
- vperfsanity was cut off before its read phase (FR-2) and refused to start on large clusters.
- Aborted workflows left test data and services on the cluster (FR-3).
- Switch operations failed when VMS had no switches (FR-4).
- Log Bundle reported OK while collecting almost nothing (FR-5).
- Network Extraction and vnetmap missed nodes on EBox clusters (NET-6).
- Firmware Consistency warned on identical BIOS versions written differently (HCF-7).
- Skipped health checks showed `[????]` instead of `[SKIP]` and a reason (HCF-8).
- Milan EBoxes were drawn at 1U (HWL-3), and devices above U42 vanished from taller racks.
- Table titles could sit on one page with their table on the next.
- Clearer messages for lost SSH sessions, rejected logins and missing VIP pools; the Test Suite no
  longer starts while pre-validation is running.

See `CHANGELOG.md` for the full list.

## Security

- Credentials used by the run (passwords, per-switch and candidate passwords, API token) are masked
  as `[REDACTED]` in the bundled `diagnostics/operation_log.jsonl`.

## Upgrade notes

1. In a running 1.6.x app, wait for **UPDATE AVAILABLE**, open **Download**, pick your macOS
   architecture (or Windows), then **Exit & Upgrade** before replacing the app.
2. No config or Library migration. The installed app is still named **VAST Reporter**, so it replaces
   the existing copy in place.
3. After install, open the header tools menu and run **Update Tools** if the freshness badge is stale.

## Known issues

- **Results page cluster filter mixes Tech Port clusters (TP-4).** Clusters reached through the Tech
  Port all use `192.168.2.2`, so filtering by one lists the others' results too. Check the cluster name
  in the file name before sharing results. Planned for v1.6.3.
- Tech Port discovery records `192.168.2.2` as the management IP (TP-3).
- Remote archives stay on the cluster after download (FR-11).
- Artifact file names mix UTC and local time (OBS-1).
- vperfsanity Step 6 reports "Upload skipped" as success (HUB-7); Cancel does not interrupt long steps
  other than vperfsanity (FR-15).
- Unchanged: cluster profiles store credentials in plaintext (SEC-3); `/validation-results` is
  reachable outside Developer Mode (SEC-4).

## Artifacts

- `VAST-Reporter-v1.6.2-mac-arm64.dmg` (Apple Silicon)
- `VAST-Reporter-v1.6.2-mac-x64.dmg` (Intel)
- `VAST-Reporter-v1.6.2-win.zip` (Windows)

Built by `.github/workflows/build-release.yml` from the `v1.6.2` tagged commit after the blocking
quality-gate and test jobs pass.

## QA sign-off (prepare-release)

```
Release: v1.6.2            Date: 2026-10-16   Signed off by: pending ship-release

[x] Local quality gate green (version-sync, black, flake8, mypy, pytest 60%)
[x] Update-pill staged dry-run (§6a) green (1.6.1 → 1.6.2)
[x] Version / CHANGELOG / RELEASE_NOTES consistent
[ ] CI green on release commit (all jobs incl. qa-cross-os + build-smoke)
[x] Live validation: EBox cluster report reviewed clean; remaining live-test-plan sections waived by the owner
[ ] Release-specific functional cases (§4) validated
--- after tag ---
[ ] GitHub Release published, marked latest, artifacts attached (2x .dmg + .zip)
[ ] Live update-pill (§6b) verified from a real 1.6.1 build (online)
```
