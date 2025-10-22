# VAST As-Built Report Generator - Deployment Guide

This guide provides comprehensive instructions for deploying the VAST As-Built Report Generator in various environments, from development to production.

## Table of Contents

1. [Quick Start Deployment](#quick-start-deployment)
2. [Production Deployment](#production-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Systemd Service Setup](#systemd-service-setup)
5. [Monitoring and Alerting](#monitoring-and-alerting)
6. [Security Hardening](#security-hardening)
7. [Backup and Recovery](#backup-and-recovery)
8. [Troubleshooting](#troubleshooting)

## Quick Start Deployment

### Prerequisites

- Python 3.8+ installed
- Network access to VAST Management Service
- Valid VAST cluster credentials

### Installation Steps

1. **Clone and Setup**
   ```bash
   git clone https://github.com/rstamps01/ps-deploy-report.git
   cd ps-deploy-report
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure**
   ```bash
   cp config/config.yaml.template config/config.yaml
   # Edit config/config.yaml as needed
   ```

3. **Test Installation**
   ```bash
   python3 src/main.py --version
   python3 src/main.py --help
   ```

4. **Generate First Report**
   ```bash
   python3 src/main.py --cluster 192.168.1.100 --output ./output
   ```

## Production Deployment

### System Requirements

- **OS**: Ubuntu 20.04+ LTS, CentOS 8+, RHEL 8+, or equivalent
- **CPU**: 2+ cores recommended
- **RAM**: 1GB minimum, 2GB+ recommended
- **Disk**: 10GB+ for logs and output files
- **Network**: HTTPS access to VAST clusters

### Installation Process

1. **Create System User**
   ```bash
   sudo useradd -m -s /bin/bash vast-asbuilt-reporter
   sudo mkdir -p /opt/vast-asbuilt-reporter
   sudo chown vast-asbuilt-reporter:vast-asbuilt-reporter /opt/vast-asbuilt-reporter
   ```

2. **Install Application**
   ```bash
   sudo -u vast-asbuilt-reporter git clone https://github.com/rstamps01/ps-deploy-report.git /opt/vast-asbuilt-reporter
   cd /opt/vast-asbuilt-reporter
   sudo -u vast-asbuilt-reporter python3 -m venv venv
   sudo -u vast-asbuilt-reporter ./venv/bin/pip install -r requirements.txt
   ```

3. **Install System Dependencies**
   ```bash
   # Ubuntu/Debian
   sudo apt-get update
   sudo apt-get install -y libpango1.0-dev libharfbuzz-dev libffi-dev libxml2-dev libxslt1-dev

   # CentOS/RHEL
   sudo yum install -y pango-devel harfbuzz-devel libffi-devel libxml2-devel libxslt-devel
   ```

4. **Configure Application**
   ```bash
   sudo -u vast-asbuilt-reporter cp config/config.yaml.template config/config.yaml
   sudo -u vast-asbuilt-reporter nano config/config.yaml
   ```

5. **Set Up Logging**
   ```bash
   sudo mkdir -p /var/log/vast-asbuilt-reporter
   sudo chown vast-asbuilt-reporter:vast-asbuilt-reporter /var/log/vast-asbuilt-reporter
   sudo cp config/logrotate.conf /etc/logrotate.d/vast-asbuilt-reporter
   ```

6. **Create Output Directory**
   ```bash
   sudo mkdir -p /var/opt/vast-asbuilt-reporter/output
   sudo chown vast-asbuilt-reporter:vast-asbuilt-reporter /var/opt/vast-asbuilt-reporter/output
   ```

## Docker Deployment

### Dockerfile

Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.12-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpango1.0-dev \
    libharfbuzz-dev \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -s /bin/bash vast-asbuilt-reporter && \
    chown -R vast-asbuilt-reporter:vast-asbuilt-reporter /app

USER vast-asbuilt-reporter

# Create directories
RUN mkdir -p logs output

# Set default command
CMD ["python3", "src/main.py", "--help"]
```

### Docker Compose

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  vast-asbuilt-reporter:
    build: .
    container_name: vast-asbuilt-reporter
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./output:/app/output
    environment:
      - VAST_USERNAME=${VAST_USERNAME}
      - VAST_PASSWORD=${VAST_PASSWORD}
    command: ["python3", "src/main.py", "--cluster", "192.168.1.100", "--output", "./output"]
    restart: unless-stopped
```

### Build and Run

```bash
# Build image
docker build -t vast-asbuilt-reporter .

# Run container
docker run -it --rm \
  -e VAST_USERNAME=admin \
  -e VAST_PASSWORD=password \
  -v $(pwd)/output:/app/output \
  vast-asbuilt-reporter \
  python3 src/main.py --cluster 192.168.1.100 --output ./output

# Or use docker-compose
docker-compose up -d
```

## Systemd Service Setup

### Service File

Create `/etc/systemd/system/vast-asbuilt-reporter.service`:

```ini
[Unit]
Description=VAST As-Built Report Generator
After=network.target

[Service]
Type=simple
User=vast-asbuilt-reporter
Group=vast-asbuilt-reporter
WorkingDirectory=/opt/vast-asbuilt-reporter
ExecStart=/opt/vast-asbuilt-reporter/venv/bin/python3 src/main.py --cluster 192.168.1.100 --output /var/opt/vast-asbuilt-reporter/output
Restart=on-failure
RestartSec=30
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/vast-asbuilt-reporter /var/opt/vast-asbuilt-reporter/output

[Install]
WantedBy=multi-user.target
```

### Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable vast-asbuilt-reporter
sudo systemctl start vast-asbuilt-reporter
sudo systemctl status vast-asbuilt-reporter
```

### Service Management

```bash
# Start service
sudo systemctl start vast-asbuilt-reporter

# Stop service
sudo systemctl stop vast-asbuilt-reporter

# Restart service
sudo systemctl restart vast-asbuilt-reporter

# View logs
sudo journalctl -u vast-asbuilt-reporter -f

# Check status
sudo systemctl status vast-asbuilt-reporter
```

## Monitoring and Alerting

### Log Monitoring

Set up log monitoring with tools like:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana + Loki**
- **Splunk**
- **CloudWatch** (AWS)

### Health Checks

Create a health check script `/opt/vast-asbuilt-reporter/health_check.sh`:

```bash
#!/bin/bash

# Check if service is running
if ! systemctl is-active --quiet vast-asbuilt-reporter; then
    echo "ERROR: vast-asbuilt-reporter service is not running"
    exit 1
fi

# Check if logs are being written
if [ ! -f /var/log/vast-asbuilt-reporter/vast_report_generator.log ]; then
    echo "ERROR: Log file not found"
    exit 1
fi

# Check if output directory is writable
if [ ! -w /var/opt/vast-asbuilt-reporter/output ]; then
    echo "ERROR: Output directory not writable"
    exit 1
fi

echo "OK: All checks passed"
exit 0
```

### Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
- name: vast-asbuilt-reporter
  rules:
  - alert: VastReporterDown
    expr: up{job="vast-asbuilt-reporter"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "VAST Reporter is down"
      description: "VAST Reporter has been down for more than 5 minutes"

  - alert: VastReporterHighErrorRate
    expr: rate(vast_reporter_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in VAST Reporter"
      description: "Error rate is {{ $value }} errors per second"
```

## Security Hardening

### File Permissions

```bash
# Set proper permissions
sudo chmod 755 /opt/vast-asbuilt-reporter
sudo chmod 644 /opt/vast-asbuilt-reporter/config/config.yaml
sudo chmod 755 /opt/vast-asbuilt-reporter/src/main.py
sudo chmod 700 /var/log/vast-asbuilt-reporter
sudo chmod 755 /var/opt/vast-asbuilt-reporter/output

# Set ownership
sudo chown -R vast-asbuilt-reporter:vast-asbuilt-reporter /opt/vast-asbuilt-reporter
sudo chown -R vast-asbuilt-reporter:vast-asbuilt-reporter /var/log/vast-asbuilt-reporter
sudo chown -R vast-asbuilt-reporter:vast-asbuilt-reporter /var/opt/vast-asbuilt-reporter
```

### Network Security

```bash
# Configure firewall (UFW example)
sudo ufw allow from 192.168.1.0/24 to any port 443
sudo ufw deny 22  # Disable SSH if not needed

# Configure iptables for more granular control
sudo iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 443 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 443 -j DROP
```

### Credential Management

```bash
# Use environment variables for credentials
export VAST_USERNAME=admin
export VAST_PASSWORD=$(cat /etc/vast-asbuilt-reporter/password.txt)

# Or use a secrets management system
# HashiCorp Vault, AWS Secrets Manager, etc.
```

### SSL/TLS Configuration

```bash
# For self-signed certificates
openssl req -x509 -newkey rsa:4096 -keyout vast-asbuilt-reporter.key -out vast-asbuilt-reporter.crt -days 365 -nodes

# Update configuration
api:
  verify_ssl: true
  ca_cert: /path/to/ca-certificate.crt
```

## Backup and Recovery

### Backup Script

Create `/opt/vast-asbuilt-reporter/backup.sh`:

```bash
#!/bin/bash

BACKUP_DIR="/backup/vast-asbuilt-reporter"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup configuration
cp -r /opt/vast-asbuilt-reporter/config $BACKUP_DIR/config_$DATE

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /var/log/vast-asbuilt-reporter/

# Backup output files
tar -czf $BACKUP_DIR/output_$DATE.tar.gz /var/opt/vast-asbuilt-reporter/output/

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR"
```

### Automated Backups

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/vast-asbuilt-reporter/backup.sh >> /var/log/vast-asbuilt-reporter/backup.log 2>&1
```

### Recovery Procedures

```bash
# Restore configuration
cp -r /backup/vast-asbuilt-reporter/config_20250927_020000/* /opt/vast-asbuilt-reporter/config/

# Restore logs
tar -xzf /backup/vast-asbuilt-reporter/logs_20250927_020000.tar.gz -C /

# Restore output files
tar -xzf /backup/vast-asbuilt-reporter/output_20250927_020000.tar.gz -C /
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   sudo chown -R vast-asbuilt-reporter:vast-asbuilt-reporter /opt/vast-asbuilt-reporter
   sudo chmod +x /opt/vast-asbuilt-reporter/src/main.py
   ```

2. **Module Not Found**
   ```bash
   cd /opt/vast-asbuilt-reporter
   sudo -u vast-asbuilt-reporter ./venv/bin/pip install -r requirements.txt
   ```

3. **SSL Certificate Errors**
   ```bash
   # Update config.yaml
   api:
     verify_ssl: false
   ```

4. **Out of Memory**
   ```bash
   # Increase memory limits
   ulimit -v 2097152  # 2GB virtual memory
   ```

### Debug Mode

```bash
# Enable debug logging
python3 src/main.py --cluster 192.168.1.100 --output ./output --verbose

# Check system resources
top -p $(pgrep -f vast-asbuilt-reporter)

# Monitor network connections
netstat -tulpn | grep python3
```

### Log Analysis

```bash
# View recent errors
grep "ERROR" /var/log/vast-asbuilt-reporter/vast_report_generator.log | tail -20

# Monitor real-time logs
tail -f /var/log/vast-asbuilt-reporter/vast_report_generator.log

# Analyze log patterns
grep "Connection timeout" /var/log/vast-asbuilt-reporter/vast_report_generator.log | wc -l
```

## Performance Tuning

### Large Cluster Optimization

```yaml
# config/config.yaml
api:
  timeout: 120
  max_retries: 3
  concurrent_requests: 10

data_collection:
  concurrent_requests: 8
  validate_responses: true
  graceful_degradation: true
```

### Resource Limits

```bash
# Set memory limits
echo "vast-asbuilt-reporter soft memlock 2097152" >> /etc/security/limits.conf
echo "vast-asbuilt-reporter hard memlock 2097152" >> /etc/security/limits.conf

# Set CPU limits
echo "vast-asbuilt-reporter soft cpu 4" >> /etc/security/limits.conf
echo "vast-asbuilt-reporter hard cpu 4" >> /etc/security/limits.conf
```

## Maintenance

### Regular Maintenance Tasks

1. **Log Rotation**: Automated via logrotate
2. **Backup Verification**: Weekly backup integrity checks
3. **Security Updates**: Monthly dependency updates
4. **Performance Monitoring**: Weekly resource usage review
5. **Configuration Review**: Quarterly security configuration audit

### Update Procedures

```bash
# Update application
cd /opt/vast-asbuilt-reporter
sudo -u vast-asbuilt-reporter git pull origin main
sudo -u vast-asbuilt-reporter ./venv/bin/pip install -r requirements.txt
sudo systemctl restart vast-asbuilt-reporter
```

---

**Last Updated**: September 27, 2025
**Version**: 1.0.0-dev
**Compatibility**: VAST 5.3+, Python 3.8+
