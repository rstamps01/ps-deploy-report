"""
Tests for port mapping modules: port_mapper, vnetmap_parser, enhanced_port_mapper.

Covers PortMapper designation generation, cross-connection detection,
VNetMapParser file parsing, and EnhancedPortMapper enhanced mappings.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from port_mapper import PortMapper  # noqa: E402
from vnetmap_parser import VNetMapParser  # noqa: E402


class TestPortMapperInit(unittest.TestCase):
    """Verify PortMapper initialization and node-to-box assignment."""

    def _make_mapper(self, cboxes=None, dboxes=None, cnodes=None, dnodes=None, switches=None):
        return PortMapper(
            cboxes=cboxes or [],
            dboxes=dboxes or [],
            cnodes=cnodes or [],
            dnodes=dnodes or [],
            switches=switches or [],
        )

    def test_empty_init(self):
        mapper = self._make_mapper()
        summary = mapper.get_port_map_summary()
        self.assertEqual(summary["cboxes"], 0)
        self.assertEqual(summary["cnodes"], 0)

    def test_sorts_cnodes_by_ip(self):
        cnodes = [
            {"id": 2, "ip": "10.0.0.5"},
            {"id": 1, "ip": "10.0.0.1"},
        ]
        mapper = self._make_mapper(cnodes=cnodes)
        self.assertEqual(mapper.cnodes[0]["ip"], "10.0.0.1")
        self.assertEqual(mapper.cnodes[1]["ip"], "10.0.0.5")

    def test_assigns_cnodes_to_cboxes_default_capacity(self):
        cboxes = [{"id": 1, "serial_number": "CB001"}]
        cnodes = [{"id": 1, "ip": "10.0.0.1"}]
        mapper = self._make_mapper(cboxes=cboxes, cnodes=cnodes)
        self.assertEqual(mapper.cnode_to_cbox, {"CN1": "CB1"})

    def test_assigns_dnodes_to_dboxes_ceres_v2(self):
        dboxes = [{"id": 1, "hardware_type": "ceres_v2"}]
        dnodes = [
            {"id": 1, "ip": "10.0.0.101"},
            {"id": 2, "ip": "10.0.0.102"},
        ]
        mapper = self._make_mapper(dboxes=dboxes, dnodes=dnodes)
        self.assertEqual(mapper.dnode_to_dbox, {"DN1": "DB1", "DN2": "DB1"})

    def test_assigns_dnodes_to_dboxes_ceres_4_capacity(self):
        dboxes = [{"id": 1, "hardware_type": "ceres"}]
        dnodes = [{"id": i, "ip": f"10.0.0.{100+i}"} for i in range(1, 5)]
        mapper = self._make_mapper(dboxes=dboxes, dnodes=dnodes)
        for i in range(1, 5):
            self.assertEqual(mapper.dnode_to_dbox[f"DN{i}"], "DB1")

    def test_dell_ice_cbox_has_4_capacity(self):
        cboxes = [{"id": 1, "box_vendor": "Dell Ice Lake"}]
        cnodes = [{"id": i, "ip": f"10.0.0.{i}"} for i in range(1, 5)]
        mapper = self._make_mapper(cboxes=cboxes, cnodes=cnodes)
        for i in range(1, 5):
            self.assertEqual(mapper.cnode_to_cbox[f"CN{i}"], "CB1")


class TestPortMapperDesignations(unittest.TestCase):
    """Test port designation generation."""

    def setUp(self):
        self.cboxes = [{"id": 1, "serial_number": "CB001"}]
        self.dboxes = [{"id": 1, "hardware_type": "ceres_v2"}]
        self.cnodes = [{"id": 1, "ip": "10.0.0.1"}, {"id": 2, "ip": "10.0.0.2"}]
        self.dnodes = [{"id": 1, "ip": "10.0.0.101"}, {"id": 2, "ip": "10.0.0.102"}]
        self.switches = [
            {"id": 1, "mgmt_ip": "10.0.0.201"},
            {"id": 2, "mgmt_ip": "10.0.0.202"},
        ]
        self.mapper = PortMapper(self.cboxes, self.dboxes, self.cnodes, self.dnodes, self.switches)

    def test_cnode_designation_network_a(self):
        designation, ntype = self.mapper.generate_node_designation("10.0.0.1", "A")
        self.assertEqual(ntype, "CNode")
        self.assertIn("CB1-CN1-R", designation)

    def test_cnode_designation_network_b(self):
        designation, _ntype = self.mapper.generate_node_designation("10.0.0.1", "B")
        self.assertIn("-L", designation)

    def test_dnode_designation(self):
        designation, ntype = self.mapper.generate_node_designation("10.0.0.101", "A")
        self.assertEqual(ntype, "DNode")
        self.assertIn("DB1-DN1-R", designation)

    def test_unknown_cnode_returns_question_mark(self):
        designation, node_type = self.mapper.generate_node_designation("10.0.0.99", "A")
        self.assertIn("?", designation)

    def test_switch_designation(self):
        result = self.mapper.generate_switch_designation("10.0.0.201", "swp20")
        self.assertEqual(result, "SWA-P20")

    def test_switch_designation_second_switch(self):
        result = self.mapper.generate_switch_designation("10.0.0.202", "swp5")
        self.assertEqual(result, "SWB-P5")

    def test_switch_designation_unknown_ip(self):
        result = self.mapper.generate_switch_designation("10.0.0.99", "swp1")
        self.assertIn("?", result)


class TestPortMapperCrossConnection(unittest.TestCase):
    """Test cross-connection detection."""

    def setUp(self):
        self.switches = [
            {"id": 1, "mgmt_ip": "10.0.0.201"},
            {"id": 2, "mgmt_ip": "10.0.0.202"},
        ]
        self.mapper = PortMapper([], [], [], [], self.switches)

    def test_correct_connection_switch_a_network_a(self):
        is_cross, expected = self.mapper.detect_cross_connection("10.0.0.201", "10.0.0.1", "A")
        self.assertFalse(is_cross)
        self.assertEqual(expected, "A")

    def test_cross_connection_switch_a_network_b(self):
        is_cross, expected = self.mapper.detect_cross_connection("10.0.0.201", "10.0.0.1", "B")
        self.assertTrue(is_cross)
        self.assertEqual(expected, "A")

    def test_correct_connection_switch_b_network_b(self):
        is_cross, _expected = self.mapper.detect_cross_connection("10.0.0.202", "10.0.0.1", "B")
        self.assertFalse(is_cross)

    def test_unknown_switch_returns_false(self):
        is_cross, expected = self.mapper.detect_cross_connection("10.0.0.99", "10.0.0.1", "A")
        self.assertFalse(is_cross)
        self.assertEqual(expected, "Unknown")


class TestPortMapperSummary(unittest.TestCase):

    def test_summary_counts(self):
        mapper = PortMapper(
            cboxes=[{"id": 1}],
            dboxes=[{"id": 1}, {"id": 2}],
            cnodes=[{"id": 1, "ip": "10.0.0.1"}],
            dnodes=[{"id": 1, "ip": "10.0.0.101"}],
            switches=[{"id": 1, "mgmt_ip": "10.0.0.201"}],
        )
        summary = mapper.get_port_map_summary()
        self.assertEqual(summary["cboxes"], 1)
        self.assertEqual(summary["dboxes"], 2)
        self.assertEqual(summary["cnodes"], 1)
        self.assertEqual(summary["dnodes"], 1)
        self.assertEqual(summary["switches"], 1)


class TestVNetMapParserMissingFile(unittest.TestCase):

    def test_parse_missing_file_returns_unavailable(self):
        parser = VNetMapParser("/nonexistent/file.txt")
        result = parser.parse()
        self.assertFalse(result["available"])
        self.assertIn("not found", result["error"])
        self.assertEqual(result["topology"], [])
        self.assertEqual(result["cross_connections"], [])


class TestVNetMapParserParsing(unittest.TestCase):

    def _write_vnetmap(self, content: str) -> str:
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False)
        f.write(content)
        f.close()
        return f.name

    def test_parse_valid_topology(self):
        content = (
            "Full topology\n"
            "cnode-1  10.0.0.201  swp1   10.0.0.1   eth0  aa:bb:cc:dd:ee:01  A\n"
            "dnode-1  10.0.0.201  swp5   10.0.0.101 eth0  aa:bb:cc:dd:ee:02  A\n"
            "\n"
        )
        path = self._write_vnetmap(content)
        try:
            parser = VNetMapParser(path)
            result = parser.parse()
            self.assertTrue(result["available"])
            self.assertEqual(result["total_connections"], 2)
            self.assertEqual(result["topology"][0]["hostname"], "cnode-1")
            self.assertEqual(result["topology"][0]["switch_ip"], "10.0.0.201")
            self.assertEqual(result["topology"][0]["port"], "swp1")
            self.assertEqual(result["topology"][0]["network"], "A")
        finally:
            os.unlink(path)

    def test_parse_empty_topology(self):
        content = "Some header info\nNo topology section here\n"
        path = self._write_vnetmap(content)
        try:
            parser = VNetMapParser(path)
            result = parser.parse()
            self.assertTrue(result["available"])
            self.assertEqual(result["total_connections"], 0)
        finally:
            os.unlink(path)

    def test_connections_by_switch(self):
        content = (
            "Full topology\n"
            "cnode-1  10.0.0.201  swp1   10.0.0.1   eth0  aa:bb:cc:dd:ee:01  A\n"
            "cnode-2  10.0.0.202  swp2   10.0.0.2   eth0  aa:bb:cc:dd:ee:02  B\n"
            "\n"
        )
        path = self._write_vnetmap(content)
        try:
            parser = VNetMapParser(path)
            parser.parse()
            by_switch = parser.get_connections_by_switch()
            self.assertIn("10.0.0.201", by_switch)
            self.assertIn("10.0.0.202", by_switch)
            self.assertEqual(len(by_switch["10.0.0.201"]), 1)
        finally:
            os.unlink(path)

    def test_connections_by_node(self):
        content = (
            "Full topology\n"
            "cnode-1  10.0.0.201  swp1   10.0.0.1   eth0  aa:bb:cc:dd:ee:01  A\n"
            "cnode-1  10.0.0.202  swp1   10.0.0.1   eth1  aa:bb:cc:dd:ee:02  B\n"
            "\n"
        )
        path = self._write_vnetmap(content)
        try:
            parser = VNetMapParser(path)
            parser.parse()
            by_node = parser.get_connections_by_node()
            self.assertEqual(len(by_node["cnode-1"]), 2)
        finally:
            os.unlink(path)

    def test_get_node_ips_separates_cnodes_and_dnodes(self):
        content = (
            "Full topology\n"
            "cnode-1  10.0.0.201  swp1   10.0.0.1   eth0  aa:bb:cc:dd:ee:01  A\n"
            "dnode-1  10.0.0.201  swp5   10.0.0.101 eth0  aa:bb:cc:dd:ee:02  A\n"
            "\n"
        )
        path = self._write_vnetmap(content)
        try:
            parser = VNetMapParser(path)
            parser.parse()
            ips = parser.get_node_ips()
            self.assertIn("10.0.0.1", ips["cnodes"])
            self.assertIn("10.0.0.101", ips["dnodes"])
        finally:
            os.unlink(path)

    def test_no_cross_connections(self):
        content = "Full topology\ncnode-1  10.0.0.201  swp1   10.0.0.1   eth0  aa:bb:01  A\n\n"
        path = self._write_vnetmap(content)
        try:
            parser = VNetMapParser(path)
            parser.parse()
            self.assertFalse(parser.has_cross_connections())
            self.assertIn("No cross-connections", parser.get_cross_connection_summary())
        finally:
            os.unlink(path)

    def test_extract_port_number(self):
        parser = VNetMapParser("/dev/null")
        self.assertEqual(parser._extract_port_number("swp20"), 20)
        self.assertEqual(parser._extract_port_number("eth1/1"), 1)
        self.assertEqual(parser._extract_port_number("nodigits"), 0)


class TestEnhancedPortMapper(unittest.TestCase):
    """Test EnhancedPortMapper with mocked dependencies."""

    def test_import_succeeds(self):
        from enhanced_port_mapper import EnhancedPortMapper

        self.assertIsNotNone(EnhancedPortMapper)

    def test_init_with_hardware(self):
        from enhanced_port_mapper import EnhancedPortMapper

        mapper = EnhancedPortMapper(
            cboxes=[{"id": 1, "serial_number": "CB001"}],
            dboxes=[{"id": 1, "hardware_type": "ceres_v2"}],
            cnodes=[{"id": 1, "ip": "10.0.0.1", "name": "cnode-1"}],
            dnodes=[{"id": 1, "ip": "10.0.0.101", "name": "dnode-1"}],
            switches=[{"id": 1, "mgmt_ip": "10.0.0.201", "name": "sw-A"}],
        )
        self.assertIsNotNone(mapper)

    def test_is_ipl_port(self):
        from enhanced_port_mapper import EnhancedPortMapper

        mapper = EnhancedPortMapper([], [], [], [], [])
        self.assertTrue(mapper.is_ipl_port("swp31", "100G"))
        self.assertTrue(mapper.is_ipl_port("swp32", "100G"))
        self.assertFalse(mapper.is_ipl_port("swp1", "25G"))

    def test_generate_enhanced_port_map_empty(self):
        from enhanced_port_mapper import EnhancedPortMapper

        mapper = EnhancedPortMapper([], [], [], [], [])
        result = mapper.generate_enhanced_port_map([])
        self.assertEqual(result["total_connections"], 0)
        self.assertIn("port_map", result)

    def test_build_node_maps_uses_node_type_field(self):
        """Nodes should be classified by their node_type field, not interface heuristics."""
        from enhanced_port_mapper import EnhancedPortMapper

        external_port_map = [
            {
                "node_ip": "172.16.128.1",
                "node_hostname": "cnode-host-01",
                "node_type": "Cnode",
                "interface": "ens1f0",
                "box_name": "cbox-ABC",
            },
            {
                "node_ip": "172.16.128.102",
                "node_hostname": "aidc-vast01-d102",
                "node_type": "Dnode",
                "interface": "ens3",
                "box_name": "dbox-225PF029",
            },
            {
                "node_ip": "172.16.128.103",
                "node_hostname": "Rack-DB1-UU7-bottom",
                "node_type": "Dnode",
                "interface": "ens14",
                "box_name": "dbox-25APF04F",
            },
        ]
        mapper = EnhancedPortMapper(
            cboxes=[], dboxes=[], cnodes=[], dnodes=[], switches=[],
            external_port_map=external_port_map,
        )
        self.assertIn("172.16.128.1", mapper.cnode_map)
        self.assertIn("172.16.128.102", mapper.dnode_map)
        self.assertIn("172.16.128.103", mapper.dnode_map)
        self.assertNotIn("172.16.128.102", mapper.cnode_map)
        self.assertNotIn("172.16.128.103", mapper.cnode_map)

    def test_build_node_maps_dbox_numbering(self):
        """DNodes from different DBoxes should get distinct dbox_num values."""
        from enhanced_port_mapper import EnhancedPortMapper

        external_port_map = [
            {
                "node_ip": "172.16.128.102",
                "node_hostname": "dnode-a",
                "node_type": "Dnode",
                "interface": "ens3",
                "box_name": "dbox-AAA",
            },
            {
                "node_ip": "172.16.128.103",
                "node_hostname": "dnode-b",
                "node_type": "Dnode",
                "interface": "ens14",
                "box_name": "dbox-AAA",
            },
            {
                "node_ip": "172.16.128.104",
                "node_hostname": "dnode-c",
                "node_type": "Dnode",
                "interface": "ens3",
                "box_name": "dbox-BBB",
            },
        ]
        mapper = EnhancedPortMapper(
            cboxes=[], dboxes=[], cnodes=[], dnodes=[], switches=[],
            external_port_map=external_port_map,
        )
        dbox_nums = {ip: info["dbox_num"] for ip, info in mapper.dnode_map.items()}
        self.assertEqual(dbox_nums["172.16.128.102"], dbox_nums["172.16.128.103"])
        self.assertNotEqual(dbox_nums["172.16.128.102"], dbox_nums["172.16.128.104"])

    def test_build_node_maps_fallback_heuristic(self):
        """When node_type is missing, the interface/hostname heuristic applies."""
        from enhanced_port_mapper import EnhancedPortMapper

        external_port_map = [
            {
                "node_ip": "172.16.0.1",
                "node_hostname": "host-d-105",
                "node_type": "",
                "interface": "enp3s0f0",
                "box_name": "",
            },
            {
                "node_ip": "172.16.0.2",
                "node_hostname": "some-cnode-host",
                "node_type": "",
                "interface": "enp129s0f0",
                "box_name": "",
            },
        ]
        mapper = EnhancedPortMapper(
            cboxes=[], dboxes=[], cnodes=[], dnodes=[], switches=[],
            external_port_map=external_port_map,
        )
        self.assertIn("172.16.0.1", mapper.dnode_map)
        self.assertIn("172.16.0.2", mapper.cnode_map)

    def test_dnode_designation_format(self):
        """DNodes should produce DB#-DN#-R/L designations."""
        from enhanced_port_mapper import EnhancedPortMapper

        external_port_map = [
            {
                "node_ip": "172.16.128.102",
                "node_hostname": "dnode-1",
                "node_type": "Dnode",
                "interface": "ens3",
                "switch_ip": "10.0.0.201",
                "port": "swp5",
                "mac": "aa:bb:cc:dd:ee:01",
                "network": "A",
                "port_side": "R",
                "box_name": "dbox-X",
                "notes": "",
            },
        ]
        mapper = EnhancedPortMapper(
            cboxes=[], dboxes=[], cnodes=[], dnodes=[],
            switches=[{"mgmt_ip": "10.0.0.201", "name": "sw-A"}],
            external_port_map=external_port_map,
        )
        result = mapper.generate_enhanced_port_map(external_port_map)
        entry = result["port_map"][0]
        self.assertEqual(entry["node_type"], "dnode")
        self.assertIn("DB", entry["node_designation"])
        self.assertIn("DN", entry["node_designation"])


