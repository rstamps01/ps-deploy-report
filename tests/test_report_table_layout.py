"""Report-level wiring of the wrapped table layout and its legacy toggle (RPT-LAYOUT-1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: E402
from reportlab.platypus import CondPageBreak, KeepTogether, PageBreak, Paragraph, Spacer, Table  # noqa: E402

from brand_compliance import create_vast_brand_compliance  # noqa: E402
from report_builder import ReportConfig, VastReportBuilder  # noqa: E402
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


def _builder(layout):
    return VastReportBuilder(config=ReportConfig(table_layout=layout))


def _tables(flowables):
    found = []
    for f in flowables:
        if isinstance(f, Table):
            found.append(f)
        found.extend(_tables(getattr(f, "_content", []) or []))
    return found


class TestConfig:
    def test_default_is_wrapped(self):
        assert ReportConfig().table_layout == "wrapped"

    def test_yaml_legacy(self):
        assert ReportConfig.from_yaml({"report": {"table_layout": "legacy"}}).table_layout == "legacy"

    def test_yaml_invalid_falls_back_to_wrapped(self):
        assert ReportConfig.from_yaml({"report": {"table_layout": "fancy"}}).table_layout == "wrapped"

    def test_builder_passes_layout_to_brand_compliance(self):
        assert _builder("legacy").brand_compliance.table_layout == "legacy"
        assert _builder("wrapped").brand_compliance.table_layout == "wrapped"

    def test_cli_and_replay_honor_table_layout(self):
        from main import _layout_report_config

        assert _layout_report_config({"report": {"table_layout": "legacy"}}).table_layout == "legacy"
        assert _layout_report_config(None).table_layout == "wrapped"


class TestHealthSection:
    def test_wrapped_renders_consolidated_groups(self):
        text = _flowable_text(_builder("wrapped")._create_health_check_section(HEALTH_DATA))
        assert "Health Check Details — Cluster State &amp; Software" in text or (
            "Health Check Details — Cluster State & Software" in text
        )
        assert "Health Check Details — Network" in text
        assert "1.1.1.1, 8.8.8.8" in text
        assert "— details" not in text

    def test_legacy_keeps_per_check_subtables(self):
        text = _flowable_text(_builder("legacy")._create_health_check_section(HEALTH_DATA))
        assert "Cluster State — details" in text
        assert "Health Check Details —" not in text

    def test_wrapped_tables_are_wrapped(self):
        tables = _tables(_builder("wrapped")._create_health_check_section(HEALTH_DATA))
        assert tables and all(isinstance(t, VastWrappedTable) for t in tables)

    def test_legacy_tables_are_plain(self):
        tables = _tables(_builder("legacy")._create_health_check_section(HEALTH_DATA))
        assert tables and not any(isinstance(t, VastWrappedTable) for t in tables)


class TestBrandTables:
    def _bc(self, layout):
        bc = create_vast_brand_compliance()
        bc.table_layout = layout
        return bc

    def test_wrapped_titled_table_is_flat(self):
        elements = self._bc("wrapped").create_vast_table([["a", "b"]], title="Things", headers=["A", "B"])
        assert not any(isinstance(e, KeepTogether) for e in elements)
        assert any(isinstance(e, VastWrappedTable) for e in elements)

    def test_legacy_titled_table_kept_together(self):
        elements = self._bc("legacy").create_vast_table([["a", "b"]], title="Things", headers=["A", "B"])
        assert isinstance(elements[0], KeepTogether)
        assert not _tables(elements)[0].__class__ is VastWrappedTable

    def test_wrapped_hardware_table_flows_continuously(self):
        rows = [[f"r{i}", "m", "n", "s", "ACTIVE", "1U"] for i in range(60)]
        headers = ["Rack", "Model", "Name", "Serial", "Status", "Height"]
        elements = self._bc("wrapped").create_vast_hardware_table_with_pagination(rows, "Hardware Inventory", headers)
        assert not any(isinstance(e, PageBreak) for e in elements)
        assert len(_tables(elements)) == 1
        assert "(Page 1 of" not in _flowable_text(elements)

    def test_wrapped_hardware_columns_fit_short_words(self):
        serial = "S000000X0000001-PLATFORM-RDMA:4200"
        rows = [["Unknown", "supermicro_turin_ebox24", f"ebox-{serial}-{serial}", serial, "ACTIVE", "1U"]]
        headers = ["Rack", "Model", "Name", "Serial", "Status", "Height"]
        bc = self._bc("wrapped")
        table = _tables(bc.create_vast_hardware_table_with_auto_width(rows, "Hardware Inventory", headers))[0]
        table.wrap(sum(table._argW), 10_000)
        size = bc.typography.BODY_SIZE
        assert table._argW[0] >= stringWidth("Unknown", bc.typography.BODY_FONT, size)
        assert table._argW[5] >= stringWidth("Height", "Helvetica-Bold", size)

    def test_legacy_hardware_table_paginates(self):
        rows = [[f"r{i}", "m", "n", "s", "ACTIVE", "1U"] for i in range(60)]
        headers = ["Rack", "Model", "Name", "Serial", "Status", "Height"]
        elements = self._bc("legacy").create_vast_hardware_table_with_pagination(rows, "Hardware Inventory", headers)
        assert "(Page 1 of 3)" in _flowable_text(elements)


class TestStoryFinalization:
    def test_wrapped_binds_titles(self):
        story = [Paragraph("<b>Title</b>"), Spacer(1, 4), Table([["h"], ["v"]], colWidths=[50])]
        out = _builder("wrapped")._finalize_story(story)
        assert isinstance(out[0], CondPageBreak)

    def test_legacy_story_unchanged(self):
        story = [Paragraph("<b>Title</b>"), Spacer(1, 4), Table([["h"], ["v"]], colWidths=[50])]
        assert _builder("legacy")._finalize_story(story) == story


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

    def test_wrapped_uses_wrapped_table(self):
        tables = _tables(_builder("wrapped")._create_cnodes_network_configuration(self.DATA))
        assert tables and isinstance(tables[0], VastWrappedTable)

    def test_legacy_uses_plain_table(self):
        tables = _tables(_builder("legacy")._create_cnodes_network_configuration(self.DATA))
        assert tables and type(tables[0]) is Table
