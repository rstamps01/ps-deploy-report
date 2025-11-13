# VAST As-Built Report Generator

A comprehensive Python command-line tool that automatically generates professional "as-built" reports for VAST Data clusters following deployment by Professional Services. This tool achieves 80% automation in data collection and provides enhanced features for rack positioning and PSNT tracking.

## Overview

The VAST As-Built Report Generator connects to VAST Data clusters via the REST API v7, extracts comprehensive configuration and status information, and generates both professional PDF reports and machine-readable JSON data files. It is designed to streamline the post-deployment documentation process for VAST Professional Services engineers while providing enhanced automation and professional reporting capabilities.

## Key Features

### 🚀 **Enhanced Automation (80% Target Achieved)**
- **Automated Data Collection**: Comprehensive cluster data extraction with 80% automation
- **Enhanced API Integration**: Support for VAST REST API v7 with advanced features
- **Rack Positioning**: Automated U-number generation and physical layout visualization
- **PSNT Tracking**: Cluster Product Serial Number integration for support systems

### 📊 **Professional Reporting**
- **Dual Output Formats**: Professional PDF reports and machine-readable JSON files
- **Comprehensive Sections**: Executive summary, hardware inventory, network configuration, security settings, and more
- **Professional Formatting**: Customer-ready PDF documents with proper styling and organization
- **Enhanced Data Visualization**: Professional tables, charts, and layout formatting

### 🔒 **Security & Reliability**
- **Secure Authentication**: Multiple credential handling methods (CLI args, environment variables, interactive prompts)
- **Fault Tolerance**: Handles network failures, API errors, and missing data gracefully
- **Comprehensive Logging**: Detailed logging with sensitive data filtering for troubleshooting and audit
- **Error Recovery**: Graceful degradation and retry mechanisms with exponential backoff

### 🛠 **Administration & Operations**
- **Flexible Configuration**: YAML-based configuration with environment-specific settings
- **Multiple Output Options**: Configurable output directories and file naming conventions
- **Comprehensive Testing**: 100+ unit tests with 100% pass rate
- **Professional Documentation**: Complete API documentation and user guides

## Requirements

### System Requirements
- **Python**: 3.8 or higher (tested with Python 3.12)
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 512MB RAM (1GB recommended)
- **Disk Space**: 100MB for installation, additional space for output files

### Network Requirements
- **Network Access**: Direct network access to VAST Management Service (VMS)
- **Ports**: HTTPS (443) access to VAST cluster management interface
- **SSL/TLS**: Support for SSL certificate verification (configurable for self-signed certs)

### Authentication Requirements
- **VAST Credentials**: Valid VAST cluster credentials with elevated read access
- **Required Username**: `support` user or equivalent with full read permissions
- **Permissions**: Comprehensive read access to cluster configuration, hardware, and status information
- **API Access**: VAST REST API v7 support (VAST cluster version 5.3+)
- **Note**: Standard user accounts may have insufficient permissions for complete report generation

### Dependencies
- All Python dependencies are listed in `requirements.txt`
- PDF generation requires ReportLab (included) or WeasyPrint (optional)
- Additional system libraries may be required for WeasyPrint (see troubleshooting section)

## Installation

### Quick Start for PS Engineers

**For Mac Users:**
```bash
# Download and run the automated installation script
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/v1.3.0/docs/deployment/install-mac.sh
chmod +x install-mac.sh
./install-mac.sh
```

**For Windows Users:**
```powershell
# Download and run the automated installation script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/v1.3.0/docs/deployment/install-windows.ps1" -OutFile "install-windows.ps1"
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.\install-windows.ps1
```

### Manual Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/rstamps01/ps-deploy-report.git
   cd ps-deploy-report
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # Create virtual environment
   python3 -m venv venv

   # Activate virtual environment
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation:**
   ```bash
   python3 src/main.py --version
   ```

### Documentation & Guides

