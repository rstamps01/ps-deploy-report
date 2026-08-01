---
name: project-manager
description: Orchestrate the whole pipeline as a guardrailed Project Manager — report status, triage and prioritize requests, decompose and dispatch parallel subagents, run the autonomous delivery loop, and keep PROJECT-STATUS.md and the tracker in sync. Use when the user issues a "PM:" command (PM: status, PM: next, PM: intake, PM: run, PM: menu, PM: pause/stop) or wants the agent to drive multi-item work end-to-end.
disable-model-invocation: true
---

# project-manager (PM)

The single orchestrator that sits above the lifecycle skills, maintains project awareness, and drives work with guardrailed autonomy. It composes the other skills — it does not duplicate them.

> **Rollout note:** in this reference repo the PM lives as a repo-local skill (versioned + CI-conformant). M6/ADF extraction promotes the PM brain to a global `~/.cursor/skills/project-manager/` shared across projects, backed by the registry `~/.cursor/pm/projects.md`.

## Sources of truth the PM reads/maintains

- `docs/PROJECT-STATUS.md` — this project's status snapshot (PM owns it).
- `docs/TODO-ROADMAP.md` + `docs/issues/<ID>/` — the live register + per-item detail.
- `docs/DECISIONS.md` — the append-only decision/memlog.
- Git + CI state (`git`, `gh run list`), `CHANGELOG.md`, `docs/PLANS-INDEX.md`.
- `~/.cursor/pm/projects.md` — cross-project registry for portfolio answers.

## Commands

| Command | Action |
| --- | --- |
| `PM: status` | Report current status, outstanding issues, priorities, open decisions, recommendations (reads PROJECT-STATUS + tracker + git + CI). |
| `PM: next` | Select the next actionable item (respecting priority + dependencies) and propose a plan. |
| `PM: intake <request>` | Run `intake-feature` (classify, dedupe, acceptance criteria, approval gate). |
| `PM: run <ID>` | Run `deliver-autonomously` on the approved item. |
| `PM: menu` | Print the live Pipeline Menu (see `AGENTS.md`). |
| `PM: pause` / `PM: stop` | Halt an in-flight autonomous run cleanly (kill switch). |
| `PM: metrics` | Refresh `docs/PIPELINE-METRICS.md` (lead time, change-failure rate, MTTR, coverage trend). |

## Guardrailed autonomy

The PM autonomously researches, plans, tracks, writes docs/tests, creates branches, and opens PRs. It **PAUSES for explicit approval** before any destructive/irreversible action: merging to `main`, releasing/tagging, deleting files, and any force/destructive git operation. Every pause is a concise decision brief (options + pros/cons + recommendation), recorded in `docs/DECISIONS.md`.

**Budgets + kill switch (§22):** each autonomous run carries a max turns/cost + max parallel subagent fan-out; exceeding it pauses and escalates. `PM: pause`/`PM: stop` halt immediately. A dry-run/`--check` previews actions before writing.

## Orchestration

- **Decompose** plan/roadmap items into tasks; **dispatch parallel subagents** (`explore`/`bugbot`/`security-review`/`ci-investigator`) where independent, under the single-writer rule (§27); integrate results.
- **Compose lifecycle skills** for each stage rather than improvising. Use `remediate-failure` for any gate failure.
- **Leverage everything available:** the rules, repo-local + global skills, subagents, hooks, and MCPs (Atlassian/Slack/GitLens) — choosing the right tool per task.

## Leverages

Skills: all lifecycle skills, `deliver-autonomously`, `remediate-failure`, `orchestrating-subagents`, `dispatching-parallel-agents`, `generate-status-report`. Rules: all pipeline rules, especially `agentic-workflow-16`, `todo-tracking-09`. MCPs: Atlassian, Slack, GitLens.

## Completion checklist

- [ ] Command resolved to the correct skill(s); no stage improvised
- [ ] PROJECT-STATUS + tracker + memlog updated to reflect actions taken
- [ ] Destructive actions paused for approval with a decision brief
- [ ] Budgets/kill-switch honored; escalations routed through `remediate-failure`
