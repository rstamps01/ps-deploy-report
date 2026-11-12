"""
Port-map source selection (NET-7).

The operator picks the port-map source per run: ``auto`` (default), ``vnetmap`` (switch
login) or ``lldp`` (vnetmap_lldp from the nodes). Callers ask :func:`select_topology_source`
once before vnetmap runs and, when vnetmap ran, once more with its step result.
"""

from typing import Any, Dict, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

SOURCE_AUTO = "auto"
SOURCE_VNETMAP = "vnetmap"
SOURCE_LLDP = "lldp"
VALID_SOURCES = (SOURCE_AUTO, SOURCE_VNETMAP, SOURCE_LLDP)


def normalize_topology_source(requested: Optional[str]) -> str:
    """Return ``auto``, ``vnetmap`` or ``lldp``; empty means ``auto``, unknown values warn.

    Args:
        requested: Operator-selected source (case and surrounding spaces ignored).

    Returns:
        The normalized source name.
    """
    value = str(requested or "").strip().lower()
    if not value:
        return SOURCE_AUTO
    if value not in VALID_SOURCES:
        logger.warning("Unknown port map source %r; using auto", requested)
        return SOURCE_AUTO
    return value


def select_topology_source(
    requested: str,
    has_switch_creds: bool,
    vnetmap_outcome: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    """Decide which port-map workflow to run next.

    ``vnetmap_outcome`` is ``None`` before vnetmap runs; afterwards it is the vnetmap
    "Run vnetmap.py" step result, whose ``switch_auth_failed_all`` is True only when the
    login failed on every switch.

    Truth table (``-`` = any value):

    ========= ================ ============================== =========
    requested has_switch_creds vnetmap_outcome                 result
    ========= ================ ============================== =========
    vnetmap   -                None                            vnetmap
    vnetmap   -                any dict (never auto-switches)  None
    lldp      -                -                               lldp
    auto      True             None                            vnetmap
    auto      False            None                            lldp
    auto      -                switch_auth_failed_all True     lldp
    auto      -                switch_auth_failed_all False    None
    ========= ================ ============================== =========

    ``auto`` never switches when any switch login worked: the vnetmap result stands, even
    when the run failed for another reason. Empty or unknown ``requested`` values are
    treated as ``auto`` (unknown values log a warning).

    Args:
        requested: ``auto``, ``vnetmap`` or ``lldp``.
        has_switch_creds: Whether switch credentials were provided for this run.
        vnetmap_outcome: vnetmap step result after it ran, else ``None``.

    Returns:
        ``"vnetmap"``, ``"lldp"`` or ``None`` (nothing more to run).
    """
    source = normalize_topology_source(requested)

    if source == SOURCE_LLDP:
        return SOURCE_LLDP

    if vnetmap_outcome is None:
        if source == SOURCE_VNETMAP or has_switch_creds:
            return SOURCE_VNETMAP
        return SOURCE_LLDP

    if source == SOURCE_AUTO and vnetmap_outcome.get("switch_auth_failed_all") is True:
        return SOURCE_LLDP
    return None
