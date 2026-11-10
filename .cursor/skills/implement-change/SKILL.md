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

1. **Research first.** Start from `docs/issues/<ID>/context.md` (build it with `python3 scripts/context-pack.py <ID> --terms <symbols>`). Dispatch `explore` subagents (fast model tier) only for what the pack doesn't answer. Do not guess file locations, and read large modules by line range.
2. **TDD loop** (per `test-driven-development`):
   - Write a failing test that encodes the next slice of acceptance criteria. For a BUG, this is the failing-first regression test.
   - Implement the minimum to pass.
   - Refactor; keep it green.
   - Repeat per slice.
   - **Targeted tests only** in the loop: `python3 -m pytest tests/test_<module>.py -x --lf` (coverage is not collected by default). The full suite runs once at `quality-gate`; don't re-run it per slice.
3. **Guardrails while coding:**
   - Respect the layered architecture and module boundaries in `architecture-03` (e.g. `api_handler` never imports `data_extractor`/`report_builder`; workflows never import `report_builder`/`data_extractor`).
   - Follow `python-standards-04` (Google docstrings, typing) and `config-security-11` (no hardcoded secrets; sanitize logs).
   - New modules follow the layered map in `repo-structure-17`; new files land in-standard.
4. **Independent review + bounded auto-debug.** Dispatch ONE fresh reviewer subagent (that did NOT write the code) on the finished change. Plans with more than 3 tasks get one reviewer per task instead. Re-reviews cover only the changed hunks. On a failure, run a bounded assess→fix→re-run loop (max 3 attempts, `systematic-debugging`); two reviewer REJECTs escalate to `remediate-failure`.
5. **Update `tasks.md`** and the memlog as tasks complete (resumable if interrupted). Write user-facing changes to `docs/issues/<ID>/changelog.md` (2–5 Keep-a-Changelog lines) instead of editing `CHANGELOG.md`; `prepare-release` assembles them.
6. **Hub-and-worker.** For plans with more than 3 independent to-dos, run each as a `generalPurpose` subagent on the fast model tier (`.cursor/pipeline.yml` `models.fast`) with the brief, the to-do, the context pack and the file list. The parent integrates, reviews and runs the gate.

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
- [ ] `tasks.md` + memlog updated; changelog fragment written for user-facing changes
