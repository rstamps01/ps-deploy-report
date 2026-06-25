"""
Result Scanner Module

Scans all output directories and returns structured result metadata grouped
by operation type and tagged with cluster_ip.  Used by the Validation Results
page and the ResultBundler to provide cluster-aware result browsing and
bundle creation.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.cluster_paths import cluster_paths, iter_cluster_roots, read_cluster_marker
from utils.logger import get_logger

logger = get_logger(__name__)

_IP_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})")
_TIMESTAMP_RE = re.compile(r"(\d{8}_\d{6})")


# ------------------------------------------------------------------
# Shared cluster-matching helpers (also used by ResultBundler)
# ------------------------------------------------------------------


def json_cluster_ip(filepath: Path) -> Optional[str]:
    """Extract ``cluster_ip`` from a JSON file, or *None*."""
    try:
        data = json.loads(filepath.read_text(encoding="utf-8"))
        ip = data.get("cluster_ip")
        return ip if isinstance(ip, str) and ip.strip() else None
    except Exception:
        return None


def json_matches_cluster(filepath: Path, cluster_ip: str) -> bool:
    return json_cluster_ip(filepath) == cluster_ip


def text_header_ip(filepath: Path) -> Optional[str]:
    """Return the first IP address found in the first 10 lines of a text file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for _, line in zip(range(10), f):
                m = _IP_RE.search(line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None


def text_header_matches(filepath: Path, cluster_ip: str) -> bool:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            for _, line in zip(range(10), f):
                if cluster_ip in line:
                    return True
    except Exception:
        pass
    return False


def filename_ip(filepath: Path) -> Optional[str]:
    """Extract an IP address embedded in a filename (dots or underscores)."""
    name = filepath.stem
    m = _IP_RE.search(name)
    if m:
        return m.group(1)
    parts = re.findall(r"(\d{1,3}_\d{1,3}_\d{1,3}_\d{1,3})", name)
    if parts:
        return str(parts[0]).replace("_", ".")
    return None


def filename_matches(filepath: Path, cluster_ip: str) -> bool:
    name = filepath.name
    return cluster_ip in name or cluster_ip.replace(".", "_") in name


def sidecar_cluster_ip(archive_path: Path) -> Optional[str]:
    """Read cluster_ip from a ``.meta.json`` sidecar next to *archive_path*."""
    meta = archive_path.parent / f"{archive_path.name}.meta.json"
    if meta.exists():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            ip = data.get("cluster_ip")
            return ip if isinstance(ip, str) and ip.strip() else None
        except Exception:
            pass
    return None


def verification_cluster_ip(archive_path: Path) -> Optional[str]:
    """Read cluster_ip from a ``.verification.json`` sidecar."""
    verify = archive_path.with_suffix(".verification.json")
    if not verify.exists():
        stem = archive_path.stem
        if stem.endswith(".tar"):
            verify = archive_path.parent / (stem + ".verification.json")
    if verify.exists():
        try:
            data = json.loads(verify.read_text(encoding="utf-8"))
            ip = data.get("cluster_ip")
            return ip if isinstance(ip, str) and ip.strip() else None
        except Exception:
            pass
    return None


def extract_timestamp(filename: str) -> Optional[str]:
    """Extract ``YYYYMMDD_HHMMSS`` timestamp from a filename."""
    m = _TIMESTAMP_RE.search(filename)
    return m.group(1) if m else None


def bundle_manifest_ip(zip_path: Path) -> Optional[str]:
    """Read cluster_ip from the manifest.json inside a ZIP bundle."""
    import zipfile

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if "manifest.json" in zf.namelist():
                manifest = json.loads(zf.read("manifest.json"))
                meta = manifest.get("metadata", {})
                ip = meta.get("cluster_ip")
                return ip if isinstance(ip, str) and ip.strip() else None
    except Exception:
        pass
    return None


# ------------------------------------------------------------------
# Result entry
# ------------------------------------------------------------------


@dataclass
class ResultEntry:
    """Metadata for a single result file on disk."""

    filename: str
    path: str
    size: int
    modified: str
    cluster_ip: str
    file_type: str
    operation: str
    # QP-2: folder-unique identity for a per-cluster artifact (the
    # ``clusters/<key>/`` folder name). Empty for legacy-flat files. This is
    # what association/de-dup keys on so two tech-port folders that share the
    # marker ``cluster_ip`` (192.168.2.2) never collapse into one cluster.
    cluster_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "path": self.path,
            "size": self.size,
            "modified": self.modified,
            "cluster_ip": self.cluster_ip,
            "file_type": self.file_type,
            "operation": self.operation,
            "cluster_key": self.cluster_key,
        }


# ------------------------------------------------------------------
# Scanner
# ------------------------------------------------------------------

