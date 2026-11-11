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
* **Live output**: ``run_ssh_command(..., on_output=cb)`` calls ``cb`` with
  decoded stdout/stderr text chunks as they arrive, for long commands whose
  progress the UI should show before they exit.  The return value is still
  the full ``(rc, stdout, stderr)``.

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

import codecs
import logging
import os
import platform
import re
import signal
import subprocess
import threading
import time
from typing import Any, Callable, List, Optional, Tuple

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"

OutputCallback = Callable[[str], None]

_STREAM_READ_SIZE = 65536
_PARAMIKO_POLL_S = 0.1
_PARAMIKO_EOF_GRACE_S = 2.0
_READER_JOIN_AFTER_KILL_S = 5

# Client-side SSH failures observed when a laptop sleeps, a VPN flaps, or the
# local stack cannot bind (macOS "Can't assign requested address").  These are
# transport problems, not remote-command failures — workflows should say so.
_SSH_TRANSPORT_MARKERS = (
    "can't assign requested address",
    "broken pipe",
    "connection reset by peer",
    "connection timed out",
    "no route to host",
    "network is unreachable",
    "connection refused",
    "operation timed out",
    "ssh: connect to host",
    "connection closed by remote host",
)


def is_ssh_transport_failure(rc: int, stdout: str = "", stderr: str = "") -> bool:
    """True when *rc*/output indicate the SSH client lost the connection.

    Remote commands that fail for their own reasons (non-zero rc with ordinary
    stderr) return False so callers do not mislabel elbencho/tool errors.
    """
    if rc == 0:
        return False
    blob = f"{stdout or ''}\n{stderr or ''}".lower()
    return any(marker in blob for marker in _SSH_TRANSPORT_MARKERS)


def ssh_transport_failure_message(rc: int, stdout: str = "", stderr: str = "") -> str:
    """One-line operator message for a transport drop."""
    blob = f"{stderr or ''}\n{stdout or ''}"
    symptom = "connection lost"
    for marker in _SSH_TRANSPORT_MARKERS:
        idx = blob.lower().find(marker)
        if idx >= 0:
            # Prefer the original casing from the stream.
            line = next(
                (ln.strip() for ln in blob.splitlines() if marker in ln.lower()),
                marker,
            )
            symptom = line or marker
            break
    return f"SSH connection lost to cluster ({symptom}; rc={rc})"


# Login rejected before the remote command ran (ssh rc=255, sshpass rc=5 for a
# repeated password prompt).  Remote "Permission denied" from a command is not a
# login failure, so the markers are the ssh client's own auth messages.
_SSH_AUTH_MARKERS = (
    "too many authentication failures",
    "permission denied, please try again",
    "permission denied (",
)
_SSHPASS_BAD_PASSWORD_RC = 5
_AUTH_RETRY_DELAY_S = 3

# Client banners OpenSSH prints on every connection; they bury the real error.
_SSH_NOISE_PREFIXES = (
    "warning: permanently added",
    "** warning: connection is not using a post-quantum",
    "** this session may be vulnerable",
    "** the server may need to be upgraded",
)


def is_ssh_auth_failure(rc: int, stdout: str = "", stderr: str = "") -> bool:
    """True when the SSH login itself was rejected, so the remote command never ran."""
    if rc == _SSHPASS_BAD_PASSWORD_RC:
        return True
    if rc != 255:
        return False
    blob = f"{stdout or ''}\n{stderr or ''}".lower()
    return any(marker in blob for marker in _SSH_AUTH_MARKERS)


def ssh_auth_failure_message(rc: int, stdout: str = "", stderr: str = "", host: str = "") -> str:
    """One-line operator message for a rejected SSH login."""
    lines = [ln.strip() for ln in f"{stderr or ''}\n{stdout or ''}".splitlines() if ln.strip()]
    symptom = "password rejected"
    for marker in _SSH_AUTH_MARKERS:
        match = next((ln for ln in lines if marker in ln.lower()), None)
        if match:
            symptom = match
            break
    target = f" to {host}" if host else ""
    return f"SSH login{target} was rejected ({symptom}; rc={rc})"


