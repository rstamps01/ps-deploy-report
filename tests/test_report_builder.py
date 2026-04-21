"""
Unit tests for VAST As-Built Report Generator Report Builder Module.

This module contains comprehensive unit tests for the report builder,
including PDF generation, report formatting, and error handling.

Author: Manus AI
Date: September 26, 2025
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from report_builder import VastReportBuilder, ReportConfig, ReportGenerationError, create_report_builder


class TestReportConfig(unittest.TestCase):
    """Test cases for ReportConfig dataclass."""

    def test_report_config_creation(self):
        """Test ReportConfig creation with default values."""
        config = ReportConfig()

        self.assertEqual(config.page_size, "A4")
        self.assertEqual(config.margin_top, 1.0)
        self.assertEqual(config.margin_bottom, 1.0)
        self.assertEqual(config.margin_left, 1.0)
        self.assertEqual(config.margin_right, 1.0)
        self.assertEqual(config.font_name, "Helvetica")
        self.assertEqual(config.font_size, 10)
        self.assertEqual(config.title_font_size, 16)
        self.assertEqual(config.heading_font_size, 12)
        self.assertEqual(config.line_spacing, 1.2)
        self.assertTrue(config.include_toc)
        self.assertTrue(config.include_timestamp)
        self.assertTrue(config.include_enhanced_features)

    def test_report_config_custom_values(self):
        """Test ReportConfig creation with custom values."""
        config = ReportConfig(page_size="Letter", margin_top=0.5, font_size=12, include_toc=False)

        self.assertEqual(config.page_size, "Letter")
        self.assertEqual(config.margin_top, 0.5)
        self.assertEqual(config.font_size, 12)
        self.assertFalse(config.include_toc)


class TestVastReportBuilder(unittest.TestCase):
    """Test cases for VastReportBuilder class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = ReportConfig()

        # Sample processed data for testing
        self.sample_data = {
            "metadata": {
                "extraction_timestamp": "2025-09-26T23:00:00",
                "overall_completeness": 0.95,
                "enhanced_features": {"rack_height_supported": True, "psnt_supported": True},
                "api_version": "v7",
                "cluster_version": "5.3.0",
            },
            "cluster_summary": {
                "name": "Test Cluster",
                "guid": "test-guid-123",
                "version": "5.3.0",
                "state": "active",
                "license": "Enterprise",
                "psnt": "PSNT123456789",
            },
            "hardware_inventory": {
                "total_nodes": 4,
                "cnodes": [
                    {
                        "id": "cnode-1",
                        "model": "CBox-100",
                        "serial_number": "SN123456",
                        "status": "active",
                        "rack_position": 5,
                    },
                    {
                        "id": "cnode-2",
                        "model": "CBox-100",
                        "serial_number": "SN123457",
                        "status": "active",
                        "rack_position": 6,
                    },
                ],
                "dnodes": [
                    {
                        "id": "dnode-1",
                        "model": "DBox-100",
                        "serial_number": "SN789012",
                        "status": "active",
                        "rack_position": 10,
                    },
                    {
                        "id": "dnode-2",
                        "model": "DBox-100",
                        "serial_number": "SN789013",
                        "status": "active",
                        "rack_position": 11,
                    },
                ],
                "rack_positions_available": True,
                "physical_layout": {
                    "statistics": {
                        "occupied_positions": 4,
                        "min_position": 5,
                        "max_position": 11,
                        "total_cnodes": 2,
                        "total_dnodes": 2,
                    }
                },
            },
            "sections": {
                "network_configuration": {
                    "data": {
                        "dns": {"enabled": True, "servers": ["8.8.8.8", "8.8.4.4"], "search_domains": ["example.com"]},
                        "ntp": {"enabled": True, "servers": ["pool.ntp.org"]},
                        "vippools": {"pools": [{"name": "default", "vips": ["192.168.1.10"]}]},
                    }
                },
                "logical_configuration": {
                    "data": {
                        "tenants": {"tenants": [{"name": "tenant1", "id": "t1", "state": "active"}]},
                        "views": {"views": [{"name": "view1", "path": "/view1", "state": "active"}]},
                        "view_policies": {"policies": [{"name": "policy1", "type": "read-only", "state": "active"}]},
                    }
                },
                "security_configuration": {
                    "data": {
                        "active_directory": {"enabled": True, "domain": "example.com", "servers": ["dc1.example.com"]},
                        "ldap": {"enabled": False},
                        "nis": {"enabled": False},
                    }
                },
                "data_protection_configuration": {
                    "data": {
                        "snapshot_programs": {
                            "programs": [{"name": "daily", "schedule": "0 2 * * *", "enabled": True}]
                        },
                        "protection_policies": {
                            "policies": [{"name": "backup", "type": "replication", "retention": "30d", "enabled": True}]
                        },
                    }
                },
            },
        }

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test report builder initialization."""
        builder = VastReportBuilder()

        self.assertIsInstance(builder.config, ReportConfig)
        self.assertEqual(builder.config.page_size, "A4")

    def test_initialization_with_config(self):
        """Test report builder initialization with custom config."""
        custom_config = ReportConfig(page_size="Letter", font_size=12)
        builder = VastReportBuilder(custom_config)

        self.assertEqual(builder.config.page_size, "Letter")
        self.assertEqual(builder.config.font_size, 12)

    @patch("report_builder.REPORTLAB_AVAILABLE", False)
    def test_initialization_no_libraries(self):
        """Test initialization when ReportLab is not available."""
        with self.assertRaises(ReportGenerationError):
            VastReportBuilder()

    @patch("report_builder.REPORTLAB_AVAILABLE", True)
    def test_generate_pdf_report_reportlab(self):
        """Test PDF generation with ReportLab."""
        builder = VastReportBuilder()
        output_path = str(Path(self.temp_dir) / "test_report.pdf")

        result = builder.generate_pdf_report(self.sample_data, output_path)

        self.assertTrue(result)
        self.assertTrue(Path(output_path).exists())

    def test_generate_pdf_report_invalid_data(self):
        """Test PDF generation with invalid data."""
        builder = VastReportBuilder()
        output_path = str(Path(self.temp_dir) / "test_report.pdf")

        result = builder.generate_pdf_report({}, output_path)

        # Should still succeed but with minimal content
        self.assertTrue(result)

    def test_generate_pdf_report_invalid_path(self):
        """Test PDF generation with invalid output path."""
        builder = VastReportBuilder()
        invalid_path = "/invalid/path/that/does/not/exist/test.pdf"

        result = builder.generate_pdf_report(self.sample_data, invalid_path)

        self.assertFalse(result)

    def test_create_title_page(self):
        """Test title page creation."""
        builder = VastReportBuilder()

        content = builder._create_title_page(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_table_of_contents(self):
        """Test table of contents creation."""
        builder = VastReportBuilder()

        content = builder._create_table_of_contents(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_executive_summary(self):
        """Test executive summary creation."""
        builder = VastReportBuilder()

        content = builder._create_executive_summary(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_cluster_information(self):
        """Test cluster information section creation."""
        builder = VastReportBuilder()

        content = builder._create_cluster_information(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_hardware_inventory(self):
        """Test hardware inventory section creation."""
        builder = VastReportBuilder()

        content = builder._create_hardware_inventory(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_network_configuration(self):
        """Test network configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_network_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_logical_configuration(self):
        """Test logical configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_logical_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_security_configuration(self):
        """Test security configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_security_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_data_protection_configuration(self):
        """Test data protection configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_data_protection_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_enhanced_features_section(self):
        """Test enhanced features section creation."""
        builder = VastReportBuilder()

        content = builder._create_enhanced_features_section(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_appendix(self):
        """Test appendix section creation."""
        builder = VastReportBuilder()

        content = builder._create_appendix(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_report_builder(self):
        """Test convenience function for creating report builder."""
        builder = create_report_builder()

        self.assertIsInstance(builder, VastReportBuilder)

    def test_create_report_builder_with_config(self):
        """Test convenience function with custom config."""
        custom_config = ReportConfig(font_size=14)
        builder = create_report_builder(custom_config)

        self.assertEqual(builder.config.font_size, 14)


class TestReportGenerationError(unittest.TestCase):
    """Test cases for ReportGenerationError exception."""

    def test_report_generation_error_creation(self):
        """Test ReportGenerationError creation."""
        error = ReportGenerationError("Test error message")

        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)


class TestSpinePortTables(unittest.TestCase):
    """Coverage for the SP1 Port-to-Device Mapping table emitted when spine
    switches have LLDP-discovered (or inferred) uplinks.

    Regression guard for the "spine switch missing from port mapping tables"
    bug reported against the Logical Network Diagram.
    """

    def setUp(self):
        self.builder = VastReportBuilder()
        self.switches = [
            {"mgmt_ip": "10.0.0.153", "hostname": "leaf-a", "role": "leaf"},
            {"mgmt_ip": "10.0.0.154", "hostname": "leaf-b", "role": "leaf"},
            {"mgmt_ip": "10.0.0.156", "hostname": "spine-1", "role": "spine"},
        ]
        self.headers = ["Switch Port", "Node Connection", "Network", "Speed", "Notes"]

    def _capture_table_data(self, content):
        """Pull the raw table rows we built by inspecting the brand-compliance call."""
        captured = {}

        def _fake_create_vast_table(data, title, headers):
            captured.setdefault("calls", []).append({"data": data, "title": title})
            return ["<table-flowable>"]

        with patch.object(self.builder.brand_compliance, "create_vast_table", side_effect=_fake_create_vast_table):
            result = self.builder._create_spine_port_tables(
                port_mapping_data=content,
                switches=self.switches,
                leaf_switch_ips={"10.0.0.153", "10.0.0.154"},
                headers=self.headers,
            )
        return captured.get("calls", []), result

    def test_returns_empty_when_no_spine_uplinks(self):
        port_mapping_data = {
            "ipl_connections": [
                {
                    "switch1_ip": "10.0.0.153",
                    "switch2_ip": "10.0.0.154",
                    "connection_type": "ipl",
                    "switch_designation": "SWA",
                    "node_designation": "SWB",
                }
            ]
        }
        calls, content = self._capture_table_data(port_mapping_data)
        self.assertEqual(calls, [])
        self.assertEqual(content, [])

    def test_emits_spine_table_with_uplink_rows(self):
        port_mapping_data = {
            "ipl_connections": [
                {
                    "switch1_ip": "10.0.0.156",
                    "switch2_ip": "10.0.0.153",
                    "connection_type": "spine_uplink",
                    "switch_designation": "SP1",
                    "node_designation": "SWA",
                    "notes": "Spine uplink",
                },
                {
                    "switch1_ip": "10.0.0.156",
                    "switch2_ip": "10.0.0.154",
                    "connection_type": "spine_uplink",
                    "switch_designation": "SP1",
                    "node_designation": "SWB",
                    "notes": "Spine uplink (inferred)",
                },
            ]
        }
        calls, _content = self._capture_table_data(port_mapping_data)

        self.assertEqual(len(calls), 1, "Exactly one spine table expected for a single spine")
        call = calls[0]
        self.assertIn("SP1", call["title"], "Title should surface the spine designation")
        self.assertIn("spine-1", call["title"], "Title should also show the hostname")

        rows = call["data"]
        self.assertEqual(len(rows), 2)
        self.assertEqual({rows[0][0], rows[1][0]}, {"SP1"})
        self.assertEqual({rows[0][1], rows[1][1]}, {"SWA", "SWB"})
        for row in rows:
            self.assertEqual(row[2], "Uplink")

    def test_leaf_ips_excluded_from_spine_candidates(self):
        """Even if a leaf appears in a spine_uplink endpoint, it must not get a spine table."""
        port_mapping_data = {
            "ipl_connections": [
                {
                    "switch1_ip": "10.0.0.156",
                    "switch2_ip": "10.0.0.153",
                    "connection_type": "spine_uplink",
                },
            ]
        }
        calls, _content = self._capture_table_data(port_mapping_data)
        self.assertEqual(len(calls), 1)
        self.assertNotIn("leaf-a", calls[0]["title"], "Leaf must not be promoted to a spine table")


if __name__ == "__main__":
    unittest.main()
