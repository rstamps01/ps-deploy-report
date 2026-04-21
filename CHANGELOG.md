# Changelog

All notable changes to the VAST As-Built Report Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.5.3] - 2026-03-21

Test-Suite log-triage release — addresses five defects (RM-1..RM-5)
surfaced by triage of the 5:44:20 operator-log excerpt from bundle
`validation_bundle_selab-var-202_20260421_054733.zip`. RM-1 is a
credential-exposure bug and was landed first; the remaining four ride
on the same release to keep a single coherent change set.

### Security

- **RM-1: Redact per-switch passwords from operator logs.** Before this
  release, `ScriptRunner.execute_remote()` echoed the full shell command
  to the UI output pane, which for `VnetmapWorkflow` meant the vnetmap
  `-p` argument and the embedded JSON map of per-switch passwords
  rendered in plaintext in every workflow log and in the `vnetmap_command`
  field of the step summary (and therefore the result bundle).
  - `ScriptRunner.execute_remote()` and `execute_remote_persistent()`
    now accept an optional `display_command=` kwarg; when provided it
    is used for logging and the real `command` is still what's sent to
    the remote host.
  - `SessionManager.start_session()` (tmux path) received the same
    `display_command` parameter — without it the credential would still
    leak when `execute_remote_persistent` fell back through the session
    manager.
  - `VnetmapWorkflow._step_generate_command` now builds and emits a
    `<switch-password>`-placeholder command for UI logs; the real
    command is stored internally only for execution.
  - `VnetmapWorkflow._step_run_vnetmap` (both the per-switch-password
    fast path and the candidate-sweep legacy path) passes
    `display_command=` to `ScriptRunner` and persists the redacted form
    to `_step_data["vnetmap_command"]` so bundles/manifests never
    capture the secret.
  - **Operational follow-up** (still required, not automated by this
    release): rotate any switch passwords that were captured in prior
    logs or result bundles, and scrub archived copies that predate the
    fix.
- **RM-1 supplementary: stop committing switch passwords to the repo.**
  - `config/config.yaml.template` no longer ships plaintext factory
    default switch passwords; the `advanced_operations.default_switch_passwords`
    list is now `[]` with commentary on the two supported secret
    channels (local `config/config.yaml`, or
    `VAST_DEFAULT_SWITCH_PASSWORDS` env var, colon-separated).
  - `config/config.yaml` is now listed in `.gitignore` and was removed
    from the repo (`git rm --cached`) so user-local secrets never get
    staged accidentally.
  - The `_FALLBACK_SWITCH_PASSWORDS` tuple was removed from
    `src/oneshot_runner.py`; autofill now loads candidates exclusively
    from the config file or the env var, and logs a `WARNING` when
    neither is populated (instead of silently using baked-in defaults).
  - `src/app.py` bootstrap now copies `config.yaml.template` when the
    user has no `config/config.yaml`, with a fallback to any legacy
    `config.yaml` for older bundles.

### Fixed

- **RM-2: Health check respects per-switch SSH passwords.**
  `HealthChecker.run_switch_ssh_checks()` now reads an optional
  `switch_ssh_config["password_by_ip"]` map and looks up the correct
  password per switch IP, falling back to `switch_ssh_config["password"]`
  only when the map has no entry. `OneShotRunner._run_health_checks`
  populates the map from the credentials that pre-validation already
  resolved, so MLAG / Switch NTP / Switch Config Readability checks no
  longer fail on the switch that needs the fallback credential (observed
  regression on `10.143.11.156`). A malformed (non-dict) map is ignored
  safely and falls back to the primary password.
- **RM-3: `MINOR` VAST alarms no longer log at `[ERROR]`.**
  `SupportToolWorkflow._step_run_support_tools` used naïve substring
  matching (`"error" in line.lower()`), so any `MINOR`-severity alarm
  whose message text happened to contain the word "error" (e.g. a DNS
  query "failed due to internal error") was promoted to `[ERROR]` in
  the live log. Classification now parses the structured alarm format
  (`<timestamp> | <SEVERITY> | <message>`) first via
  `_classify_alarm_line`: `CRITICAL → error`, `MAJOR → warn`,
  `MINOR/INFO/UNKNOWN → info`. The legacy keyword-based path remains as
  a fallback for non-alarm lines.
- **RM-4: Log-line copy/paste from the output pane.** Text selection in
  the Advanced Operations output pane used to yield strings like
  `12:44:29[INFO]` because the HTML emitted `</span>[` with no
  separator. Both `frontend/templates/advanced_ops.html` and
  `frontend/templates/reporter.html` now emit `</span> [`, so copies
  paste as `HH:MM:SS [LEVEL] message` for triage tickets.
- **RM-5: Prior vperfsanity output is preserved in the bundle.** When
  the vperfsanity workflow is skipped this run (it can take ~30 min)
  the bundler previously shipped a one-line `performance/vperfsanity_STALE.txt`
  placeholder, discarding any prior-run `vperfsanity_results_*.txt`
  file. With this release the bundler instead attaches the prior file
  as `performance/vperfsanity_PRIOR_<original-name>.txt` prefixed with
  a banner that names the source, its original mtime, and the current
  run's start time (so reviewers cannot mistake it for current-run data).
  Behaviour is controlled by the new `bundle.include_prior_vperfsanity`
  config key (default `true`); setting it to `false` restores the
  pre-RM-5 behaviour.

### Changed

- **Result bundle manifest** bumped to version **1.2**. New fields:
  - `vperfsanity_prior_source` — original filename of the prior
    vperfsanity file that was rescued, or `null` if none.
  - `include_prior_vperfsanity` — the flag that was in effect when the
    bundle was produced.
- **`SUMMARY.md`** now reports vperfsanity as "STALE (included as
  PRIOR with banner) — `vperfsanity_PRIOR_<name>`" when the rescue
  branch fired, rather than "STALE — `<name>` (not included)".
- **`config/config.yaml.template`** gained a new top-level `bundle:`
  section with `include_prior_vperfsanity: true` for discoverability.

### Tests

- `tests/test_script_runner.py::TestScriptRunnerRedaction` (3 tests)
  proves the `display_command` kwarg suppresses the real command in
  emitted log entries while still running it.
- `tests/test_health_checker.py::TestSwitchSSHPerIPPassword` (3 tests)
  covers per-IP password resolution, fallback to primary, and safe
  handling of malformed maps.
- `tests/test_workflows.py::TestAlarmLineClassifier` (7 tests) is a
  table-driven check of the alarm-severity → log-level mapping, the
  "MINOR + `error` in message ≠ ERROR" regression, and the fallback
  behaviour for non-alarm lines.
- `tests/test_result_bundler.py::TestPriorVperfsanity` (6 tests)
  covers the prior-file attach path, the flag-off fallback, the
  manifest fields, the SUMMARY.md marker, the fresh-run no-op, and the
  `get_result_bundler(include_prior_vperfsanity=...)` factory plumbing.
- `tests/test_oneshot_runner.py::TestSwitchPasswordCandidates::test_autofill_without_config_yields_empty_candidates`
  updated to match the RM-1 supplementary behaviour (empty candidate
  list + WARNING log when neither config nor env var is populated).

### Fixed (Download Bundle served stale zip after successful one-shot run)

- **Symptom** (reported from `import/logs/output-results-0518.txt`):
  a successful Test Suite run at 12:18:14 UTC produced
  `validation_bundle_selab-var-202_20260421_051813.zip`, but clicking
  **Download Bundle** 12 seconds later returned
  `validation_bundle_selab-var-202_20260421_050004.zip` — the *previous*
  run's zip from earlier in the day.  Every subsequent click returned
  the same stale zip (log lines 3103–3107).
- **Root cause:** `_record_last_oneshot_bundle` in `src/app.py` updates
  the `ONESHOT_LAST_BUNDLE` registry via `current_app.config[...]`, but
  it's invoked from a bare `threading.Thread` (the `_run` closure in
  `advanced_ops_oneshot_start`) that has **no Flask application
  context** pushed.  That raised `RuntimeError: Working outside of
  application context`, which the outer `except Exception: pass`
  silently swallowed.  The registry was therefore never refreshed
  after the first cold-start rehydration, and
  `/advanced-ops/bundle/last` kept serving whatever zip the startup
  scan had captured.
- **Fix:** `src/app.py::advanced_ops_oneshot_start._run` now pushes an
  explicit `app.app_context()` around the registry-update call, and
  the silent `except: pass` is replaced with a `logger.warning(...)`
  that surfaces any residual failure (so future regressions show up as
  a warning log instead of a mysterious "stale download" user report).
