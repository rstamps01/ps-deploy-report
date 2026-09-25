---
name: Dashboard Mechanical Odometer
overview: Add a CSS/JS-animated mechanical odometer (5 wheels, 0-9 digits on each) above the Results Odometer tile grid on the Dashboard, displaying the total results count with realistic rolling-wheel transitions.
todos:
  - id: odo-html-css
    content: Add mechanical odometer HTML structure and CSS styles to dashboard.html, positioned above the 9-tile grid
    status: pending
  - id: odo-js
    content: Update updateStatus() JS to animate odometer wheels based on total count
    status: pending
  - id: odo-verify
    content: Verify odometer renders and animates correctly in the running app
    status: pending
isProject: false
---

# Dashboard Mechanical Odometer

## Location

Above the existing 9-tile Results Odometer grid, centered, inside the existing `<!-- Report Odometer -->` section in [frontend/templates/dashboard.html](frontend/templates/dashboard.html). Replaces the current `dsOdoTotal` "Total: --" text span with the visual odometer.

## Visual Design

A row of 5 side-by-side "wheels" rendered with pure CSS (no images). Each wheel:

- Dark housing (rounded rect, `#1a1a1a` or `var(--bg-secondary)` with subtle border)
- Visible window showing the current digit plus partial top/bottom neighbors (3D depth illusion via `perspective` and slight gradient overlay at top/bottom edges)
- White/light digit text, monospace font, ~2rem size
- Thin divider lines between wheels
- Smooth CSS `transform: translateY()` transition when value changes (0.6s ease-out), simulating mechanical rotation
- A subtle metallic frame border around the entire 5-wheel assembly

Each wheel contains a vertical strip of digits 0-9 (repeated to allow seamless wrapping). The strip slides vertically via `translateY` to show the correct digit in the window.

## HTML Structure (in dashboard.html)

```html
<div class="mech-odometer" id="mechOdometer">
  <div class="mech-odo-frame">
    <div class="mech-odo-wheel" data-digit="0">
      <div class="mech-odo-strip">
        <span>0</span><span>1</span>...<span>9</span><span>0</span>
      </div>
    </div>
    <!-- repeat x5 -->
  </div>
</div>
```

Placed above the `<div class="status-bar" id="dsOdometer">` grid, centered.

## CSS (inline `<style>` in dashboard.html)

- `.mech-odometer` — flex centered, margin-bottom
- `.mech-odo-frame` — dark background with rounded corners, flex row, border, subtle box-shadow for depth
- `.mech-odo-wheel` — fixed width/height, overflow hidden, position relative
- `.mech-odo-strip` — vertical column of digit spans, transition on transform
- Gradient overlays at top/bottom of each wheel window for the curved-glass 3D effect
- Divider pseudo-elements between wheels

## JavaScript (in existing `<script>` block)

Update the existing `updateStatus(data)` function. After computing `total`:

```javascript
var totalStr = String(total).padStart(5, '0');
var wheels = document.querySelectorAll('.mech-odo-wheel');
wheels.forEach(function(w, i) {
    var digit = parseInt(totalStr[i], 10);
    var strip = w.querySelector('.mech-odo-strip');
    strip.style.transform = 'translateY(-' + (digit * digitHeight) + 'px)';
    w.setAttribute('data-digit', digit);
});
```

The wheels animate via CSS transition on `transform`, creating the rolling effect. Right-most wheel changes most frequently (ones), cascading left through tens, hundreds, etc.

## Files Changed

- [frontend/templates/dashboard.html](frontend/templates/dashboard.html) — Add odometer HTML, CSS, and update JS `updateStatus()` function
