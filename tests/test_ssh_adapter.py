"""
Tests for the cross-platform SSH adapter (src/utils/ssh_adapter.py).

All tests mock the underlying transports (subprocess, pexpect, paramiko)
so no real SSH connections are made.
"""

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.ssh_adapter import (
    run_ssh_command,
    run_interactive_ssh,
    _subprocess_ssh,
    _paramiko_exec,
    _pexpect_interactive,
)


class TestSubprocessSSH(unittest.TestCase):
    """Tests for the macOS/Linux subprocess SSH path.

    Must patch subprocess.run and shutil.which at the use site (utils.ssh_adapter).
    When which('sshpass') returns a path, the code uses subprocess.run; when None,
    it falls back to _paramiko_exec. So subprocess-path tests need which to return
    a path so the subprocess branch is exercised.
    """

    @patch("utils.ssh_adapter.subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/sshpass")
    def test_successful_command(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="ok\n", stderr="")
        rc, out, err = _subprocess_ssh("host", "user", "pass", "ls", 10, "/dev/null")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "ok\n")
        mock_run.assert_called_once()

    @patch("utils.ssh_adapter.subprocess.run")
    @patch("shutil.which", return_value="/usr/bin/sshpass")
    def test_uses_sshpass_when_available(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        _subprocess_ssh("host", "user", "pass", "ls", 10, "/dev/null")
        cmd = mock_run.call_args[0][0]
        self.assertEqual(cmd[0], "sshpass")

    @patch("utils.ssh_adapter.subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ssh", timeout=5))
    @patch("shutil.which", return_value="/usr/bin/sshpass")
    def test_timeout_returns_error(self, _which, _run):
        rc, out, err = _subprocess_ssh("host", "user", "pass", "ls", 5, "/dev/null")
        self.assertEqual(rc, 1)
        self.assertIn("timed out", err)

    @patch("utils.ssh_adapter.subprocess.run", side_effect=OSError("no such file"))
    @patch("shutil.which", return_value="/usr/bin/sshpass")
    def test_os_error_returns_error(self, _which, _run):
        rc, out, err = _subprocess_ssh("host", "user", "pass", "ls", 5, "/dev/null")
        self.assertEqual(rc, 1)
        self.assertIn("no such file", err)


class TestParamikoExec(unittest.TestCase):
    """Tests for the paramiko SSH path."""

    def _make_mock_paramiko(self):
        mock_paramiko = MagicMock()
        mock_paramiko.AuthenticationException = type("AuthenticationException", (Exception,), {})
        mock_paramiko.AutoAddPolicy.return_value = "policy"
        return mock_paramiko

    @patch.dict("sys.modules", {})
    def test_successful_command(self):
        mock_paramiko = self._make_mock_paramiko()
        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client

        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"output data"
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec("host", "user", "pass", "ls", 10)

        self.assertEqual(rc, 0)
        self.assertEqual(out, "output data")
        mock_client.connect.assert_called_once()
        mock_client.close.assert_called_once()

    @patch.dict("sys.modules", {})
    def test_auth_failure(self):
        mock_paramiko = self._make_mock_paramiko()
        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client
        mock_client.connect.side_effect = mock_paramiko.AuthenticationException("denied")

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec("host", "user", "pass", "ls", 10)

        self.assertEqual(rc, 1)
        self.assertIn("Authentication failed", err)

    @patch.dict("sys.modules", {})
    def test_connection_error(self):
        mock_paramiko = self._make_mock_paramiko()
        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client
        mock_client.connect.side_effect = OSError("Connection refused")

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._paramiko_exec("host", "user", "pass", "ls", 10)

        self.assertEqual(rc, 1)
        self.assertIn("Connection refused", err)

    @patch.dict("sys.modules", {})
    def test_client_always_closed(self):
        mock_paramiko = self._make_mock_paramiko()
        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client
        mock_client.connect.side_effect = RuntimeError("boom")

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            mod._paramiko_exec("host", "user", "pass", "ls", 10)

        mock_client.close.assert_called_once()


