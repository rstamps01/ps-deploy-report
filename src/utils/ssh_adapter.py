"""
Cross-platform SSH adapter.

Provides a unified interface for running remote commands over SSH:
  - macOS / Linux: uses subprocess (ssh binary via sshpass) with pexpect for
    interactive sessions (Mellanox Onyx switches)
  - Windows: uses paramiko (pure-Python SSH) for all sessions

Key design choices
------------------
* **Password security**: sshpass receives the password via the SSHPASS
  environment variable (``sshpass -e``) rather than ``-p password`` on the
  command line, avoiding exposure in the process table.
* **Connection stability**: SSH options ``ConnectTimeout``,
  ``ServerAliveInterval`` and ``ServerAliveCountMax`` prevent commands from
  hanging on unresponsive hosts.
* **Login-shell support**: The ``login_shell`` flag wraps the remote command
  in ``bash -l -c '...'`` so that the target user's full environment (PATH,
  SSH_AUTH_SOCK, aliases, etc.) is available -- critical for commands such as
  ``clush`` that spawn their own SSH connections.
* **Agent forwarding**: When ``agent_forward=True`` the ``-A`` flag (or
  paramiko agent forwarding) is added, allowing nested SSH operations to
  reuse the caller's SSH agent.
* **PTY allocation**: ``force_tty=True`` adds ``-tt`` (subprocess) or
  ``get_pty=True`` (paramiko) for commands that require a pseudo-terminal
  (``docker exec -it``, ``vms.sh``, etc.).

Usage::

    from utils.ssh_adapter import run_ssh_command, run_interactive_ssh

    rc, stdout, stderr = run_ssh_command(host, user, password, "show version")
    rc, stdout, stderr = run_ssh_command(
        host, user, password, "clush -a 'hostname'",
        force_tty=True, login_shell=True,
    )
    rc, stdout, stderr = run_interactive_ssh(
        host, user, password, "show mac-address-table",
    )
"""

import logging
import os
import platform
import subprocess
from typing import Optional, Tuple

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
    force_tty: bool = False,
    login_shell: bool = False,
    agent_forward: bool = False,
    jump_host: Optional[str] = None,
    jump_user: Optional[str] = None,
    jump_password: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Execute a single command over SSH and return (returncode, stdout, stderr).

    Args:
        host:             Remote hostname or IP.
        username:         SSH username.
        password:         SSH password.
        command:          Shell command to run on the remote host.
        timeout:          Maximum seconds to wait (applies to both connection
                          and command execution).
        known_hosts_file: Path used for ``UserKnownHostsFile`` (default
                          ``/dev/null`` to suppress host-key prompts).
        force_tty:        Allocate a pseudo-TTY (``-tt`` / ``get_pty``).
                          Required for ``docker exec -it`` and similar.
        login_shell:      Wrap *command* in ``bash -l -c '...'`` so that the
                          remote user's profile/environment is loaded.  Use
                          for commands that depend on PATH, SSH_AUTH_SOCK, or
                          other env vars (e.g. ``clush``).
        agent_forward:    Enable SSH agent forwarding (``-A``).  Allows
                          commands on the remote host to use the caller's
                          SSH agent for nested SSH connections.
        jump_host:        Intermediate host to tunnel through (e.g. a CNode
                          tech-port IP).  When provided, paramiko's
                          ``direct-tcpip`` channel is used regardless of
                          platform.
        jump_user:        Username for the jump host.
        jump_password:    Password for the jump host.
    """
    effective_cmd = _wrap_login_shell(command) if login_shell else command

    if jump_host:
        return _paramiko_exec(
            host,
            username,
            password,
            effective_cmd,
            timeout,
            force_tty=force_tty,
            agent_forward=agent_forward,
            jump_host=jump_host,
            jump_user=jump_user,
            jump_password=jump_password,
        )

    if IS_WINDOWS:
        return _paramiko_exec(
            host,
            username,
            password,
            effective_cmd,
            timeout,
            force_tty=force_tty,
            agent_forward=agent_forward,
        )
    return _subprocess_ssh(
        host,
        username,
        password,
        effective_cmd,
        timeout,
        known_hosts_file,
        force_tty=force_tty,
        agent_forward=agent_forward,
    )


def run_interactive_ssh(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int = 30,
    known_hosts_file: str = "/dev/null",
    jump_host: Optional[str] = None,
    jump_user: Optional[str] = None,
    jump_password: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Interactive SSH session (required for Mellanox Onyx admin user).

    Uses *pexpect* on macOS/Linux to drive the password prompt and the
    switch CLI interactively.  Falls back to paramiko on Windows.

    When *jump_host* is provided, paramiko's ``direct-tcpip`` channel is
    used regardless of platform (pexpect cannot drive a tunnelled session).
    """
    if jump_host:
        return _paramiko_exec(
            host, username, password, command, timeout,
            force_tty=True,
            jump_host=jump_host,
            jump_user=jump_user,
            jump_password=jump_password,
        )
    if IS_WINDOWS:
        return _paramiko_exec(host, username, password, command, timeout, force_tty=True)
    return _pexpect_interactive(host, username, password, command, timeout, known_hosts_file)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wrap_login_shell(command: str) -> str:
    """Wrap *command* in ``bash -l -c '...'`` for full login-shell environment."""
    escaped = command.replace("'", "'\\''")
    return "bash -l -c '" + escaped + "'"


