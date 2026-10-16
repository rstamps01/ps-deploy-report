"""PDF layout helpers for report tables (RPT-LAYOUT-1).

- ``VastWrappedTable``: data table whose text cells wrap inside their column and are
  centered horizontally and vertically, keeping each cell's own font, size and colour.
- ``bind_titles_to_content``: keeps table/section titles on the same page as the
  content they introduce.

ReportLab only wraps ``Paragraph`` cells; plain strings in a ``Table`` overflow their
column regardless of the ``WORDWRAP`` style, which is why cells are converted here.
"""

import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple
from xml.sax.saxutils import escape

from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.platypus import CondPageBreak, KeepTogether, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.doctemplate import ActionFlowable
from reportlab.platypus.flowables import UseUpSpace

MIN_SIDE_PADDING = 2.0

_SEPARATORS = "-_:/."
_SEGMENT_RE = re.compile(r"[^-_:/.]*[-_:/.]|[^-_:/.]+$")
_CENTER_MIDDLE = TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE")])


def _split_token(token: str, font_name: str, font_size: float, max_width: float) -> List[str]:
    """Split one over-wide token into pieces that fit, preferring separator boundaries."""

    def fits(text: str) -> bool:
        return bool(stringWidth(text, font_name, font_size) <= max_width)

    pieces: List[str] = []
    current = ""
    for segment in _SEGMENT_RE.findall(token):
        if not segment:
            continue
        if fits(current + segment):
            current += segment
            continue
        if current:
            pieces.append(current)
            current = ""
        if fits(segment):
            current = segment
            continue
        for ch in segment:
            if current and not fits(current + ch):
                pieces.append(current)
                current = ""
            current += ch
    if current:
        pieces.append(current)
    return pieces


def break_long_tokens(text: str, font_name: str, font_size: float, max_width: float) -> str:
    """Escape ``text`` for a Paragraph and insert line breaks inside tokens wider than ``max_width``.

    Args:
        text: Plain cell text (one line).
        font_name: Registered font used to measure the text.
        font_size: Font size in points.
        max_width: Usable cell width in points.

    Returns:
        str: Paragraph markup; tokens that fit are unchanged.
    """
    words = []
    for word in text.split(" "):
        if not word or max_width <= 0 or stringWidth(word, font_name, font_size) <= max_width:
            words.append(escape(word))
        else:
            words.append("<br/>".join(escape(p) for p in _split_token(word, font_name, font_size, max_width)))
    return " ".join(words)


def widest_word(text: str, font_name: str, font_size: float) -> float:
    """Width in points of the widest whitespace-separated word in ``text``."""
    return max((stringWidth(w, font_name, font_size) for w in text.split()), default=0.0)


def min_unbroken_width(text: str, font_name: str, font_size: float, keep_whole: float = 72.0) -> float:
    """Narrowest width that renders ``text`` without breaking inside a short word.

    Words up to ``keep_whole`` points stay whole; longer tokens (serials, UUIDs) may
    break at ``-_:/.`` separators, so only their widest segment counts.
    """
    widest = 0.0
    for word in text.split():
        width = stringWidth(word, font_name, font_size)
        if width > keep_whole:
            width = max(stringWidth(s, font_name, font_size) for s in _SEGMENT_RE.findall(word) if s)
        widest = max(widest, width)
    return widest


def _fit_padding(cell_style: Any, col_width: float, word_width: float) -> None:
    """Shrink a cell's side padding (not below ``MIN_SIDE_PADDING``) so ``word_width`` fits unbroken."""
    left, right = cell_style.leftPadding, cell_style.rightPadding
    if word_width <= col_width - left - right - 2:
        return
    pad = max(MIN_SIDE_PADDING, min(left, right, (col_width - word_width - 2) / 2))
    cell_style.leftPadding = cell_style.rightPadding = pad


