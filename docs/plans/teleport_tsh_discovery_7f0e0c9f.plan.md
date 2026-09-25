---
name: Teleport tsh discovery
overview: Make Teleport Mode robust for packaged apps by auto-discovering the tsh binary (A), augmenting PATH at startup (B), adding a Teleport Settings UI with a status pill + discovery button and persistence (C), then documenting Teleport Mode (D).
todos:
  - id: discover-tsh
    content: Add discover_tsh() to teleport_tunnel.py and use it in TeleportTunnel.__init__/preflight with improved error message (A)
    status: completed
  - id: augment-path
    content: Add augment_process_path() in main.py and call it early in main() to prepend well-known bin dirs (B)
    status: completed
  - id: api-endpoints
    content: Add GET /api/teleport/status (read-only) and POST /api/teleport/discover (persists to config.yaml) in app.py (C)
    status: completed
  - id: adv-config-ui
    content: "Add Teleport Settings section to advanced_config.html: tsh path field (data-key teleport.tsh_path), status pill, Run Discovery button + JS (C)"
    status: completed
  - id: reporter-pill
    content: Add identical status pill above the Teleport Mode Beta Feature badge in reporter.html and fetch status on load (C)
    status: completed
  - id: pill-css-config
    content: Add shared .tsh-pill CSS and ensure config.yaml.template has a documented teleport block with tsh_path (C)
    status: completed
  - id: tests
    content: Add unit tests for discover_tsh and the two teleport API endpoints; run full quality gate (A/B/C)
    status: completed
  - id: docs
    content: "After verification: write docs/TELEPORT-MODE.md, register in _DOC_REGISTRY, update ADVANCED-OPERATIONS/CHANGELOG/README/roadmap, bump version (D)"
    status: completed
isProject: false
---

# Robust Teleport `tsh` Discovery + UI + Docs

Fixes the packaged-app failure "Teleport CLI 'tsh' not found on PATH" (GUI apps launched from Finder/Explorer get a restricted `PATH`) and gives operators a self-service way to locate/validate `tsh`.

## Assumptions (chosen defaults, not blocking)

- `teleport.tsh_path` stays a single machine-level setting in `config/config.yaml` (applies to all Teleport profiles), which is the correct scope for a CLI tool path. "Saved for future profiles" = persisted globally.
- Version bump is a MINOR feature release: `1.5.8` -> `1.6.0` (per `release-packaging-12.mdc`). Can be `1.5.9` if you prefer treating it as a fix.
- D adds a dedicated `docs/TELEPORT-MODE.md` registered in the in-app Docs viewer.

## A. Robust `tsh` auto-discovery

File: [src/utils/teleport_tunnel.py](src/utils/teleport_tunnel.py)

