# Multi-Rack Support Findings - Cluster 10.143.11.204

**Generated:** November 5, 2025
**Cluster:** selab-var-204 (10.143.11.204)
**Cluster Version:** 5.3.1.1.10603406698381149702
**Report Generated:** output/vast_asbuilt_report_selab-var-204_20251105_141400.pdf

---

## Executive Summary

The API discovery script successfully identified **rack identification fields** and **switch fields** available in the VAST API. While this cluster is currently a **single-rack deployment** (rack_id=1, rack_name="Rack"), the API supports multi-rack deployments with explicit rack identifiers.

**Key Findings:**
- ✅ **Rack identification fields ARE available** (`rack_id`, `rack_name`, `rack_unit`)
- ⚠️ **Switch role classification is limited** (`role`="switch" is generic, not Leaf/Spine specific)
- ✅ **Racks endpoint exists** (`/api/v7/racks/`) with 2 racks defined (Rack ID 1 and 2)
- ⚠️ **Current report does NOT display rack identifiers** in hardware tables
- ⚠️ **Switches do NOT have rack information** collected or displayed

---

## 1. API Field Discovery Results

### 1.1 Rack Identification Fields

#### Available Fields:
| Field Name | Endpoints | Example Values | Current Usage |
|------------|-----------|----------------|---------------|
| `rack_id` | `/cboxes/`, `/dboxes/` | `1` | ✅ Collected, ❌ Not displayed |
| `rack_name` | `/cboxes/`, `/dboxes/` | `"Rack"`, `"Rack1"` | ✅ Collected, ❌ Not displayed |
| `rack_unit` | `/cboxes/`, `/dboxes/` | `"U23"`, `"U24"`, `"U18"` | ✅ Collected, ✅ Displayed |
| `index_in_rack` | `/cboxes/`, `/dboxes/` | `null` | ❌ Not used |
| `position` | `/cnodes/`, `/dnodes/`, `/dtrays/` | Various | ✅ Collected (as `rack_position`) |

#### Sample Data from Cluster:
```json
// CBoxes
{
  "rack_id": 1,
  "rack_name": "Rack",
  "rack_unit": "U23",
  "index_in_rack": null
}

// DBoxes
{
  "rack_id": 1,
  "rack_name": "Rack",
  "rack_unit": "U18",
  "index_in_rack": null
}

// Racks Endpoint
[
  {
    "id": 1,
    "name": "Rack",
    "number_of_units": 42,
    "column": null,
    "row": null
  },
  {
    "id": 2,
    "name": "Rack1",
    "number_of_units": null,
    "column": null,
    "row": null
  }
]
```

**Key Observation:** There are 2 racks defined in the system (Rack ID 1 and 2), but this cluster only uses Rack ID 1. This confirms multi-rack support exists in the API.

---

### 1.2 Switch Classification Fields

#### Available Fields:
| Field Name | Endpoints | Example Values | Current Usage |
|------------|-----------|----------------|---------------|
| `role` | `/switches/` | `"switch"` | ✅ Collected, ❌ Not displayed |
| `switch_type` | `/switches/` | `"cumulus"`, `"onyx"` | ✅ Collected, ✅ Displayed |

#### Sample Data from Cluster:
```json
{
  "id": 1,
  "name": "se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)",
  "hostname": "se-var-1-1",
  "role": "switch",
  "switch_type": "cumulus",
  "mgmt_ip": "10.143.11.153",
  "model": "MSN3700-VS2FC"
}
```

**Key Observation:**
- The `role` field is generic (`"switch"`), not specific to Leaf/Spine classification
- Switch hostnames contain rack identifiers: `se-var-1-1` (likely "rack 1, switch 1")
- **Switches do NOT have `rack_id` or `rack_unit` fields** in the API response
- Switch position must be inferred from hostname or calculated based on CBox/DBox positions

---

### 1.3 CNode/DNode Position Fields

#### Available Fields:
| Field Name | Endpoints | Current Usage |
|------------|-----------|---------------|
| `position` | `/cnodes/`, `/dnodes/` | ✅ Collected (as `rack_position`) |

**Note:** CNodes and DNodes inherit rack information from their parent CBox/DBox, but this relationship is not explicitly shown in the report.

---

## 2. Current Report Status

### 2.1 Hardware Inventory Section

#### What's Currently Displayed:

**CBox Information Table:**
- CBox ID (e.g., CB-1, CB-2, CB-3)
- Model
- Name
- Status
- **Rack Position (U-number only)** ✅

**DBox Information Table:**
- DBox ID (e.g., DB-1)
- Model
- Name
- Status
- **Rack Position (U-number only)** ✅

**Switch Information Table:**
- Switch ID
- Model
- Management IP
- Status
- **Rack Position (calculated, not from API)** ⚠️

#### What's Missing:

**For CBoxes/DBoxes:**
- ❌ **Rack ID** (collected but not displayed)
- ❌ **Rack Name** (collected but not displayed)

**For CNodes/DNodes:**
- ❌ **Rack ID** (available from parent CBox/DBox, not propagated)
- ❌ **Rack Name** (available from parent CBox/DBox, not propagated)
- ✅ Rack Position (U-number) is displayed