class TestPortSpeedLookup(unittest.TestCase):
    """Verify that the switch port speed lookup map is constructed correctly."""

    def test_speed_lookup_maps_swp_to_eth_speed(self):
        """Switch inventory Eth1/N names should map to swpN for speed lookup."""
        switches = [
            {
                "mgmt_ip": "10.0.0.201",
                "name": "sw-A",
                "ports": [
                    {"name": "Eth1/1", "speed": "100G"},
                    {"name": "Eth1/5", "speed": "100G"},
                    {"name": "Eth1/11/1", "speed": "50G"},
                ],
            }
        ]
        lookup: dict[str, dict[str, str]] = {}
        for switch in switches:
            mgmt_ip = switch.get("mgmt_ip")
            speed_map: dict[str, str] = {}
            for port_info in switch.get("ports", []):
                port_name = port_info.get("name", "")
                port_speed = port_info.get("speed", "")
                if port_name and port_speed:
                    speed_map[port_name] = port_speed
                    if port_name.startswith("Eth") and "/" in port_name:
                        parts = port_name.split("/")
                        if len(parts) == 2:
                            speed_map[f"swp{parts[1]}"] = port_speed
                        elif len(parts) == 3:
                            speed_map[f"swp{parts[1]}/{parts[2]}"] = port_speed
            if mgmt_ip:
                lookup[mgmt_ip] = speed_map

        self.assertEqual(lookup["10.0.0.201"]["swp1"], "100G")
        self.assertEqual(lookup["10.0.0.201"]["swp5"], "100G")
        self.assertEqual(lookup["10.0.0.201"]["Eth1/1"], "100G")
        self.assertEqual(lookup["10.0.0.201"]["swp11/1"], "50G")
        self.assertNotIn("swp999", lookup["10.0.0.201"])

    def test_speed_lookup_missing_port_returns_empty(self):
        """Unknown port names should not be in the lookup."""
        switches = [
            {
                "mgmt_ip": "10.0.0.201",
                "name": "sw-A",
                "ports": [{"name": "Eth1/5", "speed": "100G"}],
            }
        ]
        lookup: dict[str, dict[str, str]] = {}
        for switch in switches:
            mgmt_ip = switch.get("mgmt_ip")
            speed_map: dict[str, str] = {}
            for port_info in switch.get("ports", []):
                port_name = port_info.get("name", "")
                port_speed = port_info.get("speed", "")
                if port_name and port_speed:
                    speed_map[port_name] = port_speed
                    if port_name.startswith("Eth") and "/" in port_name:
                        parts = port_name.split("/")
                        if len(parts) == 2:
                            speed_map[f"swp{parts[1]}"] = port_speed
            if mgmt_ip:
                lookup[mgmt_ip] = speed_map

        self.assertEqual(lookup["10.0.0.201"].get("swp20", ""), "")


