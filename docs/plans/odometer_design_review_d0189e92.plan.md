---
name: Odometer Design Review
overview: Create a standalone HTML preview page with three odometer design variants (Sleek Modern, Classic Car, Futuristic AI) for visual comparison before integrating the chosen style into the Dashboard.
todos:
  - id: preview-page
    content: Create standalone odometer_preview.html with all three style variants and demo controls
    status: completed
  - id: review-pick
    content: User reviews and picks preferred style for Dashboard integration
    status: completed
isProject: false
---

# Odometer Design Review Preview

## Approach

Create a single standalone HTML file at `frontend/templates/odometer_preview.html` (or a simpler static file) that renders all three odometer styles side by side with a shared demo counter and +1 / +10 / +100 / Reset buttons for testing the rolling animation. This avoids touching the live dashboard until a style is chosen.

## Three Styles

### Style A: Sleek Modern

- Clean, minimal dark housing matching the app's `--bg-surface` / `--bg-elevated` palette
- Thin `1px` borders with `var(--border)` color, generous `border-radius`
- Light sans-serif digits (system font), subtle gradient overlay at top/bottom of each wheel window for depth
- Smooth `0.6s ease-out` CSS transition on `translateY`
- Accent-blue (`#1A6FB5`) thin glow line across the center reading line

### Style B: Classic Car

- Matte black housing with a chrome/silver outer bezel (`linear-gradient` metallic effect on border)
- Visible screw/rivet accents at corners (small circle pseudo-elements)
- Ivory/cream digit color on charcoal wheel background, serif-ish font (Georgia or serif fallback)
- Thicker divider grooves between wheels (dark inset shadow)
- Top/bottom gradient simulates a curved glass lens over the digit window
- Slightly slower `0.8s` transition with a mechanical `ease-in-out` feel

### Style C: Futuristic AI

- Translucent glass-morphism housing (`backdrop-filter: blur`, semi-transparent background)
- Cyan/teal accent glow (`#1BA3D1` — the app's VAST brand primary) around the frame and between digits
- Monospace/tech font for digits, with a subtle text-shadow glow
- Each digit has a faint scan-line overlay (repeating-linear-gradient at 2px intervals, low opacity)
- Center reading line is a bright cyan horizontal bar with `box-shadow` bloom
- Faster `0.4s` transition with a snappy `cubic-bezier(0.2, 0.8, 0.2, 1)` for a digital-meets-mechanical feel

## Shared JS

All three odometers share the same animation logic:

- 5 wheels per odometer, each containing a strip of digits 0-9 (plus a repeated 0 for wrap)
- `setOdometer(element, value)` — pads to 5 digits, sets `translateY` per wheel
- Demo buttons: +1, +10, +100, +1000, Reset

## Preview Page Structure

```
[  Style A: Sleek Modern  ]  [  Style B: Classic Car  ]  [  Style C: Futuristic AI  ]
      [ 00042 ]                    [ 00042 ]                    [ 00042 ]

                    [ +1 ]  [ +10 ]  [ +100 ]  [ +1000 ]  [ Reset ]
```

## File

- `frontend/static/odometer_preview.html` — Self-contained HTML with inline CSS and JS (no Flask template needed; can be opened directly in the browser via `file://` or served at a temp route)

## After Review

User picks a style, and it gets integrated into the real Dashboard per the existing plan (above the 9-tile grid, wired to the `total` from `/api/dashboard/status`).
