# Spine Configuration Update - Fix Port Mapping

## Current Configuration Analysis

### Spine Switch Configuration (NEEDS UPDATE)
- **Current**: swp1-28 for leaf connections
- **Should Be**: swp21-28 for leaf connections
- **Reason**: Leaf switches are configured to use swp21-28

### Leaf Switch Configuration (NO CHANGE)
- **Current**: swp21-28 for spine connections ✅
- **Keep As**: swp21-28 for spine connections ✅

## Solution: Update Spine Configuration

### Current Spine Config (WRONG)
```bash
nv set vrf default router bgp neighbor swp1-28 peer-group eBGP
nv set vrf default router bgp neighbor swp1-28 type unnumbered
```

### Updated Spine Config (CORRECT)
```bash
# Remove current configuration
nv unset vrf default router bgp neighbor swp1-28 peer-group eBGP
nv unset vrf default router bgp neighbor swp1-28 type unnumbered

# Add new configuration
nv set vrf default router bgp neighbor swp21-28 peer-group eBGP
nv set vrf default router bgp neighbor swp21-28 type unnumbered
```

## Physical Cabling Plan

### Spine Switch 1 (10.1.0.1)
- swp21-22 → Leaf 1 (10.0.0.1) swp21-22
- swp23-24 → Leaf 2 (10.0.0.2) swp21-22
- swp25-26 → Leaf 3 (10.0.0.3) swp21-22
- swp27-28 → Leaf 4 (10.0.0.4) swp21-22
- swp29-30 → Leaf 5 (10.0.0.5) swp21-22
- swp31-32 → Leaf 6 (10.0.0.6) swp21-22
- swp33-34 → Leaf 7 (10.0.0.7) swp21-22
- swp35-36 → Leaf 8 (10.0.0.8) swp21-22
- swp37-38 → Leaf 9 (10.0.0.9) swp21-22
- swp39-40 → Leaf 10 (10.0.0.10) swp21-22
- swp41-42 → Leaf 11 (10.0.0.11) swp21-22
- swp43-44 → Leaf 12 (10.0.0.12) swp21-22
- swp45-46 → Leaf 13 (10.0.0.13) swp21-22
- swp47-48 → Leaf 14 (10.0.0.14) swp21-22

### Spine Switch 2 (10.1.0.2)
- swp21-22 → Leaf 1 (10.0.0.1) swp23-24
- swp23-24 → Leaf 2 (10.0.0.2) swp23-24
- ... (same pattern for all 14 leaves)

### Spine Switch 3 (10.1.0.3)
- swp21-22 → Leaf 1 (10.0.0.1) swp25-26
- swp23-24 → Leaf 2 (10.0.0.2) swp25-26
- ... (same pattern for all 14 leaves)

### Spine Switch 4 (10.1.0.4)
- swp21-22 → Leaf 1 (10.0.0.1) swp27-28
- swp23-24 → Leaf 2 (10.0.0.2) swp27-28
- ... (same pattern for all 14 leaves)

## Implementation Steps

### 1. Update Spine Configurations
For each of the 4 spine switches, run:

```bash
# Connect to each spine switch and run:
nv unset vrf default router bgp neighbor swp1-28 peer-group eBGP
nv unset vrf default router bgp neighbor swp1-28 type unnumbered
nv set vrf default router bgp neighbor swp21-28 peer-group eBGP
nv set vrf default router bgp neighbor swp21-28 type unnumbered
nv config apply -y
nv config save
```

### 2. Verify Physical Cabling
Ensure cables are connected according to the mapping above:
- Spine swp21-48 ↔ Leaf swp21-28
- Each leaf uses 2 ports per spine (8 ports ÷ 4 spines = 2 ports per spine)
- Each spine uses 2 ports per leaf (28 ports ÷ 14 leaves = 2 ports per leaf)

### 3. Test BGP Sessions
Verify BGP sessions establish between spines and leaves:
```bash
# On spine switches
nv show vrf default router bgp neighbor

# On leaf switches
nv show vrf default router bgp neighbor
```

## Port Usage Summary

### Spine Switch Port Usage (After Fix)
- **swp1-20**: Unused (20 ports available for future expansion)
- **swp21-48**: Leaf connections (2 ports per leaf × 14 leaves = 28 ports)
- **swp49-56**: VAST cluster connections (8 ports)
- **swp57-64**: Unused (8 ports available for future expansion)

### Leaf Switch Port Usage (No Change)
- **swp1-20**: Server connections (20 ports)
- **swp21-28**: Spine connections (2 ports per spine × 4 spines = 8 ports)
- **swp29-32**: Unused (4 ports available for future expansion)

## Expected Results

After implementing this fix:
- ✅ BGP sessions will establish between spines and leaves
- ✅ Each leaf will have 2 connections to each spine (8 total)
- ✅ Each spine will have 2 connections to each leaf (28 total)
- ✅ Network will function as designed
- ✅ Excellent redundancy and performance

## Summary

**Action Required**: Update all 4 spine switches to use swp21-28 for leaf connections instead of swp1-28.

**Leaf Switches**: No changes needed - keep using swp21-28 for spine connections.

**Result**: Perfect alignment between spine and leaf configurations with excellent redundancy (2 connections per spine-leaf pair).
