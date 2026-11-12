"""NET-7 unit tests for ``EnhancedPortMapper`` with name-keyed switches.

Node-side LLDP (``vnetmap_lldp.py``) reports each switch by its LLDP system
name. The extractor rewrites a row's ``switch_ip`` to the VMS ``mgmt_ip``
when the name resolves, and otherwise keeps the name as the key and adds a
synthetic switch entry (``mgmt_ip`` = name, ``registered_in_vms: False``).
The mapper must letter such switches from the rows' ``network`` label and
never fall through to ``Unknown switch IP`` / ``SW?-<port>``.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enhanced_port_mapper import EnhancedPortMapper  # noqa: E402
from vnetmap_lldp_parser import parse_lldp_text  # noqa: E402

_FIXTURE = Path(__file__).parent / "fixtures" / "vnetmap_lldp" / "onyx_show_mapping.txt"


def _synthetic_switch(name: str) -> Dict[str, Any]:
    return {"mgmt_ip": name, "hostname": name, "name": name, "discovered_via": "lldp", "registered_in_vms": False}


def _fixture_rows() -> List[Dict[str, Any]]:
    return parse_lldp_text(_FIXTURE.read_text())["topology"]


def _mapper(switches: List[Dict[str, Any]], rows: List[Dict[str, Any]]) -> EnhancedPortMapper:
    return EnhancedPortMapper(cboxes=[], dboxes=[], cnodes=[], dnodes=[], switches=switches, external_port_map=rows)


class TestNameKeyedSwitches:
    def test_designation_follows_network_label_not_name(self):
        """ACME-SW-02 serves network A in the fixture, so it is SWA even though
        ACME-SW-01 sorts first by name."""
        rows = _fixture_rows()
        assert {r["switch_name"]: r["network"] for r in rows} == {"ACME-SW-01": "B", "ACME-SW-02": "A"}

        mapper = _mapper([_synthetic_switch("ACME-SW-01"), _synthetic_switch("ACME-SW-02")], rows)

        assert mapper.switch_map["ACME-SW-02"]["designation"] == "SWA"
        assert mapper.switch_map["ACME-SW-01"]["designation"] == "SWB"
        assert mapper.get_switch_hostname("ACME-SW-01") == "ACME-SW-01"

    def test_port_labels_render_without_unknown_switch(self, caplog):
        rows = _fixture_rows()
        mapper = _mapper([_synthetic_switch("ACME-SW-01"), _synthetic_switch("ACME-SW-02")], rows)

        with caplog.at_level(logging.WARNING, logger="enhanced_port_mapper"):
            result = mapper.generate_enhanced_port_map(rows)

        assert "Unknown switch IP" not in caplog.text
        designations = {(e["node_hostname"], e["interface"]): e["switch_designation"] for e in result["port_map"]}
        assert not any(d.startswith("SW?") for d in designations.values())
        assert designations[("acme-cn1", "enp7s0f0")] == "SWA-P1/1"
        assert designations[("acme-cn1", "enp7s0f1")] == "SWB-P1/1"
        assert designations[("acme-dn1", "enp3s0f0np0")] == "SWA-P13/1"
        node_designations = {(e["node_hostname"], e["interface"]): e["node_designation"] for e in result["port_map"]}
        assert node_designations[("acme-cn1", "enp7s0f0")] == "CB1-CN1-R"
        assert node_designations[("acme-cn1", "enp7s0f1")] == "CB1-CN1-L"
        assert node_designations[("acme-dn2", "enp3s0f0np0")] == "DB2-DN2-R"

    def test_cumulus_port_names(self):
        rows = [
            {"switch_ip": "ACME-SW-01", "port": "swp1s0", "node_ip": "198.51.100.10", "network": "A"},
            {"switch_ip": "ACME-SW-02", "port": "swp1s0", "node_ip": "203.0.113.10", "network": "B"},
        ]
        mapper = _mapper([_synthetic_switch("ACME-SW-02"), _synthetic_switch("ACME-SW-01")], rows)
        assert mapper.generate_switch_designation("ACME-SW-01", "swp1s0") == "SWA-P1s0"
        assert mapper.generate_switch_designation("ACME-SW-02", "swp1s0") == "SWB-P1s0"

    def test_unlabelled_switches_sort_last_then_by_name(self):
        rows = [
            {"switch_ip": "ACME-SW-03", "port": "swp1", "node_ip": "198.51.100.10", "network": ""},
            {"switch_ip": "ACME-SW-09", "port": "swp1", "node_ip": "198.51.100.11", "network": "B"},
            {"switch_ip": "ACME-SW-02", "port": "swp1", "node_ip": "198.51.100.12", "network": ""},
        ]
        names = ["ACME-SW-03", "ACME-SW-09", "ACME-SW-02"]
        mapper = _mapper([_synthetic_switch(n) for n in names], rows)
        assert [mapper.switch_map[n]["designation"] for n in ("ACME-SW-09", "ACME-SW-02", "ACME-SW-03")] == [
            "SWA",
            "SWB",
            "SWC",
        ]

    def test_registered_switch_absent_from_lldp_is_spine(self):
        rows = _fixture_rows()
        switches = [
            _synthetic_switch("ACME-SW-01"),
            _synthetic_switch("ACME-SW-02"),
            {"name": "ACME-SP-01", "hostname": "ACME-SP-01", "mgmt_ip": "192.0.2.250"},
        ]
        mapper = _mapper(switches, rows)
        assert mapper.switch_map["192.0.2.250"]["role"] == "spine"
        assert mapper.switch_map["192.0.2.250"]["designation"] == "SP1"


class TestMixedResolvedAndUnresolved:
    def test_one_resolved_ip_one_name(self):
        """ACME-SW-01 resolved to a VMS mgmt_ip (rows rewritten); ACME-SW-02 did not."""
        rows = _fixture_rows()
        for row in rows:
            if row["switch_name"] == "ACME-SW-01":
                row["switch_ip"] = "192.0.2.201"
        switches = [
            {"name": "ACME-SW-01", "hostname": "ACME-SW-01", "mgmt_ip": "192.0.2.201"},
            _synthetic_switch("ACME-SW-02"),
        ]
        mapper = _mapper(switches, rows)
        result = mapper.generate_enhanced_port_map(rows)

        assert mapper.switch_map["ACME-SW-02"]["designation"] == "SWA"
        assert mapper.switch_map["192.0.2.201"]["designation"] == "SWB"
        by_switch = {e["switch_ip"]: e["switch_hostname"] for e in result["port_map"]}
        assert by_switch == {"192.0.2.201": "ACME-SW-01", "ACME-SW-02": "ACME-SW-02"}
        assert not any(e["switch_designation"].startswith("SW?") for e in result["port_map"])

    def test_unrewritten_name_row_aliases_to_registered_switch(self):
        """A row still keyed by the name resolves to the VMS switch by name, case-insensitively."""
        rows = [
            {"switch_ip": "acme-sw-01", "port": "Eth1/1/1", "node_ip": "198.51.100.11", "network": "A"},
            {"switch_ip": "ACME-SW-02", "port": "Eth1/1/1", "node_ip": "203.0.113.11", "network": "B"},
        ]
        switches = [
            {"name": "ACME-SW-01", "mgmt_ip": "192.0.2.201"},
            _synthetic_switch("ACME-SW-02"),
        ]
        mapper = _mapper(switches, rows)

        assert mapper.switch_map["192.0.2.201"]["role"] == "leaf"
        assert mapper.switch_map["acme-sw-01"] is mapper.switch_map["192.0.2.201"]
        assert mapper.generate_switch_designation("acme-sw-01", "Eth1/1/1") == "SWA-P1/1"
        assert mapper.generate_switch_designation("ACME-SW-02", "Eth1/1/1") == "SWB-P1/1"


class TestIpKeyedUnchanged:
    def test_ip_keyed_leaves_still_letter_by_mgmt_ip(self):
        """Network labels only order leaves when a key is not an IP."""
        rows = [
            {"switch_ip": "192.0.2.1", "port": "swp1", "node_ip": "203.0.113.10", "network": "B"},
            {"switch_ip": "192.0.2.2", "port": "swp1", "node_ip": "198.51.100.10", "network": "A"},
        ]
        switches = [{"name": "sw-2", "mgmt_ip": "192.0.2.2"}, {"name": "sw-1", "mgmt_ip": "192.0.2.1"}]
        mapper = _mapper(switches, rows)
        assert mapper.switch_map["192.0.2.1"]["designation"] == "SWA"
        assert mapper.switch_map["192.0.2.2"]["designation"] == "SWB"

    def test_is_ipv4_guard(self):
        assert EnhancedPortMapper._is_ipv4("192.0.2.1")
        assert not EnhancedPortMapper._is_ipv4("ACME-SW-01")
        assert not EnhancedPortMapper._is_ipv4("0xb83fd20300e856b8")
        assert not EnhancedPortMapper._is_ipv4(None)
