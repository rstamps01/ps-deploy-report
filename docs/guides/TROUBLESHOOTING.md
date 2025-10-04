# VAST As-Built Report Generator - Troubleshooting Guide

This guide provides comprehensive troubleshooting information for common issues encountered when deploying and using the VAST As-Built Report Generator.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Installation Issues](#installation-issues)
3. [Configuration Issues](#configuration-issues)
4. [Connection Issues](#connection-issues)
5. [Authentication Issues](#authentication-issues)
6. [PDF Generation Issues](#pdf-generation-issues)
7. [Performance Issues](#performance-issues)
8. [Log Analysis](#log-analysis)
9. [Advanced Debugging](#advanced-debugging)

## Quick Diagnostics

### Health Check Script

Create a diagnostic script to quickly identify common issues:

```bash
#!/bin/bash
# File: diagnose.sh

echo "=== VAST As-Built Report Generator Diagnostics ==="
echo "Date: $(date)"
echo

# Check Python version
echo "1. Python Version:"
python3 --version
if [ $? -eq 0 ]; then
    echo "   ✓ Python is available"
else
    echo "   ✗ Python not found"
    exit 1
fi
echo

# Check virtual environment
echo "2. Virtual Environment:"
if [ -d "venv" ]; then
    echo "   ✓ Virtual environment exists"
    if [ -f "venv/bin/activate" ]; then
        echo "   ✓ Virtual environment is valid"
    else
        echo "   ✗ Virtual environment is corrupted"
    fi
else
    echo "   ✗ Virtual environment not found"
fi
echo

# Check dependencies
echo "3. Dependencies:"
if [ -f "venv/bin/pip" ]; then
    echo "   Checking critical dependencies..."
    venv/bin/pip list | grep -E "(requests|PyYAML|reportlab)" > /dev/null
    if [ $? -eq 0 ]; then
        echo "   ✓ Critical dependencies installed"
    else
        echo "   ✗ Missing critical dependencies"
    fi
else
    echo "   ✗ pip not available in virtual environment"
fi
echo

# Check configuration
echo "4. Configuration:"
if [ -f "config/config.yaml" ]; then
    echo "   ✓ Configuration file exists"
    python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "   ✓ Configuration file is valid YAML"
    else
        echo "   ✗ Configuration file has syntax errors"
    fi
else
    echo "   ✗ Configuration file not found"
fi
echo

# Check permissions
echo "5. Permissions:"
if [ -r "src/main.py" ]; then
    echo "   ✓ Main script is readable"
else
    echo "   ✗ Main script not readable"
fi

if [ -w "output" ] || [ -w "." ]; then
    echo "   ✓ Output directory is writable"
else
    echo "   ✗ Output directory not writable"
fi
echo

# Check network connectivity
echo "6. Network Connectivity:"
if command -v curl > /dev/null; then
    echo "   Testing HTTPS connectivity..."
    curl -s --connect-timeout 5 https://httpbin.org/get > /dev/null
    if [ $? -eq 0 ]; then
        echo "   ✓ HTTPS connectivity working"
    else
        echo "   ✗ HTTPS connectivity issues"
    fi
else
    echo "   ⚠ curl not available, skipping network test"
fi
echo

echo "=== Diagnostics Complete ==="
```

### Run Diagnostics

```bash
chmod +x diagnose.sh
./diagnose.sh
```

## Installation Issues

### Python Version Issues

**Problem**: `python3: command not found`

**Solutions**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install python3 python3-pip

# macOS
brew install python3

# Verify installation
python3 --version
```

**Problem**: Python version too old (< 3.8)

**Solutions**:
```bash
# Check current version
python3 --version

# Install newer version
# Ubuntu 20.04+ has Python 3.8+
# For older systems, use pyenv or compile from source

# Using pyenv
curl https://pyenv.run | bash
pyenv install 3.12.0
pyenv global 3.12.0
```

### Virtual Environment Issues

**Problem**: `python3 -m venv` fails

**Solutions**:
```bash
# Install venv module
sudo apt-get install python3-venv  # Ubuntu/Debian
sudo yum install python3-venv      # CentOS/RHEL

# Alternative: use virtualenv
pip3 install virtualenv
virtualenv venv
```

**Problem**: Virtual environment activation fails

**Solutions**:
```bash
# Check if activation script exists
ls -la venv/bin/activate

# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
```

### Dependency Installation Issues

**Problem**: `pip install` fails with SSL errors

**Solutions**:
```bash
# Upgrade pip
python3 -m pip install --upgrade pip

# Use trusted hosts
pip install --trusted-host pypi.org --trusted-host pypi.python.org -r requirements.txt

# Use alternative index
pip install -i https://pypi.org/simple/ -r requirements.txt
```

**Problem**: WeasyPrint installation fails

**Solutions**:
```bash
# Install system dependencies first
# Ubuntu/Debian
sudo apt-get install libpango1.0-dev libharfbuzz-dev libffi-dev libxml2-dev libxslt1-dev

# CentOS/RHEL
sudo yum install pango-devel harfbuzz-devel libffi-devel libxml2-devel libxslt-devel

# macOS
brew install pango harfbuzz libffi libxml2 libxslt

# Then install Python packages
pip install weasyprint
```

## Configuration Issues

### YAML Syntax Errors

**Problem**: `yaml.scanner.ScannerError`

**Solutions**:
```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config/config.yaml'))"

# Check for common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing colons after keys
# - Unquoted special characters
# - Mismatched quotes
```

**Example of correct YAML**:
```yaml
api:
  timeout: 30
  max_retries: 3
  verify_ssl: true
```

### Missing Configuration File

**Problem**: `FileNotFoundError: config/config.yaml`

**Solutions**:
```bash
# Copy template
cp config/config.yaml.template config/config.yaml

# Or create minimal config
cat > config/config.yaml << EOF
api:
  timeout: 30
  max_retries: 3
  verify_ssl: true
logging:
  level: "INFO"
  file_path: "logs/vast_report_generator.log"
EOF
```

### Invalid Configuration Values

**Problem**: Application fails with configuration errors

**Solutions**:
```bash
# Check specific configuration values
python3 -c "
import yaml
config = yaml.safe_load(open('config/config.yaml'))
print('API timeout:', config.get('api', {}).get('timeout'))
print('Log level:', config.get('logging', {}).get('level'))
"

# Validate against schema (if available)
python3 -c "
import yaml
import jsonschema

# Load configuration
with open('config/config.yaml') as f:
    config = yaml.safe_load(f)

# Basic validation
required_sections = ['api', 'logging']
for section in required_sections:
    if section not in config:
        print(f'Missing required section: {section}')
"
```

## Connection Issues

### Network Connectivity

**Problem**: `ConnectionError: Failed to establish connection`

**Solutions**:
```bash
# Test basic connectivity
ping 192.168.1.100

# Test HTTPS connectivity
curl -k https://192.168.1.100/api/versions

# Check firewall rules
sudo ufw status
sudo iptables -L

# Test with telnet
telnet 192.168.1.100 443
```

### SSL Certificate Issues

**Problem**: `SSL: CERTIFICATE_VERIFY_FAILED`

**Solutions**:
```bash
# Option 1: Disable SSL verification (not recommended for production)
# Update config/config.yaml
api:
  verify_ssl: false

# Option 2: Add certificate to trusted store
# Download certificate
openssl s_client -connect 192.168.1.100:443 -showcerts < /dev/null 2>/dev/null | openssl x509 -outform PEM > vast-cluster.crt

# Add to trusted store
sudo cp vast-cluster.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates

# Option 3: Use custom CA bundle
api:
  verify_ssl: true
  ca_cert: /path/to/ca-bundle.crt
```

### Timeout Issues

**Problem**: `ReadTimeout: HTTPSConnectionPool`

**Solutions**:
```bash
# Increase timeout in configuration
api:
  timeout: 120
  max_retries: 5
  retry_delay: 5

# Check network latency
ping -c 10 192.168.1.100

# Test with curl
curl -w "@curl-format.txt" -o /dev/null -s https://192.168.1.100/api/versions
```

Create `curl-format.txt`:
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

## Authentication Issues

### Invalid Credentials

**Problem**: `401 Unauthorized` or `403 Forbidden`

**Solutions**:
```bash
# Test credentials manually
curl -u admin:password -k https://192.168.1.100/api/versions

# Check credential format
# Username should not contain special characters
# Password should be properly escaped if containing special characters

# Use environment variables
export VAST_USERNAME=admin
export VAST_PASSWORD='your_password'
python3 src/main.py --cluster 192.168.1.100 --output ./output
```

### Session Management Issues

**Problem**: `Session expired` or `Token invalid`

**Solutions**:
```bash
# Check session timeout settings
security:
  session_timeout: 3600  # 1 hour

# Enable session refresh
api:
  auto_refresh_session: true

# Check cluster time synchronization
# Ensure cluster and client have synchronized time
```

### Permission Issues

**Problem**: `403 Forbidden` for specific API endpoints

**Solutions**:
```bash
# Check user permissions in VAST cluster
# Ensure user has read access to required endpoints

# Test with different user account
export VAST_USERNAME=readonly_user
export VAST_PASSWORD=readonly_password

# Check API version compatibility
curl -u admin:password -k https://192.168.1.100/api/versions
```

## PDF Generation Issues

### ReportLab Issues

**Problem**: `ImportError: No module named 'reportlab'`

**Solutions**:
```bash
# Install ReportLab
pip install reportlab

# Or reinstall all dependencies
pip install -r requirements.txt

# Check installation
python3 -c "import reportlab; print(reportlab.Version)"
```

**Problem**: PDF generation fails silently

**Solutions**:
```bash
# Enable debug logging
logging:
  level: "DEBUG"

# Check file permissions
ls -la output/
chmod 755 output/

# Test with minimal data
python3 -c "
from src.report_builder import VastReportBuilder
builder = VastReportBuilder()
result = builder.generate_pdf_report({'test': 'data'}, 'test.pdf')
print('PDF generation result:', result)
"
```

### WeasyPrint Issues

**Problem**: `OSError: cannot load library 'libgobject-2.0-0'`

**Solutions**:
```bash
# Install system dependencies
# Ubuntu/Debian
sudo apt-get install libpango1.0-dev libharfbuzz-dev libffi-dev libxml2-dev libxslt1-dev

# CentOS/RHEL
sudo yum install pango-devel harfbuzz-devel libffi-devel libxml2-devel libxslt-devel

# macOS
brew install pango harfbuzz libffi libxml2 libxslt

# Alternative: Use ReportLab only
# The application will automatically fall back to ReportLab if WeasyPrint is not available
```

### Memory Issues

**Problem**: `MemoryError` during PDF generation

**Solutions**:
```bash
# Increase memory limits
ulimit -v 2097152  # 2GB virtual memory

# Optimize configuration for large reports
report:
  pdf:
    include_toc: false
    font_size: 8

# Process in smaller chunks
data_collection:
  concurrent_requests: 2
```

## Performance Issues

### Slow Data Collection

**Problem**: Data collection takes too long

**Solutions**:
```bash
# Increase concurrent requests
data_collection:
  concurrent_requests: 10

# Optimize API settings
api:
  timeout: 60
  max_retries: 2

# Disable unnecessary sections
data_collection:
  sections:
    executive_summary: true
    hardware_inventory: true
    network_configuration: false  # Disable if not needed
    logical_configuration: false
    security_authentication: false
    data_protection: false
```

### High Memory Usage

**Problem**: Application consumes too much memory

**Solutions**:
```bash
# Monitor memory usage
top -p $(pgrep -f vast-reporter)
htop

# Optimize configuration
data_collection:
  concurrent_requests: 2  # Reduce concurrent requests

# Enable garbage collection
python3 -c "
import gc
gc.set_threshold(100, 10, 10)
"
```

### Slow PDF Generation

**Problem**: PDF generation is slow

**Solutions**:
```bash
# Use ReportLab instead of WeasyPrint
# ReportLab is generally faster

# Optimize report settings
report:
  pdf:
    include_toc: false
    font_size: 10
    page_size: "A4"

# Reduce data size
data_collection:
  graceful_degradation: true
```

## Log Analysis

### Understanding Log Messages

**Log Level Meanings**:
- `DEBUG`: Detailed information for debugging
- `INFO`: General information about program execution
- `WARNING`: Something unexpected happened but program continues
- `ERROR`: A serious problem occurred
- `CRITICAL`: A very serious error occurred

**Common Log Patterns**:
```bash
# Successful connection
grep "Connected to cluster" logs/vast_report_generator.log

# Authentication issues
grep "Authentication failed" logs/vast_report_generator.log

# API errors
grep "API request failed" logs/vast_report_generator.log

# PDF generation issues
grep "PDF generation" logs/vast_report_generator.log
```

### Log Analysis Scripts

**Error Summary Script**:
```bash
#!/bin/bash
# File: analyze_logs.sh

LOG_FILE="logs/vast_report_generator.log"

echo "=== Log Analysis Report ==="
echo "Date: $(date)"
echo "Log file: $LOG_FILE"
echo

# Count log levels
echo "Log Level Summary:"
grep -o " - [A-Z]* - " $LOG_FILE | sort | uniq -c | sort -nr
echo

# Recent errors
echo "Recent Errors (last 10):"
grep "ERROR" $LOG_FILE | tail -10
echo

# Connection issues
echo "Connection Issues:"
grep -i "connection\|timeout\|refused" $LOG_FILE | wc -l
echo

# Performance metrics
echo "Performance Metrics:"
grep "Data collection completed" $LOG_FILE | tail -5
echo

echo "=== Analysis Complete ==="
```

**Real-time Monitoring**:
```bash
# Monitor logs in real-time
tail -f logs/vast_report_generator.log | grep -E "(ERROR|WARNING|CRITICAL)"

# Monitor specific patterns
tail -f logs/vast_report_generator.log | grep -E "(API request|PDF generation|Data collection)"
```

## Advanced Debugging

### Debug Mode

**Enable comprehensive debugging**:
```bash
# Set debug logging
logging:
  level: "DEBUG"

# Enable verbose output
python3 src/main.py --cluster 192.168.1.100 --output ./output --verbose

# Enable Python debug mode
PYTHONPATH=. python3 -u src/main.py --cluster 192.168.1.100 --output ./output
```

### API Testing

**Test API endpoints manually**:
```bash
# Test cluster connectivity
curl -k https://192.168.1.100/api/versions

# Test authentication
curl -u admin:password -k https://192.168.1.100/api/cluster

# Test specific endpoints
curl -u admin:password -k https://192.168.1.100/api/cnodes
curl -u admin:password -k https://192.168.1.100/api/dnodes
```

### Python Debugging

**Use Python debugger**:
```python
# Add to main.py for debugging
import pdb; pdb.set_trace()

# Or use ipdb for better interface
import ipdb; ipdb.set_trace()
```

**Debug specific modules**:
```bash
# Test API handler
python3 -c "
from src.api_handler import VastApiHandler
handler = VastApiHandler('192.168.1.100', 'admin', 'password')
print(handler.authenticate())
"

# Test data extractor
python3 -c "
from src.data_extractor import VastDataExtractor
extractor = VastDataExtractor()
print('Data extractor initialized')
"

# Test report builder
python3 -c "
from src.report_builder import VastReportBuilder
builder = VastReportBuilder()
print('Report builder initialized')
"
```

### Network Debugging

**Capture network traffic**:
```bash
# Capture HTTPS traffic (requires sudo)
sudo tcpdump -i any -w vast-reporter.pcap host 192.168.1.100 and port 443

# Analyze with Wireshark
wireshark vast-reporter.pcap
```

**Test with different tools**:
```bash
# Test with wget
wget --no-check-certificate https://192.168.1.100/api/versions

# Test with openssl
openssl s_client -connect 192.168.1.100:443 -servername 192.168.1.100
```

### System Resource Monitoring

**Monitor system resources**:
```bash
# Monitor CPU and memory
htop

# Monitor disk I/O
iotop

# Monitor network
nethogs

# Monitor specific process
top -p $(pgrep -f vast-reporter)
```

---

**Last Updated**: September 27, 2025
**Version**: 1.0.0-dev
**Compatibility**: VAST 5.3+, Python 3.8+
