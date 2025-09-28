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
- **VAST Credentials**: Valid VAST cluster credentials with read access
- **Permissions**: Read-only access to cluster configuration and status information
- **API Access**: VAST REST API v7 support (VAST cluster version 5.3+)

### Dependencies
- All Python dependencies are listed in `requirements.txt`
- PDF generation requires ReportLab (included) or WeasyPrint (optional)
- Additional system libraries may be required for WeasyPrint (see troubleshooting section)

## Installation

### Quick Start for PS Engineers

**For Mac Users:**
```bash
# Download and run the automated installation script
curl -O https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/install-mac.sh
chmod +x install-mac.sh
./install-mac.sh
```

**For Windows Users:**
```powershell
# Download and run the automated installation script
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rstamps01/ps-deploy-report/develop/install-windows.ps1" -OutFile "install-windows.ps1"
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

### Platform-Specific Installation Guides

- **📖 [Complete Installation Guide](INSTALLATION-GUIDE.md)**: Comprehensive installation instructions for Mac and Windows
- **🍎 [macOS Installation Script](install-mac.sh)**: Automated installation for Mac users
- **🪟 [Windows Installation Script](install-windows.ps1)**: Automated installation for Windows users
- **🔗 [API Reference](API-REFERENCE.md)**: Complete API documentation with curl examples

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
   sudo cp config/logrotate.conf /etc/logrotate.d/vast-reporter
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
  file_path: "/var/log/vast-reporter/vast_report_generator.log"

security:
  prompt_for_credentials: true
  session_timeout: 1800
```

## Usage

### Command Line Interface

The VAST As-Built Report Generator provides a comprehensive command-line interface with multiple options for different deployment scenarios.

#### Basic Usage
```bash
python3 src/main.py --cluster 192.168.1.100 --output ./output
```

#### Advanced Usage Options

**Full command syntax:**
```bash
python3 src/main.py [OPTIONS]
```

**Available options:**
- `--cluster, --cluster-ip CLUSTER_IP`: IP address of the VAST Management Service (required)
- `--output, --output-dir OUTPUT_DIR`: Output directory for generated reports (required)
- `--username, -u USERNAME`: VAST username (will prompt if not provided)
- `--password, -p PASSWORD`: VAST password (will prompt if not provided)
- `--config, -c CONFIG`: Path to configuration file (default: config/config.yaml)
- `--verbose, -v`: Enable verbose output for debugging
- `--version`: Show program version and exit
- `--help, -h`: Show help message and exit

#### Usage Examples

**1. Interactive credential entry (recommended for security):**
```bash
python3 src/main.py --cluster 192.168.1.100 --output ./reports
# Tool will prompt for username and password securely
```

**2. Using environment variables:**
```bash
export VAST_USERNAME=admin
export VAST_PASSWORD=your_password
python3 src/main.py --cluster 192.168.1.100 --output ./reports
```

**3. Command-line credentials (not recommended for production):**
```bash
python3 src/main.py --cluster 192.168.1.100 --username admin --password your_password --output ./reports
```

**4. Custom configuration file:**
```bash
python3 src/main.py --cluster 192.168.1.100 --output ./reports --config /path/to/custom_config.yaml
```

**5. Verbose output for debugging:**
```bash
python3 src/main.py --cluster 192.168.1.100 --output ./reports --verbose
```

**6. Batch processing with script:**
```bash
#!/bin/bash
# Process multiple clusters
for cluster in 192.168.1.100 192.168.1.101 192.168.1.102; do
    python3 src/main.py --cluster $cluster --output ./reports/$cluster
done
```

### Output Files

The tool generates comprehensive output in multiple formats:

#### 1. PDF Report (`vast_asbuilt_report_{cluster_name}_{timestamp}.pdf`)
- **Professional customer-facing document**
- **Comprehensive sections:**
  - Executive Summary with cluster overview and statistics
  - Cluster Information with detailed configuration
  - Hardware Inventory with rack positioning and U-numbers
  - Network Configuration (DNS, NTP, VIP pools)
  - Logical Configuration (tenants, views, policies)
  - Security & Authentication settings
  - Data Protection configuration
  - Enhanced Features (rack positioning, PSNT tracking)
  - Appendix with metadata and physical layout

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

**1. Connection Timeout**
```bash
# Increase timeout in config.yaml
api:
  timeout: 60
  max_retries: 5
```

**2. SSL Certificate Issues**
```bash
# Disable SSL verification for self-signed certs
api:
  verify_ssl: false
```

**3. WeasyPrint Dependencies Missing**
```bash
# Install system dependencies
# Ubuntu/Debian:
sudo apt-get install libpango1.0-dev libharfbuzz-dev libffi-dev libxml2-dev libxslt1-dev

# macOS:
brew install pango harfbuzz libffi libxml2 libxslt
```

**4. Permission Issues**
```bash
# Ensure proper permissions
chmod +x src/main.py
chmod 755 output/
chmod 755 logs/
```

#### Debug Mode
```bash
# Enable verbose logging
python3 src/main.py --cluster 192.168.1.100 --output ./reports --verbose

# Check configuration
python3 -c "import yaml; print(yaml.safe_load(open('config/config.yaml')))"
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
├── STATUS.md                    # Development status tracking
├── API-REFERENCE.md             # Complete API documentation
├── requirements.txt             # Python dependencies
├── config/                      # Configuration files
│   ├── config.yaml             # Main configuration
│   └── config.yaml.template    # Configuration template
├── src/                         # Source code
│   ├── main.py                 # Main CLI application
│   ├── api_handler.py          # VAST API client
│   ├── data_extractor.py       # Data processing module
│   ├── report_builder.py       # PDF report generation
│   └── utils/                  # Utility modules
│       └── logger.py           # Logging infrastructure
├── tests/                       # Unit and integration tests
│   ├── test_main.py            # Main application tests
│   ├── test_api_handler.py     # API handler tests
│   ├── test_data_extractor.py  # Data extractor tests
│   └── test_report_builder.py  # Report builder tests
├── templates/                   # Report templates
│   └── config.yaml.template    # Configuration template
├── docs/                        # Documentation
│   └── design-guide/           # Design documentation
├── logs/                        # Application logs
└── output/                      # Generated reports
```

## Development

This project follows the development guidelines outlined in the AI Development Reference Guide. See `STATUS.md` for current development status and next steps.

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

**Version**: 1.0.0-dev
**Target VAST Version**: 5.3+
**API Version**: 7
**Development Status**: 95% Complete
**Last Updated**: September 27, 2025
