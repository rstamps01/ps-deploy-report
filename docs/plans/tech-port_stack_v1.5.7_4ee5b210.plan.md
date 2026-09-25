---
name: Tech-Port stack v1.5.7
overview: Ship v1.5.7 by completing the in-flight TP-1/TP-2/SR-1/SR-5 stack and adding SR-3/SR-4. <customer-cluster> IB cluster is permanently inaccessible; SR-5 PDF output already manually verified by operator. SR-5 commits immediately as a quick win. `--from-json` CLI flag still ships in v1.5.7 as durable infrastructure (partially closes DEV-1, unblocks SB-1/RFE-1, becomes the long-term IB regression substitute for rendering-layer changes). SR-3 verifies via fixture-based parser+mapper integration tests against saved <customer-cluster> vnetmap text. SR-4 verifies via unit tests (IB override path) plus <lab-cluster> Eth regression (back-compat).
todos:
  - id: p1-sr5-verify
    content: "Phase 1: SR-5 PDF output verified manually by operator (no further verification needed)"
    status: completed
  - id: p1-sr5-commit
    content: "Phase 1: Commit SR-5 — fix(report): wrap IB MAC GIDs in Port Mapping tables"
    status: completed
  - id: p2-from-json-impl
    content: "Phase 2: Implement permanent --from-json CLI flag in src/main.py + tests (DEV-1 partial)"
    status: completed
  - id: p2-from-json-commit
    content: "Phase 2 commit: feat(cli): add --from-json offline replay flag (DEV-1 partial)"
    status: completed
  - id: p3-sr3-tests
    content: "Phase 3: TDD red — SR-3 tests in tests/test_vnetmap_parser.py + tests/test_enhanced_port_mapper.py + tests/test_data_extractor.py using <customer-cluster> vnetmap_output_*.txt fixtures"
    status: completed
  - id: p3-sr3-impl
    content: "Phase 3: Implement SR-3 — IB header parsing in vnetmap_parser + GUID→mgmt_ip alias in EnhancedPortMapper.switch_map"
    status: completed
  - id: p3-sr3-verify
    content: "Phase 3: Fixture-based integration test verifies zero 'Unknown switch IP' + IPL ports > 0 from <customer-cluster> vnetmap text + synthetic API switch list; <lab-cluster> Eth regression confirms back-compat"
    status: completed
  - id: p3-sr3-commit
    content: "Phase 3 commit: fix(port-mapping): resolve IB GUIDs to switch mgmt_ip via alias map (SR-3)"
    status: completed
  - id: p4-sr4-tests
    content: "Phase 4: TDD red — SR-4 tests in test_workflows + test_app + test_oneshot_runner for net_type threading"
    status: completed
  - id: p4-sr4-impl
    content: "Phase 4: Implement SR-4 — thread net_type from API into vnetmap_creds in app.py + oneshot_runner.py; consume override in vnetmap_workflow"
    status: completed
  - id: p4-sr4-verify
    content: "Phase 4: Unit tests prove IB override path; <lab-cluster> Eth regression run confirms 'Network type: ETH' still emitted with API consultation enabled"
    status: completed
  - id: p4-sr4-commit
    content: "Phase 4 commit: fix(workflow): use API net_type as authoritative cluster type (SR-4)"
    status: completed
  - id: p5-docs
    content: "Phase 5: Update TODO-ROADMAP, CHANGELOG, SR issue docs (SR-2/3/4 placeholders, SR-1/5 → Resolved, DEV-1 partial)"
    status: completed
  - id: p5-commit
    content: "Phase 5 commit: docs: roadmap + changelog + SR issue tracking for v1.5.7"
    status: completed
  - id: p6-quality-gate
    content: "Phase 6: Quality gate — flake8 + black + full pytest suite green"
    status: completed
  - id: p6-version-bump
    content: "Phase 6: Bump version 1.5.6 → 1.5.7 in 5 locations + CHANGELOG block"
    status: completed
  - id: p6-release-commit
    content: "Phase 6 commit: release(v1.5.7): TP-1/TP-2/SR-1/SR-3/SR-4/SR-5 + DEV-1 partial"
    status: completed
  - id: p6-merge-tag
    content: "Phase 6: Push branch, merge develop→main, tag v1.5.7, push tag, verify CI artifacts"
    status: pending
