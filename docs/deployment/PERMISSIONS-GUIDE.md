# VAST As-Built Report Generator - Permissions Guide

## Overview

The VAST As-Built Report Generator requires **elevated read permissions** to access all necessary API endpoints for comprehensive report generation. This guide explains the permission requirements and provides troubleshooting steps.

---

## Required Username

### Support User Account

**Required**: `support` username or equivalent account with full read permissions

**Why**: The report generator accesses multiple API endpoints that require elevated privileges:
- Hardware inventory (CBoxes, DBoxes, CNodes, DNodes)
- Network configuration and settings
- Cluster configuration and status
- Storage capacity and metrics
- Security settings and policies
- Tenant and view configurations

**Standard user accounts** typically have restricted API access and will result in incomplete reports or permission errors.

---

## Permission Requirements

### API Endpoints Accessed

The report generator requires read access to the following endpoints:

#### Core Cluster Information
- `GET /api/v7/clusters/` - Cluster configuration and status
- `GET /api/v7/vms/` - VMS information (legacy fallback)

#### Hardware Inventory
- `GET /api/v7/cnodes/` - Compute node details
- `GET /api/v7/dnodes/` - Data node details
- `GET /api/v1/cboxes/` - CBox hardware information
- `GET /api/v7/dboxes/` - DBox hardware information
- `GET /api/v7/dtrays/` - Storage tray details

#### Network Configuration
- `GET /api/v7/vms/1/network_settings/` - Network settings for all nodes
- `GET /api/v7/dns/` - DNS configuration
- `GET /api/v7/ntps/` - NTP configuration
- `GET /api/v7/vippools/` - VIP pool configuration

#### Logical Configuration
- `GET /api/v7/tenants/` - Tenant information
- `GET /api/v7/views/` - View configuration
- `GET /api/v7/viewpolicies/` - View policies
- `GET /api/v7/protectionpolicies/` - Protection policies

#### Security & Authentication
- `GET /api/v7/activedirectory/` - Active Directory integration
- `GET /api/v7/ldap/` - LDAP configuration
- `GET /api/v7/nis/` - NIS configuration

### RBAC Requirements

**Minimum Role**: Viewer role with comprehensive read permissions

**Recommended**: `support` user account (built-in elevated account)

---

## Common Permission Errors

### Error 1: 403 Forbidden

**Symptoms**:
```
ERROR: API request failed: 403 Forbidden
ERROR: Access denied to endpoint /api/v7/cnodes/
```

**Cause**: User account lacks permission to access the requested API endpoint

**Solution**:
```bash
# Use the support username
python3 -m src.main --cluster-ip <CLUSTER_IP> --username support --password <PASSWORD> --output-dir reports
```

### Error 2: Incomplete Report Data

**Symptoms**:
```
WARNING: Unable to retrieve hardware information
WARNING: Network configuration incomplete
WARNING: Missing storage capacity data
```

**Cause**: User account has partial permissions but not comprehensive read access

**Solution**: Switch to `support` user or ensure your account has Viewer role with all read permissions enabled

### Error 3: API Version Not Supported

**Symptoms**:
```
ERROR: API v7 not available
INFO: Falling back to API v1
WARNING: Some features unavailable with API v1
```

**Cause**: May occur with restricted accounts that don't have v7 API access

**Solution**: Use `support` user which has access to all API versions

---

## Verifying Permissions

### Test API Access

You can manually test API access using curl:

```bash
# Test with your credentials
curl -u <USERNAME>:<PASSWORD> -k https://<CLUSTER_IP>/api/v7/clusters/ | jq

# Test with support user
curl -u support:<PASSWORD> -k https://<CLUSTER_IP>/api/v7/clusters/ | jq
```

**Expected Result**: JSON response with cluster data

**Permission Error**: HTTP 403 or 401 response

### Check User Permissions in VAST GUI

1. Log in to VAST GUI as administrator
2. Navigate to **Settings** → **Users**
3. Find your user account
4. Verify **Role** is set to "Viewer" or higher
5. Ensure **API Access** is enabled

### Test Report Generation

Run a test report to verify permissions:

```bash
python3 -m src.main \
  --cluster-ip <CLUSTER_IP> \
  --username support \
  --password <PASSWORD> \
  --output-dir reports \
  --verbose
```

Check the logs for any permission errors:
```bash
grep -i "403\|forbidden\|denied\|permission" logs/vast_report_generator.log
```

---

## Alternative Solutions

### Option 1: Request Elevated Permissions

Contact your VAST administrator to:
1. Grant Viewer role to your user account
2. Enable comprehensive read permissions
3. Ensure API access is enabled

