"""Wrapped table cells and title binding for the PDF report (RPT-LAYOUT-1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # noqa: E402
from reportlab.platypus import CondPageBreak, KeepTogether, PageBreak, Paragraph, Spacer, Table  # noqa: E402
from reportlab.platypus import TableStyle  # noqa: E402

from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402

from utils.pdf_layout import (  # noqa: E402
    VastWrappedTable,
    apply_word_floor,
    bind_titles_to_content,
    break_long_tokens,
    make_table,
    min_unbroken_width,
)

SERIAL = "S000000X0000001-PLATFORM-RDMA:4200"


def _wrapped(data, widths, style_cmds=()):
    table = VastWrappedTable(data, colWidths=widths)
    table.setStyle(TableStyle(list(style_cmds)))
    table.wrap(sum(widths), 10_000)
    return table


def _cell(table, row, col):
    """Cell content after layout (ReportLab 4 stores flowable cells as tuples)."""
    value = table._cellvalues[row][col]
    return value[0] if isinstance(value, (list, tuple)) and value else value


class TestMakeTable:
    def test_wrapped_layout_returns_wrapped_table(self):
        assert isinstance(make_table([["a"]], "wrapped", colWidths=[50]), VastWrappedTable)

    def test_legacy_layout_returns_plain_table(self):
        table = make_table([["a"]], "legacy", colWidths=[50])
        assert type(table) is Table


class TestVastWrappedTableCells:
    def test_text_cells_become_centered_paragraphs(self):
        table = _wrapped([["Header"], ["value"]], [100])
        for r in range(2):
            assert isinstance(_cell(table, r, 0), Paragraph)
            assert _cell(table, r, 0).style.alignment == TA_CENTER

    def test_cell_keeps_its_font_size_and_colour(self):
        table = _wrapped(
            [["Head"], ["body"]],
            [100],
            [
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 7),
            ],
        )
        head, body = _cell(table, 0, 0), _cell(table, 1, 0)
        assert head.style.textColor == colors.white
        assert head.style.fontName == "Helvetica-Bold"
        assert body.style.fontSize == 7

    def test_long_value_wraps_and_row_grows(self):
        table = _wrapped([["Serial"], [SERIAL]], [60])
        assert table._rowHeights[1] > table._rowHeights[0]
        _, height = _cell(table, 1, 0).wrap(60 - 12, 10_000)
        assert height > _cell(table, 1, 0).style.leading

    def test_existing_left_aligned_paragraph_is_centered(self):
        left = ParagraphStyle("left", parent=getSampleStyleSheet()["Normal"], alignment=TA_LEFT)
        table = _wrapped([[Paragraph("message text", left)]], [120])
        assert _cell(table, 0, 0).style.alignment == TA_CENTER
        assert left.alignment == TA_LEFT

    def test_non_text_flowables_are_left_alone(self):
        spacer = Spacer(10, 10)
        table = _wrapped([[spacer]], [50])
        assert _cell(table, 0, 0) is spacer

    def test_markup_characters_are_escaped(self):
        table = _wrapped([["<none> & more"]], [200])
        assert "&lt;none&gt;" in _cell(table, 0, 0).text

    def test_newlines_become_line_breaks(self):
        table = _wrapped([["line one\nline two"]], [200])
        assert "<br/>" in _cell(table, 0, 0).text

    def test_alignment_forced_to_center_middle(self):
        table = _wrapped([["x"]], [50], [("ALIGN", (0, 0), (-1, -1), "LEFT"), ("VALIGN", (0, 0), (-1, -1), "TOP")])
        cell_style = table._cellStyles[0][0]
        assert cell_style.alignment == "CENTER"
        assert cell_style.valign == "MIDDLE"

    def test_spanned_cell_uses_combined_width(self):
        table = _wrapped([["a", "b"], [SERIAL, ""]], [40, 220], [("SPAN", (0, 1), (1, 1))])
        assert "<br/>" not in _cell(table, 1, 0).text

    def test_split_tables_keep_wrapped_cells(self):
        data = [["Head"]] + [[f"row {i}"] for i in range(60)]
        table = VastWrappedTable(data, colWidths=[100], repeatRows=1)
        parts = table.split(100, 200)
        assert len(parts) == 2
        assert all(isinstance(p, VastWrappedTable) for p in parts)
        assert isinstance(_cell(parts[1], 0, 0), Paragraph)


class TestNarrowColumns:
    def test_short_word_in_narrow_column_shrinks_padding_instead_of_splitting(self):
        # "Unknown" is ~42pt at 10pt Helvetica: fits a 50pt column only without the 12pt side padding.
        table = _wrapped(
            [["Unknown"]], [50], [("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12)]
        )
        assert "<br/>" not in _cell(table, 0, 0).text
        assert table._cellStyles[0][0].leftPadding < 12

    def test_exact_fit_header_is_not_split(self):
        word = stringWidth("Height", "Helvetica-Bold", 10)
        table = _wrapped([["Height"], ["1U"]], [word + 6], [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")])
        assert "<br/>" not in _cell(table, 0, 0).text

    def test_paragraph_cell_padding_shrinks_for_its_word(self):
        style = ParagraphStyle("pill", parent=getSampleStyleSheet()["Normal"], fontSize=9)
        table = _wrapped([[Paragraph("warning", style)]], [stringWidth("warning", "Helvetica", 9) + 6])
        assert table._cellStyles[0][0].leftPadding < 6

    def test_column_narrower_than_a_short_word_is_widened_from_wider_columns(self):
        word = stringWidth("performance", "Helvetica", 10)
        table = _wrapped([["performance", "a long message that can wrap freely"]], [word - 5, 300])
        assert table._argW[0] >= word
        assert abs(sum(table._argW) - (word + 295)) < 1e-6
        assert "<br/>" not in _cell(table, 0, 0).text

    def test_cjk_paragraph_wraps_at_spaces(self):
        cjk = ParagraphStyle("cjk", parent=getSampleStyleSheet()["Normal"], wordWrap="CJK")
        table = _wrapped([[Paragraph("Firmware Consistency", cjk)]], [stringWidth("Consistency", "Helvetica", 10) + 20])
        cell = _cell(table, 0, 0)
        assert cell.style.wordWrap is None
        assert [" ".join(line[1]) for line in cell.blPara.lines] == ["Firmware", "Consistency"]

    def test_padding_kept_when_text_fits(self):
        table = _wrapped([["ok"]], [100], [("LEFTPADDING", (0, 0), (-1, -1), 12)])
        assert table._cellStyles[0][0].leftPadding == 12

    def test_word_floor_unchanged_when_no_violation(self):
        assert apply_word_floor([100, 200, 300], [50, 50, 50]) == [100, 200, 300]

    def test_word_floor_raises_narrow_column_and_keeps_total(self):
        widths = apply_word_floor([30, 270, 200], [45, 60, 60])
        assert widths[0] == 45
        assert abs(sum(widths) - 500) < 1e-6
        assert widths[1] > widths[2] > 60

    def test_word_floor_scales_when_floors_exceed_total(self):
        widths = apply_word_floor([50, 50], [80, 120])
        assert abs(sum(widths) - 100) < 1e-6
        assert widths[0] < widths[1]

    def test_min_unbroken_width_keeps_short_words_and_splits_long_tokens(self):
        unknown = min_unbroken_width("Unknown", "Helvetica", 10)
        assert unknown == stringWidth("Unknown", "Helvetica", 10)
        assert min_unbroken_width(SERIAL, "Helvetica", 10) < stringWidth(SERIAL, "Helvetica", 10) / 2


class TestBreakLongTokens:
    def test_short_text_unchanged(self):
        assert break_long_tokens("ACTIVE", "Helvetica", 9, 100) == "ACTIVE"

    def test_breaks_at_separators(self):
        out = break_long_tokens(SERIAL, "Helvetica", 9, 90)
        pieces = out.split("<br/>")
        assert len(pieces) > 1
        assert "".join(pieces) == SERIAL
        assert all(p[-1] in "-_:/." for p in pieces[:-1])

    def test_hard_splits_segment_without_separators(self):
        out = break_long_tokens("X" * 80, "Helvetica", 9, 60)
        assert out.replace("<br/>", "") == "X" * 80
        assert out.count("<br/>") >= 1

    def test_words_that_fit_are_not_split(self):
        out = break_long_tokens("All 43 CNodes healthy", "Helvetica", 9, 60)
        assert "<br/>" not in out


def _title(text="<b>Section</b>"):
    return Paragraph(text, getSampleStyleSheet()["Normal"])


def _table(rows=5):
    return Table([["H"]] + [[str(i)] for i in range(rows)], colWidths=[100])


class TestBindTitlesToContent:
    def test_title_before_table_gets_conditional_break(self):
        title, spacer, table = _title(), Spacer(1, 4), _table()
        out = bind_titles_to_content([title, spacer, table], 400, 700)
        assert isinstance(out[0], CondPageBreak)
        assert out[1:] == [title, spacer, table]

    def test_break_height_covers_title_header_and_first_rows(self):
        title, table = _title(), _table(10)
        out = bind_titles_to_content([title, table], 400, 700)
        _, title_h = title.wrap(400, 700)
        table.wrap(400, 700)
        assert out[0].height >= title_h + sum(table._rowHeights[:4])

    def test_title_before_paragraph_kept_together(self):
        title, body = _title(), Paragraph("Body text", getSampleStyleSheet()["Normal"])
        out = bind_titles_to_content([title, body], 400, 700)
        assert len(out) == 1 and isinstance(out[0], KeepTogether)

    def test_heading_style_counts_as_title(self):
        heading = Paragraph("Network", getSampleStyleSheet()["Heading1"])
        out = bind_titles_to_content([heading, _table()], 400, 700)
        assert isinstance(out[0], CondPageBreak)

    def test_partially_bold_label_is_not_a_title(self):
        label = Paragraph("<b>Total DNodes:</b> 86", getSampleStyleSheet()["Normal"])
        table = _table()
        assert bind_titles_to_content([label, table], 400, 700) == [label, table]

    def test_no_binding_across_page_break(self):
        title, brk, table = _title(), PageBreak(), _table()
        assert bind_titles_to_content([title, brk, table], 400, 700) == [title, brk, table]

    def test_consecutive_titles_bind_to_same_content(self):
        t1, t2, table = _title("<b>A</b>"), _title("<b>B</b>"), _table()
        out = bind_titles_to_content([t1, t2, table], 400, 700)
        assert isinstance(out[0], CondPageBreak)
        assert out[1:] == [t1, t2, table]

    def test_title_not_bound_to_content_taller_than_page(self):
        title = _title()
        big = Paragraph("word " * 4000, getSampleStyleSheet()["Normal"])
        assert bind_titles_to_content([title, big], 400, 300) == [title, big]

    def test_break_height_capped_at_frame(self):
        out = bind_titles_to_content([_title(), _table(200)], 400, 300)
        assert out[0].height <= 300
