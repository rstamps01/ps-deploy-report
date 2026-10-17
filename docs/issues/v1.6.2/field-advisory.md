# GOV-3 — Field advisory for VAST Reporter v1.6.1 users (draft)

**Status:** Draft, not posted. Post to the field Slack channel before v1.6.2 ships; update the "Fixed in" line with the release link once v1.6.2 is tagged.

The message below uses standard markdown (the Slack MCP message tools convert it). It names no customers or clusters; keep it that way.

---

**:warning: VAST Reporter v1.6.1: known issues in the post-deployment Test Suite, and what to do until v1.6.2**

If you ran the Test Suite (One-Shot) or Advanced Operations with **v1.6.1** on a deployment, check the items below. The as-built PDF/JSON report itself is not affected. Fixes ship in **v1.6.2**.

**1. vperfsanity can leave test data on the customer cluster** _(act on this one)_
- On large clusters the write + read test hit a 60-minute cap during the burst-recovery wait, and a failed or cancelled run skipped cleanup. One field run left about **53 TB** of test data plus the `vperfsanity` view, policy, user and elbencho services.
- **If any vperfsanity run failed, timed out or was cancelled**, run cleanup from a CNode:

```bash
cd /tmp/vast_scripts/vperfsanity
./vperfsanity_run.sh -c <vip-pool>
export ADMIN_USER='<admin user>' ADMIN_PASSWORD='<admin password>'
./vperfsanity_prepare.sh -c <vip-pool>
```

- If the directory is gone, re-run vperfsanity **Step 7 (Cleanup)** from Advanced Operations, or remove the `vperfsanity` view, view policy and user in VMS.
- On very large clusters (for example 40+ EBoxes) vperfsanity may stop in seconds with `HINT: Consider increasing the number of objects`. Skip vperfsanity there for now; v1.6.2 re-runs it automatically with a larger object count.

**2. Support Tools fail on every EBox cluster**
- Step 3 reports success and Step 4 fails with "output directory not found". The tool looks for `vms.sh` in the wrong place on EBox. Run the support tool manually or skip it on EBox until v1.6.2.

**3. Switch operations fail when switches are not registered in VMS**
- Switch Configuration and Ethernet vnetmap report "Authentication failed on all N candidate switch password(s)" even when the passwords are right. Register the switches in VMS first, or deselect the switch operations.

**4. Log Bundle reports OK but collects almost nothing on 5.x CNodes**
- The archive may contain only `/var/log/messages`. Collect `/vast/log` manually if you need logs.

**5. EBox clusters: Network Extraction and vnetmap can miss a node**
- Check the node count in Network Extraction against the cluster; v1.6.1 can drop one CNode on EBox clusters.

**6. Health Check Summary shows "Total 0"** _(cosmetic)_
- The Pass/Fail/Warning/Skipped counts are correct; only the Total column is wrong.

**Fixed in:** v1.6.2 (link when released). Questions or a run that doesn't match the above: reply in thread with the bundle's `SUMMARY.md` and `diagnostics/operation_log.jsonl` (v1.6.2) or the Output Results log.