def is_ssh_noise_line(line: str) -> bool:
    """True for an OpenSSH client banner line (host-key or post-quantum warning)."""
    return line.strip().lower().startswith(_SSH_NOISE_PREFIXES)


def strip_ssh_noise(text: str) -> str:
    """Drop OpenSSH client banner lines (host-key and post-quantum warnings)."""
    if not text:
        return text or ""
    kept = [ln for ln in text.splitlines(keepends=True) if not is_ssh_noise_line(ln)]
    return "".join(kept)


# ---------------------------------------------------------------------------
# Switch credential ordering
# ---------------------------------------------------------------------------


def build_switch_credential_combos(
    primary_user: str,
    password_candidates: List[str],
) -> List[Tuple[str, str]]:
    """Return an ordered, deduplicated list of ``(user, password)`` combinations
    to try when authenticating against an unknown cluster switch.

    Pre-validation, Switch Extraction, and External Port Mapping all consume
    this ordering so they agree on which credentials to try and in what order.
    For the typical Cumulus primary user the ordering is:

    * Operator-provided ``primary_user`` × each password candidate first
      (Connection Settings + the configured ``default_switch_passwords`` —
      ``Vastdata1!`` primary, ``Cumu1usLinux!`` secondary in the stock
      config).
    * ``admin/admin`` (Onyx/MLNX-OS factory default).
    * When the operator's ``primary_user`` is neither ``cumulus`` nor
      ``admin``, ``cumulus`` × each password candidate is appended as a
      fallback so the stock Cumulus account is still exercised.

    The ``admin × <password candidate>`` permutations that earlier releases
    tried on Onyx-with-VMS-synced passwords are *not* included — operators
    who need that path can enter the admin credentials explicitly in
    Connection Settings so the combo list resolves correctly.

    This function never issues network I/O; callers drive the iteration.
    """
    combos: List[Tuple[str, str]] = []
    seen: set = set()

    def _add(user: str, password: str) -> None:
        if not user or not password:
            return
        key = (user, password)
        if key in seen:
            return
        seen.add(key)
        combos.append((user, password))

    primary = primary_user or "cumulus"
    for pw in password_candidates or []:
        _add(primary, pw)

    _add("admin", "admin")

    if primary not in ("cumulus", "admin"):
        for pw in password_candidates or []:
            _add("cumulus", pw)

    return combos


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
    port: int = 22,
    jump_port: int = 22,
    on_output: Optional[OutputCallback] = None,
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
        port:             TCP port for the *host* connection (default 22).
                          Teleport mode forwards a CNode's SSH to a local
                          port, so callers pass that local port here.
        jump_port:        TCP port for the *jump_host* connection (default
                          22).  Used when the jump host itself is reached
                          over a forwarded local port (Teleport mode).
        on_output:        Optional callback for live output.  Called with
                          decoded text chunks (any size, not line-aligned) of
                          remote stdout and stderr as they arrive.  Exceptions
                          it raises are ignored.  Adapter-generated messages
                          (timeout notice, connection errors) are only in the
                          returned stderr.  The return value is unchanged.
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
            port=port,
            jump_port=jump_port,
            on_output=on_output,
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
            port=port,
            on_output=on_output,
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
        port=port,
        on_output=on_output,
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
    port: int = 22,
    jump_port: int = 22,
) -> Tuple[int, str, str]:
    """Interactive SSH session (required for Mellanox Onyx admin user).

    Uses *pexpect* on macOS/Linux to drive the password prompt and the
    switch CLI interactively.  Falls back to paramiko on Windows.

    When *jump_host* is provided, paramiko's ``invoke_shell()`` is used
    to open a true interactive shell channel through the tunnel — this is
    required for Onyx restricted shells that reject ``exec_command()``.

    ``port``/``jump_port`` override the default port 22 for the host and
    jump-host connections respectively (used by Teleport mode where a
    CNode's SSH is forwarded to a local port).
    """
    if jump_host:
        rc, out, err = _paramiko_shell(
            host,
            username,
            password,
            command,
            timeout,
            jump_host=jump_host,
            jump_user=jump_user,
            jump_password=jump_password,
            jump_port=jump_port,
        )
    elif IS_WINDOWS:
        rc, out, err = _paramiko_shell(host, username, password, command, timeout, port=port)
    else:
        rc, out, err = _pexpect_interactive(host, username, password, command, timeout, known_hosts_file, port=port)

    # Onyx/MLNX-OS shells prepend terminal-mode escapes; strip them so the
    # caller receives clean text for hostname/filename/parse use.
    return rc, strip_terminal_escapes(out), strip_terminal_escapes(err)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _wrap_login_shell(command: str) -> str:
    """Wrap *command* in ``bash -l -c '...'`` for full login-shell environment."""
    escaped = command.replace("'", "'\\''")
    return "bash -l -c '" + escaped + "'"


