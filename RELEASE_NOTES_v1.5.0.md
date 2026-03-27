# Release Notes — v1.5.0

**Date:** 2026-03-26  
**Branch:** feature/health-check-v2 → develop → main  
**Previous release:** v1.4.7 (2026-03-17)

---

## Executive Summary

v1.5.0 is a major release that introduces the **Reporter page** as the primary user-facing workflow, a complete **One-Shot UI overhaul**, **SSH proxy hop** for field deployments, the **VAST logo progress indicator**, and extensive UI/UX improvements across all pages. This release also includes the health check module, advanced operations framework, and over 100 individual improvements to documentation, testing, and infrastructure.

---

## Highlights

### Reporter Page (New)
The new `/reporter` page replaces Advanced Ops as the primary interface for standard users. It combines switch placement (auto/manual), as-built report generation, pre-validation, and optional health checks into a single streamlined workflow. No `--dev-mode` required.

### SSH Proxy Hop
Switch SSH connections now tunnel through the CNode by default, enabling port mapping and Tier 3 health checks when switches are only reachable from inside the cluster network. A "Proxy through CNode" toggle is available on Generate and Reporter pages, with CLI opt-out via `--no-proxy-jump`.

### NVMe/TCP Ethernet MTU (NET-1)
The `nb_eth_mtu` field is now collected from the VAST API and reported in the PDF Network Configuration table and JSON export alongside `eth_mtu` and `ib_mtu`.

### One-Shot UI Overhaul
The One-Shot mode received a complete visual and functional refresh:
- Pre-Validation converted from button to inline checkbox
- Color-coded operation badges (Net Test, Sys Test, Perf Test, Pull Logs, Pull Config)
- "Download Bundle" hidden until completion
- vperfsanity default unchecked

### VAST Logo Progress Indicator
A custom CSS mask-image fill animation renders the VAST Data logo as a progress indicator, with percentage and stopwatch timer in the center. Replaces the previous SVG ring design.

### Navigation Restructuring
Standard navigation now shows Dashboard, Reporter, Results, Library, and Docs. Legacy pages (Generate, Reports) and developer pages (Advanced Ops, Health Check, Configuration) are in a hamburger menu. "Validation Results" renamed to "Results".

---

## New Features

- **Reporter page** — combined switch placement, report generation, and validation workflow
- **SSH proxy hop** — CNode tunneling for switch SSH in field deployments
- **VAST logo progress** — fill animation with timer and percentage
- **One-Shot orchestration mode** — sequential multi-operation execution with auto-bundling
- **Validation Results page** — 9 operation tabs with cluster profile filtering
- **Operation badges** — color-coded labels on each workflow operation
- **Connection settings tooltips** — info icons with credential guidance on all fields
- **Manual switch placement** — add switches manually when discovery fails
- **Dynamic log tier filtering** — Status/Live/Debug output levels
- **Persistent operation logs** — 1GB capacity with auto-purge
- **Window state persistence** — resume exact UI state after navigation or restart

## Key Fixes

- Rack diagram placeholder Arista switch injection removed
- Manual switch placement data correctly flows to report
- Port mapping activation payload mismatch fixed
- Log tier passthrough on Reporter and Advanced Ops output panes
- CNode/DNode status detection uses correct `state` field
- Network settings API correctly unwraps `response["data"]`
- SSH check timeout with 60s overall limit
- vperfsanity cross-tenant bucket conflict resolved

## Infrastructure

- Coverage threshold raised to 60% (from 47-55% depending on workflow)
- CI and build-release coverage thresholds aligned
- Beta badge removed for production release
- Version strings synchronized across all 6 canonical locations
- Configuration template updated with SSH, health check, and advanced operations settings
- ADVANCED-OPERATIONS.md and POST-INSTALL-VALIDATION.md added to in-app docs viewer and PyInstaller bundle
- Deployment docs updated from v1.4.7 references to v1.5.0

---

## Upgrade Notes

- No breaking changes to CLI or config file format
- New `--no-proxy-jump` CLI flag available (proxy hop is ON by default)
- The Reporter page is accessible without `--dev-mode`; previous Advanced Ops workflows remain available with `--dev-mode`
- Configuration template (`config.yaml.template`) has new sections: `ssh`, `health_check`, `advanced_operations`

---

## Known Limitations

- AO-15 (Advanced Ops hardening) and AO-19 (dynamic log levels, state persistence) — to be completed before final tag
- Coverage target is 60%; roadmap target is 75%+ (TSE-9)
