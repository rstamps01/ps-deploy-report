"""
Tool Manager - Manages deployment tools with local caching and smart deployment.

Features:
- Downloads and caches tools locally
- Deploys to CNode (internet-first, local fallback)
- Update tools button support
"""

import os
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.ssh_adapter import run_ssh_command
from utils.logger import get_logger

logger = get_logger(__name__)


class ToolManager:
    """Manages deployment tools with local caching and smart deployment."""

    # Tool definitions with download URLs
    TOOLS: Dict[str, Dict[str, Any]] = {
        "vnetmap.py": {
            "url": "https://vastdatasupport.blob.core.windows.net/support-tools/main/support/vnetperf/vnetmap.py",
            "description": "Network topology validation tool",
        },
        "mlnx_switch_api.py": {
            "url": "https://vastdatasupport.blob.core.windows.net/support-tools/main/support/vnetperf/mlnx_switch_api.py",
            "description": "Mellanox switch API helper",
        },
        "vast_support_tools.py": {
            "url": "https://vastdatasupport.blob.core.windows.net/support-tools/main/support/upgrade_checks/vast_support_tools.py",
            "description": "VAST support diagnostics tool",
        },
        "vperfsanity-latest-stable.tar.gz": {
            "url": "http://vast-vperfsanity.s3.amazonaws.com/download/vperfsanity-latest-stable.tar.gz",
            "description": "Performance validation test suite",
            "is_archive": True,
        },
    }

    REMOTE_DIR = "/tmp/vast_scripts"

    def __init__(self, output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None):
        self._output_callback = output_callback
        self._local_tools_dir = self._get_local_tools_dir()
        self._ensure_local_dir()

    def _get_local_tools_dir(self) -> Path:
        """Get the local tools storage directory."""
        # Store in output/tools directory
        base_dir = Path(__file__).parent.parent / "output" / "tools"
        return base_dir

    def _ensure_local_dir(self) -> None:
        """Ensure local tools directory exists."""
        self._local_tools_dir.mkdir(parents=True, exist_ok=True)

    def _emit(self, level: str, message: str) -> None:
        """Emit output to callback, or fall back to the Python logger."""
        if self._output_callback:
            try:
                self._output_callback(level, message, None)
            except Exception:
                pass
        else:
            logger.log({"info": 20, "warn": 30, "error": 40, "success": 20, "debug": 10}.get(level, 20), message)

    def get_local_tool_path(self, tool_name: str) -> Path:
        """Get the local path for a tool."""
        return self._local_tools_dir / tool_name

    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a tool."""
        if tool_name not in self.TOOLS:
            return None

        local_path = self.get_local_tool_path(tool_name)
        info = {
            "name": tool_name,
            "url": self.TOOLS[tool_name]["url"],
            "description": self.TOOLS[tool_name]["description"],
            "local_path": str(local_path),
            "cached": local_path.exists(),
        }

        if local_path.exists():
            stat = local_path.stat()
            info["cached_size"] = stat.st_size
            info["cached_date"] = datetime.fromtimestamp(stat.st_mtime).isoformat()

        return info

    def get_all_tools_info(self) -> List[Dict[str, Any]]:
        """Get information about all tools."""
        return [self.get_tool_info(name) for name in self.TOOLS.keys()]

    def update_local_tool(self, tool_name: str) -> Tuple[bool, str]:
        """Download the latest version of a tool to local cache."""
        if tool_name not in self.TOOLS:
            return False, f"Unknown tool: {tool_name}"

        url = self.TOOLS[tool_name]["url"]
        local_path = self.get_local_tool_path(tool_name)

        self._emit("info", f"Downloading {tool_name}...")
        self._emit("info", f"  URL: {url}")

        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()

            # Save to local cache
            local_path.write_bytes(response.content)
            size = len(response.content)

            self._emit("success", f"  Saved: {local_path}")
            self._emit("info", f"  Size: {size:,} bytes")

            return True, f"Downloaded {tool_name} ({size:,} bytes)"

        except requests.RequestException as e:
            self._emit("error", f"  Download failed: {e}")
            return False, f"Download failed: {e}"

    def update_all_tools(self) -> Dict[str, Any]:
        """Update all tools in local cache."""
        results: Dict[str, Any] = {"success": True, "tools": {}, "updated": 0, "failed": 0}

        self._emit("info", "═" * 60)
        self._emit("info", "Updating Deployment Tools")
        self._emit("info", "═" * 60)

        for tool_name in self.TOOLS.keys():
            self._emit("info", "")
            success, message = self.update_local_tool(tool_name)
            results["tools"][tool_name] = {"success": success, "message": message}

            if success:
                results["updated"] += 1
            else:
                results["failed"] += 1
                results["success"] = False

        self._emit("info", "")
        self._emit("info", "─" * 60)
        self._emit(
            "success" if results["success"] else "warn",
            f"Updated {results['updated']}/{len(self.TOOLS)} tools",
        )

        return results

    def _ensure_remote_dir(self, host: str, username: str, password: str) -> Tuple[bool, str]:
        """Ensure the remote directory exists on the CNode."""
        mkdir_cmd = f"mkdir -p {self.REMOTE_DIR}"
        self._emit("info", f"Ensuring remote directory exists: {self.REMOTE_DIR}")

        rc, stdout, stderr = run_ssh_command(host, username, password, mkdir_cmd, timeout=30)
        if rc != 0:
            error_msg = stderr or stdout or "SSH command failed"
            return False, f"Failed to create directory: {error_msg}"

        self._emit("success", f"Remote directory ready: {self.REMOTE_DIR}")
        return True, "Directory ready"

    def deploy_tool_to_cnode(
        self,
        tool_name: str,
        host: str,
        username: str,
        password: str,
        skip_mkdir: bool = False,
    ) -> Tuple[bool, str]:
        """
        Deploy a tool to CNode.

        Strategy:
        1. Ensure remote directory exists (once)
        2. Try to download directly to CNode from internet
        3. If that fails, copy from local cache to CNode
        """
        if tool_name not in self.TOOLS:
            return False, f"Unknown tool: {tool_name}"

        url = self.TOOLS[tool_name]["url"]
        remote_path = f"{self.REMOTE_DIR}/{tool_name}"
        local_path = self.get_local_tool_path(tool_name)

        self._emit("info", f"Deploying {tool_name} to CNode...")

        # Step 1: Ensure remote directory exists (unless already done)
        if not skip_mkdir:
            success, msg = self._ensure_remote_dir(host, username, password)
            if not success:
                return False, msg

        # Step 2: Try to download directly to CNode
        self._emit("info", f"  Attempting direct download to CNode...")
        wget_cmd = f'wget -q "{url}" -O {remote_path} 2>&1'

        rc, stdout, stderr = run_ssh_command(host, username, password, wget_cmd, timeout=60)

        if rc == 0:
            # Verify file exists and has content
            check_cmd = f"test -s {remote_path} && echo 'ok'"
            rc2, stdout2, _ = run_ssh_command(host, username, password, check_cmd, timeout=10)

            if "ok" in stdout2:
                self._emit("success", f"  Downloaded directly to CNode: {remote_path}")
                # Set executable
                run_ssh_command(host, username, password, f"chmod +x {remote_path}", timeout=10)
                return True, f"Downloaded {tool_name} directly to CNode"

        # Step 3: Fallback to local copy
        self._emit("warn", f"  Direct download failed, using local cache...")

        if not local_path.exists():
            self._emit("error", f"  Local cache not found: {local_path}")
            self._emit("info", "  Run 'Update Deployment Tools' first")
            return False, f"Tool not in local cache. Update tools first."

        # Use SCP to copy from local to CNode
        self._emit("info", f"  Copying from local cache...")

        try:
            import paramiko  # type: ignore[import-untyped]
            from scp import SCPClient

            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(
                host,
                username=username,
                password=password,
                timeout=30,
                banner_timeout=30,
                look_for_keys=False,
                allow_agent=False,
            )

            with SCPClient(ssh.get_transport()) as scp:
                scp.put(str(local_path), remote_path)

            ssh.close()

            # Set executable
            run_ssh_command(host, username, password, f"chmod +x {remote_path}", timeout=10)

            self._emit("success", f"  Copied from local cache: {remote_path}")
            return True, f"Copied {tool_name} from local cache"

        except Exception as e:
            self._emit("error", f"  SCP failed: {e}")
            return False, f"Failed to copy tool: {e}"

    def deploy_all_tools_to_cnode(
        self,
        host: str,
        username: str,
        password: str,
        tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Deploy multiple tools to CNode."""
        if tools is None:
            tools = list(self.TOOLS.keys())

        results: Dict[str, Any] = {"success": True, "tools": {}, "deployed": 0, "failed": 0}

        self._emit("info", f"Deploying {len(tools)} tools to {username}@{host}:{self.REMOTE_DIR}")
        self._emit("info", "")

        # Create remote directory once before deploying any tools
        dir_success, dir_msg = self._ensure_remote_dir(host, username, password)
        if not dir_success:
            self._emit("error", f"Failed to create remote directory: {dir_msg}")
            results["success"] = False
            return results

        self._emit("info", "")

        for tool_name in tools:
            # skip_mkdir=True since we already created the directory
            success, message = self.deploy_tool_to_cnode(tool_name, host, username, password, skip_mkdir=True)
            results["tools"][tool_name] = {"success": success, "message": message}

            if success:
                results["deployed"] += 1
            else:
                results["failed"] += 1
                results["success"] = False

            self._emit("info", "")

        self._emit("info", "─" * 60)
        self._emit(
            "success" if results["success"] else "warn",
            f"Deployed {results['deployed']}/{len(tools)} tools",
        )

        return results
