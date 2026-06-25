"""
Teleport (``tsh``) connection tunnel.

Teleport mode lets the As-Built Reporter generate a report (and run
``vnetmap``/port mapping) against a cluster that is only reachable through a
Teleport proxy.  The challenge the previous manual ``socat`` attempts hit is
that the app needs *both* the VMS REST API (TCP 443) and CNode SSH (TCP 22)
at the same time, while a single ``tsh ... -L`` / ``socat`` forward can only
expose one remote port locally.

This module launches a single ``tsh ssh`` subprocess with **two** ``-L``
forwards off the chosen CNode's loopback::

    tsh ssh -L <apiPort>:127.0.0.1:443 -L <sshPort>:127.0.0.1:22 \\
        -l <user> <teleport-node> <keepalive>

* API traffic terminates on ``<api_remote_host>:443`` as seen from the
  CNode -- by default the CNode's own ``127.0.0.1`` (works only when that node
  hosts the VMS), or the VMS management VIP to reach the VMS from any node --
  exposed locally as ``api_local_address``.
* SSH traffic terminates on ``127.0.0.1:22`` (the CNode's sshd), exposed
  locally as ``ssh_local_address`` -- the existing paramiko stack
  (vnetmap deploy/run, clush, switch proxy-jump) targets that endpoint.

The tunnel assumes an already-authenticated ``tsh`` session; it does not
handle SSO/MFA.  ``preflight()`` verifies ``tsh`` is on PATH and a session is
active before launching.

Usage::

    with TeleportTunnel("PDX02-Vast01-c-128-4", "vastdata") as tunnel:
        tunnel.connect()
        api_host = tunnel.api_local_address      # 127.0.0.1:<port>
        ssh_host, ssh_port = tunnel.ssh_endpoint  # ("127.0.0.1", <port>)
"""

import json
import logging
import shutil
import socket
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Remote command that keeps the tsh session (and therefore the -L forwards)
# alive without allocating a PTY.  Terminating the local tsh process tears the
# forwards down, so we don't need the remote sleep to ever wake up.
_KEEPALIVE_CMD = "sleep 315360000"


class TeleportError(Exception):
    """Raised when the Teleport tunnel cannot be established."""


def options_from_config(config: Optional[dict]) -> dict:
    """Extract ``TeleportTunnel`` keyword options from a loaded config dict.

    Reads the ``teleport`` block (``tsh_path``, ``auto_login``, ``proxy``,
    ``login_timeout``) and returns only the keys that are set, so callers can
    splat it: ``TeleportTunnel(node, user, **options_from_config(cfg))``.
    """
    block = (config or {}).get("teleport") or {}
    opts: dict = {}
    if block.get("tsh_path"):
        opts["tsh_path"] = str(block["tsh_path"])
    if "auto_login" in block:
        opts["auto_login"] = bool(block["auto_login"])
    if block.get("proxy"):
        opts["proxy"] = str(block["proxy"])
    if block.get("login_timeout"):
        opts["login_timeout"] = int(block["login_timeout"])
    return opts


