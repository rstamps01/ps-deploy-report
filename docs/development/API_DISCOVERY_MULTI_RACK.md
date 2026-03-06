# API Discovery Guide: Multi-Rack Support

## Purpose
This document provides a systematic approach to discovering API endpoints and fields that support multi-rack deployment identification and reporting.

**Target Cluster:** 10.142.11.204
**Date:** November 5, 2025

---

## 1. API Endpoints to Examine

### 1.1 Primary Endpoints (Currently Used)

#### CNodes
```bash
GET /api/v7/cnodes/
```
**Fields to Check:**
- `rack_id` or `rack_number` or `rack_name`
- `rack_unit` (already have - confirm format)
- `location.rack` or `physical_location.rack`
- `cbox_id` (already have)
- `cbox` (already have)
- `box_vendor` (already have)

**Sample Response Structure to Inspect:**
```json
{
  "id": 1,
  "name": "se-az-arrow-cb2-cn-1",
  "cbox_id": "cbox-ABC123",
  "cbox": "cbox-ABC123",
  "rack_unit": "U23",
  "rack_id": "???",  // Check for this
  "location": {
    "rack": "???",    // Check for this
    "datacenter": "???"
  }
}
```

---

#### DNodes
```bash
GET /api/v7/dnodes/
```
**Fields to Check:**
- `rack_id` or `rack_number` or `rack_name`
- `rack_unit` (already have - confirm format)
- `location.rack` or `physical_location.rack`
- `dbox_id` (already have)
- `dbox` (already have)
- `hardware_type` (already have)

**Sample Response Structure to Inspect:**
```json
{
  "id": 100,
  "name": "se-az-arrow-db2-dn-100",
  "dbox_id": "dbox-XYZ789",
  "dbox": "dbox-XYZ789",
  "rack_unit": "U18",
  "rack_id": "???",  // Check for this
  "location": {
    "rack": "???",    // Check for this
    "datacenter": "???"
  }
}
```

---

#### CBoxes
```bash
GET /api/v7/cboxes/
```
**Fields to Check:**
- `rack_id` or `rack_number` or `rack_name`
- `rack_unit` (already have - confirm format)
- `location.rack` or `physical_location.rack`
- `rack_label` or `rack_name`
- `physical_location` object

**Sample Response Structure to Inspect:**
```json
{
  "id": "cbox-ABC123",
  "name": "cbox-ABC123",
  "rack_unit": "U23",
  "rack_id": "???",  // Check for this
  "rack_number": "???",  // Check for this
  "location": {
    "rack": "Rack-1",  // Check for this
    "unit": "U23",
    "datacenter": "???"
  }
}
```

---

#### DBoxes
```bash
GET /api/v7/dboxes/
```
**Fields to Check:**
- `rack_id` or `rack_number` or `rack_name`
- `rack_unit` (already have - confirm format)
- `location.rack` or `physical_location.rack`
- `rack_label` or `rack_name`
- `physical_location` object

**Sample Response Structure to Inspect:**
```json
{
  "id": "dbox-XYZ789",
  "name": "dbox-XYZ789",
  "rack_unit": "U18",
  "rack_id": "???",  // Check for this
  "location": {
    "rack": "Rack-2",  // Check for this
    "unit": "U18"
  }
}
```

---

#### Switches
```bash
GET /api/v7/switches/
```
**Fields to Check:**
- `rack_id` or `rack_number` or `rack_name`
- `rack_unit` (currently missing - check for this)
- `location.rack` or `physical_location.rack`
- `switch_type` or `role` or `topology_role`
- `is_leaf` or `is_spine` (boolean flags)
- `connected_racks` (array of rack IDs)
- `topology` object

**Sample Response Structure to Inspect:**
```json
{
  "name": "switch-1",
  "mgmt_ip": "10.142.11.153",
  "model": "Cumulus",
  "rack_unit": "???",  // Check for this
  "rack_id": "???",    // Check for this
  "switch_type": "leaf",  // Check for: "leaf" or "spine"
  "role": "leaf",      // Alternative field name
  "is_leaf": true,     // Boolean flag
  "is_spine": false,   // Boolean flag
  "location": {
    "rack": "Rack-1",  // Check for this
    "unit": "U1"
  },
  "topology": {
    "role": "leaf",    // Check for this
    "connected_racks": ["Rack-1"],  // Check for this
    "spine_connections": []  // Check for this
  }
}
```

---

### 1.2 Potential New Endpoints (To Discover)

#### Racks Endpoint
```bash
GET /api/v7/racks/
```
**Purpose:** Direct rack inventory and information