OPERATION_KEYS = [
    "asbuilt_reports",
    "health_checks",
    "network_config",
    "switch_config",
    "vnetmap",
    "vperfsanity",
    "support_tools",
    "log_bundles",
    "bundles",
]

OPERATION_LABELS = {
    "asbuilt_reports": "As-Built Reports",
    "health_checks": "Health Checks",
    "network_config": "Network Configuration",
    "switch_config": "Switch Configuration",
    "vnetmap": "vnetmap Topology",
    "vperfsanity": "vperfsanity Performance",
    "support_tools": "Support Tools",
    "log_bundles": "Log Bundles",
    "bundles": "Validation Bundles",
}


@dataclass
class _ScanScope:
    """A set of category directories to scan, plus an optional identity override.

    A *scope* is either the legacy flat tree (``cluster_ip_override`` and
    ``cluster_key`` are ``None``, so per-file IP heuristics decide the cluster)
    or a single per-cluster root under ``<data_dir>/clusters/<key>/``.

    For a per-cluster scope ``cluster_key`` is the folder name — the
    folder-unique identity used for association/de-dup — and
    ``cluster_ip_override`` carries the marker's ``cluster_ip`` purely for
    display. Under tech-port mode that IP is the shared ``192.168.2.2`` for
    every cluster, so it is NOT a distinguishing identity; only ``cluster_key``
    separates the folders.
    """

    reports: Path
    health: Path
    network_configs: Path
    switch_configs: Path
    scripts: Path
    bundles: Path
    cluster_ip_override: Optional[str] = None
    cluster_key: Optional[str] = None


