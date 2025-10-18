# Documentation

## Overview

This directory contains **user-facing documentation** for installing and using the VAST As-Built Report Generator.

All development documentation, design guides, and implementation references have been moved to `.archive/development_docs/` to maintain a clean, user-focused structure.

---

## Directory Structure

```
docs/
├── README.md (this file)
└── deployment/
    ├── DEPLOYMENT.md           # Production deployment guide
    ├── INSTALLATION-GUIDE.md   # Installation instructions
    ├── UPDATE-GUIDE.md         # Update/upgrade procedures
    ├── UNINSTALL-GUIDE.md      # Uninstallation procedures
    ├── PERMISSIONS-GUIDE.md    # API permissions & requirements
    ├── install-mac.sh          # Mac installation script
    ├── install-windows.ps1     # Windows installation script
    ├── uninstall-mac.sh        # Mac uninstall script
    └── uninstall-windows.ps1   # Windows uninstall script
```

---

## Quick Start

### Installation

**Mac/Linux**:
```bash
cd docs/deployment
chmod +x install-mac.sh
./install-mac.sh
```

**Windows**:
```powershell
cd docs\deployment
.\install-windows.ps1
```

### Generating Reports

After installation:
```bash
cd ps-deploy-report
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir reports
```

Example:
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir reports
# Note: Use 'support' username for full API permissions
```

---

## Documentation Files

### Deployment Documentation

**DEPLOYMENT.md**
- Comprehensive deployment guide
- System requirements
- Configuration options
- Troubleshooting common issues

**INSTALLATION-GUIDE.md**
- Step-by-step installation instructions
- Platform-specific guidance
- Dependency management
- Verification procedures

**UPDATE-GUIDE.md**
- Update existing installations
- Version upgrade procedures
- Rollback strategies
- Automated update scripts

**UNINSTALL-GUIDE.md**
- Complete removal procedures
- Manual and automated uninstall
- Data backup and preservation
- Cleanup verification

**PERMISSIONS-GUIDE.md**
- Required API permissions
- Support username requirements
- Troubleshooting permission errors
- Security best practices

**Installation Scripts**
- `install-mac.sh` - Automated Mac/Linux installation
- `install-windows.ps1` - Automated Windows installation
- `uninstall-mac.sh` - Automated Mac/Linux uninstall
- `uninstall-windows.ps1` - Automated Windows uninstall

---

## Development Documentation

All development-related documentation has been moved to:
```
.archive/development_docs/
├── design-guide/        # Original design documents and requirements
├── analysis/            # Technical analysis and implementation studies
├── guides/              # Development guides and technical references
└── test/                # Test documentation
```

**To access development docs**: See `.archive/development_docs/README.md`

---

## Support

### Common Issues

**Installation Problems**:
- Check Python version (3.8+ required)
- Verify pip is updated
- Review logs in `logs/` directory

**Report Generation Issues**:
- Verify cluster connectivity
- **Use 'support' username for full API access**
- Check credentials and permissions
- Review API version compatibility
- Ensure elevated read permissions for all endpoints

**Permission Errors**:
- Standard user accounts may lack sufficient API permissions
- Report generation requires comprehensive read access
- Use `support` user or equivalent elevated account

**For detailed troubleshooting**: See deployment documentation

---

## System Requirements

### Minimum Requirements
- Python 3.8 or higher
- pip (Python package installer)
- Network access to VAST cluster
- 500MB free disk space

### Supported Platforms
- macOS 10.15+
- Linux (Ubuntu 18.04+, RHEL 7+)
- Windows 10/11

---

## Report Features

### Generated Report Includes

1. **Title Page** - Cluster identity and configuration
2. **Executive Summary** - Overview tables
3. **Cluster Information** - Detailed configuration
4. **Hardware Summary** - Inventory and capacity
5. **Hardware Inventory** - Detailed tables with images
6. **Physical Rack Layout** - Visual 42U rack diagram
7. **Network Configuration** - Network settings
8. **Logical Network Diagram** - Topology visualization
9. **Logical Configuration** - VIP pools, tenants, views
10. **Security & Authentication** - Security settings

### Report Formats
- **PDF** - Professional formatted report
- **JSON** - Raw data for programmatic access

---

## Quick Reference

### Generate Report
```bash
python3 -m src.main \
  --cluster-ip <IP> \
  --username <USER> \
  --password <PASS> \
  --output-dir reports
```

### View Latest Report
```bash
open reports/vast_asbuilt_report_*.pdf  # Mac
xdg-open reports/vast_asbuilt_report_*.pdf  # Linux
start reports\vast_asbuilt_report_*.pdf  # Windows
```

### Check Installation
```bash
python3 -m src.main --version
```

---

## Additional Resources

- **Project README**: `../README.md` - Project overview
- **Development Docs**: `.archive/development_docs/` - Technical details
- **API Reference**: `.archive/development_docs/design-guide/10-API-Reference.pdf`
- **Report Examples**: See `reports/MVP/` for sample output

---

**Last Updated**: October 17, 2025
**Version**: 1.0
**Maintained By**: VAST Professional Services
