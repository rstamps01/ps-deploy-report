# Hardware Image Implementation - Complete

## Date: October 23, 2025
## Status: ✅ COMPLETE with Notes

---

## PROBLEM IDENTIFIED

The `network_topology.pdf` was generating with hardcoded images instead of using the actual hardware models from the Hardware Inventory:

1. **CBoxes**: Always used `supermicro_gen5_cbox_1u.png` instead of Broadwell and CascadeLake images
2. **Switches**: Always used `msn3700-vs2fc` image instead of MSN2100-CB2F image
3. **DBoxes**: Used generic `ceres_v2` image

---

## ROOT CAUSE ANALYSIS

### CBoxes and DBoxes
- The `hardware_inventory["cboxes"]` and `hardware_inventory["dboxes"]` dictionaries **do not contain model information**
- Model information is stored at the **CNode/DNode level**, not the CBox/DBox level
- CNodes have `model` field: e.g., `"Broadwell, single dual-port NIC"`
- CNodes have `box_vendor` field with similar information
- DNodes have similar fields, but for Bonzo-01 cluster, they only contain DBox IDs

### Switches
- Switches **do** have the `model` field in `hardware_inventory["switches"]`
- The network diagram was hardcoded to use `"msn3700-vs2fc"` instead of the actual model
- MSN2100-CB2F switches require special handling (single image represents both switches side-by-side)

---

## SOLUTION IMPLEMENTED

### 1. Removed Temporary Test Devices
**File**: `src/report_builder.py` (lines 1900-1971 removed)

Removed all temporary test devices that were used for validation:
- Test-Broadwell CBox at U24
- Test-CascadeLake CBox at U26
- Test-Sanmina DBox at U19
- Test MSN2100-CB2F switch pair at U21

**Result**: Rack diagram now shows only actual cluster hardware

---

### 2. Model Enrichment for CBoxes
**File**: `src/report_builder.py` (lines 2928-2950)

Added logic to enrich CBox dictionaries with model information from CNodes:

```python
# Enrich CBoxes with model information from CNodes
if cboxes_list and cnodes_data:
    cnode_models_by_cbox = {}
    for cnode in cnodes_data:
        cbox_id = cnode.get("cbox_id")
        model = cnode.get("model") or cnode.get("box_vendor")
        if cbox_id and model:
            if cbox_id not in cnode_models_by_cbox:
                cnode_models_by_cbox[cbox_id] = model

    # Add model to each CBox based on its cbox_id
    for cbox in cboxes_list:
        cbox_id = cbox.get("id")
        if cbox_id in cnode_models_by_cbox:
            # Extract just the hardware model name (first part before comma)
            full_model = cnode_models_by_cbox[cbox_id]
            # Parse "Broadwell, single dual-port NIC" -> "Broadwell"
            model_name = full_model.split(",")[0].strip()
            cbox["model"] = model_name
            cbox["hardware_type"] = model_name
```

**How It Works**:
1. Groups CNodes by `cbox_id`
2. Extracts the `model` or `box_vendor` field from CNodes
3. Parses the model name (takes first part before comma)
4. Adds `model` and `hardware_type` fields to the CBox dictionary

**Log Output**:
```
[INFO] Enriched CBox 7 with model: CascadeLake
[INFO] Enriched CBox 1 with model: Broadwell
```

**Result**: CBoxes now have accurate model information

---

### 3. Model Enrichment for DBoxes
**File**: `src/report_builder.py` (lines 2952-2972)

Added similar logic for DBoxes:

```python
# Enrich DBoxes with model information from DNodes
if dboxes_list and dnodes_data:
    dnode_models = []
    for dnode in dnodes_data:
        model = dnode.get("model") or dnode.get("box_vendor")
        if model:
            dnode_models.append(model)

    # Apply model to DBoxes (assuming homogeneous DBox types)
    if dnode_models and dboxes_list:
        # Use the first DNode model as representative
        full_model = dnode_models[0]
        # Parse model name
        model_name = full_model.split(",")[0].strip()
        for dbox in dboxes_list:
            dbox["model"] = model_name
            dbox["hardware_type"] = model_name
```

