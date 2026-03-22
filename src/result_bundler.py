"""
Result Bundler Module

Creates downloadable validation packages containing all workflow outputs,
health check results, and configuration extracts.
"""

import json
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
        self._output_dir = output_dir or Path("output/bundles")
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
        """Set cluster metadata for the bundle."""
        self._metadata = {
            "cluster_name": cluster_name,
            "cluster_ip": cluster_ip,
            "cluster_version": cluster_version,
            "bundle_created": datetime.now().isoformat(),
            "manifest_version": self.BUNDLE_MANIFEST_VERSION,
        }

    def collect_results(self, results_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Collect all validation result files from output directories.

        Returns dict mapping category to file path.
        """
        self.emit("info", "Collecting validation results...")

        results_dir = results_dir or Path("output")
        collected = {}

        # Health check results
        health_dir = results_dir / "health"
        if health_dir.exists():
            for f in health_dir.glob("health_check_*.json"):
                collected["health_check"] = f
                self.emit("success", f"Found health check: {f.name}")
                break

        # Network configurations
        network_dir = results_dir / "advanced_ops" / "network_configs"
        if network_dir.exists():
            for f in sorted(network_dir.glob("*.json"), reverse=True):
                collected["network_config"] = f
                self.emit("success", f"Found network config: {f.name}")
                break
            for f in sorted(network_dir.glob("*.txt"), reverse=True):
                if "commands" in f.name:
                    collected["network_commands"] = f
                    self.emit("success", f"Found network commands: {f.name}")
                    break

        # Switch configurations
        switch_dir = results_dir / "advanced_ops" / "switch_configs"
        if switch_dir.exists():
            for f in sorted(switch_dir.glob("*.json"), reverse=True):
                collected["switch_config"] = f
                self.emit("success", f"Found switch config: {f.name}")
                break

        # vnetmap results
        vnetmap_dir = results_dir / "advanced_ops" / "vnetmap"
        if vnetmap_dir.exists():
            for f in sorted(vnetmap_dir.glob("*.json"), reverse=True):
                collected["vnetmap"] = f
                self.emit("success", f"Found vnetmap results: {f.name}")
                break

        # Support tool results
        support_dir = results_dir / "advanced_ops" / "support_tools"
        if support_dir.exists():
            for f in sorted(support_dir.glob("*.tar.gz"), reverse=True):
                collected["support_tools"] = f
                self.emit("success", f"Found support tools archive: {f.name}")
                break

        # vperfsanity results
        perf_dir = results_dir / "advanced_ops" / "vperfsanity"
        if perf_dir.exists():
            for f in sorted(perf_dir.glob("*.json"), reverse=True):
                collected["vperfsanity"] = f
                self.emit("success", f"Found vperfsanity results: {f.name}")
                break

        # Log bundles
        log_dir = results_dir / "advanced_ops" / "log_bundles"
        if log_dir.exists():
            for f in sorted(log_dir.glob("*.tar.gz"), reverse=True):
                collected["log_bundle"] = f
                self.emit("success", f"Found log bundle: {f.name}")
                break

        # Report PDFs
        reports_dir = Path("reports")
        if reports_dir.exists():
            for f in sorted(reports_dir.glob("vast_asbuilt_report_*.pdf"), reverse=True):
                collected["asbuilt_report"] = f
                self.emit("success", f"Found As-Built report: {f.name}")
                break

        self._collected_files = collected
        self.emit("info", f"Collected {len(collected)} result files")
        return collected

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
            "network_config": "Network Configuration",
            "network_commands": "Network Commands History",
            "switch_config": "Switch Configuration",
            "vnetmap": "vnetmap Topology Validation",
            "support_tools": "VAST Support Tools Output",
            "vperfsanity": "vperfsanity Performance Results",
            "log_bundle": "VMS Log Bundle",
            "asbuilt_report": "As-Built Report PDF",
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
                    # Organize files into subdirectories
                    if category in ("health_check",):
                        arcname = f"health/{filepath.name}"
                    elif category in ("network_config", "network_commands"):
                        arcname = f"network/{filepath.name}"
                    elif category in ("switch_config",):
                        arcname = f"switches/{filepath.name}"
                    elif category in ("vnetmap",):
                        arcname = f"topology/{filepath.name}"
                    elif category in ("support_tools", "log_bundle"):
                        arcname = f"diagnostics/{filepath.name}"
                    elif category in ("vperfsanity",):
                        arcname = f"performance/{filepath.name}"
                    elif category in ("asbuilt_report",):
                        arcname = f"reports/{filepath.name}"
                    else:
                        arcname = filepath.name

                    zf.write(filepath, arcname)
                    self.emit("success", f"Added: {arcname}")

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
    def _format_size(size_bytes: int) -> str:
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
