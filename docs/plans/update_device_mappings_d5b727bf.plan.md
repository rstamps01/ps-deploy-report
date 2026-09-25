---
name: Update device mappings
overview: Update identifier keys, image mappings, and re-extract the correct Ceres front bezel image across rack_diagram.py, network_diagram.py, and app.py.
todos:
  - id: re-extract-ceres
    content: Re-extract Ceres front bezel (V logo, 1U) from composite at correct position (~y:748-782) and save as ceres_v2_1u.png
    status: completed
  - id: update-sanmina
    content: Change sanmina from 1U/Ceres to 2U/Maverick in all three source files
    status: completed
  - id: rename-hpe-key
    content: Rename hpe_il_cbox to hpe_icelake in all three source files
    status: completed
  - id: rename-dell-key
    content: Rename dell_il_cbox to dell_icelake in all three source files
    status: completed
  - id: update-add-dbox
    content: Update dbox-515 description and add dbox-516 entry in all three source files
    status: completed
isProject: false
---

# Update Device Mappings and Re-extract Ceres Image

## Changes Summary

### 1. Re-extract Ceres front bezel image

The current `ceres_v2_1u.png` was cropped from the wrong region (y=650-678, which is a rear panel). The correct "Ceres v1 & v2" front bezel with the VAST V logo is located directly below the CERES heading in the composite, at approximately **y=748-782** (x:830-1220). This needs to be re-cropped, resized to 480x44 (1U target), and saved as `ceres_v2_1u.png`.

### 2. Sanmina: Change from 1U Ceres to 2U Maverick

- **Key**: `sanmina`
- **Change**: DBox / 1U / ceres_v2_1u.png --> DBox / 2U / maverick_2u.png
- Files: [rack_diagram.py](src/rack_diagram.py), [network_diagram.py](src/network_diagram.py), [app.py](src/app.py)
- Also move `"sanmina"` from `one_u_models` to `two_u_models` in `_get_device_height_units()`

### 3. Rename HPE IceLake key: `hpe_il_cbox` --> `hpe_icelake`

- Image filename stays `hpe_il_cbox_2u.png` (no file rename)
- Update the key in all three `image_map` dicts and `_get_builtin_devices()`
- Update `two_u_models` list in `_get_device_height_units()`

### 4. Rename Dell IceLake key: `dell_il_cbox` --> `dell_icelake`

- Image filename stays `dell_il_cbox_2u.png` (no file rename)
- Update the key in all three `image_map` dicts and `_get_builtin_devices()`
- Update `two_u_models` list in `_get_device_height_units()`

### 5. Update dbox-515 description (from previous request)

- In `_get_builtin_devices()`: Change description from "Ceres V1 DBox-515" to "Ceres V2 1U DBox"

### 6. Add dbox-516 entry (from previous request)

- Add `"dbox-516"` mapping to `ceres_v2_1u.png` in all three files
- Add to `one_u_models` in `_get_device_height_units()`
- Add to `_get_builtin_devices()` with description "Ceres V2 1U DBox"

## Files Modified

- [src/rack_diagram.py](src/rack_diagram.py) -- `image_map`, `_get_device_height_units()`
- [src/network_diagram.py](src/network_diagram.py) -- `image_map`
- [src/app.py](src/app.py) -- `_get_builtin_devices()`
- `assets/hardware_images/ceres_v2_1u.png` -- re-extracted from composite

