<!--
Follow the agentic pipeline (AGENTS.md). PRs target `develop` (never `main` directly).
Use a Conventional Commit title: <type>(<scope>): <summary>  (types: feat/fix/docs/style/refactor/test/chore).
-->

## Summary

<!-- What changed and WHY (not just what). Link the tracker item / issue. -->

- Tracker item: <!-- docs/TODO-ROADMAP.md ID or docs/issues/<ID>/ -->
- Type: <!-- FEAT | BUG | CHG -->

## Changes

-

## Definition of Done

- [ ] Tests added/updated for new behavior (BUG fixes include a **failing-first** regression test)
- [ ] Coverage did **not** decrease (>= 60% floor; ratchets upward only)
- [ ] Quality gate passes locally: `check-version-sync.sh`, black, flake8 (+E722), mypy, pytest
- [ ] `CHANGELOG.md` updated for user-facing changes; docs updated where impacted
- [ ] Version strings in sync (canonical: `src/app.py` `APP_VERSION`) — only when releasing
- [ ] `functional-validate` passed for UI/behavior changes (screenshots attached if UI)
- [ ] Tracker/register updated (status + acceptance criteria)
- [ ] Review subagents clean (bugbot + security-review) for non-trivial changes
- [ ] No secrets/credentials in the diff

## Test plan

<!-- Commands run + results, screenshots for UI. -->
