# VAST As-Built Report Generator - Complete API Reference

## Overview

This document provides a comprehensive reference for all API calls used by the VAST As-Built Report Generator. The tool automatically detects the highest supported API version for each cluster, preferring v7 for enhanced features, with graceful fallback to older versions as needed.

**Total API Endpoints:** 17
**Authentication Methods:** Basic Auth (primary), API Tokens (fallback)
**API Version:** Auto-detected (v7 preferred, falls back to v6, v5, v4, v3, v2, v1)
**Target Cluster Version:** 5.3+ (with enhanced features)

---

## API Version Detection

The VAST As-Built Report Generator automatically detects the highest supported API version for each cluster:

### Version Detection Process
1. **Test API Versions**: Tests versions in order: v7 → v6 → v5 → v4 → v3 → v2 → v1
2. **Use Highest Supported**: Selects the newest version that returns HTTP 200
3. **Fallback to v1**: If no version works, falls back to v1 as last resort
4. **Log Detection Results**: Logs which API version is being used

### Enhanced Features by Version
- **v7**: Full enhanced features (rack positioning, PSNT) for cluster 5.3+
- **v6**: Limited enhanced features for cluster 5.2+
- **v5**: Basic enhanced features for cluster 5.1+
- **v4 and below**: Standard features only

### Example Detection Log
```
2025-09-27 22:58:24 - api_handler - INFO - Detecting highest supported API version...
2025-09-27 22:58:24 - api_handler - DEBUG - Testing API version v7 with URL: https://10.143.11.204/api/v7/vms/
2025-09-27 22:58:24 - api_handler - DEBUG - API version v7 not supported: 404
2025-09-27 22:58:24 - api_handler - DEBUG - Testing API version v6 with URL: https://10.143.11.204/api/v6/vms/
2025-09-27 22:58:24 - api_handler - DEBUG - API version v6 not supported: 404
2025-09-27 22:58:24 - api_handler - DEBUG - Testing API version v1 with URL: https://10.143.11.204/api/v1/vms/
2025-09-27 22:58:24 - api_handler - INFO - Successfully detected API version: v1
2025-09-27 22:58:24 - api_handler - INFO - Using API version: v1
```

---

## Authentication APIs

### 1. Basic Authentication Test
**Endpoint:** `GET /api/v1/vms/`
**Purpose:** Test basic authentication credentials and retrieve cluster information
**Method:** GET
**Authentication:** Basic Auth (username:password)

**Information Gathered:**
- Cluster name, GUID, version, state
- License information
- Management IP addresses
- SSL certificate details
- Cluster capabilities and features
- Capacity information
- Performance settings

**Actual Response:**
```json
[{
  "id": 1,
  "guid": "9af9009f-e0ae-4897-814e-2cdac2b1d6aa",
  "name": "VMS",
  "url": "https://10.143.11.204/api/v1/vms/1",
  "title": "VMS",
  "created": "2025-08-07T18:17:54.088986Z",
  "auto_logout_timeout": 600,
  "state": "CLUSTERED",
  "sw_version": "5.3.1.1.10603406698381149702",
  "build": "release-5.3.1-sp3-1898015-vms",
  "ip1": "172.16.1.12",
  "ip2": "172.16.2.12",
  "mgmt_ip": "UNKNOWN",
  "mgmt_vip": "10.143.11.204",
  "mgmt_vip_ipv6": "UNKNOWN",
  "mgmt_cnode": "cnode-3-12",
  "mgmt_inner_vip_cnode": "cnode-3-11",
  "disable_vms_metrics": false,
  "disable_mgmt_ha": false,
  "min_pwd_length": 8,
  "performance_base_10": true,
  "capacity_base_10": false,
  "ssl_port": 443,
  "ssl_certificate": "***",
  "ssl_keyfile": "***",
  "ssl_certificate_info": {
    "subject": [["commonName", "*.selab.vastdata.com"]],
    "issuer": [["countryName", "GB"], ["organizationName", "Sectigo Limited"], ["commonName", "Sectigo Public Server Authentication CA DV R36"]],
    "version": 3,
    "serialNumber": "1D09D91E317403B9975B78E5FC0C83AF",
    "notBefore": "Aug 12 00:00:00 2025 GMT",
    "notAfter": "Sep 2 23:59:59 2026 GMT",
    "subjectAltName": [["DNS", "*.selab.vastdata.com"], ["DNS", "selab.vastdata.com"]],
    "OCSP": ["http://ocsp.sectigo.com"],
    "caIssuers": ["http://crt.sectigo.com/SectigoPublicServerAuthenticationCADVR36.crt"]
  },
  "min_tls_version": "1.2",
  "capacity_usable": true,
  "degraded_reason": "NA",
  "access_token_lifetime": "01:00:00",
  "refresh_token_lifetime": "1 00:00:00",
  "login_banner": null,
  "total_usage_capacity_percentage": 0.0,
  "total_active_capacity": 0.0,
  "total_remaining_capacity": 0.0,
  "ipv6_support": true,
  "vms_perf_debug_metrics_enabled": true,
  "ssl_client_certificate": null,
  "ssl_client_keyfile": null,
  "ssl_client_certificate_info": null,
  "maintenance_mode": false,
  "min_qos_supported": false,
  "max_api_tokens_per_user": 5
}]
```

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/vms/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 2. API Token Creation
**Endpoint:** `POST /api/v1/apitokens/`
**Purpose:** Create API tokens for authentication (when basic auth fails or for token-based auth)
**Method:** POST
**Authentication:** Basic Auth (username:password)

