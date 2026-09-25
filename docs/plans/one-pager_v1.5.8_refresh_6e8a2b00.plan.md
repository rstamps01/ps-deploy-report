---
name: One-pager v1.5.8 refresh
overview: "Refresh the SE/PSE marketing one-pager: make the version badge auto-update from the GitHub Releases API, refresh all UI/report screenshots to the current v1.5.8 interface, and update the feature copy to cover everything added since 1.5.0."
todos:
  - id: version-badge
    content: Add id hooks + v1.5.8 fallback to both badges and a GitHub Releases API fetch that sets latest tag_name (graceful offline fallback)
    status: completed
  - id: copy-screenshots
    content: Copy 8 mapped screenshots into docs/marketing/screenshots/ (overwrite 7, add Update-Tools.png)
    status: completed
  - id: showcase-tiles
    content: Swap Advanced Configuration tile for Update Tools tile and refresh showcase captions
    status: completed
  - id: feature-copy
    content: Update hero subtext, benefits cards, report-preview date, and topology copy to cover features since 1.5.0
    status: completed
  - id: verify-deploy
    content: Verify rendering/lightbox/badge locally, then commit assets + HTML and push to main to deploy
    status: completed
isProject: false
---

# One-Pager v1.5.8 Refresh

Target file: [docs/marketing/se-one-pager.html](docs/marketing/se-one-pager.html). It is static HTML deployed by [.github/workflows/pages.yml](.github/workflows/pages.yml) (uploads `docs/marketing/` as-is on push to `main` when `docs/marketing/**` changes). Screenshots live in `docs/marketing/screenshots/`.

## 1. Auto-updating version badge (dynamic JS)

The page hardcodes `v1.5.0` in two spots: the hero brand badge (line 983) and the footer badge (line 1368).

- Update both hardcoded strings to `v1.5.8` (offline fallback) and tag them so JS can target them: hero `<span class="brand-version" id="appVersion">` and footer `<span class="version-badge" id="appVersionFooter">`.
- Add a small script in the existing `<script>` IIFE (near the bottom, ~line 1500) that fetches `https://api.github.com/repos/rstamps01/ps-deploy-report/releases/latest`, reads `tag_name`, and writes it (normalized to a leading `v`) into both spans. On any error it silently leaves the hardcoded fallback. This means every future GitHub Release updates the badge with zero edits.

```js
fetch('https://api.github.com/repos/rstamps01/ps-deploy-report/releases/latest')
  .then(function (r) { return r.ok ? r.json() : null; })
  .then(function (d) {
    if (!d || !d.tag_name) return;
    var v = d.tag_name[0] === 'v' ? d.tag_name : 'v' + d.tag_name;
    ['appVersion', 'appVersionFooter'].forEach(function (id) {
      var el = document.getElementById(id); if (el) el.textContent = v;
    });
  }).catch(function () {});
```

## 2. Refresh screenshots (copy 8 files into `docs/marketing/screenshots/`)

Source images are the 9 attached captures. Mapping (the second Test Suite capture, 3.34.14, is a near-duplicate and is not used):

- `Dash.png` <- Dashboard / Quick Start (3.32.59)
- `Reporter.png` <- Reporter checklist: Pre-Validation, Run Vnetmap, Generate As-Built Report, Health Check (3.33.10)
- `Test-Suite.png` <- Test Suite full operations list (3.35.21)
- `Results.png` <- Validation Results tabbed browser (3.33.18)
- `Library.png` <- Hardware Device Library (3.35.40)
- `Update-Tools.png` (NEW) <- Reporter with Update Tools / Deployment Tools "4/4 cached" dropdown (3.36.37)
- `Report-Rack-Diagram.png` <- PDF 42U rack diagram (2.51.36)
- `Logical-Network-Diagram.png` <- PDF Logical Network Topology with cabling-validation banner (2.50.56)

All new captures already show `v1.5.8` and the green "LATEST VERSION" pill, so the UI matches the badge.

## 3. UI showcase tiles (Section 4)

Replace the six tiles 1:1 with the refreshed screenshots and swap the **Advanced Configuration** tile (`Adv-Config.png`) for a new **Update Tools** tile (`Update-Tools.png`). Updated captions:

- Dashboard: keep (Quick Start tiles, Results Odometer, Usage & Privacy local metrics).
- Reporter: "Guided 3-step Reporter workflow with Tech Port / VMS / Teleport (Beta) connection modes, Discovery, switch placement, and one-click Health Check."
- Post-Deployment Test Suite: keep, confirm copy matches the operations shown (Re-Validation, vnetmap, Support Tools, vperfsanity, VMS Log Bundle, Switch/Network Extraction, Generate Report + Health Checks).
- Validation Results: "Per-cluster results browser with tabs and live counts for Reports, Health, Network, Switch, vnetmap, vperfsanity, Support, Logs, and Bundles; regenerate PDFs from saved JSON."
- Hardware Library: keep.
- NEW Update Tools: "One-click deployment-tool sync (vnetmap, mlnx_switch_api, vast_support_tools, vperfsanity) cached locally and shown READY, so runs work air-gapped." The orphaned `Adv-Config.png` file stays in the repo but is no longer referenced.

## 4. Feature copy updates (since 1.5.0)

- Hero `subtext` (line 986): add connection-mode breadth, e.g. "No Python. No terminal. Tech Port, VMS, or Teleport (Beta) - download, connect, and go."
- Benefits grid (Section 3): update the "Field-Ready Design" card to name Teleport (Beta) + Tech Port modes and same-named-switch handling; consider repurposing/adding a card for the Post-Deployment Test Suite and cached Update Tools. Keep the 4-card layout (replace weakest card rather than grow the grid).
- Report preview (Section 5): replace the dated `Generated March 31, 2026` line (line 1215) with a neutral/current value; optionally add "Mis-cabling detection" to the topology context since the new network-diagram capture shows the cabling-validation banner.
- Footer brand line still reads `asbuilt-reporter` + badge (now auto-updating).

Key 1.5.1 -> 1.5.8 themes to weave in (from [CHANGELOG.md](CHANGELOG.md)): Teleport (Beta) + Tech Port modes, Post-Deployment Test Suite, cached Update Tools, per-cluster (QP-2) results segmentation + Validation Results browser, network-diagram overhaul (subnet coloring, mis-cabling detection, spine/IPL rendering), same-named switch disambiguation, local Usage & Privacy metrics, and the Intel + Apple Silicon macOS builds.

## 5. Verify and deploy

- Open the file locally to confirm screenshots render, the lightbox gallery still indexes the new images, and the badge JS updates without console errors (graceful offline fallback to v1.5.8).
- Commit the HTML + new screenshot assets and push to `main`; `pages.yml` auto-deploys the live page at the GitHub Pages URL. (Note: pushing to `main` publishes immediately.)

## Open notes / assumptions

- Version source for the badge is the GitHub Releases API `tag_name` (latest published release), matching the existing "Download / GitHub Releases" links - not `src/app.py`.
- No new "Advanced Configuration" capture was provided, so that tile is replaced by Update Tools per your selection.
