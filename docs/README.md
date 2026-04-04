# Documentation

## Overview

This directory contains all documentation for the VAST As-Built Report Generator, organized into four categories: top-level operational guides, deployment guides for end users, development references for contributors, and project design documents synced from Confluence.

---

## Directory Structure

```
docs/
├── README.md                        # This file
├── ADVANCED-OPERATIONS.md           # Advanced Operations workflows guide
├── API-REFERENCE.md                 # VAST REST API endpoints reference
├── POST-INSTALL-VALIDATION.md       # Post-install validation procedures
├── PRE-RELEASE-QA-GAP-ANALYSIS.md   # Pre-release QA checklist
├── TODO-ROADMAP.md                  # Canonical roadmap and task tracking
├── api/                             # API discovery documentation
│   ├── CLUSTER_10.143.11.202_API_DISCOVERY.md
│   └── EBOX_API_V7_DISCOVERY.md
├── confluence/                      # Internal only — not published to GitHub
│   └── (26 design & requirements docs synced from Confluence)
├── deployment/                      # End-user installation and operations
│   ├── DEPLOYMENT.md                # Production deployment guide
│   ├── INSTALLATION-GUIDE.md        # Step-by-step installation
│   ├── UPDATE-GUIDE.md              # Update/upgrade procedures
│   ├── UNINSTALL-GUIDE.md           # Complete removal procedures
│   ├── PERMISSIONS-GUIDE.md         # API permissions & support user requirements
│   ├── PORT-MAPPING-GUIDE.md        # SSH-based switch port mapping setup
│   ├── WINDOWS-ZIP-PACKAGE-AND-WORKFLOWS.md  # Windows packaging details
│   ├── PYTHON_3.14_INSTALLATION_FIX.md
│   ├── install-mac.sh              # Automated macOS installation
│   ├── install-windows.ps1         # Automated Windows installation
│   ├── uninstall-mac.sh            # Automated macOS uninstall
│   └── uninstall-windows.ps1       # Automated Windows uninstall
└── development/                     # Developer references and analysis
    ├── DYNAMIC-TOC-IMPLEMENTATION.md
    ├── EBOX-HARDWARE-TABLE-IMPLEMENTATION-PLAN.md
    ├── HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md
    ├── MYPY_FIX_SUGGESTIONS.md
    ├── READ_ONLY_VAST_API_POLICY.md
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

### Operational Guides

| Document | Purpose |
|----------|---------|
| [Advanced Operations](ADVANCED-OPERATIONS.md) | Developer-mode workflows (vnetmap, support tools, vperfsanity, log bundle, switch/network config) |
| [Post-Install Validation](POST-INSTALL-VALIDATION.md) | Post-install validation procedures and One-Shot mode |
| [API Reference](API-REFERENCE.md) | VAST REST API endpoints used by the app (v7 and v1) |
| [TODO Roadmap](TODO-ROADMAP.md) | Canonical roadmap and task tracking |

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
| [Health Check Module Guide](development/HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md) | Tier 1 + Tier 3 health check architecture and implementation |
| [Read-Only API Policy](development/READ_ONLY_VAST_API_POLICY.md) | GET-only API access policy rationale |
| [EBox Hardware Plan](development/EBOX-HARDWARE-TABLE-IMPLEMENTATION-PLAN.md) | EBox cluster support implementation |
| [Onyx SSH Implementation](development/ONYX_INTERACTIVE_SSH_IMPLEMENTATION.md) | Mellanox Onyx interactive SSH approach |
| [Onyx Support Summary](development/ONYX_SUPPORT_SUMMARY.md) | Onyx OS detection and dual-credential support |
| [Port Mapping Analysis](development/PORT_MAPPING_ANALYSIS.md) | Port mapping discovery troubleshooting |
| [Multi-Rack Analysis](development/MULTI_RACK_IDENTIFICATION_ANALYSIS.md) | Multi-rack detection via API |
| [TOC Implementation](development/TOC-IMPLEMENTATION-GUIDE.md) | Dynamic table of contents generation |

### Project Design (Confluence — Internal Only)

26 design documents are synced from Confluence (page 6664028496) into `docs/confluence/` on developer machines. These serve as the authoritative source for project requirements, design decisions, and implementation guidance. They are **not published to GitHub** — see `.cursor/rules/` for how they are referenced by workspace rules.

---

**Last Updated**: March 21, 2026
**Maintained By**: VAST Professional Services
