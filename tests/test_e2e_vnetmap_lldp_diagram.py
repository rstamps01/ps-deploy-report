"""End-to-end smoke test: vnetmap_lldp output -> parse -> port map -> diagram PNG.

Mirrors ``test_e2e_vnetmap_diagram.py`` for node-side LLDP (NET-7): switches
are known only by LLDP name, so the input is built the way
``data_extractor.extract_port_mapping`` builds it for unresolved names
(synthetic unregistered switches keyed by name, ``isl_discovered: False``).
"""

import sys
from pathlib import Path
from typing import Any, Dict

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

_FIXTURE = Path(__file__).parent / "fixtures" / "vnetmap_lldp" / "onyx_show_mapping.txt"


def _synthetic_switch(name: str) -> Dict[str, Any]:
    return {"mgmt_ip": name, "hostname": name, "name": name, "discovered_via": "lldp", "registered_in_vms": False}


class TestEndToEndVnetmapLLDPDiagram:
    def test_vnetmap_lldp_to_png(self, tmp_path):
        """Parse the Onyx fixture and produce a PNG diagram from it."""
        import network_diagram_v2
        from enhanced_port_mapper import EnhancedPortMapper
        from network_diagram_v2 import RackCentricDiagramGenerator
        from vnetmap_lldp_parser import VNetMapLLDPParser

        # network_diagram_v2 sets the macOS library path cairosvg needs, so
        # probe the backends only after importing it.
        if not network_diagram_v2._SVGWRITE_AVAILABLE:
            pytest.skip("svgwrite not installed")
        try:
            import fitz  # noqa: F401

            has_fitz = True
        except ImportError:
            has_fitz = False
        if not (network_diagram_v2._CAIROSVG_AVAILABLE or has_fitz):
            pytest.skip("no SVG-to-PNG backend (cairosvg or PyMuPDF) available")

        # Step 1: Parse
        parsed = VNetMapLLDPParser(str(_FIXTURE)).parse()
        assert parsed["available"] is True
        assert parsed["source"] == "lldp"
        assert len(parsed["topology"]) == 8
        assert parsed["switch_names"] == ["ACME-SW-01", "ACME-SW-02"]

        # Step 2: Switches as the extractor supplies them for unresolved names
        switches = [_synthetic_switch(name) for name in parsed["switch_names"]]

        # Step 3: Enhanced port map
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=switches,
            external_port_map=parsed["topology"],
        )
        enhanced = mapper.generate_enhanced_port_map(parsed["topology"])
        assert enhanced["total_connections"] == 8
        assert not any(e["switch_designation"].startswith("SW?") for e in enhanced["port_map"])
        assert mapper.switch_map["ACME-SW-02"]["designation"] == "SWA"
        assert mapper.switch_map["ACME-SW-01"]["designation"] == "SWB"

        port_mapping_data = {
            "port_map": enhanced["port_map"],
            "ipl_connections": [],
            "data_source": "lldp",
            "isl_discovered": False,
        }

        # Step 4: Hardware data
        hardware_data = {
            "cboxes": [
                {"name": "acme-cn1", "rack_name": "Rack-1", "mgmt_ip": "192.0.2.11", "data_ips": []},
                {"name": "acme-cn2", "rack_name": "Rack-1", "mgmt_ip": "192.0.2.12", "data_ips": []},
            ],
            "dboxes": [
                {"name": "acme-dn1", "rack_name": "Rack-1", "mgmt_ip": "192.0.2.21", "data_ips": []},
                {"name": "acme-dn2", "rack_name": "Rack-1", "mgmt_ip": "192.0.2.22", "data_ips": []},
            ],
            "eboxes": [],
            "switches": switches,
        }

        # Step 5: Generate diagram
        gen = RackCentricDiagramGenerator(
            config={
                "mode": "detailed",
                "show_port_labels": False,
                "device_icons": "flat",
                "orientation": "landscape",
            }
        )
        png_paths = gen.generate(
            port_mapping_data=port_mapping_data,
            hardware_data=hardware_data,
            output_dir=str(tmp_path / "diagrams"),
        )

        # Step 6: Verify
        assert len(png_paths) >= 1, "At least one diagram page should be generated"
        for p in png_paths:
            png = Path(p)
            assert png.exists(), f"PNG file should exist: {p}"
            assert png.stat().st_size > 500, "PNG should be non-trivial in size"
            assert png.suffix == ".png"
