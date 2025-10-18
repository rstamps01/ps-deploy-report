# Logical Network Diagram Section - Implementation Guide

## Overview

A new **Logical Network Diagram** section has been added to the As-Built Report on **Page 8**, positioned between the Network Configuration section and the Logical Configuration section.

## Report Structure

```
Page 1: Title Page
Page 2: Executive Summary
Page 3: Cluster Information
Page 4-5: Hardware Inventory
Page 6: Physical Rack Layout
Page 7: Network Configuration
Page 8: Logical Network Diagram  ← NEW SECTION
Page 9: Logical Configuration
Page 10: Security & Authentication
```

## Section Content

### Heading
**"Logical Network Diagram"** - Level 1 heading with VAST brand styling

### Section Overview
Provides context explaining the purpose and value of the network topology diagram:

> "The Logical Network Diagram provides a visual representation of the cluster's network topology,
> illustrating the connectivity between compute nodes (CBoxes), data nodes (DBoxes), network switches,
> and the customer network. This diagram shows the redundant network paths, switch interconnections,
> and how data flows through the storage infrastructure. Understanding the logical network topology
> is essential for network planning, troubleshooting connectivity issues, validating redundancy
> configurations, and ensuring optimal network performance across the storage cluster."

### Diagram Title
**"Placeholder"** - Centered above the network diagram image

### Network Topology Image
- **File**: `assets/diagrams/network_topology_placeholder.png`
- **Size**: Automatically scaled to fit page with 0.5" margins
- **Aspect Ratio**: Maintained (proportional scaling)
- **Positioning**: Centered horizontally on page
- **Max Dimensions**:
  - Width: ~7.5 inches (90% of available width)
  - Height: ~5.5 inches (leaves room for heading and footer)

## Network Diagram Components

The diagram illustrates:

1. **CBox Nodes** (Blue rectangles):
   - CBox-1, CBox-2, CBox-3, CBox-4
   - Compute nodes containing CNodes

2. **DBox Nodes** (Green rectangles):
   - DBox-100, DBox-101, DBox-102, DBox-103
   - Data nodes containing storage

3. **Network Switches**:
   - **Switch A** (Red) - Primary switch with customer network connection
   - **Switch B** (Orange) - Secondary switch for redundancy

4. **Customer Network** (Cloud icon):
   - External connectivity point

5. **Network Connections**:
   - **Red lines**: Connections to Switch A
   - **Orange lines**: Connections to Switch B
   - **Black lines**: Inter-switch links for redundancy

## Adding the Network Diagram Image

### Quick Steps

1. **Save the image** as:
   ```
   network_topology_placeholder.png
   ```

2. **Place in directory**:
   ```
   /Users/ray.stamps/Documents/as-built-report/ps-deploy-report/assets/diagrams/
   ```

3. **Regenerate report**:
   ```bash
   cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report
   python3 -m src.main --cluster-ip 10.143.11.204 --username support --password 654321
   ```

4. **Check Page 8** for the network diagram

### Image Requirements

- **Format**: PNG (recommended), JPG also supported
- **Recommended Size**: 1200-1600px width for optimal quality
- **Transparent Background**: Optional but recommended
- **Color**: Full color diagram (as shown in provided image)

## Fallback Behavior

If the image file is not found:
- A placeholder box will be displayed instead
- Log message: "Network diagram not found at ..., using placeholder"
- Placeholder shows: "Network Topology Diagram" with descriptive text
- Report generation continues successfully

## Technical Implementation

### Code Location
- **Method**: `_create_logical_network_diagram()` in `src/report_builder.py`
- **Line**: ~1896-2034

### Integration Point
- Called between Network Configuration and Logical Configuration
- Added at line ~235 in `_generate_with_reportlab()` method

### Key Features
- Automatic image detection
- Graceful degradation to placeholder
- Centered layout with proper spacing
- Maintains aspect ratio
- Section overview for context

## Customization

### Change Diagram Title
Edit line ~1966 in `report_builder.py`:
```python
content.append(Paragraph("Placeholder", title_style))
```
Change `"Placeholder"` to your desired title.

### Adjust Image Size
Edit lines ~1971-1977 in `report_builder.py`:
```python
if self.config.page_size == "Letter":
    page_width = 8.5 * inch
else:
    page_width = 595.27

available_width = page_width - (2 * 0.5 * inch)
max_height = 5.5 * inch
```

### Change Image Filename
Edit line ~1947-1952 in `report_builder.py`:
```python
diagram_path = (
    Path(__file__).parent.parent
    / "assets"
    / "diagrams"
    / "network_topology_placeholder.png"  # Change filename here
)
```

## Troubleshooting

### Image Not Appearing

1. **Check filename**:
   ```bash
   ls -la assets/diagrams/network_topology_placeholder.png
   ```

2. **Verify file permissions**:
   ```bash
   chmod 644 assets/diagrams/network_topology_placeholder.png
   ```

3. **Check logs**:
   Look for: `"Added network topology diagram from"` or `"Network diagram not found"`

4. **Verify path**:
   Ensure file is in correct directory relative to `src/report_builder.py`

### Image Quality Issues

- Use higher resolution source image (1600px+ width recommended)
- Save as PNG for best quality
- Ensure sufficient contrast for printing
- Verify colors are not too light/faded

## Future Enhancements

Potential improvements:
1. Dynamic diagram generation from cluster data
2. Multiple diagram types (physical, logical, data flow)
3. Interactive elements (for HTML/web version)
4. Automatic labeling of nodes from inventory data
5. Color-coding based on node status

## Related Documentation

- `assets/diagrams/README.md` - Diagrams directory documentation
- `assets/diagrams/INSTRUCTIONS.md` - Step-by-step image saving guide
- `PROJECT_STRUCTURE.md` - Overall project organization

---

**Status**: ✅ **Implemented and Ready**
**Page**: 8 (Logical Network Diagram)
**Awaiting**: Network topology diagram image file