- Add module fn `discover_tsh(explicit: Optional[str] = None) -> Optional[str]`:
  1. If `explicit` set: accept if `shutil.which(explicit)` resolves or it's an executable file; return absolute path.
  2. `shutil.which("tsh")` (benefits from B's augmented PATH).
  3. Scan well-known locations:
     - macOS: `/usr/local/bin/tsh`, `/opt/homebrew/bin/tsh`, `/opt/teleport/bin/tsh`, `~/.local/bin/tsh`
     - Windows: `%ProgramFiles%\\Teleport\\tsh.exe`, `%LOCALAPPDATA%\\Programs\\teleport\\tsh.exe`, `%USERPROFILE%\\scoop\\shims\\tsh.exe`
     - Linux (dev): `/usr/bin/tsh`, `/usr/local/bin/tsh`
  4. Return `None` if nothing is executable.
- In `TeleportTunnel.__init__` (line ~129): when `tsh_path` is unset/`"tsh"`, set `self.tsh_path = discover_tsh() or "tsh"` so bare invocations still self-heal.
- In `preflight()` (line ~265): keep the `shutil.which` guard but re-run `discover_tsh(self.tsh_path)` first; on failure, improve the error to point at "Advanced Configuration -> Teleport Settings -> Run Discovery."
- `options_from_config()` (line ~57) unchanged (explicit config `tsh_path` still wins).

## B. Augment PATH at startup

File: [src/main.py](src/main.py)

- Add helper `augment_process_path()` mirroring the existing darwin DYLD block (lines 37-42): prepend the same well-known bin dirs (macOS `/usr/local/bin`, `/opt/homebrew/bin`; Windows Teleport install dirs; `~/.local/bin`) to `os.environ["PATH"]` if absent. This also helps `sshpass`/`ssh` resolution in the packaged app.
- Call it once near the top of `main()` (line ~1174), before GUI/CLI routing, so the Flask process and all subprocesses inherit it.

## C. Teleport Settings UI + status pill + persistence

Backend — new endpoints in [src/app.py](src/app.py) (near the `/config/json` routes, ~1459):

- `GET /api/teleport/status` (read-only): returns `{installed: bool, tsh_path: str, source: "config"|"auto"|"none"}`. Resolves via config `teleport.tsh_path` then `discover_tsh()`; does NOT write.
- `POST /api/teleport/discover` (persists): optional body `{tsh_path: "<custom>"}`. Runs `discover_tsh(custom)`; if found, writes `teleport.tsh_path` into `config.yaml` via the existing `_load_yaml`/`_write_config` helpers and returns `{installed, tsh_path, message}`; if not found, returns `installed:false` with guidance (does not overwrite an existing good value with blank).

Advanced Configuration — [frontend/templates/advanced_config.html](frontend/templates/advanced_config.html):

- Add a new `cfg-section` titled "Teleport Settings" as the LAST section (after Security, line ~458), containing:
  - The status pill badge (green "tsh Installed" / yellow "Install tsh").
  - Editable "tsh Path" field bound with `data-key="teleport.tsh_path"` (auto-persists through the existing deep-merge Save at line ~558). Blank when not installed; populated with the discovered/edited path.
  - A "Run Discovery" button that POSTs to `/api/teleport/discover` (sending the field's current value as the optional custom path), then updates the field + pill from the response.
  - Small info text: edit the path if auto-discovery fails, then Run Discovery to validate.
- Add JS (in the page's existing IIFE): `refreshTeleportStatus()` called from `loadConfig()` init to set the field/pill from `GET /api/teleport/status`, and `runTeleportDiscovery()` for the button.

Reporter page — [frontend/templates/reporter.html](frontend/templates/reporter.html):

- Add an identical pill badge inside the Connection Settings tile, positioned directly ABOVE the existing "Beta Feature" badge on the Teleport Mode option (line ~131-135). Fetch `GET /api/teleport/status` on page load to set green/yellow state.

Shared CSS:

- Add `.tsh-pill`, `.tsh-pill--ok` (green) and `.tsh-pill--warn` (yellow) styles. Put reusable rules in [frontend/templates/base.html](frontend/templates/base.html) (or each template's `<style>`), matching the existing `.beta-badge` pill shape (lines ~792-805 of reporter.html).

Config template — [config/config.yaml.template](config/config.yaml.template): ensure a documented `teleport:` block with `tsh_path: ""` and comments.

## D. Documentation (after A-C verified)

- New `docs/TELEPORT-MODE.md`: prerequisites (install `tsh`, `tsh login`), the new auto-discovery + Teleport Settings workflow, node targeting formats (bare hostname, node ID, `key=value`, comma-AND combos), and troubleshooting (PATH issue, discovery button).
- Register it in `_DOC_REGISTRY` in [src/app.py](src/app.py) (line ~100) and ensure `docs/` is bundled (check `packaging/vast-reporter.spec`).
- Update the Teleport subsection of [docs/ADVANCED-OPERATIONS.md](docs/ADVANCED-OPERATIONS.md), `CHANGELOG.md`, `README.md`, and `docs/TODO-ROADMAP.md`.

## Testing & verification

- Unit: extend `tests/test_teleport_tunnel.py` for `discover_tsh` (explicit valid/invalid, PATH hit, known-location hit via monkeypatched `shutil.which`/`os.path`, None case). Add app tests for `/api/teleport/status` and `/api/teleport/discover` (found + not-found, persistence write).
- Quality gate: `black --check --line-length 120 src/ tests/`, `flake8 src/ tests/`, `mypy src/ --ignore-missing-imports`, `pytest` (use `--timeout` locally), `scripts/check-version-sync.sh`.
- Manual smoke: launch GUI, confirm pill shows correctly with/without `tsh`, edit path + Run Discovery, verify `config.yaml` persists and a Teleport connection preflight passes.
- Release: bump version in all locations, then commit/merge/tag per `release-packaging-12.mdc`.