**Information Gathered:**
- API token ID and secret
- Token expiration date
- Token owner information

**Expected Response:**
```json
{
  "id": "PILpmpLs",
  "token": "PILpmpLs.SyIMdS1Z67NxEmCXDYU0l09sRdakLZs3",
  "name": "VAST-As-Built-Report-1695852345",
  "expiry_date": "2025-10-28T04:25:38.624192Z",
  "owner": "admin",
  "created": "2025-09-28T04:25:38.625397Z",
  "revoked": false
}
```

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/apitokens/ \
  -X POST \
  -u admin:123456 \
  -H "Content-Type: application/json" \
  -d '{
    "name": "VAST-As-Built-Report-Test",
    "expiry_date": "30D",
    "owner": "admin"
  }'
```

---

### 3. List Existing API Tokens
**Endpoint:** `GET /api/v1/apitokens/`
**Purpose:** Retrieve list of existing API tokens for the user
**Method:** GET
**Authentication:** Basic Auth (username:password)

**Information Gathered:**
- All API tokens for the user
- Token status (active/revoked)
- Creation and expiration dates
- Last used timestamps

**Actual Response:**
```json
[{
  "id": "PILpmpLs",
  "created": "2025-09-28T04:25:38.625397Z",
  "name": "VAST-As-Built-Report-Test",
  "revoked": false,
  "expiry_date": "2025-10-28T04:25:38.624192Z",
  "revocation_time": null,
  "owner": "admin",
  "last_used": "2025-09-28T05:51:44.954874Z"
}]
```

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/apitokens/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

## Data Collection APIs

### 4. Cluster Information
**Endpoint:** `GET /api/v1/vms/`
**Purpose:** Get comprehensive cluster information and capabilities
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- Cluster name, GUID, version, state
- License information
- Management IP addresses
- SSL certificate details
- Cluster capabilities and features
- Capacity information
- Performance settings

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/vms/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 5. CNode Details
**Endpoint:** `GET /api/v1/cnodes/`
**Purpose:** Get Control Node hardware information and status
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- CNode ID, model, serial number
- Node state and status
- Rack position (if supported in v5.3+)
- Hardware specifications
- Network configuration

**Actual Response:**
```json
[{
  "id": 6,
  "state": "ACTIVE",
  "model": "Unknown",
  "serial_number": "Unknown"
}, {
  "id": 2,
  "state": "ACTIVE",
  "model": "Unknown",
  "serial_number": "Unknown"
}, {
  "id": 3,
  "state": "ACTIVE",
  "model": "Unknown",
  "serial_number": "Unknown"
}]
```

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/cnodes/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 6. DNode Details
**Endpoint:** `GET /api/v1/dnodes/`
**Purpose:** Get Data Node hardware information and status
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- DNode ID, model, serial number
- Node state and status
- Rack position (if supported in v5.3+)
- Hardware specifications
- Storage capacity

**Actual Response:**
```json
[{
  "id": 1,
  "state": "ACTIVE",
  "model": "Unknown",
  "serial_number": "Unknown"
}, {
  "id": 2,
  "state": "ACTIVE",
  "model": "Unknown",
  "serial_number": "Unknown"
}]
```

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/dnodes/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

## Network Configuration APIs

### 7. DNS Configuration
**Endpoint:** `GET /api/v1/dns/`
**Purpose:** Get DNS server configuration
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- DNS server addresses
- DNS search domains
- DNS configuration status

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/dns/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 8. NTP Configuration
**Endpoint:** `GET /api/v1/ntps/`
**Purpose:** Get NTP server configuration
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- NTP server addresses
- NTP synchronization status
- Time zone settings

**Status:** `404 Not Found` (Not available in this cluster)

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/ntps/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 9. VIP Pool Configuration
**Endpoint:** `GET /api/v1/vippools/`
**Purpose:** Get Virtual IP pool configuration
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- VIP pool definitions
- IP address ranges
- Pool assignments and status

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/vippools/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

## Logical Configuration APIs

### 10. Tenants Configuration
**Endpoint:** `GET /api/v1/tenants/`
**Purpose:** Get tenant configuration and settings
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- Tenant names and IDs
- Tenant quotas and limits
- Tenant status and configuration

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/tenants/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 11. Views Configuration
**Endpoint:** `GET /api/v1/views/`
**Purpose:** Get view configuration and settings
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- View names and paths
- View permissions and access controls
- View status and configuration

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/views/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 12. View Policies Configuration
**Endpoint:** `GET /api/v1/viewpolicies/`
**Purpose:** Get view policy configuration
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- Policy names and rules
- Policy assignments
- Policy status and configuration

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/viewpolicies/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

## Security Configuration APIs

### 13. Active Directory Configuration
**Endpoint:** `GET /api/v1/activedirectory/`
**Purpose:** Get Active Directory integration settings
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- AD server configuration
- Domain settings
- Authentication status

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/activedirectory/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 14. LDAP Configuration
**Endpoint:** `GET /api/v1/ldap/`
**Purpose:** Get LDAP integration settings
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- LDAP server configuration
- LDAP search base and filters
- Authentication settings

**Status:** `404 Not Found` (Not available in this cluster)

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/ldap/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 15. NIS Configuration
**Endpoint:** `GET /api/v1/nis/`
**Purpose:** Get NIS integration settings
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- NIS server configuration
- NIS domain settings
- Authentication status

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/nis/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

## Data Protection APIs

### 16. Snapshot Programs Configuration
**Endpoint:** `GET /api/v1/snapprograms/`
**Purpose:** Get snapshot program configuration
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- Snapshot program definitions
- Schedule settings
- Retention policies

**Status:** `404 Not Found` (Not available in this cluster)

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/snapprograms/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

### 17. Protection Policies Configuration
**Endpoint:** `GET /api/v1/protectionpolicies/`
**Purpose:** Get data protection policy configuration
**Method:** GET
**Authentication:** Basic Auth or API Token

**Information Gathered:**
- Protection policy definitions
- Replication settings
- Backup configurations

**Curl Command:**
```bash
curl -k https://10.143.11.204/api/v1/protectionpolicies/ \
  -u admin:123456 \
  -H "Content-Type: application/json"
