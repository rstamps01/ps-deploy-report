"""
VMS Log Bundle Workflow

5-step workflow for collecting VMS log bundles:
1. Discover Log Sizes
2. Confirm Collection
3. Create Archive
4. Download to Laptop
5. Verify Contents
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from script_runner import ScriptRunner
from utils.logger import get_logger
from utils.ssh_adapter import is_ssh_transport_failure, ssh_transport_failure_message

logger = get_logger(__name__)


class LogBundleWorkflow:
    """VMS Log Bundle collection workflow."""

    name = "VMS Log Bundle"
    description = "Collect VMS log bundle for support analysis"
    enabled = True
    min_vast_version = "5.0"

    LOG_DIRS = [
        "/var/log/vast",
        "/var/log/messages",
        "/var/log/syslog",
    ]
    # VAST container logs live under /vast/log on 5.x CNodes (the legacy dirs above are
    # often absent).  Only recent files are taken, and only below a size cap, so the
    # bundle stays small enough to download from the field.
    RECENT_LOG_DIRS = ["/vast/log"]
    RECENT_LOG_MINUTES = 24 * 60
    RECENT_LOG_MAX_MB = 2048
    MAX_BUNDLE_MB = 5120
    # Intentional [B108]: staging directory on the remote VAST CNode (populated via SSH), not a local tempfile.
    BUNDLE_DIR = "/tmp/vast_log_bundle"  # nosec B108

    def __init__(self):
        self._output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._credentials: Dict[str, Any] = {}
        self._script_runner: Optional[ScriptRunner] = None
        self._output_dir: Optional[Path] = None
        self._step_data: Dict[str, Any] = {}

    def set_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        self._output_callback = callback
        if self._script_runner:
            self._script_runner._output_callback = callback

    def set_output_dir(self, output_dir: Any) -> None:
        """Point local script output at a per-cluster scripts dir (QP-2)."""
        self._output_dir = Path(output_dir)
        if self._script_runner is not None:
            self._script_runner.set_local_dir(self._output_dir)

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

    def _ssh_host(self) -> str:
        """SSH target host: the Teleport-forwarded local endpoint when set,
        otherwise the cluster IP (Tech Port / direct modes)."""
        host = self._credentials.get("ssh_host") or self._credentials.get("cluster_ip")
        return str(host) if host else ""

    def _ssh_port(self) -> int:
        """SSH target port: the Teleport-forwarded local port when set, else 22."""
        try:
            return int(self._credentials.get("ssh_port") or 22)
        except (TypeError, ValueError):
            return 22

    def emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        if self._output_callback:
            try:
                self._output_callback(level, message, details)
            except Exception:
                pass

    def get_steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": 1, "name": "Discover Log Sizes", "description": "Check available log sizes before collection"},
            {"id": 2, "name": "Confirm Collection", "description": "Review sizes and confirm collection"},
            {"id": 3, "name": "Create Archive", "description": "Generate compressed log bundle archive"},
            {"id": 4, "name": "Download to Laptop", "description": "SCP archive to local system"},
            {"id": 5, "name": "Verify Contents", "description": "Verify archive integrity and contents"},
        ]

    def validate_prerequisites(self) -> tuple[bool, str]:
        required = ["cluster_ip", "node_user", "node_password"]
        missing = [k for k in required if not self._credentials.get(k)]
        if missing:
            return False, "Missing credentials: " + ", ".join(missing)
        return True, "Prerequisites met"

    def run_step(self, step_id: int) -> Dict[str, Any]:
        step_methods = {
            1: self._step_discover_sizes,
            2: self._step_confirm_collection,
            3: self._step_create_archive,
            4: self._step_download_to_laptop,
            5: self._step_verify_contents,
        }

        method = step_methods.get(step_id)
        if not method:
            return {"success": False, "message": f"Invalid step ID: {step_id}"}

        if self._script_runner is None:
            self._script_runner = ScriptRunner(output_callback=self._output_callback, local_dir=self._output_dir)
        # Route SSH/SCP through the Teleport-forwarded port when active.
        self._script_runner.set_ssh_port(self._ssh_port())

        try:
            return method()
        except Exception as e:
            logger.exception(f"Step {step_id} failed")
            return {"success": False, "message": str(e)}

    def _step_discover_sizes(self) -> Dict[str, Any]:
        """Step 1: Discover log sizes on CNode."""
        self.emit("info", "Step 1: Discovering log sizes...")

        host = self._ssh_host()
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        # Check prerequisites
        ok, msg = self._script_runner.check_prerequisites(host, user, password)
        if not ok:
            return {"success": False, "message": msg}

        # Get sizes of log directories
        sizes = {}
        total_size: float = 0
        size_details = []

        for log_dir in self.LOG_DIRS:
            cmd = f"sudo du -sh {log_dir} 2>/dev/null || echo '0 {log_dir}'"
            result = self._script_runner.execute_remote(host, user, password, cmd, timeout=60)
            if result.success and result.stdout:
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    size_str = parts[0]
                    sizes[log_dir] = size_str
                    size_details.append(f"{log_dir}: {size_str}")
                    # Parse size for total
                    try:
                        num = float(size_str.rstrip("GMKB"))
                        if "G" in size_str:
                            total_size += num * 1024
                        elif "M" in size_str:
                            total_size += num
                        elif "K" in size_str:
                            total_size += num / 1024
                    except ValueError:
                        pass

        # Recent /vast/log is the bulk of a 5.x bundle; include it in the total so
        # operators are not told "~1 MB" when Step 3 will archive hundreds of MB.
        minutes = self.RECENT_LOG_MINUTES
        for log_dir in self.RECENT_LOG_DIRS:
            size_cmd = (
                f"sudo find {log_dir} -type f -mmin -{minutes} -printf '%s\\n' 2>/dev/null "
                "| awk '{s+=$1} END {printf \"%d\\n\", s}'"
            )
            result = self._script_runner.execute_remote(host, user, password, size_cmd, timeout=120)
            try:
                recent_bytes = int((result.stdout or "0").strip().splitlines()[-1])
            except (ValueError, IndexError):
                recent_bytes = 0
            if recent_bytes <= 0:
                sizes[f"{log_dir} (recent {minutes // 60}h)"] = "0"
                size_details.append(f"{log_dir} (recent {minutes // 60}h): 0")
                continue
            recent_mb = recent_bytes / 1048576
            sizes[f"{log_dir} (recent {minutes // 60}h)"] = f"{recent_mb:.0f}M"
            size_details.append(f"{log_dir} (recent {minutes // 60}h): {recent_mb:.0f}M")
            total_size += recent_mb

        self._step_data["log_sizes"] = sizes
        self._step_data["total_size_mb"] = total_size

        size_warning = ""
        if total_size > 1024:
            size_warning = f"\nWARNING: Total size exceeds 1GB ({total_size:.0f} MB)"

        return {
            "success": True,
            "message": f"Discovered {len(sizes)} log sources, total ~{total_size:.0f} MB",
            "details": "\n".join(size_details) + size_warning,
            "data": {"sizes": sizes, "total_mb": total_size},
        }

    def _step_confirm_collection(self) -> Dict[str, Any]:
        """Step 2: Confirm collection based on discovered sizes."""
        self.emit("info", "Step 2: Confirming log collection...")

        total_size = self._step_data.get("total_size_mb", 0)

        # Check if size is reasonable
        if total_size > self.MAX_BUNDLE_MB:
            return {
                "success": False,
                "message": f"Log bundle too large ({total_size:.0f} MB). Max: 5GB",
                "details": "Consider collecting specific log directories instead",
            }

        # Mark as confirmed
        self._step_data["collection_confirmed"] = True

        return {
            "success": True,
            "message": f"Collection confirmed for {total_size:.0f} MB of logs",
            "details": "Proceeding to create archive",
        }

    def _step_create_archive(self) -> Dict[str, Any]:
        """Step 3: Create compressed log bundle archive."""
        self.emit("info", "Step 3: Creating log bundle archive...")

        if not self._step_data.get("collection_confirmed"):
            return {"success": False, "message": "Collection not confirmed. Run step 2 first."}

        host = self._ssh_host()
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"vast_log_bundle_{timestamp}.tar.gz"
        # Intentional [B108]: archive is created on the remote CNode with a timestamped name, not a local tempfile.
        archive_path = f"/tmp/{archive_name}"  # nosec B108

        # Start from an empty staging dir so files from earlier runs are never re-bundled.
        self._script_runner.execute_remote(
            host, user, password, f"sudo rm -rf {self.BUNDLE_DIR} && sudo mkdir -p {self.BUNDLE_DIR}", timeout=60
        )

        # Copy logs to bundle directory, recording which sources actually existed.
        sources: Dict[str, str] = {}
        for log_dir in self.LOG_DIRS:
            cmd = f"test -e {log_dir} && sudo cp -r {log_dir} {self.BUNDLE_DIR}/ && echo COPIED || echo MISSING"
            copy_result = self._script_runner.execute_remote(host, user, password, cmd, timeout=120)
            sources[log_dir] = "copied" if "COPIED" in (copy_result.stdout or "") else "missing"

        for log_dir in self.RECENT_LOG_DIRS:
            sources[log_dir] = self._copy_recent_logs(host, user, password, log_dir)

        self._step_data["log_sources"] = sources
        missing = [src for src, state in sources.items() if state != "copied"]
        for src in missing:
            self.emit("warn", f"Log source not collected ({sources[src]}): {src}")

        # Create archive, then drop the staging copy so it doesn't accumulate in the CNode's /tmp.
        cmd = f"sudo tar -czf {archive_path} -C {self.BUNDLE_DIR} . 2>&1"
        result = self._script_runner.execute_remote(host, user, password, cmd, timeout=600)
        self._script_runner.execute_remote(host, user, password, f"sudo rm -rf {self.BUNDLE_DIR}", timeout=120)

        if not result.success:
            rc = result.returncode if result.returncode is not None else 1
            if is_ssh_transport_failure(rc, result.stdout or "", result.stderr or ""):
                msg = ssh_transport_failure_message(rc, result.stdout or "", result.stderr or "")
                return {
                    "success": False,
                    "message": f"Failed to create archive — {msg}",
                    "details": result.stderr or result.stdout,
                }
            return {
                "success": False,
                "message": "Failed to create archive",
                "details": result.stderr or result.stdout,
            }

        # Get archive size
        size_result = self._script_runner.execute_remote(
            host, user, password, f"ls -lh {archive_path} | awk '{{print $5}}'", timeout=30
        )

        # Make archive readable
        self._script_runner.execute_remote(host, user, password, f"sudo chmod 644 {archive_path}", timeout=30)

        self._step_data["archive_path"] = archive_path
        self._step_data["archive_name"] = archive_name

        message = f"Created archive: {archive_name}"
        if missing:
            message += f" (partial: not collected {', '.join(missing)})"
        return {
            "success": True,
            "message": message,
            "details": f"Size: {size_result.stdout.strip() if size_result.success else 'unknown'}",
        }

    def _copy_recent_logs(self, host: str, user: str, password: str, log_dir: str) -> str:
        """Copy files under ``log_dir`` modified in the recent window, if below the size cap.

        Returns:
            "copied", "missing" (nothing recent / dir absent), "skipped_too_large", or
            "copy_failed" (the copy staged no files).
        """
        assert self._script_runner is not None
        minutes = self.RECENT_LOG_MINUTES
        size_cmd = (
            f"sudo find {log_dir} -type f -mmin -{minutes} -printf '%s\\n' 2>/dev/null "
            "| awk '{s+=$1} END {printf \"%d\\n\", s}'"
        )
        size_result = self._script_runner.execute_remote(host, user, password, size_cmd, timeout=120)
        try:
            recent_bytes = int((size_result.stdout or "0").strip().splitlines()[-1])
        except (ValueError, IndexError):
            recent_bytes = 0
        if recent_bytes <= 0:
            return "missing"
        recent_mb = recent_bytes / 1048576
        # Keep the whole bundle inside Step 2's 5 GB limit as well as this source's own cap.
        remaining_mb = self.MAX_BUNDLE_MB - float(self._step_data.get("total_size_mb", 0) or 0)
        limit_mb = min(self.RECENT_LOG_MAX_MB, remaining_mb)
        if recent_mb > limit_mb:
            self.emit(
                "warn",
                f"{log_dir}: {recent_mb:.0f} MB changed in the last {minutes // 60}h exceeds the "
                f"{limit_mb:.0f} MB allowance; not included",
            )
            return "skipped_too_large"
        copy_cmd = (
            f"cd / && sudo find {log_dir} -type f -mmin -{minutes} -print0 2>/dev/null "
            f"| sudo xargs -0 -r cp --parents -t {self.BUNDLE_DIR}/ 2>/dev/null; "
            f"sudo find {self.BUNDLE_DIR}{log_dir} -type f 2>/dev/null | wc -l"
        )
        copy_result = self._script_runner.execute_remote(host, user, password, copy_cmd, timeout=600)
        try:
            staged = int((copy_result.stdout or "0").strip().splitlines()[-1])
        except (ValueError, IndexError):
            staged = 0
        if not copy_result.success or staged <= 0:
            self.emit("warn", f"{log_dir}: copying recent logs staged no files; not included")
            return "copy_failed"
        return "copied"

    def _step_download_to_laptop(self) -> Dict[str, Any]:
        """Step 4: Download archive to local system."""
        self.emit("info", "Step 4: Downloading archive to laptop...")

        host = self._ssh_host()
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")
        archive_path = self._step_data.get("archive_path")

        if not archive_path:
            return {"success": False, "message": "No archive path available from previous step"}

        local_dir = self._script_runner.get_local_dir()
        local_path = str(local_dir / self._step_data.get("archive_name", "log_bundle.tar.gz"))

        result = self._script_runner.download_from_remote(host, user, password, archive_path, local_path)

        if not result.success:
            return {
                "success": False,
                "message": f"Download failed: {result.error}",
            }

        self._step_data["local_path"] = local_path
        self._step_data["archive_size"] = result.size_bytes

        return {
            "success": True,
            "message": f"Downloaded to: {local_path}",
            "details": f"Size: {result.size_bytes:,} bytes",
        }

    def _step_verify_contents(self) -> Dict[str, Any]:
        """Step 5: Verify archive integrity and contents."""
        self.emit("info", "Step 5: Verifying archive contents...")

        local_path = self._step_data.get("local_path")
        if not local_path or not Path(local_path).exists():
            return {"success": False, "message": "Archive file not found"}

        import subprocess

        # List archive contents
        try:
            result = subprocess.run(["tar", "-tzf", local_path], capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                return {
                    "success": False,
                    "message": "Archive verification failed",
                    "details": result.stderr,
                }

            files = result.stdout.strip().split("\n")
            file_count = len(files)

            # Save verification results
            sources = self._step_data.get("log_sources", {})
            not_collected = [src for src, state in sources.items() if state != "copied"]
            verification = {
                "timestamp": datetime.now().isoformat(),
                "archive_path": local_path,
                "file_count": file_count,
                "archive_size": self._step_data.get("archive_size", 0),
                "sample_files": files[:10],
                "cluster_ip": self._credentials.get("cluster_ip", ""),
                "sources": sources,
                "partial": bool(not_collected),
            }

            verification_file = Path(local_path).with_suffix(".verification.json")
            verification_file.write_text(json.dumps(verification, indent=2))

            message = f"Archive verified: {file_count} files"
            if not_collected:
                message += f" (partial: not collected {', '.join(not_collected)})"
            return {
                "success": True,
                "message": message,
                "details": f"Sample contents:\n" + "\n".join(files[:10]),
                "data": verification,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Archive verification timed out"}
        except Exception as e:
            return {"success": False, "message": f"Verification error: {str(e)}"}
