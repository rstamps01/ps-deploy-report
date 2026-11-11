# Handoff: v1.6.3 implementation (2026-11-11)

Start here for the implementation chat. Code and git outrank this file. Plan: [`plan.md`](plan.md); scope and
gates: [`spec.md`](spec.md); tasks: [`tasks.md`](tasks.md). Owner decisions: `docs/DECISIONS.md` 2026-11-11.

## State

- Planning is done and approved by the owner. Docs PR [#51](https://github.com/rstamps01/ps-deploy-report/pull/51)
  (`chore/v1.6.3-plan`) has the plan, all specs, register, decisions and brief. Gate passed locally (coverage 74%).
- No code has started. FR-16 is merged (PR #49); its lab re-run (T8) is still pending.
- Lab: the owner has a cluster with LLDP already active on the nodes (NET-7 gate). Ask which one when needed;
  never enable lldpd/lldpad.

## Worktrees and branches

- `~/vast-asbuilt-reporter`: main checkout on `develop`. Other chats may use it; don't switch branches there.
- `~/asbuilt-net7`: branch `feature/NET-7-vnetmap-lldp` (from `develop` at `f5ea66a`, upstream unset). Rebase
  it on `develop` after #51 merges. The `venv` symlink to the main checkout's venv is excluded locally (via
  `.git/info/exclude`); don't stage it.
- Every other item gets its own worktree off `develop` (after #51 merges), for example
  `git worktree add -b fix/FR-10-paramiko-deadline ../asbuilt-fr10 origin/develop`, then `ln -s
  ~/vast-asbuilt-reporter/venv venv` to run `bash scripts/quality-gate.sh`.

## Next agent actions

1. Confirm #51 is merged (or ask the owner to merge it); then rebase `feature/NET-7-vnetmap-lldp` on `develop`.
2. Wave A, in parallel (one subagent per item on the implementation model, each with the brief, its spec and its
   file list): FR-10, FR-11, TP-4, HCF-3. Failing-first test for each. Then OBS-1 after HCF-3, and FR-7 after FR-10.
3. NET-7 in `~/asbuilt-net7`, per [`../NET-7/plan.md`](../NET-7/plan.md): workers A (parser) and C (workflow,
   selector, guardrail test, tool manager) in parallel, B (mapper/diagram) after A's row contract, parent
   integration last.
4. TP-3: ask the owner for the scrubbed field ops log or a lab Tech Port session; otherwise move it to v1.7.0
   with the reason.
5. Each item: changelog fragment in `docs/issues/<ID>/changelog.md`, independent review, gate, PR to `develop`,
   register to in-review.

## Gotchas

- `vnetmap_lldp.py show-mapping` rewrites `/userdata/switch_mapping.json` on the CNode (Support's `ifup` reads
  it). The workflow must preserve it, and the guardrail test checks the restore on success and failure.
- Its readiness check requires the `lldpad` package; we never pass `-f`.
- `health_checker.py` is edited by both HCF-3 and OBS-1, and `ssh_adapter.py` by both FR-10 and FR-7: keep them
  sequential.
- HCF-3 is a behavior change in a patch release; the release notes must name it with the `fail_on: none` opt-out.
