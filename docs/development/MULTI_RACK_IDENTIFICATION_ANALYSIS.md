# Multi-Rack Deployment Identification Analysis

## Executive Summary

This document analyzes how the VAST As-Built Report Generator identifies and documents CBox/CNode, DBox/DNode, and Leaf/Spine switches in reports, and identifies what information is needed for proper multi-rack deployment reporting and visual diagram generation.

**Generated:** November 5, 2025
**Target Cluster:** 10.142.11.204
**Report Version:** 1.1.0

---

## 1. Report Sections Containing Hardware Identification

### 1.1 Cluster Information Section (Section 1)
**Location:** Pages 1-2

**What's Documented:**
- Cluster name and version
- Total node counts (CNodes, DNodes)
- Cluster capacity metrics
- **Does NOT include:** Individual CBox/DBox identification, rack locations

**Data Source:**
- API: `/api/v7/vms/`
- Fields: `cluster_name`, `version`, `total_cnodes`, `total_dnodes`

---

### 1.2 Hardware Inventory Section (Section 4)
**Location:** Pages 4-5

**What's Documented:**

#### CBox Information Table:
| Column | Source Field | Example Value |
|--------|-------------|---------------|
| CBox ID | `cbox_id` or `box_name` | CB-1, cbox-ABC123 |
| Model | `box_vendor` or `model` | Broadwell, Skylake |
| Name | `name` | se-az-arrow-cb2-cn-1 |
| Status | `state` or `status` | ACTIVE, INACTIVE |
| Rack Position | `rack_unit` or `rack_u` | U23, U24 |

#### DBox Information Table:
| Column | Source Field | Example Value |
|--------|-------------|---------------|
| DBox ID | `dbox_id` or `box_name` | DB-1, dbox-XYZ789 |
| Model | `hardware_type` | supermicro_gen5_dbox |
| Name | `name` | se-az-arrow-db2-dn-100 |
| Status | `state` | ACTIVE |
| Rack Position | `rack_unit` | U18 |

#### Switch Information Table:
| Column | Source Field | Example Value |
|--------|-------------|---------------|
| Switch ID | `name` | switch-1, se-var-1-1 |
| Model | `model` | Cumulus, Onyx |
| Management IP | `mgmt_ip` | 10.142.11.153 |
| Status | `state` | ACTIVE |
| **Rack Position** | **Calculated** | **U1, U2** |

**Key Limitations:**
- Switch positions are **calculated** based on CBox/DBox positions, not retrieved from API
- No explicit rack number/identifier
- No Leaf vs Spine designation

**Data Sources:**
- API: `/api/v7/cnodes/`, `/api/v7/dnodes/`, `/api/v7/cboxes/`, `/api/v7/dboxes/`, `/api/v7/switches/`

---

### 1.3 Physical Rack Layout Section (Section 6)
**Location:** Page 6

**What's Documented:**
- Visual rack diagram showing:
  - CBoxes with their U-number positions
  - DBoxes with their U-number positions
  - Switches with calculated positions (typically U1-U2)
  - Hardware images/models

**Calculation Logic:**
```python
# From rack_diagram.py
def _calculate_switch_positions(cboxes, dboxes, num_switches):
    # Switches typically placed at:
    # - U1 (bottom switch)
    # - U2 (top switch)
    # Based on CBox/DBox positions
```

**Key Limitations:**
- **Single rack assumption** - no multi-rack support
- Switch positions are **inferred**, not from API
- No rack number/identifier displayed
- No distinction between Leaf and Spine switches

---

### 1.4 Port Mapping Section (Section 7)
**Location:** Pages 7-8 (if port mapping enabled)

**What's Documented:**

#### Port Mapping Tables (per switch):
| Column | Source | Example |
|--------|--------|---------|
| Switch Port | `switch_entry["port"]` | swp20, swp29 |
| Node Connection | `node_designation` | CB1-CN1-R, DB1-DN2-L |
| Network | Determined by switch | A, B |
| Speed | Default | 200G |
| Notes | Connection type | Primary, IPL |

**Node Designation Format:**
- **CNodes:** `CB{cbox_num}-CN{cnode_num}-{R|L}`
  - Example: `CB1-CN1-R` = CBox-1, CNode-1, Port-A (Right/Network A)
