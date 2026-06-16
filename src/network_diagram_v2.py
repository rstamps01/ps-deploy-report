"""
Rack-Centric Network Diagram Generator (Design 3)

Generates a logical network topology diagram using an SVG renderer where each
rack is a self-contained column with its own local leaf-switch pair.  Spine
switches (when present) span across the top.

Connections use orthogonal (vertical-horizontal-vertical) routing with rounded
corners at each bend so that individual links remain traceable even in large
clusters.

Output: one or more PNG files (converted from SVG via cairosvg) suitable for
embedding in the PDF report.
"""

from __future__ import annotations

import logging
import os
import platform
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

if platform.system() == "Darwin":
    _brew_lib = "/opt/homebrew/lib"
    _dyld_key = "DYLD_FALLBACK_LIBRARY_PATH"
    _cur = os.environ.get(_dyld_key, "")
    if _brew_lib not in _cur:
        os.environ[_dyld_key] = f"{_brew_lib}:{_cur}" if _cur else _brew_lib

try:
    import svgwrite as _svgwrite

    _SVGWRITE_AVAILABLE = True
except ImportError:
    _svgwrite = None  # type: ignore[assignment]
    _SVGWRITE_AVAILABLE = False

_CAIROSVG_AVAILABLE = False
try:
    import cairosvg as _cairosvg  # noqa: F401

    _CAIROSVG_AVAILABLE = True
except (ImportError, OSError):
    pass

# ---------------------------------------------------------------------------
# Color palette (B7)
# ---------------------------------------------------------------------------
# NET-3: subnet-based edge coloring replaces the deprecated Network A/B
# classifier. Edges are colored by the switch's serviced /24 subnet:
# the lowest-mgmt-IP switch's subnet gets palette[0] (design-mandated green),
# the next gets palette[1] (design-mandated blue), additional subnets cycle
# through the rest of the palette. Switches sharing a subnet share a color.
SUBNET_COLOR_PALETTE: List[str] = [
    "#0F9D58",  # teal-green (design-mandated for first subnet)
    "#4285F4",  # deep blue  (design-mandated for second subnet)
    "#FF6F00",  # amber/orange
    "#00838F",  # dark teal
    "#AB47BC",  # mauve (intentionally distinct from IPL purple)
]
# Backward-compatible aliases — kept so existing test/code references resolve.
# Prefer SUBNET_COLOR_PALETTE for new code.
COLOR_NETWORK_A = SUBNET_COLOR_PALETTE[0]
COLOR_NETWORK_B = SUBNET_COLOR_PALETTE[1]
COLOR_IPL = "#7B1FA2"  # purple
COLOR_SPINE_FABRIC = "#757575"  # gray
COLOR_DEVICE_STROKE = "#2F2042"
COLOR_CBOX_FILL = "#c8e6f8"
COLOR_DBOX_FILL = "#ffe0b2"
COLOR_SWITCH_FILL = "#e8f5e9"
COLOR_SPINE_FILL = "#e0f2f1"
COLOR_RACK_BG = "#f5f5f5"
COLOR_RACK_HEADER = "#616161"
COLOR_TEXT = "#212121"
COLOR_LABEL = "#424242"

# ---------------------------------------------------------------------------
# Layout constants (points; 1 pt = 1/72 in)
# ---------------------------------------------------------------------------
DEVICE_W = 230
DEVICE_H = 28
DEVICE_GAP = 6
SWITCH_W = 110
SWITCH_H = 32
SWITCH_GAP = 24
RACK_PAD_X = 16
RACK_PAD_TOP = 40  # space for rack header text
RACK_PAD_BOTTOM = 12
# Horizontal distance the bezier swoop's first control point extends out
# from a device's exit side (must match _bezier_swoop_path's default). The
# inter-rack gap is derived from it so the left rack's right-side fan, which
# bulges this far into the gutter, never overlaps the right rack.
SWOOP_HORIZONTAL_OFFSET = 50.0
# Horizontal gap between rack columns. Sized to clear the left rack's
# right-side connection fan (swoop offset + clearance) so both racks can
# route connections off their RIGHT edge without the left fan touching the
# right rack.
RACK_GAP = int(SWOOP_HORIZONTAL_OFFSET) + 30  # 80
SPINE_ROW_H = 60
SPINE_GAP = 40  # gap between spine tier and racks
LEGEND_H = 36
# Legend pill metrics. Pills are sized to their label so long labels
# (e.g. "ISL (Leaf-Spine)") are not clipped, and the row is centered and
# clamped to the margin so the leftmost pill is never cut off (the canvas
# width in _render_page is also widened to hold the whole row).
LEGEND_PILL_H = 22
LEGEND_PILL_GAP = 14  # horizontal gap between adjacent pills
LEGEND_PILL_MIN_W = 96  # floor so short labels still read as pills
LEGEND_TEXT_X = 32  # label x-offset within a pill (after the color swatch line)
LEGEND_PILL_PAD_R = 12  # right padding after the label text
LEGEND_CHAR_W = 5.4  # approx px per char for 9px bold Helvetica
TITLE_H = 36
MARGIN = 30
BEND_R = 6  # radius for rounded corners on connections
CONN_OFFSET_A = 8  # left-edge offset for Network A connections
CONN_OFFSET_B = 8  # right-edge offset for Network B connections

# Portrait Letter (8.5 x 11 in) in points
PORTRAIT_W = 8.5 * 72  # 612
PORTRAIT_H = 11 * 72  # 792

# Max racks per page before splitting (portrait fits 2 side-by-side)
MAX_RACKS_PER_PAGE = 2

# ---------------------------------------------------------------------------
# Inline flat-icon SVG path data (B5)
# ---------------------------------------------------------------------------
ICON_SERVER = (
    "M3,2 h18 a1,1 0 0,1 1,1 v6 a1,1 0 0,1 -1,1 H3 a1,1 0 0,1 -1,-1 V3 " "a1,1 0 0,1 1,-1 Z M5,5 h2 v2 H5Z M9,5.5 h10"
)
ICON_STORAGE = (
    "M3,2 h18 a1,1 0 0,1 1,1 v6 a1,1 0 0,1 -1,1 H3 a1,1 0 0,1 -1,-1 V3 "
    "a1,1 0 0,1 1,-1 Z M5,4 a1.5,1.5 0 1,0 3,0 a1.5,1.5 0 1,0 -3,0 "
    "M10,4 a1.5,1.5 0 1,0 3,0 a1.5,1.5 0 1,0 -3,0"
)
ICON_SWITCH = (
    "M2,3 h20 a1,1 0 0,1 1,1 v4 a1,1 0 0,1 -1,1 H2 a1,1 0 0,1 -1,-1 V4 "
    "a1,1 0 0,1 1,-1 Z M4,5 v2 M6,5 v2 M8,5 v2 M10,5 v2 M12,5 v2 "
    "M14,5 v2 M16,5 v2 M18,5 v2 M20,5 v2"
)


# ---------------------------------------------------------------------------
# Helper: orthogonal path with rounded corners
# ---------------------------------------------------------------------------
def _ortho_path(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    mid_y: Optional[float] = None,
    r: float = BEND_R,
) -> str:
    """Build an SVG ``d`` attribute for a vertical-horizontal-vertical path.

    The path goes from ``(x1, y1)`` straight down/up to ``mid_y``, then
    horizontally to ``x2``, then vertically to ``(x2, y2)``.  Each right-angle
    bend uses a quarter-circle arc of radius *r*.
    """
    if mid_y is None:
        mid_y = (y1 + y2) / 2

    dy1 = 1 if mid_y > y1 else -1
    dy2 = 1 if y2 > mid_y else -1
    dx = 1 if x2 > x1 else -1

    r = (
        min(r, abs(mid_y - y1) / 2, abs(y2 - mid_y) / 2, abs(x2 - x1) / 2)
        if (abs(mid_y - y1) > 0 and abs(y2 - mid_y) > 0 and abs(x2 - x1) > 0)
        else 0
    )

    if r < 1 or x1 == x2:
        return f"M{x1},{y1} L{x1},{mid_y} L{x2},{mid_y} L{x2},{y2}"

    # First bend (vertical to horizontal)
    b1x = x1
    b1y = mid_y - dy1 * r
    # Arc sweep: depends on direction
    sweep1 = 1 if (dy1 > 0) == (dx > 0) else 0

    # Second bend (horizontal to vertical)
    b2x = x2 - dx * r
    sweep2 = 1 if (dx > 0) == (dy2 > 0) else 0

    return (
        f"M{x1},{y1} "
        f"L{b1x},{b1y} "
        f"A{r},{r} 0 0,{sweep1} {b1x + dx * r},{mid_y} "
        f"L{b2x},{mid_y} "
        f"A{r},{r} 0 0,{sweep2} {x2},{mid_y + dy2 * r} "
        f"L{x2},{y2}"
    )


def _rounded_polyline(
    points: List[Tuple[float, float]],
    r: float = BEND_R,
) -> str:
    """Build an SVG path through axis-aligned waypoints with rounded corners.

    Each waypoint is an ``(x, y)`` pair.  Adjacent segments must be
    axis-aligned (horizontal or vertical).  At each interior waypoint a
    quarter-circle arc of radius *r* replaces the right-angle corner.
    """
    if len(points) < 2:
        return ""
    if len(points) == 2:
        return f"M{points[0][0]},{points[0][1]} L{points[1][0]},{points[1][1]}"

    parts = [f"M{points[0][0]},{points[0][1]}"]

    for i in range(1, len(points) - 1):
        px, py = points[i - 1]
        cx, cy = points[i]
        nx, ny = points[i + 1]

        dx1 = 1 if cx > px else (-1 if cx < px else 0)
        dy1 = 1 if cy > py else (-1 if cy < py else 0)
        dx2 = 1 if nx > cx else (-1 if nx < cx else 0)
        dy2 = 1 if ny > cy else (-1 if ny < cy else 0)

        seg_in = abs(cx - px) + abs(cy - py)
        seg_out = abs(nx - cx) + abs(ny - cy)
        max_r = min(seg_in, seg_out) / 2
        ar = min(r, max_r) if max_r > 1 else 0

        if ar < 1:
            parts.append(f"L{cx},{cy}")
            continue

        pre_x = cx - (dx1 * ar if dx1 else 0)
        pre_y = cy - (dy1 * ar if dy1 else 0)
        post_x = cx + (dx2 * ar if dx2 else 0)
        post_y = cy + (dy2 * ar if dy2 else 0)

        cross = dx1 * dy2 - dy1 * dx2
        sweep = 1 if cross > 0 else 0

        parts.append(f"L{pre_x},{pre_y}")
        parts.append(f"A{ar},{ar} 0 0,{sweep} {post_x},{post_y}")

    parts.append(f"L{points[-1][0]},{points[-1][1]}")
    return " ".join(parts)


