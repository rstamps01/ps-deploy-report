# VAST As-Built Report - Physical Rack Diagram Feature

## Overview

The Physical Rack Diagram feature generates visual representations of hardware placement in 42U data center racks. This feature automatically populates rack diagrams with CBox, DBox, and (future) Switch hardware based on inventory data collected from the VAST cluster API.

## Implementation Summary

### Phase 1: Rack Template
- Created a 42U rack diagram with proper aspect ratio (19" internal width × 73.5" internal height)
- Scaled to fit within available page space
- U numbering displayed on the left side (U1 at bottom, U42 at top - standard data center convention)
- Empty rack space shown with light gray background and subtle horizontal U division lines

### Phase 2: Device Representation
- **CBox**: Blue rectangle with "CPU" icon (compute representation) and green status indicator
- **DBox**: Purple rectangle with "HDD" icon (storage cylinder representation) and green status indicator
- **Switch**: Gray rectangle with "NET" icon (network representation) - ready for future implementation
- Green dot status indicator for ACTIVE/ONLINE devices

### Phase 3: Device Placement
- Parses inventory data from CBox and DBox sections
- Extracts `rack_u`, `id`, `model`, and `state` fields
- Determines device height (1U or 2U) based on model name
- Places devices at correct U positions:
  - **1U devices**: Occupy specified U position
  - **2U devices**: Occupy specified U position (top) and U-1 (bottom)
- Adds labels outside rack frame: "CBox-#" or "DBox-#"
- Connector lines from devices to labels (dashed lines)

### Phase 4: Page Layout
- Integrated into Hardware Summary section (Page 6)
- Heading: "Physical Rack Layout"
- Section overview description included
- Entire rack diagram fits on single page
- Graceful fallback to placeholder if rack position data not available

## Technical Architecture

### New Module: `src/rack_diagram.py`

#### Class: `RackDiagram`

**Purpose**: Generate visual 42U rack diagrams with automated hardware placement.

**Key Methods**:
- `__init__()`: Initialize rack diagram with proper scaling
- `_get_device_height_units(model)`: Determine device height (1U or 2U) from model name
- `_parse_rack_position(position)`: Parse rack position strings (e.g., "U17" → 17)
- `_create_empty_rack_background(drawing)`: Create 42U rack template with U divisions
- `_create_device_representation(drawing, device_type, device_id, u_position, u_height, status)`: Place device in rack
- `generate_rack_diagram(cboxes, dboxes)`: Generate complete rack diagram

**Constants**:
- `RACK_INTERNAL_HEIGHT = 73.5` inches
- `RACK_INTERNAL_WIDTH = 19.0` inches
- `U_HEIGHT = 1.75` inches
- Brand colors for CBox (blue), DBox (purple), Switch (gray)

### Integration: `src/report_builder.py`

**Modified Method**: `_create_hardware_inventory()`

**Changes**:
1. Imports `RackDiagram` module
2. Extracts rack position data from hardware inventory
3. Creates `RackDiagram` instance
4. Generates rack drawing with CBox and DBox data
5. Appends drawing to report content
6. Fallback to placeholder if rack data unavailable or error occurs

## Data Requirements

### CBox Data Structure
```python
{
    "id": "6",                      # CBox ID
    "model": "supermicro_gen5_cbox", # Model name (determines U height)
    "rack_u": "U25",                 # Rack position
    "state": "ACTIVE"                # Device status
}
```

### DBox Data Structure
```python
{
    "id": "1",                          # DBox ID
    "model": "dbox-515-25042300200055", # Hardware type (determines U height)
    "rack_u": "U4",                     # Rack position
    "state": "ACTIVE"                   # Device status
}
```

### API Endpoints Used
- `/api/v7/cnodes/` - CNode information
- `/api/v1/cboxes/` - CBox information (includes rack position)
- `/api/v7/dboxes/` - DBox information (includes rack position)

## Device Height Detection

### Current Mappings
- **1U Devices**:
  - `supermicro_gen5_cbox`
  - `ceres_v2`

- **2U Devices**:
  - `supermicro_2u_cbox` (example pattern)
  - Additional 2U patterns can be added as needed

### Default Behavior
- Unknown models default to **1U**
- Warning logged for unknown models

## Scaling and Layout

### Drawing Dimensions
- **Page width**: 7.5" (available content area)
- **Page height**: 9.5" (available content area)
- **Scale factor**: Calculated dynamically to fit rack with 75% scaling
- **Margins**: 0.5" on all sides for labels and spacing

### U Position Calculation
- **Formula**: `y = start_y + ((u_position - 1) * u_height)`
- **2U devices**: Start at specified U, extend downward to U-1
- **Example**: Device at U17 (2U) occupies U17 (top) and U16 (bottom)

