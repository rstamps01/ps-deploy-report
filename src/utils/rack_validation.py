"""Full-rack validation layouts built from the hardware library (RACK-2).

Fills racks of every supported height with one of each library device, bottom to
top in library order, and turns the result into the same rack specs and node
status map the report's Physical Rack Layout uses. ``scripts/generate_rack_validation_report.py``
renders them through ``VastReportBuilder._build_rack_layout_flowables``.

Rules for each rack height H:

- Rack A takes devices in library order from U1 upward. A device that does not fit
  the space left is skipped (it moves to rack B) and the next one that fits is used,
  so the rack ends full.
- Rack B takes the devices rack A did not place, then restarts from the top of the
  library until it is full. If the whole library fits in rack A, rack B instead uses
  the library in reverse order.
"""

from typing import Any, Dict, List, Optional, Tuple

from hardware_library import BUILTIN_DEVICES, get_device_height

LibraryEntry = Tuple[str, Dict[str, Any]]

# Indicator pattern cycled across devices so every color, shape and count appears.
CNODE_STATES: List[Dict[str, Any]] = [
    {"status": "ACTIVE", "is_mgmt": False},
    {"status": "INACTIVE", "is_mgmt": False},
    {"status": "STANDBY", "is_mgmt": True},
]
DNODE_STATES = ["ACTIVE", "INACTIVE"]
SWITCH_STATES = ["ACTIVE", "OFFLINE"]


def library_sequence(user_library: Optional[Dict[str, Any]] = None) -> List[LibraryEntry]:
    """Library devices in index order: built-ins first, then user-added keys.

    Args:
        user_library: Optional user device library (a user key that shadows a
            built-in replaces it in place).

    Returns:
        List[LibraryEntry]: ``(key, entry)`` pairs.
    """
    user_library = user_library or {}
    seq: List[LibraryEntry] = [(k, user_library.get(k, v)) for k, v in BUILTIN_DEVICES.items()]
    seq += [(k, v) for k, v in user_library.items() if k not in BUILTIN_DEVICES]
    return seq


def _height(key: str, user_library: Optional[Dict[str, Any]]) -> int:
    return max(1, int(get_device_height(key, user_library)))


def _place(order: List[LibraryEntry], rack_u: int, user_library: Optional[Dict[str, Any]]) -> Tuple[list, list]:
    """Place devices bottom-up; return (placed, skipped) in input order."""
    placed: List[Dict[str, Any]] = []
    skipped: List[LibraryEntry] = []
    next_u = 1
    for key, entry in order:
        h = _height(key, user_library)
        if next_u + h - 1 <= rack_u:
            placed.append({"key": key, "type": entry.get("type", "cbox"), "height_u": h, "u_position": next_u})
            next_u += h
        else:
            skipped.append((key, entry))
    return placed, skipped


