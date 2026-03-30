# VAST As-Built Report Generator — Reports Directory

## Overview

This directory contains generated VAST As-Built reports. All development iterations and test reports have been archived to maintain a clean working structure.

## Active Reports

### Current Production Report
**Latest Report**: `vast_asbuilt_report_<cluster>_<timestamp>.pdf`
- Most recent production-ready report
- Includes all latest features and improvements
- Automatically replaces previous version on new generation

### MVP Baseline Report
**Location**: `MVP/vast_asbuilt_report_MVP_baseline_selab-var-204/`
- Reference baseline for minimum viable product
- Preserved for comparison and rollback purposes
- Generated: October 17, 2025

## Report Types

- **PDF Reports**: VAST-branded reports ready for customer distribution
- **JSON Reports**: Structured data for automation, archival, and PDF regeneration

## File Naming Convention

```
vast_asbuilt_report_<cluster-name>_<timestamp>.pdf
vast_data_<cluster-name>_<timestamp>.json
```

Where:
- `<cluster-name>`: Name of the VAST cluster (e.g., selab-var-204)
- `<timestamp>`: Generation timestamp (YYYYMMDD_HHMMSS)

## Report Sections

Reports contain the following sections (each individually toggleable via config):

1. **Title Page** — Cluster identity, PSNT, hardware summary
2. **Table of Contents** — Dynamic TOC with page links
3. **Executive Summary** — Cluster and hardware overview tables
4. **Cluster Information** — Configuration and feature flags
5. **Hardware Summary** — Inventory and capacity metrics
6. **Hardware Inventory** — CBox, DBox, and EBox detailed tables
7. **Physical Rack Layout** — 42U rack diagrams with CBox, DBox, EBox, and switch positions; device status indicators (active/inactive/VMS) with legend; hardware bezel images
8. **Network Configuration** — Detailed network settings
9. **Switch Port Mapping** — Port-level connectivity (when SSH port mapping enabled)
10. **Logical Network Diagram** — Network topology with port mapping and IPL/MLAG links; EBox clusters with EB# labels and color-coded Network A/B connections
11. **Logical Configuration** — VIP pools, tenants, views, policies
12. **Security & Authentication** — Security settings
13. **Cluster Health Check Results** — Summary + detailed table (when health check enabled)
14. **Post Deployment Activities** — Dynamic next-steps checklist derived from health check results

## Generating Reports

### Web UI (recommended)

Open the **Reporter** page in the web UI, enter cluster credentials, run Discovery, and click **Run**.

### CLI

```bash
python3 src/main.py --cli --cluster <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output reports
```

### Regenerating PDF from JSON

Rebuild a PDF from a saved JSON file without cluster access:

```bash
python3 scripts/regenerate_report.py path/to/vast_data_CLUSTER_TIMESTAMP.json
python3 scripts/regenerate_report.py path/to/vast_data_CLUSTER_TIMESTAMP.json output/custom.pdf
```

The **Report Tuning Tool** on the Results page also supports regeneration with section toggles and formatting overrides.

## Report Formatting Options

Configurable via Advanced Configuration or `config/config.yaml`:

- **Organization** — Name displayed in PDF footer
- **Margins** — 0.25"–1.5" (default 0.5")
- **Font family** — Helvetica, Times-Roman, or Courier
- **Include TOC** — Toggle table of contents
- **Include Page Numbers** — Toggle page number footer

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
└── <generated reports>
```

## Archive Policy

### Keep Active
- MVP baseline report (always)
- Latest production report (current version only)

### Archive Automatically
- Development iterations
- Test reports
- Old production reports (superseded)

---

**Last Updated**: March 21, 2026
**Report Version**: v1.5.0
**Maintained By**: VAST Professional Services
