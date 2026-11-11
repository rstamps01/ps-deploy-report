# TODO & Roadmap — Planned Features and Enhancements

**Purpose:** Canonical **live** register of planned and in-progress work. Completed history lives in [`ROADMAP-ARCHIVE.md`](ROADMAP-ARCHIVE.md); shipped detail is in [`../CHANGELOG.md`](../CHANGELOG.md); the current point-in-time snapshot is in [`PROJECT-STATUS.md`](PROJECT-STATUS.md). Validated in CI (todo-tracking-09).

**Last updated:** 2026-11-10 — **FR-16 merged** to `develop` in [PR #49](https://github.com/rstamps01/ps-deploy-report/pull/49) (live Step 4 output, elbencho frame collapse, batched output pane); lab re-run (T8) pending. Before that: **PIPE-T1 token-efficiency workflow merged** to `develop` ([#44](https://github.com/rstamps01/ps-deploy-report/pull/44)); row archived, KPI re-measure tracked as PIPE-T4 (due 2026-11-24).

**Earlier update:** 2026-10-23 — **FR-16 logged as a v1.6.3 release blocker** (vperfsanity shows no output during Step 4, then a flood of output freezes the browser; a field engineer's Chrome tab hung). Must be fixed before v1.6.3 is cut; work not started. Spec: [`issues/FR-16/spec.md`](issues/FR-16/spec.md).

**Previous update:** 2026-10-17 — v1.6.2 shipped (details in [`DECISIONS.md`](DECISIONS.md) and [`../CHANGELOG.md`](../CHANGELOG.md)).

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

## Release blockers — must be fixed before the next release (v1.6.3)

*Source: lab vperfsanity run on a 3-CNode cluster (2026-10-23) and a field report of a Chrome hang during the same operation (field logs requested). Do not cut v1.6.3 until these are Done.*

| ID | Item | Type | Priority | Size | Target | Status | Notes |
|------|------|------|----------|------|--------|--------|--------|
| FR-16 | **vperfsanity output stalls, then a flood of output freezes Chrome.** Step 4 shows nothing in Output Results for the whole write → burst-recovery wait → read sequence, then dumps everything at once. In the lab run, the page went silent for 18.5 min and then froze for about 90 s adding about 12,400 lines. On a larger cluster a field engineer's Chrome tab hung. Causes: (1) `_step_run_tests` uses a blocking `run_ssh_command` and emits output only after the script exits; (2) `force_tty=True` captures every elbencho full-screen redraw (about 1,500 frames, 2.2 MB); (3) the output pane's `append` re-serializes the whole history into `sessionStorage` and forces a layout on every line (`reporter.html` and `advanced_ops.html`), so cost grows with the square of the line count; (4) werkzeug access lines for the page's own polls are streamed back into the panel; (5) a new tab replays all output through the same path. | Bug | P0 | M | v1.6.3 (blocker) | In review | Merged in [PR #49](https://github.com/rstamps01/ps-deploy-report/pull/49) (`92f3669`); stays open until the lab re-run with a full Step 4 (T8) still needed. Branch `fix/FR-16-vperfsanity-output-stall` (started 2026-11-10; plan [`issues/FR-16/plan.md`](issues/FR-16/plan.md)). Spec and acceptance criteria: [`issues/FR-16/spec.md`](issues/FR-16/spec.md). Fix: stream Step 4 output live, collapse elbencho frames to progress lines, post burst-wait status, batch and cap the output pane, drop werkzeug lines from `/stream/logs`. The 13m27s write-to-read gap itself is vperfsanity's burst-recovery wait (by design). Does not wait on FR-7. Field workaround until fixed: don't quit the app; close only the frozen tab and don't reopen the page until the run ends. |

---

## Planned — Pipeline & ops follow-ups (2026-07-31)

*Source: prior-plan reconciliation (see [`PLANS-INDEX.md`](PLANS-INDEX.md), Bucket D). Genuinely-open items surfaced from `~/.cursor/plans/` that are in-scope for this repo.*

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| OPS-1 | **Remote access to the reporter app (Windows `netsh portproxy`).** Document/support exposing the local Flask UI to a remote operator via a Windows port-proxy hop, for field machines where the browser runs elsewhere. | Low | Planned (confirm need) | From plan `expose_asbuilt-reporter_remotely_8b7d907f`. Confirm this is still needed before implementing. |
| SEC-3 | **Cluster profiles store credentials in plaintext.** `config/cluster_profiles.json` holds saved passwords and API tokens unencrypted on disk. | Medium | Deferred (documented) | Surfaced while rewriting `DEPLOYMENT.md` for v1.6.1 and documented there as a caveat. Deferred by decision on 2026-08-01: encrypting it needs a key-storage decision and a migration path for existing profiles, neither of which should ride along in a patch release. |
| SEC-4 | **`/validation-results` is not behind the Developer Mode guard.** `architecture-03` lists the route as Developer-Mode-only, but it is reachable in a normal session. | Low | Deferred (documented) | Surfaced during the v1.6.1 docs audit. Deferred by decision on 2026-08-01: gating it now would withdraw access someone may be relying on, so confirm nobody depends on it first, then either gate the route or correct `architecture-03`. |
| GOV-2 | **vperfsanity package embeds long-lived upload keys.** | Medium | Planned | Notify the vperfsanity owner. Never reuse the keys; HUB-21 replaces the upload path. The keys are not bundled in the DMG (`output/tools/` is not packaged). |
| GOV-3 | **Field advisory for v1.6.1 users.** EBox Support Tools, vperfsanity timeout and cleanup, switches missing from VMS. | Medium | In progress | Drafted 2026-10-16: [`issues/v1.6.2/field-advisory.md`](issues/v1.6.2/field-advisory.md). Post to Slack before v1.6.2 ships, then add the release link. |
| SEC-5 | **Optional branch protection on `develop`.** | Low | Planned | Follow-up to SEC-2 (plan `protect_main_branch_1260e0f8`). |
| PIPE-T2 | **Optional `pytest-xdist` for local full runs.** `scripts/quality-gate.sh --parallel` is wired; add `pytest-xdist` to `requirements-dev.txt` once the suite is verified xdist-safe (network guard, shared fixtures). | Low | Planned | From PIPE-T1 Phase 7. |
| PIPE-T3 | **Split the largest modules for cheaper reads.** `report_builder.py` (266 KB) by section, `app.py` routes into Blueprints, plus a complexity ratchet (Gap Analysis S1–S3). | Medium | Planned | From PIPE-T1 Phase 6; do incrementally with feature work. |
| PIPE-T4 | **Re-measure PIPE-T1 KPIs (due 2026-11-24).** Run `make report` in `cursor-budget-report` and compare against the KPI and tripwire tables in [`issues/PIPE-T1/spec.md`](issues/PIPE-T1/spec.md); revert the latest intervention if a tripwire worsens by more than 10%. | Medium | Paused | Paused 2026-11-10 by the owner: cursor-budget-report needs changes before it can measure. |
| PIPE-1 | **Optional agentic pipeline phase-2 patterns:** dependency graph, next-actionable selector, fix-bug path. | Low | Planned | From plan `agentic_cicd_pipeline`. |
| PLN-1 | **Audit the project plan archive.** Re-check every plan in [`plans/`](plans/README.md) against `CHANGELOG.md` and release tags. Re-bucket each as A–D in [`PLANS-INDEX.md`](PLANS-INDEX.md), mark stale frontmatter as done in the archived copies, and move any genuine open work into this roadmap. Then call `scripts/sync-cursor-plans.py --check` from the `update-tracker` skill so new plans don't go untracked. | Medium | Planned | The archive was created 2026-09-25. The last reconciliation was 2026-07-31. |

---

## Planned — Field feedback (2026-09-23)

*Source: field feedback on v1.6.x (health check output, node identity, drive firmware). The triage plan with the full assessment is archived at [`plans/field_feedback_triage_1d3ae704.plan.md`](plans/field_feedback_triage_1d3ae704.plan.md). Accepted 2026-09-25; decisions are in [`DECISIONS.md`](DECISIONS.md).*

One root cause runs through several of the health check items: `HealthCheckResult.details` is collected but never shown, in either the PDF (`_create_health_check_section`) or `health.html`. HCF-6 fixes that and unblocks HCF-3 and HCF-5.

| ID | Item | Type | Priority | Size | Target | Status | Notes |
|------|------|------|----------|------|--------|--------|--------|
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
| FR-7 | **vperfsanity background runner.** Detached remote run with polled heartbeat (write / burst wait + fill % / read), stall detector, effective Cancel, Quick vs Full dataset. | Enhancement | P1 | M | v1.6.3 | Planned | Needs lab validation. FR-16 (release blocker) delivers live Step 4 output first; FR-7 builds on it. |
| FR-8 | **Use manual `+Switch` entries as a switch source.** Accept IPs, or hostnames resolved on the CNode; validate input in the UI. | Enhancement | P2 | S-M | v1.6.3 | Planned | Today manual entries only place switches in the rack diagram. |
| FR-9 | **Log bundle from all CNodes/DNodes.** | Enhancement | P2 | M | v1.6.3 | Planned | Via clush, bounded by age/size. |
| FR-10 | **Paramiko SSH path has no overall deadline.** `recv_exit_status()` can block past the timeout on Windows (no sshpass). | Bug | P2 | S | v1.6.3 | Planned | Deadline loop that keeps partial output; rework the existing paramiko mocks. |
| FR-11 | **Remote archives left on the cluster.** `/tmp/vast_log_bundle_*.tar.gz` stays on the CNode and `/userdata/*-support_tool_logs_*.tgz` on the VMS host after download. | Bug (hygiene) | P3 | S | v1.6.3 | Planned | Remove after a verified download; the HUB-4 residue check reports anything left. |
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

*All items in this section are done; see [ROADMAP-ARCHIVE.md](ROADMAP-ARCHIVE.md).*

---


## Planned — Test suite enhancements (pre-release QA)

*Source: PRE-RELEASE-QA-GAP-ANALYSIS.md §6.3*

| ID   | Item | Priority | Status   | Notes |
|------|------|----------|---------|--------|
| TSE-9 | **Coverage — low-coverage modules:** Expand tests for external_port_mapper, rack_diagram, report_builder, health_checker, tool_manager, script_runner, workflows to raise total coverage toward 80% | Lower | In progress | Phase A-C complete: +98 tests across 8 work streams; coverage 53%→56%; dead-code modules archived; external_port_mapper, rack_diagram, health_checker, tool_manager, script_runner, workflows augmented |

---

## Planned — Quality gates and pre-release checklist

| ID   | Item | Status   | Notes |
|------|------|----------|--------|
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

*All items in this section are done; see [ROADMAP-ARCHIVE.md](ROADMAP-ARCHIVE.md).*

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
| RFE-6 | Container deployment option | Planned | |
| RFE-7 | Update deployment procedures | Planned | |
| RFE-8 | Package as Mac.app / Win.msi | Planned | |
| RFE-9 | Add recommended next steps | Planned | |
| RFE-10 | Add Alert Summary | Planned | |
| RFE-11 | Create .json export database | Planned | |
| RFE-12 | Fix DC/DBox Rack naming | Deferred | Needs concrete bug report; depends on RFE-13 (now fixed) |
| RFE-14 | Check capacity calculations | Deferred | No local calculations (API pass-through); needs specific discrepancy report |

---

## Planned — Network mapping fallbacks (2026-10-16)

| ID | Item | Priority | Target | Status | Notes |
|------|------|----------|--------|--------|--------|
| NET-7 | **vnetmap fallback to `vnetmap_lldp.py` for customer-managed switches.** With no switch credentials, build the port map and network diagram from node-side LLDP (`vnetmap_lldp.py --operation show-mapping`) and add `vnetmap_lldp.py` to Update Tools. **Never** disable/enable/install/start `lldpad` or `lldpd` (customer coordination required); readiness is checked read-only, and `ifdown`/`ifup` are never offered. | Medium | v1.7.x (owner to confirm) | Planning | Requested 2026-11-10 with the critical fixes; handoff: [`issues/NET-7/handoff.md`](issues/NET-7/handoff.md). Assessment: [`issues/NET-7/spec.md`](issues/NET-7/spec.md). A new `VNetMapLLDPParser` emitting the existing topology-row contract lets the current mapper and diagram render it; gaps are switch IP (name only), MAC and network side (derive from subnet), and inter-switch links (not discoverable from nodes). The Confluence tcpdump/`nw_check.sh` scripts are optional enrichment (switch IP, MAC, fabric) and also leave lldpd untouched. No existing roadmap item covered this. |

## In progress

*(Move items here when work starts; move to Done when complete.)*

| ID | Item | Notes |
|------|------|--------|
| — | *Nothing in progress.* | v1.6.2 shipped 2026-10-17; v1.6.3 work has not started. |

## Planned — Tech-Port follow-ups (v1.5.7+)

*All items in this section are done; see [ROADMAP-ARCHIVE.md](ROADMAP-ARCHIVE.md).*

## Planned — UI Enhancement & Restyle (phased)

| ID | Item | Priority | Status | Notes |
|------|------|----------|--------|--------|
| UI-4 | **Enhanced checklist rows:** Card-style elevated container, right-aligned status tags, post-completion green Passed indicators | Medium | Planned | Part of Phase 1 foundation |
| UI-5 | **Phase 1 — Foundation restyle:** Update app.css :root tokens, shared components (cards, buttons, forms, tables, toggles, badges); pill segmented controls; cascades to all pages | Medium | Planned | ~2 hours; highest ROI |
| UI-8 | **Phase 2 — Advanced Ops restyle:** Apply stepper/checklist/modal patterns from Reporter to Advanced Ops page | Low | Planned | ~1-2 hours; largely copy-paste from Reporter |
| UI-9 | **Phase 3 — Remaining pages:** Polish Dashboard, Results, Library, Docs, Config, Generate, Health pages with foundation styles | Low | Planned | ~2-3 hours; most benefit from Phase 1 automatically |

---

## Planned — Future enhancements

| ID | Item | Priority | Notes |
|------|------|----------|--------|
| UPL-1 | **Automated results posting:** Field compliance with the Field Procedure (DOC-16) depends on engineers manually attaching the as-built PDF, JSON, and validation bundle to the SFDC account (Notes & Attachments) and the `#internal-<customer>` Slack thread. Add an in-app "post results" action after a Test Suite run. Needs: auth model for SFDC and Slack, customer/account mapping from the cluster profile, and credential storage consistent with SEC-3. | Medium | Superseded by HUB-10 (upload client) and HUB-17–20 (Mission Control relay to Slack and SFDC) |
| AO-18 | **Validation Results page (dev mode):** Browse all operation results with tabs and profile-based cluster filtering. Will replace production Reports page when Post Deployment Validation is fully released. | Medium | result_scanner.py, app.py, validation_results.html — implemented, needs polish |
| AO-20 | **Generate Report page enhancements:** Apply log level selector (Status/Live/Debug), persistent log storage with 1GB capacity, and window state persistence to the Generate Report page. Align Generate page UX with Advanced Ops improvements. | Low | Future work — apply patterns from AO-19 to generate.html and report generation pipeline |
| UPD-1 | **In-app self-update mechanism:** Add ability for the application to check for, download, and apply updates (hot-fixes and new versions) from GitHub Releases. Workflow: (1) Check current version against latest GitHub Release tag; (2) Display update notification with release notes when newer version available; (3) User-initiated download of platform-appropriate artifact (.dmg / .zip); (4) Apply update and restart. Consider: auto-check on launch (configurable), manual check via UI button, rollback capability, update channel (stable vs pre-release), signature verification for downloaded artifacts. | Medium | Future enhancement; reduces manual update friction for field-deployed instances |
| CFG-1 | **Configuration template refresh:** Update `config/config.yaml.template` to reflect all settings, features, and enhancements added since last update. Ensure parity between template and runtime config keys. Document new keys (ops_log settings, SSH proxy defaults, reporter defaults) in README Configuration section. | High | Planned — re-scoped 2026-09-26. The template is still drifting (for example the `vperfsanity_timeout_s` override is undocumented). Add a CI key-parity check between the template and the keys the code reads. |
| DOC-9 | **RELEASE_NOTES_v1.5.0.md — Add recent changes:** Add to Highlights and New Features: (1) Advanced Configuration UI with Report Tuning Tool; (2) Report formatting fixes (organization, margins, page numbers, font family, blank page on page 9); (3) VIP Pools status changed from fail to warning with render-time fixup; (4) Reporter UI config wiring (SSH, health check, advanced ops settings initialized from config.yaml); (5) Advanced Config deep-merge save prevents config key loss; (6) Prometheus diagnostics script for future metric evaluation. Update Known Limitations: remove AO-15/AO-19 if complete; note pending font-family troubleshooting task. | High | Deferred — obsolete. v1.5.0 shipped and its release notes are frozen; archive at the next sweep. |
| DOC-13 | **docs/API-REFERENCE.md — Prometheus and monitoring endpoints:** Verify Prometheus metric endpoints (`/api/prometheusmetrics/{path}`) are documented with available paths (devices, cnodes, cluster, network, etc.). Check if monitoring endpoints section references removed SNMP/syslog endpoints and remove if present. Confirm `nb_eth_mtu` field reference in network settings. Update "Last updated" date. | Low | Planned |
| DOC-14 | **Confluence docs sync (`docs/confluence/`):** Refresh local copies of Confluence design/requirements pages (page 6664028496) before v1.5.0 release using Atlassian MCP tools. Ensure RFE table and version references reflect current state. Directory currently empty — requires initial download or re-sync from Confluence. | Medium | Planned — the always-applied rule `design-guidelines-01.mdc` references about 25 files in this empty directory, so every session loads dangling references. Either run the sync or trim the rule to the Confluence page link (rule change via PR). |
| AO-28 | **Switch config backup in Network Configuration Extraction:** Add a full switch config backup step to the One-Shot Network Configuration Extraction workflow (`src/workflows/network_config_workflow.py`). Run `nv config show` (full output, not head-50) on each switch and save the complete config to a file in the output directory (e.g. `switch_config_<ip>.txt`). Include in the result bundle. The existing Tier 3 health check `_check_switch_config_backup` (now renamed to `Switch Config Readability`) only captures a 50-line snippet for verification — the workflow step should capture the full config for backup/reference purposes. | Medium | Planned |
| PROM-1 | **Enhanced Prometheus device metrics capture:** Enrich the Device Health (Prometheus) health check to capture per-device structured data in the JSON details: endurance %, temperature, media errors, power-on hours, power cycles, and active/inactive/failed state for all SSDs and NVRAMs. Add warning thresholds (endurance <80%, temperature >55°C SSD / >65°C NVRAM). Currently only aggregate counts are stored; individual device data is discarded after scanning. Diagnostic script at `tests/diag_prometheus_metrics.py`. | Medium | Planned |
| PROM-2 | **Probe additional Prometheus metric paths (CNode and cluster):** Discover and integrate additional `/api/prometheusmetrics/` paths beyond `devices` (e.g. `cnodes`, `cluster`, `network`, `protocols`, `capacity`). The `devices` path only returns DBox SSD/NVRAM data. CNode metrics (CPU, memory, NIC) may be available at other paths. Use `tests/diag_prometheus_metrics.py` to probe available paths per cluster version. | Low | Planned |

---


## Next steps (current focus)

> **Execution status (2026-10-17):** **v1.6.2 shipped** (tag on `9111ca2`; `main` = `develop`). Next is v1.6.3. ReportLab 5.x still held ([PR #31](https://github.com/rstamps01/ps-deploy-report/pull/31)); the title-with-table layout depends on ReportLab 4.4 page splitting.

0. **Release blocker for v1.6.3: FR-16** (vperfsanity output stall and Chrome hang). Fix and lab-verify before cutting v1.6.3. Field logs from the engineer whose browser hung have been requested. Merged in PR #49; lab re-run pending (2026-11-10).
1. **v1.6.2 ship-release leftovers:** confirm the UPDATE AVAILABLE pill on a real 1.6.1 install (the live API check passed), then publish: Confluence page, Slack announcement, GOV-3 advisory ([draft](issues/v1.6.2/field-advisory.md)). Each publishing step needs approval.
2. **v1.6.3:** FR-16 (blocker, above), TP-4, FR-7–15, OBS-1, TP-3, and the local diagnostics work HUB-1–9 plus DATA-1.
3. **v1.7.0 minor:** HCF-3/4, INV-2, DRV-1, **RCS-1–5** (Ross install-time logging), HUB-10/11. DRV-2 follows. SW-1 waits on logs.
4. **Results Hub backend (separate repos):** HUB-12–16, then connectors HUB-17–23 in v1.7.x.
5. **v1.6.1 ship-release leftovers:** the live update-pill check from a real 1.6.0 build (QA §6b), and the Slack and Confluence release announcement (draft, then confirm).
6. **Governance:** GOV-1 done on the branch (older docs and git history still name customers; a history rewrite is a separate decision). GOV-2 (vperfsanity upload keys notice) open.
7. **Dependabot backlog:** #28, #29 (types-paramiko 5.x, mypy clean on the branch), #30 and #32 merged 2026-10-16. #31 reportlab 5.0.1 stays on hold for a separately tested branch.
8. **PLN-1:** audit the project plan archive (`docs/plans/`) against CHANGELOG and tags; [`PLANS-INDEX.md`](PLANS-INDEX.md) has the 2026-09-26 re-bucket as the starting point.
9. **Teleport beta exit:** shipped in v1.6.2; PR #36 closed as a duplicate.
10. **HWL-3:** shipped in v1.6.2 (EBox models use the library's declared height).
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

---

## RFE and other tracking

- **RFE:** Requests for Enhancement from Confluence (page 6664028496) are tracked as GitHub issues or referenced here when work begins.
- **Session-level work:** Use Cursor TODO tracking during sessions; promote agreed next steps to this roadmap.