# ANSI / terminal control sequences emitted by switch CLIs.  NVIDIA Onyx (and
# other MLNX-OS restricted shells) send terminal-mode setup on shell entry
# (e.g. ``\x1b[?1h\x1b=``), which otherwise pollutes captured output — poisoning
# derived hostnames/filenames (``switch_^[[?1h^[=_...txt``) and breaking parsers.
_ANSI_ESCAPE_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"  # CSI sequences (e.g. \x1b[?1h, \x1b[0m)
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"  # OSC sequences terminated by BEL or ST
    r"|\x1b[()][0-9A-Za-z]"  # charset selection (e.g. \x1b(B)
    r"|\x1b[=>]"  # keypad application / normal mode
    r"|\x1b[@-Z\\^_]"  # other single-char escapes (e.g. \x1bM)
)


def strip_terminal_escapes(text: str) -> str:
    """Remove ANSI/terminal control sequences from captured shell output.

    Applied to interactive-SSH output so downstream consumers (hostname
    derivation, filename slugs, config parsing) see clean text even when a
    switch emits terminal-mode setup sequences on shell entry.
    """
    if not text:
        return text
    cleaned = _ANSI_ESCAPE_RE.sub("", text)
    # Drop any orphaned ESC and non-printable control chars, preserving the
    # usual whitespace (tab, newline, carriage-return).
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned)
    return cleaned


def _run_ssh_popen(
    cmd: List[str],
    timeout: int,
    env: dict,
    on_output: Optional[OutputCallback] = None,
) -> Tuple[int, str, str]:
    """Run an SSH client command, killing the whole process group on timeout.

    ``subprocess.run(..., timeout=...)`` only signals the direct child.  With
    ``sshpass`` → ``ssh`` → remote shell, that can leave ``ssh`` hanging after
    the timeout fires (seen as a 30 s views-API call lasting tens of minutes
    when the laptop slept or the TCP session wedged).  A new session +
    ``killpg`` tears the whole tree down.

    With *on_output*, stdout and stderr are read by two threads and each
    decoded chunk is passed to the callback as it arrives.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    if on_output is not None:
        return _stream_popen(proc, timeout, on_output)
    try:
        stdout_b, stderr_b = proc.communicate(timeout=timeout)
        return int(proc.returncode or 0), _as_text(stdout_b), _as_text(stderr_b)
    except subprocess.TimeoutExpired:
        _kill_process_group(proc)
        try:
            stdout_b, stderr_b = proc.communicate(timeout=5)
        except Exception:
            stdout_b, stderr_b = b"", b""
        return 1, _as_text(stdout_b), _timeout_stderr(_as_text(stderr_b), timeout)


def _kill_process_group(proc: "subprocess.Popen[bytes]") -> None:
    """SIGKILL *proc*'s process group, falling back to the process itself."""
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.kill()
        except OSError:
            pass


