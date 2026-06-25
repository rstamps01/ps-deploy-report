"""
VMS Auto-Discovery and API Proxy Tunnel.

Enables the As-Built Reporter to connect to any CBox Tech Port (192.168.2.2)
and automatically discover the VMS, then tunnel all API calls through a
two-hop SSH chain directly to the VMS localhost.

Discovery and tunnel chain:
    1. SSH to Tech Port (any CBox) → run ``find-vms`` → VMS internal IP
    2. SSH hop to VMS internal IP → ``ip addr`` → VMS management IP
    3. Nested SSH from Tech Port → VMS internal IP (port 22)
    4. ``direct-tcpip`` channel from VMS → 127.0.0.1:443 (VMS localhost)
    5. Local TCP listener forwards ``requests`` traffic through the tunnel

By terminating on the VMS loopback, the management REST API is reached
directly — bypassing the S3 gateway virtual-host routing that intercepts
connections arriving on external management VIPs.

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
import shlex
import threading
from typing import List, Optional, Tuple

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

# TP-2: widened to also accept CGNAT 100.64/10 (RFC 6598).  On VAST IPoIB
# clusters the customer-facing VMS UI is typically bound to a CGNAT address
# on em3 (e.g. 100.64.44.2:443 served by nginx), so candidate enumeration
# must include it.  Link-local 169.254/16 is still excluded (no API ever).
_PRIVATE_RE = re.compile(
    r"\binet\s+("
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    r"|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}"
    r"|192\.168\.\d{1,3}\.\d{1,3}"
    r"|100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}"
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


# Interface-name prefixes treated as Ethernet (vs Infiniband) for ordering.
_ETH_IFACE_PREFIXES: Tuple[str, ...] = ("em", "eno", "enp", "ens", "eth", "p")


def _classify_iface(iface: str) -> Tuple[str, str]:
    """Return ``(base, alias)`` for an iface name, splitting on ``:``.

    ``"bond0:m"`` -> ``("bond0", "m")``; ``"em3"`` -> ``("em3", "")``.
    """
    base, _, alias = iface.partition(":")
    return base, alias


def parse_management_ip_candidates(ip_addr_output: Optional[str]) -> List[str]:
    """Return candidate management IPs from ``ip addr show`` in probe order.

    The intent is empirical: discovery should probe each candidate on TCP/443
    and pick the first that actually serves the VMS API.  Without probing,
    no parse heuristic can reliably distinguish (e.g.) the IPoIB-internal
    ``bond0:m`` mgmt VIP from the customer-facing ``em3`` base IP.

    Probe priority (highest first):
      1. Plain Ethernet base addresses (``em*``, ``eno*``, ``enp*``, ``eth*``,
         etc.) -- the typical customer mgmt LAN.
      2. Plain Ethernet ``:e`` (external) aliases.
      3. Plain Ethernet other-aliased / secondary addresses.
      4. Infiniband device base addresses (``ib*``).
      5. Infiniband ``:a`` / ``:b`` / non-``:m`` aliases.
      6. Bond + ``:m`` aliases (last -- internal IPoIB mgmt VIP, only useful
         when the cluster wires the customer API there too).

    Excludes loopback, docker / bridge / veth / vpn devices and link-local
    addresses.  Includes RFC1918 + CGNAT (RFC 6598).  Deduplicates.
    """
    if not ip_addr_output:
        return []

    eth_base: List[str] = []
    eth_e: List[str] = []
    eth_other: List[str] = []
    ib_base: List[str] = []
    ib_alias: List[str] = []
    bond_m: List[str] = []

    seen: set = set()

    for line in ip_addr_output.splitlines():
        stripped = line.strip()
        match = _PRIVATE_RE.search(stripped)
        if not match:
            continue
        if "scope global" not in stripped:
            continue

        tokens = stripped.split()
        iface = tokens[-1] if tokens else ""
        if _iface_excluded(iface):
            continue

        ip = match.group(1)
        if ip in seen:
            continue
        seen.add(ip)

        base, alias = _classify_iface(iface)
        is_secondary = "secondary" in stripped
        is_ib_or_bond = base.startswith("ib") or base.startswith("bond")

        if alias == "m":
            bond_m.append(ip)
        elif is_ib_or_bond:
            if alias:
                ib_alias.append(ip)
            else:
                ib_base.append(ip)
        else:
            # Plain Ethernet family.
            if alias == "e":
                eth_e.append(ip)
            elif alias or is_secondary:
                eth_other.append(ip)
            else:
                eth_base.append(ip)

    return eth_base + eth_e + eth_other + ib_base + ib_alias + bond_m


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

    # TP-2: empirical candidate probing.  Pre-TP-2 we picked by interface
    # alias convention (`:m` first), but on VAST IPoIB clusters the actual
    # VMS UI lives on em3's CGNAT base IP (nginx) while bond0:m is an
    # internal cluster-mgmt VIP that does NOT serve 443.  Enumerate every
    # plausible candidate and TCP-probe each one from the tech port.
    candidates = parse_management_ip_candidates(out)
    if not candidates:
        raise VMSDiscoveryError(
            f"No candidate management IP found on VMS CNode {vms_internal_ip}. "
            f"No RFC1918 / CGNAT address was present on a non-excluded "
            f"interface. Discovered ip-addr output:\n{out!r}"
        )

    probe_results = _first_443_reachable(entry_host, ssh_user, ssh_password, candidates, timeout=timeout)
    for ip, status in probe_results:
        if status == "OPEN":
            logger.info("VMS management IP: %s (probe: %s)", ip, _format_probe_log(probe_results))
            return vms_internal_ip, ip

    raise VMSDiscoveryError(
        f"No candidate management IP responded on 443 from {entry_host}. "
        f"Probed: {_format_probe_log(probe_results)}. "
        f"Hint: confirm the VMS service is running on the cluster and that "
        f"the tech port can reach the management network on TCP/443."
    )


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


def _first_443_reachable(
    entry_host: str,
    ssh_user: str,
    ssh_password: str,
    candidates: List[str],
    timeout: int = 30,
) -> List[Tuple[str, str]]:
    """Probe TCP/443 on each candidate from *entry_host* in a single SSH session.

    Returns a list of ``(ip, status)`` tuples in the same order as the input
    candidates, where ``status`` is ``"OPEN"``, ``"CLOSED"``, or ``"ERROR"``.
    The shell loop short-circuits at the first OPEN to keep typical-case
    latency low (one ~0.1s connect for the winner).

    Implementation note: uses bash ``/dev/tcp`` and a per-candidate
    ``timeout 2`` so a single hung TCP/443 cannot stall the whole probe.
    """
    if not candidates:
        return []

    quoted_ips = " ".join(shlex.quote(ip) for ip in candidates)
    probe = (
        "for ip in " + quoted_ips + "; do "
        "if timeout 2 bash -c '</dev/tcp/'\"$ip\"'/443' 2>/dev/null; "
        'then echo "$ip OPEN"; break; '
        'else echo "$ip CLOSED"; fi; '
        "done"
    )
    try:
        rc, out, _err = run_ssh_command(
            entry_host,
            ssh_user,
            ssh_password,
            probe,
            timeout=timeout,
        )
    except Exception as exc:  # pragma: no cover - SSH layer is mocked in tests
        logger.debug("Multi-probe raised %s", exc)
        return [(ip, "ERROR") for ip in candidates]

    parsed: List[Tuple[str, str]] = []
    if rc == 0 and out:
        seen: set = set()
        for line in out.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0] in candidates and parts[1] in ("OPEN", "CLOSED"):
                if parts[0] in seen:
                    continue
                seen.add(parts[0])
                parsed.append((parts[0], parts[1]))
    # Fill in any candidate the loop short-circuited past, marking them
    # UNTESTED so they don't masquerade as CLOSED in error messages.
    parsed_ips = {ip for ip, _ in parsed}
    for ip in candidates:
        if ip not in parsed_ips:
            parsed.append((ip, "UNTESTED"))
    return parsed


def _format_probe_log(results: List[Tuple[str, str]]) -> str:
    """One-line readable summary of probe results for log/error messages."""
    return ", ".join(f"{ip}={status}" for ip, status in results)


# ---------------------------------------------------------------------------
# TCP Tunnel via paramiko
# ---------------------------------------------------------------------------


class VMSTunnel:
    """Two-hop SSH tunnel forwarding a local TCP port to VMS localhost:443.

    Connection chain:
        local:random_port → SSH(tech_port_ip) → SSH(vms_internal_ip) →
        direct-tcpip(127.0.0.1:443 on VMS)

    By terminating on the VMS's own loopback interface, the management API
    is reached directly — bypassing the S3 gateway virtual-host routing that
    intercepts connections arriving on external management VIPs.

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
        self._vms_ssh_client: Optional[paramiko.SSHClient] = None
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
        """Discover VMS and open the two-hop forwarding tunnel.

        Chain: tech_port → VMS internal IP → localhost:443 on VMS.

        Raises:
            VMSDiscoveryError: If VMS discovery fails.
            RuntimeError: If the SSH transport cannot be established.
        """
        # 1. Discover VMS management IP (also determines vms_internal_ip)
        self.vms_internal_ip, self.vms_management_ip = discover_vms_management_ip(
            self.tech_port_ip, self.ssh_user, self.ssh_password, self.timeout
        )

        # 2. SSH to entry CNode (tech port)
        logger.info("Opening persistent SSH to %s for API tunnel...", self.tech_port_ip)
        self._ssh_client = paramiko.SSHClient()
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
        entry_transport = self._ssh_client.get_transport()
        if entry_transport is None:
            raise RuntimeError("SSH transport unavailable after connect to tech port")
        entry_transport.set_keepalive(15)

        # 3. Nested SSH hop: tech port → VMS internal IP
        logger.info("Opening nested SSH hop to VMS %s ...", self.vms_internal_ip)
        vms_channel = entry_transport.open_channel(
            "direct-tcpip",
            (self.vms_internal_ip, 22),
            ("127.0.0.1", 0),
        )
        self._vms_ssh_client = paramiko.SSHClient()
        self._vms_ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # nosec B507
        self._vms_ssh_client.connect(
            self.vms_internal_ip,
            username=self.ssh_user,
            password=self.ssh_password,
            sock=vms_channel,
            timeout=self.timeout,
            banner_timeout=self.timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        vms_transport = self._vms_ssh_client.get_transport()
        if vms_transport is None:
            raise RuntimeError("SSH transport unavailable after connect to VMS")
        vms_transport.set_keepalive(15)

        # 4. Bind local listener
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind(("127.0.0.1", 0))
        self.local_port = self._server_socket.getsockname()[1]
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)

        # 5. Accept loop in background
        self._running = True
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

        logger.info(
            "VMS API tunnel active: 127.0.0.1:%d → %s (SSH) → 127.0.0.1:%d (via %s)",
            self.local_port,
            self.vms_internal_ip,
            self.remote_port,
            self.tech_port_ip,
        )

    def close(self) -> None:
        """Shut down the tunnel, listener, and both SSH connections."""
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

        if self._vms_ssh_client:
            try:
                self._vms_ssh_client.close()
            except Exception:
                pass
            self._vms_ssh_client = None

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
        """Forward one TCP connection through the two-hop SSH tunnel to VMS localhost."""
        channel = None
        try:
            assert self._vms_ssh_client is not None
            transport = self._vms_ssh_client.get_transport()
            if transport is None or not transport.is_active():
                logger.warning("VMS SSH transport not active, dropping connection")
                local_sock.close()
                return

            channel = transport.open_channel(
                "direct-tcpip",
                ("127.0.0.1", self.remote_port),
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