class TestExternalPortMapperImport(unittest.TestCase):
    """Verify ExternalPortMapper can be imported and basic structure is sound."""

    def test_import_succeeds(self):
        from external_port_mapper import ExternalPortMapper

        self.assertIsNotNone(ExternalPortMapper)

    @patch("external_port_mapper.subprocess.run")
    @patch("external_port_mapper.shutil.which", return_value=None)
    def test_parse_cumulus_mac_table(self, mock_which, mock_run):
        from external_port_mapper import ExternalPortMapper

        mapper = ExternalPortMapper(
            cluster_ip="10.0.0.100",
            api_user="admin",
            api_password="test",
            cnode_ip="10.0.0.1",
            node_user="vastdata",
            node_password="test",
            switch_ips=["10.0.0.201"],
            switch_user="cumulus",
            switch_password="test",
        )
        raw_output = (
            "VLAN      Mac Address          Type     Port\n"
            "untagged  aa:bb:cc:dd:ee:01    dynamic  swp1\n"
            "untagged  aa:bb:cc:dd:ee:02    dynamic  swp5\n"
        )
        result = mapper._parse_cumulus_mac_table(raw_output)
        self.assertIn("aa:bb:cc:dd:ee:01", result)
        self.assertEqual(result["aa:bb:cc:dd:ee:01"]["port"], "swp1")


if __name__ == "__main__":
    unittest.main()