- **📖 [Installation Guide](docs/deployment/INSTALLATION-GUIDE.md)**: Complete installation instructions for Mac and Windows
- **🔄 [Update Guide](docs/deployment/UPDATE-GUIDE.md)**: Update existing installations to latest version
- **🗑️ [Uninstall Guide](docs/deployment/UNINSTALL-GUIDE.md)**: Complete removal instructions and procedures
- **🔐 [Permissions Guide](docs/deployment/PERMISSIONS-GUIDE.md)**: API permissions and support user requirements
- **🚀 [Deployment Guide](docs/deployment/DEPLOYMENT.md)**: Production deployment and configuration

### Installation Scripts

- **🍎 [macOS Install](docs/deployment/install-mac.sh)**: Automated installation for Mac
- **🪟 [Windows Install](docs/deployment/install-windows.ps1)**: Automated installation for Windows
- **🍎 [macOS Uninstall](docs/deployment/uninstall-mac.sh)**: Automated uninstallation for Mac
- **🪟 [Windows Uninstall](docs/deployment/uninstall-windows.ps1)**: Automated uninstallation for Windows

### Production Installation

For production deployments, consider the following additional steps:

1. **System-level dependencies (for WeasyPrint support):**
   ```bash
   # Ubuntu/Debian
   sudo apt-get install libpango1.0-dev libharfbuzz-dev libffi-dev libxml2-dev libxslt1-dev

   # CentOS/RHEL
   sudo yum install pango-devel harfbuzz-devel libffi-devel libxml2-devel libxslt-devel

   # macOS (with Homebrew)
   brew install pango harfbuzz libffi libxml2 libxslt
   ```

2. **Create dedicated user account:**
   ```bash
   sudo useradd -m -s /bin/bash vast-reporter
   sudo su - vast-reporter
   # Follow quick start installation steps
   ```

3. **Set up log rotation:**
   ```bash
   sudo cp config/logrotate.conf /etc/logrotate.d/vast-asbuilt-reporter
   ```

## Configuration

### Initial Configuration

1. **Copy the configuration template:**
   ```bash
   cp config/config.yaml.template config/config.yaml
   ```

2. **Edit configuration file:**
   ```bash
   nano config/config.yaml  # or your preferred editor
   ```

### Configuration Options

The `config/config.yaml` file contains comprehensive settings for:

#### API Configuration
- **Connection timeout**: Adjustable timeout for API requests (default: 30 seconds)
- **Retry settings**: Number of retries and delay between attempts
- **SSL verification**: Enable/disable SSL certificate verification
- **API version**: Target API version (default: v7)

#### Logging Configuration
- **Log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Log rotation**: File size limits and backup retention
- **Console colors**: Colored output for different log levels
- **Sensitive data filtering**: Automatic redaction of credentials

#### Report Configuration
- **Organization details**: Company name and branding
- **Page formatting**: Page size, margins, fonts
- **PDF options**: Table of contents, page numbers, styling
- **Output settings**: File naming conventions and directories

#### Data Collection Settings
- **Report sections**: Enable/disable specific report sections
- **Concurrent requests**: Parallel processing limits
- **Data validation**: Response validation and error handling
- **Graceful degradation**: Handle missing data gracefully

#### Security Settings
- **Credential handling**: Interactive prompts and environment variables
- **Session management**: Timeout and security settings
- **Data sanitization**: Log filtering and sensitive data protection

### Environment-Specific Configuration

#### Development Environment
```yaml
logging:
  level: "DEBUG"
  console_colors:
    DEBUG: "cyan"

api:
  timeout: 60
  max_retries: 5
```

#### Production Environment
```yaml
logging:
  level: "INFO"
  file_path: "/var/log/vast-asbuilt-reporter/vast_report_generator.log"

security:
  prompt_for_credentials: true
  session_timeout: 1800
```

## Usage

### Command Line Interface

The VAST As-Built Report Generator provides a comprehensive command-line interface with multiple options for different deployment scenarios.

#### Basic Usage
```bash
python3 -m src.main --cluster-ip 192.168.1.100 --output-dir ./reports
```

