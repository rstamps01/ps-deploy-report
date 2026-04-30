"""Tests for VMS auto-discovery and API proxy tunnel."""

import socket
import threading
from unittest.mock import MagicMock, patch

import pytest

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from utils.vms_tunnel import (
    VMSDiscoveryError,
    VMSTunnel,
    discover_vms_management_ip,
    parse_find_vms_output,
    parse_management_ip,
)
from api_handler import VastApiHandler, create_vast_api_handler

# ---------------------------------------------------------------------------
# parse_find_vms_output
# ---------------------------------------------------------------------------


class TestParseFindVmsOutput:
    def test_simple_ip(self):
        assert parse_find_vms_output("172.16.3.4\n") == "172.16.3.4"

    def test_ip_with_whitespace(self):
        assert parse_find_vms_output("  172.16.3.4  \n") == "172.16.3.4"

    def test_ip_with_extra_text(self):
        assert parse_find_vms_output("VMS is at 172.16.3.4 on cnode-3-4\n") == "172.16.3.4"

    def test_empty_output(self):
        assert parse_find_vms_output("") is None

    def test_none_output(self):
        assert parse_find_vms_output(None) is None  # type: ignore[arg-type]

    def test_whitespace_only(self):
        assert parse_find_vms_output("   \n  \n") is None

    def test_no_ip_in_output(self):
        assert parse_find_vms_output("command not found: find-vms") is None

    def test_ten_network_ip(self):
        assert parse_find_vms_output("10.143.11.202\n") == "10.143.11.202"

    def test_multiline_picks_first(self):
        output = "172.16.3.4\n10.143.11.202\n"
        assert parse_find_vms_output(output) == "172.16.3.4"

    def test_invalid_octet(self):
        assert parse_find_vms_output("999.999.999.999") is None


# ---------------------------------------------------------------------------
# parse_management_ip
# ---------------------------------------------------------------------------

SELAB_IP_ADDR_OUTPUT = """\
    inet 10.143.11.202/16 scope global enp194s0f0
    inet 10.143.11.61/16 scope global secondary enp194s0f0:e
"""

SINGLE_IP_OUTPUT = """\
    inet 10.1.2.3/24 scope global eth0
"""

SECONDARY_ONLY_OUTPUT = """\
    inet 10.1.2.3/24 scope global secondary eth0
    inet 10.4.5.6/24 scope global secondary eth1
"""

# Pre-TP-1 fixture renamed: this used to assert None because the parser was
# hard-coded to 10.x.x.x. After the fix, the first non-secondary RFC1918
# address is the expected result.
NO_TEN_NETWORK = """\
    inet 192.168.1.100/24 scope global eth0
    inet 172.16.3.4/16 scope global eth1
"""

# IPv4 only on lo / docker / CGNAT — no routable management IP at all.
LOOPBACK_AND_CGNAT_ONLY = """\
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536
    inet 127.0.0.1/8 scope host lo
2: docker0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
3: em3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    inet 100.64.44.2/20 scope global em3
"""

# Realistic mammoth (Infiniband / IPoIB) payload.  Mgmt VIP lives on the
# `bond0:m` alias on top of an ib2 (mtu 2044) device.
MAMMOTH_IP_ADDR_OUTPUT = """\
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    inet 127.0.0.1/8 scope host lo
2: em1: <BROADCAST,MULTICAST> mtu 1500 qdisc noop state DOWN group default qlen 1000
3: em2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    inet 192.168.3.3/24 brd 192.168.3.255 scope global em2
4: em3: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    inet 100.64.44.2/20 scope global em3
    inet 100.64.44.9/20 scope global secondary em3:e
7: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc fq state UP group default qlen 256
    inet 172.16.254.243/24 scope global ib0
    inet 100.64.24.4/20 scope global ib0
8: ib1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc fq state UP group default qlen 256
    inet 100.64.24.13/20 scope global ib1
9: ib2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc fq state UP group default qlen 256
    inet 172.16.0.4/18 brd 172.16.63.255 scope global ib2:a
    inet 172.16.64.4/18 brd 172.16.127.255 scope global ib3:b
    inet 172.16.128.4/18 brd 172.16.191.255 scope global bond0:m
    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0
"""

# Single IB device with mgmt alias `:m` directly on it (no bond).
IB_M_ALIAS_DIRECT = """\
1: ib0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc fq state UP group default qlen 256
    inet 172.16.5.10/24 scope global ib0
    inet 172.16.5.99/24 scope global ib0:m
"""


