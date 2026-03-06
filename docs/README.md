# Documentation

## Overview

This directory contains all documentation for the VAST As-Built Report Generator, organized into three categories: deployment guides for end users, development references for contributors, and project design documents synced from Confluence.

---

## Directory Structure

```
docs/
├── README.md                   # This file
├── confluence/                 # 26 design & requirements docs (synced from Confluence)
│   ├── 00-VAST-As-Built-Report-Generator-v1.3.0.md
│   ├── 01-Concept.md
│   ├── 02-PRD.md
│   ├── 03-Project-Plan.md
│   ├── ...                     # See confluence/ for full listing
│   └── 14-Hardware-Diagrams.md
├── deployment/                 # End-user installation and operations
│   ├── DEPLOYMENT.md           # Production deployment guide
│   ├── INSTALLATION-GUIDE.md   # Step-by-step installation
│   ├── UPDATE-GUIDE.md         # Update/upgrade procedures
│   ├── UNINSTALL-GUIDE.md      # Complete removal procedures
│   ├── PERMISSIONS-GUIDE.md    # API permissions & support user requirements
│   ├── PORT-MAPPING-GUIDE.md   # SSH-based switch port mapping setup
│   ├── PYTHON_3.14_INSTALLATION_FIX.md
│   ├── install-mac.sh          # Automated macOS installation
│   ├── install-windows.ps1     # Automated Windows installation
│   ├── uninstall-mac.sh        # Automated macOS uninstall
│   └── uninstall-windows.ps1   # Automated Windows uninstall
└── development/                # Developer references and analysis
    ├── DYNAMIC-TOC-IMPLEMENTATION.md
    ├── TOC-IMPLEMENTATION-GUIDE.md
    ├── ONYX_INTERACTIVE_SSH_IMPLEMENTATION.md
    ├── ONYX_SUPPORT_SUMMARY.md
    ├── PORT_MAPPING_ANALYSIS.md
    ├── PORT_MAPPING_ISSUE_ANALYSIS.md
    ├── API_DISCOVERY_MULTI_RACK.md
    ├── MULTI_RACK_FINDINGS_10.143.11.204.md
    ├── MULTI_RACK_IDENTIFICATION_ANALYSIS.md
    ├── MULTI_RACK_QUICK_START.md
    ├── RCA_ANALYSIS_SUMMARY.md
    ├── RCA_LAMBDA-VAST-SLC-02_DBox_Unresponsive_Issue.md
    └── RCA_Slack_Thread_Analysis_Template.md
```

---

## Quick Links

### For End Users / PS Engineers

| Document | Purpose |
|----------|---------|
| [Installation Guide](deployment/INSTALLATION-GUIDE.md) | Install the application from scratch |
| [Update Guide](deployment/UPDATE-GUIDE.md) | Update an existing installation |
| [Uninstall Guide](deployment/UNINSTALL-GUIDE.md) | Completely remove the application |
| [Permissions Guide](deployment/PERMISSIONS-GUIDE.md) | Required API credentials and access |
| [Port Mapping Guide](deployment/PORT-MAPPING-GUIDE.md) | Set up SSH-based switch port mapping |
| [Deployment Guide](deployment/DEPLOYMENT.md) | Production configuration and operations |

### For Developers

| Document | Purpose |
|----------|---------|
| [Onyx SSH Implementation](development/ONYX_INTERACTIVE_SSH_IMPLEMENTATION.md) | Mellanox Onyx interactive SSH approach |
| [Onyx Support Summary](development/ONYX_SUPPORT_SUMMARY.md) | Onyx OS detection and dual-credential support |
| [Port Mapping Analysis](development/PORT_MAPPING_ANALYSIS.md) | Port mapping discovery troubleshooting |
| [Multi-Rack Analysis](development/MULTI_RACK_IDENTIFICATION_ANALYSIS.md) | Multi-rack detection via API |
| [TOC Implementation](development/TOC-IMPLEMENTATION-GUIDE.md) | Dynamic table of contents generation |

### Project Design (Confluence)

The `confluence/` directory contains 26 design documents synced from Confluence page 6664028496. These serve as the authoritative source for project requirements, design decisions, and implementation guidance. See `.cursor/rules/` for how these are referenced by workspace rules.

---

**Last Updated**: March 6, 2026
**Maintained By**: VAST Professional Services