class ResultScanner:
    """Scans output directories for operation results tagged by cluster."""

    def __init__(self, data_dir: Optional[Path] = None, profiles: Optional[Dict[str, Any]] = None):
        if data_dir is None:
            from utils import get_data_dir

            data_dir = get_data_dir()
        self._data_dir = data_dir
        self._profiles = profiles or {}
        self._cluster_name_to_ip: Dict[str, str] = {}
        for _name, p in self._profiles.items():
            cip = p.get("cluster_ip", "")
            if cip:
                self._cluster_name_to_ip[_name.lower()] = cip

        reports_dir = self._data_dir / "reports"
        if reports_dir.exists():
            for jf in reports_dir.glob("vast_data_*.json"):
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    api_name = data.get("cluster_summary", {}).get("name", "")
                    cip = data.get("cluster_ip", "")
                    if api_name and cip:
                        self._cluster_name_to_ip[api_name.lower()] = cip
                except Exception:
                    pass

    def scan_all(self, cluster_ip: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """Return all results grouped by operation key.

        When *cluster_ip* is given, only results matching that cluster are
        returned.  Each value is a list of ``ResultEntry.to_dict()`` dicts
        sorted newest-first.
        """
        results: Dict[str, List[Dict[str, Any]]] = {k: [] for k in OPERATION_KEYS}

        # Folder-scoped first (per-cluster roots), legacy flat second. Segmented
        # and legacy artifacts live in different paths, so the union never
        # double-counts a file.
        for scope in self._build_scopes():
            self._scan_asbuilt_reports(results["asbuilt_reports"], cluster_ip, scope)
            self._scan_health_checks(results["health_checks"], cluster_ip, scope)
            self._scan_network_config(results["network_config"], cluster_ip, scope)
            self._scan_switch_config(results["switch_config"], cluster_ip, scope)
            self._scan_vnetmap(results["vnetmap"], cluster_ip, scope)
            self._scan_vperfsanity(results["vperfsanity"], cluster_ip, scope)
            self._scan_support_tools(results["support_tools"], cluster_ip, scope)
            self._scan_log_bundles(results["log_bundles"], cluster_ip, scope)
            self._scan_bundles(results["bundles"], cluster_ip, scope)

        for key in results:
            results[key].sort(key=lambda e: e["modified"], reverse=True)

        return results

    def _legacy_scope(self) -> _ScanScope:
        """The legacy flat directory tree under ``<data_dir>``."""
        scripts = self._data_dir / "output" / "scripts"
        return _ScanScope(
            reports=self._data_dir / "reports",
            health=self._data_dir / "output" / "health",
            network_configs=scripts / "network_configs",
            switch_configs=scripts / "switch_configs",
            scripts=scripts,
            bundles=self._data_dir / "output" / "bundles",
            cluster_ip_override=None,
        )

    def _build_scopes(self) -> List[_ScanScope]:
        """Return per-cluster scopes (folder-scoped) plus the legacy flat scope."""
        scopes: List[_ScanScope] = []
        for root in iter_cluster_roots(self._data_dir):
            marker = read_cluster_marker(root)
            override = marker.get("cluster_ip")
            override = override if isinstance(override, str) and override.strip() else None
            cp = cluster_paths(self._data_dir, root.name)
            scopes.append(
                _ScanScope(
                    reports=cp.reports,
                    health=cp.health,
                    network_configs=cp.network_configs,
                    switch_configs=cp.switch_configs,
                    scripts=cp.scripts,
                    bundles=cp.bundles,
                    cluster_ip_override=override,
                    cluster_key=root.name,
                )
            )
        scopes.append(self._legacy_scope())
        return scopes

    def get_known_clusters(self) -> List[Dict[str, Any]]:
        """Return distinct clusters found across all result files with counts.

        Clusters are de-duplicated by their folder-unique identity
        (``cluster_key`` for per-cluster folders, falling back to ``cluster_ip``
        for legacy-flat files) — NEVER by ``cluster_ip`` alone. Two tech-port
        folders that share the marker IP ``192.168.2.2`` therefore surface as
        TWO clusters, each carrying its own ``cluster_key``.
        """
        all_results = self.scan_all()
        clusters: Dict[str, Dict[str, Any]] = {}

        for op_key, entries in all_results.items():
            for entry in entries:
                key = entry.get("cluster_key") or ""
                cip = entry.get("cluster_ip", "")
                identity = key or cip
                if not identity:
                    continue
                if identity not in clusters:
                    clusters[identity] = {"cluster_ip": cip, "cluster_key": key, "counts": {"total": 0}}
                bucket = clusters[identity]["counts"]
                bucket["total"] += 1
                bucket[op_key] = bucket.get(op_key, 0) + 1

        result = []
        for _identity, info in sorted(clusters.items()):
            cip = info["cluster_ip"]
            profile_name = self._ip_to_profile_name(cip)
            result.append(
                {
                    "cluster_ip": cip,
                    "cluster_key": info["cluster_key"],
                    "profile_name": profile_name,
                    "counts": info["counts"],
                }
            )
        return result

    def resolve_file_path(self, operation: str, filename: str) -> Optional[Path]:
        """Resolve an operation + filename to an absolute path with safety checks."""
        base_dirs = self._operation_base_dirs(operation)
        for base in base_dirs:
            candidate = (base / filename).resolve()
            if candidate.exists() and str(candidate).startswith(str(base.resolve())):
                return candidate
        return None

    # ------------------------------------------------------------------
    # Per-operation scanners
    # ------------------------------------------------------------------

    def _scan_asbuilt_reports(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        reports_dir = scope.reports
        if not reports_dir.exists():
            return
        for pattern in ("vast_asbuilt_report_*.pdf", "vast_data_*.json"):
            for f in reports_dir.glob(pattern):
                cip = scope.cluster_ip_override or self._resolve_report_cluster_ip(f)
                if cluster_ip and cip != cluster_ip:
                    continue
                out.append(self._make_entry(f, cip, "asbuilt_reports", scope.cluster_key or ""))

    def _scan_health_checks(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        health_dir = scope.health
        if not health_dir.exists():
            return
        for f in health_dir.glob("health_check_*.json"):
            cip = scope.cluster_ip_override or json_cluster_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "health_checks", scope.cluster_key or ""))
        for f in health_dir.glob("health_remediation_*.txt"):
            cip = scope.cluster_ip_override or self._remediation_cluster_ip(f, health_dir)
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "health_checks", scope.cluster_key or ""))

    def _scan_network_config(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        net_dir = scope.network_configs
        if not net_dir.exists():
            return
        ip_by_timestamp: Dict[str, str] = {}
        for f in net_dir.glob("network_summary_*.json"):
            cip = scope.cluster_ip_override or json_cluster_ip(f) or ""
            ts = extract_timestamp(f.name)
            if ts:
                ip_by_timestamp[ts] = cip
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "network_config", scope.cluster_key or ""))
        for pattern in (
            "configure_network_commands_*.txt",
            "interface_config_*.txt",
            "routing_table_*.txt",
            "bond_config_*.txt",
        ):
            for f in net_dir.glob(pattern):
                ts = extract_timestamp(f.name)
                cip = scope.cluster_ip_override or (ip_by_timestamp.get(ts, "") if ts else "")
                if not cip:
                    cip = text_header_ip(f) or ""
                if cluster_ip and cip != cluster_ip:
                    continue
                out.append(self._make_entry(f, cip, "network_config", scope.cluster_key or ""))

    def _scan_switch_config(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        sw_dir = scope.switch_configs
        if not sw_dir.exists():
            return
        ip_by_timestamp: Dict[str, str] = {}
        for f in sw_dir.glob("switch_configs_*.json"):
            cip = scope.cluster_ip_override or json_cluster_ip(f) or ""
            ts = extract_timestamp(f.name)
            if ts:
                ip_by_timestamp[ts] = cip
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "switch_config", scope.cluster_key or ""))
        for f in sw_dir.glob("switch_*.txt"):
            if f.name.startswith("switch_configs_"):
                continue
            ts = extract_timestamp(f.name)
            cip = scope.cluster_ip_override or (ip_by_timestamp.get(ts, "") if ts else "")
            if not cip:
                cip = text_header_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "switch_config", scope.cluster_key or ""))

    def _scan_vnetmap(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        scripts_dir = scope.scripts
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("vnetmap_results_*.json"):
            cip = scope.cluster_ip_override or json_cluster_ip(f) or filename_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "vnetmap", scope.cluster_key or ""))
        for f in scripts_dir.glob("vnetmap_output_*.txt"):
            cip = scope.cluster_ip_override or filename_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "vnetmap", scope.cluster_key or ""))

    def _scan_vperfsanity(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        scripts_dir = scope.scripts
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("vperfsanity_results_*.txt"):
            cip = scope.cluster_ip_override or filename_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "vperfsanity", scope.cluster_key or ""))

    def _scan_support_tools(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        scripts_dir = scope.scripts
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("*support_tool_logs*.tgz"):
            cip = scope.cluster_ip_override or sidecar_cluster_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "support_tools", scope.cluster_key or ""))

    def _scan_log_bundles(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        scripts_dir = scope.scripts
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("vast_log_bundle_*.tar.gz"):
            cip = scope.cluster_ip_override or verification_cluster_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "log_bundles", scope.cluster_key or ""))

    def _scan_bundles(self, out: List[Dict[str, Any]], cluster_ip: Optional[str], scope: _ScanScope) -> None:
        bundles_dir = scope.bundles
        if not bundles_dir.exists():
            return
        for f in bundles_dir.glob("*.zip"):
            cip = scope.cluster_ip_override or bundle_manifest_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "bundles", scope.cluster_key or ""))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_entry(filepath: Path, cluster_ip: str, operation: str, cluster_key: str = "") -> Dict[str, Any]:
        st = filepath.stat()
        return ResultEntry(
            filename=filepath.name,
            path=str(filepath),
            size=st.st_size,
            modified=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            cluster_ip=cluster_ip,
            file_type=filepath.suffix.lstrip(".").upper() or "FILE",
            operation=operation,
            cluster_key=cluster_key,
        ).to_dict()

    def _resolve_report_cluster_ip(self, filepath: Path) -> str:
        """Resolve cluster_ip for an As-Built report from its filename.

        Filename pattern: ``vast_asbuilt_report_{cluster_name}_{timestamp}.pdf``
        or ``vast_data_{cluster_name}_{timestamp}.json``.

        If cluster_name matches a saved profile, use that profile's cluster_ip.
        If the file is JSON, try to extract cluster_ip from the content.
        """
        if filepath.suffix == ".json":
            cip = json_cluster_ip(filepath)
            if cip:
                return cip

        meta_path = filepath.parent / (filepath.stem + ".meta.json")
        if meta_path.exists():
            cip = json_cluster_ip(meta_path)
            if cip:
                return cip

        name = filepath.stem
        for prefix in ("vast_asbuilt_report_", "vast_data_"):
            if name.startswith(prefix):
                rest = name[len(prefix) :]
                ts = extract_timestamp(rest)
                if ts:
                    cluster_name = rest[: rest.rfind(ts)].rstrip("_")
                else:
                    cluster_name = rest
                if cluster_name:
                    cip = self._cluster_name_to_ip.get(cluster_name.lower(), "")
                    if cip:
                        return cip
        return ""

    def _remediation_cluster_ip(self, filepath: Path, health_dir: Path) -> str:
        """Match a health_remediation file to a cluster via paired JSON."""
        ts = extract_timestamp(filepath.name)
        if ts:
            for jf in health_dir.glob(f"health_check_*{ts}.json"):
                cip = json_cluster_ip(jf)
                if cip:
                    return cip
        return text_header_ip(filepath) or ""

    def _ip_to_profile_name(self, cluster_ip: str) -> str:
        for name, p in self._profiles.items():
            if p.get("cluster_ip") == cluster_ip:
                return name
        return ""

    def _operation_base_dirs(self, operation: str) -> List[Path]:
        """Return the base directories for a given operation key.

        Includes every per-cluster root's category dir plus the legacy flat
        dir so files segmented under ``clusters/<key>/`` are resolvable too.
        """
        dirs: List[Path] = []
        for scope in self._build_scopes():
            mapping: Dict[str, Path] = {
                "asbuilt_reports": scope.reports,
                "health_checks": scope.health,
                "network_config": scope.network_configs,
                "switch_config": scope.switch_configs,
                "vnetmap": scope.scripts,
                "vperfsanity": scope.scripts,
                "support_tools": scope.scripts,
                "log_bundles": scope.scripts,
                "bundles": scope.bundles,
            }
            base = mapping.get(operation)
            if base is not None:
                dirs.append(base)
        return dirs
