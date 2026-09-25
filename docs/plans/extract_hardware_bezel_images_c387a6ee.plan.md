---
name: Extract Hardware Bezel Images
overview: Extract front-bezel images for all CBoxes, DBoxes, and switches from the reference composite image, crop and scale them to consistent rack-diagram-ready dimensions, and save with the project's naming convention.
todos:
  - id: crop-cboxes
    content: "Crop front bezel images for 6 CBox variants: SMC Gen5 (update), HPE Genoa (update), HPE IceLake (new), Dell IceLake (new), Dell Turin (new), SMC Turin (new)"
    status: completed
  - id: crop-dboxes
    content: "Crop front images for DBoxes: Maverick/MLK 2U (update), Ceres 1U (update, shared by sanmina/dbox-515/ceres_v2)"
    status: completed
  - id: crop-switches
    content: "Crop port-side images for all switches: SN2100, SN2700, SN3700, SN4600C, SN4600, SN5600 (new), Arista CX4 (new), Arista DX4 (new), Arista DX5 (update)"
    status: completed
  - id: update-mappings
    content: Update image_map in rack_diagram.py, network_diagram.py, and _get_builtin_devices() in app.py for new entries (dell_turin_cbox, smc_turin_cbox, hpe_il_cbox, dell_il_cbox, sn5600, arista variants)
    status: completed
isProject: false
---

# Extract Hardware Bezel Images from Reference

## Current State

**Existing images** in `assets/hardware_images/` vary widely in quality:

- Very small: `supermicro_gen5_cbox_1u.png` (120x12), `ceres_v2_1u.png` (121x11), `maverick_2u.png` (120x21)
- Medium: `mellanox_msn3700_1x32p_200g_switch_1u.png` (242x22), `dell_il_cbox_2u.png` (242x44)
- High quality: `hpe_genoa_cbox.png` (1900x175), `arista_7060dx5_1x64p_800g_switch_2u.jpeg` (1900x350)

**Reference image** (`image-20251227-230229.png`) is a 2076x1338 composite containing front/rear views of all current deployment hardware.

## Target Dimensions

Based on rack diagram rendering (images scaled to `rack_width - 4` points) and the README recommendation of 800-1200px width:

- **1U devices**: 480 x 44 px (approx 10.9:1 aspect ratio matching 19" x 1.75")
- **2U devices**: 480 x 88 px (approx 5.5:1 aspect ratio matching 19" x 3.5")
- Format: PNG, RGBA mode (transparent background)

## Devices to Extract (Front Bezel Only)

### CBoxes (Compute Nodes) -- 6 devices

- `supermicro_gen5_cbox` / CBox / 1U / "Supermicro Gen5 CBox" -- **update** existing `supermicro_gen5_cbox_1u.png`
  - Source region: Gen5/SMC/CNode/EBox "SMC FRONT VIEW"
- `hpe_genoa_cbox` / CBox / 1U / "HPE Genoa CBox" -- **update** existing `hpe_genoa_cbox.png`
  - Source region: HPE Gen5 CNode "HPE DL325 GEN11 FRONT VIEW, WITH BEZEL"
- `hpe_il_cbox` / CBox / 2U / "HPE IceLake 2U CBox" -- **NEW** file `hpe_il_cbox_2u.png`
  - Source region: HPE ICELAKE "HP ICELAKE FRONT VIEW"
- `dell_il_cbox` / CBox / 2U / "Dell IceLake 2U CBox" -- **update** existing `dell_il_cbox_2u.png`
  - Source region: DELL ICELAKE "DELL ICELAKE FRONT VIEW"
- `dell_turin_cbox` / CBox / 1U / "Dell Gen6 CBox" -- **NEW** file `dell_turin_cbox_1u.png`
  - Source region: Gen6 DELL TURIN CNode "DELL TURIN (PowerEdge R6715) Front w/bezel"
