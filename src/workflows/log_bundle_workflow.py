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
    # Intentional [B108]: staging directory on the remote VAST CNode (populated via SSH), not a local tempfile.
    BUNDLE_DIR = "/tmp/vast_log_bundle"  # nosec B108

    def __init__(self):
        self._output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._credentials: Dict[str, Any] = {}
        self._script_runner: Optional[ScriptRunner] = None
        self._step_data: Dict[str, Any] = {}

    def set_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        self._output_callback = callback
        if self._script_runner:
            self._script_runner._output_callback = callback

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

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
            self._script_runner = ScriptRunner(output_callback=self._output_callback)

        try:
            return method()
        except Exception as e:
            logger.exception(f"Step {step_id} failed")
            return {"success": False, "message": str(e)}

    def _step_discover_sizes(self) -> Dict[str, Any]:
        """Step 1: Discover log sizes on CNode."""
        self.emit("info", "Step 1: Discovering log sizes...")

        host = self._credentials.get("cluster_ip")
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

        self._step_data["log_sizes"] = sizes
        self._step_data["total_size_mb"] = total_size

        size_warning = ""
        if total_size > 1024:
            size_warning = f"\nWARNING: Total size exceeds 1GB ({total_size:.0f} MB)"

        return {
            "success": True,
            "message": f"Discovered {len(sizes)} log directories, total ~{total_size:.0f} MB",
            "details": "\n".join(size_details) + size_warning,
            "data": {"sizes": sizes, "total_mb": total_size},
        }

    def _step_confirm_collection(self) -> Dict[str, Any]:
        """Step 2: Confirm collection based on discovered sizes."""
        self.emit("info", "Step 2: Confirming log collection...")

        total_size = self._step_data.get("total_size_mb", 0)

        # Check if size is reasonable
        if total_size > 5120:  # 5GB limit
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

        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_name = f"vast_log_bundle_{timestamp}.tar.gz"
        # Intentional [B108]: archive is created on the remote CNode with a timestamped name, not a local tempfile.
        archive_path = f"/tmp/{archive_name}"  # nosec B108

        # Create bundle directory and copy logs
        self._script_runner.execute_remote(host, user, password, f"sudo mkdir -p {self.BUNDLE_DIR}", timeout=30)

        # Copy logs to bundle directory
        for log_dir in self.LOG_DIRS:
            cmd = f"sudo cp -r {log_dir} {self.BUNDLE_DIR}/ 2>/dev/null || true"
            self._script_runner.execute_remote(host, user, password, cmd, timeout=120)

        # Create archive
        cmd = f"sudo tar -czf {archive_path} -C {self.BUNDLE_DIR} . 2>&1"
        result = self._script_runner.execute_remote(host, user, password, cmd, timeout=600)

        if not result.success:
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

        return {
            "success": True,
            "message": f"Created archive: {archive_name}",
            "details": f"Size: {size_result.stdout.strip() if size_result.success else 'unknown'}",
        }

    def _step_download_to_laptop(self) -> Dict[str, Any]:
        """Step 4: Download archive to local system."""
        self.emit("info", "Step 4: Downloading archive to laptop...")

        host = self._credentials.get("cluster_ip")
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
            verification = {
                "timestamp": datetime.now().isoformat(),
                "archive_path": local_path,
                "file_count": file_count,
                "archive_size": self._step_data.get("archive_size", 0),
                "sample_files": files[:10],
                "cluster_ip": self._credentials.get("cluster_ip", ""),
            }

            verification_file = Path(local_path).with_suffix(".verification.json")
            verification_file.write_text(json.dumps(verification, indent=2))

            return {
                "success": True,
                "message": f"Archive verified: {file_count} files",
                "details": f"Sample contents:\n" + "\n".join(files[:10]),
                "data": verification,
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "message": "Archive verification timed out"}
        except Exception as e:
            return {"success": False, "message": f"Verification error: {str(e)}"}
