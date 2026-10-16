---
name: Status and roadmap gaps
overview: Status of every project plan with open todos, the current branch/PR/release state, and the items discussed this session that are missing from docs/TODO-ROADMAP.md or docs/DECISIONS.md, with a docs-only plan to close those gaps.
todos:
  - id: roadmap-hub-section
    content: Add Results Hub / field diagnostics section (HUB-1..23, DATA-1, FR follow-ups) to TODO-ROADMAP; mark UPL-1 superseded by HUB-10
    status: completed
  - id: roadmap-hygiene
    content: Fix Next steps line merge (items 2/3), refresh Execution status (main=develop=2ddda94), add governance items (redaction list, vperfsanity key notice, field advisory)
    status: completed
  - id: decisions-entries
    content: "Record approved decisions in DECISIONS.md: S3 presigned intake, hybrid topology, tiered collection, private triage store, MC relay delivery, PSNT+confirm account mapping"
    status: completed
  - id: plans-index-rebucket
    content: Re-bucket the 24 open-todo plans in PLANS-INDEX.md (active / tracked / stale-shipped) as PLN-1 starting point
    status: completed
  - id: plan-frontmatter-sync
    content: Tick completed Phase 1 todos in field_diagnostics_pipeline plan; run sync-cursor-plans.py and --check
    status: completed
  - id: bug-net3-localcfg
    content: "NET-6 (v1.6.2; NET-3 was already taken): local.cfg parsing drops nodes (duplicate keys overwrite; no comma/single-index brackets) - shared parser with ClusterShell union semantics used by Network Extraction and vnetmap; failing-first test with the field local.cfg"
    status: completed
  - id: bug-hcf7-firmware
    content: "HCF-7 (v1.6.2): Firmware Consistency false positive on equivalent BIOS strings ('2.90' vs 'A56 v2.90 (01/09/2026)') - normalize versions before comparing; failing-first test"
    status: completed
  - id: bug-hcf8-skipped-icon
    content: "HCF-8 (v1.6.2): skipped health checks print as [????] in Output Results (oneshot_runner icon maps lack skipped/info) - add [SKIP]; test"
    status: completed
  - id: track-remaining-bugs
    content: "Add to roadmap: OBS-1 mixed UTC/local artifact timestamps, TP-3 (TP-2 was already taken) mgmt IP discovery returns the Tech Port IP (investigate), FR-11 remote archives left on CNode/VMS; HWL-3 note (ask field for EBox height); SW-1 ask reporter for the ops log"
    status: completed
  - id: roadmap-stale-entries
    content: "Fix stale entries: TP-1 Done (shipped v1.5.7), close DOC-9, re-scope CFG-1 (template drift), dedupe UI-5 In progress/Planned, DOC-14 vs design-guidelines-01 referencing an empty docs/confluence/"
    status: completed
isProject: false
---

# Status snapshot and roadmap gap closure

## 1. Current state (2026-09-26)

- **Release:** v1.6.1 is the latest tag. `origin/main` = `origin/develop` = `2ddda94`: #35 (Gatekeeper note) merged, CI green.
- **Active branch:** `fix/v1.6.2-field-feedback`.
  - Changes are **uncommitted** (your hold). The branch is **2 commits behind** `develop`.
  - It contains DIAG-1, HCF-1/2/5/6, INV-1, SR-2, RPT-VALIDATION-1/2, FR-1..6, and the plan-archive and redaction updates.
  - Quality gate: 1757 passed, 70.47% coverage.
