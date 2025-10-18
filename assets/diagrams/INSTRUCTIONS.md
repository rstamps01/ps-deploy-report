# How to Add the Network Topology Diagram

## Quick Steps

1. **Save the network topology image** from your message/attachment as:
   ```
   network_topology_placeholder.png
   ```

2. **Place it in this directory**:
   ```
   /Users/ray.stamps/Documents/as-built-report/ps-deploy-report/assets/diagrams/
   ```

3. **Regenerate the report**:
   ```bash
   cd /Users/ray.stamps/Documents/as-built-report/ps-deploy-report
   python3 -m src.main --cluster-ip 10.143.11.204 --username support --password 654321
   ```

4. **Check Page 8** of the generated report to see your network topology diagram!

---

## What the Diagram Shows

The network topology diagram illustrates:
- **CBox-1, CBox-2, CBox-3, CBox-4** (Blue) - Compute nodes
- **DBox-100, DBox-101, DBox-102, DBox-103** (Green) - Data nodes
- **Switch A** (Red) - Primary network switch with customer network connection
- **Switch B** (Orange) - Secondary network switch
- **Customer Network** (Cloud) - External network connectivity
- **Network connections** color-coded by switch
- **Inter-switch links** (Black) - Redundant switch interconnection

---

## Report Section Details

**Section**: Logical Network Diagram (Page 8)
**Title**: Placeholder
**Description**: Provides visual representation of cluster network topology

---

## If You Need Help

If the image doesn't appear in the report:
1. Verify filename is exactly: `network_topology_placeholder.png`
2. Check file is in: `assets/diagrams/` directory
3. Run: `ls -la assets/diagrams/*.png` to confirm
4. Review report generation logs for any errors

The report will show a placeholder box if the image file is not found.
