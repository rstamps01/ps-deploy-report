# Port Mapping Solution - Spine-Leaf Configuration Fix

## Current Configuration Analysis

### Spine Switch Configuration
- **Ports Used**: swp1-28 (28 ports)
- **Connections**: 14 leaf switches
- **Mapping**: 2 ports per leaf switch (28 ÷ 14 = 2)

### Leaf Switch Configuration
- **Ports Used**: swp21-28 (8 ports)
- **Connections**: 4 spine switches
- **Mapping**: 2 ports per spine switch (8 ÷ 4 = 2)

## The Mismatch Problem

### Current Spine Config
```bash
nv set vrf default router bgp neighbor swp1-28 peer-group eBGP
nv set vrf default router bgp neighbor swp1-28 type unnumbered
```

### Current Leaf Config
```bash
nv set vrf default router bgp neighbor swp21-28 peer-group eBGP
nv set vrf default router bgp neighbor swp21-28 type unnumbered
```

**Problem**: Spine expects connections on swp1-28, but leaves are configured to connect on swp21-28.

## Solution Options

### Option 1: Update Leaf Configuration (RECOMMENDED)
Change leaf switches to use swp1-8 instead of swp21-28:

```bash
# Remove current configuration
nv unset vrf default router bgp neighbor swp21-28 peer-group eBGP
nv unset vrf default router bgp neighbor swp21-28 type unnumbered

# Add new configuration
nv set vrf default router bgp neighbor swp1-8 peer-group eBGP
nv set vrf default router bgp neighbor swp1-8 type unnumbered
```

**Physical Cabling**:
- Spine swp1-28 ↔ Leaf swp1-8
- Each leaf uses 2 ports per spine (8 ports ÷ 4 spines = 2 ports per spine)

### Option 2: Update Spine Configuration
Change spine switches to use swp21-28 instead of swp1-28:

```bash
# Remove current configuration
nv unset vrf default router bgp neighbor swp1-28 peer-group eBGP
nv unset vrf default router bgp neighbor swp1-28 type unnumbered

# Add new configuration
nv set vrf default router bgp neighbor swp21-28 peer-group eBGP
nv set vrf default router bgp neighbor swp21-28 type unnumbered
```

**Physical Cabling**:
- Spine swp21-28 ↔ Leaf swp21-28
- Each spine uses 7 ports per leaf (28 ports ÷ 14 leaves = 2 ports per leaf)

## Recommended Solution: Option 1

### Why Option 1 is Better
1. **Minimal Changes**: Only need to update leaf configurations
2. **Logical Port Usage**: Leaves use swp1-8 for spine connections (logical)
3. **Consistent with Design**: Leaves use swp1-20 for servers, swp1-8 for spines
4. **Easier Implementation**: 14 leaf switches vs 4 spine switches

### Updated Leaf Configuration

#### For Each Leaf Switch (14 switches)
```bash
# Remove current BGP neighbor configuration
nv unset vrf default router bgp neighbor swp21-28 peer-group eBGP
nv unset vrf default router bgp neighbor swp21-28 type unnumbered

# Add new BGP neighbor configuration
nv set vrf default router bgp neighbor swp1-8 peer-group eBGP
nv set vrf default router bgp neighbor swp1-8 type unnumbered

# Update interface configuration
nv set interface swp1-8 type swp
nv set interface swp9-20 bridge domain br_default
nv set interface swp9-20 qos pfc-watchdog
nv set interface swp21-28 type swp
```

### Physical Cabling Plan

#### Spine Switch 1 (10.1.0.1)
- swp1-2 → Leaf 1 (10.0.0.1) swp1-2
- swp3-4 → Leaf 2 (10.0.0.2) swp1-2
- swp5-6 → Leaf 3 (10.0.0.3) swp1-2
- swp7-8 → Leaf 4 (10.0.0.4) swp1-2
- swp9-10 → Leaf 5 (10.0.0.5) swp1-2
- swp11-12 → Leaf 6 (10.0.0.6) swp1-2
- swp13-14 → Leaf 7 (10.0.0.7) swp1-2
- swp15-16 → Leaf 8 (10.0.0.8) swp1-2
- swp17-18 → Leaf 9 (10.0.0.9) swp1-2
- swp19-20 → Leaf 10 (10.0.0.10) swp1-2
- swp21-22 → Leaf 11 (10.0.0.11) swp1-2
- swp23-24 → Leaf 12 (10.0.0.12) swp1-2
- swp25-26 → Leaf 13 (10.0.0.13) swp1-2
- swp27-28 → Leaf 14 (10.0.0.14) swp1-2

#### Spine Switch 2 (10.1.0.2)
- swp1-2 → Leaf 1 (10.0.0.1) swp3-4
- swp3-4 → Leaf 2 (10.0.0.2) swp3-4
- ... (same pattern for all 14 leaves)

#### Spine Switch 3 (10.1.0.3)
- swp1-2 → Leaf 1 (10.0.0.1) swp5-6
- swp3-4 → Leaf 2 (10.0.0.2) swp5-6
- ... (same pattern for all 14 leaves)

#### Spine Switch 4 (10.1.0.4)
- swp1-2 → Leaf 1 (10.0.0.1) swp7-8
- swp3-4 → Leaf 2 (10.0.0.2) swp7-8
- ... (same pattern for all 14 leaves)

### Port Usage Summary

#### Leaf Switch Port Usage (After Fix)
- **swp1-8**: Spine connections (2 ports per spine × 4 spines = 8 ports)
- **swp9-20**: Server connections (12 ports)
- **swp21-28**: Unused (8 ports available for future expansion)

#### Spine Switch Port Usage (No Change)
- **swp1-28**: Leaf connections (2 ports per leaf × 14 leaves = 28 ports)
- **swp29-48**: Unused (20 ports available for future expansion)
- **swp49-56**: VAST cluster connections (8 ports)
- **swp57-64**: Unused (8 ports available for future expansion)

## Implementation Steps

### 1. Update Leaf Configurations
For each of the 14 leaf switches, run:
```bash
# Connect to each leaf switch and run:
nv unset vrf default router bgp neighbor swp21-28 peer-group eBGP
nv unset vrf default router bgp neighbor swp21-28 type unnumbered
nv set vrf default router bgp neighbor swp1-8 peer-group eBGP
nv set vrf default router bgp neighbor swp1-8 type unnumbered
nv set interface swp1-8 type swp
nv set interface swp9-20 bridge domain br_default
nv set interface swp9-20 qos pfc-watchdog
nv config apply -y
nv config save
```

### 2. Verify Physical Cabling
Ensure cables are connected according to the mapping above.

### 3. Test BGP Sessions
Verify BGP sessions establish between spines and leaves:
```bash
# On spine switches
nv show vrf default router bgp neighbor

# On leaf switches
nv show vrf default router bgp neighbor
```

## Expected Results

After implementing this fix:
- ✅ BGP sessions will establish between spines and leaves
- ✅ Each leaf will have 2 connections to each spine (8 total)
- ✅ Each spine will have 2 connections to each leaf (28 total)
- ✅ Network will function as designed
- ✅ Excellent redundancy and performance

## Summary

**Recommended Action**: Update all 14 leaf switches to use swp1-8 for spine connections instead of swp21-28.

**Result**: Perfect alignment between spine and leaf configurations with excellent redundancy (2 connections per spine-leaf pair).
