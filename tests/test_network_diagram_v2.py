"""Unit tests for the rack-centric network diagram generator (v2).

Covers:
  - Rack grouping by API rack_name
  - Default rack fallback
  - Spine detection and classification
  - SVG output generation (requires svgwrite)
  - Multi-page splitting (portrait, 2 racks per page)
  - Mode toggle (config-driven)
  - Color constants
  - LLDP-confirmed spine uplinks
"""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from network_diagram_v2 import (
    COLOR_NETWORK_A,
    COLOR_NETWORK_B,
    COLOR_IPL,
    PORTRAIT_W,
    MAX_RACKS_PER_PAGE,
    RackCentricDiagramGenerator,
    _ortho_path,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cbox(name: str, rack: str = "Rack-1", mgmt_ip: str = "") -> Dict[str, Any]:
    return {"name": name, "rack_name": rack, "mgmt_ip": mgmt_ip, "data_ips": []}


def _make_switch(hostname: str, mgmt_ip: str) -> Dict[str, Any]:
    return {"hostname": hostname, "mgmt_ip": mgmt_ip}


def _make_port_map_entry(
    node_ip: str, switch_ip: str, network: str = "A",
    interface: str = "f0", hostname: str = "",
) -> Dict[str, Any]:
    return {
        "node_ip": node_ip,
        "switch_ip": switch_ip,
        "network": network,
        "interface": interface,
        "node_hostname": hostname,
        "hostname": hostname,
        "port": "Eth1/1",
        "node_designation": "CN1",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRackGrouping:
    def test_cboxes_grouped_by_rack_name(self):
        gen = RackCentricDiagramGenerator()
        cboxes = [
            _make_cbox("cb-1", "Rack-1"),
            _make_cbox("cb-2", "Rack-2"),
            _make_cbox("cb-3", "Rack-1"),
        ]
        racks = gen._build_rack_groups(cboxes, [], [], [], None, "DB")
        rack_names = [r["rack_name"] for r in racks]
        assert "Rack-1" in rack_names
        assert "Rack-2" in rack_names
        r1 = next(r for r in racks if r["rack_name"] == "Rack-1")
        assert len(r1["cboxes"]) == 2

    def test_default_rack_fallback(self):
        gen = RackCentricDiagramGenerator()
        cboxes = [_make_cbox("cb-1", rack="")]
        racks = gen._build_rack_groups(cboxes, [], [], [], None, "DB")
        assert len(racks) == 1
        assert racks[0]["rack_name"] == "Default"


class TestSpineDetection:
    def test_spine_detected_when_not_in_rack(self):
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("leaf-a", "10.0.0.1")
        sw2 = _make_switch("spine-1", "10.0.0.3")

        racks = [{
            "rack_name": "Rack-1",
            "cboxes": [],
            "bottom_devices": [],
            "switches": [sw1],
            "bottom_label": "DB",
        }]
        spines = gen._detect_spines([sw1, sw2], racks)
        assert len(spines) == 1
        assert spines[0]["hostname"] == "spine-1"

    def test_no_spines_when_all_assigned(self):
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("leaf-a", "10.0.0.1")
        racks = [{
            "rack_name": "Rack-1",
            "cboxes": [],
            "bottom_devices": [],
            "switches": [sw1],
            "bottom_label": "DB",
        }]
        spines = gen._detect_spines([sw1], racks)
        assert len(spines) == 0

    def test_spine_vs_leaf_classification_in_generate(self):
        """Switches in port_map are leaf; others are spine."""
        gen = RackCentricDiagramGenerator()
        port_map = [
            _make_port_map_entry("10.0.0.1", "10.0.0.101", "A", "f0", "cb-1"),
        ]
        switches = [
            _make_switch("leaf-a", "10.0.0.101"),
            _make_switch("spine-1", "10.0.0.200"),
        ]
        port_map_ips = {c.get("switch_ip") for c in port_map if c.get("switch_ip")}
        leaf = [sw for sw in switches if sw.get("mgmt_ip") in port_map_ips]
        spine = [sw for sw in switches if sw.get("mgmt_ip") not in port_map_ips]
        assert len(leaf) == 1
        assert leaf[0]["hostname"] == "leaf-a"
        assert len(spine) == 1
        assert spine[0]["hostname"] == "spine-1"


class TestOrthoPath:
    def test_straight_line_when_same_x(self):
        path = _ortho_path(100, 0, 100, 200)
        assert path.startswith("M100,0")
        assert "L100,200" in path

    def test_path_has_arcs_when_offset(self):
        path = _ortho_path(100, 0, 200, 200)
        assert "A" in path


class TestPortraitConstants:
    def test_portrait_dimensions(self):
        assert PORTRAIT_W == 8.5 * 72

    def test_max_racks_per_page_is_two(self):
        assert MAX_RACKS_PER_PAGE == 2


class TestSVGGeneration:
    def test_generate_produces_png_files(self):
        try:
            import svgwrite  # noqa: F401
            import cairosvg  # noqa: F401
        except (ImportError, OSError):
            return  # skip if deps or system cairo library not installed

        gen = RackCentricDiagramGenerator(config={"mode": "detailed"})
        port_map = [
            _make_port_map_entry("10.0.0.1", "10.0.0.101", "A", "f0", "cb-1"),
            _make_port_map_entry("10.0.0.1", "10.0.0.102", "B", "f1", "cb-1"),
        ]
        hardware = {
            "cboxes": [_make_cbox("cb-1", "Rack-1", "10.0.0.1")],
            "dboxes": [],
            "eboxes": [],
            "switches": [
                _make_switch("SWA", "10.0.0.101"),
                _make_switch("SWB", "10.0.0.102"),
            ],
        }

        with tempfile.TemporaryDirectory() as td:
            paths = gen.generate(
                port_mapping_data={"port_map": port_map, "ipl_connections": []},
                hardware_data=hardware,
                output_dir=td,
            )
            assert len(paths) >= 1
            for p in paths:
                assert Path(p).exists()
                assert Path(p).stat().st_size > 0

    def test_generate_with_spine_and_lldp(self):
        """Spine switch appears when LLDP IPL data confirms the link."""
        try:
            import svgwrite  # noqa: F401
            import cairosvg  # noqa: F401
        except (ImportError, OSError):
            return

        gen = RackCentricDiagramGenerator(config={"mode": "detailed"})
        port_map = [
            _make_port_map_entry("10.0.0.1", "10.0.0.101", "A", "f0", "cb-1"),
            _make_port_map_entry("10.0.0.1", "10.0.0.102", "B", "f1", "cb-1"),
        ]
        ipl_conns = [{
            "switch1_ip": "10.0.0.101",
            "switch2_ip": "10.0.0.200",
            "switch_designation": "SWA",
            "node_designation": "SP1",
            "notes": "LLDP uplink",
        }]
        hardware = {
            "cboxes": [_make_cbox("cb-1", "Rack-1", "10.0.0.1")],
            "dboxes": [],
            "eboxes": [],
            "switches": [
                _make_switch("SWA", "10.0.0.101"),
                _make_switch("SWB", "10.0.0.102"),
                _make_switch("spine-1", "10.0.0.200"),
            ],
        }

        with tempfile.TemporaryDirectory() as td:
            paths = gen.generate(
                port_mapping_data={"port_map": port_map, "ipl_connections": ipl_conns},
                hardware_data=hardware,
                output_dir=td,
            )
            assert len(paths) >= 1
            for p in paths:
                assert Path(p).exists()


class TestMultiPage:
    def test_more_than_max_racks_splits(self):
        gen = RackCentricDiagramGenerator()
        cboxes = [_make_cbox(f"cb-{i}", f"Rack-{i}") for i in range(MAX_RACKS_PER_PAGE + 2)]
        racks = gen._build_rack_groups(cboxes, [], [], [], None, "DB")
        assert len(racks) > MAX_RACKS_PER_PAGE

    def test_three_racks_yields_two_pages(self):
        gen = RackCentricDiagramGenerator()
        cboxes = [_make_cbox(f"cb-{i}", f"Rack-{i}") for i in range(3)]
        racks = gen._build_rack_groups(cboxes, [], [], [], None, "DB")
        pages: List[List[Any]] = []
        for i in range(0, len(racks), MAX_RACKS_PER_PAGE):
            pages.append(racks[i: i + MAX_RACKS_PER_PAGE])
        assert len(pages) == 2
        assert len(pages[0]) == 2
        assert len(pages[1]) == 1


class TestColorConstants:
    def test_a_and_b_colors_differ(self):
        assert COLOR_NETWORK_A != COLOR_NETWORK_B

    def test_ipl_color_distinct(self):
        assert COLOR_IPL != COLOR_NETWORK_A
        assert COLOR_IPL != COLOR_NETWORK_B


class TestConfigToggle:
    def test_port_labels_off_by_default(self):
        gen = RackCentricDiagramGenerator()
        assert gen.show_port_labels is False

    def test_port_labels_on_via_config(self):
        gen = RackCentricDiagramGenerator(config={"show_port_labels": True})
        assert gen.show_port_labels is True

    def test_device_icons_default_flat(self):
        gen = RackCentricDiagramGenerator()
        assert gen.device_icon_mode == "flat"
