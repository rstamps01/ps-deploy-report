"""Shared switch identity helper.

VAST clusters can legitimately contain multiple switches that share the same
``name`` (e.g. two spine switches both named ``Spine-B`` at different
management IPs).  Historically the app keyed switch identity by name in the
placement UI, the report tables, and the rack/network diagrams, so placing one
of the duplicates made the other vanish from the Discovery dropdown and the
two collapsed into a single entry downstream.

This module centralises switch identity so every layer agrees:

* ``switch_id`` — a stable unique key for the physical switch.  Management IP
  (``mgmt_ip``) is the natural choice; we fall back to ``serial`` and then the
  raw ``name`` so a switch without an IP still gets *a* key.
* ``display_name`` — the human label.  When a name is unique it is the name
  verbatim; when a name is shared by 2+ switches each gets a stable
  ``(a)``/``(b)``/... suffix assigned in ascending ``switch_id`` order so the
  same physical switch always earns the same designator across runs.

Keeping this in one pure function (no I/O) means the backend discovery
endpoint and the report pipeline produce identical ``switch_id`` /
``display_name`` values from the same inventory, and it has a single unit-test
surface.
"""

from __future__ import annotations

from typing import Any, Dict, List

__all__ = ["switch_identity_key", "designator_suffix", "assign_switch_designators"]


def switch_identity_key(switch: Dict[str, Any]) -> str:
    """Return a stable unique key for *switch*.

    Precedence: ``mgmt_ip`` -> ``serial`` -> ``name`` -> ``hostname``.  The
    first non-empty, non-``Unknown`` value wins; an empty string is returned
    only when the switch carries no usable identifier at all.
    """
    for field in ("mgmt_ip", "serial", "name", "hostname"):
        value = str(switch.get(field, "") or "").strip()
        if value and value.lower() != "unknown":
            return value
    return ""


def designator_suffix(index: int) -> str:
    """Return a letter designator for *index* (0->'a', 1->'b', ... 26->'aa')."""
    if index < 0:
        index = 0
    letters = ""
    n = index
    while True:
        letters = chr(ord("a") + (n % 26)) + letters
        n = n // 26 - 1
        if n < 0:
            break
    return letters


def assign_switch_designators(switches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Enrich each switch dict in place with ``switch_id`` and ``display_name``.

    For every name shared by 2+ switches, a ``(a)``/``(b)``/... suffix is
    appended to ``display_name`` in ascending ``switch_id`` order so the
    designator is stable across runs.  Switches whose name is unique keep
    ``display_name == name``.  The same list (mutated) is returned for
    convenience so callers can write ``switches = assign_switch_designators(...)``.

    Args:
        switches: List of switch dicts.  Each is expected to have at least a
            ``name`` and ideally a ``mgmt_ip``; missing fields are tolerated.

    Returns:
        The same list, with ``switch_id`` and ``display_name`` set on each
        element.
    """
    if not switches:
        return switches

    # First pass: assign the stable identity key and group by display name.
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for sw in switches:
        sw["switch_id"] = switch_identity_key(sw)
        name = str(sw.get("name", "") or "").strip()
        by_name.setdefault(name, []).append(sw)

    # Second pass: designate duplicates by ascending switch_id (stable order).
    for name, group in by_name.items():
        if len(group) <= 1:
            for sw in group:
                sw["display_name"] = name
            continue
        ordered = sorted(group, key=lambda s: (str(s.get("switch_id", "")), id(s)))
        for idx, sw in enumerate(ordered):
            sw["display_name"] = f"{name} ({designator_suffix(idx)})" if name else designator_suffix(idx)

    return switches