- **DNodes:** `DB{dbox_num}-DN{dnode_num}-{R|L}`
  - Example: `DB1-DN2-L` = DBox-1, DNode-2, Port-B (Left/Network B)

**Switch Designation Format:**
- **Switch 1:** `SWA-P{port_num}` (Switch A, Port X)
- **Switch 2:** `SWB-P{port_num}` (Switch B, Port X)

**Key Limitations:**
- No rack identifier in designations
- Assumes 2 switches per rack (Leaf switches)
- No Spine switch identification
- Network assignment based on switch IP sorting, not explicit topology

**Data Sources:**
- External SSH collection via `external_port_mapper.py`
- Switch MAC address tables
- Node interface MACs via `clush`

---

## 2. Current Data Collection Methods

### 2.1 CBox/CNode Data Collection

**API Endpoints Used:**
```python
# CNodes
GET /api/v7/cnodes/
# Returns: List of CNode objects

# CBoxes (if available)
GET /api/v7/cboxes/
# Returns: Dictionary of CBox objects keyed by box_name
```

**Key Fields Extracted:**
```python
{
    "id": cnode_id,                    # CNode ID
    "name": hostname,                  # e.g., "se-az-arrow-cb2-cn-1"
    "cbox_id": cbox_id,                # Links to CBox
    "cbox": cbox_name,                 # CBox name (e.g., "cbox-ABC123")
    "box_vendor": model,               # Hardware model
    "rack_unit": "U23",                # Rack position (if available)
    "mgmt_ip": ip_address,             # Management IP
    "ip": data_ip,                     # Data plane IP
    "state": "ACTIVE"                  # Operational status
}
```

**Current Identification Logic:**
1. CNodes are grouped by `cbox_id` or `cbox` field
2. CBox number assigned sequentially (CB-1, CB-2, etc.)
3. CNode number assigned sequentially within each CBox (CN-1, CN-2, etc.)
4. Rack position taken from CBox `rack_unit` field (if available)

**Limitations:**
- No explicit rack number field
- CBox-to-rack mapping not direct from API
- CBoxes inferred from CNodes (no direct CBox enumeration)

---

### 2.2 DBox/DNode Data Collection

**API Endpoints Used:**
```python
# DNodes
GET /api/v7/dnodes/
# Returns: List of DNode objects

# DBoxes
GET /api/v7/dboxes/
# Returns: Dictionary of DBox objects keyed by box_name

# DTrays
GET /api/v7/dtrays/
# Returns: Dictionary of DTray objects
```

**Key Fields Extracted:**
```python
{
    "id": dnode_id,                    # DNode ID
    "name": hostname,                  # e.g., "se-az-arrow-db2-dn-100"
    "dbox_id": dbox_id,                # Links to DBox
    "dbox": dbox_name,                 # DBox name (e.g., "dbox-XYZ789")
    "dtray": dtray_name,               # DTray within DBox
    "hardware_type": model,            # Hardware model
    "rack_unit": "U18",                # Rack position from DBox
    "mgmt_ip": ip_address,             # Management IP
    "ip": data_ip,                     # Data plane IP
    "state": "ACTIVE"                  # Operational status
}
```

**Current Identification Logic:**
1. DNodes are grouped by `dbox_id` or `dbox` field
2. DBox number assigned sequentially (DB-1, DB-2, etc.)
3. DNode number assigned sequentially within each DBox (DN-1, DN-2, etc.)
4. Rack position taken from DBox `rack_unit` field (if available)

**Limitations:**
- No explicit rack number field
- DBox-to-rack mapping not direct from API
- DTray position within DBox not always displayed

---

### 2.3 Switch Data Collection

**API Endpoints Used:**
```python
# Switches
GET /api/v7/switches/
# Returns: List of switch objects
```

**Key Fields Extracted:**
```python
{
    "name": switch_name,               # e.g., "switch-1", "se-var-1-1"
    "mgmt_ip": ip_address,             # Management IP
    "model": switch_model,             # e.g., "Cumulus", "Onyx"
    "state": "ACTIVE",                 # Operational status
    # NOTE: No rack_unit field available from API
}
```

**Current Identification Logic:**
1. Switches sorted by management IP
2. Switch 1 (lower IP) = SWA (Network A)
3. Switch 2 (higher IP) = SWB (Network B)
4. **Switch positions calculated** based on CBox/DBox positions:
   - Typically placed at U1 (bottom) and U2 (top)
   - Assumes 2 switches per rack (Leaf switches)