def _timeout_stderr(partial_err: str, timeout: int) -> str:
    """Append the adapter's timeout notice to whatever stderr was captured."""
    if partial_err and not partial_err.endswith("\n"):
        partial_err += "\n"
    return partial_err + "SSH command timed out after " + str(timeout) + "s"


def _deliver_chunk(
    text: str,
    parts: List[str],
    on_output: Optional[OutputCallback],
    lock: Optional[threading.Lock] = None,
    stopped: Optional[threading.Event] = None,
) -> None:
    """Record *text* and hand it to *on_output*; callback errors never propagate.

    Once *stopped* is set (the call has returned) chunks are dropped, so a reader
    thread kept alive by an orphaned pipe can't call back into a finished caller.
    """
    if not text or (stopped is not None and stopped.is_set()):
        return
    parts.append(text)
    if on_output is None:
        return
    try:
        if lock is None:
            on_output(text)
        else:
            with lock:
                if stopped is None or not stopped.is_set():
                    on_output(text)
    except Exception:
        logger.debug("SSH on_output callback raised; ignoring", exc_info=True)


def _stop_delivery(lock: threading.Lock, stopped: threading.Event) -> None:
    """Set *stopped* under *lock* so no callback can still be running or start after this returns."""
    with lock:
        stopped.set()


def _pump_pipe(
    pipe: Any, parts: List[str], on_output: OutputCallback, lock: threading.Lock, stopped: threading.Event
) -> None:
    """Reader-thread body: read *pipe* (a buffered ``Popen`` pipe) until EOF, decoding UTF-8 incrementally."""
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    try:
        while True:
            data = pipe.read1(_STREAM_READ_SIZE)
            if not data:
                break
            _deliver_chunk(decoder.decode(data), parts, on_output, lock, stopped)
    except Exception:
        logger.debug("SSH output reader stopped", exc_info=True)
    finally:
        _deliver_chunk(decoder.decode(b"", final=True), parts, on_output, lock, stopped)


def _stream_popen(proc: "subprocess.Popen[bytes]", timeout: int, on_output: OutputCallback) -> Tuple[int, str, str]:
    """Wait for *proc* while streaming its pipes to *on_output*.

    Mirrors ``communicate(timeout=...)``: the deadline covers both process exit
    and EOF on both pipes, and on expiry the process group is killed.
    """
    deadline = time.monotonic() + timeout
    out_parts: List[str] = []
    err_parts: List[str] = []
    lock = threading.Lock()
    stopped = threading.Event()
    readers = [
        threading.Thread(target=_pump_pipe, args=(proc.stdout, out_parts, on_output, lock, stopped), daemon=True),
        threading.Thread(target=_pump_pipe, args=(proc.stderr, err_parts, on_output, lock, stopped), daemon=True),
    ]
    for reader in readers:
        reader.start()

    timed_out = False
    try:
        proc.wait(timeout=max(0.0, deadline - time.monotonic()))
        for reader in readers:
            reader.join(timeout=max(0.0, deadline - time.monotonic()))
        timed_out = any(reader.is_alive() for reader in readers)
    except subprocess.TimeoutExpired:
        timed_out = True

    if timed_out:
        _kill_process_group(proc)
        grace_deadline = time.monotonic() + _READER_JOIN_AFTER_KILL_S
        try:
            proc.wait(timeout=_READER_JOIN_AFTER_KILL_S)
        except Exception:
            pass
        for reader in readers:
            reader.join(timeout=max(0.0, grace_deadline - time.monotonic()))
        _stop_delivery(lock, stopped)
        _close_drained_pipes(proc, readers)
        return 1, "".join(list(out_parts)), _timeout_stderr("".join(list(err_parts)), timeout)

    _stop_delivery(lock, stopped)
    _close_drained_pipes(proc, readers)
    return int(proc.returncode or 0), "".join(out_parts), "".join(err_parts)


