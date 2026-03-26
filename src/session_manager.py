"""
Session Manager - tmux-based persistent session management for remote commands.

Provides:
- Persistent sessions that survive disconnections
- Output capture via log files
- Session status polling
- Automatic cleanup
"""

import time
import uuid
from dataclasses import dataclass
from typing import Optional, Tuple, List

from utils.ssh_adapter import run_ssh_command
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class SessionInfo:
    """Information about a tmux session."""

    session_name: str
    log_file: str
    host: str
    username: str
    started_at: float
    command: str


@dataclass
class SessionResult:
    """Result of a session execution."""

    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int
    session_name: str


class SessionManager:
    """
    Manages tmux sessions for long-running remote commands.
    """

    SESSION_PREFIX = "vast_asbuilt"
    DEFAULT_POLL_INTERVAL = 2.0
    DEFAULT_TIMEOUT = 600

    def __init__(self, output_callback=None):
        self._output_callback = output_callback
        self._active_sessions: dict[str, SessionInfo] = {}

    def _emit(self, level: str, message: str) -> None:
        """Emit output to callback."""
        if self._output_callback:
            try:
                self._output_callback(level, message, None)
            except Exception:
                pass
        logger.log({"info": 20, "warn": 30, "error": 40, "success": 20}.get(level, 20), message)

    def _generate_session_name(self, workflow_id: str) -> str:
        """Generate a unique session name."""
        short_id = uuid.uuid4().hex[:8]
        return f"{self.SESSION_PREFIX}_{workflow_id}_{short_id}"

    def _get_log_path(self, session_name: str) -> str:
        """Get the log file path for a session."""
        return f"/tmp/{session_name}.log"

    def check_tmux_available(self, host: str, username: str, password: str) -> Tuple[bool, str]:
        """Check if tmux is available on the remote host."""
        rc, stdout, stderr = run_ssh_command(host, username, password, "which tmux", timeout=10)
        if rc == 0:
            return True, stdout.strip()
        return False, "tmux not found on remote host"

    def start_session(
        self,
        host: str,
        username: str,
        password: str,
        command: str,
        workflow_id: str = "workflow",
        working_dir: Optional[str] = None,
    ) -> Tuple[bool, str, SessionInfo]:
        """
        Start a new tmux session with the given command.
        """
        session_name = self._generate_session_name(workflow_id)
        log_file = self._get_log_path(session_name)

        # Build the full command with working directory
        if working_dir:
            full_cmd = f"cd {working_dir} && {command}"
        else:
            full_cmd = command

        self._emit("info", f"$ tmux new-session -d -s {session_name}")
        self._emit("info", f"  Command: {command}")
        self._emit("info", f"  Log file: {log_file}")

        # Write command to a temp script file on remote host to avoid escaping issues
        # This ensures proper shell expansion of variables and command substitutions
        script_file = f"/tmp/{session_name}_cmd.sh"

        # Create the wrapper script using heredoc
        # The script runs the command and records the exit code
        create_script_cmd = f"""cat > {script_file} << 'VAST_CMD_EOF'
#!/bin/bash
{full_cmd}
echo "__EXITCODE__=$?"
VAST_CMD_EOF
chmod +x {script_file}"""

        rc, _, stderr = run_ssh_command(host, username, password, create_script_cmd, timeout=30)
        if rc != 0:
            self._emit("error", f"Failed to create command script: {stderr}")
            return False, f"Failed to create script: {stderr}", None

        # Run tmux with simple output redirection
        # The script outputs everything including the exit code marker to the log file
        tmux_cmd = f"tmux new-session -d -s {session_name} 'bash {script_file} > {log_file} 2>&1'"

        rc, stdout, stderr = run_ssh_command(host, username, password, tmux_cmd, timeout=30)

        if rc != 0:
            self._emit("error", f"Failed to start tmux session: {stderr}")
            return False, f"Failed to start session: {stderr}", None

        session_info = SessionInfo(
            session_name=session_name,
            log_file=log_file,
            host=host,
            username=username,
            started_at=time.time(),
            command=command,
        )
        self._active_sessions[session_name] = session_info

        self._emit("success", f"Session started: {session_name}")
        return True, session_name, session_info

    def is_session_running(self, host: str, username: str, password: str, session_name: str) -> bool:
        """Check if a tmux session is still running."""
        check_cmd = f"tmux has-session -t {session_name} 2>/dev/null && echo 'running' || echo 'done'"
        rc, stdout, _ = run_ssh_command(host, username, password, check_cmd, timeout=10)
        return "running" in stdout.lower()

    def get_session_output(
        self,
        host: str,
        username: str,
        password: str,
        log_file: str,
        tail_lines: Optional[int] = None,
    ) -> Tuple[str, Optional[int]]:
        """
        Get the current output from a session's log file.

        Returns:
            Tuple of (output, exit_code or None if not complete)
        """
        if tail_lines:
            cmd = f"tail -n {tail_lines} {log_file} 2>/dev/null"
        else:
            cmd = f"cat {log_file} 2>/dev/null"

        rc, stdout, _ = run_ssh_command(host, username, password, cmd, timeout=30)

        # Check for exit code marker
        exit_code = None
        if "__EXITCODE__=" in stdout:
            for line in stdout.split("\n"):
                if "__EXITCODE__=" in line:
                    try:
                        exit_code = int(line.split("=")[1].strip())
                    except (ValueError, IndexError):
                        pass

        return stdout, exit_code

    def wait_for_completion(
        self,
        host: str,
        username: str,
        password: str,
        session_info: SessionInfo,
        timeout: int = None,
        poll_interval: float = None,
    ) -> SessionResult:
        """
        Wait for a session to complete and return the result.
        """
        timeout = timeout or self.DEFAULT_TIMEOUT
        poll_interval = poll_interval or self.DEFAULT_POLL_INTERVAL
        session_name = session_info.session_name
        log_file = session_info.log_file

        start_time = time.time()
        last_output_len = 0
        last_output = ""
        exit_code = None

        self._emit("info", f"Waiting for session {session_name} to complete...")
        self._emit("info", "─" * 60)

        while True:
            elapsed = time.time() - start_time

            # Check timeout
            if elapsed > timeout:
                self._emit("error", f"Session timed out after {timeout}s")
                self.kill_session(host, username, password, session_name)
                return SessionResult(
                    success=False,
                    exit_code=-1,
                    stdout=last_output,
                    stderr=f"Timeout after {timeout}s",
                    duration_ms=int(elapsed * 1000),
                    session_name=session_name,
                )

            # Get current output
            output, exit_code = self.get_session_output(host, username, password, log_file)

            # Stream new output
            if len(output) > last_output_len:
                new_output = output[last_output_len:]
                for line in new_output.strip().split("\n"):
                    # Skip exit code marker
                    if line and "__EXITCODE__" not in line:
                        # Clean control characters
                        clean_line = line.replace("\r", "")
                        if clean_line.strip():
                            self._emit("info", clean_line)
                last_output_len = len(output)
                last_output = output

            # Check if complete
            if exit_code is not None:
                break

            # Also check if session is still running
            if not self.is_session_running(host, username, password, session_name):
                # Session ended, get final output
                time.sleep(0.5)
                output, exit_code = self.get_session_output(host, username, password, log_file)
                last_output = output
                if exit_code is None:
                    exit_code = 0
                break

            time.sleep(poll_interval)

        duration_ms = int((time.time() - start_time) * 1000)

        # Clean output - remove exit code line
        clean_lines = []
        for line in last_output.split("\n"):
            if "__EXITCODE__" in line:
                continue
            clean_line = line.replace("\r", "").strip()
            if clean_line:
                clean_lines.append(clean_line)

        clean_output = "\n".join(clean_lines)

        self._emit("info", "─" * 60)
        self._emit(
            "success" if exit_code == 0 else "error",
            f"Session completed with exit code {exit_code} in {duration_ms}ms",
        )

        # Cleanup
        self.cleanup_session(host, username, password, session_name, log_file)

        return SessionResult(
            success=(exit_code == 0),
            exit_code=exit_code,
            stdout=clean_output,
            stderr="",
            duration_ms=duration_ms,
            session_name=session_name,
        )

    def kill_session(self, host: str, username: str, password: str, session_name: str) -> bool:
        """Kill a tmux session."""
        kill_cmd = f"tmux kill-session -t {session_name} 2>/dev/null"
        self._emit("info", f"$ {kill_cmd}")
        rc, _, _ = run_ssh_command(host, username, password, kill_cmd, timeout=10)
        if session_name in self._active_sessions:
            del self._active_sessions[session_name]
        return bool(rc == 0)

    def cleanup_session(self, host: str, username: str, password: str, session_name: str, log_file: str) -> bool:
        """Clean up a session and its log file."""
        # Kill session if still exists
        self.kill_session(host, username, password, session_name)

        # Remove log file and script file
        script_file = f"/tmp/{session_name}_cmd.sh"
        rm_cmd = f"rm -f {log_file} {script_file}"
        self._emit("info", f"$ {rm_cmd}")
        run_ssh_command(host, username, password, rm_cmd, timeout=10)

        self._emit("success", f"Session {session_name} cleaned up")
        return True

    def list_sessions(self, host: str, username: str, password: str) -> List[str]:
        """List all vast_asbuilt sessions on the remote host."""
        list_cmd = f"tmux list-sessions 2>/dev/null | grep '{self.SESSION_PREFIX}' | cut -d: -f1"
        rc, stdout, _ = run_ssh_command(host, username, password, list_cmd, timeout=10)
        if rc != 0 or not stdout.strip():
            return []
        return [s.strip() for s in stdout.strip().split("\n") if s.strip()]

    def cleanup_all_sessions(self, host: str, username: str, password: str) -> int:
        """Clean up all vast_asbuilt sessions on the remote host."""
        sessions = self.list_sessions(host, username, password)
        cleaned = 0
        for session_name in sessions:
            log_file = self._get_log_path(session_name)
            if self.cleanup_session(host, username, password, session_name, log_file):
                cleaned += 1
        self._emit("info", f"Cleaned up {cleaned} sessions")
        return cleaned
