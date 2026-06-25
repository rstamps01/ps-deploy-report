"""Regression tests: DNode classification from IB vnetmap hostnames.

On InfiniBand clusters the vnetmap-derived ``external_port_map`` rows
carry ``node_type="cnode"`` for every node (the upstream classifier did
not distinguish DNodes), and DNode hostnames use the ``RackP01C02-DB1-U3-DN2``
form. The previous ``_build_node_maps`` only flagged a row as a DNode
when the hostname contained the literal ``-dn-`` segment or ``dnode``,
neither of which matches ``-DN2`` / ``-DB1``. As a result every IB DNode
was mapped into ``cnode_map`` and rendered with a ``CN`` designation.

The fix recognises the box/node hostname pattern ``D<B|N><digit>``
(e.g. ``-DB1`` or ``-DN2``) as a DNode, independent of the (unreliable)
``node_type`` column.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enhanced_port_mapper import EnhancedPortMapper  # noqa: E402


def _mapper(external_port_map):
    return EnhancedPortMapper(
        cboxes=[],
        dboxes=[],
        cnodes=[],
        dnodes=[],
        switches=[],
        external_port_map=external_port_map,
    )


class TestDNodeHostnameClassification:
    def test_db_dn_hostname_is_dnode(self):
        """A ``-DB1-...-DN2`` IB hostname must map to dnode_map even though
        the row's node_type column still says 'cnode'."""
        epm = _mapper(
            [
                {
                    "node_ip": "172.16.65.3",
                    "node_hostname": "RackP01C02-DB1-U3-DN2",
                    "node_type": "cnode",  # deliberately wrong upstream value
                    "interface": "ib1",
                    "box_name": "dbox-1",
                    "network": "B",
                }
            ]
        )
        assert "172.16.65.3" in epm.dnode_map
        assert "172.16.65.3" not in epm.cnode_map
        _, node_type = epm.generate_node_designation("172.16.65.3", "B", "RackP01C02-DB1-U3-DN2")
        assert node_type == "dnode"

    def test_cb_cn_hostname_stays_cnode(self):
        """CNode hostnames (``-CB1-...-CN1``) must NOT be misread as DNodes."""
        epm = _mapper(
            [
                {
                    "node_ip": "172.16.0.1",
                    "node_hostname": "RackP01C02-CB1-U5-CN1",
                    "node_type": "cnode",
                    "interface": "ib0",
                    "box_name": "cbox-1",
                    "network": "A",
                }
            ]
        )
        assert "172.16.0.1" in epm.cnode_map
        assert "172.16.0.1" not in epm.dnode_map

    def test_mixed_cluster_splits_correctly(self):
        epm = _mapper(
            [
                {
                    "node_ip": "172.16.0.1",
                    "node_hostname": "RackP01C02-CB1-U5-CN1",
                    "node_type": "cnode",
                    "interface": "ib0",
                    "box_name": "cbox-1",
                    "network": "A",
                },
                {
                    "node_ip": "172.16.65.3",
                    "node_hostname": "RackP01C02-DB1-U3-DN2",
                    "node_type": "cnode",
                    "interface": "ib1",
                    "box_name": "dbox-1",
                    "network": "B",
                },
            ]
        )
        assert len(epm.cnode_map) == 1
        assert len(epm.dnode_map) == 1

    def test_explicit_dnode_type_still_respected(self):
        epm = _mapper(
            [
                {
                    "node_ip": "10.0.0.50",
                    "node_hostname": "some-host",
                    "node_type": "dnode",
                    "interface": "f0",
                    "box_name": "dbox-1",
                    "network": "A",
                }
            ]
        )
        assert "10.0.0.50" in epm.dnode_map