- **Open PRs:**
  - [#36](https://github.com/rstamps01/ps-deploy-report/pull/36) Teleport out of Beta: green, mergeable.
  - [#37](https://github.com/rstamps01/ps-deploy-report/pull/37) day-one checklist: conflict resolved, green, mergeable.
  - Dependabot #28/#30/#32 (minor), #29 (types-paramiko major, check with mypy), #31 (ReportLab 5, on hold).
- **Worktrees:** `vast-pr1-teleport-beta` and `vast-pr2-dashboard-dayone`. Remove them once their PRs merge (needs your approval).
- **Untouched by instruction:** dormant branches (`feature/pywebview`, `feature/health-check-v2`, `feature/tp-1-techport-discovery`, `feature/v1.5.8-batch`) and 2 stashes. Local `main`/`develop` refs are behind origin (a fast-forward only).
- **Verified:** [packaging/vast-reporter.spec](packaging/vast-reporter.spec) does not bundle `output/tools/`, so the vperfsanity tarball with its embedded upload keys is not shipped in the DMG.

## 2. Plans with open todos (24 of 94 in `docs/plans/MANIFEST.txt`)

**Genuinely open or active:**
- `field_diagnostics_pipeline_9b6d157c`: 38/39 pending in frontmatter, but Phase 1 is largely implemented on the branch.
  - Done: fix-ssh-timeout, fix-vperf-cleanup, fix-vnetmap-empty-s, fix-hcf1-not-uploaded, fix-placeholders, fix-logbundle-paths.
  - Partial:
    - fix-support-tools: node-count timeout scaling not done.
    - fix-vperfsanity: budget only; the runner is FR-7.
    - fix-switch-hostname: skip done; the manual-switch fallback is FR-8.
  - Not started: Phases 2-6.
- `expose_asbuilt-reporter_remotely`: tracked as OPS-1 ("confirm need").
- `agentic_cicd_pipeline`: the only open todo is the optional phase-2 patterns (dependency graph, next-actionable selector, fix-bug path). **Not tracked.**
- `protect_main_branch`: SEC-2 is done. The optional `develop` protection is **not tracked**.
- `switch_discovery_workflow`: the `field-styling` CSS task, which PLANS-INDEX says to fold into UI-5.

**Stale frontmatter (the work shipped; todos were never ticked; PLN-1 scope):**
- `field_feedback_triage`: all 5 done (roadmap section, DECISIONS, PR #34).
- `pre-release_cleanup`, `v1.5.8_release_prep`, `v1.5.8_release_batch`, `tech-port_stack_v1.5.7`, `pre-release_readiness_plan`: those releases shipped.
- `segment_results_by_psnt` (QP-2), `node_management_map_table` (QP-1), `ui_and_software_mgmt_enhancements` (QP-3; 2b deferred).
- `macos_intel_support`: arm64/x64 DMGs ship. `dashboard_mechanical_odometer`: shipped.
- `cnode_management_status_check`: HC-1, v1.5.0. `restore_atlassian_mcp`: the MCP works.
- `post_install_validation_gap_analysis`: bundling, tests and the CI job all exist.
- `bug_tracking_documentation_update`: BUG-1..6 are in ROADMAP-ARCHIVE.
- `nav_devmode_and_log_levels`: the remaining item is AO-20. `tp-1_fix_+_ui_investigation`: RPT-VALIDATION-1/2 are now fixed.
- `thread_handoff_prep`: handoff delivered. `api_health_check_report`: an operational one-off.

## 3. Discussed this session but not on the roadmap

**Results Hub and diagnostics** (plan Phases 2-6; only FR-1..10, RCS-1..5 and the old UPL-1 exist today). Proposed IDs:
- **v1.6.3, local only:**
  - HUB-1 installation ID.
  - HUB-2 run recorder: run_id, Output Results, steps, remote transcripts, environment, operator notes.
  - HUB-3 cluster capability probe.
  - HUB-4 cluster hygiene / residue check.
  - HUB-5 local results ledger with backfill.
  - HUB-6 Export Diagnostics UI and routes.
  - HUB-7 copy the vperfsanity artifacts to the laptop and report the `-U` upload honestly.
  - HUB-8 vperfsanity parser (shared with RCS-5).
  - HUB-9 rules analyzer and CI `diagnostics-rules` job.
- **v1.7.0:**
  - HUB-10 upload client: enrollment, outbox, Upload-now dialog, destinations, receipts, tracking keys. Supersedes UPL-1.
  - HUB-11 Tier-0 counts default-on, a policy change: TELEMETRY.md rewrite and Legal notice text.
- **Backend, separate repos:**
  - HUB-12 AWS intake (S3 / API Gateway / GuardDuty / SQS).
  - HUB-13 Mission Control hardening (HTTPS, SSO, backups, DB not exposed).
  - HUB-14 results DB, ingest worker, unzip and full-text index.
  - HUB-15 Grafana dashboards, including Total Results Generated and performance by hardware/network.
  - HUB-16 read API and tool access.
- **v1.7.x connectors:**
  - HUB-17 connector framework.
  - HUB-18 PSNT-to-SFDC-Account and Slack-channel mapping.
  - HUB-19 Slack connector.
  - HUB-20 SFDC connector.
  - HUB-21 vperfsanity DB relay.
  - HUB-22 LaunchPad (JSON schema contract, then an Integrated App push).
  - HUB-23 private triage plus the Cursor agent.
- **Also:** DATA-1, move the data directory to OS-standard locations (and migrate the installation ID).

**Small follow-ups from the FR work:**
- Remove the no-op vperfsanity `VAST_VMS` export and the test that pins it.
- Expose `vperfsanity_timeout_s` in config/UI, and add a "keep test data on failure" opt-out.
- Scale the support-tools inspect timeout by node count.
- Remove the log-bundle archive left in the CNode's `/tmp` after download.
- Make Cancel interrupt long steps other than vperfsanity. FR-7 covers vperfsanity only.

**Governance and ops:**
- Move the customer-name redaction patterns out of the public [scripts/sync-cursor-plans.py](scripts/sync-cursor-plans.py) into a gitignored local list.
- Tell the vperfsanity owner that the package embeds long-lived upload keys.
- Optional `develop` branch protection. Optional agentic phase-2 patterns.
- Field advisory for v1.6.1 users (EBox support tools, vperfsanity timeout/cleanup, switches in VMS): not yet drafted.
- <customer> follow-ups (operational, not roadmap):
  - Engineer cleanup confirmation.
  - The "3 hours" question.
  - NIC alarms and the IPv6 duplicate-address storm on VLAN 1262.
- Ross follow-ups: friendly-name table, 1-strip field name, RLR quantity semantics. Your message was sent; the replies feed RCS-1..4.

**Decisions approved but not recorded in DECISIONS.md:**
- Upload target: a VAST-owned AWS S3 intake using presigned URLs.
- Hybrid topology: S3 intake plus a Mission Control pull.
- Tiered collection policy.
- Private triage store before any public issue.
- Destination delivery via the Mission Control relay.
- PSNT lookup with engineer confirmation for Account/channel mapping.
- Teleport beta exit and Dashboard Approach C are recorded only on the PR #36/#37 branches (they land on merge).

**Roadmap hygiene defects:**
- In [docs/TODO-ROADMAP.md](docs/TODO-ROADMAP.md) Next steps, items 2 and 3 run together on one line ("SW-1 waits on logs.3.").
- The Execution status block is stale: it is dated 2026-09-25, says main = `2567eb6`, and still lists the #34 context.
- Next steps item 6 (Teleport beta exit) resolves when #36 merges.
- UPL-1 should point to HUB-10 / the plan.

## 3b. Outstanding bugs (roadmap review plus field-report evidence)

**New bugs confirmed from field-report evidence, not on the roadmap** (recommended for v1.6.2; small, with failing-first tests):
- **NET-6: `local.cfg` parsing drops nodes (P1).** (Proposed as NET-3, which was already in use.)
  - Network Extraction found 11 of 12 EBox hosts, and CNode `<ip>` was never collected (it appears in vperfsanity's clush list).
  - The field `local.cfg` repeats group keys (`cnodesub0`, `dnodesubN`). [src/workflows/network_config_workflow.py](src/workflows/network_config_workflow.py) `_parse_local_cfg` stores groups in a dict, so each later duplicate overwrites the earlier one. Its bracket regex `(.+)\[(\d+)-(\d+)\]` handles only a single range, not `[1-3,5]` or `[5]`.
  - Fix:
    - Expand on the CNode with ClusterShell (`nodeset -e @cnodes @dnodes`), keeping the parser only as a fallback.
    - Take the union of duplicate keys and support comma lists and single indexes in the parser.
    - Apply the same audit to vnetmap's `_parse_local_cfg` / `_convert_ip_format`.
- **HCF-7: Firmware Consistency false positive (P2).**
  - It flagged `dnode.bios_version` because the D-4000 containers report `2.90` and the D-4100 containers report `A56 v2.90 (01/09/2026)`, which is the same BIOS.
  - Fix: normalize version strings (extract the version token) before comparing in [src/health_checker.py](src/health_checker.py) `_check_firmware_consistency`.
- **HCF-8: skipped checks print as `[????]` (P3, cosmetic).**
  - Output Results showed `[????] CBox Status` and `[????] Switches in VMS`.
  - The icon maps in [src/oneshot_runner.py](src/oneshot_runner.py) (~L477, L1360, L1752) have no `skipped` entry; add `[SKIP]`.

**New bugs to track** (v1.6.3 unless noted):
- **OBS-1:** artifact timestamps mix UTC and local time. Health files are named `..._20260926_013125` (UTC) while the bundle and report use `..._20260925_183126` (local), which confuses correlation. Resolved by the recorder's UTC rule; the filenames still need a fix.
- **TP-3** (proposed as TP-2, which was already in use)**:** Tech Port discovery logged `management=192.168.2.2`, so it didn't resolve the VMS management IP. The tunnel worked, but downstream code that uses the management IP gets the Tech Port IP. Investigate.
- **FR-11:** remote archives are left behind: `/tmp/vast_log_bundle_*.tar.gz` on the CNode and `/userdata/*-support_tool_logs_*.tgz` on the VMS host. Remove them after download (cluster hygiene).

**Existing roadmap bugs still open:**
- **FR-10:** Windows SSH path has no deadline (v1.6.3).
- **HWL-3:** EBox 1U short-circuit. It needs the true EBox rack height; the field rack units (for example U16 and U18) are consistent with 2U. Ask the field for model and height.
- **SW-1:** awaiting logs. Now that we know where the ops log lives, ask the reporter for it (likely the FR-4/FR-8 family).
- **HCF-4:** a Trial license passes (v1.7.0).
- **SEC-3 / SEC-4:** deferred by decision.
- **RFE-12 / RFE-14:** deferred; they need reports.

**Stale roadmap entries:**
- TP-1 is still "Planned", but Tech Port auto-discovery shipped in v1.5.7 and worked in the field log.
- DOC-9 (v1.5.0 release notes) is still "Planned".
- CFG-1 has no status, and the template has drifted again (for example `vperfsanity_timeout_s`).
- UI-5 appears as both "In progress" and "Planned".
- DOC-14: `docs/confluence/` is empty, yet the always-applied rule `design-guidelines-01.mdc` references about 25 files there. Either run the sync or trim the rule.

## 4. Proposed docs-only changes (on the current branch, still uncommitted)

The three v1.6.2 bug fixes above (NET-6, HCF-7, HCF-8) are code changes, implemented with failing-first tests on the same branch (executed 2026-09-26).

- [docs/TODO-ROADMAP.md](docs/TODO-ROADMAP.md):
  - Add a "Planned — Results Hub and field diagnostics" section with HUB-1..23, DATA-1 and the FR follow-ups.
  - Mark UPL-1 as superseded by HUB-10.
  - Fix the Next steps formatting, refresh the Execution status, and add the governance items (redaction list, vperfsanity key notice, field advisory).
- [docs/DECISIONS.md](docs/DECISIONS.md): add Decision entries for the six approved Results Hub decisions (dated 2026-09-25/26, approver: user).
- [docs/PLANS-INDEX.md](docs/PLANS-INDEX.md): re-bucket the 24 open-todo plans as above, so PLN-1 starts from current data.
- Plan frontmatter: tick the completed Phase 1 todos in `field_diagnostics_pipeline_9b6d157c.plan.md`, then re-run `scripts/sync-cursor-plans.py` and `--check`.
- Leave stale-frontmatter plans for PLN-1. Do not delete anything, or touch branches or worktrees, without your approval.
