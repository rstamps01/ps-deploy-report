# Release v1.2.0 - Commands to Execute

## Step 1: Push develop branch to GitHub
```bash
cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report
git push origin develop
```

## Step 2: Checkout main branch and merge develop
```bash
git checkout main
git pull origin main
git merge develop --no-ff -m "Merge develop into main for v1.2.0 release"
```

## Step 3: Create and push v1.2.0 tag
```bash
git tag -a v1.2.0 -m "Release v1.2.0 - Capacity Base 10 Display Feature

Major Features:
- Added Capacity-Base 10 row to Cluster Overview table (Page 4)
- Dynamic TB/TiB units in Storage Capacity table based on cluster setting
- Improved port mapping accuracy for DNodes on Network B
- Enhanced watermark rendering
- Fixed IPL connection display in port mapping tables

API Changes:
- Added capacity_base_10 field collection from VMS API endpoint
- Fallback query to VMS when clusters endpoint missing capacity_base_10

Bug Fixes:
- Fixed MAC address collection for interfaces with SR-IOV virtual functions
- Fixed DNode Network B port mapping on Switch 2
- Corrected IPL connection deduplication in network diagrams
- Fixed watermark sizing to fit within page boundaries

Data Flow:
- API Handler -> Data Extractor -> Report Builder
- VMS endpoint query for capacity_base_10 configuration
- Dynamic unit display (TB vs TiB) based on setting"

git push origin v1.2.0
git push origin main
```

## Step 4: Create GitHub Release
Go to GitHub repository and create a new release:
- Tag: `v1.2.0`
- Title: `v1.2.0 - Capacity Base 10 Display & Enhanced Port Mapping`
- Description: Use the tag message content above

## Step 5: Switch back to develop branch
```bash
git checkout develop
```

## Summary of Changes in v1.2.0

### New Features
1. **Capacity-Base 10 Display**
   - Added "Capacity-Base 10" row to Cluster Overview table showing True/False
   - Storage Capacity table dynamically displays TB (base 10) or TiB (base 2)
   - Applied to all capacity metrics: usable, physical, and logical space

2. **Enhanced Port Mapping**
   - Improved DNode Network B MAC address collection
   - Fixed VLAN 69 interface handling
   - Corrected SR-IOV virtual function MAC filtering

3. **Network Diagram Improvements**
   - Fixed IPL connection display (4 connections, not 8)
   - Improved DNode to Switch 2 connection rendering
   - Corrected switch-based network assignment logic

4. **Watermark Enhancements**
   - Re-implemented watermark rendering on all pages except title
   - Fixed watermark sizing to fit within page boundaries
   - Maintained aspect ratio and positioning

### Bug Fixes
- Fixed MAC address parser to capture first physical MAC only
- Corrected network assignment to be switch-based (not interface-based)
- Fixed IPL deduplication in network topology diagrams
- Resolved DNode connections missing from Switch 2 port mapping

### Technical Improvements
- VMS endpoint fallback for capacity_base_10 collection
- Enhanced data flow: API Handler → Data Extractor → Report Builder
- Improved MAC table parsing for VLAN subinterfaces
- Better handling of SR-IOV virtual functions

### Commits Included (20 total)
- e6dd1d3: Simplify Capacity-Base 10 display to True/False
- 7a2496a: Include capacity_base_10 in get_all_data() serialization
- 3f74ff4: Query VMS endpoint for capacity_base_10 fallback
- 82e56f4: Add Capacity-Base 10 feature with dynamic units
- 9b7d27b: Fix MAC collection for SR-IOV interfaces
- 22727c6: Add VLAN 69-specific MAC table collection
- 3f3436b: Adjust watermark to fit page width
- 71ca2db: Re-add watermark rendering
- bfb04ec: Add IPL connections to Switch 2 table
- ... and 11 more commits

### Testing
Tested on clusters:
- 10.143.15.203 (tmphx-203): capacity_base_10 = False → TiB units ✓
- 10.143.15.204 (tmphx-204): capacity_base_10 = False → TiB units ✓

Both clusters generated successfully with:
- Port mapping tables (Switch 1 & 2)
- Network topology diagrams
- IPL connections
- Capacity-Base 10 row display
- Dynamic capacity units