## Visual Design

### Color Scheme (VAST Brand Compliance)
- **Rack frame**: `#2F2042` (VAST brand dark purple)
- **CBox**: `#1BA3D1` (VAST brand primary blue)
- **DBox**: `#7B68A6` (Purple for storage)
- **Switch**: `#808080` (Gray for network)
- **Status indicator**: `#06d69f` (Vivid green for active)
- **Empty rack**: `#F2F2F7` (Light gray)

### Labels
- **Position**: Outside rack frame (right side)
- **Format**: "CBox-#" or "DBox-#"
- **Font size**: 8pt
- **Connector**: Dashed line from device to label
- **Max height**: 1.5" (< 1U to prevent overlap)

### Icons
- **CBox (Compute)**: "CPU" text (placeholder for future icon)
- **DBox (Storage)**: "HDD" text (placeholder for future icon)
- **Switch (Network)**: "NET" text (placeholder for future icon)

## Future Enhancements

### Switches
- Typically positioned in middle of rack
- 1U space above and below switches (separation from CBox/DBox)
- Leaf and spine switches visually distinguished
- Implementation ready, pending switch inventory data

### Multiple Racks
- One rack per page
- Automatic page breaks for additional racks
- Rack numbering/labeling for multi-rack deployments

### Hardware Images
- Replace text icons with actual hardware images
- Images scaled to fit 1U or 2U dimensions
- Maintain aspect ratio with `kind='proportional'`

### Enhanced Status Indicators
- Color-coded status: Green (active), Red (offline), Yellow (warning)
- Multiple indicators per device (power, network, health)

### Interactive Features
- Clickable devices linking to detailed specs
- Hover tooltips with device information
- (Requires HTML/interactive PDF format)

## Testing

### Test Cluster: selab-var-204
- **CBoxes**: 3 devices (supermicro_gen5_cbox, 1U)
- **DBoxes**: 2 devices (dbox-515-25042300200055, 1U)
- **Rack positions**: U4, U7, U25, U38, U41

### Validation Checklist
✅ Rack diagram renders on Page 6
✅ U numbering on left side (U1 bottom, U42 top)
✅ CBoxes displayed with blue color and CPU icon
✅ DBoxes displayed with purple color and HDD icon
✅ Green status indicators on all devices
✅ Labels positioned outside rack with connectors
✅ Empty rack space shown with gray background
✅ U divisions visible throughout rack
✅ Diagram fits within page boundaries
✅ No device overlap or positioning errors

## Error Handling

### Graceful Degradation
1. **Missing rack position data**: Falls back to placeholder message
2. **Invalid U position**: Logs warning, skips device
3. **Unknown model**: Defaults to 1U, logs warning
4. **Drawing too large**: Automatically scales to fit
5. **API errors**: Falls back to placeholder with error message

### Logging
- **INFO**: Successful diagram generation with device counts
- **WARNING**: Unknown models, missing positions, data issues
- **ERROR**: Critical failures, fallback to placeholder

## Configuration

### Modifying Rack Dimensions
Edit constants in `src/rack_diagram.py`:
```python
RACK_INTERNAL_HEIGHT = 73.5  # inches
RACK_INTERNAL_WIDTH = 19.0   # inches
U_HEIGHT = 1.75              # inches per U
```

### Adding New Device Models
Edit `_get_device_height_units()` method:
```python
one_u_models = [
    "supermicro_gen5_cbox",
    "ceres_v2",
    "your_new_1u_model",  # Add here
]

two_u_models = [
    "supermicro_2u_cbox",
    "your_new_2u_model",  # Add here
]
```

### Adjusting Colors
Edit color constants in `RackDiagram` class:
```python
CBOX_COLOR = HexColor("#1BA3D1")  # CBox color
DBOX_COLOR = HexColor("#7B68A6")  # DBox color
STATUS_ACTIVE = HexColor("#06d69f")  # Status color
```

## Dependencies

### Required Packages
- `reportlab` - PDF generation and graphics
- `reportlab.graphics.shapes` - Drawing shapes and lines
- `reportlab.lib.colors` - Color handling

### Internal Modules
- `src.brand_compliance` - VAST brand colors and styling
- `src.utils.logger` - Logging infrastructure

## Conclusion

The Physical Rack Diagram feature successfully provides automated visual representation of VAST cluster hardware deployment in data center racks. The implementation follows VAST brand guidelines, uses accurate physical dimensions, and provides a solid foundation for future enhancements including switches, multiple racks, and hardware images.

**Status**: ✅ MVP Complete - All 4 phases implemented and tested

**Next Steps**:
1. Gather user feedback on diagram appearance and accuracy
2. Add switch support when inventory data becomes available
3. Implement hardware images to replace text icons
4. Support multi-rack deployments if needed
