# Decisions & Memlog

Append-only decision log (ADR-lite) **and** working-memory ledger for the agentic pipeline (pipeline §24/§27). Two uses, one file:

- **Decisions** — every approval, plan decision, superseded/deleted item, and escalation resolution, with date + rationale + approver. The traceability backbone for change-control and the "open decisions" list.
- **Memlog** — skills and subagents append short, chronological, machine-readable progress/coordination entries so long runs are **resumable** after an interruption and parallel work stays coordinated.

**Rules:** append only (never rewrite history); newest at the top of each section; keep entries terse; redact secrets. Owned by the `project-manager`, appended to by all skills/subagents.

---

## Decisions (newest first)

### 2026-07-31 — PM skill lives repo-local in the reference impl
- **Decision:** the `project-manager` skill is authored as a repo-local `.cursor/skills/project-manager/SKILL.md` here (versioned + CI-conformant); the global `~/.cursor/skills/project-manager/` + `~/.cursor/pm/projects.md` promotion happens at M6/ADF extraction.
- **Rationale:** "build in the reference repo first, then extract" (plan §29); keeps M3 self-contained and conformance-checked. **Approver:** user (M3 go-ahead).

### 2026-07-31 — Escalation channels: SMTP email + Slack reply
- **Decision:** escalation email via SMTP (`src/utils/notifier.py`); interactive reply over Slack via the Slack MCP. Both fire on the same escalation event; credentials via `SMTP_USERNAME`/`SMTP_PASSWORD` env vars only.
- **Rationale:** email is the durable record; an agent can read a Slack thread reply (to drive a 2nd loop) but cannot read an inbound mailbox. **Approver:** user (plan §16).

### 2026-07-31 — Stay bespoke (Plan A)
- **Decision:** implement all pipeline mechanics ourselves, adopting leading-framework mechanics as PATTERNS only — no external code/deps. Core patterns 1–6 woven in; 7–10 optional/phase-2.
- **Rationale:** human-oversight time (not token cost) dominates; bespoke keeps full control with modest incremental cost. **Approver:** user.

### 2026-07-31 — Canonical version source = `src/app.py` `APP_VERSION`
- **Decision:** `src/app.py` `APP_VERSION` is the single canonical version; `scripts/check-version-sync.sh` enforces all other locations against it.
- **Rationale:** resolve the prior drift where the script treated `src/__init__.py` as canonical while rules named `src/app.py`. **Approver:** user (M1).

### 2026-07-31 — Existing `src/` stays flat
- **Decision:** enforce the layered module map for NEW modules only; do not refactor the ~28 existing flat modules now (deferred backlog item).
- **Rationale:** a subpackage move triggers 40+ test-import changes for no functional gain. **Approver:** user (audit decision).

### 2026-07-31 — Release-notes + CHANGELOG consolidation (deferred to M4)
- **Decision:** move `RELEASE_NOTES_v*.md` → `docs/releases/`, split old CHANGELOG into `docs/CHANGELOG-ARCHIVE.md`, untrack `.archive/`. Standard defined in M1; one-time cleanup executed as its own reviewable PR in M4.
- **Rationale:** separate the standard from the disruptive move. **Approver:** user (audit decision).

---

## Memlog (newest first)

### 2026-07-31 — M4 tracking & docs consolidation (`c89172d`, pushed)
- Recovered from a tool-backend outage: the pre-outage chained move command had actually executed (errors were false negatives). Verified real repo state before proceeding.
- Roadmap restructured: `TODO-ROADMAP.md` trimmed 400→~260 lines (narrative header stripped, work-item state machine added), ~160 lines of Done history → `docs/ROADMAP-ARCHIVE.md`.
- CHANGELOG split: v1.5.0+ live; v1.4.7↓ → `docs/CHANGELOG-ARCHIVE.md`. Release notes → `docs/releases/`. Added `AGENTIC-CICD-PIPELINE.md` (master doc) + `PIPELINE-METRICS.md` + `PLANS-INDEX.md` (scaffold). `docs/README.md` re-indexed (0 dangling links).
- Hygiene: `.archive/` untracked + gitignored; `logs/*.out`, `.cursor/settings.json` gitignored; `scripts/clean-workspace.sh` added; workspace file renamed.
- **Docs-accuracy audit:** fixed `.vscode/README.md` workspace name, marked CHANGELOG `[1.6.0]` as **Unreleased** (no `v1.6.0` tag exists), updated `REPO-STRUCTURE.md` status to "applied". In-app docs-viewer paths + packaging spec verified intact after moves.
- **Open:** full prior-plan reconciliation (174 plan files) running via subagent → `PLANS-INDEX.md`; deletion batch will be surfaced for approval before any plan file is removed.

### 2026-07-31 — M3 orchestration in progress
- notifier.py + tests green (20/20); `notifications:` config + README/rule docs added.
- Skills authored: `remediate-failure`, `deliver-autonomously`, `project-manager`; global `~/.cursor/pm/projects.md` seeded.
- Next: governance (flaky marker + budgets), CATALOG/AGENTS update, M3 gate + commit.

### 2026-07-31 — M2 complete (`724d1a7`)
- 11 lifecycle skills + `CATALOG.md` + `scripts/check-skill-conformance.py` wired into CI; all skills conform. Pushed to `origin/develop`.

### 2026-07-31 — M1 complete
- Rules reconciled (coverage 60, canonical version, `agentic-workflow-16`, `repo-structure-17`); `AGENTS.md`, hooks (`guard-git.sh`), GitHub scaffolding, `REPO-STRUCTURE.md`. Pushed.

### 2026-07-31 — M0 baseline
- Segmented 1.6.0 work onto `develop`; `docs/PROJECT-STATUS.md` snapshot; green gate recorded (1582 unit tests). Pushed.