class TestParseManagementIp:
    def test_selab_primary(self):
        assert parse_management_ip(SELAB_IP_ADDR_OUTPUT) == "10.143.11.202"

    def test_single_ip(self):
        assert parse_management_ip(SINGLE_IP_OUTPUT) == "10.1.2.3"

    def test_secondary_only_falls_back(self):
        assert parse_management_ip(SECONDARY_ONLY_OUTPUT) == "10.1.2.3"

    def test_picks_first_rfc1918_when_no_ten_network(self):
        # Inverted from pre-TP-1 behaviour (was: returns None).
        assert parse_management_ip(NO_TEN_NETWORK) == "192.168.1.100"

    def test_empty_output(self):
        assert parse_management_ip("") is None

    def test_none_output(self):
        assert parse_management_ip(None) is None  # type: ignore[arg-type]

    # ----- TP-1 coverage: RFC1918 ranges + IB + `:m` alias priority -----

    def test_mammoth_ib_picks_bond0_m(self):
        # Realistic mammoth payload; mgmt VIP lives on `bond0:m`.
        assert parse_management_ip(MAMMOTH_IP_ADDR_OUTPUT) == "172.16.128.4"

    def test_picks_iface_m_alias_on_ib(self):
        # `:m` alias directly on IB device (no bond) still wins.
        assert parse_management_ip(IB_M_ALIAS_DIRECT) == "172.16.5.99"

    def test_172_16_network(self):
        out = "    inet 172.16.10.5/24 scope global eth0\n"
        assert parse_management_ip(out) == "172.16.10.5"

    def test_192_168_network(self):
        out = "    inet 192.168.50.5/24 scope global eth0\n"
        assert parse_management_ip(out) == "192.168.50.5"

    def test_excludes_loopback(self):
        out = "    inet 127.0.0.1/8 scope host lo\n    inet 10.0.0.1/24 scope global eth0\n"
        assert parse_management_ip(out) == "10.0.0.1"

    def test_excludes_cgnat_100_64(self):
        out = "    inet 100.64.44.2/20 scope global em3\n    inet 192.168.1.5/24 scope global eth0\n"
        assert parse_management_ip(out) == "192.168.1.5"

    def test_excludes_docker_bridge(self):
        out = "    inet 172.17.0.1/16 brd 172.17.255.255 scope global docker0\n    inet 172.16.5.10/24 scope global eth0\n"
        assert parse_management_ip(out) == "172.16.5.10"

    def test_excludes_secondary_when_primary_present(self):
        out = "    inet 10.1.2.3/24 scope global secondary eth0:e\n" "    inet 10.4.5.6/24 scope global eth1\n"
        assert parse_management_ip(out) == "10.4.5.6"

    def test_ipoib_high_mtu_no_effect(self):
        # mtu 2044 on the interface header line must not confuse the parser.
        out = (
            "9: ib2: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 2044 qdisc fq state UP\n"
            "    inet 172.16.10.5/18 scope global ib2\n"
        )
        assert parse_management_ip(out) == "172.16.10.5"

    def test_no_routable_ip_returns_none(self):
        # Loopback + CGNAT + docker only — nothing should match.
        assert parse_management_ip(LOOPBACK_AND_CGNAT_ONLY) is None

    def test_excludes_bridge_and_veth(self):
        out = (
            "    inet 192.168.42.1/24 scope global br-abc123\n"
            "    inet 169.254.1.1/16 scope link veth0a1b\n"
            "    inet 10.0.0.5/24 scope global eth0\n"
        )
        assert parse_management_ip(out) == "10.0.0.5"


# ---------------------------------------------------------------------------
# discover_vms_management_ip
# ---------------------------------------------------------------------------


# Probe response constants for the new 443 short-circuit step.
# Format mirrors what `_check_management_via_internal_ip` emits over SSH.
_PROBE_443_OPEN = (0, "OPEN\n", "")
_PROBE_443_CLOSED = (0, "CLOSED\n", "")


