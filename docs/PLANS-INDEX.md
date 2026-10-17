# Plans Index

Reconciliation of the prior Cursor plan files (in the shared `~/.cursor/plans/`) against the actual shipped state of this repository (release tags + `CHANGELOG.md`) — so there is one place that says which plans shipped, which were superseded, and which have genuinely open scope (pipeline §9).

**Last reconciled:** 2026-07-31 — 173 plan files scanned (103 belong to this repo; 70 belong to other projects). **Partial re-bucket 2026-09-26:** the 24 archived plans with open todos (see the section below the buckets).

**Archive:** since 2026-09-25, redacted copies of this repo's plans are versioned in [`plans/`](plans/README.md). That's 93 plans: the 103 above, minus the 12 deleted on 2026-07-31, plus 14 plans found during the archive build or created since. Plans from other projects in the shared directory are excluded. Audit against the archive rather than `~/.cursor/plans/`. **Re-reconciliation pending (PLN-1):** 14 archived plans aren't bucketed below yet (`bug_tracking_documentation_update`, `dashboard_mechanical_odometer`, `odometer_design_review`, `ebox_label_&_sort_fix`, `fix_stepper_layout_issues`, `fix_ui_consistency`, `one-shot_report_fixes`, `reorder_sections_fix_config`, `test_suite_log_colors`, `test_suite_success_box`, `v1.5.0_pre-release_completion`, `v1.5.0_release_readiness`, `field_feedback_triage`, `thread_handoff_prep`).

## Method

Each related plan is validated against reality and sorted into one bucket:

- **A. Shipped, frontmatter stale** — work that shipped but the plan still reads not-started/in-progress → treat as Done.
- **B. Superseded / duplicate / empty stub** — replaced by a later plan or empty → annotate; empties/dupes proposed for deletion.
- **C. Mostly shipped, minor tail** — validate the residual; close if done, else promote the tail into `TODO-ROADMAP.md`.
- **D. Genuinely open** — real remaining scope → tracked in `TODO-ROADMAP.md` where in-scope.

> **Guardrail:** plan-file deletions are surfaced as a **reviewable batch for approval** (they live in a shared directory); nothing is deleted without sign-off, and approvals are recorded in [`DECISIONS.md`](DECISIONS.md).

## Summary counts

| Bucket | Count | Meaning |
|--------|-------|---------|
| A — shipped, frontmatter stale | 82 | Done; frontmatter never updated |
| B — superseded / duplicate / empty | 13 | Replaced or empty (12 proposed for deletion) |
| C — mostly shipped, minor tail | 4 | Small residual tracked below |
| D — genuinely open | 4 | 2 already tracked, 2 new candidates |
| Not this repo | 70 | Belong to other projects in the shared plans dir |
| **Total** | **173** | |

## Bucket A — Shipped, frontmatter stale (82)

All correspond to features already in `CHANGELOG.md` / released tags; the plan frontmatter simply was never flipped to Done. Representative mapping (full list preserved in the 2026-07-31 reconciliation memlog):

- **v1.4.x foundational:** `auto_switch_placement`, `manual_switch_placement`, `hardware_device_library`, `extract_hardware_bezel_images`, `update_device_mappings`, `self-contained_app_packaging`, `tech_port_api_tunnel`.
- **v1.5.0 (bulk):** `advanced_configuration_ui`, `advanced_ops_final_phases`, `oneshot_mode_aligned_plan`, `one-shot_ui_overhaul`, `health_check_full_build`, `health_check_fresh_branch_port`, `post_install_validation_gap_analysis`, `rack_diagram_status_indicators` (RPT-3), `post-deploy_status_updates` (RPT-2), `cnode_management_status_check` (HC-1), `fix_pre-release_bugs` (BUG-1..6), `fix_margin_layouterror`, `fix_one-shot_route_guard`, `fix_port_mapping_issues`, `fix_pre-validation_cancel`, `portrait_diagram_redesign`, `output_results_color_coding`, `dashboard_quick_start_revamp`, `add_profiles_to_pages`, `default_credentials_toggle`, `vast_logo_progress_indicator`, `progress_indicator_options`, `project_housekeeping_cleanup`, and the v1.5.0 release plans (`v1.5.0_release_plan`, `_readiness`, `_pre-release_completion`, `pre-release_readiness_plan`, `docs_update_and_rc1_tag`, `confluence_update_v1.5.0`).
- **v1.5.1:** `app_heading_restyle`, `granular_progress_tracking`, `network_diagram_enhancement`, `github_pages_+_readme_banner`, `fix-bundle-collection-gaps`, `nav_devmode_and_log_levels`, `relocate_report_tuning_ui`, `reports_tabs_bundle_fix`.
- **v1.5.6:** `rm-16_oneshot_report_auth_parity`.
- **v1.5.7:** `tech-port_stack_v1.5.7` (TP-1/TP-2/SR-1..5), `ib_diagram_rack_switch_placement`.
- **v1.5.8:** `allow_duplicate_switch_names`, `macos_intel_support`, `disable_auto-shutdown_by_default`, `docs_and_sample-data_cleanup`, `fix_beta_release_latest`, `node_management_map_table` (QP-1), `one-pager_v1.5.8_refresh`, `v1.5.8_release_batch`, `v1.5.8_release_prep`.
- **Done, roadmap-cited:** `segment_results_by_psnt` (QP-2, 2026-06-16), `teleport_connection_option` (TPM-1, 2026-06-19).
- **Unreleased / staged for [1.6.0]:** `teleport_tsh_discovery`, `fix_run-result_issues` (VAST-PI-01), `vnetmap_and_log-bundle_teleport_fixes`.
- **Foundational / infra:** `ci_cd_pipeline_implementation`, `restore_atlassian_mcp` (env).
- **Local dev tooling (repo `tools/`), not release features:** `op_tracer_framework`, `op_tracer_web_ui`, `analyzer_gitignore_+_ui_overhaul`, `se_marketing_one-pager`.
- **Ongoing test-coverage (TSE):** `test_coverage_extension_plan`, `test_coverage_phase_a-c`.

