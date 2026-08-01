# VAST As-Built Report Generator — v1.6.0

**Focus:** Teleport connection-mode hardening (`tsh` auto-discovery + settings UI), cross-cluster vnetmap safety, and switch-identity/credential correctness for Onyx/MLNX-OS fabrics.

> This release folds in the two `[Unreleased]` fixes staged on `develop` (vnetmap Onyx `admin` user, and Teleport tunnel routing for VMS Log Bundle + vperfsanity SSH).

## Added

- **Teleport `tsh` auto-discovery.** The app locates the Teleport CLI on `PATH` and in well-known install locations (macOS/Windows/Linux), so packaged builds launched from Finder/Explorer no longer fail with "tsh not found on PATH".
- **Teleport Settings** in Advanced Configuration: view the discovered `tsh` path, enter a custom path, and **Run Discovery** to validate and persist it (`teleport.tsh_path`).
- **tsh status pill** (green "tsh Installed" / yellow "Install tsh") on the Reporter Connection Settings tile and in Teleport Settings.
- New API endpoints `GET /api/teleport/status` (read-only) and `POST /api/teleport/discover` (persists to `config.yaml`).
- New docs guide `docs/TELEPORT-MODE.md`, registered in the in-app Docs viewer.

## Changed

- Startup augments `PATH` with common bin directories (e.g. `/usr/local/bin`, `/opt/homebrew/bin`, the Windows Teleport dir) to aid resolution of `tsh`, `sshpass`, and `ssh` in packaged apps.
- Teleport preflight re-resolves `tsh` via discovery and emits an actionable error pointing to Advanced Configuration → Teleport Settings.

## Fixed

- **Cross-cluster vnetmap contamination via a shared Tech Port IP.** When two clusters were reported through the same Tech Port, a failed vnetmap run could be populated with the previous cluster's saved topology (identical `vnetmap_output_<ip>_*.txt` filenames). The finder is now authoritative per cluster (searches only that cluster's `clusters/<key>/output/scripts`), plus a defense-in-depth identity guard rejects any parsed vnetmap whose node hostnames/IPs do not overlap the cluster being reported.
- **vnetmap authenticated to Onyx switches as the wrong user.** Onyx/MLNX-OS switches reject the Cumulus default `cumulus` on their HTTP/HTTPS web API and require `admin`. The workflow now propagates the discovered per-IP switch user (`switch_user_by_ip`) into the generated `-u` flag for both the multi-password run and candidate-sweep retries, falling back to the configured user when the discovered map is empty/non-uniform.
- **Teleport mode: all SSH-based workflows route through the tunnel.** Network Config, Support Tools, VMS Log Bundle, and vperfsanity previously dialed the real cluster IP directly and timed out ("SSH command timed out") under Teleport. They now resolve the SSH target from `ssh_host`/`ssh_port` (falling back to the cluster IP on port 22 for Tech Port/direct modes) and thread the forwarded port into every remote SSH/SCP call and tool deployment. vperfsanity still uses the real VMS IP for on-CNode API calls.
- **Onyx switch health checks authenticated as the wrong user.** The winning per-IP `(user, password)` captured during probing is now propagated end-to-end, so MLAG/NTP/config-readability checks connect as `admin` where required.
- **Garbled switch-config backup filenames.** Interactive SSH output is stripped of ANSI/terminal control sequences centrally, and backup filenames are built from a sanitized hostname slug (falling back to the switch IP), eliminating names like `switch_^[[?1h^[=_….txt`.
- **Spurious `/api/vnetmap-status` error** from credential redaction rewriting a `%s` placeholder — the message no longer uses a `key=` token and the SSE handler absorbs formatting errors.
- **Blank cluster version in the validation bundle `SUMMARY.md`** — now uses the version detected from the live cluster during identity resolution.
- **Clearer messaging for Onyx vnetmap web-API failures** — a single plain-language hint (verify the web API is enabled and the switch's *web* login credentials) instead of a raw traceback.

## Artifacts

- `VAST-Reporter-v1.6.0-mac-arm64.dmg` (Apple Silicon)
- `VAST-Reporter-v1.6.0-mac-x64.dmg` (Intel)
- `VAST-Reporter-v1.6.0-win.zip` (Windows)

Built by `.github/workflows/build-release.yml` from the `v1.6.0` tagged commit after the blocking quality-gate + test jobs pass.
