# Release v1.4.2 – EBox, Report Fixes, Docs & UI

**Release Date:** March 2026  
**Target VAST Version:** 5.3+  
**API Version:** v7

## Summary

Release 1.4.2 adds full EBox support (API v7), improves report robustness when the API returns alternate response shapes, and enhances the docs UI and Hardware Inventory display. Pre-release validation: full unit test suite (235 tests), flake8, and Black formatting applied.

---

## Enhancements in 1.4.2

### EBox & API
- **EBox discovery (API v7)**: Full EBox integration — `GET /api/v7/eboxes/`, cluster `ebox` flag, `ebox_id` on CNodes/DNodes; EBox quantity and inventory in report (cover, executive summary, consolidated hardware table).
- **API reference**: EBox endpoints and fields documented in `docs/API-REFERENCE.md`.
- **Library**: Device type EBox; EBox devices in EBox Hardware section with images.
- **Rack diagram**: EBox in Physical Rack Layout (1U default); switch placement above/below ebox; rack diagram tests for generic 1U/2U fallback.

### Report & Data
- **Report missing sections**: API list/dict normalization and raw fallback so title page, Hardware Overview, Hardware Inventory, rack layout, switch config, port mapping, and diagram populate when API returns alternate shapes or extractor returns empty.
- **Unknown rack**: Physical Rack Layout only includes racks present in VMS; "Unknown" rack excluded when not in VMS.
- **Hardware Inventory**: Content-based column widths; Model column — comma and trailing NIC description stripped; for `dell_turin_cbox`, display model includes ` / <CNode serial>` (serial from `serial_number`/`sn`).
- **Port mapping**: Partial clush output accepted; multi-CNode fallback in app and CLI; partial-flag/reason in report when mapping is incomplete.

### Docs & UI
- **Documentation in-app**: Internal `.md` links in doc content rewritten to `/docs#<doc_id>`; docs page hashchange and click handlers for in-app navigation.
- **Docs layout**: Content area constrained (no horizontal scroll); Swagger 500 hint and "Open (v7)" link.
- **Tests**: `TestDocsRoutes` in `tests/test_app.py` — docs page 200, content 200/404, internal link rewrite to `/docs#installation`.

### Technical
- **Data extractor**: `_normalize_to_list()`, `raw_hardware`/`raw_switch_inventory`; hardware/switch inventory accepts list or dict.
- **Report builder**: `_ensure_hardware_inventory()`, `_normalize_boxes_to_dict()`, vms_rack_names filter, ebox grouping; Model column logic for comma strip and dell_turin_cbox + serial.
- **API handler**: `_normalize_list_response()` for list, paginated `results`, dict-of-items, single resource.
- **Rack diagram**: EBox in `_get_device_height_units`, `_gather_device_boundaries(eboxes)`, `_calculate_switch_positions(eboxes=)`.
- **App**: `_build_doc_link_map()`, `_rewrite_doc_links_in_html()`; Black formatting applied to `src/app.py`.

---

## Pre-Release Validation

- **Unit tests**: 235 passed (excluding UI and integration).
- **Lint**: flake8 run (pre-existing findings in other modules; no new issues from 1.4.2 session).
- **Format**: Black `--line-length 120` applied to `src/app.py`.
- **Coverage**: Suite run with `--cov=src`; project-wide line coverage remains below 80% (pre-existing).

---

## Files Touched in 1.4.2 Session

- `CHANGELOG.md`: [1.4.2] entry plus "Docs & UI (1.4.2 session)" subsection.
- `RELEASE_NOTES_v1.4.2.md`: This file.
- `tests/test_app.py`: New `TestDocsRoutes` (4 tests).
- `src/app.py`: Black reformat.
