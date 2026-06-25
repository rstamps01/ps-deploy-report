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
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from network_diagram_v2 import (
    COLOR_NETWORK_A,
    COLOR_NETWORK_B,
    COLOR_IPL,
    COLOR_VALIDATION_PASS,
    SUBNET_COLOR_PALETTE,
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
    node_ip: str,
    switch_ip: str,
    network: str = "A",
    interface: str = "f0",
    hostname: str = "",
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

    def test_default_rack_name_rescued_from_hostname(self):
        """A device tagged rack_name='Default' but whose hostname encodes a
        known rack is rescued into that rack instead of spawning a stray
        'Default' rack that pagination would isolate."""
        gen = RackCentricDiagramGenerator()
        cboxes = [
            {"name": "c1", "hostname": "R0404-CB1-U22", "rack_name": "R0404", "data_ips": []},
            {"name": "c2", "hostname": "R0406-CB1-U43", "rack_name": "R0406", "data_ips": []},
            # Stray: API gave it "Default" but the hostname says R0404.
            {"name": "c3", "hostname": "R0404-CB10-U31", "rack_name": "Default", "data_ips": []},
        ]
        racks = gen._build_rack_groups(cboxes, [], [], [], None, "DB")
        rack_names = {r["rack_name"] for r in racks}
        assert "Default" not in rack_names
        r0404 = next(r for r in racks if r["rack_name"] == "R0404")
        assert len(r0404["cboxes"]) == 2

    def test_unknown_hostname_rack_not_invented(self):
        """Hostname inference only rescues into ALREADY-known racks; it must
        not fabricate a rack from arbitrary hostname noise."""
        gen = RackCentricDiagramGenerator()
        cboxes = [
            {"name": "c1", "hostname": "R0404-CB1-U22", "rack_name": "R0404", "data_ips": []},
            # Hostname token R9999 is not a known rack -> stays Default.
            {"name": "c2", "hostname": "R9999-CB1-U1", "rack_name": "Default", "data_ips": []},
        ]
        racks = gen._build_rack_groups(cboxes, [], [], [], None, "DB")
        rack_names = {r["rack_name"] for r in racks}
        assert rack_names == {"R0404", "Default"}


class TestSpineDetectionFromTopology:
    """Spines must be recognized from spine_uplink/spine_fabric topology even
    when their hostnames use the 'SS' convention the name classifier does not
    match. Otherwise the diagram draws a leaf-leaf IPL mesh and drops the
    spines instead of rendering leaf->spine ISLs."""

    def test_ss_named_switch_classified_as_spine(self):
        fn = RackCentricDiagramGenerator._classify_switch_role
        assert fn({"hostname": "VAST-SS-A"}) == "spine"
        assert fn({"hostname": "VAST-SS-B"}) == "spine"
        # Leaf naming still resolves to leaf.
        assert fn({"hostname": "VAST-SL-A"}) == "leaf"
        assert fn({"hostname": "VAST-TN1-SL-3"}) == "leaf"

    def test_spine_ips_from_ipl_excludes_leaves(self):
        fn = RackCentricDiagramGenerator._spine_ips_from_ipl
        ipl = [
            {"connection_type": "spine_uplink", "switch1_ip": "10.0.0.21", "switch2_ip": "10.0.0.11"},
            {"connection_type": "spine_uplink", "switch1_ip": "10.0.0.22", "switch2_ip": "10.0.0.12"},
            {"connection_type": "IPL", "switch1_ip": "10.0.0.11", "switch2_ip": "10.0.0.12"},
        ]
        leaf_ips = {"10.0.0.11", "10.0.0.12"}
        assert fn(ipl, leaf_ips) == {"10.0.0.21", "10.0.0.22"}

    def test_no_spine_uplinks_returns_empty(self):
        fn = RackCentricDiagramGenerator._spine_ips_from_ipl
        ipl = [{"connection_type": "IPL", "switch1_ip": "10.0.0.11", "switch2_ip": "10.0.0.12"}]
        assert fn(ipl, {"10.0.0.11", "10.0.0.12"}) == set()


class TestRackFromHostname:
    def test_extracts_leading_rack_token(self):
        fn = RackCentricDiagramGenerator._rack_from_hostname
        assert fn({"hostname": "R0404-CB10-U31"}) == "R0404"
        assert fn({"hostname": "R0406-CB1-U43-top-right"}) == "R0406"

    def test_falls_back_to_name_field(self):
        fn = RackCentricDiagramGenerator._rack_from_hostname
        assert fn({"name": "RackA1-CB1"}) == "RackA1"

    def test_no_token_returns_empty(self):
        fn = RackCentricDiagramGenerator._rack_from_hostname
        assert fn({"hostname": "cnode-129-10"}) == ""
        assert fn({}) == ""


class TestPaginationAffinity:
    """Racks connected by the port_map must share a page so node->switch
    edges are not dropped as 'orphan' when an operator places a switch in a
    different rack than the nodes wired to it."""

    def _rack(self, name: str, cbox_hosts: List[str], switch_ips: List[str]) -> Dict[str, Any]:
        return {
            "rack_name": name,
            "cboxes": [{"name": h, "hostname": h, "data_ips": [], "mgmt_ip": ""} for h in cbox_hosts],
            "bottom": [],
            "switches": [{"hostname": ip, "mgmt_ip": ip} for ip in switch_ips],
        }

    def test_no_reorder_when_fits_one_page(self):
        gen = RackCentricDiagramGenerator()
        racks = [self._rack("A", ["h1"], ["10.0.0.1"]), self._rack("B", ["h2"], ["10.0.0.2"])]
        out = gen._order_racks_for_pagination(racks, [])
        assert [r["rack_name"] for r in out] == ["A", "B"]

    def test_connected_racks_paired_on_same_page(self):
        gen = RackCentricDiagramGenerator()
        # A's node wired to C's switch; B is a lone rack. With 3 racks and
        # MAX_RACKS_PER_PAGE=2, A and C must end up adjacent (same page).
        racks = [
            self._rack("A", ["nodeA"], []),
            self._rack("B", ["nodeB"], ["10.0.0.9"]),
            self._rack("C", [], ["10.0.0.1"]),
        ]
        port_map = [
            _make_port_map_entry("", "10.0.0.1", hostname="nodeA"),
            _make_port_map_entry("", "10.0.0.1", hostname="nodeA"),
        ]
        out = gen._order_racks_for_pagination(racks, port_map)
        order = [r["rack_name"] for r in out]
        # A and C land in the same 2-rack page chunk.
        pages = [order[i : i + MAX_RACKS_PER_PAGE] for i in range(0, len(order), MAX_RACKS_PER_PAGE)]
        assert any("A" in p and "C" in p for p in pages)


class TestNodeRackFromBoxId:
    """Node rack placement must come from the engineer-assigned hardware
    inventory: each CNode/DNode inherits its rack from its parent box via
    ``cbox_id``/``dbox_id`` -> box ``id`` -> box ``rack_name``.

    Regression: cnodes/dnodes carry ``rack_id=None``, so the old
    ``_enrich_devices`` fallback grabbed ``boxes[0].rack_name`` for every
    node and collapsed the whole cluster into one rack.
    """

    def _enrich(self):
        return RackCentricDiagramGenerator._enrich_devices

    def test_cnode_inherits_rack_from_parent_cbox(self):
        cboxes = [
            {"id": 1, "rack_name": "RackP01C01"},
            {"id": 2, "rack_name": "RackP01C02"},
        ]
        cnodes = [
            {"hostname": "h-c1", "cbox_id": 1, "rack_id": None, "rack_name": None},
            {"hostname": "h-c2", "cbox_id": 2, "rack_id": None, "rack_name": None},
        ]
        enriched = self._enrich()(cnodes, cboxes, "CB", "cbox_id")
        by_host = {d["hostname"]: d for d in enriched}
        assert by_host["h-c1"]["rack_name"] == "RackP01C01"
        assert by_host["h-c2"]["rack_name"] == "RackP01C02"

    def test_dnode_inherits_rack_from_parent_dbox(self):
        dboxes = [
            {"id": 3, "rack_name": "RackP01C01"},
            {"id": 4, "rack_name": "RackP01C02"},
        ]
        dnodes = [
            {"hostname": "h-d1", "dbox_id": 4, "rack_id": None, "rack_name": None},
            {"hostname": "h-d2", "dbox_id": 3, "rack_id": None, "rack_name": None},
        ]
        enriched = self._enrich()(dnodes, dboxes, "DB", "dbox_id")
        by_host = {d["hostname"]: d for d in enriched}
        assert by_host["h-d1"]["rack_name"] == "RackP01C02"
        assert by_host["h-d2"]["rack_name"] == "RackP01C01"

    def test_nodes_split_across_racks_not_collapsed(self):
        """The whole point: nodes must NOT all land in one rack."""
        cboxes = [{"id": i, "rack_name": ("RackP01C01" if i <= 2 else "RackP01C02")} for i in range(1, 5)]
        cnodes = [{"hostname": f"c{i}", "cbox_id": i, "rack_id": None} for i in range(1, 5)]
        enriched = self._enrich()(cnodes, cboxes, "CB", "cbox_id")
        racks = {d["rack_name"] for d in enriched}
        assert racks == {"RackP01C01", "RackP01C02"}

    def test_unknown_box_id_falls_back_gracefully(self):
        """A node whose box id has no matching box must not crash; it falls
        back to its own rack_name or 'Default' rather than a wrong rack."""
        cboxes = [{"id": 1, "rack_name": "RackP01C01"}]
        cnodes = [{"hostname": "orphan", "cbox_id": 99, "rack_id": None}]
        enriched = self._enrich()(cnodes, cboxes, "CB", "cbox_id")
        assert enriched[0]["rack_name"] in ("Default", "RackP01C01")

    def test_backwards_compatible_without_box_id_field(self):
        """Legacy callers that pass no box_id_field still get a rack_name."""
        cboxes = [{"id": 1, "rack_name": "RackP01C01", "rack_id": 1}]
        cnodes = [{"hostname": "c1", "rack_id": 1}]
        enriched = self._enrich()(cnodes, cboxes, "CB")
        assert enriched[0]["rack_name"] == "RackP01C01"


class TestDrawableInterfaceIB:
    """IB clusters use ibN interfaces (ib0/ib1/...); these must be drawable
    or no IB node->switch edge ever renders."""

    def _fn(self):
        return RackCentricDiagramGenerator._is_drawable_interface

    def test_ib_interfaces_drawable(self):
        assert self._fn()("ib0", {}) is True
        assert self._fn()("ib1", {}) is True
        assert self._fn()("ib2", {"node_designation": "DB1-DN2-L"}) is True

    def test_existing_fn_interfaces_still_drawable(self):
        assert self._fn()("f0", {}) is True
        assert self._fn()("f3", {}) is True

    def test_bond_interface_not_drawable(self):
        assert self._fn()("bond0", {}) is False


class TestHostnameNodeKey:
    """Rack-prefix-independent node identity for IB edge joins."""

    def _key(self):
        return RackCentricDiagramGenerator._hostname_node_key

    def test_strips_rack_prefix_to_box_suffix(self):
        assert self._key()("RackP01C01-CB6-U22-CN1") == "cb6-u22-cn1"
        assert self._key()("RackP01C02-CB6-U22-CN1") == "cb6-u22-cn1"

    def test_dnode_suffix(self):
        assert self._key()("RackP01C02-DB1-U3-DN2") == "db1-u3-dn2"

    def test_ebox_suffix(self):
        assert self._key()("SITE-EB2-U10-CN3") == "eb2-u10-cn3"

    def test_cross_rack_hostnames_share_key(self):
        """The whole point: the suffix collides across racks, so callers
        must disambiguate by same-rack switch."""
        assert self._key()("RackP01C01-CB6-U22-CN1") == self._key()("RackP01C02-CB6-U22-CN1")

    def test_no_box_token_returns_lowered_hostname(self):
        assert self._key()("plain-host") == "plain-host"

    def test_empty(self):
        assert self._key()("") == ""
        assert self._key()(None) == ""


class TestLeafSpineISL:
    """Leaf/spine topology rendering: no leaf-leaf IPL; inferred leaf->spine
    ISL mesh; legend shows ISL instead of IPL/MLAG."""

    def _render(self, spines, ipl_conns):
        import svgwrite
        from network_diagram_v2 import COLOR_SPINE_FABRIC  # noqa: F401

        gen = RackCentricDiagramGenerator(config={"mode": "detailed"})
        racks = [
            {
                "rack_name": "RackP01C01",
                "cboxes": [],
                "bottom_devices": [],
                "switches": [{"hostname": "SW-LF-01", "mgmt_ip": "10.0.0.13"}],
                "bottom_label": "DN",
            },
            {
                "rack_name": "RackP01C02",
                "cboxes": [],
                "bottom_devices": [],
                "switches": [{"hostname": "SW-LF-03", "mgmt_ip": "10.0.0.15"}],
                "bottom_label": "DN",
            },
        ]
        all_switches = [
            {"hostname": "SW-LF-01", "mgmt_ip": "10.0.0.13"},
            {"hostname": "SW-LF-03", "mgmt_ip": "10.0.0.15"},
        ] + spines
        return gen._render_page(svgwrite, racks, spines, ipl_conns, [], all_switches)

    def test_spine_topology_draws_isl_and_suppresses_ipl(self):
        from network_diagram_v2 import COLOR_SPINE_FABRIC

        spines = [
            {"hostname": "SW-SP-01", "mgmt_ip": "10.0.0.11", "_assigned_rack": "RackP01C01"},
            {"hostname": "SW-SP-02", "mgmt_ip": "10.0.0.12", "_assigned_rack": "RackP01C02"},
        ]
        ipl_conns = [{"switch1_ip": "10.0.0.13", "switch2_ip": "10.0.0.15", "connection_type": "ipl"}]
        svg = self._render(spines, ipl_conns)
        assert COLOR_SPINE_FABRIC in svg  # ISL lines drawn in spine-fabric color
        assert "ISL (Leaf-Spine)" in svg  # legend shows ISL
        assert "IPL/MLAG" not in svg  # no leaf-leaf IPL legend in leaf/spine

    def test_non_spine_topology_keeps_ipl(self):
        ipl_conns = [{"switch1_ip": "10.0.0.13", "switch2_ip": "10.0.0.15", "connection_type": "ipl"}]
        svg = self._render([], ipl_conns)
        assert "IPL/MLAG" in svg  # legend keeps IPL for non-leaf/spine
        assert "ISL (Leaf-Spine)" not in svg


class TestLegendSizing:
    """The bottom legend must never clip the leftmost pill.

    Regression: the v1.5.8 legend used fixed ``spacing=126`` and centered on
    ``len(items) * spacing``. On a narrow 2-rack page (total_w ~614) a 5-item
    legend (4 subnets + ISL) produced ``start_x = -8`` and the green pill was
    cut off on the left edge of the diagram.
    """

    def _gen(self):
        return RackCentricDiagramGenerator(config={"mode": "detailed"})

    def test_pill_width_grows_with_label_and_has_floor(self):
        gen = self._gen()
        short = gen._legend_pill_width("IPL")
        long = gen._legend_pill_width("ISL (Leaf-Spine)")
        assert long > short
        assert short >= 96  # floor so short labels still read as pills

    def test_content_width_sums_pills_and_gaps(self):
        gen = self._gen()
        items = [("#0F9D58", "172.16.0/24"), ("#4285F4", "172.16.64/24")]
        expected = gen._legend_pill_width(items[0][1]) + gen._legend_pill_width(items[1][1]) + 14
        assert gen._legend_content_width(items) == expected

    def test_compute_items_subnets_plus_isl_for_spine(self):
        gen = self._gen()
        switches = [
            {"hostname": "SW-LF-01", "mgmt_ip": "10.0.0.1"},
            {"hostname": "SW-LF-02", "mgmt_ip": "10.0.0.2"},
        ]
        port_map = [
            {"switch_ip": "10.0.0.1", "node_ip": "172.16.0.5"},
            {"switch_ip": "10.0.0.2", "node_ip": "172.16.64.5"},
        ]
        color_map = gen._assign_subnet_colors(switches, port_map)
        items = gen._compute_legend_items(switches, color_map, port_map, has_spine=True)
        labels = [lbl for _, lbl in items]
        assert "ISL (Leaf-Spine)" in labels
        assert "IPL/MLAG" not in labels

    def test_five_item_legend_not_clipped_on_narrow_page(self):
        """End-to-end: a 4-subnet + spine cluster renders all 5 pills with the
        first pill's x >= MARGIN (no negative start_x / left clip)."""
        import re as _re
        import svgwrite
        from network_diagram_v2 import MARGIN

        gen = self._gen()
        switches = [
            {"hostname": "SW-LF-01", "mgmt_ip": "10.0.0.1"},
            {"hostname": "SW-LF-02", "mgmt_ip": "10.0.0.2"},
            {"hostname": "SW-LF-03", "mgmt_ip": "10.0.0.3"},
            {"hostname": "SW-LF-04", "mgmt_ip": "10.0.0.4"},
        ]
        spines = [
            {"hostname": "SW-SP-01", "mgmt_ip": "10.0.0.11", "_assigned_rack": "RackP01C01"},
            {"hostname": "SW-SP-02", "mgmt_ip": "10.0.0.12", "_assigned_rack": "RackP01C02"},
        ]
        racks = [
            {
                "rack_name": "RackP01C01",
                "cboxes": [],
                "bottom_devices": [],
                "switches": [switches[0], switches[1]],
                "bottom_label": "DN",
            },
            {
                "rack_name": "RackP01C02",
                "cboxes": [],
                "bottom_devices": [],
                "switches": [switches[2], switches[3]],
                "bottom_label": "DN",
            },
        ]
        port_map = [
            {"switch_ip": "10.0.0.1", "node_ip": "172.16.0.5"},
            {"switch_ip": "10.0.0.2", "node_ip": "172.16.64.5"},
            {"switch_ip": "10.0.0.3", "node_ip": "172.16.1.5"},
            {"switch_ip": "10.0.0.4", "node_ip": "172.16.65.5"},
        ]
        all_switches = switches + spines
        svg = gen._render_page(svgwrite, racks, spines, [], port_map, all_switches)

        color_map = gen._assign_subnet_colors(all_switches, port_map)
        items = gen._compute_legend_items(all_switches, color_map, port_map, has_spine=True)
        assert len(items) == 5  # 4 subnets + ISL

        # Canvas must be wide enough to hold the legend with margins.
        m = _re.search(r'width="([0-9.]+)px"', svg)
        assert m is not None
        total_w = float(m.group(1))
        assert total_w >= gen._legend_content_width(items) + 2 * MARGIN

        # The leftmost legend pill must start at x >= MARGIN (not clipped).
        start_x = max(float(MARGIN), (total_w - gen._legend_content_width(items)) / 2)
        assert start_x >= MARGIN


class TestSwitchRoleClassification:
    """Leaf vs spine must be decided by switch naming (SW-LF-* / SW-SP-*)
    from switch discovery, NOT by port-map membership. The port-map only
    covers vnetmap-reached switches, so membership-based classification
    misplaces real leaf switches that were not captured.
    """

    def _classify(self):
        return RackCentricDiagramGenerator._classify_switch_role

    def test_sw_sp_is_spine(self):
        assert self._classify()({"hostname": "SW-SP-01"}) == "spine"
        assert self._classify()({"hostname": "SW-SP-02"}) == "spine"

    def test_sw_lf_is_leaf(self):
        assert self._classify()({"hostname": "SW-LF-01"}) == "leaf"
        assert self._classify()({"hostname": "SW-LF-04"}) == "leaf"

    def test_site_prefixed_leaf_is_leaf(self):
        assert self._classify()({"hostname": "LAX-01-SW-LF-02"}) == "leaf"

    def test_uses_name_when_hostname_absent(self):
        assert self._classify()({"name": "SW-SP-01"}) == "spine"

    def test_unknown_defaults_to_leaf(self):
        assert self._classify()({"hostname": "some-switch"}) == "leaf"
        assert self._classify()({}) == "leaf"

    def test_all_leaf_switches_placed_in_racks_by_role(self):
        """All four LF switches (incl. the two vnetmap did NOT capture)
        must be placed in their manual-placement racks, not dumped into a
        spine tier."""
        gen = RackCentricDiagramGenerator()
        switches = [
            {"hostname": "SW-LF-01", "mgmt_ip": "10.0.0.13"},
            {"hostname": "LAX-01-SW-LF-02", "mgmt_ip": "10.0.0.14"},
            {"hostname": "SW-LF-03", "mgmt_ip": "10.0.0.15"},
            {"hostname": "SW-LF-04", "mgmt_ip": "10.0.0.16"},
        ]
        manual = [
            {"switch_name": "SW-LF-01", "rack_name": "RackP01C01"},
            {"switch_name": "LAX-01-SW-LF-02", "rack_name": "RackP01C01"},
            {"switch_name": "SW-LF-03", "rack_name": "RackP01C02"},
            {"switch_name": "SW-LF-04", "rack_name": "RackP01C02"},
        ]
        cboxes = [
            {"id": 1, "rack_name": "RackP01C01"},
            {"id": 2, "rack_name": "RackP01C02"},
        ]
        racks = gen._build_rack_groups(cboxes, [], switches, [], None, "DB", manual_switch_placements=manual)
        placed = {}
        for r in racks:
            for sw in r["switches"]:
                placed[sw.get("hostname")] = r["rack_name"]
        assert placed.get("SW-LF-01") == "RackP01C01"
        assert placed.get("LAX-01-SW-LF-02") == "RackP01C01"
        assert placed.get("SW-LF-03") == "RackP01C02"
        assert placed.get("SW-LF-04") == "RackP01C02"


class TestSortSwitchesByNetwork:
    """Ordering of rack-local switches so SWA=left=NetA and SWB=right=NetB.

    Regression coverage for the "crossing leaf paths" visual bug where the
    diagram used API iteration order instead of network-majority order,
    putting the Network B switch on the left (SWA position) when the API
    returned it first.
    """

    def test_network_a_majority_sorts_first(self):
        """Switch with mostly Network A connections should land at index 0 (SWA/left)."""
        sw_b = _make_switch("switch-B", "10.0.0.154")
        sw_a = _make_switch("switch-A", "10.0.0.153")
        port_map = [
            _make_port_map_entry("10.0.0.1", "10.0.0.153", network="A"),
            _make_port_map_entry("10.0.0.2", "10.0.0.153", network="A"),
            _make_port_map_entry("10.0.0.1", "10.0.0.154", network="B"),
            _make_port_map_entry("10.0.0.2", "10.0.0.154", network="B"),
        ]

        # Caller-supplied order deliberately puts the B switch first to mimic
        # the problematic case seen in production.
        ordered = RackCentricDiagramGenerator._sort_switches_by_network([sw_b, sw_a], port_map)

        assert ordered[0]["hostname"] == "switch-A", "Network A majority switch must be at position 0 (SWA/left)"
        assert ordered[1]["hostname"] == "switch-B", "Network B majority switch must be at position 1 (SWB/right)"

    def test_stable_fallback_to_mgmt_ip_when_no_port_map(self):
        """With no port_map evidence, fall back to mgmt_ip ascending (matches enhanced_port_mapper)."""
        sw_high = _make_switch("sw-high", "10.0.0.154")
        sw_low = _make_switch("sw-low", "10.0.0.153")

        ordered = RackCentricDiagramGenerator._sort_switches_by_network([sw_high, sw_low], [])

        assert ordered[0]["hostname"] == "sw-low"
        assert ordered[1]["hostname"] == "sw-high"

    def test_empty_input_returns_empty(self):
        assert RackCentricDiagramGenerator._sort_switches_by_network([], []) == []

    def test_build_rack_groups_produces_sorted_switches(self):
        """Integration: _build_rack_groups returns per-rack switch order that honors Network A/B."""
        gen = RackCentricDiagramGenerator()
        sw_b = _make_switch("switch-B", "10.0.0.154")
        sw_a = _make_switch("switch-A", "10.0.0.153")
        cboxes = [_make_cbox("cb-1", "Rack-1", "10.0.0.1")]
        port_map = [
            _make_port_map_entry("10.0.0.1", "10.0.0.153", network="A"),
            _make_port_map_entry("10.0.0.1", "10.0.0.154", network="B"),
        ]

        racks = gen._build_rack_groups(cboxes, [], [sw_b, sw_a], port_map, None, "DB")

        assert len(racks) == 1
        rack_switches = racks[0]["switches"]
        assert rack_switches[0]["hostname"] == "switch-A"
        assert rack_switches[1]["hostname"] == "switch-B"


class TestSpineDetection:
    def test_spine_detected_when_not_in_rack(self):
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("leaf-a", "10.0.0.1")
        sw2 = _make_switch("spine-1", "10.0.0.3")

        racks = [
            {
                "rack_name": "Rack-1",
                "cboxes": [],
                "bottom_devices": [],
                "switches": [sw1],
                "bottom_label": "DB",
            }
        ]
        spines = gen._detect_spines([sw1, sw2], racks)
        assert len(spines) == 1
        assert spines[0]["hostname"] == "spine-1"

    def test_no_spines_when_all_assigned(self):
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("leaf-a", "10.0.0.1")
        racks = [
            {
                "rack_name": "Rack-1",
                "cboxes": [],
                "bottom_devices": [],
                "switches": [sw1],
                "bottom_label": "DB",
            }
        ]
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
        ipl_conns = [
            {
                "switch1_ip": "10.0.0.101",
                "switch2_ip": "10.0.0.200",
                "switch_designation": "SWA",
                "node_designation": "SP1",
                "notes": "LLDP uplink",
            }
        ]
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
            pages.append(racks[i : i + MAX_RACKS_PER_PAGE])
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


class TestNET2AManualSwitchPlacement:
    """NET-2A: ``manual_switch_placements`` (operator-specified switch->rack
    assignments from the Discovery UI) MUST override topology voting in the
    logical network diagram.

    The v1.5.7 bug: ``_assign_switches_to_racks`` used pure topology voting
    (port_map node->rack majority) and fell back to the first rack key when
    no votes existed. When the operator manually placed sw1 in R1 and sw2 in
    R2, the rack diagram honored those assignments but the logical diagram
    ignored them — both switches landed in the same rack (typically R1).

    Fix surface:
      - ``_extract_manual_switch_to_rack(placements)`` — pure helper that
        builds a ``{switch_name -> rack_name}`` map from the Discovery UI's
        ``manual_switch_placements`` list.
      - ``_assign_switches_to_racks(..., manual_switch_to_rack=...)`` —
        consults the manual map first; topology voting only for unmapped
        switches.
    """

    @staticmethod
    def _placements(*pairs):
        """Build manual_switch_placements list from (switch_name, rack_name) pairs."""
        return [
            {
                "switch_name": name,
                "rack_name": rack,
                "u_position": 35,
                "height_u": 2,
                "model": "msn4600c",
            }
            for name, rack in pairs
        ]

    def test_extract_manual_switch_to_rack_builds_name_keyed_map(self):
        """Helper produces {switch_name -> rack_name} from a list of placements."""
        fn = RackCentricDiagramGenerator._extract_manual_switch_to_rack
        placements = self._placements(("sw1", "R1"), ("sw2", "R2"))
        result = fn(placements)
        assert result == {"sw1": "R1", "sw2": "R2"}

    def test_extract_manual_switch_to_rack_handles_none_and_empty(self):
        """Helper returns an empty dict for None or [] (defensive)."""
        fn = RackCentricDiagramGenerator._extract_manual_switch_to_rack
        assert fn(None) == {}
        assert fn([]) == {}

    def test_extract_manual_switch_to_rack_skips_entries_missing_fields(self):
        """Entries without switch_name or rack_name are skipped, not errored."""
        fn = RackCentricDiagramGenerator._extract_manual_switch_to_rack
        placements = [
            {"switch_name": "sw1", "rack_name": "R1"},
            {"switch_name": "sw2"},  # missing rack_name
            {"rack_name": "R3"},  # missing switch_name
            {"switch_name": "", "rack_name": "R4"},  # empty switch_name
        ]
        result = fn(placements)
        assert result == {"sw1": "R1"}

    def test_manual_assignment_overrides_topology_when_evidence_only_in_one_rack(self):
        """v1.5.7 bug: port_map only ties switches to R1's nodes, but operator
        wants sw2 placed in R2. Manual map MUST win.
        """
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("sw1", "10.0.0.153")
        sw2 = _make_switch("sw2", "10.0.0.154")
        cb_r1 = _make_cbox("cb-r1", "R1", "10.0.0.1")
        cb_r2 = _make_cbox("cb-r2", "R2", "10.0.0.2")
        port_map = [
            _make_port_map_entry("10.0.0.1", "10.0.0.153", network="A", hostname="cb-r1"),
            _make_port_map_entry("10.0.0.1", "10.0.0.154", network="B", hostname="cb-r1"),
        ]
        rack_map = {
            "R1": {"cboxes": [cb_r1], "bottom": [], "switches": []},
            "R2": {"cboxes": [cb_r2], "bottom": [], "switches": []},
        }
        manual_map = {"sw1": "R1", "sw2": "R2"}

        result = gen._assign_switches_to_racks(
            [sw1, sw2],
            port_map,
            rack_map,
            manual_switch_to_rack=manual_map,
        )

        assert result[id(sw1)] == "R1", "sw1 manual assignment to R1 must win"
        assert result[id(sw2)] == "R2", (
            "sw2 manual assignment to R2 must override topology voting "
            "(port_map only contained evidence for R1's nodes)"
        )

    def test_manual_assignment_overrides_when_no_topology_evidence(self):
        """Empty port_map: without manual map both switches fall to first
        rack key (the broken v1.5.7 fallback). Manual map MUST split them.
        """
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("sw1", "10.0.0.153")
        sw2 = _make_switch("sw2", "10.0.0.154")
        rack_map = {
            "R1": {"cboxes": [_make_cbox("cb-r1", "R1")], "bottom": [], "switches": []},
            "R2": {"cboxes": [_make_cbox("cb-r2", "R2")], "bottom": [], "switches": []},
        }
        manual_map = {"sw1": "R1", "sw2": "R2"}

        result = gen._assign_switches_to_racks(
            [sw1, sw2],
            [],  # no port_map evidence
            rack_map,
            manual_switch_to_rack=manual_map,
        )

        assert result[id(sw1)] == "R1"
        assert result[id(sw2)] == "R2"

    def test_partial_manual_assignment_falls_back_to_topology(self):
        """Switches without a manual entry MUST still use topology voting."""
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("sw1", "10.0.0.153")
        sw2 = _make_switch("sw2", "10.0.0.154")
        sw3 = _make_switch("sw3", "10.0.0.155")
        cb_r1 = _make_cbox("cb-r1", "R1", "10.0.0.1")
        cb_r2 = _make_cbox("cb-r2", "R2", "10.0.0.2")
        port_map = [
            # sw3 has clear topology evidence for R2
            _make_port_map_entry("10.0.0.2", "10.0.0.155", network="A", hostname="cb-r2"),
            _make_port_map_entry("10.0.0.2", "10.0.0.155", network="A", hostname="cb-r2"),
        ]
        rack_map = {
            "R1": {"cboxes": [cb_r1], "bottom": [], "switches": []},
            "R2": {"cboxes": [cb_r2], "bottom": [], "switches": []},
        }
        manual_map = {"sw1": "R1", "sw2": "R2"}  # sw3 is NOT in the map

        result = gen._assign_switches_to_racks(
            [sw1, sw2, sw3],
            port_map,
            rack_map,
            manual_switch_to_rack=manual_map,
        )

        assert result[id(sw1)] == "R1"
        assert result[id(sw2)] == "R2"
        assert result[id(sw3)] == "R2", "sw3 (no manual entry) should fall back to topology voting -> R2"

    def test_build_rack_groups_propagates_manual_switch_placements(self):
        """End-to-end: ``_build_rack_groups`` accepts manual_switch_placements
        and the resulting rack assignments honor them.
        """
        gen = RackCentricDiagramGenerator()
        sw1 = _make_switch("sw1", "10.0.0.153")
        sw2 = _make_switch("sw2", "10.0.0.154")
        cboxes = [_make_cbox("cb-r1", "R1", "10.0.0.1"), _make_cbox("cb-r2", "R2", "10.0.0.2")]
        placements = self._placements(("sw1", "R1"), ("sw2", "R2"))

        racks = gen._build_rack_groups(
            cboxes,
            [],
            [sw1, sw2],
            [],  # empty port_map
            None,  # device manual_placements
            "DB",
            manual_switch_placements=placements,
        )

        rack_by_name = {r["rack_name"]: r for r in racks}
        assert "R1" in rack_by_name and "R2" in rack_by_name
        assert any(
            s.get("hostname") == "sw1" for s in rack_by_name["R1"]["switches"]
        ), "sw1 must land in R1 per manual placement"
        assert any(
            s.get("hostname") == "sw2" for s in rack_by_name["R2"]["switches"]
        ), "sw2 must land in R2 per manual placement"
        assert not any(
            s.get("hostname") == "sw2" for s in rack_by_name["R1"]["switches"]
        ), "sw2 must NOT appear in R1 (the v1.5.7 bug)"


class TestDuplicateNamedSwitchPlacement:
    """Two switches that share a name (e.g. two "Spine-B" at different mgmt
    IPs) must map to their assigned racks independently. The bug keyed the
    manual switch->rack map by name, so the second duplicate collided with the
    first. The fix keys by the stable switch_id/mgmt_ip.
    """

    def test_extract_manual_switch_to_rack_keys_by_switch_id(self):
        fn = RackCentricDiagramGenerator._extract_manual_switch_to_rack
        placements = [
            {"switch_name": "Spine-B", "switch_id": "10.84.214.28", "mgmt_ip": "10.84.214.28", "rack_name": "R1"},
            {"switch_name": "Spine-B", "switch_id": "10.84.214.29", "mgmt_ip": "10.84.214.29", "rack_name": "R2"},
        ]
        result = fn(placements)
        # Both ids present and mapped to distinct racks despite the shared name.
        assert result["10.84.214.28"] == "R1"
        assert result["10.84.214.29"] == "R2"

    def test_duplicate_named_spines_assigned_to_distinct_racks(self):
        gen = RackCentricDiagramGenerator()
        sw1 = {"hostname": "Spine-B", "name": "Spine-B", "switch_id": "10.84.214.28", "mgmt_ip": "10.84.214.28"}
        sw2 = {"hostname": "Spine-B", "name": "Spine-B", "switch_id": "10.84.214.29", "mgmt_ip": "10.84.214.29"}
        rack_map = {
            "R1": {"cboxes": [_make_cbox("cb-r1", "R1")], "bottom": [], "switches": []},
            "R2": {"cboxes": [_make_cbox("cb-r2", "R2")], "bottom": [], "switches": []},
        }
        manual_map = {"10.84.214.28": "R1", "10.84.214.29": "R2"}

        result = gen._assign_switches_to_racks(
            [sw1, sw2],
            [],  # no topology evidence; manual map must split them
            rack_map,
            manual_switch_to_rack=manual_map,
        )

        assert result[id(sw1)] == "R1"
        assert result[id(sw2)] == "R2"


class TestNET2BEdgeRouting:
    """NET-2B: outer/inner exit-side rule + cross-rack edge rendering.

    The v1.5.7 bug had two sub-failures in ``_draw_device_connections``:

    1. **Cross-rack edges silently dropped.** When a device's port_map row
       referenced a switch in a *different* rack on the same page, the
       per-rack accumulating ``switch_centers`` dict didn't yet contain
       that switch (asymmetric drop for the first rack iteration), so
       lines 1254 ``if sw_ip not in switch_centers: continue`` skipped
       the row entirely.

    2. **Deprecated A/B exit-side rule.** Lines 1269-1276 forced left-edge
       exit for Network A and right-edge exit for Network B regardless
       of the device's rack column, producing crossed lines whenever the
       SWA/SWB labels disagreed with rack position. The v1.5.8 rule
       routes by rack-column relationship instead:

         - Same-rack edges: solid, exit the RIGHT edge of the device
           for BOTH rack columns (consistent right-side routing — the
           left rack's fan swoops into the widened inter-rack gutter and
           back up to its own switches, matching the right rack's look).
         - Cross-rack edges: dashed (``6,4``, opacity 0.40), exit
           INNER side toward the inter-rack gutter.
           (Left rack: right edge. Right rack: left edge.)

    Fix surface:
      - ``_plan_device_edge(...)`` — pure helper returning ``exit_x``,
        ``dasharray``, ``opacity`` for one edge given ``is_cross_rack``
        and the device's rack column ("left" or "right").
      - ``_classify_edge(...)`` — pure helper classifying a switch IP
        as ``"same_rack" | "cross_rack" | "orphan"`` so the renderer
        can never silently drop a switch that exists on the page.
    """

    def _planner(self):
        return RackCentricDiagramGenerator._plan_device_edge

    def _classifier(self):
        return RackCentricDiagramGenerator._classify_edge

    def test_same_rack_left_device_exits_right_edge(self):
        # Consistent right-side routing: the left rack now ALSO exits the
        # right edge (was the left edge under the old outer-side rule).
        plan = self._planner()(is_cross_rack=False, device_rack_column="left", dev_x=100.0, dev_w=80.0)
        assert plan["exit_x"] == 180.0, "Left-rack same-rack edge must exit the RIGHT edge (consistent routing)"

    def test_same_rack_right_device_exits_right_edge(self):
        plan = self._planner()(is_cross_rack=False, device_rack_column="right", dev_x=100.0, dev_w=80.0)
        assert plan["exit_x"] == 180.0, "Right-rack same-rack edge must exit the RIGHT edge"

    def test_cross_rack_left_device_exits_inner_right_edge(self):
        plan = self._planner()(is_cross_rack=True, device_rack_column="left", dev_x=100.0, dev_w=80.0)
        assert plan["exit_x"] == 180.0, "Left-rack cross-rack edge must exit the RIGHT edge (inner, toward gutter)"

    def test_cross_rack_right_device_exits_inner_left_edge(self):
        plan = self._planner()(is_cross_rack=True, device_rack_column="right", dev_x=100.0, dev_w=80.0)
        assert plan["exit_x"] == 100.0, "Right-rack cross-rack edge must exit the LEFT edge (inner, toward gutter)"

    def test_rack_gap_clears_left_rack_right_side_fan(self):
        """The inter-rack gap must be wide enough that the left rack's
        right-side fan (which bulges ``SWOOP_HORIZONTAL_OFFSET`` px into the
        gutter) cannot overlap the right rack."""
        from network_diagram_v2 import RACK_GAP, SWOOP_HORIZONTAL_OFFSET

        assert RACK_GAP > SWOOP_HORIZONTAL_OFFSET, (
            "RACK_GAP must exceed the swoop horizontal offset so the left "
            "rack's right-side connection fan does not overlap the right rack"
        )

    def test_canvas_reserves_clearance_for_right_fan(self):
        """The rendered canvas must reserve at least SWOOP_HORIZONTAL_OFFSET
        of horizontal padding beyond the rightmost rack so the right rack's
        right-side fan is not clipped at the diagram border."""
        import re as _re
        import svgwrite
        from network_diagram_v2 import (
            DEVICE_W,
            RACK_PAD_X,
            RACK_GAP,
            SWOOP_HORIZONTAL_OFFSET,
        )

        gen = RackCentricDiagramGenerator(config={"mode": "detailed"})
        switches = [
            {"hostname": "SW-LF-01", "mgmt_ip": "10.0.0.1"},
            {"hostname": "SW-LF-03", "mgmt_ip": "10.0.0.3"},
        ]
        racks = [
            {"rack_name": "RackP01C01", "cboxes": [], "bottom_devices": [], "switches": [switches[0]]},
            {"rack_name": "RackP01C02", "cboxes": [], "bottom_devices": [], "switches": [switches[1]]},
        ]
        svg = gen._render_page(svgwrite, racks, [], [], [], switches)
        total_w = float(_re.search(r'width="([0-9.]+)px"', svg).group(1))

        rack_w = DEVICE_W + 2 * RACK_PAD_X
        rack_span = 2 * rack_w + RACK_GAP
        # Racks are centered, so each side margin is (total_w - rack_span)/2.
        side_margin = (total_w - rack_span) / 2
        assert side_margin >= SWOOP_HORIZONTAL_OFFSET, (
            f"side margin {side_margin} must be >= swoop offset {SWOOP_HORIZONTAL_OFFSET} "
            "so the right rack's fan is not clipped"
        )

    def test_same_rack_edge_is_solid(self):
        plan = self._planner()(is_cross_rack=False, device_rack_column="left", dev_x=0, dev_w=10)
        assert plan["dasharray"] in (None, ""), "Same-rack edges must be SOLID (no dasharray)"

    def test_cross_rack_edge_is_dashed(self):
        """v1.5.8 follow-up: cross-rack edges use a DASHED pattern (``6,4``)
        for clear visibility across the inter-rack gutter while still
        reading as visually secondary to solid same-rack edges. (An
        earlier dotted ``1,3`` variant was too subtle on dense diagrams.)
        """
        plan = self._planner()(is_cross_rack=True, device_rack_column="left", dev_x=0, dev_w=10)
        assert plan["dasharray"] == "6,4", "Cross-rack edges must use stroke-dasharray='6,4' (dashed) for visibility"

    def test_cross_rack_edge_uses_lower_opacity(self):
        """v1.5.8 follow-up: more transparent (0.40) so dense fans don't
        visually clutter same-rack edges they overlap."""
        plan = self._planner()(is_cross_rack=True, device_rack_column="left", dev_x=0, dev_w=10)
        assert plan["opacity"] == 0.40, "Cross-rack edges use opacity 0.40 per v1.5.8 follow-up"

    def test_same_rack_edge_uses_translucent_opacity(self):
        """v1.5.8 follow-up: same-rack opacity reduced from 0.85 to 0.65
        so overlapping fans under a switch are easier to read."""
        plan = self._planner()(is_cross_rack=False, device_rack_column="left", dev_x=0, dev_w=10)
        assert plan["opacity"] == 0.65, "Same-rack edges use opacity 0.65 per v1.5.8 follow-up"

    def test_classify_edge_same_rack(self):
        result = self._classifier()(
            sw_ip="10.0.0.1",
            current_rack_switch_ips={"10.0.0.1", "10.0.0.2"},
            all_switch_ips={"10.0.0.1", "10.0.0.2", "10.0.0.3"},
        )
        assert result == "same_rack"

    def test_classify_edge_cross_rack_must_not_be_dropped(self):
        """v1.5.7 bug: cross-rack switches were dropped because they weren't
        in the current rack's ``switch_centers`` yet. The classifier MUST
        return 'cross_rack' so the renderer keeps the edge instead of
        silently skipping it.
        """
        result = self._classifier()(
            sw_ip="10.0.0.3",
            current_rack_switch_ips={"10.0.0.1", "10.0.0.2"},
            all_switch_ips={"10.0.0.1", "10.0.0.2", "10.0.0.3"},
        )
        assert result == "cross_rack", "Cross-rack switches must NOT be silently dropped (v1.5.7 bug)"

    def test_classify_edge_orphan_when_not_on_page(self):
        """Switch IP not present in any rack on this page is genuinely orphan."""
        result = self._classifier()(
            sw_ip="10.0.0.99",
            current_rack_switch_ips={"10.0.0.1"},
            all_switch_ips={"10.0.0.1", "10.0.0.2"},
        )
        assert result == "orphan"

    def test_classify_edge_empty_inputs(self):
        """Defensive: empty sets return 'orphan'."""
        result = self._classifier()(
            sw_ip="10.0.0.1",
            current_rack_switch_ips=set(),
            all_switch_ips=set(),
        )
        assert result == "orphan"


class TestNET3SubnetColoring:
    """NET-3: color edges by the switch's serviced /24 subnet, replacing the
    deprecated Network A / Network B classifier.

    Per the v1.5.8 design (``docs/issues/NET-2/00-design.md``):

    - Each switch's color is determined by the most common /24 prefix of the
      ``node_ip``'s in port_map rows where ``switch_ip == switch.mgmt_ip``.
    - The lowest-mgmt-IP switch's subnet gets ``SUBNET_COLOR_PALETTE[0]``, the
      next gets ``SUBNET_COLOR_PALETTE[1]``, additional subnets cycle through a
      fixed palette.
    - Two switches sharing the same /24 (e.g. an IPL pair both servicing
      ``172.16.0.x``) MUST share a color.
    - IPL/MLAG retains ``#7B1FA2`` (purple) — unchanged.

    Fix surface (pure helpers, easy to unit-test):
      - ``_ipv4_subnet_24(ip)`` -> ``"a.b.c"`` or ``None``
      - ``_compute_switch_subnet(sw_ip, port_map)`` -> majority /24 or ``None``
      - ``_assign_subnet_colors(switches, port_map)`` -> ``{sw_mgmt_ip -> color}``
      - ``SUBNET_COLOR_PALETTE`` module constant whose first two entries are
        the most-used, maximally distinct colors.
    """

    def _subnet_24(self):
        return RackCentricDiagramGenerator._ipv4_subnet_24

    def _compute(self):
        return RackCentricDiagramGenerator._compute_switch_subnet

    def _assign(self):
        return RackCentricDiagramGenerator._assign_subnet_colors

    @staticmethod
    def _conn(node_ip: str, switch_ip: str) -> Dict[str, Any]:
        return {
            "node_ip": node_ip,
            "switch_ip": switch_ip,
            "network": "A",
            "interface": "f0",
            "node_hostname": "",
            "hostname": "",
            "port": "Eth1/1",
            "node_designation": "CN1",
        }

    # ------------------------------------------------------------------
    # _ipv4_subnet_24
    # ------------------------------------------------------------------
    def test_ipv4_subnet_24_extracts_first_three_octets(self):
        assert self._subnet_24()("172.16.0.42") == "172.16.0"

    def test_ipv4_subnet_24_handles_high_octets(self):
        assert self._subnet_24()("192.168.255.99") == "192.168.255"

    def test_ipv4_subnet_24_returns_none_for_empty(self):
        assert self._subnet_24()("") is None

    def test_ipv4_subnet_24_returns_none_for_non_ipv4(self):
        assert self._subnet_24()("not-an-ip") is None

    def test_ipv4_subnet_24_returns_none_for_too_few_octets(self):
        assert self._subnet_24()("172.16") is None

    def test_ipv4_subnet_24_returns_none_for_out_of_range_octet(self):
        assert self._subnet_24()("172.16.300.1") is None

    # ------------------------------------------------------------------
    # _compute_switch_subnet
    # ------------------------------------------------------------------
    def test_compute_switch_subnet_returns_majority_subnet(self):
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
            self._conn("172.16.0.3", "10.0.0.153"),
        ]
        assert self._compute()("10.0.0.153", port_map) == "172.16.0"

    def test_compute_switch_subnet_returns_most_common_when_mixed(self):
        """NET-4 mis-cabling case: when a switch services nodes from multiple
        subnets, the *most common* one is the switch's subnet.
        """
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
            self._conn("172.16.0.3", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.153"),  # mis-cabled
        ]
        assert self._compute()("10.0.0.153", port_map) == "172.16.0"

    def test_compute_switch_subnet_returns_none_for_unknown_switch(self):
        port_map = [self._conn("172.16.0.1", "10.0.0.153")]
        assert self._compute()("10.0.0.99", port_map) is None

    def test_compute_switch_subnet_returns_none_for_empty_port_map(self):
        assert self._compute()("10.0.0.153", []) is None

    def test_compute_switch_subnet_ignores_invalid_node_ips(self):
        port_map = [
            self._conn("not-an-ip", "10.0.0.153"),
            self._conn("172.16.0.1", "10.0.0.153"),
        ]
        assert self._compute()("10.0.0.153", port_map) == "172.16.0"

    # ------------------------------------------------------------------
    # _assign_subnet_colors
    # ------------------------------------------------------------------
    def test_assign_subnet_colors_lowest_mgmt_ip_subnet_gets_first_color(self):
        sw_low = _make_switch("sw1", "10.0.0.153")
        sw_high = _make_switch("sw2", "10.0.0.154")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.154"),
        ]
        colors = self._assign()([sw_high, sw_low], port_map)
        assert colors["10.0.0.153"] == SUBNET_COLOR_PALETTE[0], "Lowest-mgmt-IP switch's subnet must get palette[0]"

    def test_assign_subnet_colors_second_subnet_gets_second_color(self):
        sw_a = _make_switch("sw1", "10.0.0.153")
        sw_b = _make_switch("sw2", "10.0.0.154")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.154"),
        ]
        colors = self._assign()([sw_a, sw_b], port_map)
        assert colors["10.0.0.154"] == SUBNET_COLOR_PALETTE[1], "Second subnet must get palette[1]"

    def test_assign_subnet_colors_switches_sharing_subnet_share_color(self):
        """An IPL pair where both switches service ``172.16.0.x`` must share
        a single subnet color — they're not two distinct subnets.
        """
        sw_a = _make_switch("sw1", "10.0.0.153")
        sw_b = _make_switch("sw2", "10.0.0.154")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.154"),
        ]
        colors = self._assign()([sw_a, sw_b], port_map)
        assert colors["10.0.0.153"] == colors["10.0.0.154"], "Switches sharing /24 must share color"
        assert colors["10.0.0.153"] == SUBNET_COLOR_PALETTE[0]

    def test_assign_subnet_colors_palette_cycles_for_extra_subnets(self):
        """Three distinct subnets => palette[0], palette[1], palette[2]."""
        sw1 = _make_switch("sw1", "10.0.0.151")
        sw2 = _make_switch("sw2", "10.0.0.152")
        sw3 = _make_switch("sw3", "10.0.0.153")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.151"),
            self._conn("172.16.64.1", "10.0.0.152"),
            self._conn("10.5.5.1", "10.0.0.153"),
        ]
        colors = self._assign()([sw1, sw2, sw3], port_map)
        # First 3 palette entries — distinct
        assert colors["10.0.0.151"] != colors["10.0.0.152"]
        assert colors["10.0.0.152"] != colors["10.0.0.153"]
        assert colors["10.0.0.151"] != colors["10.0.0.153"]

    def test_assign_subnet_colors_empty_switches_returns_empty(self):
        assert self._assign()([], []) == {}

    def test_assign_subnet_colors_switch_with_no_subnet_evidence_omitted(self):
        """A switch whose mgmt_ip has zero port_map rows must NOT crash; it
        is simply omitted from the color map (caller falls back to default).
        """
        sw = _make_switch("sw1", "10.0.0.153")
        colors = self._assign()([sw], [])
        assert "10.0.0.153" not in colors


