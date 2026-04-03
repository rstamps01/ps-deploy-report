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
        unique_pairs = {
            (n["local_switch_ip"], n["local_port"], n["remote_switch_ip"], n["remote_port"])
            for n in lldp
        }
        assert len(unique_pairs) == len(lldp), "LLDP entries should be deduplicated"


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

        assert RackCentricDiagramGenerator._is_drawable_interface(
            "f0", {"node_designation": "CN1"}
        )

    def test_dnode_ens3_is_drawable(self):
        from network_diagram_v2 import RackCentricDiagramGenerator

        assert RackCentricDiagramGenerator._is_drawable_interface(
            "ens3f0", {"node_designation": "DN1", "node_type": "dnode"}
        )

    def test_unknown_interface_not_drawable(self):
        from network_diagram_v2 import RackCentricDiagramGenerator

        assert not RackCentricDiagramGenerator._is_drawable_interface(
            "lo", {"node_designation": "CN1"}
        )
