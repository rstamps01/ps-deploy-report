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

NO_TEN_NETWORK = """\
    inet 192.168.1.100/24 scope global eth0
    inet 172.16.3.4/16 scope global eth1
"""


class TestParseManagementIp:
    def test_selab_primary(self):
        assert parse_management_ip(SELAB_IP_ADDR_OUTPUT) == "10.143.11.202"

    def test_single_ip(self):
        assert parse_management_ip(SINGLE_IP_OUTPUT) == "10.1.2.3"

    def test_secondary_only_falls_back(self):
        assert parse_management_ip(SECONDARY_ONLY_OUTPUT) == "10.1.2.3"

    def test_no_ten_network(self):
        assert parse_management_ip(NO_TEN_NETWORK) is None

    def test_empty_output(self):
        assert parse_management_ip("") is None

    def test_none_output(self):
        assert parse_management_ip(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# discover_vms_management_ip
# ---------------------------------------------------------------------------


class TestDiscoverVmsManagementIp:
    @patch("utils.vms_tunnel.run_ssh_command")
    def test_success_via_motd(self, mock_ssh):
        """MOTD strategy succeeds on first call; hop is call #2."""
        mock_ssh.side_effect = [
            (0, "│ VMS:    172.16.3.4                │\n", ""),
            (0, SELAB_IP_ADDR_OUTPUT, ""),
        ]
        internal, mgmt = discover_vms_management_ip("192.168.2.2", "vastdata", "pw")
        assert internal == "172.16.3.4"
        assert mgmt == "10.143.11.202"
        assert mock_ssh.call_count == 2

        first_call = mock_ssh.call_args_list[0]
        assert first_call[0][0] == "192.168.2.2"
        assert "motd" in first_call[0][3]

        second_call = mock_ssh.call_args_list[1]
        assert second_call[0][0] == "172.16.3.4"
        assert second_call[1]["jump_host"] == "192.168.2.2"

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_success_via_clush_fallback(self, mock_ssh):
        """MOTD fails, clush fallback succeeds."""
        mock_ssh.side_effect = [
            (1, "", "no such file"),
            (0, "172.16.3.4\n", ""),
            (0, SELAB_IP_ADDR_OUTPUT, ""),
        ]
        internal, mgmt = discover_vms_management_ip("192.168.2.2", "vastdata", "pw")
        assert internal == "172.16.3.4"
        assert mgmt == "10.143.11.202"
        assert mock_ssh.call_count == 3

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
            (0, "│ VMS:    172.16.3.4                │\n", ""),
            (1, "", "Connection refused"),
        ]
        with pytest.raises(VMSDiscoveryError, match="Failed to get management IP"):
            discover_vms_management_ip("192.168.2.2", "vastdata", "pw")

    @patch("utils.vms_tunnel.run_ssh_command")
    def test_no_management_ip_found(self, mock_ssh):
        mock_ssh.side_effect = [
            (0, "│ VMS:    172.16.3.4                │\n", ""),
            (0, "    inet 192.168.1.1/24 scope global eth0\n", ""),
        ]
        with pytest.raises(VMSDiscoveryError, match="Could not parse management IP"):
            discover_vms_management_ip("192.168.2.2", "vastdata", "pw")


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
