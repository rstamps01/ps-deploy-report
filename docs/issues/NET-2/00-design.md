# NET-2 / NET-3 / NET-4: Logical Network Diagram Redesign — v1.5.8 Design Artifacts

**Status:** Design approved (mockups), implementation pending on `feature/v1.5.8-batch`. 
**Severity:** Medium — does not block report generation, but produces an inaccurate / partially-empty Logical Network Diagram for any cluster whose switches are manually placed across multiple racks (the standard 2-rack topology). 
**Discovered:** 2026-05-19 in v1.5.7 production deployment for cluster `m-pr-xpvast-a01`. 
**Related:** RPT-6 (rack diagram U-position parity for 2U+ manual switch placements). 
**Out of scope for:** SR-1, SR-3, SR-4, SR-5, TP-1, TP-2 (all v1.5.7).

---

## Symptom

End-to-end run on cluster `m-pr-xpvast-a01` (2 racks, 2 switches, 22 nodes, 44 port-map entries) produces a Logical Network Diagram with three observable problems:

1. **Both switches drawn in `H1U12`** even though `manual_switch_placements` says `sw1 → H1U12`, `sw2 → H1U11`. The vote-counting heuristic in `_assign_switches_to_racks` overrides the operator's manual rack assignment.
2. **20 of 44 edges silently dropped.** The renderer skips any port-map row whose switch is not on the same page as the device, so the 10 sw1↔CBox edges and 10 sw2↔DBox edges that were scheduled to render across racks never appear.
3. **A/B network designation no longer matches reality.** `vnetmap` reports each switch carrying both Network A and Network B traffic; the v1.5.7 classifier still labels every edge as one or the other based on a deprecated convention.

See [mockup-before.svg](mockup-before.svg) for the v1.5.7 broken state and [mockup-target.svg](mockup-target.svg) for the v1.5.8 target.

## Items in this batch

This design covers four related items, each tracked as an independent ID with its own TDD red→impl→commit cycle on the same `feature/v1.5.8-batch` branch:

| ID | Layer | Description |
|---|---|---|
| **RPT-6** | rack_diagram | Align manual switch U-position with Discovery UI convention (top-U vs bottom-U) |
| **NET-2A** | network_diagram_v2 | Honor `manual_switch_placements` for switch→rack assignment (replace vote-counting heuristic) |
| **NET-2B** | network_diagram_v2 | Render cross-rack switch-to-node edges (currently dropped); apply outer-side same-rack / inner-side cross-rack routing rule |
| **NET-3** | network_diagram_v2 | Subnet-based edge coloring (deprecate Network A/B classifier; color by switch's serviced /24 subnet) |
| **NET-4** | network_diagram_v2 | Mis-cabling detection: when a switch services nodes in multiple distinct /24 subnets, highlight offending nodes (red dashed outline + warning glyph) and render a "Cabling validation" banner |

## Mockups (operator-approved 2026-05-19)

- [mockup-before.svg](mockup-before.svg) — current v1.5.7 broken state, with red BUG callouts for: empty switch slot in H1U11, both switches stacked in H1U12, red bracket around CBoxes indicating 20 dropped edges, A/B-based legend.
- [mockup-target.svg](mockup-target.svg) — target v1.5.8 state with: manual switch placement honored, all 44 edges rendered (22 solid same-rack outer + 22 dashed cross-rack inner), subnet-based colors (`172.16.0.x` green for sw1, `172.16.64.x` blue for sw2), "Cabling validation: PASS" banner, dual legend (top swatches + bottom production-style pills).
- PNG snapshots regenerated via PyMuPDF at 1600×2200 alongside each SVG.

Both mockups are 800×1100 portrait, fitting the report's effective network diagram render area (~497×662 pt at 0.751 aspect, A4 portrait, 0.5in margins per [src/report_builder.py](../../../src/report_builder.py) lines 569-592, 3840-3859).

## Routing rule (NET-2B)

- **Same-rack edges**: solid line, exits OUTER side of device (left side for left-rack device, right side for right-rack device); curves up to the switch in the same column.
- **Cross-rack edges**: dashed line (`stroke-dasharray="6,4"`, opacity 0.55), exits INNER side of device (toward the inter-rack gutter); routes through the gutter to the switch in the other column.

This replaces the deprecated v1.5.7 convention where Network A always exited the left side and Network B always exited the right side regardless of switch position.

## Color rule (NET-3)

- Each switch IP is mapped to its serviced subnet (the most common `192.168.X.0/24`-equivalent prefix among the nodes connected to it).
- The lowest-IP switch's subnet gets `#0F9D58` (green); the next switch's subnet gets `#4285F4` (blue); subsequent switches cycle through a fixed palette.
- Edges to/from a switch use that switch's subnet color; the dash style encodes same-rack vs cross-rack but the color stays consistent within a subnet.
- IPL/MLAG retains `#7B1FA2` (purple) — unchanged.
- Network A/B classifier is removed from both colors and from the legend.

## Mis-cabling rule (NET-4)

- For each switch, collect the set of distinct /24-equivalent subnets across all of its connected nodes (using `port_map[*].node_ip` for the side that connected to that switch).
- A switch with `len(subnet_set) > 1` is considered mis-cabled.
- Each mis-cabled connection (the offending node ↔ switch edge) is rendered with the standard subnet color of the *node's* expected subnet, but the destination node box gets a red dashed outline and a small warning glyph.
- Above the diagram, a banner replaces "Cabling validation: PASS" (green) with "Cabling validation: N mis-cabled connection(s) detected" (red).

## Verification (planned)

1. **Offline replay** via `--from-json` against `import/Assets-2026-05-19/vast_data_m-pr-xpvast-a01_20260519_181453.json` (the v1.5.7 production fixture that exposed all 4 issues).
2. Cross-check against `import/Assets-2026-05-19/vnetmap_output_192.168.2.2_20260519_181335.txt` for switch-subnet mapping ground truth (sw1 reports `Switch 10.103.0.8 has {'172.16.0'}`; sw2 reports `Switch 10.103.0.9 has {'172.16.64'}`).
3. TDD red→impl→commit per item; all v1.5.8 items merge as a single PR `feature/v1.5.8-batch → develop` and ship as v1.5.8.

## Evidence

- `import/Assets-2026-05-19/vast_data_m-pr-xpvast-a01_20260519_181453.json` — v1.5.7 production JSON for cluster `m-pr-xpvast-a01`, 44-row `port_map`, 2 switches, 2 racks.
- `import/Assets-2026-05-19/vnetmap_output_192.168.2.2_20260519_181335.txt` — vnetmap ground truth confirming subnet-per-switch assignment.
- `import/Assets-2026-05-19/vast_asbuilt_report_m-pr-xpvast-a01_20260519_181453.pdf` — v1.5.7 production PDF showing the broken Logical Network Diagram and the production pill legend that this design extends.
