# v1.6.2 — Live-cluster validation plan

Validates every v1.6.2 fix on real clusters before the branch is committed, merged and version-bumped. Unit tests already cover each fix; this pass checks the parts that depend on real cluster layouts (EBox wrapper paths, `local.cfg`, `/vast/log`, burst-wait timing, cleanup).

Keep raw evidence (Output Results logs, bundles, PDFs, DIAG-1 output) local: it contains cluster data. Commit only a redacted summary to this folder.

## 0. Setup

**Clusters**

| Cluster | Purpose | Connection |
|---------|---------|------------|
| A — EBox (5.5 if possible) | FR-1, FR-4 skip path, FR-5, NET-6, HCF-2/7/8 | Tech Port (matches the field report) |
| B — CBox/DBox, Ethernet, switches registered in VMS | Regression: FR-1 legacy wrapper, FR-4 normal path, NET-6, SR-2 | VMS management or Tech Port |
| vperfsanity target (A, B or another lab cluster) | FR-2, FR-3 | Any. Needs a multi-hour window and room for temporary test data |

Cluster A should have **no switches registered in VMS** to exercise FR-4. If it has them, test the FR-4 skip path on any lab cluster without registered switches.

**Build and app settings**
1. Check out `fix/v1.6.2-field-feedback` (in a worktree if the workspace is on another branch) and run `python3 src/main.py --dev-mode`. Dev mode is needed for Advanced Ops and the Health Check page. The app still reports 1.6.1; that is expected.
2. Click **Update Tools** so vperfsanity and the support tools are current.
3. Set the Output Results log level to **Debug** for every run you keep as evidence.

**Baseline per cluster** (SSH to a CNode)
- Expected node count: `nodeset -c @cnodes`, `nodeset -c @dnodes`, and `nodeset -c @all`. If `nodeset` is missing, use `clush -g cnodes hostname | wc -l`. On a 12-EBox cluster all three are 12.
- Before vperfsanity: capacity used (VMS dashboard), and confirm there is no `/vperfsanity` view, no `vperfsanity` user, and no elbencho processes (`clush -a 'pgrep -fl elbencho'`).

## 1. UI checks — RPT-VALIDATION-1/2 (5 min)

1. Reporter: load a saved profile. **Expect:** Node User shows its value immediately, without clicking into the field.
2. With the profile loaded, turn **Autofill Passwords** off. **Expect:** fields unlock and the passwords stay filled.
3. Retype Node User. **Expect:** Node Password is still filled.

If PRs #36/#37 are merged into the test build: the Teleport option shows no Beta badge anywhere (Reporter, Docs, Quick Start), and the Dashboard "Before you begin" checklist ticks and keeps its state across a reload.

## 2. DIAG-1 probe (10 min per cluster)

The script talks to the API directly, so point it at the VMS management IP from a machine that can reach it (a Tech Port session alone is not enough).

```bash
read -rs VAST_PW   # keeps the password out of shell history
python3 scripts/diag_api_fields.py <vms-mgmt-ip> <api-user> "$VAST_PW"
```

**Expect:** one JSON dump per endpoint under `reports/`, highlighted serial / firmware / license / upgrade / capacity / RLR / strip keys, and sensitive-looking values redacted. Send back the key names (not values) to confirm fields for HCF-4, INV-2, DRV-1 and RCS-2–4.

## 3. Reporter run on A and B — INV-1, HCF-1/2/5/6/7, NET-6 (vnetmap) (20 min per cluster)

Enable the health check and vnetmap / port mapping, then generate the report.

**PDF**
- **INV-1:** Hardware Inventory has a separate **Serial** column with real serial numbers, not node names (the EBox-only table too). The CNode/DNode Management Map has a Serial column.
- **HCF-6:** the Health section shows detail sub-tables (alarms, inactive components, performance metrics), and only where there is data.
- **HCF-1:** Upgrade State no longer appears in Health Check results or the Cluster State & Software details (check removed).
- **HCF-5:** Performance Baseline either passes with a metrics sub-table or is skipped with "no performance metrics". It must not be an empty pass.
- **HCF-2 (A only):** CBox Status reads "Not applicable — converged EBox cluster (covered by EBox Status)"; DBox Status reads "All N EBox storage enclosures ACTIVE".
- **HCF-7:** Firmware Consistency passes on A, with "(reported in different formats: dnode.bios_version)" if the DNode containers report the BIOS differently. On B the result matches 1.6.1.

**Output Results (vnetmap)**
- **NET-6:** `[PARSED] cnodes (raw)` and `dnodes (raw)` cover every node from the baseline (A: one range for all 12 hosts). The **Expanded Values** list contains every host, with no duplicates.
- **FR-4 (cluster without switches in VMS):** "No switches registered in VMS; vnetmap needs switch IPs on Ethernet clusters". vnetmap is skipped, not reported as an authentication failure.

**Health Check page (dev mode):** the same results; detail rows expand into tables.

## 4. Test Suite on A (EBox, Tech Port) — FR-1, FR-4, FR-5, FR-6, NET-6, HCF-8 (30–45 min)

Select Health, Support Tools, Log Bundle, Network Extraction, Switch Config, vnetmap and Report. vperfsanity is tested separately in section 5.

- **HCF-8:** health lines read `[SKIP] CBox Status (n/N)` followed by the reason line. Search the downloaded log: there is no `[????]` anywhere.
- **FR-1 (Support Tools):**
  - The log shows "EBox container layout detected: using /vast/data/C-<port>/vms.sh".
  - Step 3 succeeds, and Step 4 finds the `support-checks` output and downloads the archive.
  - If anything goes wrong, **Step 3** must fail with the exit code and error. Failing only at Step 4 with "output directory not found" is the old bug.
