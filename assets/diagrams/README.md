# Network Diagrams

This directory contains network topology diagrams used in the As-Built Report.

## Current Diagrams

### network_topology_placeholder.png
**Location**: Page 8 - Logical Network Diagram section
**Purpose**: Visual representation of cluster network topology

**Shows**:
- CBox nodes (blue rectangles) - Compute nodes
- DBox nodes (green rectangles) - Data nodes
- Switch A (red) and Switch B (orange) - Network switches
- Customer Network (cloud) - External connectivity
- Connection topology between all components
- Redundant network paths (color-coded by switch)
- Inter-switch links (black lines)

**To Add This Diagram**:
1. Save the network topology image as: `network_topology_placeholder.png`
2. Place it in this directory (`assets/diagrams/`)
3. Regenerate the report

**Image Requirements**:
- Format: PNG (recommended), JPG also supported
- Recommended size: 1200-1600px width for optimal quality
- Transparent background: Optional but recommended
- Aspect ratio: Automatically maintained by report generator

## Adding More Diagrams

To add additional diagrams to the report:

1. Save diagram images in this directory
2. Update `src/report_builder.py` to reference the new diagram
3. Follow the same pattern as `_create_logical_network_diagram()` method

## Usage in Report

The diagram is automatically:
- Centered on the page
- Scaled to fit within margins
- Maintains aspect ratio
- Includes section overview description
- Titled "Placeholder" (can be customized)

## Troubleshooting

If diagram doesn't appear:
1. Check filename matches exactly: `network_topology_placeholder.png`
2. Verify file is in correct directory: `assets/diagrams/`
3. Check file permissions (should be readable)
4. Review report generation logs for errors
5. Fallback placeholder will display if image is missing