**Limitations:**
- **No explicit rack position from API** - positions are calculated
- **No Leaf vs Spine designation** - all switches treated as Leaf
- **No rack identifier** - cannot distinguish switches in different racks
- **No topology information** - which switches connect to which racks

---

## 3. Information Needed for Multi-Rack Deployments

### 3.1 Critical Missing Information

#### 3.1.1 Rack Number/Identifier
**Current State:**
- Only rack unit (U-number) is available (e.g., "U23")
- No rack identifier (e.g., "Rack-1", "Rack-A", "Rack-01")

**What's Needed:**
- Explicit rack number/identifier field for:
  - CBoxes
  - DBoxes
  - Switches
  - CNodes (inherited from CBox)
  - DNodes (inherited from DBox)

**Potential API Fields to Check:**
- `rack_id`
- `rack_number`
- `rack_name`
- `rack_label`
- `location.rack`
- `physical_location.rack`

---

#### 3.1.2 Leaf vs Spine Switch Classification
**Current State:**
- All switches treated equally
- No distinction between Leaf (ToR) and Spine switches
- Assumes 2 switches per rack (Leaf switches only)

**What's Needed:**
- Switch type/role field:
  - `leaf` - Top of Rack switches (connect to nodes in rack)
  - `spine` - Spine switches (connect multiple racks)
- Switch topology information:
  - Which racks each switch connects to
  - Which switches connect to which racks

**Potential API Fields to Check:**
- `switch_type`
- `role`
- `topology_role`
- `is_leaf`
- `is_spine`
- `connected_racks`
- `topology.role`

---

#### 3.1.3 Multi-Rack Topology Information
**Current State:**
- Single rack layout visualization
- No inter-rack connectivity information
- No rack-to-rack relationships

**What's Needed:**
- Rack inventory:
  - List of all racks in deployment
  - Rack identifiers and locations
- Rack contents:
  - Which CBoxes/DBoxes are in which racks
  - Which switches are in which racks
- Inter-rack connectivity:
  - Which switches connect which racks
  - Spine switch connections

**Potential API Endpoints to Check:**
- `/api/v7/racks/`
- `/api/v7/topology/`
- `/api/v7/network/topology/`
- `/api/v7/physical_layout/`

---

#### 3.1.4 CBox-to-Rack Direct Mapping
**Current State:**
- CBoxes inferred from CNodes
- CBox rack position taken from `rack_unit` field
- No explicit CBox enumeration endpoint

**What's Needed:**
- Direct CBox API endpoint with rack information
- CBox-to-rack mapping
- CBox inventory with rack assignments

**Potential API Endpoints to Check:**
- `/api/v7/cboxes/` (enhanced with rack info)
- `/api/v7/hardware/cboxes/`
- `/api/v7/physical/cboxes/`

---

#### 3.1.5 Switch-to-Rack Association
**Current State:**
- Switch positions calculated based on CBox/DBox positions
- No direct switch-to-rack mapping from API
- Assumes switches are in same rack as compute/storage

**What's Needed:**
- Direct switch-to-rack mapping
- Switch rack position from API
- Switch topology role (Leaf/Spine)

**Potential API Fields to Check:**
- `rack_unit` (for switches)
- `rack_id` (for switches)
- `physical_location.rack`
- `location.rack`

---

## 4. Proposed Solutions

### 4.1 Enhanced Data Collection

#### 4.1.1 API Field Discovery
**Action Items:**
1. Generate report for cluster 10.142.11.204
2. Review API responses for:
   - Rack identifier fields
   - Switch type/role fields
   - Topology information
   - Multi-rack support endpoints

#### 4.1.2 Fallback Identification Methods
**If API doesn't provide rack numbers:**
- Use hostname patterns (e.g., "rack1-", "r1-")
- Use IP address ranges (e.g., 10.142.11.x = Rack 1, 10.142.12.x = Rack 2)
- Use management IP subnet analysis
- Manual configuration file for rack assignments

---

### 4.2 Enhanced Report Sections

#### 4.2.1 Multi-Rack Layout Section
**New Section Needed:**
- Multi-rack overview diagram
- Rack-by-rack breakdown
- Inter-rack connectivity diagram
- Spine switch topology visualization

#### 4.2.2 Enhanced Hardware Inventory
**Enhancements:**
- Add "Rack" column to all hardware tables
- Group hardware by rack
- Show rack-level summaries

