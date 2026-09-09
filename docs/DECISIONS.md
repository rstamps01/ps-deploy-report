# Decisions & Memlog

Append-only decision log (ADR-lite) **and** working-memory ledger for the agentic pipeline (pipeline §24/§27). Two uses, one file:

- **Decisions** — every approval, plan decision, superseded/deleted item, and escalation resolution, with date + rationale + approver. The traceability backbone for change-control and the "open decisions" list.
- **Memlog** — skills and subagents append short, chronological, machine-readable progress/coordination entries so long runs are **resumable** after an interruption and parallel work stays coordinated.

**Rules:** append only (never rewrite history); newest at the top of each section; keep entries terse; redact secrets. Owned by the `project-manager`, appended to by all skills/subagents.

---

## Decisions (newest first)

### 2026-09-02 — Library and built-in devices matched as one namespace
- **Decision:** `get_device_height` / `get_device_image_filename` / `NetworkDiagramGenerator.load_hardware_image` now merge the built-in catalog and the user Library into a single namespace matched longest-key-first, instead of searching all built-ins before any user entry.
- **Rationale:** the built-in catalog contains broad vendor fallbacks (`hpe`, `arista`, `broadwell`, `cascadelake`, `sanmina`). Under built-in-first precedence those keys swallowed any user device from the same vendor, which meant adding a device to the Library could not override a vendor default — defeating the Library's purpose. A user's 1U `hpe_turin_cbox` was claimed by the bare `hpe` key and drawn at 2U; because the rack diagram's image lookup already used merged precedence, the result was the correct artwork stretched 1.8x. Verified against all 39 catalog keys: exactly one result changes (the reported device), and vendor fallbacks still apply where nothing more specific matches. **Approver:** user (2026-09-02).

### 2026-09-02 — EBox height short-circuit left unfixed for now (HWL-3)
- **Decision:** the `ebox`/`enclosure` early return in `get_device_height` stays as-is; recorded as roadmap HWL-3 rather than folded into the precedence fix.
- **Rationale:** it returns 1U before consulting either catalog, so the built-in `supermicro_milan_ebox` and `smc_milan_ebox` — both declaring 2U — render at 1U, and no Library entry can define a 2U EBox. Correcting it changes the rendered height of every existing Milan EBox cluster, so it needs confirmation of the true rack height first; bundling a second behavioral change into a targeted bug fix would obscure which change moved a diagram. **Approver:** agent proposal, surfaced to user.