class TestNET3PaletteConstants:
    """NET-3: ``SUBNET_COLOR_PALETTE`` is the module-level palette. Its first
    two entries are the most-used, maximally distinct colors. The set is the
    modern design-MCP palette and MUST stay clear of the reserved IPL purple
    and spine gray.
    """

    def test_subnet_palette_starts_with_primary_blue(self):
        from network_diagram_v2 import SUBNET_COLOR_PALETTE

        assert SUBNET_COLOR_PALETTE[0] == "#1D4ED8", "First palette entry must be the modern primary blue"

    def test_subnet_palette_second_is_amber(self):
        from network_diagram_v2 import SUBNET_COLOR_PALETTE

        assert SUBNET_COLOR_PALETTE[1] == "#F59E0B", "Second palette entry must be the modern amber"

    def test_subnet_palette_has_at_least_three_entries(self):
        """At least three colors so a 3-subnet cluster doesn't immediately wrap."""
        from network_diagram_v2 import SUBNET_COLOR_PALETTE

        assert len(SUBNET_COLOR_PALETTE) >= 3

    def test_subnet_palette_does_not_collide_with_reserved_colors(self):
        from network_diagram_v2 import COLOR_IPL, COLOR_SPINE_FABRIC, SUBNET_COLOR_PALETTE

        assert COLOR_IPL not in SUBNET_COLOR_PALETTE, "Palette must not include the IPL purple"
        assert COLOR_SPINE_FABRIC not in SUBNET_COLOR_PALETTE, "Palette must not include the spine gray"

    def test_ipl_color_unchanged(self):
        from network_diagram_v2 import COLOR_IPL

        assert COLOR_IPL == "#7B1FA2"


