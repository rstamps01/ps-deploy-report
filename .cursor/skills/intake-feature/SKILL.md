---
name: intake-feature
description: Capture a feature or bug request into the project's single tracking register with an ID, type, priority, risk, and testable acceptance criteria, then present it for approval. Use when a new request, enhancement, RFE, or bug arrives and needs to enter the pipeline before any work begins.
disable-model-invocation: true
---

# intake-feature

First stage of the golden path (`AGENTS.md`). Turns a raw request into a tracked, approved work item. No branches or code yet.

## Preconditions

- The request is understood (ask clarifying questions first; use `brainstorming` for non-trivial FEATs).
- The register `docs/TODO-ROADMAP.md` and `docs/issues/` exist.

## Steps

1. **De-dupe.** Search `docs/TODO-ROADMAP.md`, `docs/issues/`, `docs/PLANS-INDEX.md`, open PRs/issues (`gh issue list`), and CHANGELOG for an existing/shipped equivalent. If found, link it instead of creating a duplicate. (Atlassian `triage-issue` pattern.)
2. **Classify.** Assign: `type` = FEAT | BUG | CHG; `priority` = P0–P3; a one-line `risk` note.
3. **Allocate an ID.** Use the next sequential ID in the register's scheme (e.g. `FEAT-###`, `BUG-###`).
4. **Write acceptance criteria.** Testable GIVEN/WHEN/THEN outcomes. For a BUG, describe the observed vs expected behavior that a failing-first regression test will pin.
5. **Create the register entry** at status `draft` (state machine: `draft → ready-for-dev → in-progress → in-review → done → blocked`) with: ID, type, priority, risk, acceptance criteria, links.
6. **Spec (non-trivial only).** For anything beyond a trivial fix, create `docs/issues/<ID>/spec.md` with the 5 fields: Why, Capabilities, Constraints, Non-goals, Success-signal. Skip for trivial one/two-file fixes (right-size the process).
7. **Present for approval.** Surface a concise brief (what/why/priority/acceptance) and ask the user to approve, adjust, or defer. Do not proceed to `start-work` without approval.
8. On approval, set status `ready-for-dev`. If the user requests autonomous delivery, hand off to the §13 delivery loop.

## Subagents / MCPs

- `explore` (parallel) for codebase impact scan on non-trivial items.
- Atlassian MCP (`triage-issue`, `spec-to-backlog`) when the item mirrors to Confluence page 6664028496 / Jira.

## Leverages

Rules: `todo-tracking-09`. Skills: `brainstorming`, `writing-plans`. Next stage: `start-work`.

## Completion checklist

- [ ] De-dup search done; no duplicate created
- [ ] Register entry created with ID, type, priority, risk, acceptance criteria
- [ ] `spec.md` created for non-trivial items (5 fields)
- [ ] User approved; status set to `ready-for-dev`