isProject: false
---

# Tech-Port stack v1.5.7 — adapted plan (<customer-cluster> permanently inaccessible; SR-5 manually verified)

## Branch state going in

`feature/tp-1-techport-discovery`, 4 commits ahead of `develop` (none pushed):

- `7b94453` TP-1 — VMS mgmt-IP widened to RFC1918 + 443 short-circuit
- `f49aa2b` TP-2 — empirical 443 candidate probing
- `6f421ac` SR-1 docs
- `8bba3aa` SR-1 fix — `tunnel_address` threaded into `vnetmap_creds`

Uncommitted: SR-5 implementation in [src/report_builder.py](src/report_builder.py) + [tests/test_report_builder.py](tests/test_report_builder.py) (8 SR-5 tests green, 205/205 regression). **PDF output manually verified by operator — wrap behavior confirmed correct.**

## Verification strategy (<customer-cluster> permanently lost)

- **SR-5:** done — operator visually verified the regenerated PDF (IB MACs wrap, Interface/Net columns no longer obscured).
- **SR-3:** fixture-based parser + mapper integration tests. Saved `output/scripts/vnetmap_output_192.168.2.2_*.txt` files become permanent fixtures (the actual <customer-cluster> IB topology text with GUID-header lines). Synthetic API switch list (constructed from the same fixture's hostname references) feeds `EnhancedPortMapper`. Integration test in [tests/test_data_extractor.py](tests/test_data_extractor.py) walks parser → mapper → extractor and asserts zero `Unknown switch IP` warnings, IPL ports > 0.
- **SR-4:** unit tests for the IB override path (mocked `api_handler.get_cluster_network_configuration()` returning `{"net_type": "ib"}`); <lab-cluster> Eth-cluster live regression confirms back-compat (heuristic answer matches API answer = `ETH`).
- **`--from-json`:** ships in v1.5.7 as durable infrastructure; not used to verify any of SR-3/SR-4 (which touch data-extraction / workflow layers below `report_builder`). Saved `vast_data_mammoth_*.json` files were generated WITH the SR-3 bug baked in, so replaying them does not exercise the fix path.

## Phase 1 — SR-5 commit (quick win, no new work)

Verification complete (manual by operator). Commit the staged changes as the next stacked commit.

Stacked commit: `fix(report): wrap IB MAC GIDs in Port Mapping tables (SR-5)`

## Phase 2 — Permanent `--from-json` CLI flag (durable infrastructure)

Ships in v1.5.7 even though no longer needed for this branch's verification. Locks in the long-term substitute for losing IB-cluster access on rendering-layer fixes; partially closes [DEV-1](docs/TODO-ROADMAP.md); unblocks [SB-1](docs/TODO-ROADMAP.md) and [RFE-1](docs/TODO-ROADMAP.md).

- Add `--from-json <path>` and `--output <path>` argparse args in [src/main.py](src/main.py)
- Branch in `main()` before API connect: load JSON, skip `api_handler` + `data_extractor`, call `VastReportBuilder.generate_pdf_report(processed_data, output_path)` directly
- Helper `_run_from_json(json_path, output_path)` returning bool
- Schema sanity check: confirm top-level `sections` key exists; reject early with actionable error
- Unit tests in `tests/test_main_from_json.py` (~4 tests: success, missing file, malformed JSON, bad output dir)
- One end-to-end test using `reports/vast_data_<cluster>_20260501_173741.json` as fixture (verify PDF byte-size > 100KB, contains expected cluster name in metadata)

~30-45 min, ~50-100 LOC.

Stacked commit: `feat(cli): add --from-json offline replay flag (DEV-1 partial)`

## Phase 3 — SR-3 (GUID → mgmt_ip aliasing)

Design (recommended path):

1. Keep `switch_ip = '0x…'` (GUID) in topology entries for back-compat with any consumers that read this field today
2. Add new `switch_guid` + `switch_hostname` fields populated from `Switch MF0;<hostname>:<model> - <guid>` header lines in vnetmap output
3. Add GUID alias to `EnhancedPortMapper.switch_map` matching `switch_hostname` against API switch `name`

Touch points:

- [src/vnetmap_parser.py](src/vnetmap_parser.py) — new `_parse_ib_switch_headers()` regex `r"Switch MF0;([^:]+):(\S+) - (0x[0-9a-fA-F]+) has"`; augment `_parse_topology_section` to set `switch_guid` + `switch_hostname` when `parts[1]` starts with `0x`
- [src/enhanced_port_mapper.py](src/enhanced_port_mapper.py) — `_build_switch_map` adds GUID alias entries when external_port_map has `switch_guid` matching API `name`

TDD:

- `tests/test_vnetmap_parser.py::TestSR3IBHeaderParsing` — 3 tests using saved <customer-cluster> fixture (`output/scripts/vnetmap_output_192.168.2.2_20260501_173741.txt`): GUID→hostname map populated; topology entries get `switch_guid`+`switch_hostname` fields; Eth fixture unaffected.
- `tests/test_enhanced_port_mapper.py::TestSR3GuidAliasing` — 3 tests: GUID resolves to designation when alias built, Eth path unaffected (no aliasing applied), missing hostname graceful (logs warning, falls back to `SW?-port`).
- `tests/test_data_extractor.py::TestSR3IntegrationMammothFixture` — 1 integration test: feeds the saved <customer-cluster> vnetmap_output text + a synthetic API switch list (`[{"name": "vast-switch1-bot", "mgmt_ip": "<ip>"}, {"name": "vast-switch2-top", "mgmt_ip": "<ip>"}]`) through `VNetMapParser` → `EnhancedPortMapper` → assert zero `Unknown switch IP` log records, all 40 connections resolved to `SWA-P*` / `SWB-P*` designations, IPL inference produces ≥ 1 connection with port count > 0.

Verification (no live cluster needed):

- Integration test above is the authoritative smoke test (replicates the exact <customer-cluster> pipeline end-to-end through extraction layer).
- <lab-cluster> Eth regression run: confirm Eth path produces no `switch_guid` field, no GUID aliases, IPL inference still works as before. Compare port designations against a pre-fix baseline run.

Stacked commit: `fix(port-mapping): resolve IB GUIDs to switch mgmt_ip via alias map (SR-3)`

## Phase 4 — SR-4 (net_type from API)

Design (recommended path):

- [src/app.py](src/app.py) `_run_report_job` calls `api_handler.get_cluster_network_configuration()` after auth, extracts `net_type`, threads into `vnetmap_creds["net_type"]`
- Same in [src/oneshot_runner.py](src/oneshot_runner.py) `_get_workflow_credentials` for Test-Suite-tile parity
- [src/workflows/vnetmap_workflow.py](src/workflows/vnetmap_workflow.py) consumes `self._credentials.get("net_type")`; if set, override the `if switch_ips: ETH else: IB` heuristic; else fall back to existing logic for back-compat

TDD:

- `tests/test_workflows.py::TestSR4NetTypeOverride` — 3 tests (`net_type='ib'` overrides switches-present heuristic, `net_type='eth'` confirms heuristic where they agree, missing `net_type` falls back to legacy heuristic).
- `tests/test_app.py::TestSR4NetTypePropagation` — 1 test confirming `vnetmap_creds["net_type"]` set from `get_cluster_network_configuration()` mock when present.
- `tests/test_oneshot_runner.py::TestSR4NetTypePropagation` — 1 test for parity.

Verification:

- IB override path: unit tests only (no IB cluster available). Mocked API consultation returning `{"net_type": "ib"}` proves the override fires; an additional unit test consuming the saved <customer-cluster> `vast_data_mammoth_*.json` `network_settings` extract confirms the field shape matches what the helper expects from a real IB cluster.
- <lab-cluster> Eth regression run: confirm `Network type: ETH` log line still emitted; both heuristic and API path agree.

Stacked commit: `fix(workflow): use API net_type as authoritative cluster type (SR-4)`

## Phase 5 — Wrap-up docs + roadmap

- Promote TP-1, TP-2, SR-1, SR-3, SR-4, SR-5 in [docs/TODO-ROADMAP.md](docs/TODO-ROADMAP.md) from "In progress / Planned" to "Done"
- Add SR-2 placeholder doc (deferred — cosmetic Onyx pre-probe warning)
- Update [CHANGELOG.md](CHANGELOG.md) `[Unreleased]` block with v1.5.7 entries: TP-1, TP-2, SR-1, SR-3, SR-4, SR-5, DEV-1-partial (`--from-json`)
- Update [docs/issues/SR-1/01-summary.md](docs/issues/SR-1/01-summary.md), [docs/issues/SR-5/01-summary.md](docs/issues/SR-5/01-summary.md) status → Resolved (note SR-5 manually verified by operator since <customer-cluster> no longer accessible)
- Create [docs/issues/SR-3/01-summary.md](docs/issues/SR-3/01-summary.md), [docs/issues/SR-4/01-summary.md](docs/issues/SR-4/01-summary.md), [docs/issues/SR-2/01-summary.md](docs/issues/SR-2/01-summary.md)
- Save <customer-cluster> fixture artifacts (vnetmap_output_*.txt + one representative vast_data_mammoth_*.json + the SR-5-verified PDF) under `tests/data/golden/mammoth_ib/` for permanent IB regression baseline

Stacked commit: `docs: roadmap + changelog + SR issue tracking for v1.5.7`

## Phase 6 — Release v1.5.7

Per [.cursor/rules/release-packaging-12.mdc](.cursor/rules/release-packaging-12.mdc):

1. Quality gate: `flake8 src/ tests/`, `black --check --line-length 120 src/ tests/`, `python3 -m pytest tests/ -v` all green
2. Bump version 1.5.6 → 1.5.7 in 5 locations: [src/app.py](src/app.py) `APP_VERSION`, [src/main.py](src/main.py) argparse `version=`, [src/**init**.py](src/__init__.py) `__version__`, [packaging/vast-reporter.spec](packaging/vast-reporter.spec) `CFBundleShortVersionString` + `CFBundleVersion`, [README.md](README.md) version refs
3. Add `## [1.5.7] - 2026-05-15` block to [CHANGELOG.md](CHANGELOG.md)
4. Optional: create `RELEASE_NOTES_v1.5.7.md` for highlight bullets
5. Final commit: `release(v1.5.7): TP-1/TP-2/SR-1/SR-3/SR-4/SR-5 + DEV-1 partial`
6. Push `feature/tp-1-techport-discovery` → open PR or fast-forward merge to `develop`
7. Merge `develop` → `main`
8. Tag `v1.5.7`, push tag → CI builds .dmg + .zip and attaches to GitHub Release
9. Verify GitHub Release artifacts attached

## Out of scope for this branch

- RPT-VALIDATION-1/2 UI investigation (Phase 2 from earlier plan) → defer to its own branch after v1.5.7
- TSE-9 coverage push, UI-5 restyle, DOC-13/14 → roadmap items, separate branches
- SR-2 cosmetic Onyx pre-probe warning fix → tracked but not implemented

## Risk assessment

| Risk | Mitigation |
|---|---|
| **No live IB cluster for end-to-end SR-3 / SR-4 verification (<customer-cluster> permanently inaccessible).** | Fixture-based integration test in `tests/test_data_extractor.py` walks the entire parser → mapper → extractor pipeline using the actual saved <customer-cluster> `vnetmap_output_192.168.2.2_*.txt` text. SR-4 unit tests use a real `network_settings` extract from the saved <customer-cluster> `vast_data_mammoth_*.json` to validate the field shape. <customer-cluster> fixtures preserved under `tests/data/golden/mammoth_ib/` for permanent regression. |
| SR-3 fix doesn't behave correctly on edge cases (1-switch IB cluster, mixed-vendor switches, GUID collision across clusters) | Unit tests cover missing-hostname (graceful `SW?-port` fallback), single-switch IB topology, and GUID-not-in-API-list (warning logged, no crash) |
| SR-4 Eth path regresses (heuristic gave the right answer for Eth previously) | Back-compat fallback when `net_type` is missing or unrecognized; <lab-cluster> live regression run validates Eth path end-to-end |
| SR-5 layout already verified — risk now: future report_builder change re-introduces overflow | The 8 `TestSR5FormatMacCell` boundary tests pin behavior; future regression caught at unit-test layer |
| `--from-json` schema drift over future releases | Schema sanity check rejects malformed JSON early with actionable error; helper isolated for easy maintenance |
| Mypy 2 pre-existing errors in report_builder.py mistakenly attributed to this branch | Already verified pre-existing via stash test; document in commit message |
