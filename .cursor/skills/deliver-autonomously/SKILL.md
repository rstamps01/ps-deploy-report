---
name: deliver-autonomously
description: Run the full intake-to-ship delivery loop for one approved work item with minimal human intervention, driven by the work-item state machine and bounded by autonomy budgets. Use when the user approves an item for hands-off delivery ("run this", "deliver BUG-042") after intake-feature.
disable-model-invocation: true
---

# deliver-autonomously

The end-to-end loop that composes the lifecycle skills so the only required human touchpoints are **submission** and **approval** (plus any destructive-action pause). It does not reimplement the stages — it sequences them and manages state, budgets, and recovery.

## Preconditions

- The item is approved and at status `ready-for-dev` (via `intake-feature`) with acceptance criteria.
- Autonomy budget + governance (§22) are known: max turns/cost, max parallel fan-out, dry-run flag.

## Loop (driven by the §6 state machine)

```
intake-feature (done) → start-work → [spec.md + consistency check if non-trivial]
  → implement-change (TDD + per-task independent review + bounded auto-debug)
  → functional-validate (UI/behavior/report)
  → quality-gate (iterate-until-green)
  → open-pr (bugbot + security-review)
  → [PAUSE for merge approval] → merge → prepare/ship-release (only if releasing)
  → publish-docs → update-tracker
```

1. **Advance state** on every transition (`in-progress` → `in-review` → `done`); persist to the tracker + memlog so an interrupted run resumes at the last completed task (not from scratch).
2. **Spec-first (right-sized):** for non-trivial items produce a minimal `spec.md` and run a cross-artifact consistency check (spec ↔ plan ↔ tasks ↔ code) before `implement-change`; trivial fixes skip the ceremony.
3. **Delegate in parallel** where independent (`explore` research, partitioned implementers) under the single-writer rule (§27) — never two implementers on the same files.
4. **On any gate failure**, hand to `remediate-failure` (bounded 3-attempt loop + escalation); do not silently retry forever.
5. **Respect budgets + kill switch (§22):** on `PM: pause`/`PM: stop`, or budget exhaustion, stop cleanly and escalate with current state. `--check`/dry-run previews the plan without writing.

## Required human touchpoints (everything else is autonomous)

- **Submission** (the request) and **approval** (`intake-feature`).
- **Destructive/irreversible pauses:** merge to `main`, tag/release, file deletion, force git — each surfaced with a decision brief.

## Subagents

`explore`/`generalPurpose` (research), fresh reviewer per task, `bugbot`+`security-review` (PR), `ci-investigator` (remediation). Orchestrated via `subagent-driven-development` (durable ledger = the memlog).

## Leverages

Skills: every lifecycle skill (`start-work`…`update-tracker`), `remediate-failure`, `subagent-driven-development`, `dispatching-parallel-agents`, `verification-before-completion`. Rules: all pipeline rules. Owned by the `project-manager` when run cross-project.

## Completion checklist

- [ ] Item carried through every stage; state machine advanced + persisted at each step
- [ ] Non-trivial item had spec.md + consistency check; trivial skipped it
- [ ] Every gate green (failures went through `remediate-failure`)
- [ ] Destructive actions paused for approval; budgets/kill-switch honored
- [ ] Docs published + tracker/memlog updated; item at `done`
