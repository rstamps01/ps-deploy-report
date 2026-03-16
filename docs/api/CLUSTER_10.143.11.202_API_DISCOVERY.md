# API & Data Gathering Discovery — Cluster 10.143.11.202 (selab-var-202)

**Cluster:** 10.143.11.202  
**Resolved name:** selab-var-202  
**API version:** v7  
**Catalog source:** `docs/api/swagger_selab-var-202_v7_20260310.json` (export_swagger.py)  
**Generated:** 2026-03-10

This document lists **all data gathering options** available for this cluster and related infrastructure: REST API endpoints (with availability on this cluster) and non-API collection (SSH port mapping).

---

## 1. Summary

| Category | Available | Unavailable (404) | Used by app |
|----------|-----------|-------------------|-------------|
| **Cluster & hardware** | 8 | 0 | Yes |
| **Network (API)** | 4 | 1 (ntps) | Yes |
| **Logical (tenants/views)** | 3 | 0 | Yes |
| **Security** | 2 | 1 (ldap) | Yes |
| **Data protection** | 1 | 1 (snapprograms) | Yes |
| **Monitoring** | 0 | 3 (snmp, syslog, alerts) | Yes (optional) |
| **Racks & switches** | 3 | 0 | Yes |
| **Other (vms/1/network_settings)** | 1* | — | Yes |

\* Not probed by export script; used by app for cluster/cnode/dnode network settings.

**Total API endpoints used by app:** 23 (21 probed in catalog + 1 `vms/1/network_settings/` + v1 switches/ports).  
**Available on this cluster:** 21 returning 200; 6 return 404 (optional or not configured).  
**Non-API:** SSH-based port mapping (optional, when enabled).

---

## 2. REST API Endpoints — Full Matrix

### 2.1 Cluster & identity

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/clusters/` | 200 | 263 | Yes | Cluster info, capacity, RAID, PSNT, features |
| `GET /api/v7/vms/` | 200 | 50 | Yes | Fallback cluster/VMS info, capacity_base_10 |
| `GET /api/v7/apitokens/` | 200 | 8 | Yes (auth) | List/create API tokens |

### 2.2 Hardware (nodes, boxes, trays)

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/cnodes/` | 200 | 58 | Yes | CNode list, IPs, serials, cbox_id, position |
| `GET /api/v7/dnodes/` | 200 | 46 | Yes | DNode list, IPs, serials, dbox_id, position |
| `GET /api/v7/cboxes/` | 200 | 15 | Yes | CBox list, index_in_rack, rack_unit, rack_id/name |
| `GET /api/v7/dboxes/` | 200 | 26 | Yes | DBox list, index_in_rack, rack_unit, hardware_type |
| `GET /api/v7/dtrays/` | 200 | 25 | Yes | DTray details for DNode mapping |

### 2.3 Network (API)

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/dns/` | 200 | 25 | Yes | DNS config, VIP, domain_suffix |
| `GET /api/v7/ntps/` | 404 | — | Yes (optional) | NTP servers (not configured here) |
| `GET /api/v7/vippools/` | 200 | 38 | Yes | VIP pools, gateways, subnets |
| `GET /api/v7/vms/1/network_settings/` | not probed | — | Yes | Cluster/cnode/dnode network settings, net_type, boxes/hosts |

### 2.4 Logical configuration

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/tenants/` | 200 | 51 | Yes | Tenants, protocols, identity providers |
| `GET /api/v7/views/` | 200 | 60 | Yes | Views/exports, paths, protocols |
| `GET /api/v7/viewpolicies/` | 200 | 72 | Yes | View policies, NFS/SMB/S3 options |

### 2.5 Security

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/activedirectory/` | 200 | 20 | Yes | AD integration |
| `GET /api/v7/ldap/` | 404 | — | Yes (optional) | LDAP (not configured here) |
| `GET /api/v7/nis/` | 200 | 0* | Yes (optional) | NIS (empty list or no fields) |

### 2.6 Data protection

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/snapprograms/` | 404 | — | Yes (optional) | Snap programs (not exposed/configured) |
| `GET /api/v7/protectionpolicies/` | 200 | 27 | Yes | Protection/snapshot policies |

