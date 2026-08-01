---
name: implement-change
description: Implement an approved tracker item using a test-driven loop with architecture/boundary guardrails, parallel research subagents, and per-task independent review with bounded auto-debug. Use when writing or modifying application code on a feature/fix branch after start-work.
disable-model-invocation: true
---

# implement-change

Core build stage of the golden path. Produces code + tests that satisfy the item's acceptance criteria without violating module boundaries.

## Preconditions

- On the item's `feature/*` / `fix/*` branch (see `start-work`).
- Acceptance criteria (and `spec.md` for non-trivial items) are known.

## Steps

1. **Research first.** Dispatch parallel `explore` subagents to map the affected code, existing patterns, and tests. Do not guess file locations.
2. **TDD loop** (per `test-driven-development`):
   - Write a failing test that encodes the next slice of acceptance criteria. For a BUG, this is the failing-first regression test.
   - Implement the minimum to pass.
   - Refactor; keep it green.
   - Repeat per slice.
3. **Guardrails while coding:**
   - Respect the layered architecture and module boundaries in `architecture-03` (e.g. `api_handler` never imports `data_extractor`/`report_builder`; workflows never import `report_builder`/`data_extractor`).
   - Follow `python-standards-04` (Google docstrings, typing) and `config-security-11` (no hardcoded secrets; sanitize logs).
   - New modules follow the layered map in `repo-structure-17`; new files land in-standard.
4. **Per-task independent review + bounded auto-debug.** After each meaningful task, dispatch a FRESH reviewer subagent (that did NOT write the code) to check correctness/boundaries/tests. On a failure, run a bounded assess→fix→re-run loop (max 3 attempts, `systematic-debugging`); two reviewer REJECTs escalate to `remediate-failure`.
5. **Update `tasks.md`** and the memlog as tasks complete (resumable if interrupted).

## Subagents

- `explore` / `generalPurpose` (parallel) — research and impact analysis.
- Fresh reviewer subagent per task (independent-reviewer pattern).
- Single-writer rule: never run two implementer subagents editing the same files; partition by domain.

## Leverages

Rules: `architecture-03`, `python-standards-04`, `testing-standards-06`, `config-security-11`, `repo-structure-17`. Skills: `test-driven-development`, `systematic-debugging`, `dispatching-parallel-agents`, `subagent-driven-development`. Next stage: `functional-validate` (UI/behavior) or `quality-gate`.

## Completion checklist

- [ ] Every acceptance slice has a passing test (BUG has a regression test)
- [ ] No module-boundary violations (`architecture-03`)
- [ ] Docstrings/typing per `python-standards-04`; no secrets/logging leaks
- [ ] Independent reviewer clean; any auto-debug stayed within 3 attempts
- [ ] `tasks.md` + memlog updated