**Expected Response Structure:**
```json
[
  {
    "rack_id": "Rack-1",
    "rack_number": 1,
    "rack_name": "Rack-1",
    "location": "Datacenter-A",
    "cboxes": ["cbox-ABC123", "cbox-DEF456"],
    "dboxes": ["dbox-XYZ789"],
    "switches": ["switch-1", "switch-2"],
    "rack_units": {
      "cboxes": ["U23", "U24"],
      "dboxes": ["U18"],
      "switches": ["U1", "U2"]
    }
  },
  {
    "rack_id": "Rack-2",
    ...
  }
]
```

**Check for:**
- List of all racks
- Rack identifiers
- Contents of each rack
- Switch assignments per rack

---

#### Topology Endpoint
```bash
GET /api/v7/topology/
# OR
GET /api/v7/network/topology/
# OR
GET /api/v7/physical_layout/
```
**Purpose:** Network topology and rack-to-rack connectivity

**Expected Response Structure:**
```json
{
  "racks": [
    {
      "rack_id": "Rack-1",
      "leaf_switches": ["switch-1", "switch-2"],
      "spine_connections": [
        {
          "spine_switch": "spine-1",
          "ports": ["swp1", "swp2"]
        }
      ]
    }
  ],
  "spine_switches": [
    {
      "name": "spine-1",
      "mgmt_ip": "10.142.11.200",
      "connected_racks": ["Rack-1", "Rack-2"],
      "is_spine": true
    }
  ],
  "leaf_switches": [
    {
      "name": "switch-1",
      "rack": "Rack-1",
      "is_leaf": true
    }
  ]
}
```

**Check for:**
- Rack-to-rack connectivity
- Spine switch identification
- Leaf switch identification
- Inter-rack connections

---

#### Physical Layout Endpoint
```bash
GET /api/v7/physical_layout/
# OR
GET /api/v7/layout/
```
**Purpose:** Physical hardware layout and positions

**Expected Response Structure:**
```json
{
  "racks": [
    {
      "rack_id": "Rack-1",
      "components": [
        {
          "type": "cbox",
          "id": "cbox-ABC123",
          "rack_unit": "U23",
          "cnodes": ["cn-1", "cn-2"]
        },
        {
          "type": "switch",
          "id": "switch-1",
          "rack_unit": "U1",
          "role": "leaf"
        }
      ]
    }
  ]
}
```

**Check for:**
- Complete physical layout
- Component positions
- Rack assignments

---

## 2. Field Discovery Checklist

### 2.1 Rack Identification Fields

**Check these field names in API responses:**
- [ ] `rack_id`
- [ ] `rack_number`
- [ ] `rack_name`
- [ ] `rack_label`
- [ ] `rack` (simple string)
- [ ] `location.rack`
- [ ] `location.rack_id`
- [ ] `physical_location.rack`
- [ ] `physical_location.rack_id`
- [ ] `site.rack`
- [ ] `datacenter.rack`

**For each field found:**
- [ ] Document the field name
- [ ] Document the data type (string, integer, object)
- [ ] Document example values
- [ ] Document which endpoints contain it
- [ ] Document consistency across endpoints

---

### 2.2 Switch Type/Role Fields

**Check these field names in API responses:**
- [ ] `switch_type` (values: "leaf", "spine", etc.)
- [ ] `role` (values: "leaf", "spine", etc.)
- [ ] `topology_role` (values: "leaf", "spine", etc.)
- [ ] `is_leaf` (boolean)
- [ ] `is_spine` (boolean)
- [ ] `type` (general type field)
- [ ] `switch_role`
- [ ] `network_role`

**For each field found:**
- [ ] Document the field name
- [ ] Document possible values
- [ ] Document which endpoints contain it
- [ ] Test with known Leaf switches
- [ ] Test with known Spine switches (if available)

---

### 2.3 Topology/Connectivity Fields

**Check these field names in API responses:**
- [ ] `connected_racks` (array)
- [ ] `topology.connected_racks`
- [ ] `spine_connections` (array)
- [ ] `leaf_connections` (array)
- [ ] `inter_rack_connections`
- [ ] `uplinks` (array)
- [ ] `downlinks` (array)
- [ ] `neighbors` (array)
- [ ] `topology` (object)

**For each field found:**
- [ ] Document the field name
- [ ] Document the structure (array, object)
- [ ] Document example values
- [ ] Document which endpoints contain it

---

### 2.4 Switch Position Fields

**Check these field names in API responses:**
- [ ] `rack_unit` (currently missing - check if it exists)
- [ ] `rack_position`
- [ ] `location.rack_unit`
- [ ] `physical_location.rack_unit`
- [ ] `u_number` or `u_number_start` / `u_number_end`
- [ ] `position` (object with rack and unit)

**For each field found:**
- [ ] Document the field name
- [ ] Document the format (e.g., "U1", "1", etc.)
- [ ] Document which endpoints contain it
- [ ] Compare with calculated positions

