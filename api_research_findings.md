# VAST API v7 Research Findings

## Data Points from Research Document

Based on the API data gathering research document, the following data points are required for the as-built report:

### Cluster Hardware Details
- **BOM (Bill of Materials)**
  - Part Numbers
  - Quantities  
  - Serial Numbers

- **CBoxes (Compute Boxes)**
  - Quantity
  - Hardware type & manufacturer
  - Number of Nodes
  - Number of NICs
  - B2B enabled status
  - Encryption enabled status
  - Similarity enabled status
  - VAST Code Version(s)
  - Rack Height (U#)

- **DBoxes (Data Boxes)**
  - Quantity
  - Hardware type & manufacturer
  - Number of Nodes
  - B2B enabled status
  - VAST Code Version(s)
  - Rack Height (U#)

- **Switches**
  - Quantity
  - Hardware type & manufacturer (Mellanox/Cisco/Aruba)
  - Protocol (Ethernet/IB)
  - Port Count (16/32/40/64)
  - Port Speed(s)
  - Port Function (Node/IPL/ISL/MLAG)
  - Ports in use
  - Ports Available
  - Switch role (Master/Slave)
  - Switch tier (Leaf/Spine)
  - Firmware Version(s)
  - Rack Height (U#)
  - Cables (direct/splitter)

- **Northbound Connection**
  - Switch to Switch / CNode to Switch

### Cluster Deployment Details
- Usable Capacity
- Licensed Capacity
- Protocol (NFS, SMB, Object, Block, etc)
- Use Case(s) (AI, ML, HPC, DB, BU, Cloud, Hybrid, etc)
- Advanced Features (Replication, DataBase, etc)

### Cluster Administration Details
- **Basic Information**
  - Cluster Name
  - Cluster PSNT
  - Cluster VMS VIP
  - Default Users & Passwords (VMS, IPMI, Mgmt Port, Tech Port)

- **IP Information**
  - Network Services (DNS, DNS Search Domain, NTP, AD, LDAP, Other)
  - CNode & DNode & Switch Management (Port Label, Port IP, Port Function, IPMI, Mgmt Port, Tech Port)
  - Data Network (VIP, Replication, Other)

- **Network Configuration**
  - Node to Switch to Switch Connectivity map
  - Network Port Map
  - Switch Configuration
  - Switch Cable Routing Validation Report

## Research Progress
- [x] Document analysis complete
- [x] VAST API v7 endpoint research
- [x] Data availability analysis
- [x] Alternative methods identification

## Updated API Schema Findings

**Additional API Capabilities Discovered:**

### Rack Height Information:
- **CBox Rack Heights**: Available via `Schema/CBox/index_in_rack`
- **DBox Rack Heights**: Available via `Schema/DBox/index_in_rack`

### Cluster PSNT:
- **Cluster PSNT**: Available via `Schema/Cluster/psnt`

These discoveries significantly improve the API coverage for the as-built report, moving these data points from "Manual" to "API" collection methods.



## VAST API v7 Documentation Access

Successfully accessed VAST Data API documentation at: https://support.vastdata.com/s/api-docs

### Key Findings from API Documentation:

**Changes in Version 7 (for VAST Cluster 5.3):**
- About Versioning and Backward Compatibility
- Authentication
- API Tokens
- Block Storage Protocol Support
- Client Metrics
- Encryption with External Key Management (EKM)
- Folder Management
- Layer 3 Network Connectivity
- Multi-tenancy Enhancements
- S3 Indestructible Object Mode
- User Impersonation
- VAST Audit Log
- VAST Database
- VAST Event Broker
- Other Additions and Changes

**Available API Sections:**
- Introduction to the VMS REST API
- Getting Started
- User Permissions for Cluster, Tenant and Resource Access
- Authentication
- VMS
- Administrators
- Infrastructure
- Element Store
- Network Access
- Data Engine
- Data Protection



## VAST REST API Access Information

**API Documentation Location:** `https://<VMS_VIP>/docs/index.html`
- VMS_VIP is the IP provided when installing the cluster as the management VIP
- This is the IP used to connect to the VAST Cluster management server (VMS)
- Documentation is accessible from within the VMS management network

**Key Information:**
- VAST Management System (VMS) has a REST API for developing custom management clients
- API can be used to integrate VMS functionality into custom management infrastructure
- API documentation is exposed using Swagger for easier understanding and use


## Hardware Management via VMS Web UI

**Key Findings from Hardware Management Documentation:**

### CBox/DBox/EBox Management Process:
1. **Discovery Process**: VMS can discover new hardware automatically
   - Uses "Discover Now" functionality
   - Validates discovered hardware
   - Shows discovery state and completion status
   - Monitors via Activities page with _host_discovery_ activity

2. **Hardware Information Available**:
   - **CBoxes**: Compute service boxes
   - **DBoxes**: Storage boxes  
   - **EBoxes**: Combined compute and storage boxes
   - Node-level details within each box
   - Hardware validation and error detection

3. **Error Detection Capabilities**:
   - CPU errors
   - Memory errors
   - Disk errors
   - SCM (Storage Class Memory) errors
   - Port connectivity errors
   - Licensing issues
   - Node location identification (hover to see position in CBox/DBox)

4. **Configuration Management**:
   - IP pool assignment for management networks
   - IPMI pool configuration
   - Rack assignments
   - Network configuration per node

### Hardware Identification Features:
- Remote LED Control for hardware identification
- Failed device location
- Hardware activation/deactivation
- Power cycling capabilities
- Hardware description editing
- Status LEDs (Mavericks DBox)


## Switch Management via VAST API

**Key Findings from Switch Management Documentation:**

### Switch Discovery and Management:
- **Automatic Discovery**: Starting with VAST Cluster 5.3.2, switches may be discovered automatically
- **Manual Addition**: Switches can be added manually via Web UI or CLI
- **Credential Management**: Requires switch OS credentials for full property access

### Switch Properties Available via API:
- **Basic Information**:
  - ID (VMS ID of the switch)
  - Name (descriptive name)
  - Title (descriptive name)
  - Hostname
  - IP (management IP address)
  - Model
  - Serial Number
  - Firmware Version
  - State (varies by vendor)

- **Switch Types Supported**:
  - arista
  - mellanox
  - mellanox-os
  - aruba
  - cumulus
  - unknown

### Switch Port Properties Available via API:
- **Port Identification**:
  - ID (VMS ID of switch port)
  - Name (interface name on switch OS)
  - Title (composite title with Model and Name values)

- **Port Configuration**:
  - Model (port configuration mode):
    - PORT
    - MLAG
    - CHANNEL
  - Speed (configured port speed)
  - MTU (configured MTU)
  - State (port state from switch, vendor-specific)
  - Switch (reference to parent switch)

### CLI Commands Available:
- `switch add` - Add switch
- `switch modify` - Modify switch credentials
- `switch list` - Display switches and properties
- `switch show` - Show specific switch details
- `port list` - Display switch ports and properties
- `port show` - Show specific port details

### API Access Methods:
- **Web UI**: Infrastructure page → Switches tab / Switch Ports tab
- **CLI**: Various switch and port commands
- **REST API**: Accessible via VMS REST API endpoints

