---
name: open-pr
description: Commit with a Conventional Commit message, push the branch to develop, open a PR via gh using the repo template, and run bugbot + security-review subagents in parallel. Use after quality-gate passes and the change is ready for review.
disable-model-invocation: true
---

# open-pr

Change-control stage. Gets the branch into review with automated checks. Enforces `change-control-07` and the Definition of Done.

## Preconditions

- `quality-gate` passed and `functional-validate` passed for UI/behavior changes.
- On a `feature/*` / `fix/*` branch (never `main`).

## Steps

1. **Commit** with a Conventional Commit message: `<type>(<scope>): <summary>` (types: feat/fix/docs/style/refactor/test/chore; scopes per `change-control-07`). Body explains WHY. Never commit to `main`.
2. **Push:** `git push -u origin HEAD`.
3. **Open the PR** targeting `develop` via `gh pr create`, using `.github/PULL_REQUEST_TEMPLATE.md`. Pass the body via a heredoc; fill the DoD checklist honestly.
4. **Parallel review subagents:** dispatch `bugbot` (Task description exactly "Bugbot") and `security-review` (description "Security Review") on the branch changes. Fold their findings back — fix blockers before requesting human review; two REJECTs escalate to `remediate-failure`.
5. **Independent human/agent review:** request review (`requesting-code-review`); the reviewer is fresh (did not write the code).
6. **Update the register** to `in-review` with the PR link; append to the memlog.

## Definition of Done (mirrors the PR template)

Tests added/updated (BUG = failing-first regression); coverage not decreased; CHANGELOG + docs updated; version-sync (at release); `functional-validate` passed for UI; tracker updated; review subagents clean; no secrets in the diff.

## Subagents

`bugbot`, `security-review` (parallel), `explore` for targeted follow-up.

## Leverages

Rules: `change-control-07`, `documentation-08`. Skills: `requesting-code-review`, `receiving-code-review`, `review-bugbot`, `review-security`. Next stage: merge → `prepare-release` (when releasing) or back to `update-tracker`.

## Completion checklist

- [ ] Conventional-commit message; branch pushed
- [ ] PR opened against `develop` with the template + DoD filled
- [ ] bugbot + security-review run; blockers resolved
- [ ] Register moved to `in-review` with PR link
