"""
Functional validation tests for CI/CD.

These tests validate behaviors that caused production issues (Windows charmap,
network diagram PNG fallback) so that regressions are caught before release.
Run with: pytest tests/test_functional_validation.py -v
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestPortMappingWindowsCharmap(unittest.TestCase):
    """Validate port mapping does not raise charmap/codec errors on Windows-style output."""

    def test_safe_str_replaces_non_ascii(self):
        """_safe_str() must never raise and must produce ASCII-safe string for logging."""
        from external_port_mapper import _safe_str

        # Simulates Windows UnicodeEncodeError scenario: exception message with non-ASCII
        bad = "charmap codec can't encode characters in position 33-72: character maps to <undefined>"
        self.assertEqual(_safe_str(bad), bad)
        # Non-ASCII (e.g. from SSH banner or switch output)
        with_unicode = "Cumulus Linux \u2014 hostname\n"
        out = _safe_str(with_unicode)
        self.assertIsInstance(out, str)
        out.encode("ascii")  # must be encodable
        self.assertIn("?", out)  # replacement char for non-ASCII

    def test_verbose_logger_log_result_with_unicode_stdout_does_not_raise(self):
        """VerboseLogger.log_result() with non-ASCII stdout must not raise (Windows-safe logging)."""
        from external_port_mapper import VerboseLogger

        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "test_port_mapper.log"
            vlog = VerboseLogger(log_file=str(log_file))
            # Simulate subprocess result with UTF-8 / non-ASCII output (e.g. from Linux switch)
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Cumulus Linux \u2014 hostname\n  \u03b2-test\n"
            result.stderr = ""
            # Must not raise UnicodeEncodeError (e.g. on Windows cp1252)
            vlog.log_result(result, "TEST RESULT")
            self.assertTrue(log_file.exists())
            content = log_file.read_text(encoding="utf-8")
            self.assertIn("STDOUT", content)
            # Non-ASCII should be replaced in logged content (ASCII-safe)
            self.assertNotIn("\u2014", content)  # em dash replaced

    def test_port_mapper_exception_logged_safely(self):
        """When port mapping raises with Unicode in message, error is logged without raising."""
        from external_port_mapper import _safe_str

        e = ValueError("'charmap' codec can't encode characters in position 33-72: character maps to <undefined>")
        safe = _safe_str(e)
        self.assertIsInstance(safe, str)
        safe.encode("ascii")

    def test_app_port_mapping_failure_logs_safe_message(self):
        """Web app logs port mapping failure with ASCII-safe message (no charmap error on Windows)."""
        unicode_error_msg = "'charmap' codec can't encode characters in position 33-72: character maps to <undefined>"
        with patch("app.logger") as mock_logger:
            with patch("external_port_mapper.ExternalPortMapper", MagicMock(side_effect=ValueError(unicode_error_msg))):
                from app import _collect_port_mapping_web

                result = _collect_port_mapping_web(
                    params={"cluster_ip": "1.2.3.4"},
                    raw_data={
                        "switch_inventory": {"switches": [{"mgmt_ip": "10.0.0.1"}]},
                        "cnodes_network": [{"mgmt_ip": "10.0.0.2"}],
                    },
                    api_handler=MagicMock(username="u", password="p"),
                )
            self.assertIsNone(result)
            # "Port mapping collection failed for all CNodes: %s" with safe last_error
            warning_calls = [c for c in mock_logger.warning.call_args_list if "failed for all CNodes" in str(c)]
            self.assertTrue(warning_calls, "Expected warning for port mapping failed for all CNodes")
            logged_arg = warning_calls[0][0][1] if len(warning_calls[0][0]) > 1 else ""
            logged_arg.encode("ascii")  # must not raise on Windows


class TestNetworkDiagramPngFallback(unittest.TestCase):
    """Validate network diagram uses PDF-to-PNG fallback (no placeholder) when renderPM fails (e.g. Windows T1 font)."""

    @pytest.mark.slow
    def test_generate_returns_png_via_fallback_when_render_pm_fails(self):
        """When renderPM fails (e.g. T1 font), PDF-to-PNG fallback (PyMuPDF) is used and returns PNG path (no placeholder)."""
        from network_diagram import NetworkDiagramGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "network_topology.pdf"
            gen = NetworkDiagramGenerator(assets_path=str(Path(__file__).parent.parent / "assets"))
            port_mapping_data = {"port_map": [], "ipl_connections": []}
            hardware_data = {"cboxes": [], "dboxes": [], "switches": [{"name": "SW1", "model": "test"}]}

            with patch("reportlab.graphics.renderPM.drawToFile", side_effect=TypeError("T1 font")):
                # PDF is written; renderPM fails; PyMuPDF fallback should produce PNG
                result = gen.generate_network_diagram(
                    port_mapping_data=port_mapping_data,
                    hardware_data=hardware_data,
                    output_path=str(out_pdf),
                    drawing_size=(400, 300),
                )
            # Fallback (PyMuPDF) should produce PNG so report does not use placeholder
            self.assertIsNotNone(result, "Expected PNG path from fallback when renderPM fails")
            self.assertTrue(Path(result).exists(), f"PNG file should exist: {result}")

    def test_generate_returns_none_only_when_both_render_pm_and_fallback_fail(self):
        """When renderPM and PDF fallback both fail, generate returns None."""
        from network_diagram import NetworkDiagramGenerator

        try:
            import fitz  # ensure module exists so we can patch it
        except ImportError:
            self.skipTest("fitz not installed")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "network_topology.pdf"
            gen = NetworkDiagramGenerator(assets_path=str(Path(__file__).parent.parent / "assets"))
            port_mapping_data = {"port_map": [], "ipl_connections": []}
            hardware_data = {"cboxes": [], "dboxes": [], "switches": [{"name": "SW1", "model": "test"}]}

            with patch("network_diagram.renderPDF.drawToFile"):
                with patch("reportlab.graphics.renderPM.drawToFile", side_effect=TypeError("T1 font")):
                    with patch("fitz.open", side_effect=RuntimeError("test fallback failure")):
                        result = gen.generate_network_diagram(
                            port_mapping_data=port_mapping_data,
                            hardware_data=hardware_data,
                            output_path=str(out_pdf),
                            drawing_size=(400, 300),
                        )
            self.assertIsNone(result)

    def test_generate_pdf_succeeds_even_when_render_pm_fails(self):
        """PDF is written even when renderPM raises (e.g. Windows T1 font)."""
        from network_diagram import NetworkDiagramGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            out_pdf = Path(tmpdir) / "network_topology.pdf"
            gen = NetworkDiagramGenerator(assets_path=str(Path(__file__).parent.parent / "assets"))
            port_mapping_data = {"port_map": [], "ipl_connections": []}
            hardware_data = {"cboxes": [], "dboxes": [], "switches": [{"name": "SW1", "model": "test"}]}

            with patch("network_diagram.renderPDF.drawToFile") as mock_pdf:
                with patch("reportlab.graphics.renderPM.drawToFile", side_effect=TypeError("T1 font")):
                    gen.generate_network_diagram(
                        port_mapping_data=port_mapping_data,
                        hardware_data=hardware_data,
                        output_path=str(out_pdf),
                        drawing_size=(400, 300),
                    )
            mock_pdf.assert_called_once()


if __name__ == "__main__":
    unittest.main()
