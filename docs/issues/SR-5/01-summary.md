# SR-5 — IB MAC overflows Port Mapping MAC column

**Status:** In progress (TDD red → green on `feature/tp-1-techport-discovery`)
**Reporter:** Ray Stamps (visual review of mammoth report PDF, 2026-04-30)
**Severity:** Visual / report-quality (no data loss)
**Scope:** `src/report_builder.py::_create_vnetmap_topology_tables`
**Stack:** Stacked on TP-1 / TP-2 / SR-1 (commits `7b94453` → `f49aa2b` → `8bba3aa`)

## Symptom

In the **Port Mapping** section of the generated PDF, the **MAC** column
overflows its allocated width on InfiniBand clusters. The 20-byte IB GID
values (e.g. `80:00:01:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:80`,
59 ASCII chars with no whitespace) extend past the column boundary and
visually obscure both the **Interface** column on the left and the **Net**
column on the right. Affected tables:

1. The **Full Topology** table (`_create_vnetmap_topology_tables`, line 3974)
2. Each per-switch table titled `Switch <ID> — subnet {…}, network {…}`
   (`_create_vnetmap_topology_tables`, line 4016)

(See screenshots provided by user, 2026-04-30, three-page mammoth PDF excerpt.)

## Root Cause

`brand_compliance.create_vast_table` builds the table with
`("WORDWRAP", (0, 0), (-1, -1), "CJK")` (`brand_compliance.py:404`). CJK
word-wrap mode breaks long strings only at character boundaries that exist
between CJK glyphs OR at whitespace within ASCII strings. IB MAC strings
contain no whitespace, no break-opportunities — they are a single ~59-char
token.

Ethernet MACs (`xx:xx:xx:xx:xx:xx` = 17 chars) fit comfortably in the
allocated column width (3.5 weight units, ~58 pt at A4) so no wrap is needed.
IB GIDs are ~3.5× wider than the allocated cell, so they overflow.

## Fix

Add a small module-level helper in `src/report_builder.py`:

```python
def _format_mac_cell(mac: str, paragraph_style: ParagraphStyle, group_size: int = 7) -> Any:
    """Wrap long MAC/GID values so they don't overflow narrow table columns.

    Ethernet MACs (≤ group_size colon-separated bytes) pass through as plain
    strings — ReportLab Tables render them without Paragraph overhead. IB MACs
    / GIDs (typically 20 bytes) are wrapped in a Paragraph with explicit
    <br/> breaks every group_size bytes so they wrap cleanly to 2–3 lines
    within the cell.
    """
```

Apply at the two MAC cell sites in `_create_vnetmap_topology_tables`:

- Line 3969: `e.get("mac", "") or ""` → `_format_mac_cell(e.get("mac", ""), mac_style)`
- Line 4009: same substitution in per-switch tables

Add a `mac_style: ParagraphStyle` defined locally in the method (compact font
matching `font_sz - 2`, `wordWrap='LTR'`, `alignment=TA_CENTER`).

No column-weight changes required — wrapping inside the existing column width
is sufficient and preserves the rest of the table layout.

## Acceptance Criteria

1. New unit tests in `tests/test_report_builder.py` (or new file
   `tests/test_report_builder_mac_wrap.py`):
   - 6-byte Ethernet MAC `'00:11:22:33:44:55'` → returns plain `str`.
   - 20-byte IB GID → returns `Paragraph` instance whose XML payload contains
     `<br/>` separators producing 3 chunks of 7 + 7 + 6 bytes.
   - Empty / `None` / non-MAC string → returns empty string or original
     unchanged (no Paragraph wrapping).
2. Quality gate: `black --check`, `flake8`, targeted pytest pass.
3. Live verification on mammoth: re-run the report; visually confirm in the
   PDF that:
   - IB MAC cells wrap to 3 lines inside the MAC column.
   - Interface column to the left and Net column to the right are no longer
     obscured.
4. Ethernet cluster regression check (selab-var-202): MAC cells still render
   on a single line, no layout shift.

## Workaround

None — purely visual; raw data in the JSON export is correct.
