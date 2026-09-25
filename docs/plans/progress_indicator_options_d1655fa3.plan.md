---
name: Progress Indicator Options
overview: Evaluate and recommend a visually compelling progress indicator for both Reporter and One-Shot run modes, considering available backend telemetry and UI consistency.
todos:
  - id: progress-ring-component
    content: Build reusable ProgressRing component with SVG segmented ring, percentage text, stopwatch timer (MM:SS), and CSS animations
    status: completed
  - id: reporter-integration
    content: Integrate ring into Reporter checklist flow with step-based percentage
    status: completed
  - id: oneshot-integration
    content: Integrate ring into One-Shot polling loop using operation_index/total_operations
    status: completed
  - id: completion-states
    content: Handle completion (checkmark), error (red), and cancelled states
    status: completed
isProject: false
---

# Progress Indicator for Reporter and One-Shot

## Available Progress Data

Understanding what the backend provides determines what we can render:

**One-Shot mode** (rich telemetry via `/advanced-ops/oneshot/status`):

- `state.phase` -- discrete phases: `validating`, `health_checks`, `operations`, `report`, `bundling`, `completed`
- `state.operation_index` / `state.total_operations` -- e.g., 3/7
- `state.current_operation` -- name of active operation
- Percentage can be computed: `(operation_index / total_operations) * 100`

**Reporter mode** (limited telemetry via `/generate/status`):

- Only `running: bool` and `result: object`
- No intermediate sub-step progress from the backend
- Checklist steps are known client-side: Pre-Validation, Report Generation, Health Check (3 discrete steps)
- Percentage can be approximated client-side from checklist step completion

---

## Recommended Option: Segmented Ring with Percentage

A **segmented arc/ring indicator** that combines the best of both approaches:

- A single SVG ring (approx 100x100px) displayed at the top of the progress area
- The ring is divided into **colored segments** matching the phases (e.g., teal for validation, blue for operations, green for report, orange for bundling)
- Each segment fills clockwise as that phase progresses
- A **percentage number** sits centered inside the ring (top line)
- A **stopwatch timer** (MM:SS) sits just below the percentage inside the ring (second line), tracking total elapsed time since the run started
- Below the ring, the current operation name is displayed as text
- On completion: ring fills to 100%, percentage changes to a checkmark, timer freezes at final elapsed time and remains visible

**Why this option:**

- Compact -- does not consume vertical space like a full-width bar
- Informative -- segments show which phase is active and how many remain
- Visually distinct from the existing phase pills (complements rather than replaces)
- Pure CSS + SVG -- no external libraries needed
- Works for both modes: One-Shot uses real data, Reporter uses step-based approximation

### Visual concept (Reporter mode, 3 segments)

```
        ╭───────╮
      ╱  ██████   ╲        Segment 1: Pre-Validation (done, green)
     │   67%       │       Segment 2: Report Gen (in progress, blue pulse)
     │  02:34      │       Stopwatch timer (MM:SS elapsed)
      ╲  ░░░░░░   ╱        Segment 3: Health Check (pending, grey)
        ╰───────╯
   Generating PDF report...
```

### Visual concept (One-Shot mode, dynamic segments)

```
        ╭───────╮
      ╱  ████░░   ╲        Segments map to phases
     │   43%       │       Filled proportional to operation_index/total_operations
     │  04:12      │       Stopwatch timer (MM:SS elapsed)
      ╲  ░░░░░░   ╱
        ╰───────╯
   vnetmap (3/7)
```

### Visual concept (completed state)

```
        ╭───────╮
      ╱  ██████   ╲        All segments filled green
     │    ✓        │       Checkmark replaces percentage
     │  06:47      │       Timer frozen at final elapsed time
      ╲  ██████   ╱
        ╰───────╯
   Completed
```

---

## Alternative Options Considered

### Option A: Animated Linear Progress Bar with Phase Markers

A horizontal bar spanning the tile width with tick marks at phase boundaries. The fill animates smoothly. Phase labels sit above the tick marks.

```
Pre-Val    Operations         Report    Bundle
  |  ████████████░░░░░░░░░░░░░  |  ░░░░  |
  0%              43%                    100%
```

- Pro: Familiar UX pattern, easy to read at a glance
- Pro: Phase markers show where you are in the pipeline
- Con: Takes full width, may feel generic
- Con: Harder to make visually "interesting"

### Option B: Stacked Phase Cards with Inline Progress

Each phase gets its own mini-card in a vertical stack. The active card expands slightly and shows an inline thin progress bar. Completed cards collapse with a checkmark.

```
  [check] Pre-Validation .......................... done
  [>>>  ] Operations ........ vnetmap (3/7) ...... 43%
  [     ] Report Generation
  [     ] Bundling
```

- Pro: Very readable, shows all phases at once
- Pro: Natural fit for the existing phase-pill layout (enhancement, not replacement)
- Con: Takes more vertical space
- Con: Less visually "innovative" -- closer to a checklist

### Option C: Radial Gauge with Needle

A half-circle speedometer-style gauge with the needle sweeping from 0% to 100%. Phase zones are color-banded on the arc. The current operation name appears below.

- Pro: Visually striking and unique
- Con: Half-circle wastes horizontal space
- Con: Harder to read precise progress
- Con: May feel over-designed for a dev tool

---

## Recommendation

**Go with the Segmented Ring (recommended option)** -- it is compact, informative, visually distinctive, and works well for both Reporter (3 segments) and One-Shot (dynamic segments based on selected operations). It can be implemented purely with SVG `stroke-dasharray` / `stroke-dashoffset` animation and requires no external dependencies.

For the Reporter mode, which lacks backend sub-step progress, the ring updates at checklist-step granularity: 0% -> 33% (pre-validation done) -> 67% (report done) -> 100% (health check done), with a pulsing animation on the active segment.

---

## Implementation Sketch (if approved)

### Files to modify

- [frontend/templates/reporter.html](frontend/templates/reporter.html) -- add SVG ring component, JS update logic, CSS animations

### Key implementation details

- SVG ring using `<circle>` elements with `stroke-dasharray` for segmentation
- CSS `@keyframes` for pulse animation on the active segment
- JS `ProgressRing` constructor/class encapsulating the SVG, percentage text, timer text, and update logic
- `ProgressRing.start()` -- begins the `setInterval` stopwatch (ticks every 1s, updates MM:SS display)
- `ProgressRing.update(percent, label)` -- updates ring fill and percentage text
- `ProgressRing.complete()` -- fills ring to 100%, replaces percentage with checkmark, freezes timer, turns ring green
- `ProgressRing.error()` -- turns active segment red, freezes timer
- `ProgressRing.reset()` -- clears ring, resets timer to 00:00
- Reporter mode: percentage computed client-side from checklist step index; `start()` called at beginning of `runReporterChecklist()`, `complete()`/`error()` at end
- One-Shot mode: percentage computed from `statusData.state.operation_index / statusData.state.total_operations`; `start()` called from `startOneShot()`, updated from `startOneShotPolling()` interval
- Ring placed inside existing `#oneShotProgress` div (One-Shot) and a new `#reporterProgress` div (Reporter)
- Both modes share the same `ProgressRing` implementation; each instantiates its own instance