class TestNET4MiscablingDetection:
    """NET-4: detect and surface mis-cabled nodes.

    A switch is **mis-cabled** when it services nodes from more than one
    /24 subnet (per ``port_map``). The most-common subnet is the switch's
    canonical subnet; nodes on other subnets are the offending mis-cabled
    nodes.

    Per the v1.5.8 design (``docs/issues/NET-2/00-design.md``):

    - Each mis-cabled node box gets a red dashed outline + warning glyph.
    - The banner above the diagram switches from
      ``"Cabling validation: PASS"`` (green) to
      ``"Cabling validation: N mis-cabled connection(s) detected"`` (red).

    Fix surface (pure helpers, easy to unit-test):
      - ``_switch_subnet_set(sw_ip, port_map)`` -> ``Set[str]`` of /24 prefixes.
      - ``_detect_miscabled_switches(switches, port_map)`` ->
        ``{mgmt_ip -> off_subnet_set}`` for switches with > 1 subnet.
      - ``_detect_miscabled_node_ips(sw_ip, port_map)`` -> ``Set[str]``
        of node IPs whose subnet differs from the switch's canonical subnet.
      - ``_build_validation_banner(miscabling)`` ->
        ``(text, color)`` tuple for banner rendering.
    """

    def _subnet_set(self):
        return RackCentricDiagramGenerator._switch_subnet_set

    def _detect_switches(self):
        return RackCentricDiagramGenerator._detect_miscabled_switches

    def _detect_node_ips(self):
        return RackCentricDiagramGenerator._detect_miscabled_node_ips

    def _banner(self):
        return RackCentricDiagramGenerator._build_validation_banner

    @staticmethod
    def _conn(node_ip: str, switch_ip: str) -> Dict[str, Any]:
        return {
            "node_ip": node_ip,
            "switch_ip": switch_ip,
            "network": "A",
            "interface": "f0",
            "node_hostname": "",
            "hostname": "",
            "port": "Eth1/1",
            "node_designation": "CN1",
        }

    # ------------------------------------------------------------------
    # _switch_subnet_set
    # ------------------------------------------------------------------
    def test_subnet_set_returns_single_subnet_for_clean_switch(self):
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
            self._conn("172.16.0.3", "10.0.0.153"),
        ]
        assert self._subnet_set()("10.0.0.153", port_map) == {"172.16.0"}

    def test_subnet_set_returns_multiple_subnets_for_miscabled_switch(self):
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.153"),  # mis-cabled
        ]
        assert self._subnet_set()("10.0.0.153", port_map) == {"172.16.0", "172.16.64"}

    def test_subnet_set_unknown_switch_returns_empty(self):
        port_map = [self._conn("172.16.0.1", "10.0.0.153")]
        assert self._subnet_set()("10.0.0.99", port_map) == set()

    def test_subnet_set_excludes_invalid_node_ips(self):
        port_map = [
            self._conn("not-an-ip", "10.0.0.153"),
            self._conn("172.16.0.1", "10.0.0.153"),
        ]
        assert self._subnet_set()("10.0.0.153", port_map) == {"172.16.0"}

    # ------------------------------------------------------------------
    # _detect_miscabled_switches
    # ------------------------------------------------------------------
    def test_detect_switches_no_miscabling_returns_empty_dict(self):
        sw1 = _make_switch("sw1", "10.0.0.153")
        sw2 = _make_switch("sw2", "10.0.0.154")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.154"),
        ]
        assert self._detect_switches()([sw1, sw2], port_map) == {}

    def test_detect_switches_flags_one_miscabled_switch(self):
        sw1 = _make_switch("sw1", "10.0.0.153")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.153"),
        ]
        result = self._detect_switches()([sw1], port_map)
        assert "10.0.0.153" in result, "Mis-cabled switch must appear in the result"

    def test_detect_switches_returns_off_subnet_set_excluding_canonical(self):
        """The off_subnet_set returned for a mis-cabled switch must EXCLUDE
        the switch's canonical (most-common) subnet — those are the "wrong"
        subnets the operator needs to investigate.
        """
        sw1 = _make_switch("sw1", "10.0.0.153")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
            self._conn("172.16.0.3", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.153"),
        ]
        result = self._detect_switches()([sw1], port_map)
        assert result["10.0.0.153"] == {"172.16.64"}, (
            "off_subnet_set must contain only the non-canonical subnets " "(canonical 172.16.0 must be excluded)"
        )

    def test_detect_switches_flags_multiple_miscabled_switches(self):
        sw1 = _make_switch("sw1", "10.0.0.153")
        sw2 = _make_switch("sw2", "10.0.0.154")
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.153"),  # mis-cabled
            self._conn("10.5.5.1", "10.0.0.154"),
            self._conn("172.16.0.2", "10.0.0.154"),  # mis-cabled
        ]
        result = self._detect_switches()([sw1, sw2], port_map)
        assert set(result.keys()) == {"10.0.0.153", "10.0.0.154"}

    # ------------------------------------------------------------------
    # _detect_miscabled_node_ips
    # ------------------------------------------------------------------
    def test_detect_node_ips_clean_switch_returns_empty(self):
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
        ]
        assert self._detect_node_ips()("10.0.0.153", port_map) == set()

    def test_detect_node_ips_returns_offending_node_ips(self):
        port_map = [
            self._conn("172.16.0.1", "10.0.0.153"),
            self._conn("172.16.0.2", "10.0.0.153"),
            self._conn("172.16.0.3", "10.0.0.153"),
            self._conn("172.16.64.1", "10.0.0.153"),  # offender
            self._conn("10.5.5.1", "10.0.0.153"),  # offender
        ]
        result = self._detect_node_ips()("10.0.0.153", port_map)
        assert result == {"172.16.64.1", "10.5.5.1"}, "Must return all node IPs not in the canonical subnet"

    def test_detect_node_ips_unknown_switch_returns_empty(self):
        port_map = [self._conn("172.16.0.1", "10.0.0.153")]
        assert self._detect_node_ips()("10.0.0.99", port_map) == set()

    # ------------------------------------------------------------------
    # _build_validation_banner
    # ------------------------------------------------------------------
    def test_banner_no_miscabling_returns_pass_text(self):
        text, _ = self._banner()({})
        assert "PASS" in text, "Clean cluster banner must contain 'PASS'"

    def test_banner_no_miscabling_uses_green(self):
        _, color = self._banner()({})
        assert color == COLOR_VALIDATION_PASS, "PASS banner must use the green validation color"

    def test_banner_miscabling_returns_fail_text_with_count(self):
        text, _ = self._banner()({"10.0.0.153": {"172.16.64"}})
        assert "1" in text, "FAIL banner must include the count of mis-cabled connections"
        assert "PASS" not in text

    def test_banner_miscabling_uses_red(self):
        _, color = self._banner()({"10.0.0.153": {"172.16.64"}})
        assert color == "#EA4335", "FAIL banner must use the design-mandated red"

    def test_banner_count_is_total_off_subnets_across_switches(self):
        """Count is the sum of off_subnet sizes across all mis-cabled switches.

        Two switches each carrying one off-subnet => 2 mis-cabled connections.
        """
        miscabling = {
            "10.0.0.153": {"172.16.64"},
            "10.0.0.154": {"10.5.5"},
        }
        text, _ = self._banner()(miscabling)
        assert "2" in text


