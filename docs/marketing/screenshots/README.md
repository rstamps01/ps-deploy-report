# Screenshot Capture Guide

Instructions for adding real screenshots to the SE one-pager (`../se-one-pager.html`).

## Setup

1. Launch the app: `python3 src/main.py` (or open the `.dmg` / `.exe`)
2. Set browser window to **1440 x 900** for consistent framing
3. Use a connected cluster with data for the best-looking captures
4. Save all images to this `screenshots/` directory

## Required Screenshots

| Filename | Page / Route | What to Capture |
|---|---|---|
| `screenshot-dashboard.png` | Dashboard (`/`) | Full page showing Quick Start tiles, Results Odometer, and workflow cards |
| `screenshot-reporter.png` | Reporter (`/reporter`) | Connection form filled in, stepper visible, discovery complete or in-progress |
| `screenshot-results.png` | Validation Results (`/validation-results`) | Tab bar with at least 2-3 operation types populated |
| `screenshot-library.png` | Library (`/library`) | Device table with a few entries and hardware images visible |
| `screenshot-advanced-ops.png` | Advanced Ops (`/advanced-ops`) | Workflow list with status badges (requires `--dev-mode` launch flag) |
| `screenshot-report-pdf.png` | PDF output | First page of a generated PDF report (open in Preview / browser) |

## Capture Tips

- **macOS:** Cmd+Shift+4 then Space to capture the browser window, or use the Screenshot app for precise region capture.
- **Windows:** Win+Shift+S for Snip & Sketch region capture.
- Crop to the browser viewport (exclude browser chrome/address bar) for a cleaner look.
- PNG format preferred for crisp text rendering.
- Aim for roughly **16:10 aspect ratio** to match the placeholder slots.

## Adding Screenshots to the One-Pager

In `se-one-pager.html`, each screenshot slot has a placeholder `<div>` and a commented-out `<img>` tag. To swap in a real image:

1. Remove or comment out the `<div class="screenshot-placeholder">...</div>` block
2. Uncomment the `<img>` tag below it
3. Verify the `src` path matches your filename

Example before:

```html
<div class="screenshot-placeholder">
    <svg>...</svg>
    <span>Dashboard Screenshot</span>
</div>
<!-- <img src="screenshots/screenshot-dashboard.png" alt="Dashboard" class="screenshot-img"> -->
```

Example after:

```html
<!-- placeholder removed -->
<img src="screenshots/screenshot-dashboard.png" alt="Dashboard" class="screenshot-img">
```

No CSS or layout changes are needed -- the `screenshot-img` class handles sizing automatically.