### Option 2: Use Support Account

**Recommended for PS Engineers**:
```bash
# The support account has all necessary permissions
python3 -m src.main \
  --cluster-ip <CLUSTER_IP> \
  --username support \
  --password <PASSWORD> \
  --output-dir reports
```

### Option 3: Create Service Account

For automated reporting, create a dedicated service account:

1. **Create User**: Create a new user account in VAST GUI
2. **Assign Role**: Set role to "Viewer" or "Administrator" (read-only)
3. **Enable API**: Ensure API access is enabled
4. **Test Access**: Verify all required endpoints are accessible
5. **Use in Automation**: Use this account for scheduled reports

---

## Security Considerations

### Read-Only Access

The report generator **only requires read access** - it never modifies cluster configuration:
- ✅ Safe to use on production clusters
- ✅ No risk of accidental configuration changes
- ✅ All API calls are GET requests
- ✅ No write operations performed

### Credential Security

**Best Practices**:
1. **Use interactive prompts** for manual report generation
2. **Use environment variables** for automation
3. **Never commit credentials** to version control
4. **Rotate credentials** regularly
5. **Use dedicated service account** for automation

**Example (Interactive - Most Secure)**:
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --output-dir reports
# Will prompt for username and password
# Enter 'support' for username when prompted
```

**Example (Environment Variables)**:
```bash
export VAST_CLUSTER_IP=<CLUSTER_IP>
export VAST_USERNAME=support
export VAST_PASSWORD=<PASSWORD>

python3 -m src.main \
  --cluster-ip $VAST_CLUSTER_IP \
  --username $VAST_USERNAME \
  --password $VAST_PASSWORD \
  --output-dir reports
```

---

## Troubleshooting Permission Issues

### Step 1: Verify Connectivity

```bash
# Test basic connectivity
ping <CLUSTER_IP>

# Test HTTPS access
curl -k https://<CLUSTER_IP>/api/
```

### Step 2: Verify Credentials

```bash
# Test authentication
curl -u support:<PASSWORD> -k https://<CLUSTER_IP>/api/v7/clusters/
```

### Step 3: Check API Access

```bash
# Test specific endpoints
curl -u support:<PASSWORD> -k https://<CLUSTER_IP>/api/v7/cnodes/ | jq
curl -u support:<PASSWORD> -k https://<CLUSTER_IP>/api/v7/dnodes/ | jq
curl -u support:<PASSWORD> -k https://<CLUSTER_IP>/api/v1/cboxes/ | jq
```

### Step 4: Review Logs

```bash
# Run with verbose logging
python3 -m src.main \
  --cluster-ip <CLUSTER_IP> \
  --username support \
  --password <PASSWORD> \
  --output-dir reports \
  --verbose

# Check for permission errors
tail -f logs/vast_report_generator.log
grep -i "error\|warning\|403\|forbidden" logs/vast_report_generator.log
```

### Step 5: Contact Support

If issues persist:
1. Collect verbose logs
2. Note specific API endpoints failing
3. Verify VAST cluster version
4. Contact VAST support or your account team

---

## FAQ

### Q: Can I use a regular user account?

**A**: Not recommended. Regular user accounts typically have restricted API access and will result in incomplete reports or permission errors. Use the `support` account for best results.

### Q: What if I don't have the support password?

**A**: Contact your VAST administrator or account team to:
- Obtain the support password
- Create an elevated service account
- Grant your account comprehensive read permissions

### Q: Does the report generator modify the cluster?

**A**: No. The tool only performs read operations (GET requests). It never modifies cluster configuration.

### Q: Can I use API tokens instead of username/password?

**A**: Yes, if your cluster supports API token authentication:
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --token <YOUR_API_TOKEN> --output-dir reports
```

### Q: What permissions does "support" user have?

**A**: The support user has comprehensive read/write access to all cluster functions. The report generator only uses read operations.

### Q: Is it safe to use support account in production?

**A**: Yes, the report generator only performs read operations. However, for security best practices, consider creating a dedicated read-only service account.

---

## Summary

**Key Points**:
- ✅ Use `support` username for complete report generation
- ✅ Standard users may lack sufficient permissions
- ✅ Report generator only requires read access
- ✅ All API calls are GET requests (safe for production)
- ✅ Interactive prompts recommended for security
- ✅ Create service account for automation

**Quick Start**:
```bash
python3 -m src.main --cluster-ip <CLUSTER_IP> --output-dir reports
# When prompted:
# Username: support
# Password: <your_support_password>
```

---

**Last Updated**: October 18, 2025
**Version**: 1.0.0
**Applies To**: VAST Cluster 5.3+