#### 4.2.3 Enhanced Port Mapping
**Enhancements:**
- Include rack identifier in designations:
  - `R1-CB1-CN1-R` (Rack 1, CBox 1, CNode 1, Port A)
- Separate Leaf vs Spine switch sections
- Show inter-rack connections via Spine switches

---

### 4.3 Visual Diagram Enhancements

#### 4.3.1 Multi-Rack Diagram
**Features:**
- Multiple rack side-by-side view
- Rack identifiers clearly labeled
- Component positions within each rack
- Spine switch connections shown

#### 4.3.2 Topology Diagram
**Features:**
- Leaf switch connections (within rack)
- Spine switch connections (between racks)
- Network A/B separation
- Rack-to-rack connectivity

---

## 5. Implementation Checklist

### Phase 1: Data Discovery
- [ ] Generate report for cluster 10.142.11.204
- [ ] Review all API responses for rack/topology fields
- [ ] Document available fields vs. needed fields
- [ ] Test API endpoints for multi-rack information

### Phase 2: Enhanced Collection
- [ ] Add rack identifier extraction logic
- [ ] Add switch type/role detection
- [ ] Add topology information collection
- [ ] Implement fallback identification methods

### Phase 3: Enhanced Reporting
- [ ] Add rack column to hardware tables
- [ ] Create multi-rack layout section
- [ ] Enhance port mapping with rack identifiers
- [ ] Create topology diagram generation

### Phase 4: Visual Enhancements
- [ ] Implement multi-rack diagram generator
- [ ] Create topology visualization
- [ ] Add rack-level summaries
- [ ] Enhance switch position calculation for multi-rack

---

## 6. Next Steps

1. **Generate Report:** Once network connectivity is available, generate report for cluster 10.142.11.204
2. **Review API Responses:** Analyze JSON output for available rack/topology fields
3. **Identify Gaps:** Compare available data vs. needed data
4. **Implement Enhancements:** Add multi-rack support based on findings
5. **Test and Validate:** Verify multi-rack reporting works correctly

---

## Appendix A: Current Code Locations

### Hardware Identification Code:
- **CBox/CNode:** `src/api_handler.py` - `get_cnode_details()`, `get_cbox_details()`
- **DBox/DNode:** `src/api_handler.py` - `get_dnode_details()`, `get_dbox_details()`
- **Switches:** `src/api_handler.py` - `get_switch_inventory()`

### Report Generation Code:
- **Hardware Inventory:** `src/report_builder.py` - `_create_hardware_inventory()`
- **Rack Layout:** `src/report_builder.py` - `_create_hardware_inventory()` (rack diagram section)
- **Port Mapping:** `src/report_builder.py` - `_create_port_mapping_section()`

### Data Processing Code:
- **Hardware Extraction:** `src/data_extractor.py` - `extract_hardware_inventory()`
- **Node Processing:** `src/data_extractor.py` - `_process_hardware_node()`
- **Rack Layout:** `src/data_extractor.py` - `_generate_physical_layout()`

### Visual Diagram Code:
- **Rack Diagram:** `src/rack_diagram.py` - `generate_rack_diagram()`
- **Switch Position Calculation:** `src/rack_diagram.py` - `_calculate_switch_positions()`

---

## Appendix B: API Field Reference

### Current API Fields Used:
```yaml
CNodes:
  - id, name, cbox_id, cbox, box_vendor, rack_unit, mgmt_ip, ip, state

DNodes:
  - id, name, dbox_id, dbox, dtray, hardware_type, rack_unit, mgmt_ip, ip, state

CBoxes:
  - id, name, rack_unit, state

DBoxes:
  - id, name, rack_unit, hardware_type, state

Switches:
  - name, mgmt_ip, model, state
```

### Potential API Fields to Investigate:
```yaml
Rack Information:
  - rack_id, rack_number, rack_name, rack_label
  - location.rack, physical_location.rack

Switch Information:
  - switch_type, role, topology_role, is_leaf, is_spine
  - connected_racks, topology.role, rack_unit, rack_id

Topology Information:
  - topology, network_topology, physical_layout
  - inter_rack_connections, spine_switches
```

---

**Document Version:** 1.0
**Last Updated:** November 5, 2025
**Status:** Awaiting report generation for cluster 10.142.11.204