## Bucket B — Superseded / duplicate / empty (13)

| Plan file | Reason | Superseded by |
|-----------|--------|---------------|
| `dual_legend_plan_(top_swatches_+_bottom_pills)` | NET-2 mockup iteration, superseded | `top-center_pill_legend_plan` |
| `health_check_module` | Early spec, all-pending | `health_check_full_build`, `health_check_fresh_branch_port` |
| `one-shot_mode_advanced_ops` | Early draft, all-pending | `oneshot_mode_aligned_plan` |
| `one-shot_switch_placements` | Early draft, all-pending | `one-shot_ui_overhaul` |
| `port_mapping_and_diagram_fixes` | Duplicate scope, all-pending | `node_management_map_table` (QP-1) |
| `portrait_mockup_adjustment_plan` | NET-2 mockup iteration, superseded | `dual_legend_plan` → `top-center_pill_legend_plan` |
| `pywebview_native_window` | Marked done but no `pywebview` dep exists — approach abandoned for browser-launched Flask UI | n/a (abandoned) |
| `reporter_page_staging` | Early draft of Reporter restructure | `switch_placement_modal` + `switch_discovery_workflow` |
| `restore_atlassian_mcp_a8ab1681` | Empty stub (`todos: []`) | `restore_atlassian_mcp_4487dc26` |
| `rpt-6_net-2_diagram_fixes` | Near-duplicate/earlier draft | `v1.5.8_release_batch` |
| `top-center_pill_legend_plan` | Mockup-only; production already matches (v1.5.7) | n/a (mockup obsolete) |
| `ui_and_software_mgmt_enhancements_e6c62c5d` | Empty stub (`todos: []`) | `ui_and_software_mgmt_enhancements_a24a071a` |
| `vnetmap_port_mapping` | Early draft, smaller scope | `vnetmap_+_network_diagram` |

## Bucket C — Mostly shipped, minor tail (4)

| Plan file | Topic | Residual |
|-----------|-------|----------|
| `pre-release_cleanup` | v1.5.8 pre-release cleanup | `pre-1.5.8-cleanup` tag exists (done); orphan `config/hardware_images/ebox_1u.png` may remain — verify/remove |
| `switch_discovery_workflow` | Reporter switch discovery rework | `field-styling` CSS task still pending (fold into UI-5 foundation restyle) |
| `tp-1_fix_+_ui_investigation` | TP-1 fix + UI side-findings | Phase-2 UI write-up covered by `tp-1_ui_repro`; see roadmap RPT-VALIDATION-1/2 |
| `ui_and_software_mgmt_enhancements_a24a071a` | QP-3 tools nav / auto-update / autoclose / telemetry | Item 2b (auto-apply/relaunch) explicitly deferred (roadmap) |

## Bucket D — Genuinely open (4)

| Plan file | Topic | Disposition |
|-----------|-------|-------------|
| `agentic_cicd_pipeline` | Agentic CI/CD pipeline (M0→M4) | **Already tracked** — active on `develop`; no new ID |
| `api_health_check_report` | Ad-hoc selab-var-203 health debrief | Operational one-off, not product scope — no tracking |
| `protect_main_branch` | GitHub branch protection on `main` | **New — proposed SEC-2 (Medium).** `main` confirmed unprotected; add to roadmap |
| `expose_asbuilt-reporter_remotely` | Expose app via Windows `netsh portproxy` | **New — proposed OPS-1 (Low), if still needed.** Add to roadmap pending confirmation |

## 2026-09-26 re-bucket: archived plans with open todos (24)

Starting point for PLN-1. Covers only the 24 archived plans in [`plans/`](plans/README.md) whose frontmatter still has pending todos, checked against `CHANGELOG.md`, tags and the roadmap. The frontmatter in the archived copies is not edited here; PLN-1 does that.