def fill_rack_pair(
    rack_u: int, user_library: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Fill two racks of ``rack_u`` with library devices.

    Args:
        rack_u: Rack height in U.
        user_library: Optional user device library.

    Returns:
        Tuple of placements for rack A and rack B. Each placement has ``key``,
        ``type``, ``height_u`` and ``u_position`` (bottom U).
    """
    seq = library_sequence(user_library)
    total = sum(_height(k, user_library) for k, _ in seq)

    rack_a, leftover = _place(seq, rack_u, user_library)

    if total <= rack_u:
        reversed_rack, _ = _place(list(reversed(seq)), rack_u, user_library)
        return rack_a, reversed_rack

    rack_b: List[Dict[str, Any]] = []
    next_u = 1
    queue = list(leftover)
    wrapped = False
    while next_u <= rack_u:
        progress = False
        for key, entry in queue:
            h = _height(key, user_library)
            if next_u + h - 1 <= rack_u:
                rack_b.append({"key": key, "type": entry.get("type", "cbox"), "height_u": h, "u_position": next_u})
                next_u += h
                progress = True
            if next_u > rack_u:
                break
        if wrapped and not progress:
            break
        queue, wrapped = seq, True
    return rack_a, rack_b


def build_rack_spec(
    name: str, rack_u: int, placements: List[Dict[str, Any]], status_map: Dict[str, Any], counter: Dict[str, int]
) -> Dict[str, Any]:
    """Turn placements into a report rack spec and extend ``status_map``.

    Labels read ``<key> U<a>-U<b>``. Indicators cycle through every state:
    CBoxes get 1-4 CNode dots, DBoxes 2 DNode squares, EBoxes 1 CNode dot plus
    2 DNode squares, switches 1 dot.

    Args:
        name: Rack name.
        rack_u: Rack height in U.
        placements: Output of :func:`fill_rack_pair` for one rack.
        status_map: Node status map to extend (same shape as the report's).
        counter: Running per-type id counter shared across racks.

    Returns:
        Dict[str, Any]: Spec for ``VastReportBuilder._build_rack_layout_flowables``.
    """
    spec: Dict[str, Any] = {"name": name, "height_u": rack_u, "cboxes": [], "dboxes": [], "eboxes": [], "switches": []}
    for p in placements:
        top = p["u_position"] + p["height_u"] - 1
        span = f"U{p['u_position']}" if top == p["u_position"] else f"U{p['u_position']}-U{top}"
        label = f"{p['key']} {span}"
        kind = str(p["type"]).lower()
        counter[kind] = counter.get(kind, 0) + 1
        n = counter[kind]
        device = {"id": n, "model": p["key"], "rack_unit": f"U{p['u_position']}", "state": "ACTIVE", "name": label}

        if kind == "cbox":
            cnodes = [CNODE_STATES[(n + i) % len(CNODE_STATES)] for i in range(1 + (n - 1) % 4)]
            status_map["cnodes_by_cbox"][n] = [dict(c) for c in cnodes]
            spec["cboxes"].append(device)
        elif kind == "dbox":
            device["hardware_type"] = p["key"]
            status_map["dnodes_by_dbox"][n] = [{"status": DNODE_STATES[(n + i) % len(DNODE_STATES)]} for i in range(2)]
            spec["dboxes"].append(device)
        elif kind == "ebox":
            status_map["cnode_by_ebox"][n] = dict(CNODE_STATES[n % len(CNODE_STATES)])
            status_map["dnodes_by_ebox"][n] = [{"status": DNODE_STATES[(n + i) % len(DNODE_STATES)]} for i in range(2)]
            spec["eboxes"].append(device)
        else:
            device = {"id": label, "model": p["key"], "rack_unit": f"U{p['u_position']}", "state": "ACTIVE"}
            status_map["switch_in_inventory"][label] = SWITCH_STATES[n % len(SWITCH_STATES)]
            spec["switches"].append(device)
    spec["switches"] = spec["switches"] or None
    return spec


def empty_status_map() -> Dict[str, Any]:
    """Return an empty node status map with the keys the rack diagram reads."""
    return {
        "cnodes_by_cbox": {},
        "cnode_by_ebox": {},
        "dnodes_by_dbox": {},
        "dnodes_by_ebox": {},
        "switch_in_inventory": {},
    }


def build_validation_racks(
    heights: Optional[List[int]] = None, user_library: Optional[Dict[str, Any]] = None
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Two fully populated racks per height.

    Args:
        heights: Rack heights; defaults to every supported height.
        user_library: Optional user device library.

    Returns:
        Tuple of (rack specs in page order, node status map).
    """
    from rack_diagram import RackDiagram

    heights = list(heights or RackDiagram.SUPPORTED_RACK_HEIGHTS)
    status_map = empty_status_map()
    counter: Dict[str, int] = {}
    racks: List[Dict[str, Any]] = []
    for h in heights:
        rack_a, rack_b = fill_rack_pair(h, user_library)
        racks.append(build_rack_spec(f"VAL-{h}U-A", h, rack_a, status_map, counter))
        racks.append(build_rack_spec(f"VAL-{h}U-B", h, rack_b, status_map, counter))
    return racks, status_map
