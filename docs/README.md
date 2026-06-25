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
└── development/                     # Developer references and active guides
    ├── HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md
    ├── READ_ONLY_VAST_API_POLICY.md
    └── TELEMETRY.md
```

> Historical implementation notes, RCA write-ups, and completed-issue evidence
> were retired in the v1.5.8 pre-release cleanup; their content remains in git
> history (see the `pre-1.5.8-cleanup` tag).

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
| [Telemetry](development/TELEMETRY.md) | Opt-in usage metrics and future central-receiver contract |

### Project Design (Confluence — Internal Only)

26 design documents are synced from Confluence (page 6664028496) into `docs/confluence/` on developer machines. These serve as the authoritative source for project requirements, design decisions, and implementation guidance. They are **not published to GitHub** — see `.cursor/rules/` for how they are referenced by workspace rules.

---

**Last Updated**: June 25, 2026
**Maintained By**: VAST Professional Services
