"""
Script Runner Module

Core infrastructure for downloading, copying, and executing scripts on remote hosts.
Provides secure credential handling and cross-platform compatibility.

This module is used by the Advanced Operations workflows to execute multi-step
validation scripts on VAST clusters.
"""

import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from utils.logger import get_logger
from utils.ssh_adapter import run_ssh_command

logger = get_logger(__name__)

IS_WINDOWS = platform.system() == "Windows"


@dataclass
class ScriptResult:
    """Result of a script execution."""

    success: bool
    returncode: int
    stdout: str
    stderr: str
    duration_ms: int
    error: Optional[str] = None


@dataclass
class FileTransferResult:
    """Result of a file transfer operation."""

    success: bool
    local_path: str
    remote_path: str
    size_bytes: int
    error: Optional[str] = None


class ScriptRunner:
    """
    Core infrastructure for script download, copy, and remote execution.

    Handles secure credential passing, API compatibility checks, and
    cross-platform file operations.
    """

    # Known script sources from VAST support
    SCRIPT_SOURCES = {
        "vnetmap.py": "https://vastdatasupport.blob.core.windows.net/support-tools/main/support/vnetperf/vnetmap.py",
        "mlnx_switch_api.py": "https://vastdatasupport.blob.core.windows.net/support-tools/main/support/vnetperf/mlnx_switch_api.py",
        "vast_support_tools.py": "https://support.vastdata.com/s/scripts/vast_support_tools.py",
        "vperfsanity": "https://support.vastdata.com/s/tools/vperfsanity.tar.gz",
    }

    # Default remote paths
    DEFAULT_REMOTE_DIR = "/tmp/vast_scripts"
    DEFAULT_LOCAL_DIR = "output/scripts"

    def __init__(
        self,
        output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None,
    ):
        """
        Initialize the ScriptRunner.

        Args:
            output_callback: Callback function for logging output (level, message, details)
        """
        self._output_callback = output_callback
        self._local_dir: Optional[Path] = None

    def _emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        """Emit output to the callback if set."""
        logger.log({"info": 20, "warn": 30, "error": 40, "success": 20, "debug": 10}.get(level, 20), message)
        if self._output_callback:
            try:
                self._output_callback(level, message, details)
            except Exception:
                pass

    def get_local_dir(self) -> Path:
        """Get the local directory for script storage."""
        if self._local_dir is None:
            from utils import get_data_dir

            self._local_dir = get_data_dir() / self.DEFAULT_LOCAL_DIR
            self._local_dir.mkdir(parents=True, exist_ok=True)
        return self._local_dir

    def check_prerequisites(self, host: str, username: str, password: str) -> Tuple[bool, str]:
        """
        Check that prerequisites are met for remote execution.

        Args:
            host: Remote host to check
            username: SSH username
            password: SSH password

        Returns:
            Tuple of (success, message)
        """
        self._emit("info", f"Checking prerequisites for {host}")

        # Check SSH connectivity
        rc, stdout, stderr = run_ssh_command(host, username, password, "echo OK", timeout=10)
        if rc != 0:
            error = stderr or "SSH connection failed"
            self._emit("error", f"SSH check failed: {error}")
            return False, f"Cannot connect to {host}: {error}"

        # Check for required directories
        rc, stdout, stderr = run_ssh_command(
            host, username, password, f"mkdir -p {self.DEFAULT_REMOTE_DIR} && echo OK", timeout=10
        )
        if rc != 0:
            self._emit("error", f"Cannot create remote directory: {stderr}")
            return False, f"Cannot create {self.DEFAULT_REMOTE_DIR} on {host}"

        self._emit("success", f"Prerequisites OK for {host}")
        return True, "Prerequisites met"

    def download_to_local(
        self,
        script_name: str,
        url: Optional[str] = None,
        force: bool = False,
    ) -> FileTransferResult:
        """
        Download a script from URL to local directory.

        Args:
            script_name: Name of the script file
            url: URL to download from (uses SCRIPT_SOURCES if not provided)
            force: Force re-download even if file exists

        Returns:
            FileTransferResult with download status
        """
        import time

        start_time = time.time()

        local_dir = self.get_local_dir()
        local_path = local_dir / script_name

        # Use default URL if not provided
        if url is None:
            url = self.SCRIPT_SOURCES.get(script_name)
            if url is None:
                return FileTransferResult(
                    success=False,
                    local_path=str(local_path),
                    remote_path="",
                    size_bytes=0,
                    error=f"No URL known for script: {script_name}",
                )

        # Check if already exists
        if local_path.exists() and not force:
            size = local_path.stat().st_size
            self._emit("info", f"Script already exists: {local_path} ({size} bytes)")
            return FileTransferResult(
                success=True,
                local_path=str(local_path),
                remote_path="",
                size_bytes=size,
            )

        # Show the equivalent wget command
        self._emit("info", f'$ wget "{url}" -O {script_name}')
        self._emit("info", f"--{time.strftime('%Y-%m-%d %H:%M:%S')}--  {url}")

        try:
            import requests
            from urllib.parse import urlparse

            # Parse URL for display
            parsed = urlparse(url)
            host = parsed.netloc

            self._emit("info", f"Resolving {host}...")

            response = requests.get(url, timeout=60, verify=True, stream=True)
            response.raise_for_status()

            self._emit("info", f"Connecting to {host}... connected.")
            self._emit("info", f"HTTP request sent, awaiting response... {response.status_code} {response.reason}")

            # Get content length if available
            content_length = response.headers.get("Content-Length", "unknown")
            content_type = response.headers.get("Content-Type", "application/octet-stream")

            self._emit("info", f"Length: {content_length} [{content_type}]")
            self._emit("info", f"Saving to: '{script_name}'")

            # Download content
            content = response.content
            local_path.write_bytes(content)
            size = len(content)

            duration_sec = time.time() - start_time
            speed_kbs = (size / 1024) / duration_sec if duration_sec > 0 else 0

            self._emit("info", "")
            self._emit(
                "info",
                f"{script_name}                 100%[===================>]  {size/1024:.2f}K  {speed_kbs:.0f}KB/s    in {duration_sec:.1f}s",
            )
            self._emit("info", "")
            self._emit(
                "success",
                f"{time.strftime('%Y-%m-%d %H:%M:%S')} ({speed_kbs:.0f} KB/s) - '{script_name}' saved [{size}/{size}]",
            )

            return FileTransferResult(
                success=True,
                local_path=str(local_path),
                remote_path="",
                size_bytes=size,
            )

        except Exception as e:
            error = str(e)
            self._emit("error", f"Download failed: {error}")
            return FileTransferResult(
                success=False,
                local_path=str(local_path),
                remote_path="",
                size_bytes=0,
                error=error,
            )

    def copy_to_remote(
        self,
        local_path: str,
        host: str,
        username: str,
        password: str,
        remote_dir: Optional[str] = None,
        set_executable: bool = True,
        skip_mkdir: bool = False,
    ) -> FileTransferResult:
        """
        Copy a local file to a remote host via SCP.

        Args:
            local_path: Path to local file
            host: Remote host
            username: SSH username
            password: SSH password
            remote_dir: Remote directory (uses DEFAULT_REMOTE_DIR if not provided)
            set_executable: Whether to chmod +x the file after copy

        Returns:
            FileTransferResult with transfer status
        """
        import time

        start_time = time.time()

        local_file = Path(local_path)
        if not local_file.exists():
            return FileTransferResult(
                success=False,
                local_path=local_path,
                remote_path="",
                size_bytes=0,
                error=f"Local file not found: {local_path}",
            )

        remote_dir = remote_dir or self.DEFAULT_REMOTE_DIR
        remote_path = f"{remote_dir}/{local_file.name}"

        try:
            size = local_file.stat().st_size

            # Create remote directory if not skipped
            if not skip_mkdir:
                mkdir_cmd = f"mkdir -p {remote_dir}"
                self._emit("info", f"$ ssh {username}@{host} '{mkdir_cmd}'")
                rc, stdout, stderr = run_ssh_command(host, username, password, mkdir_cmd, timeout=10)
                if rc == 0:
                    self._emit("success", f"Directory ready: {remote_dir}")
                else:
                    self._emit("warn", stderr.strip() if stderr else "mkdir warning")

            # Show SCP command like terminal
            self._emit("info", f"$ scp {local_path} {username}@{host}:{remote_path}")
            self._emit("info", f"{local_file.name}                 100%   {size/1024:.1f}KB")

            # Use SCP for file transfer
            if IS_WINDOWS:
                # Use paramiko for Windows
                success = self._paramiko_scp(local_path, host, username, password, remote_path)
            else:
                # Use scp command on Unix
                success = self._subprocess_scp(local_path, host, username, password, remote_path)

            if not success:
                self._emit("error", "scp: Transfer failed")
                return FileTransferResult(
                    success=False,
                    local_path=local_path,
                    remote_path=remote_path,
                    size_bytes=0,
                    error="SCP transfer failed",
                )

            # Set executable permission if requested
            if set_executable:
                chmod_cmd = f"chmod +x {remote_path}"
                self._emit("info", f"$ ssh {username}@{host} '{chmod_cmd}'")
                rc, _, stderr = run_ssh_command(host, username, password, chmod_cmd, timeout=10)
                if rc == 0:
                    self._emit("success", "Executable permission set")
                else:
                    self._emit("warn", stderr.strip() if stderr else "chmod warning")

            duration_sec = time.time() - start_time
            self._emit("success", f"Transfer complete: {size} bytes in {duration_sec:.2f}s")

            return FileTransferResult(
                success=True,
                local_path=local_path,
                remote_path=remote_path,
                size_bytes=size,
            )

        except Exception as e:
            error = str(e)
            self._emit("error", f"Copy failed: {error}")
            return FileTransferResult(
                success=False,
                local_path=local_path,
                remote_path=remote_path,
                size_bytes=0,
                error=error,
            )

    def _subprocess_scp(
        self,
        local_path: str,
        host: str,
        username: str,
        password: str,
        remote_path: str,
    ) -> bool:
        """SCP transfer using subprocess and sshpass.

        Uses SSHPASS env var (sshpass -e) to avoid exposing password in
        the process table.
        """
        env = self._augmented_env()
        env["SSHPASS"] = password

        if not shutil.which("sshpass", path=env.get("PATH")):
            logger.warning("sshpass not found, falling back to paramiko")
            return self._paramiko_scp(local_path, host, username, password, remote_path)

        cmd = [
            "sshpass",
            "-e",
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=30",
            local_path,
            f"{username}@{host}:{remote_path}",
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"SCP failed: {e}")
            return False

    def _paramiko_scp(
        self,
        local_path: str,
        host: str,
        username: str,
        password: str,
        remote_path: str,
    ) -> bool:
        """SCP transfer using paramiko SFTP."""
        try:
            import paramiko
        except ImportError:
            logger.error("paramiko not installed")
            return False

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                host,
                username=username,
                password=password,
                timeout=30,
                banner_timeout=30,
                look_for_keys=False,
                allow_agent=False,
            )

            sftp = client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            client.close()

            return True
        except Exception as e:
            logger.error(f"Paramiko SCP failed: {e}")
            return False

    def _augmented_env(self) -> dict:
        """Return env with PATH augmented for Homebrew tool locations."""
        env = os.environ.copy()
        extra = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
        existing = env.get("PATH", "")
        for p in extra:
            if p not in existing:
                existing = f"{p}:{existing}"
        env["PATH"] = existing
        return env

    def _classify_output_line(self, line: str) -> Optional[str]:
        """Classify a remote command output line for appropriate log level.

        Returns None for lines that should be completely suppressed (SSH key
        retry tracebacks, CalledProcessError details, key dictionaries).
        These are internal retry mechanisms in tools like vnetmap.py and
        provide no actionable information to the user.

        Returns 'warn' for actual failure indicators that the user should see.
        Returns 'info' for normal output.
        """
        ll = line.lower().strip()
        if not ll:
            return "info"

        # --- Suppress entirely: SSH key retry noise ---
        # Traceback blocks
        if ll.startswith("traceback (most recent call last"):
            return None
        # Traceback file references
        if ll.startswith("file ") and ", line " in ll and ", in " in ll:
            return None
        # CalledProcessError / subprocess error lines
        if "calledprocesserror" in ll or "subprocess.calledprocesserror" in ll:
            return None
        if "returned non-zero exit status" in ll and "command" not in ll[:20]:
            return None
        # SSH key retry {ERROR} lines for sudo /bin/true checks
        if "{error}" in ll and "general exception" in ll and "sudo /bin/true" in ll:
            return None
        # SSH key dict lines like {'SSH_KEY1': ...}
        if ll.startswith("{'ssh_key"):
            return None
        # return subprocess.check_output lines (inside tracebacks)
        if ll.startswith("return subprocess.check_output"):
            return None
        if ll.startswith("**kwargs"):
            return None
        if ll.startswith("output=stdout"):
            return None

        # --- Condense: SSH retry info to brief summary ---
        if "ssh check failed with" in ll and "retrying" in ll:
            return "info"  # Keep but as info (brief retry notice)
        if "try again using" in ll:
            return None  # Suppress individual retry attempts
        if "ssh check" in ll and "works for" in ll:
            return "info"  # Keep the success message

        # --- Info: zero-count failure summaries are not warnings ---
        if "failed:" in ll:
            idx = ll.index("failed:")
            after = ll[idx + 7:].lstrip()
            if after.startswith("0"):
                return "info"

        # --- Warn: actual failures the user should know about ---
        if "{error}" in ll and "general exception" in ll:
            return "warn"
        if "failed getting data from" in ll:
            return "warn"
        if "failed nodes:" in ll:
            return "warn"
        if ll.startswith("172.") and "failed" in ll:
            return "warn"
        if "failed:" in ll:
            idx = ll.index("failed:")
            after = ll[idx + 7:].lstrip()
            if after and after[0] in "123456789":
                return "warn"

        return "info"

    def execute_remote(
        self,
        host: str,
        username: str,
        password: str,
        command: str,
        timeout: int = 300,
        working_dir: Optional[str] = None,
    ) -> ScriptResult:
        """
        Execute a command on a remote host.

        Args:
            host: Remote host
            username: SSH username
            password: SSH password
            command: Command to execute
            timeout: Command timeout in seconds
            working_dir: Working directory for command execution

        Returns:
            ScriptResult with execution status
        """
        import time

        start_time = time.time()

        # Prepend cd if working_dir specified
        if working_dir:
            command = f"cd {working_dir} && {command}"

        # Show full SSH command like terminal
        self._emit("info", f"$ ssh {username}@{host}")
        self._emit("info", f"{username}@{host}:~$ {command}")
        self._emit("info", "")

        try:
            rc, stdout, stderr = run_ssh_command(host, username, password, command, timeout=timeout)
            duration_sec = time.time() - start_time

            success = rc == 0
            level = "success" if success else "error"

            # Show output with intelligent level classification
            if stdout:
                for line in stdout.strip().split("\n"):
                    line_level = self._classify_output_line(line)
                    if line_level is not None:
                        self._emit(line_level, line)
            if stderr:
                for line in stderr.strip().split("\n"):
                    self._emit("warn" if success else "error", line)

            self._emit("info", "")
            result_level = "success" if success else "error"
            self._emit(result_level, f"{username}@{host}:~$ echo $?")
            self._emit(result_level, str(rc))
            self._emit("info", f"[Command completed in {duration_sec:.2f}s]")

            return ScriptResult(
                success=success,
                returncode=rc,
                stdout=stdout,
                stderr=stderr,
                duration_ms=int(duration_sec * 1000),
            )

        except Exception as e:
            duration = int((time.time() - start_time) * 1000)
            error = str(e)
            self._emit("error", f"Execution failed: {error}")

            return ScriptResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=error,
                duration_ms=duration,
                error=error,
            )

    def execute_remote_persistent(
        self,
        host: str,
        username: str,
        password: str,
        command: str,
        timeout: int = 600,
        working_dir: Optional[str] = None,
        workflow_id: str = "workflow",
    ) -> ScriptResult:
        """
        Execute a command on a remote host using a persistent tmux session.

        This method is preferred for long-running commands as it:
        - Survives network disconnections
        - Captures full output to a log file
        - Allows reconnection if needed
        - Automatically cleans up when done

        Args:
            host: Remote host
            username: SSH username
            password: SSH password
            command: Command to execute
            timeout: Command timeout in seconds (default 10 minutes)
            working_dir: Working directory for command execution
            workflow_id: ID for naming the session

        Returns:
            ScriptResult with execution status
        """
        from session_manager import SessionManager

        session_mgr = SessionManager(output_callback=self._output_callback)

        # Check tmux availability
        self._emit("info", f"$ ssh {username}@{host} 'which tmux'")
        tmux_ok, tmux_msg = session_mgr.check_tmux_available(host, username, password)
        if not tmux_ok:
            self._emit("warn", "tmux not available, falling back to direct execution")
            return self.execute_remote(host, username, password, command, timeout, working_dir)

        self._emit("success", f"tmux found: {tmux_msg}")

        # Start the session
        success, msg, session_info = session_mgr.start_session(
            host=host,
            username=username,
            password=password,
            command=command,
            workflow_id=workflow_id,
            working_dir=working_dir,
        )

        if not success:
            return ScriptResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr=msg,
                duration_ms=0,
                error=msg,
            )

        # Wait for completion with streaming output
        result = session_mgr.wait_for_completion(
            host=host,
            username=username,
            password=password,
            session_info=session_info,
            timeout=timeout,
        )

        return ScriptResult(
            success=result.success,
            returncode=result.exit_code,
            stdout=result.stdout,
            stderr=result.stderr,
            duration_ms=result.duration_ms,
        )

    def download_from_remote(
        self,
        host: str,
        username: str,
        password: str,
        remote_path: str,
        local_path: Optional[str] = None,
    ) -> FileTransferResult:
        """
        Download a file from a remote host to local.

        Args:
            host: Remote host
            username: SSH username
            password: SSH password
            remote_path: Remote file path
            local_path: Local destination (auto-generated if not provided)

        Returns:
            FileTransferResult with transfer status
        """
        import time

        start_time = time.time()

        # Generate local path if not provided
        if local_path is None:
            local_dir = self.get_local_dir()
            filename = Path(remote_path).name
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            local_path = str(local_dir / f"{timestamp}_{filename}")

        self._emit("info", f"Downloading {remote_path} from {host}")

        try:
            if IS_WINDOWS:
                success = self._paramiko_download(host, username, password, remote_path, local_path)
            else:
                success = self._subprocess_download(host, username, password, remote_path, local_path)

            if not success:
                return FileTransferResult(
                    success=False, local_path=local_path, remote_path=remote_path, size_bytes=0, error="Download failed"
                )

            size = Path(local_path).stat().st_size
            duration = int((time.time() - start_time) * 1000)
            self._emit("success", f"Downloaded to {local_path} ({size} bytes) in {duration}ms")

            return FileTransferResult(
                success=True,
                local_path=local_path,
                remote_path=remote_path,
                size_bytes=size,
            )

        except Exception as e:
            error = str(e)
            self._emit("error", f"Download failed: {error}")
            return FileTransferResult(
                success=False,
                local_path=local_path,
                remote_path=remote_path,
                size_bytes=0,
                error=error,
            )

    def _subprocess_download(
        self,
        host: str,
        username: str,
        password: str,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """Download file using subprocess scp.

        Uses SSHPASS env var (sshpass -e) to avoid exposing password in
        the process table.
        """
        env = self._augmented_env()
        env["SSHPASS"] = password

        if not shutil.which("sshpass", path=env.get("PATH")):
            return self._paramiko_download(host, username, password, remote_path, local_path)

        cmd = [
            "sshpass",
            "-e",
            "scp",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            "UserKnownHostsFile=/dev/null",
            "-o",
            "ConnectTimeout=30",
            f"{username}@{host}:{remote_path}",
            local_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"SCP download failed: {e}")
            return False

    def _paramiko_download(
        self,
        host: str,
        username: str,
        password: str,
        remote_path: str,
        local_path: str,
    ) -> bool:
        """Download file using paramiko SFTP."""
        try:
            import paramiko
        except ImportError:
            logger.error("paramiko not installed")
            return False

        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(
                host,
                username=username,
                password=password,
                timeout=30,
                banner_timeout=30,
                look_for_keys=False,
                allow_agent=False,
            )

            sftp = client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            client.close()

            return True
        except Exception as e:
            logger.error(f"Paramiko download failed: {e}")
            return False

    def cleanup_remote(
        self,
        host: str,
        username: str,
        password: str,
        paths: List[str],
    ) -> bool:
        """
        Clean up files on remote host.

        Args:
            host: Remote host
            username: SSH username
            password: SSH password
            paths: List of paths to remove

        Returns:
            True if cleanup succeeded
        """
        self._emit("info", f"Cleaning up {len(paths)} files on {host}")

        success = True
        for path in paths:
            rc, _, stderr = run_ssh_command(host, username, password, f"rm -rf {path}", timeout=30)
            if rc != 0:
                self._emit("warn", f"Failed to remove {path}: {stderr}")
                success = False

        if success:
            self._emit("success", "Cleanup completed")
        return success
