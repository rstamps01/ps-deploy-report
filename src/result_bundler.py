"""
Result Bundler Module

Creates downloadable validation packages containing all workflow outputs,
health check results, and configuration extracts.

Files are scoped to the selected cluster by matching the cluster_ip from
the user's profile against metadata embedded in output files (JSON fields,
text-file headers, or filename-embedded IPs).
"""

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class ResultBundler:
    """Bundles validation results into downloadable ZIP archives."""

    BUNDLE_MANIFEST_VERSION = "1.0"

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ):
        if output_dir is None:
            from utils import get_data_dir

            output_dir = get_data_dir() / "output" / "bundles"
        self._output_dir = output_dir
        self._output_callback = output_callback
        self._collected_files: Dict[str, Path] = {}
        self._metadata: Dict[str, Any] = {}

    def emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        """Emit output message via callback."""
        if self._output_callback:
            try:
                self._output_callback(level, message, details)
            except Exception:
                pass
        logger.info(f"[{level}] {message}")

    def set_metadata(self, cluster_name: str, cluster_ip: str, cluster_version: str) -> None:
        """Set cluster metadata for the bundle.

        If *cluster_name* looks like an IP or is unknown, attempt to
        resolve the real API cluster name from existing report JSON files.
        """
        resolved_name = cluster_name
        if cluster_ip and (not cluster_name or cluster_name == "Unknown" or cluster_name == cluster_ip):
            resolved_name = self._resolve_cluster_name(cluster_ip) or cluster_ip
        self._metadata = {
            "cluster_name": resolved_name,
            "cluster_ip": cluster_ip,
            "cluster_version": cluster_version,
            "bundle_created": datetime.now().isoformat(),
            "manifest_version": self.BUNDLE_MANIFEST_VERSION,
        }

    @staticmethod
    def _resolve_cluster_name(cluster_ip: str) -> Optional[str]:
        """Scan report JSON files for the real API cluster name matching *cluster_ip*."""
        try:
            from utils import get_data_dir

            reports_dir = get_data_dir() / "reports"
            if not reports_dir.exists():
                return None
            for jf in sorted(reports_dir.glob("vast_data_*.json"), reverse=True):
                try:
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    if data.get("cluster_ip") == cluster_ip:
                        name = data.get("cluster_summary", {}).get("name")
                        if name and name != "unknown":
                            return str(name)
                except Exception:
                    continue
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Cluster-identity helpers  (delegates to result_scanner functions)
    # ------------------------------------------------------------------

    @staticmethod
    def _json_has_cluster_ip(filepath: Path, cluster_ip: str) -> bool:
        from result_scanner import json_matches_cluster

        return bool(json_matches_cluster(filepath, cluster_ip))

    @staticmethod
    def _text_header_has_ip(filepath: Path, cluster_ip: str) -> bool:
        from result_scanner import text_header_matches

        return bool(text_header_matches(filepath, cluster_ip))

    @staticmethod
    def _filename_has_ip(filepath: Path, cluster_ip: str) -> bool:
        from result_scanner import filename_matches

        return bool(filename_matches(filepath, cluster_ip))

    @staticmethod
    def _sidecar_matches(filepath: Path, cluster_ip: str) -> bool:
        from result_scanner import sidecar_cluster_ip

        return bool(sidecar_cluster_ip(filepath) == cluster_ip)

    @staticmethod
    def _verification_matches(filepath: Path, cluster_ip: str) -> bool:
        from result_scanner import verification_cluster_ip

        return bool(verification_cluster_ip(filepath) == cluster_ip)

    def _pick_latest(
        self,
        candidates: List[Path],
        cluster_ip: Optional[str],
        match_fn,
    ) -> Optional[Path]:
        """Return the most recent file that passes *match_fn*, or None."""
        for f in sorted(candidates, reverse=True):
            if cluster_ip is None or match_fn(f, cluster_ip):
                return f
        return None

    # ------------------------------------------------------------------

    ALL_CATEGORIES = [
        "health_check",
        "health_remediation",
        "network_config",
        "network_commands",
        "network_interfaces",
        "network_routing",
        "network_bonds",
        "switch_config",
        "vnetmap",
        "vnetmap_output",
        "vperfsanity",
        "support_tools",
        "log_bundle",
        "asbuilt_report",
        "asbuilt_json",
    ]

    def collect_results(
        self,
        results_dir: Optional[Path] = None,
        cluster_ip: Optional[str] = None,
    ) -> Dict[str, Path]:
        """Collect validation result files scoped to *cluster_ip*.

        For each category the most recent matching file is selected.
        When *cluster_ip* is ``None`` the latest file regardless of cluster
        is chosen.
        """
        if cluster_ip:
            self.emit("info", f"Collecting results for cluster {cluster_ip}...")
        else:
            self.emit("info", "Collecting validation results (all clusters)...")

        if results_dir is None:
            from utils import get_data_dir

            results_dir = get_data_dir() / "output"
        collected: Dict[str, Path] = {}

        scripts_dir = results_dir / "scripts"

        # -- Health check results --
        health_dir = results_dir / "health"
        if health_dir.exists():
            hit = self._pick_latest(
                list(health_dir.glob("health_check_*.json")),
                cluster_ip,
                self._json_has_cluster_ip,
            )
            if hit:
                collected["health_check"] = hit
                self.emit("success", f"Found health check: {hit.name}")

            # Health remediation text (paired by timestamp with the JSON)
            hit_rem = self._pick_latest(
                list(health_dir.glob("health_remediation_*.txt")),
                cluster_ip,
                self._text_header_has_ip,
            )
            if hit_rem:
                collected["health_remediation"] = hit_rem
                self.emit("success", f"Found health remediation: {hit_rem.name}")

        # -- Network configurations --
        network_dir = scripts_dir / "network_configs"
        if network_dir.exists():
            hit = self._pick_latest(
                list(network_dir.glob("network_summary_*.json")),
                cluster_ip,
                self._json_has_cluster_ip,
            )
            if hit:
                collected["network_config"] = hit
                self.emit("success", f"Found network config: {hit.name}")

                timestamp = self._extract_timestamp(hit.name)
                if timestamp:
                    self._collect_network_text_files(network_dir, timestamp, collected)

        # -- Switch configurations --
        switch_dir = scripts_dir / "switch_configs"
        if switch_dir.exists():
            hit = self._pick_latest(
                list(switch_dir.glob("switch_configs_*.json")),
                cluster_ip,
                self._json_has_cluster_ip,
            )
            if hit:
                collected["switch_config"] = hit
                self.emit("success", f"Found switch config: {hit.name}")

                timestamp = self._extract_timestamp(hit.name)
                if timestamp:
                    for idx, txt in enumerate(sorted(switch_dir.glob(f"switch_*_{timestamp}.txt"))):
                        key = "switch_config_txt" if idx == 0 else f"switch_config_txt_{idx}"
                        collected[key] = txt
                        self.emit("success", f"Found switch backup: {txt.name}")

        # -- vnetmap results --
        if scripts_dir.exists():
            hit = self._pick_latest(
                list(scripts_dir.glob("vnetmap_results_*.json")),
                cluster_ip,
                lambda f, ip: self._json_has_cluster_ip(f, ip) or self._filename_has_ip(f, ip),
            )
            if hit:
                collected["vnetmap"] = hit
                self.emit("success", f"Found vnetmap results: {hit.name}")

            # vnetmap output text
            hit_out = self._pick_latest(
                list(scripts_dir.glob("vnetmap_output_*.txt")),
                cluster_ip,
                self._filename_has_ip,
            )
            if hit_out:
                collected["vnetmap_output"] = hit_out
                self.emit("success", f"Found vnetmap output: {hit_out.name}")

        # -- vperfsanity results --
        if scripts_dir.exists():
            hit = self._pick_latest(
                list(scripts_dir.glob("vperfsanity_results_*.txt")),
                cluster_ip,
                self._filename_has_ip,
            )
            if hit:
                collected["vperfsanity"] = hit
                self.emit("success", f"Found vperfsanity results: {hit.name}")

        # -- Support tool archives (via sidecar .meta.json or text header) --
        if scripts_dir.exists():
            hit = self._pick_latest(
                list(scripts_dir.glob("*support_tool_logs*.tgz")),
                cluster_ip,
                lambda f, ip: self._sidecar_matches(f, ip) or self._text_header_has_ip(f, ip),
            )
            if hit:
                collected["support_tools"] = hit
                self.emit("success", f"Found support tools archive: {hit.name}")

        # -- Log bundles (via verification JSON cluster_ip) --
        if scripts_dir.exists():
            hit = self._pick_latest(
                list(scripts_dir.glob("vast_log_bundle_*.tar.gz")),
                cluster_ip,
                self._verification_matches,
            )
            if hit:
                collected["log_bundle"] = hit
                self.emit("success", f"Found log bundle: {hit.name}")

        # -- Report PDFs (filter by sidecar cluster_ip, JSON cluster_ip, or cluster_name in filename) --
        from utils import get_data_dir as _gdd

        reports_dir = _gdd() / "reports"
        if reports_dir.exists():
            hit = self._pick_latest(
                list(reports_dir.glob("vast_asbuilt_report_*.pdf")),
                cluster_ip,
                lambda f, ip: (self._sidecar_matches(f, ip) or self._filename_has_ip(f, ip)),
            )
            if hit is None:
                cluster_name = self._metadata.get("cluster_name", "")
                if cluster_name and cluster_name != "Unknown":
                    hit = self._pick_latest(
                        list(reports_dir.glob("vast_asbuilt_report_*.pdf")),
                        cluster_name,
                        lambda f, cn: cn.lower() in f.name.lower(),
                    )
            if hit:
                collected["asbuilt_report"] = hit
                self.emit("success", f"Found As-Built report: {hit.name}")

            # Companion JSON data file (paired by matching stem timestamp)
            json_hit = self._pick_latest(
                list(reports_dir.glob("vast_data_*.json")),
                cluster_ip,
                self._json_has_cluster_ip,
            )
            if json_hit:
                collected["asbuilt_json"] = json_hit
                self.emit("success", f"Found As-Built JSON: {json_hit.name}")

        self._collected_files = collected
        self.emit("info", f"Collected {len(collected)} result files for bundle")
        return collected

    @staticmethod
    def _extract_timestamp(filename: str) -> Optional[str]:
        """Extract ``YYYYMMDD_HHMMSS`` timestamp from a filename."""
        m = re.search(r"(\d{8}_\d{6})", filename)
        return m.group(1) if m else None

    def _collect_network_text_files(
        self,
        network_dir: Path,
        timestamp: str,
        collected: Dict[str, Path],
    ) -> None:
        """Add the network text files that share the same extraction timestamp."""
        patterns = {
            "network_commands": f"configure_network_commands_*_{timestamp}.txt",
            "network_interfaces": f"interface_config_*_{timestamp}.txt",
            "network_routing": f"routing_table_*_{timestamp}.txt",
            "network_bonds": f"bond_config_*_{timestamp}.txt",
        }
        for category, pattern in patterns.items():
            for f in network_dir.glob(pattern):
                collected[category] = f
                self.emit("success", f"Found {category}: {f.name}")
                break

    def generate_summary(self) -> str:
        """Generate a markdown summary of collected results."""
        lines = [
            "# Validation Results Summary",
            "",
            f"**Cluster:** {self._metadata.get('cluster_name', 'Unknown')}",
            f"**IP:** {self._metadata.get('cluster_ip', 'Unknown')}",
            f"**Version:** {self._metadata.get('cluster_version', 'Unknown')}",
            f"**Bundle Created:** {self._metadata.get('bundle_created', 'Unknown')}",
            "",
            "## Included Files",
            "",
        ]

        category_names = {
            "health_check": "Health Check Results",
            "health_remediation": "Health Remediation Report",
            "network_config": "Network Configuration Summary",
            "network_commands": "Network Commands History",
            "network_interfaces": "Interface Configuration",
            "network_routing": "Routing Table",
            "network_bonds": "Bond Configuration",
            "switch_config": "Switch Configuration (JSON)",
            "switch_config_txt": "Switch Configuration (Text)",
            "vnetmap": "vnetmap Topology Validation",
            "vnetmap_output": "vnetmap Raw Output",
            "support_tools": "VAST Support Tools Output",
            "vperfsanity": "vperfsanity Performance Results",
            "log_bundle": "VMS Log Bundle",
            "asbuilt_report": "As-Built Report PDF",
            "asbuilt_json": "As-Built Report Data (JSON)",
        }

        for category, filepath in self._collected_files.items():
            name = category_names.get(category, category)
            lines.append(f"- **{name}**: `{filepath.name}`")

        lines.extend(
            [
                "",
                "## Validation Status",
                "",
            ]
        )

        # Parse health check for summary if available
        health_file = self._collected_files.get("health_check")
        if health_file and health_file.exists():
            try:
                health_data = json.loads(health_file.read_text())
                summary = health_data.get("summary", {})
                lines.append("### Health Check Summary")
                lines.append("")
                lines.append(f"- Pass: {summary.get('pass', 0)}")
                lines.append(f"- Fail: {summary.get('fail', 0)}")
                lines.append(f"- Warning: {summary.get('warning', 0)}")
                lines.append(f"- Skipped: {summary.get('skipped', 0)}")
                lines.append(f"- Error: {summary.get('error', 0)}")
                lines.append("")
            except Exception as e:
                logger.warning(f"Could not parse health check: {e}")

        lines.extend(
            [
                "## Notes",
                "",
                "This bundle was created by the VAST As-Built Report Generator.",
                "For support, contact your VAST Data representative.",
            ]
        )

        return "\n".join(lines)

    def create_bundle(self, bundle_name: Optional[str] = None) -> Path:
        """
        Create a ZIP bundle containing all collected results.

        Returns path to the created ZIP file.
        """
        if not self._collected_files:
            self.collect_results()

        if not self._collected_files:
            raise ValueError("No results to bundle")

        self._output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cluster_name = self._metadata.get("cluster_name", "unknown").replace(" ", "_")

        if bundle_name:
            zip_name = f"{bundle_name}.zip"
        else:
            zip_name = f"validation_bundle_{cluster_name}_{timestamp}.zip"

        zip_path = self._output_dir / zip_name

        self.emit("info", f"Creating bundle: {zip_name}")

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # Add manifest
            manifest = {
                "version": self.BUNDLE_MANIFEST_VERSION,
                "metadata": self._metadata,
                "files": {k: v.name for k, v in self._collected_files.items()},
                "created": datetime.now().isoformat(),
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Add summary
            summary_md = self.generate_summary()
            zf.writestr("SUMMARY.md", summary_md)

            # Add all collected files
            for category, filepath in self._collected_files.items():
                if filepath.exists():
                    arcname = self._archive_path(category, filepath.name)
                    zf.write(filepath, arcname)
                    self.emit("success", f"Added: {arcname}")

            # Write placeholders for missing top-level categories
            cip = self._metadata.get("cluster_ip", "unknown")
            placeholder_categories = {
                "health_check": "health",
                "network_config": "network",
                "switch_config": "switches",
                "vnetmap": "topology",
                "vperfsanity": "performance",
                "support_tools": "diagnostics",
                "log_bundle": "diagnostics",
                "asbuilt_report": "reports",
                "asbuilt_json": "reports",
            }
            for cat, folder in placeholder_categories.items():
                if cat not in self._collected_files:
                    note = f"No {cat.replace('_', ' ')} results found for cluster {cip}.\n"
                    arcname = f"{folder}/{cat}_NOT_FOUND.txt"
                    zf.writestr(arcname, note)
                    self.emit("info", f"Placeholder: {arcname}")

        file_size = zip_path.stat().st_size
        size_str = self._format_size(file_size)
        self.emit("success", f"Bundle created: {zip_path.name} ({size_str})")

        return zip_path

    def get_bundle_info(self, bundle_path: Path) -> Dict[str, Any]:
        """Get information about an existing bundle."""
        if not bundle_path.exists():
            return {"error": "Bundle not found"}

        info = {
            "path": str(bundle_path),
            "name": bundle_path.name,
            "size": bundle_path.stat().st_size,
            "size_formatted": self._format_size(bundle_path.stat().st_size),
            "files": [],
        }

        try:
            with zipfile.ZipFile(bundle_path, "r") as zf:
                info["files"] = zf.namelist()

                # Try to read manifest
                if "manifest.json" in zf.namelist():
                    manifest = json.loads(zf.read("manifest.json"))
                    info["manifest"] = manifest
        except Exception as e:
            info["error"] = str(e)

        return info

    def list_bundles(self) -> List[Dict[str, Any]]:
        """List all available bundles."""
        bundles = []
        if self._output_dir.exists():
            for f in sorted(self._output_dir.glob("*.zip"), reverse=True):
                bundles.append(
                    {
                        "name": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "size_formatted": self._format_size(f.stat().st_size),
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    }
                )
        return bundles

    @staticmethod
    def _archive_path(category: str, filename: str) -> str:
        """Determine the archive subdirectory for a file category."""
        if category in ("health_check", "health_remediation"):
            return f"health/{filename}"
        if category.startswith("network_"):
            return f"network/{filename}"
        if category.startswith("switch_config"):
            return f"switches/{filename}"
        if category in ("vnetmap", "vnetmap_output"):
            return f"topology/{filename}"
        if category in ("support_tools", "log_bundle"):
            return f"diagnostics/{filename}"
        if category in ("vperfsanity",):
            return f"performance/{filename}"
        if category in ("asbuilt_report", "asbuilt_json"):
            return f"reports/{filename}"
        return filename

    @staticmethod
    def _format_size(size_bytes: float) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


def get_result_bundler(
    output_dir: Optional[Path] = None,
    output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None,
) -> ResultBundler:
    """Factory function for creating ResultBundler instances."""
    return ResultBundler(output_dir=output_dir, output_callback=output_callback)
