# VAST As-Built Report Generator - Reports Directory

## Overview

This directory contains **active** VAST As-Built reports. All development iterations and test reports have been archived to maintain a clean working structure.

## Active Reports

### Current Production Report
**Latest Report**: `vast_asbuilt_report_selab-var-204_YYYYMMDD_HHMMSS.pdf`
- Most recent production-ready report
- Includes all latest features and improvements
- Automatically replaces previous version on new generation

### MVP Baseline Report
**Location**: `MVP/vast_asbuilt_report_MVP_baseline_selab-var-204/`
- Reference baseline for minimum viable product
- Preserved for comparison and rollback purposes
- Generated: October 17, 2025

## Features in Latest Report

✅ **Physical Rack Layout (Page 6)**:
- 42U rack diagram with actual hardware images
- Precise U-position placement
- Supermicro CBox and Ceres DBox hardware images
- Green status indicators

✅ **Logical Network Diagram (Page 8)**:
- Complete network topology visualization
- CBoxes, DBoxes, Switch A, Switch B connectivity
- Customer Network integration
- Color-coded network paths

✅ **Professional Styling**:
- VAST brand color scheme (#2F2042)
- Centered tables with alternating row colors
- Repeating footers with page numbers
- Section overviews for context

✅ **Comprehensive Data**:
- Cluster information and configuration
- Hardware inventory with images
- Network configuration tables
- Logical configuration details
- Security and authentication settings

## Report Types

- **PDF Reports**: Formatted reports ready for distribution
- **JSON Reports**: Raw data in JSON format for programmatic access

## File Naming Convention

```
vast_asbuilt_report_<cluster-name>_<timestamp>.pdf
vast_data_<cluster-name>_<timestamp>.json
```

Where:
- `<cluster-name>`: Name of the VAST cluster (e.g., selab-var-204)
- `<timestamp>`: Generation timestamp (YYYYMMDD_HHMMSS)

## Generating New Reports

### Basic Generation
```bash
cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir reports
```

### Example
```bash
python3 -m src.main --cluster-ip 10.143.11.204 --username support --password 654321 --output-dir reports
```

## Archived Reports

All development iterations, test reports, and reference reports have been moved to:
```
.archive/development_reports/
```

This directory is **not tracked in Git** (excluded via `.gitignore`) and includes:
- Rack diagram development iterations
- Network diagram integration phases
- Table formatting tests
- Color scheme tests
- All historical test reports

See `.archive/README.md` for detailed archive information.

## Directory Structure

```
reports/
├── README.md (this file)
├── VAST_Logo.png (used in report generation)
├── MVP/
│   └── vast_asbuilt_report_MVP_baseline_selab-var-204/
│       ├── vast_asbuilt_report_selab-var-204_20251017_084623.pdf
│       └── vast_data_selab-var-204_20251017_084623.json
├── vast_asbuilt_report_selab-var-204_20251017_180708.pdf (latest)
└── vast_data_selab-var-204_20251017_180708.json (latest)
```

## Report Sections

1. **Title Page**: Cluster identity, PSNT, hardware summary
2. **Executive Summary**: Cluster and hardware overview tables
3. **Cluster Information**: Configuration and feature flags
4. **Hardware Summary**: Inventory and capacity metrics
5. **Hardware Inventory**: CBox and DBox detailed tables
6. **Physical Rack Layout**: Visual 42U rack diagram
7. **Network Configuration**: Detailed network settings
8. **Logical Network Diagram**: Network topology visualization
9. **Logical Configuration**: VIP pools, tenants, views, policies
10. **Security & Authentication**: Security settings

## Data Completeness

Current reports achieve **84.1% data completeness**:
- ✅ Complete: Network configuration, logical configuration
- ⚠️ Partial: Cluster network (87.5%), data protection (50.0%)
- ❌ Missing: Performance metrics, licensing (cluster-specific)

## Archive Policy

### Keep Active
- ✅ MVP baseline report (always)
- ✅ Latest production report (current version only)

### Archive Automatically
- ✅ Development iterations
- ✅ Test reports
- ✅ Old production reports (superseded)

### Manual Cleanup
To free disk space, delete archived reports older than 30 days:
```bash
find ../.archive/development_reports -name "*.pdf" -mtime +30 -delete
```

---

**Last Updated**: October 17, 2025
**Report Version**: Production with Network Diagram
**Maintained By**: VAST Professional Services
