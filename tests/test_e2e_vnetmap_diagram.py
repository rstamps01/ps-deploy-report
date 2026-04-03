"""End-to-end smoke test: vnetmap file -> parse -> diagram PNG generation.

Verifies the complete data pipeline from raw vnetmap text output through
parsing, port mapping enhancement, and rack-centric SVG diagram rendering.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


VNETMAP_FILE_CONTENT = """\
Full topology
cnode-1    10.0.0.101    Eth1/15/1    10.0.1.1    f0    aa:bb:cc:00:00:01    A
cnode-1    10.0.0.102    Eth1/16/1    10.0.1.1    f1    aa:bb:cc:00:00:02    B
cnode-2    10.0.0.101    Eth1/17/1    10.0.1.2    f0    aa:bb:cc:00:00:03    A
cnode-2    10.0.0.102    Eth1/18/1    10.0.1.2    f1    aa:bb:cc:00:00:04    B
dnode-1    10.0.0.101    Eth1/19/1    10.0.1.11   ens3f0  aa:bb:cc:00:00:05    A
dnode-1    10.0.0.102    Eth1/20/1    10.0.1.11   ens14f0 aa:bb:cc:00:00:06    B

LLDP neighbors on 10.0.0.101:
    Eth1/1    10.0.0.102    Eth1/1
    Eth1/2    10.0.0.102    Eth1/2
"""


class TestEndToEndVnetmapDiagram:
    def test_vnetmap_to_png(self):
        """Parse a vnetmap file and produce a PNG diagram from it."""
        try:
            import svgwrite  # noqa: F401
            import cairosvg  # noqa: F401
        except (ImportError, OSError):
            return  # skip if rendering deps or system cairo library not installed

        from vnetmap_parser import VNetMapParser
        from network_diagram_v2 import RackCentricDiagramGenerator

        with tempfile.TemporaryDirectory() as td:
            # Step 1: Write vnetmap file
            vnetmap_file = Path(td) / "vnetmap_output.txt"
            vnetmap_file.write_text(VNETMAP_FILE_CONTENT)

            # Step 2: Parse
            parser = VNetMapParser(str(vnetmap_file))
            parsed = parser.parse()

            assert parsed["available"] is True
            assert len(parsed["topology"]) == 6
            assert len(parsed["lldp_neighbors"]) >= 1

            # Step 3: Build port_mapping_data shape expected by diagram generator
            port_map = []
            for conn in parsed["topology"]:
                port_map.append({
                    "node_ip": conn["node_ip"],
                    "node_hostname": conn["node_hostname"],
                    "hostname": conn["hostname"],
                    "switch_ip": conn["switch_ip"],
                    "port": conn["port"],
                    "interface": conn["interface"],
                    "network": conn["network"],
                    "node_designation": "CN1" if "cnode" in conn["hostname"] else "DN1",
                    "node_type": "cnode" if "cnode" in conn["hostname"] else "dnode",
                })

            ipl_connections = []
            for lldp in parsed["lldp_neighbors"]:
                ipl_connections.append({
                    "switch_a_ip": lldp["local_switch_ip"],
                    "switch_a_port": lldp["local_port"],
                    "switch_b_ip": lldp["remote_switch_ip"],
                    "switch_b_port": lldp["remote_port"],
                })

            port_mapping_data = {
                "port_map": port_map,
                "ipl_connections": ipl_connections,
            }

            # Step 4: Hardware data
            hardware_data = {
                "cboxes": [
                    {"name": "cnode-1", "rack_name": "Rack-1", "mgmt_ip": "10.0.1.1", "data_ips": []},
                    {"name": "cnode-2", "rack_name": "Rack-1", "mgmt_ip": "10.0.1.2", "data_ips": []},
                ],
                "dboxes": [
                    {"name": "dnode-1", "rack_name": "Rack-1", "mgmt_ip": "10.0.1.11", "data_ips": []},
                ],
                "eboxes": [],
                "switches": [
                    {"hostname": "SWA", "mgmt_ip": "10.0.0.101"},
                    {"hostname": "SWB", "mgmt_ip": "10.0.0.102"},
                ],
            }

            # Step 5: Generate diagram
            gen = RackCentricDiagramGenerator(config={
                "mode": "detailed",
                "show_port_labels": False,
                "device_icons": "flat",
                "orientation": "landscape",
            })

            output_dir = Path(td) / "diagrams"
            png_paths = gen.generate(
                port_mapping_data=port_mapping_data,
                hardware_data=hardware_data,
                output_dir=str(output_dir),
            )

            # Step 6: Verify
            assert len(png_paths) >= 1, "At least one diagram page should be generated"
            for p in png_paths:
                png = Path(p)
                assert png.exists(), f"PNG file should exist: {p}"
                assert png.stat().st_size > 500, "PNG should be non-trivial in size"
                assert png.suffix == ".png"