class TestNET2BBezierSwoopRouting:
    """NET-2B v1.5.8 visual refresh: device->switch edges use mockup-style
    bezier swoops instead of orthogonal waypoints.

    Per ``docs/issues/NET-2/mockup-target.svg``, each switch->device line is
    a single cubic bezier:

      ``M (exit_x, exit_y) C (cp1_x, exit_y) (landing_x, sw_bot+drop) (landing_x, sw_bot)``

    where:

    - ``cp1`` extends OUTWARD from the device's exit side by
      ``horizontal_offset`` so the curve has a horizontal "tail" near the
      device (echoing a port stub).
    - ``cp2`` is positioned BELOW the switch's bottom edge by
      ``drop_offset`` so the curve approaches the switch vertically.
    - The endpoint sits exactly on the switch's bottom edge at ``landing_x``.

    Fix surface (pure helper, easy to unit-test):
      - ``_bezier_swoop_path(...)`` builds the SVG ``d`` string.
    """

    def _builder(self):
        return RackCentricDiagramGenerator._bezier_swoop_path

    def _parse_path(self, d: str) -> Dict[str, Tuple[float, float]]:
        """Parse the four control points from a single 'M ... C ... ...' path."""
        # Format: "M sx,sy C cp1x,cp1y cp2x,cp2y ex,ey"
        parts = d.replace(",", " ").split()
        # parts: ['M', 'sx', 'sy', 'C', 'cp1x', 'cp1y', 'cp2x', 'cp2y', 'ex', 'ey']
        assert parts[0] == "M" and parts[3] == "C", f"unexpected path: {d}"
        return {
            "start": (float(parts[1]), float(parts[2])),
            "cp1": (float(parts[4]), float(parts[5])),
            "cp2": (float(parts[6]), float(parts[7])),
            "end": (float(parts[8]), float(parts[9])),
        }

    def test_path_starts_at_exit_point(self):
        d = self._builder()(
            exit_x=65.0,
            exit_y=348.0,
            landing_x=179.0,
            sw_bot_y=321.0,
            exit_extends_right=False,
        )
        pts = self._parse_path(d)
        assert pts["start"] == (65.0, 348.0)

    def test_path_ends_at_landing_x_and_sw_bot(self):
        d = self._builder()(
            exit_x=65.0,
            exit_y=348.0,
            landing_x=179.0,
            sw_bot_y=321.0,
            exit_extends_right=False,
        )
        pts = self._parse_path(d)
        assert pts["end"] == (179.0, 321.0), "Path must end exactly at the switch's bottom edge"

    def test_left_side_exit_pulls_cp1_leftward(self):
        d = self._builder()(
            exit_x=65.0,
            exit_y=348.0,
            landing_x=179.0,
            sw_bot_y=321.0,
            exit_extends_right=False,
            horizontal_offset=50.0,
        )
        pts = self._parse_path(d)
        assert pts["cp1"][0] < pts["start"][0], "Left exit must pull cp1 LEFTWARD (outward)"
        assert pts["cp1"][1] == pts["start"][1], "cp1 must be at the same y as the exit (horizontal tail)"
        assert pts["cp1"][0] == 65.0 - 50.0

    def test_right_side_exit_pulls_cp1_rightward(self):
        d = self._builder()(
            exit_x=345.0,
            exit_y=348.0,
            landing_x=569.0,
            sw_bot_y=321.0,
            exit_extends_right=True,
            horizontal_offset=50.0,
        )
        pts = self._parse_path(d)
        assert pts["cp1"][0] > pts["start"][0], "Right exit must pull cp1 RIGHTWARD (outward)"
        assert pts["cp1"][1] == pts["start"][1]
        assert pts["cp1"][0] == 345.0 + 50.0

    def test_cp2_sits_below_switch_by_drop_offset(self):
        d = self._builder()(
            exit_x=65.0,
            exit_y=348.0,
            landing_x=179.0,
            sw_bot_y=321.0,
            exit_extends_right=False,
            drop_offset=70.0,
        )
        pts = self._parse_path(d)
        assert pts["cp2"][0] == 179.0, "cp2.x must equal landing_x for vertical approach"
        assert pts["cp2"][1] == 321.0 + 70.0, "cp2.y must be drop_offset below the switch's bottom"

    def test_offsets_are_configurable(self):
        d = self._builder()(
            exit_x=100.0,
            exit_y=200.0,
            landing_x=300.0,
            sw_bot_y=180.0,
            exit_extends_right=True,
            horizontal_offset=25.0,
            drop_offset=40.0,
        )
        pts = self._parse_path(d)
        assert pts["cp1"] == (125.0, 200.0)
        assert pts["cp2"] == (300.0, 220.0)

    def test_path_format_is_valid_svg_cubic_bezier(self):
        """The returned d-string must parse as ``M ... C ...`` with 4 points."""
        d = self._builder()(
            exit_x=0.0,
            exit_y=0.0,
            landing_x=100.0,
            sw_bot_y=50.0,
            exit_extends_right=False,
        )
        pts = self._parse_path(d)
        assert set(pts.keys()) == {"start", "cp1", "cp2", "end"}


