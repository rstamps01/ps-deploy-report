# RPT-LAYOUT-1 — Tasks and evidence

| # | Task | Status |
| --- | --- | --- |
| 1 | `src/utils/pdf_layout.py`: `VastWrappedTable`, `make_table`, token breaking, adaptive side padding, short-word column floor, `bind_titles_to_content` | Done |
| 2 | `src/utils/health_detail_groups.py`: functional-area groups + Other Check Details | Done |
| 3 | `report_builder.py`: data tables via `make_table`, health group rendering, `_finalize_story` title binding | Done |
| 4 | `brand_compliance.py`: wrapped tables; flat titled tables and continuous hardware tables | Done |
| 5 | Temporary `report.table_layout: wrapped / legacy` toggle (all report paths) for side-by-side review | Done, then removed |
| 6 | Tests: `test_pdf_layout.py`, `test_health_detail_groups.py`, `test_report_table_layout.py`; HCF-6 PDF tests moved to the grouped layout | Done |
| 7 | Docs: `README.md`, `CHANGELOG.md`, `TODO-ROADMAP.md` | Done |
| 8 | User review of the rendered 43-EBox report | Approved 2026-10-16 |
| 9 | Remove `legacy`, the HCF-6 PDF sub-table code, and the toggle | Done 2026-10-16 |

## Evidence (43-EBox report, `--from-json` replay of the 2026-10-15 run)

| Layout | Pages | Pages with text crossing a cell border | Short words broken mid-word |
| --- | --- | --- | --- |
| `legacy` | 33 | 13 | — (text overflows instead) |
| `wrapped` | 37 | 0 | 0 |

Quality gate: black, flake8, mypy (CI flags) clean; unit suite passes with coverage above the 60 % floor.