### 2.7 Monitoring

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/snmp/` | 404 | — | Yes (optional) | SNMP config |
| `GET /api/v7/syslog/` | 404 | — | Yes (optional) | Syslog config |
| `GET /api/v7/alerts/` | 404 | — | Yes (optional) | Alerts config |

### 2.8 Racks & switches (infrastructure)

| Endpoint | Status | Fields | Used by app | Purpose |
|----------|--------|--------|-------------|---------|
| `GET /api/v7/racks/` | 200 | 10 | Yes | Rack list, name, number_of_units, row, column |
| `GET /api/v1/switches/` | 200 | 28 | Yes | Switch inventory, hostname, model, fw_version, mgmt_ip, role |
| `GET /api/v1/ports/` | 200 | 14 | Yes | Port list per switch, name, state, speed, mtu |

---

## 3. Non-API Data Gathering (Related Infrastructure)

### 3.1 SSH-based port mapping (optional)

When **Enable port mapping** is turned on, the app uses **ExternalPortMapper** to gather:

| Source | Method | Data gathered |
|--------|--------|----------------|
| **VAST API** | `GET /api/v7/vms/1/network_settings/` (Basic Auth) | Node inventory, hostnames, IPs |
| **SSH to CNode** | clush / SSH as `node_user` (e.g. vastdata) | Hostname→data IP mapping; node interface MACs |
| **SSH to switches** | SSH as `switch_user` (e.g. cumulus / admin) | MAC tables; LLDP (Cumulus/Onyx) for port mapping |

**Purpose:** Build node↔switch↔port connectivity for the report (port map section).  
**Requires:** CNode management IP (from API), switch management IPs (from API), node and switch SSH credentials.  
**Supported switch OS:** Cumulus, Mellanox Onyx (interactive SSH).

### 3.2 Not used by this app

- **VNetMap** (e.g. `vnetmap.py`): Can be run separately; not invoked by the report generator.  
- **Switch config export:** Not automated; manual or external tool.  
- **BOM / part numbers:** Not available via API; manual input.

---

## 4. Data Gathering Options — Checklist

Use this to see what can be collected for cluster 10.143.11.202 and related infrastructure.

### 4.1 Cluster & capacity

- [x] Cluster identity, version, state, PSNT — `clusters/` (200)
- [x] Capacity (usable, free, logical/physical) — `clusters/`, `vms/`
- [x] RAID/health (SSD, NVRAM, memory) — `clusters/`
- [x] Features (encryption, similarity, S3, SMB, replication, etc.) — `clusters/`

### 4.2 Hardware (nodes, boxes, trays)

- [x] CNodes (IPs, serials, BIOS, CBox, position) — `cnodes/` (200)
- [x] DNodes (IPs, serials, DBox, position) — `dnodes/` (200)
- [x] CBoxes (rack_unit, index_in_rack, rack_id/name) — `cboxes/` (200)
- [x] DBoxes (rack_unit, index_in_rack, hardware_type) — `dboxes/` (200)
- [x] DTrays — `dtrays/` (200)

### 4.3 Network (API)

- [x] DNS — `dns/` (200)
- [ ] NTP — `ntps/` (404 on this cluster)
- [x] VIP pools — `vippools/` (200)
- [x] Per-node/cluster network settings — `vms/1/network_settings/` (used by app; not in export)

### 4.4 Logical & security

- [x] Tenants — `tenants/` (200)
- [x] Views — `views/` (200)
- [x] View policies — `viewpolicies/` (200)
- [x] Active Directory — `activedirectory/` (200)
- [ ] LDAP — `ldap/` (404 on this cluster)
- [x] NIS — `nis/` (200; empty)
- [x] Protection policies — `protectionpolicies/` (200)
- [ ] Snap programs — `snapprograms/` (404 on this cluster)

### 4.5 Monitoring

- [ ] SNMP — `snmp/` (404)
- [ ] Syslog — `syslog/` (404)
- [ ] Alerts — `alerts/` (404)

### 4.6 Racks & switches

- [x] Racks — `racks/` (200)
- [x] Switches — `api/v1/switches/` (200)
- [x] Switch ports — `api/v1/ports/` (200)

### 4.7 Node–switch connectivity (non-API)

- [x] Port mapping (node↔switch↔port) — **ExternalPortMapper** (SSH to CNode + switches) when enabled

---

## 5. Field Highlights (from catalog)

- **clusters/** (263 fields): Full cluster config, capacity, DR, EKM, S3/NFS/SMB, replication, upgrade state, performance metrics.  
- **cboxes/dboxes**: `index_in_rack`, `rack_unit`, `rack_id`, `rack_name` for rack positioning.  
- **racks/**: `name`, `number_of_units`, `row`, `column`, `available_capacity`, `total_capacity`.  
- **v1 switches/**: `hostname`, `model`, `fw_version`, `mgmt_ip`, `role`, `switch_type`, `sn`.  
- **v1 ports/**: `switch`, `name`, `state`, `speed`, `mtu`.

---

## 6. Recommendations

1. **No change required** for 404s: ntps, ldap, snapprograms, snmp, syslog, alerts are optional; app handles missing data.
2. **vms/1/network_settings/** is not in `export_swagger.py`’s probe list; consider adding it for future exports so network_settings appears in the catalog.
3. **Port mapping**: Ensure CNode and switch SSH credentials and network access if the report should include the port map.
4. **Rack/switch data**: All required API endpoints for racks and switches are available (200) on this cluster.
