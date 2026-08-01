# Cross-Platform QA Test Plan

**Owner:** release engineer (via `prepare-release` / `ship-release` skills)
**Applies to:** every release; the per-release checklist in §8 is filled out before a `vX.Y.Z` tag is cut.
**Companion docs:** `docs/PRE-RELEASE-QA-GAP-ANALYSIS.md` (test-suite coverage gaps), `.cursor/rules/ci-pipeline-13.mdc` (CI gates), `.cursor/rules/release-packaging-12.mdc` (release flow).

This plan validates that the product works as intended on all supported deployment targets **before** a release ships, and pairs an automated (CI) path with a manual checklist for when physical hardware/clusters are available.

---

## 1. Deployment targets

| Target | Form | Built by | QA path |
| --- | --- | --- | --- |
| macOS (Apple Silicon) | Packaged `.app` in `VAST-Reporter-vX.Y.Z-mac-arm64.dmg` | `build-release.yml` → `build-mac.sh` | CI build-smoke + cross-OS functional + manual |
| macOS (Intel) | Packaged `.app` in `VAST-Reporter-vX.Y.Z-mac-x64.dmg` | `build-release.yml` → `build-mac.sh` | CI build-smoke + cross-OS functional + manual |
| Windows | Packaged `VAST-Reporter-vX.Y.Z-win.zip` | `build-release.yml` → `build-windows.ps1` | CI build-smoke + cross-OS functional + manual |
| Linux | **Run-from-source** (`python3 src/main.py`) — no packaged artifact | n/a | CI cross-OS functional (ubuntu) + manual |

> **Linux is a run-from-source target only.** There is no PyInstaller Linux artifact today. If a packaged Linux build is ever required, add it to `build-release.yml` and this table.

---

## 2. Automated QA (CI) — what runs where

All gates are **blocking** for a release tag (`build-release.yml`, pipeline §5).

| Gate | Runner(s) | Job |
| --- | --- | --- |
| Lint (`flake8` + E722), format (`black`), types (`mypy`) | ubuntu | `quality-gate` |
| Version sync (`scripts/check-version-sync.sh`) | ubuntu | `quality-gate` |
| Unit + integration tests, coverage floor (`--cov-fail-under=60`) | ubuntu (3.11 + 3.12 on develop/main) | `unit-tests` / `integration-tests` |
| UI tests (Playwright) | ubuntu | `ui-tests` |
| **Cross-OS functional subset** (routes, update pill, Teleport endpoints) | **ubuntu + macOS + windows** | `qa-cross-os` |
| Build smoke (packaged app builds) | macOS + windows | `build-smoke` |
| Skill conformance | ubuntu | `check-skill-conformance` |

The `qa-cross-os` job runs the app's HTTP layer from source on all three OSes:
`tests/test_app.py`, `tests/test_updater.py`, `tests/test_update_release_readiness.py`, `tests/test_functional_validation.py`. `cairosvg` is import-guarded, so native Cairo is not required for this job (SVG rendering is validated separately in build-smoke / manual).

**Cost note:** `qa-cross-os` and `build-smoke` only run on `develop`/`main` and PRs targeting them (macOS = 10× / Windows = 2× Linux cost).

---

## 3. Cross-OS functional matrix (manual — when hardware is available)

Run the packaged app (mac/win) or `python3 src/main.py` (Linux) and verify:

| Area | Check | mac-arm64 | mac-x64 | win | linux |
| --- | --- | --- | --- | --- | --- |
| Launch | App starts, browser opens, no `tsh`/path errors in console | ☐ | ☐ | ☐ | ☐ |
| Header | Version pill shows `vX.Y.Z`; no PRE-RELEASE on a stable build | ☐ | ☐ | ☐ | ☐ |
| Update pill | See §6 | ☐ | ☐ | ☐ | ☐ |
| Dashboard / nav | All nav links load (Dashboard, Reporter, Results, Library, Config, Docs) | ☐ | ☐ | ☐ | ☐ |
| Config | Advanced Configuration loads; Teleport Settings render; Save persists | ☐ | ☐ | ☐ | ☐ |
| Report (with cluster) | Generate a report end-to-end; PDF renders with rack/network diagrams | ☐ | ☐ | ☐ | ☐ |
| Library | Built-in devices render images (not generic fallback) | ☐ | ☐ | ☐ | ☐ |
| Docs viewer | In-app docs open, including new guides | ☐ | ☐ | ☐ | ☐ |

Diagram rendering (Cairo/SVG) is the most platform-sensitive area — always exercise a real report render on each packaged OS when a cluster/Tech Port is reachable.

---

## 4. Release-specific functional cases — v1.6.0 delta

Derived from the changes since the last full release (`git diff v1.5.8..HEAD`). Validate each on at least one OS (all OSes for anything path/OS-sensitive):