```

---

## API Summary

### Endpoint Categories
- **Authentication:** 3 APIs
- **Hardware:** 3 APIs (Cluster, CNodes, DNodes)
- **Network:** 3 APIs (DNS, NTP, VIP Pools)
- **Logical:** 3 APIs (Tenants, Views, View Policies)
- **Security:** 3 APIs (AD, LDAP, NIS)
- **Data Protection:** 2 APIs (Snapshots, Protection Policies)

### Response Status
- ✅ **Working:** 13 APIs
- ❌ **Not Available:** 4 APIs (NTP, LDAP, Snapshot Programs, some enhanced features)

### Enhanced Features (v5.3+)
- Rack positioning data (`index_in_rack` field)
- Cluster PSNT (Product Serial Number Tracking)
- Advanced hardware specifications

### Authentication Methods
1. **Basic Authentication** (Primary)
   - Uses username:password in Authorization header
   - Tested with `admin:123456` credentials

2. **API Token Authentication** (Fallback)
   - Creates API tokens when basic auth fails
   - Uses `Authorization: Api-Token <token>` header
   - Handles token limit scenarios gracefully

### Common Parameters
- **Base URL:** `https://<cluster_ip>/api/v1/`
- **SSL Verification:** Disabled (`--insecure` flag)
- **Content-Type:** `application/json`
- **User-Agent:** `VAST-As-Built-Report-Generator/1.0`

### Error Handling
- **401 Unauthorized:** Automatic re-authentication
- **404 Not Found:** Graceful degradation (endpoint not available)
- **503 Service Unavailable:** Token limit reached (fallback to basic auth)
- **Retry Logic:** Exponential backoff for transient failures

---

## Usage Notes

1. **SSL Certificates:** All curl commands use the `--insecure` flag to handle self-signed certificates
2. **Credentials:** Replace `admin:123456` with actual cluster credentials
3. **Cluster IP:** Replace `10.143.11.204` with actual cluster management IP
4. **API Version:** This reference is for API v1 (not v7)
5. **Enhanced Features:** Rack positioning and PSNT require cluster version 5.3+

---

*Generated by VAST As-Built Report Generator v1.0*
*Last Updated: September 27, 2025*
