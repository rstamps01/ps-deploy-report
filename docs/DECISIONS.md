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

### 2026-08-01 — Pre-ship review + cross-OS QA phase (gates 1.6.0)
- **Pre-ship review:** v1.5.8 plan fully shipped (tag exists; devices/health/version-sync deliverables confirmed). Delta since v1.5.8 = 12 commits / 22 app files (+1217/-108): Teleport tsh discovery + settings + tunnel routing fixes, vnetmap cross-cluster guard + Onyx `admin` auth, switch-config filename sanitization, bundle SUMMARY version, plus non-app `notifier.py` + M0–M5. Working tree clean.
- **Update-pill requirement:** verified `src/updater.py` is present at tag `v1.5.8`, so existing 1.5.8 installs already have the in-app checker → they will detect a published v1.6.0 stable release and show the header **UPDATE AVAILABLE** pill. Repo target `rstamps01/ps-deploy-report` is correct.
- **QA decisions (user):** Linux = run-from-source only; deliver both a checklist doc AND automated tests; execution is CI-only for now; validate the pill via a staged (mocked) dry-run before the real tag; online-only update check is acceptable (documented).
- **Delivered:** `docs/development/QA-TEST-PLAN.md` (cross-OS matrix, 1.6.0 functional cases, update-pill §6, caveats, sign-off checklist); `tests/test_update_release_readiness.py` (staged 1.5.8→1.6.0 dry-run with real v1.6.0 asset names + non-semver-tag handling + dual-mac-DMG arch caveat pinned); new `qa-cross-os` CI job (functional subset on ubuntu+macOS+windows, cost-gated). Wired into `prepare-release`/`ship-release` + `docs/README.md`.
- **Two documented caveats (non-blocking):** (1) air-gapped machines never see the pill (by design); (2) a shipped 1.5.8 client links the first mac DMG, so an Intel user may get the arm64 link — follow-up: make `extract_download_urls` arch-aware for 1.6.0+ clients.
- **Still paused:** actual 1.6.0 ship (merge→tag→release) + branch-protection policy await approval; ship is now gated behind this QA phase.

### 2026-07-31 — M5 release hardening
- **Blocking release gates (§5):** removed `continue-on-error` from `build-release.yml` quality-gate + test jobs; `build` now `needs: [quality-gate, test]`, so artifacts only build after gates pass. Updated `release-packaging-12.mdc` to match (no more "does not block"). **Rationale:** a release must never ship un-gated artifacts; branch protection keeps `main` green so a proper tag still produces the `.dmg`/`.zip`.
- **Drift fix:** the release-notes step read `RELEASE_NOTES_v*.md` from repo root, but M4 moved them to `docs/releases/`. Workflow now checks `docs/releases/` first, then root, then CHANGELOG.
- **New skills (§18/§28):** `hotfix` (branch off the released tag, minimal failing-first fix, patch release, back-merge), `rollback` (re-point "latest" to last good tag — first option on a bad release), `maintain` (Dependabot triage, success comms, config migration). Indexed in `CATALOG.md` + `AGENTS.md`; all pass conformance.
- **Project manifest (§30, Phase A portability):** added `.cursor/pipeline.yml` — declarative capability profile (commands, version locations, coverage floor, artifacts, doc surfaces, notification channels, tracking files, autonomy budgets) so skills read config instead of hardcoding. Python adapter instance; schema stack-agnostic.
- **1.6.0 release PREP:** wrote `docs/releases/RELEASE_NOTES_v1.6.0.md`. Version already synced to 1.6.0; latest tag is `v1.5.8`. **Paused:** the actual merge→tag→release is a destructive/approval-gated action (PM guardrail) — awaiting explicit go-ahead.
- **Open decisions surfaced:** (a) ship `1.6.0` now? (b) branch-protection policy on `main` (SEC-2) — interacts with the direct `develop→main` merge release flow.

### 2026-07-31 — Prior-plan reconciliation + approved deletion batch
- Reconciled 173 prior Cursor plans → `docs/PLANS-INDEX.md` (this-repo: 82 shipped-stale, 13 superseded/empty, 4 minor-tail, 4 open; 70 belong to other projects). Commits `cf0a391`.
- **Approver:** user approved the conservative 12-file deletion batch. Deleted from `~/.cursor/plans/` (173 → 161); `pywebview_native_window` retained by design.
- Promoted 2 genuinely-open in-scope items to the roadmap: **SEC-2** (branch protection on `main`), **OPS-1** (Windows netsh portproxy remote access).

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
