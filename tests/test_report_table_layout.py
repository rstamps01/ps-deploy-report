"""Report-level wiring of the wrapped table layout (RPT-LAYOUT-1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

import pymupdf  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import getSampleStyleSheet  # noqa: E402
from reportlab.lib.units import inch  # noqa: E402
from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate  # noqa: E402
from reportlab.platypus import CondPageBreak, KeepTogether, PageBreak, Paragraph, Spacer, Table  # noqa: E402

from brand_compliance import create_vast_brand_compliance  # noqa: E402
from report_builder import ReportConfig, VastReportBuilder  # noqa: E402
from utils.health_detail_groups import build_health_detail_groups  # noqa: E402
from utils.pdf_layout import VastWrappedTable  # noqa: E402


def _flowable_text(content):
    """Recursively collect plain text from flowables, table cells and wrappers."""
    out = []

    def walk(obj):
        if obj is None:
            return
        if isinstance(obj, str):
            out.append(obj)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item)
        elif callable(getattr(obj, "getPlainText", None)):
            out.append(obj.getPlainText())
        elif getattr(obj, "_cellvalues", None) is not None:
            walk(obj._cellvalues)
        elif isinstance(getattr(obj, "_content", None), (list, tuple)):
            walk(obj._content)

    walk(content)
    return "\n".join(out)


HEALTH_DATA = {
    "summary": {"pass": 2, "fail": 0, "warning": 0, "skipped": 0, "error": 0, "total": 2},
    "results": [
        {
            "check_name": "Cluster State",
            "category": "api",
            "status": "pass",
            "message": "Cluster is ONLINE and enabled",
            "details": {"state": "ONLINE", "enabled": True},
        },
        {
            "check_name": "Network Settings",
            "category": "api",
            "status": "pass",
            "message": "DNS, NTP, and gateway are configured",
            "details": {"dns": ["1.1.1.1", "8.8.8.8"], "ntp": ["10.0.0.5"], "gateway": ["10.0.0.1"]},
        },
    ],
}


def _builder():
    return VastReportBuilder()


def _tables(flowables):
    found = []
    for f in flowables:
        if isinstance(f, Table):
            found.append(f)
        found.extend(_tables(getattr(f, "_content", []) or []))
    return found


class TestConfig:
    def test_retired_table_layout_key_is_ignored(self):
        config = ReportConfig.from_yaml({"report": {"table_layout": "legacy", "organization": "Acme"}})
        assert config.organization == "Acme"
        assert not hasattr(config, "table_layout")


class TestHealthSection:
    def test_renders_consolidated_groups(self):
        text = _flowable_text(_builder()._create_health_check_section(HEALTH_DATA))
        assert "Health Check Details — Cluster State &amp; Software" in text or (
            "Health Check Details — Cluster State & Software" in text
        )
        assert "Health Check Details — Network" in text
        assert "1.1.1.1, 8.8.8.8" in text
        assert "— details" not in text

    def test_tables_are_wrapped(self):
        tables = _tables(_builder()._create_health_check_section(HEALTH_DATA))
        assert tables and all(isinstance(t, VastWrappedTable) for t in tables)


class TestBrandTables:
    def test_titled_table_is_flat(self):
        elements = create_vast_brand_compliance().create_vast_table([["a", "b"]], title="Things", headers=["A", "B"])
        assert not any(isinstance(e, KeepTogether) for e in elements)
        assert any(isinstance(e, VastWrappedTable) for e in elements)

    def test_hardware_table_flows_continuously(self):
        rows = [[f"r{i}", "m", "n", "s", "ACTIVE", "1U"] for i in range(60)]
        headers = ["Rack", "Model", "Name", "Serial", "Status", "Height"]
        bc = create_vast_brand_compliance()
        elements = bc.create_vast_hardware_table_with_pagination(rows, "Hardware Inventory", headers)
        assert not any(isinstance(e, PageBreak) for e in elements)
        assert len(_tables(elements)) == 1
        assert "(Page 1 of" not in _flowable_text(elements)

    def test_hardware_columns_fit_short_words(self):
        serial = "S000000X0000001-PLATFORM-RDMA:4200"
        rows = [["Unknown", "supermicro_turin_ebox24", f"ebox-{serial}-{serial}", serial, "ACTIVE", "1U"]]
        headers = ["Rack", "Model", "Name", "Serial", "Status", "Height"]
        bc = create_vast_brand_compliance()
        table = _tables(bc.create_vast_hardware_table_with_auto_width(rows, "Hardware Inventory", headers))[0]
        table.wrap(sum(table._argW), 10_000)
        size = bc.typography.BODY_SIZE
        assert table._argW[0] >= stringWidth("Unknown", bc.typography.BODY_FONT, size)
        assert table._argW[5] >= stringWidth("Height", "Helvetica-Bold", size)


class TestStoryFinalization:
    def test_binds_titles(self):
        story = [Paragraph("<b>Title</b>"), Spacer(1, 4), Table([["h"], ["v"]], colWidths=[50])]
        out = _builder()._finalize_story(story)
        assert len(out) == 1 and isinstance(out[0], KeepTogether)

    def test_long_table_still_starts_under_its_title(self):
        story = [Paragraph("<b>Title</b>"), Table([["h"]] + [[str(i)] for i in range(120)], colWidths=[50])]
        out = _builder()._finalize_story(story)
        assert isinstance(out[0], CondPageBreak)


class TestHealthGroupPagination:
    """A health detail heading lands on the same page as its whole first table."""

    FRAME_W = A4[0] - 1.0 * inch
    FRAME_H = A4[1] - 1.5 * inch

    def _render(self, tmp_path, lead_height):
        from test_health_detail_groups import EBOX_RESULTS

        builder = _builder()
        builder._frame_width, builder._frame_height = self.FRAME_W, self.FRAME_H
        styles = getSampleStyleSheet()
        story = [Spacer(1, lead_height)] + builder._create_health_detail_group_tables(EBOX_RESULTS, styles)
        path = tmp_path / f"groups_{lead_height}.pdf"
        doc = BaseDocTemplate(str(path), pagesize=A4)
        frame = Frame(0.5 * inch, 0.75 * inch, self.FRAME_W, self.FRAME_H, 0, 0, 0, 0)
        doc.addPageTemplates([PageTemplate(frames=[frame])])
        doc.build(builder._finalize_story(story))
        return [page.get_text() for page in pymupdf.open(str(path))]

    def test_heading_and_first_table_share_a_page(self, tmp_path):
        from test_health_detail_groups import EBOX_RESULTS

        groups = build_health_detail_groups(EBOX_RESULTS)
        for lead in range(0, int(self.FRAME_H), 30):
            pages = self._render(tmp_path, lead)
            for group in groups:
                first = next(t for t in group.tables if t.rows)
                title_page = next(i for i, text in enumerate(pages) if group.title in text)
                text = pages[title_page]
                tail = text[text.index(group.title) :]
                for cell in (first.headers[0], first.rows[0][0], first.rows[-1][0]):
                    assert str(cell) in tail, f"lead={lead}: {group.title!r} split from its table ({cell!r})"


class TestNetworkConfigTables:
    DATA = {
        "sections": {
            "cnodes_network_configuration": {
                "data": {
                    "cnodes": [{"id": 1, "hostname": "cnode-1", "mgmt_ip": "10.0.0.1", "box_vendor": "x"}],
                    "total_cnodes": 1,
                }
            }
        }
    }

    def test_uses_wrapped_table(self):
        tables = _tables(_builder()._create_cnodes_network_configuration(self.DATA))
        assert tables and isinstance(tables[0], VastWrappedTable)