def _close_drained_pipes(proc: "subprocess.Popen[bytes]", readers: List[threading.Thread]) -> None:
    """Close the pipes whose reader thread has finished (a live reader keeps its pipe)."""
    for pipe, reader in zip((proc.stdout, proc.stderr), readers):
        if pipe is not None and not reader.is_alive():
            try:
                pipe.close()
            except OSError:
                pass


def _as_text(value: Any) -> str:
    """Decode captured subprocess output (bytes on some platforms even with text=True)."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


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
    port: int = 22,
    on_output: Optional[OutputCallback] = None,
) -> Tuple[int, str, str]:
    """Non-interactive SSH via ``sshpass -e`` + ``ssh``.

    Falls back to paramiko when ``sshpass`` is not installed.  *on_output*
    receives raw remote output chunks (before ``strip_ssh_noise``).
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
        if port and int(port) != 22:
            cmd.extend(["-p", str(port)])

        connect_timeout = min(timeout, 30)
        if password:
            # Offered keys count against the server's MaxAuthTries; with several
            # agent/identity keys the password can be refused as "Too many
            # authentication failures".  Keys stay as the last fallback.
            cmd.extend(["-o", "PreferredAuthentications=keyboard-interactive,password,publickey"])
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
            rc, out, err = _run_ssh_popen(cmd, timeout=timeout, env=env, on_output=on_output)
            if rc == 255 and is_ssh_auth_failure(rc, out, err) and not out.strip():
                # The server dropped the login before the command ran, so a retry cannot
                # repeat remote side effects.  A plainly wrong password is sshpass rc=5
                # and is not retried, so switch password sweeps do not double up.
                logger.warning("SSH login to %s rejected (rc=%s); retrying once in %ss", host, rc, _AUTH_RETRY_DELAY_S)
                time.sleep(_AUTH_RETRY_DELAY_S)
                rc, out, err = _run_ssh_popen(cmd, timeout=timeout, env=env, on_output=on_output)
            return rc, out, strip_ssh_noise(err)
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
        port=port,
        on_output=on_output,
    )