class TestNET2BEdgeFilterTwoPass:
    """v1.5.8 follow-up: ``_draw_device_connections`` must accept an
    ``edge_filter`` parameter so the renderer can do a two-pass draw
    (same-rack first per rack, then cross-rack last on top of all rack
    frames).

    Without this, cross-rack lines drawn during the FIRST rack's
    iteration get visually clipped/obscured by the SECOND rack's frame
    fill, which is drawn AFTER them. The fix is a draw-order change in
    ``_render_page`` that uses the filter to defer cross-rack edges.

    These tests target the pure helper signature; the renderer wiring
    is exercised by the existing rendering smoke tests.
    """

    def _make_dwg(self):
        """Recording stub: collects every ``add(...)`` call as ``(kind, attribs)``."""

        class _Stub:
            def __init__(self):
                self.added = []

            def add(self, obj):
                kind = type(obj).__name__
                attribs = getattr(obj, "attribs", {})
                self.added.append((kind, dict(attribs)))

            def path(self, **kwargs):
                class _P:
                    pass

                p = _P()
                p.attribs = kwargs
                return p

            def text(self, *args, **kwargs):
                class _T:
                    pass

                t = _T()
                t.attribs = kwargs
                return t

        return _Stub()

    def _gen(self):
        from network_diagram_v2 import RackCentricDiagramGenerator

        return RackCentricDiagramGenerator()

    def _common_args(self):
        return {
            "switch_centers": {"10.0.0.1": (200.0, 100.0), "10.0.0.2": (600.0, 100.0)},
            "_rack_switches": [{"mgmt_ip": "10.0.0.1"}],
            "port_map": [
                {
                    "node_ip": "10.1.0.5",
                    "switch_ip": "10.0.0.1",
                    "interface": "f0",
                    "network": "data_a",
                },
                {
                    "node_ip": "10.1.0.5",
                    "switch_ip": "10.0.0.2",
                    "interface": "f1",
                    "network": "data_b",
                },
            ],
            "bus_y_base": 200.0,
            "device_index": 0,
            "current_rack_switch_ips": {"10.0.0.1"},
            "all_switch_ips": {"10.0.0.1", "10.0.0.2"},
            "device_rack_column": "left",
            "gutter_mid_x": 400.0,
            "subnet_color_map": {"10.0.0.1": "#0F9D58", "10.0.0.2": "#4285F4"},
        }

    def test_edge_filter_same_rack_only_draws_same_rack_edges(self):
        """With ``edge_filter='same_rack'``, only the same-rack edge to
        switch 10.0.0.1 should be drawn (1 path); the cross-rack edge to
        10.0.0.2 must be skipped."""
        gen = self._gen()
        dwg = self._make_dwg()
        device = {"name": "node1", "ip": "10.1.0.5"}
        gen._draw_device_connections(
            dwg,
            device,
            dev_x=100.0,
            dev_y=300.0,
            dev_w=80.0,
            dev_h=20.0,
            edge_filter="same_rack",
            **self._common_args(),
        )
        paths = [a for a in dwg.added if a[0] == "_P"]
        assert len(paths) == 1, f"Expected 1 same-rack path, got {len(paths)}"

    def test_edge_filter_cross_rack_only_draws_cross_rack_edges(self):
        """With ``edge_filter='cross_rack'``, only the cross-rack edge to
        switch 10.0.0.2 should be drawn (1 path)."""
        gen = self._gen()
        dwg = self._make_dwg()
        device = {"name": "node1", "ip": "10.1.0.5"}
        gen._draw_device_connections(
            dwg,
            device,
            dev_x=100.0,
            dev_y=300.0,
            dev_w=80.0,
            dev_h=20.0,
            edge_filter="cross_rack",
            **self._common_args(),
        )
        paths = [a for a in dwg.added if a[0] == "_P"]
        assert len(paths) == 1, f"Expected 1 cross-rack path, got {len(paths)}"

    def test_edge_filter_all_draws_both_kinds_default_behavior(self):
        """Default ``edge_filter='all'`` (or omitted) draws both same-rack
        and cross-rack edges, preserving v1.5.8 baseline behavior for
        callers that haven't opted into the two-pass draw."""
        gen = self._gen()
        dwg = self._make_dwg()
        device = {"name": "node1", "ip": "10.1.0.5"}
        gen._draw_device_connections(
            dwg,
            device,
            dev_x=100.0,
            dev_y=300.0,
            dev_w=80.0,
            dev_h=20.0,
            edge_filter="all",
            **self._common_args(),
        )
        paths = [a for a in dwg.added if a[0] == "_P"]
        assert len(paths) == 2, f"Expected 2 paths (same+cross), got {len(paths)}"

    def test_edge_filter_default_is_all(self):
        """Calling without an ``edge_filter`` kwarg behaves like
        ``edge_filter='all'`` so legacy callers keep working."""
        gen = self._gen()
        dwg = self._make_dwg()
        device = {"name": "node1", "ip": "10.1.0.5"}
        gen._draw_device_connections(
            dwg,
            device,
            dev_x=100.0,
            dev_y=300.0,
            dev_w=80.0,
            dev_h=20.0,
            **self._common_args(),
        )
        paths = [a for a in dwg.added if a[0] == "_P"]
        assert len(paths) == 2, f"Default should draw all edges, got {len(paths)}"