class TestDiscoverVmsManagementIp:
    @patch("utils.vms_tunnel.run_ssh_command")
    def test_success_via_motd(self, mock_ssh):
        """MOTD discovery + 443 closed -> ip-addr hop."""
        mock_ssh.side_effect = [
            (0, "\u2502 VMS:    172.16.3.4                \u2502\n", ""),
            _PROBE_443_CLOSED,
            (0, SELAB_IP_ADDR_OUTPUT, ""),
        ]
        internal, mgmt = discover_vms_management_ip("192.168.2.2", "vastdata", "pw")
        assert internal == "172.16.3.4"
        assert mgmt == "10.143.11.202"
        assert mock_ssh.call_count == 3

        first_call = mock_ssh.call_args_list[0]
        assert first_call[0][0] == "192.168.2.2"
        assert "motd" in first_call[0][3]

        third_call = mock_ssh.call_args_list[2]
        assert third_call[0][0] == "172.16.3.4"
        assert third_call[1]["jump_host"] == "192.168.2.2"

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_success_via_clush_fallback(self, mock_ssh):
        """MOTD fails, clush succeeds, 443 closed -> ip-addr hop."""
        mock_ssh.side_effect = [
            (1, "", "no such file"),
            (0, "172.16.3.4\n", ""),
            _PROBE_443_CLOSED,
            (0, SELAB_IP_ADDR_OUTPUT, ""),
        ]
        internal, mgmt = discover_vms_management_ip("192.168.2.2", "vastdata", "pw")
        assert internal == "172.16.3.4"
        assert mgmt == "10.143.11.202"
        assert mock_ssh.call_count == 4

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_both_strategies_fail(self, mock_ssh):
        mock_ssh.return_value = (1, "", "command not found")
        with pytest.raises(VMSDiscoveryError, match="motd and clush both failed"):
            discover_vms_management_ip("192.168.2.2", "vastdata", "pw")

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_both_strategies_empty_output(self, mock_ssh):
        mock_ssh.return_value = (0, "", "")
        with pytest.raises(VMSDiscoveryError, match="Could not discover VMS IP"):
            discover_vms_management_ip("192.168.2.2", "vastdata", "pw")

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_ssh_hop_fails(self, mock_ssh):
        mock_ssh.side_effect = [
            (0, "\u2502 VMS:    172.16.3.4                \u2502\n", ""),
            _PROBE_443_CLOSED,
            (1, "", "Connection refused"),
        ]
        with pytest.raises(VMSDiscoveryError, match="Failed to get management IP"):
            discover_vms_management_ip("192.168.2.2", "vastdata", "pw")

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_no_routable_ip_in_output(self, mock_ssh):
        # Inverted from pre-TP-1: payload now contains only loopback/CGNAT/docker
        # so parse_management_ip legitimately returns None.
        mock_ssh.side_effect = [
            (0, "\u2502 VMS:    172.16.3.4                \u2502\n", ""),
            _PROBE_443_CLOSED,
            (0, LOOPBACK_AND_CGNAT_ONLY, ""),
        ]
        with pytest.raises(VMSDiscoveryError, match="Could not parse management IP"):
            discover_vms_management_ip("192.168.2.2", "vastdata", "pw")

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_443_short_circuit_returns_internal_ip(self, mock_ssh):
        """When VMS internal IP itself answers on 443, skip the ip-addr hop."""
        mock_ssh.side_effect = [
            (0, "\u2502 VMS:    172.16.128.4              \u2502\n", ""),
            _PROBE_443_OPEN,
        ]
        internal, mgmt = discover_vms_management_ip("192.168.2.2", "vastdata", "pw")
        assert internal == "172.16.128.4"
        assert mgmt == "172.16.128.4"
        # Exactly 2 SSH calls: motd + 443 probe.  No ip-addr hop.
        assert mock_ssh.call_count == 2

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_443_short_circuit_falls_through_when_closed(self, mock_ssh):
        """443 closed on internal IP -> fall through to ip-addr hop."""
        mock_ssh.side_effect = [
            (0, "\u2502 VMS:    172.16.3.4                \u2502\n", ""),
            _PROBE_443_CLOSED,
            (0, MAMMOTH_IP_ADDR_OUTPUT, ""),
        ]
        internal, mgmt = discover_vms_management_ip("192.168.2.2", "vastdata", "pw")
        assert internal == "172.16.3.4"
        assert mgmt == "172.16.128.4"  # `bond0:m` alias wins via `:m` priority
        assert mock_ssh.call_count == 3


# ---------------------------------------------------------------------------
# VMSTunnel
# ---------------------------------------------------------------------------