- **Tests:** new `TestOneShotLastBundleBackgroundThreadUpdate` class
  in `tests/test_app.py` (4 tests) — proves the helper requires an app
  context (regression guard), proves `app.app_context()` at the call
  site updates the registry from a background thread that never saw a
  request, and proves the subsequent `/advanced-ops/bundle/last`
  response names the new bundle.  Also covers the no-op paths
  (run didn't complete / bundle file missing).

### Fixed (Logical Network Diagram + Port Mapping — spine visibility and crossing paths)

Addresses two visual defects seen in `/health` report screenshots:

1. **Leaf-switch paths crossed at the top of the Logical Network Diagram.**
   The renderer placed rack-local switches in the order the API returned
   them, so the physical switch serving Network B could land in the
   left-hand SWA position while its Network A connections were still
   drawn green-to-left. That produced the diagonal crossing pattern
   reported in the screenshots.
2. **No spine ↔ leaf mapping in either the diagram or the Port Mapping
   tables.** Only leaf switches received Port-to-Device Mapping tables,
   and the only uplink lines ever drawn were pulled from
   `ipl_connections` — a list the collector populated only when every
   switch in the pair advertised LLDP on port `swp29..swp32` **and**
   both sides used symmetric port numbers.

### Changed

- `src/network_diagram_v2.py`: new static helper
  `RackCentricDiagramGenerator._sort_switches_by_network()` re-orders
  per-rack switches before rendering so that the switch with
  majority-Network-A connections always lands at position 0 (SWA / left)
  and the majority-B switch at position 1 (SWB / right). Falls back to
  `mgmt_ip` ascending, matching the canonical ordering used by
  `EnhancedPortMapper._build_switch_map`. Eliminates the crossing lines
  entirely.
- `src/data_extractor.py`: `_infer_ipl_from_switch_pair` is no longer
  restricted to exactly two leaves. Given a populated `switch_map` it
  now emits one inferred `IPL` per leaf pair **and** one inferred
  `spine_uplink` per (leaf, spine) pair, so the diagram can still draw
  something meaningful when `vnetmap` returns no LLDP neighbor blocks.
  Inferred rows carry `notes` ending in `(inferred)` so rendering can
  style them distinctly if desired.
- `src/external_port_mapper.py`: `_collect_ipl_connections` and
  `_parse_cumulus_lldp_for_ipl` now perform a generalized LLDP walk
  across **every** port on **every** switch when callers supply a
  `switch_hostname_map` (hostname → mgmt_ip) and `spine_ips`. Each
  discovered edge is deduplicated (unordered endpoint pair) and
  classified with a `connection_type` of `ipl`, `spine_uplink`, or
  `spine_fabric`. The legacy narrow `swp29..swp32` symmetric-port scan
  is preserved when no map / spine list is provided, so existing
  callers see identical output.
- `src/app.py`, `src/oneshot_runner.py`, `src/main.py`: build and pass
  the `switch_hostname_map` + `spine_ips` arguments to
  `ExternalPortMapper` from the switch inventory (spines identified via
  the `role` / `switch_type` fields).
- `src/report_builder.py`: new `_create_spine_port_tables()` helper
  renders a dedicated `SP1 (<hostname>) Port-to-Device Mapping` table
  for every spine switch that has spine-uplink or spine-fabric edges.
  The leaf tables in the same section now include `Uplink` rows for any
  `spine_uplink` edge that terminates on that leaf, sourced from the
  same `ipl_connections` list.
- **PMI-4 — Onyx generalized LLDP walk.**
  `src/external_port_mapper.py::_parse_onyx_lldp_for_ipl` now mirrors
  the Cumulus rewrite: whenever `switch_hostname_map` or `spine_ips` is
  populated, every `Eth*` / `swp*` port on every Onyx switch is
  inspected, the symmetric-port check is dropped, and neighbors are
  resolved via `_resolve_neighbor_to_switch_ip` so leaf-to-spine
  uplinks on arbitrary ports are discovered. The historical
  `Eth1/29..Eth1/32` symmetric-port heuristic is preserved as a
  fallback for callers that don't supply a hostname map, so legacy
  two-leaf Onyx deployments see identical output.
- **PMI-5 — vnetmap fabric-report capture.**
  `src/workflows/vnetmap_workflow.py::_step_save_output` now pulls
  `/vast/log/vnetmap-*.txt` (the detailed LLDP dump `vnetmap.py` writes
  on cnode-1 for every switch in the fabric) and splices it into the
  saved `vnetmap_output_<cluster>_<ts>.txt`. The merged file feeds
  straight into `VNetMapParser._parse_lldp_neighbors`, so
  support-bundle / offline runs that disable per-switch SSH can now
  recover full spine visibility without any additional credentials.
  New helpers `_fetch_fabric_report()` and `_merge_fabric_report()`
  encapsulate the SSH fetch (sentinel-delimited, failure-safe) and the
  append-with-delimiter merge. The structured results JSON now records
  `fabric_report_path` and `fabric_report_bytes` so operators can see
  at a glance whether the report was recovered.

### Tests

- `tests/test_network_diagram_v2.py`: new `TestSortSwitchesByNetwork`
  class — direct coverage for the helper (A-majority at position 0,
  fallback to mgmt_ip, empty input) plus an integration test through
  `_build_rack_groups` that confirms the rack's `switches` list is
  ordered correctly end-to-end.
- `tests/test_data_extractor.py`: new `TestInferIplFromSwitchPair`
  class covering two-leaf clusters (single IPL), three-switch clusters
  (one IPL + one spine_uplink per leaf), four-leaf clusters (all six
  pairings), and empty-input edge cases.
- `tests/test_external_port_mapper.py`: new `TestEdgeClassification`,
  `TestNeighborResolution`, and `TestCumulusLldpGeneralizedWalk`
  classes covering the new `_classify_edge`,
  `_resolve_neighbor_to_switch_ip`, and generalized walk paths, plus an
  explicit regression guarding the legacy narrow scan for callers that
  don't supply a hostname map.
- `tests/test_report_builder.py`: new `TestSpinePortTables` class
  covering spine-table emission, leaf-IP exclusion from spine
  candidates, and the no-spine-uplinks early return.
- `tests/test_external_port_mapper.py`: new `TestOnyxLldpGeneralizedWalk`
  class covering PMI-4 — generalized mode emits both IPL and
  spine-uplink edges, drops unresolved neighbors, skips self-
  advertisements, and the legacy narrow scan is preserved exactly when
  no hostname map is provided.
- `tests/test_workflows.py`: new `TestVnetmapFabricReportCapture` class
  covering PMI-5 end-to-end — the expected shell command is issued
  with the missing-file and path sentinels, SSH / permission / OS
  failures all return `(None, None)` without aborting the save step,
  the merged file is parseable by `VNetMapParser._parse_lldp_neighbors`
  (regression guard: spine uplink 10.1.1.156 → 10.1.1.153 is now
  recovered), and `fabric_report_path` / `fabric_report_bytes` are
  recorded in the structured results JSON.

### Notes

- Both follow-ups originally deferred at the end of Phase 3 are now
  complete: Onyx parity with the Cumulus generalized walk (PMI-4), and
  `vnetmap` fabric-report capture for offline / support-bundle runs
  (PMI-5).

## [1.5.2] - 2026-03-21

### Fixed (validation bundle no longer ships stale, cross-run files)
- **Downloaded `validation_bundle_…_<ts>.zip` contained 7 files that
  predated the current run.** Reported scenario
  (`import/Assets-2026-04-21a/2026-04-21a-output-results.txt`,
  `validation_bundle_selab-var-202_20260421_002141`): the one-shot runner
  generated a clean bundle at `00:21:09` (with `since=run_started_at`
  correctly filtering pre-run files), but 30 seconds later the user
  clicked **Download Results** and received a second, contaminated bundle
  (`…_002141.zip`) that swept in files from 2026-03-24 / 2026-04-03
  referencing the wrong CNode. Manifest read `status=ok` for every
  category and an empty `stale` dict, so nothing about the bundle
  surfaced the drift.
- **Root cause:** the UI's Download button hit
  `/advanced-ops/bundle/collect` + `/advanced-ops/bundle/create`, both of
  which called `ResultBundler.collect_results(cluster_ip=…)` **without**
  `since=` or `operation_status=`. With the freshness filter absent, any
  file whose filename/header matched the current cluster was considered
  current, no matter how old the file was. The bundle that the one-shot
  path already produced (correctly filtered) was ignored by the Download
  button and rebuilt from scratch.
- **Fix — serve the one-shot bundle directly (Option A).** The Download
  button now returns the exact zip the runner produced; it no longer
  rebuilds from scratch, and therefore cannot pull in anything the
  runner's `since=run_started_at` filter already excluded.
  - `src/app.py` maintains a per-cluster `ONESHOT_LAST_BUNDLE` registry
    (`{cluster_ip → {bundle_path, run_started_at, operation_status}}`)
    populated on successful one-shot completion. A new read-only route
    `GET /advanced-ops/bundle/last?cluster_ip=…` returns the exact zip
    the runner produced.
  - The registry is **rehydrated on first request after restart** by
    scanning `output/bundles/*.zip` newest-first and picking each
    cluster's first zip whose `manifest.json` has a non-null
    `run_started_at` — the flag that identifies bundles produced by the
    one-shot path (which applies the freshness filter), explicitly
    skipping rebuild-path zips that lack the flag and may contain stale
    files.
  - `downloadResults()` in `frontend/templates/reporter.html` and
    `frontend/templates/advanced_ops.html` now asks
    `/advanced-ops/bundle/last` first and falls back to the legacy
    collect + create path only when no one-shot bundle is on record.
  - The fallback rebuild path now threads `since=` and
    `operation_status=` through to `ResultBundler.collect_results` via
    `_last_bundle_freshness_for(cluster_ip)`, so even the rebuild path
    honours the freshness filter when a prior one-shot ran.
- **Rollback — no pre-run archiving of historical files.** An earlier
  defence-in-depth cleaner (`src/output_cleaner.py` +
  `src/bundle_scan_spec.py`) moved every same-cluster, pre-`started_at`
  file out of the scan dirs into
  `<data_dir>/archive/<ISO>/…`. In the field this was destructive to
  operator workflow — historical `vnetmap_results_*.json`,
  `health_check_*.json`, `network_summary_*.json`, and
  `switch_configs_*.json` from prior runs were being swept out of
  `output/scripts/`, `output/health/`, etc. (observed in
  `import/Assets-2026-04-21b/Output-Results-2026-04-21b.txt`, ~200
  archive lines on a single run). Direct-serve of the runner's bundle
  (Option A) already prevents the contamination the cleaner was
  defending against, so the cleaner, its scan-spec module, and their
  test modules were removed. `output/scripts/` and peer dirs now keep
  every file in place; the runner simply produces a correctly filtered
  bundle and serves it unchanged.
- **Regression coverage.** New cases in `tests/test_app.py` lock in the
  `/advanced-ops/bundle/last` lookup, the cold-start rehydration that
  rejects rebuild-path zips, and the `since + operation_status`
  threading through `/advanced-ops/bundle/collect`. Full suite: 951
  unit tests passing.

### Fixed (As-Built Report now populates Port Mapping from vnetmap on one-shot)
- **The one-shot As-Built Report ignored vnetmap output and always
  re-collected port mapping over SSH.** Reported scenario
  (`import/Assets-2026-04-21b/Output-Results-2026-04-21b.txt`): the
  `VAST vnetmap` workflow completed successfully at `08:44:24`,
  writing `output/scripts/vnetmap_output_10.143.11.202_…_014423.txt`
  and the companion `vnetmap_results_…_014423.json`. Ten minutes later
  the report generation phase logged
  `Collecting port mapping data via SSH...` and went straight into
  `ExternalPortMapper` — never looking at the freshly-produced vnetmap
  file — so the PDF's Port Mapping section used the SSH MAC-correlation
  path instead of vnetmap's LLDP-derived topology.
- **Root cause:** `OneShotRunner._run_report` implemented only the
  `ExternalPortMapper` branch of the three-source priority
  (`vnetmap → SSH → static vnetmap_output.txt`) that
  `extract_port_mapping` expects. The `/generate` web path in
  `app.py._run()` had been wired to look for
  `vnetmap_output_{cluster_ip}_*.txt` since v1.5.0, but the one-shot
  reporter never got the same wiring, so any deployment that used the
  Advanced Ops flow quietly skipped the vnetmap source even when it
  had just been generated seconds earlier.
- **Fix.** `OneShotRunner` now owns `_find_latest_vnetmap_output`,
  which scans `output/scripts/` for `vnetmap_output_{cluster_ip}_*.txt`
  (strictly cluster-scoped to avoid cross-cluster contamination).
  `_run_report` calls it before any SSH work; when a match exists it
  parses the file with `VNetMapParser`, attaches the result as
  `raw_data["port_mapping_vnetmap"]`, and passes `use_vnetmap=True` to
  `data_extractor.extract_all_data`. `ExternalPortMapper` only runs
  when no vnetmap file is available or the parse yields no topology.
  The log now shows
  `Found vnetmap output: vnetmap_output_<cluster>_<ts>.txt — using as
  port mapping source` followed by
  `Vnetmap data parsed: <N> connections`, matching the `/generate`
  path line-for-line.
- **Regression coverage.** New `TestVnetmapPortMappingInReport` in
  `tests/test_oneshot_runner.py` covers: `_find_latest_vnetmap_output`
  newest-wins selection, missing scripts dir, cross-cluster isolation,
  empty cluster IP, the success path (use_vnetmap=True,
  use_external_port_mapping=False, ExternalPortMapper not called), and
  the SSH fallback when no vnetmap file exists.

### Fixed (vnetmap `--multiple-passwords` no longer crashes with `EOFError` on non-interactive SSH)
- **vnetmap Step 4 crashed inside `getpass.getpass()` the moment the
  per-switch password fast path engaged.** Reported scenario
  (`output-results-d.txt`, 06:32:52): pre-validation probed all three
  switches successfully (`Switch SSH connected on 3/3 switch(es)`) and
  the workflow correctly logged `"Using per-switch passwords from
  pre-validation (3 switch(es))"`, but vnetmap then printed
  `GetPassWarning: Can not control echo on the terminal`, followed by
  `Enter password for switch 10.143.11.156:` and an immediate
  `EOFError` from `fallback_getpass → _raw_input → readline()`.
- **Root cause:** the fast path piped the password list on stdin
  (`printf '%s\n' pw1 pw2 pw3 | python3 vnetmap.py --multiple-passwords`)
  and relied on `getpass.getpass()` falling back to `sys.stdin.readline()`
  when `/dev/tty` isn't available. That works only if nothing else
  consumes stdin first. `vnetmap.py 1.0.6` calls
  `check_ssh_keys()` → `ssh_exe()` → `subprocess.check_output("ssh …",
  shell=True)` **before** any `getpass` prompt (see lines 404-408,
  1142-1151 of vnetmap.py). `subprocess.check_output` with default
  `stdin=None` inherits the parent's stdin, and OpenSSH's default
  behavior is to forward stdin to the remote. The ssh probe therefore
  drained every byte we'd queued up with `printf`, and vnetmap's first
  `getpass` call hit EOF on the very first switch.
- **Fix — stop using stdin; read the password map from a file on the
  remote instead.** `VnetmapWorkflow._build_multiple_passwords_cmd`
  now builds a multi-line bash command that:
  1. `mktemp`s two files under `/tmp/vast_scripts/` with `umask 077`
     (`.vnetmap_pw.XXXXXX.json` and `.vnetmap_wrap.XXXXXX.py`).
  2. Writes, via single-quoted heredocs (`<<'__VNM_PW_EOF__'` and
     `<<'__VNM_WRAP_EOF__'`), the per-switch password map as compact
     JSON and a small Python wrapper that monkey-patches
     `getpass.getpass` to consult that map based on the IPv4 found in
     the prompt string, then `runpy.run_path`s the real `vnetmap.py`
     as `__main__`.
  3. Installs `trap 'rm -f "$_VNM_PWF" "$_VNM_WRAP"' EXIT HUP INT
     QUIT TERM` before any content is written, so the JSON and wrapper
     temp files are deleted on success, failure, or signal.
  4. Invokes `VAST_SWITCH_PW_FILE="$_VNM_PWF"
     VAST_VNETMAP_PATH="/tmp/vast_scripts/vnetmap.py"
     python3 "$_VNM_WRAP" -s $MLX_IPS -i $cnodes_ips,$dnodes_ips
     -u cumulus --multiple-passwords`. The wrapper reads the JSON,
     immediately `os.remove`s the file, and returns the mapped
     password from its patched `getpass` — stdin is never touched,
     so nothing vnetmap's ssh probe does can break it.
- **Operator-log hygiene:** `_build_multiple_passwords_cmd` now
  returns a tuple `(full_cmd, display_cmd)`. `display_cmd` is a
  one-line summary (`… && VAST_SWITCH_PW_FILE=<redacted: N switch
  credential(s)> … python3 <multi-password wrapper> …
  --multiple-passwords`) that replaces the heredoc bodies and the
  password payload for the UI echo, while the shell still runs the
  real command. The old `_redact_multi_cmd_passwords` helper is
  removed — the display form is produced alongside the real form, so
  there is no longer a redactor that could desynchronize from the
  builder.
- **Regression coverage** (in
  `tests/test_workflows.py::TestVnetmapPerSwitchPasswords`):
  - `test_build_multiple_passwords_cmd_drops_single_password_flag`
    — `-p '…'` is stripped, `--multiple-passwords` is appended, the
    old `printf '%s'` stdin prefix is gone, and
    `python3 "$_VNM_WRAP"` is the invocation.
  - `test_build_multiple_passwords_cmd_encodes_full_map_as_json`
    pins the compact JSON form, the two heredoc delimiters, and both
    env vars (`VAST_SWITCH_PW_FILE`, `VAST_VNETMAP_PATH`).
  - `test_build_multiple_passwords_cmd_installs_trap_and_chmod`
    pins `umask 077`, both `mktemp` templates, and the exact `trap`
    registered for `EXIT HUP INT QUIT TERM`, and confirms literal
    single quotes inside passwords survive the JSON round-trip.
  - `test_build_multiple_passwords_cmd_returns_redacted_display`
    asserts the display form contains
    `<redacted: 2 switch credential(s)>` and `<multi-password
    wrapper>` and no cleartext passwords.
  - `test_run_vnetmap_uses_per_switch_map_on_happy_path` confirms
    the executed command carries the JSON map in `switch_ips` order,
    uses the wrapper, and never emits `printf '%s`.
  - `test_run_vnetmap_skips_fast_path_when_map_incomplete` confirms
    a partial map falls through to the legacy single-`-p` path
    (wrapper scaffolding absent).
  - `test_run_vnetmap_falls_back_to_candidate_sweep_on_fast_path_auth_failure`
    confirms an auth-failure result on the wrapper run still rolls
    into the legacy candidate sweep and the third candidate wins.

### Fixed (per-switch password map now survives Pre-Validation → Execute handoff)
- **Execution runner discarded the per-switch password map that
  Pre-Validation had just discovered.** Reported scenario
  (`import/Assets-2026-0420c/output-results-Output-Results-2026-0420d.txt`):
  Pre-Validation ran the full Switch SSH probe and authenticated all three
  switches (`10.143.11.156 → Vastdata1!`, `.154 → VastData1!`,
  `.153 → VastData1!`). The operator then clicked Run, and vnetmap Step 4
  immediately logged `"Using primary switch password (candidate 1/3)"` —
  the legacy candidate-sweep — and exhausted all three passwords, none of
  which could satisfy every switch on its own.
- **Root cause:** `/advanced-ops/oneshot/validate` and
  `/advanced-ops/oneshot/start` each construct a **new** `OneShotRunner`.
  Pre-Validation populated `runner_A._switch_password_by_ip`; Execution
  threw `runner_A` away and started `runner_B` with the map at `{}`. The
  vnetmap fast path's guard
  (`all(ip in switch_password_by_ip for ip in switch_ips)`) therefore
  never held on the execution runner, and the workflow fell back to the
  single-`-p` candidate loop.
- **Fix — handoff + runtime safety net:**
  - `OneShotRunner.seed_switch_credentials(switch_user_by_ip,
    switch_password_by_ip)` accepts a pre-computed map and merges it into
    `_switch_user_by_ip` / `_switch_password_by_ip`. Empty IPs/passwords
    are dropped so `VnetmapWorkflow` never shell-quotes a blank token
    into the `--multiple-passwords` stdin stream.
  - `OneShotRunner.switch_password_by_ip` / `switch_user_by_ip` are now
    read-only properties exposing copies of the maps, so callers
    (notably `app.py`) can hand them off without reaching into
    underscored internals.
  - `/advanced-ops/oneshot/start` in `src/app.py` reads those properties
    off `app.config["ONESHOT_RUNNER"]` (the prior Pre-Validation runner)
    and calls `new_runner.seed_switch_credentials(...)` before assigning
    the new runner. Seeding is wrapped in try/except so a malformed
    prior runner never blocks a Run.
  - `OneShotRunner.run_all()` gained a runtime fallback: if a switch-op
    is selected (`SSH_SWITCH_OPS & selected_ops`), the map is empty, and
    the credentials needed to probe are present, it silently invokes
    `_validate_switch_ssh` before `_run_operations`. This covers the
    "operator clicked Run without Pre-Validating" edge case and any
    future endpoint that calls `run_all()` directly.
- **Regression coverage:**
  - `tests/test_oneshot_runner.py::TestPrevalidationSwitchSshFallback::
    test_seed_switch_credentials_populates_map_and_workflow_creds`
    verifies seeding flows through `_get_workflow_credentials` so the
    workflow sees `switch_password_by_ip` + `switch_user_by_ip`.
  - `...::test_seed_switch_credentials_ignores_empty_entries` pins the
    "no blank tokens in --multiple-passwords" invariant.
  - `...::test_run_all_reprobes_switches_when_map_empty` confirms the
    runtime fallback probes when the map is empty.
  - `...::test_run_all_skips_reprobe_when_map_already_seeded` confirms
    the seed short-circuits the re-probe (no duplicate SSH round-trips
    on the happy path).
  - `tests/test_app.py::TestOneShotStartHandoff::
    test_start_seeds_new_runner_from_prior_runner` verifies the Flask
    endpoint reads the prior runner's properties and calls
    `seed_switch_credentials` with the exact discovered maps.
  - `...::test_start_skips_seed_when_no_prior_runner` confirms the
    first-launch flow does not call the setter, so the runtime fallback
    in `run_all` remains authoritative in that path.

### Fixed (Switch SSH pre-validation now runs when only vnetmap is selected)
- **Selecting vnetmap without `switch_config` skipped the Switch SSH probe,
  which silently disabled the per-switch password fast path.** Reported
  scenario (`import/Assets-2026-0420c/output-results-d.txt`): operator
  selected only `vnetmap` + `support_tool`, pre-validation ran five checks
  (Credentials, Cluster API, Node SSH, Internet, Tool Freshness) with **no
  Switch SSH line**, then vnetmap Step 4 logged
  `"Using primary switch password (candidate 1/3)"` — the legacy
  candidate-sweep path — and failed on the first mixed-default switch it
  reached.
- **Root cause:** `SSH_SWITCH_OPS` in `src/oneshot_runner.py` contained only
  `{"switch_config"}`, so `needs_switch_ssh` was `False` whenever vnetmap
  was the only switch-touching op selected. `_validate_switch_ssh` never
  ran, `_switch_password_by_ip` stayed empty, and the vnetmap fast path
  guard (`all(ip in switch_password_by_ip for ip in switch_ips)`) never
  held.
- **Fix:** `SSH_SWITCH_OPS` now includes `vnetmap`. With this change,
  selecting vnetmap alone (or vnetmap + any non-switch op) runs the full
  Switch SSH probe during Pre-Validation, records the winning
  `(user, password)` per switch, and feeds the map to `VnetmapWorkflow`,
  so Step 4 takes the `printf ... | python3 vnetmap.py
  --multiple-passwords` fast path that was introduced earlier in 1.5.2.
- **Regression coverage:**
  `tests/test_oneshot_runner.py::TestPrevalidationInclusion::
  test_prevalidation_runs_switch_ssh_when_only_vnetmap_selected` asserts
  that `_validate_switch_ssh` is called when `selected_ops=["vnetmap"]`,
  `include_health=False`, `include_report=False` — locking in the
  previously-missing Pre-Validation check.

### Fixed (vnetmap runs per-switch-password on mixed-default clusters)
- **vnetmap Step 4 no longer exhausts all candidate passwords on clusters
  whose switches carry different defaults.** Reported scenario: three
  switches — `10.143.11.156` on `VastData1!`, `.154` and `.153` on
  `Vastdata1!` — passed Pre-Validation (each switch authenticated on its
  correct candidate) but `vnetmap.py` still failed because it was being
  invoked with a **single** `-p '<one password>'` flag that had to work
  for every switch simultaneously. Every candidate run failed the first
  switch it reached with the wrong casing, leaving the run at
  "Authentication failed on all N candidate switch password(s)" even
  though the per-switch credentials were known.
- **Root cause:** pre-validation discovered the winning password for each
  switch but discarded the information. The workflow then brute-forced
  one password at a time against all switches — structurally incompatible
  with mixed-default clusters.
- **Fix — per-switch credential propagation:**
  - `OneShotRunner._validate_switch_ssh` now records the winning
    `(user, password)` pair for every switch that authenticates and
    exposes them via `_get_workflow_credentials` as
    `switch_password_by_ip` / `switch_user_by_ip`.
  - `VnetmapWorkflow._step_generate_export_commands` captures that map.
  - `VnetmapWorkflow._step_run_vnetmap` takes a fast path when the map
    has an entry for every listed switch: it rewrites the vnetmap
    command to drop `-p` and add `--multiple-passwords` (vnetmap.py
    1.0.6's native flag, which calls `getpass.getpass()` per switch),
    and prefixes the command with
    `printf '%s\n' 'pw1' 'pw2' 'pw3' |` so the correct password for
    each switch is delivered on stdin in the same order as `-s`
    (getpass falls back to stdin when no TTY is available, which is
    the case for SSH `exec_command`). Single quotes inside passwords
    are shell-escaped. The log echo redacts the printf tokens as
    `'***'` so credentials don't leak into the UI stream.
  - If the fast-path run still reports an auth-style failure the
    workflow falls back to the legacy single-password candidate sweep
    so operators don't lose the previous recovery behaviour.
- **Regression coverage:**
  - `tests/test_workflows.py::TestVnetmapPerSwitchPasswords` locks in
    single-password flag removal, argument ordering matches switch-IP
    order, single-quote escaping, password redaction in the echo, the
    happy-path one-call execution, the fallback to the legacy sweep on
    an incomplete map, and the fallback on fast-path auth failure.
  - `tests/test_oneshot_runner.py::TestPrevalidationSwitchSshFallback`
    gains `test_records_per_switch_winning_password_for_workflows` and
    `test_does_not_record_passwords_for_unreachable_switches` to assert
    the map is populated correctly and never leaks credentials for
    switches that did not authenticate.

### Fixed (Pre-validation now honours the Autofill toggle)
- **Pre-validation Switch SSH probe was collapsing to a 2-combo list** (just
  `cumulus/<entered password>` + `admin/admin`) because
  `/advanced-ops/oneshot/validate` constructed its `OneShotRunner` without
  forwarding `config_path` or `use_default_creds`. That meant the Autofill
  toggle was ignored during pre-validation — clusters that needed the
  `VastData1!` case variant or the `Cumu1usLinux!` factory default were
  flagged as "auth failed on N/N" even though runtime workflows (which go
  through `/advanced-ops/oneshot/start` and did forward the kwargs) would
  have authenticated successfully with the full candidate list.
- **Fix:** `/advanced-ops/oneshot/validate` now reads `use_default_creds`
  from the request payload and passes both it and
  `app.config["CONFIG_PATH"]` into `OneShotRunner`, matching the `/start`
  path. The pre-validation probe now iterates the complete configured
  `default_switch_passwords` list plus `admin/admin`, so the Switch SSH
  check matches what the actual workflows will try at run time.
- **Regression coverage:** `tests/test_app.py::TestOneShotValidateAutofillForwarding`
  asserts both kwargs are forwarded when the toggle is on, and that
  `use_default_creds` defaults to `False` when absent.

### Changed (Switch credential fallback ordering simplified)
- **Autofill switch-SSH credential list now matches operator intent exactly:**
  for a Cumulus primary user the probe tries `cumulus/<entered password>` →
  `cumulus/Vastdata1!` → `cumulus/VastData1!` → `cumulus/Cumu1usLinux!` →
  `admin/admin` and stops there. The previous build also tried
  `admin/Vastdata1!` and `admin/VastData1!` (an
  Onyx-with-VMS-synced-password defensive combo) which could trip
  account-lockout policies on Onyx switches that reject bad admin attempts;
  those permutations have been removed. Operators who need the
  Onyx-with-custom-admin-password path should enter the admin credentials
  explicitly in Connection Settings.
- **`advanced_operations.default_switch_passwords`** default extended to
  `["Vastdata1!", "VastData1!", "Cumu1usLinux!"]` so Autofill exercises both
  the VMS-synced casings and the stock Cumulus Linux factory default
  (`Cumu1usLinux!`).
- **`utils.ssh_adapter.build_switch_credential_combos`** simplified: drops
  the `admin × <each candidate>` loop; keeps the `cumulus × <each candidate>`
  fallback only when the operator set a non-default primary user.
- **UI tooltips refreshed:** the Switch Password hint in Connection Settings
  and the Autofill tooltip on Test Suite now list the final fallback chain
  (Vastdata1! / VastData1! / Cumu1usLinux! / admin-admin).

### Fixed (Autofill — two-password switch SSH retry)
- **Mixed-default switch passwords no longer break the run:** clusters where VMS has synced one Cumulus pair to `Vastdata1!` while a spare Onyx leaf still carries the original `VastData1!` (or vice versa) previously caused `vnetmap` Step 4, `Switch Extraction` Step 1, and `External Port Mapper` OS detection to fail with "authentication failed with both credential sets" after a single pass. The Autofill path now iterates an ordered candidate list (primary entered/`default_switch_passwords[0]` first, then fallbacks) per switch and records the winning password on the switch entry so Step 2 reuses it.
- **`ExternalPortMapper._detect_switch_os`** accepts a `switch_password_candidates` list and tries each candidate against every `(user, os_type)` pairing before giving up; connectivity errors still short-circuit immediately so timeouts are not multiplied.
- **`SwitchConfigWorkflow._step_discover_switches`** retries the std-SSH + interactive-SSH probe pair for each password candidate on auth failure only, and `_step_extract_config` reuses the per-switch winning password instead of the first credential.
- **`VnetmapWorkflow._step_run_vnetmap`** re-executes `vnetmap.py` with the next password candidate when the previous attempt output matches known auth/connect failure patterns (`authentication failed`, `permission denied`, `failed to connect to switch`, `unable to determine suitable switch api`, `login incorrect`). Password substitution in the generated command is shell-safe (single quotes inside the password are escaped).

### Fixed (Pre-validation switch SSH check honours the Autofill fallback)
- **"Switch SSH: connected but command failed (rc=5)" warning on mixed-default clusters no longer fires:** `OneShotRunner._validate_switch_ssh` now probes *every* switch returned by `switches/` (not just the first one) and tries *every* entry in `switch_password_candidates` per switch before reporting a result. On auth-failure it also retries over the MLNX-OS interactive SSH path so Onyx leaves authenticate without looking like a failure. The check passes when all switches are reachable + authenticated (even if an Onyx switch returns a non-zero rc for `hostname` outside the MLNX-OS shell) and warns with a per-IP breakdown only when a switch is genuinely unreachable or rejects every candidate password.
- **Fallback usage is surfaced in the check message:** when at least one switch authenticated via a non-primary candidate, the Pre-Validation message appends "one or more switches authenticated via fallback credentials" so the operator knows why the run took an extra attempt.
- **Stderr is now classified into auth vs. connectivity failures:** connectivity errors (`timed out`, `connection refused`, `no route to host`, `host unreachable`, `network is unreachable`, `name or service not known`) short-circuit the candidate loop for that switch so timeouts are not multiplied by the number of password candidates.

### Fixed (Shared switch-credential ordering across pre-validation, Switch Extraction, and Port Mapping)
- **New `utils.ssh_adapter.build_switch_credential_combos` helper** consolidates the credential-ordering policy that previously lived ad-hoc in `ExternalPortMapper._detect_switch_os`.  Order: primary `switch_user` × each password candidate first (Cumulus path), then `admin/admin` (Onyx/MLNX-OS factory default), then `admin` × each password candidate (Onyx with a VMS-synced password), and finally `cumulus` × each password candidate when the operator-entered primary user was neither.  De-duplicated; never issues network I/O.
- **`SwitchConfigWorkflow._step_discover_switches`** now iterates this combo list instead of just `(switch_user, password_candidate)` pairs.  Previously a Cumulus-only credential pass meant Onyx switches that required `admin` as the SSH user would fail Step 1 even when Port Mapping handled them correctly; the two paths now agree.  The winning `user` + `password` pair is stored on each `connected_switches` entry so `_step_extract_config` reuses the exact credential that authenticated.
- **`OneShotRunner._validate_switch_ssh`** now calls the shared helper, so pre-validation tries the same combo order as the workflow.  Messaging was updated from "fallback password" to "fallback credentials" to reflect that both user and password can differ between the primary combo and the winning combo.

### Fixed (Pre-validation honours ProxyJump in Tech Port mode)
- **Reported scenario:** a Cumulus Linux 5.11.1 switch reachable from a cluster node via ProxyJump but *not* directly from the Reporter's LAN was flagged as `auth failed on 1/3` in Pre-Validation even though the operator had just run `ssh cumulus@<ip>` successfully from a jump host with the same password.  The other two switches happened to be directly reachable and therefore passed.
- **Root cause:** `OneShotRunner._validate_switch_ssh` was calling `run_ssh_command` without the `jump_host` / `jump_user` / `jump_password` kwargs that `SwitchConfigWorkflow._jump_kwargs()` already produces at runtime.  In Tech Port mode the Reporter has no direct L3 path to the cluster management network, so switches are ordinarily reached via a CNode; direct-SSH attempts either time out or hit an unrelated login banner and are misreported as auth failures.
- **Fix:** added `OneShotRunner._switch_jump_kwargs()` that mirrors the workflow's jump-host wiring and threads the kwargs through `_probe_switch_candidates` into both `run_ssh_command` and `run_interactive_ssh`.  Pre-validation now reaches switches over the same ProxyJump path the actual Switch Extraction, vnetmap, and External Port Mapping workflows use, eliminating false auth-failure warnings caused by routing differences.

### Fixed (Download Results reuses the one-shot bundle)
- **"Download Bundle" no longer re-collects and silently re-includes stale files:** the UI now reads `state.bundle_path` from `/advanced-ops/oneshot/status` and downloads that exact archive (the one built with `since=run_started_at` freshness filters applied). The previous code path called `/advanced-ops/bundle/collect` and `/advanced-ops/bundle/create` without `since` / `operation_status`, which re-pulled pre-run artefacts marked as `ok`. The legacy collect/create path is kept as a fallback for sessions where no one-shot bundle exists.
- **`lastOneShotBundlePath` is cleared at the start of each new one-shot run** so a previous bundle cannot be served after a fresh (possibly incomplete) run.

### Added (Configurable switch password list)
- **`advanced_operations.default_switch_passwords`** (ordered list) added to `config/config.yaml.template` and `config/config.yaml`. Defaults to `["Vastdata1!", "VastData1!"]` to cover the two common factory password casings. `OneShotRunner` loads this list when Autofill is enabled, deduplicates, promotes the operator-entered password (if any) to the head, and propagates the resulting `switch_password_candidates` list to every workflow via `_get_workflow_credentials`.
- **Autofill tooltip on the Advanced Operations page** now documents the primary/fallback behaviour so operators understand why two password variants are accepted.

### Tests
- `tests/test_external_port_mapper.py::TestSwitchPasswordCandidates` — candidate list default/explicit ordering, dedup, and fallback-to-second-password on auth failure.
- `tests/test_workflows.py::TestVnetmapPasswordFallback` — `_rebuild_vnetmap_cmd` substitution (including single-quote escaping), IB no-op behaviour, auth-failure detection, two-attempt retry success, and no-retry-on-connectivity.
- `tests/test_workflows.py::TestSwitchConfigPasswordFallback` — primary-password-first happy path, fallback-on-auth-failure persisted on the switch entry, and early break on connectivity errors.
- `tests/test_workflows.py::TestSwitchConfigWorkflow::test_is_auth_failure_detects_auth_errors` — classifier covers `authentication failed`, `permission denied`, `login incorrect`, `access denied`.
- `tests/test_oneshot_runner.py::TestSwitchPasswordCandidates` — manual mode yields a single-entry list; autofill loads config and honours precedence; built-in fallback kicks in when the config is missing; explicit `switch_password_candidates` always wins; list is propagated via `_get_workflow_credentials`.
- `tests/test_oneshot_runner.py::TestPrevalidationSwitchSshFallback` — covers the expanded Pre-Validation probe: single-password all-pass, mixed-defaults pass with fallback note, Onyx-reachable-but-command-rejected pass, one-switch-unreachable warn, all-passwords-auth-failed warn, Tech-Port-mode ProxyJump wiring, and no-jump-host in direct mode.
- `tests/test_ssh_adapter.py::TestBuildSwitchCredentialCombos` — locks in the shared `(user, password)` ordering: primary first, `admin/admin` factory default included, `admin` × candidates for VMS-synced Onyx, `cumulus` × candidates when the operator's primary user is neither `admin` nor `cumulus`, and dedup.

## [1.5.1] - 2026-03-21

### Fixed (One-Shot Bundle Integrity)
- **vperfsanity results written outside the PyInstaller bundle:** `VperfsanityWorkflow._step_collect_results` now saves results via `ScriptRunner.get_local_dir()` (which resolves to `get_data_dir()/output/scripts`) instead of `Path(__file__).parent.parent.parent`. On frozen macOS/Windows builds the previous path resolved to a read-only location inside the `.app` bundle, so `ResultBundler` could not see the file and a `vperfsanity_NOT_FOUND.txt` placeholder shipped in place of real data.
- **Support Tools "Permission denied" on /vast/data/ copy:** `SupportToolWorkflow._step_set_permissions` now uses `sudo cp`, `sudo chown`, and `sudo chmod` when staging `vast_support_tools.py` into `/vast/data/` on both the CNode and the VMS. Clusters where `/vast/data/` is root-owned previously failed Step 2 with `cp: Permission denied`, producing `support_tools_NOT_FOUND.txt`. The error path also surfaces a hint when sudo itself was rejected (password required or missing TTY).

### Fixed (Bundler — no more silently stale data)
- **`ResultBundler.collect_results` learned a `since=<run-start>` filter:** `_pick_latest` now skips files whose mtime predates the current run. Pre-run files that would previously have been bundled silently are instead recorded in a new `_stale_files` map and surfaced in the manifest.
- **Per-category status in `manifest.json`:** manifest now includes a `categories` map (`ok` / `stale` / `failed` / `skipped` / `missing`), a `stale` map of excluded pre-run file names, the `operation_status` reported by the runner, and `run_started_at`. Manifest `version` bumped to `1.1`.
- **Placeholders now describe *why* a category is missing:** `<cat>_STALE.txt`, `<cat>_FAILED.txt`, and `<cat>_SKIPPED.txt` replace the blanket `<cat>_NOT_FOUND.txt` when the bundler knows the real cause. Stale files themselves are never added to the bundle.
- **`SUMMARY.md` surfaces the same per-category status** so a human reading the bundle can immediately see which operations succeeded, which produced no fresh data, and which were skipped.

### Fixed (Advanced Operations UI)
- **Test Suite completion banner no longer claims success when ops failed:** the `/advanced-ops/oneshot/status` response now includes `operation_results` (per category) and `selected_operations`. The page renders a completion summary card with per-op `SUCCESS` / `FAILED` / `SKIPPED` badges and tints the banner amber when one or more selected operations did not collect results.

### Changed (One-Shot Runner)
- **Operation outcomes are tracked in `OneShotState.operation_results`** and threaded to the bundler as `operation_status`. Health checks and the As-Built report phases also report their outcomes so the bundler can distinguish "not selected" from "ran and failed".
- **Bundling now passes `since=started_at`** to the bundler so only artifacts produced in the current run are considered fresh.

### Tests
- `tests/test_workflows.py::TestVperfsanityStepExecution::test_step5_collect_results_saves_under_script_runner_local_dir` — regression test ensuring vperfsanity Step 5 writes to `ScriptRunner.get_local_dir()`.
- `tests/test_result_bundler.py::TestStalenessFilter` — verifies pre-run files are excluded when `since` is set and legacy behaviour is preserved when it is omitted.
- `tests/test_result_bundler.py::TestCategoryStatus` — operation_status drives `failed` / `skipped` / `missing` manifest entries.
- `tests/test_result_bundler.py::TestManifestAndPlaceholders` — manifest advertises `categories`, `stale`, and `run_started_at`; `_STALE.txt` / `_FAILED.txt` placeholders replace `_NOT_FOUND.txt` when applicable; stale files never enter the archive.
- `tests/test_oneshot_runner.py::test_bundle_passes_cluster_ip` — updated for the new `since` / `operation_status` kwargs.

### Fixed (CI — Security Audit workflow)
- **`security` label auto-created:** `.github/workflows/security.yml` now creates the `security` issue label on demand. Previously every report job failed with `could not add label: 'security' not found` because the label had never been defined in this repo.
- **Vulnerability detection uses structured JSON, not grep:** the workflow now parses `pip-audit` JSON for dependencies with non-empty `vulns` and `bandit` JSON for `MEDIUM`/`HIGH` `issue_severity`, instead of grepping human-readable strings that appeared even on clean runs. This eliminates the false positives that were causing a spurious tracking issue to be opened on every scheduled run.
- **Issue de-duplication:** when a `security`-labelled issue is already open, the workflow now comments on it instead of creating a new one.
- **Run summary:** each scan run emits a `$GITHUB_STEP_SUMMARY` with exact pip-audit and bandit counts for quick triage.

### Changed (Bandit — intentional findings annotated)
- **32 Medium/High bandit findings across `src/` are now narrowly suppressed with `# nosec BXXX`** and justifying comments, because each one is an intentional consequence of the reporter's architecture (connecting to a freshly-deployed VAST cluster over the network):
  - **B108 × 11** (`hardcoded_tmp_directory`) — all paths (`/tmp/vast_scripts`, `/tmp/vast_log_bundle`, `/tmp/vast_support_output`, `/tmp/{session_name}*`) live on the **remote VAST CNode** and are created over SSH; the two `session_manager.py` sites additionally embed a `uuid4().hex[:8]` suffix, so they are neither local nor predictable.
  - **B501 × 9** (`request_with_no_cert_validation`) — VAST VMS ships with self-signed TLS certs and `api.verify_ssl: false` is the documented default (see `.cursor/rules/config-security-11.mdc`).
  - **B507 × 11** (`ssh_no_host_key_verification`) — the reporter targets CNodes and management switches whose host keys are not yet in `known_hosts` at the time of first contact; `paramiko.AutoAddPolicy()` is required for the post-install discovery workflows this tool exists to support.
  - **B601 × 1** (`paramiko_calls`) — `ssh_adapter.run_ssh_command`'s `command` argument is always assembled internally from fixed templates plus validated inputs (credentials from interactive prompts, IPs from discovery), never from untrusted external sources.
- **Result:** bandit (`-ll`) now reports **0 Medium/High findings**, and the `security.yml` detection job no longer has reason to open a tracking issue on clean runs.

### Added (GitHub Pages and Marketing)
- **Product Overview page:** Interactive HTML one-pager at `rstamps01.github.io/ps-deploy-report/` showcasing UI screenshots, report previews, key benefits, and quick start steps
- **Visual Quick Start Guide:** Step-by-step macOS and Windows installation walkthroughs with screenshots, path selector for New Install vs. Upgrade, and Gatekeeper/SmartScreen guidance
- **GitHub Pages workflow:** `.github/workflows/pages.yml` auto-deploys `docs/marketing/` on pushes to `main`
- **README visual banner:** Dashboard preview image and links to Product Overview and Quick Start Guide at the top of README.md

### Added (Vnetmap Integration)
- **Run Vnetmap checkbox** on Reporter page: pre-select to run `vnetmap.py` before report generation for fresh port mapping and network diagram data; requires node SSH credentials
- **`/api/vnetmap-status` endpoint:** Detects existing vnetmap output for a cluster and compares hardware fingerprints between the two most recent reports to recommend re-running vnetmap when CBox/DBox/EBox/switch counts change
- **Hardware change detection:** `_extract_hardware_fingerprint()` and `_compare_hardware_fingerprints()` compare device counts and models across report JSON files to surface topology drift
- **Three-source port mapping priority** in data extractor: (1) vnetmap output (pre-parsed in app.py) → (2) external SSH collection → (3) static file fallback; each path feeds into `EnhancedPortMapper` for consistent output
- **LLDP neighbor parsing:** VNetMap parser now extracts LLDP neighbor data for switch-to-switch (IPL/MLAG) connections; data extractor formats IPL from LLDP neighbors or infers IPL from switch pairs when LLDP is absent
- **Advanced Config toggle:** "Run Vnetmap" default selection added under Reporter Defaults in Advanced Configuration page

### Added (SVG Diagram Support)
- **New dependencies:** `svgwrite>=1.4.0` and `cairosvg>=2.7.0` added to `requirements.txt` for rack-centric SVG network topology generation
- **Landscape page template:** Report builder supports landscape-oriented pages for wide diagrams via `_create_landscape_template()` — registered alongside the portrait "VastPage" template

### Changed (Port Mapping and Network Diagrams)
- **Enhanced port mapper node classification:** Refactored from simple interface-prefix heuristic to multi-signal classification using hostname patterns, `node_type` field, and interface prefix for reliable CNode/DNode distinction
- **Network diagram DNode interfaces:** Additional interface patterns recognized as primary drawable interfaces: `ens3`, `ens14`, `enp65s0`, `enp94s0`, `enp3s0` (alongside existing `f0`/`f1`)
- **Brand compliance tables:** `create_vast_table()` now accepts optional `col_widths` (proportional weight list) and `compact` (smaller font/tighter padding) parameters for dense data tables

### Changed (Reporter UI — Step Workflow)
- **Simplified to 3 numbered step badges:** Step 1 (Enter IP and Save), Step 2 (Discovery), Step 3 (Run) — replacing the previous 4-step layout with inline numbered badge circles on labels and buttons
- **Vnetmap status badge** displayed next to the Run Vnetmap checkbox showing freshness and hardware-change recommendations
- **Step badge CSS:** `.step-badge-filled` (accent background) for instruction labels; `.step-badge-outline` (white background, accent border) for action buttons

### Fixed (Rack Diagram — U-Position Calculation)
- **Bottom-based U positioning:** Device placement changed from top-based (`u_position - u_height + 1`) to bottom-based (`u_position`) calculation — `u_position` now represents the base (bottom) U where a device is mounted and extends upward; CBox/DBox/EBox top/bottom calculations updated to match

### Fixed (Health Check — License Detection)
- **Multi-source license resolution:** New `_resolve_license()` method checks `license`, `license_state`, `license_type`, `license_status`, and `is_licensed` fields in cluster data, then falls back to the `licenses/` API endpoint — replaces the previous single-field lookup that returned null on many clusters
- **License message enriched:** Pass status now includes the license value (e.g., "License is present and active (Licensed)")

### Fixed (Health Check — Call Home)
- **`callhomeconfigs/` endpoint:** Call Home check now queries the dedicated `callhomeconfigs/` endpoint (VAST v5.x+) for `cloud_registered`, `cloud_enabled`, `log_enabled`, `bundle_enabled`, and `customer` fields, with fallback to cluster boolean fields for older deployments
- **Enriched status message:** Pass result now lists active features (e.g., "cloud registered, logging active, bundles active")
- **Null-safe handling:** When Call Home status is not exposed via API, returns pass with guidance to verify in VMS GUI instead of a false failure

### Fixed (Script Runner — Stderr Classification)
- **`_classify_stderr_line()` method:** Intelligently classifies stderr output — SSH host-key warnings and known-hosts messages as `info`, ping diagnostics as `warn`, Python tracebacks as `error`, and generic stderr as `warn` (previously all stderr was emitted as `warn` or `error` based solely on exit code)
- **`_emit()` deduplication:** Output callback and Python logger are now mutually exclusive — when an output callback is registered, lines go only to the callback; when no callback is set, lines go to the Python logger. Prevents duplicate log entries

### Fixed (Discovery — Tech Port Probe)
- **Port-aware connectivity check:** `/api/discover` pre-flight probe now uses port 22 for Tech Port connections and port 443 for VMS VIP connections (previously always probed 443, causing false "unreachable" errors for Tech Port IPs)
- **Contextual error message:** Failure message now includes connection type label ("SSH (Tech Port)" or "HTTPS")

### Fixed (Deployment Packaging — SVG Diagram Dependencies)
- **Multi-backend SVG-to-PNG fallback:** `network_diagram_v2.py` now tries three backends in priority order: (1) cairosvg (best quality, requires system libcairo), (2) PyMuPDF/fitz (pure-Python, works on all platforms), (3) SVG file fallback with compact diagram mode — eliminates the hard failure on Windows and clean macOS installs where Cairo is absent
- **PyInstaller spec overhaul:** Added 15 hidden imports for the SVG diagram chain (`svgwrite`, `cairosvg`, `cairocffi`, `cffi`, `_cffi_backend`, `cssselect2`, `defusedxml`, `tinycss2`, `webencodings`, `fitz`, `pymupdf`, `scp`, `click`, `markdown`, `reportlab.graphics.renderPM`); removed `cairocffi`/`pycairo` from excludes list that was blocking Cairo bindings; added `reportlab.graphics.renderPDF`, `reportlab.lib.utils`, `reportlab.pdfbase.pdfmetrics` for lazy-imported report modules
- **macOS libcairo bundling:** PyInstaller spec now collects `libcairo.2.dylib` from Homebrew paths (`/opt/homebrew/lib` or `/usr/local/lib`) into the app bundle so cairosvg works in the packaged .dmg without requiring a system Homebrew install
- **macOS build script (`build-mac.sh`):** Added pre-build step to install Cairo via Homebrew (`brew install cairo`) if not already present
- **CI workflow updates:** Both `build-release.yml` (release builds) and `ci.yml` (build-smoke tests) now install Cairo on macOS runners before building, ensuring cairosvg functions in CI-produced artifacts

### Fixed (Rack Diagram — N-Switch Placement)
- **Generalized switch placement:** Rack diagram switch placement strategies (center gap, above, below) now accept any number of switches instead of being hardcoded for exactly 2 — resolves the `Switch placement logic currently only supports 2 switches, got 3` warning for clusters with 3+ switches per rack

### Fixed (macOS — cairosvg Library Path)
- **DYLD_FALLBACK_LIBRARY_PATH:** Both `app.py` and `main.py` now prepend `/opt/homebrew/lib` to the dynamic library fallback path on macOS, enabling cairosvg to find Homebrew-installed libcairo without manual environment setup

### Fixed (Report — Deduplication Field)
- **Removed phantom "Deduplication Active" row** from the Cluster Information table — the underlying `dedup_active` API field does not exist in the VAST REST API; deduplication status is correctly reported by the existing "Similarity Enabled" row (field: `enable_similarity`). Removed the phantom field from `VastClusterInfo`, `ClusterSummary`, and JSON export

### Added (Tests)
- **`test_port_mapper.py`:** New test file for port mapping unit tests
- **Updated test suites:** Health checker, rack diagram, external port mapper, and SSH adapter tests updated to match current API and behavior

### Changed (Reporter UI — Connection Settings)
- **Step text revised:** Step 1 now reads "Connect to Tech Port (TP) and verify SSH access"; Step 2 reads "Enter Tech Port IP below and save as a new profile" — steps stacked vertically for clarity
- **"SSH Proxy Mode — CNode to Switch"** shortened to **"SSH Proxy Mode"** across all three templates (`reporter.html`, `advanced_ops.html`, `generate.html`)

### Changed (Reporter UI — Select Operation Tile)
- **Step numbering unified across tiles:** Connection Settings uses Steps 1–2; Select Operation uses Steps 3–4 for a continuous workflow
- **Step 3** text reads "Click Discovery to add racks, switches, and assign U-heights"; **Step 4** reads "Save to profile and click Run to generate the Report"
- **Switch Placement Mode toggle removed:** Default to Manual; fallback to Auto if no placements configured. Compact summary section shows placement/manual counts with "Edit Placements" button
- **Switch Placement Editor modal:** All Discovery, Manual Add, assignment controls, and tables relocated from inline panel into a dedicated modal dialog with Save to Profile / Cancel buttons, Escape / click-outside-to-close, and snapshot/restore for cancel safety
- **5-step stepper action bar** replaces the flat action bar: sequential workflow (Discovery → Run → View PDF → Download PDF → Download JSON) with connected dot indicators, track line, and ghosted buttons for steps 3-5 until report completes
- **Update Tools relocated to card header:** Icon-only button with orange notification dot badge; removed from bottom action bar along with Tool Status button
- **Discovery, +Switch buttons** restyled with section labels and info icons (carried forward from prior session)
- **Enter key submission** for U Height and Switch IP / Switch Model fields (carried forward from prior session)

### Changed (Reporter UI — Test Suite)
- **Step 3** instruction added: "Select operations, click Run" — aligns with the unified step numbering

### Changed (Validation Results Page — Report Tuning Tool)
- **Regenerate PDF** button moved to the far left of the toolbar; Preview and Download buttons now populate to its right after regeneration
- **Report Tuning Tool label** restyled to match Cluster Filter label format (0.82rem, weight 500, secondary color) for visual consistency
- **"Report Sections"** heading renamed to **"Add / Remove Report Sections"** with a pencil/edit icon prefix

### Changed (Reporter UI — VAST Logo Progress Tracker)
- **Dedicated right column** for the progress tracker in both Reporter and Test Suite panels — always visible at 25% opacity when idle, fully opaque during runs
- **Smaller logo** (180x154px down from 320x274px) to fit the permanent right column without dominating the layout
- **Brand gradient on completion:** Logo fill transitions from progress cyan to official VAST brand gradient (dark navy → teal → cyan sweep) with a subtle glow animation
- **Responsive layout:** `panel-flex` uses CSS flexbox (200px right column) with column stacking on mobile

### Fixed (Reporter UI — Deployment Tools Status)
- **Close behaviors** added for Deployment Tools Status panel: Escape key, click-outside-to-close (in addition to existing X button) — applies to both Reporter and Test Suite panels

### Added (Reporter UI — Granular Progress Tracking)
- **Backend phase-level progress** for report generation: `JOB_PROGRESS` dict in app.config tracks `percent`, `phase`, and `label` across 7 weighted phases (auth 5%, data_collection 20%, health_check 15%, port_mapping 10%, data_extraction 20%, json_save 5%, pdf_generation 25%) with dynamic weight redistribution when phases are skipped
- **Backend health check progress:** `HEALTH_JOB_PROGRESS` dict with `progress_callback` on `HealthChecker`; fires after each of the 27 API checks and per-switch SSH checks with cumulative offset tracking across tiers
- **`_update_progress()` helper** in `app.py` for thread-safe progress writes under `JOB_LOCK` / `HEALTH_JOB_LOCK`
- **`/generate/status` and `/health/status`** endpoints now include a `progress` field in the JSON response
- **Frontend weighted segment mapping:** `runReporterChecklist` assigns each operation a start/width percentage range (Pre-Validation weight 10, Report 80, Health 80); polling loops read backend sub-progress and map into the overall 0–100% range
- **Smooth animation:** `VastProgress._animateTo()` uses `requestAnimationFrame` with ease-in-out curve (200–800ms) to smoothly count between percentage updates instead of jumping

### Changed (Reporter UI — Select Operation Tile Refinements)
- **Reporter / Test Suite segmented toggle** moved into a dedicated `.op-mode-bar` header bar inside the card with edge-to-edge blue separator line, matching the footer stepper style
- **Placement summary pills:** Rack count, Switches Placed count, and Open Editor button displayed as compact pills; rack count derived from placed switches when discovery data is not persisted
- **Step text formatting:** Key action phrases in Steps 1–4 styled in bold accent blue; info icon tooltips updated with physical/network connection guidance
- **Field label update:** "Tech Port IP or VMS VIP" changed to "Tech Port IP / VMS VIP"
- **Stepper action bar:** Upgraded to CSS grid layout with 18px dots, 3px borders, and chevron separators for precise alignment
- **Toggle border fix:** Corrected `var(--border-color)` (undefined) to `var(--border)` on segmented toggle
- **Info icon tooltips:** Pre-Validation and Generate As-Built Report tooltip overflow fixed by changing `.oneshot-checklist` from `overflow: hidden` to `overflow: visible`

### Changed (Reporter UI — Manual Switch Entry)
- **Switch Name field** replaces Switch IP for manually added non-VMS switches — allows free-text descriptions, names, or designations instead of requiring an IP address
- **Updated labels, placeholders, table headers, and validation** to reflect the name-based entry

### Changed (Reporter UI — Defaults and UX)
- **Generate As-Built Report** checkbox now enabled by default in the Reporter checklist
- **Info icon appearance time** reduced to 0.5 seconds via `transition-delay` on `.info-icon` hover
- **Saved Profile dropdown** default message changed to "- Create or Select a profile -"

### Changed (Application Heading)
- **Navbar heading restyled:** "As-Built Reporter" changed to "asbuilt-reporter" with "asbuilt" in white and "-reporter" in accent cyan, matching the product branding

### Changed (Dashboard — Quick Start Content)
- **Prerequisites:** "via +Switch" removed; now reads "customer-managed switches can be added manually"
- **Getting Started:** Rewritten to "Connect directly to a Tech Port or to VMS VIP over the network. Tech Port connections discover VMS CNode automatically." — removed two "If password is not default" bullets
- **Deployment Workflow — Connection Settings:** Tech Port and Network connection types moved to separate bullet lines for clarity
- **Deployment Workflow — Discovery & Switch Placement:** Rewritten to "Run Discovery, assign switch U-height. Optionally, use +Switch to add customer-managed switches and assign rack U-height, then Save to Profile."
- **Deployment Workflow — Run Report:** Rewritten from single paragraph to structured checklist (Pre-Validation, Generate As-Built Report, Health Check) with "Click Run, then monitor progress in Output Results logging console"

### Fixed (Support Tool Workflow — Output Overwriting)
- **Timestamped archive filenames:** Support tool `.tgz` archives now include `YYYYMMDD_HHMMSS` timestamp in the filename (e.g., `hostname-support_tool_logs_20260321_143022.tgz`), preventing newer runs from overwriting previous results
- **Glob patterns updated:** `result_bundler.py` and `result_scanner.py` changed from `*support_tool_logs.tgz` to `*support_tool_logs*.tgz` to discover timestamped archives

### Fixed (Reporter UI — Config Sync)
- **Advanced Configuration settings** (SSH Proxy Jump, Tech Port Mode, Auto-fill Default Passwords) now correctly sync to Reporter Connection Settings Advanced checkboxes at page load, overriding stale localStorage values
- **Autofill Passwords credential handling:** All user/password settings saved regardless of Autofill state; custom values persist when Autofill is disabled; re-enabling Autofill resets to defaults; user edits take precedence over defaults

### Fixed (Reporter UI — Discovery Timeout)
- **Discovery API timeout** reduced from ~2 minutes to 15 seconds with a pre-flight connectivity check; graceful error message when cluster IP is unreachable

## [1.5.0] - 2026-03-28

### Added (Advanced Configuration UI)
- **Advanced Configuration page** (`/config/advanced`): New form-based settings management page replacing the raw YAML editor as the default configuration interface
  - **Report Tuning Tool** (sticky top toolbar): Select a JSON report file from output directories or upload a new one, apply configuration overrides (formatting, sections), and regenerate a PDF with Preview and Download buttons
  - **Nine accordion sections:** Report Formatting, Report Data Collection, API Settings, Logging, Output, SSH, Health Check, Advanced Operations, Security — each with typed form controls (text, number, select, toggle) bound to `config.yaml` keys via `data-key` attributes
  - **Deep-merge save:** Save operation merges form values into existing config rather than replacing the entire file, preventing loss of config keys not represented in the form
  - **Upload and select workflow:** Browsed JSON files are uploaded to the reports directory, added to the dropdown, and auto-selected
  - **Reset to Template** button loads default values from `config.yaml.template` without saving
- **Raw YAML config editor** moved to Developer Mode only (accessible via hamburger menu)

### Changed (Report Formatting — Margin & Content Sizing)
- **Default margins changed to 0.5"** on all sides (from 1.0") in both `config.yaml.template` and active `config.yaml` — resolves TOC layout issues and narrow table columns at 1.0"
- **Margin-aware content sizing:** All table `colWidths` and diagram scaling now derive from `self._frame_width` / `self._frame_height` instead of hardcoded `A4[0] - 1.0 * inch`; 9 width calculations updated across report builder methods
- **Margin clamping:** UI restricts inputs to 0.25"–1.5" with validation warning; backend enforces `MIN_FRAME_W=360` / `MIN_FRAME_H=600` floor with automatic fallback to 0.5" defaults
- **Rack diagram headroom:** Frame height passed to `RackDiagram` reserves 1.0" for heading/spacer; wrapper table padding zeroed out — prevents `LayoutError` overflow at any valid margin setting
- **"Report Data Collection"** renamed from "Data Collection" in Advanced Configuration

### Fixed (Report Formatting)
- **Organization field** now passed through `ReportConfig` and `brand_compliance.create_vast_page_template()` to PDF report footer
- **Margins** correctly applied via `brand_compliance` frame dimensions instead of ignored `BaseDocTemplate` margin parameters
- **Include Page Numbers** toggle now conditionally draws page numbers in `brand_compliance` footer
- **Font Family** selection (Helvetica, Times-Roman, Courier) applied via `_font()` helper that resolves dynamic font variants (bold, italic) for each family
- **Blank page on page 9** fixed: removed redundant `PageBreak()` in `_create_hardware_inventory` that triggered double page breaks when `total_devices > 15` with rack positions available

### Changed (Health Check — VIP Pools)
- **VIP Pools:** Status changed from `fail` to `warning` when no VIP pools are configured — an unconfigured VIP pool is informational, not a failure
- **Render-time fixup for VIP Pools:** Reports regenerated from pre-fix JSON files automatically correct stale `fail` status to `warning` for "No VIP pools configured" and "No enabled VIP pools" messages, with summary counts adjusted

### Fixed (Reporter UI — Config Wiring)
- **SSH, Health Check, Advanced Operations, and Security** settings configured in Advanced Configuration are now reflected in the Reporter UI at page load
  - Proxy Jump toggle initialized from `ssh.proxy_jump`
  - Default credentials toggle from `advanced_operations.autofill_default_passwords`
  - Switch placement mode from `advanced_operations.default_switch_placement`
  - vperfsanity default selection from `advanced_operations.vperfsanity_default_selected`
  - Reporter vs Test Suite mode from `advanced_operations.default_mode`

### Added (Diagnostics)
- **Prometheus device metrics diagnostic** (`tests/diag_prometheus_metrics.py`): Probes 14 Prometheus metric paths (`devices`, `cnodes`, `cluster`, `network`, etc.), parses and summarizes each, highlights health-relevant metrics, and saves raw text and parsed JSON to `reports/` for evaluation

### Changed (Health Check — Check Tuning & Tier 2 Removal)
- **Active Alarms:** Status changed from `fail` to `warning` when unresolved critical/major alarms are present — alarms are informational indicators, not hard failures
- **CNode Status — Management CNode handling:** Inactive CNodes that are the dedicated Management CNode (VMS) no longer cause a failure; check passes with message `"All N CNodes healthy (VMS on cnode-X)"`
- **Switches in VMS:** Status changed from `warning` to `skipped` when no switches are registered; removed the prescriptive "Add switches in VMS for port mapping functionality" message
- **Monitoring Config check removed:** Entire check removed — SNMP and syslog API endpoints do not exist in the VAST API; check always returned false results
- **Tier 2 node SSH checks removed:** All 10 node SSH checks removed (Panic/Alert Logs, Management Ping, Memory Usage, Disk Space, Time Sync, Core Dumps, Network Interfaces, VAST Services, VAST Support Tools, VNet Map) — these are redundant with diagnostics run by `vast_support_tools.py` in the One-Shot test suite, and produced false-positive results when SSH targeted the Management CNode
- **Render-time fixups for old JSON:** Reports regenerated from pre-fix JSON files automatically correct stale health check results (CNode Status management pass-through, Active Alarms downgrade, Switches in VMS reclassification, Monitoring Config removal, node_ssh row filtering) with summary counts adjusted to match

### Added (Report — Post Deployment Activities Dynamic Status)
- **Dynamic status column** in Post Deployment Activities table: status auto-resolves from health check results and cluster data at report generation time
  - **Completed** (green): Call Home enabled, VIP pools configured, License activated — detected from health check pass or cluster API fields
  - **Optional** (accent blue): Fail-over testing and VIP/ARP validation — manual verification items
  - **Pending** (orange): Items not yet completed or not auto-detectable (e.g., Change Default Passwords)
- **Render-time fallback:** Reports regenerated from existing JSON files also resolve status from embedded health check data
- **`ACCENT_BLUE`** (#1A6FB5) added to brand compliance colors — matches app UI button color

### Added (Rack Diagram — Status Indicators)
- **Per-device status indicators:** Color-coded shapes drawn on each device in the Physical Rack Layout diagram
  - **CBox**: 1–4 circles (one per CNode) — green=Active, orange=Inactive, blue=Management CNode (VMS)
  - **DBox**: 1–4 squares (one per DNode) — green=Active, orange=Inactive
  - **EBox**: 1 circle (CNode) + 2 squares (DNodes) grouped in a horizontal line
  - **Switch**: Single dot — green if ACTIVE/ONLINE/OK in Hardware Inventory, orange otherwise; no dot for manually-added switches
- **Dark pill background** behind each device's indicator row for contrast against hardware images
- **Status Indicator legend tile** positioned to the left of each rack diagram, centered vertically, explaining circle/square color codes

### Changed (Rack Diagram — Device Labels)
- **CBox/DBox labels replaced with serial names:** Rack diagram labels now show the Hardware Inventory Name/Serial Number (e.g., `cbox-S961313X6134067`) instead of generic `CBox-6` / `DBox-1` numbering
- **DBox deduplication:** Multiple dnodes sharing the same physical DBox at a given U position (e.g., 4x Ceres V1 dnodes) now render as a single device with one label instead of 4 overlapping entries

### Added (Hardware Library)
- **`supermicro_turin_cbox`** entry: Matches the `supermicro_turin_cbox` model string returned by the VMS API for SMC Gen6 Turin CBoxes (image: `smc_turin_cbox_1u.png`)
- **`bluefield`** entry: Matches the `bluefield` hardware_type returned by the VMS API for Ceres V1 1U DBoxes (image: `ceres_v2_1u.png`)

### Added (Report — Section Toggles)
- **Per-section PDF visibility toggles:** All 11 report sections (Executive Summary, Cluster Information, Hardware Inventory, Network Configuration, Switch Configuration, Port Mapping, Logical Configuration, Security & Authentication, Data Protection, Health Check, Post Deployment Activities) can be individually disabled via `data_collection.sections` in `config/config.yaml`
- When a section is set to `false`, its heading, description paragraph, tables, images, and TOC entry are all omitted from the PDF output
- JSON data export is unaffected — all data is always collected regardless of section toggle state

### Changed (Dashboard — Quick Start Revamp)
- **Dashboard redesigned as Quick Start launch pad:** Replaced generic cards and Recent Reports table with a dynamic status bar (job status, last report, deployment tools, saved profiles) and five clickable workflow step cards guiding users from prerequisites through report review
- **New `/api/dashboard/status` endpoint:** Lightweight JSON API aggregating active job state, tool cache status, profile count, and latest report metadata; polled every 15 seconds by Dashboard JS
- **New CSS component library:** Status bar tiles (`status-tile`, `status-dot`), numbered workflow cards (`step-card`, `step-number`), responsive grid layouts with hover effects and accent borders

### Added (Network Configuration — NVMe/TCP Ethernet MTU)
- **`nb_eth_mtu` collection and reporting (NET-1):** NVMe/TCP Ethernet MTU is now collected from both `clusters/` and `vms/1/network_settings/` API endpoints, extracted through `VastClusterInfo` and `ClusterSummary` dataclasses, and reported in the PDF Network Configuration sections and JSON export alongside `eth_mtu` and `ib_mtu`

### Added (SSH Proxy Hop — Field Deployment Support)
- **SSH proxy hop for field deployments:** Switch SSH connections now tunnel through the CNode via paramiko nested transport (`direct-tcpip` channel), enabling port mapping and Tier 3 health checks when switches are only reachable from inside the cluster network
- **"Proxy through CNode" toggle** on Generate and Reporter pages (default: ON) — persists in profiles and UI state
- **CLI `--no-proxy-jump` flag** to disable proxy hop for direct-connection environments
- **Improved error messages** distinguish unreachable switches (network/connectivity) from authentication failures, with actionable guidance

### Changed (Version & Branding)
- **Version bumped to v1.5.0** across all canonical locations (`src/app.py`, `src/main.py`, `src/__init__.py`, `packaging/vast-reporter.spec`)
- **Beta badge removed** from the navigation header for production release (REL-1)

### Changed (Connection Settings Layout — Advanced Ops)
- **Collapse/expand arrow** moved to the card header for always-accessible tile toggling
- **Initial render** now shows only the Saved Profiles dropdown, Create Cluster button, and collapse arrow (collapsed by default)
- **Expand** reveals all credential fields, the Global Setting — Autofill Default Passwords toggle (Disable / Enable labels), and Save / Delete profile icons
- **Collapse** returns to the minimal dropdown-only view; no intermediate state
- **Create Cluster Profile button** always expands the full tile, sets dropdown to "-- Create a profile --", and clears Cluster IP
- **Default Passwords toggle** relabeled: heading reads "Global Setting — Autofill Default Passwords" with Disable/Enable flanking the switch
- **Save and Delete icons** relocated to the bottom-right of the tile toolbar
- Tile collapse/expand state persisted in localStorage across page navigation

### Changed (Default Credentials)
- **Global default changed to `support` / `654321`** across Advanced Ops, Generate, and Health Check pages — all pages now share the same default API user
- **vperfsanity auto-override:** When "Autofill Default Passwords" is enabled, the One-Shot runner automatically injects `admin` / `123456` for the vperfsanity operation only — the single operation that requires admin access
- **Actionable auth failure hint:** If vperfsanity encounters an HTTP 403, the output now advises the user to disable autofill defaults and enter the current admin credentials

### Fixed (Report — Health Check & Post Deployment)
- **Memory usage message:** Removed the parenthetical "(high utilization is normal for VAST clusters)" from the Detailed Check Results memory usage row for a cleaner report
- **Next Steps table word wrap:** The "Post Deployment Activities — Next Steps" checklist table now wraps text properly within column boundaries using `Paragraph` objects; row heights dynamically resize to fit wrapped content

### Fixed (Result Bundler — As-Built Report Collection)
- **As-Built report PDF now included in bundle:** Bundler matches reports via `.meta.json` sidecar `cluster_ip` field instead of relying on cluster name in filename (which failed when only the IP was known)
- **As-Built JSON data file** now collected alongside the PDF in the `reports/` folder within the bundle
- **Cluster name auto-resolution:** When `cluster_name` is missing or equals the IP, the bundler scans existing `vast_data_*.json` files to resolve the real API cluster name for accurate manifest metadata
- **One-Shot runner** now passes the resolved API cluster name (from report data) to the bundler instead of the raw IP

### Added (Reporter Page — Standard-Mode Workflow Interface)
- **Reporter page:** New `/reporter` page as the primary user-facing workflow interface, combining as-built report generation with switch placement and post-install validation
  - **Switch Placement Mode:** Auto/Manual toggle with rack/switch discovery, manual switch IP entry, and placed switches table; settings persist in cluster profiles
  - **Reporter Checklist:** Pre-Validation (recommended), Run Reporter, and optional Health Check with tier logic
  - **View/Download PDF and Download JSON buttons** appear upon report completion
  - **Manual switch discovery workflow:** When no switches found, options to manually add switches or add in VMS with re-run discovery
  - **Library switch integration:** Manual switch IP entries use library switch model dropdown for correct rack diagram rendering

### Added (Navigation Restructuring)
- **Hamburger menu:** Legacy and Developer pages moved to collapsible menu in top-right navbar
  - **Legacy section:** Generate, Reports
  - **Developer section** (dev-mode only): Advanced Ops, Health Check, Configuration
- **Standard navigation:** Dashboard, Reporter, Results, Library, Docs always visible
- **"Validation Results" renamed to "Results"** in navigation header
- **Library** repositioned between Results and Docs in navigation order
- **Page heading icons** added to all navigation buttons and page titles

### Added (One-Shot UI Overhaul)
- **Pre-Validation converted to checkbox** at the top of the One-Shot checklist (previously a separate button)
- **"Start One-Shot" button renamed to "Run"**
- **"Download Bundle" button** now hidden until all operations complete
- **"View Deployment Tool Status" button** added next to "Update Tools"
- **Operation badges** with color-coded labels on left side of each operation:
  - Pre-Validation: "Recommended" (orange)
  - vnetmap: "Net Test" (green)
  - Support Tools: "Sys Test" (green)
  - vperfsanity: "Perf Test" (green)
  - Log Bundle: "Pull Logs" (green)
  - Switch Config: "Pull Config" (green)
  - Network Config: "Pull Config" (green)
  - Generate As-Built Report: "Recommended" (orange)
  - Include Health Checks: "Optional" (blue)
- **Reporter/One-Shot toggle** uses consistent blue on both sides (mode switch, not on/off)
- **vperfsanity default unchecked** in One-Shot checklist

### Added (VAST Logo Progress Indicator)
- **VAST Logo fill animation** replaces previous SVG ring progress indicator
  - CSS `mask-image` over dynamic `linear-gradient` fills the VAST logo incrementally as operations progress
  - Percentage and stopwatch timer displayed in the logo center
  - Positioned in open area to the right of operations list (One-Shot) or under placed switches table / centered overlay (Reporter)
  - Pulse animation during active operations; fills to completion state with checkmark on success
  - Error and cancel states with distinct colors

### Added (Connection Settings Enhancements)
- **Field label changes:** "Cluster IP" → "Cluster IP / VMS", "API Username" → "VMS Username", "API Password" → "VMS Password"
- **Info icons with tooltips** on all connection settings fields:
  - Cluster IP: Tech Port IP guidance (192.168.2.2)
  - VMS Username: Support-level authorization requirement
  - VMS Password: Default support password
  - Node SSH Password: Default vastdata password
  - Switch SSH User: Per-vendor user guidance (cumulus, admin)
  - Switch SSH Password: Per-vendor default passwords
- **"Global Setting — Autofill Default Passwords" info icon** listing applied credentials

### Changed (Validation Results Page)
- **Tab space increased** to eliminate vertical scrollbar
- **Output Directory tile** added at page top
- **Cluster Profile dropdown** positioned parallel to output directory
- **Tab labels shortened:** Reports, Health, Network, Switch, vnetmap, vperfsanity, Support, Logs, Bundles
- **Equal tab sizing** with even spacing; tabs prevent overflow on narrow widths
- **Tab colors adjusted** for visibility with darker edge contrast
- **SVG document type icons** and icon action buttons replace text buttons
- **Column widths optimized** to minimize text wrap

### Changed (Library Page)
- **Image requirements text removed** (format, "No file chosen", placeholder notes)
- **Choose File button** replaced with consistently styled button
- **Device Image info icon** with hover tooltip detailing image guidelines (format, dimensions, sizes)

### Changed (Health Check Page)
- **Log window height increased** in Progress tile for better log visibility

### Changed (Docs Page)
- **Live API Explorer** restricted to Developer Mode only

### Fixed (Rack Diagram)
- **Placeholder Arista switch injection removed:** Fallback code that injected 2 placeholder Arista 7060DX5 switches eliminated
- **Manual switch placement data** now correctly flows to report generation even without API-discovered switches
- **Manual placement processing enhanced:** `model_key`, `name`, and `height_u` correctly extracted from manual placement data

### Fixed (Dynamic Log Tier Filtering)
- **Log tier passthrough** fixed on Reporter and Advanced Ops output panes — Status, Live, Debug filtering now works correctly by passing `e.log_tier` to `outputPane.append()`

### Fixed (Port Mapping Activation)
- **Frontend-backend payload mismatch:** `enable_port_mapping` now sent as `'on'` string instead of boolean `true` to match backend expectation

### Added (One-Shot Orchestration Mode — AO-16)
- **One-Shot Mode for Advanced Operations:** New toggle in Advanced Ops "Select Operation" tile switches between step-by-step and one-shot modes
  - **Checkbox Operation Selection:** Select multiple operations to run sequentially in a single pass
  - **Pre-Validation Checks:** Automated checks before execution — credential completeness, cluster API reachability, node/switch SSH connectivity (with proceed/stop option), cluster outbound internet access (for vnetmap/support tools/vperfsanity downloads), tool freshness (warn if >10 days old), vperfsanity ~30 min duration notice
  - **Sequential Execution:** Selected operations first, then optional As-Built report generation (health checks run within report when selected)
  - **Auto-Bundling:** All results automatically bundled into a cluster-scoped ZIP on completion
  - **Progress Tracking:** Phase indicator (Health Checks → Operations → Report → Bundling) with operation counter
  - **Cancellation Support:** Cancel at any point between phases or workflow steps
  - **Health Checks now optional:** Selectable checkbox (checked by default, "Recommended" badge) instead of forced
  - **SSL fix for pre-validation:** Disabled SSL verification and reduced timeouts in validation API calls to prevent hangs with self-signed cluster certs
  - **Async pre-validation with cancel:** Validation runs in a background thread; Cancel button stops validation at any point
- **OneShotRunner Module:** New `src/oneshot_runner.py` orchestrator with pre-validation, phased execution, and progress state tracking

### Added (Validation Results Page — AO-18, Developer Mode)
- **Validation Results Page:** New `/validation-results` page (developer mode only) for browsing all operation results
  - **Operation Tabs:** 9 tabs — As-Built Reports, Health Checks, Network Config, Switch Config, vnetmap, vperfsanity, Support Tools, Log Bundles, Bundles
  - **Profile Filter Dropdown:** Filter all tabs by saved cluster profile, "All Clusters", or "Unsaved Cluster Results"
  - **Per-Tab Result Tables:** File name, type badge, size, cluster IP, generated date, View/Download/Delete actions
  - **File Counts:** Tab badges show result counts per operation
- **ResultScanner Module:** New `src/result_scanner.py` scans all output directories, tags results by cluster_ip, groups by operation type

### Added (Dynamic Log Levels and State Persistence — AO-19, in progress)
- **Dynamic Log Level Selector:** Three-tier output filter buttons (Status / Live / Debug) in the Advanced Ops output pane
  - **Status:** Operation start/complete banners, progress counters (1/N), phase results summary
  - **Live:** Everything in Status + piped internal logger output from HealthChecker, report pipeline, and workflows
  - **Debug:** Everything in Live + debug-level messages
- **Per-Check Health Progress:** Individual health check results reported in output (e.g., "[PASS] Cluster RAID Health (1/28)")
- **Report Generation Progress:** Step-by-step status messages during As-Built report generation (authenticating, collecting data, processing, generating PDF)
- **Persistent Operation Logs:** Session logs auto-saved to disk on One-Shot completion with 1GB total capacity limit; oldest 25% purged when exceeded with user warning
- **Window State Persistence:** Advanced Ops page resumes its exact state after navigation or browser close/reopen
  - Backend state snapshot API returns running operation state, progress, and output count
  - Frontend hydrates from backend snapshot on page load — resumes polling and progress UI
  - UI preferences (mode toggle, selected profile, checklist, log tier) persisted in localStorage
  - Output buffer de-duplication prevents duplicate log entries on resume

### Changed (Navigation — AO-19, in progress)
- **Health Check and Configuration moved to Developer Mode:** Nav links and routes now gated behind `--dev-mode` flag alongside Advanced Ops and Validation Results

### Planned (Generate Report Page — AO-20, future)
- Apply log level selector, persistent log storage, and window state persistence to Generate Report page

### Changed (Result Bundler — Cluster-Scoped Improvements)
- **PDF reports now filtered by cluster name** instead of always picking the globally latest PDF
- **Support tools matched via sidecar `.meta.json`** (new) instead of broken text-header heuristic on binary .tgz files
- **Log bundles matched via verification JSON `cluster_ip`** (new) instead of being excluded when cluster-scoped
- **All switch txt files included** in bundle (previously only one due to `setdefault` bug)
- **Health remediation report** and **vnetmap output txt** now collected in bundles
- **Missing operation placeholders:** Bundle includes `{category}_NOT_FOUND.txt` for operations not run for the cluster
- **Workflow metadata improvements:** Log bundle verification JSON and support tool archives now embed `cluster_ip`

### Added (Test Coverage Phase A-C)
- **Test Coverage Phase A-C:** Implemented 8-stream test coverage plan adding ~98 new tests across all modules
  - **WS-1 Config:** Fixed stale vperfsanity step count test (6→7); added `[tool.coverage.run]` omit for 3 dead-code modules; raised `cov-fail-under` from 45 to 55
  - **WS-2 ToolManager Tests:** New `tests/test_tool_manager.py` with 12 tests for initialization, local cache operations, and CNode deployment (internet-first, SCP fallback)
  - **WS-3 Workflow Execution Tests:** 18 tests added to `tests/test_workflows.py` for cross-tenant cleanup, vperfsanity step execution, switch type detection, network config clush, support tool container paths, log bundle discovery
  - **WS-4 App Route Tests:** 15 tests added to `tests/test_app.py` for profile merge-save (field preservation, api_token→token normalization, defaults), advanced ops routes, and tool management routes
  - **WS-5 ScriptRunner Tests:** 10 tests added to `tests/test_script_runner.py` for output line classification, copy_to_remote, and download_from_remote
  - **WS-6 Health Checker Tests:** 15 tests added to `tests/test_health_checker.py` for remediation report generation, correlation engine (chassis-level, leader-inactive), SSH tier-2 (management ping, memory), and SSH tier-3 (MLAG, NTP, switch checks)
  - **WS-7 Rack Diagram Tests:** 14 tests added to `tests/test_rack_diagram.py` for device boundaries, center/above/below switch placement strategies, and diagram generation
  - **WS-8 External Port Mapper Tests:** New `tests/test_external_port_mapper.py` with 12 tests for switch OS detection, MAC table parsing (Cumulus/Onyx), clush output parsing, and cross-connection detection
- **Coverage Omit Config:** Added `[tool.coverage.run]` section to `pyproject.toml` excluding dead-code modules (`comprehensive_report_template.py`, `enhanced_report_builder.py`, `session_manager.py`) from coverage measurement

- **Advanced Operations Module (Developer Mode):** New `/advanced-ops` page for complex script-based validations with step-by-step execution
  - **vnetmap Workflow (7 steps):** Download and run vnetmap.py for network topology validation
  - **VAST Support Tools Workflow (5 steps):** Run vast_support_tools.py for cluster diagnostics
  - **vperfsanity Workflow (7 steps):** Deploy, extract, prepare infrastructure (with cross-tenant cleanup), run tests, collect results, upload, and cleanup
  - **VMS Log Bundle Workflow (5 steps):** Discover log sizes, confirm collection, create and download bundle
  - **Switch Configuration Workflow (3 steps):** Extract switch config for backup/replacement; auto-detects Cumulus NVUE/NCLU and Mellanox switch types
  - **Network Configuration Workflow (4 steps):** Extract configure_network.py commands via gateway-proxied clush execution
- **Result Bundler:** Create downloadable ZIP packages containing all validation outputs
- **Workflow Registry Pattern:** Centralized workflow registration and discovery via `src/workflows/__init__.py`
- **Script Runner Framework:** Core infrastructure for secure script download, remote execution, and intelligent output classification
- **Tool Manager:** Centralized deployment tool management with internet-first download strategy and local cache fallback; "Update Tools" button in UI
- **Cross-Tenant View Cleanup:** vperfsanity Step 3 now queries the VAST API for stale `vperfsanity` views across ALL tenants and deletes them before running the prepare script, preventing HTTP 400 "bucket name already in use" errors
- **Unified Profile Management:** Profiles saved in Advanced Ops are accessible in Health Check and Generate Report (and vice versa) via merge-save pattern in backend; handles `api_token`/`token` field name aliases
- **Default Credentials Toggle:** Toggleable feature on Advanced Ops page (default ON) auto-populates standard credentials (admin/123456 for API, vastdata/vastdata for nodes, cumulus/Vastdata1! for switches)
- **Connection Settings Redesign:** Collapsible credential section, profile icon buttons (save/add/delete), green Add button toggles expand/collapse, VIP Pool Name field for vperfsanity
- **Developer Mode Gating:** Advanced Operations page only accessible when app started with `--dev-mode` flag
- **CI Advanced Ops Tests:** New `advanced-ops-tests` job in CI pipeline for workflow testing
- **Health Check Module:** New `health_checker.py` with 26 Tier-1 API checks, Tier-2 node SSH checks, and Tier-3 switch SSH checks
- **Dynamic Health Check Tiers in Generate:** When "Include Health Check" is enabled, tiers are selected based on Port Mapping:
  - Port Mapping disabled → Tier 1 only (26 API checks)
  - Port Mapping enabled with SSH credentials → Tier 1+2+3 (API + Node SSH + Switch SSH)
- **Health Check UI Hint:** Generate page shows dynamic hint explaining which tiers will run
- **Health Check UI:** New `/health` page with real-time SSE log streaming, tier selection, and job control
- **Remediation Report Generator:** Health check auto-generates `.txt` remediation report with numbered findings, severity levels, timestamps, impact statements, correlated issues, and actionable remediation steps
- **Health Check Correlation Engine:** Detects related failures (e.g., CNode+DNode down = chassis issue; leader marked inactive = inconsistency warning)
- **Health Check PDF Sections:** Cluster Health Check Results and Post Deployment Validation sections in PDF report
- **API Handler Extensions:** New `get_alarms()`, `get_events()`, `get_snapshots()`, `get_quotas()`, `get_prometheus_metrics()` methods
- **Include Health Check Option:** Checkbox in Generate page to optionally include Tier-1 health check in report generation
- **CI Health Check Tests:** New `health-check-tests` job in CI pipeline for fast feedback

### Fixed
- **CNode/DNode Status Detection:** Fixed false-positive failures where active nodes were reported as inactive; health checker now uses `state` field (VAST API standard) instead of `status`
- **API Endpoint Cleanup:** Removed undocumented/non-functional API calls per official VAST API v7 documentation:
  - Removed `ntps/` call (NTP retrieved from `clusters/` endpoint)
  - Removed `alerts/` call (not documented in VAST API)
  - Changed `alarmdefinitions/` to `eventdefinitions/` (documented endpoint)
- **Reduced Log Noise:** Changed WARNING to DEBUG for optional endpoints that return 404 when features aren't configured (ldap/, nis/, snapprograms/, snmp/, syslog/)
- **Network Settings API Mapping:** Fixed DNS/NTP/gateway always showing as null; now correctly unwraps `response["data"]` from VMS API and uses proper field names
- **SSH Check Timeout:** Fixed indefinite hang on Tier-2 node SSH checks; management ping now has 60s overall limit, 10s per-ping SSH timeout, and cancellation checks
- **RAID Rebuild Progress:** Fixed 100% rebuild progress incorrectly shown as "in-progress"; now correctly reports as complete
- **Leader State Check:** Fixed "UP" leader state incorrectly flagged; now accepts "UP" as healthy
- **Upgrade State Check:** Fixed "DONE" upgrade state shown as warning; now correctly reports as pass
- **Prometheus Timeout:** Fixed hardcoded timeout; now uses configurable `self.timeout` value
- **vperfsanity Cross-Tenant Bucket Conflict:** Fixed HTTP 400 "bucket name already in use by another tenant" by adding API-level cross-tenant view cleanup before running `vperfsanity_prepare.sh`
- **vperfsanity Missing VAST_VMS:** Fixed prepare/run/cleanup commands not passing `VAST_VMS` environment variable to remote scripts, causing API calls to target wrong endpoint
- **vperfsanity SSH Credentials:** Fixed workflow incorrectly using API credentials for SSH connections; now correctly uses node SSH credentials (vastdata) for all SSH operations
- **vnetmap Resilience:** Workflow continues through partial failures (e.g., CNode down) with warnings and recommendations instead of hard-failing
- **vnetmap SSH Retry Noise:** Intelligent output classification (`_classify_output_line`) suppresses SSH key retry messages from vnetmap.py stderr
- **Switch Config Detection:** Auto-detects Cumulus NVUE vs NCLU vs Mellanox switch types; uses appropriate commands (`nv` vs `net`); removed `sudo` commands that require password
- **Network Config clush:** Rewrote to use gateway-proxied clush execution with proper single-quote escaping for inner commands; fixed "Binary file matches" error with `-a` grep flag
- **VAST Support Tools Container Path:** Fixed script execution path to use `/vast/data/` inside VAST container instead of `/tmp/vast_scripts/`
- **SSH Adapter Stability:** Enhanced paramiko connections with `banner_timeout=30`, `look_for_keys=False`, `allow_agent=False`; added `force_tty`, `login_shell`, `agent_forward` parameters
- **App Stability:** Resolved frequent app shutdowns from port conflicts and stale processes

### Changed
- **Alarm Details:** Health check captures per-alarm severity, object type, object name, and timestamp for detailed remediation guidance
- **Health Check Report Table:** Removed Duration column from "Detailed Check Results" table; adjusted column widths (Message column expanded to 56% for better text fit)
- **Event Definitions:** Health checker now uses `/api/eventdefinitions/` (documented) instead of `/api/alarmdefinitions/` (undocumented) for enriching alarm descriptions
- **Events API:** Added pagination and time filter to prevent timeout on clusters with large event history

### Changed (Advanced Operations)
- **vperfsanity Workflow:** Expanded from 6 to 7 steps (added Upload Results); pre-cleanup step runs before prepare; admin credentials passed via `ADMIN_USER`/`ADMIN_PASSWORD` environment variables
- **Advanced Ops UI:** Redesigned Connection Settings with collapsible section, icon-based profile controls, Default Credentials toggle switch, and increased output pane height (+200px)
- **Profile Controls:** Reverted dropdown to standard form-group style with icon buttons for consistency across Generate, Health Check, and Advanced Ops pages
- **Script Runner:** Added `_classify_output_line` method for intelligent SSH output noise filtering

### Technical Details
- Validated on selab-var-202, selab-var-203, selab-var-204 clusters
- Tier-1 + Tier-2 health checks now complete in ~24 seconds
- Remediation reports saved to `output/health/health_remediation_<cluster>_<timestamp>.txt`
- `src/workflows/vperfsanity_workflow.py`: `_api_cleanup_cross_tenant_views()` queries `GET /api/views/`, finds stale views by alias/bucket/path, deletes via `DELETE /api/views/<id>/`
- `src/tool_manager.py`: Internet-first download with local cache fallback; `deploy_tool_to_cnode()` for secure remote deployment
- `src/app.py`: Merge-save profile pattern preserves fields across pages; `ALL_FIELDS` dict with defaults; `api_token`/`token` normalization
- `src/script_runner.py`: `_classify_output_line()` demotes SSH retry noise to DEBUG level
- `src/utils/ssh_adapter.py`: `force_tty`, `login_shell`, `agent_forward` parameters; `sshpass` security; paramiko hardening

## [1.4.7] - 2026-03-17

### Fixed
- **PDF Generation Error:** Fixed `'str' object has no attribute 'wrapOn'` error when API returns list values (e.g., `ekm_servers`, `dns`, `ntp`) that were placed directly in ReportLab table cells
- **Security & Authentication Table:** EKM servers, addresses, and encryption settings now properly handle list values from API by converting to comma-separated strings
- **Network Configuration Table:** Management VIPs, external gateways, DNS servers, NTP servers, and IPMI settings now safely converted to strings before table insertion

### Added
- **Safe Table Value Helper:** New `_safe_table_value()` method in `VastReportBuilder` that converts any value type (lists, None, dicts) to safe strings for table cells

### Technical Details
- Root cause: VAST API returns `ekm_servers` as nested list (e.g., `[['hostname', port]]`) which ReportLab cannot render directly in table cells
- Fix handles lists by joining elements with commas; handles None/empty with configurable default
- Validated with JSON-to-PDF regeneration test on affected cluster data

## [1.4.6] - 2026-03-17

### Added
- **Pre-release checklist (QG-1):** README Development section documents running flake8, black, mypy, and pytest (with coverage) before release/merge; aligns with CI quality gate.
- **Library API tests (TSE-1):** Unit tests for GET `/library`, GET/POST/DELETE `/api/library` with mocked `_load_library`/`_save_library` in `tests/test_app.py` (TestLibraryRoutes).
- **Generate cancel test (TSE-2):** Unit tests for POST `/generate/cancel` — no job returns `no_job`; job running accepts cancel and sets JOB_RESULT (TestGenerateCancel).
- **Reports dirs tests (TSE-3):** Unit tests for GET `/reports/dirs` and POST `/reports/dirs` with valid path (updates config) and 400 for empty/nonexistent (TestReportsDirsRoutes).
- **EBox Port Mapping:** EBox-specific port mapping with CNode/DNode names in Notes column; standard CBox/DBox clusters show "Primary" in Notes
- **EBox Network Diagram:** Logical Network Diagram shows EB# labels for EBox clusters with Green (Network A) and Blue (Network B) connections to switches
- **Built-in Hardware Library:** Added msn4700-ws2rc (Mellanox SN4700 400Gb 32pt Switch, 1U) and dell_genoa_ebox (Dell Genoa 1U EBox) as permanent built-in devices

### Changed
- **Coverage threshold:** `cov-fail-under` set to 47% in pyproject.toml and CI workflows (current suite ~47%); restoration to 49%+ tracked in docs/TODO-ROADMAP.md (QG-3, TSE-8).
- **Port Mapping Section:** Added page break before Port Mapping heading; Switch 1 table now appears before Switch 2
- **Switch Configuration Section:** Added page break before Switch Configuration heading
- **Network Diagram Connections:** Fixed CNode-to-switch (top to middle) and DNode-to-switch (bottom to middle) connection line coordinates

### Policy & API
- **Read-only VAST API policy:** The app must never use VAST API calls that change or update the cluster. Data collection uses **GET only**. `_make_api_request()` in `api_handler` now accepts only GET and raises `ValueError` for POST/PUT/DELETE. Authentication may still use POST only to establish read-only access (session/token/JWT). See [docs/development/READ_ONLY_VAST_API_POLICY.md](docs/development/READ_ONLY_VAST_API_POLICY.md) and `.cursor/rules/api-handler-05.mdc`.

### Added (tests)
- **TSE-4:** Unit tests for POST `/api/discover` (400 missing cluster_ip, 401 auth failure, 200 success with mocked `create_vast_api_handler` and `RackDiagram`). All discovery flows are read-only (get_racks, get_switch_inventory).
- **Read-only enforcement test:** `test_make_api_request_only_get_allowed` in test_api_handler verifies that POST/PUT/DELETE/PATCH raise ValueError.
- **TSE-5:** Integration test for report content: raw data with EBox + dell_turin_cbox + serial; asserts processed hardware_inventory and successful PDF generation (test_integration.py).
- **TSE-6:** Unit tests for Profiles API: GET/POST `/profiles` and DELETE `/profiles/<name>` with mocked `_load_profiles`/`_save_profiles` (TestProfilesRoutes in test_app.py).
- **TSE-7:** Unit test for POST `/shutdown` (200, status `shutting_down`; `os._exit` mocked so process does not exit).
- **TSE-8:** Coverage restored above 49%; full suite (unit + integration) now ~53% (279 tests).

## [1.4.3] - 2026-03-16

### Fixed
- **CBoxes missing from Physical Rack Layout**: Rack diagram now builds one entry per CBox (not per CNode) and uses CBox `rack_unit` / `rack_name` with fallback to CNode `rack_position` (`U{n}`); single-VMS rack fallback so CBoxes are not dropped when rack name is "Unknown"
- **Network diagram placeholder on macOS**: When reportlab renderPM fails (T1 font), use `qlmanage` to convert the generated PDF to PNG so the report embeds the real topology diagram instead of the placeholder
- **Windows PDF "Permission denied"**: First-pass temp PDF now uses `tempfile.mkstemp()` and explicit unlink instead of `NamedTemporaryFile(delete=True)` to avoid Windows temp file locking
- **Windows port mapping charmap error**: All SSH/subprocess output in port mapping now decoded with `encoding="utf-8", errors="replace"` so UTF-8 from switches/nodes does not trigger `'charmap' codec can't encode` on Windows

### Changed
- **README**: Table of contents, quick start, and troubleshooting (Windows PDF, port mapping charmap); project structure and docs links updated
- **Report builder**: Per-CBox rack grouping and rack_unit from CBox or CNode; Unknown rack mapped to single VMS rack when applicable

## [1.4.2] - 2026-03-11

### Added
- **EBox discovery (API v7)**: Full EBox integration — `GET /api/v7/eboxes/`, cluster `ebox` flag, `ebox_id` on CNodes/DNodes; `get_ebox_details()` in API handler; EBox quantity and inventory in report (cover, executive summary, consolidated hardware table); `docs/api/EBOX_API_V7_DISCOVERY.md`
- **Library — Type EBox**: Add Device supports type **EBox**; devices appear in the **EBox Hardware** section with images
- **API reference**: EBox endpoints and fields documented in `docs/API-REFERENCE.md` (cluster `ebox`, node `ebox_id`, `get_ebox_details`, data collection sequence, enhanced features table)
- **Rack diagram tests**: `tests/test_rack_diagram.py` verifies generic 1U/2U fallback when an identifier key is not found in the Library
- **EBox in Physical Rack Layout**: For ebox clusters, diagram uses EBox U height (default 1U); DBox U height documented in Hardware Inventory only and omitted from rack diagram; Hardware Summary note for ebox clusters
- **Switch placement for EBox**: Auto placement tries above ebox hardware then below ebox hardware (same logic as above CBox / below DBox)

### Changed
- **Data extractor**: Hardware inventory accepts list or dict for `cboxes`/`dboxes`/`eboxes` (normalized via `_normalize_boxes_to_dict`); `switch_inventory` may be list or dict; error-path `HardwareInventory` includes all required fields; `_normalize_to_list()` for cnodes/dnodes; `raw_hardware`/`raw_switch_inventory` in report data for fallback
- **Report builder**: `total_devices` includes eboxes; consolidated inventory table shown when `cboxes or dboxes or eboxes or switches`; EBox rows in inventory table; title page and overview show hardware block from cboxes/dboxes/switches when cnodes/dnodes empty; `_ensure_hardware_inventory()` builds from raw when missing; Physical Rack Layout only includes racks present in VMS (excludes "Unknown"); content-based column widths for Hardware Inventory table
- **API handler**: `_normalize_list_response()` handles list, paginated `results`, dict-of-items, and single resource; used for cnodes, dnodes, cboxes, dboxes, eboxes
- **Rack diagram**: EBox drawing (1U default); `_gather_device_boundaries(eboxes=)`; switch placement above/below ebox; `generate_rack_diagram(eboxes=)`
- **Export script**: `scripts/export_swagger.py` probes `GET /api/v7/eboxes/` in the v7 endpoint list

### Fixed
- **Report missing sections**: API list/dict response normalization and raw fallback so title page, Hardware Overview, Hardware Inventory, rack layout, switch config, port mapping, and diagram populate when API returns alternate shapes or extractor returns empty
- **Unknown rack in diagram**: Physical Rack Layout only includes racks that exist in VMS (`data.racks`); "Unknown" rack excluded when not in VMS
- **Hardware Inventory column widths**: Content-based column widths (stringWidth) for Rack, Node, Model, Name/Serial Number, Status, Height so columns fit variable value lengths

### Technical Details
- `src/api_handler.py`: `_normalize_list_response()`, list/dict/single-object handling for hardware endpoints
- `src/data_extractor.py`: `_normalize_to_list()`, `raw_hardware`/`raw_switch_inventory` in report_data
- `src/report_builder.py`: `_ensure_hardware_inventory()`, `_normalize_boxes_to_dict()`, vms_rack_names filter, ebox grouping and diagram_dboxes=[] for ebox clusters, per_rack_eboxes in auto placement
- `src/rack_diagram.py`: EBox in `_get_device_height_units` (1U), `_gather_device_boundaries(eboxes)`, `_calculate_switch_positions(eboxes=)`, above/below ebox strategies, `generate_rack_diagram(eboxes=)`, ebox device drawing
- `src/brand_compliance.py`: `_content_based_column_widths()` for Hardware Inventory table

### Docs & UI (1.4.2 session)
- **Documentation in-app**: Internal `.md` links in doc content are rewritten to `/docs#<doc_id>` so navigation stays in-app; `_build_doc_link_map()`, `_rewrite_doc_links_in_html()` in `app.py`; docs page hashchange and click handlers for in-app doc navigation
- **Docs layout**: Content area constrained to avoid horizontal scroll; Swagger 500 hint and "Open (v7)" link added
- **Port mapping**: Partial clush output accepted; multi-CNode fallback in `app.py` and `main.py`; partial-flag/reason surfaced in report when mapping is incomplete
- **Hardware Inventory Model column**: Comma and trailing NIC description stripped; for `dell_turin_cbox`, display model includes ` / <CNode serial>` (serial from `serial_number`/`sn` in data_extractor and report_builder)
- **Tests**: `TestDocsRoutes` in `tests/test_app.py` — docs page 200, content 200/404, internal link rewrite to `/docs#installation`

## [1.4.1] - 2026-03-05

### Added
- **Hardware Device Library**: New Library page (`/library`) with categorized tables (CBox, DBox, Switch, EBox with Support Pending), user-defined device upload, image preview, and persistent JSON storage
- **Hardware Image Refresh**: 20 bezel images extracted, cropped edge-to-edge, and added for CBoxes (Dell Turin, SMC Turin, HPE/Dell IceLake, HPE Genoa), DBoxes (Ceres V2, Maverick), and Switches (Arista 7050 series, SN5600, MSN2700, MSN4600)
- **Partial Key Matching**: Device lookup in rack/network diagrams now sorts keys longest-first to prevent `msn4600` from incorrectly matching before `msn4600c`
- **Job Cancellation**: Cancel button on the Generate page with `/generate/cancel` endpoint; 8 cancellation checkpoints in the report pipeline using `threading.Event` for graceful abort
- **Exit Button**: Navbar Exit button with confirmation prompt; graceful server shutdown via stored `werkzeug` server reference
- **Favicon & App Icon**: White VAST logo as browser favicon; blue VAST logo as `.icns`/`.ico` for macOS `.app` bundle and DMG installer
- **macOS Launcher**: `Start Reporter.command` double-click launcher in project root
- **Port Mapping Logging**: Specific error messages when SSH port mapping fails (missing switch IPs, CNode IPs, SSH errors) instead of silent failure

### Changed
- **Threaded Server**: `make_server` now runs with `threaded=True` to allow concurrent SSE log stream and status polling, fixing UI hang after report completion
- **Status Polling**: Added `Cache-Control: no-store` headers and `?_t=<timestamp>` cache-buster to `/generate/status` to prevent stale browser caching
- **Library Table Sections**: Device definitions organized into CBox, DBox, Switch, and EBox categories with section headers and pending-support badges
- **Footer Copyright**: Updated to `© 2026 VAST Data`
- **Height Field**: Removed spinner arrows from Manual Switch Placement U-position input
- **Build Script**: Fixed `build-mac.sh` grep for macOS compatibility; `.spec` updated to bundle `device_library.json`, `cluster_profiles.json`, and exclude large source composite image
- **Launcher Test**: Fixed `test_run_gui_starts_flask` to mock `make_server` instead of deprecated `flask_app.run()`

### Fixed
- **Rack Diagram Images**: Reverted from custom `_StretchedImage` widget to native `GraphicsImage` shape, fixing invisible hardware images in rack diagrams
- **Image Padding**: Auto-cropped transparent/white borders from 6 hardware images to achieve edge-to-edge rack slot rendering
- **Report Hang**: Enabled multi-threaded werkzeug server to prevent SSE stream from blocking status polling
- **Shutdown Crash**: Replaced `os._exit(0)` with graceful `server.shutdown()` via background thread to prevent abrupt process termination
- **WeasyPrint Cleanup**: Removed dead WeasyPrint/Cairo imports from `report_builder.py` and `requirements-dev.txt`

### Technical Details
- `src/app.py`: Added `/library`, `/generate/cancel`, `/shutdown` routes; `JOB_CANCEL` threading.Event; `_SERVER` config key for graceful shutdown; port mapping error logging
- `src/rack_diagram.py`: Updated `image_map`, `one_u_models`, `two_u_models`; longest-first partial key matching in `_get_hardware_image_path()` and `_get_device_height_units()`
- `src/network_diagram.py`: Longest-first partial key matching in `load_hardware_image()`
- `src/main.py`: `threading` and `webbrowser` moved to module-level imports; `flask_app.config["_SERVER"] = server`
- `frontend/templates/base.html`: Favicon link, apple-touch-icon, Exit button in navbar
- `frontend/templates/library.html`: 4-section device table with Jinja2 `selectattr` filtering
- `frontend/static/css/app.css`: `.btn-exit`, `.btn-cancel`, `.lib-section-header`, `.lib-badge-pending`, spinner removal for `#uPositionInput`
- `frontend/static/js/app.js`: Exit button handler with confirmation; Cancel button handler; cache-busting on status fetch
- `packaging/icons/icon.icns`, `icon.ico`: Generated from VAST-Data-Icon-Blue.png
- `packaging/vast-reporter.spec`: Bundled device_library.json, cluster_profiles.json; per-file hardware image inclusion; NSAppTransportSecurity plist entry
- Tests: 214 passed (fixed hanging `test_run_gui_starts_flask`)

## [1.4.0] - 2026-03-04

### Added
- **Web UI**: Browser-based GUI with dashboard, report generation form, live progress streaming, report browser, and YAML configuration editor
- **Self-Contained Packaging**: PyInstaller-based builds for macOS (.app/.dmg) and Windows (.exe/.zip) — no Python installation required
- **SSE Log Streaming**: Real-time log output in the browser during report generation via Server-Sent Events
- **Cross-Platform SSH**: New `ssh_adapter.py` using paramiko (Windows) and pexpect (macOS/Linux) for port mapping on all platforms
- **GitHub Actions CI/CD**: Automated cross-platform builds triggered on version tags, with artifacts uploaded to GitHub Releases
- **Development Dependency Split**: `requirements-dev.txt` separates test/lint/optional dependencies from bundled runtime
- **Auto Switch Placement**: Cascading fallback logic (center → above CBoxes → below DBoxes) with per-rack attempts in alpha-numeric order
- **Manual Switch Placement**: UI-driven rack/switch discovery via `/api/discover`, drop-down selection of rack and switch, U-height entry, saved placements table with delete capability
- **Cluster Profiles**: Save, load, and delete cluster connection profiles (IP, credentials, settings) via `cluster_profiles.json`
- **Report File Filtering**: Reports page now lists only `vast_asbuilt_report_*.pdf` and `vast_data_*.json` files
- **Folder Browse API**: Server-side `/api/browse` endpoint for UI-based directory picker
- **VAST Admin UI Theme**: Dark theme with CSS variables matching VAST Admin UI color scheme, custom select dropdowns, toggle switches, and SVG file-type icons
- **Confluence Docs Sync**: 26 Confluence design/requirements pages downloaded into `docs/confluence/` for offline reference

### Changed
- **Launcher**: `main.py` now defaults to GUI mode (web UI); use `--cli` flag or `--cluster` argument for command-line mode
- **Dependencies**: WeasyPrint and Cairo moved to dev-only (ReportLab is the sole production PDF engine); added Flask, paramiko
- **Packaging**: `.gitignore` updated for PyInstaller artifacts; `packaging/` directory added with spec file and build scripts
- **UI Redesign**: Dashboard, Generate, and Reports pages updated with VAST-branded dark theme, icon-based actions, centered table headings, right-justified action columns
- **Output Directory**: Simplified to single default directory model with browse/set functionality; removed multi-directory complexity
- **Watermark**: Adjusted transparency to balance visibility with readability
- **Report Margins**: Centered content with even left/right borders
- **Progress Tile**: Fixed-height scrollable log panel; resized to 60% width for better balance
- **Cursor Rules**: All 11 `.mdc` rules updated to match current codebase (method names, config keys, import paths, version locations, web UI layer)
- **Version**: Aligned `src/__init__.py` to 1.4.0

### Fixed
- **Switch Placement Limits**: Auto placement now respects discovered switch count per rack instead of duplicating
- **Hardware Inventory Rack Column**: Switches show the rack name they are placed in (auto or manual)
- **UnboundLocalError in report_builder**: Hardware collection variables (`cboxes`, `cnodes`, etc.) now assigned before conditional block
- **Download/View Buttons**: Fixed "Not Found" error when using custom output directories
- **Config Reset**: Fixed "Configuration file not found" error on Reset to Template
- **Report File Browsing**: Resolved `PermissionError` from recursive directory scans in large directories
- **Test Suite**: All 169 tests passing (fixed 14 stale tests in data_extractor, report_builder, and main)

### Technical Details
- `src/app.py`: Flask application with routes for dashboard, generate, config, reports, SSE stream, `/api/discover`, `/api/browse`, `/profiles`
- `src/rack_diagram.py`: Refactored into `_gather_device_boundaries`, `_try_center_placement`, `_try_above_placement`, `_try_below_placement` with cascading orchestration
- `src/report_builder.py`: Manual switch placement support via `manual_switch_placements` data key; per-rack switch limiting for auto mode
- `src/utils/logger.py`: Added `SSELogHandler`, `get_sse_queue()`, `enable_sse_logging()`
- `src/utils/ssh_adapter.py`: `run_ssh_command()` and `run_interactive_ssh()` with platform detection
- `frontend/`: Jinja2 templates (base, dashboard, generate, config, reports) with VAST-branded CSS and vanilla JS
- `frontend/static/css/app.css`: Dark theme with CSS variables, toggle switches, icon buttons, file-type SVG icons
- `frontend/static/js/app.js`: Discovery API integration, manual placement UI, profile management, defensive DOM handling
- `packaging/vast-reporter.spec`: PyInstaller spec with hidden imports, data files, and macOS .app bundle
- `.github/workflows/build-release.yml`: Matrix build (macOS + Windows), test gate, GitHub release creation
- `docs/confluence/`: 26 Markdown files synced from Confluence page hierarchy

## [1.3.0] - 2025-11-12

### Added
- **Installation Script Documentation**: Enhanced installation scripts now document enhanced features during dependency installation
- **Port Mapping Usage Examples**: Added port mapping collection examples to both Mac and Windows installation scripts
- **Enhanced Features Verification**: Installation scripts now verify and confirm installation of enhanced feature dependencies

### Changed
- **Installation Process**: Improved user experience with clear messaging about enhanced features being installed
- **Documentation**: Updated installation scripts to include port mapping usage examples

### Technical Details
- Updated `docs/deployment/install-mac.sh`: Added enhanced features documentation and port mapping examples
- Updated `docs/deployment/install-windows.ps1`: Added enhanced features documentation and port mapping examples

## [1.2.0] - 2025-11-11

### Added
- **Hardware Inventory Node Column**: Replaced ID column with "Node" column showing programmatically generated CNode/DNode names
- **One Row Per Node**: Each CNode and DNode now appears on its own row for detailed tracking
- **Multiple Nodes Per Box Support**: CBoxes and DBoxes with multiple nodes display each node on a separate row with the same Name/Serial Number
- **Port Mapping Collection**: Enhanced port mapping collection via SSH with `--enable-port-mapping` flag
- **Port Mapping Credentials**: Support for switch and node SSH credentials via command-line arguments
- **Network Topology with Connections**: Network diagram now includes port mapping connections when available

### Changed
- **Column Renaming**:
  - "CNode/DNode" → "Node" (more concise)
  - "Position" → "Height" (clearer terminology)
- **Column Width Optimization**:
  - Model column: Increased from 30% to 40% for better readability
  - Rack column: Decreased from 10% to 8%
  - Node column: Decreased from 18% to 12%
  - Height column: Decreased from 10% to 8%
- **Node Name Source**: Now uses programmatically generated `name` field (e.g., `cnode-3-10`, `dnode-3-112`) instead of customer-assigned hostnames
- **Data Collection**: Enhanced CNode and DNode name extraction from API
- **DBox Association**: Improved DNode to DBox association with `dbox_id` field

### Fixed
- **Missing Name Field**: Fixed data extractor to include `name` field in processed hardware inventory data
- **Missing DBox ID**: Fixed DNode data structure to include `dbox_id` for proper DBox association
- **Dataclass Field Order**: Fixed `VastHardwareInfo` dataclass field ordering to resolve Python dataclass initialization errors

### Technical Details
- Updated `src/data_extractor.py`: Added `name` and `dbox_id` fields to `_process_hardware_node` method
- Updated `src/api_handler.py`: Added `hostname` field to `VastHardwareInfo` dataclass and hardware data structures
- Updated `src/report_builder.py`: Modified `_create_consolidated_inventory_table` to create one row per node
- Updated `src/brand_compliance.py`: Adjusted column width ratios for Hardware Inventory table

## [1.1.0] - 2025-10-17

### Added
- Initial production release
- Comprehensive report generation
- Rack positioning support
- PSNT tracking
- Network topology diagrams

## [1.0.0] - 2025-09-27

### Added
- Initial release
- Basic report generation
- API integration
- PDF and JSON output formats

