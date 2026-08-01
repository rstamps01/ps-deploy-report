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

### 2026-08-01 — M6 in-repo start: manifest adapter (§30) + ADF extraction spec
- **Decision (checkpoint):** M6 begins **in-repo** (prove the framework/instance seam here first); defer creating the standalone ADF repo. When created, it targets **`github.com/rstamps01/agentic-dev-framework` (private)** — no new repo until Phase B is explicitly kicked off.
- **project-manifest (§30) DONE:** built `scripts/pipeline_manifest.py` — a dependency-light adapter that resolves the canonical commands/gates from `.cursor/pipeline.yml` (`get <name>`, `gate` = blocking-gate commands in order with `version_sync`→`version.sync_check` resolution, `show`, `validate --strict`). 18 tests (`tests/test_pipeline_manifest.py`). Wired: `quality-gate` skill now sources commands from the manifest via the adapter (manifest wins on drift); CI `quality-gate` job runs `pipeline_manifest.py validate --strict`; `CATALOG.md` documents it. Skills are now stack-agnostic — a Node/Go/Docker repo swaps the manifest and every skill keeps working.
- **ADF extraction spec DONE:** `docs/development/ADF-EXTRACTION.md` — framework-vs-instance separation, precedence, a **portable-asset inventory** (core / template / instance-only), adoption tiers L1–L3, ADF versioning + `update-framework`, adoption flows (`new-project`/`adopt-existing`), `framework-doctor` + portfolio PM, a **phased extraction plan** (A reference impl ✅ → B extract core → C bootstrap+tiers → D pilot on VAST Plan Analyzer → E portfolio rollout), and the `HANDBOOK.md` outline. Indexed in `docs/README.md`.
- **Verified:** full unit gate **1635 passed, 69.25% coverage, bounded 3:18**; version-sync/black/flake8/manifest-validate green. (mypy's 5 local `paramiko` `import-untyped` errors are the documented local-only stub gap — suppressed in CI; not from changed files.)
- **Remaining (M6, needs the new repo — deferred):** `adf-core-repo`, `framework-versioning`, `bootstrap-installer`, `adoption-flows`, `maturity-tiers`, `conformance-doctor`, `methodology-handbook`, `rollout-sequence`.

### 2026-08-01 — Pipeline tails closed: flaky/timeout CI wiring (§21) + secrets registry (§19)
- **§21 test reliability (DONE):** added `pytest-timeout` to `requirements-dev.txt` + a global `--timeout=300` backstop in `pyproject.toml` (platform-auto method); wired `-m "not flaky"` into every CI test job (`ci.yml` unit/health/advanced-ops/integration/qa-cross-os) and the `build-release.yml` release gate so quarantined nondeterministic tests never block. `quality-gate` skill updated to match. Combined with the conftest network guard, the suite is now hang-proof on any OS. Verified: **1617 passed, 69.25% coverage, bounded 3:20**. Per-loop wall-clock/cost budgets remain policy-level (documented in skills; bespoke pipeline has no runtime harness to instrument them).
- **§19 secrets model (DONE):** authored `docs/development/PIPELINE-SECRETS.md` — the single registry of every secret (VAST creds, `SMTP_*`, Slack/Atlassian MCP auth, `gh`/`GITHUB_TOKEN`, optional `CURSOR_API_KEY`), its store (local `.env` / OS env / GitHub Actions secret / MCP auth), and its consumer. Referenced from `config-security-11.mdc`, `AGENTS.md`, and `docs/README.md`. Manual security assessment of the notifier/Slack/Confluence surface confirmed: redaction on every field, env-only SMTP creds, failures returned-not-raised, TLS. **Hardening applied:** `EscalationReport.subject()` now collapses CR/LF (defense-in-depth vs email header injection) + regression test. Formal `security-review` subagent pass available on-request.
- Plan `agentic_cicd_pipeline_2eb2e257`: both tails flipped to completed. Remaining open work is **M6 (ADF portability extraction)** + its `project-manifest` adapter tail.

### 2026-08-01 — Test-suite network guard (fixes local "hung agent")
- **Root cause of the recurring local hang:** several unit tests (`test_oneshot_runner`) exercise paths that open **real TCP sockets** to `10.0.0.1` (VMS API `:443`, node/switch SSH `:22`) — the switch-SSH safety-net probe in `run_all()` and `_validate_node_ssh`/`_validate_switch_ssh` build a live `VastApiHandler`. In CI those targets refuse instantly (tests pass in ms); on a dev Mac attached to a routable `10.0.0.0/8` fabric the SYNs are silently dropped, so each connect blocks its full timeout × retries × API-version probes → the suite ran for minutes and, without `--timeout`, looked like a hung agent (aborted shell `669564`). No process was actually stuck — all PIDs were dead on inspection.
- **Fix:** added an autouse network guard in `tests/conftest.py` that makes non-loopback `socket.connect`/`connect_ex` fail fast with `ConnectionRefusedError` (mirrors CI). Loopback + AF_UNIX always allowed; `@pytest.mark.integration` and `VAST_TEST_ALLOW_NETWORK=1` opt out. Any test that leaks real network I/O now surfaces instantly instead of stalling the run.
- **Verified:** the 3 previously-timing-out tests pass; full `test_oneshot_runner.py` 80/80 in 36s; **full unit suite 1616 passed in 2:19** (previously hung indefinitely). black + flake8 clean. Dev-only change (no runtime code touched).

### 2026-08-01 — v1.6.0 shipped + branch protection on `main`
- **Released v1.6.0** (first run of the new `prepare-release`/`ship-release` path). CHANGELOG `[1.6.0]` folded + dated (2026-08-01); `develop`→`main` merged (`2c9368b`); annotated tag `v1.6.0` pushed → `build-release.yml` (run `30703978929`) with the now-**blocking** quality-gate + test gates, then mac-arm64/mac-x64 `.dmg` + win `.zip` build and GitHub Release publish. Back-merged `main`→`develop` (both at `2c9368b`).
- **Quality gate:** develop CI green on the release content (full suite on ubuntu). Local run showed 69% coverage / 1611 passed; the only 5 failures were the documented env-sensitive `test_oneshot_runner` SSH-timeout cases (pass on CI), not regressions.
- **Branch protection (SEC-2, decision: admin bypass):** enabled on `main` via API — required status checks (`quality-gate`, `unit-tests (3.11/3.12)`, `integration-tests`), `enforce_admins: false` (admins merge directly so the `develop`→`main` release flow keeps working), force-push + deletion disabled. Blocks accidental red merges by non-admins.
- **Workspace-disconnect mitigation:** confirmed the disconnect is triggered by `git checkout <branch>` rewriting the watched working tree. Ran the release via ref-only ops (annotated tag on a SHA, FF ref pushes `2c9368b:develop`) to avoid checkouts; branch switches were only done between identical trees (no file changes). The one `checkout main` that disconnected had still completed server-side (false-negative spawn error).
- **Pending:** monitor `build-release` to green + verify artifacts attach; live update-pill check from a real 1.5.8 build once the Release publishes (QA §6b).

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