- `smc_turin_cbox` / CBox / 1U / "SMC Gen6 CBox" -- **NEW** file `smc_turin_cbox_1u.png`
  - Source region: Gen6 SMC TURIN CNode "SMC TURIN DG5-1115C5-Th80 Front w/bezel"

### DBoxes (Storage/Data Nodes) -- 2 images, 4 keys

Two distinct front-view images map to four identifier keys:

**Image 1 -- Maverick/MLK front (2U):**

- `maverick_1.5` / DBox / 2U / "Maverick 2U DBox" -- **update** existing `maverick_2u.png`
  - Source region: MAVERICK/MLK "MAVERICK & MLK FRONT"

**Image 2 -- Ceres front (1U), shared by three keys:**

- `sanmina` / DBox / 1U / "Ceres V1 1U DBox" -- points to `ceres_v2_1u.png` (update)
- `dbox-515` / DBox / 1U / "Ceres V1 1U DBox" -- points to `ceres_v2_1u.png` (update)
- `ceres_v2` / DBox / 1U / "Ceres V2 1U DBox" -- points to `ceres_v2_1u.png` (update)
  - Source region: CERES "Ceres v1 & v2" top image

### Switches (Port-Side View) -- 9 devices

**100Gb (existing, update):**

- `mellanox_msn2100_2x16p_100g_switch_1u.png` -- 1U, source: "Mellanox/Nvidia SN2100 100Gb 1pt"
- `mellanox_msn2700_1x32p_100g_switch_1u.png` -- 1U, source: "Mellanox/Nvidia SN2700 100Gb 32pt"
- `mellanox_msn4600C_1x64p_100g_switch_2u.png` -- 2U, source: "Mellanox/Nvidia SN4600C 100Gb 64pt"

**200Gb (existing, update):**

- `mellanox_msn3700_1x32p_200g_switch_1u.png` -- 1U, source: "Mellanox/Nvidia SN3700 200Gb 32pt"
- `mellanox_msn4600_1x64p_200g_switch_2u.png` -- 2U, source: "Mellanox/Nvidia SN4600 200Gb 64pt"

**200/400Gb (new + update):**

- `arista_7060cx4_1x24p_400g_switch_2u.png` -- 2U, **NEW**, source: "Arista DCS-7060CX4-24D8-F"
- `arista_7060dx4_1x25p_400g_switch_2u.png` -- 2U, **NEW**, source: "Arista DCS-7060DX4-S25-F"
- `arista_7060dx5_1x64p_800g_switch_2u.jpeg` -- 2U, **update**, source: "Arista DCS-7060DX5-64S-F"

**800Gb (new):**

- `mellanox_sn5600_1x64p_800g_switch_2u.png` -- 2U, **NEW**, source: "Mellanox/Nvidia SN5600 800Gb 64pt"

## Implementation Approach

1. Use Python PIL to crop each front-bezel region from the 2076x1338 composite
2. For each crop: trim whitespace, resize to standard dimensions (480x44 for 1U, 480x88 for 2U), save as PNG/RGBA
3. New devices: add entries to `image_map` in [src/rack_diagram.py](src/rack_diagram.py) and [src/network_diagram.py](src/network_diagram.py)
4. New devices: add entries to `_get_builtin_devices()` in [src/app.py](src/app.py) and to `_get_device_height_units()` patterns
5. Existing devices: replace image files in place (same filenames, better quality)

## Summary of Changes

- **6 new image files**: `hpe_il_cbox_2u.png`, `dell_turin_cbox_1u.png`, `smc_turin_cbox_1u.png`, `arista_7060cx4_1x24p_400g_switch_2u.png`, `arista_7060dx4_1x25p_400g_switch_2u.png`, `mellanox_sn5600_1x64p_800g_switch_2u.png`
- **11 updated image files**: all remaining existing images re-extracted at 480px wide
- **Code changes**: new device keys added to rack_diagram.py, network_diagram.py, and app.py

