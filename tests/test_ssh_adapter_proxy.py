"""
Tests for jump-host (proxy hop) support in the SSH adapter.

All tests mock paramiko so no real SSH connections are made.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, call

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _make_mock_paramiko():
    """Build a mock paramiko module with real exception classes."""
    mock_paramiko = MagicMock()
    mock_paramiko.AuthenticationException = type(
        "AuthenticationException",
        (Exception,),
        {},
    )
    mock_paramiko.SSHException = type("SSHException", (Exception,), {})
    mock_paramiko.AutoAddPolicy.return_value = "policy"
    return mock_paramiko


def _setup_successful_exec(mock_client):
    """Wire up a mock SSHClient so exec_command returns successfully."""
    mock_stdout = MagicMock()
    mock_stdout.channel.recv_exit_status.return_value = 0
    mock_stdout.read.return_value = b"switch-01"
    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""
    mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)


class TestParamikoExecWithJumpHost(unittest.TestCase):
    """Verify the two-stage paramiko connection through a jump host."""

    def test_paramiko_exec_with_jump_host_opens_tunnel(self):
        mock_paramiko = _make_mock_paramiko()

        mock_jump_client = MagicMock()
        mock_target_client = MagicMock()
        mock_channel = MagicMock()

        mock_jump_transport = MagicMock()
        mock_jump_client.get_transport.return_value = mock_jump_transport
        mock_jump_transport.open_channel.return_value = mock_channel

        _setup_successful_exec(mock_target_client)

        mock_paramiko.SSHClient.side_effect = [mock_target_client, mock_jump_client]

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec(
                "172.27.51.4",
                "admin",
                "switchpass",
                "hostname",
                30,
                jump_host="192.168.2.2",
                jump_user="vastdata",
                jump_password="cnodepass",
            )

        self.assertEqual(rc, 0)
        self.assertEqual(out, "switch-01")

        mock_jump_client.connect.assert_called_once()
        jc_kwargs = mock_jump_client.connect.call_args
        self.assertEqual(jc_kwargs[0][0], "192.168.2.2")
        self.assertEqual(jc_kwargs[1]["username"], "vastdata")
        self.assertEqual(jc_kwargs[1]["password"], "cnodepass")

        mock_jump_transport.open_channel.assert_called_once_with(
            "direct-tcpip",
            ("172.27.51.4", 22),
            ("127.0.0.1", 0),
        )

        tc_kwargs = mock_target_client.connect.call_args
        self.assertEqual(tc_kwargs[0][0], "172.27.51.4")
        self.assertEqual(tc_kwargs[1]["username"], "admin")
        self.assertEqual(tc_kwargs[1]["sock"], mock_channel)

    def test_paramiko_exec_without_jump_host_is_direct(self):
        mock_paramiko = _make_mock_paramiko()
        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client
        _setup_successful_exec(mock_client)

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec(
                "10.0.0.1",
                "user",
                "pass",
                "ls",
                10,
            )

        self.assertEqual(rc, 0)
        self.assertEqual(out, "switch-01")

        mock_paramiko.SSHClient.assert_called_once()
        tc_kwargs = mock_client.connect.call_args
        self.assertEqual(tc_kwargs[0][0], "10.0.0.1")
        self.assertIsNone(tc_kwargs[1].get("sock"))

    def test_jump_host_auth_failure_returns_error(self):
        mock_paramiko = _make_mock_paramiko()

        mock_jump_client = MagicMock()
        mock_target_client = MagicMock()
        mock_jump_client.connect.side_effect = mock_paramiko.AuthenticationException(
            "bad creds",
        )

        mock_paramiko.SSHClient.side_effect = [mock_target_client, mock_jump_client]

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec(
                "172.27.51.4",
                "admin",
                "switchpass",
                "hostname",
                30,
                jump_host="192.168.2.2",
                jump_user="vastdata",
                jump_password="wrong",
            )

        self.assertEqual(rc, 1)
        self.assertIn("Jump host authentication failed", err)
        self.assertIn("vastdata@192.168.2.2", err)

    def test_partial_jump_params_returns_error(self):
        mock_paramiko = _make_mock_paramiko()
        mock_paramiko.SSHClient.return_value = MagicMock()

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec(
                "172.27.51.4",
                "admin",
                "switchpass",
                "hostname",
                30,
                jump_host="192.168.2.2",
                jump_user="vastdata",
            )

        self.assertEqual(rc, 1)
        self.assertIn("Incomplete jump host config", err)

    def test_jump_host_cleanup_closes_both_clients(self):
        mock_paramiko = _make_mock_paramiko()

        mock_jump_client = MagicMock()
        mock_target_client = MagicMock()
        mock_channel = MagicMock()

        mock_jump_transport = MagicMock()
        mock_jump_client.get_transport.return_value = mock_jump_transport
        mock_jump_transport.open_channel.return_value = mock_channel

        mock_target_client.connect.side_effect = RuntimeError("target unreachable")

        mock_paramiko.SSHClient.side_effect = [mock_target_client, mock_jump_client]

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec(
                "172.27.51.4",
                "admin",
                "switchpass",
                "hostname",
                30,
                jump_host="192.168.2.2",
                jump_user="vastdata",
                jump_password="cnodepass",
            )

        self.assertEqual(rc, 1)
        mock_target_client.close.assert_called_once()
        mock_jump_client.close.assert_called_once()


class TestRunInteractiveSSHWithJumpHost(unittest.TestCase):
    """Verify run_interactive_ssh routes through paramiko when jump_host is provided."""

    @patch("utils.ssh_adapter._paramiko_exec", return_value=(0, "proxied", ""))
    def test_run_interactive_ssh_with_jump_uses_paramiko(self, mock_exec):
        from utils.ssh_adapter import run_interactive_ssh

        rc, out, err = run_interactive_ssh(
            "172.27.51.4",
            "admin",
            "switchpass",
            "show version",
            jump_host="192.168.2.2",
            jump_user="vastdata",
            jump_password="cnodepass",
        )

        self.assertEqual(rc, 0)
        self.assertEqual(out, "proxied")
        mock_exec.assert_called_once_with(
            "172.27.51.4",
            "admin",
            "switchpass",
            "show version",
            30,
            force_tty=True,
            jump_host="192.168.2.2",
            jump_user="vastdata",
            jump_password="cnodepass",
        )


if __name__ == "__main__":
    unittest.main()
