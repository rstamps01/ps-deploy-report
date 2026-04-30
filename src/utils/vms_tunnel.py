"""
VMS Auto-Discovery and API Proxy Tunnel.

Enables the As-Built Reporter to connect to any CBox Tech Port (192.168.2.2)
and automatically discover the VMS management IP, then tunnel all API calls
through the SSH connection.

Discovery chain:
    1. SSH to Tech Port (any CBox) → run ``find-vms`` → VMS internal IP
    2. SSH hop to VMS internal IP → ``ip addr`` → VMS management IP
    3. Open paramiko ``direct-tcpip`` channel to management IP:443
    4. Local TCP listener forwards ``requests`` traffic through the tunnel

Usage::

    with VMSTunnel("192.168.2.2", "vastdata", "vastdata") as tunnel:
        tunnel.connect()
        handler = create_vast_api_handler(
            cluster_ip="192.168.2.2",
            tunnel_address=tunnel.local_bind_address,
            ...
        )
        handler.authenticate()
        data = handler.get_all_data()
"""

import logging
import re
import select
import socket
import threading
from typing import Optional, Tuple

import paramiko  # type: ignore[import-untyped]

from utils.ssh_adapter import run_ssh_command

logger = logging.getLogger(__name__)


class VMSDiscoveryError(Exception):
    """Raised when VMS auto-discovery fails."""


# ---------------------------------------------------------------------------
# Parsing helpers (pure functions, no I/O)
# ---------------------------------------------------------------------------

_IP_RE = re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b")

# RFC1918 private ranges (10/8, 172.16/12, 192.168/16) anchored to `inet `
# preamble so `inet6` lines and bare textual matches are skipped.  CGNAT
# (100.64/10, RFC 6598) and link-local (169.254/16) are intentionally NOT
# part of this set: they must never be picked as a management IP.
_RFC1918_RE = re.compile(
    r"\binet\s+("
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r")/\d+"
)

# Interface name prefixes whose addresses are never the cluster mgmt IP.
# Matches both exact names (`lo`, `docker0`) and aliased forms (`docker0:e`).
_EXCLUDE_IFACE_PREFIXES: Tuple[str, ...] = (
    "lo",
    "docker",
    "br-",
    "veth",
    "tun",
    "tap",
    "tailscale",
    "virbr",
    "vnet",
    "cni",
    "flannel",
)


def _iface_excluded(iface: str) -> bool:
    """True if *iface* belongs to an excluded class (loopback, container, vpn)."""
    if not iface:
        return False
    base = iface.split(":", 1)[0]  # strip any `:alias` suffix
    return any(base == p or base.startswith(p) for p in _EXCLUDE_IFACE_PREFIXES)


def parse_find_vms_output(output: str) -> Optional[str]:
    """Extract VMS internal IP from ``find-vms`` command output.

    ``find-vms`` typically returns a single line like ``172.16.3.4``.
    This function finds the first valid IPv4 address in the output.

    Returns:
        The VMS internal IP string, or ``None`` if no IP was found.
    """
    if not output or not output.strip():
        return None
    match = _IP_RE.search(output)
    if match:
        ip = match.group(1)
        octets = ip.split(".")
        if all(0 <= int(o) <= 255 for o in octets):
            return ip
    return None


