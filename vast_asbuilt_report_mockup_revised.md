


# VAST Data Cluster As-Built Report (Revised)

**Customer:** Acme Corporation  
**Cluster Name:** ACME-PROD-01  
**Product Serial Number (PSNT):** VST-2025-AC-001234  
**Report Generated:** September 12, 2025  
**VAST Code Version:** 5.3.2  

---

## 1. Executive Summary

This document provides a comprehensive as-built summary of the VAST Data cluster deployed for Acme Corporation. The cluster is built on VAST's **Direct Attached Share Everything (DASE)** architecture, which provides a high-performance, scalable, and resilient platform for modern data-intensive workloads.

### 1.1. Cluster Overview

*   **Cluster Name:** ACME-PROD-01
*   **Product Serial Number (PSNT):** VST-2025-AC-001234
*   **VAST Code Version:** 5.3.2
*   **Cluster State:** Healthy
*   **Management VIP:** 192.168.100.10

### 1.2. Capacity Summary

*   **Total Usable Capacity:** 2.4 PB
*   **Licensed Capacity:** 2.5 PB

### 1.3. Deployed Architecture

*   **Core Architecture:** VAST DASE
*   **Internal Fabric:** High-Speed NVMe/InfiniBand (IPL)
*   **Customer Network Connectivity:** Secondary Dual-Port NICs from CBoxes

---

## 2. Architecture Overview

The VAST DASE architecture disaggregates compute and storage, allowing for independent scaling. Frontend **CBoxes (Compute Boxes)** are connected to backend **DBoxes (Data Boxes)** via a high-speed, low-latency NVMe/InfiniBand switch fabric. This allows any CNode to access any SSD on any DNode, creating a resilient and highly parallel share-everything environment.

![VAST DASE Architecture](/home/ubuntu/vast_dase_architecture_corrected.png)
*Figure 1: VAST DASE Architecture showing the separation of CBoxes and DBoxes connected by the IPL fabric, and customer network connectivity options.*




--- 

## 3. Physical Hardware Inventory

The cluster hardware is organized to support the DASE architecture, with frontend CBoxes providing compute and protocol services, and backend DBoxes providing high-density NVMe flash storage.

### 3.1. CBoxes (Frontend Compute)

| Unit   | Model | Serial Number | Nodes | Rack Position | Management IP  | Status  |
|--------|-------|---------------|-------|---------------|----------------|---------|
| CBox-1 | C24   | CB2025001234  | 24    | Rack A, U35-37 | 192.168.100.11 | Healthy |
| CBox-2 | C24   | CB2025001235  | 24    | Rack A, U38-40 | 192.168.100.12 | Healthy |
| CBox-3 | C24   | CB2025001236  | 24    | Rack A, U41-42 | 192.168.100.13 | Healthy |

### 3.2. DBoxes (Backend Storage)

| Unit   | Model | Serial Number | Nodes | Rack Position | Management IP  | Status  |
|--------|-------|---------------|-------|---------------|----------------|---------|
| DBox-1 | D24   | DB2025001234  | 24    | Rack A, U15-18 | 192.168.100.21 | Healthy |
| DBox-2 | D24   | DB2025001235  | 24    | Rack A, U19-22 | 192.168.100.22 | Healthy |
| DBox-3 | D24   | DB2025001236  | 24    | Rack A, U23-26 | 192.168.100.23 | Healthy |
| DBox-4 | D24   | DB2025001237  | 24    | Rack A, U27-30 | 192.168.100.24 | Healthy |
| DBox-5 | D24   | DB2025001238  | 24    | Rack A, U31-34 | 192.168.100.25 | Healthy |

### 3.3. Internal Fabric Switches (NVMe/IB)

| Unit      | Model          | Type      | Ports     | Firmware  | Rack Position | Role |
|-----------|----------------|-----------|-----------|-----------|---------------|------|
| IPL-SW-1  | Mellanox QM8700 | InfiniBand | 40x200GbE | 2.9.1000  | Rack A, U1-2  | Leaf |
| IPL-SW-2  | Mellanox QM8700 | InfiniBand | 40x200GbE | 2.9.1000  | Rack A, U3-4  | Leaf |

---

## 4. Network Configuration

### 4.1. Internal IPL Fabric

The internal fabric provides the high-speed, low-latency connectivity between CBoxes and DBoxes essential for the DASE architecture. All C-nodes and D-nodes are connected to this fabric.

*   **Fabric Type:** NVMe/InfiniBand
*   **Switch Model:** Mellanox QM8700
*   **Port Speed:** 200GbE

### 4.2. Customer Network Connectivity

Connectivity to the customer network is provided via secondary dual-port NICs on each CBox. This provides a direct, high-bandwidth path for data access without traversing the internal IPL fabric.

*   **Connection Method:** Secondary Dual-Port NICs from CBoxes
*   **NIC Type:** 2 x 100GbE Ethernet
*   **VLANs:** 100 (NFS), 200 (SMB), 300 (S3)

### 4.3. Management Network

*   **VMS VIP:** 192.168.100.10
*   **DNS Servers:** 8.8.8.8, 8.8.4.4
*   **NTP Servers:** pool.ntp.org




---

## 5. Physical Layout Diagram

The following diagram illustrates the physical placement of all VAST cluster components within a single 42U rack.

![VAST Cluster Single Rack Layout](/home/ubuntu/vast_rack_layout_corrected.png)
*Figure 2: Physical rack layout of the VAST Data cluster, showing the placement of CBoxes, DBoxes, and IPL switches.*

### 5.1. Rack Layout Summary

*   **U35-42:** CBoxes (Frontend Compute)
*   **U15-34:** DBoxes (Backend Storage)
*   **U1-4:** IPL Fabric Switches (NVMe/IB)

---

## 6. Appendix: Manual Data

### 6.1. Bill of Materials (BOM)

*   **CBox C24:** Part# VAST-C24-2025
*   **DBox D24:** Part# VAST-D24-2025
*   **Mellanox QM8700:** Part# MQM8700-HS2F

### 6.2. Cable Information

*   **Internal Fabric:** Direct Attach Copper (DAC) 200GbE
*   **Customer Network:** Fiber Optic 100GbE (QSFP28)



