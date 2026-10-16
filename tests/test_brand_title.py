"""Tests for the report title brand treatment (RPT-TITLE-1)."""

import os
import sys
from pathlib import Path
from unittest.mock import patch

from reportlab.platypus import Paragraph

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import brand_compliance  # noqa: E402
from brand_compliance import VastBrandCompliance  # noqa: E402
from report_builder import VastReportBuilder  # noqa: E402


def _title_paragraph(elements):
    return next(e for e in elements if isinstance(e, Paragraph))


class TestBrandTitle:
    def test_title_text_is_rebranded(self):
        content = VastReportBuilder()._create_title_page({"cluster_summary": {}, "hardware_inventory": {}})
        title = _title_paragraph(content)
        assert title.getPlainText() == "VAST asbuilt-reporter"

    def test_title_uses_black_and_accent_blue(self):
        elements = VastBrandCompliance().create_vast_header("VAST asbuilt-reporter")
        markup = _title_paragraph(elements).text
        assert 'color="#000000">VAST asbuilt</font>' in markup
        assert 'color="#1a6fb5">-reporter</font>' in markup

    def test_fira_sans_bold_is_registered_for_title(self):
        bc = VastBrandCompliance()
        assert bc.title_font == brand_compliance.BRAND_TITLE_FONT
        markup = _title_paragraph(bc.create_vast_header("VAST asbuilt-reporter")).text
        assert f'name="{brand_compliance.BRAND_TITLE_FONT}"' in markup

    def test_missing_font_falls_back_to_helvetica_bold(self, tmp_path):
        with patch.object(brand_compliance, "_brand_font_path", return_value=Path(tmp_path) / "missing.ttf"):
            assert brand_compliance.register_brand_title_font(force=True) == "Helvetica-Bold"
            bc = VastBrandCompliance()
        markup = _title_paragraph(bc.create_vast_header("VAST asbuilt-reporter")).text
        assert 'name="Helvetica-Bold"' in markup
        brand_compliance.register_brand_title_font(force=True)

    def test_other_titles_render_as_plain_bold(self):
        markup = _title_paragraph(VastBrandCompliance().create_vast_header("Some Other Title")).text
        assert markup == "<b>Some Other Title</b>"
