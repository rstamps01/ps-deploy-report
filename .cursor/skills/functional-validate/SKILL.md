---
name: functional-validate
description: Verify a UI or behavioral change works end-to-end before review, using Playwright/test_ui.py functional checks and screenshots. Use after implement-change for any change that alters the web UI, a route, a report artifact, or user-visible behavior.
disable-model-invocation: true
---

# functional-validate

Confirms the change actually works from the user's perspective, not just that unit tests pass. Skip only for pure-internal changes with no user-visible effect.

## Preconditions

- Code change implemented on the branch; unit tests green locally.
- For UI: Playwright is available (`tests/test_ui.py`).

## Steps

1. **Decide scope.** UI/route change → browser checks. Report/PDF/JSON change → generate a sample artifact and inspect. CLI change → run the command.
2. **Run functional checks:**
   - UI: `python3 -m pytest tests/test_ui.py -v --screenshot=on --output=test-results/` (or drive the running Flask dev server directly). Capture screenshots of the changed screens.
   - Report: render a sample report from fixture/mock data and open the PDF/JSON to confirm the section/field renders correctly.
3. **Check against acceptance criteria.** Walk each GIVEN/WHEN/THEN and confirm the observed behavior matches. Note any gap.
4. **Attach evidence.** Save screenshots/artifacts under `docs/issues/<ID>/evidence/`; reference them in the PR and memlog.
5. On failure, return to `implement-change` (or `remediate-failure` if it recurs). Do not proceed to review with a failing functional check.

## Subagents

- Coordinate with the running dev server (stop/restart around git-affecting changes) per the single-writer rule.

## Leverages

Rules: `testing-standards-06`. Skills: `verification-before-completion`. Next stage: `quality-gate`.

## Completion checklist

- [ ] Functional check run for the change type (UI/report/CLI)
- [ ] Every acceptance scenario verified against observed behavior
- [ ] Screenshots/artifacts saved to `docs/issues/<ID>/evidence/`
- [ ] No open functional gaps