**For Switches:**
- ❌ **Rack ID** (not available from API, must be inferred)
- ❌ **Rack Name** (not available from API, must be inferred)
- ⚠️ **Rack Position** (calculated, not from API)
- ❌ **Switch Role** (Leaf/Spine - not available from API)

---

### 2.2 Physical Rack Layout Section

#### What's Currently Displayed:
- Visual rack diagram showing:
  - CBoxes with U-number positions
  - DBoxes with U-number positions
  - Switches with calculated positions
  - Hardware images/models

#### What's Missing:
- ❌ **Rack identifier label** (which rack is this?)
- ❌ **Multi-rack support** (assumes single rack)
- ⚠️ **Switch positions** are calculated, not from API

---

### 2.3 Port Mapping Section

#### What's Currently Displayed:
- Switch Port
- Node Connection (e.g., `CB1-CN1-R`, `DB1-DN2-L`)
- Network
- Speed
- Notes

#### What's Missing:
- ❌ **Rack identifier in designations** (e.g., should be `R1-CB1-CN1-R`)
- ❌ **Switch role classification** (Leaf vs Spine)
- ❌ **Inter-rack connections** (if multi-rack)

**Note:** Port mapping failed for this cluster due to switch authentication issues, so this section may be empty.

---

## 3. Data Collection Status

### 3.1 What's Being Collected

#### From API:
- ✅ `rack_id` from `/cboxes/` and `/dboxes/`
- ✅ `rack_name` from `/cboxes/` and `/dboxes/`
- ✅ `rack_unit` from `/cboxes/` and `/dboxes/`
- ✅ `position` from `/cnodes/` and `/dnodes/`
- ✅ `role` from `/switches/` (but generic "switch")
- ✅ `switch_type` from `/switches/`

#### From Racks Endpoint:
- ✅ Rack inventory (`/api/v7/racks/`)
- ✅ Rack identifiers and names
- ✅ Rack unit counts

### 3.2 What's NOT Being Collected