---

## 3. Discovery Process

### Step 1: Generate Report with Verbose Logging
```bash
python3 src/main.py \
  --cluster 10.142.11.204 \
  --output ./output \
  --username support \
  --password 654321 \
  --enable-port-mapping \
  --node-user vastdata \
  --node-password vastdata \
  --switch-user cumulus \
  --switch-password "Vasdata1!" \
  --verbose
```

### Step 2: Capture Raw API Responses
**Method A: Enable API Response Logging**
- Modify `src/api_handler.py` to log full API responses
- Save responses to `logs/api_responses/` directory

**Method B: Use API Testing Tool**
```bash
# Test each endpoint directly
curl -k -u support:654321 \
  https://10.142.11.204/api/v7/cnodes/ \
  | jq '.' > logs/api_responses/cnodes.json

curl -k -u support:654321 \
  https://10.142.11.204/api/v7/dnodes/ \
  | jq '.' > logs/api_responses/dnodes.json

curl -k -u support:654321 \
  https://10.142.11.204/api/v7/cboxes/ \
  | jq '.' > logs/api_responses/cboxes.json

curl -k -u support:654321 \
  https://10.142.11.204/api/v7/dboxes/ \
  | jq '.' > logs/api_responses/dboxes.json

curl -k -u support:654321 \
  https://10.142.11.204/api/v7/switches/ \
  | jq '.' > logs/api_responses/switches.json
```

**Method C: Test Potential New Endpoints**
```bash
# Test for racks endpoint
curl -k -u support:654321 \
  https://10.142.11.204/api/v7/racks/ \
  | jq '.' > logs/api_responses/racks.json

# Test for topology endpoint
curl -k -u support:654321 \
  https://10.142.11.204/api/v7/topology/ \
  | jq '.' > logs/api_responses/topology.json

curl -k -u support:654321 \
  https://10.142.11.204/api/v7/network/topology/ \
  | jq '.' > logs/api_responses/network_topology.json

# Test for physical layout endpoint
curl -k -u support:654321 \
  https://10.142.11.204/api/v7/physical_layout/ \
  | jq '.' > logs/api_responses/physical_layout.json
```

### Step 3: Analyze Responses
For each API response:

1. **Extract Field Names:**
   ```bash
   # Use jq to list all keys in response
   jq '.[0] | keys' logs/api_responses/cnodes.json
   ```

2. **Search for Rack-Related Fields:**
   ```bash
   # Search for "rack" in field names
   jq '.[0] | keys | .[] | select(contains("rack"))' logs/api_responses/cnodes.json
   ```

3. **Search for Location Fields:**
   ```bash
   # Search for "location" in field names
   jq '.[0] | keys | .[] | select(contains("location"))' logs/api_responses/cnodes.json
   ```

4. **Extract Nested Objects:**
   ```bash
   # Check for nested location object
   jq '.[0].location' logs/api_responses/cnodes.json
   ```

5. **Document Findings:**
   - Create `docs/API_FIELD_DISCOVERY_RESULTS.md`
   - Record all discovered fields
   - Document field types and example values
   - Note which endpoints contain which fields

---

## 4. Field Extraction Test Script

Create a test script to systematically extract and document all fields:

```python
# scripts/discover_api_fields.py
import json
import requests
from requests.auth import HTTPBasicAuth
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

CLUSTER_IP = "10.142.11.204"
USERNAME = "support"
PASSWORD = "654321"
BASE_URL = f"https://{CLUSTER_IP}/api/v7"

ENDPOINTS = [
    "/cnodes/",
    "/dnodes/",
    "/cboxes/",
    "/dboxes/",
    "/switches/",
    "/racks/",           # Test if exists
    "/topology/",        # Test if exists
    "/network/topology/", # Test if exists
    "/physical_layout/", # Test if exists
]

RACK_KEYWORDS = ["rack", "location", "position", "physical", "site"]
SWITCH_KEYWORDS = ["type", "role", "leaf", "spine", "topology"]
TOPOLOGY_KEYWORDS = ["topology", "connection", "connect", "neighbor", "uplink"]

def discover_fields(endpoint):
    """Discover all fields in an API endpoint."""
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        # Extract all unique keys from response
        if isinstance(data, list) and len(data) > 0:
            keys = set()
            for item in data:
                keys.update(_extract_keys(item))
            return list(keys), data
        elif isinstance(data, dict):
            keys = _extract_keys(data)
            return list(keys), data
        else:
            return [], data
    except requests.exceptions.RequestException as e:
        print(f"Error accessing {endpoint}: {e}")
        return [], None

def _extract_keys(obj, prefix=""):
    """Recursively extract all keys from nested objects."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            if isinstance(value, (dict, list)):
                keys.update(_extract_keys(value, full_key))
    elif isinstance(obj, list) and len(obj) > 0:
        keys.update(_extract_keys(obj[0], prefix))
    return keys

def categorize_fields(fields):
    """Categorize fields by relevance."""
    rack_fields = []
    switch_fields = []
    topology_fields = []
    other_fields = []

    for field in fields:
        field_lower = field.lower()
        if any(keyword in field_lower for keyword in RACK_KEYWORDS):
            rack_fields.append(field)
        elif any(keyword in field_lower for keyword in SWITCH_KEYWORDS):
            switch_fields.append(field)
        elif any(keyword in field_lower for keyword in TOPOLOGY_KEYWORDS):
            topology_fields.append(field)
        else:
            other_fields.append(field)

    return {
        "rack_fields": sorted(rack_fields),
        "switch_fields": sorted(switch_fields),
        "topology_fields": sorted(topology_fields),
        "other_fields": sorted(other_fields)
    }

def main():
    """Main discovery function."""
    results = {}

    print("Discovering API fields...")
    print("=" * 80)

    for endpoint in ENDPOINTS:
        print(f"\nChecking: {endpoint}")
        fields, data = discover_fields(endpoint)

        if fields:
            print(f"  Found {len(fields)} unique fields")
            categorized = categorize_fields(fields)
            results[endpoint] = {
                "fields": fields,
                "categorized": categorized,
                "sample_data": data[0] if isinstance(data, list) and len(data) > 0 else data
            }

            # Print categorized fields
            if categorized["rack_fields"]:
                print(f"  Rack-related fields: {len(categorized['rack_fields'])}")
                for field in categorized["rack_fields"][:5]:  # Show first 5
                    print(f"    - {field}")
            if categorized["switch_fields"]:
                print(f"  Switch-related fields: {len(categorized['switch_fields'])}")
                for field in categorized["switch_fields"][:5]:
                    print(f"    - {field}")
            if categorized["topology_fields"]:
                print(f"  Topology-related fields: {len(categorized['topology_fields'])}")
                for field in categorized["topology_fields"][:5]:
                    print(f"    - {field}")
        else:
            print(f"  Endpoint not available or empty")
            results[endpoint] = {"available": False}

    # Save results
    with open("logs/api_field_discovery.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print("\n" + "=" * 80)
    print("Discovery complete! Results saved to logs/api_field_discovery.json")

    # Generate summary report
    print("\n" + "=" * 80)
    print("SUMMARY OF DISCOVERED FIELDS")
    print("=" * 80)

    for endpoint, result in results.items():
        if result.get("available", True) and "categorized" in result:
            cat = result["categorized"]
            print(f"\n{endpoint}:")
            if cat["rack_fields"]:
                print(f"  Rack Fields: {', '.join(cat['rack_fields'])}")
            if cat["switch_fields"]:
                print(f"  Switch Fields: {', '.join(cat['switch_fields'])}")
            if cat["topology_fields"]:
                print(f"  Topology Fields: {', '.join(cat['topology_fields'])}")

if __name__ == "__main__":
    main()
```

---

## 5. Documentation Template

### API Field Discovery Results Template

**Endpoint:** `/api/v7/cnodes/`
**Date Discovered:** [Date]
**Status:** ✅ Available / ❌ Not Available

**Rack-Related Fields:**
| Field Name | Type | Example Value | Notes |
|------------|------|---------------|-------|
| `rack_unit` | string | "U23" | Already using |
| `rack_id` | string | "Rack-1" | NEW - if found |
| `location.rack` | string | "Rack-1" | NEW - if found |

**Switch-Related Fields:**
| Field Name | Type | Example Value | Notes |
|------------|------|---------------|-------|
| N/A | - | - | Not applicable for CNodes |

**Topology-Related Fields:**
| Field Name | Type | Example Value | Notes |
|------------|------|---------------|-------|
| N/A | - | - | Not applicable for CNodes |

---

## 6. Action Items

### Immediate Actions (When Connectivity Available):
1. [ ] Generate report for cluster 10.142.11.204
2. [ ] Run API field discovery script
3. [ ] Test all potential endpoints listed above
4. [ ] Document all discovered fields
5. [ ] Compare discovered fields vs. needed fields
6. [ ] Create implementation plan based on findings

### Follow-up Actions:
1. [ ] Update code to use discovered fields
2. [ ] Implement fallback methods if fields missing
3. [ ] Add validation for multi-rack data
4. [ ] Update report generation for multi-rack
5. [ ] Test with actual multi-rack deployment

---

**Document Version:** 1.0
**Last Updated:** November 5, 2025
**Status:** Ready for execution when network connectivity is available