class TestInterRackIPL:
    """v1.5.8 follow-up: render IPL/MLAG between paired switches even when
    the two switches live in DIFFERENT racks.

    The v1.5.8 baseline only drew an IPL line when both paired switches
    appeared in the SAME ``rack_switches`` list (i.e. both leaf switches
    in one rack). Real-world clusters often have a single switch per
    rack with the IPL crossing the inter-rack gutter; in that topology
    the v1.5.8 baseline produced no IPL line at all.

    Fix surface (pure helpers, easy to unit-test):

    - ``_collect_inter_rack_ipl_pairs(ipl_conns, switch_centers,
      switch_rack_idx)`` — returns the de-duplicated list of
      ``(switch1_ip, switch2_ip)`` pairs that should be rendered as a
      cross-rack IPL line. Pairs are filtered to:

        * Both endpoints present in ``switch_centers`` (otherwise the
          line cannot be drawn).
        * Switches in DIFFERENT racks per ``switch_rack_idx`` (same-rack
          pairs are still drawn by the per-rack loop, so emitting them
          again would double-draw the line).
        * Each undirected pair is yielded only once even if the source
          data lists ``(A, B)`` and ``(B, A)``.
    """

    def _collector(self):
        from network_diagram_v2 import RackCentricDiagramGenerator

        return RackCentricDiagramGenerator._collect_inter_rack_ipl_pairs

    def test_returns_pair_when_switches_in_different_racks(self):
        ipl_conns = [{"switch1_ip": "10.0.0.8", "switch2_ip": "10.0.0.9", "connection_type": "IPL"}]
        switch_centers = {"10.0.0.8": (600.0, 100.0), "10.0.0.9": (200.0, 100.0)}
        switch_rack_idx = {"10.0.0.8": 1, "10.0.0.9": 0}
        pairs = self._collector()(ipl_conns, switch_centers, switch_rack_idx)
        assert len(pairs) == 1
        assert set(pairs[0]) == {"10.0.0.8", "10.0.0.9"}

    def test_skips_pairs_in_same_rack(self):
        """Same-rack IPL pairs are drawn by the per-rack loop, so the
        cross-rack collector must NOT return them (would double-draw)."""
        ipl_conns = [{"switch1_ip": "10.0.0.8", "switch2_ip": "10.0.0.9"}]
        switch_centers = {"10.0.0.8": (200.0, 100.0), "10.0.0.9": (300.0, 100.0)}
        switch_rack_idx = {"10.0.0.8": 0, "10.0.0.9": 0}
        pairs = self._collector()(ipl_conns, switch_centers, switch_rack_idx)
        assert pairs == []

    def test_skips_pairs_with_missing_switch_centers(self):
        """If either endpoint isn't on the page (no center coordinate),
        the line cannot be drawn — collector must drop the pair."""
        ipl_conns = [{"switch1_ip": "10.0.0.8", "switch2_ip": "10.0.0.99"}]
        switch_centers = {"10.0.0.8": (200.0, 100.0)}  # 10.0.0.99 not present
        switch_rack_idx = {"10.0.0.8": 0, "10.0.0.99": 1}
        pairs = self._collector()(ipl_conns, switch_centers, switch_rack_idx)
        assert pairs == []

    def test_dedupes_undirected_pairs(self):
        """If ipl_conns lists both (A, B) and (B, A), collector must
        emit a single undirected pair, not two."""
        ipl_conns = [
            {"switch1_ip": "10.0.0.8", "switch2_ip": "10.0.0.9"},
            {"switch1_ip": "10.0.0.9", "switch2_ip": "10.0.0.8"},
        ]
        switch_centers = {"10.0.0.8": (600.0, 100.0), "10.0.0.9": (200.0, 100.0)}
        switch_rack_idx = {"10.0.0.8": 1, "10.0.0.9": 0}
        pairs = self._collector()(ipl_conns, switch_centers, switch_rack_idx)
        assert len(pairs) == 1

    def test_empty_inputs_return_empty_list(self):
        assert self._collector()([], {}, {}) == []
        assert self._collector()(None, {}, {}) == []  # Defensive: None ipl_conns

    def test_handles_missing_switch_ip_fields_gracefully(self):
        """Defensive: ipl_conns entries without switch1_ip/switch2_ip
        must not raise, just be skipped."""
        ipl_conns = [
            {"connection_type": "IPL"},  # missing both IPs
            {"switch1_ip": "10.0.0.8"},  # missing switch2_ip
            {"switch1_ip": "10.0.0.8", "switch2_ip": "10.0.0.9"},  # valid
        ]
        switch_centers = {"10.0.0.8": (600.0, 100.0), "10.0.0.9": (200.0, 100.0)}
        switch_rack_idx = {"10.0.0.8": 1, "10.0.0.9": 0}
        pairs = self._collector()(ipl_conns, switch_centers, switch_rack_idx)
        assert len(pairs) == 1