#### Advanced Usage Options

**Full command syntax:**
```bash
python3 -m src.main [OPTIONS]
```

**Available options:**
- `--cluster-ip CLUSTER_IP` or `--cluster CLUSTER_IP`: IP address of the VAST Management Service (required)
- `--output-dir OUTPUT_DIR` or `--output OUTPUT_DIR`: Output directory for generated reports (required)
- `--username USERNAME` or `-u USERNAME`: VAST username (will prompt if not provided)
- `--password PASSWORD` or `-p PASSWORD`: VAST password (will prompt if not provided)
- `--token TOKEN` or `-t TOKEN`: API token for authentication (alternative to username/password)
- `--enable-port-mapping`: Enable port mapping collection via switch SSH access
- `--switch-user SWITCH_USER`: SSH username for switches (default: cumulus)
- `--switch-password SWITCH_PASSWORD`: SSH password for switches
- `--node-user NODE_USER`: SSH username for VAST nodes (default: vastdata)
- `--node-password NODE_PASSWORD`: SSH password for VAST nodes
- `--config CONFIG`: Path to configuration file (optional)
- `--verbose`: Enable verbose output for debugging
- `--version`: Show program version and exit
- `--help`: Show help message and exit

#### Usage Examples

**1. Interactive credential entry (recommended for security):**
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --output-dir ./reports
# Tool will prompt for username and password securely
# Use 'support' username for full API access
```

**2. Using command-line credentials:**
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir ./reports
# Note: Use 'support' username or equivalent for full report generation
```

**3. Using API token (recommended for automation):**
```bash
python3 -m src.main --cluster-ip 10.143.11.204 --token YOUR_API_TOKEN --output-dir ./reports
```

**4. Custom configuration file:**
```bash
python3 -m src.main --cluster-ip 10.143.11.204 --output-dir ./reports --config /path/to/custom_config.yaml
```

**5. Verbose output for debugging:**
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir ./reports --verbose
```

**6. Generate report with port mapping:**
```bash
python3 -m src.main --cluster 10.143.11.204 \
  --username support --password <PASSWORD> \
  --node-user vastdata --node-password <NODE_PASSWORD> \
  --switch-user cumulus --switch-password <SWITCH_PASSWORD> \
  --enable-port-mapping \
  --output output
```

**7. Batch processing with script:**
```bash
#!/bin/bash
# Process multiple clusters
for cluster in cluster1.example.com cluster2.example.com cluster3.example.com; do
    python3 -m src.main --cluster-ip $cluster --username $VAST_USERNAME --password $VAST_PASSWORD --output-dir ./reports
done
```

### Output Files

The tool generates comprehensive output in multiple formats:

#### 1. PDF Report (`vast_asbuilt_report_{cluster_name}_{timestamp}.pdf`)
- **Professional customer-facing document** with VAST brand styling
- **Comprehensive sections:**
  1. Title Page with cluster identity and PSNT
  2. Executive Summary with cluster and hardware overview
  3. Cluster Information with configuration and feature flags
  4. Hardware Summary with storage capacity metrics
  5. Hardware Inventory with enhanced node-level detail:
     - **Node column**: Shows programmatically generated CNode/DNode names (e.g., `cnode-3-10`, `dnode-3-112`)
     - **One row per node**: Each CNode and DNode has its own row for detailed tracking
     - **Multiple nodes per box**: If a CBox or DBox contains multiple nodes, each appears on a separate row
     - **Optimized column widths**: Model column expanded for better readability
  6. Physical Rack Layout with visual 42U rack diagram
  7. Network Configuration with detailed network settings
  8. Logical Network Diagram with topology visualization (includes port mapping connections when available)
  9. Logical Configuration (VIP pools, tenants, views, policies)
  10. Security & Authentication settings
  11. Port Mapping (when enabled via `--enable-port-mapping`)

#### 2. JSON Data File (`vast_data_{cluster_name}_{timestamp}.json`)
- **Machine-readable structured data**
- **Complete cluster configuration**
- **Enhanced features data (rack heights, PSNT)**
- **Metadata and processing information**
- **Suitable for automation and integration**

#### 3. Log Files (`logs/vast_report_generator.log`)
- **Detailed execution logs**
- **Error tracking and debugging information**
- **Sensitive data filtering enabled**
- **Configurable log rotation**

### File Naming Convention

Output files follow a consistent naming pattern:
- **PDF Reports**: `vast_asbuilt_report_{cluster_name}_{timestamp}.pdf`
- **JSON Data**: `vast_data_{cluster_name}_{timestamp}.json`
- **Timestamp Format**: `YYYYMMDD_HHMMSS` (e.g., `20250927_143022`)

**Example output files:**
```
output/
├── vast_asbuilt_report_Production-Cluster_20250927_143022.pdf
├── vast_data_Production-Cluster_20250927_143022.json
└── logs/
    └── vast_report_generator.log
