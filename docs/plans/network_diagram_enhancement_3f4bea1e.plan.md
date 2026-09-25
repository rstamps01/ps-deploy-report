---
name: Network Diagram Enhancement
overview: Enhance the rack-centric network diagram SVG renderer to close visual and structural gaps between the current output and the approved Design 3 mockup.
todos:
  - id: t1-switch-filter
    content: Filter leaf switches to only those present in port_map switch_ip set; classify others as upstream/spine
    status: completed
  - id: t1-conn-routing
    content: "Fix connection routing: A-side to left edge -> SWA, B-side to right edge -> SWB, stagger mid_y per device index"
    status: completed
  - id: t2-switch-labels
    content: Use short designation labels (SWA/SWB) with hostname subtitle on switch boxes
    status: completed
  - id: t2-section-sep
    content: Add visible CNode/DNode section separator with dashed line and increased gap
    status: completed
  - id: t2-fill-colors
    content: Intensify CBox/DBox gradient fills for better visual differentiation
    status: completed
  - id: t2-conn-width
    content: Increase connection stroke width and add per-device bus stagger to prevent overlap
    status: completed
  - id: t3-upstream-row
    content: Optionally show non-leaf switches (client/upstream) in a separate tier above racks
    status: completed
  - id: t3-legend-style
    content: Polish legend pill badges with tinted fills
    status: completed
isProject: false
---

# Network Diagram Enhancement Plan

## Gap Analysis: Current Output vs. Mockup

Comparing the current render (image 1) against the approved Design 3 mockup (image 2), there are 9 discrepancies to address, grouped into three tiers.

---

### Tier 1 — Critical (connections and data fidelity)

**1. Connection lines are barely visible / misrouted**

- **Mockup**: Each CBox/DBox shows clear green (Network A) and blue (Network B) orthogonal lines running from the left/right edge of the device up to the corresponding switch (SWA / SWB). Lines are well separated, thick enough to see, and use distinct routing channels.
- **Current**: Lines are faint, very close together, and routed through the same narrow column on the left edge only. DNodes (dnode-3-105) show no connections at all.
- **Fix**: Offset Network A connections to the left edge and Network B connections to the right edge of each device box. Increase stroke width from 1.5 to 2.0. Route Network A lines to the left switch center and Network B lines to the right switch center. Add spacing between adjacent horizontal bus segments.

**2. Wrong switch shown as leaf — "SE-CLIENT-1-2" is not a VAST leaf switch**

- **Mockup**: Each rack shows only the VAST leaf switch pair (SWA / SWB).
- **Current**: "SE-CLIENT-1-2" (a client-facing upstream switch at `<ip>`) is placed as a leaf switch. It has no port_map entries connecting to CNodes/DNodes.
- **Fix**: Filter switches to only show those that appear in `port_map` as `switch_ip` (i.e., have at least one device connection). Non-participating switches should be excluded from the rack leaf pair (or optionally shown in the spine tier).

**3. Missing second leaf switch — "se-var-1-2" not shown**

- **Mockup**: Two leaf switches per rack (SWA + SWB with IPL badge).
- **Current**: Only two switches are placed in the rack, but one is the wrong client switch. The second VAST leaf `se-var-1-2` (<ip>) is missing from the rack.
- **Fix**: This is a consequence of issue 2 — once the switch filter is applied, `se-var-1-1` and `se-var-1-2` will both appear as the leaf pair.

---

### Tier 2 — Visual polish (layout and styling)

**4. Switch boxes too small / labels truncated**

- **Mockup**: Switch boxes are wide enough to show full "SWA" / "SWB" labels with icon detail.
- **Current**: Switch pair boxes are about 95px each (rack_w minus padding, divided by 2). "SE-CLIENT-..." is heavily clipped.
- **Fix**: Calculate `sw_pair_w` from the wider rack width (now DEVICE_W=180 + padding = 212). Each switch gets ~96px which is still tight. Either: (a) widen the rack to accommodate two SWITCH_W boxes, or (b) use short designation labels ("SWA" / "SWB") with hostname as a small subtitle beneath.

**5. No visible separator between CNode and DNode sections**

- **Mockup**: Has a clear "SEPARATOR" label and horizontal rule between CBox and DBox sections within each rack, plus section labels ("CNODE SECTION", "DNODE SECTION").
- **Current**: Only a faint 0.5px line and a small gap.
- **Fix**: Draw a 1px dashed separator line with an optional small "SEPARATOR" or divider label. Increase gap between sections from `DEVICE_GAP` to `DEVICE_GAP * 3`.

**6. Device fill colors need differentiation**

- **Mockup**: CBoxes use a distinct light-blue fill, DBoxes use orange/amber. Both have a clear visual identity.
- **Current**: CBoxes use `#e8f4fd` (very faint blue), DBoxes use `#fff3e0` (very faint orange). The difference is hard to see.
- **Fix**: Intensify the gradient fills: CBox gradient to a richer `#c8e6f8` bottom, DBox to `#ffe0b2` bottom. This keeps the same hue but increases saturation.

**7. Connection routing lacks channel separation**

- **Mockup**: Network A (green) and Network B (blue) lines use distinct horizontal channels, never overlapping. The orthogonal routing is clean with visible gaps between each device's connection pair.
- **Current**: All connections funnel through the same narrow vertical column near the left edge.
- **Fix**: Offset Network A exit point to device left edge (`dev_x + 8`) and route to SWA center. Offset Network B exit point to device right edge (`dev_x + dev_w - 8`) and route to SWB center. Use unique `mid_y` bus heights per device to prevent overlap (stagger by 3-4px per device index).

---

### Tier 3 — Nice to have

**8. No spine uplink dashed lines from leaf switches**

- **Mockup**: Dashed gray lines run from each leaf switch up to the spine tier.
- **Current**: The code exists but only triggers when `has_spine` is True. For this cluster with 3 switches, the client switch should appear as spine/upstream (if not filtered out entirely).
- **Fix**: Classify `SE-CLIENT-1-2` as an upstream switch. If the user has such switches, show them in a simplified "Upstream" row above the racks with dashed uplinks. This is optional and depends on whether the user wants client switches shown.

**9. Legend styling**

- **Mockup**: Legend uses colored filled badges with clear text labels.
- **Current**: Legend uses pill outlines with small colored circles — functional but less polished.
- **Fix**: Minor styling enhancement — fill the pill badges with a light tint of each color for better contrast.

---

## Recommended Implementation Order

Focus on Tier 1 first (fixes the broken diagram), then Tier 2 (makes it match the mockup).

All changes are in [src/network_diagram_v2.py](src/network_diagram_v2.py).