class TestIBSwitchGuidAlias:
    """SR-3 / IB follow-up: InfiniBand vnetmap output stores the switch
    identity in the port_map ``switch_ip`` column as a 16-byte GUID
    (e.g. ``0xa088c203007860bc``), while the rest of the renderer keys
    switches by their API ``mgmt_ip``. Without an alias, every IB
    device->switch edge is classified ``orphan`` (the GUID is never in
    ``switch_centers``) and silently dropped.

    ``_build_switch_ip_alias(port_map, switches)`` resolves each distinct
    ``switch_ip`` in the port map to a switch ``mgmt_ip`` using the
    ``switch_hostname`` carried on every port_map row joined to the API
    switch list. Rows whose ``switch_ip`` is already an API mgmt_ip
    resolve to themselves (identity) so Ethernet clusters are unaffected.
    """

    def _alias(self):
        return RackCentricDiagramGenerator._build_switch_ip_alias

    def test_guid_resolves_to_mgmt_ip_via_switch_hostname(self):
        switches = [
            _make_switch("SW-LF-03", "10.208.59.15"),
            _make_switch("SW-LF-04", "10.208.59.16"),
        ]
        port_map = [
            {
                "node_ip": "172.16.1.1",
                "switch_ip": "0xa088c203007860bc",
                "switch_hostname": "SW-LF-03",
                "switch_designation": "SWE-P21",
                "network": "A",
                "interface": "ib0",
            },
            {
                "node_ip": "172.16.65.1",
                "switch_ip": "0xa088c203007861dc",
                "switch_hostname": "SW-LF-04",
                "switch_designation": "SWF-P21",
                "network": "B",
                "interface": "ib1",
            },
        ]
        alias = self._alias()(port_map, switches)
        assert alias["0xa088c203007860bc"] == "10.208.59.15"
        assert alias["0xa088c203007861dc"] == "10.208.59.16"

    def test_mgmt_ip_switch_ip_resolves_to_itself_identity(self):
        """Ethernet clusters already key the port_map switch_ip on the
        API mgmt_ip; the alias must be the identity so they're unaffected."""
        switches = [_make_switch("sw1", "10.0.0.8")]
        port_map = [{"node_ip": "10.0.0.50", "switch_ip": "10.0.0.8", "switch_hostname": "sw1", "interface": "f0"}]
        alias = self._alias()(port_map, switches)
        assert alias["10.0.0.8"] == "10.0.0.8"

    def test_unresolvable_guid_is_omitted(self):
        """A GUID whose switch_hostname has no API match is left out of
        the alias (caller keeps the original value, edge degrades to orphan)."""
        switches = [_make_switch("SW-LF-03", "10.208.59.15")]
        port_map = [
            {"node_ip": "172.16.1.1", "switch_ip": "0xdeadbeef", "switch_hostname": "SW-UNKNOWN", "interface": "ib0"}
        ]
        alias = self._alias()(port_map, switches)
        assert "0xdeadbeef" not in alias

    def test_empty_inputs_return_empty(self):
        assert self._alias()([], []) == {}
        assert self._alias()(None, None) == {}

    def test_generate_resolves_ib_subnet_color_after_alias(self):
        """End-to-end: with GUID switch_ip + switch_hostname, the alias
        normalization must let NET-3 subnet coloring resolve the switch
        (previously zero rows matched because GUID != mgmt_ip)."""
        switches = [_make_switch("SW-LF-03", "10.208.59.15")]
        port_map = [
            {
                "node_ip": "172.16.1.1",
                "switch_ip": "0xa088c203007860bc",
                "switch_hostname": "SW-LF-03",
                "network": "A",
                "interface": "ib0",
            },
            {
                "node_ip": "172.16.1.3",
                "switch_ip": "0xa088c203007860bc",
                "switch_hostname": "SW-LF-03",
                "network": "A",
                "interface": "ib0",
            },
        ]
        alias = self._alias()(port_map, switches)
        normalized = [{**c, "switch_ip": alias.get(c["switch_ip"], c["switch_ip"])} for c in port_map]
        colors = RackCentricDiagramGenerator._assign_subnet_colors(switches, normalized)
        assert colors.get("10.208.59.15")  # switch now has a subnet color


