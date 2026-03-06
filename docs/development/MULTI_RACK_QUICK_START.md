# Multi-Rack Support: Quick Start Guide

## Overview
This guide provides quick steps to discover and implement multi-rack support for the VAST As-Built Report Generator.

---

## Step 1: Discover API Fields

When network connectivity is available, run the API discovery script:

```bash
python3 scripts/discover_api_fields.py \
  --cluster 10.142.11.204 \
  --username support \
  --password 654321 \
  --verbose
```

**What it does:**
- Tests all known API endpoints
- Tests potential new endpoints (racks, topology, etc.)
- Categorizes fields by type (rack, switch, topology)
- Saves sample API responses to `logs/api_responses/`
- Generates summary report in `logs/api_field_discovery.json`

**Output:**
- Console summary of discovered fields
- JSON file with complete field inventory
- Sample API responses for analysis

---

## Step 2: Review Discovered Fields

After running the discovery script:

1. **Check the console output** for immediate findings
2. **Review `logs/api_field_discovery.json`** for complete field list
3. **Examine sample responses** in `logs/api_responses/` directory
4. **Compare with needed fields** listed in `docs/API_DISCOVERY_MULTI_RACK.md`

**Key Fields to Look For:**

### Rack Identification
- `rack_id`, `rack_number`, `rack_name`, `rack_label`
- `location.rack`, `physical_location.rack`

### Switch Classification
- `switch_type`, `role`, `topology_role`
- `is_leaf`, `is_spine`
- `rack_unit` (for switches)

### Topology Information
- `connected_racks`
- `topology.role`
- `spine_connections`

---

## Step 3: Generate Test Report

Generate a report to see current behavior:

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

**Review the report for:**
- Current CBox/CNode identification
- Current DBox/DNode identification
- Current switch identification
- Missing rack information
- Missing Leaf/Spine classification

---

## Step 4: Implement Enhancements

Based on discovered fields, implement enhancements:

### If Rack Fields Found:
1. Update `src/api_handler.py` to extract rack identifiers
2. Update `src/data_extractor.py` to include rack in hardware data
3. Update `src/report_builder.py` to display rack information
4. Update `src/rack_diagram.py` to support multi-rack layouts

### If Switch Type Fields Found:
1. Update `src/api_handler.py` to extract switch type/role
2. Update `src/data_extractor.py` to classify switches
3. Update `src/report_builder.py` to separate Leaf/Spine switches
4. Update port mapping to show topology connections

### If Topology Fields Found:
1. Update `src/api_handler.py` to collect topology data
2. Create topology diagram generator
3. Update report to show inter-rack connectivity

---

## Step 5: Fallback Methods

If API doesn't provide needed fields, implement fallback methods:

### Rack Identification Fallbacks:
- **Hostname patterns:** Extract rack from hostname (e.g., "rack1-", "r1-")
- **IP address ranges:** Map IP subnets to racks
- **Configuration file:** Manual rack assignment file
- **Inference:** Group by `rack_unit` ranges (assume sequential U-numbers = same rack)

### Switch Classification Fallbacks:
- **Position-based:** Switches at U1/U2 = Leaf, others = Spine
- **Port count:** High port count = Spine, lower = Leaf
- **IP address analysis:** Different subnet = Spine switch
- **Configuration file:** Manual switch role assignment

---

## Documentation Files

### Main Documents:
- **`docs/MULTI_RACK_IDENTIFICATION_ANALYSIS.md`** - Comprehensive analysis of current implementation
- **`docs/API_DISCOVERY_MULTI_RACK.md`** - Detailed API discovery guide
- **`docs/MULTI_RACK_QUICK_START.md`** - This quick start guide

### Code Files:
- **`scripts/discover_api_fields.py`** - API field discovery script
- **`src/api_handler.py`** - API interaction (modify for new fields)
- **`src/data_extractor.py`** - Data processing (modify for rack/switch data)
- **`src/report_builder.py`** - Report generation (modify for multi-rack display)
- **`src/rack_diagram.py`** - Rack visualization (modify for multi-rack)

---

## Expected Outcomes

### After Discovery:
- ✅ List of available rack identification fields
- ✅ List of available switch classification fields
- ✅ List of available topology fields
- ✅ Sample API responses for analysis

### After Implementation:
- ✅ Reports show rack identifiers for all hardware
- ✅ Reports distinguish Leaf vs Spine switches
- ✅ Reports show multi-rack layouts
- ✅ Reports show inter-rack connectivity
- ✅ Port mapping includes rack identifiers

---

## Troubleshooting

### No Rack Fields Found:
- Check if cluster is single-rack (may not have rack fields)
- Try manual configuration file approach
- Use hostname/IP-based inference

### No Switch Type Fields Found:
- Use position-based classification (U1/U2 = Leaf)
- Use port count analysis
- Use configuration file for manual assignment

### API Endpoints Return 404:
- Some endpoints may not exist in all VAST versions
- Focus on existing endpoints
- Use fallback methods

---

## Next Steps

1. **Wait for network connectivity** to cluster 10.142.11.204
2. **Run discovery script** to identify available fields
3. **Review findings** and compare with needed fields
4. **Implement enhancements** based on discovered fields
5. **Test with multi-rack deployment** to validate

---

**Last Updated:** November 5, 2025
**Status:** Ready for execution when network connectivity is available
