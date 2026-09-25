---
name: Test Suite log colors
overview: "Port the Reporter tile's log-level color-coding fixes from `reporter.html` to the Test Suite tile in `advanced_ops.html`. Two gaps exist: missing CSS class aliases and missing message-content heuristic in `_renderEntry`."
todos:
  - id: css-aliases
    content: "Update CSS selectors in advanced_ops.html: add .warning/.critical aliases and align color hex values with reporter.html"
    status: completed
  - id: render-heuristic
    content: Port the message-content heuristic from reporter.html _renderEntry into advanced_ops.html _renderEntry
    status: completed
isProject: false
---

# Fix Test Suite Output Results Log Level Color Coding

## Problem

The Test Suite tile (`advanced_ops.html`) Output Results pane displays all log lines without proper color coding because it is missing two fixes that were already applied to the Reporter tile (`reporter.html`).

## Gap Analysis

### Gap 1: CSS class aliases missing

**Reporter (fixed)** -- [frontend/templates/reporter.html](frontend/templates/reporter.html) lines 492-495:

```css
.output-line.info { color: #e0e0e0; }
.output-line.warn, .output-line.warning { color: #ff9800; }
.output-line.error, .output-line.fail, .output-line.critical { color: #f44336; }
.output-line.success { color: #4caf50; }
```

**Test Suite (broken)** -- [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html) lines 296-299:

```css
.output-line.info { color: #e0e0e0; }
.output-line.warn { color: #ffc107; }
.output-line.error, .output-line.fail { color: #ff5252; }
.output-line.success { color: #4caf50; }
```

Missing selectors:

- `.output-line.warning` (alias for `.warn`) -- Python logging emits `WARNING` as the level, which lowercases to `warning`, not `warn`
- `.output-line.critical` (alias for errors) -- Python logging emits `CRITICAL`, which lowercases to `critical`

Color inconsistency:

- Warn color is `#ffc107` vs Reporter's `#ff9800`
- Error color is `#ff5252` vs Reporter's `#f44336`

### Gap 2: Message-content heuristic missing from `_renderEntry`

**Reporter (fixed)** -- [frontend/templates/reporter.html](frontend/templates/reporter.html) lines 882-888:

```javascript
var cls = entry.level;
var msgUpper = (entry.message || '').toUpperCase();
if (cls === 'info') {
    if (msgUpper.indexOf('[WARN') !== -1 || msgUpper.indexOf('WARNING') !== -1) cls = 'warn';
    else if (msgUpper.indexOf('[ERROR') !== -1 || msgUpper.indexOf('FAIL') !== -1) cls = 'error';
    else if (msgUpper.indexOf('SUCCESS') !== -1 || msgUpper.indexOf('COMPLETED') !== -1) cls = 'success';
}
```

**Test Suite (broken)** -- [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html) line 624:

```javascript
line.className = 'output-line ' + entry.level;
```

The Test Suite uses `entry.level` verbatim. Many backend log entries arrive with level `info` but contain messages like `[WARN] ...`, `SUCCESS: ...`, `FAIL: ...`, etc. Without the heuristic, these all render as plain white `info` lines instead of being color-coded.

## Plan

### 1. Update CSS selectors and align colors

In [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html), replace lines 297-298:

```css
.output-line.warn, .output-line.warning { color: #ff9800; }
.output-line.error, .output-line.fail, .output-line.critical { color: #f44336; }
```

This adds the `.warning` and `.critical` aliases and aligns the color hex values with the Reporter tile.

### 2. Add message-content heuristic to `_renderEntry`

In [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html), replace line 624:

```javascript
line.className = 'output-line ' + entry.level;
```

with:

```javascript
var cls = entry.level;
var msgUpper = (entry.message || '').toUpperCase();
if (cls === 'info') {
    if (msgUpper.indexOf('[WARN') !== -1 || msgUpper.indexOf('WARNING') !== -1) cls = 'warn';
    else if (msgUpper.indexOf('[ERROR') !== -1 || msgUpper.indexOf('FAIL') !== -1) cls = 'error';
    else if (msgUpper.indexOf('SUCCESS') !== -1 || msgUpper.indexOf('COMPLETED') !== -1) cls = 'success';
}
line.className = 'output-line ' + cls;
```

This is an exact port of the Reporter tile logic.

## Scope

Single file change: [frontend/templates/advanced_ops.html](frontend/templates/advanced_ops.html) -- two edits (CSS block and JS `_renderEntry` method).
