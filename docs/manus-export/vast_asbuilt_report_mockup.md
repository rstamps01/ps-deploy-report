# VAST Data Cluster As-Built Report

**Customer:** Acme Corporation  
**Cluster Name:** ACME-PROD-01  
**Product Serial Number (PSNT):** VST-2025-AC-001234  
**Report Generated:** September 11, 2025  
**VAST Code Version:** 5.3.2  

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Physical Hardware Inventory](#physical-hardware-inventory)
3. [Network Configuration](#network-configuration)
4. [Logical Configuration](#logical-configuration)
5. [Security Configuration](#security-configuration)
6. [Data Protection](#data-protection)
7. [Physical Layout Diagram](#physical-layout-diagram)
8. [Appendix: Manual Data](#appendix-manual-data)

---

## Executive Summary

### Cluster Overview

**Cluster Identification:**
- **Cluster Name:** ACME-PROD-01
- **Product Serial Number (PSNT):** VST-2025-AC-001234
- **VAST Code Version:** 5.3.2
- **Cluster GUID:** 12345678-1234-5678-9abc-123456789012
- **Cluster State:** Healthy
- **Management VIP:** 192.168.100.10

**Capacity Summary:**
- **Total Usable Capacity:** 2.4 PB
- **Licensed Capacity:** 2.5 PB
- **Utilization:** 15% (360 TB used)

**Key Features Enabled:**
- ✅ Encryption at Rest
- ✅ B2B (Business to Business) Connectivity
- ✅ Data Similarity Detection
- ✅ Native Replication
- ✅ Snapshot Policies

**Protocols in Use:**
- NFS v3/v4
- SMB 2.1/3.0
- S3 Compatible API

---

## Physical Hardware Inventory

### CBoxes (Compute Boxes)

| Unit | Model | Serial Number | Nodes | Rack Position | Management IP | Status |
|------|-------|---------------|-------|---------------|---------------|--------|
| CBox-1 | C24 | CB2025001234 | 24 | Rack A, U1-4 | 192.168.100.11 | Healthy |
| CBox-2 | C24 | CB2025001235 | 24 | Rack A, U5-8 | 192.168.100.12 | Healthy |
| CBox-3 | C24 | CB2025001236 | 24 | Rack B, U1-4 | 192.168.100.13 | Healthy |

**CBox Summary:**
- **Total CBoxes:** 3
- **Total CNodes:** 72
- **NICs per CNode:** 2 (1x Management, 1x Data)
- **Total Rack Space:** 12U

### DBoxes (Data Boxes)

| Unit | Model | Serial Number | Nodes | Rack Position | Management IP | Status |
|------|-------|---------------|-------|---------------|---------------|--------|
| DBox-1 | D24 | DB2025001234 | 24 | Rack A, U9-12 | 192.168.100.21 | Healthy |
| DBox-2 | D24 | DB2025001235 | 24 | Rack A, U13-16 | 192.168.100.22 | Healthy |
| DBox-3 | D24 | DB2025001236 | 24 | Rack A, U17-20 | 192.168.100.23 | Healthy |
| DBox-4 | D24 | DB2025001237 | 24 | Rack B, U5-8 | 192.168.100.24 | Healthy |
| DBox-5 | D24 | DB2025001238 | 24 | Rack B, U9-12 | 192.168.100.25 | Healthy |
| DBox-6 | D24 | DB2025001239 | 24 | Rack B, U13-16 | 192.168.100.26 | Healthy |

**DBox Summary:**
- **Total DBoxes:** 6
- **Total DNodes:** 144
- **Total Rack Space:** 24U

### Network Switches

| Unit | Model | Type | Ports | Firmware | Rack Position | Management IP | Role |
|------|-------|------|-------|----------|---------------|---------------|------|
| SW-LEAF-1 | Mellanox SN3700 | Ethernet | 32x100GbE | 3.10.1000 | Rack A, U21-22 | 192.168.100.31 | Leaf |
| SW-LEAF-2 | Mellanox SN3700 | Ethernet | 32x100GbE | 3.10.1000 | Rack B, U17-18 | 192.168.100.32 | Leaf |
| SW-SPINE-1 | Mellanox SN4600 | Ethernet | 64x100GbE | 3.10.1000 | Rack C, U1-2 | 192.168.100.33 | Spine |
| SW-SPINE-2 | Mellanox SN4600 | Ethernet | 64x100GbE | 3.10.1000 | Rack C, U3-4 | 192.168.100.34 | Spine |

**Switch Summary:**
- **Total Switches:** 4
- **Leaf Switches:** 2
- **Spine Switches:** 2
- **Total Ports:** 192 (64 in use, 128 available)

---

## Network Configuration

### Management Network

**VMS (VAST Management Service):**
- **Primary VIP:** 192.168.100.10
- **Secondary VIP:** 192.168.100.11 (Standby)

**Network Services:**
- **DNS Servers:** 8.8.8.8, 8.8.4.4
- **NTP Servers:** pool.ntp.org, time.google.com
- **Domain:** acme.local

### Data Network

**VIP Pools:**

| Pool Name | VLAN | Subnet | Gateway | Available IPs |
|-----------|------|--------|---------|---------------|
| NFS-Pool | 100 | 10.100.0.0/24 | 10.100.0.1 | 10.100.0.10-10.100.0.50 |
| SMB-Pool | 200 | 10.200.0.0/24 | 10.200.0.1 | 10.200.0.10-10.200.0.50 |
| S3-Pool | 300 | 10.300.0.0/24 | 10.300.0.1 | 10.300.0.10-10.300.0.50 |

### Port Configuration

**Switch Port Utilization:**

| Switch | Total Ports | Used Ports | Available Ports | Utilization |
|--------|-------------|------------|-----------------|-------------|
| SW-LEAF-1 | 32 | 18 | 14 | 56% |
| SW-LEAF-2 | 32 | 18 | 14 | 56% |
| SW-SPINE-1 | 64 | 14 | 50 | 22% |
| SW-SPINE-2 | 64 | 14 | 50 | 22% |

---

## Logical Configuration

### Tenants

| Tenant Name | Protocols | Views | Policies | Status |
|-------------|-----------|-------|----------|--------|
| Production | NFS, SMB | 12 | 8 | Active |
| Development | NFS | 4 | 2 | Active |
| Backup | S3 | 2 | 1 | Active |

### Views

**Production Tenant Views:**

| View Name | Protocol | Path | Size Limit | Snapshot Policy |
|-----------|----------|------|------------|-----------------|
| prod-nfs-01 | NFS | /prod/app1 | 100 TB | Daily-7d |
| prod-nfs-02 | NFS | /prod/app2 | 150 TB | Daily-7d |
| prod-smb-01 | SMB | \\acme\shares\prod | 200 TB | Hourly-24h |

**Development Tenant Views:**

| View Name | Protocol | Path | Size Limit | Snapshot Policy |
|-----------|----------|------|------------|-----------------|
| dev-nfs-01 | NFS | /dev/testing | 50 TB | Daily-3d |
| dev-nfs-02 | NFS | /dev/staging | 75 TB | Daily-3d |

---

## Security Configuration

### Authentication Providers

**Active Directory Integration:**
- **Domain Controller:** dc1.acme.local
- **LDAP Server:** ldap://dc1.acme.local:389
- **Base DN:** DC=acme,DC=local
- **Service Account:** vast-service@acme.local
- **Status:** Connected

**User Mappings:**
- **Domain Admins → VAST Admins**
- **IT Team → VAST Power Users**
- **Developers → VAST Users**

### Access Control

**View Policies:**

| Policy Name | Applied To | Permissions | User/Group |
|-------------|------------|-------------|------------|
| Prod-ReadWrite | prod-nfs-* | RW | IT Team |
| Prod-ReadOnly | prod-nfs-* | RO | Developers |
| Dev-Full | dev-nfs-* | RW | Developers |

---

## Data Protection

### Snapshot Policies

| Policy Name | Schedule | Retention | Applied Views | Status |
|-------------|----------|-----------|---------------|--------|
| Hourly-24h | Every hour | 24 hours | prod-smb-01 | Active |
| Daily-7d | Daily at 2 AM | 7 days | prod-nfs-*, dev-nfs-01 | Active |
| Daily-3d | Daily at 3 AM | 3 days | dev-nfs-02 | Active |
| Weekly-4w | Weekly on Sunday | 4 weeks | All production views | Active |

### Replication

**Replication Targets:**
- **DR Site:** ACME-DR-01 (192.168.200.10)
- **Replication Schedule:** Every 4 hours
- **Status:** Healthy
- **Last Sync:** September 11, 2025 14:00 UTC

---

## Physical Layout Diagram

![Rack Layout Diagram](/home/ubuntu/rack_layout_diagram.png)
*Figure 1: Physical rack layout of the VAST Data cluster, showing the positions of all CBoxes, DBoxes, and switches across three racks.*

### Rack Layout Summary

**Rack A (Primary Data Rack):**
- U1-4: CBox-1 (CB2025001234)
- U5-8: CBox-2 (CB2025001235)
- U9-12: DBox-1 (DB2025001234)
- U13-16: DBox-2 (DB2025001235)
- U17-20: DBox-3 (DB2025001236)
- U21-22: SW-LEAF-1 (Mellanox SN3700)
- U23-42: Available

**Rack B (Secondary Data Rack):**
- U1-4: CBox-3 (CB2025001236)
- U5-8: DBox-4 (DB2025001237)
- U9-12: DBox-5 (DB2025001238)
- U13-16: DBox-6 (DB2025001239)
- U17-18: SW-LEAF-2 (Mellanox SN3700)
- U19-42: Available

**Rack C (Network Rack):**
- U1-2: SW-SPINE-1 (Mellanox SN4600)
- U3-4: SW-SPINE-2 (Mellanox SN4600)
- U5-42: Available

---

## Appendix: Manual Data

### Bill of Materials (BOM) Part Numbers

**Hardware Components:**
- **CBox C24:** Part# VAST-C24-2025
- **DBox D24:** Part# VAST-D24-2025
- **Mellanox SN3700:** Part# MSN3700-CS2F
- **Mellanox SN4600:** Part# MSN4600-CS2F

### Cable Information

**Data Network Cables:**
- **CBox to Leaf:** Direct Attach Copper (DAC) 100GbE
- **DBox to Leaf:** Direct Attach Copper (DAC) 100GbE
- **Leaf to Spine:** Fiber Optic 100GbE (QSFP28)

### Use Cases

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




## Network Topology Diagram

![Network Topology Diagram](/home/ubuntu/network_topology_diagram.png)
*Figure 2: Network topology of the VAST Data cluster, illustrating the connectivity between spine switches, leaf switches, CBoxes, and DBoxes. The diagram shows the separation of data and management networks.*

