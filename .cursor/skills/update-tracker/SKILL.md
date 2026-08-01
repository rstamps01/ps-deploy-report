---
name: update-tracker
description: Maintain the single work register (docs/TODO-ROADMAP.md) — advance work-item states, keep the Done archive, Last updated, and Next steps current, and keep CHANGELOG in sync. Use whenever a work item changes state, at the end of a session, and during prepare-release.
disable-model-invocation: true
---

# update-tracker

Keeps project state truthful in one place. Enforces `todo-tracking-09`. The register is the live source of truth; `CHANGELOG.md` is shipped history; `docs/PROJECT-STATUS.md` is the PM snapshot.

## Register model

- **Live backlog** (Planned / In progress) at the top of `docs/TODO-ROADMAP.md`.
- **Done archive** — older completed items live in `docs/ROADMAP-ARCHIVE.md`; keep the register lean.
- **Per-item detail** in `docs/issues/<ID>/`; **plan reconciliation** in `docs/PLANS-INDEX.md` — referenced, not duplicated.
- Every item carries: ID, type (BUG/FEAT/CHG), priority (P0–P3), status, acceptance criteria, links.

## Work-item state machine

`draft → ready-for-dev → in-progress → in-review → done → blocked`. Advance the item's `status` as it moves through the golden path; `blocked` records the blocker + owner.

## Steps

1. **Locate the item** by ID in the register (create it via `intake-feature` if missing).
2. **Advance the state** to match reality (branch open = `in-progress`; PR open = `in-review`; merged + released = `done`).
3. **Move completed items** to `docs/ROADMAP-ARCHIVE.md` when the live list grows; keep only active + near-term work in the register.
4. **Refresh metadata:** "Last updated" (date + one-line what-changed) and "Next steps (current focus)".
5. **Sync CHANGELOG** for user-facing changes (Keep a Changelog). Do not duplicate CHANGELOG narrative inside the register.
6. **Append to the memlog** (`docs/DECISIONS.md` for decisions; issue log for progress) so runs are resumable.
7. Confirm CI's todo-list structural validation still passes (required sections/headings intact).

## Leverages

Rules: `todo-tracking-09`, `documentation-08`. Skills: `generate-status-report` (status rollups).

## Completion checklist

- [ ] Item status matches reality (state machine)
- [ ] Done items archived; register kept lean
- [ ] "Last updated" + "Next steps" refreshed
- [ ] CHANGELOG in sync for user-facing changes
- [ ] Memlog appended; CI todo-validation still passes
