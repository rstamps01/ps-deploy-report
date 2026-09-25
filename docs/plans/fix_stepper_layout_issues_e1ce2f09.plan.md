---
name: Fix stepper layout issues
overview: "Fix two layout bugs: Cancel button overlapping View PDF in the stepper bar, and the Edit Placements button appearing to float."
todos:
  - id: fix-cancel-btn
    content: "Fix Cancel button position: wrap Run+Cancel in same container, remove absolute positioning"
    status: completed
  - id: fix-edit-placement
    content: "Fix Edit Placements button layout: ensure proper anchoring within rpt-section"
    status: completed
isProject: false
---

# Fix Stepper Bar and Placement Summary Layout

## Issue 1: Cancel Button Covers View PDF

**Root cause:** The Cancel button has `position:absolute; left:50%; transform:translateX(-50%)` which makes it overlay the View PDF button when visible.

**Fix:** Remove absolute positioning. Instead, show Cancel in the same slot as the Run button by hiding Run and showing Cancel in-place. Both buttons share the same grid/flex position.

**File:** [frontend/templates/reporter.html](frontend/templates/reporter.html), line 214

- Wrap Run + Cancel in a single container div so they swap in-place
- Remove `position:absolute; left:50%; transform:translateX(-50%)` from Cancel

## Issue 2: Edit Placements Button Floating

**Root cause:** The `.placement-summary` has `margin-top: 8px` and the button has `margin-left: auto`, but the entire `rpt-section` sits inside `panel-flex-left` which now shares space with the 200px progress column. The summary box may appear disconnected visually.

**Fix:** Ensure the placement summary is anchored properly within its section, and the button is right-aligned within the row. Add `width: 100%` or remove any float that could cause misalignment.