def parse_management_ip(ip_addr_output: str) -> Optional[str]:
    """Extract the cluster management IP from ``ip addr show`` output.

    Selection priority (media-agnostic; works on Ethernet, Infiniband / IPoIB,
    bonds, etc.):

    1. RFC1918 ``scope global`` address whose interface name ends in ``:m``
       (VAST mgmt VIP convention, e.g. ``bond0:m`` on IB clusters).
    2. RFC1918 non-secondary ``scope global`` address on a non-excluded
       interface (loopback, docker, bridge, veth, vpn devices excluded).
    3. RFC1918 secondary ``scope global`` address on a non-excluded interface.

    CGNAT (100.64/10), link-local (169.254/16), and IPv6 are intentionally
    not considered.  Returns ``None`` when no candidate matches.
    """
    if not ip_addr_output:
        return None

    m_alias_pick: Optional[str] = None
    primary_pick: Optional[str] = None
    secondary_pick: Optional[str] = None

    for line in ip_addr_output.splitlines():
        stripped = line.strip()
        match = _RFC1918_RE.search(stripped)
        if not match:
            continue
        if "scope global" not in stripped:
            continue

        tokens = stripped.split()
        iface = tokens[-1] if tokens else ""
        if _iface_excluded(iface):
            continue

        ip = match.group(1)
        is_secondary = "secondary" in stripped

        if iface.endswith(":m") and not is_secondary and m_alias_pick is None:
            m_alias_pick = ip
        elif not is_secondary and primary_pick is None:
            primary_pick = ip
        elif is_secondary and secondary_pick is None:
            secondary_pick = ip

    return m_alias_pick or primary_pick or secondary_pick


# ---------------------------------------------------------------------------
# SSH-based VMS discovery
# ---------------------------------------------------------------------------


def discover_vms_management_ip(
    entry_host: str,
    ssh_user: str,
    ssh_password: str,
    timeout: int = 30,
) -> Tuple[str, str]:
    """Discover VMS management IP via two-hop SSH chain.

    1. SSH to *entry_host* (Tech Port or any CNode management IP).
    2. Run ``find-vms`` to obtain the VMS internal IP.
    3. From *entry_host*, SSH hop to VMS internal IP and run
       ``ip addr show`` to extract the VMS management IP.

    Args:
        entry_host: IP of the CNode to SSH into (e.g. 192.168.2.2).
        ssh_user:   SSH username (typically ``vastdata``).
        ssh_password: SSH password.
        timeout:    Per-command SSH timeout in seconds.

    Returns:
        Tuple of (vms_internal_ip, vms_management_ip).

    Raises:
        VMSDiscoveryError: If any step in the discovery chain fails.
    """
    # Step 1: Discover VMS internal IP.  ``find-vms`` is a shell alias
    # (clush + docker ps) that only works in interactive sessions.  We use
    # two fallback strategies that work non-interactively:
    #   1. Parse /etc/motd — VAST updates this with "VMS: <ip>" on every CNode
    #   2. Run the expanded alias chain directly via clush
    logger.info("Discovering VMS via SSH to %s ...", entry_host)

    # Strategy 1: parse /etc/motd (fast, local file, no PATH dependency)
    rc, out, err = run_ssh_command(
        entry_host,
        ssh_user,
        ssh_password,
        "grep 'VMS:' /etc/motd 2>/dev/null",
        timeout=timeout,
    )
    vms_internal_ip = parse_find_vms_output(out) if rc == 0 else None

    # Strategy 2: expanded find-vms alias (clush + docker ps)
    if not vms_internal_ip:
        logger.debug("MOTD parse failed, trying clush fallback...")
        clush_cmd = (
            "clush -g cnodes "
            "'docker ps --format \"{{.Names}}\" | grep vast_vms' "
            "2>/dev/null | cut -d: -f1 | head -1"
        )
        rc, out, err = run_ssh_command(
            entry_host,
            ssh_user,
            ssh_password,
            clush_cmd,
            timeout=timeout,
        )
        vms_internal_ip = parse_find_vms_output(out) if rc == 0 else None

    if not vms_internal_ip:
        raise VMSDiscoveryError(f"Could not discover VMS IP on {entry_host} " f"(motd and clush both failed): {err}")
    logger.info("VMS internal IP: %s", vms_internal_ip)

    # Step 1.5: 443 short-circuit.
    # On many clusters (especially IPoIB) the VMS internal IP discovered via
    # /etc/motd is itself the management VIP and already serves the VMS UI on
    # TCP/443.  When that's the case, skip the second SSH hop entirely; this
    # avoids the historical "no 10.x.x.x found" failure mode on clusters whose
    # mgmt network lives in 172.16/12 or 192.168/16 (TP-1).
    if _check_management_via_internal_ip(
        entry_host,
        ssh_user,
        ssh_password,
        vms_internal_ip,
        timeout=timeout,
    ):
        logger.info(
            "VMS internal IP %s already answers on 443; skipping ip-addr hop",
            vms_internal_ip,
        )
        return vms_internal_ip, vms_internal_ip

    # Step 2: SSH hop to VMS internal IP, get management IP from `ip addr`.
    # Note: do NOT pre-filter with `grep 'inet 10\\.'` -- TP-1 fix.  The
    # parser handles RFC1918 ranges itself and excludes loopback / docker /
    # CGNAT / link-local interfaces by name and class.
    ip_cmd = "ip addr show 2>/dev/null"
    rc, out, err = run_ssh_command(
        vms_internal_ip,
        ssh_user,
        ssh_password,
        ip_cmd,
        timeout=timeout,
        jump_host=entry_host,
        jump_user=ssh_user,
        jump_password=ssh_password,
    )
    if rc != 0:
        raise VMSDiscoveryError(f"Failed to get management IP from VMS CNode {vms_internal_ip} (rc={rc}): {err}")

    vms_mgmt_ip = parse_management_ip(out)
    if not vms_mgmt_ip:
        raise VMSDiscoveryError(
            f"Could not parse management IP from VMS CNode {vms_internal_ip}. "
            f"No RFC1918 address (10/8, 172.16/12, 192.168/16) was found on a "
            f"non-excluded interface. Discovered ip-addr output:\n{out!r}"
        )
    logger.info("VMS management IP: %s", vms_mgmt_ip)

    return vms_internal_ip, vms_mgmt_ip


