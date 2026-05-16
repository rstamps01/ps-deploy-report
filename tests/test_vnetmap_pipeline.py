"""Unit tests for the vnetmap data pipeline.

Covers:
  - VNetMapParser: LLDP neighbor parsing, node_hostname alias
  - EnhancedPortMapper: Eth1/X/Y breakout port normalisation
  - Vnetmap file discovery helper in app.py
  - DataExtractor vnetmap extraction path
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ---------------------------------------------------------------------------
# VNetMapParser
# ---------------------------------------------------------------------------

SAMPLE_VNETMAP_OUTPUT = """\
Full topology
cnode-1    10.128.101.141    Eth1/15/1    10.0.0.1    f0    aa:bb:cc:dd:ee:01    A
cnode-1    10.128.101.142    Eth1/16/1    10.0.0.1    f1    aa:bb:cc:dd:ee:02    B
cnode-2    10.128.101.141    Eth1/17/1    10.0.0.2    f0    aa:bb:cc:dd:ee:03    A
cnode-2    10.128.101.142    Eth1/18/1    10.0.0.2    f1    aa:bb:cc:dd:ee:04    B

LLDP neighbors on 10.128.101.141:
    Eth1/1    10.128.101.142    Eth1/1
    Eth1/2    10.128.101.142    Eth1/2
"""


SAMPLE_IB_VNETMAP_OUTPUT = """\
Mapping nodes ['172.16.128.1', '172.16.128.2'] to IB Switches

Full topology

c-128-1                   0xb83fd20300e856b8     19   172.16.0.1      ib2          80:00:01:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:80 A
c-128-1                   0xb83fd20300e85d18     19   172.16.64.1     ib3          80:00:09:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:81 B
B2-CB2-U33-CN1            0xb83fd20300e856b8     25   172.16.0.5      ib1          80:00:10:4a:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:2c:b0 A
B2-CB2-U33-CN1            0xb83fd20300e85d18     25   172.16.64.5     ib2          80:00:11:4a:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:2c:b1 B

Switch MF0;vast-switch1-bot:MQM8700/U1 - 0xb83fd20300e856b8 has {'172.16.0'}, network {'B', 'A'},  should be only one be in either range 172.16.{0..63} or in range 172.16.{64..127}

c-128-1                   19           172.16.0.1      ib2          80:00:01:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:80 A
B2-CB2-U33-CN1            25           172.16.0.5      ib1          80:00:10:4a:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:2c:b0 A

Switch MF0;vast-switch2-top:MQM8700/U1 - 0xb83fd20300e85d18 has {'172.16.64'}, network {'B', 'A'},  should be only one be in either range 172.16.{0..63} or in range 172.16.{64..127}

c-128-1                   19           172.16.64.1     ib3          80:00:09:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:81 B
B2-CB2-U33-CN1            25           172.16.64.5     ib2          80:00:11:4a:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:2c:b1 B
"""


class TestVNetMapParser:
    def _write_and_parse(self, content: str):
        from vnetmap_parser import VNetMapParser

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            parser = VNetMapParser(f.name)
            return parser.parse()

    def test_parse_topology_adds_node_hostname(self):
        result = self._write_and_parse(SAMPLE_VNETMAP_OUTPUT)
        connections = result.get("topology", [])
        assert len(connections) >= 4
        for conn in connections:
            assert "node_hostname" in conn
            assert conn["node_hostname"] in ("cnode-1", "cnode-2")

    def test_parse_lldp_neighbors(self):
        result = self._write_and_parse(SAMPLE_VNETMAP_OUTPUT)
        lldp = result.get("lldp_neighbors", [])
        assert len(lldp) >= 1
        first = lldp[0]
        assert "local_switch_ip" in first
        assert "remote_switch_ip" in first
        assert "local_port" in first
        assert "remote_port" in first

    def test_lldp_deduplication(self):
        """LLDP blocks from both sides should be deduplicated."""
        two_side_output = SAMPLE_VNETMAP_OUTPUT + """\
LLDP neighbors on 10.128.101.142:
    Eth1/1    10.128.101.141    Eth1/1
    Eth1/2    10.128.101.141    Eth1/2
