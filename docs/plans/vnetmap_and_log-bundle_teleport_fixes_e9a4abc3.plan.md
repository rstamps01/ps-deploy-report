---
name: vnetmap and log-bundle teleport fixes
overview: "Fix the two remaining tool defects in the VAST-PI-01 Teleport run: vnetmap is invoked with the wrong switch user (cumulus instead of the pre-validated admin) so the Onyx web-API login is rejected, and VMS Log Bundle (plus vperfsanity) never routes SSH through the Teleport tunnel so it times out dialing the cluster IP directly."
todos:
  - id: vnetmap-user
    content: In vnetmap_workflow._step_generate_export_commands, derive effective switch user from switch_user_by_ip (uniform -> that user, else configured switch_user) and use it in the -u slots (710/713); verify multiple-passwords and candidate-sweep inherit it.
    status: completed
  - id: logbundle-tunnel
    content: In log_bundle_workflow.py add _ssh_host/_ssh_port helpers, call script_runner.set_ssh_port(_ssh_port()) on creation, and replace cluster_ip host reads with _ssh_host().
    status: completed
  - id: vperfsanity-tunnel
    content: Apply the same tunnel-routing fix to vperfsanity_workflow.py (helpers, _ssh_host() host, port threaded into run_ssh_command).
    status: completed
  - id: tests-quality
    content: Add regression tests for vnetmap -u propagation and log_bundle/vperfsanity ssh_host/port; run black, flake8, mypy, pytest; update CHANGELOG.
    status: completed
isProject: false
---

## Root causes (confirmed in code)

### 1. vnetmap `-u cumulus` vs Onyx web API needing `admin`

`mlnx_switch_api.py` authenticates to the switch **web API** (`POST /admin/launch?...template=login` with `f_user_id`/`f_password`), not SSH. These Onyx switches only accept `admin` for that login. Pre-validation already discovered this (`combo 4/4 admin/admin` wins; combos 1-3 `cumulus` fail) and stored it in `_switch_user_by_ip`, which is passed to workflows as `switch_user_by_ip` (282:288:src/oneshot_runner.py). But `vnetmap_workflow` builds the command with the static `switch_user` (default `cumulus`) at 569:713:src/workflows/vnetmap_workflow.py, so every web-API login is `cumulus/...` and is rejected -> "Unable to determine suitable switch API" -> "Please add switches" / "Failed to connect to switch".

### 2. Log Bundle / vperfsanity ignore the Teleport tunnel

`log_bundle_workflow.py` dials `cluster_ip` (<ip>) directly and never calls `set_ssh_port()` (109:113:src/workflows/log_bundle_workflow.py). In Teleport mode the laptop can only reach the node via the forwarded `127.0.0.1:<port>` endpoint, so the direct dial times out ("SSH command timed out after 10s"). Only `vnetmap_workflow` currently calls `set_ssh_port()` (187). `vperfsanity_workflow.py` has the same latent bug (uses `cluster_ip` throughout).

---

## Fix 1 - Propagate the discovered switch user into vnetmap `-u`

In [src/workflows/vnetmap_workflow.py](src/workflows/vnetmap_workflow.py), `_step_generate_export_commands`:

- After reading `switch_user` (569) and `switch_password_by_ip` (594-597), compute an effective user from the pre-validated map:
  - Read `raw_user_by_ip = self._credentials.get("switch_user_by_ip") or {}`.
  - If all non-empty values are identical, use that single user (e.g. `admin`); otherwise keep the configured `switch_user`. vnetmap.py accepts only one `-u`, so a uniform discovered user is the correct signal.
  - Store it as `self._step_data["switch_user"]` and use it in the `-u {switch_user}` slots at 710 and 713.
- Because `_build_multiple_passwords_cmd` preserves `-u` from the base command (it only strips `-p` and appends `--multiple-passwords`) and `_rebuild_vnetmap_cmd` only swaps `-p`, fixing the base-command `-u` automatically corrects both the multiple-passwords run and the candidate-sweep retries.

Caveat to keep: SSH success does not guarantee web-API success. If the switch web API is disabled or uses different credentials (as seen previously on ZOOMNFS01), vnetmap will still fail; the existing "Onyx switch web API unavailable" hint (already emitted) remains the correct guidance for that case.

## Fix 2 - Route Log Bundle (and vperfsanity) through the tunnel

In [src/workflows/log_bundle_workflow.py](src/workflows/log_bundle_workflow.py):

- Add `_ssh_host()` / `_ssh_port()` helpers mirroring 109:120:src/workflows/support_tool_workflow.py (`ssh_host`/`ssh_port` creds, fallback to `cluster_ip`/22).
- When lazily creating `self._script_runner` (97), call `self._script_runner.set_ssh_port(self._ssh_port())` (as vnetmap does at 187).
- Replace every `host = self._credentials.get("cluster_ip")` (109, 188, 237) with `host = self._ssh_host()` so all `check_prerequisites`/`execute_remote`/`download_from_remote` calls target the forwarded endpoint.

Apply the same three changes to [src/workflows/vperfsanity_workflow.py](src/workflows/vperfsanity_workflow.py) (all `cluster_ip` reads at 118/152/264/372/429/471/504 -> `_ssh_host()`, add helpers, and thread the port into its `run_ssh_command(..., port=self._ssh_port())` calls) for parity, since it shares the identical defect.

## Validation

- Unit tests:
  - vnetmap: assert that when `switch_user_by_ip` maps all switches to `admin`, the generated command and the multiple-passwords/candidate-sweep commands use `-u admin`; when the map is empty it falls back to the configured `switch_user`.
  - log_bundle/vperfsanity: assert `_ssh_host()` returns the tunnel `ssh_host` when set and `cluster_ip` otherwise, and that `set_ssh_port` is called with `ssh_port`.
- Quality gates: `black --line-length 120`, `flake8 src/ tests/`, `mypy src/ --ignore-missing-imports`, and `python3 -m pytest tests/ -q` (with the existing `--timeout` guard).
- Update `CHANGELOG.md` under the unreleased/`[1.6.0]` entry (vnetmap switch-user propagation; log_bundle + vperfsanity Teleport SSH routing).

## Note on live testing

These edits only take effect after the dev server is restarted. The current run shows a mix of fixed and unfixed behavior only because those two workflows were never patched - not staleness. After applying, relaunch `python3 src/main.py --gui --dev-mode` from your terminal and re-run the one-shot; vnetmap should attempt `-u admin` and Log Bundle should connect via `127.0.0.1:<tunnel-port>`.