# ========================================================================
# Main generator class
# ========================================================================
class RackCentricDiagramGenerator:
    """Generate rack-centric logical network topology SVG diagrams."""

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        assets_path: str = "assets",
        library_path: Optional[str] = None,  # noqa: ARG002  kept for API compat
        user_images_dir: Optional[str] = None,  # noqa: ARG002  kept for API compat
    ):
        self.cfg = config or {}
        self.show_port_labels = bool(self.cfg.get("show_port_labels", False))
        self.device_icon_mode = self.cfg.get("device_icons", "flat")
        self.assets_path = Path(assets_path)
        self._library_path = library_path
        self._user_images_dir = user_images_dir
        self._use_gradients = _CAIROSVG_AVAILABLE

    # ------------------------------------------------------------------
    # Data enrichment
    # ------------------------------------------------------------------
    @staticmethod
    def _enrich_devices(
        nodes: List[Dict[str, Any]],
        boxes: List[Dict[str, Any]],
        prefix: str,
        box_id_field: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Merge node data (IPs, hostname) with box data (rack_name).

        Nodes (cnodes/dnodes) carry network addresses that match port_map
        entries; boxes (cboxes/dboxes) carry the engineer-assigned rack
        placement.  This method produces a unified device list suitable
        for rendering.

        Rack assignment is driven by the hardware inventory: when
        ``box_id_field`` (``"cbox_id"`` / ``"dbox_id"``) is supplied, each
        node inherits ``rack_name`` from its parent box via
        ``node[box_id_field] -> box["id"] -> box["rack_name"]``.  This is
        the authoritative reference — nodes themselves carry
        ``rack_id=None``, so the legacy sibling/``boxes[0]`` fallback
        collapsed every node into a single rack.  The fallback is retained
        only for nodes that already carry a rack or cannot be matched to a
        parent box.
        """
        box_by_id: Dict[Any, Dict[str, Any]] = {}
        box_by_rack_id: Dict[Any, List[Dict[str, Any]]] = {}
        for bx in boxes:
            bid = bx.get("id")
            if bid is not None:
                box_by_id[bid] = bx
            rid = bx.get("rack_id")
            if rid is not None:
                box_by_rack_id.setdefault(rid, []).append(bx)

        enriched: List[Dict[str, Any]] = []
        for idx, node in enumerate(nodes):
            dev: Dict[str, Any] = dict(node)
            dev.setdefault("name", node.get("hostname", node.get("name", f"{prefix}{idx + 1}")))

            # Primary: inherit rack from the parent box via cbox_id/dbox_id.
            rack_name = ""
            if box_id_field:
                parent_box = box_by_id.get(node.get(box_id_field))
                if parent_box and parent_box.get("rack_name"):
                    rack_name = parent_box["rack_name"]

            # Secondary: a rack the node already carries.
            if not rack_name:
                rack_name = node.get("rack_name") or ""

            # Last resort: sibling box in the same rack_id, else "Default".
            if not rack_name:
                sibling_boxes = box_by_rack_id.get(node.get("rack_id"))
                if sibling_boxes:
                    rack_name = sibling_boxes[0].get("rack_name", "Default")
                else:
                    rack_name = "Default"

            dev["rack_name"] = rack_name

            # Gather all known IPs for connection matching
            ips: list = []
            for field in ("mgmt_ip", "ipmi_ip", "ip"):
                v = node.get(field)
                if v:
                    ips.append(v)
            for dip in node.get("data_ips", []):
                ips.append(dip)
            dev["_all_ips"] = ips

            enriched.append(dev)

        return enriched

    @staticmethod
    def _classify_switch_role(switch: Any) -> str:
        """Return ``"spine"`` or ``"leaf"`` from a switch's name.

        Leaf/spine fabrics name switches with ``-LF-`` (leaf) and ``-SP-``
        (spine) segments, e.g. ``SW-LF-01``, ``LAX-01-SW-LF-02``,
        ``SW-SP-01``.  Role is taken from switch discovery naming rather
        than port-map membership: vnetmap only reaches some switches, so a
        membership test would misclassify real leaf switches it could not
        capture.  Anything that matches neither pattern defaults to
        ``"leaf"`` so non-leaf/spine clusters keep their historical
        single-tier behavior.
        """
        if not isinstance(switch, dict):
            return "leaf"
        name = (switch.get("hostname") or switch.get("name") or "").upper()
        if "-SP-" in name or "SW-SP" in name or "SPINE" in name:
            return "spine"
        if "-LF-" in name or "SW-LF" in name or "LEAF" in name:
            return "leaf"
        return "leaf"

    @staticmethod
    def _hostname_node_key(hostname: Optional[str]) -> str:
        """Return a rack-prefix-independent node identity key from a hostname.

        Hardware inventory hostnames carry the engineer-assigned rack
        prefix (``RackP01C01-CB6-U22-CN1``), while IB vnetmap ``port_map``
        hostnames may carry a different/placeholder prefix
        (``RackP01C02-CB6-U22-CN1``) and IB data IPs that are absent from
        the API inventory.  The stable identity is the box/node suffix
        (``CB6-U22-CN1``), so we anchor on the first box token
        (``C``/``D``/``E`` + ``B`` + digit) and return everything from
        there, lowercased.  Returns ``""`` when no hostname is given.

        Note: this suffix is NOT unique across racks (both racks reuse
        ``CB6-U22-CN1``), so callers must only treat a suffix-only match
        as authoritative when other context (same-rack switch) disambiguates.
        """
        if not hostname:
            return ""
        match = re.search(r"[cde]b\d.*$", hostname, re.IGNORECASE)
        return (match.group(0) if match else hostname).lower()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def generate(
        self,
        port_mapping_data: Dict[str, Any],
        hardware_data: Dict[str, Any],
        output_dir: str,
        manual_placements: Optional[Dict[str, Any]] = None,
        manual_switch_placements: Optional[Any] = None,
    ) -> List[str]:
        """Generate one or more PNG diagram files.

        Returns:
            List of output PNG file paths (one per page).
        """
        if not _SVGWRITE_AVAILABLE:
            logger.error(
                "svgwrite package is not installed — cannot generate detailed diagram. "
                "Install with: pip install svgwrite"
            )
            return []
        svgwrite = _svgwrite

        port_map = port_mapping_data.get("port_map", [])
        ipl_conns = port_mapping_data.get("ipl_connections", [])
        switches = hardware_data.get("switches", [])

        # IB clusters store the switch identity as a GUID in the port_map's
        # ``switch_ip`` column, but the renderer keys switches by mgmt_ip.
        # Normalize GUID -> mgmt_ip up front (on copies) so leaf/spine
        # classification, switch_centers lookup, edge classification, and
        # NET-3 subnet coloring all resolve. Identity for Ethernet clusters.
        switch_ip_alias = self._build_switch_ip_alias(port_map, switches)
        if switch_ip_alias:
            port_map = [
                {**conn, "switch_ip": switch_ip_alias.get(conn.get("switch_ip"), conn.get("switch_ip"))}
                for conn in port_map
                if isinstance(conn, dict)
            ]
            normalized_ipl: List[Dict[str, Any]] = []
            for ipl in ipl_conns or []:
                if not isinstance(ipl, dict):
                    continue
                new_ipl = dict(ipl)
                for field in ("switch1_ip", "switch2_ip"):
                    val = new_ipl.get(field)
                    if val in switch_ip_alias:
                        new_ipl[field] = switch_ip_alias[val]
                normalized_ipl.append(new_ipl)
            ipl_conns = normalized_ipl
            logger.info(
                "Normalized %d port_map switch GUID(s) to mgmt_ip for rendering",
                len(switch_ip_alias),
            )

        # Prefer cnodes/dnodes (which carry IPs matching port_map) over cboxes/dboxes
        cnodes = hardware_data.get("cnodes", [])
        dnodes = hardware_data.get("dnodes", [])
        if isinstance(cnodes, dict):
            cnodes = list(cnodes.values())
        if isinstance(dnodes, dict):
            dnodes = list(dnodes.values())

        cboxes = hardware_data.get("cboxes", [])
        dboxes = hardware_data.get("dboxes", [])
        eboxes = hardware_data.get("eboxes", [])
        if isinstance(cboxes, dict):
            cboxes = list(cboxes.values())
        if isinstance(dboxes, dict):
            dboxes = list(dboxes.values())
        if isinstance(eboxes, dict):
            eboxes = list(eboxes.values())

        # Use cnodes as top devices if available (they have IPs); fall back to cboxes
        top_devices = self._enrich_devices(cnodes, cboxes, "CB", "cbox_id") if cnodes else cboxes
        # Use dnodes or eboxes as bottom devices
        if eboxes:
            bottom_devices = eboxes
            bottom_label = "EB"
        elif dnodes:
            bottom_devices = self._enrich_devices(dnodes, dboxes, "DB", "dbox_id")
            bottom_label = "DN"
        else:
            bottom_devices = dboxes
            bottom_label = "DB"

        # ----- classify switches by role (naming), not port_map membership -----
        # Leaf/spine fabrics: SW-LF-* are leaves (placed in their assigned
        # racks), SW-SP-* are spines (rendered above their rack). Using
        # port_map membership here would dump leaf switches that vnetmap
        # could not reach into the spine tier.
        port_map_switch_ips = {c.get("switch_ip") for c in port_map if c.get("switch_ip")}
        spine_switches = [sw for sw in switches if self._classify_switch_role(sw) == "spine"]
        leaf_switches = [sw for sw in switches if self._classify_switch_role(sw) != "spine"]

        if not leaf_switches:
            leaf_switches = switches
            spine_switches = []

        logger.info(
            "Switch classification: %d leaf (%s), %d spine (%s)",
            len(leaf_switches),
            ", ".join(sw.get("hostname", "?") for sw in leaf_switches),
            len(spine_switches),
            ", ".join(sw.get("hostname", "?") for sw in spine_switches),
        )
        logger.info(
            "Devices: %d top (CNodes/CBoxes), %d bottom (DNodes/DBoxes)",
            len(top_devices),
            len(bottom_devices),
        )
        logger.info(
            "Port map: %d connections across %d switch IPs",
            len(port_map),
            len(port_map_switch_ips),
        )

        # ----- rack grouping -----
        racks = self._build_rack_groups(
            top_devices,
            bottom_devices,
            leaf_switches,
            port_map,
            manual_placements,
            bottom_label,
            manual_switch_placements=manual_switch_placements,
        )
        if not racks:
            logger.warning("No rack groups could be formed — falling back to single rack")
            racks = [self._default_rack(top_devices, bottom_devices, leaf_switches, bottom_label)]

        # Resolve each spine's rack from switch discovery so the renderer can
        # center it above the rack where it is installed (SW-SP-01 -> C01,
        # SW-SP-02 -> C02). Spines do not flow through _assign_switches_to_racks
        # (that handles rack-local leaves), so annotate them here.
        manual_switch_to_rack = self._extract_manual_switch_to_rack(manual_switch_placements)
        for sp in spine_switches:
            if isinstance(sp, dict):
                sp_name = sp.get("hostname") or sp.get("name") or ""
                sp["_assigned_rack"] = manual_switch_to_rack.get(sp_name, "")

        # ----- paginate -----
        pages: List[List[Dict[str, Any]]] = []
        for i in range(0, len(racks), MAX_RACKS_PER_PAGE):
            pages.append(racks[i : i + MAX_RACKS_PER_PAGE])

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        png_paths: List[str] = []

        total_pages = len(pages)
        for page_idx, page_racks in enumerate(pages):
            svg_content = self._render_page(
                svgwrite,
                page_racks,
                spine_switches,
                ipl_conns,
                port_map,
                switches,
                page_num=page_idx + 1,
                total_pages=total_pages,
            )
            png_path = out_dir / f"network_topology_p{page_idx + 1}.png"
            self._svg_to_png(svg_content, str(png_path))
            if png_path.exists():
                png_paths.append(str(png_path))
                logger.info("Generated diagram page %d: %s", page_idx + 1, png_path.name)

        return png_paths

    # ------------------------------------------------------------------
    # Rack grouping
    # ------------------------------------------------------------------
    def _build_rack_groups(
        self,
        cboxes: List[Dict[str, Any]],
        bottom_devices: List[Dict[str, Any]],
        switches: List[Dict[str, Any]],
        port_map: List[Dict[str, Any]],
        manual_placements: Optional[Dict[str, Any]],
        bottom_label: str,
        manual_switch_placements: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Group devices into racks using API rack_name, falling back to profile.

        NET-2A: ``manual_switch_placements`` (operator-specified switch->rack
        assignments from the Discovery UI) flows through to
        ``_assign_switches_to_racks`` and overrides topology voting.
        """
        rack_map: Dict[str, Dict[str, List[Any]]] = defaultdict(lambda: {"cboxes": [], "bottom": [], "switches": []})

        # --- API rack_name ---
        for cb in cboxes:
            rn = cb.get("rack_name") or "Default"
            rack_map[rn]["cboxes"].append(cb)
        for bd in bottom_devices:
            rn = bd.get("rack_name") or "Default"
            rack_map[rn]["bottom"].append(bd)

        # If everything landed in "Default" and we have manual_placements, use those
        all_default = list(rack_map.keys()) == ["Default"]
        if all_default and manual_placements:
            rack_map = self._apply_manual_placements(cboxes, bottom_devices, manual_placements)

        # NET-2A: ensure racks named in manual_switch_placements exist on the
        # rack map even when no devices were grouped into them yet (otherwise
        # topology voting would discard the manual assignment).
        manual_switch_to_rack = self._extract_manual_switch_to_rack(manual_switch_placements)
        for rn in manual_switch_to_rack.values():
            if rn not in rack_map:
                rack_map[rn] = {"cboxes": [], "bottom": [], "switches": []}

        # --- Assign switches to racks (manual placements first, then topology) ---
        switch_rack = self._assign_switches_to_racks(
            switches,
            port_map,
            rack_map,
            manual_switch_to_rack=manual_switch_to_rack,
        )
        for sw in switches:
            rn = switch_rack.get(id(sw), "Default")
            rack_map[rn]["switches"].append(sw)

        # --- Order switches within each rack so Network A lands on the left
        # (SWA position) and Network B on the right (SWB position).  Prevents
        # the visual "cross" that occurs when the diagram's left/right position
        # disagrees with the Port Mapping tables' SWA/SWB assignment.
        for rn in rack_map:
            rack_map[rn]["switches"] = self._sort_switches_by_network(rack_map[rn]["switches"], port_map)

        # Build ordered list
        results: List[Dict[str, Any]] = []
        for rn in sorted(rack_map.keys()):
            data = rack_map[rn]
            results.append(
                {
                    "rack_name": rn,
                    "cboxes": data["cboxes"],
                    "bottom_devices": data["bottom"],
                    "switches": data["switches"],
                    "bottom_label": bottom_label,
                }
            )

        return results

    @staticmethod
    def _sort_switches_by_network(
        switches: List[Dict[str, Any]],
        port_map: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Order rack-local switches so Network A lands at position 0 (SWA/left).

        Uses a two-key sort:

        1. **Primary** — the network this switch serves more connections to in
           ``port_map``.  ``A`` → 0, ``B`` → 1, unknown/mixed → 2.  This keeps
           the diagram aligned with VAST's left=A / right=B visual convention
           regardless of how the API returned the switch list.
        2. **Secondary** — management IP ascending.  Matches the SWA/SWB
           assignment used by ``EnhancedPortMapper._build_switch_map`` so the
           Port Mapping tables and the Logical Network Diagram agree on which
           physical switch is "SWA" for every cluster.
        """
        if not switches:
            return switches

        # Tally per-switch network counts from port_map.
        counts: Dict[str, Dict[str, int]] = defaultdict(lambda: {"A": 0, "B": 0})
        for conn in port_map or []:
            sw_ip = conn.get("switch_ip", "")
            network = (conn.get("network") or "").upper()
            if not sw_ip or network not in ("A", "B"):
                continue
            counts[sw_ip][network] += 1

        def _primary_key(sw: Any) -> int:
            if not isinstance(sw, dict):
                return 2
            tally = counts.get(sw.get("mgmt_ip", ""), {"A": 0, "B": 0})
            if tally["A"] > tally["B"]:
                return 0
            if tally["B"] > tally["A"]:
                return 1
            return 2

        def _secondary_key(sw: Any) -> str:
            if not isinstance(sw, dict):
                return ""
            return sw.get("mgmt_ip", "") or ""

        return sorted(switches, key=lambda s: (_primary_key(s), _secondary_key(s)))

    def _default_rack(self, cboxes: list, bottom_devices: list, switches: list, bottom_label: str) -> Dict[str, Any]:
        return {
            "rack_name": "Rack 1",
            "cboxes": cboxes,
            "bottom_devices": bottom_devices,
            "switches": switches,
            "bottom_label": bottom_label,
        }

    def _apply_manual_placements(
        self,
        cboxes: list,
        bottom_devices: list,
        placements: Dict[str, Any],
    ) -> Dict[str, Dict[str, list]]:
        rack_map: Dict[str, Dict[str, list]] = defaultdict(lambda: {"cboxes": [], "bottom": [], "switches": []})
        placed_cb = set()
        placed_bd = set()

        for entry in (placements if isinstance(placements, list) else placements.values()):
            rn = entry.get("rack_name", "Default")
            device_name = entry.get("device_name", "")
            for cb in cboxes:
                if cb.get("name") == device_name and id(cb) not in placed_cb:
                    rack_map[rn]["cboxes"].append(cb)
                    placed_cb.add(id(cb))
            for bd in bottom_devices:
                if bd.get("name") == device_name and id(bd) not in placed_bd:
                    rack_map[rn]["bottom"].append(bd)
                    placed_bd.add(id(bd))

        # Assign unplaced devices to Default
        for cb in cboxes:
            if id(cb) not in placed_cb:
                rack_map["Default"]["cboxes"].append(cb)
        for bd in bottom_devices:
            if id(bd) not in placed_bd:
                rack_map["Default"]["bottom"].append(bd)

        return rack_map

    @staticmethod
    def _plan_device_edge(
        *,
        is_cross_rack: bool,
        device_rack_column: str,
        dev_x: float,
        dev_w: float,
    ) -> Dict[str, Any]:
        """Compute exit_x, dasharray, opacity for one device->switch edge (NET-2B).

        Routing rules (v1.5.8 + follow-up):

        - Same-rack edges exit the RIGHT edge of the device for BOTH rack
          columns (consistent right-side routing). The left rack's fan
          swoops into the widened inter-rack gutter and curves back up to
          its own switches, matching the right rack's look. Solid line,
          opacity 0.65 (lowered from the v1.5.8 baseline 0.85 so dense
          fans under a switch read as translucent strands). RACK_GAP is
          sized (> SWOOP_HORIZONTAL_OFFSET) so this fan never overlaps the
          right rack.
        - Cross-rack edges exit the INNER side of the device (toward
          the inter-rack gutter): right edge for left-rack devices,
          left edge for right-rack devices. Dashed line
          ``stroke-dasharray='6,4'`` (an earlier dotted ``1,3``
          variant was too subtle on dense diagrams; dashes give
          clearer visibility across the gutter), opacity 0.40
          (lowered from 0.55 so the cross-rack fan does not compete
          with same-rack edges where it overlaps).

        ``device_rack_column`` is ``"left"`` for the leftmost rack on the
        page and ``"right"`` for any other rack (the diagram constrains
        ``MAX_RACKS_PER_PAGE = 2``, so the binary distinction is exact).

        Args:
            is_cross_rack: True if the switch is in a different rack than the device.
            device_rack_column: ``"left"`` or ``"right"``.
            dev_x: Device box left coordinate.
            dev_w: Device box width.

        Returns:
            Dict with keys ``exit_x`` (float), ``dasharray`` (str | None), ``opacity`` (float).
        """
        is_left = device_rack_column == "left"
        if is_cross_rack:
            exit_x = dev_x + dev_w if is_left else dev_x
            return {"exit_x": exit_x, "dasharray": "6,4", "opacity": 0.40}
        # Consistent right-side routing: same-rack edges always exit the
        # device's RIGHT edge regardless of rack column.
        exit_x = dev_x + dev_w
        return {"exit_x": exit_x, "dasharray": None, "opacity": 0.65}

    @staticmethod
    def _classify_edge(
        *,
        sw_ip: str,
        current_rack_switch_ips: set,
        all_switch_ips: set,
    ) -> str:
        """Classify a port_map edge by switch position relative to the device's rack.

        Returns one of:

        - ``"same_rack"`` — switch lives in the same rack as the device.
        - ``"cross_rack"`` — switch lives in a different rack on the same page.
        - ``"orphan"``     — switch isn't present in any rack on this page.

        NET-2B v1.5.7 bug: cross-rack edges were dropped because the
        renderer treated any switch missing from the per-rack
        ``switch_centers`` accumulator as orphan. The classifier must
        treat cross-rack and orphan as distinct so the renderer only
        skips genuine orphans.
        """
        if sw_ip in current_rack_switch_ips:
            return "same_rack"
        if sw_ip in all_switch_ips:
            return "cross_rack"
        return "orphan"

    @staticmethod
    def _ipv4_subnet_24(ip: str) -> Optional[str]:
        """Return the /24 prefix as ``"a.b.c"`` for a valid IPv4, else ``None``.

        NET-3: helper used to bucket node IPs into /24 subnets so the
        renderer can color edges by the switch's serviced subnet.
        """
        if not ip or not isinstance(ip, str):
            return None
        parts = ip.strip().split(".")
        if len(parts) != 4:
            return None
        try:
            octets = [int(p) for p in parts]
        except ValueError:
            return None
        if not all(0 <= o <= 255 for o in octets):
            return None
        return f"{octets[0]}.{octets[1]}.{octets[2]}"

    @staticmethod
    def _compute_switch_subnet(
        sw_ip: str,
        port_map: List[Dict[str, Any]],
    ) -> Optional[str]:
        """Return the most common /24 prefix among nodes connected to ``sw_ip``.

        NET-3: a switch's "subnet" is defined as the most frequent /24 prefix
        of the ``node_ip`` values in ``port_map`` rows where
        ``switch_ip == sw_ip``. Invalid node_ips are ignored. Returns
        ``None`` if the switch has no valid evidence in the port map.

        The mis-cabling case (NET-4): when a switch services nodes from
        multiple /24 subnets, the most-common subnet is its canonical
        subnet; the off-subnet rows are flagged separately.
        """
        if not sw_ip or not port_map:
            return None
        counts: Dict[str, int] = defaultdict(int)
        for conn in port_map:
            if conn.get("switch_ip") != sw_ip:
                continue
            subnet = RackCentricDiagramGenerator._ipv4_subnet_24(conn.get("node_ip", ""))
            if subnet:
                counts[subnet] += 1
        if not counts:
            return None
        # Determinism: tie-break by lexicographic subnet order to keep output stable.
        return max(counts.items(), key=lambda kv: (kv[1], -hash(kv[0]) if False else kv[0]))[0]

    @staticmethod
    def _assign_subnet_colors(
        switches: List[Dict[str, Any]],
        port_map: List[Dict[str, Any]],
    ) -> Dict[str, str]:
        """Map each switch's mgmt_ip to its NET-3 subnet color.

        Switches sharing a /24 subnet share the same color. Subnets are
        colored in order of the lowest mgmt_ip serving them: first subnet
        gets ``SUBNET_COLOR_PALETTE[0]`` (green), second gets ``[1]`` (blue),
        and so on, cycling through the palette for additional subnets.

        Switches without subnet evidence (no matching port_map rows) are
        omitted from the result; the renderer falls back to a default
        color in that case.
        """
        if not switches:
            return {}

        # 1) compute subnet per switch (mgmt_ip -> subnet)
        sw_subnet: Dict[str, str] = {}
        for sw in switches:
            mgmt_ip = sw.get("mgmt_ip", "") if isinstance(sw, dict) else ""
            if not mgmt_ip:
                continue
            subnet = RackCentricDiagramGenerator._compute_switch_subnet(mgmt_ip, port_map)
            if subnet:
                sw_subnet[mgmt_ip] = subnet

        if not sw_subnet:
            return {}

        # 2) order subnets by the lowest mgmt_ip serving each one.
        # mgmt_ip strings sort lexicographically — fine for the IPv4 dotted form
        # produced by VAST API since IPv4 strings of equal-length octets sort
        # in the same order numerically.
        subnet_to_min_ip: Dict[str, str] = {}
        for ip, subnet in sw_subnet.items():
            if subnet not in subnet_to_min_ip or ip < subnet_to_min_ip[subnet]:
                subnet_to_min_ip[subnet] = ip
        ordered_subnets = sorted(subnet_to_min_ip.keys(), key=lambda s: subnet_to_min_ip[s])

        # 3) assign palette colors (cycling)
        subnet_to_color: Dict[str, str] = {}
        palette_n = len(SUBNET_COLOR_PALETTE)
        for idx, subnet in enumerate(ordered_subnets):
            subnet_to_color[subnet] = SUBNET_COLOR_PALETTE[idx % palette_n]

        # 4) project back to switch_ip -> color
        return {ip: subnet_to_color[subnet] for ip, subnet in sw_subnet.items()}

    @staticmethod
    def _build_switch_ip_alias(
        port_map: Optional[List[Dict[str, Any]]],
        switches: Optional[List[Dict[str, Any]]],
    ) -> Dict[str, str]:
        """Map each port_map ``switch_ip`` to the API switch ``mgmt_ip``.

        InfiniBand vnetmap output stores the switch identity in the
        port_map ``switch_ip`` column as a 16-byte GUID (e.g.
        ``0xa088c203007860bc``), while every other part of the renderer —
        ``switch_centers``, ``_classify_edge``, leaf/spine classification,
        and NET-3 subnet coloring — keys switches by their API-supplied
        ``mgmt_ip``.  Without translation, every IB device->switch edge is
        classified ``orphan`` (the GUID is never in ``switch_centers``)
        and silently dropped.

        Each port_map row also carries ``switch_hostname``, so we resolve
        GUID -> hostname -> mgmt_ip against the API switch list.  Rows
        whose ``switch_ip`` is already an API mgmt_ip resolve to
        themselves (identity), so Ethernet clusters are unaffected.
        Unresolvable identifiers are omitted (caller keeps the original
        value; the edge degrades to ``orphan`` rather than crashing).

        Args:
            port_map: ``port_mapping_data['port_map']`` rows. ``None``
                tolerated (returns ``{}``).
            switches: API switch list with ``hostname``/``mgmt_ip``.

        Returns:
            Dict mapping ``switch_ip`` (as seen in the port map) to a
            resolved ``mgmt_ip``.
        """
        if not port_map:
            return {}

        host_to_mgmt: Dict[str, str] = {}
        mgmt_ips: set = set()
        for sw in switches or []:
            if not isinstance(sw, dict):
                continue
            mgmt = sw.get("mgmt_ip")
            if not mgmt:
                continue
            mgmt_ips.add(mgmt)
            host = sw.get("hostname")
            if host:
                host_to_mgmt[host] = mgmt

        alias: Dict[str, str] = {}
        for conn in port_map:
            if not isinstance(conn, dict):
                continue
            sw_ip = conn.get("switch_ip")
            if not sw_ip or sw_ip in alias:
                continue
            # Ethernet: switch_ip already equals an API mgmt_ip -> identity
            if sw_ip in mgmt_ips:
                alias[sw_ip] = sw_ip
                continue
            # InfiniBand: resolve GUID via switch_hostname -> mgmt_ip
            host = conn.get("switch_hostname")
            mgmt = host_to_mgmt.get(host) if host else None
            if mgmt:
                alias[sw_ip] = mgmt

        return alias

    @staticmethod
    def _collect_inter_rack_ipl_pairs(
        ipl_conns: Optional[List[Dict[str, Any]]],
        switch_centers: Dict[str, Tuple[float, float]],
        switch_rack_idx: Dict[str, int],
    ) -> List[Tuple[str, str]]:
        """Return de-duplicated cross-rack IPL/MLAG pairs to draw.

        The v1.5.8 baseline drew the IPL line only inside the per-rack
        loop, which silently dropped the line whenever the paired
        switches lived in different racks (e.g. clusters with one
        switch per rack and the IPL crossing the inter-rack gutter).
        This helper picks out exactly those cross-rack pairs so
        ``_render_page`` can render them in a post-loop pass.

        Filtering rules:

        - Both endpoints must be present in ``switch_centers`` —
          otherwise the line cannot be drawn (defensive).
        - Switches must live in DIFFERENT racks per
          ``switch_rack_idx`` — same-rack pairs are still drawn by the
          per-rack loop, so emitting them again would double-draw.
        - Each undirected pair is yielded only once even if
          ``ipl_conns`` lists ``(A, B)`` and ``(B, A)``.

        Args:
            ipl_conns: Raw ``port_mapping_data['ipl_connections']``
                list. ``None`` is tolerated (returns ``[]``).
            switch_centers: Map of ``switch_ip -> (cx, sw_bot_y)``.
            switch_rack_idx: Map of ``switch_ip -> rack_index``.

        Returns:
            List of ``(switch1_ip, switch2_ip)`` tuples, each pair
            unique. Order within a pair is not normalized; callers
            should treat pairs as unordered.
        """
        if not ipl_conns:
            return []
        seen: set = set()
        out: List[Tuple[str, str]] = []
        for ipl in ipl_conns:
            if not isinstance(ipl, dict):
                continue
            ip1 = ipl.get("switch1_ip", "")
            ip2 = ipl.get("switch2_ip", "")
            if not ip1 or not ip2:
                continue
            if ip1 not in switch_centers or ip2 not in switch_centers:
                continue
            r1 = switch_rack_idx.get(ip1)
            r2 = switch_rack_idx.get(ip2)
            if r1 is None or r2 is None or r1 == r2:
                continue
            key = tuple(sorted([ip1, ip2]))
            if key in seen:
                continue
            seen.add(key)
            out.append((ip1, ip2))
        return out

    @staticmethod
    def _bezier_swoop_path(
        exit_x: float,
        exit_y: float,
        landing_x: float,
        sw_bot_y: float,
        *,
        exit_extends_right: bool,
        horizontal_offset: float = SWOOP_HORIZONTAL_OFFSET,
        drop_offset: float = 70.0,
    ) -> str:
        """Build the SVG ``d`` attribute for a v1.5.8 mockup-style edge.

        Each edge is a single cubic bezier that:

        1. Exits the device horizontally (``cp1`` extends OUTWARD from the
           device's exit side by ``horizontal_offset``, producing a short
           horizontal "tail" that visually echoes a port stub).
        2. Sweeps smoothly toward the switch.
        3. Approaches the switch vertically (``cp2`` is positioned BELOW
           the switch's bottom edge by ``drop_offset`` so the curve drops
           in cleanly at ``landing_x``).
        4. Ends exactly on the switch's bottom edge at
           ``(landing_x, sw_bot_y)``.

        See ``docs/issues/NET-2/mockup-target.svg`` for the design source.

        Args:
            exit_x: x of the device's exit point (left edge or right edge).
            exit_y: y of the device's exit point (mid-height).
            landing_x: x where the line lands on the switch's bottom edge.
            sw_bot_y: y of the switch's bottom edge.
            exit_extends_right: True if the exit is on the device's right
                side (cp1 extends rightward); False for left exits (cp1
                extends leftward).
            horizontal_offset: pixels cp1 extends outward from the device.
            drop_offset: pixels cp2 sits below the switch's bottom edge.

        Returns:
            SVG path ``d`` string of the form
            ``"M sx,sy C cp1x,cp1y cp2x,cp2y ex,ey"``.
        """
        cp1_x = exit_x + (horizontal_offset if exit_extends_right else -horizontal_offset)
        cp2_y = sw_bot_y + drop_offset
        return f"M {exit_x},{exit_y} " f"C {cp1_x},{exit_y} " f"{landing_x},{cp2_y} " f"{landing_x},{sw_bot_y}"

    @staticmethod
    def _switch_subnet_set(sw_ip: str, port_map: List[Dict[str, Any]]) -> set:
        """Return the set of distinct /24 prefixes among nodes connected to ``sw_ip``.

        NET-4: a switch with ``len(subnet_set) > 1`` is mis-cabled — it
        services nodes from multiple subnets, which usually indicates a
        physical patching error.
        """
        if not sw_ip or not port_map:
            return set()
        result: set = set()
        for conn in port_map:
            if conn.get("switch_ip") != sw_ip:
                continue
            subnet = RackCentricDiagramGenerator._ipv4_subnet_24(conn.get("node_ip", ""))
            if subnet:
                result.add(subnet)
        return result

    @staticmethod
    def _detect_miscabled_switches(
        switches: List[Dict[str, Any]],
        port_map: List[Dict[str, Any]],
    ) -> Dict[str, set]:
        """Return ``{mgmt_ip -> off_subnet_set}`` for switches with > 1 subnet.

        NET-4: ``off_subnet_set`` excludes the switch's canonical
        (most-common) subnet. Each entry in the off-subnet set indicates a
        group of mis-cabled connections to investigate.
        """
        result: Dict[str, set] = {}
        for sw in switches:
            mgmt_ip = sw.get("mgmt_ip", "") if isinstance(sw, dict) else ""
            if not mgmt_ip:
                continue
            subnets = RackCentricDiagramGenerator._switch_subnet_set(mgmt_ip, port_map)
            if len(subnets) <= 1:
                continue
            canonical = RackCentricDiagramGenerator._compute_switch_subnet(mgmt_ip, port_map)
            off_subnets = subnets - ({canonical} if canonical else set())
            if off_subnets:
                result[mgmt_ip] = off_subnets
        return result

    @staticmethod
    def _detect_miscabled_node_ips(
        sw_ip: str,
        port_map: List[Dict[str, Any]],
    ) -> set:
        """Return the node IPs whose subnet differs from the switch's canonical subnet.

        NET-4: each returned node IP is an offending mis-cabled connection.
        The renderer flags the corresponding device box with a red dashed
        outline and a warning glyph.
        """
        canonical = RackCentricDiagramGenerator._compute_switch_subnet(sw_ip, port_map)
        if canonical is None:
            return set()
        offenders: set = set()
        for conn in port_map:
            if conn.get("switch_ip") != sw_ip:
                continue
            node_ip = conn.get("node_ip", "")
            subnet = RackCentricDiagramGenerator._ipv4_subnet_24(node_ip)
            if subnet and subnet != canonical:
                offenders.add(node_ip)
        return offenders

    @staticmethod
    def _device_has_miscabled_ip(
        device: Any,
        miscabled_node_ips: set,
    ) -> bool:
        """Return True if any of the device's IPs is in ``miscabled_node_ips`` (NET-4)."""
        if not isinstance(device, dict) or not miscabled_node_ips:
            return False
        for field in ("mgmt_ip", "ipmi_ip", "ip"):
            ip = device.get(field)
            if ip and ip in miscabled_node_ips:
                return True
        for dip in device.get("data_ips", []):
            if dip in miscabled_node_ips:
                return True
        for aip in device.get("_all_ips", []):
            if aip in miscabled_node_ips:
                return True
        return False

    @staticmethod
    def _build_validation_banner(miscabling: Dict[str, set]) -> Tuple[str, str]:
        """Return ``(banner_text, banner_color)`` for the cabling validation banner.

        NET-4:
        - When ``miscabling`` is empty, return the green PASS banner.
        - Otherwise return the red FAIL banner with a count of mis-cabled
          connections (sum of off_subnet set sizes across all switches).
        """
        if not miscabling:
            return ("Cabling validation: PASS", SUBNET_COLOR_PALETTE[0])  # green
        count = sum(len(off_subnets) for off_subnets in miscabling.values())
        word = "connection" if count == 1 else "connections"
        return (f"Cabling validation: {count} mis-cabled {word} detected", "#EA4335")  # red

    @staticmethod
    def _extract_manual_switch_to_rack(
        manual_switch_placements: Optional[Any],
    ) -> Dict[str, str]:
        """Build a ``{switch_name -> rack_name}`` map from Discovery UI placements.

        The Discovery UI (frontend/templates/reporter.html) emits
        ``manual_switch_placements`` as a list of entries with at least
        ``switch_name`` and ``rack_name``. This helper normalizes that payload
        into a name-keyed dict the diagram can consult during rack assignment.

        Entries missing ``switch_name`` or ``rack_name`` (or with empty values)
        are silently skipped — the caller falls back to topology voting for
        any switch not covered by the map.
        """
        if not manual_switch_placements:
            return {}
        entries = (
            manual_switch_placements
            if isinstance(manual_switch_placements, list)
            else list(manual_switch_placements.values()) if isinstance(manual_switch_placements, dict) else []
        )
        result: Dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            name = entry.get("switch_name")
            rack = entry.get("rack_name")
            if name and rack:
                result[name] = rack
        return result

    def _assign_switches_to_racks(
        self,
        switches: List[Dict[str, Any]],
        port_map: List[Dict[str, Any]],
        rack_map: Dict[str, Dict[str, list]],
        manual_switch_to_rack: Optional[Dict[str, str]] = None,
    ) -> Dict[int, str]:
        """Determine which rack each switch belongs to.

        NET-2A: ``manual_switch_to_rack`` (operator-specified switch->rack
        assignments from the Discovery UI) wins over topology voting. Any
        switch matched by ``hostname`` or ``name`` against the manual map is
        placed in its assigned rack regardless of port_map evidence; switches
        not covered by the map fall back to the original topology voting
        behavior.
        """
        manual_map = manual_switch_to_rack or {}

        ip_to_rack: Dict[str, str] = {}
        hostname_to_rack: Dict[str, str] = {}
        for rn, data in rack_map.items():
            for dev in data["cboxes"] + data["bottom"]:
                for ip_field in ("mgmt_ip", "ipmi_ip", "ip"):
                    ip = dev.get(ip_field)
                    if ip:
                        ip_to_rack[ip] = rn
                for dip in dev.get("data_ips", []):
                    ip_to_rack[dip] = rn
                for aip in dev.get("_all_ips", []):
                    ip_to_rack[aip] = rn
                for hf in ("hostname", "name"):
                    hn = dev.get(hf)
                    if hn:
                        hostname_to_rack[hn] = rn

        switch_rack_votes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for conn in port_map:
            sw_ip = conn.get("switch_ip", "")
            node_ip = conn.get("node_ip", "")
            conn_host = conn.get("node_hostname", "")
            rn = ip_to_rack.get(node_ip) or hostname_to_rack.get(conn_host)
            if rn and sw_ip:
                switch_rack_votes[sw_ip][rn] += 1

        result: Dict[int, str] = {}
        for sw in switches:
            sw_name = sw.get("hostname") or sw.get("name") or ""
            manual_rack = manual_map.get(sw_name)
            if manual_rack and manual_rack in rack_map:
                best_rack = manual_rack
            else:
                mgmt_ip = sw.get("mgmt_ip", "")
                votes = switch_rack_votes.get(mgmt_ip, {})
                if votes:
                    best_rack = max(votes, key=votes.get)  # type: ignore[arg-type]
                else:
                    best_rack = list(rack_map.keys())[0] if rack_map else "Default"
            result[id(sw)] = best_rack
            sw["_assigned_rack"] = best_rack

        return result

    def _detect_spines(self, switches: List[Dict[str, Any]], racks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify spine switches (those not assigned as rack-local leaves)."""
        leaf_ids = set()
        for rack in racks:
            for sw in rack.get("switches", []):
                if isinstance(sw, dict):
                    leaf_ids.add(id(sw))
        return [sw for sw in switches if id(sw) not in leaf_ids]

    # ------------------------------------------------------------------
    # SVG rendering
    # ------------------------------------------------------------------
    def _render_page(
        self,
        svgwrite: Any,
        racks: List[Dict[str, Any]],
        spines: List[Dict[str, Any]],
        ipl_conns: List[Dict[str, Any]],
        port_map: List[Dict[str, Any]],
        _all_switches: List[Dict[str, Any]],
        page_num: int = 1,
        total_pages: int = 1,
    ) -> str:
        """Render a single page SVG and return the XML string."""
        num_racks = len(racks)

        # Calculate rack column dimensions
        max_devs = max((len(r["cboxes"]) + len(r["bottom_devices"]) for r in racks), default=4)
        has_bottom_devs = any(r["bottom_devices"] for r in racks)
        separator_space = DEVICE_GAP * 4 if has_bottom_devs else 0
        rack_inner_h = SWITCH_H + SWITCH_GAP + max_devs * (DEVICE_H + DEVICE_GAP) + DEVICE_GAP * 2 + separator_space
        rack_w = DEVICE_W + 2 * RACK_PAD_X
        rack_h = RACK_PAD_TOP + rack_inner_h + RACK_PAD_BOTTOM

        has_spine = len(spines) > 0
        spine_section = SPINE_ROW_H + SPINE_GAP if has_spine else 0

        # NET-3: assign a subnet color to each switch (computed up front so it
        # can size the legend). Edges use this color to group by /24 subnet.
        subnet_color_map: Dict[str, str] = self._assign_subnet_colors(_all_switches, port_map)

        # Compute legend items up front so the canvas is wide enough to hold
        # the whole legend row — otherwise a narrow 2-rack page clips the
        # leftmost pill (start_x went negative under the old fixed spacing).
        legend_items = self._compute_legend_items(
            switches=_all_switches,
            subnet_color_map=subnet_color_map,
            port_map=port_map,
            has_spine=has_spine,
        )
        legend_w = self._legend_content_width(legend_items)

        # Right-side routing makes the rightmost rack's connection fan bulge
        # SWOOP_HORIZONTAL_OFFSET past its right edge. Pad both sides (racks
        # are centered) by at least that much so no far-right line is clipped.
        edge_pad = max(float(MARGIN), SWOOP_HORIZONTAL_OFFSET + 10)
        total_w = max(
            2 * edge_pad + num_racks * rack_w + (num_racks - 1) * RACK_GAP,
            2 * MARGIN + legend_w,
            PORTRAIT_W,
        )
        # NET-4: reserve a row above the diagram for the cabling validation
        # banner. Always rendered (PASS in green or FAIL in red); 24 px tall.
        BANNER_H = 24
        total_h = MARGIN + TITLE_H + BANNER_H + spine_section + rack_h + LEGEND_H + MARGIN

        dwg = svgwrite.Drawing(size=(f"{total_w}px", f"{total_h}px"))
        dwg.attribs["xmlns"] = "http://www.w3.org/2000/svg"

        # Background
        dwg.add(dwg.rect(insert=(0, 0), size=(total_w, total_h), fill="white"))

        # Defs: gradients
        self._add_gradients(dwg)

        # Title
        title_y = MARGIN + 20
        dwg.add(
            dwg.text(
                "Logical Network Topology",
                insert=(total_w / 2, title_y),
                text_anchor="middle",
                font_size="18px",
                font_family="Helvetica, Arial, sans-serif",
                font_weight="bold",
                fill=COLOR_TEXT,
            )
        )
        dwg.add(
            dwg.line(
                start=(MARGIN, title_y + 8),
                end=(total_w - MARGIN, title_y + 8),
                stroke="#e0e0e0",
                stroke_width=1,
            )
        )

        # NET-4: detect mis-cabled switches and render the cabling validation
        # banner. Always present so the operator can confirm a clean cluster
        # at a glance; switches to red FAIL when off-subnet edges are seen.
        miscabling = self._detect_miscabled_switches(_all_switches, port_map)
        miscabled_node_ips: set = set()
        for sw_ip in miscabling:
            miscabled_node_ips.update(self._detect_miscabled_node_ips(sw_ip, port_map))
        banner_text, banner_color = self._build_validation_banner(miscabling)
        banner_y = MARGIN + TITLE_H
        banner_tint = self._color_tint(banner_color)
        bw_banner = min(360.0, total_w - 2 * MARGIN)
        bx_banner = (total_w - bw_banner) / 2
        dwg.add(
            dwg.rect(
                insert=(bx_banner, banner_y),
                size=(bw_banner, BANNER_H - 4),
                rx=10,
                ry=10,
                fill=banner_tint,
                stroke=banner_color,
                stroke_width=1.5,
            )
        )
        dwg.add(
            dwg.text(
                banner_text,
                insert=(total_w / 2, banner_y + (BANNER_H - 4) / 2 + 4),
                text_anchor="middle",
                font_size="10px",
                font_family="Helvetica, Arial, sans-serif",
                font_weight="bold",
                fill=banner_color,
            )
        )

        content_y = MARGIN + TITLE_H + BANNER_H

        # Rack column geometry (computed up front so spines can be centered
        # above the rack where each is installed).
        rack_x_start = (total_w - (num_racks * rack_w + (num_racks - 1) * RACK_GAP)) / 2
        rack_name_to_index: Dict[str, int] = {}
        for ri_name, rack_name_entry in enumerate(racks):
            rn = rack_name_entry.get("rack_name")
            if rn and rn not in rack_name_to_index:
                rack_name_to_index[rn] = ri_name

        def _rack_center_x(rack_index: int) -> float:
            return rack_x_start + rack_index * (rack_w + RACK_GAP) + rack_w / 2

        # Spine tier
        spine_positions: Dict[str, Tuple[float, float]] = {}
        if has_spine:
            tier_label_y = content_y + 4
            dwg.add(
                dwg.text(
                    "Spine Switches",
                    insert=(total_w / 2, tier_label_y),
                    text_anchor="middle",
                    font_size="9px",
                    font_family="Helvetica, Arial, sans-serif",
                    fill=COLOR_SPINE_FABRIC,
                )
            )

            # Center each spine above its assigned rack (SW-SP-01 -> C01,
            # SW-SP-02 -> C02). Spines whose rack is unknown fall back to an
            # evenly distributed centered row. Track per-rack counts so two
            # spines in the same rack don't overlap.
            fallback_start = (total_w - len(spines) * (SWITCH_W + 40)) / 2
            per_rack_count: Dict[int, int] = {}
            for i, sp in enumerate(spines):
                assigned_rack = sp.get("_assigned_rack", "") if isinstance(sp, dict) else ""
                rack_index = rack_name_to_index.get(assigned_rack)
                if rack_index is not None:
                    nth = per_rack_count.get(rack_index, 0)
                    per_rack_count[rack_index] = nth + 1
                    # Offset multiple spines in the same rack side by side.
                    sx = _rack_center_x(rack_index) - SWITCH_W / 2 + (nth - 0) * (SWITCH_W + 12)
                else:
                    sx = fallback_start + i * (SWITCH_W + 40)
                sy = content_y + 10
                hostname = sp.get("hostname", f"Spine-{i+1}")
                self._draw_switch_node(
                    dwg,
                    sx,
                    sy,
                    SWITCH_W,
                    SWITCH_H,
                    f"SP{i+1}",
                    hostname,
                    self._fill("grad_spine"),
                    COLOR_DEVICE_STROKE,
                )
                spine_positions[sp.get("mgmt_ip", f"spine_{i}")] = (sx + SWITCH_W / 2, sy + SWITCH_H)

            content_y += SPINE_ROW_H + SPINE_GAP

        # ----- Rack columns -----

        # NET-2B pre-pass: compute switch_centers for ALL racks BEFORE drawing
        # any device->switch edges so cross-rack lookups resolve. The v1.5.7
        # bug populated switch_centers as it iterated, which silently dropped
        # cross-rack edges from the first rack (those switches weren't in
        # the dict yet when the first rack's devices were being rendered).
        switch_centers: Dict[str, Tuple[float, float]] = {}
        rack_switch_ips_by_index: List[set] = []
        switch_rack_idx: Dict[str, int] = {}
        sw_pair_w_pre = min(SWITCH_W, (rack_w - 2 * RACK_PAD_X - SWITCH_GAP) / 2)
        for ri_pre, rack_pre in enumerate(racks):
            rx_pre = rack_x_start + ri_pre * (rack_w + RACK_GAP)
            sw_y_pre = content_y + RACK_PAD_TOP
            rack_ips: set = set()
            for si_pre, sw_pre in enumerate(rack_pre.get("switches", [])[:2]):
                if not isinstance(sw_pre, dict):
                    continue
                sx_pre = rx_pre + RACK_PAD_X + si_pre * (sw_pair_w_pre + SWITCH_GAP)
                mgmt_ip_pre = sw_pre.get("mgmt_ip", "")
                if mgmt_ip_pre:
                    switch_centers[mgmt_ip_pre] = (sx_pre + sw_pair_w_pre / 2, sw_y_pre + SWITCH_H)
                    rack_ips.add(mgmt_ip_pre)
                    switch_rack_idx[mgmt_ip_pre] = ri_pre
            rack_switch_ips_by_index.append(rack_ips)
        all_switch_ips: set = set(switch_centers.keys())

        # NET-2B: compute the inter-rack gutter midpoint for cross-rack
        # waypoint routing. With MAX_RACKS_PER_PAGE = 2 this is just the
        # midpoint between rack 0's right edge and rack 1's left edge.
        gutter_mid_x: Optional[float] = None
        if num_racks >= 2:
            left_rx = rack_x_start
            right_rx = rack_x_start + (rack_w + RACK_GAP)
            gutter_mid_x = (left_rx + rack_w + right_rx) / 2

        # v1.5.8 follow-up: collect every (device, rack, geometry) tuple during
        # the per-rack loop so we can run a SECOND draw pass after all rack
        # frames, switches, and devices are on the canvas. The second pass
        # draws only cross-rack edges, ensuring they land on top of every
        # rack frame fill and are clearly visible (the v1.5.8 baseline drew
        # them mid-loop and they were obscured by the next rack's frame).
        pending_cross_rack: List[Dict[str, Any]] = []

        for ri, rack in enumerate(racks):
            rx = rack_x_start + ri * (rack_w + RACK_GAP)
            ry = content_y

            # Rack background
            dwg.add(
                dwg.rect(
                    insert=(rx, ry),
                    size=(rack_w, rack_h),
                    rx=6,
                    ry=6,
                    fill=COLOR_RACK_BG,
                    stroke="#e0e0e0",
                    stroke_width=1,
                )
            )
            # Rack header
            dwg.add(
                dwg.text(
                    rack["rack_name"],
                    insert=(rx + rack_w / 2, ry + 16),
                    text_anchor="middle",
                    font_size="11px",
                    font_family="Helvetica, Arial, sans-serif",
                    font_weight="bold",
                    fill=COLOR_RACK_HEADER,
                )
            )

            # Local leaf switches at top of rack
            rack_switches = rack.get("switches", [])
            sw_y = ry + RACK_PAD_TOP
            sw_pair_w = min(SWITCH_W, (rack_w - 2 * RACK_PAD_X - SWITCH_GAP) / 2)
            for si, sw in enumerate(rack_switches[:2]):
                sx = rx + RACK_PAD_X + si * (sw_pair_w + SWITCH_GAP)
                designation = "SWA" if si == 0 else "SWB"
                hostname = sw.get("hostname", "") if isinstance(sw, dict) else ""
                self._draw_switch_node(
                    dwg,
                    sx,
                    sw_y,
                    sw_pair_w,
                    SWITCH_H,
                    designation,
                    hostname,
                    self._fill("grad_switch"),
                    COLOR_DEVICE_STROKE,
                )
                mgmt_ip = sw.get("mgmt_ip", "") if isinstance(sw, dict) else ""
                switch_centers[mgmt_ip] = (sx + sw_pair_w / 2, sw_y + SWITCH_H)

            # IPL between paired leaf switches — only for non-leaf/spine
            # topologies. Leaf/spine fabrics have NO leaf-leaf IPL; each
            # leaf instead uplinks to every spine via ISLs (drawn below).
            if not has_spine and len(rack_switches) >= 2:
                sw0 = rack_switches[0]
                sw1 = rack_switches[1]
                ip0 = sw0.get("mgmt_ip", "") if isinstance(sw0, dict) else ""
                ip1 = sw1.get("mgmt_ip", "") if isinstance(sw1, dict) else ""
                if ip0 in switch_centers and ip1 in switch_centers:
                    c0 = switch_centers[ip0]
                    c1 = switch_centers[ip1]
                    ipl_y = sw_y + SWITCH_H / 2
                    dwg.add(
                        dwg.line(
                            start=(c0[0] + sw_pair_w / 2 + 2, ipl_y),
                            end=(c1[0] - sw_pair_w / 2 - 2, ipl_y),
                            stroke=COLOR_IPL,
                            stroke_width=2,
                        )
                    )
                    mid_ipl_x = (c0[0] + c1[0]) / 2
                    # IPL badge
                    bw, bh = 28, 14
                    dwg.add(
                        dwg.rect(
                            insert=(mid_ipl_x - bw / 2, ipl_y - bh / 2),
                            size=(bw, bh),
                            rx=7,
                            ry=7,
                            fill="white",
                            stroke=COLOR_IPL,
                            stroke_width=1,
                        )
                    )
                    dwg.add(
                        dwg.text(
                            "IPL",
                            insert=(mid_ipl_x, ipl_y + 4),
                            text_anchor="middle",
                            font_size="8px",
                            font_family="Helvetica, Arial, sans-serif",
                            font_weight="bold",
                            fill=COLOR_IPL,
                        )
                    )

            # Separator line
            sep_y = sw_y + SWITCH_H + SWITCH_GAP / 2
            dwg.add(
                dwg.line(
                    start=(rx + 8, sep_y),
                    end=(rx + rack_w - 8, sep_y),
                    stroke="#e0e0e0",
                    stroke_width=0.5,
                )
            )

            # CBoxes
            dev_y = sep_y + DEVICE_GAP
            dev_x = rx + RACK_PAD_X
            for ci, cb in enumerate(rack["cboxes"]):
                cb_name = cb.get("name", f"CB{ci+1}") if isinstance(cb, dict) else f"CB{ci+1}"
                cb_is_miscabled = self._device_has_miscabled_ip(cb, miscabled_node_ips)
                self._draw_device_node(
                    dwg,
                    dev_x,
                    dev_y,
                    DEVICE_W,
                    DEVICE_H,
                    cb_name,
                    self._fill("grad_cbox"),
                    COLOR_DEVICE_STROKE,
                    icon="server",
                    is_miscabled=cb_is_miscabled,
                )

                # Pass 1: draw only SAME-RACK edges during the per-rack loop
                # so they appear above this rack's frame but below the
                # cross-rack pass that runs after every rack is drawn.
                self._draw_device_connections(
                    dwg,
                    cb,
                    dev_x,
                    dev_y,
                    DEVICE_W,
                    DEVICE_H,
                    switch_centers,
                    rack_switches,
                    port_map,
                    sep_y,
                    device_index=ci,
                    current_rack_switch_ips=rack_switch_ips_by_index[ri],
                    all_switch_ips=all_switch_ips,
                    device_rack_column=("left" if ri == 0 else "right"),
                    gutter_mid_x=gutter_mid_x,
                    subnet_color_map=subnet_color_map,
                    edge_filter="same_rack",
                )
                # Stash device geometry for the post-loop cross-rack pass.
                pending_cross_rack.append(
                    {
                        "device": cb,
                        "dev_x": dev_x,
                        "dev_y": dev_y,
                        "device_index": ci,
                        "rack_index": ri,
                        "rack_switches": rack_switches,
                        "sep_y": sep_y,
                    }
                )

                dev_y += DEVICE_H + DEVICE_GAP

            # Section separator between CBoxes and DBoxes
            if rack["bottom_devices"]:
                sep_line_y = dev_y + DEVICE_GAP
                dwg.add(
                    dwg.line(
                        start=(rx + 10, sep_line_y),
                        end=(rx + rack_w - 10, sep_line_y),
                        stroke="#9e9e9e",
                        stroke_width=1,
                        stroke_dasharray="4,3",
                    )
                )
                dev_y = sep_line_y + DEVICE_GAP * 3

            # Bottom devices (DBoxes/EBoxes)
            for di, bd in enumerate(rack["bottom_devices"]):
                bd_name = (
                    bd.get("name", f"{rack['bottom_label']}{di+1}")
                    if isinstance(bd, dict)
                    else f"{rack['bottom_label']}{di+1}"
                )
                grad = self._fill("grad_cbox") if rack["bottom_label"] == "EB" else self._fill("grad_dbox")
                bd_is_miscabled = self._device_has_miscabled_ip(bd, miscabled_node_ips)
                self._draw_device_node(
                    dwg,
                    dev_x,
                    dev_y,
                    DEVICE_W,
                    DEVICE_H,
                    bd_name,
                    grad,
                    COLOR_DEVICE_STROKE,
                    icon="storage",
                    is_miscabled=bd_is_miscabled,
                )

                total_cboxes = len(rack["cboxes"])
                # Pass 1: same-rack only; cross-rack deferred to post-loop pass.
                self._draw_device_connections(
                    dwg,
                    bd,
                    dev_x,
                    dev_y,
                    DEVICE_W,
                    DEVICE_H,
                    switch_centers,
                    rack_switches,
                    port_map,
                    sep_y,
                    device_index=total_cboxes + di,
                    current_rack_switch_ips=rack_switch_ips_by_index[ri],
                    all_switch_ips=all_switch_ips,
                    device_rack_column=("left" if ri == 0 else "right"),
                    gutter_mid_x=gutter_mid_x,
                    subnet_color_map=subnet_color_map,
                    edge_filter="same_rack",
                )
                pending_cross_rack.append(
                    {
                        "device": bd,
                        "dev_x": dev_x,
                        "dev_y": dev_y,
                        "device_index": total_cboxes + di,
                        "rack_index": ri,
                        "rack_switches": rack_switches,
                        "sep_y": sep_y,
                    }
                )

                dev_y += DEVICE_H + DEVICE_GAP

            # Leaf -> spine ISLs. Leaf/spine fabrics run multiple ISLs from
            # each leaf to each spine (no leaf-leaf IPL). vnetmap does not
            # capture inter-switch links, so we render an inferred full mesh:
            # every leaf in this rack connects to every spine. Drawn in the
            # spine-fabric gray, dashed, to distinguish from node edges.
            if has_spine and rack_switches and spine_positions:
                for sw in rack_switches[:2]:
                    if not isinstance(sw, dict):
                        continue
                    leaf_ip = sw.get("mgmt_ip", "")
                    if leaf_ip not in switch_centers:
                        continue
                    sw_cx, sw_bot = switch_centers[leaf_ip]
                    sw_top_y = sw_bot - SWITCH_H
                    for sp_cx, sp_bot in spine_positions.values():
                        mid_y_up = content_y - SPINE_GAP / 2
                        path_d = _ortho_path(sw_cx, sw_top_y, sp_cx, sp_bot, mid_y=mid_y_up)
                        dwg.add(
                            dwg.path(
                                d=path_d,
                                fill="none",
                                stroke=COLOR_SPINE_FABRIC,
                                stroke_width=1.2,
                                stroke_dasharray="4,2",
                            )
                        )

        # ----- Inter-rack IPL/MLAG (v1.5.8 follow-up) ----------------
        # The per-rack loop above only draws an IPL line when both
        # paired switches live in the SAME rack. For clusters with one
        # switch per rack (and the IPL crossing the gutter), we render
        # the line here in a post-loop pass so the IPL appears on top
        # of every rack frame and switch box.
        sw_y_ipl = content_y + RACK_PAD_TOP
        ipl_y_global = sw_y_ipl + SWITCH_H / 2
        inter_rack_ipl_pairs = (
            [] if has_spine else self._collect_inter_rack_ipl_pairs(ipl_conns, switch_centers, switch_rack_idx)
        )
        for ip1, ip2 in inter_rack_ipl_pairs:
            c1 = switch_centers[ip1]
            c2 = switch_centers[ip2]
            # Order endpoints left-to-right so the line endpoints sit
            # against the correct switch edges regardless of which
            # rack came first in the data.
            if c1[0] > c2[0]:
                c1, c2 = c2, c1
            dwg.add(
                dwg.line(
                    start=(c1[0] + sw_pair_w_pre / 2 + 2, ipl_y_global),
                    end=(c2[0] - sw_pair_w_pre / 2 - 2, ipl_y_global),
                    stroke=COLOR_IPL,
                    stroke_width=2,
                )
            )
            mid_ipl_x = (c1[0] + c2[0]) / 2
            bw, bh = 28, 14
            dwg.add(
                dwg.rect(
                    insert=(mid_ipl_x - bw / 2, ipl_y_global - bh / 2),
                    size=(bw, bh),
                    rx=7,
                    ry=7,
                    fill="white",
                    stroke=COLOR_IPL,
                    stroke_width=1,
                )
            )
            dwg.add(
                dwg.text(
                    "IPL",
                    insert=(mid_ipl_x, ipl_y_global + 4),
                    text_anchor="middle",
                    font_size="8px",
                    font_family="Helvetica, Arial, sans-serif",
                    font_weight="bold",
                    fill=COLOR_IPL,
                )
            )

        # ----- Pass 2: cross-rack edges (drawn AFTER every rack frame,
        # switch box, and device box so they sit on top and stay visible
        # regardless of which rack column they traverse). -----
        for entry in pending_cross_rack:
            ri_e = entry["rack_index"]
            self._draw_device_connections(
                dwg,
                entry["device"],
                entry["dev_x"],
                entry["dev_y"],
                DEVICE_W,
                DEVICE_H,
                switch_centers,
                entry["rack_switches"],
                port_map,
                entry["sep_y"],
                device_index=entry["device_index"],
                current_rack_switch_ips=rack_switch_ips_by_index[ri_e],
                all_switch_ips=all_switch_ips,
                device_rack_column=("left" if ri_e == 0 else "right"),
                gutter_mid_x=gutter_mid_x,
                subnet_color_map=subnet_color_map,
                edge_filter="cross_rack",
            )

        # ----- Legend -----
        legend_y = content_y + rack_h + 10
        self._draw_legend(
            dwg,
            total_w,
            legend_y,
            switches=_all_switches,
            subnet_color_map=subnet_color_map,
            port_map=port_map,
            has_spine=has_spine,
            items=legend_items,
        )

        # ----- Page number -----
        if total_pages > 1:
            dwg.add(
                dwg.text(
                    f"Page {page_num} of {total_pages}",
                    insert=(total_w / 2, total_h - 8),
                    text_anchor="middle",
                    font_size="8px",
                    font_family="Helvetica, Arial, sans-serif",
                    fill="#9e9e9e",
                )
            )

        return str(dwg.tostring())

    # ------------------------------------------------------------------
    # Draw helpers
    # ------------------------------------------------------------------
    _GRADIENT_FLAT_MAP = {
        "grad_cbox": COLOR_CBOX_FILL,
        "grad_dbox": COLOR_DBOX_FILL,
        "grad_switch": COLOR_SWITCH_FILL,
        "grad_spine": COLOR_SPINE_FILL,
    }

    def _fill(self, grad_id: str) -> str:
        """Return gradient URL when cairosvg will render, else flat color."""
        if self._use_gradients:
            return f"url(#{grad_id})"
        return self._GRADIENT_FLAT_MAP.get(grad_id, COLOR_CBOX_FILL)

    def _add_gradients(self, dwg: Any) -> None:
        if not self._use_gradients:
            return
        defs = dwg.defs
        for gid, c1, c2 in [
            ("grad_cbox", "#ffffff", COLOR_CBOX_FILL),
            ("grad_dbox", "#ffffff", COLOR_DBOX_FILL),
            ("grad_switch", "#ffffff", COLOR_SWITCH_FILL),
            ("grad_spine", "#ffffff", COLOR_SPINE_FILL),
        ]:
            lg = dwg.linearGradient(id=gid, x1="0%", y1="0%", x2="0%", y2="100%")
            lg.add_stop_color(0, c1)
            lg.add_stop_color(1, c2)
            defs.add(lg)

    def _draw_device_node(
        self,
        dwg: Any,
        x: float,
        y: float,
        w: float,
        h: float,
        label: str,
        fill: str,
        stroke: str,
        icon: Optional[str] = None,
        is_miscabled: bool = False,
    ) -> None:
        """Draw a device rectangle with optional icon and label.

        NET-4: when ``is_miscabled`` is True, an extra red dashed outline
        is drawn around the device box and a small "!" glyph is appended
        to the right side of the label so the operator can quickly spot
        offending nodes.
        """
        dwg.add(
            dwg.rect(
                insert=(x, y),
                size=(w, h),
                rx=4,
                ry=4,
                fill=fill,
                stroke=stroke,
                stroke_width=1,
            )
        )

        if is_miscabled:
            # NET-4: red dashed outline + warning glyph on offending nodes
            dwg.add(
                dwg.rect(
                    insert=(x - 1, y - 1),
                    size=(w + 2, h + 2),
                    rx=5,
                    ry=5,
                    fill="none",
                    stroke="#EA4335",
                    stroke_width=1.5,
                    stroke_dasharray="3,2",
                )
            )
            dwg.add(
                dwg.text(
                    "!",
                    insert=(x + w - 8, y + h / 2 + 4),
                    text_anchor="middle",
                    font_size="11px",
                    font_family="Helvetica, Arial, sans-serif",
                    font_weight="bold",
                    fill="#EA4335",
                )
            )

        # Icon (small, left side)
        if icon and self.device_icon_mode == "flat":
            icon_data = {
                "server": ICON_SERVER,
                "storage": ICON_STORAGE,
                "switch": ICON_SWITCH,
            }.get(icon)
            if icon_data:
                icon_g = dwg.g(transform=f"translate({x + 4},{y + h / 2 - 5}) scale(0.8)")
                icon_g.add(dwg.path(d=icon_data, fill="none", stroke=stroke, stroke_width=0.8))
                dwg.add(icon_g)

        # Label text — truncate to fit box width
        text_x = x + (24 if icon and self.device_icon_mode == "flat" else 6)
        avail_chars = int((w - (text_x - x) - 4) / 5.0)  # ~5px per char at 9px font
        display_label = label if len(label) <= avail_chars else label[: avail_chars - 1] + "…"
        dwg.add(
            dwg.text(
                display_label,
                insert=(text_x, y + h / 2 + 4),
                font_size="9px",
                font_family="Helvetica, Arial, sans-serif",
                fill=COLOR_LABEL,
            )
        )

    def _draw_switch_node(
        self,
        dwg: Any,
        x: float,
        y: float,
        w: float,
        h: float,
        designation: str,
        hostname: str,
        fill: str,
        stroke: str,
    ) -> None:
        """Draw a switch box with a bold designation label and small hostname subtitle."""
        dwg.add(
            dwg.rect(
                insert=(x, y),
                size=(w, h),
                rx=4,
                ry=4,
                fill=fill,
                stroke=stroke,
                stroke_width=1,
            )
        )

        if self.device_icon_mode == "flat":
            icon_g = dwg.g(transform=f"translate({x + 4},{y + h / 2 - 5}) scale(0.8)")
            icon_g.add(dwg.path(d=ICON_SWITCH, fill="none", stroke=stroke, stroke_width=0.8))
            dwg.add(icon_g)

        text_x = x + (24 if self.device_icon_mode == "flat" else 6)

        dwg.add(
            dwg.text(
                designation,
                insert=(text_x, y + h / 2 - 1),
                font_size="10px",
                font_family="Helvetica, Arial, sans-serif",
                font_weight="bold",
                fill=COLOR_LABEL,
            )
        )

        if hostname:
            avail = int((w - (text_x - x) - 4) / 4.5)
            short_name = hostname if len(hostname) <= avail else hostname[: avail - 1] + "…"
            dwg.add(
                dwg.text(
                    short_name,
                    insert=(text_x, y + h / 2 + 9),
                    font_size="7px",
                    font_family="Helvetica, Arial, sans-serif",
                    fill="#757575",
                )
            )

    def _draw_device_connections(
        self,
        dwg: Any,
        device: Any,
        dev_x: float,
        dev_y: float,
        dev_w: float,
        dev_h: float,
        switch_centers: Dict[str, Tuple[float, float]],
        _rack_switches: List[Any],
        port_map: List[Dict[str, Any]],
        bus_y_base: float,
        device_index: int = 0,
        current_rack_switch_ips: Optional[set] = None,
        all_switch_ips: Optional[set] = None,
        device_rack_column: str = "left",
        gutter_mid_x: Optional[float] = None,
        subnet_color_map: Optional[Dict[str, str]] = None,
        edge_filter: str = "all",
    ) -> None:
        """Draw device->switch connections as v1.5.8 mockup-style bezier swoops.

        Each edge is a single cubic bezier built by ``_bezier_swoop_path``:
        it exits the device's exit side horizontally, sweeps toward the
        switch, and lands vertically on the switch's bottom edge at a
        per-device ``landing_x`` (staggered by ``device_index`` so the
        lines fan out under the switch instead of overlapping).

        NET-2B routing classification still applies:

        - Same-rack edges exit the OUTER side of the device (left edge for
          left-rack devices, right edge for right-rack devices). They are
          drawn solid with opacity 0.85.
        - Cross-rack edges exit the INNER side of the device toward the
          inter-rack gutter. They are drawn dashed (``stroke-dasharray='6,4'``)
          with opacity 0.55.

        ``current_rack_switch_ips`` and ``all_switch_ips`` are used by
        ``_classify_edge`` to determine same-rack vs cross-rack vs orphan.
        Only true orphans are skipped — cross-rack edges are rendered
        instead of silently dropped (the v1.5.7 bug). ``gutter_mid_x`` is
        accepted for API compatibility but is no longer used: the bezier
        swoop's ``cp1`` extends naturally outward from the exit side, so
        no gutter waypoint is needed.

        ``edge_filter`` controls which classification(s) are emitted:
        ``"all"`` (default) draws both kinds; ``"same_rack"`` and
        ``"cross_rack"`` draw only that classification. The two-pass
        renderer in ``_render_page`` uses the filtered modes so
        cross-rack edges land on top of every rack frame, switch box,
        and device — fixing the v1.5.8 issue where right-rack
        cross-rack lines were obscured by the right rack's frame fill.
        """
        if not isinstance(device, dict):
            return

        dev_ips = set()
        for field in ("mgmt_ip", "ipmi_ip", "ip"):
            ip = device.get(field)
            if ip:
                dev_ips.add(ip)
        for dip in device.get("data_ips", []):
            dev_ips.add(dip)
        for aip in device.get("_all_ips", []):
            dev_ips.add(aip)
        dev_name = device.get("name", "")
        dev_hostname = device.get("hostname", "")
        dev_node_key = self._hostname_node_key(dev_hostname) or self._hostname_node_key(dev_name)

        if not dev_ips and not dev_name and not dev_hostname:
            return

        # Defaults preserve v1.5.7 behavior when called without NET-2B context
        # (e.g. legacy callers); _classify_edge degenerates to "same_rack" if
        # current_rack_switch_ips covers every switch.
        if all_switch_ips is None:
            all_switch_ips = set(switch_centers.keys())
        if current_rack_switch_ips is None:
            current_rack_switch_ips = set(switch_centers.keys())

        # Bezier landing fan: each edge lands at a unique x under the switch's
        # bottom edge, staggered by device_index. Centered around the switch
        # center so the fan visually balances under the switch box.
        LANDING_STAGGER = 5.0
        LANDING_FAN_CENTER_INDEX = 4.5  # roughly centers a 10-device rack
        _ = bus_y_base  # kept in signature for API compat with prior orthogonal path

        drawn: set = set()

        for conn in port_map:
            node_ip = conn.get("node_ip", "")
            conn_hostname = conn.get("node_hostname", conn.get("hostname", ""))
            sw_ip = conn.get("switch_ip", "")
            network = conn.get("network", "")
            interface = conn.get("interface", "")

            ip_match = node_ip and node_ip in dev_ips
            name_match = (
                dev_hostname
                and conn_hostname
                and (dev_hostname == conn_hostname or dev_hostname in conn_hostname or conn_hostname in dev_hostname)
            ) or (
                dev_name
                and conn_hostname
                and (dev_name == conn_hostname or dev_name in conn_hostname or conn_hostname in dev_name)
            )
            # IB fallback: match on the rack-prefix-independent box/node
            # suffix (CB6-U22-CN1). The suffix is reused across racks, so a
            # suffix-only match is honored ONLY for a same-rack switch
            # (handled below) — this also reflects that vnetmap reaches only
            # the leaf switches it could SSH to.
            conn_node_key = self._hostname_node_key(conn_hostname)
            suffix_match = bool(dev_node_key and conn_node_key and dev_node_key == conn_node_key)

            if not (ip_match or name_match or suffix_match):
                continue

            classification = self._classify_edge(
                sw_ip=sw_ip,
                current_rack_switch_ips=current_rack_switch_ips,
                all_switch_ips=all_switch_ips,
            )
            if classification == "orphan":
                continue
            # A suffix-only match (no IP/full-name evidence) is ambiguous
            # across racks, so only trust it for a same-rack switch.
            if suffix_match and not (ip_match or name_match) and classification != "same_rack":
                continue
            if edge_filter != "all" and classification != edge_filter:
                continue

            if not self._is_drawable_interface(interface, conn):
                continue

            conn_key = (sw_ip, node_ip, network)
            if conn_key in drawn:
                continue
            drawn.add(conn_key)

            sw_cx, sw_bot = switch_centers[sw_ip]

            is_cross_rack = classification == "cross_rack"
            edge_plan = self._plan_device_edge(
                is_cross_rack=is_cross_rack,
                device_rack_column=device_rack_column,
                dev_x=dev_x,
                dev_w=dev_w,
            )
            exit_x = edge_plan["exit_x"]
            dasharray = edge_plan["dasharray"]
            opacity = edge_plan["opacity"]
            exit_extends_right = exit_x > dev_x + dev_w / 2

            # NET-3: color by the switch's serviced /24 subnet (deprecates
            # the v1.5.7 Network A/B classifier). Fall back to palette[0] if
            # the switch has no subnet evidence yet — defensive only; the
            # renderer normally has full port_map evidence at this point.
            if subnet_color_map and sw_ip in subnet_color_map:
                color = subnet_color_map[sw_ip]
            else:
                color = SUBNET_COLOR_PALETTE[0]
            _ = network  # explicitly unused — kept in port_map for legacy data
            _ = gutter_mid_x  # no longer needed: bezier swoop replaces gutter routing

            exit_y = dev_y + dev_h / 2
            landing_x = sw_cx + (device_index - LANDING_FAN_CENTER_INDEX) * LANDING_STAGGER

            path_d = self._bezier_swoop_path(
                exit_x=exit_x,
                exit_y=exit_y,
                landing_x=landing_x,
                sw_bot_y=sw_bot,
                exit_extends_right=exit_extends_right,
            )
            path_kwargs: Dict[str, Any] = {
                "d": path_d,
                "fill": "none",
                "stroke": color,
                "stroke_width": 2.0,
                "opacity": opacity,
            }
            if dasharray:
                path_kwargs["stroke_dasharray"] = dasharray
            dwg.add(dwg.path(**path_kwargs))

            if self.show_port_labels:
                port_name = conn.get("port", "")
                if port_name:
                    # Anchor the label on the side away from the device so
                    # it doesn't overlap the box edge.
                    label_x = exit_x + (6 if exit_x == dev_x else -6)
                    label_y = exit_y - 4
                    dwg.add(
                        dwg.text(
                            port_name,
                            insert=(label_x, label_y),
                            font_size="6px",
                            font_family="Helvetica, Arial, sans-serif",
                            fill=color,
                            opacity=0.7,
                        )
                    )

    @staticmethod
    def _is_drawable_interface(interface: str, conn: Dict[str, Any]) -> bool:
        """Decide whether a connection should appear in the diagram (B6)."""
        if not interface:
            return True

        # Standard CNode interfaces
        if any(f in interface for f in ("f0", "f1", "f2", "f3")):
            return True

        # InfiniBand interfaces (ib0, ib1, ...) — IB clusters carry node
        # connectivity on ibN rather than the fN/ensN Ethernet names.
        if re.match(r"^ib\d", interface):
            return True

        # DNode interfaces that don't follow the fN convention
        node_des = conn.get("node_designation", "")
        is_dnode = "DN" in node_des or "dnode" in conn.get("node_type", "")
        if is_dnode:
            dnode_ifaces = ("ens3", "ens14", "enp65s0", "enp94s0", "enp3s0")
            if any(interface.startswith(p) for p in dnode_ifaces):
                return True

        return False

    @staticmethod
    def _color_tint(color: str) -> str:
        """Return a light tint for a legend pill background, given a stroke color.

        Mapping is hand-tuned for the design palette + IPL/spine; falls back
        to white when the color is not in the map (defensive — keeps the pill
        readable but visually distinct).
        """
        tints = {
            "#0F9D58": "#e6f4ea",  # green
            "#4285F4": "#e3f2fd",  # blue
            "#FF6F00": "#fff3e0",  # amber
            "#00838F": "#e0f2f1",  # teal
            "#AB47BC": "#f3e5f5",  # mauve
            COLOR_IPL: "#f3e5f5",  # purple
            COLOR_SPINE_FABRIC: "#f5f5f5",  # gray
        }
        return tints.get(color, "white")

    def _compute_legend_items(
        self,
        switches: Optional[List[Dict[str, Any]]] = None,
        subnet_color_map: Optional[Dict[str, str]] = None,
        port_map: Optional[List[Dict[str, Any]]] = None,
        has_spine: bool = False,
    ) -> List[Tuple[str, str]]:
        """Build the ordered ``(color, label)`` legend items.

        NET-3: one pill per distinct subnet color in use, labeled with the
        /24 prefix (e.g. ``"172.16.0/24"``). IPL/MLAG and Spine pills are
        appended only when relevant. Falls back to a generic
        ``Same-rack``/``Cross-rack`` legend when subnet evidence is absent.

        Extracted from ``_draw_legend`` so ``_render_page`` can size the
        canvas to the legend's natural width up front (preventing the
        leftmost pill from being clipped).
        """
        switches = switches or []
        subnet_color_map = subnet_color_map or {}
        port_map = port_map or []

        seen_colors: set = set()
        items: List[Tuple[str, str]] = []
        for sw in sorted(switches, key=lambda s: s.get("mgmt_ip", "") if isinstance(s, dict) else ""):
            mgmt_ip = sw.get("mgmt_ip", "") if isinstance(sw, dict) else ""
            color = subnet_color_map.get(mgmt_ip)
            if not color or color in seen_colors:
                continue
            subnet = self._compute_switch_subnet(mgmt_ip, port_map)
            label = f"{subnet}/24" if subnet else "Subnet"
            items.append((color, label))
            seen_colors.add(color)

        if not items:
            items = [
                (SUBNET_COLOR_PALETTE[0], "Same-rack"),
                (SUBNET_COLOR_PALETTE[1], "Cross-rack"),
            ]

        # Leaf/spine fabrics have no leaf-leaf IPL — show the ISL legend
        # instead. Only show IPL/MLAG for non-spine topologies.
        if has_spine:
            items.append((COLOR_SPINE_FABRIC, "ISL (Leaf-Spine)"))
        elif switches:
            items.append((COLOR_IPL, "IPL/MLAG"))
        return items

    @staticmethod
    def _legend_pill_width(label: str) -> float:
        """Width of one legend pill, sized to its label so it is not clipped."""
        text_w = len(label) * LEGEND_CHAR_W
        return max(float(LEGEND_PILL_MIN_W), LEGEND_TEXT_X + text_w + LEGEND_PILL_PAD_R)

    @classmethod
    def _legend_content_width(cls, items: List[Tuple[str, str]]) -> float:
        """Total horizontal extent of the legend row (pills + inter-pill gaps)."""
        if not items:
            return 0.0
        widths = [cls._legend_pill_width(label) for _, label in items]
        return sum(widths) + LEGEND_PILL_GAP * (len(items) - 1)

    def _draw_legend(
        self,
        dwg: Any,
        total_w: float,
        y: float,
        switches: Optional[List[Dict[str, Any]]] = None,
        subnet_color_map: Optional[Dict[str, str]] = None,
        port_map: Optional[List[Dict[str, Any]]] = None,
        has_spine: bool = False,
        items: Optional[List[Tuple[str, str]]] = None,
    ) -> None:
        """Render the bottom legend.

        Pills are sized to their labels and the row is centered within
        ``total_w``, with the start clamped to ``MARGIN`` so the leftmost
        pill is never clipped (the v1.5.8 fixed-spacing layout produced a
        negative start_x on narrow 2-rack pages, cutting off the first
        pill). ``items`` may be precomputed by the caller to keep canvas
        sizing and rendering in sync; otherwise it is derived here.
        """
        if items is None:
            items = self._compute_legend_items(switches, subnet_color_map, port_map, has_spine)

        content_w = self._legend_content_width(items)
        start_x = max(float(MARGIN), (total_w - content_w) / 2)
        bh = LEGEND_PILL_H
        x = start_x
        for color, label in items:
            bw = self._legend_pill_width(label)
            tint = self._color_tint(color)
            dwg.add(
                dwg.rect(
                    insert=(x, y),
                    size=(bw, bh),
                    rx=11,
                    ry=11,
                    fill=tint,
                    stroke=color,
                    stroke_width=1.5,
                )
            )
            dwg.add(
                dwg.line(
                    start=(x + 10, y + bh / 2),
                    end=(x + 26, y + bh / 2),
                    stroke=color,
                    stroke_width=2.5,
                )
            )
            dwg.add(
                dwg.text(
                    label,
                    insert=(x + LEGEND_TEXT_X, y + bh / 2 + 4),
                    font_size="9px",
                    font_family="Helvetica, Arial, sans-serif",
                    font_weight="bold",
                    fill=color,
                )
            )
            x += bw + LEGEND_PILL_GAP

    # ------------------------------------------------------------------
    # SVG to PNG conversion
    # ------------------------------------------------------------------
    @staticmethod
    def _svg_to_png(svg_content: str, output_path: str, dpi: int = 150) -> None:
        """Convert SVG string to PNG using the best available backend.

        Backends tried in order:
        1. cairosvg  (requires system libcairo — best quality)
        2. PyMuPDF/fitz  (pure-Python, already a project dependency)
        3. Log warning and write the SVG file so the report can still reference it
        """
        scale = dpi / 96.0
        svg_bytes = svg_content.encode("utf-8")

        # --- Backend 1: cairosvg (best quality) ---
        if _CAIROSVG_AVAILABLE:
            try:
                import cairosvg

                cairosvg.svg2png(
                    bytestring=svg_bytes,
                    write_to=output_path,
                    scale=scale,
                )
                return
            except Exception as e:
                logger.debug("cairosvg backend failed: %s", e)

        # --- Backend 2: PyMuPDF (fitz) — works on all platforms ---
        try:
            import fitz

            svg_doc = fitz.open(stream=svg_bytes, filetype="svg")
            if len(svg_doc) > 0:
                page = svg_doc[0]
                mat = fitz.Matrix(scale, scale)
                pix = page.get_pixmap(matrix=mat)
                pix.save(output_path)
                svg_doc.close()
                logger.info("SVG converted to PNG via PyMuPDF: %s", Path(output_path).name)
                return
            svg_doc.close()
        except Exception as e:
            logger.debug("PyMuPDF SVG backend failed: %s", e)

        # --- No backend available — save SVG as fallback ---
        svg_fallback = Path(output_path).with_suffix(".svg")
        svg_fallback.write_text(svg_content, encoding="utf-8")
        logger.warning(
            "No SVG-to-PNG backend available (install cairosvg or pymupdf). "
            "SVG saved to %s — network diagram will use compact fallback.",
            svg_fallback.name,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_rack_centric_diagram_generator(
    config: Optional[Dict[str, Any]] = None,
    assets_path: str = "assets",
    library_path: Optional[str] = None,
    user_images_dir: Optional[str] = None,
) -> RackCentricDiagramGenerator:
    return RackCentricDiagramGenerator(
        config=config,
        assets_path=assets_path,
        library_path=library_path,
        user_images_dir=user_images_dir,
    )
