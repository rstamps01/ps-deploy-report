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


class TestSR5FormatMacCell(unittest.TestCase):
    """SR-5: ``_format_mac_cell`` must wrap long IB GIDs into a Paragraph
    so they don't overflow the Port Mapping MAC column, while leaving short
    Ethernet MACs as plain strings (zero overhead).
    """

    @classmethod
    def setUpClass(cls):
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.platypus import Paragraph

        cls.Paragraph = Paragraph
        cls.style = ParagraphStyle("test_mac_cell", fontName="Helvetica", fontSize=8)

    def _import_helper(self):
        from report_builder import _format_mac_cell

        return _format_mac_cell

    def test_short_ethernet_mac_returns_plain_string(self):
        """6-byte Ethernet MAC fits the column \u2014 no Paragraph wrapping needed."""
        fn = self._import_helper()
        result = fn("00:11:22:33:44:55", self.style)
        self.assertEqual(result, "00:11:22:33:44:55")
        self.assertNotIsInstance(result, self.Paragraph)

    def test_empty_mac_returns_empty_string(self):
        fn = self._import_helper()
        self.assertEqual(fn("", self.style), "")

    def test_none_mac_returns_empty_string(self):
        fn = self._import_helper()
        self.assertEqual(fn(None, self.style), "")

    def test_non_mac_string_with_no_colons_returns_input(self):
        fn = self._import_helper()
        result = fn("not-a-mac", self.style)
        self.assertEqual(result, "not-a-mac")
        self.assertNotIsInstance(result, self.Paragraph)

    def test_ib_gid_returns_paragraph_with_explicit_breaks(self):
        """20-byte IB GID must be wrapped in a Paragraph with <br/> separators
        so ReportLab can break it within the cell.
        """
        fn = self._import_helper()
        ib_gid = "80:00:01:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:80"
        result = fn(ib_gid, self.style)
        self.assertIsInstance(result, self.Paragraph)
        xml = getattr(result, "text", "") or result.getPlainText()
        self.assertIn("<br/>", xml)

    def test_ib_gid_splits_into_three_chunks_at_group_size_seven(self):
        """20 bytes / group_size=7 \u2192 chunks of 7 + 7 + 6 bytes."""
        fn = self._import_helper()
        ib_gid = "80:00:01:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:80"
        result = fn(ib_gid, self.style, group_size=7)
        self.assertIsInstance(result, self.Paragraph)
        xml = getattr(result, "text", "")
        chunks = xml.split("<br/>")
        self.assertEqual(len(chunks), 3, f"Expected 3 chunks, got {len(chunks)}: {chunks}")
        self.assertEqual(chunks[0], "80:00:01:07:fe:80:00")
        self.assertEqual(chunks[1], "00:00:00:00:00:a0:88")
        self.assertEqual(chunks[2], "c2:03:00:57:36:80")

    def test_seven_byte_mac_at_threshold_returns_string_not_paragraph(self):
        """Boundary: exactly group_size bytes \u2192 still returns string (no wrap)."""
        fn = self._import_helper()
        seven_byte = "00:11:22:33:44:55:66"  # exactly 7 bytes
        result = fn(seven_byte, self.style, group_size=7)
        self.assertEqual(result, seven_byte)
        self.assertNotIsInstance(result, self.Paragraph)

    def test_eight_byte_mac_just_above_threshold_wraps(self):
        fn = self._import_helper()
        eight_byte = "00:11:22:33:44:55:66:77"
        result = fn(eight_byte, self.style, group_size=7)
        self.assertIsInstance(result, self.Paragraph)


class TestRPT6ManualSwitchUPosition(unittest.TestCase):
    """RPT-6: convert Discovery UI top-U convention to rack diagram bottom-U.

    The Discovery UI (frontend/templates/reporter.html) stores ``u_position``
    as the TOP of the device occupied (highest U). Example: a 2U switch at
    U35 means span U34-U35, ``u_position=35``. The rack diagram renderer
    (src/rack_diagram.py ``_create_device_representation``) treats the same
    value as the BOTTOM of the device. Without conversion, 2U+ manual switch
    placements render one U too high in the rack diagram.

    Fix: ``_manual_switch_bottom_u(top_u, height_u)`` returns the lowest U
    occupied. For 1U devices top == bottom; for 2U+ bottom = top - (h - 1).
    """

    def _helper(self):
        return VastReportBuilder._manual_switch_bottom_u

    def test_1u_switch_returns_top_unchanged(self):
        """1U at U35: top equals bottom, no conversion needed."""
        self.assertEqual(self._helper()(35, 1), 35)

    def test_2u_switch_returns_top_minus_one(self):
        """2U at U35: spans U34-U35, bottom is U34."""
        self.assertEqual(self._helper()(35, 2), 34)

    def test_4u_switch_returns_top_minus_three(self):
        """4U at U33: spans U30-U33, bottom is U30."""
        self.assertEqual(self._helper()(33, 4), 30)

    def test_2u_switch_at_top_of_42u_rack(self):
        """2U at U42 (top of 42U rack): spans U41-U42, bottom is U41."""
        self.assertEqual(self._helper()(42, 2), 41)

    def test_height_zero_treated_as_1u(self):
        """Defensive: height=0 should not corrupt the position."""
        self.assertEqual(self._helper()(10, 0), 10)