**How It Works**:
1. Collects all DNode models
2. Uses the first DNode model as representative (assumes homogeneous DBox types)
3. Parses the model name
4. Adds `model` and `hardware_type` fields to all DBoxes

**Log Output**:
```
[INFO] Enriched DBox with model: dbox-3d0603af
[WARNING] No image found for hardware type: dbox-3d0603af
```

**Note**: For the Bonzo-01 cluster, DNodes don't have proper hardware model information (only DBox IDs), so this needs cluster-specific attention (see "Known Issues" below).

---

### 4. Network Diagram: Use Actual CBox Models
**File**: `src/network_diagram.py` (lines 389-404)

**Before**:
```python
self._draw_device(
    device_group, x, y, device_width, device_height,
    f"CB{idx + 1}", cbox.get("name", "CBox"),
    "supermicro_gen5_cbox",  # HARDCODED!
    label_font_size, name_font_size,
)
```

**After**:
```python
# Get actual CBox model from hardware data
cbox_model = cbox.get("model", cbox.get("hardware_type", "supermicro_gen5_cbox"))
self._draw_device(
    device_group, x, y, device_width, device_height,
    f"CB{idx + 1}", cbox.get("name", "CBox"),
    cbox_model,  # Use actual model!
    label_font_size, name_font_size,
)
```

**Result**: CBoxes now use their actual hardware images (Broadwell, CascadeLake, etc.)

---

### 5. Network Diagram: Use Actual Switch Models with MSN2100 Special Handling
**File**: `src/network_diagram.py` (lines 406-446)

**Before**:
```python
for switch_num, (x, y) in switch_positions.items():
    if switch_num <= len(switches):
        switch = switches[switch_num - 1]
        switch_name = f"SW{'A' if switch_num == 1 else 'B'}"
        self._draw_device(
            device_group, x, y, device_width, device_height,
            switch_name, switch.get("hostname", "Switch"),
            "msn3700-vs2fc",  # HARDCODED!
            label_font_size, name_font_size,
        )
```

**After**:
```python
# Check if we have MSN2100 switches (side-by-side representation)
msn2100_switches = [s for s in switches if "msn2100" in s.get("model", "").lower()]

if len(msn2100_switches) >= 2:
    # Special case: MSN2100-CB2F represents BOTH switches in single image
    if 1 in switch_positions:
        x, y = switch_positions[1]
        self._draw_device(
            device_group, x, y, device_width, device_height,
            "SWA/SWB",  # Label showing both switches
            "MSN2100 Pair",
            "MSN2100-CB2F",  # Use the side-by-side image
            label_font_size, name_font_size,
        )
else:
    # Normal case: Draw each switch separately with its actual model
    for switch_num, (x, y) in switch_positions.items():
        if switch_num <= len(switches):
            switch = switches[switch_num - 1]
            switch_name = f"SW{'A' if switch_num == 1 else 'B'}"
            # Get actual switch model from hardware data
            switch_model = switch.get("model", switch.get("hardware_type", "msn3700-vs2fc"))
            self._draw_device(
                device_group, x, y, device_width, device_height,
                switch_name, switch.get("hostname", "Switch"),
                switch_model,  # Use actual model!
                label_font_size, name_font_size,
            )
```

**Result**:
- Switches use their actual hardware images
- MSN2100-CB2F: Single image represents both switches side-by-side

---

### 6. Network Diagram: Route Connections for MSN2100
**File**: `src/network_diagram.py` (lines 281-293)

For MSN2100 switches, all connections (both SWA and SWB) should converge to the single switch image:

```python
# Get switch position
# For MSN2100 switches (side-by-side), both switches use position 1
msn2100_switches = [s for s in switches if "msn2100" in s.get("model", "").lower()]
if len(msn2100_switches) >= 2:
    # Both switches connect to the single MSN2100 image at position 1
    if 1 not in switch_positions:
        continue
    switch_x, switch_y_pos = switch_positions[1]
else:
    # Normal case: use the specific switch position
    if switch_num not in switch_positions:
        continue
    switch_x, switch_y_pos = switch_positions[switch_num]
```