class VastWrappedTable(Table):
    """Table whose text cells wrap within their column and are centered both ways.

    Text cells are converted to ``Paragraph`` on first layout, using the cell's computed
    font, size and colour and the column width (span-aware), so rows grow in height
    while column widths stay as given. Existing ``Paragraph`` cells are re-centered;
    other flowables are left untouched. Tables without numeric column widths are not
    converted (ReportLab cannot size wrapped paragraphs in auto-width columns).
    """

    _cellvalues: List[Any]
    _argW: Any

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._vast_cells_wrapped = False
        Table.setStyle(self, _CENTER_MIDDLE)

    def setStyle(self, tblstyle: Any) -> None:
        """Apply ``tblstyle``, then re-assert centered/middle alignment for every cell."""
        super().setStyle(tblstyle)
        Table.setStyle(self, _CENTER_MIDDLE)

    def _calc(self, availWidth: float, availHeight: float) -> Any:
        if not getattr(self, "_vast_cells_wrapped", False):
            self._vast_cells_wrapped = True
            self._wrap_text_cells()
        return super()._calc(availWidth, availHeight)

    def _span_geometry(self, widths: Sequence[float]) -> Tuple[Dict[Tuple[int, int], float], Set[Tuple[int, int]]]:
        """Return (combined width per span origin, cells covered by a span but not its origin)."""
        n_rows, n_cols = len(self._cellvalues), len(widths)
        origin_width: Dict[Tuple[int, int], float] = {}
        covered: Set[Tuple[int, int]] = set()
        for cmd in getattr(self, "_spanCmds", None) or []:
            _, (sc, sr), (ec, er) = cmd
            sc, ec = sorted((sc % n_cols, ec % n_cols))
            sr, er = sorted((sr % n_rows, er % n_rows))
            origin_width[(sr, sc)] = sum(widths[sc : ec + 1])
            for r in range(sr, er + 1):
                for c in range(sc, ec + 1):
                    if (r, c) != (sr, sc):
                        covered.add((r, c))
        return origin_width, covered

    def _wrap_text_cells(self) -> None:
        widths = list(self._argW or [])
        if not self._cellvalues or not widths or not all(isinstance(w, (int, float)) for w in widths):
            return
        origin_width, covered = self._span_geometry(widths)
        floors = self._word_floors(len(widths), origin_width, covered)
        if any(w < f for w, f in zip(widths, floors)):
            widths = apply_word_floor(widths, floors)
            self._argW = self._colWidths = widths
            origin_width, covered = self._span_geometry(widths)
        styles: Dict[Tuple[Any, ...], ParagraphStyle] = {}
        rows = [list(row) for row in self._cellvalues]
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                if (r, c) in covered or c >= len(widths):
                    continue
                cell_style = self._cellStyles[r][c]
                col_width = origin_width.get((r, c), widths[c])
                _fit_padding(cell_style, col_width, self._cell_word_width(value, cell_style, widest_word))
                width = col_width - cell_style.leftPadding - cell_style.rightPadding - 1
                row[c] = self._wrap_value(value, cell_style, width, styles)
        self._cellvalues = rows

    @staticmethod
    def _cell_word_width(value: Any, cell_style: Any, measure: Any) -> float:
        """Apply ``measure(text, font, size)`` to a text or Paragraph cell; 0 for other content."""
        if isinstance(value, (str, int, float)):
            return float(measure(str(value), cell_style.fontname, cell_style.fontsize))
        if isinstance(value, Paragraph):
            return float(measure(value.getPlainText(), value.style.fontName, value.style.fontSize))
        return 0.0

    def _word_floors(
        self, n_cols: int, origin_width: Dict[Tuple[int, int], float], covered: Set[Tuple[int, int]]
    ) -> List[float]:
        """Per-column width needed so short words in single-column cells are not broken."""
        floors = [0.0] * n_cols
        for r, row in enumerate(self._cellvalues):
            for c, value in enumerate(row[:n_cols]):
                if (r, c) in covered or (r, c) in origin_width:
                    continue
                need = self._cell_word_width(value, self._cellStyles[r][c], min_unbroken_width)
                floors[c] = max(floors[c], need)
        return [f + 2 * MIN_SIDE_PADDING + 2 if f else 0.0 for f in floors]

    @staticmethod
    def _wrap_value(value: Any, cell_style: Any, width: float, styles: Dict[Tuple[Any, ...], ParagraphStyle]) -> Any:
        if isinstance(value, Paragraph):
            # CJK wrapping breaks inside words; wrap at spaces and split only over-long words.
            if value.style.alignment != TA_CENTER or getattr(value.style, "wordWrap", None) == "CJK":
                value.style = value.style.clone(f"{value.style.name}_centered", alignment=TA_CENTER, wordWrap=None)
            return value
        if not isinstance(value, (str, int, float)) or value == "":
            return value
        key = (cell_style.fontname, cell_style.fontsize, str(cell_style.color))
        style = styles.get(key)
        if style is None:
            style = ParagraphStyle(
                f"vast_cell_{len(styles)}",
                fontName=cell_style.fontname,
                fontSize=cell_style.fontsize,
                leading=cell_style.fontsize * 1.2,
                textColor=cell_style.color,
                alignment=TA_CENTER,
            )
            styles[key] = style
        lines = str(value).split("\n")
        markup = "<br/>".join(break_long_tokens(line, style.fontName, style.fontSize, width) for line in lines)
        return Paragraph(markup, style)


