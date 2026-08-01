---
name: start-work
description: Create the working branch and scaffolding for an approved tracker item off develop. Use after intake-feature approval, when beginning implementation of a FEAT, BUG, or CHG that has an ID and acceptance criteria.
disable-model-invocation: true
---

# start-work

Second stage of the golden path. Sets up an isolated branch and per-item workspace so implementation is traceable and resumable.

## Preconditions

- The item exists in `docs/TODO-ROADMAP.md` at status `ready-for-dev` with acceptance criteria.
- Working tree is clean (commit or stash unrelated changes first).

## Steps

1. **Sync `develop`.** `git checkout develop && git pull origin develop`.
2. **Branch.** Create `feature/<ID>-<slug>` (FEAT/CHG) or `fix/<ID>-<slug>` (BUG) off `develop`. Never branch off or commit to `main`.
3. **Per-item workspace.** Ensure `docs/issues/<ID>/` exists. For non-trivial items create/confirm `spec.md` (from intake) and add `plan.md` (approach) and `tasks.md` (checklist). Trivial fixes may skip `plan.md`/`tasks.md`.
4. **Optional plan file.** For multi-task work, create a `.cursor/plans/*.plan.md` and prefer `subagent-driven-development` as the execution engine.
5. **Update the register.** Move the item `ready-for-dev → in-progress`; refresh "Last updated".
6. **Memlog.** Append a start entry (ID, branch, timestamp) to the working-memory ledger (`docs/DECISIONS.md` / issue log) for crash recovery.

## Subagents

- `using-git-worktrees` when the work needs isolation from the current workspace (e.g. parallel experiments).

## Leverages

Rules: `change-control-07`. Skills: `writing-plans`, `subagent-driven-development`, `using-git-worktrees`. Next stage: `implement-change`.

## Completion checklist

- [ ] On a fresh `feature/*` or `fix/*` branch off up-to-date `develop`
- [ ] `docs/issues/<ID>/` scaffolded (spec/plan/tasks as warranted)
- [ ] Register moved to `in-progress`
- [ ] Start entry appended to the memlog