def _pexpect_interactive(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int,
    known_hosts_file: str,
    port: int = 22,
) -> Tuple[int, str, str]:
    """Interactive SSH via *pexpect* (for Onyx switches that reject non-interactive SSH)."""
    try:
        import pexpect
    except ImportError:
        logger.warning("pexpect not available, falling back to paramiko")
        return _paramiko_exec(host, username, password, command, timeout, force_tty=True, port=port)

    try:
        connect_timeout = min(timeout, 30)
        port_opt = ("-p " + str(port) + " ") if port and int(port) != 22 else ""
        ssh_cmd = (
            "ssh -o StrictHostKeyChecking=no "
            "-o UserKnownHostsFile=" + known_hosts_file + " "
            "-o ConnectTimeout=" + str(connect_timeout) + " " + port_opt + username + "@" + host
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


def _paramiko_shell(
    host: str,
    username: str,
    password: str,
    command: str,
    timeout: int,
    jump_host: Optional[str] = None,
    jump_user: Optional[str] = None,
    jump_password: Optional[str] = None,
    port: int = 22,
    jump_port: int = 22,
) -> Tuple[int, str, str]:
    """Open an interactive shell channel via paramiko and type the command.

    Unlike ``exec_command()``, ``invoke_shell()`` spawns the remote user's
    default shell (e.g. the Onyx restricted CLI) and then sends the command
    as typed input.  This is required for Mellanox Onyx switches whose
    restricted shell rejects exec-style command execution with
    ``UNIX shell commands cannot be executed using this account``.
    """
    try:
        import paramiko  # type: ignore[import-untyped]
    except ImportError:
        return 1, "", "paramiko not installed. Run: pip install paramiko"

    import re
    import time as _time

    jump_params = [jump_host, jump_user, jump_password]
    if any(jump_params) and not all(jump_params):
        return 1, "", "Incomplete jump host config"

    use_jump = jump_host and jump_user and jump_password
    jump_client: Optional[paramiko.SSHClient] = None
    client = paramiko.SSHClient()
    # Intentional [B507]: target is a freshly-deployed VAST CNode/switch; AutoAddPolicy is required
    # for first-contact SSH where host keys are not yet trusted (documented tool behavior).
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507

    try:
        connect_timeout = min(timeout, 30)
        sock = None

        if use_jump:
            jump_client = paramiko.SSHClient()
            # Intentional [B507]: jump host is the newly-installed VMS; AutoAddPolicy is required
            # for first-contact tunneling before host keys are known to the operator.
            jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
            try:
                jump_client.connect(
                    jump_host,
                    port=jump_port,
                    username=jump_user,
                    password=jump_password,
                    timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            except paramiko.AuthenticationException:
                return 1, "", "Jump host authentication failed for " + jump_user + "@" + jump_host
            except (paramiko.SSHException, OSError) as exc:
                return 1, "", "Jump host connection failed for " + jump_host + ": " + str(exc)

            jump_transport = jump_client.get_transport()
            if jump_transport is None:
                return 1, "", "Jump host transport unavailable for " + jump_host
            sock = jump_transport.open_channel("direct-tcpip", (host, 22), ("127.0.0.1", 0))

        client.connect(
            host,
            port=port,
            username=username,
            password=password,
            timeout=connect_timeout,
            banner_timeout=connect_timeout,
            look_for_keys=False,
            allow_agent=False,
            sock=sock,
        )

        chan = client.invoke_shell(term="vt100", width=200, height=50)
        chan.settimeout(float(timeout))

        _PROMPT_RE = re.compile(r"[\]#>$]\s*$")

        def _read_until_prompt(deadline: float) -> str:
            buf = ""
            while _time.time() < deadline:
                if chan.recv_ready():
                    chunk = chan.recv(65536).decode("utf-8", errors="replace")
                    buf += chunk
                    if _PROMPT_RE.search(buf.split("\n")[-1]):
                        break
                else:
                    _time.sleep(0.1)
            return buf

        deadline = _time.time() + timeout

        _read_until_prompt(deadline)

        chan.sendall((command + "\n").encode())
        _time.sleep(0.3)

        raw_output = _read_until_prompt(deadline)

        chan.sendall(b"exit\n")
        _time.sleep(0.2)
        chan.close()

        lines = raw_output.splitlines()
        if lines and command in lines[0]:
            lines = lines[1:]
        if lines and _PROMPT_RE.search(lines[-1]):
            lines = lines[:-1]
        output = "\n".join(lines).strip()

        return 0, output, ""
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
    port: int = 22,
    jump_port: int = 22,
    on_output: Optional[OutputCallback] = None,
) -> Tuple[int, str, str]:
    """Execute a command over SSH using paramiko (pure Python, cross-platform).

    When *jump_host*, *jump_user*, and *jump_password* are all provided the
    connection is tunnelled through the jump host using a ``direct-tcpip``
    channel.  This is the only reliable cross-platform approach for reaching
    hosts (e.g. switches) that are only accessible from inside a cluster
    network.

    With *on_output*, the channel is polled and each decoded chunk is passed
    to the callback as it arrives, within an overall *timeout* deadline.
    """
    try:
        import paramiko  # type: ignore[import-untyped]
    except ImportError:
        return 1, "", "paramiko not installed. Run: pip install paramiko"

    jump_params = [jump_host, jump_user, jump_password]
    if any(jump_params) and not all(jump_params):
        return (
            1,
            "",
            "Incomplete jump host config: jump_host, jump_user, " "and jump_password must all be provided",
        )

    use_jump = jump_host and jump_user and jump_password
    jump_client: Optional[paramiko.SSHClient] = None
    client = paramiko.SSHClient()
    # Intentional [B507]: target is a freshly-deployed VAST CNode/switch; AutoAddPolicy is required
    # for first-contact SSH where host keys are not yet trusted (documented tool behavior).
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507

    try:
        connect_timeout = min(timeout, 30)
        sock = None

        if use_jump:
            logger.debug(
                "Opening SSH tunnel via jump host %s to reach %s",
                jump_host,
                host,
            )
            jump_client = paramiko.SSHClient()
            # Intentional [B507]: jump host is the newly-installed VMS; AutoAddPolicy is required
            # for first-contact tunneling before host keys are known to the operator.
            jump_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
            try:
                jump_client.connect(
                    jump_host,
                    port=jump_port,
                    username=jump_user,
                    password=jump_password,
                    timeout=connect_timeout,
                    banner_timeout=connect_timeout,
                    look_for_keys=False,
                    allow_agent=False,
                )
            except paramiko.AuthenticationException:
                return (
                    1,
                    "",
                    "Jump host authentication failed for " + jump_user + "@" + jump_host,
                )
            except (paramiko.SSHException, OSError) as exc:
                return (
                    1,
                    "",
                    "Jump host connection failed for " + jump_host + ": " + str(exc),
                )

            jump_transport = jump_client.get_transport()
            if jump_transport is None:
                return 1, "", "Jump host transport unavailable for " + jump_host
            sock = jump_transport.open_channel(
                "direct-tcpip",
                (host, 22),
                ("127.0.0.1", 0),
            )
            logger.debug(
                "SSH tunnel established: %s -> %s:22 via %s",
                jump_host,
                host,
                jump_host,
            )

        client.connect(
            host,
            port=port,
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

        # Intentional [B601]: `command` is always constructed internally by workflow code from
        # fixed templates plus validated parameters (host/user/password from credential
        # prompts and discovered IPs), never sourced from untrusted external input.
        _stdin, stdout, stderr = client.exec_command(  # nosec B601
            command,
            timeout=timeout,
            get_pty=force_tty,
        )
        if on_output is not None:
            return _stream_paramiko_channel(stdout.channel, timeout, on_output)
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


def _stream_paramiko_channel(chan: Any, timeout: int, on_output: OutputCallback) -> Tuple[int, str, str]:
    """Poll a paramiko exec channel, passing decoded output chunks to *on_output*.

    The exit status can arrive before the last output (the remote PTY drains
    after the process exits), so reading continues until the channel reports
    EOF with empty buffers, or ``_PARAMIKO_EOF_GRACE_S`` after the exit status
    for servers that never send EOF.  Unlike the non-streaming path, *timeout*
    is a hard deadline for the whole command, not a per-read idle timeout.
    """
    deadline = time.monotonic() + timeout
    out_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    err_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    out_parts: List[str] = []
    err_parts: List[str] = []

    def _finish() -> None:
        _deliver_chunk(out_decoder.decode(b"", final=True), out_parts, on_output)
        _deliver_chunk(err_decoder.decode(b"", final=True), err_parts, on_output)

    exited_idle_since: Optional[float] = None
    while True:
        received = False
        if chan.recv_ready():
            data = chan.recv(_STREAM_READ_SIZE)
            if data:
                received = True
                _deliver_chunk(out_decoder.decode(data), out_parts, on_output)
        if chan.recv_stderr_ready():
            data = chan.recv_stderr(_STREAM_READ_SIZE)
            if data:
                received = True
                _deliver_chunk(err_decoder.decode(data), err_parts, on_output)
        drained = not received and not chan.recv_ready() and not chan.recv_stderr_ready()
        if drained and chan.exit_status_ready():
            if getattr(chan, "eof_received", False):
                break
            now = time.monotonic()
            if exited_idle_since is None:
                exited_idle_since = now
            elif now - exited_idle_since >= _PARAMIKO_EOF_GRACE_S:
                break
        elif received:
            exited_idle_since = None
        if time.monotonic() >= deadline:
            chan.close()
            _finish()
            return 1, "".join(out_parts), _timeout_stderr("".join(err_parts), timeout)
        if not received:
            time.sleep(_PARAMIKO_POLL_S)

    _finish()
    return chan.recv_exit_status(), "".join(out_parts), "".join(err_parts)