- **Teleport `tsh` auto-discovery:** launch a packaged build from Finder/Explorer (not a terminal); the tsh status pill resolves and no "tsh not found on PATH" error appears. In Advanced Config → Teleport Settings, **Run Discovery** validates and persists `teleport.tsh_path`.
- **Teleport tunnel routing:** under Teleport Mode, Network Config, Support Tools, VMS Log Bundle, and vperfsanity SSH all route through the forwarded local endpoint (no "SSH command timed out"). *(requires a Teleport-reachable cluster)*
- **vnetmap cross-cluster safety:** two clusters behind the same Tech Port IP do not cross-contaminate topology; a failed vnetmap run degrades gracefully rather than embedding another cluster's data. *(requires cluster)*
- **Onyx/MLNX-OS auth:** vnetmap and health checks authenticate as `admin` on Onyx switches. *(requires cluster)*
- **Switch-config backups:** backup filenames are clean (no `^[[?1h` escape-code garbage). *(requires cluster)*
- **Bundle SUMMARY:** validation bundle `SUMMARY.md` shows the live cluster version (not blank). *(requires cluster)*

Cluster-dependent cases are validated manually against a lab cluster or a captured fixture; they are not part of CI.

---

## 5. Quality gates before tag (local mirror of CI)

```bash
bash scripts/check-version-sync.sh
black --check --line-length 120 src/ tests/
flake8 src/ tests/
mypy src/ --ignore-missing-imports --no-strict-optional
python3 -m pytest tests/ --ignore=tests/test_ui.py --cov=src --cov-fail-under=60
# Cross-OS functional subset (run per OS available):
python3 -m pytest tests/test_app.py tests/test_updater.py tests/test_update_release_readiness.py tests/test_functional_validation.py -q --no-cov
```

---

## 6. Update-notification (in-app "UPDATE AVAILABLE" pill) validation

**Requirement:** an existing v1.5.8 install must detect that v1.6.0 has been released and surface the header pill with a working download link.

**Mechanism (already shipped in v1.5.8):** `src/updater.py` queries the GitHub Releases API for `rstamps01/ps-deploy-report`, `/api/update/status` serves the result, and `base.html` + `app.js` render the `#appStatusPill` / `#appUpdate` dropdown. Config: `updates.enabled: true` (stable channel) in `config/config.yaml.template`.

### 6a. Staged dry-run (automated — runs in CI, no network)
`tests/test_update_release_readiness.py` feeds a realistic GitHub `/releases` payload using the **actual v1.6.0 asset names** and asserts a 1.5.8 client reports `update_available` with populated mac/win download URLs, ignores non-version tags (`pre-1.5.8-cleanup`), and excludes pre-releases on the stable channel. This is the automated proof the pill flips before the real tag exists.

### 6b. Live verification (manual — right after the tag is published)
1. Ensure the GitHub Release for `vX.Y.Z` is **published, non-draft, non-prerelease, marked latest** (`build-release.yml` does this for non-pre tags).
2. Launch a **real v1.5.8 build** on an internet-connected machine.
3. Confirm the header pill flips to **UPDATE AVAILABLE**, the dropdown shows "Version X.Y.Z (you have 1.5.8)", the Release-notes link opens the release, and Download offers the OS-matched installer.
4. Repeat on Windows (and, if desired, verify the dropdown lists both mac DMGs).

### 6c. Known caveats (document, don't block)
- **Offline / air-gapped machines never show the pill** — the check needs outbound HTTPS to `api.github.com` and degrades silently to hidden. This is by design for v1.6.0 (online-only). An offline/manual "newer version" indicator would be a separate feature.
- **macOS arch ambiguity:** a shipped v1.5.8 client has a single `download_url_mac` slot, so with two mac DMGs (arm64 + x64) it links whichever DMG GitHub returns first (pinned by `test_first_dmg_is_selected_when_two_arches_present`). We cannot patch already-installed clients; users can pick the correct arch from the Release page. *Follow-up (v1.6.0+ clients only): make `extract_download_urls` arch-aware so future updates auto-pick the right mac build.*

---

## 7. Sign-off gates

A release may be tagged only when:
- All CI gates green on the release commit (quality-gate, unit/integration, ui, `qa-cross-os`, build-smoke, skill-conformance).
- §5 local mirror green.
- §4 release-specific cases validated (cluster cases against lab/fixture).
- §6a automated dry-run green; §6b scheduled for immediately post-tag.
- Version sync + CHANGELOG + `docs/releases/RELEASE_NOTES_vX.Y.Z.md` consistent.

---

## 8. Per-release sign-off checklist (copy into the release notes / PR)

```
Release: vX.Y.Z            Date: ____________   Signed off by: ____________

[ ] CI green on release commit (all jobs incl. qa-cross-os + build-smoke)
[ ] Local quality gate green (version-sync, black, flake8, mypy, pytest 60%)
[ ] Cross-OS functional subset run on: [ ] macOS-arm64 [ ] macOS-x64 [ ] Windows [ ] Linux
[ ] Release-specific functional cases (§4) validated
[ ] Update-pill staged dry-run (§6a) green
[ ] Version / CHANGELOG / RELEASE_NOTES consistent
--- after tag ---
[ ] GitHub Release published, marked latest, artifacts attached (2x .dmg + .zip)
[ ] Live update-pill (§6b) verified from a real 1.5.8 build (online)
```