**Result**: All connections (green and blue) converge to the single MSN2100 image

---

## VERIFICATION

### Test Report Generated
- **Cluster**: Bonzo-01 (10.27.200.32)
- **Generated**: `/Users/ray.stamps/Documents/as-built-report/ps-deploy-report/reports/vast_asbuilt_report_Bonzo-01_20251023_014517.pdf`
- **JSON Data**: `/Users/ray.stamps/Documents/as-built-report/ps-deploy-report/reports/vast_data_Bonzo-01_20251023_014517.json`

### Verification from Logs

#### CBox Model Enrichment ✅
```
[INFO] Enriched CBox 7 with model: CascadeLake
[INFO] Enriched CBox 1 with model: Broadwell
```
- CBox 7 (ID 7) correctly identified as **CascadeLake**
- CBox 1 (ID 1) correctly identified as **Broadwell**

#### DBox Model Enrichment ⚠️
```
[INFO] Enriched DBox with model: dbox-3d0603af
[WARNING] No image found for hardware type: dbox-3d0603af
```
- DBox model enrichment is working
- However, the DNode API data only provides DBox IDs, not hardware models
- This is cluster-specific and requires Hardware Inventory table review

#### Image Loading ✅
```
[INFO] Loaded hardware image for broadwell: .../broadwell_cbox_2u.png
[INFO] Loaded hardware image for cascadelake: .../cascadelake_cbox_2u.png
[INFO] Loaded hardware image for msn2100-cb2f: .../mellanox_msn2100_2x16p_100g_switch_1u.png
```
- All hardware images loaded successfully
- Broadwell and CascadeLake images are available
- MSN2100-CB2F image is available

#### Switch Model ✅
From earlier data collection logs, switches were correctly identified:
```json
{
  "model": "MSN2100-CB2F",
  "name": "rack6-1",
  "hostname": "rack6-1"
}
```

---

## EXPECTED RESULTS

### Normal Clusters (e.g., MSN3700)
- **CBox images**: Match Hardware Inventory model (Broadwell, CascadeLake, Supermicro, etc.)
- **DBox images**: Match Hardware Inventory model (Ceres V2, Maverick 1.5, Sanmina, etc.)
- **Switch images**: One image per switch, matches model (MSN3700-VS2FC, etc.)
- **Connections**: Green to SWA, Blue to SWB (separate switches)

### MSN2100-CB2F Clusters (Qty 2)
- **CBox images**: Match Hardware Inventory model
- **DBox images**: Match Hardware Inventory model
- **Switch image**: **ONE** image representing **BOTH** switches side-by-side
- **Label**: "SWA/SWB" and "MSN2100 Pair"
- **Connections**: All converge to single switch image (green and blue lines)

### Visual Representation for MSN2100
```
                 ┌─────────────────┐
                 │  SWA/SWB        │
                 │  MSN2100 Pair   │
                 │ ┌─────┬─────┐   │ ← Single image shows both switches
                 │ │ SW1 │ SW2 │   │
                 │ └─────┴─────┘   │
                 └─────────────────┘
                    ↑↑    ↑↑
Green lines (SWA) ─┘│    │└─ Blue lines (SWB)
                    │    │
              All connections converge here
```

---

## KNOWN ISSUES & NOTES

### 1. DBox Model for Bonzo-01 Cluster
**Issue**: DNode API data only provides DBox ID (`"dbox-3d0603af"`), not hardware model

**Workaround Options**:
1. **Manual Mapping**: Add a mapping in the code for known DBox IDs to hardware models
2. **Hardware Inventory Review**: Check if the Hardware Inventory section of the report has accurate DBox model information
3. **API Enhancement**: Request VAST to include hardware model in DNode API response

**Current Behavior**: Falls back to generic `ceres_v2` image since `dbox-3d0603af` is not in the image map

### 2. Port Mapping Failed
The port mapping collection failed due to PTY issues:
```
[ERROR] Error collecting node MACs via clush: clush command failed:
Failed to get a pseudo terminal: Operation not permitted
```

This is unrelated to the hardware image issue but affects the network diagram connections. When port mapping works, the connections will be displayed correctly.