def _augmented_env(password=None):
    """Return a copy of ``os.environ`` with:

    * PATH augmented for common tool locations (Homebrew, system).
    * ``SSHPASS`` set when *password* is provided so that ``sshpass -e``
      reads the credential from the environment instead of the command line.
    """
    env = os.environ.copy()
    extra = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    existing = env.get("PATH", "")
    for p in extra:
        if p not in existing:
            existing = p + ":" + existing
    env["PATH"] = existing

    if password is not None:
        env["SSHPASS"] = password

    return env


# ---------------------------------------------------------------------------
# macOS / Linux implementations
# ---------------------------------------------------------------------------


def _subprocess_ssh(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int,
    known_hosts_file: str,
    force_tty: bool = False,
    agent_forward: bool = False,
) -> Tuple[int, str, str]:
    """Non-interactive SSH via ``sshpass -e`` + ``ssh``.

    Falls back to paramiko when ``sshpass`` is not installed.
    """
    import shutil

    env = _augmented_env(password=password)

    if shutil.which("sshpass", path=env.get("PATH")):
        # sshpass -e reads password from $SSHPASS (set in env above)
        cmd = ["sshpass", "-e", "ssh"]

        if force_tty:
            cmd.append("-tt")
        if agent_forward:
            cmd.append("-A")

        connect_timeout = min(timeout, 30)
        cmd.extend(
            [
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=" + known_hosts_file,
                "-o",
                "ConnectTimeout=" + str(connect_timeout),
                "-o",
                "ServerAliveInterval=15",
                "-o",
                "ServerAliveCountMax=3",
                username + "@" + host,
                command,
            ]
        )
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return 1, "", "SSH command timed out after " + str(timeout) + "s"
        except subprocess.CalledProcessError as exc:
            return exc.returncode, exc.stdout or "", exc.stderr or str(exc)
        except Exception as exc:
            return 1, "", str(exc)

    logger.debug("sshpass not found, falling back to paramiko for %s", host)
    return _paramiko_exec(
        host,
        username,
        password,
        command,
        timeout,
        force_tty=force_tty,
        agent_forward=agent_forward,
    )


