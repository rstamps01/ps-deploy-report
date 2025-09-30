# Leaf Switch Configuration Analysis - Mellanox Leaf Switches

## Overview
Analysis of 14 Mellanox leaf switch configuration files from the VAST cluster deployment. Each switch is configured with Cumulus Linux using `nv` (NVUE) commands.

## Leaf Switch Inventory
- **Leaf 1**: ams17-spi-leaf1-vast-a (10.0.0.1) - AS 4263716756
- **Leaf 2**: ams17-spi-leaf2-vast-a (10.0.0.2) - AS 4263716757
- **Leaf 3**: ams17-spi-leaf3-vast-a (10.0.0.3) - AS 4263716758
- **Leaf 4**: ams17-spi-leaf4-vast-a (10.0.0.4) - AS 4263716759
- **Leaf 5**: ams17-spi-leaf5-vast-a (10.0.0.5) - AS 4263716760
- **Leaf 6**: ams17-spi-leaf6-vast-a (10.0.0.6) - AS 4263716761
- **Leaf 7**: ams17-spi-leaf7-vast-a (10.0.0.7) - AS 4263716762
- **Leaf 8**: ams17-spi-leaf8-vast-a (10.0.0.8) - AS 4263716763
- **Leaf 9**: ams17-spi-leaf9-vast-a (10.0.0.9) - AS 4263716764
- **Leaf 10**: ams17-spi-leaf10-vast-a (10.0.0.10) - AS 4263716765
- **Leaf 11**: ams17-spi-leaf11-vast-a (10.0.0.11) - AS 4263716766
- **Leaf 12**: ams17-spi-leaf12-vast-a (10.0.0.12) - AS 4263716767
- **Leaf 13**: ams17-spi-leaf13-vast-a (10.0.0.13) - AS 4263716768
- **Leaf 14**: ams17-spi-leaf14-vast-a (10.0.0.14) - AS 4263716769

## Configuration Analysis

### ✅ **Consistent Configurations**

#### Management Network
- All leaf switches use consistent management IP addressing:
  - Leaf 1: 10.71.198.8/23
  - Leaf 2: 10.71.198.9/23
  - Leaf 3: 10.71.198.10/23
  - Leaf 4: 10.71.198.11/23
  - Leaf 5: 10.71.198.12/23
  - Leaf 6: 10.71.198.13/23
  - Leaf 7: 10.71.198.14/23
  - Leaf 8: 10.71.198.15/23
  - Leaf 9: 10.71.198.16/23
  - Leaf 10: 10.71.198.17/23
  - Leaf 11: 10.71.198.18/23
  - Leaf 12: 10.71.198.19/23
  - Leaf 13: 10.71.198.20/23
  - Leaf 14: 10.71.198.21/23
- Gateway: 10.71.198.1 (consistent across all)
- VRF: mgmt (consistent)

#### BGP Configuration
- **AS Numbers**: Sequential from 4263716756 to 4263716769 (unique per leaf)
- **Router IDs**: Properly sequential (10.0.0.1 through 10.0.0.14)
- **Graceful Restart**: Identical settings across all switches
- **BFD Settings**: Consistent parameters (detect-multiplier: 3, intervals: 300ms)

#### EVPN/VXLAN Configuration
- **EVPN**: Enabled on all switches
- **VNI**: 4001 for VRF RED (consistent)
- **VXLAN**: Enabled on all switches
- **VXLAN Source Addresses**: Sequential (10.0.0.1 through 10.0.0.14)

#### VLAN and Bridge Configuration
- **VLAN 10**: VNI 10, untagged
- **VLAN 69**: VNI 69
- **VLAN 100**: VNI 100, SVI with VRR
- **VLAN 200**: VNI 200, SVI with VRR

#### Services
- **NTP Server**: 10.71.1.90 (consistent)
- **DNS Server**: 10.71.24.8 (consistent)
- **QoS**: RoCE enabled, L3 trust mapping, PFC watchdog enabled

### ⚠️ **Potential Issues and Conflicts**

