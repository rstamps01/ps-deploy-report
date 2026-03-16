"""
Cross-platform SSH adapter.

Provides a unified interface for running remote commands over SSH:
  - macOS / Linux: uses subprocess (ssh binary) with pexpect for interactive sessions
  - Windows: uses paramiko (pure-Python SSH) for all sessions

Usage:
    from utils.ssh_adapter import run_ssh_command, run_interactive_ssh

    rc, stdout, stderr = run_ssh_command(host, user, password, "show version")
    rc, stdout, stderr = run_interactive_ssh(host, user, password, "show mac-address-table")
"""

import logging
import platform
import subprocess
from typing import Tuple

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_ssh_command(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int = 30,
    known_hosts_file: str = "/dev/null",
) -> Tuple[int, str, str]:
    """Execute a single command over SSH and return (returncode, stdout, stderr)."""
    if IS_WINDOWS:
        return _paramiko_exec(host, username, password, command, timeout)
    return _subprocess_ssh(host, username, password, command, timeout, known_hosts_file)


def run_interactive_ssh(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int = 30,
    known_hosts_file: str = "/dev/null",
) -> Tuple[int, str, str]:
    """Interactive SSH session (required for Mellanox Onyx admin user)."""
    if IS_WINDOWS:
        return _paramiko_exec(host, username, password, command, timeout)
    return _pexpect_interactive(host, username, password, command, timeout, known_hosts_file)


# ---------------------------------------------------------------------------
# macOS / Linux implementations
# ---------------------------------------------------------------------------


def _augmented_env() -> dict:
    """Return env with PATH augmented for Homebrew tool locations."""
    import os

    env = os.environ.copy()
    extra = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    existing = env.get("PATH", "")
    for p in extra:
        if p not in existing:
            existing = f"{p}:{existing}"
    env["PATH"] = existing
    return env


def _subprocess_ssh(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int,
    known_hosts_file: str,
) -> Tuple[int, str, str]:
    """Non-interactive SSH via sshpass + ssh.  Falls back to paramiko if sshpass is missing."""
    import shutil

    env = _augmented_env()

    if shutil.which("sshpass", path=env.get("PATH")):
        cmd = [
            "sshpass",
            "-p",
            password,
            "ssh",
            "-o",
            "StrictHostKeyChecking=no",
            "-o",
            f"UserKnownHostsFile={known_hosts_file}",
            f"{username}@{host}",
            command,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", f"SSH command timed out after {timeout}s"
        except Exception as exc:
            return 1, "", str(exc)

    logger.debug("sshpass not found, falling back to paramiko for %s", host)
    return _paramiko_exec(host, username, password, command, timeout)


def _pexpect_interactive(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int,
    known_hosts_file: str,
) -> Tuple[int, str, str]:
    """Interactive SSH via pexpect (for Onyx switches that reject non-interactive SSH)."""
    try:
        import pexpect
    except ImportError:
        logger.warning("pexpect not available, falling back to paramiko")
        return _paramiko_exec(host, username, password, command, timeout)

    try:
        ssh_cmd = f"ssh -o StrictHostKeyChecking=no " f"-o UserKnownHostsFile={known_hosts_file} " f"{username}@{host}"
        child = pexpect.spawn(ssh_cmd, timeout=timeout, encoding="utf-8")

        i = child.expect([r"[Pp]assword:", pexpect.TIMEOUT, pexpect.EOF])
        if i != 0:
            return 1, "", f"No password prompt: {child.before}"

        child.sendline(password)

        i = child.expect([r"\[.*\]\s*>", r"[$#>]", pexpect.TIMEOUT, pexpect.EOF], timeout=15)
        if i >= 2:
            return 1, "", f"No CLI prompt: {child.before}"

        child.sendline(command)

        i = child.expect([r"\[.*\]\s*>", r"[$#>]", pexpect.TIMEOUT, pexpect.EOF], timeout=timeout)
        output = child.before if child.before else ""

        child.sendline("exit")
        child.expect(pexpect.EOF, timeout=5)
        child.close()

        return 0, output.strip(), ""
    except Exception as exc:
        return 1, "", str(exc)


# ---------------------------------------------------------------------------
# Windows / fallback implementation (paramiko)
# ---------------------------------------------------------------------------


def _paramiko_exec(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int,
) -> Tuple[int, str, str]:
    """Execute a command over SSH using paramiko (pure Python, cross-platform)."""
    try:
        import paramiko
    except ImportError:
        return 1, "", "paramiko not installed. Run: pip install paramiko"

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(host, username=username, password=password, timeout=timeout, look_for_keys=False)
        _stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        rc = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return rc, out, err
    except paramiko.AuthenticationException:
        return 1, "", f"Authentication failed for {username}@{host}"
    except Exception as exc:
        return 1, "", str(exc)
    finally:
        client.close()
