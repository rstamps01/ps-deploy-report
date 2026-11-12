# Handoff: v1.6.3 implementation (2026-11-11, evening)

Start here. Code and git outrank this file. Plan: [`plan.md`](plan.md); scope and gates: [`spec.md`](spec.md);
tasks: [`tasks.md`](tasks.md). Owner decisions: `docs/DECISIONS.md` 2026-11-11.

## State

- Plan PR #51 merged to `develop` (`9bbd671`).
- Wave A is in review, each with a green local gate (coverage 74%), green CI and a changelog fragment:
  FR-11 [#52](https://github.com/rstamps01/ps-deploy-report/pull/52), FR-10
  [#53](https://github.com/rstamps01/ps-deploy-report/pull/53), TP-4
  [#54](https://github.com/rstamps01/ps-deploy-report/pull/54), HCF-3
  [#55](https://github.com/rstamps01/ps-deploy-report/pull/55). Review fixes already folded in: FR-11 stale
  `local_path` (second commit); HCF-3 CLI report paths now apply `ReportConfig.from_yaml` (third commit).
- TP-4 #54: independent review says REQUEST CHANGES (details in the PR comment). Blocker: `ResultBundler` writes every bundle to the flat `output/bundles/`, so Tech Port bundles show under Unassigned (legacy) and never under their cluster. Fix in `~/asbuilt-tp4`: pass the per-cluster bundles dir at `oneshot_runner.py:2140` and `app.py:1061`, move the test fixtures to where the app writes (failing-first), plus the two low findings (cluster-scoped file actions; early-exit Unassigned check). Manual UI check is listed in the PR.
- NET-7 (`feature/NET-7-vnetmap-lldp`, pushed, no PR yet): N1–N6 committed (`b528a1f` parser, `9c4cfbe`
  workflow + selector + guardrail test + tool manager, `f026f2f` mapper/diagram). Parent integration N7–N10 next.
- TP-3: owner chose "decide later"; ask again before the release cut, else move to v1.7.0 with the reason.

## Worktrees (one per branch; never switch branches in `~/vast-asbuilt-reporter`)

`~/asbuilt-fr10`, `~/asbuilt-fr11`, `~/asbuilt-tp4`, `~/asbuilt-hcf3`, `~/asbuilt-net7`, `~/asbuilt-tracker`
(`chore/v1.6.3-tracker`). Each has a `venv` symlink (excluded via `.git/info/exclude`). Remove a worktree only
after its PR merges, with owner approval.

## Next agent actions

1. Fix TP-4 #54 first (above). Check #52–#55 for review comments and CI; ask the owner to merge (or for approval to merge) to `develop`.
2. OBS-1 after HCF-3 and FR-7 after FR-10: new worktrees off `develop` once #55 / #53 merge, or stacked on
   those branches if the owner wants to proceed first. One implementer subagent each (current model, not the
   fast tier), failing-first test, parent review + gate + PR.
3. NET-7 parent integration in `~/asbuilt-net7`, per [`../NET-7/plan.md`](../NET-7/plan.md) Design 2, 7–9:
   - N7 `extract_port_mapping` LLDP branch: resolve `switch_name` to VMS `mgmt_ip` (name, hostname,
     case-insensitive, domain stripped); unresolved names become synthetic switches (`mgmt_ip` = name,
     `discovered_via: "lldp"`, `registered_in_vms: False`); set `data_source = "lldp"`, `ipl_connections = []`,
     `isl_discovered = False`. Worker B: the diagram reads `port_mapping_data["isl_discovered"]`, and the
     synthetic switches must also go into the hardware-inventory switches list `report_builder` passes to the
     diagram.
   - N8 Reporter job and One-Shot call `select_topology_source()` before/after vnetmap; output discovery for
     both filename patterns; add `vnetmap_lldp` to One-Shot's node-SSH and download operation sets; bundler
     and Results scanner pick up `vnetmap_lldp_*` files.
   - N9 report source line + "Switch not registered in VMS" note; `data_source.startswith("vnetmap")` gate
     accepts `lldp`. N10 UI select (`vnetmap_source`), config keys, README. Then review, gate, changelog
     fragment, PR.
4. Owner questions for NET-7 (from worker C): Auto falls back to LLDP only when every switch login fails (one
   switch: any auth failure) — OK? Should a failed `switch_mapping.json` restore fail step 3 (today: warn and
   report the backup path)? Confirm `clush -a` covers the intended nodes on the lab cluster.
5. Lab pass (owner): FR-16 T8, FR-7, NET-7 on a cluster with LLDP already active, TP-3 if reproducible.

## Gotchas

- The `bugbot` and `security-review` subagents diff against a stale base (about 85–90 files, apparently
  `main`) and skip most item files; their findings must be verified, and the parent reviews security-sensitive
  code directly. Worth a pipeline fix item.
- `ui-tests` CI can fail at "Install Playwright browsers" when the runner cannot resolve the Ubuntu mirrors;
  re-run the failed job (PR #51 needed four attempts).
- Adding Python 3.10+ syntax to a test file can make black reformat older `with` blocks in it; accept it as
  a separate `style(tests)` commit.
- `~/Downloads/vnetmap-lldp-output.txt` is a real customer capture: format reference only, never copied.
- `vnetmap_lldp.py show-mapping` rewrites `/userdata/switch_mapping.json`; the workflow restores it and the
  guardrail test enforces that. We never pass `-f` and never touch lldpd/lldpad.
- HCF-3 and NET-7 are behavior changes; the v1.6.3 release notes must name them (HCF-3 with the
  `fail_on: none` opt-out). FR-11 deletes with `sudo rm -f`, and a Support Tools size mismatch now fails the step.
