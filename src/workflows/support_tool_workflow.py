"""
VAST Support Tools Workflow

5-step workflow for running vast_support_tools.py diagnostics:
1. Download Script to CNode
2. Set Permissions
3. Run in VAST Container
4. Create Archive
5. Download to Laptop
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from script_runner import ScriptRunner
from utils.ssh_adapter import run_ssh_command
from utils.logger import get_logger

logger = get_logger(__name__)


class SupportToolWorkflow:
    """VAST Support Tools workflow for diagnostics collection."""

    name = "VAST Support Tools"
    description = "Run vast_support_tools.py for cluster diagnostics"
    enabled = True
    min_vast_version = "5.0"

    SCRIPT_URL = "https://vastdatasupport.blob.core.windows.net/support-tools/main/support/upgrade_checks/vast_support_tools.py"
    # REMOTE_SCRIPT_PATH now managed by ToolManager (/tmp/vast_scripts/)
    VMS_PATH = "/vast/data/vms.sh"
    CONTAINER_SCRIPT_PATH = "/vast/data/vast_support_tools.py"
    OUTPUT_DIR = "/vast/data/support-checks"

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
            {
                "id": 1,
                "name": "Download Script to CNode",
                "description": "Download vast_support_tools.py to /vast/data/",
            },
            {
                "id": 2,
                "name": "Set Permissions",
                "description": "Add execute permissions to the script",
            },
            {
                "id": 3,
                "name": "Run Support Tools",
                "description": "Execute vast_support_tools.py inspect inside VAST container",
            },
            {
                "id": 4,
                "name": "Create Archive",
                "description": "Create tarball of support-checks output",
            },
            {
                "id": 5,
                "name": "Download Results",
                "description": "SCP the tarball to local system",
            },
        ]

    def validate_prerequisites(self) -> tuple[bool, str]:
        required = ["cluster_ip", "node_user", "node_password"]
        missing = [k for k in required if not self._credentials.get(k)]
        if missing:
            return False, "Missing credentials: " + ", ".join(missing)
        return True, "Prerequisites met"

    def run_step(self, step_id: int) -> Dict[str, Any]:
        step_methods = {
            1: self._step_download_script,
            2: self._step_set_permissions,
            3: self._step_run_support_tools,
            4: self._step_create_archive,
            5: self._step_download_results,
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

    def _step_download_script(self) -> Dict[str, Any]:
        from tool_manager import ToolManager
        
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        # Validate credentials
        if not host:
            self.emit("error", "Cluster IP is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Cluster IP is required"}
        if not password:
            self.emit("error", "Node SSH Password is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Node SSH Password is required"}

        self.emit("info", "Deploying vast_support_tools.py to CNode...")
        self.emit("info", f"Target: {user}@{host}:{ToolManager.REMOTE_DIR}")
        self.emit("info", "")
        self.emit("info", "Strategy: Internet download first, local cache fallback")
        self.emit("info", "")

        tool_manager = ToolManager(output_callback=self._output_callback)
        
        success, message = tool_manager.deploy_tool_to_cnode("vast_support_tools.py", host, user, password)
        
        if not success:
            self.emit("error", f"Deployment failed: {message}")
            return {"success": False, "message": message}

        # Store the remote path for later steps
        self._step_data["remote_script_path"] = f"{ToolManager.REMOTE_DIR}/vast_support_tools.py"
        
        self.emit("success", f"Script deployed to {ToolManager.REMOTE_DIR}/vast_support_tools.py")
        return {"success": True, "message": "Script deployed successfully"}

    def _step_set_permissions(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        remote_script = self._step_data.get("remote_script_path", "/tmp/vast_scripts/vast_support_tools.py")

        # Copy script to /vast/data/ so it is visible inside the VMS container
        self.emit("info", "Copying script to container-accessible path...")
        copy_cmd = f"cp {remote_script} {self.CONTAINER_SCRIPT_PATH}"
        self.emit("info", f"$ ssh {user}@{host}")
        self.emit("info", f"$ {copy_cmd}")

        rc, stdout, stderr = run_ssh_command(host, user, password, copy_cmd, timeout=30)
        if rc != 0:
            self.emit("error", f"Copy failed: {stderr}")
            return {"success": False, "message": f"Failed to copy script to /vast/data/: {stderr}"}

        self.emit("success", f"Copied to {self.CONTAINER_SCRIPT_PATH}")

        # Set execute permissions on the container copy
        self.emit("info", "Setting execute permissions...")
        chmod_cmd = f"chmod +x {self.CONTAINER_SCRIPT_PATH}"
        self.emit("info", f"$ {chmod_cmd}")

        rc, stdout, stderr = run_ssh_command(host, user, password, chmod_cmd, timeout=30)
        if rc != 0:
            self.emit("error", f"chmod failed: {stderr}")
            return {"success": False, "message": f"Failed to set permissions: {stderr}"}

        # Verify
        verify_cmd = f"ls -la {self.CONTAINER_SCRIPT_PATH}"
        rc, stdout, _ = run_ssh_command(host, user, password, verify_cmd, timeout=10)
        if stdout:
            self.emit("info", stdout.strip())

        self.emit("success", "Script ready in container path")
        return {"success": True, "message": "Permissions set successfully"}

    def _step_run_support_tools(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        self.emit("info", "Running vast_support_tools.py inspect inside VAST container...")
        self.emit("info", "This may take several minutes...")
        self.emit("info", "")

        # Run inside VAST container using vms.sh with container-accessible path
        run_cmd = f"{self.VMS_PATH} {self.CONTAINER_SCRIPT_PATH} inspect"
        
        self.emit("info", f"$ ssh {user}@{host}")
        self.emit("info", f"$ {run_cmd}")
        self.emit("info", "")

        # This command can take a while, use longer timeout
        # force_tty=True is needed because vms.sh uses docker exec which requires a TTY
        rc, stdout, stderr = run_ssh_command(host, user, password, run_cmd, timeout=600, force_tty=True)

        # Show output
        output = stdout + stderr
        for line in output.strip().split("\n"):
            if line.strip():
                # Determine log level based on content
                ll = line.lower()
                if "error" in ll and "traceback" not in ll:
                    self.emit("error", line)
                elif "warning" in ll or "warn" in ll:
                    self.emit("warn", line)
                elif "success" in ll or "passed" in ll or "complete" in ll:
                    self.emit("success", line)
                else:
                    self.emit("info", line)

        self._step_data["support_tools_output"] = output

        if rc != 0:
            self.emit("warn", f"Command exited with code {rc}")
            # Don't fail - the tool may return non-zero for warnings
        
        self.emit("success", "Support tools inspection completed")
        return {"success": True, "message": "Support tools completed", "details": output}

    def _step_create_archive(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        self.emit("info", "Creating archive of support tools output...")

        # Get hostname for archive name
        rc, hostname, _ = run_ssh_command(host, user, password, "hostname", timeout=10)
        hostname = hostname.strip() if rc == 0 else "cnode"
        
        archive_name = f"{hostname}-support_tool_logs.tgz"
        archive_path = f"/userdata/{archive_name}"
        
        self._step_data["archive_name"] = archive_name
        self._step_data["archive_path"] = archive_path
        self._step_data["hostname"] = hostname

        # Find where support tools output was created
        # Check multiple possible locations
        possible_dirs = [
            "/vast/data/support-checks",
            "/tmp/vast_support_output",
            "/vast/data/support_checks",
            "/userdata/support-checks",
        ]
        
        output_dir = None
        for dir_path in possible_dirs:
            check_cmd = f"test -d {dir_path} && echo 'exists'"
            rc, stdout, _ = run_ssh_command(host, user, password, check_cmd, timeout=10)
            if "exists" in stdout:
                output_dir = dir_path
                self.emit("info", f"Found output directory: {output_dir}")
                break
        
        # If not found, look for recent directories created by the tool
        if not output_dir:
            self.emit("info", "Searching for support tool output...")
            find_cmd = "find /vast/data /tmp /userdata -maxdepth 2 -type d -name '*support*' 2>/dev/null | head -5"
            rc, stdout, _ = run_ssh_command(host, user, password, find_cmd, timeout=30)
            
            if stdout.strip():
                for line in stdout.strip().split("\n"):
                    if line.strip():
                        self.emit("info", f"  Found: {line.strip()}")
                # Use the first found directory
                output_dir = stdout.strip().split("\n")[0].strip()
        
        if not output_dir:
            # If still not found, check if the tool created any output
            self.emit("warn", "No support-checks directory found")
            self.emit("info", "Looking for any output from vast_support_tools.py...")
            
            # List what's in /vast/data
            list_cmd = "ls -la /vast/data/ 2>/dev/null | head -20"
            rc, stdout, _ = run_ssh_command(host, user, password, list_cmd, timeout=10)
            if stdout:
                self.emit("info", "/vast/data/ contents:")
                for line in stdout.strip().split("\n"):
                    self.emit("info", f"  {line}")
            
            return {"success": False, "message": "Support tools output directory not found. Check Step 3 output."}

        # Create tarball from the found directory
        tar_cmd = f"sudo tar cvfz {archive_path} {output_dir}/"
        
        self.emit("info", "")
        self.emit("info", f"$ ssh {user}@{host}")
        self.emit("info", f"$ {tar_cmd}")
        self.emit("info", "")

        rc, stdout, stderr = run_ssh_command(host, user, password, tar_cmd, timeout=120)

        # Show files being archived (filter out tar noise)
        file_count = 0
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if line and not line.startswith("tar:"):
                self.emit("info", f"  {line}")
                file_count += 1

        if rc != 0:
            # Check if it's just the "removing leading /" warning
            if "No such file" in stderr or "Cannot stat" in stderr:
                self.emit("error", f"Archive creation failed: {stderr}")
                return {"success": False, "message": f"Failed to create archive: {stderr}"}
            # tar may return non-zero for warnings but still succeed
            self.emit("warn", f"tar completed with warnings: {stderr}")

        # Verify archive exists and get size
        verify_cmd = f"ls -lh {archive_path}"
        rc, stdout, _ = run_ssh_command(host, user, password, verify_cmd, timeout=10)
        
        if rc == 0 and stdout:
            self.emit("info", "")
            self.emit("info", stdout.strip())
            self.emit("success", f"Archive created: {archive_path} ({file_count} files)")
            return {"success": True, "message": f"Archive created with {file_count} files"}
        else:
            return {"success": False, "message": "Archive file was not created"}

    def _step_download_results(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        archive_name = self._step_data.get("archive_name", "support_tool_logs.tgz")
        archive_path = self._step_data.get("archive_path", f"/userdata/{archive_name}")

        self.emit("info", "Downloading archive to local system...")

        # Get local output directory
        local_dir = self._script_runner.get_local_dir()
        local_path = local_dir / archive_name

        self.emit("info", f"Source: {user}@{host}:{archive_path}")
        self.emit("info", f"Target: {local_path}")
        self.emit("info", "")

        # Use SCP to download
        import paramiko
        from scp import SCPClient

        try:
            # Create SSH client
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, username=user, password=password, timeout=30)

            # SCP download
            self.emit("info", f"$ scp {user}@{host}:{archive_path} {local_path}")
            
            with SCPClient(ssh.get_transport()) as scp:
                scp.get(archive_path, str(local_path))

            ssh.close()

            # Verify download
            if local_path.exists():
                size = local_path.stat().st_size
                self.emit("success", f"Downloaded: {local_path}")
                self.emit("info", f"Size: {size:,} bytes ({size/1024/1024:.2f} MB)")
                
                self._step_data["local_archive"] = str(local_path)
                return {
                    "success": True,
                    "message": f"Downloaded {archive_name}",
                    "details": str(local_path),
                }
            else:
                return {"success": False, "message": "Download failed - file not found"}

        except Exception as e:
            self.emit("error", f"SCP failed: {e}")
            return {"success": False, "message": f"Download failed: {e}"}
