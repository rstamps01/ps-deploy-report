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

## Shared working tree: don't touch it

The main checkout `~/vast-asbuilt-reporter` is on `fix/FR-16-vperfsanity-output-stall` with **uncommitted FR-16 work** owned by another chat (16 modified and 8 new files). Never `git checkout`, `git stash`, `git commit -a` or `git add -A` there. Do any work for this stream in its own worktree:

`git worktree add -b feature/NET-7-vnetmap-lldp ../asbuilt-net7 origin/develop`

On 2026-11-10 a branch switch in the shared tree carried that FR-16 work into a docs commit (closed PR #46; restored, nothing lost). The remote branch `chore/pipe-t1-owner-decisions` still holds that commit. Deleting it is waiting on owner approval.

## Critical fixes: candidates (confirm scope with the owner)

| ID | Item | Priority | State |
| --- | --- | --- | --- |
| FR-16 | vperfsanity Step 4 output stalls, then floods and freezes Chrome | P0, v1.6.3 blocker | **In progress in another chat** (branch above). Plan around it; don't re-plan it. |
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
- **Overlap with FR-16:** FR-16's uncommitted changes touch `src/app.py`, `src/oneshot_runner.py`, `src/advanced_ops.py`, `src/utils/ssh_adapter.py`, `src/utils/logger.py`, `reporter.html` and `advanced_ops.html`. Sequence NET-7 edits to those files after FR-16 merges, or rebase onto it.

## Open questions for the owner

1. **Replace or fall back?** The request says "replace default vnetmap functionality"; the spec says "fallback when there are no switch credentials". Options: LLDP becomes the default with vnetmap optional; LLDP is used automatically when switch credentials are missing; or the operator picks per run.
2. **Which "associated LLDP scripts"?** `vnetmap_lldp.py` only, or also the Confluence tcpdump / `nw_check.sh` enrichment for switch IP, MAC and fabric?
3. **Release target:** the spec says v1.7.x; v1.6.3 is gated on FR-16. Does NET-7 ride in v1.6.3 or go to v1.7.0?
4. **Critical fixes scope:** FR-16 is already in progress. Is HCF-3 in? Anything from field feedback not in the register?
5. **Lab access:** a cluster with `lldpd` running on the nodes, and real `show-mapping` output (sanitized) for fixtures.

## Next agent actions

1. Read this file, `spec.md` and `docs/BRIEF.md`; create the worktree above.
2. Plan mode: brainstorm, ask the open questions, then write the plan (`docs/issues/NET-7/plan.md`, plus a `docs/issues/<ID>/` folder for any critical fix that lacks one).
3. On approval: `start-work`, then `implement-change` per to-do. Ship tests with every feature and a failing-first regression test with every bug fix.