def _pexpect_interactive(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int,
    known_hosts_file: str,
) -> Tuple[int, str, str]:
    """Interactive SSH via *pexpect* (for Onyx switches that reject non-interactive SSH)."""
    try:
        import pexpect
    except ImportError:
        logger.warning("pexpect not available, falling back to paramiko")
        return _paramiko_exec(host, username, password, command, timeout, force_tty=True)

    try:
        connect_timeout = min(timeout, 30)
        ssh_cmd = (
            "ssh -o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=" + known_hosts_file + " "
            "-o ConnectTimeout=" + str(connect_timeout) + " " + username + "@" + host
        )
        child = pexpect.spawn(ssh_cmd, timeout=timeout, encoding="utf-8")

        i = child.expect([r"[Pp]assword:", pexpect.TIMEOUT, pexpect.EOF])
        if i != 0:
            return 1, "", "No password prompt: " + str(child.before)

        child.sendline(password)

        i = child.expect(
            [r"\[.*\]\s*>", r"[$#>]", pexpect.TIMEOUT, pexpect.EOF],
            timeout=15,
        )
        if i >= 2:
            return 1, "", "No CLI prompt: " + str(child.before)

        child.sendline(command)

        i = child.expect(
            [r"\[.*\]\s*>", r"[$#>]", pexpect.TIMEOUT, pexpect.EOF],
            timeout=timeout,
        )
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
    force_tty: bool = False,
    agent_forward: bool = False,
    jump_host: Optional[str] = None,
    jump_user: Optional[str] = None,
    jump_password: Optional[str] = None,
) -> Tuple[int, str, str]:
    """Execute a command over SSH using paramiko (pure Python, cross-platform).

    When *jump_host*, *jump_user*, and *jump_password* are all provided the
    connection is tunnelled through the jump host using a ``direct-tcpip``
    channel.  This is the only reliable cross-platform approach for reaching
    hosts (e.g. switches) that are only accessible from inside a cluster
    network.
    """
    try:
        import paramiko  # type: ignore[import-untyped]
    except ImportError:
        return 1, "", "paramiko not installed. Run: pip install paramiko"

    jump_params = [jump_host, jump_user, jump_password]
    if any(jump_params) and not all(jump_params):
        return (
            1, "",
            "Incomplete jump host config: jump_host, jump_user, "
            "and jump_password must all be provided",
        )

    use_jump = jump_host and jump_user and jump_password
    jump_client: Optional[paramiko.SSHClient] = None
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_timeout = min(timeout, 30)
        sock = None

        if use_jump:
            logger.debug(
                "Opening SSH tunnel via jump host %s to reach %s",
                jump_host, host,
            )
            jump_client = paramiko.SSHClient()
            jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            try:
                jump_client.connect(
                    jump_host,
                    username=jump_user,
                    password=jump_password,
                    timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            except paramiko.AuthenticationException:
                return (
                    1, "",
                    "Jump host authentication failed for "
                    + jump_user + "@" + jump_host,
                )
            except (paramiko.SSHException, OSError) as exc:
                return (
                    1, "",
                    "Jump host connection failed for "
                    + jump_host + ": " + str(exc),
                )

            jump_transport = jump_client.get_transport()
            if jump_transport is None:
                return 1, "", "Jump host transport unavailable for " + jump_host
            sock = jump_transport.open_channel(
                "direct-tcpip", (host, 22), ("127.0.0.1", 0),
            )
            logger.debug(
                "SSH tunnel established: %s -> %s:22 via %s",
                jump_host, host, jump_host,
            )

        client.connect(
            host,
            username=username,
            password=password,
            timeout=connect_timeout,
            banner_timeout=connect_timeout,
            look_for_keys=False,
            allow_agent=agent_forward,
            sock=sock,
        )

        transport = client.get_transport()
        if transport:
            transport.set_keepalive(15)

        _stdin, stdout, stderr = client.exec_command(
            command,
            timeout=timeout,
            get_pty=force_tty,
        )
        rc = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        return rc, out, err
    except paramiko.AuthenticationException:
        return 1, "", "Authentication failed for " + username + "@" + host
    except paramiko.SSHException as exc:
        return 1, "", "SSH error for " + username + "@" + host + ": " + str(exc)
    except OSError as exc:
        return 1, "", "Connection failed for " + host + ": " + str(exc)
    except Exception as exc:
        return 1, "", str(exc)
    finally:
        client.close()
        if jump_client is not None:
            jump_client.close()
