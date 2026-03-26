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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "filename": self.filename,
            "path": self.path,
            "size": self.size,
            "modified": self.modified,
            "cluster_ip": self.cluster_ip,
            "file_type": self.file_type,
            "operation": self.operation,
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

        self._scan_asbuilt_reports(results["asbuilt_reports"], cluster_ip)
        self._scan_health_checks(results["health_checks"], cluster_ip)
        self._scan_network_config(results["network_config"], cluster_ip)
        self._scan_switch_config(results["switch_config"], cluster_ip)
        self._scan_vnetmap(results["vnetmap"], cluster_ip)
        self._scan_vperfsanity(results["vperfsanity"], cluster_ip)
        self._scan_support_tools(results["support_tools"], cluster_ip)
        self._scan_log_bundles(results["log_bundles"], cluster_ip)
        self._scan_bundles(results["bundles"], cluster_ip)

        for key in results:
            results[key].sort(key=lambda e: e["modified"], reverse=True)

        return results

    def get_known_clusters(self) -> List[Dict[str, Any]]:
        """Return unique cluster IPs found across all result files with counts."""
        all_results = self.scan_all()
        cluster_counts: Dict[str, Dict[str, int]] = {}

        for op_key, entries in all_results.items():
            for entry in entries:
                cip = entry.get("cluster_ip", "")
                if not cip:
                    continue
                if cip not in cluster_counts:
                    cluster_counts[cip] = {"total": 0}
                cluster_counts[cip]["total"] += 1
                cluster_counts[cip][op_key] = cluster_counts[cip].get(op_key, 0) + 1

        result = []
        for cip, counts in sorted(cluster_counts.items()):
            profile_name = self._ip_to_profile_name(cip)
            result.append({"cluster_ip": cip, "profile_name": profile_name, "counts": counts})
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

    def _scan_asbuilt_reports(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        reports_dir = self._data_dir / "reports"
        if not reports_dir.exists():
            return
        for pattern in ("vast_asbuilt_report_*.pdf", "vast_data_*.json"):
            for f in reports_dir.glob(pattern):
                cip = self._resolve_report_cluster_ip(f)
                if cluster_ip and cip != cluster_ip:
                    continue
                out.append(self._make_entry(f, cip, "asbuilt_reports"))

    def _scan_health_checks(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        health_dir = self._data_dir / "output" / "health"
        if not health_dir.exists():
            return
        for f in health_dir.glob("health_check_*.json"):
            cip = json_cluster_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "health_checks"))
        for f in health_dir.glob("health_remediation_*.txt"):
            cip = self._remediation_cluster_ip(f, health_dir)
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "health_checks"))

    def _scan_network_config(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        net_dir = self._data_dir / "output" / "scripts" / "network_configs"
        if not net_dir.exists():
            return
        ip_by_timestamp: Dict[str, str] = {}
        for f in net_dir.glob("network_summary_*.json"):
            cip = json_cluster_ip(f) or ""
            ts = extract_timestamp(f.name)
            if ts:
                ip_by_timestamp[ts] = cip
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "network_config"))
        for pattern in (
            "configure_network_commands_*.txt",
            "interface_config_*.txt",
            "routing_table_*.txt",
            "bond_config_*.txt",
        ):
            for f in net_dir.glob(pattern):
                ts = extract_timestamp(f.name)
                cip = ip_by_timestamp.get(ts, "") if ts else ""
                if not cip:
                    cip = text_header_ip(f) or ""
                if cluster_ip and cip != cluster_ip:
                    continue
                out.append(self._make_entry(f, cip, "network_config"))

    def _scan_switch_config(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        sw_dir = self._data_dir / "output" / "scripts" / "switch_configs"
        if not sw_dir.exists():
            return
        ip_by_timestamp: Dict[str, str] = {}
        for f in sw_dir.glob("switch_configs_*.json"):
            cip = json_cluster_ip(f) or ""
            ts = extract_timestamp(f.name)
            if ts:
                ip_by_timestamp[ts] = cip
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "switch_config"))
        for f in sw_dir.glob("switch_*.txt"):
            if f.name.startswith("switch_configs_"):
                continue
            ts = extract_timestamp(f.name)
            cip = ip_by_timestamp.get(ts, "") if ts else ""
            if not cip:
                cip = text_header_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "switch_config"))

    def _scan_vnetmap(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        scripts_dir = self._data_dir / "output" / "scripts"
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("vnetmap_results_*.json"):
            cip = json_cluster_ip(f) or filename_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "vnetmap"))
        for f in scripts_dir.glob("vnetmap_output_*.txt"):
            cip = filename_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "vnetmap"))

    def _scan_vperfsanity(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        scripts_dir = self._data_dir / "output" / "scripts"
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("vperfsanity_results_*.txt"):
            cip = filename_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "vperfsanity"))

    def _scan_support_tools(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        scripts_dir = self._data_dir / "output" / "scripts"
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("*support_tool_logs.tgz"):
            cip = sidecar_cluster_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "support_tools"))

    def _scan_log_bundles(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        scripts_dir = self._data_dir / "output" / "scripts"
        if not scripts_dir.exists():
            return
        for f in scripts_dir.glob("vast_log_bundle_*.tar.gz"):
            cip = verification_cluster_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "log_bundles"))

    def _scan_bundles(self, out: List[Dict[str, Any]], cluster_ip: Optional[str]) -> None:
        bundles_dir = self._data_dir / "output" / "bundles"
        if not bundles_dir.exists():
            return
        for f in bundles_dir.glob("*.zip"):
            cip = bundle_manifest_ip(f) or ""
            if cluster_ip and cip != cluster_ip:
                continue
            out.append(self._make_entry(f, cip, "bundles"))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_entry(filepath: Path, cluster_ip: str, operation: str) -> Dict[str, Any]:
        st = filepath.stat()
        return ResultEntry(
            filename=filepath.name,
            path=str(filepath),
            size=st.st_size,
            modified=datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            cluster_ip=cluster_ip,
            file_type=filepath.suffix.lstrip(".").upper() or "FILE",
            operation=operation,
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
        """Return the base directories for a given operation key."""
        mapping: Dict[str, List[Path]] = {
            "asbuilt_reports": [self._data_dir / "reports"],
            "health_checks": [self._data_dir / "output" / "health"],
            "network_config": [self._data_dir / "output" / "scripts" / "network_configs"],
            "switch_config": [self._data_dir / "output" / "scripts" / "switch_configs"],
            "vnetmap": [self._data_dir / "output" / "scripts"],
            "vperfsanity": [self._data_dir / "output" / "scripts"],
            "support_tools": [self._data_dir / "output" / "scripts"],
            "log_bundles": [self._data_dir / "output" / "scripts"],
            "bundles": [self._data_dir / "output" / "bundles"],
        }
        return mapping.get(operation, [])
