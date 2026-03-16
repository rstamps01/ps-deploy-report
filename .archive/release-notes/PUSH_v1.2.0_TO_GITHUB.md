# Push v1.2.0 Release to GitHub

## ✅ Completed Steps:
1. ✓ Merged develop into main (conflicts resolved)
2. ✓ Created v1.2.0 tag with release notes
3. ✓ Currently on main branch

## Next Steps - Run These Commands:

```bash
cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report

# Push main branch to GitHub
git push origin main

# Push v1.2.0 tag to GitHub
git push origin v1.2.0

# Switch back to develop branch
git checkout develop
```

## After Pushing to GitHub:

### Create GitHub Release
1. Go to: https://github.com/[your-username]/ps-deploy-report/releases/new
2. Select tag: `v1.2.0`
3. Release title: `v1.2.0 - Capacity Base 10 Display & Enhanced Port Mapping`
4. Description (copy this):

```markdown
# Release v1.2.0 - Capacity Base 10 Display Feature

## 🎯 Major Features

### Capacity-Base 10 Display
- Added **"Capacity-Base 10"** row to Cluster Overview table (Page 4)
  - Displays: "True" or "False" based on cluster configuration
- **Dynamic TB/TiB units** in Storage Capacity table (Page 5)
  - Shows "TB" when capacity_base_10 = True (base 10)
  - Shows "TiB" when capacity_base_10 = False (base 2)
- Applied to all capacity metrics: usable, physical, and logical space

### Enhanced Port Mapping
- Improved DNode Network B MAC address collection
- Fixed VLAN 69 interface handling
- Corrected SR-IOV virtual function MAC filtering
- Enhanced switch-based network assignment logic

### Network Diagram Improvements
- Fixed IPL connection display (4 connections, not 8)
- Improved DNode to Switch 2 connection rendering
- Corrected deduplication in network topology diagrams

### Watermark Enhancements
- Re-implemented watermark rendering on all pages except title
- Fixed watermark sizing to fit within page boundaries
- Maintained aspect ratio and positioning

## 🔧 API Changes
- Added `capacity_base_10` field collection from VMS API endpoint
- Implemented fallback query to VMS when clusters endpoint missing field
- Enhanced data flow: API Handler → Data Extractor → Report Builder

## 🐛 Bug Fixes
- Fixed MAC address parser to capture first physical MAC only
- Resolved SR-IOV virtual function MAC address issues
- Corrected network assignment to be switch-based (not interface-based)
- Fixed DNode connections missing from Switch 2 port mapping
- Resolved IPL deduplication in network topology diagrams
- Fixed watermark rendering issues

## 🔬 Technical Improvements
- VMS endpoint fallback for capacity_base_10 collection
- Improved MAC table parsing for VLAN subinterfaces
- Better handling of SR-IOV virtual functions
- Enhanced VLAN 69-specific MAC table collection
- Switch-based network assignment logic

## ✅ Testing
Tested on production clusters:
- **10.143.15.203 (tmphx-203)**: capacity_base_10 = False → TiB units ✓
- **10.143.15.204 (tmphx-204)**: capacity_base_10 = False → TiB units ✓

Both clusters generated successfully with:
- ✓ Port mapping tables (Switch 1 & 2)
- ✓ Network topology diagrams
- ✓ IPL connections
- ✓ Capacity-Base 10 row display
- ✓ Dynamic capacity units
- ✓ Watermark rendering

## 📦 Installation

Download the latest release and follow the installation guide in the README.

## 🔄 Upgrade from v1.1.0

No breaking changes. Simply pull the latest code and reinstall dependencies:

```bash
git pull origin main
pip install -r requirements.txt
```

## 📊 Commits Included

This release includes 20+ commits from the develop branch:
- Capacity-Base 10 feature implementation
- Port mapping accuracy improvements
- Network diagram enhancements
- Watermark rendering fixes
- MAC address collection improvements

## 🙏 Notes

This release focuses on improving report accuracy and adding the highly requested Capacity-Base 10 display feature. Reports now correctly reflect whether a cluster is using base-10 (TB) or base-2 (TiB) capacity reporting.
```

5. Click **"Publish release"**

## Verification Commands:

After pushing, verify the release:

```bash
# Check remote tags
git ls-remote --tags origin

# Verify main branch is pushed
git fetch origin main
git log origin/main -1

# Verify you're back on develop
git branch --show-current
```

## Summary of Changes

### Files Modified (22):
- src/api_handler.py
- src/data_extractor.py
- src/report_builder.py
- src/external_port_mapper.py
- src/network_diagram.py
- src/brand_compliance.py
- src/rack_diagram.py
- .gitignore
- Plus documentation and asset files

### New Features:
1. Capacity-Base 10 display on Cluster Overview table
2. Dynamic TB/TiB units based on cluster configuration
3. Enhanced port mapping for DNode Network B
4. Improved watermark rendering
5. Fixed IPL connection display

### Bug Fixes:
- MAC address collection for SR-IOV interfaces
- DNode Network B port mapping accuracy
- IPL connection deduplication
- Watermark sizing and positioning
- Network assignment logic

---

**Ready to push!** Run the commands above to complete the v1.2.0 release.