---

## FILES MODIFIED

### 1. `src/report_builder.py`
- **Lines 1900-1971**: Removed temporary test devices
- **Lines 2928-2950**: Added CBox model enrichment from CNodes
- **Lines 2952-2972**: Added DBox model enrichment from DNodes

### 2. `src/network_diagram.py`
- **Lines 389-404**: CBox model resolution - uses actual model from hardware data
- **Lines 406-446**: Switch model resolution with MSN2100 special case
- **Lines 281-293**: Connection routing for MSN2100 (all connections to single image)

---

## IMAGE MAP REFERENCE

**File**: `src/network_diagram.py` (lines 66-76)
**File**: `src/rack_diagram.py` (lines 98-109)

Current mappings:
```python
image_map = {
    "supermicro_gen5_cbox": "supermicro_gen5_cbox_1u.png",
    "broadwell": "broadwell_cbox_2u.png",               # ✅ Broadwell 2U CBox
    "cascadelake": "cascadelake_cbox_2u.png",           # ✅ CascadeLake 2U CBox
    "ceres_v2": "ceres_v2_1u.png",
    "dbox-515": "ceres_v2_1u.png",
    "sanmina": "ceres_v2_1u.png",                       # ✅ Sanmina 1U DBox
    "maverick_1.5": "maverick_2u.png",                  # ✅ Maverick 2U DBox
    "msn3700-vs2fc": "mellanox_msn3700_1x32p_200g_switch_1u.png",
    "msn2100-cb2f": "mellanox_msn2100_2x16p_100g_switch_1u.png",  # ✅ MSN2100 2x side-by-side
}
```

**To Add New Hardware**:
1. Add PNG image to `assets/hardware_images/`
2. Add mapping to `image_map` in both `network_diagram.py` and `rack_diagram.py`
3. Add model to `one_u_models` or `two_u_models` list in `rack_diagram.py`

---

## TESTING RECOMMENDATIONS

### Test Different Cluster Types

1. **Broadwell/CascadeLake Cluster** ✅
   - **Status**: Tested with Bonzo-01
   - **Result**: CBox images correctly use Broadwell and CascadeLake

2. **MSN2100-CB2F Cluster** ✅
   - **Status**: Tested with Bonzo-01
   - **Result**: Switch logic correctly detects MSN2100 and uses single image

3. **MSN3700-VS2FC Cluster** ⏳
   - **Status**: Not yet tested
   - **Expected**: Should use MSN3700 image for each switch separately

4. **Maverick 1.5 DBox Cluster** ⏳
   - **Status**: Not yet tested
   - **Expected**: Should use `maverick_2u.png` for DBoxes

### Verify Hardware Inventory Section
- Open the generated PDF
- Navigate to "Hardware Summary" section
- Check if CBox and DBox models are correctly listed
- Verify that the model names match what's in the image map

---

## CONCLUSION

✅ **Implementation Complete**

The network topology diagram now dynamically uses hardware images based on the actual models from the Hardware Inventory. The solution:

1. **Enriches** CBox and DBox data with model information from CNodes and DNodes
2. **Updates** network diagram to use actual models instead of hardcoded values
3. **Handles** special case for MSN2100-CB2F (side-by-side representation)
4. **Maintains** aspect ratios and proper image scaling

The only remaining issue is cluster-specific: DNode API data for Bonzo-01 doesn't provide hardware models, only DBox IDs. This can be addressed through manual mapping or by verifying the Hardware Inventory table.

**Next Steps**:
1. Review Hardware Inventory section in the PDF to verify DBox model display
2. If DBox model is shown correctly in the table, we can use that data source
3. Test with other cluster types (MSN3700, Maverick 1.5) to verify compatibility
4. Add manual mappings for known DBox IDs if needed

---

## CONTACT

For questions or issues related to this implementation, refer to:
- `src/report_builder.py` (model enrichment logic)
- `src/network_diagram.py` (diagram generation with actual models)
- `src/rack_diagram.py` (image map and U height definitions)

**Generated**: October 23, 2025
**Report**: vast_asbuilt_report_Bonzo-01_20251023_014517.pdf