def _alloc_local_port() -> int:
    """Reserve an ephemeral loopback TCP port and return it.

    Binds to ``127.0.0.1:0``, reads the assigned port, then closes the
    socket.  There is an inherent (small) race between releasing the port
    here and ``tsh`` binding it; acceptable for an interactive desktop tool.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to *host:port* succeeds."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class TeleportTunnel:
    """Manage a ``tsh ssh`` subprocess that forwards API (443) and SSH (22).

    Attributes:
        node:            Teleport node target (hostname or label query such as
                         ``hostname=PDX02-Vast01-c-128-4``, or ``user@host``).
        ssh_user:        Teleport login user (default ``vastdata``).
        api_local_port:  Local port forwarded to the CNode's 443.
        ssh_local_port:  Local port forwarded to the CNode's 22.
    """

    def __init__(
        self,
        node: str,
        ssh_user: str = "vastdata",
        *,
        tsh_path: str = "tsh",
        api_remote_host: str = "127.0.0.1",
        api_remote_port: int = 443,
        ssh_remote_port: int = 22,
        timeout: int = 30,
        auto_login: bool = True,
        login_timeout: int = 180,
        proxy: Optional[str] = None,
    ):
        self.node = node
        self.ssh_user = ssh_user or "vastdata"
        self.tsh_path = tsh_path or "tsh"
        # Remote host the API ``-L`` forward terminates on, as seen from the
        # Teleport node. Defaults to the node's own loopback (only works when
        # that node hosts the VMS). Point this at the VMS management VIP to
        # reach the VMS from any node in the cluster.
        self.api_remote_host = api_remote_host or "127.0.0.1"
        self.api_remote_port = api_remote_port
        self.ssh_remote_port = ssh_remote_port
        self.timeout = timeout
        # When the preflight finds no valid Teleport session, run ``tsh login``
        # so the SSO browser window pops up and the operator can re-auth
        # in-place instead of dropping to a terminal.  ``login_timeout`` bounds
        # how long we wait for them to complete SSO/MFA before giving up.
        self.auto_login = auto_login
        self.login_timeout = login_timeout
        # Optional explicit proxy (``host:port``) for ``tsh login``.  When
        # unset, a bare ``tsh login`` reuses the existing local profile's
        # proxy (the common case once the operator has logged in once).
        self.proxy = proxy

        self.api_local_port: Optional[int] = None
        self.ssh_local_port: Optional[int] = None
        self._proc: Optional[subprocess.Popen] = None
        # The argv host token actually dialed, after resolving ``node`` against
        # the Teleport inventory (``user@<node-id>``). ``None`` means resolution
        # was skipped (``tsh ls`` unavailable) and ``node`` is used verbatim.
        self._resolved_target: Optional[str] = None

    # -- public address helpers ---------------------------------------------

    @property
    def api_local_address(self) -> str:
        """``127.0.0.1:<api_local_port>`` for the API handler tunnel_address."""
        if self.api_local_port is None:
            raise RuntimeError("Tunnel not connected; call connect() first")
        return f"127.0.0.1:{self.api_local_port}"

    @property
    def ssh_local_address(self) -> str:
        """``127.0.0.1:<ssh_local_port>`` for the SSH stack."""
        if self.ssh_local_port is None:
            raise RuntimeError("Tunnel not connected; call connect() first")
        return f"127.0.0.1:{self.ssh_local_port}"

    @property
    def ssh_endpoint(self) -> Tuple[str, int]:
        """``("127.0.0.1", <ssh_local_port>)`` tuple for credential plumbing."""
        if self.ssh_local_port is None:
            raise RuntimeError("Tunnel not connected; call connect() first")
        return "127.0.0.1", self.ssh_local_port

    # -- lifecycle ----------------------------------------------------------

    def _status(self) -> Tuple[int, str]:
        """Run ``tsh status``; return ``(returncode, detail)``.

        ``detail`` is the trimmed stderr/stdout (e.g. ``Active profile
        expired``) used to build an actionable error or progress message.
        """
        try:
            result = subprocess.run(
                [self.tsh_path, "status"],
                capture_output=True,
                text=True,
                timeout=15,
            )
        except subprocess.TimeoutExpired as exc:
            raise TeleportError(f"'tsh status' timed out: {exc}") from exc
        except OSError as exc:
            raise TeleportError(f"Could not run '{self.tsh_path} status': {exc}") from exc
        return result.returncode, (result.stderr or result.stdout or "").strip()

    def _attempt_interactive_login(self) -> bool:
        """Run ``tsh login`` so the SSO browser window opens; wait for it.

        Returns ``True`` when ``tsh login`` exits 0 (the operator completed
        SSO/MFA in the browser), ``False`` on failure or timeout.  ``tsh``
        opens the browser itself; we additionally surface its output (the
        fallback login URL, progress) to the operator log so it is visible
        in the app's output pane if the browser does not auto-open.
        """
        cmd = [self.tsh_path, "login"]
        if self.proxy:
            cmd.append(f"--proxy={self.proxy}")
        logger.info(
            "Teleport session is not active — launching '%s'. A browser window will open; "
            "complete the SSO/MFA login to continue (waiting up to %ds).",
            " ".join(cmd),
            self.login_timeout,
        )
        try:
            result = subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=self.login_timeout,
            )
        except subprocess.TimeoutExpired as exc:
            logger.warning(
                "Teleport SSO login did not complete within %ds. %s",
                self.login_timeout,
                (exc.output or "").strip() if isinstance(exc.output, str) else "",
            )
            return False
        except OSError as exc:
            logger.warning("Could not launch '%s login': %s", self.tsh_path, exc)
            return False

        for line in (result.stdout or "").splitlines():
            if line.strip():
                logger.info("tsh login: %s", line.strip())
        if result.returncode != 0:
            logger.warning(
                "Teleport SSO login failed (rc=%d): %s",
                result.returncode,
                (result.stderr or result.stdout or "").strip(),
            )
            return False
        logger.info("Teleport SSO login completed.")
        return True

    def preflight(self) -> None:
        """Verify ``tsh`` is installed and a Teleport session is active.

        When no valid session is found and ``auto_login`` is enabled, runs
        ``tsh login`` (opening the SSO browser window) and re-checks before
        giving up — so an expired session can be refreshed in-place without
        the operator dropping to a terminal.

        Raises:
            TeleportError: If ``tsh`` is missing from PATH, or no session is
                logged in and interactive login was disabled / declined /
                failed (so the operator gets an actionable message instead
                of a generic connection failure later).
        """
        if not shutil.which(self.tsh_path):
            raise TeleportError(
                f"Teleport CLI '{self.tsh_path}' not found on PATH. Install Teleport "
                "(tsh) and ensure it is on your PATH, then try again."
            )

        rc, detail = self._status()
        if rc == 0:
            return

        if self.auto_login:
            logger.info(
                "No active Teleport session (%s) — attempting interactive login.",
                detail or "session expired",
            )
            if self._attempt_interactive_login():
                rc, detail2 = self._status()
                if rc == 0:
                    return
                detail = detail2 or detail

        raise TeleportError(
            "No active Teleport session. Run `tsh login` (and `tsh proxy`/`tsh ssh` "
            "access as required) first." + (f" Details: {detail}" if detail else "")
        )

    # -- node resolution ----------------------------------------------------

    @staticmethod
    def _parse_node_input(raw: str) -> Tuple[Optional[str], str]:
        """Split an optional ``user@`` prefix from a node target.

        Returns ``(user_or_None, token)``. A leading ``user@`` is stripped so
        the user is preserved while the remaining token (hostname, node ID,
        ``key=value`` label, or comma-separated label blob) is resolved.
        ``key=value`` tokens never contain ``@`` first, so partitioning on the
        first ``@`` is safe.
        """
        raw = (raw or "").strip()
        if "@" in raw:
            user, _, token = raw.partition("@")
            token = token.strip()
            if token:
                return (user.strip() or None), token
        return None, raw

    @staticmethod
    def _normalize_nodes(data: Any) -> List[Dict[str, Any]]:
        """Flatten ``tsh ls --format=json`` output to ``{id, hostname, labels}``.

        ``id`` is the dial-able node UUID (``metadata.name``), NOT the
        ``teleport.internal/resource-id`` label (a different id). Static
        (``metadata.labels``) and dynamic (``spec.cmd_labels[*].result``)
        labels are merged so either can be matched.
        """
        out: List[Dict[str, Any]] = []
        for item in data or []:
            if not isinstance(item, dict):
                continue
            md = item.get("metadata", {}) or {}
            spec = item.get("spec", {}) or {}
            labels: Dict[str, str] = dict(md.get("labels", {}) or {})
            for key, val in (spec.get("cmd_labels", {}) or {}).items():
                if isinstance(val, dict) and "result" in val:
                    labels[key] = val["result"]
            out.append(
                {
                    "id": md.get("name", "") or "",
                    "hostname": spec.get("hostname", "") or "",
                    "labels": labels,
                }
            )
        return out

    @staticmethod
    def _label_get(labels: Dict[str, str], key: str) -> Optional[str]:
        """Case-insensitive label lookup."""
        if key in labels:
            return labels[key]
        low = key.lower()
        for k, v in labels.items():
            if k.lower() == low:
                return v
        return None

    @classmethod
    def _match_nodes(cls, nodes: List[Dict[str, Any]], token: str) -> List[Dict[str, Any]]:
        """Return nodes matching ``token``.

        ``token`` may be:
          * a single ``key=value`` label (``cluster_psnt=VA...``),
          * a comma-separated label blob (``cluster_name=...,cluster_psnt=...``)
            — ALL pairs must match (``hostname`` matched against the node
            hostname, everything else against labels),
          * or a bare value matched against the node ID, hostname, or ANY
            label value (so ``VA24129237`` or ``VAST-PI-01`` resolve).
        """
        token = (token or "").strip()
        if not token:
            return []
        pairs = cls._parse_label_pairs(token)
        matches: List[Dict[str, Any]] = []
        if pairs:
            for node in nodes:
                if all(cls._pair_matches(node, key, val) for key, val in pairs):
                    matches.append(node)
            return matches
        low = token.lower()
        for node in nodes:
            if (
                (node.get("id", "") or "").lower() == low
                or (node.get("hostname", "") or "").lower() == low
                or any(str(v).lower() == low for v in (node.get("labels", {}) or {}).values())
            ):
                matches.append(node)
        return matches

    @staticmethod
    def _parse_label_pairs(token: str) -> List[Tuple[str, str]]:
        """Parse ``k=v[,k=v...]`` into pairs; ``[]`` when not label-shaped."""
        if "=" not in token:
            return []
        pairs: List[Tuple[str, str]] = []
        for segment in token.split(","):
            key, sep, val = segment.partition("=")
            if not sep or not key.strip() or not val.strip():
                return []  # malformed -> treat the whole token as bare
            pairs.append((key.strip(), val.strip()))
        return pairs

    @classmethod
    def _pair_matches(cls, node: Dict[str, Any], key: str, val: str) -> bool:
        if key.lower() == "hostname":
            return (node.get("hostname", "") or "").lower() == val.lower()
        label_val = cls._label_get(node.get("labels", {}) or {}, key)
        return label_val is not None and str(label_val).lower() == val.lower()

    @staticmethod
    def _format_candidates(nodes: List[Dict[str, Any]], limit: int = 12) -> str:
        """Human-readable candidate list for no-match / ambiguous errors."""
        lines: List[str] = []
        for node in nodes[:limit]:
            labels = node.get("labels", {}) or {}
            cname = TeleportTunnel._label_get(labels, "cluster_name") or "-"
            psnt = TeleportTunnel._label_get(labels, "cluster_psnt") or "-"
            lines.append(
                f"  hostname={node.get('hostname', '') or '-'}  "
                f"cluster_name={cname}  cluster_psnt={psnt}  id={node.get('id', '') or '-'}"
            )
        if len(nodes) > limit:
            lines.append(f"  ... and {len(nodes) - limit} more")
        return "\n".join(lines)

    @classmethod
    def resolve_node_target(cls, nodes: List[Dict[str, Any]], raw: str, default_user: str) -> str:
        """Resolve ``raw`` to a unique ``user@<node-id>`` dial string.

        When several nodes match but they all belong to the SAME cluster
        (identical, non-empty ``cluster_psnt``), the input named a cluster
        rather than a single node; any of its CNodes is a valid tunnel target,
        so one is auto-picked deterministically. Raises ``TeleportError`` with
        the candidate list only on no match, or when matches span DIFFERENT
        clusters — turning Teleport's cryptic "ambiguous host" / "offline or
        does not exist" failures into actionable guidance.
        """
        user, token = cls._parse_node_input(raw)
        eff_user = user or default_user
        matches = cls._match_nodes(nodes, token)
        if len(matches) == 1:
            return f"{eff_user}@{matches[0]['id']}"
        if not matches:
            raise TeleportError(
                f"No Teleport node matched '{raw}'. Enter a hostname, node ID, "
                "cluster_name, cluster_psnt, or a key=value label. Available nodes:\n" + cls._format_candidates(nodes)
            )
        # Multiple matches that all share one non-empty cluster_psnt name the
        # same cluster, not a node. Any CNode is a valid tunnel target (the API
        # still forwards to the VMS VIP) and `tsh ls` only lists online nodes,
        # so auto-pick one deterministically instead of erroring.
        psnts = {(cls._label_get(n.get("labels", {}) or {}, "cluster_psnt") or "").lower() for n in matches}
        if len(psnts) == 1 and "" not in psnts:
            chosen = sorted(matches, key=lambda n: (n.get("id") or ""))[0]
            logger.info(
                "Teleport target '%s' matched %d nodes of one cluster (cluster_psnt=%s); using node %s (%s).",
                raw,
                len(matches),
                cls._label_get(chosen.get("labels", {}) or {}, "cluster_psnt"),
                chosen.get("hostname") or "?",
                chosen.get("id"),
            )
            return f"{eff_user}@{chosen['id']}"
        raise TeleportError(
            f"Teleport target '{raw}' is ambiguous ({len(matches)} nodes across different clusters). "
            "Use a unique value — node ID, cluster_psnt=<PSNT>, or cluster_name=<name>:\n"
            + cls._format_candidates(matches)
        )

    def _list_nodes(self) -> Optional[List[Dict[str, Any]]]:
        """Return normalized Teleport nodes via ``tsh ls --format=json``.

        Returns ``None`` (not ``[]``) when the listing could not be obtained
        (``tsh`` missing/errored/timed out/unparseable) so the caller can fall
        back to dialing the node target verbatim instead of failing outright.
        """
        try:
            result = subprocess.run(
                [self.tsh_path, "ls", "--format=json"],
                capture_output=True,
                text=True,
                timeout=20,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("'tsh ls' could not be run: %s", exc)
            return None
        if result.returncode != 0:
            logger.debug("'tsh ls' exited %d: %s", result.returncode, (result.stderr or "").strip())
            return None
        try:
            data = json.loads(result.stdout or "[]")
        except ValueError as exc:
            logger.debug("Could not parse 'tsh ls --format=json' output: %s", exc)
            return None
        return self._normalize_nodes(data)

    def _build_command(self) -> List[str]:
        """Construct the ``tsh ssh`` argv with both ``-L`` forwards."""
        cmd: List[str] = [
            self.tsh_path,
            "ssh",
            "-L",
            f"{self.api_local_port}:{self.api_remote_host}:{self.api_remote_port}",
            "-L",
            f"{self.ssh_local_port}:127.0.0.1:{self.ssh_remote_port}",
        ]
        # Prefer the resolved ``user@<node-id>`` (unique). Otherwise fall back:
        # ``user@host`` form carries the login user inline; a bare token is
        # passed verbatim (supports Teleport label queries like ``hostname=...``)
        # with an explicit ``-l <user>``.
        if self._resolved_target:
            cmd.append(self._resolved_target)
        elif "@" in self.node:
            cmd.append(self.node)
        else:
            cmd.extend(["-l", self.ssh_user, self.node])
        cmd.append(_KEEPALIVE_CMD)
        return cmd

    def connect(self) -> None:
        """Run preflight, launch the tunnel, and wait for both ports to open.

        Raises:
            TeleportError: On preflight failure, if ``tsh`` exits early, or if
                either forwarded port does not accept connections within the
                timeout.
        """
        self.preflight()

        # Resolve the operator-entered target to a unique node before dialing.
        # When the inventory is available, this turns any of {hostname, node ID,
        # cluster_name, cluster_psnt, key=value label, label blob, user@...}
        # into an unambiguous ``user@<node-id>`` — and raises an actionable
        # error (candidate list) on no-match / ambiguity instead of letting
        # ``tsh`` fail cryptically. Falls back to verbatim when ``tsh ls`` is
        # unavailable so existing setups keep working.
        nodes = self._list_nodes()
        if nodes is not None:
            self._resolved_target = self.resolve_node_target(nodes, self.node, self.ssh_user)
            logger.info("Resolved Teleport target '%s' -> %s", self.node, self._resolved_target)
        else:
            self._resolved_target = None
            logger.info("Teleport node listing unavailable; using target verbatim: %s", self.node)

        self.api_local_port = _alloc_local_port()
        self.ssh_local_port = _alloc_local_port()
        while self.ssh_local_port == self.api_local_port:
            self.ssh_local_port = _alloc_local_port()

        cmd = self._build_command()
        logger.info(
            "Launching Teleport tunnel: api 127.0.0.1:%d->%s:%d, ssh 127.0.0.1:%d->127.0.0.1:%d (node %s)",
            self.api_local_port,
            self.api_remote_host,
            self.api_remote_port,
            self.ssh_local_port,
            self.ssh_remote_port,
            self.node,
        )

        try:
            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except OSError as exc:
            raise TeleportError(f"Failed to launch '{self.tsh_path} ssh': {exc}") from exc

        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if self._proc.poll() is not None:
                # tsh exited before the forwards came up — surface its output.
                _out, err = self._drain_proc()
                raise TeleportError(
                    "Teleport tunnel process exited early (rc="
                    f"{self._proc.returncode}). {err.strip() or _out.strip()}".strip()
                )
            if _port_open(self.api_local_port) and _port_open(self.ssh_local_port):
                logger.info(
                    "Teleport tunnel active: API %s, SSH %s",
                    self.api_local_address,
                    self.ssh_local_address,
                )
                return
            time.sleep(0.5)

        # Timed out waiting for the forwards.
        self.close()
        raise TeleportError(
            "Teleport tunnel did not become ready within "
            f"{self.timeout}s (api port {self.api_local_port}, ssh port {self.ssh_local_port}). "
            "Verify the node target and that your Teleport role permits port forwarding."
        )

    def _drain_proc(self) -> Tuple[str, str]:
        """Best-effort read of the subprocess stdout/stderr after exit."""
        if self._proc is None:
            return "", ""
        try:
            out, err = self._proc.communicate(timeout=2)
            return out or "", err or ""
        except Exception:
            return "", ""

    def close(self) -> None:
        """Terminate the ``tsh`` subprocess, tearing down both forwards."""
        if self._proc is None:
            return
        proc = self._proc
        self._proc = None
        if proc.poll() is None:
            try:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Error terminating Teleport tunnel: %s", exc)
        logger.info("Teleport tunnel closed")

    def __enter__(self) -> "TeleportTunnel":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
