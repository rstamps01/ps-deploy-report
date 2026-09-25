---
name: VAST Logo Progress Indicator
overview: Replace the circular SVG progress ring with a VAST logo fill animation that fills bottom-to-top as operations progress, using CSS mask-image over a gradient. Reposition the progress visual to the right side of the operations list in both Reporter and One-Shot panels.
todos:
  - id: copy-icon
    content: Copy VAST icon PNG to frontend/static/img/ for Flask serving
    status: completed
  - id: css-vast-progress
    content: Replace progress-ring CSS with vast-progress mask-image and gradient-fill classes
    status: completed
  - id: html-flex-layout
    content: Restructure Reporter and One-Shot panels into two-column flex layouts with progress visual on the right
    status: completed
  - id: js-vast-progress
    content: Replace ProgressRing constructor with VastProgress using CSS mask gradient fill technique
    status: completed
  - id: wire-calls
    content: Update all rptRing/osRing call sites and initialization to use new VastProgress instances
    status: completed
  - id: responsive-stack
    content: Add media query to stack layout vertically on narrow viewports
    status: completed
isProject: false
---

# VAST Logo Progress Indicator

## Technique: CSS mask-image with gradient fill

The white-on-transparent VAST icon (`VAST-Data-Icon-Solid-White.png`, 518x444 RGBA) is used as a CSS `mask-image`. Behind the mask, a `linear-gradient(to top, ...)` creates the fill-from-bottom effect. As progress advances, the gradient boundary shifts upward via JS, causing the logo to visually "fill up." The percentage and timer text overlay the center of the triangle.

```
Idle        25%         75%         100%
+------+   +------+   +------+   +------+
|      |   |      |   |FILLED|   |FILLED|
| dim  |   | dim  |   |FILLED|   |FILLED|
| logo |   |FILLED|   |FILLED|   |FILLED|
+------+   +------+   +------+   +------+
           "25%"       "75%"       check
           01:12       03:45       05:02
```

## Layout restructure

Both Reporter and One-Shot panels get a two-column flex layout: operations list on the left, progress visual on the right. The progress visual is ~160px wide, vertically centered, and only visible during/after a run.

```
+--------------------------------------------+
| Select Operation        [Reporter/OneShot] |
+--------------------------------------------+
| Operations list       |   [VAST Logo]      |
| [ ] Pre-Validation    |     filling        |
| [x] Run Reporter      |      43%           |
| [ ] Health Check       |     02:31          |
|                        |                    |
| [Run] [Cancel] [Tools] |                   |
+--------------------------------------------+
```

## File changes

### 1. Copy icon to static assets

Copy `assets/diagrams/VAST-Data-Icon-Solid-White.png` to [`frontend/static/img/vast-icon-mask.png`](frontend/static/img/vast-icon-mask.png) so Flask can serve it at `/static/img/vast-icon-mask.png`.

### 2. CSS changes in [`frontend/templates/reporter.html`](frontend/templates/reporter.html) `<style>` block

Remove the old `.progress-ring-*` CSS classes and replace with:

- `.vast-progress-container` -- the outer wrapper placed to the right; flex column, center-aligned, ~160-180px width
- `.vast-progress-logo` -- the masked logo element:
  - `mask-image: url('/static/img/vast-icon-mask.png')` + `-webkit-` prefix
  - `mask-size: contain; mask-repeat: no-repeat; mask-position: center`
  - `background: linear-gradient(to top, <fill-color> Xpx, <dim-color> Xpx)` -- gradient boundary controlled by JS
  - Width/height ~160px, aspect ratio matching the icon (518:444 ~ 1.17:1)
- `.vast-progress-overlay` -- absolutely positioned over the logo center for percentage + timer text
- `.vast-progress-label` -- step name text below the logo
- Pulse keyframe on the filled gradient during running state

### 3. HTML restructure in [`frontend/templates/reporter.html`](frontend/templates/reporter.html)

**Reporter panel (`#stepByStepPanel`):** Wrap the existing content (sections A-D) in a flex row. Left column gets the operations list + buttons (flex: 1). Right column gets the VAST progress container (`#reporterProgress`), initially hidden.

**One-Shot panel (`#oneShotPanel`):** Same approach -- wrap existing content in a flex row. Left column: checklist + buttons (flex: 1). Right column: `#oneShotProgressVast`, initially hidden.

Remove the old `#reporterProgressRing` and `#oneShotProgressRing` div placeholders.

### 4. JS refactor of `ProgressRing` to `VastProgress` in [`frontend/templates/reporter.html`](frontend/templates/reporter.html) `<script>` block

Replace the `ProgressRing` constructor with a `VastProgress` constructor that:

- `_render()` -- creates the logo div (mask element), overlay div (percentage + timer), and label div inside the container
- `show()` / `hide()` -- toggle visibility
- `start()` -- sets state to running, starts `setInterval` stopwatch, resets fill to 0%, shows pulse animation
- `_tickTimer()` -- updates MM:SS display every second
- `_setFill(pct)` -- calculates pixel offset for the gradient boundary and updates `background` style; at 0% the gradient boundary is at the bottom (all dim), at 100% at the top (all filled)
- `update(percent, label, sub)` -- calls `_setFill`, updates percentage text and label
- `complete(label)` -- fills to 100%, changes fill color to green, replaces percentage with checkmark, freezes timer
- `error(label)` -- changes fill color to red, freezes timer
- `cancel()` -- changes fill color to amber, freezes timer
- `reset()` -- clears everything, hides container

All existing `rptRing.*` and `osRing.*` call sites remain identical in signature; only the constructor name and internal rendering change.

### 5. State colors

| State | Fill color | Text |
|-------|-----------|------|
Running | `#00d4ff` (VAST cyan) | percentage + MM:SS
Completed | `#4caf50` (green) | checkmark + frozen MM:SS
Error | `#f44336` (red) | percentage + frozen MM:SS
Cancelled | `#ffc107` (amber) | percentage + frozen MM:SS
Idle/dim | `rgba(100,100,100,0.15)` | -- hidden --

### 6. Responsive behavior

On narrow widths (< 600px), the flex layout stacks vertically with the progress visual centered below the operations list rather than to the right.