- **NET-6 (Network Extraction):**
  - Step 1 lists every internal node from the baseline.
  - Known issue TP-3: in Tech Port mode the gateway is also listed under `192.168.2.2`, so the reported total is baseline + 1. That is expected for now.
  - Steps 2 and 3 return data for each node.
- **FR-4 (no switches in VMS):** Switch Config is SKIPPED with "No switches registered in VMS; add switches in VMS to enable switch extraction", and vnetmap is SKIPPED as in section 3. No vnetmap command runs with an empty `-s`, and there is no "Authentication failed on all N candidate switch password(s)".
- **FR-5 (Log Bundle):**
  - Step 3 lists each source as copied or missing, and copies recent `/vast/log` files (last 24 h, capped at 2 GB).
  - The archive downloads. Any missing source is named in "(partial: not collected …)".
  - On the CNode afterwards, `/tmp/vast_log_bundle` (the staging dir) is gone. The archive `/tmp/vast_log_bundle_*.tar.gz` is still there (known issue FR-11, v1.6.3).
  - **Decision point:** if `/var/log/vast` and `/var/log/syslog` are missing on every 5.x cluster, every bundle will say "partial". Report it, and we make those two sources optional before release.
- **FR-6:** download the validation bundle and inspect it (section 8).

## 5. vperfsanity full run — FR-2 (1–4 h)

Run only where a multi-hour test and large temporary writes are approved (lab, or a customer cluster with explicit approval).

1. **Expect in pre-validation:** "vperfsanity can take 1-4 hours on large clusters … cleaned up automatically".
2. Step 4 runs past 60 minutes with no "SSH command timed out after 3600s". The log shows writes, then the burst-recovery wait, then reads.
3. Step 5 collects results. Note what Step 6 reports: with no internet, it currently reports "Upload skipped" as success (tracked as HUB-7).
4. Step 7 cleanup runs. Then, on the cluster:
   - The `/vperfsanity` view and policy are gone.
   - The `vperfsanity` user is gone.
   - `clush -a 'pgrep -fl elbencho'` returns nothing.
   - Capacity returns to baseline, allowing for reclaim time.

## 6. vperfsanity forced failure and cancel — FR-3 (45 min)

Cancel is checked between steps, not inside Step 4 (FR-7/FR-15 address that later), so force a Step 4 failure instead.

1. Test Suite with only vperfsanity selected. Once Step 4 shows writes running (5–10 min in), open a separate SSH session on the CNode running it and run `pkill -f vperfsanity_run.sh`.
2. **Expect:**
   - Step 4 FAILED with an exit code and error.
   - "Running cleanup for 'vperfsanity' after … so no test artifacts remain on the cluster", then Step 7 runs.
   - The overall result shows "Step 4 (Run Performance Tests): …".
3. Verify the cluster is clean (same checks as section 5, step 4).
4. Repeat through **Advanced Ops → vperfsanity → Run All** with the same kill. **Expect:** cleanup runs. Single-step mode does not auto-clean; that is known.
5. Cancel path: start Run All and click **Cancel** during Step 3 (Prepare Infrastructure). **Expect:** once Step 3 finishes, cleanup runs and the cluster is clean.

## 7. Cluster B regression (CBox/DBox, switches in VMS) — FR-1, FR-4, NET-6, SR-2 (45 min)

Run the same Test Suite selection as section 4, plus the Reporter run from section 3.

- **FR-1:** Support Tools succeed with no "EBox container layout" line and no "wrapper not found" warning (the legacy `/vast/data/vms.sh` path).
- **FR-4:** Switch Config and vnetmap run normally. The vnetmap `-s` argument lists the switch IPs, and the report includes the port map and network diagram.
- **NET-6:** Network Extraction's node list matches the baseline, and every node returns config.
- **SR-2:** use a switch whose first password candidate is wrong (for example Onyx with a non-default password).
  - Status level shows no `[WARN]` per rejected candidate, and one line: "Authenticated <ip> as '<user>' with candidate N/M".
  - Debug level shows "Rejected candidate …" lines.

## 8. Bundle inspection — FR-6 (both clusters)

Unzip each validation bundle:
- `diagnostics/operation_log.jsonl` exists and contains the run's Output Results lines.
- In `manifest.json`, `manifest_version` is `1.4`, and `operation_details` has "Step N (name): message" for failed or skipped operations.
- FAILED/SKIPPED placeholder files (for example Switch Config on cluster A) name the step and the error and point to `diagnostics/operation_log.jsonl`.
- The statuses in `SUMMARY.md` match Output Results.
- The health JSON contains the HCF-6 details and the HCF-7 firmware result.

## 9. Exit criteria

- Every check passes or has an agreed disposition. The FR-5 "partial" decision point is resolved.
- Evidence (Debug logs, both bundles, both PDFs) is saved locally; a redacted summary is added here.
- Then: merge `develop` into the branch, commit, open the v1.6.2 PR, merge #36/#37, bump the version, release.

**Disposition (2026-10-16, owner):** the EBox cluster report was reviewed and came back clean (section 3
on cluster A). The owner accepted that result and waived the remaining sections (4–8) for v1.6.2. They are
covered by unit and regression tests and will be exercised on the next field runs; any finding is filed
against v1.6.3. The FR-5 "partial" decision stands as shipped: a missing source marks the archive partial.

**Known issues, not blockers:**
- TP-3: gateway counted twice in Tech Port mode.
- FR-11: remote archives left on the cluster.
- OBS-1: UTC and local times mixed in filenames.
- HUB-7: vperfsanity upload reporting.
- FR-15: Cancel inside long steps.
