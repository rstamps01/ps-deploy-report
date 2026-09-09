# VAST As-Built Report Generator — v1.6.1

**Focus:** rack-diagram correctness for Library and HPE Turin CBoxes, architecture-aware updates, and documentation that matches the desktop app.

> Patch release of the post-1.6.0 correction batch. No config-key or data migration. Existing cluster profiles, Library entries, and `config.yaml` carry forward unchanged.

## Highlights

- **HPE Turin CBox ships in the built-in catalog at 1U**, so a fresh install draws it correctly without a manual Library entry.
- **Library devices outrank broad vendor fallbacks**, so adding a device no longer has its height stolen by a shorter built-in key (`hpe`, `arista`, …).
- **Update dropdown offers Apple Silicon, Intel, and Windows separately**, with **Exit & Upgrade** so the installer is not refused by a running copy.
- **In-app docs stay on the shipped version** via `{{APP_VERSION}}` tokens; the marketing site badge is live on every page.

## Added

- **HPE Gen6 Turin CBox (DL325 Gen11)** in `BUILTIN_DEVICES`. VMS reports `hpe_turin_cbox`; it was the missing member of the Gen6 Turin family (Dell and SMC were already catalogued). Uncatalogued, it matched the bare `hpe` fallback and inherited that entry's 2U IceLake height — so two 1U CBoxes at U24 and U25 drew as overlapping 2U boxes with artwork stretched 1.8×. An existing user Library entry under the same key still takes precedence.
- **Exit & Upgrade** in the update dropdown. Reuses `/shutdown` so the running bundle is not locked when the new `.app` / `.exe` is installed.
- **`docs/development/GITHUB-WORKFLOW.md`** — branching, Dependabot, and the release flow.

## Fixed

- **Library height/image lookup searched built-ins to exhaustion before the user Library.** Broad vendor keys swallowed specific user devices. Built-in and user catalogs are now one namespace, longest key first. Same fix on the logical network diagram, which had been returning the vendor fallback's artwork outright.
- **Wrong macOS DMG offered.** Asset matching is architecture-aware (`mac_arm64` / `mac_x64`); the single `mac` slot stays populated for already-shipped 1.5.8/1.6.0 clients.
- **Output Results heading vanished on Expand**, and the menu was inert during page startup. Expand now keeps the heading under the navbar (Escape collapses); the menu binds before backend hydration.
- **Stale artifact names and dead links in the Docs tab.** Tokens resolve at render time; unregistered `.md` targets fall back to GitHub.

## Changed

- Installation Guide documents the real Reporter workflow (Update Tools, connection modes, Discovery including non-VMS switches and the top-U convention, checklist, results). Advanced Configuration is reached from the header **☰** menu.
- Quick Start upgrade path starts at the in-app **UPDATE AVAILABLE** pill; Deployment Tools live in the header dropdown.
- Reporter-tile Update Tools / Tool Status duplicates removed; per-tool detail moved into the nav dropdown.
- CI: Node 20 deprecation cleared; Pages upload/deploy bumped as a pair; `main` is exempt from `cancel-in-progress` so a superseded `develop` run cannot redden a released commit.
- Dependency floors: `scp`, `flask`, `types-requests`, `jsonschema`. ReportLab 5.x is held ([PR #20](https://github.com/rstamps01/ps-deploy-report/pull/20)).

## Upgrade notes

1. In a running 1.5.8 or 1.6.0 app, wait for **UPDATE AVAILABLE**, open **Download**, pick the matching macOS architecture (or Windows), then **Exit & Upgrade** before replacing the app.
2. No config or Library migration. Operators who already added `hpe_turin_cbox` to the Library keep that entry; it still wins on an exact key.
3. After install, open the header tools dropdown and **Update Tools** if the freshness badge is stale.

## Known issues (unchanged)

- Cluster profiles store credentials in plaintext (`config/cluster_profiles.json`, roadmap SEC-3).
- `/validation-results` is reachable outside Developer Mode (roadmap SEC-4).
- EBox/`enclosure` models are forced to 1U before catalog lookup (roadmap HWL-3) — Milan EBoxes declared 2U still render at 1U.

## Artifacts

- `VAST-Reporter-v1.6.1-mac-arm64.dmg` (Apple Silicon)
- `VAST-Reporter-v1.6.1-mac-x64.dmg` (Intel)
- `VAST-Reporter-v1.6.1-win.zip` (Windows)

Built by `.github/workflows/build-release.yml` from the `v1.6.1` tagged commit after the blocking quality-gate + test jobs pass.

## QA sign-off (prepare-release)

```
Release: v1.6.1            Date: 2026-09-08   Signed off by: pending ship-release

[x] Local quality gate green (version-sync, black, flake8, mypy, pytest 60%)
[x] Update-pill staged dry-run (§6a) green (1.6.0 → 1.6.1 + 1.5.8 → 1.6.1)
[x] Version / CHANGELOG / RELEASE_NOTES consistent
[ ] CI green on release commit (all jobs incl. qa-cross-os + build-smoke)
[ ] Cross-OS functional subset run on: [x] macOS-arm64 (local source) [ ] macOS-x64 [ ] Windows [ ] Linux
[ ] Release-specific functional cases (§4) validated
--- after tag ---
[ ] GitHub Release published, marked latest, artifacts attached (2x .dmg + .zip)
[ ] Live update-pill (§6b) verified from a real 1.6.0 build (online)
```