def _check_management_via_internal_ip(
    entry_host: str,
    ssh_user: str,
    ssh_password: str,
    internal_ip: str,
    timeout: int = 30,
) -> bool:
    """Return True if *internal_ip* answers on TCP/443 from *entry_host*.

    Uses bash's ``/dev/tcp`` pseudo-device so no extra package (nc, socat) is
    required.  Wrapped in ``timeout 3`` so a hung connection cannot stall
    discovery longer than the SSH command timeout.  A non-zero exit status
    or any value other than ``OPEN`` in stdout means "not reachable".
    """
    probe = f"timeout 3 bash -c '</dev/tcp/{internal_ip}/443' 2>/dev/null " f"&& echo OPEN || echo CLOSED"
    try:
        rc, out, _err = run_ssh_command(
            entry_host,
            ssh_user,
            ssh_password,
            probe,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - SSH layer is mocked in tests
        logger.debug("443 probe raised %s; falling through to ip-addr", exc)
        return False
    return rc == 0 and "OPEN" in (out or "")


# ---------------------------------------------------------------------------
# TCP Tunnel via paramiko
# ---------------------------------------------------------------------------


class VMSTunnel:
    """SSH tunnel forwarding a local TCP port to VMS management IP:443.

    The tunnel uses paramiko's ``direct-tcpip`` channel through an SSH
    connection to a CNode.  A local TCP server accepts connections on
    ``127.0.0.1:<random_port>`` and forwards each one through the channel
    to the VMS management IP.

    Attributes:
        vms_internal_ip:  Internal cluster IP discovered via ``find-vms``.
        vms_management_ip: Management IP discovered via ``ip addr``.
        local_port:       Local TCP port accepting forwarded connections.
    """

    def __init__(
        self,
        tech_port_ip: str,
        ssh_user: str,
        ssh_password: str,
        remote_port: int = 443,
        timeout: int = 30,
    ):
        self.tech_port_ip = tech_port_ip
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self.remote_port = remote_port
        self.timeout = timeout

        self._ssh_client: Optional[paramiko.SSHClient] = None
        self._server_socket: Optional[socket.socket] = None
        self._accept_thread: Optional[threading.Thread] = None
        self._running = False
        self._forwarding_threads: list[threading.Thread] = []

        self.vms_internal_ip: Optional[str] = None
        self.vms_management_ip: Optional[str] = None
        self.local_port: Optional[int] = None

    @property
    def local_bind_address(self) -> str:
        """Connection string for the API handler (``127.0.0.1:<port>``)."""
        if self.local_port is None:
            raise RuntimeError("Tunnel not connected; call connect() first")
        return f"127.0.0.1:{self.local_port}"

    # -- lifecycle -----------------------------------------------------------

    def connect(self) -> None:
        """Discover VMS and open the forwarding tunnel.

        Raises:
            VMSDiscoveryError: If VMS discovery fails.
            RuntimeError: If the SSH transport cannot be established.
        """
        # 1. Discover VMS management IP
        self.vms_internal_ip, self.vms_management_ip = discover_vms_management_ip(
            self.tech_port_ip, self.ssh_user, self.ssh_password, self.timeout
        )

        # 2. SSH to entry CNode (kept alive for the tunnel lifetime)
        logger.info("Opening persistent SSH to %s for API tunnel...", self.tech_port_ip)
        self._ssh_client = paramiko.SSHClient()
        # Intentional [B507]: tunnel target is the freshly-deployed CNode (tech_port_ip) used for
        # post-install discovery; AutoAddPolicy is required for first-contact operations.
        self._ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
        self._ssh_client.connect(
            self.tech_port_ip,
            username=self.ssh_user,
            password=self.ssh_password,
            timeout=self.timeout,
            banner_timeout=self.timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        transport = self._ssh_client.get_transport()
        if transport is None:
            raise RuntimeError("SSH transport unavailable after connect")
        transport.set_keepalive(15)

        # 3. Bind local listener
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(("127.0.0.1", 0))
        self.local_port = self._server_socket.getsockname()[1]
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)

        # 4. Accept loop in background
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

        logger.info(
            "VMS API tunnel active: 127.0.0.1:%d → %s:%d (via %s)",
            self.local_port,
            self.vms_management_ip,
            self.remote_port,
            self.tech_port_ip,
        )

    def close(self) -> None:
        """Shut down the tunnel, listener, and SSH connection."""
        self._running = False

        if self._server_socket:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None

        if self._accept_thread and self._accept_thread.is_alive():
            self._accept_thread.join(timeout=3)

        for t in self._forwarding_threads:
            t.join(timeout=2)
        self._forwarding_threads.clear()

        if self._ssh_client:
            try:
                self._ssh_client.close()
            except Exception:
                pass
            self._ssh_client = None

        logger.info("VMS API tunnel closed")

    def __enter__(self) -> "VMSTunnel":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    # -- internal forwarding -------------------------------------------------

    def _accept_loop(self) -> None:
        """Accept incoming TCP connections and spawn forwarders."""
        while self._running:
            try:
                client_sock, addr = self._server_socket.accept()  # type: ignore[union-attr]
            except socket.timeout:
                continue
            except OSError:
                break

            t = threading.Thread(target=self._forward_connection, args=(client_sock,), daemon=True)
            t.start()
            self._forwarding_threads.append(t)

    def _forward_connection(self, local_sock: socket.socket) -> None:
        """Forward one TCP connection through the SSH tunnel."""
        channel = None
        try:
            assert self._ssh_client is not None
            transport = self._ssh_client.get_transport()
            if transport is None or not transport.is_active():
                logger.warning("SSH transport not active, dropping connection")
                local_sock.close()
                return

            channel = transport.open_channel(
                "direct-tcpip",
                (self.vms_management_ip, self.remote_port),
                local_sock.getpeername(),
            )

            while self._running:
                r, _w, _x = select.select([local_sock, channel], [], [], 1.0)
                if local_sock in r:
                    data = local_sock.recv(32768)
                    if not data:
                        break
                    channel.sendall(data)
                if channel in r:
                    data = channel.recv(32768)
                    if not data:
                        break
                    local_sock.sendall(data)
        except Exception as exc:
            logger.debug("Tunnel forwarding ended: %s", exc)
        finally:
            if channel:
                try:
                    channel.close()
                except Exception:
                    pass
            try:
                local_sock.close()
            except Exception:
                pass
