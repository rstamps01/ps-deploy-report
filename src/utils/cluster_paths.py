"""Per-cluster artifact path segmentation (QP-2).

Every cluster the tool talks to over a tech port shares the same management IP
(``192.168.2.2``), so artifacts written to the legacy flat directory tree
intermingle between clusters. This module resolves a stable, human-readable,
filesystem-safe *cluster key* from a cluster's identity and produces a
self-contained per-cluster directory tree::

    <data_dir>/clusters/<key>/
        reports/                      # PDF, vast_data_*.json, *.meta.json
        output/{scripts,health,diagrams,bundles}/
        logs/operations/
        cluster.json                  # identity marker (PSNT/GUID/name/IP/version)

The key uses the readable ``<sanitized-name>__<PSNT-or-GUID>`` form, falling
back to name-only, then the management IP, then ``unknown-cluster``. PSNT and
GUID are globally unique, so the suffix prevents collisions when two clusters
share a name or a tech-port IP.

Discovery (``ResultScanner`` / ``ResultBundler``) enumerates these per-cluster
roots first and reads legacy flat files as a backward-compatible fallback, so
existing artifacts are never orphaned.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

CLUSTERS_DIRNAME = "clusters"
CLUSTER_MARKER = "cluster.json"
UNKNOWN_KEY = "unknown-cluster"

_NAME_MAX_LEN = 48
_ID_MAX_LEN = 40
_UNSAFE_RE = re.compile(r"[^A-Za-z0-9._-]+")
_EDGE_STRIP = "-._ "


def sanitize_component(value: Optional[str], max_len: int = 64) -> str:
    """Return a filesystem-safe form of ``value`` (no separators, no traversal).

    Keeps ``[A-Za-z0-9._-]``, collapses any other run of characters to a single
    ``-``, strips leading/trailing separators, and truncates to ``max_len``.
    Returns ``""`` for ``None``/empty/all-unsafe input. Case is preserved so
    names such as ``LAMBDA-VAST-LAX-01`` stay readable.
    """
    if not value:
        return ""
    text = str(value).replace("/", "-").replace("\\", "-")
    text = _UNSAFE_RE.sub("-", text)
    text = text.strip(_EDGE_STRIP)
    if len(text) > max_len:
        text = text[:max_len].strip(_EDGE_STRIP)
    return text


def resolve_cluster_key(
    *,
    name: Optional[str] = None,
    psnt: Optional[str] = None,
    guid: Optional[str] = None,
    cluster_ip: Optional[str] = None,
) -> str:
    """Resolve a stable cluster key from available identity fields.

    Order of preference:
      1. ``<sanitized-name>__<PSNT-or-GUID>`` when a name and an id are present
      2. ``<sanitized-name>`` when only a name is present
      3. the sanitized PSNT or GUID when only an id is present
      4. the sanitized management IP as a last resort
      5. ``"unknown-cluster"`` when nothing usable is present
    """
    safe_name = sanitize_component(name, _NAME_MAX_LEN)
    safe_id = sanitize_component(psnt, _ID_MAX_LEN) or sanitize_component(guid, _ID_MAX_LEN)

    if safe_name and safe_id:
        return f"{safe_name}__{safe_id}"
    if safe_name:
        return safe_name
    if safe_id:
        return safe_id
    safe_ip = sanitize_component(cluster_ip, _ID_MAX_LEN)
    if safe_ip:
        return safe_ip
    return UNKNOWN_KEY


def resolve_cluster_key_from_summary(summary: Optional[Union[Dict[str, Any], Any]]) -> str:
    """Resolve a cluster key from a ``cluster_summary`` dict or a processed-report dict.

    Accepts either the cluster-summary mapping itself (``{name, psnt, guid}``)
    or the top-level processed-report dict (which nests it under
    ``cluster_summary`` and may carry a top-level ``cluster_ip``). Also accepts
    objects with matching attributes (e.g. ``ClusterSummary`` / ``VastClusterInfo``).
    """
    if summary is None:
        return UNKNOWN_KEY

    def _get(obj: Any, field: str) -> Optional[str]:
        if isinstance(obj, dict):
            val = obj.get(field)
        else:
            val = getattr(obj, field, None)
        return val if val in (None, "") or isinstance(val, str) else str(val)

    # If this is the top-level report dict, dig into cluster_summary for identity
    # but keep the top-level cluster_ip as the IP fallback.
    nested = None
    if isinstance(summary, dict) and "cluster_summary" in summary:
        nested = summary.get("cluster_summary") or {}
    elif not isinstance(summary, dict) and hasattr(summary, "cluster_summary"):
        nested = getattr(summary, "cluster_summary") or {}

    identity_src = nested if nested is not None else summary
    cluster_ip = _get(summary, "cluster_ip") or (_get(identity_src, "cluster_ip") if identity_src else None)

    return resolve_cluster_key(
        name=_get(identity_src, "name"),
        psnt=_get(identity_src, "psnt"),
        guid=_get(identity_src, "guid"),
        cluster_ip=cluster_ip,
    )


@dataclass(frozen=True)
class ClusterPaths:
    """Per-cluster directory tree under ``<data_dir>/clusters/<key>/``.

    Paths mirror the legacy flat layout so writers only need their base output
    directory swapped. Directories are created lazily via :meth:`ensure` /
    :meth:`ensure_all` — constructing a ``ClusterPaths`` touches no disk.
    """

    data_dir: Path
    key: str

    @property
    def root(self) -> Path:
        return Path(self.data_dir) / CLUSTERS_DIRNAME / self.key

    @property
    def reports(self) -> Path:
        return self.root / "reports"

    @property
    def output(self) -> Path:
        return self.root / "output"

    @property
    def scripts(self) -> Path:
        return self.output / "scripts"

    @property
    def network_configs(self) -> Path:
        return self.scripts / "network_configs"

    @property
    def switch_configs(self) -> Path:
        return self.scripts / "switch_configs"

    @property
    def health(self) -> Path:
        return self.output / "health"

    @property
    def diagrams(self) -> Path:
        return self.output / "diagrams"

    @property
    def bundles(self) -> Path:
        return self.output / "bundles"

    @property
    def ops_logs(self) -> Path:
        return self.root / "logs" / "operations"

    @property
    def marker(self) -> Path:
        return self.root / CLUSTER_MARKER

    def ensure(self, *names: str) -> List[Path]:
        """Create and return the named category dirs (e.g. ``ensure("reports")``)."""
        created: List[Path] = []
        for name in names:
            d = getattr(self, name)
            d.mkdir(parents=True, exist_ok=True)
            created.append(d)
        return created

    def ensure_all(self) -> List[Path]:
        """Create the full per-cluster tree and return all created dirs."""
        return self.ensure(
            "reports",
            "scripts",
            "network_configs",
            "switch_configs",
            "health",
            "diagrams",
            "bundles",
            "ops_logs",
        )


def cluster_paths(data_dir: Union[str, Path], key: str) -> ClusterPaths:
    """Build a :class:`ClusterPaths` for ``key`` under ``data_dir``."""
    return ClusterPaths(Path(data_dir), key)


def iter_cluster_roots(data_dir: Union[str, Path]) -> List[Path]:
    """Return the per-cluster root directories under ``<data_dir>/clusters/``.

    Only directories are returned (stray files are ignored). Returns an empty
    list when no ``clusters/`` directory exists.
    """
    clusters_dir = Path(data_dir) / CLUSTERS_DIRNAME
    if not clusters_dir.is_dir():
        return []
    return sorted((p for p in clusters_dir.iterdir() if p.is_dir()), key=lambda p: p.name)


def write_cluster_marker(root: Union[str, Path], identity: Dict[str, Any]) -> Path:
    """Write/update the ``cluster.json`` identity marker in ``root``.

    Preserves ``first_seen`` across updates and refreshes ``last_seen``. The
    marker captures PSNT/GUID/name/IP/version so a folder is self-describing
    even when its key is just a sanitized IP.
    """
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    marker_path = root / CLUSTER_MARKER

    existing = read_cluster_marker(root)
    now = datetime.now(timezone.utc).isoformat()
    merged: Dict[str, Any] = {}
    merged.update(existing)
    merged.update({k: v for k, v in (identity or {}).items() if v not in (None, "")})
    merged["first_seen"] = existing.get("first_seen", now)
    merged["last_seen"] = now

    try:
        marker_path.write_text(json.dumps(merged, indent=2, default=str), encoding="utf-8")
    except OSError:
        pass
    return marker_path


def read_cluster_marker(root: Union[str, Path]) -> Dict[str, Any]:
    """Read the ``cluster.json`` marker from ``root``; ``{}`` if missing/corrupt."""
    marker_path = Path(root) / CLUSTER_MARKER
    if not marker_path.is_file():
        return {}
    try:
        data = json.loads(marker_path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def segment_enabled(config: Optional[Any]) -> bool:
    """Return whether per-cluster segmentation is enabled (default ``True``).

    Reads ``output.segment_by_cluster`` from either a dict-shaped config or an
    object with an ``output`` attribute. Missing config or missing key defaults
    to enabled.
    """
    if config is None:
        return True
    output: Any = None
    if isinstance(config, dict):
        output = config.get("output")
    else:
        output = getattr(config, "output", None)
    if output is None:
        return True
    if isinstance(output, dict):
        val = output.get("segment_by_cluster", True)
    else:
        val = getattr(output, "segment_by_cluster", True)
    return bool(val) if val is not None else True
