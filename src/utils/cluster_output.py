"""Write-side helpers for QP-2 per-cluster artifact segmentation.

These thin helpers sit on top of the fully-tested foundation in
:mod:`utils.cluster_paths` and centralize the small amount of logic the
report/health/one-shot writers share: deciding whether segmentation is on,
resolving the per-cluster :class:`~utils.cluster_paths.ClusterPaths`, and
building the ``cluster.json`` identity marker payload.

Keeping this in one place ensures every writer produces the same directory
layout and the same marker fields, so the read side (``ResultScanner`` /
``ResultBundler``) can rely on a single contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Union

from utils.cluster_paths import (
    ClusterPaths,
    cluster_paths,
    resolve_cluster_key_from_summary,
    segment_enabled,
)


def cluster_paths_if_enabled(
    config: Optional[Any],
    identity_source: Optional[Union[Dict[str, Any], Any]],
    data_dir: Optional[Union[str, Path]] = None,
) -> Optional[ClusterPaths]:
    """Return a :class:`ClusterPaths` when segmentation is enabled, else ``None``.

    ``identity_source`` may be a ``cluster_summary`` dict, the top-level
    processed-report dict, or an object with those attributes — anything
    accepted by :func:`resolve_cluster_key_from_summary`. ``data_dir`` defaults
    to the runtime data directory.
    """
    if not segment_enabled(config):
        return None
    if data_dir is None:
        from utils import get_data_dir

        data_dir = get_data_dir()
    key = resolve_cluster_key_from_summary(identity_source)
    return cluster_paths(data_dir, key)


def build_marker_identity(
    processed_data: Optional[Dict[str, Any]],
    *,
    cluster_ip: Optional[str] = None,
    version: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the ``cluster.json`` identity payload from processed report data.

    Pulls ``name``/``psnt``/``guid`` from ``cluster_summary`` and falls back to
    the top-level ``cluster_ip`` when no explicit IP is supplied. Empty values
    are dropped by :func:`utils.cluster_paths.write_cluster_marker`.
    """
    data = processed_data if isinstance(processed_data, dict) else {}
    summary = data.get("cluster_summary") or {}
    if not isinstance(summary, dict):
        summary = {}
    return {
        "name": summary.get("name"),
        "psnt": summary.get("psnt"),
        "guid": summary.get("guid"),
        "cluster_ip": cluster_ip or data.get("cluster_ip"),
        "version": version,
    }
