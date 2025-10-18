# Hardware Images for Rack Diagrams

This directory contains hardware images used to populate the Physical Rack Layout diagrams in VAST As-Built Reports.

## Adding Hardware Images

To add a hardware image for automatic use in rack diagrams:

1. **Prepare the Image**:
   - Image should show the front panel view of the hardware
   - Recommended format: PNG with transparent background
   - Image should be clear and high quality
   - Aspect ratio should match the actual hardware (e.g., wide and short for 1U devices)

2. **Name the Image File**:
   - Use the model name from the API as the base filename
   - Add the U height suffix
   - Format: `{model_name}_{height}u.png`

   Examples:
   - `supermicro_gen5_cbox_1u.png` - 1U Supermicro Gen5 CBox
   - `ceres_v2_1u.png` - 1U Ceres v2 DBox
   - `supermicro_2u_cbox_2u.png` - 2U Supermicro CBox

3. **Place the Image**:
   - Copy the image file to this directory (`assets/hardware_images/`)
   - The rack diagram generator will automatically detect and use it

4. **Verify**:
   - Run the report generator
   - Check the logs for messages like: `Loaded hardware image for {model}: {path}`
   - If no image is found, the system will fall back to colored rectangles

## Current Hardware Images

### CBoxes (Compute Nodes)
- [ ] `supermicro_gen5_cbox_1u.png` - Supermicro Gen5 CBox (1U)
- [ ] Add more as needed

### DBoxes (Data Nodes)
- [ ] `ceres_v2_1u.png` - Ceres v2 DBox (1U)
- [ ] Add more as needed

### Switches
- [ ] Add switch images as needed

## Image Specifications

**Recommended Image Dimensions**:
- 1U devices: Width proportional to rack width (19"), height ~1.75" aspect ratio
- 2U devices: Same width, double the height (~3.5" aspect ratio)
- Suggested pixel dimensions: 800-1200px width for good quality

**Image Quality**:
- PNG format preferred (supports transparency)
- Minimum 150 DPI for print quality
- Transparent or white background
- Clear view of front panel details (LEDs, labels, ports)

## How It Works

The rack diagram generator:
1. Checks this directory for images matching the hardware model name
2. If found, uses the actual hardware image in the rack diagram
3. If not found, falls back to colored rectangles with icons
4. Scales images automatically to fit the rack space (1U or 2U height)

## Example: Adding the Supermicro Gen5 CBox Image

The user has provided an image of the Supermicro Gen5 CBox. To use it:

```bash
# Save the image as:
assets/hardware_images/supermicro_gen5_cbox_1u.png

# The rack diagram will automatically detect and use it for any device with model name containing "supermicro_gen5_cbox"
```

## Notes

- Images are cached when the RackDiagram object is initialized
- If you add new images, restart the report generator to load them
- Images should accurately represent the hardware to maintain report professional appearance
- Future enhancement: Support for SVG images for scalable vector graphics
