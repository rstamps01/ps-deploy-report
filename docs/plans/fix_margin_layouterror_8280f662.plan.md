---
name: Fix Margin LayoutError
overview: "Fix the LayoutError when margins exceed safe thresholds by: (1) tightening margin clamping in the backend, (2) lowering the HTML max attribute on margin inputs, (3) making content widths margin-aware instead of hardcoded, and (4) passing actual frame dimensions to the rack diagram generator."
todos:
  - id: tighten-clamp
    content: Raise MIN_FRAME_W/H in brand_compliance.py to 450/650 so 2" margins trigger clamping
    status: completed
  - id: ui-max
    content: Lower margin input max from 3 to 1.5 in advanced_config.html; update JS pre-flight check
    status: completed
  - id: frame-attrs
    content: Store self._frame_width / self._frame_height on VastReportBuilder from effective_margins after page template creation
    status: completed
  - id: content-widths
    content: Replace all hardcoded page_width / available_width calculations in report_builder.py with self._frame_width
    status: completed
  - id: rack-diagram-dims
    content: Pass actual frame dimensions to RackDiagram constructor so SVG scales to fit
    status: completed
  - id: verify
    content: Run tests, lint, and manual smoke test with 1.5" margins to confirm no LayoutError
    status: completed
isProject: false
---

# Fix Margin LayoutError

## Root Cause

The error `LayoutError: Flowable <Table ...> (540.0 x 618.0) too large in frame (307.3 x 553.9)` occurs because:

1. **Hardcoded content dimensions**: All table `colWidths` and the `RackDiagram` generator use hardcoded 0.5" margin assumptions, producing content 540pt wide regardless of actual margins.
2. **Rack diagram fixed size**: `RackDiagram.__init__` defaults to `page_width=7.27"`, `page_height=8.5"` -- these are never overridden by `report_builder.py`, so the drawing is always ~618pt tall.
3. **Weak clamping**: The `MIN_FRAME_W=300` / `MIN_FRAME_H=400` thresholds added earlier are below the 307x553 frame that 2" margins produce on A4, so clamping never triggers.
4. **Competing margin systems**: `BaseDocTemplate` and `PageTemplate.Frame` both define margins; the fix from earlier synced them via `effective_margins`, which is correct but insufficient when the frame is still too small for the hardcoded content.

## Fix Strategy (3 layers of defense)

### Layer 1: Tighten backend clamping (`brand_compliance.py`)

Raise `MIN_FRAME_W` to 450 and `MIN_FRAME_H` to 650. With 2" margins on A4 the frame would be 307x553, well below these thresholds, so clamping kicks in and resets to safe defaults. This guarantees the frame is always large enough for the current hardcoded content.

- File: `[src/brand_compliance.py](src/brand_compliance.py)` line 841-842

### Layer 2: Restrict UI margin inputs (`advanced_config.html`)

Lower the HTML `max` attribute on all four margin `<input>` fields from `3` to `1.5`. This prevents the user from even entering a value that would trigger backend clamping. Also update the JS pre-flight check thresholds to match.

- File: `[frontend/templates/advanced_config.html](frontend/templates/advanced_config.html)` lines 168, 172, 176, 180 and the JS block around line 688

### Layer 3: Make content widths margin-aware (`report_builder.py`)

Store the effective frame width/height as instance attributes after `create_vast_page_template` returns, then use them wherever content dimensions are currently hardcoded. This ensures content always fits the actual frame, regardless of margins.

Affected locations in `[src/report_builder.py](src/report_builder.py)`:

- **Line 1275**: `available_width = A4[0] - 1.0 * inch` -- replace with `self._frame_width`
- **Line 2693**: `colWidths=[page_width - (2 * 0.5 * inch)]` (rack diagram wrapper table) -- replace with `self._frame_width`
- **Line 2643-2647**: `RackDiagram(rack_height_u=...)` -- pass `page_width=self._frame_width`, `page_height=self._frame_height` so the SVG drawing itself scales down to fit
- **Lines 3050, 3160**: `page_width = A4[0] - 1.0 * inch` (CNode/DNode tables) -- replace with `self._frame_width`
- **Lines 3694-3705**: Network diagram `available_width` / `available_height` -- replace with `self._frame_width` / `self._frame_height`

The `_frame_width` and `_frame_height` attributes are derived from `effective_margins` right after the page template is created (around line 498).