class TestPexpectInteractive(unittest.TestCase):
    """Tests for the pexpect interactive SSH path."""

    def test_successful_session(self):
        mock_pexpect = MagicMock()
        mock_child = MagicMock()
        mock_pexpect.spawn.return_value = mock_child
        mock_pexpect.TIMEOUT = "TIMEOUT"
        mock_pexpect.EOF = "EOF"
        mock_child.expect.side_effect = [0, 0, 0, 0]
        mock_child.before = "switch output data"

        with patch.dict("sys.modules", {"pexpect": mock_pexpect}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._pexpect_interactive("host", "user", "pass", "show ver", 10, "/dev/null")

        self.assertEqual(rc, 0)
        self.assertIn("switch output data", out)
        mock_child.sendline.assert_any_call("pass")
        mock_child.sendline.assert_any_call("show ver")

    def test_no_password_prompt(self):
        mock_pexpect = MagicMock()
        mock_child = MagicMock()
        mock_pexpect.spawn.return_value = mock_child
        mock_pexpect.TIMEOUT = "TIMEOUT"
        mock_pexpect.EOF = "EOF"
        mock_child.expect.return_value = 1
        mock_child.before = "some banner"

        with patch.dict("sys.modules", {"pexpect": mock_pexpect}):
            from importlib import reload
            import utils.ssh_adapter as mod

            reload(mod)
            rc, out, err = mod._pexpect_interactive("host", "user", "pass", "cmd", 10, "/dev/null")

        self.assertEqual(rc, 1)
        self.assertIn("No password prompt", err)


class TestPexpectFallback(unittest.TestCase):
    """When pexpect is not installed, falls back to paramiko."""

    def test_falls_back_to_paramiko_when_pexpect_missing(self):
        mock_paramiko = MagicMock()
        mock_paramiko.AuthenticationException = type("AuthenticationException", (Exception,), {})
        mock_paramiko.AutoAddPolicy.return_value = "policy"

        mock_client = MagicMock()
        mock_paramiko.SSHClient.return_value = mock_client
        mock_stdout = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"fallback output"
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        import builtins

        real_import = builtins.__import__

        def selective_import(name, *args, **kwargs):
            if name == "pexpect":
                raise ImportError("no pexpect")
            return real_import(name, *args, **kwargs)

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            with patch("builtins.__import__", side_effect=selective_import):
                from importlib import reload
                import utils.ssh_adapter as mod

                reload(mod)
                rc, out, err = mod._pexpect_interactive("host", "user", "pass", "cmd", 10, "/dev/null")

        self.assertEqual(rc, 0)
        self.assertEqual(out, "fallback output")


class TestPublicAPIRouting(unittest.TestCase):
    """Tests for run_ssh_command / run_interactive_ssh platform routing."""

    @patch("utils.ssh_adapter.IS_WINDOWS", False)
    @patch("utils.ssh_adapter._subprocess_ssh", return_value=(0, "unix", ""))
    def test_run_ssh_command_unix(self, mock_ssh):
        rc, out, err = run_ssh_command("h", "u", "p", "cmd")
        self.assertEqual(out, "unix")
        mock_ssh.assert_called_once()

    @patch("utils.ssh_adapter.IS_WINDOWS", True)
    @patch("utils.ssh_adapter._paramiko_exec", return_value=(0, "win", ""))
    def test_run_ssh_command_windows(self, mock_ssh):
        rc, out, err = run_ssh_command("h", "u", "p", "cmd")
        self.assertEqual(out, "win")
        mock_ssh.assert_called_once()

    @patch("utils.ssh_adapter.IS_WINDOWS", False)
    @patch("utils.ssh_adapter._pexpect_interactive", return_value=(0, "interactive", ""))
    def test_run_interactive_ssh_unix(self, mock_ssh):
        rc, out, err = run_interactive_ssh("h", "u", "p", "cmd")
        self.assertEqual(out, "interactive")

    @patch("utils.ssh_adapter.IS_WINDOWS", True)
    @patch("utils.ssh_adapter._paramiko_exec", return_value=(0, "win-int", ""))
    def test_run_interactive_ssh_windows(self, mock_ssh):
        rc, out, err = run_interactive_ssh("h", "u", "p", "cmd")
        self.assertEqual(out, "win-int")


if __name__ == "__main__":
    unittest.main()