```

### Regenerating Reports from JSON Data

You can regenerate PDF reports from existing JSON data files without needing cluster access. This is useful for:
- **Formatting adjustments**: Iterate on report layout and styling
- **Template updates**: Test new report templates with existing data
- **Offline work**: Work on reports without cluster connectivity
- **Data preservation**: Regenerate reports from archived JSON files

#### Basic Usage

```bash
# Regenerate from a JSON file (auto-generates output filename)
python3 scripts/regenerate_report.py output/vast_data_CLUSTER_TIMESTAMP.json

# Specify custom output file
python3 scripts/regenerate_report.py output/vast_data_CLUSTER_TIMESTAMP.json output/custom_report.pdf

# Use custom output directory
python3 scripts/regenerate_report.py output/vast_data_CLUSTER_TIMESTAMP.json --output-dir ./test_reports
```

#### Examples

**1. Regenerate latest report:**
```bash
# Find the latest JSON file
ls -t output/vast_data_*.json | head -1

# Regenerate it
python3 scripts/regenerate_report.py $(ls -t output/vast_data_*.json | head -1)
```

**2. Test formatting changes:**
```bash
# Make formatting changes to src/report_builder.py
# Then regenerate to see the changes
python3 scripts/regenerate_report.py output/vast_data_LAMBDA-VAST-SLC-02_20251106_122547.json output/test_formatting.pdf
```

**3. Batch regenerate multiple reports:**
```bash
for json_file in output/vast_data_*.json; do
    python3 scripts/regenerate_report.py "$json_file"
done
```

#### Command Options

- `json_file`: Path to JSON data file (required)
- `output_file`: Optional output PDF file path (default: auto-generated from JSON filename)
- `--output-dir`: Output directory for generated reports (default: `output`)
- `--log-level`: Logging level - DEBUG, INFO, WARNING, ERROR (default: INFO)

**Note**: The regeneration utility uses the same report builder as the main tool, so any formatting changes you make to `src/report_builder.py` will be reflected in regenerated reports.

## Administration & Operations

### Monitoring and Logging

#### Log Management
- **Log Location**: `logs/vast_report_generator.log`
- **Log Rotation**: Automatic rotation at 10MB with 5 backup files
- **Log Levels**: Configurable (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Sensitive Data**: Automatic filtering of credentials and sensitive information

#### Monitoring Commands
```bash
# View recent logs
tail -f logs/vast_report_generator.log

# Check log rotation
ls -la logs/

# Monitor specific log levels
grep "ERROR" logs/vast_report_generator.log
```

### Troubleshooting

#### Common Issues

**1. Insufficient API Permissions**
```
Error: API request failed with 403 Forbidden
Error: Incomplete data - missing hardware/network information
```

**Solution**: Use the `support` username or an account with equivalent elevated read permissions:
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --username support --password <PASSWORD> --output-dir ./reports
```

**Required Permissions**:
- Read access to `/api/v7/clusters/`
- Read access to `/api/v7/cnodes/`, `/api/v7/dnodes/`
- Read access to `/api/v1/cboxes/`, `/api/v7/dboxes/`
- Read access to network, tenant, and policy endpoints

