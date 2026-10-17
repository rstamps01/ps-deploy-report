# TODO & Roadmap — Planned Features and Enhancements

**Purpose:** Canonical **live** register of planned and in-progress work. Completed history lives in [`ROADMAP-ARCHIVE.md`](ROADMAP-ARCHIVE.md); shipped detail is in [`../CHANGELOG.md`](../CHANGELOG.md); the current point-in-time snapshot is in [`PROJECT-STATUS.md`](PROJECT-STATUS.md). Validated in CI (todo-tracking-09).

**Last updated:** 2026-10-16 — **v1.6.2 prepared for release** on `fix/v1.6.2-field-feedback`: version 1.6.2, CHANGELOG folded, [release notes](releases/RELEASE_NOTES_v1.6.2.md), QA plan §4 delta, update-pill dry run for 1.6.1 → 1.6.2. Live validation: EBox report clean, remaining live-test sections waived by the owner. Product renamed to asbuilt-reporter in visible text; in-app guides and marketing refreshed. Contents: DIAG-1, HCF-1/2/5/6/7/8, INV-1, SR-2, RPT-VALIDATION-1/2, NET-6, FR-1–6, FR-12, GOV-1, RPT-LAYOUT-1, RPT-TITLE-1, RACK-1/2/3, HWL-3, Turin 2U EBox. TP-4 (Results filter mixes Tech Port clusters) logged for v1.6.3. **v1.6.1 shipped** (tag on `7095ccb`). See [`DECISIONS.md`](DECISIONS.md).

**Reference:** [PRE-RELEASE-QA-GAP-ANALYSIS.md](PRE-RELEASE-QA-GAP-ANALYSIS.md) (feature coverage and recommendations)

---

## Status key

| Status   | Meaning |
|----------|--------|
| Planned  | Not started; agreed as next or future work |
| In progress | Actively being worked on |
| Done     | Completed (move to CHANGELOG / release notes and archive in `ROADMAP-ARCHIVE.md`) |
| Deferred | Postponed; reason and target release noted |

### Work-item state machine

The autonomous delivery loop (see `.cursor/skills/deliver-autonomously` + `project-manager`) drives each tracked item through a canonical lifecycle. The table statuses above are the human-facing summary; the machine states are:

```
draft ──▶ ready-for-dev ──▶ in-progress ──▶ in-review ──▶ done
                                │                │
                                └──────▶ blocked ◀┘
```

| State | Meaning | Enters via | Leaves via |
|-------|---------|------------|------------|
| `draft` | Captured, not yet scoped/agreed | `intake-feature` | scoped + approved → `ready-for-dev` |
| `ready-for-dev` | Scoped, prioritized, unblocked | approval | `start-work` → `in-progress` |
| `in-progress` | Branch open, implementation underway | `start-work` | gate + PR → `in-review` |
| `in-review` | PR open / review + quality gate running | `open-pr` | approve/merge → `done`; changes → `in-progress` |
| `done` | Merged (and released where applicable) | merge | archived to `ROADMAP-ARCHIVE.md` |
| `blocked` | Waiting on a dependency/decision/escalation | any state | resolution → prior state |

Mapping to the summary key: `draft`/`ready-for-dev` → **Planned**; `in-progress`/`in-review` → **In progress**; `done` → **Done**; `blocked` → **Deferred** (with reason).

---

## Planned — Pipeline & ops follow-ups (2026-07-31)

