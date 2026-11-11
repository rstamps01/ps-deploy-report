# Handoff: critical fixes + NET-7 vnetmap_lldp (2026-11-10, 18:30 PT)

Start here for the planning chat. Code and git outrank this file. Project state: [`../../BRIEF.md`](../../BRIEF.md). Feature assessment: [`spec.md`](spec.md).

## Owner request (verbatim)

> Switch to plan mode and develop a plan to implement critical fixes along with adding support for vnetmap_lldp and associated lldp related scripts required to replace default vnetmap functionality to generate port map and logical network diagram.

Cost measurement (PIPE-T4) is paused: the cursor-budget-report tool needs changes first. Don't spend effort on it.

## How to run the planning chat

1. Switch to Plan mode. This is a new feature, so the Superpowers `brainstorming` step applies.
2. Run `python3 scripts/context-pack.py NET-7` (writes `docs/issues/NET-7/context.md`), then read `spec.md` in full (5.7 KB).
3. Plans with more than 3 to-dos: hand each to-do to a subagent with the brief, the to-do and its file list (`AGENTS.md`, Working efficiently).
4. Ask the owner the open questions below before writing the final plan.

## Working tree

FR-16 is merged to `develop` ([PR #49](https://github.com/rstamps01/ps-deploy-report/pull/49), `92f3669`); the owner's lab re-run (T8) is still pending. The main checkout `~/vast-asbuilt-reporter` is on `develop` with a clean tree. Do NET-7 work in its own worktree so the two branches never share a checkout:

`git worktree add -b feature/NET-7-vnetmap-lldp ../asbuilt-net7 origin/develop`

Never `git checkout`, `git stash` or `git commit -a` in a checkout another chat is using. On 2026-11-10 a branch switch in the shared tree carried uncommitted FR-16 work into a docs commit (PR #46, closed; nothing lost; backup bundle in `~/git-backups/`).

## Critical fixes: candidates (confirm scope with the owner)

| ID | Item | Priority | State |
| --- | --- | --- | --- |
| FR-16 | vperfsanity Step 4 output stalls, then floods and freezes Chrome | P0, v1.6.3 blocker | **Merged (PR #49).** Lab re-run (T8) before v1.6.3. Don't re-plan it. |
| HCF-3 | Critical alarms only produce a warning (17 critical/major alarms gave a warning in one field run) | P1 | Planned |
| FR-7 | vperfsanity background runner (builds on FR-16) | P1 | Planned |
| DRV-1, RCS-1–5 | Report-content features (drive inventory, friendly model names, RLR count, metadata triplication, 1-strip, vperfsanity figure) | P1 | Planned; enhancements, not fixes |

`docs/TODO-ROADMAP.md` "Release blockers" (line ~47) and "Next steps" (line ~293) are the authoritative lists. Grep them; don't read the whole file.

## NET-7: what exists today

- **Spec** (`spec.md`) sections: Problem, Hard guardrails, What vnetmap_lldp produces, Gap analysis against the vnetmap topology rows, Supplemental LLDP scripts (Confluence 5491851319), Scope when implemented, Acceptance.
- **Hard guardrails (non-negotiable):**
  - never disable, stop, install, enable or start `lldpad` or `lldpd`
  - check readiness read-only (`systemctl is-active`, plus the tool's own `LLDP service status` line)
  - run only `--operation show-mapping` and `dry-run`; never offer `ifdown` or `ifup`
  - field output is never committed; fixtures use ACME and documentation-range IPs (GOV-1)
- **Design in the spec:** a new `VNetMapLLDPParser` that emits the existing topology-row contract, so the current port mapper and diagram render it unchanged.
  - Gaps: switch IP (only the name is known), MAC and network side (derive from subnet), inter-switch links (not discoverable from nodes).
  - The Confluence tcpdump and `nw_check.sh` scripts are optional enrichment (switch IP, MAC, fabric).
- **Tool delivery:** `src/tool_manager.py` downloads `vnetmap.py` from `https://vastdatasupport.blob.core.windows.net/support-tools/main/support/vnetperf/vnetmap.py`. `vnetmap_lldp.py` is in the same `support/vnetperf/` folder but not yet in Update Tools. No local copy exists (`output/tools/` has `vnetmap.py`, `mlnx_switch_api.py`, `vast_support_tools.py`, the vperfsanity tarball).
- **Confluence:** [How to run vnetmap_lldp](https://vastdata.atlassian.net/wiki/spaces/CS/pages/7347404806/How+to+run+vnetmap_lldp), [Use LLDP as an alternative to vnetmap](https://vastdata.atlassian.net/wiki/spaces/CS/pages/5491851319/Use+LLDP+as+an+alternative+to+vnetmap+to+scan+for+switch+connectivity). Fetch the outline first.
- **Code areas (vnetmap path):**
  - workflow, parsing, mapping and diagram: `src/workflows/vnetmap_workflow.py`, `src/vnetmap_parser.py`, `src/external_port_mapper.py`, `src/enhanced_port_mapper.py`, `src/network_diagram_v2.py`
  - tooling and output: `src/tool_manager.py`, `src/result_bundler.py`, `src/oneshot_runner.py`, `src/app.py`, `src/data_extractor.py`, `src/report_builder.py` (over 1,000 lines; grep it)
  - templates: `frontend/templates/reporter.html`, `advanced_ops.html`
  - config: `config/config.yaml.template` (`run_vnetmap`, `include_prior_vnetmap`)
  - tests: `test_vnetmap_*`, `test_e2e_vnetmap_diagram.py`, `test_external_port_mapper.py`, `test_port_mapper.py`, `test_network_diagram_v2.py`, `test_tool_manager.py`, `test_workflows.py`
  - earlier plans: `docs/plans/vnetmap_+_network_diagram_d3e4b87f.plan.md`, `docs/plans/vnetmap_and_log-bundle_teleport_fixes_e9a4abc3.plan.md`
- **Overlap with FR-16 (PR #49):** FR-16 changes `src/app.py`, `src/oneshot_runner.py`, `src/advanced_ops.py`, `src/utils/ssh_adapter.py`, `src/utils/logger.py`, `reporter.html` and `advanced_ops.html`. #49 is merged, so branch NET-7 from current `develop`.

## Open questions for the owner

1. **Replace or fall back?** The request says "replace default vnetmap functionality"; the spec says "fallback when there are no switch credentials". Options: LLDP becomes the default with vnetmap optional; LLDP is used automatically when switch credentials are missing; or the operator picks per run.
2. **Which "associated LLDP scripts"?** `vnetmap_lldp.py` only, or also the Confluence tcpdump / `nw_check.sh` enrichment for switch IP, MAC and fabric?
3. **Release target:** the spec says v1.7.x; v1.6.3 is gated on FR-16. Does NET-7 ride in v1.6.3 or go to v1.7.0?
4. **Critical fixes scope:** FR-16 is already in progress. Is HCF-3 in? Anything from field feedback not in the register?
5. **Lab access:** a cluster with `lldpd` running on the nodes, and real `show-mapping` output (sanitized) for fixtures.

## Next agent actions

Planning is done (2026-11-11). The open questions above are answered in `docs/DECISIONS.md` (2026-11-11) and
[`plan.md`](plan.md). The worktree exists.

1. Read [`../v1.6.3/plan.md`](../v1.6.3/plan.md), [`plan.md`](plan.md) and [`tasks.md`](tasks.md).
2. `start-work`, then `implement-change` per to-do (workers A–C in `plan.md`). Ship tests with every feature and a failing-first regression test with every bug fix.