**2. Connection Timeout**
```bash
# Increase timeout in config.yaml
api:
  timeout: 60
  max_retries: 5
```

**3. SSL Certificate Issues**
```bash
# Disable SSL verification for self-signed certs
api:
  verify_ssl: false
```

**4. WeasyPrint Dependencies Missing**
```bash
# Install system dependencies
# Ubuntu/Debian:
sudo apt-get install libpango1.0-dev libharfbuzz-dev libffi-dev libxml2-dev libxslt1-dev

# macOS:
brew install pango harfbuzz libffi libxml2 libxslt
```

**5. File Permission Issues**
```bash
# Ensure proper permissions
chmod +x src/main.py
chmod 755 output/
chmod 755 logs/
```

#### Debug Mode
```bash
# Enable verbose logging
python3 -m src.main --cluster-ip <CLUSTER_IP> --username <USERNAME> --password <PASSWORD> --output-dir ./reports --verbose

# Check version
python3 -m src.main --version

# Validate environment
python3 -c "import sys; print(f'Python {sys.version}')"
python3 -c "import reportlab; print(f'ReportLab {reportlab.Version}')"
```

### Security Considerations

#### Credential Management
- **Never store credentials in configuration files**
- **Use environment variables or interactive prompts**
- **Implement proper access controls for log files**
- **Regularly rotate credentials**

#### Network Security
- **Use HTTPS for all API communications**
- **Implement proper firewall rules**
- **Consider VPN access for remote clusters**
- **Monitor network traffic for anomalies**

#### Data Protection
- **Sensitive data is automatically filtered from logs**
- **Output files should be secured appropriately**
- **Implement proper backup and retention policies**
- **Consider encryption for stored reports**

### Performance Optimization

#### Configuration Tuning
```yaml
# Optimize for large clusters
api:
  timeout: 120
  max_retries: 3
  concurrent_requests: 10

data_collection:
  concurrent_requests: 8
  validate_responses: true
```

#### Resource Management
- **Monitor memory usage for large clusters**
- **Adjust concurrent request limits based on cluster size**
- **Implement proper cleanup of temporary files**
- **Consider scheduling during off-peak hours**

### Updating

To update an existing installation to the latest version:

**Quick Update (Recommended)**:
```bash
cd ~/vast-asbuilt-reporter
git pull origin main
source venv/bin/activate  # Mac/Linux
# .\venv\Scripts\Activate  # Windows
pip install --upgrade -r requirements.txt
```

**For detailed update procedures**, see the [Update Guide](docs/deployment/UPDATE-GUIDE.md).

### Uninstalling

To remove the VAST As-Built Report Generator:

**Automated Uninstall (Mac)**:
```bash
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/v1.1.0/docs/deployment/uninstall-mac.sh
chmod +x uninstall-mac.sh
./uninstall-mac.sh
```

**Automated Uninstall (Windows)**:
```powershell
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/v1.1.0/docs/deployment/uninstall-windows.ps1" -OutFile "uninstall-windows.ps1"
.\uninstall-windows.ps1
```

**For manual uninstall procedures**, see the [Uninstall Guide](docs/deployment/UNINSTALL-GUIDE.md).

### Backup and Recovery

#### Backup Strategy
```bash
# Backup configuration
cp config/config.yaml config/config.yaml.backup

# Backup logs
tar -czf logs_backup_$(date +%Y%m%d).tar.gz logs/

# Backup output files
rsync -av output/ /backup/vast-reports/
```

#### Recovery Procedures
```bash
# Restore configuration
cp config/config.yaml.backup config/config.yaml

# Restore from backup
tar -xzf logs_backup_20250927.tar.gz
```

## Project Structure