class TestRPT6ManualSwitchBridge(unittest.TestCase):
    """RPT-6: ``_build_diagram_switch_entry`` is the bridge between
    ``manual_switch_placements`` (top-U convention) and the rack diagram
    renderer (bottom-U convention). The bridge MUST apply the U conversion
    so manual 2U+ switches render at the operator-intended position.
    """

    def _builder(self):
        return VastReportBuilder._build_diagram_switch_entry

    def test_1u_manual_placement_produces_top_u_unchanged(self):
        """1U switch: bridge emits rack_unit equal to the operator's input."""
        placement = {
            "switch_name": "sw1",
            "u_position": 35,
            "height_u": 1,
            "model": "msn4600c_1u_variant",
            "state": "ACTIVE",
        }
        entry = self._builder()(placement)
        self.assertEqual(entry["rack_unit"], "U35")

    def test_2u_manual_placement_emits_bottom_u(self):
        """2U switch at top-U=35: bridge MUST emit rack_unit='U34' (the bottom)."""
        placement = {
            "switch_name": "sw1",
            "u_position": 35,
            "height_u": 2,
            "model": "msn4600c",
            "state": "ACTIVE",
        }
        entry = self._builder()(placement)
        self.assertEqual(
            entry["rack_unit"],
            "U34",
            "RPT-6: 2U switch at top-U=35 must produce rack_unit='U34' "
            "(bottom-U), not 'U35' (top-U). The Discovery UI top-U "
            "convention is one slot higher than the rack diagram bottom-U "
            "convention; without conversion 2U switches render one U too high.",
        )

    def test_height_u_missing_defaults_to_1u(self):
        """When the placement omits height_u, treat as 1U (top == bottom)."""
        placement = {
            "switch_name": "sw1",
            "u_position": 35,
            "model": "switch",
            "state": "ACTIVE",
        }
        entry = self._builder()(placement)
        self.assertEqual(entry["rack_unit"], "U35")

    def test_bridge_preserves_id_model_state(self):
        """Bridge must preserve id (switch name), model, state for the diagram."""
        placement = {
            "switch_name": "sw1",
            "name": "sw1",
            "u_position": 35,
            "height_u": 2,
            "model": "msn4600c",
            "state": "ACTIVE",
        }
        entry = self._builder()(placement)
        self.assertEqual(entry["id"], "sw1")
        self.assertEqual(entry["model"], "msn4600c")
        self.assertEqual(entry["state"], "ACTIVE")


def _flowable_text(content):
    """Recursively collect plain text from a list of ReportLab flowables/cells."""
    out = []

    def walk(obj):
        if obj is None:
            return
        if isinstance(obj, str):
            out.append(obj)
            return
        if isinstance(obj, (list, tuple)):
            for item in obj:
                walk(item)
            return
        # ReportLab Paragraph
        get_plain = getattr(obj, "getPlainText", None)
        if callable(get_plain):
            try:
                out.append(get_plain())
                return
            except Exception:
                pass
        text_attr = getattr(obj, "text", None)
        if isinstance(text_attr, str):
            out.append(text_attr)
            return
        # ReportLab Table stores rows in _cellvalues
        cells = getattr(obj, "_cellvalues", None)
        if cells is not None:
            walk(cells)
            return
        # Wrappers like KeepTogether hold child flowables in _content
        children = getattr(obj, "_content", None)
        if isinstance(children, (list, tuple)):
            walk(children)

    walk(content)
    return "\n".join(out)


