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
COLOR_NETWORK_A = "#0F9D58"   # teal-green
COLOR_NETWORK_B = "#4285F4"   # deep blue
COLOR_IPL = "#7B1FA2"         # purple
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
RACK_PAD_TOP = 40          # space for rack header text
RACK_PAD_BOTTOM = 12
RACK_GAP = 30              # horizontal gap between rack columns
SPINE_ROW_H = 60
SPINE_GAP = 40              # gap between spine tier and racks
LEGEND_H = 36
TITLE_H = 36
MARGIN = 30
BEND_R = 6                  # radius for rounded corners on connections
CONN_OFFSET_A = 8           # left-edge offset for Network A connections
CONN_OFFSET_B = 8           # right-edge offset for Network B connections

# Portrait Letter (8.5 x 11 in) in points
PORTRAIT_W = 8.5 * 72       # 612
PORTRAIT_H = 11 * 72        # 792

# Max racks per page before splitting (portrait fits 2 side-by-side)
MAX_RACKS_PER_PAGE = 2

# ---------------------------------------------------------------------------
# Inline flat-icon SVG path data (B5)
# ---------------------------------------------------------------------------
ICON_SERVER = (
    "M3,2 h18 a1,1 0 0,1 1,1 v6 a1,1 0 0,1 -1,1 H3 a1,1 0 0,1 -1,-1 V3 "
    "a1,1 0 0,1 1,-1 Z M5,5 h2 v2 H5Z M9,5.5 h10"
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
    x1: float, y1: float, x2: float, y2: float,
    mid_y: Optional[float] = None, r: float = BEND_R,
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

    r = min(r, abs(mid_y - y1) / 2, abs(y2 - mid_y) / 2, abs(x2 - x1) / 2) if (
        abs(mid_y - y1) > 0 and abs(y2 - mid_y) > 0 and abs(x2 - x1) > 0
    ) else 0

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
    points: List[Tuple[float, float]], r: float = BEND_R,
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

    # ------------------------------------------------------------------
    # Data enrichment
    # ------------------------------------------------------------------
    @staticmethod
    def _enrich_devices(
        nodes: List[Dict[str, Any]],
        boxes: List[Dict[str, Any]],
        prefix: str,
    ) -> List[Dict[str, Any]]:
        """Merge node data (IPs, hostname) with box data (rack_name).

        Nodes (cnodes/dnodes) carry network addresses that match port_map
        entries; boxes (cboxes/dboxes) carry rack placement info.  This
        method produces a unified device list suitable for rendering.
        """
        box_by_rack_id = {}
        for bx in boxes:
            rid = bx.get("rack_id")
            if rid is not None:
                box_by_rack_id.setdefault(rid, []).append(bx)

        enriched: List[Dict[str, Any]] = []
        for idx, node in enumerate(nodes):
            dev: Dict[str, Any] = dict(node)
            dev.setdefault("name", node.get("hostname", node.get("name", f"{prefix}{idx + 1}")))
            dev.setdefault("rack_name", "")

            # Try to inherit rack_name from a sibling box in the same rack
            if not dev.get("rack_name"):
                rack_id = node.get("rack_id")
                sibling_boxes = box_by_rack_id.get(rack_id, boxes)
                if sibling_boxes:
                    dev["rack_name"] = sibling_boxes[0].get("rack_name", "Default")
                else:
                    dev["rack_name"] = "Default"

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

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------
    def generate(
        self,
        port_mapping_data: Dict[str, Any],
        hardware_data: Dict[str, Any],
        output_dir: str,
        manual_placements: Optional[Dict[str, Any]] = None,
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
        top_devices = self._enrich_devices(cnodes, cboxes, "CB") if cnodes else cboxes
        # Use dnodes or eboxes as bottom devices
        if eboxes:
            bottom_devices = eboxes
            bottom_label = "EB"
        elif dnodes:
            bottom_devices = self._enrich_devices(dnodes, dboxes, "DB")
            bottom_label = "DN"
        else:
            bottom_devices = dboxes
            bottom_label = "DB"

        # ----- classify switches: leaf (in port_map) vs upstream -----
        port_map_switch_ips = {c.get("switch_ip") for c in port_map if c.get("switch_ip")}
        leaf_switches = [sw for sw in switches if sw.get("mgmt_ip") in port_map_switch_ips]
        upstream_switches = [sw for sw in switches if sw.get("mgmt_ip") not in port_map_switch_ips]

        if not leaf_switches:
            leaf_switches = switches
            upstream_switches = []

        logger.info(
            "Switch classification: %d leaf (%s), %d upstream (%s)",
            len(leaf_switches),
            ", ".join(sw.get("hostname", "?") for sw in leaf_switches),
            len(upstream_switches),
            ", ".join(sw.get("hostname", "?") for sw in upstream_switches),
        )
        logger.info(
            "Devices: %d top (CNodes/CBoxes), %d bottom (DNodes/DBoxes)",
            len(top_devices), len(bottom_devices),
        )
        logger.info(
            "Port map: %d connections across %d switch IPs",
            len(port_map), len(port_map_switch_ips),
        )

        # ----- rack grouping -----
        racks = self._build_rack_groups(
            top_devices, bottom_devices, leaf_switches, port_map,
            manual_placements, bottom_label,
        )
        if not racks:
            logger.warning("No rack groups could be formed — falling back to single rack")
            racks = [self._default_rack(top_devices, bottom_devices, leaf_switches, bottom_label)]

        # Upstream switches shown in the spine/upstream tier
        spine_switches = upstream_switches

        # ----- paginate -----
        pages: List[List[Dict[str, Any]]] = []
        for i in range(0, len(racks), MAX_RACKS_PER_PAGE):
            pages.append(racks[i: i + MAX_RACKS_PER_PAGE])

        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        png_paths: List[str] = []

        total_pages = len(pages)
        for page_idx, page_racks in enumerate(pages):
            svg_content = self._render_page(
                svgwrite, page_racks, spine_switches, ipl_conns,
                port_map, switches,
                page_num=page_idx + 1, total_pages=total_pages,
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
    ) -> List[Dict[str, Any]]:
        """Group devices into racks using API rack_name, falling back to profile."""
        rack_map: Dict[str, Dict[str, List[Any]]] = defaultdict(
            lambda: {"cboxes": [], "bottom": [], "switches": []}
        )

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
            rack_map = self._apply_manual_placements(
                cboxes, bottom_devices, manual_placements
            )

        # --- Assign switches to racks by topology ---
        switch_rack = self._assign_switches_to_racks(switches, port_map, rack_map)
        for sw in switches:
            rn = switch_rack.get(id(sw), "Default")
            rack_map[rn]["switches"].append(sw)

        # Build ordered list
        results: List[Dict[str, Any]] = []
        for rn in sorted(rack_map.keys()):
            data = rack_map[rn]
            results.append({
                "rack_name": rn,
                "cboxes": data["cboxes"],
                "bottom_devices": data["bottom"],
                "switches": data["switches"],
                "bottom_label": bottom_label,
            })

        return results

    def _default_rack(
        self, cboxes: list, bottom_devices: list, switches: list, bottom_label: str
    ) -> Dict[str, Any]:
        return {
            "rack_name": "Rack 1",
            "cboxes": cboxes,
            "bottom_devices": bottom_devices,
            "switches": switches,
            "bottom_label": bottom_label,
        }

    def _apply_manual_placements(
        self, cboxes: list, bottom_devices: list, placements: Dict[str, Any],
    ) -> Dict[str, Dict[str, list]]:
        rack_map: Dict[str, Dict[str, list]] = defaultdict(
            lambda: {"cboxes": [], "bottom": [], "switches": []}
        )
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

    def _assign_switches_to_racks(
        self,
        switches: List[Dict[str, Any]],
        port_map: List[Dict[str, Any]],
        rack_map: Dict[str, Dict[str, list]],
    ) -> Dict[int, str]:
        """Determine which rack each switch belongs to based on topology."""
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
            mgmt_ip = sw.get("mgmt_ip", "")
            votes = switch_rack_votes.get(mgmt_ip, {})
            if votes:
                best_rack = max(votes, key=votes.get)  # type: ignore[arg-type]
            else:
                best_rack = list(rack_map.keys())[0] if rack_map else "Default"
            result[id(sw)] = best_rack
            sw["_assigned_rack"] = best_rack

        return result

    def _detect_spines(
        self, switches: List[Dict[str, Any]], racks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
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
        max_devs = max(
            (len(r["cboxes"]) + len(r["bottom_devices"]) for r in racks), default=4
        )
        has_bottom_devs = any(r["bottom_devices"] for r in racks)
        separator_space = DEVICE_GAP * 4 if has_bottom_devs else 0
        rack_inner_h = (
            SWITCH_H + SWITCH_GAP
            + max_devs * (DEVICE_H + DEVICE_GAP)
            + DEVICE_GAP * 2
            + separator_space
        )
        rack_w = DEVICE_W + 2 * RACK_PAD_X
        rack_h = RACK_PAD_TOP + rack_inner_h + RACK_PAD_BOTTOM

        has_spine = len(spines) > 0
        spine_section = SPINE_ROW_H + SPINE_GAP if has_spine else 0

        total_w = max(
            2 * MARGIN + num_racks * rack_w + (num_racks - 1) * RACK_GAP,
            PORTRAIT_W,
        )
        total_h = (
            MARGIN + TITLE_H + spine_section + rack_h + LEGEND_H + MARGIN
        )

        dwg = svgwrite.Drawing(size=(f"{total_w}px", f"{total_h}px"))
        dwg.attribs["xmlns"] = "http://www.w3.org/2000/svg"

        # Background
        dwg.add(dwg.rect(insert=(0, 0), size=(total_w, total_h), fill="white"))

        # Defs: gradients
        self._add_gradients(dwg)

        # Title
        title_y = MARGIN + 20
        dwg.add(dwg.text(
            "Logical Network Topology",
            insert=(total_w / 2, title_y),
            text_anchor="middle",
            font_size="18px",
            font_family="Helvetica, Arial, sans-serif",
            font_weight="bold",
            fill=COLOR_TEXT,
        ))
        dwg.add(dwg.line(
            start=(MARGIN, title_y + 8), end=(total_w - MARGIN, title_y + 8),
            stroke="#e0e0e0", stroke_width=1,
        ))

        content_y = MARGIN + TITLE_H

        # Spine tier
        spine_positions: Dict[str, Tuple[float, float]] = {}
        if has_spine:
            tier_label_y = content_y + 4
            dwg.add(dwg.text(
                "Spine Switches",
                insert=(total_w / 2, tier_label_y),
                text_anchor="middle", font_size="9px",
                font_family="Helvetica, Arial, sans-serif",
                fill=COLOR_SPINE_FABRIC,
            ))

            sx_start = (total_w - len(spines) * (SWITCH_W + 40)) / 2
            for i, sp in enumerate(spines):
                sx = sx_start + i * (SWITCH_W + 40)
                sy = content_y + 10
                hostname = sp.get("hostname", f"Spine-{i+1}")
                self._draw_switch_node(
                    dwg, sx, sy, SWITCH_W, SWITCH_H,
                    f"SP{i+1}", hostname,
                    "url(#grad_spine)", COLOR_DEVICE_STROKE,
                )
                spine_positions[sp.get("mgmt_ip", f"spine_{i}")] = (
                    sx + SWITCH_W / 2, sy + SWITCH_H
                )

            if len(spines) >= 2:
                ips = list(spine_positions.keys())
                p1 = spine_positions[ips[0]]
                p2 = spine_positions[ips[-1]]
                mid_y_fab = p1[1] - SWITCH_H / 2
                dwg.add(dwg.line(
                    start=(p1[0] + SWITCH_W / 2 + 4, mid_y_fab),
                    end=(p2[0] - SWITCH_W / 2 - 4, mid_y_fab),
                    stroke=COLOR_SPINE_FABRIC, stroke_width=1.5,
                    stroke_dasharray="6,3",
                ))

            content_y += SPINE_ROW_H + SPINE_GAP

        # ----- Rack columns -----
        rack_x_start = (total_w - (num_racks * rack_w + (num_racks - 1) * RACK_GAP)) / 2

        switch_centers: Dict[str, Tuple[float, float]] = {}

        for ri, rack in enumerate(racks):
            rx = rack_x_start + ri * (rack_w + RACK_GAP)
            ry = content_y

            # Rack background
            dwg.add(dwg.rect(
                insert=(rx, ry), size=(rack_w, rack_h),
                rx=6, ry=6,
                fill=COLOR_RACK_BG, stroke="#e0e0e0", stroke_width=1,
            ))
            # Rack header
            dwg.add(dwg.text(
                rack["rack_name"],
                insert=(rx + rack_w / 2, ry + 16),
                text_anchor="middle", font_size="11px",
                font_family="Helvetica, Arial, sans-serif",
                font_weight="bold", fill=COLOR_RACK_HEADER,
            ))

            # Local leaf switches at top of rack
            rack_switches = rack.get("switches", [])
            sw_y = ry + RACK_PAD_TOP
            sw_pair_w = min(SWITCH_W, (rack_w - 2 * RACK_PAD_X - SWITCH_GAP) / 2)
            for si, sw in enumerate(rack_switches[:2]):
                sx = rx + RACK_PAD_X + si * (sw_pair_w + SWITCH_GAP)
                designation = "SWA" if si == 0 else "SWB"
                hostname = sw.get("hostname", "") if isinstance(sw, dict) else ""
                self._draw_switch_node(
                    dwg, sx, sw_y, sw_pair_w, SWITCH_H,
                    designation, hostname,
                    "url(#grad_switch)", COLOR_DEVICE_STROKE,
                )
                mgmt_ip = sw.get("mgmt_ip", "") if isinstance(sw, dict) else ""
                switch_centers[mgmt_ip] = (sx + sw_pair_w / 2, sw_y + SWITCH_H)

            # IPL between paired switches
            if len(rack_switches) >= 2:
                sw0 = rack_switches[0]
                sw1 = rack_switches[1]
                ip0 = sw0.get("mgmt_ip", "") if isinstance(sw0, dict) else ""
                ip1 = sw1.get("mgmt_ip", "") if isinstance(sw1, dict) else ""
                if ip0 in switch_centers and ip1 in switch_centers:
                    c0 = switch_centers[ip0]
                    c1 = switch_centers[ip1]
                    ipl_y = sw_y + SWITCH_H / 2
                    dwg.add(dwg.line(
                        start=(c0[0] + sw_pair_w / 2 + 2, ipl_y),
                        end=(c1[0] - sw_pair_w / 2 - 2, ipl_y),
                        stroke=COLOR_IPL, stroke_width=2,
                    ))
                    mid_ipl_x = (c0[0] + c1[0]) / 2
                    # IPL badge
                    bw, bh = 28, 14
                    dwg.add(dwg.rect(
                        insert=(mid_ipl_x - bw / 2, ipl_y - bh / 2),
                        size=(bw, bh), rx=7, ry=7,
                        fill="white", stroke=COLOR_IPL, stroke_width=1,
                    ))
                    dwg.add(dwg.text(
                        "IPL", insert=(mid_ipl_x, ipl_y + 4),
                        text_anchor="middle", font_size="8px",
                        font_family="Helvetica, Arial, sans-serif",
                        font_weight="bold", fill=COLOR_IPL,
                    ))

            # Separator line
            sep_y = sw_y + SWITCH_H + SWITCH_GAP / 2
            dwg.add(dwg.line(
                start=(rx + 8, sep_y), end=(rx + rack_w - 8, sep_y),
                stroke="#e0e0e0", stroke_width=0.5,
            ))

            # CBoxes
            dev_y = sep_y + DEVICE_GAP
            dev_x = rx + RACK_PAD_X
            for ci, cb in enumerate(rack["cboxes"]):
                cb_name = cb.get("name", f"CB{ci+1}") if isinstance(cb, dict) else f"CB{ci+1}"
                self._draw_device_node(
                    dwg, dev_x, dev_y, DEVICE_W, DEVICE_H,
                    cb_name, "url(#grad_cbox)", COLOR_DEVICE_STROKE,
                    icon="server",
                )

                self._draw_device_connections(
                    dwg, cb, dev_x, dev_y, DEVICE_W, DEVICE_H,
                    switch_centers, rack_switches, port_map, sep_y,
                    device_index=ci,
                )

                dev_y += DEVICE_H + DEVICE_GAP

            # Section separator between CBoxes and DBoxes
            if rack["bottom_devices"]:
                sep_line_y = dev_y + DEVICE_GAP
                dwg.add(dwg.line(
                    start=(rx + 10, sep_line_y), end=(rx + rack_w - 10, sep_line_y),
                    stroke="#9e9e9e", stroke_width=1,
                    stroke_dasharray="4,3",
                ))
                dev_y = sep_line_y + DEVICE_GAP * 3

            # Bottom devices (DBoxes/EBoxes)
            for di, bd in enumerate(rack["bottom_devices"]):
                bd_name = bd.get("name", f"{rack['bottom_label']}{di+1}") if isinstance(bd, dict) else f"{rack['bottom_label']}{di+1}"
                grad = "url(#grad_cbox)" if rack["bottom_label"] == "EB" else "url(#grad_dbox)"
                self._draw_device_node(
                    dwg, dev_x, dev_y, DEVICE_W, DEVICE_H,
                    bd_name, grad, COLOR_DEVICE_STROKE,
                    icon="storage",
                )

                total_cboxes = len(rack["cboxes"])
                self._draw_device_connections(
                    dwg, bd, dev_x, dev_y, DEVICE_W, DEVICE_H,
                    switch_centers, rack_switches, port_map, sep_y,
                    device_index=total_cboxes + di,
                )

                dev_y += DEVICE_H + DEVICE_GAP

            # LLDP-confirmed spine uplinks from leaf switches
            if has_spine and rack_switches and ipl_conns:
                spine_ips = set(spine_positions.keys())
                for ipl in ipl_conns:
                    ip1 = ipl.get("switch1_ip", "")
                    ip2 = ipl.get("switch2_ip", "")
                    # Identify spine-to-leaf pairs confirmed by LLDP
                    leaf_ip = spine_ip = None
                    if ip1 in spine_ips and ip2 in switch_centers:
                        spine_ip, leaf_ip = ip1, ip2
                    elif ip2 in spine_ips and ip1 in switch_centers:
                        spine_ip, leaf_ip = ip2, ip1
                    if not (spine_ip and leaf_ip):
                        continue
                    sw_cx, sw_bot = switch_centers[leaf_ip]
                    sw_top_y = sw_bot - SWITCH_H
                    sp_cx, sp_bot = spine_positions[spine_ip]
                    mid_y_up = content_y - SPINE_GAP / 2
                    path_d = _ortho_path(sw_cx, sw_top_y, sp_cx, sp_bot, mid_y=mid_y_up)
                    dwg.add(dwg.path(
                        d=path_d, fill="none",
                        stroke=COLOR_SPINE_FABRIC, stroke_width=1.2,
                        stroke_dasharray="4,2",
                    ))

        # ----- Legend -----
        legend_y = content_y + rack_h + 10
        self._draw_legend(dwg, total_w, legend_y)

        # ----- Page number -----
        if total_pages > 1:
            dwg.add(dwg.text(
                f"Page {page_num} of {total_pages}",
                insert=(total_w / 2, total_h - 8),
                text_anchor="middle", font_size="8px",
                font_family="Helvetica, Arial, sans-serif",
                fill="#9e9e9e",
            ))

        return dwg.tostring()

    # ------------------------------------------------------------------
    # Draw helpers
    # ------------------------------------------------------------------
    def _add_gradients(self, dwg: Any) -> None:
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
        self, dwg: Any, x: float, y: float, w: float, h: float,
        label: str, fill: str, stroke: str,
        icon: Optional[str] = None,
    ) -> None:
        """Draw a device rectangle with optional icon and label."""
        dwg.add(dwg.rect(
            insert=(x, y), size=(w, h), rx=4, ry=4,
            fill=fill, stroke=stroke, stroke_width=1,
        ))

        # Icon (small, left side)
        if icon and self.device_icon_mode == "flat":
            icon_data = {
                "server": ICON_SERVER,
                "storage": ICON_STORAGE,
                "switch": ICON_SWITCH,
            }.get(icon)
            if icon_data:
                icon_g = dwg.g(
                    transform=f"translate({x + 4},{y + h / 2 - 5}) scale(0.8)"
                )
                icon_g.add(dwg.path(d=icon_data, fill="none", stroke=stroke, stroke_width=0.8))
                dwg.add(icon_g)

        # Label text — truncate to fit box width
        text_x = x + (24 if icon and self.device_icon_mode == "flat" else 6)
        avail_chars = int((w - (text_x - x) - 4) / 5.0)  # ~5px per char at 9px font
        display_label = label if len(label) <= avail_chars else label[: avail_chars - 1] + "…"
        dwg.add(dwg.text(
            display_label,
            insert=(text_x, y + h / 2 + 4),
            font_size="9px",
            font_family="Helvetica, Arial, sans-serif",
            fill=COLOR_LABEL,
        ))

    def _draw_switch_node(
        self, dwg: Any, x: float, y: float, w: float, h: float,
        designation: str, hostname: str,
        fill: str, stroke: str,
    ) -> None:
        """Draw a switch box with a bold designation label and small hostname subtitle."""
        dwg.add(dwg.rect(
            insert=(x, y), size=(w, h), rx=4, ry=4,
            fill=fill, stroke=stroke, stroke_width=1,
        ))

        if self.device_icon_mode == "flat":
            icon_g = dwg.g(transform=f"translate({x + 4},{y + h / 2 - 5}) scale(0.8)")
            icon_g.add(dwg.path(d=ICON_SWITCH, fill="none", stroke=stroke, stroke_width=0.8))
            dwg.add(icon_g)

        text_x = x + (24 if self.device_icon_mode == "flat" else 6)

        dwg.add(dwg.text(
            designation,
            insert=(text_x, y + h / 2 - 1),
            font_size="10px",
            font_family="Helvetica, Arial, sans-serif",
            font_weight="bold",
            fill=COLOR_LABEL,
        ))

        if hostname:
            avail = int((w - (text_x - x) - 4) / 4.5)
            short_name = hostname if len(hostname) <= avail else hostname[:avail - 1] + "…"
            dwg.add(dwg.text(
                short_name,
                insert=(text_x, y + h / 2 + 9),
                font_size="7px",
                font_family="Helvetica, Arial, sans-serif",
                fill="#757575",
            ))

    def _draw_device_connections(
        self,
        dwg: Any,
        device: Any,
        dev_x: float, dev_y: float, dev_w: float, dev_h: float,
        switch_centers: Dict[str, Tuple[float, float]],
        _rack_switches: List[Any],
        port_map: List[Dict[str, Any]],
        bus_y_base: float,
        device_index: int = 0,
    ) -> None:
        """Draw orthogonal connections from a device to its rack-local switches.

        Lines exit from the left (Network A) or right (Network B) side of the
        device box at mid-height, route through vertical channels in the rack
        padding, then connect to the corresponding switch via a horizontal bus
        segment.  ``device_index`` staggers bus heights to prevent overlap.
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

        if not dev_ips and not dev_name and not dev_hostname:
            return

        rx = dev_x - RACK_PAD_X
        rack_w = dev_w + 2 * RACK_PAD_X
        chan_a = rx + 6
        chan_b = rx + rack_w - 6

        BUS_STAGGER = 3
        drawn: set = set()

        for conn in port_map:
            node_ip = conn.get("node_ip", "")
            conn_hostname = conn.get("node_hostname", conn.get("hostname", ""))
            sw_ip = conn.get("switch_ip", "")
            network = conn.get("network", "")
            interface = conn.get("interface", "")

            ip_match = node_ip and node_ip in dev_ips
            name_match = (
                (dev_hostname and conn_hostname and (
                    dev_hostname == conn_hostname or dev_hostname in conn_hostname or conn_hostname in dev_hostname
                )) or
                (dev_name and conn_hostname and (
                    dev_name == conn_hostname or dev_name in conn_hostname or conn_hostname in dev_name
                ))
            )

            if not (ip_match or name_match):
                continue

            if sw_ip not in switch_centers:
                continue

            if not self._is_drawable_interface(interface, conn):
                continue

            conn_key = (sw_ip, node_ip, network)
            if conn_key in drawn:
                continue
            drawn.add(conn_key)

            sw_cx, sw_bot = switch_centers[sw_ip]

            mid = bus_y_base - 2 - device_index * BUS_STAGGER

            if network == "A":
                exit_x = dev_x
                chan_x = chan_a
                color = COLOR_NETWORK_A
            else:
                exit_x = dev_x + dev_w
                chan_x = chan_b
                color = COLOR_NETWORK_B

            exit_y = dev_y + dev_h / 2

            waypoints: List[Tuple[float, float]] = [
                (exit_x, exit_y),
                (chan_x, exit_y),
                (chan_x, mid),
                (sw_cx, mid),
                (sw_cx, sw_bot),
            ]

            path_d = _rounded_polyline(waypoints)
            dwg.add(dwg.path(
                d=path_d, fill="none",
                stroke=color, stroke_width=2.0,
                opacity=0.85,
            ))

            if self.show_port_labels:
                port_name = conn.get("port", "")
                if port_name:
                    label_x = exit_x + (6 if network == "A" else -6)
                    label_y = exit_y - 4
                    dwg.add(dwg.text(
                        port_name,
                        insert=(label_x, label_y),
                        font_size="6px",
                        font_family="Helvetica, Arial, sans-serif",
                        fill=color, opacity=0.7,
                    ))

    @staticmethod
    def _is_drawable_interface(interface: str, conn: Dict[str, Any]) -> bool:
        """Decide whether a connection should appear in the diagram (B6)."""
        if not interface:
            return True

        # Standard CNode interfaces
        if any(f in interface for f in ("f0", "f1", "f2", "f3")):
            return True

        # DNode interfaces that don't follow the fN convention
        node_des = conn.get("node_designation", "")
        is_dnode = "DN" in node_des or "dnode" in conn.get("node_type", "")
        if is_dnode:
            dnode_ifaces = ("ens3", "ens14", "enp65s0", "enp94s0", "enp3s0")
            if any(interface.startswith(p) for p in dnode_ifaces):
                return True

        return False

    def _draw_legend(self, dwg: Any, total_w: float, y: float) -> None:
        tint_map = {
            COLOR_NETWORK_A: "#e6f4ea",
            COLOR_NETWORK_B: "#e3f2fd",
            COLOR_IPL: "#f3e5f5",
            COLOR_SPINE_FABRIC: "#f5f5f5",
        }
        items = [
            (COLOR_NETWORK_A, "Network A"),
            (COLOR_NETWORK_B, "Network B"),
            (COLOR_IPL, "IPL/MLAG"),
            (COLOR_SPINE_FABRIC, "Spine"),
        ]
        spacing = 126
        start_x = (total_w - len(items) * spacing) / 2
        for i, (color, label) in enumerate(items):
            x = start_x + i * spacing
            bw, bh = 110, 22
            tint = tint_map.get(color, "white")
            dwg.add(dwg.rect(
                insert=(x, y), size=(bw, bh), rx=11, ry=11,
                fill=tint, stroke=color, stroke_width=1.5,
            ))
            dwg.add(dwg.line(
                start=(x + 10, y + bh / 2), end=(x + 26, y + bh / 2),
                stroke=color, stroke_width=2.5,
            ))
            dwg.add(dwg.text(
                label, insert=(x + 32, y + bh / 2 + 4),
                font_size="9px",
                font_family="Helvetica, Arial, sans-serif",
                font_weight="bold",
                fill=color,
            ))

    # ------------------------------------------------------------------
    # SVG to PNG conversion
    # ------------------------------------------------------------------
    @staticmethod
    def _svg_to_png(svg_content: str, output_path: str, dpi: int = 150) -> None:
        """Convert SVG string to PNG file via cairosvg."""
        if not _CAIROSVG_AVAILABLE:
            logger.error(
                "cairosvg is not available — cannot convert SVG to PNG. "
                "Install with: brew install cairo && pip install cairosvg"
            )
            return
        try:
            import cairosvg

            scale = dpi / 96.0
            cairosvg.svg2png(
                bytestring=svg_content.encode("utf-8"),
                write_to=output_path,
                scale=scale,
            )
        except Exception as e:
            logger.error("SVG to PNG conversion failed: %s", e)


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