class TestVMSTunnel:
    def test_init_defaults(self):
        t = VMSTunnel("192.168.2.2", "vastdata", "pw")
        assert t.tech_port_ip == "192.168.2.2"
        assert t.remote_port == 443
        assert t.local_port is None

    def test_local_bind_address_before_connect(self):
        t = VMSTunnel("192.168.2.2", "vastdata", "pw")
        with pytest.raises(RuntimeError, match="Tunnel not connected"):
            _ = t.local_bind_address

    @patch("utils.vms_tunnel.discover_vms_management_ip")
    def test_connect_and_close(self, mock_discover):
        mock_discover.return_value = ("172.16.3.4", "10.143.11.202")

        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True

        mock_client = MagicMock()
        mock_client.get_transport.return_value = mock_transport

        with patch("utils.vms_tunnel.paramiko") as mock_paramiko:
            mock_paramiko.SSHClient.return_value = mock_client
            mock_paramiko.AutoAddPolicy.return_value = MagicMock()

            tunnel = VMSTunnel("192.168.2.2", "vastdata", "pw")
            tunnel.connect()

            assert tunnel.vms_internal_ip == "172.16.3.4"
            assert tunnel.vms_management_ip == "10.143.11.202"
            assert tunnel.local_port is not None
            assert "127.0.0.1:" in tunnel.local_bind_address

            mock_client.connect.assert_called_once()
            mock_transport.set_keepalive.assert_called_once_with(15)

            tunnel.close()
            mock_client.close.assert_called()

    @patch("utils.vms_tunnel.discover_vms_management_ip")
    def test_context_manager(self, mock_discover):
        mock_discover.return_value = ("172.16.3.4", "10.143.11.202")

        mock_transport = MagicMock()
        mock_client = MagicMock()
        mock_client.get_transport.return_value = mock_transport

        with patch("utils.vms_tunnel.paramiko") as mock_paramiko:
            mock_paramiko.SSHClient.return_value = mock_client
            mock_paramiko.AutoAddPolicy.return_value = MagicMock()

            with VMSTunnel("192.168.2.2", "vastdata", "pw") as tunnel:
                tunnel.connect()
                assert tunnel.local_port is not None

            mock_client.close.assert_called()

    @patch("utils.vms_tunnel.discover_vms_management_ip")
    def test_discovery_failure_propagates(self, mock_discover):
        mock_discover.side_effect = VMSDiscoveryError("find-vms failed")
        tunnel = VMSTunnel("192.168.2.2", "vastdata", "pw")
        with pytest.raises(VMSDiscoveryError):
            tunnel.connect()

    @patch("utils.vms_tunnel.discover_vms_management_ip")
    def test_tunnel_forwards_data(self, mock_discover):
        """Verify that a connection to the local port gets forwarded."""
        mock_discover.return_value = ("172.16.3.4", "10.143.11.202")

        mock_channel = MagicMock()
        mock_channel.recv.return_value = b"HTTP/1.1 200 OK\r\n"

        mock_transport = MagicMock()
        mock_transport.is_active.return_value = True
        mock_transport.open_channel.return_value = mock_channel

        mock_client = MagicMock()
        mock_client.get_transport.return_value = mock_transport

        with patch("utils.vms_tunnel.paramiko") as mock_paramiko:
            mock_paramiko.SSHClient.return_value = mock_client
            mock_paramiko.AutoAddPolicy.return_value = MagicMock()

            tunnel = VMSTunnel("192.168.2.2", "vastdata", "pw")
            tunnel.connect()

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("127.0.0.1", tunnel.local_port))
                sock.sendall(b"GET /api/clusters/ HTTP/1.1\r\n\r\n")
                import time

                time.sleep(0.2)
            finally:
                sock.close()

            tunnel.close()

            mock_transport.open_channel.assert_called_once()
            call_args = mock_transport.open_channel.call_args
            assert call_args[0][0] == "direct-tcpip"
            assert call_args[0][1] == ("10.143.11.202", 443)


# ---------------------------------------------------------------------------
# API Handler tunnel_address integration
# ---------------------------------------------------------------------------


class TestApiHandlerTunnelAddress:
    def test_no_tunnel_uses_cluster_ip(self):
        handler = VastApiHandler("10.143.11.202", username="admin", password="pw")
        assert handler.cluster_ip == "10.143.11.202"
        assert handler._api_host == "10.143.11.202"

    def test_tunnel_address_overrides_api_host(self):
        handler = VastApiHandler(
            "10.143.11.202",
            username="admin",
            password="pw",
            tunnel_address="127.0.0.1:54321",
        )
        assert handler.cluster_ip == "10.143.11.202"
        assert handler._api_host == "127.0.0.1:54321"

    def test_set_api_version_uses_api_host(self):
        handler = VastApiHandler(
            "10.143.11.202",
            username="admin",
            password="pw",
            tunnel_address="127.0.0.1:54321",
        )
        handler._set_api_version("v7")
        assert handler.base_url == "https://127.0.0.1:54321/api/v7/"
        assert handler.cluster_ip == "10.143.11.202"

    def test_set_api_version_without_tunnel(self):
        handler = VastApiHandler("10.143.11.202", username="admin", password="pw")
        handler._set_api_version("v5")
        assert handler.base_url == "https://10.143.11.202/api/v5/"

    def test_factory_passes_tunnel_address(self):
        handler = create_vast_api_handler(
            "10.143.11.202",
            username="admin",
            password="pw",
            tunnel_address="127.0.0.1:12345",
        )
        assert handler._api_host == "127.0.0.1:12345"
        assert handler.cluster_ip == "10.143.11.202"

    def test_factory_no_tunnel(self):
        handler = create_vast_api_handler("10.143.11.202", username="admin", password="pw")
        assert handler._api_host == "10.143.11.202"