class TestNodeManagementMap(unittest.TestCase):
    """QP-1: Node Management Map tables (Device Name (VMS) | Hostname | Mgmt IP)."""

    def _data(self):
        return {
            "metadata": {"enhanced_features": {}},
            "cluster_summary": {"name": "LAMBDA-VAST-LAX-01", "psnt": "VA2553454"},
            "hardware_inventory": {
                "cnodes": [
                    {
                        "id": "1",
                        "name": "cnode-128-1",
                        "hostname": "RackP01C01-CB6-U22-CN1",
                        "mgmt_ip": "10.208.59.22",
                        "ipmi_ip": "192.168.3.1",
                    }
                ],
                "dnodes": [
                    {
                        "id": "5",
                        "name": "dnode-128-104",
                        "hostname": "RackP01C01-DB2-U4-DN1",
                        "mgmt_ip": "10.208.59.106",
                        "ipmi_ip": "192.168.3.21",
                    }
                ],
            },
            "sections": {},
        }

    def test_management_map_tables_present(self):
        """Both CNode and DNode Management Map tables render with their titles."""
        builder = VastReportBuilder()
        text = _flowable_text(builder._create_comprehensive_network_configuration(self._data()))
        self.assertIn("CNode Management Map", text)
        self.assertIn("DNode Management Map", text)
        self.assertIn("Device Name (VMS)", text)

    def test_management_map_maps_name_hostname_mgmt_ip(self):
        """Each node row carries VMS name, hostname, and external mgmt IP together."""
        builder = VastReportBuilder()
        text = _flowable_text(builder._create_comprehensive_network_configuration(self._data()))
        # Hostname appears only in the new map (existing node tables show name, not hostname)
        self.assertIn("RackP01C01-CB6-U22-CN1", text)
        self.assertIn("cnode-128-1", text)
        self.assertIn("10.208.59.22", text)
        self.assertIn("RackP01C01-DB2-U4-DN1", text)
        self.assertIn("dnode-128-104", text)


class TestVnetmapTopologySwitchIdentity(unittest.TestCase):
    """QP-1: Port Mapping tables resolve switch GUID -> hostname -> mgmt IP."""

    def _args(self):
        from reportlab.lib.styles import getSampleStyleSheet

        port_map = [
            {
                "node_hostname": "RackP01C01-CB6-U22-CN1",
                "node_ip": "172.16.128.5",
                "interface": "ib0",
                "mac": "aa:bb:cc:dd:ee:ff",
                "network": "A",
                "switch_ip": "0xa088c203007860bc",
                "switch_hostname": "SW-LF-03",
                "port": "24",
            }
        ]
        switches = [{"name": "SW-LF-03", "hostname": "SW-LF-03", "mgmt_ip": "10.208.59.15", "model": "MQM8700-HS2F"}]
        return port_map, switches, getSampleStyleSheet()

    def test_full_topology_shows_mgmt_ip_not_guid(self):
        builder = VastReportBuilder()
        port_map, switches, styles = self._args()
        text = _flowable_text(builder._create_vnetmap_topology_tables(port_map, switches, styles))
        self.assertIn("Switch Mgmt IP", text)
        self.assertIn("10.208.59.15", text)

    def test_per_switch_title_has_name_guid_mgmt_ip(self):
        builder = VastReportBuilder()
        port_map, switches, styles = self._args()
        text = _flowable_text(builder._create_vnetmap_topology_tables(port_map, switches, styles))
        self.assertIn("SW-LF-03", text)
        self.assertIn("0xa088c203007860bc", text)
        self.assertIn("10.208.59.15", text)


class TestSwitchConfigActivePortsMtu(unittest.TestCase):
    """QP-1: Active Ports + Port MTU recomputed from ports[] for replayed JSON."""

    def _ports(self):
        ports = [{"name": f"IB1/{i}", "state": "Active", "speed": "200G", "mtu": "4096"} for i in range(1, 39)]
        ports += [{"name": "IB1/39", "state": "Down", "speed": "-", "mtu": "0"}]
        ports += [{"name": "IB1/40", "state": "Down", "speed": "-", "mtu": "0"}]
        return ports

    def test_count_active_ports_counts_up_and_active(self):
        self.assertEqual(VastReportBuilder._count_active_ports(self._ports()), 38)

    def test_derive_port_mtu_picks_most_common_nonzero(self):
        self.assertEqual(VastReportBuilder._derive_port_mtu(self._ports()), "4096")

    def test_switch_config_recomputes_blank_active_ports_and_mtu(self):
        builder = VastReportBuilder()
        data = {
            "hardware_inventory": {
                "switches": [
                    {
                        "name": "SW-LF-03",
                        "hostname": "SW-LF-03",
                        "mgmt_ip": "10.208.59.15",
                        "total_ports": 40,
                        "active_ports": 0,
                        "mtu": 0,
                        "ports": self._ports(),
                    }
                ]
            }
        }
        text = _flowable_text(builder._create_switch_configuration(data))
        self.assertIn("Active Ports", text)
        self.assertIn("38", text)
        self.assertIn("4096", text)


if __name__ == "__main__":
    unittest.main()