#### 1. **VLAN IP Address Conflicts**
**CRITICAL ISSUE**: All leaf switches have identical VLAN IP addressing, which will cause conflicts:

**VLAN 100 (10.71.197.0/23)**:
- All switches use different IPs but same VRR address (10.71.197.254)
- This is actually correct - each switch has its own IP, but they share the VRR VIP

**VLAN 200 (10.71.195.0/24)**:
- All switches use different IPs but same VRR address (10.71.195.254)
- This is actually correct - each switch has its own IP, but they share the VRR VIP

**Analysis**: The VLAN addressing is actually correct. Each leaf has a unique IP in the VLAN, but they all share the same VRR (Virtual Router Redundancy) address for high availability.

#### 2. **BGP Neighbor Configuration**
**POTENTIAL ISSUE**: All leaf switches are configured to peer with spine switches on interfaces swp21-28:
- `nv set vrf default router bgp neighbor swp21-22,23-24,25-26,27-28 peer-group eBGP`
- `nv set vrf default router bgp neighbor swp21-22,23-24,25-26,27-28 type unnumbered`

This suggests a standardized configuration, but it's unclear if all interfaces are actually connected and in use.

#### 3. **Interface Configuration**
**MINOR ISSUE**: All switches have identical interface configurations:
- swp1-20: Bridge domain br_default (for server connections)
- swp21-28: Type swp (for spine connections)

This suggests a standardized configuration, but it's unclear if all interfaces are actually connected and in use.

### 🔍 **Detailed IP Address Analysis**

#### Management Network (10.71.198.0/23)
- Gateway: 10.71.198.1
- Leaf switches: 10.71.198.8 through 10.71.198.21
- **Status**: ✅ No conflicts, proper sequential addressing

#### Loopback Addresses (10.0.0.0/32)
- Leaf 1: 10.0.0.1/32
- Leaf 2: 10.0.0.2/32
- ... (sequential through)
- Leaf 14: 10.0.0.14/32
- **Status**: ✅ No conflicts, proper sequential addressing

#### VLAN 100 Network (10.71.197.0/23)
- VRR VIP: 10.71.197.254/23 (shared across all leaves)
- Individual IPs: 10.71.197.253, 10.71.197.252, 10.71.197.251, etc.
- **Status**: ✅ Correct VRR configuration

#### VLAN 200 Network (10.71.195.0/24)
- VRR VIP: 10.71.195.254/24 (shared across all leaves)
- Individual IPs: 10.71.195.253, 10.71.195.252, 10.71.195.251, etc.
- **Status**: ✅ Correct VRR configuration

### 📋 **Recommendations**

#### 1. **Immediate Actions**
- **Verify Spine-Leaf Connectivity**: Ensure leaf switches are properly connected to spine switches on interfaces swp21-28
- **Test BGP Connectivity**: Verify BGP sessions are established between leaf and spine switches
- **Validate VRR Configuration**: Test VRR failover between leaf switches

#### 2. **Configuration Validation**
- **BFD Testing**: Verify BFD sessions are working properly for fast failure detection
- **EVPN Verification**: Confirm EVPN is properly advertising routes between switches
- **VRF Isolation**: Test that VRF RED traffic is properly isolated from management traffic

#### 3. **Monitoring and Maintenance**
- **BGP Monitoring**: Implement monitoring for BGP session status
- **Interface Monitoring**: Monitor interface utilization and errors
- **VRR Monitoring**: Monitor VRR status and failover events

### 🎯 **Summary**

**Overall Assessment**: The leaf switch configurations appear to be well-planned and properly implemented with no critical conflicts detected. The VRR configuration is correctly implemented for high availability.

**Key Findings**:
- ✅ No IP address conflicts
- ✅ Consistent BGP configuration with unique AS numbers
- ✅ Proper VRR configuration for high availability
- ✅ Correct VRF separation
- ⚠️ Need to validate actual connectivity and BGP session establishment
- ⚠️ Need to verify spine-leaf interconnection

**Confidence Level**: 90% - Configuration appears sound with proper VRR implementation, but requires validation of end-to-end connectivity.
