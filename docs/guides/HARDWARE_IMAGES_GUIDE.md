# Hardware Images for Rack Diagrams - Implementation Guide

## Overview

The VAST As-Built Report Generator now supports using actual hardware images in the Physical Rack Layout diagrams. This feature automatically detects and loads hardware images from a library directory, falling back to colored rectangles if images are not available.

## Implementation Summary

### Architecture

**Image Library System**:
- Hardware images stored in: `assets/hardware_images/`
- Images loaded at RackDiagram initialization
- Automatic model name matching
- Graceful fallback to colored rectangles

**Supported Features**:
- PNG image format (with transparency)
- 1U and 2U device heights
- Automatic scaling to fit rack space
- Model name pattern matching
- Maintains aspect ratio

## How to Add Hardware Images

### Step 1: Prepare the Image

From the provided Supermicro Gen5 CBox image, follow these guidelines:

**Image Requirements**:
- Format: PNG (preferred) or JPG
- View: Front panel of the hardware
- Background: Transparent or white
- Quality: High resolution (800-1200px width recommended)
- Aspect Ratio: Match physical hardware (1U = ~1.75" height, 19" width ratio)

### Step 2: Save the Image

Save the hardware image with the correct naming convention:

```bash
# Naming format: {model_name}_{height}u.png

# For the Supermicro Gen5 CBox (provided image):
cp supermicro_gen5_cbox_image.png \
   assets/hardware_images/supermicro_gen5_cbox_1u.png

# For other hardware:
# assets/hardware_images/ceres_v2_1u.png
# assets/hardware_images/supermicro_2u_cbox_2u.png
```

### Step 3: Verify Image is Detected

Run the report generator and check the logs:

```bash
python3 -m src.main --cluster-ip <IP> --username <USER> --password <PASS>

# Look for log messages like:
# [INFO] Loaded hardware image for supermicro_gen5_cbox: .../supermicro_gen5_cbox_1u.png
```

## Technical Implementation

### Code Changes Made

**1. Image Loading System** (`rack_diagram.py`):
```python
# Initialize hardware image cache
self.hardware_images = self._load_hardware_images()

# Load images from library directory
HARDWARE_IMAGE_DIR = Path(__file__).parent.parent / "assets" / "hardware_images"
```

**2. Image Rendering** (`_create_device_representation`):
- Checks if hardware image exists for model
- Uses `reportlab.graphics.shapes.Image` to render
- Scales image to fit 1U or 2U rack space
- Falls back to colored rectangle if image not found or fails to load

**3. Model Name Matching**:
- Exact match: `supermicro_gen5_cbox` → `supermicro_gen5_cbox_1u.png`
- Partial match: Model containing "supermicro_gen5_cbox" uses the image
- Case-insensitive matching

### Enhanced Rack Diagram Features

**Visual Improvements**:
- Rack posts (dark gray) on sides
- Mounting holes at every U position
- Bold U number labels
- Professional appearance matching real data center racks
- Larger scale (95%) to fill available space

**Current Specifications**:
- Page height: 8.5"
- Scale: 95% of available space
- Margins: 0.3" for optimal sizing
- 42U rack with accurate U divisions

## Model Name Reference

### CBox Models
| Model Name | Image Filename | Status |
|------------|----------------|--------|
| supermicro_gen5_cbox | `supermicro_gen5_cbox_1u.png` | ⏳ Pending (image provided by user) |
| supermicro_2u_cbox | `supermicro_2u_cbox_2u.png` | ❌ Not yet available |

### DBox Models
| Model Name | Image Filename | Status |
|------------|----------------|--------|
| ceres_v2 | `ceres_v2_1u.png` | ❌ Not yet available |
| dbox-515-* | `dbox_515_1u.png` | ❌ Not yet available |

### Switches
| Model Name | Image Filename | Status |
|------------|----------------|--------|
| (Future) | `switch_*_1u.png` | ❌ Not yet implemented |

## Example: Using the Provided Supermicro Image

The user has provided an image of the 1U Supermicro Gen5 CBox. To use it:

```bash
# 1. Save the image to the hardware images directory
mkdir -p assets/hardware_images
cp /path/to/supermicro_image.png assets/hardware_images/supermicro_gen5_cbox_1u.png

# 2. Generate a report
python3 -m src.main --cluster-ip 10.143.11.204 --username support --password 654321

# 3. Check the Physical Rack Layout on Page 6
# - CBoxes should now show the actual Supermicro hardware image
# - Image will be scaled to fit 1U rack space
# - Maintains aspect ratio and fits rack width
```

## Fallback Behavior

If no image is found:
- System falls back to colored rectangle
- Blue for CBox, Purple for DBox
- "HW" text icon displayed
- Status indicator (green dot) still shown
- Labels and connectors work the same

## Future Enhancements

### Planned Features
1. **SVG Support**: Vector graphics for perfect scaling
2. **Image Caching**: Performance optimization for large deployments
3. **Dynamic Image Downloads**: Fetch from VAST image repository
4. **Custom Overlay**: Add status LEDs, labels dynamically
5. **Switch Images**: Network switch hardware representations

### Image Library Expansion
- Create standardized hardware image library
- Professional photography of all VAST-supported hardware
- Consistent lighting and angle for all images
- Transparent backgrounds for clean integration

## Troubleshooting

### Image Not Loading

**Problem**: Image file exists but not being used

**Solutions**:
1. Check filename matches model name exactly
2. Verify image format (PNG recommended)
3. Check file permissions
4. Review logs for error messages
5. Ensure image is in correct directory

### Image Quality Issues

**Problem**: Image appears pixelated or distorted

**Solutions**:
1. Use higher resolution source image (1200px+ width)
2. Ensure aspect ratio matches physical hardware
3. Use PNG format for better quality
4. Verify transparent background works correctly

### Model Name Not Matching

**Problem**: Model name from API doesn't match image filename

**Solutions**:
1. Check actual model name in JSON data
2. Add model name to image map in `_load_hardware_images()`
3. Use partial matching by naming image with key portion of model name

## API for Custom Extensions

### Adding New Hardware Models

To add support for new hardware models programmatically:

```python
# In rack_diagram.py, modify _load_hardware_images():

image_map = {
    "supermicro_gen5_cbox": HARDWARE_IMAGE_DIR / "supermicro_gen5_cbox_1u.png",
    "ceres_v2": HARDWARE_IMAGE_DIR / "ceres_v2_1u.png",
    "your_new_model": HARDWARE_IMAGE_DIR / "your_new_model_1u.png",  # Add here
}
```

### Custom Image Processing

To add image preprocessing or overlays:

```python
# Extend _create_device_representation() method
# Add custom processing before GraphicsImage creation
```

## Conclusion

The hardware image library system provides a flexible, extensible way to create professional rack diagrams with actual hardware representations. As images are added to the library, reports will automatically become more detailed and accurate.

**Current Status**: ✅ Implementation Complete
- Image loading system functional
- Automatic detection and scaling
- Graceful fallback behavior
- Ready for Supermicro Gen5 CBox image

**Next Step**: Add the provided Supermicro Gen5 CBox image to `assets/hardware_images/supermicro_gen5_cbox_1u.png`