**Active or tracked (open scope is real):**

| Plan | Open todos | Disposition |
|------|-----------|-------------|
| `field_diagnostics_pipeline_9b6d157c` | 38/39 | **Active.** Phase 1 is largely on the v1.6.2 branch (FR-1–6); partial items and Phases 2–6 are tracked as FR-7–15, OBS-1, TP-3, HUB-1–23, DATA-1. |
| `expose_asbuilt-reporter_remotely_8b7d907f` | 7/7 | Tracked as OPS-1 (confirm need). |
| `agentic_cicd_pipeline_2eb2e257` | 1/46 | Only the optional phase-2 patterns remain; now tracked as PIPE-1. |
| `protect_main_branch_1260e0f8` | 3/4 | SEC-2 done; optional `develop` protection now tracked as SEC-5. |
| `switch_discovery_workflow_8950f43a` | 1/7 | `field-styling` CSS task; fold into UI-5. |
| `nav_devmode_and_log_levels_7a0eb56b` | 1/10 | Remaining item is AO-20 (tracked). |
| `post_install_validation_gap_analysis_0e446ebb` | 3/13 | Bundling, tests and the CI job exist; the remaining items overlap HUB-2/HUB-9. Verify and close in PLN-1. |

**Shipped, frontmatter stale (Bucket A; tick in PLN-1):**

| Plan | Open todos | Evidence |
|------|-----------|----------|
| `field_feedback_triage_1d3ae704` | 5/5 | Roadmap section, DECISIONS entry, PR #34. |
| `pre-release_cleanup_5baaebf3` | 8/8 | `pre-1.5.8-cleanup` tag. |
| `pre-release_readiness_plan_7c8c6a1f` | 3/10 | v1.5.8 shipped. |
| `v1.5.8_release_prep_28d74930` | 11/11 | v1.5.8 tag. |
| `v1.5.8_release_batch_abeea236` | 22/22 | v1.5.8 tag. |
| `tech-port_stack_v1.5.7_4ee5b210` | 1/18 | v1.5.7 tag; TP-1/TP-2 archived. |
| `segment_results_by_psnt_739a98da` | 7/7 | QP-2 done. |
| `node_management_map_table_6c99be75` | 7/7 | QP-1 done. |
| `ui_and_software_mgmt_enhancements_a24a071a` | 7/7 | QP-3 done; item 2b deferred on the roadmap. |
| `macos_intel_support_ef739002` | 4/4 | arm64 and x64 DMGs ship. |
| `dashboard_mechanical_odometer_069590fe` | 3/3 | Shipped. |
| `cnode_management_status_check_030edbce` | 2/2 | HC-1, v1.5.0. |
| `restore_atlassian_mcp_4487dc26` | 3/3 | The Atlassian MCP works. |
| `bug_tracking_documentation_update_6cbbc0ee` | 4/4 | BUG-1–6 in `ROADMAP-ARCHIVE.md`. |
| `tp-1_fix_+_ui_investigation_a2760958` | 1/7 | RPT-VALIDATION-1/2 fixed on the v1.6.2 branch. |
| `thread_handoff_prep_3cdd35ba` | 1/8 | Handoff delivered. |

**Not product scope:** `api_health_check_report_c3c36f66` (2/2), an operational one-off cluster debrief. No tracking.

## Not this repo (70)

Plans belonging to other projects sharing `~/.cursor/plans/`: **"Chef's Kiss" recipe app** (~24, incl. the `recipe_data_import_pipeline_*` series), **VAST Plan Analyzer** (~11), **Mission Control portal** (~11), **Install Daily Dashboard** (~9), **post-sales process initiative** (~6), **Docker/Keycloak local dev** (~6 `local_dev_environment_setup_*`), **global Cursor environment / personal skills** (~5), plus ad-hoc cluster debriefs. These are out of scope for this repo and are left untouched.

## Proposed deletion batch (awaiting approval)

Conservative — empties, exact duplicates, and fully-superseded early drafts only (12 files). `pywebview_native_window` is retained (abandoned but historically informative). **Nothing is deleted without explicit approval.**

```
health_check_module_1c149000
one-shot_mode_advanced_ops_ac6abdd0
one-shot_switch_placements_2355f179
port_mapping_and_diagram_fixes_12c5bda6
portrait_mockup_adjustment_plan_c7840a11
dual_legend_plan_(top_swatches_+_bottom_pills)_70a9aec2
top-center_pill_legend_plan_426c8374
reporter_page_staging_a876a261
restore_atlassian_mcp_a8ab1681
rpt-6_net-2_diagram_fixes_25165519
ui_and_software_mgmt_enhancements_e6c62c5d
vnetmap_port_mapping_9b18693e
```

Status: **deletion batch approved and executed 2026-07-31** — all 12 files removed from `~/.cursor/plans/` (173 → 161 plan files). `pywebview_native_window` was retained by design. Recorded in [`DECISIONS.md`](DECISIONS.md).