- ❌ Switch rack information (not available from API)
- ❌ Switch Leaf/Spine classification (role field is generic)
- ❌ Topology information (endpoints don't exist)
- ❌ Inter-rack connectivity (not available from API)

---

## 4. Implementation Requirements

### 4.1 Immediate Enhancements (Available Data)

#### 4.1.1 Add Rack Column to Hardware Tables
**Priority:** High
**Effort:** Low
**Data Available:** Yes

**Changes Needed:**
1. Update `src/report_builder.py` - `_create_hardware_inventory()`:
   - Add "Rack" column to CBox table showing `rack_name` or `rack_id`
   - Add "Rack" column to DBox table showing `rack_name` or `rack_id`
   - Add "Rack" column to CNode table (inherit from CBox)
   - Add "Rack" column to DNode table (inherit from DBox)

2. Update `src/data_extractor.py`:
   - Ensure `rack_id` and `rack_name` are propagated from CBox/DBox to CNodes/DNodes
   - Add rack information to node data structures

#### 4.1.2 Add Rack Label to Rack Diagram
**Priority:** Medium
**Effort:** Low
**Data Available:** Yes

**Changes Needed:**
1. Update `src/rack_diagram.py`:
   - Add rack identifier label (e.g., "Rack 1" or "Rack: selab-var-204-Rack")
   - Display rack name from API

2. Update `src/report_builder.py`:
   - Pass rack information to rack diagram generator

#### 4.1.3 Enhance Port Mapping with Rack Identifiers
**Priority:** Medium
**Effort:** Medium
**Data Available:** Partial (rack info for nodes, not switches)

**Changes Needed:**
1. Update `src/data_extractor.py` - `extract_port_mapping()`:
   - Include rack identifier in node designations:
     - Format: `R{rack_id}-CB{cbox_num}-CN{cnode_num}-{R|L}`
     - Example: `R1-CB1-CN1-R` (Rack 1, CBox 1, CNode 1, Port A)

2. Update `src/report_builder.py` - `_create_port_mapping_section()`:
   - Update designation format to include rack identifier
   - Group port mappings by rack if multi-rack

---

### 4.2 Advanced Enhancements (Requires Inference/Fallback)

#### 4.2.1 Switch Rack Assignment
**Priority:** Medium
**Effort:** Medium
**Data Available:** Partial (hostname patterns)

**Approach:**
1. Parse switch hostname for rack identifier:
   - `se-var-1-1` → Rack 1, Switch 1
   - `se-var-1-2` → Rack 1, Switch 2
   - `se-var-2-1` → Rack 2, Switch 1

2. Alternative: Infer from connected nodes
   - Assign switch to rack based on which nodes it connects to
   - If all connections are to Rack 1 nodes, switch is in Rack 1

3. Update `src/api_handler.py`:
   - Add `_infer_switch_rack()` method
   - Extract rack from hostname pattern

4. Update `src/data_extractor.py`:
   - Add rack information to switch data structures

#### 4.2.2 Switch Leaf/Spine Classification
**Priority:** Low
**Effort:** High
**Data Available:** No (must infer)

**Approach:**
1. **Position-based inference:**
   - Switches at U1/U2 in same rack as nodes = Leaf switches
   - Switches at other positions or in dedicated rack = Spine switches

2. **Port count analysis:**
   - High port count (32+ ports) = Spine switch
   - Lower port count (16-32 ports) = Leaf switch

3. **Connection analysis:**
   - Switch connects only to nodes in one rack = Leaf
   - Switch connects to multiple racks = Spine

4. **Configuration file:**
   - Manual assignment via config file

**Implementation:**
- Update `src/data_extractor.py`:
  - Add `_classify_switch_role()` method
  - Apply classification logic

- Update `src/report_builder.py`:
  - Separate Leaf and Spine switches in tables
  - Add topology diagram showing Leaf/Spine connections

---

### 4.3 Multi-Rack Layout Support

#### 4.3.1 Multi-Rack Diagram Generation
**Priority:** High (for multi-rack deployments)
**Effort:** High
**Data Available:** Yes (rack inventory)

**Changes Needed:**
1. Create `src/multi_rack_diagram.py`:
   - Generate side-by-side rack diagrams
   - Show rack identifiers
   - Show inter-rack connectivity (if available)

2. Update `src/report_builder.py`:
   - Detect multi-rack deployments (count racks with components)
   - Use multi-rack diagram if > 1 rack
   - Use single-rack diagram if 1 rack

3. Update `src/data_extractor.py`:
   - Group hardware by rack
   - Generate per-rack layout data

---

## 5. Implementation Checklist

### Phase 1: Basic Rack Identification (Low Effort, High Value)
- [ ] Add rack column to CBox table in report
- [ ] Add rack column to DBox table in report
- [ ] Add rack column to CNode table (inherit from CBox)
- [ ] Add rack column to DNode table (inherit from DBox)
- [ ] Add rack label to rack diagram
- [ ] Test with single-rack deployment

### Phase 2: Enhanced Port Mapping (Medium Effort, Medium Value)
- [ ] Include rack identifier in port mapping designations
- [ ] Update port mapping table format
- [ ] Test with port mapping enabled

### Phase 3: Switch Rack Assignment (Medium Effort, Medium Value)
- [ ] Implement hostname-based rack inference
- [ ] Add rack column to switch table
- [ ] Update rack diagram to show switch rack assignments
- [ ] Test with multi-rack deployment

### Phase 4: Switch Classification (High Effort, Low Priority)
- [ ] Implement Leaf/Spine classification logic
- [ ] Separate Leaf/Spine switches in tables
- [ ] Create topology diagram with Leaf/Spine connections
- [ ] Test with multi-rack deployment

### Phase 5: Multi-Rack Layout (High Effort, High Value for Multi-Rack)
- [ ] Create multi-rack diagram generator
- [ ] Update report to detect multi-rack deployments
- [ ] Test with actual multi-rack deployment

---

## 6. Sample Data from Current Report

### 6.1 Current Hardware Inventory (from JSON)

**CNodes:**
```json
{
  "id": "6",
  "type": "cnode",
  "model": "supermicro_gen5_cbox, two dual-port NICs",
  "rack_position": 25,
  "rack_u": "U25",
  "cbox_id": 4
  // Missing: rack_id, rack_name
}
```

**CBoxes:**
```json
{
  "id": 4,
  "name": "cbox-S929986X5306758",
  "rack_id": 1,
  "rack_unit": "U25",
  "rack_name": "Rack"
  // ✅ Has rack_id and rack_name, but not displayed in report
}
```

**DNodes:**
```json
{
  "id": "113",
  "type": "dnode",
  "rack_position": 18,
  "rack_u": "U18",
  "dbox_id": 1
  // Missing: rack_id, rack_name (should inherit from DBox)
}
```

**DBoxes:**
```json
{
  "id": 1,
  "name": "dbox-515-25042300200055",
  "rack_id": 1,
  "rack_unit": "U18",
  "rack_name": "Rack"
  // ✅ Has rack_id and rack_name, but not displayed in report
}
```

**Switches:**
```json
{
  "name": "se-var-1-1: switch-MSN3700-VS2FC (MT2450J01JQ7)",
  "hostname": "se-var-1-1",
  "role": "switch",
  "switch_type": "cumulus",
  "mgmt_ip": "10.143.11.153"
  // Missing: rack_id, rack_unit, Leaf/Spine classification
}
```

---

## 7. Next Steps

### Immediate Actions:
1. **Review generated report** (`output/vast_asbuilt_report_selab-var-204_20251105_141400.pdf`)
   - Identify all locations where rack information should be displayed
   - Document current vs. desired state

2. **Implement Phase 1 enhancements:**
   - Add rack columns to hardware tables
   - Add rack label to diagram
   - Test with current cluster

3. **Test with multi-rack deployment:**
   - Find or create test cluster with multiple racks
   - Verify rack identification works correctly
   - Test multi-rack diagram generation

### Future Enhancements:
- Implement Leaf/Spine classification
- Create topology diagrams
- Add inter-rack connectivity visualization

---

**Document Version:** 1.0
**Last Updated:** November 5, 2025
**Status:** Ready for implementation


