# VAST Data Cluster As-Built Report (Final Corrected)

**Customer:** Acme Corporation  
**Cluster Name:** ACME-PROD-01  
**Product Serial Number (PSNT):** VST-2025-AC-001234  
**Report Generated:** September 12, 2025  
**VAST Code Version:** 5.3.2  
**Cluster Configuration:** 4x4 (4 CBoxes, 4 DBoxes)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Physical Hardware Inventory](#physical-hardware-inventory)
4. [Network Configuration](#network-configuration)
5. [Logical Configuration](#logical-configuration)
6. [Security Configuration](#security-configuration)
7. [Data Protection](#data-protection)
8. [Physical Layout Diagrams](#physical-layout-diagrams)
9. [Cable Connectivity](#cable-connectivity)
10. [Appendix: Manual Data](#appendix-manual-data)

---

## 1. Executive Summary

### 1.1. Cluster Overview

**Cluster Identification:**
- **Cluster Name:** ACME-PROD-01
- **Product Serial Number (PSNT):** VST-2025-AC-001234
- **VAST Code Version:** 5.3.2
- **Cluster Configuration:** 4x4 (4 CBoxes, 4 DBoxes)
- **Cluster State:** Healthy
- **Management VIP:** 192.168.100.10

**Capacity Summary:**
- **Total Usable Capacity:** 2.4 PB
- **Licensed Capacity:** 2.5 PB
- **Utilization:** 15% (360 TB used)

**Key Features Enabled:**
- ✅ Encryption at Rest
- ✅ Data Similarity Detection
- ✅ Native Replication
- ✅ Snapshot Policies

**Protocols in Use:**
- NFS v3/v4
- SMB 2.1/3.0
- S3 Compatible API

---

## 2. Architecture Overview

The VAST cluster is built on a disaggregated architecture where frontend **CBoxes** (containing **CNodes**) handle all data processing and protocol services, while backend **DBoxes** (containing **DNodes**) provide high-density NVMe flash storage. All communication between CNodes and DNodes occurs exclusively through a high-speed switch fabric, ensuring optimal performance and redundancy.

### 2.1. Key Architectural Principles

- **CNodes connect only to the switch fabric** - never directly to DNodes
- **DNodes connect only to the switch fabric** - never to customer networks
- **All CNodes can access all NVMe media** in all DBoxes through the fabric
- **Customer network connectivity** via secondary dual NICs on CNodes or switch MLAG
- **Redundant A/B switch fabric** for high availability

![VAST 4x4 Cluster Architecture](/home/ubuntu/vast_4x4_architecture_corrected.png)
*Figure 1: VAST 4x4 cluster architecture showing proper connectivity through the switch fabric*

---

## 3. Physical Hardware Inventory

### 3.1. CBoxes (Frontend Compute)

| Unit   | Model | Serial Number | CNodes | Rack Position | Management IP   | Status  |
|--------|-------|---------------|--------|---------------|-----------------|---------|
| CBox-1 | C24   | CB2025001234  | 24     | Rack A, U41-42 | 192.168.100.11  | Healthy |
| CBox-2 | C24   | CB2025001235  | 24     | Rack A, U39-40 | 192.168.100.12  | Healthy |
| CBox-3 | C24   | CB2025001236  | 24     | Rack A, U37-38 | 192.168.100.13  | Healthy |
| CBox-4 | C24   | CB2025001237  | 24     | Rack A, U35-36 | 192.168.100.14  | Healthy |

**CBox Summary:**
- **Total CBoxes:** 4
- **Total CNodes:** 96
- **Connectivity:** Dual-port (A/B) to switch fabric + secondary dual NICs for customer network
- **Total Rack Space:** 8U

### 3.2. DBoxes (Backend Storage)

| Unit   | Model | Serial Number | DNodes | Rack Position | Management IP   | Status  |
|--------|-------|---------------|--------|---------------|-----------------|---------|
| DBox-1 | D24   | DB2025001234  | 24     | Rack A, U25-28 | 192.168.100.21  | Healthy |
| DBox-2 | D24   | DB2025001235  | 24     | Rack A, U21-24 | 192.168.100.22  | Healthy |
| DBox-3 | D24   | DB2025001236  | 24     | Rack A, U17-20 | 192.168.100.23  | Healthy |
| DBox-4 | D24   | DB2025001237  | 24     | Rack A, U13-16 | 192.168.100.24  | Healthy |

**DBox Summary:**
- **Total DBoxes:** 4
- **Total DNodes:** 96
- **Connectivity:** Dual-port (A/B) to switch fabric only
- **Total Rack Space:** 16U

### 3.3. Switch Fabric

| Unit     | Model           | Type     | Ports | Speed   | Firmware | Rack Position | Role    |
|----------|-----------------|----------|-------|---------|----------|---------------|---------|
| Switch-A | Mellanox SN3700 | Ethernet | 32    | 100GbE  | 3.10.1000| Rack A, U32-33| Lower   |
| Switch-B | Mellanox SN3700 | Ethernet | 32    | 100GbE  | 3.10.1000| Rack A, U30-31| Upper   |

**Switch Summary:**
- **Total Switches:** 2 (A/B redundant pair)
- **Inter-switch Links:** Multiple 100GbE uplinks
- **Port Utilization:** 64 ports used (32 per switch), 0 available
- **Total Rack Space:** 4U

---

## 4. Network Configuration

### 4.1. Switch Fabric Network

The internal switch fabric provides high-speed, low-latency connectivity between all CNodes and DNodes using a redundant A/B switch design.

**Fabric Configuration:**
- **Switch Type:** Mellanox SN3700 Ethernet
- **Port Speed:** 100GbE (200GbE supported)
- **Redundancy:** Dual A/B switches with inter-switch links
- **Port Assignment:** A ports → Switch A, B ports → Switch B

### 4.2. Customer Network Connectivity

Customer network access is provided via secondary dual-port NICs on CNodes, completely separate from the internal fabric.

**Customer Network Options:**
- **Primary Method:** Secondary dual-port NICs from CNodes
- **Alternative Method:** Switch MLAG connections (if configured)
- **Network Isolation:** DNodes have no customer network access

**VIP Pools:**

| Pool Name | VLAN | Subnet        | Gateway    | Available IPs           |
|-----------|------|---------------|------------|-------------------------|
| NFS-Pool  | 100  | 10.100.0.0/24 | 10.100.0.1 | 10.100.0.10-10.100.0.50 |
| SMB-Pool  | 200  | 10.200.0.0/24 | 10.200.0.1 | 10.200.0.10-10.200.0.50 |
| S3-Pool   | 300  | 10.300.0.0/24 | 10.300.0.1 | 10.300.0.10-10.300.0.50 |

### 4.3. Management Network

**VMS (VAST Management Service):**
- **Primary VIP:** 192.168.100.10
- **Network Services:** DNS (8.8.8.8, 8.8.4.4), NTP (pool.ntp.org)
- **Domain:** acme.local

---

## 5. Logical Configuration

### 5.1. Tenants

| Tenant Name | Protocols | Views | Policies | Status |
|-------------|-----------|-------|----------|--------|
| Production  | NFS, SMB  | 12    | 8        | Active |
| Development | NFS       | 4     | 2        | Active |
| Backup      | S3        | 2     | 1        | Active |

### 5.2. Views

**Production Tenant Views:**

| View Name   | Protocol | Path              | Size Limit | Snapshot Policy |
|-------------|----------|-------------------|------------|-----------------|
| prod-nfs-01 | NFS      | /prod/app1        | 100 TB     | Daily-7d        |
| prod-nfs-02 | NFS      | /prod/app2        | 150 TB     | Daily-7d        |
| prod-smb-01 | SMB      | \\acme\shares\prod| 200 TB     | Hourly-24h      |

---

## 6. Security Configuration

### 6.1. Authentication Providers

**Active Directory Integration:**
- **Domain Controller:** dc1.acme.local
- **LDAP Server:** ldap://dc1.acme.local:389
- **Base DN:** DC=acme,DC=local
- **Service Account:** vast-service@acme.local
- **Status:** Connected

---

## 7. Data Protection

### 7.1. Snapshot Policies

| Policy Name | Schedule      | Retention | Applied Views        | Status |
|-------------|---------------|-----------|---------------------|--------|
| Hourly-24h  | Every hour    | 24 hours  | prod-smb-01         | Active |
| Daily-7d    | Daily at 2 AM | 7 days    | prod-nfs-*, dev-nfs-01| Active |
| Weekly-4w   | Weekly Sunday | 4 weeks   | All production views| Active |

### 7.2. Replication

**Replication Configuration:**
- **DR Site:** ACME-DR-01 (192.168.200.10)
- **Schedule:** Every 4 hours
- **Status:** Healthy
- **Last Sync:** September 12, 2025 14:00 UTC

---

## 8. Physical Layout Diagrams

### 8.1. Rack Layout

![VAST 4x4 Cluster Rack Layout](/home/ubuntu/vast_4x4_rack_layout_corrected.png)
*Figure 2: Physical rack layout showing the placement of 4 CBoxes, 2 switches, and 4 DBoxes*

### 8.2. Rack Layout Summary

**Rack A (42U) - VAST 4x4 Cluster:**
- **U35-42:** CBoxes (4 units, 2U each)
- **U30-33:** Switch Fabric (2 switches, 2U each)
- **U13-28:** DBoxes (4 units, 4U each)
- **U1-12:** Available for expansion

---

## 9. Cable Connectivity

### 9.1. A/B Port Orientation

The VAST cluster uses a standardized A/B port orientation for redundancy and optimal performance:

![VAST Switch Port Map](/home/ubuntu/vast_switch_port_map.png)
*Figure 3: Switch port map showing cable labels, port assignments, and A/B orientation*

### 9.2. Switch Port Map Details

**Port Assignment Standards:**
- **A Ports (Right-side):** Connect to Switch A (Bottom/Red)
- **B Ports (Left-side):** Connect to Switch B (Top/Orange)
- **Cable Labeling:** Format: [Node]-[Port]-SW[Switch]-[Port#]
  - Example: CN1-A-SWA-1 (CNode 1, A port, Switch A, Port 1)
  - Example: DN1-B-SWB-2 (DNode 1, B port, Switch B, Port 2)

**Switch Configuration:**
- **Switch A (Bottom):** Serial# 1234367, Ports 1-32
- **Switch B (Top):** Serial# 9876543, Ports 1-32
- **Inter-switch Links:** Multiple connections between Switch A and Switch B
- **Port Utilization:** Visual indicators show used vs. available ports

**Cable Management:**
- **Cable Types:** Direct Attach Copper (DAC) 100GbE
- **Connector Type:** QSFP28
- **Cable Length:** Varies by rack position (1-3 meters typical)

---

## 10. Appendix: Manual Data

### 10.1. Bill of Materials (BOM) Part Numbers

**Hardware Components:**
- **CBox C24:** Part# VAST-C24-2025
- **DBox D24:** Part# VAST-D24-2025
- **Mellanox SN3700:** Part# MSN3700-CS2F

### 10.2. Cable Information

**Internal Fabric Cables:**
- **Type:** Direct Attach Copper (DAC)
- **Speed:** 100GbE
- **Connector:** QSFP28

**Customer Network Cables:**
- **Type:** Fiber Optic
- **Speed:** 100GbE
- **Connector:** QSFP28

### 10.3. Use Cases

**Primary Use Cases:**
- **High-Performance Computing (HPC):** Scientific simulations and modeling
- **Artificial Intelligence/Machine Learning:** Training and inference workloads
- **Media and Entertainment:** Video editing and rendering workflows
- **Database Analytics:** Large-scale data analytics and reporting

---

**Report Generation Details:**
- **Generated By:** VAST As-Built Report Generator v1.1
- **Data Collection Method:** 80% Automated via VAST API v7, 20% Manual Input
- **Generation Time:** 3 minutes 42 seconds
- **Cluster Access:** Read-only API credentials
- **Report Format:** PDF with embedded JSON data

---

*This report was automatically generated using the VAST As-Built Report Generator. For questions or support, please contact VAST Professional Services with the Cluster PSNT: VST-2025-AC-001234*

