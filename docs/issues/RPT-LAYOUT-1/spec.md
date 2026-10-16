# RPT-LAYOUT-1 — Wrapped table cells, consolidated health details, titles kept with content

**Status:** Approved and done (2026-10-16). The temporary `report.table_layout: wrapped | legacy` toggle (R4) was removed after approval; the wrapped layout is the only layout.

## Problem

1. Most PDF tables pass plain strings to ReportLab `Table`. Plain strings never wrap (the `WORDWRAP` style only affects `Paragraph` cells), so long values print over neighbouring columns. Worst case: Hardware Inventory and CNode/DNode Management Map (serials of the form `S000000X0000000-PLATFORM-RDMA:4200`, EBox UUIDs). Measured on the 43-EBox report: 13 pages with text crossing cell borders.
2. Under "Detailed Check Results", every health check with `details` gets its own two-column "Field / Value" table: raw keys (`ssd_raid_state`), unformatted numbers (`1530.8358208955226`), list values silently dropped (DNS/NTP, EBoxes missing a rack), and a 15-check cap that hides later checks.
3. Section and table titles can end a page while their table starts on the next page.

## Requirements

### R1 — Wrapped, centered cells (all data tables)

- Every data table cell wraps inside its column; rows grow in height; column widths are unchanged.
- Exception (found during review rendering): when a column is narrower than one short word (≤ 1 inch, such as `Unknown`, `performance` or a bold `Height` header), that column is raised to fit the word and the space comes from columns wider than their own minimum. Tables with no such column keep their widths exactly. A cell whose longest word does not fit inside its padding first shrinks its side padding (down to 2 pt) before any word is broken.
- `CJK` word-wrap on existing `Paragraph` cells (breaks inside words) is replaced by normal wrapping at spaces.
- All cell text is centered horizontally and vertically (including previously left-aligned Message / Description columns).
- Each cell keeps its own font, size and colour from the table style (white-on-colour status cells stay readable).
- Tokens wider than the column (no spaces) break at `-`, `_`, `:`, `/`, `.` first, and mid-token only when a single segment is still too wide.
- Applies to: `brand_compliance` tables (`create_vast_table`, hardware auto-width / pagination) and the `report_builder` data tables (CNode/DNode network config, port mapping, health summary/detail, health detail groups, post-deployment checklist).
- Excluded (layout-only tables): table of contents, rack diagram layout, image grids.
- Hardware tables: the fixed 25-row "(Page X of N)" chunks are replaced by one continuous table whose header row repeats on each page (wrapped rows no longer fit a fixed count).

### R2 — Consolidated health check details

Replace the per-check sub-tables with grouped tables. Each group: heading `Health Check Details — <Group>` plus a one-line caption describing the rows. A group renders only if at least one of its checks is present. No check cap; list values are shown in full (count + wrapped list).

| Group | Columns | Rows (source checks) |
| --- | --- | --- |
| Cluster State & Software | Setting · Reported Value · From Check | Cluster state, cluster enabled (Cluster State); leader state, leader CNode (Leader State); expansion state (Expansion State); license (License); firmware consistency incl. each mismatched version and its nodes (Firmware Consistency) |
| Hardware Components | Component · Total · Inactive · Disabled · Notes | CNodes (VMS host in Notes), DNodes, DBoxes, CBoxes, EBoxes; inactive/disabled names in Notes; a skipped check shows its message in Notes |
| Rack Placement | Item · Value | Racks defined; CBoxes without a rack; DBoxes/EBoxes without a rack (count + full list) |
| Storage & Device Health | Layer · RAID State · Rebuild Progress (%) | SSD, NVRAM, Memory (Cluster RAID Health + RAID Rebuild Progress); then a second table Item · Value: metrics scanned, failed devices, media errors (+ lists) (Device Health) |
| Capacity & Usage | Metric · Current · Threshold | Physical capacity used (Capacity); handle usage (Handle Usage); quotas configured / blocked users (Quotas); snapshots / failed (Snapshots) |
| Network & Connectivity | Item · Value | DNS servers, NTP servers, default gateway (Network Settings); VIP pools "N of M enabled" (VIP Pools); switches registered in VMS with name + IP (Switches in VMS) |
| Data Protection & Services | Item · Value | Replication (Replication); protection policies "N active of M" (Data Protection); Call Home enabled, cloud registered, cloud enabled, log upload, bundle upload, customer (Call Home Status) |
| Alarms & Events | Item · Value, then Severity · Object · Description · Raised (UTC) | Total alarms, unresolved critical/major (Active Alarms); events checked, critical events (Recent Events); full alarm list; critical event list when present |
| *(Performance Baseline — removed 2026-10-15)* | — | No details group; the check keeps its row in Detailed Check Results and its metrics are not listed under Other Check Details |
| Switch Checks (SSH) | Check · Switches · OS · Result | MLAG Status, Switch NTP, Switch Config Readability; raw `stdout` omitted; `stderr` shown (≤200 chars) when present |
| Other Check Details | Check · Item · Value | Any unmapped check or field, with readable labels (snake_case → Title Case) |

Formatting: booleans → Yes / No; `None` → "Not reported"; percentages with one decimal and `%`; lists joined with ", ".

The "Detailed Check Results" table stays as-is (wrapping/centering from R1 applies).

### R3 — Titles stay with their content

- A title (heading-style paragraph or a fully bold short paragraph) never ends a page apart from the content it introduces.
- Title followed by a table: the title moves to the next page unless the title, the table header and the first rows (up to 3) fit on the current page.
- Title followed by other content: kept together with that first flowable.
- Applied once at the end of story assembly so both build passes paginate identically (TOC page numbers stay correct).

### R4 — Restore toggle (removed 2026-10-16 after approval)

- `report.table_layout` in `config.yaml` (`wrapped` default, `legacy` = today's rendering, unchanged code paths). Documented in `config.yaml.template` and `README.md`.
- `legacy` disables R1–R3 entirely.
- Honoured by every report path: web UI, One-Shot, CLI, and `--from-json` replay (the CLI paths previously built the report with defaults only; they now read `report.table_layout`).

## Design

- `src/utils/pdf_layout.py`
  - `VastWrappedTable(Table)`: converts text cells to centered `Paragraph`s on first layout using each cell's computed style and column width (span-aware); re-centers existing `Paragraph` cells; leaves other flowables untouched; forces `ALIGN CENTER` / `VALIGN MIDDLE`.
  - `make_table(data, **kwargs)`: returns `VastWrappedTable` (during review it also returned a plain `Table` for `legacy`).
  - `bind_titles_to_content(story, frame_width, frame_height)`: R3.
- `src/utils/health_detail_groups.py`: pure functions `build_health_detail_groups(results) -> List[DetailGroup]` (title, caption, tables of headers/rows/column weights). No ReportLab import.
- `report_builder.py`: `ReportConfig.table_layout`; health section renders groups in `wrapped`, legacy sub-tables in `legacy`; data tables via `make_table`; binder at end of `_build_report_story`.
- `brand_compliance.py`: `table_layout` attribute (set by the report builder); in `wrapped` mode tables are `VastWrappedTable`, titled tables are returned flat (binder keeps titles with them) and hardware tables flow continuously.

## Verification

- Unit: cell conversion (colour/font kept, centering, token breaking, legacy untouched, spans); binder (title+table, title+paragraph, no binding before page breaks); each group from the 43-EBox health JSON; fallback group; config parsing.
- Render the 43-EBox report in both modes; border-crossing scan reports zero crossings in `wrapped`; before/after page images for review.