### 2026-08-01 — v1.6.1 merged to `develop` but deliberately not tagged
- **Decision:** the post-1.6.0 correction batch ([PR #18](https://github.com/rstamps01/ps-deploy-report/pull/18)) merges to `develop` and stops there; no version bump, tag, or release yet.
- **Rationale:** two of the eleven requested items (Quick Start upgrade steps, Update Tools walkthrough) need screenshots the user is supplying. Tagging now would ship a release whose own documentation is still being rewritten, and would burn a version number to publish it twice. **Approver:** user (2026-08-01).

### 2026-08-01 — Do not automate the macOS in-place upgrade
- **Decision:** keep the upgrade manual; prevent the failure instead by stating the constraint in the Download dropdown and offering **Exit & Upgrade**, which reuses the existing `/shutdown` endpoint.
- **Rationale:** an app cannot replace its own running bundle. Doing so needs a signed helper or a separate updater process outliving the app — disproportionate for an unsigned internal tool, and it introduces a code-signing requirement we do not currently have. The observed failure is a refused drag into `/Applications`, which a clean shutdown prevents outright. **Approver:** user (accepted the alternative they proposed).

### 2026-08-01 — Dependabot's Pages bump taken manually, as a pair
- **Decision:** closed Dependabot PR #10 (`upload-pages-artifact` v3→v5) and bumped `upload-pages-artifact` **and** `deploy-pages` together by hand.
- **Rationale:** the two actions are a matched pair and the artifact format changed between v4 and v5. Merging the upload half alone leaves a mismatch whose failure mode is a Pages deploy that publishes an empty site while still reporting success — worse than the outdated version it replaces. **Approver:** agent (documented in `docs/development/GITHUB-WORKFLOW.md`).

### 2026-08-01 — SEC-3 / SEC-4 documented rather than fixed
- **Decision:** plaintext credentials in `config/cluster_profiles.json` (SEC-3) and the ungated `/validation-results` route (SEC-4) are recorded in the roadmap and left as-is.
- **Rationale:** SEC-3 needs a key-storage decision and a migration for existing profiles; SEC-4 would withdraw access someone may depend on. Neither belongs in a patch release made of unrelated corrections. **Approver:** user (2026-08-01).

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

### 2026-08-01 — planalyzer promoted to L3 + coverage ratchet (pilot complete)

- Merged [`planalyzer` PR #3](https://github.com/rstamps01/planalyzer/pull/3): `adopt-existing --tier L3` (4 created — `deliver-autonomously`, `remediate-failure`, `docs/PIPELINE-METRICS.md`; 41 existing files preserved) plus the coverage ratchet L3 assumes.
- **Coverage wired for a non-Python adopter:** `@vitest/coverage-v8` over `src/lib/**`, thresholds in `vitest.config.ts` (lines/functions 60, branches 70), `npm run test:coverage`; manifest `coverage_floor: 60` and blocking gate `test` → `test_cov`. Baseline **64.53% lines** (165 tests). Threshold proven blocking (99% → exit 1) before merge.
- **Manifest-driven CI validated:** the GH Actions gate picked up `test_cov` with **no workflow edit** — the adapter indirection works as designed across stacks.
- **Portfolio:** all three projects now **L3 / ADF 0.3.0 / doctor 100** (`docs/PORTFOLIO.md` refreshed). The brownfield pilot is complete end-to-end: L1 → L2 → L3 on a Node/Next repo with zero framework changes required.

### 2026-08-01 — planalyzer L1 merged + L2 promoted
- Merged [`planalyzer` PR #1](https://github.com/rstamps01/planalyzer/pull/1) (ADF L1) and PR #2 (L2 promote).
- Portfolio: planalyzer now **L2 / ADF 0.3.0 / doctor 100**. Optional remaining: L3, coverage floor, GitLab switch-over.

### 2026-08-01 — M6 Phase E executed: framework-doctor + portfolio (ADF v0.3.0)
- **Shipped [`agentic-dev-framework` v0.3.0](https://github.com/rstamps01/agentic-dev-framework/releases/tag/v0.3.0)** — `framework_doctor.py` (score + remediations, `--target`/`--portfolio`), `framework-doctor` skill, `PM: doctor`/`PM: portfolio`, `docs/PORTFOLIO.md`.
- **Portfolio (all green):** vast-asbuilt-reporter L3 **100**, planalyzer L1 **100**, ADF L3 **100**.
- **This repo remediated:** added missing `update-framework` + `framework-doctor` skills; set `adf_version: "0.3.0"`. Doctor accepts `docs/development/` homes for PIPELINE-SECRETS / REPO-STRUCTURE.
- **M6 complete** (Phases A–E). Remaining follow-ups are optional (planalyzer → L2, richer update-framework merge).

### 2026-08-01 — M6 Phase D executed: brownfield pilot on planalyzer (ADF L1)
- **Pilot target:** [`rstamps01/planalyzer`](https://github.com/rstamps01/planalyzer) (formerly plan-analyzer) — Next.js/TypeScript Node sibling of this Python reference impl.
- **Flow:** `adopt-existing` → dry-run L1 → apply create-only (**33 created, 1 skipped** `.env.example`). Project-local skills (`comparing-plan-analysis`, `tracking-change-control`) and rules (`project-standards.mdc`, `change-control.mdc`) untouched. Pruned `python-standards-04.mdc`.
- **Manifest:** Node commands from existing npm scripts (`lint` / `format:check` / `typecheck` / `test` / `build`); `adf_version: 0.2.0`; version sync from `package.json`; coverage floor 0 until vitest coverage is wired. GitHub Actions CI added **alongside** GitLab (switch-over deferred).
- **Evidence:** validate --strict ✅, skill-conformance ✅, version-sync ✅, lint/typecheck/test ✅ (165 passed). Pre-existing prettier debt deferred (not introduced by adopt). PR: https://github.com/rstamps01/planalyzer/pull/1
- **Remaining M6 (Phase E):** `framework-doctor` + portfolio PM roll-up across adopters.

### 2026-08-01 — M6 Phase C executed: ADF bootstrap installer, tiers & adoption skills (v0.2.0)
- **Shipped [`agentic-dev-framework` v0.2.0](https://github.com/rstamps01/agentic-dev-framework/releases/tag/v0.2.0)** (gitflow: develop→main→tag, Framework CI green on both, GitHub Release published). Automates adoption.
- **Installer (`scripts/adf_bootstrap.py`):** copies the tier-appropriate core into any target repo — **idempotent + non-destructive** (create-if-absent, `--force` to overwrite, never deletes), `--dry-run` plan, `new`/`adopt` modes, post-install self-check (manifest-validate + skill-conformance), refuses to install onto itself.
- **Tiers (`core/tiers.yml`):** additive L1⊂L2⊂L3 skill+docs map. `update-framework` ships to every tier; `new-project`/`adopt-existing` are operator skills excluded from all tiers (never land in an adopter). Core is now **20 skills**.
- **Adoption skills:** `new-project` (greenfield scaffold) + `adopt-existing` (brownfield, **dry-run-first**, reconciles existing CI/docs/structure by hand).
- **Validated:** dry-run + real L3 install into a scratch target = 44 files; idempotent re-run skipped all 44; target manifest-validate + conformance + gate-resolution green. **30 ADF tests** (18 adapter + 12 installer) + full self-gate green.
- **Remaining M6 (Phase D–E):** pilot `adopt-existing` on VAST Plan Analyzer (non-destructive), then `framework-doctor` + portfolio PM roll-up.

### 2026-08-01 — M6 Phase B executed: ADF core extracted to a standalone repo
- **Created [`rstamps01/agentic-dev-framework`](https://github.com/rstamps01/agentic-dev-framework) (private), v0.1.0** — the portable Agentic Dev Framework, extracted from this reference implementation (gitflow: `main` + `develop`, Framework CI dogfooding its own gate).
- **Extracted (`core/`):** 18 stack-agnostic skills (all lifecycle + orchestration + the new `update-framework`), git-guard hooks, the manifest adapter, and the skill-conformance check. **Templates (`templates/`):** genericized `pipeline.yml`, `AGENTS.md`, 10 process rules, a manifest-driven `.github/ci.yml`, `env.example`, and docs scaffolds. Plus `HANDBOOK.md` (principles→governance), README, LICENSE, ADF's own `VERSION`/`framework_version.py`/CHANGELOG and `.cursor/pipeline.yml`.
- **Portability fix (also applied here):** `scripts/pipeline_manifest.py` is now **location-independent** — it discovers `.cursor/pipeline.yml` by walking up from cwd (and from the script's own location) and derives repo-root from the manifest, so the identical file works at `<repo>/scripts/` (adopter) or `core/scripts/` (framework). `check-skill-conformance.py` (ADF copy) gained `--skills-dir`. 18 adapter tests still green here.
- **Self-gate (ADF):** format + lint (black-compatible `.flake8`) + skill-conformance (18) + manifest-validate (strict, both ADF + shipped template) + version-sync + adapter tests — all green; Framework CI running on both branches.
- **Framework/instance model proven:** this repo is ADF's first adopter. Remaining (Phase C–E): `bootstrap-pipeline`, `new-project`/`adopt-existing` (dry-run-first), maturity-tier installer, `framework-doctor` + portfolio PM, then pilot on VAST Plan Analyzer.

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
