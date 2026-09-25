---
name: Test Suite Success Box
overview: Replace the inline "Download Bundle" button on the Test Suite tile with a green success box (matching the Reporter tile's "Report Generated Successfully" pattern) that appears after one-shot completion, containing a "Bundle Generated Successfully" message and a blue "Download Bundle" button.
todos:
  - id: html-panel
    content: Replace inline Download Bundle button with green success panel in the Test Suite button area
    status: completed
  - id: js-show
    content: Update one-shot completion handler to show the new panel instead of the inline button
    status: completed
  - id: js-hide
    content: Hide the panel when starting a new one-shot run
    status: completed
isProject: false
---

# Test Suite Success Box

## Current State

**Reporter tile (the pattern to match):** After report generation, a green success box (`#reporterResultPanel`) appears with:

- CSS class `rpt-result-panel`: green-tinted background, green border, rounded
- CSS class `rpt-result-title`: bold green success text
- 3 blue `btn-accent btn-sm` buttons (View PDF, Download PDF, Download JSON)

```434:435:frontend/templates/reporter.html
.rpt-result-panel { margin-top: 16px; padding: 14px 16px; background: rgba(34, 197, 94, 0.08); border: 1px solid var(--success); border-radius: 6px; }
.rpt-result-title { font-weight: 600; color: var(--success); margin-bottom: 4px; }
```

**Test Suite tile (current):** On completion, a "Download Bundle" button (`#btnOneShotDownload`, class `btn-secondary`) is unhidden inline next to the Run/Cancel buttons (line 365). Clicking it triggers `downloadResults()` which collects, creates, and auto-downloads the bundle.

## Changes (single file: [reporter.html](frontend/templates/reporter.html))

### 1. Replace inline Download Bundle button with a success panel

Remove the existing `btnOneShotDownload` button from the button group (line 365) and add a new hidden success panel after the button group, matching the Reporter pattern:

```html
<div id="oneShotResultPanel" class="rpt-result-panel" style="display: none;">
    <div class="rpt-result-title">Bundle Generated Successfully</div>
    <div class="btn-group" style="margin-top: 8px;">
        <button type="button" class="btn btn-accent btn-sm" id="btnOneShotDownload" onclick="downloadResults()">Download Bundle</button>
    </div>
</div>
```

This reuses the existing `rpt-result-panel` and `rpt-result-title` CSS classes so the green box, text color, padding, border, and border-radius match exactly.

### 2. Update completion handler to show the panel

In the one-shot polling completion handler (~line 2199), change:

```javascript
document.getElementById('btnOneShotDownload').style.display = '';
document.getElementById('btnOneShotDownload').disabled = false;
```

to:

```javascript
document.getElementById('oneShotResultPanel').style.display = '';
```

### 3. Hide the panel on new run / reset

In the `startOneShot()` function, add a line to hide the panel when starting a new run:

```javascript
document.getElementById('oneShotResultPanel').style.display = 'none';
```

Also ensure it's hidden on `loadProfile()` reset if the Reporter panel is hidden there too.