"""
        result = self._write_and_parse(two_side_output)
        lldp = result.get("lldp_neighbors", [])
        unique_pairs = {(n["local_switch_ip"], n["local_port"], n["remote_switch_ip"], n["remote_port"]) for n in lldp}
        assert len(unique_pairs) == len(lldp), "LLDP entries should be deduplicated"


# ---------------------------------------------------------------------------
# SR-3: IB switch header parsing — GUID -> hostname/model/subnet mapping
# ---------------------------------------------------------------------------


class TestSR3IBSwitchHeaders:
    """vnetmap_parser must expose ``ib_switch_headers`` so EnhancedPortMapper
    can resolve the GUIDs that IB clusters store as ``switch_ip`` to the
    corresponding API-reported switch ``mgmt_ip`` via hostname matching.

    Without this metadata the port-mapper logs ``Unknown switch IP:
    0xb83fd20300e856b8`` for every IB row and falls through to ``SW?-19``
    designations + zero IPL ports.  See docs/issues/SR-3 for the full
    repro and acceptance criteria.
    """

    def _write_and_parse(self, content: str):
        from vnetmap_parser import VNetMapParser

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            f.flush()
            parser = VNetMapParser(f.name)
            return parser.parse()

    def test_parse_returns_ib_switch_headers_key(self):
        """Even on Eth-only output the key must exist (graceful contract)."""
        result = self._write_and_parse(SAMPLE_VNETMAP_OUTPUT)
        assert "ib_switch_headers" in result
        assert isinstance(result["ib_switch_headers"], list)

    def test_eth_cluster_has_no_ib_headers(self):
        """Ethernet vnetmap output has no ``Switch MF0;...`` anchor lines."""
        result = self._write_and_parse(SAMPLE_VNETMAP_OUTPUT)
        assert result["ib_switch_headers"] == []

    def test_ib_cluster_extracts_two_headers(self):
        result = self._write_and_parse(SAMPLE_IB_VNETMAP_OUTPUT)
        headers = result["ib_switch_headers"]
        assert len(headers) == 2
        guids = {h["guid"] for h in headers}
        assert guids == {"0xb83fd20300e856b8", "0xb83fd20300e85d18"}

    def test_ib_header_extracts_hostname_model_subnet_per_switch(self):
        result = self._write_and_parse(SAMPLE_IB_VNETMAP_OUTPUT)
        by_guid = {h["guid"]: h for h in result["ib_switch_headers"]}

        bot = by_guid["0xb83fd20300e856b8"]
        assert bot["hostname"] == "vast-switch1-bot"
        assert bot["model"] == "MQM8700/U1"
        assert bot["internal_subnet"] == "172.16.0"

        top = by_guid["0xb83fd20300e85d18"]
        assert top["hostname"] == "vast-switch2-top"
        assert top["model"] == "MQM8700/U1"
        assert top["internal_subnet"] == "172.16.64"

    def test_ib_topology_still_uses_guid_as_switch_ip(self):
        """Backward compat: ``switch_ip`` continues to carry the GUID
        verbatim so existing downstream consumers (cross-connection
        detection, LLDP, IPL inference) keep working.  SR-3's resolution
        is purely additive — the alias map lives in EnhancedPortMapper,
        not in the parser's primary topology shape.
        """
        result = self._write_and_parse(SAMPLE_IB_VNETMAP_OUTPUT)
        topo = result["topology"]
        assert len(topo) >= 4
        switch_ips = {row["switch_ip"] for row in topo}
        assert "0xb83fd20300e856b8" in switch_ips
        assert "0xb83fd20300e85d18" in switch_ips


# ---------------------------------------------------------------------------
# EnhancedPortMapper: breakout port normalisation
# ---------------------------------------------------------------------------


class TestBreakoutPortNormalisation:
    def test_eth1_xy_breakout(self):
        from enhanced_port_mapper import EnhancedPortMapper

        mapper = EnhancedPortMapper.__new__(EnhancedPortMapper)
        result = mapper._normalize_port_id("Eth1/15/1")
        assert result == "15/1"

    def test_eth1_simple(self):
        from enhanced_port_mapper import EnhancedPortMapper

        mapper = EnhancedPortMapper.__new__(EnhancedPortMapper)
        result = mapper._normalize_port_id("Eth1/15")
        assert result == "15"

    def test_swp_format(self):
        from enhanced_port_mapper import EnhancedPortMapper

        mapper = EnhancedPortMapper.__new__(EnhancedPortMapper)
        result = mapper._normalize_port_id("swp15")
        assert result == "15"


# ---------------------------------------------------------------------------
# Vnetmap file discovery (app.py helper)
# ---------------------------------------------------------------------------


class TestVnetmapDiscovery:
    """Test the vnetmap file discovery logic directly (without importing app.py)."""

    @staticmethod
    def _find_latest(cluster_ip: str, base_dir: Path):
        """Replicate the discovery logic from app._find_latest_vnetmap_output."""
        scripts_dir = base_dir / "output" / "scripts"
        if not scripts_dir.is_dir():
            return None
        pattern = f"vnetmap_output_{cluster_ip}_*.txt"
        candidates = sorted(scripts_dir.glob(pattern), reverse=True)
        return candidates[0] if candidates else None

    def test_find_latest_file(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            scripts_dir = base / "output" / "scripts"
            scripts_dir.mkdir(parents=True)

            (scripts_dir / "vnetmap_output_10.0.0.1_20260301_100000.txt").write_text("old")
            (scripts_dir / "vnetmap_output_10.0.0.1_20260302_100000.txt").write_text("new")
            (scripts_dir / "vnetmap_output_10.0.0.2_20260303_100000.txt").write_text("other")

            result = self._find_latest("10.0.0.1", base)
            assert result is not None
            assert "20260302" in result.name

    def test_no_matching_files(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            scripts_dir = base / "output" / "scripts"
            scripts_dir.mkdir(parents=True)

            result = self._find_latest("10.99.99.99", base)
            assert result is None


# ---------------------------------------------------------------------------
# Interface filter (DNode)
# ---------------------------------------------------------------------------


class TestInterfaceFilter:
    def test_cnode_f0_is_drawable(self):
        from network_diagram_v2 import RackCentricDiagramGenerator

        assert RackCentricDiagramGenerator._is_drawable_interface("f0", {"node_designation": "CN1"})

    def test_dnode_ens3_is_drawable(self):
        from network_diagram_v2 import RackCentricDiagramGenerator

        assert RackCentricDiagramGenerator._is_drawable_interface(
            "ens3f0", {"node_designation": "DN1", "node_type": "dnode"}
        )

    def test_unknown_interface_not_drawable(self):
        from network_diagram_v2 import RackCentricDiagramGenerator

        assert not RackCentricDiagramGenerator._is_drawable_interface("lo", {"node_designation": "CN1"})