```
ps-deploy-report/
├── README.md                    # This documentation
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── *SUMMARY.md                  # Project cleanup summaries
├── assets/                      # Production assets
│   ├── diagrams/               # Network topology diagrams
│   └── hardware_images/        # Hardware images (CBox, DBox)
├── config/                      # Configuration files
│   └── config.yaml.template    # Configuration template
├── docs/                        # User documentation
│   ├── README.md               # Documentation overview
│   └── deployment/             # Installation & deployment
│       ├── DEPLOYMENT.md       # Deployment guide
│       ├── INSTALLATION-GUIDE.md # Installation instructions
│       ├── install-mac.sh      # macOS installation script
│       └── install-windows.ps1 # Windows installation script
├── logs/                        # Application logs (runtime)
├── output/                      # Report output (runtime)
├── reports/                     # Production reports
│   ├── MVP/                    # MVP baseline report
│   └── [latest reports]        # Current production reports
├── src/                         # Source code
│   ├── main.py                 # Main CLI application
│   ├── api_handler.py          # VAST API client
│   ├── data_extractor.py       # Data processing module
│   ├── report_builder.py       # Report generation
│   ├── rack_diagram.py         # Rack diagram generator
│   ├── brand_compliance.py     # VAST brand styling
│   └── utils/                  # Utility modules
│       └── logger.py           # Logging infrastructure
├── templates/                   # Configuration templates
│   └── config.yaml.template    # Config template
└── tests/                       # Unit tests
    ├── test_*.py               # Test files
    └── data/                   # Test data
```

**Note**: Development documentation and archived reports are in `.archive/` (local only, not in Git).
See `.archive/README.md` for development materials.

## Development

This project follows Python best practices and VAST brand guidelines. All development documentation is preserved in `.archive/development_docs/` including:

- **Design Guidelines**: `.archive/development_docs/design-guide/`
- **Implementation Guides**: `.archive/development_docs/guides/`
- **Technical Analysis**: `.archive/development_docs/analysis/`
- **API Reference**: `.archive/development_docs/design-guide/10-API-Reference.pdf`

### Testing
```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test module
python3 -m pytest tests/test_main.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

### Code Quality
```bash
# Lint code
flake8 src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/
```

## Support

For issues, questions, or contributions, please refer to the project's GitHub repository.

### Getting Help
1. **Check the logs** for error messages
2. **Review the configuration** for common issues
3. **Consult the troubleshooting section** above
4. **Check the GitHub issues** for known problems
5. **Create a new issue** with detailed information

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

[License information to be added]

---

**Version**: 1.3.0
**Target VAST Version**: 5.3+
**API Version**: v7 (with v1 fallback)
**Status**: Production Ready
**Last Updated**: November 12, 2025

## Recent Updates (v1.3.0)

### Installation Script Enhancements
- **Enhanced Features Documentation**: Installation scripts now document enhanced features during installation
- **Port Mapping Examples**: Added port mapping usage examples to installation instructions
- **Dependency Verification**: Installation scripts verify and document all enhanced feature dependencies

## Recent Updates (v1.2.0)

### Hardware Inventory Enhancements
- **Node Column**: Replaced ID column with "Node" column showing programmatically generated CNode/DNode names
- **One Row Per Node**: Each CNode and DNode now appears on its own row for better tracking
- **Multiple Nodes Support**: CBoxes and DBoxes with multiple nodes display each node on a separate row
- **Column Renaming**: 
  - "CNode/DNode" → "Node"
  - "Position" → "Height"
- **Optimized Column Widths**: Model column expanded, Rack/Node/Height columns narrowed for better layout
- **Node Name Source**: Uses programmatically generated `name` field (e.g., `cnode-3-10`) instead of customer-assigned hostnames

### Port Mapping Improvements
- Enhanced port mapping collection via SSH
- Support for Cumulus and Onyx switch operating systems
- Automatic IPL (Inter-Peer Link) connection detection
- Network topology diagram includes port mapping connections when available

### Data Collection Enhancements
- Improved CNode and DNode name extraction from API
- Enhanced DBox association for DNodes
- Better handling of multiple nodes per physical box