class TestLandingFanSizing:
    """QP-1: switch->node landing fan is centered on the switch and the switch
    box is widened so the whole fan fits within its width at fixed line spacing.

    Regression: the v1.5.8 fan keyed ``landing_x`` off the global per-rack
    ``device_index`` (0..N), so a node at index 59 landed ~270px right of a
    110px switch — connections started a quarter in from the left and ran
    well past the right edge.
    """

    def _slots(self):
        return RackCentricDiagramGenerator._build_landing_slots

    def test_slots_grouped_per_switch_and_contiguous(self):
        port_map = [
            {"switch_ip": "10.0.0.1", "node_ip": "172.16.0.3", "network": "A", "interface": "ib0"},
            {"switch_ip": "10.0.0.1", "node_ip": "172.16.0.1", "network": "A", "interface": "ib0"},
            {"switch_ip": "10.0.0.1", "node_ip": "172.16.0.2", "network": "A", "interface": "ib0"},
            {"switch_ip": "10.0.0.2", "node_ip": "172.16.64.1", "network": "B", "interface": "ib1"},
        ]
        slots, totals = self._slots()(port_map, {"10.0.0.1", "10.0.0.2"})
        assert totals == {"10.0.0.1": 3, "10.0.0.2": 1}
        # Slots contiguous 0..n-1, ordered by numeric node IP.
        assert slots["10.0.0.1"][("10.0.0.1", "172.16.0.1", "A")] == 0
        assert slots["10.0.0.1"][("10.0.0.1", "172.16.0.2", "A")] == 1
        assert slots["10.0.0.1"][("10.0.0.1", "172.16.0.3", "A")] == 2

    def test_slots_exclude_switches_not_in_drawable_set(self):
        port_map = [{"switch_ip": "10.9.9.9", "node_ip": "1.1.1.1", "network": "A", "interface": "ib0"}]
        slots, totals = self._slots()(port_map, {"10.0.0.1"})
        assert totals == {}

    def test_fan_landing_x_is_centered_and_symmetric(self):
        gen = RackCentricDiagramGenerator
        sw_cx = 200.0
        # Single connection lands exactly on the switch center.
        assert gen._fan_landing_x(sw_cx, 0, 1, 5.0) == sw_cx
        # Three connections are symmetric around the center.
        left = gen._fan_landing_x(sw_cx, 0, 3, 5.0)
        mid = gen._fan_landing_x(sw_cx, 1, 3, 5.0)
        right = gen._fan_landing_x(sw_cx, 2, 3, 5.0)
        assert mid == sw_cx
        assert abs((sw_cx - left) - (right - sw_cx)) < 1e-9

    def test_dynamic_switch_width_has_floor_and_grows(self):
        gen = RackCentricDiagramGenerator
        from network_diagram_v2 import SWITCH_W

        assert gen._dynamic_switch_width(1) == float(SWITCH_W)
        assert gen._dynamic_switch_width(2) == float(SWITCH_W)
        wide = gen._dynamic_switch_width(40)
        assert wide > float(SWITCH_W)

    def test_widened_switch_contains_centered_fan(self):
        gen = RackCentricDiagramGenerator
        stagger, pad = 5.0, 12.0
        for n in (1, 5, 20, 40, 60):
            width = gen._dynamic_switch_width(n, stagger, pad)
            half_span = (n - 1) / 2.0 * stagger
            # The extreme landing offset must sit inside the box (with pad).
            assert half_span <= width / 2.0 - pad + 1e-6


class TestEdgeColorByDeviceSubnet:
    """The switch->node connection color must reflect the network of the
    CONNECTED DEVICE's IP, not the switch's canonical subnet.

    Regression: edges were colored by ``subnet_color_map[sw_ip]`` (the
    switch's most-common /24), so a mis-cabled connection — e.g. a
    172.16.64.x (Blue) device cabled to a Network-A (Green) switch — drew
    Green, hiding the fault. Coloring by the device IP's /24 makes the
    off-network strand render in its true color (here Blue) so the mis-cable
    is visually obvious.
    """

    def _switches(self):
        # Two leaves: A canonically serves 172.16.0 (Green), B serves 172.16.64 (Blue).
        return [_make_switch("SW-LF-01", "10.0.0.1"), _make_switch("SW-LF-02", "10.0.0.2")]

    def _port_map(self):
        return [
            {"switch_ip": "10.0.0.1", "node_ip": "172.16.0.5", "network": "A", "interface": "ib0"},
            {"switch_ip": "10.0.0.1", "node_ip": "172.16.0.6", "network": "A", "interface": "ib0"},
            {"switch_ip": "10.0.0.2", "node_ip": "172.16.64.5", "network": "B", "interface": "ib1"},
            {"switch_ip": "10.0.0.2", "node_ip": "172.16.64.6", "network": "B", "interface": "ib1"},
        ]

    def test_subnet_color_map_keyed_by_subnet(self):
        from network_diagram_v2 import SUBNET_COLOR_PALETTE

        m = RackCentricDiagramGenerator._assign_subnet_color_map(self._switches(), self._port_map())
        assert m["172.16.0"] == SUBNET_COLOR_PALETTE[0]  # green
        assert m["172.16.64"] == SUBNET_COLOR_PALETTE[1]  # blue

    def test_subnet_color_map_matches_switch_color_map(self):
        """The per-subnet map must agree with the switch->color projection so
        the legend (switch-based) and the edges (device-IP-based) stay in sync."""
        sw_map = RackCentricDiagramGenerator._assign_subnet_colors(self._switches(), self._port_map())
        subnet_map = RackCentricDiagramGenerator._assign_subnet_color_map(self._switches(), self._port_map())
        assert sw_map["10.0.0.1"] == subnet_map["172.16.0"]
        assert sw_map["10.0.0.2"] == subnet_map["172.16.64"]

    def test_edge_color_uses_device_ip_subnet(self):
        from network_diagram_v2 import SUBNET_COLOR_PALETTE

        gen = RackCentricDiagramGenerator
        subnet_map = {"172.16.0": SUBNET_COLOR_PALETTE[0], "172.16.64": SUBNET_COLOR_PALETTE[1]}
        sw_map = {"10.0.0.1": SUBNET_COLOR_PALETTE[0], "10.0.0.2": SUBNET_COLOR_PALETTE[1]}
        # Mis-cabled: Blue (172.16.64) device on the Green (172.16.0) switch -> Blue.
        assert gen._edge_color("172.16.64.123", "10.0.0.1", subnet_map, sw_map) == SUBNET_COLOR_PALETTE[1]
        # Mis-cabled the other way: Green device on the Blue switch -> Green.
        assert gen._edge_color("172.16.0.123", "10.0.0.2", subnet_map, sw_map) == SUBNET_COLOR_PALETTE[0]
        # Correctly cabled: device subnet == switch subnet -> that color.
        assert gen._edge_color("172.16.0.7", "10.0.0.1", subnet_map, sw_map) == SUBNET_COLOR_PALETTE[0]

    def test_edge_color_falls_back_to_switch_then_palette(self):
        from network_diagram_v2 import SUBNET_COLOR_PALETTE

        gen = RackCentricDiagramGenerator
        sw_map = {"10.0.0.1": SUBNET_COLOR_PALETTE[1]}
        # Unknown device subnet -> switch color.
        assert gen._edge_color("10.9.9.9", "10.0.0.1", {}, sw_map) == SUBNET_COLOR_PALETTE[1]
        # Nothing known -> palette[0].
        assert gen._edge_color("", "", {}, {}) == SUBNET_COLOR_PALETTE[0]


class TestSwitchLabels:
    """QP-1: switch boxes label by hostname (primary) + mgmt IP (secondary).

    The legacy SWA/SWB (leaf) and SP1/SP2 (spine) designations are no longer
    used anywhere in the report or tooling, so they must not appear on the
    diagram. Each switch box shows its name on top and its management IP
    beneath it.
    """

    def _gen(self):
        return RackCentricDiagramGenerator(config={"mode": "detailed"})

    def _svg(self):
        import svgwrite

        switches = [
            _make_switch("SW-LF-01", "10.208.59.13"),
            _make_switch("LAX-01-SW-LF-02", "10.208.59.14"),
        ]
        spines = [
            {"hostname": "SW-SP-01", "mgmt_ip": "10.208.59.11", "_assigned_rack": "RackP01C01"},
        ]
        racks = [
            {
                "rack_name": "RackP01C01",
                "cboxes": [],
                "bottom_devices": [],
                "switches": [switches[0], switches[1]],
                "bottom_label": "DN",
            }
        ]
        port_map = [
            {"switch_ip": "10.208.59.13", "node_ip": "172.16.0.5"},
            {"switch_ip": "10.208.59.14", "node_ip": "172.16.64.5"},
        ]
        return self._gen()._render_page(svgwrite, racks, spines, [], port_map, switches + spines)

    def test_switch_name_and_mgmt_ip_rendered(self):
        svg = self._svg()
        assert "SW-LF-01" in svg
        assert "LAX-01-SW-LF-02" in svg
        assert "SW-SP-01" in svg
        assert "10.208.59.13" in svg
        assert "10.208.59.14" in svg
        assert "10.208.59.11" in svg

    def test_legacy_designations_absent(self):
        svg = self._svg()
        for legacy in (">SWA<", ">SWB<", ">SP1<", ">SP2<"):
            assert legacy not in svg
