# VAST API Reference — As-Built Report Generator

This document is the definitive API reference for the VAST As-Built Report Generator.
It catalogs every REST API endpoint the application uses, the authentication flow,
response fields depended on, version compatibility, and fallback behavior.

**Source of truth:** `src/api_handler.py`
**Last updated:** 2026-03-03
**Target:** VAST REST API v7 (cluster 5.3+), with v1 fallbacks

---

## Table of Contents

1. [Base URL and Versioning](#1-base-url-and-versioning)
2. [Authentication](#2-authentication)
3. [Version Detection](#3-version-detection)
4. [Retry and Backoff](#4-retry-and-backoff)
5. [Cluster Endpoints](#5-cluster-endpoints)
6. [Hardware Endpoints](#6-hardware-endpoints)
7. [Network Endpoints](#7-network-endpoints)
8. [Logical Configuration Endpoints](#8-logical-configuration-endpoints)
9. [Security Endpoints](#9-security-endpoints)
10. [Data Protection Endpoints](#10-data-protection-endpoints)
11. [Monitoring Endpoints](#11-monitoring-endpoints)
12. [Switch Endpoints (v1 only)](#12-switch-endpoints-v1-only)
13. [Rack Endpoints](#13-rack-endpoints)
14. [Data Collection Sequence](#14-data-collection-sequence)
15. [Field Reference by Section](#15-field-reference-by-section)
16. [Live Swagger Access](#16-live-swagger-access)

---

## 1. Base URL and Versioning

```
https://<cluster-management-vip>/api/<version>/
```

The application probes for the highest supported API version during connection.
Version probe order: `v7` → `v6` → `v5` → `v4` → `v3` → `v2` → `v1`.
First version returning HTTP 200 on `GET /api/<version>/vms/` is used.

| Version | Cluster Version | Notes |
| --- | --- | --- |
| v7 | 5.3+ | Full feature support including rack heights and PSNT |
| v1 | All | Fallback; required for switch/port endpoints |

---

## 2. Authentication

Authentication is attempted in strict priority order. The first method that succeeds is used for the session.

### Priority 1: Provided API Token

```
GET /api/<version>/vms/
Header: Authorization: Api-Token <token>
```

Token provided via CLI `--token` flag or `VAST_API_TOKEN` environment variable.

### Priority 2: Existing Tokens on Cluster

```
GET /api/<version>/apitokens/
Auth: Basic (username:password)
```

Lists all tokens. Iterates non-revoked tokens (newest first), testing each:

```
GET /api/<version>/vms/
Header: Authorization: Api-Token <token_value>
```

### Priority 3: Basic Authentication

```
GET /api/<version>/vms/
Auth: Basic (username:password)
```

### Priority 4: Create New Token

Only attempted if basic auth succeeds and fewer than 5 active tokens exist.

```
POST /api/<version>/apitokens/
Auth: Basic (username:password)
Body: {"name": "<generated>", "expiry_date": "30D", "owner": "<username>"}
```

Returns 201 with token in response body. Respects the 5-token limit.

### Session Behavior

- Token-based auth sets `Authorization` header on the session
- Basic auth sets `session.auth = (username, password)`
- Tokens are stored in memory only; never persisted to disk
- Credentials are never logged (enforced by `SensitiveDataFilter`)

---

## 3. Version Detection

**Function:** `_detect_api_version()`

Probes `GET /api/<version>/vms/` for versions v7 through v1 using basic auth.
Runs before token-based auth is established. Falls back to v1 if all probes fail.

After version is detected, capability detection runs:

```
GET /api/<version>/clusters/
```

Checks for enhanced features:
- `rack_height_supported` — `index_in_rack` field present on cboxes/dboxes
- `psnt_supported` — `psnt` field present on cluster

---

## 4. Retry and Backoff

Configured via `config/config.yaml` under `api:`:

| Setting | Default | Description |
| --- | --- | --- |
| `timeout` | 30 | Request timeout in seconds |
| `max_retries` | 3 | Maximum retry attempts |
| `retry_delay` | 2 | Backoff factor (exponential) |
| `verify_ssl` | false | SSL certificate verification |

Retry triggers on HTTP status: `429`, `500`, `502`, `503`, `504`.

On HTTP 401, the handler re-authenticates and retries once.

---

## 5. Cluster Endpoints

### GET /api/\<version\>/clusters/

**Function:** `get_cluster_info()`
**Fallback:** `GET /api/<version>/vms/` if clusters/ returns error

Key response fields consumed by the application:

| Field | Description |
| --- | --- |
| `name` | Cluster name |
| `guid` | Cluster GUID |
| `sw_version` / `version` | Software version |
| `state` | Cluster state |
| `license` | License type |
| `psnt` | Product Serial Number Tracking (v7, 5.3+) |
| `ebox` | Whether cluster has EBoxes (v7) |
| `build` | Build identifier |
| `uptime` | Cluster uptime |
| `mgmt_vip` | Management VIP |
| `ssd_raid_state` | SSD RAID health |
| `leader_cnode` | Current leader CNode |
| `usable_capacity_tb` | Usable capacity |
| `physical_space_*` | Physical space metrics |
| `logical_space_*` | Logical space metrics |
| `enable_encryption` | Encryption state |
| `enable_similarity` | Similarity/dedup state |
| `management_vips` | Management VIP list |
| `dns`, `ntp` | Cluster DNS/NTP |
| `ext_netmask`, `eth_mtu`, `ib_mtu` | Network parameters |

---

## 6. Hardware Endpoints

### GET /api/\<version\>/cnodes/

**Function:** `get_cnode_details()`

| Field | Description |
| --- | --- |
| `id`, `name`, `hostname` | Identity |
| `sn` / `serial_number` | Serial number |
| `box_vendor` | Hardware vendor |
| `state` | Node state |
| `ip`, `ip1`, `ip2` | Data IPs |
| `mgmt_ip`, `ipmi_ip` | Management IPs |
| `cores` | CPU cores |
| `cbox_id` / `box_id` | Parent CBox reference |
| `ebox_id` | Parent EBox reference (when cluster has EBoxes) |
| `bios_version`, `os_version`, `build` | Software versions |
| `index_in_rack` | Rack position (v7, 5.3+) |

### GET /api/\<version\>/dnodes/

**Function:** `get_dnode_details()`

| Field | Description |
| --- | --- |
| `id`, `name`, `hostname` | Identity |
| `sn` / `serial_number` | Serial number |
| `state` | Node state |
| `ip`, `ip1`, `ip2` | Data IPs |
| `mgmt_ip`, `ipmi_ip` | Management IPs |
| `dbox_id` / `box` | Parent DBox reference |
| `ebox_id` | Parent EBox reference (when cluster has EBoxes) |
| `bios_version`, `os_version`, `build` | Software versions |
| `index_in_rack` | Rack position (v7, 5.3+) |

### GET /api/\<version\>/cboxes/

**Function:** `get_cbox_details()`

Fields: `id`, `name`, `serial_number`, `model`, `state`, `rack_unit`, `index_in_rack`, `box_vendor`, `nodes`

### GET /api/\<version\>/dboxes/

**Function:** `get_dbox_details()`

Fields: `id`, `name`, `serial_number`, `model`, `state`, `hardware_type`, `rack_unit`, `index_in_rack`, `nodes`

### GET /api/\<version\>/eboxes/

**Function:** `get_ebox_details()`

Returns EBox (enclosure) inventory when the cluster has EBoxes. May return 404 or empty when the cluster does not use EBoxes. Same pattern as cboxes/dboxes: list of objects keyed by name in the app.

Fields (typical): `id`, `name`, `guid`, `uid`, `state`, `cluster`, `cluster_id`, `description`, `subsystem`, `index_in_rack`, `rack_id`, `rack_unit`, `rack_name`

**Cluster flag:** `GET /api/<version>/clusters/` includes `ebox` (boolean) indicating whether the cluster has EBoxes. CNodes and DNodes can include `ebox_id` linking to an EBox.

### GET /api/\<version\>/dtrays/

**Function:** `get_dtray_details()` (called internally by `get_dnode_details()`)

Provides additional DNode-to-DTray mapping for certain hardware configurations.

---

## 7. Network Endpoints

### GET /api/\<version\>/dns/

**Function:** `get_network_configuration()`

DNS server configuration and search domains.

### GET /api/\<version\>/ntps/

**Function:** `get_network_configuration()`

NTP server configuration.

### GET /api/\<version\>/vippools/

**Function:** `get_network_configuration()`

Virtual IP pool configuration including VIPs, gateways, and subnets.

### GET /api/\<version\>/vms/1/network\_settings/

**Functions:** `get_cluster_network_configuration()`, `get_cnodes_network_configuration()`, `get_dnodes_network_configuration()`

Rich network settings per-host including:
- `boxes[].hosts[].vast_install_info.net_type`
- Management VIPs, gateways, MTU settings
- Per-node: hostname, mgmt_ip, ipmi_ip, box_vendor, OS, TPM info

The `boxes` array is filtered by `box_name` prefix (`cbox-` or `dbox-`) to separate CNode and DNode network data.

---

## 8. Logical Configuration Endpoints

### GET /api/\<version\>/tenants/

**Function:** `get_logical_configuration()`

Tenant list with names, IDs, states.

### GET /api/\<version\>/views/

**Function:** `get_logical_configuration()`

View (export) list with paths, protocols, states.

### GET /api/\<version\>/viewpolicies/

**Function:** `get_logical_configuration()`

View policy list with types and states.

---

## 9. Security Endpoints

### GET /api/\<version\>/activedirectory/

**Function:** `get_security_configuration()`

Active Directory integration status, domain, servers.

### GET /api/\<version\>/ldap/

**Function:** `get_security_configuration()`

LDAP integration status and configuration.

### GET /api/\<version\>/nis/

**Function:** `get_security_configuration()`

NIS integration status and configuration.

---

## 10. Data Protection Endpoints

### GET /api/\<version\>/snapprograms/

**Function:** `get_data_protection_configuration()`

Snapshot schedule programs.

### GET /api/\<version\>/protectionpolicies/

**Function:** `get_data_protection_configuration()`

Data protection/retention policies.

---

## 11. Monitoring Endpoints

### GET /api/\<version\>/snmp/

**Function:** `get_monitoring_configuration()`

SNMP configuration.

### GET /api/\<version\>/syslog/

**Function:** `get_monitoring_configuration()`

Syslog forwarding configuration.

### GET /api/\<version\>/alerts/

**Function:** `get_monitoring_configuration()`

Alert configuration and active alerts.

---

## 12. Switch Endpoints (v1 only)

These endpoints always use the v1 API regardless of detected version.

### GET /api/v1/switches/

**Function:** `get_switches_detail()`

| Field | Description |
| --- | --- |
| `hostname` | Switch hostname |
| `sn` | Serial number |
| `model` | Hardware model |
| `fw_version` | Firmware version |
| `mgmt_ip` | Management IP |
| `state` | Switch state |
| `switch_type` | Switch type (Cumulus/Onyx) |
| `role` | Switch role |

### GET /api/v1/ports/

**Function:** `get_switch_ports()`

| Field | Description |
| --- | --- |
| `switch` | Parent switch reference |
| `name` | Port name (e.g., swp1) |
| `state` | Port state |
| `speed` | Port speed |
| `mtu` | Port MTU |

---

## 13. Rack Endpoints

### GET /api/\<version\>/racks/

**Function:** `get_racks()`

Returns rack inventory. Available on clusters that support multi-rack configurations.
Returns empty list if endpoint is unavailable.

---

## 14. Data Collection Sequence

`get_all_data()` collects data in this order:

```
 1. get_cluster_info()                → cluster_info
 2. get_racks()                       → racks
 3. get_cnode_details()               → hardware.cnodes
    └─ get_cbox_details()             → hardware.cboxes
 4. get_dnode_details()               → hardware.dnodes
    ├─ get_dtray_details()
    └─ get_dbox_details()             → hardware.dboxes
 5. get_ebox_details()                → hardware.eboxes (optional; 404 when no EBoxes)
 6. get_network_configuration()       → network (dns, ntp, vippools)
 7. get_cluster_network_configuration()  → cluster_network
 8. get_cnodes_network_configuration()   → cnodes_network
 9. get_dnodes_network_configuration()   → dnodes_network
10. get_logical_configuration()       → logical (tenants, views, policies)
11. get_security_configuration()      → security (AD, LDAP, NIS)
12. get_data_protection_configuration() → data_protection (snaps, policies)
13. get_performance_metrics()         → performance_metrics
14. get_licensing_info()              → licensing_info
15. get_monitoring_configuration()    → monitoring_config (SNMP, syslog, alerts)
16. get_customer_integration_info()   → customer_integration
17. get_deployment_timeline()         → deployment_timeline
18. get_future_recommendations()      → future_recommendations
19. get_switches_detail()             → switch_inventory
20. get_switch_ports()                → switch_ports
```

Each step is independent and uses graceful degradation — a failure in one endpoint
does not prevent collection of data from other endpoints.

---

## 15. Field Reference by Section

### Enhanced Features (v7, cluster 5.3+)

| Feature | Endpoint | Field | Fallback |
| --- | --- | --- | --- |
| Rack height | `cboxes/`, `dboxes/` | `index_in_rack` | `rack_unit` string (e.g., "U23") |
| Cluster PSNT | `clusters/` | `psnt` | Not available on older versions |
| EBoxes | `clusters/` | `ebox` | `eboxes/` may 404 when cluster has no EBoxes |

### Data Not Available via API

These data points require manual input or external tools (SSH port mapping):

- Bill of Materials part numbers
- Switch roles (Master/Slave) and tiers (Leaf/Spine)
- Cable types (direct/splitter)
- Use cases (AI, ML, HPC)
- Node-to-switch connectivity map (available via SSH port mapping module)
- Switch configuration export (available via SSH)

---

## 16. Live Swagger Access

Every VAST cluster exposes interactive API documentation:

| Method | URL |
| --- | --- |
| Swagger UI | `https://<management-vip>/api` |
| Docs index | `https://<management-vip>/docs/index.html` |

Login with administrator credentials (same as Web UI).
Supports field filtering on most endpoints: `?fields=id,name,hostname,ip`.

### Exporting Swagger Spec

Use `scripts/export_swagger.py` to capture the OpenAPI/Swagger JSON from a live cluster:

```bash
python scripts/export_swagger.py --cluster <CLUSTER_IP> --username admin --output docs/api/
```

This creates a versioned snapshot of the full API schema for offline reference.