*Source: prior-plan reconciliation (see [`PLANS-INDEX.md`](PLANS-INDEX.md), Bucket D). Genuinely-open items surfaced from `~/.cursor/plans/` that are in-scope for this repo.*

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| SEC-2 | **Enable GitHub branch protection on `main`.** Aligns with `change-control-07`. | Medium | **Done** (2026-08-01) | Applied via API (admin-bypass policy): required checks `quality-gate`, `unit-tests (3.11/3.12)`, `integration-tests`; `enforce_admins:false` keeps the `develop`→`main` release merge working for admins; force-push + deletion disabled. From plan `protect_main_branch_1260e0f8`. |
| OPS-1 | **Remote access to the reporter app (Windows `netsh portproxy`).** Document/support exposing the local Flask UI to a remote operator via a Windows port-proxy hop, for field machines where the browser runs elsewhere. | Low | Planned (confirm need) | From plan `expose_asbuilt-reporter_remotely_8b7d907f`. Confirm this is still needed before implementing. |
| SEC-3 | **Cluster profiles store credentials in plaintext.** `config/cluster_profiles.json` holds saved passwords and API tokens unencrypted on disk. | Medium | Deferred (documented) | Surfaced while rewriting `DEPLOYMENT.md` for v1.6.1 and documented there as a caveat. Deferred by decision on 2026-08-01: encrypting it needs a key-storage decision and a migration path for existing profiles, neither of which should ride along in a patch release. |
| SEC-4 | **`/validation-results` is not behind the Developer Mode guard.** `architecture-03` lists the route as Developer-Mode-only, but it is reachable in a normal session. | Low | Deferred (documented) | Surfaced during the v1.6.1 docs audit. Deferred by decision on 2026-08-01: gating it now would withdraw access someone may be relying on, so confirm nobody depends on it first, then either gate the route or correct `architecture-03`. |
| HWL-2 | **Library entries could not outrank broad built-in vendor keys.** Height and image lookups searched the built-in catalog to exhaustion before the user Library, so a bare vendor key (`hpe`) claimed a specific user device (`hpe_turin_cbox`) and rendered it at the wrong U-height, stretching its artwork. | High | **Done** (shipped v1.6.1) | Both catalogs are now matched as one namespace, longest key first. [PR #24](https://github.com/rstamps01/ps-deploy-report/pull/24). Regression suite in `tests/test_hardware_library.py`. |
| HWL-3 | **`ebox`/`enclosure` short-circuit overrides declared U-heights.** `get_device_height` returns 1U for any model containing `ebox` before consulting either catalog, so the built-in `supermicro_milan_ebox` and `smc_milan_ebox` (both declared 2U) render at 1U, and no Library entry can set a 2U EBox. | Medium | Done (branch) | 2026-10-16 (v1.6.2, approved): a model matched to an EBox catalog entry (built-in or Library) uses its declared height; 1U stays the default only for unknown EBoxes or ones that hit a vendor fallback such as `hpe`. Milan EBoxes now draw at 2U, matching the field report's U16/U18 positions. Tests in `tests/test_hardware_library.py::TestEboxHeights`. |
| HWL-4 | **HPE Gen6 Turin CBox missing from the built-in catalog.** VMS reports `hpe_turin_cbox`; Dell and SMC Turin were already catalogued. Uncatalogued it fell to the `hpe` 2U fallback. | High | **Done** (shipped v1.6.1) | Added at 1U with bundled artwork. [PR #26](https://github.com/rstamps01/ps-deploy-report/pull/26). |
| GOV-1 | **Customer names in the public plan-sync script.** `scripts/sync-cursor-plans.py` lists the customer names it redacts, which publishes them. | Medium | Done (branch) | 2026-10-16: customer patterns moved to the gitignored `config/redact-patterns.local.txt` (template committed); syncing refuses to write without it. Customer and cluster names scrubbed from `src/`, `tests/` and `scripts/`. Remaining: older docs (CHANGELOG history, roadmap, archived plans, NET-2 mockups) and git history still name them; a history rewrite needs a force-push and is a separate decision. |
| GOV-2 | **vperfsanity package embeds long-lived upload keys.** | Medium | Planned | Notify the vperfsanity owner. Never reuse the keys; HUB-21 replaces the upload path. The keys are not bundled in the DMG (`output/tools/` is not packaged). |
| GOV-3 | **Field advisory for v1.6.1 users.** EBox Support Tools, vperfsanity timeout and cleanup, switches missing from VMS. | Medium | In progress | Drafted 2026-10-16: [`issues/v1.6.2/field-advisory.md`](issues/v1.6.2/field-advisory.md). Post to Slack before v1.6.2 ships, then add the release link. |
| SEC-5 | **Optional branch protection on `develop`.** | Low | Planned | Follow-up to SEC-2 (plan `protect_main_branch_1260e0f8`). |
| PIPE-1 | **Optional agentic pipeline phase-2 patterns:** dependency graph, next-actionable selector, fix-bug path. | Low | Planned | From plan `agentic_cicd_pipeline`. |
| PLN-1 | **Audit the project plan archive.** Re-check every plan in [`plans/`](plans/README.md) against `CHANGELOG.md` and release tags. Re-bucket each as A–D in [`PLANS-INDEX.md`](PLANS-INDEX.md), mark stale frontmatter as done in the archived copies, and move any genuine open work into this roadmap. Then call `scripts/sync-cursor-plans.py --check` from the `update-tracker` skill so new plans don't go untracked. | Medium | Planned | The archive was created 2026-09-25. The last reconciliation was 2026-07-31. |

---

## Planned — Field feedback (2026-09-23)

*Source: field feedback on v1.6.x (health check output, node identity, drive firmware). The triage plan with the full assessment is archived at [`plans/field_feedback_triage_1d3ae704.plan.md`](plans/field_feedback_triage_1d3ae704.plan.md). Accepted 2026-09-25; decisions are in [`DECISIONS.md`](DECISIONS.md).*

One root cause runs through several of the health check items: `HealthCheckResult.details` is collected but never shown, in either the PDF (`_create_health_check_section`) or `health.html`. HCF-6 fixes that and unblocks HCF-3 and HCF-5.

| ID | Item | Type | Priority | Size | Target | Status | Notes |
|------|------|------|----------|------|--------|--------|--------|
| DIAG-1 | **Live API field probe.** `scripts/diag_api_fields.py`, following the `tests/diag_prometheus_metrics.py` pattern, dumps the keys of `cnodes/`, `dnodes/`, `ssds/`, `nvrams/`, `licenses/` and `clusters/` (upgrade and license fields) from a lab cluster. | Enabler | P1 | S | v1.6.2 | Done (script) | Script added; live lab run still needs operator credentials. Unblocks HCF-4, INV-2 and DRV-1. |
| HCF-1 | **Upgrade State reports "UNKNOWN" as a warning.** `_check_upgrade_state` passes only `""`/`NONE`/`NULL`/`DONE`, so the idle value `UNKNOWN` warns. | Bug | P1 | S | v1.6.2 | Done (check removed) | Initially fixed by treating `UNKNOWN` as idle. On 2026-10-15 the check was removed: VMS reports `UNKNOWN` on idle clusters, so it carried no signal. Its row is dropped from the Cluster State & Software group. |
| HCF-2 | **EBox cluster shows CBox skipped while DBox and EBox pass.** Each check is right on its own (`dboxes/` returns the EBox enclosures and `cboxes/` is empty), but the report never explains the topology. | Bug (misleading output) | P2 | S | v1.6.2 | Done | Detect an EBox cluster once. CBox then reads "Not applicable — converged EBox cluster" and DBox reads "All N EBox storage enclosures ACTIVE". Status values don't change. |
| HCF-5 | **Performance Baseline passes with no data shown.** `_check_performance_baseline` returns pass even when it captured nothing, and the captured fields are dropped at render time. | Bug | P2 | S | v1.6.2 | Done | Return `skipped` when there are no metrics. The PDF has no Performance Baseline details group (removed 2026-10-15); the check keeps its Detailed Check Results row. |
| HCF-6 | **Render check `details` in the PDF and the web page.** Adds per-check sub-tables for alarms, performance metrics and inactive-component lists. | Gap | P1 | M | v1.6.2 | Done | Only non-empty details are shown, with row caps. In the PDF the per-check sub-tables were replaced by the RPT-LAYOUT-1 group tables (2026-10-16). |
| RPT-LAYOUT-1 | **Wrapped, centered report tables and grouped health details.** Text stays inside its cell; rows grow and columns keep their widths (a column narrower than one short word borrows space). Health detail sub-tables are consolidated into functional-area groups, and titles stay on the page with their table. Spec: [`issues/RPT-LAYOUT-1/`](issues/RPT-LAYOUT-1/spec.md). | Enhancement | P1 | M | v1.6.2 | Done (branch) | Approved 2026-10-16; the temporary `legacy` toggle and the HCF-6 PDF sub-tables are removed. |
| RPT-TITLE-1 | **Report title rebrand.** The title page's top title becomes "asbuilt-reporter" in the one-pager style: Fira Sans Bold, "asbuilt" in black and "-reporter" in accent blue `#1a6fb5`. The large center logo stays. | Enhancement | P2 | S | v1.6.2 | Done (branch) | Fira Sans Bold (SIL OFL 1.1, `assets/fonts/` with `OFL.txt`) is registered at startup and bundled in the macOS/Windows builds; falls back to Helvetica-Bold if the file is missing. Footer and Executive Summary text unchanged. `tests/test_brand_title.py`. |
| RACK-1 | **Rack heights 45U, 48U, 50U and 52U in the Physical Rack Layout.** A 45U, 50U or 52U rack used to fall back to 42U and drop every device above U42. | Feature + bug | P1 | M | v1.6.2 | Done (branch) | Supported heights 42/45/48/50/52 (others round up). One points-per-U value per report, capped at today's 42U size: 42/45/48U unchanged, 50U ≈ 96%, 52U ≈ 92–93% (A4/Letter). Drawing trimmed to its content and the duplicate "Rack: X" caption dropped so every rack fits under its heading. Every U is labelled; indicators, mounting holes and fonts shrink with the pitch so a pill fits 1U. Blank padding in device artwork is cropped at draw time so stacked devices touch. |
| RACK-2 | **Full-rack validation report.** `scripts/generate_rack_validation_report.py` fills two racks per height with one of each library device (library order, wrap and reverse rules) and renders them through the report's rack code, with every indicator colour, shape and count. | Tooling | P1 | S | v1.6.2 | Done (branch) | Output (gitignored) `output/rack-validation/rack_validation_<ts>.pdf` + `.json`; exits non-zero if a rack is not full or leaves its heading page. Sequencer in `src/utils/rack_validation.py`. |
| RACK-3 | **Rack template test suite.** Geometry contract (full width, no gaps, exact U pitch), page fit on A4/Letter, every device × every height, artwork aspect/edge audit, top-U boundaries, indicators vs status map, label coverage/overlap, shared scale, user-Library device. | Tests | P1 | S | v1.6.2 | Done (branch) | `tests/test_rack_heights.py`, `tests/test_rack_validation.py`. Follow-ups: `ceres_4u` has no artwork (generic 2U placeholder) and its "4u" name vs 2U height needs confirming; several 1U switch images are ~12–14% short of the 19:1.75 ratio (within the 15% audit limit). Optional: golden-image visual regression with PyMuPDF. |
| INV-1 | **Node serial numbers in the report.** `serial_number` is already collected for every CNode and DNode (`api_handler` around L1102 and L1213) but isn't displayed; the inventory "Name/Serial Number" column shows the node name. | Feature (quick win) | P1 | S | v1.6.2 | Done | Serial column on Hardware Inventory + CNode/DNode Management Map; box `uid` used as chassis fallback when present. |
| HCF-3 | **Critical alarms only warn.** In one field run, 17 critical/major alarms produced a warning. This reverses the v1.5.0 HC-1 decision, which made alarms informational. | Policy change | P1 | M | v1.7.0 | Planned | Critical alarms fail and major alarms warn, controlled by the new key `health_check.alarms.fail_on` (`critical` / `major` / `none`). Update the render-time fixup to honour it, and render the alarm sub-table through HCF-6. The HC-1 reversal was accepted 2026-09-25. |
| HCF-4 | **A Trial license passes.** `_check_license` fails only on `EXPIRED`/`INVALID`, and doesn't read the expiry date. | Gap | P2 | S-M | v1.7.0 | Planned | Trial and evaluation licenses become a warning ("verify before go-live"), with days remaining shown if the API exposes it. DIAG-1 confirms the field names first. |
| INV-2 | **Node MAC addresses.** The API collection path doesn't gather MACs. They exist only through SSH port mapping (`external_port_mapper._collect_node_macs_via_clush`). | Feature | P2 | M-L | v1.7.0 | Planned | If DIAG-1 finds MACs in the API, use the standard api_handler → data_extractor → report_builder path; otherwise surface the port-mapping MACs. Open question: which MACs customers want (management, BMC/IPMI or data NICs). |
| DRV-1 | **Drive inventory and firmware section (DBox and EBox).** Nothing is collected today: no `ssds/`/`nvrams/` calls. | Feature (high value) | P1 | L | v1.7.0 | Planned | Add `get_drive_inventory()`, `extract_drive_inventory()` and `_create_drive_inventory_section()`: a summary by Box, Vendor, Model and Firmware with quantities, plus a TOC entry. The per-drive list goes to JSON only. Tests for all three layers. Coordinate with PROM-1. |
| DRV-2 | **Firmware advisories.** A config-driven `hardware_advisories.known_firmware` list (vendor, model and firmware, with severity and a note) flags matching rows in DRV-1. | Feature | P3 | S | Later | Planned | Nothing hardcoded. Depends on DRV-1. |
| SW-1 | **"Issues connecting to one of the switches."** Not enough detail to act on. | Possible bug | P2 | ? | TBD | Deferred (awaiting logs) | Ask the reporter for the switch vendor/OS, the error text from Output Results, and the ops log (the Test Suite `oneshot_*.jsonl`). Likely candidates are the Onyx web-API login, a non-default credential, or the FR-4/FR-8 family (switches missing from VMS). |

---

## Planned — Field report: EBox Test Suite run (2026-09-25)

*Source: engineer-supplied Test Suite bundle, ops log and app log from a 12-EBox 5.5 cluster. Root cause and the logging/upload plan are in [`plans/field_diagnostics_pipeline_9b6d157c.plan.md`](plans/field_diagnostics_pipeline_9b6d157c.plan.md).*

| ID | Item | Type | Priority | Size | Target | Status | Notes |
|------|------|------|----------|------|--------|--------|--------|
| FR-1 | **Support Tools fail on every EBox cluster.** Hardcoded `/vast/data/vms.sh`; EBox uses `/vast/data/C-<port>/vms.sh`. Step 3 hid rc=127. | Bug | P0 | S | v1.6.2 | Done (branch) | Wrapper discovery + honest Step 3 failure rules. `tests/test_support_tool_ebox.py`. Lab-verify on an EBox and a C/DBox cluster before release. |
| FR-2 | **vperfsanity killed during the burst-recovery wait.** One 60-min SSH call vs the script's 2 h burst wait. | Bug | P0 | S | v1.6.2 | Done (branch) | 4 h budget (overridable), timeout names the phase, accurate duration notice. Follow-up FR-7. |
| FR-3 | **Aborted workflows skip cleanup.** vperfsanity left ~53 TB, view/policy/user and elbencho on the cluster. | Bug | P0 | S | v1.6.2 | Done (branch) | `CLEANUP_STEPS` contract in both runners (failure and cancel). `tests/test_workflow_cleanup_contract.py`. |
| FR-4 | **Switch ops fail when VMS has no switches; vnetmap runs with empty `-s`.** | Bug | P1 | S | v1.6.2 | Done (branch) | SKIPPED with guidance; accurate auth message. Manual `+Switch` IPs as a fallback source is FR-8. |
| FR-5 | **Log bundle "OK" but only `/var/log/messages`.** | Bug | P1 | S | v1.6.2 | Done (branch) | Per-source status, recent `/vast/log` (24 h, 2 GB cap), partial labeling. Lab-verify paths; all-node collection is FR-9. |
| FR-6 | **Bundle can't explain failures.** Placeholders pointed at an ops log that wasn't included. | Bug | P1 | S | v1.6.2 | Done (branch) | Operation log in bundle, step+error in placeholders, manifest v1.4. SSH timeouts keep partial output (subprocess path). |
| FR-7 | **vperfsanity background runner.** Detached remote run with polled heartbeat (write / burst wait + fill % / read), stall detector, effective Cancel, Quick vs Full dataset. | Enhancement | P1 | M | v1.6.3 | Planned | Needs lab validation. |
| FR-8 | **Use manual `+Switch` entries as a switch source.** Accept IPs, or hostnames resolved on the CNode; validate input in the UI. | Enhancement | P2 | S-M | v1.6.3 | Planned | Today manual entries only place switches in the rack diagram. |
| FR-9 | **Log bundle from all CNodes/DNodes.** | Enhancement | P2 | M | v1.6.3 | Planned | Via clush, bounded by age/size. |
| FR-10 | **Paramiko SSH path has no overall deadline.** `recv_exit_status()` can block past the timeout on Windows (no sshpass). | Bug | P2 | S | v1.6.3 | Planned | Deadline loop that keeps partial output; rework the existing paramiko mocks. |
| NET-6 | **Network Extraction and vnetmap missed nodes on EBox clusters.** EBox `local.cfg` repeats group keys (`cnodesub0`, `dnodesubN`) across sections; ClusterShell unions them, but both parsers kept only the last definition, and Network Extraction dropped comma-joined `@group` references. The field run found 11 of 12 hosts (missing CNode `172.16.128.2`), and vnetmap's `-i` list had the same gap plus duplicates. | Bug | P1 | S | v1.6.2 | Done (branch) | Shared `src/utils/clustershell_groups.py` (union of duplicate keys, `[1-3,5]` and `[5]` ranges, cycle-safe `@group` refs) used by both workflows. `tests/test_clustershell_groups.py` uses the field `local.cfg`. Follow-up in TP-3: in Tech Port mode the gateway is also listed under `192.168.2.2`, so it is counted twice. |
| HCF-7 | **Firmware Consistency false positive on equivalent BIOS strings.** On EBox, the `-4000` and `-4100` DNode containers on each host report the same BIOS as `2.90` and `A56 v2.90 (01/09/2026)`, which warned on every cluster of that model. | Bug | P2 | S | v1.6.2 | Done (branch) | Values are compared on their dotted version tokens; the pass message notes fields that differ only in format. Real BIOS and kernel-build differences still warn. Tests in `test_health_checker.py`. |
| HCF-8 | **Skipped health checks printed as `[????]` in Output Results**, with no reason shown (for example `[????] CBox Status`). | Bug (cosmetic) | P3 | S | v1.6.2 | Done (branch) | Shared status icons (`[SKIP]`, and the status name for anything unknown); skipped checks now print their reason. `tests/test_oneshot_status_icons.py`. |
| FR-11 | **Remote archives left on the cluster.** `/tmp/vast_log_bundle_*.tar.gz` stays on the CNode and `/userdata/*-support_tool_logs_*.tgz` on the VMS host after download. | Bug (hygiene) | P3 | S | v1.6.3 | Planned | Remove after a verified download; the HUB-4 residue check reports anything left. |
| FR-12 | **vperfsanity `VAST_VMS` export is a no-op.** The script reads `/vast/vman/mgmt-vip`. | Cleanup | P3 | S | v1.6.2 | Done (branch) | Export removed from all six commands; every vperfsanity script gets the VMS address from `helpers/vast_get_vms_ip.sh`. The pinning test now asserts the export is absent. |
| FR-13 | **vperfsanity timeout and data retention are not configurable in the UI.** The `vperfsanity_timeout_s` override exists only as a credential key. | Enhancement | P3 | S | v1.6.3 | Planned | Expose it in config/UI and add a "keep test data on failure" opt-out for debugging. |
| FR-14 | **Support Tools inspect timeout does not scale with cluster size.** Fixed 600 s. | Enhancement | P3 | S | v1.6.3 | Planned | Scale by node count. |
| FR-15 | **Cancel does not interrupt long steps other than vperfsanity.** | Enhancement | P2 | M | v1.6.3 | Planned | FR-7 covers vperfsanity only; extend to log bundle and support tools. |
| OBS-1 | **Artifact timestamps mix UTC and local time.** Health files are named in UTC (`..._20260926_013125`) while the bundle, report and the timestamps inside the health file use local time (`..._20260925_183126`, `-07:00`). | Bug | P3 | S | v1.6.3 | Planned | One convention for filenames; the HUB-2 recorder uses UTC throughout. |
| TP-3 | **Tech Port discovery logged `management=192.168.2.2`.** The VMS management IP was not resolved (the tunnel still worked), so anything that uses the management IP gets the Tech Port address, and Network Extraction counts the gateway twice. | Bug (investigate) | P3 | S | v1.6.3 | Planned | Reproduce from the field ops log against a lab Tech Port session. |
| TP-4 | **Results page cluster filter returns every Tech Port cluster.** Choosing one cluster that was reported through the Tech Port also lists the results of every other Tech Port cluster, and the reverse (seen with four field clusters). The filter dropdown sends the profile's `cluster_ip`, and `/validation-results/api/results` filters by that IP, which is `192.168.2.2` for all of them. | Bug | P2 | M | v1.6.3 | Planned | Spec: [`issues/TP-4/spec.md`](issues/TP-4/spec.md). Filter by `cluster_key` (the per-cluster folder from QP-2), as `get_known_clusters()` already does. |

---

## Planned — Results Hub and field diagnostics (2026-09-26)

*Source: [`plans/field_diagnostics_pipeline_9b6d157c.plan.md`](plans/field_diagnostics_pipeline_9b6d157c.plan.md) Phases 2–6, from the EBox field report. Architecture decisions (S3 presigned intake, hybrid topology, tiered collection, private triage, Mission Control relay, PSNT account mapping) are in [`DECISIONS.md`](DECISIONS.md). Backend items live in separate repos; they are tracked here so the app and hub stay in step.*

| ID | Item | Target | Status | Notes |
|------|------|--------|--------|--------|
| HUB-1 | **Installation ID.** Stable per-install identifier stamped on every run and upload. | v1.6.3 | Planned | Reuses the telemetry `install_id`; migrates with DATA-1. |
| HUB-2 | **Run recorder.** `run_id` correlation, streamed Output Results, per-step records, remote transcripts, environment, operator notes, value-based credential redaction, UTC timestamps. | v1.6.3 | Planned | Local only. Resolves OBS-1 for new artifacts. |
| HUB-3 | **Cluster capability probe.** Records wrapper paths, ClusterShell groups, switches in VMS, and tool availability before operations run. | v1.6.3 | Planned | Would have flagged FR-1, FR-4 and NET-6 up front. |
| HUB-4 | **Cluster hygiene / residue check.** Reports leftover vperfsanity objects, elbencho, and remote archives after a run. | v1.6.3 | Planned | Pairs with FR-3 and FR-11. |
| HUB-5 | **Local results ledger** with backfill of existing bundles. | v1.6.3 | Planned | Feeds the Total Results Generated metric. |
| HUB-6 | **Export Diagnostics** UI and routes. | v1.6.3 | Planned | Manual export before any upload exists. |
| HUB-7 | **vperfsanity artifacts copied to the laptop**, and the `-U` upload reported honestly. | v1.6.3 | Planned | Step 6 reports "Upload skipped" as success today. |
| HUB-8 | **vperfsanity output parser.** | v1.6.3 | Planned | Shared with RCS-5. |
| HUB-9 | **Diagnostics rules analyzer** plus a CI `diagnostics-rules` job over sanitized fixtures. | v1.6.3 | Planned | First fixture: the EBox field report. |
| HUB-10 | **Upload client.** Enrollment, outbox, Upload-now dialog, destinations, receipts, tracking keys. | v1.7.0 | Planned | Supersedes UPL-1. |
| HUB-11 | **Tier-0 counts on by default.** | v1.7.0 | Planned | Policy change: rewrite `TELEMETRY.md` and add Legal-approved notice text. |
| HUB-12 | **AWS intake:** S3 presigned uploads, API Gateway, GuardDuty malware scan, SQS. | Backend | Planned | Separate repo. |
| HUB-13 | **Mission Control hardening:** HTTPS, SSO, backups, database not exposed. | Backend | Planned | Prerequisite for storing customer data. |
| HUB-14 | **Results database and ingest worker:** unzip, index, full-text search. | Backend | Planned | |
| HUB-15 | **Dashboards:** Total Results Generated, performance by hardware and network. | Backend | Planned | Grafana. |
| HUB-16 | **Read API** for other tools. | Backend | Planned | |
| HUB-17 | **Connector framework.** | v1.7.x | Planned | Delivery runs through the Mission Control relay. |
| HUB-18 | **PSNT to SFDC Account and Slack channel mapping**, confirmed by the engineer once and cached. | v1.7.x | Planned | |
| HUB-19 | **Slack connector** (`#internal-<customer>` thread). | v1.7.x | Planned | Needs Slack admin approval of the bot. |
| HUB-20 | **SFDC connector** (Account Notes & Attachments). | v1.7.x | Planned | Needs a Connected App and integration user. |
| HUB-21 | **vperfsanity results DB relay.** | v1.7.x | Planned | Replaces the package's embedded upload keys (GOV-2). |
| HUB-22 | **LaunchPad:** JSON schema contract for the as-built import, then an Integrated App push. | v1.7.x | Planned | SE Tools team. |
| HUB-23 | **Private triage store plus Cursor agent.** Fingerprint dedupe, agent drafts spec, failing-first test and draft PR; a sanitized public issue only when a fix is scheduled. | v1.7.x | Planned | |
| DATA-1 | **Move the app data directory to OS-standard locations.** Writing next to the `.app` or `Program Files` can fail. | v1.6.3 | Planned | Migrate the installation ID so HUB-1 stays stable. |

---

## Planned — Install-time capacity & performance logging (Ross Cooper-Smith, 2026-09-25)

*Source: Slack thread “Validating install-time capacity and performance” (group DM). Product asks after the field-feedback triage. DIAG-1 probe expansion unblocks RCS-2–4 field names; RCS-1 needs Ross’s friendly-name table; RCS-5 parses local vperfsanity output (no API dependency).*

| ID | Item | Type | Priority | Size | Target | Status | Notes |
|------|------|------|----------|------|--------|--------|--------|
| RCS-1 | **Friendly DBox/EBox model names with drive size.** Use sizing/licensing “friendly” names and append drive size in brackets (upgrade-critical). | Feature | P1 | M | v1.7.0 | Planned | Needs Ross’s name table export. Layers on drive-size discovery (DIAG-1 / DRV-1). |
| RCS-2 | **RLR quantity in Cluster Info.** Show failure-domain count (not only Yes/No on `enable_rack_level_resiliency`). | Feature | P1 | S | v1.7.0 | Planned | DIAG-1 must confirm whether quantity is the same field or a sibling. |
| RCS-3 | **Metadata triplication in Cluster Info.** | Feature | P1 | S | v1.7.0 | Planned | Field name TBD via DIAG-1. |
| RCS-4 | **EBox “1-strip” resiliency option in Cluster Info.** Higher-resiliency option for large EBox clusters (Howard / eng). | Feature | P1 | S-M | v1.7.0 | Planned | Official API name unknown — ask Ross; DIAG-1 highlights `strip`/`resilienc` keys. |
| RCS-5 | **vperfsanity final figure in Cluster Info.** Pull the final performance number from Test Suite / bundle output into the summary. | Feature | P1 | S-M | v1.7.0 | Planned | Local artifact parse — no live API. Can be its own small PR; does not wait on DIAG-1. |

---

## Planned — Queued implementation plans (2026-06-16)

*Plans drafted and queued for execution this session. One additional plan will be generated before execution begins. Plan files live in `.cursor/plans/`.*

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| QP-1 | **Report & diagram refinements (incl. Node Management Map).** Add a Node Management Map (VMS device name -> hostname -> external mgmt IP) as two compact CNode/DNode tables under Network Configuration; resolve Port Mapping switch GUID -> hostname -> mgmt IP (Full Topology "Switch IP" shows mgmt IP; per-switch titles show name + GUID + mgmt IP); replace diagram switch designations (SWA/SWB/SP1/SP2) with hostname + mgmt IP; dynamic switch width with centered landing fan; populate Switch Configuration Active Ports & Port MTU. | Medium | Done (2026-06-16) | Plan: `.cursor/plans/node_management_map_table_6c99be75.plan.md`. All five sub-items implemented with TDD and verified via LAX-01 replay/render (221 tests pass; flake8/black clean). CNode/DNode Management Map tables + TOC subsections; Full Topology shows switch mgmt IP and per-switch titles show name + mgmt IP + GUID; diagram switch labels now name + mgmt IP; dynamic `switch_w`/`device_w` centers the landing fan within each switch box (`_build_landing_slots` / `_fan_landing_x` / `_dynamic_switch_width`); Active Ports/MTU recomputed (count `up`/`active`, most-common non-zero MTU) in both `api_handler` and a defensive `report_builder` recompute. |
| QP-2 | **Per-cluster result segmentation by PSNT.** Write all generated artifacts (reports, vnetmap/workflow outputs, diagrams, health, bundles, ops logs) under per-cluster subdirectories keyed by a resolved cluster identifier (PSNT -> GUID -> name -> IP fallback) with a `cluster.json` marker; make discovery/scanning folder-scoped with a backward-compatible legacy read path. Eliminates cross-cluster data intermingling when every cluster shares tech-port IP `192.168.2.2`. | High | Done (2026-06-16) | Plan: `.cursor/plans/segment_results_by_psnt_739a98da.plan.md`. New `src/utils/cluster_paths.py` (+ `cluster_output.py` write helper); `cluster_key` threaded through app/one-shot/advanced-ops orchestration with **early** identity resolution in one-shot so operation artifacts segment before the report phase; folder-aware `_find_latest_vnetmap_output` / scanner / bundler with legacy-flat fallback. Read-side association keys on PSNT/GUID/name (never the shared tech-port IP), so two clusters on `192.168.2.2` stay separate. Gated by `output.segment_by_cluster` (default true); explicit CLI `--output-dir` honored verbatim. Code-reviewed (2 blockers found & fixed: ops-artifact segmentation + IP-based collapse). Verified: 1342 broad + 287 QP-2 + 119 app + 26 one-shot logic tests pass; flake8/black clean. |
| TPM-1 | **Teleport (tsh) connection mode + Connection Settings UI redesign.** Add a third connection method alongside Tech Port and VMS HTTPS that tunnels the cluster API (443) and CNode SSH (22) through `tsh ssh -L` dual port forwards so reports and `vnetmap`/port mapping work against Teleport-only clusters. Redesign the Connection Settings tile: three-way connection-mode radios (Tech Port / VMS Mgmt / Teleport) replacing the Advanced-menu Tech Port checkbox, Autofill Passwords promoted to a toggle (ON locks defaults / OFF keeps usernames + clears passwords), and Teleport node/user fields shown only in Teleport mode, persisted in profiles. | High | Done (2026-06-19) | New `src/utils/teleport_tunnel.py` (`TeleportTunnel` w/ preflight + dual `-L` forwards); `port`/`jump_port` threaded through `ssh_adapter`, `tool_manager`, `script_runner` (`set_ssh_port`); `ssh_host`/`ssh_port` honored by `vnetmap_workflow`, `external_port_mapper`, `switch_config_workflow`, `health_checker`, and one-shot (`_setup_teleport_tunnel`, `_validate_teleport_tunnel`). `app.py` `generate_start`/`_run_report_job`/`/api/discover` launch the right tunnel per mode. `frontend/templates/reporter.html` UI + CSS; `teleport` config block in `config.yaml.template`. Tests: `tests/test_teleport_tunnel.py` (new) + `tests/test_ssh_adapter.py` explicit-port cases. flake8/black clean. **Shipped as Beta for v1.5.8**; **2026-10-08:** Beta Feature badge and Beta labeling removed from current UI/docs after field validation (historical CHANGELOG / release notes retained). |
| QP-3 | **UI & software management enhancements.** Four parts: (1) move Deployment Tools Status + Update Tools buttons into the global top nav with an orange "needs attention" dot when tools are missing or >=10 days old; (2) phased in-app auto-update for Mac/Windows (2a notify + manual download on stable channel with pre-release opt-in, 2b auto-apply/relaunch follow-up; ties to UPD-1); (3) auto-close the server when all browser windows close (heartbeat + idle watchdog, guarded against mid-job shutdown); (4) opt-in anonymous usage telemetry + local ROI surface, plus a central-receiver design spec. | Mixed (1 Medium/now, 2-4 Medium) | **Done** (2a only for item 2; 2b auto-apply/relaunch deferred) | Items 1, 3, 4, and 2a all shipped. (1) Global-nav tools control + `GET /api/tools/status` / `POST /api/tools/update`, `TOOL_FRESHNESS_WARN_DAYS` canonical in `tool_manager`. (3) Heartbeat (`POST /api/heartbeat`) + watchdog in `run_gui`, mid-job guard, `auto_shutdown` config. **Update 2026-06-19:** changed to OPT-IN / OFF by default — background-tab timer throttling could shut the app down while a tab was still open; enable via `auto_shutdown.enabled: true`. (4) `src/usage_metrics.py` (opt-in, anonymous, local-only) + dashboard "Usage & Privacy" card + `GET /api/telemetry/status` / `POST /api/telemetry/consent` + `telemetry` config + `docs/development/TELEMETRY.md` receiver spec. (2a) `src/updater.py` (GitHub Releases check, semver+channel) + `GET /api/update/status` + in-app banner + `updates` config. Verified: 1385 broad + targeted route/logic tests pass, flake8/black/mypy clean. **Deferred:** item 2b (auto-apply/relaunch — platform-specific, risky). |

---


## Planned — Test suite enhancements (pre-release QA)

*Source: PRE-RELEASE-QA-GAP-ANALYSIS.md §6.3*

| ID   | Item | Priority | Status   | Notes |
|------|------|----------|---------|--------|
| TSE-1 | **Library:** Unit tests for GET `/library`, GET/POST/DELETE `/api/library`, mocked _load_library/_save_library | High | Done | test_app.py |
| TSE-2 | **Generate cancel:** Unit test POST `/generate/cancel` (no job → 200/409; job running → cancel accepted, mock state) | High | Done | test_app.py |
| TSE-3 | **Reports dirs:** Unit tests GET `/reports/dirs`, POST with valid path (output-dir behavior) | High | Done | test_app.py |
| TSE-4 | **API discover:** Unit test POST `/api/discover` with mocked create_vast_api_handler + RackDiagram (400/401/success) | Medium | Done | test_app.py |
| TSE-5 | **Report content:** Integration test — EBox + dell_turin_cbox + serial in data; assert PDF/intermediate contains expected strings | Medium | Done | test_integration.py |
| TSE-6 | **Profiles API:** Unit tests GET/POST/DELETE `/profiles` and `/profiles/<name>` (mock _load_profiles/_save_profiles) | Medium | Done | test_app.py |
| TSE-7 | **Shutdown:** Optional unit test POST `/shutdown` (200, no crash) or document as manual check | Lower | Done | test_app.py |
| TSE-8 | **Coverage:** Add tests for external_port_mapper, rack_diagram, report_builder (EBox path, partial port mapping) toward 80% | Lower | Done | Coverage 53%+ (49%+ restored); further toward 80% in TSE-9 |
| TSE-9 | **Coverage — low-coverage modules:** Expand tests for external_port_mapper, rack_diagram, report_builder, health_checker, tool_manager, script_runner, workflows to raise total coverage toward 80% | Lower | In progress | Phase A-C complete: +98 tests across 8 work streams; coverage 53%→56%; dead-code modules archived; external_port_mapper, rack_diagram, health_checker, tool_manager, script_runner, workflows augmented |
| TSE-10 | **Coverage — omit config:** Configure coverage omit for files not intended to be tested so cov-fail-under=80 applies only to in-scope code when threshold is raised | Lower | Done | Dead-code modules (comprehensive_report_template.py, enhanced_report_builder.py) moved to archive/; session_manager.py restored to coverage; pyproject.toml omit list cleared |

---

## Planned — Quality gates and pre-release checklist

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| QG-1 | Run flake8 + black (and optionally mypy) as part of documented pre-release run | Done | README Development § Pre-release checklist |
| QG-2 | Fix or document flake8/black/mypy exceptions to achieve green quality gate | Done | Followed MYPY_FIX_SUGGESTIONS notes (retired in v1.5.8 cleanup; see `pre-1.5.8-cleanup` tag): types-paramiko, _MEIPASS, var annotations, return casts, api_handler session/optional, network_diagram Path/float, report_builder tuple/int/float; mypy passes. |
| QG-3 | Raise coverage toward 80% or formally set cov-fail-under with restoration plan | In progress | cov-fail-under=60 (raised from 55); total coverage 60%+; Phase A-C complete; track TSE-9 for 80% |

---

## Planned — Authentication and reporting access

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| AUTH-1 | **Automate token generation:** Consider automating API token creation (e.g. on first connect or when no valid token is provided) to simplify reporting access. Token generation enables read-only API access for the report tool only; it has no direct impact on cluster components, cluster functionality or operations, or resources used by the cluster to deliver data services. Align with [READ_ONLY_VAST_API_POLICY.md](development/READ_ONLY_VAST_API_POLICY.md) (auth POST allowed to establish access). | Planned | Current flow: prefer provided token or basic auth; create token only when needed (5-token limit). Automation could streamline this for unattended or scripted reporting. |

---

## Planned — Developer mode (hidden/secure)

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| DEV-1 | **Developer button:** Add a hidden/secure Developer control at the top of the UI, enableable by developers at launch (e.g. env flag or launch option). When enabled, expose: (1) **Configuration** — move existing Configuration section under Developer; (2) **Docs** — move Docs access under Developer; (3) **Live API Explorer** — expose API Explorer interface under Developer; (4) **Report from JSON** — new UI to generate reports directly from previously generated `.json` output files (e.g. `vast_data_*.json`) without reconnecting to the cluster. | Planned | Navbar/top-level; secure so only enabled at launch |

---

## Planned — EBox Hardware Overview & Inventory

*Source: EBOX-HARDWARE-TABLE-IMPLEMENTATION-PLAN notes (retired in v1.5.8 cleanup; see `pre-1.5.8-cleanup` tag)*

| ID    | Item | Status   | Notes |
|-------|------|----------|--------|
| EBOX-1 | **Hardware Overview (EBox-only):** CBoxes=0, DBoxes=0; CNodes/DNodes as discovered | Done | report_builder.py |
| EBOX-2 | **Hardware Inventory (EBox-only):** Remove Node column; EBox→CNode→2×DNodes order; Model from CNode vendor; switches at bottom | Done | report_builder.py _create_ebox_only_inventory_table; brand_compliance 5-col |
| EBOX-3 | **Rack Layout:** EBox model from CNode vendor for library image; 1U default | Done | report_builder.py racks_data ebox model from CNode; rack_diagram 1U already |
| EBOX-4 | **Port Mapping (EBox-only):** CNode/DNode names in Notes column; separate from standard CBox/DBox logic | Done | external_port_mapper.py, report_builder.py |
| EBOX-5 | **Network Diagram (EBox-only):** EB# labels, Green (Network A) / Blue (Network B) connections | Done | network_diagram.py |
| EBOX-6 | **Hardware Library:** msn4700-ws2rc switch and dell_genoa_ebox added as built-in devices | Done | app.py, rack_diagram.py, network_diagram.py |

---

## Planned — Support bundle workflow (offline / no direct cluster access)

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
| SB-1 | **Support bundle–based report generation:** New function for clusters that cannot be directly accessed. Workflow: (1) Generate a support bundle for the cluster (customer/ops generates bundle); (2) Upload support bundle content into the app; (3) Analyze support bundle file content; (4) Generate `.json` file from bundle content (same schema as live-generated `vast_data_*.json`); (5) Generate report from the generated `.json` file (reuse existing report-from-data path). End-to-end: support bundle → JSON → PDF report without live API access. | Planned | New upload/analyze pipeline; document bundle format and required files |

---


## Planned — Requests for Enhancement (from Confluence)

*Source: [VAST As-Built Report Generator - v1.3.0](https://vastdata.atlassian.net/wiki/spaces/~7120200e1c43a9b6f741eca536d39491156fa8/pages/6664028496/VAST+As-Built+Report+Generator+-+v1.3.0) — Requests for Enhancement table.*

| ID    | Item | Status   | Notes |
|-------|------|----------|--------|
| RFE-1 | Support Bundle Integration | Planned | |
| RFE-2 | Jeff's Port Mapper Integration | Planned | |
| RFE-3 | Render Logical Net Diagram only with Port Map option enabled | Planned | |
| RFE-4 | Health Report Summary | Done | Health Check Module with Tier 1 (API) & Tier 3 (Switch SSH), PDF sections, remediation reports |
| RFE-5 | Integrate/Automate Post Deployment Tests | Done | Advanced Operations with 6 workflows (vnetmap, support tools, vperfsanity, log bundle, switch config, network config) |
| RFE-6 | Container deployment option | Planned | |
| RFE-7 | Update deployment procedures | Planned | |
| RFE-8 | Package as Mac.app / Win.msi | Planned | |
| RFE-9 | Add recommended next steps | Planned | |
| RFE-10 | Add Alert Summary | Planned | |
| RFE-11 | Create .json export database | Planned | |
| RFE-12 | Fix DC/DBox Rack naming | Deferred | Needs concrete bug report; depends on RFE-13 (now fixed) |
| RFE-13 | Fix Rack API Call | Done | get_racks() now uses _normalize_list_response() for paginated API support |
| RFE-14 | Check capacity calculations | Deferred | No local calculations (API pass-through); needs specific discrepancy report |

---

## Planned — Network mapping fallbacks (2026-10-16)

| ID | Item | Priority | Target | Status | Notes |
|------|------|----------|--------|--------|--------|
| NET-7 | **vnetmap fallback to `vnetmap_lldp.py` for customer-managed switches.** With no switch credentials, build the port map and network diagram from node-side LLDP (`vnetmap_lldp.py --operation show-mapping`) and add `vnetmap_lldp.py` to Update Tools. **Never** disable/enable/install/start `lldpad` or `lldpd` (customer coordination required); readiness is checked read-only, and `ifdown`/`ifup` are never offered. | Medium | v1.7.x | Planned | Assessment: [`issues/NET-7/spec.md`](issues/NET-7/spec.md). A new `VNetMapLLDPParser` emitting the existing topology-row contract lets the current mapper and diagram render it; gaps are switch IP (name only), MAC and network side (derive from subnet), and inter-switch links (not discoverable from nodes). The Confluence tcpdump/`nw_check.sh` scripts are optional enrichment (switch IP, MAC, fabric) and also leave lldpd untouched. No existing roadmap item covered this. |

## In progress

*(Move items here when work starts; move to Done when complete.)*

| ID | Item | Notes |
|------|------|--------|
| v1.6.2 | **Field-feedback patch** on `fix/v1.6.2-field-feedback`: DIAG-1, HCF-1/2/5/6/7/8, INV-1, SR-2, RPT-VALIDATION-1/2, NET-6, FR-1–6, RPT-LAYOUT-1, RPT-TITLE-1, RACK-1/2/3, HWL-3 (in review). | Lab verification pending. UI-5 was listed here in error; it is Planned in the UI table. |

## Planned — Tech-Port follow-ups (v1.5.7+)

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| SR-2 | **Cosmetic: "rejected candidate password" warning on Onyx switches.** Surfaced during selab-var-202 log review. The Onyx SSH pre-probe in `src/utils/switch_ssh_probe.py::probe_switch_password` correctly identifies the working password but logs a warning for each *rejected* candidate even on success runs ("rejected candidate password 1/3 for 10.x.x.x — trying next"). The warning fires as expected (it's an authentication-attempt message) but is misleading because the next candidate succeeds and the operator sees `[WARN]` lines in the log even though the probe is succeeding. Plan: demote each per-candidate rejection to `debug` level, keep a single `info` summary line on success ("authenticated 10.x.x.x with candidate 2/3"). Cosmetic only — no functional impact, no security impact. | Low | Done (on `fix/v1.6.2-field-feedback`) | Per-candidate rejects → `debug`; success → single `info` with candidate index. |
| RPT-VALIDATION-1 | **UI rendering bug: Node User field's programmatic value not rendering.** Surfaced during TP-1 / TP-2 manual validation. When the operator selects a saved profile or programmatically populates the Node User input via `value=...`, the visible text in the field stays empty until the operator clicks into it and types. The underlying form value is correct (form submission sends `vastdata`), but the rendered DOM doesn't reflect it. Likely a missing input-event dispatch in the profile-restore code path. Cosmetic / UX. | Low | Done (on `fix/v1.6.2-field-feedback`) | Unlock → `_setFieldValue` (input/change events) → re-lock on profile load. |
| RPT-VALIDATION-2 | **UI logic bug: Re-filling Node User clears Node Password.** Surfaced same session as RPT-VALIDATION-1. Re-typing into the Node User field after a profile restore clears the Node Password field, forcing the operator to re-enter both. Likely a stale `change` listener that resets the password when User changes. Cosmetic / UX. | Low | Done (on `fix/v1.6.2-field-feedback`) | Autofill OFF no longer clears passwords; unlocks and keeps current values. |

## Planned — UI Enhancement & Restyle (phased)

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| UI-1 | **Switch Placement Editor Modal:** Refactor Discovery/Manual Add into modal with Save to Profile, Cancel, snapshot/restore, Escape/click-outside close | High | Done | Implemented in reporter.html; modal with full Discovery, Manual Add, assignment, Save to Profile / Cancel |
| UI-2 | **5-step stepper action bar:** Sequential workflow bar (Discovery → Run → View → Download PDF → Download JSON) with dot indicators, connecting line, ghosted/active button states | High | Done | CSS grid stepper with 18px dots, chevron separators, ghosted/active states |
| UI-3 | **Remove Switch Placement Mode toggle:** Default Manual, fallback Auto if no placements; remove toggle HTML/JS/CSS | High | Done | Toggle removed; default Manual with Auto fallback |
| UI-4 | **Enhanced checklist rows:** Card-style elevated container, right-aligned status tags, post-completion green Passed indicators | Medium | Planned | Part of Phase 1 foundation |
| UI-5 | **Phase 1 — Foundation restyle:** Update app.css :root tokens, shared components (cards, buttons, forms, tables, toggles, badges); pill segmented controls; cascades to all pages | Medium | Planned | ~2 hours; highest ROI |
| UI-6 | **VAST Logo Progress Tracker enhancement:** Dedicated right column (always visible, dimmed at rest); granular progress; brand gradient fill on completion (navy → teal) | Medium | Done | Backend phase-level progress (7 weighted phases for report, per-check for health); frontend weighted segment mapping; smooth `_animateTo` animation; both Reporter and Test Suite tiles |
| UI-7 | **Relocate Update Tools:** Move to card header with orange badge indicator for update-needed state | Medium | Done | Icon-only button with orange notification dot in card header |
| UI-8 | **Phase 2 — Advanced Ops restyle:** Apply stepper/checklist/modal patterns from Reporter to Advanced Ops page | Low | Planned | ~1-2 hours; largely copy-paste from Reporter |
| UI-9 | **Phase 3 — Remaining pages:** Polish Dashboard, Results, Library, Docs, Config, Generate, Health pages with foundation styles | Low | Planned | ~2-3 hours; most benefit from Phase 1 automatically |

---

## Planned — Future enhancements

| ID | Item | Priority | Notes |
|------|------|----------|--------|
| UPL-1 | **Automated results posting:** Field compliance with the Field Procedure (DOC-16) depends on engineers manually attaching the as-built PDF, JSON, and validation bundle to the SFDC account (Notes & Attachments) and the `#internal-<customer>` Slack thread. Add an in-app "post results" action after a Test Suite run. Needs: auth model for SFDC and Slack, customer/account mapping from the cluster profile, and credential storage consistent with SEC-3. | Medium | Superseded by HUB-10 (upload client) and HUB-17–20 (Mission Control relay to Slack and SFDC) |
| AO-18 | **Validation Results page (dev mode):** Browse all operation results with tabs and profile-based cluster filtering. Will replace production Reports page when Post Deployment Validation is fully released. | Medium | result_scanner.py, app.py, validation_results.html — implemented, needs polish |
| AO-20 | **Generate Report page enhancements:** Apply log level selector (Status/Live/Debug), persistent log storage with 1GB capacity, and window state persistence to the Generate Report page. Align Generate page UX with Advanced Ops improvements. | Low | Future work — apply patterns from AO-19 to generate.html and report generation pipeline |
| NET-1 | **Add nb_eth_mtu to network configuration:** Collect `nb_eth_mtu` (non-blocking Ethernet MTU) from `/api/v7/vms/1/network_settings/` response `data` field. Add to `VastClusterInfo` dataclass, `get_network_config()` extraction, `data_extractor.py` network section, and report output (PDF Network Configuration table and JSON export) alongside existing `eth_mtu` and `ib_mtu` fields. | Medium | Done — v1.5.0; collected from both clusters/ and network_settings endpoints |
| REL-1 | **Remove Beta badge before v1.5.0 release:** Remove the `nav-badge-beta` span from `base.html` and its CSS from `app.css` prior to tagging the production release. | High | Done — removed in v1.5.0 release prep |
| PM-1 | **SSH proxy hop for field deployments:** Tunnel switch SSH through CNode via paramiko nested transport (`direct-tcpip` channel) so port mapping and Tier 3 health checks work when switches are only reachable from the cluster internal network. Default on. UI toggle, CLI `--no-proxy-jump`, profile persistence. Hot-fix candidate for v1.4.8 (ssh_adapter + external_port_mapper subset). | High | Done — v1.5.0; hot-fix cherry-pick available for v1.4.8 |
| UPD-1 | **In-app self-update mechanism:** Add ability for the application to check for, download, and apply updates (hot-fixes and new versions) from GitHub Releases. Workflow: (1) Check current version against latest GitHub Release tag; (2) Display update notification with release notes when newer version available; (3) User-initiated download of platform-appropriate artifact (.dmg / .zip); (4) Apply update and restart. Consider: auto-check on launch (configurable), manual check via UI button, rollback capability, update channel (stable vs pre-release), signature verification for downloaded artifacts. | Medium | Future enhancement; reduces manual update friction for field-deployed instances |
| CFG-1 | **Configuration template refresh:** Update `config/config.yaml.template` to reflect all settings, features, and enhancements added since last update. Ensure parity between template and runtime config keys. Document new keys (ops_log settings, SSH proxy defaults, reporter defaults) in README Configuration section. | High | Planned — re-scoped 2026-09-26. The template is still drifting (for example the `vperfsanity_timeout_s` override is undocumented). Add a CI key-parity check between the template and the keys the code reads. |
| CFG-2 | **Report section toggles:** Per-section true/false toggles under `data_collection.sections` controlling PDF rendering (headings, descriptions, tables, images, TOC entries). Covers all 11 report sections. JSON export unaffected. | High | Done — v1.5.0 |
| RPT-1 | **Rack diagram serial labels:** CBox/DBox labels replaced with Hardware Inventory Name/Serial Number; DBox deduplication at same U position for Ceres V1 (4x dnodes → 1 label). | Medium | Done — v1.5.0 |
| RPT-2 | **Post Deployment Activities dynamic status:** Status column auto-resolves to Completed (green), Optional (accent blue), or Pending (orange) from health check results and cluster data. Render-time fallback for existing JSON files. | Medium | Done — v1.5.0 |
| HWL-1 | **Hardware library additions:** `supermicro_turin_cbox` and `bluefield` entries added to BUILTIN_DEVICES for VMS API model matching. | Low | Done — v1.5.0 |
| RPT-3 | **Rack diagram status indicators:** Per-device color-coded indicators (CBox: 1–4 CNode dots, DBox: 1–4 DNode squares, EBox: 1 dot + 2 squares, Switch: 1 dot if in HW Inventory). Green=Active, Orange=Inactive, Blue=Management VMS. Dark pill background, legend tile. | Medium | Done — v1.5.0 |
| HC-1 | **Health check tuning & Tier 2 removal:** Active Alarms→warning, CNode Status management pass-through, Switches in VMS→skipped, Monitoring Config removed (no SNMP/syslog API), Tier 2 node SSH checks removed (redundant with One-Shot `vast_support_tools.py`). Render-time fixups for old JSON. | High | Done — v1.5.0 |
| DOC-1 | **README.md — Health check tier model:** Removed Tier 2, updated to 2-tier model (26 API + 6 Switch SSH = 32 checks) | High | Done |
| DOC-2 | **README.md — Advanced Configuration page:** Added row to Web UI table; described 9 sections, Report Tuning Tool, deep-merge save | High | Done |
| DOC-3 | **README.md — Configuration section update:** Rewrote Configuration section with Advanced Config UI as primary interface, Report Tuning Tool, formatting options | Medium | Done |
| DOC-4 | **README.md — Report formatting options:** Documented organization, margins, font family, Include TOC/Page Numbers with config keys | Medium | Done |
| DOC-5 | **README.md — VIP Pools health check behavior:** Added warning status note and render-time fixup description | Low | Done |
| DOC-6 | **POST-INSTALL-VALIDATION.md — Remove Tier 2 Node SSH section:** Removed Tier 2 table, updated Recommended Sequence, Summary Matrix, and One-Shot section | High | Done |
| DOC-7 | **POST-INSTALL-VALIDATION.md — Add Advanced Configuration reference:** Added config note to Recommended Sequence with Report Tuning Tool cross-reference | Low | Done |
| DOC-8 | **ADVANCED-OPERATIONS.md — Tier 2 removal and config page:** Updated Tiers 1-3 → Tier 1 + Tier 3; added Configuration section with Advanced Config and Report Tuning Tool cross-references | Medium | Done |
| DOC-9 | **RELEASE_NOTES_v1.5.0.md — Add recent changes:** Add to Highlights and New Features: (1) Advanced Configuration UI with Report Tuning Tool; (2) Report formatting fixes (organization, margins, page numbers, font family, blank page on page 9); (3) VIP Pools status changed from fail to warning with render-time fixup; (4) Reporter UI config wiring (SSH, health check, advanced ops settings initialized from config.yaml); (5) Advanced Config deep-merge save prevents config key loss; (6) Prometheus diagnostics script for future metric evaluation. Update Known Limitations: remove AO-15/AO-19 if complete; note pending font-family troubleshooting task. | High | Deferred — obsolete. v1.5.0 shipped and its release notes are frozen; archive at the next sweep. |
| DOC-10 | **docs/deployment/PORT-MAPPING-GUIDE.md — SSH proxy hop:** Added SSH Proxy Hop section with CNode tunneling details, CLI flag, UI toggle; updated Network Access requirements | Medium | Done |
| DOC-11 | **docs/development/HEALTH-CHECK-MODULE-IMPLEMENTATION-GUIDE.md — Tier 2 removal:** Updated WP-9 to Tier 3 only; marked Tier 2 checks as removed; added post-HC-1 state note with VIP Pools warning and fixup mechanism | Medium | Done |
| DOC-12 | **docs/deployment/DEPLOYMENT.md — Version and config updates:** Updated Python 3.8+ → 3.10+, added Advanced Config reference, updated footer to v1.5.0 | Low | Done |
| DOC-13 | **docs/API-REFERENCE.md — Prometheus and monitoring endpoints:** Verify Prometheus metric endpoints (`/api/prometheusmetrics/{path}`) are documented with available paths (devices, cnodes, cluster, network, etc.). Check if monitoring endpoints section references removed SNMP/syslog endpoints and remove if present. Confirm `nb_eth_mtu` field reference in network settings. Update "Last updated" date. | Low | Planned |
| DOC-14 | **Confluence docs sync (`docs/confluence/`):** Refresh local copies of Confluence design/requirements pages (page 6664028496) before v1.5.0 release using Atlassian MCP tools. Ensure RFE table and version references reflect current state. Directory currently empty — requires initial download or re-sync from Confluence. | Medium | Planned — the always-applied rule `design-guidelines-01.mdc` references about 25 files in this empty directory, so every session loads dangling references. Either run the sync or trim the rule to the Confluence page link (rule change via PR). |
| DOC-15 | **CHANGELOG.md — Verify completeness:** Review v1.5.0 changelog entries against all modified files and features. Ensure no changes from recent sessions (Advanced Configuration, report formatting, VIP Pools, config wiring, Prometheus diagnostics) are missing before release tag. | Low | Done — v1.5.0-rc1 |
| DOC-16 | **Field Procedure in the Quick Start Guide:** 13-step install → update → configure → run → collect → post procedure for the as-built report and post-deployment Test Suite, with condensed checklist, connection-mode / operations / bundle-status tables, troubleshooting, and data-handling notes. Linked from the Resources index and SE one-pager. | Medium | Done — 2026-09-24, [PR #33](https://github.com/rstamps01/ps-deploy-report/pull/33). Automated posting of results follows as UPL-1. |
| TP-1 | **Tech Port Auto-Discovery and API Proxy Tunnel:** Enable the app to connect to any CBox Tech Port (192.168.2.2) and automatically discover and tunnel API calls to VMS, eliminating manual CBox identification. **Feasibility validated on selab-var-202 (2026-03-28):** (1) `find-vms` returns VMS internal IP (172.16.3.4) from any CNode; (2) SSH hop from non-VMS CNode to VMS internal IP works; (3) `ip addr` on VMS CNode returns management IP (10.143.11.202); (4) API calls to management IP from any CNode return HTTP 403 (auth required = reachable); (5) VMS internal IP does NOT serve HTTPS (000) — must use management IP for API tunnel. **Discovery chain:** SSH Tech Port → `find-vms` → SSH hop to VMS internal IP → extract management IP from `ip addr` → paramiko tunnel to management IP:443. Builds on existing `ssh_adapter.py` proxy hop infrastructure (`direct-tcpip` channels). Diagnostic script at `tests/diag_vms_proxy_feasibility.py`. | High | Done — shipped in v1.5.7 with TP-2 (see `ROADMAP-ARCHIVE.md`); this row is a stale duplicate, archive at the next sweep. Follow-up bug: TP-3. |
| AO-28 | **Switch config backup in Network Configuration Extraction:** Add a full switch config backup step to the One-Shot Network Configuration Extraction workflow (`src/workflows/network_config_workflow.py`). Run `nv config show` (full output, not head-50) on each switch and save the complete config to a file in the output directory (e.g. `switch_config_<ip>.txt`). Include in the result bundle. The existing Tier 3 health check `_check_switch_config_backup` (now renamed to `Switch Config Readability`) only captures a 50-line snippet for verification — the workflow step should capture the full config for backup/reference purposes. | Medium | Planned |
| PROM-1 | **Enhanced Prometheus device metrics capture:** Enrich the Device Health (Prometheus) health check to capture per-device structured data in the JSON details: endurance %, temperature, media errors, power-on hours, power cycles, and active/inactive/failed state for all SSDs and NVRAMs. Add warning thresholds (endurance <80%, temperature >55°C SSD / >65°C NVRAM). Currently only aggregate counts are stored; individual device data is discarded after scanning. Diagnostic script at `tests/diag_prometheus_metrics.py`. | Medium | Planned |
| PROM-2 | **Probe additional Prometheus metric paths (CNode and cluster):** Discover and integrate additional `/api/prometheusmetrics/` paths beyond `devices` (e.g. `cnodes`, `cluster`, `network`, `protocols`, `capacity`). The `devices` path only returns DBox SSD/NVRAM data. CNode metrics (CPU, memory, NIC) may be available at other paths. Use `tests/diag_prometheus_metrics.py` to probe available paths per cluster version. | Low | Planned |

---


## Next steps (current focus)

> **Execution status (2026-10-16):** **v1.6.2 prepared** on `fix/v1.6.2-field-feedback`; next is the PR to `develop` and CI, then `develop` → `main`, tag `v1.6.2` (needs approval). **v1.6.1 shipped** (tag on `7095ccb`). ReportLab 5.x still held ([PR #31](https://github.com/rstamps01/ps-deploy-report/pull/31)); the title-with-table layout depends on ReportLab 4.4 page splitting.

1. **v1.6.2 release:** prepared on `fix/v1.6.2-field-feedback` (version, CHANGELOG, release notes, QA §4, docs and marketing). Remaining: CI green on the PR, merge to `develop`, merge `develop` → `main`, tag `v1.6.2`, verify the GitHub Release artifacts and the live update pill from a 1.6.1 build, then publish: Confluence page, Slack announcement, GOV-3 advisory ([draft](issues/v1.6.2/field-advisory.md)). Each publishing step needs approval.
2. **v1.6.3:** TP-4, FR-7–15, OBS-1, TP-3, and the local diagnostics work HUB-1–9 plus DATA-1.
3. **v1.7.0 minor:** HCF-3/4, INV-2, DRV-1, **RCS-1–5** (Ross install-time logging), HUB-10/11. DRV-2 follows. SW-1 waits on logs.
4. **Results Hub backend (separate repos):** HUB-12–16, then connectors HUB-17–23 in v1.7.x.
5. **v1.6.1 ship-release leftovers:** the live update-pill check from a real 1.6.0 build (QA §6b), and the Slack and Confluence release announcement (draft, then confirm).
6. **Governance:** GOV-1 done on the branch (older docs and git history still name customers; a history rewrite is a separate decision). GOV-2 (vperfsanity upload keys notice) open.
7. **Dependabot backlog:** #28, #29 (types-paramiko 5.x, mypy clean on the branch), #30 and #32 merged 2026-10-16. #31 reportlab 5.0.1 stays on hold for a separately tested branch.
8. **PLN-1:** audit the project plan archive (`docs/plans/`) against CHANGELOG and tags; [`PLANS-INDEX.md`](PLANS-INDEX.md) has the 2026-09-26 re-bucket as the starting point.
9. **Teleport beta exit:** Beta badge and labeling removed on `fix/v1.6.2-field-feedback` (2026-10-08); PR #36 closed as a duplicate.
10. **HWL-3:** done on the branch (EBox models use the library's declared height).
11. **SEC-3 / SEC-4:** plaintext profile credentials; ungated `/validation-results`.
12. **Documentation refresh (remaining):** DOC-13 (API reference Prometheus endpoints), DOC-14 (Confluence sync or rule trim), CFG-1 (template parity).
13. **UI Enhancement Phase (UI-1 through UI-9):** remaining Phase 1–3 items.
14. **Test suite:** TSE-9 (coverage toward 80%).
15. Before each release: update this file (status, Last updated, move completed items to Done).
16. CI validates this file exists and contains required sections (see todo-tracking rule and CI job).

---

## Planned — Port Mapper Integration (low priority)

*Source: Review of Jeff's Port Mapper (pm.py v5.6) — design-time switch port planning tool.*

| ID    | Item | Priority | Status  | Notes |
|-------|------|----------|---------|-------|
| PMI-1 | **Extract switch model metadata:** Extract `SWITCH_LAYOUTS` dictionary (11 switch models: SN3700, SN4600, SN5400, SN5600, Arista 7050DX4/7060DX5/7060X6, Cisco 9332D/9364D/9364E) into shared `src/switch_models.py` reference. Enriches rack diagrams, port mapping reports, and health checks with port counts, native speeds, and vendor names. | Low | Planned | Low effort; immediate value for `rack_diagram.py` and `health_checker.py` model awareness |
| PMI-2 | **Planned-vs-actual port validation health check:** Compare planned port assignments (from Port Mapper output or saved JSON) against actual MAC-to-port mapping collected by `ExternalPortMapper`. Detect wrong port assignments, missing connections, cross-cabled nodes, and reserved ports in use. New Tier 3 health check. | Low | Planned | Requires defining import format for planned port maps; high diagnostic value |
| PMI-3 | **Switch face-plate diagram in reports:** Port the `PortDrawer` class and switch face-plate PNG overlays into the PDF report's Switch Port Mapping section. Color-coded visual port diagrams supplement existing table-based data. | Low | Planned | Medium effort; depends on PMI-1 for model metadata; visually impactful for reports |
| PMI-4 | **Generalized LLDP walk for Mellanox Onyx switches:** `ExternalPortMapper._parse_onyx_lldp_for_ipl` still requires symmetric port numbers on `Eth1/29..Eth1/32`. Port the `switch_hostname_map` / `spine_ips` generalized walk (already live for Cumulus) onto the Onyx path so spine uplinks on arbitrary ports are discovered in Onyx-only deployments. | Low | **Done** | Generalized walk mirrors the Cumulus rewrite; reuses `_classify_edge` / `_resolve_neighbor_to_switch_ip`; legacy narrow scan preserved when no hostname map is supplied. 4 new tests under `TestOnyxLldpGeneralizedWalk`. |
| PMI-5 | **Capture `vnetmap` fabric-report for offline LLDP recovery:** `vnetmap.py` writes `/vast/log/vnetmap-…txt` on cnode-1 with a complete `LLDP neighbors on <IP>:` dump for every switch (leaves **and** spines). Extend `src/workflows/vnetmap_workflow.py` to retrieve that file and append its contents to the main `vnetmap_output_*.txt` the reporter consumes, so `vnetmap_parser._parse_lldp_neighbors` can recover real spine uplinks without any per-switch SSH call. | Low | **Done** | `_step_save_output` now fetches `/vast/log/vnetmap-*.txt` via SSH, appends it behind a delimiter to the saved output, and records `fabric_report_path` / `fabric_report_bytes` in the results JSON. 9 new tests under `TestVnetmapFabricReportCapture` (incl. end-to-end parseability by `VNetMapParser`). |

---

## RFE and other tracking

- **RFE:** Requests for Enhancement from Confluence (page 6664028496) are tracked as GitHub issues or referenced here when work begins.
- **Session-level work:** Use Cursor TODO tracking during sessions; promote agreed next steps to this roadmap.