def apply_word_floor(widths: Sequence[float], floors: Sequence[float]) -> List[float]:
    """Raise columns to their floor width, taking the space from columns above their floor.

    The total width is preserved; columns already at or above their floor keep their
    share of the remaining space in proportion to how far they exceed it, so a
    layout with no violations is returned unchanged.

    Args:
        widths: Desired column widths in points.
        floors: Minimum width per column (e.g. widest word plus minimum padding).

    Returns:
        List[float]: Adjusted column widths with the same total.
    """
    total = float(sum(widths))
    floor_total = float(sum(floors))
    if floor_total >= total:
        return [total * f / floor_total for f in floors] if floor_total else list(widths)
    excess = [max(w - f, 0.0) for w, f in zip(widths, floors)]
    excess_total = sum(excess)
    spare = total - floor_total
    if excess_total <= 0:
        return [f + spare / len(floors) for f in floors]
    return [f + spare * e / excess_total for f, e in zip(floors, excess)]


def make_table(data: Any, **kwargs: Any) -> Table:
    """Build a report data table (wrapped, centered cells)."""
    return VastWrappedTable(data, **kwargs)


def is_title(flowable: Any) -> bool:
    """True for heading-style paragraphs and short, fully bold paragraphs used as table titles."""
    if not isinstance(flowable, Paragraph):
        return False
    if "heading" in (getattr(flowable.style, "name", "") or "").lower():
        return True
    text = (getattr(flowable, "text", "") or "").strip()
    return text.startswith("<b>") and text.endswith("</b>") and text.count("<b>") == 1 and len(text) <= 160


def _is_break(flowable: Any) -> bool:
    return isinstance(flowable, (UseUpSpace, ActionFlowable, CondPageBreak))


def _is_filler(flowable: Any) -> bool:
    if _is_break(flowable) or isinstance(flowable, (Paragraph, Table)):
        return False
    if isinstance(flowable, Spacer):
        return True
    return bool(getattr(flowable, "width", None) == 0 and getattr(flowable, "height", None) == 0)


def _height(flowable: Any, frame_width: float, frame_height: float) -> float:
    try:
        height = flowable.wrap(frame_width, frame_height)[1]
    except Exception:
        return frame_height + 1
    return float(height + flowable.getSpaceBefore() + flowable.getSpaceAfter())


def _group_height(group: List[Any], frame_width: float, frame_height: float) -> float:
    return sum(_height(item, frame_width, frame_height) for item in group)


def _lead_height(group: List[Any], table: Table, frame_width: float, frame_height: float, lead_rows: int) -> float:
    height = _group_height(group, frame_width, frame_height)
    table.wrap(frame_width, frame_height)
    row_heights: Optional[List[float]] = getattr(table, "_rowHeights", None)
    if row_heights:
        height += sum(row_heights[: 1 + lead_rows])
    return min(height, frame_height)


def bind_titles_to_content(story: List[Any], frame_width: float, frame_height: float, lead_rows: int = 3) -> List[Any]:
    """Keep each title on the same page as the content that follows it.

    A title followed by a table gets a ``CondPageBreak`` sized to the title plus the
    table header and first ``lead_rows`` rows, so long tables still start under their
    title and split across pages. A title followed by anything else is wrapped in
    ``KeepTogether`` with that flowable. Nothing is bound across explicit page breaks.

    Args:
        story: Flowables in document order.
        frame_width: Usable frame width in points.
        frame_height: Usable frame height in points.
        lead_rows: Data rows that must fit under the title on the same page.

    Returns:
        List[Any]: New story list.
    """
    out: List[Any] = []
    i, n = 0, len(story)
    while i < n:
        if not is_title(story[i]):
            out.append(story[i])
            i += 1
            continue
        j = i
        group: List[Any] = []
        while j < n and (is_title(story[j]) or _is_filler(story[j])):
            group.append(story[j])
            j += 1
        if j >= n or _is_break(story[j]):
            out.extend(group)
            i = j
            continue
        content = story[j]
        if isinstance(content, Table):
            out.append(CondPageBreak(_lead_height(group, content, frame_width, frame_height, lead_rows)))
            out.extend(group)
            out.append(content)
        elif (
            _group_height(group, frame_width, frame_height) + _height(content, frame_width, frame_height)
            <= frame_height
        ):
            out.append(KeepTogether(group + [content]))
        else:
            out.extend(group)
            out.append(content)
        i = j + 1
    return out
