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


# Category-status values used in the manifest and SUMMARY.md.
STATUS_OK = "ok"
STATUS_STALE = "stale"
STATUS_MISSING = "missing"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


class ResultBundler:
    """Bundles validation results into downloadable ZIP archives."""

    BUNDLE_MANIFEST_VERSION = "1.3"

    # RM-6: generalization of the RM-5 "attach prior output with a
    # banner instead of a one-line STALE placeholder" rescue.
    #
    # Keys are category names (must line up with ``_stale_files`` keys).
    # Values carry the human-readable label used in the banner + the
    # rationale block that explains *why* the file is prior data.  Adding
    # a new eligible category is a two-line change: one entry here plus
    # a matching ``include_prior_<category>`` kwarg on the public factory.
    _PRIOR_RESCUE: Dict[str, Dict[str, Any]] = {
        "vperfsanity": {
            "human_name": "vperfsanity",
            "rationale": [
                "vperfsanity was not rerun during this run (it can take up to",
                "30 minutes), so this file is included for continuity only.",
                "Do NOT treat these numbers as current-run performance data.",
            ],
        },
        "vnetmap": {
            "human_name": "vnetmap",
            "rationale": [
                "vnetmap could not complete during this run (typically because",
                "one or more switches failed SSH/API auth), so this file is",
                "included for topology continuity only.",
                "Do NOT treat this LLDP map as reflecting current-run cabling.",
            ],
        },
        "vnetmap_output": {
            "human_name": "vnetmap raw output",
            "rationale": [
                "vnetmap could not complete during this run (typically because",
                "one or more switches failed SSH/API auth), so this raw output",
                "is included for topology continuity only.",
                "Do NOT treat this LLDP dump as reflecting current-run cabling.",
            ],
        },
    }

    def __init__(
        self,
        output_dir: Optional[Path] = None,
        output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None,
        *,
        include_prior_vperfsanity: bool = True,
        include_prior_vnetmap: bool = True,
    ):
        if output_dir is None:
            from utils import get_data_dir

            output_dir = get_data_dir() / "output" / "bundles"
        self._output_dir = output_dir
        self._output_callback = output_callback
        self._collected_files: Dict[str, Path] = {}
        self._stale_files: Dict[str, Path] = {}
        self._category_status: Dict[str, str] = {}
        self._operation_status: Dict[str, str] = {}
        self._since: Optional[datetime] = None
        self._metadata: Dict[str, Any] = {}
        # RM-5: rescue prior ``vperfsanity`` output when the current run
        # didn't regenerate it (it can take 30 min) — recorded in the
        # manifest as ``vperfsanity_prior_source``.  Opt out by passing
        # ``include_prior_vperfsanity=False`` / setting
        # ``bundle.include_prior_vperfsanity: false`` in config.
        self._include_prior_vperfsanity = bool(include_prior_vperfsanity)
        self._prior_vperfsanity_source: Optional[Path] = None
        # RM-6: same story for ``vnetmap`` — when a switch auth failure
        # or API blip kills the run we'd otherwise regress from a real
        # LLDP topology file to a one-line ``vnetmap_STALE.txt`` note.
        # ``include_prior_vnetmap`` applies to both the parsed JSON
        # (category ``vnetmap``) and the raw text dump (category
        # ``vnetmap_output``) since they're two halves of the same file.
        self._include_prior_vnetmap = bool(include_prior_vnetmap)
        self._prior_vnetmap_source: Optional[Path] = None
        self._prior_vnetmap_output_source: Optional[Path] = None

    def emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        """Emit output message via callback, or fall back to the Python logger."""
        if self._output_callback:
            try:
                self._output_callback(level, message, details)
            except Exception:
                pass
        else:
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
        *,
        since: Optional[datetime] = None,
    ) -> Optional[Path]:
        """Return the most recent file that passes *match_fn*, or None.

        When *since* is given, files whose ``mtime`` is strictly older than
        *since* are skipped so the bundler does not silently pick up results
        produced by an earlier run.
        """
        for f in sorted(candidates, reverse=True):
            if since is not None:
                try:
                    if datetime.fromtimestamp(f.stat().st_mtime) < since:
                        continue
                except OSError:
                    continue
            if cluster_ip is None or match_fn(f, cluster_ip):
                return f
        return None

    def _pick_stale(
        self,
        candidates: List[Path],
        cluster_ip: Optional[str],
        match_fn,
        since: datetime,
    ) -> Optional[Path]:
        """Return the newest pre-*since* file matching *match_fn*, or None.

        Used purely to annotate the bundle so a reader can see that older
        data exists on disk but was intentionally excluded.
        """
        for f in sorted(candidates, reverse=True):
            try:
                if datetime.fromtimestamp(f.stat().st_mtime) >= since:
                    continue
            except OSError:
                continue
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
        since: Optional[datetime] = None,
        operation_status: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Path]:
        """Collect validation result files scoped to *cluster_ip*.

        For each category the most recent matching file is selected.
        When *cluster_ip* is ``None`` the latest file regardless of cluster
        is chosen.

        When *since* is given, only files whose ``mtime`` is at or after
        *since* are treated as fresh results for this run.  Older matching
        files are tracked separately as ``stale`` so the bundle can report
        that pre-existing data was intentionally excluded, instead of
        silently including results from an earlier run.

        *operation_status* is an optional ``{category: "success"|"failed"|
        "skipped"}`` map from the caller (one-shot runner) describing which
        operations were actually executed.  It is used to choose between
        ``missing``, ``failed`` and ``skipped`` when no fresh file is found.
        """
        self._since = since
        self._operation_status = dict(operation_status or {})

        if cluster_ip:
            self.emit("info", f"Collecting results for cluster {cluster_ip}...")
        else:
            self.emit("info", "Collecting validation results (all clusters)...")
        if since is not None:
            self.emit("info", f"Only including results produced at or after {since.isoformat(timespec='seconds')}")

        if results_dir is None:
            from utils import get_data_dir

            results_dir = get_data_dir() / "output"
        collected: Dict[str, Path] = {}
        stale: Dict[str, Path] = {}

        def _record(category: str, candidates: List[Path], match_fn) -> None:
            hit = self._pick_latest(candidates, cluster_ip, match_fn, since=since)
            if hit:
                collected[category] = hit
                self.emit("success", f"Found {category}: {hit.name}")
                return
            if since is not None:
                stale_hit = self._pick_stale(candidates, cluster_ip, match_fn, since)
                if stale_hit:
                    stale[category] = stale_hit
                    self.emit(
                        "warn",
                        f"Stale {category} found (pre-run): {stale_hit.name} — excluded from bundle",
                    )

        scripts_dir = results_dir / "scripts"

        # -- Health check results --
        health_dir = results_dir / "health"
        if health_dir.exists():
            _record(
                "health_check",
                list(health_dir.glob("health_check_*.json")),
                self._json_has_cluster_ip,
            )
            _record(
                "health_remediation",
                list(health_dir.glob("health_remediation_*.txt")),
                self._text_header_has_ip,
            )

        # -- Network configurations --
        network_dir = scripts_dir / "network_configs"
        if network_dir.exists():
            _record(
                "network_config",
                list(network_dir.glob("network_summary_*.json")),
                self._json_has_cluster_ip,
            )
            net_hit = collected.get("network_config")
            if net_hit:
                timestamp = self._extract_timestamp(net_hit.name)
                if timestamp:
                    self._collect_network_text_files(network_dir, timestamp, collected)

        # -- Switch configurations --
        switch_dir = scripts_dir / "switch_configs"
        if switch_dir.exists():
            _record(
                "switch_config",
                list(switch_dir.glob("switch_configs_*.json")),
                self._json_has_cluster_ip,
            )
            sw_hit = collected.get("switch_config")
            if sw_hit:
                timestamp = self._extract_timestamp(sw_hit.name)
                if timestamp:
                    for idx, txt in enumerate(sorted(switch_dir.glob(f"switch_*_{timestamp}.txt"))):
                        key = "switch_config_txt" if idx == 0 else f"switch_config_txt_{idx}"
                        collected[key] = txt
                        self.emit("success", f"Found switch backup: {txt.name}")

        if scripts_dir.exists():
            # -- vnetmap results --
            _record(
                "vnetmap",
                list(scripts_dir.glob("vnetmap_results_*.json")),
                lambda f, ip: self._json_has_cluster_ip(f, ip) or self._filename_has_ip(f, ip),
            )
            _record(
                "vnetmap_output",
                list(scripts_dir.glob("vnetmap_output_*.txt")),
                self._filename_has_ip,
            )

            # -- vperfsanity results --
            _record(
                "vperfsanity",
                list(scripts_dir.glob("vperfsanity_results_*.txt")),
                self._filename_has_ip,
            )

            # -- Support tool archives --
            _record(
                "support_tools",
                list(scripts_dir.glob("*support_tool_logs*.tgz")),
                lambda f, ip: self._sidecar_matches(f, ip) or self._text_header_has_ip(f, ip),
            )

            # -- Log bundles --
            _record(
                "log_bundle",
                list(scripts_dir.glob("vast_log_bundle_*.tar.gz")),
                self._verification_matches,
            )

        # -- Report PDFs --
        from utils import get_data_dir as _gdd

        reports_dir = _gdd() / "reports"
        if reports_dir.exists():
            pdf_candidates = list(reports_dir.glob("vast_asbuilt_report_*.pdf"))
            hit = self._pick_latest(
                pdf_candidates,
                cluster_ip,
                lambda f, ip: (self._sidecar_matches(f, ip) or self._filename_has_ip(f, ip)),
                since=since,
            )
            if hit is None:
                cluster_name = self._metadata.get("cluster_name", "")
                if cluster_name and cluster_name != "Unknown":
                    hit = self._pick_latest(
                        pdf_candidates,
                        cluster_name,
                        lambda f, cn: cn.lower() in f.name.lower(),
                        since=since,
                    )
            if hit:
                collected["asbuilt_report"] = hit
                self.emit("success", f"Found As-Built report: {hit.name}")
            elif since is not None:
                stale_hit = self._pick_stale(
                    pdf_candidates,
                    cluster_ip,
                    lambda f, ip: (self._sidecar_matches(f, ip) or self._filename_has_ip(f, ip)),
                    since,
                )
                if stale_hit:
                    stale["asbuilt_report"] = stale_hit
                    self.emit(
                        "warn",
                        f"Stale asbuilt_report found (pre-run): {stale_hit.name} — excluded from bundle",
                    )

            # Companion JSON data file
            _record(
                "asbuilt_json",
                list(reports_dir.glob("vast_data_*.json")),
                self._json_has_cluster_ip,
            )

        self._collected_files = collected
        self._stale_files = stale
        self._category_status = self._compute_category_status(collected, stale)
        self.emit("info", f"Collected {len(collected)} result files for bundle")
        if stale:
            self.emit(
                "warn",
                f"Detected {len(stale)} stale pre-run file(s); they are excluded and flagged in the manifest.",
            )
        return collected

    def _compute_category_status(
        self,
        collected: Dict[str, Path],
        stale: Dict[str, Path],
    ) -> Dict[str, str]:
        """Derive per-category status from what was collected vs. stale.

        Status values:
          - ``ok``      — a fresh file was bundled for this category.
          - ``stale``   — only a pre-run file exists; excluded from bundle.
          - ``failed``  — operation was run but failed (per operation_status).
          - ``skipped`` — operation was not selected/run.
          - ``missing`` — expected category with no file and no operation_status signal.
        """
        status: Dict[str, str] = {}
        # Canonical category list we report on; extra sub-files (network_commands,
        # switch_config_txt_*) are implied by the parent and not surfaced here.
        categories = [
            "health_check",
            "network_config",
            "switch_config",
            "vnetmap",
            # RM-6: raw vnetmap output is tracked separately so the
            # bundler can rescue the TXT half of a stale run independently
            # of the JSON half (both live in ``stale``/``collected`` but
            # without an entry here the status never flips to ``stale``
            # and the placeholder/rescue loop treats it as missing).
            "vnetmap_output",
            "vperfsanity",
            "support_tools",
            "log_bundle",
            "asbuilt_report",
            "asbuilt_json",
        ]
        for cat in categories:
            if cat in collected:
                status[cat] = STATUS_OK
                continue
            if cat in stale:
                status[cat] = STATUS_STALE
                continue
            op_state = self._operation_status.get(cat, "")
            if op_state == "failed":
                status[cat] = STATUS_FAILED
            elif op_state in ("skipped", "not_run"):
                status[cat] = STATUS_SKIPPED
            else:
                status[cat] = STATUS_MISSING
        return status

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

    CATEGORY_NAMES = {
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

    STATUS_LABELS = {
        STATUS_OK: "OK (from this run)",
        STATUS_STALE: "STALE (pre-run file excluded)",
        STATUS_FAILED: "FAILED (operation did not produce output)",
        STATUS_SKIPPED: "SKIPPED (operation not selected)",
        STATUS_MISSING: "MISSING (no matching file found)",
    }

    def generate_summary(self) -> str:
        """Generate a markdown summary of collected results."""
        lines = [
            "# Validation Results Summary",
            "",
            f"**Cluster:** {self._metadata.get('cluster_name', 'Unknown')}",
            f"**IP:** {self._metadata.get('cluster_ip', 'Unknown')}",
            f"**Version:** {self._metadata.get('cluster_version', 'Unknown')}",
            f"**Bundle Created:** {self._metadata.get('bundle_created', 'Unknown')}",
        ]
        if self._since is not None:
            lines.append(f"**Run Started:** {self._since.isoformat(timespec='seconds')}")
        lines.extend(
            [
                "",
                "## Category Status",
                "",
            ]
        )

        for category, status in self._category_status.items():
            name = self.CATEGORY_NAMES.get(category, category)
            label = self.STATUS_LABELS.get(status, status.upper())
            if status == STATUS_OK:
                filepath = self._collected_files.get(category)
                fname = filepath.name if filepath else ""
                lines.append(f"- **{name}**: {label} — `{fname}`")
            elif status == STATUS_STALE:
                stale = self._stale_files.get(category)
                fname = stale.name if stale else ""
                # RM-5/RM-6: when a STALE category was rescued as a PRIOR
                # file, say so explicitly in SUMMARY.md rather than claim
                # it was excluded.  Readers of the bundle can then trust
                # the relevant folder holds continuity data instead of a
                # one-line placeholder.
                rescued_source: Optional[Path] = None
                if category == "vperfsanity":
                    rescued_source = self._prior_vperfsanity_source
                elif category == "vnetmap":
                    rescued_source = self._prior_vnetmap_source
                elif category == "vnetmap_output":
                    rescued_source = self._prior_vnetmap_output_source

                if rescued_source is not None and rescued_source == stale:
                    lines.append(
                        f"- **{name}**: STALE (included as PRIOR with banner) — " f"`{category}_PRIOR_{fname}`"
                    )
                else:
                    lines.append(f"- **{name}**: {label} — `{fname}` (not included)")
            else:
                lines.append(f"- **{name}**: {label}")

        # Also list the ancillary files bundled alongside parent categories
        extras = [
            k
            for k in self._collected_files
            if k not in self._category_status
            and k
            in (
                "health_remediation",
                "network_commands",
                "network_interfaces",
                "network_routing",
                "network_bonds",
                "vnetmap_output",
            )
            or k.startswith("switch_config_txt")
        ]
        if extras:
            lines.extend(["", "## Additional Files", ""])
            for category in extras:
                filepath = self._collected_files.get(category)
                if not filepath:
                    continue
                name = self.CATEGORY_NAMES.get(category, category)
                lines.append(f"- **{name}**: `{filepath.name}`")

        lines.extend(["", "## Validation Status", ""])

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
            # Reset per-run side effects so repeat calls on the same
            # bundler instance don't leak state from a previous bundle.
            self._prior_vperfsanity_source = None
            self._prior_vnetmap_source = None
            self._prior_vnetmap_output_source = None

            for category, filepath in self._collected_files.items():
                if filepath.exists():
                    arcname = self._archive_path(category, filepath.name)
                    zf.write(filepath, arcname)
                    self.emit("success", f"Added: {arcname}")

            cip = self._metadata.get("cluster_ip", "unknown")
            placeholder_categories = {
                "health_check": "health",
                "network_config": "network",
                "switch_config": "switches",
                "vnetmap": "topology",
                "vnetmap_output": "topology",
                "vperfsanity": "performance",
                "support_tools": "diagnostics",
                "log_bundle": "diagnostics",
                "asbuilt_report": "reports",
                "asbuilt_json": "reports",
            }
            self._write_placeholders(zf, placeholder_categories, cip)

            # Manifest / SUMMARY are written last so they can reference
            # side-effect fields (e.g. ``vperfsanity_prior_source``) set
            # while the placeholder loop ran above.
            manifest = {
                "version": self.BUNDLE_MANIFEST_VERSION,
                "metadata": self._metadata,
                "files": {k: v.name for k, v in self._collected_files.items()},
                "categories": dict(self._category_status),
                "stale": {k: v.name for k, v in self._stale_files.items()},
                "operation_status": dict(self._operation_status),
                "run_started_at": self._since.isoformat() if self._since else None,
                "created": datetime.now().isoformat(),
                "vperfsanity_prior_source": (
                    self._prior_vperfsanity_source.name if self._prior_vperfsanity_source else None
                ),
                "include_prior_vperfsanity": self._include_prior_vperfsanity,
                # RM-6: vnetmap prior-rescue sibling fields.  Both entries
                # can be populated in a single run because the structured
                # JSON (``vnetmap``) and raw dump (``vnetmap_output``) are
                # two halves of the same collection.
                "vnetmap_prior_source": (self._prior_vnetmap_source.name if self._prior_vnetmap_source else None),
                "vnetmap_output_prior_source": (
                    self._prior_vnetmap_output_source.name if self._prior_vnetmap_output_source else None
                ),
                "include_prior_vnetmap": self._include_prior_vnetmap,
            }
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            summary_md = self.generate_summary()
            zf.writestr("SUMMARY.md", summary_md)

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

    def _write_placeholders(
        self,
        zf: zipfile.ZipFile,
        placeholder_categories: Dict[str, str],
        cip: str,
    ) -> None:
        """Write per-category placeholder files for anything not collected.

        Split out from :meth:`create_bundle` so the RM-5 "attach prior
        vperfsanity output instead of a one-line STALE note" rescue — and
        its RM-6 generalization to ``vnetmap`` / ``vnetmap_output`` — has
        a single, testable home.  Any side effects (e.g. setting
        ``self._prior_vperfsanity_source`` or ``self._prior_vnetmap_source``)
        happen inside this method and are then reflected in the manifest
        by the caller.
        """
        for cat, folder in placeholder_categories.items():
            if cat in self._collected_files:
                continue
            status = self._category_status.get(cat, STATUS_MISSING)
            if status == STATUS_STALE:
                stale_path = self._stale_files.get(cat)
                stale_name = stale_path.name if stale_path else ""

                # RM-5/RM-6: rescue prior output for any category in
                # ``_PRIOR_RESCUE`` so bundles never regress from real
                # data to a one-line STALE note.  Eligibility requires
                # (a) an entry in ``_PRIOR_RESCUE``, (b) the per-category
                # include flag is on, and (c) the stale file still
                # exists on disk.
                if (
                    cat in self._PRIOR_RESCUE
                    and self._is_prior_rescue_enabled(cat)
                    and stale_path is not None
                    and stale_path.exists()
                ):
                    rescued = self._rescue_prior_file(zf, cat, folder, stale_path)
                    if rescued:
                        continue
                    # Fall through to the STALE placeholder below if the
                    # rescue couldn't read the file for some reason — the
                    # operator still sees a STALE note rather than a
                    # silent empty topology/performance folder.

                note = (
                    f"No fresh {cat.replace('_', ' ')} results for cluster {cip} "
                    f"in this run.\nA pre-run file exists on disk "
                    f"({stale_name}) but was excluded from this bundle to avoid "
                    f"silently shipping stale data.\n"
                )
                arcname = f"{folder}/{cat}_STALE.txt"
            elif status == STATUS_FAILED:
                note = (
                    f"The {cat.replace('_', ' ')} operation ran but failed for "
                    f"cluster {cip}. See the operation log for the root cause.\n"
                )
                arcname = f"{folder}/{cat}_FAILED.txt"
            elif status == STATUS_SKIPPED:
                note = f"The {cat.replace('_', ' ')} operation was not selected for this run (cluster {cip}).\n"
                arcname = f"{folder}/{cat}_SKIPPED.txt"
            else:
                note = f"No {cat.replace('_', ' ')} results found for cluster {cip}.\n"
                arcname = f"{folder}/{cat}_NOT_FOUND.txt"
            zf.writestr(arcname, note)
            self.emit("info", f"Placeholder: {arcname}")

    def _is_prior_rescue_enabled(self, category: str) -> bool:
        """Return whether prior-file rescue is enabled for *category*.

        Keeps the per-category flag mapping in one place so a new
        rescue-eligible category only needs an entry in
        ``_PRIOR_RESCUE`` plus a line here.
        """
        if category == "vperfsanity":
            return self._include_prior_vperfsanity
        if category in ("vnetmap", "vnetmap_output"):
            return self._include_prior_vnetmap
        return False

    def _record_prior_source(self, category: str, stale_path: Path) -> None:
        """Record the rescued prior file so the manifest picks it up."""
        if category == "vperfsanity":
            self._prior_vperfsanity_source = stale_path
        elif category == "vnetmap":
            self._prior_vnetmap_source = stale_path
        elif category == "vnetmap_output":
            self._prior_vnetmap_output_source = stale_path

    def _rescue_prior_file(
        self,
        zf: zipfile.ZipFile,
        category: str,
        folder: str,
        stale_path: Path,
    ) -> bool:
        """Attach *stale_path* as a PRIOR file (with banner) to *zf*.

        Returns ``True`` when the rescue succeeded and the caller should
        skip writing a STALE placeholder; ``False`` otherwise (fall
        through to STALE note so the operator isn't left with a silent
        empty folder).
        """
        rescue_cfg = self._PRIOR_RESCUE.get(category)
        if not rescue_cfg:
            return False

        try:
            prior_body = stale_path.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read prior %s file %s: %s", category, stale_path, exc)
            return False

        try:
            prior_mtime = datetime.fromtimestamp(stale_path.stat().st_mtime).isoformat(timespec="seconds")
        except OSError:
            prior_mtime = "unknown"

        stale_name = stale_path.name
        human_name = rescue_cfg.get("human_name", category)
        rationale: List[str] = list(rescue_cfg.get("rationale", []))

        run_started = self._since.isoformat(timespec="seconds") if self._since else "unknown"
        banner_lines: List[str] = [
            "=" * 72,
            f"NOTE: This is the prior {human_name} output from an earlier run.",
            f"Source file:    {stale_name}",
            f"Original mtime: {prior_mtime}",
            f"Run started:    {run_started}",
        ]
        banner_lines.extend(rationale)
        banner_lines.append("=" * 72)
        banner = "\n".join(banner_lines) + "\n\n"

        # Keep the original extension so consumers (.json parsers, etc)
        # can still open the file by type — the PRIOR marker goes in the
        # stem not the suffix.
        arcname = f"{folder}/{category}_PRIOR_{stale_name}"
        zf.writestr(arcname, banner + prior_body)
        self.emit(
            "info",
            f"Attached prior {human_name} output as {arcname} (with banner)",
        )
        self._record_prior_source(category, stale_path)
        return True

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
    *,
    include_prior_vperfsanity: bool = True,
    include_prior_vnetmap: bool = True,
) -> ResultBundler:
    """Factory function for creating ResultBundler instances."""
    return ResultBundler(
        output_dir=output_dir,
        output_callback=output_callback,
        include_prior_vperfsanity=include_prior_vperfsanity,
        include_prior_vnetmap=include_prior_vnetmap,
    )
