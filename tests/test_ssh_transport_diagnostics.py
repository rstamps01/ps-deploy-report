"""SSH transport diagnostics from the SE Lab C/DBox validation run (v1.6.2).

The laptop SSH session dropped mid-vperfsanity write and again during log-bundle
tar with ``Can't assign requested address`` / ``Broken pipe`` (rc=255). The
workflows reported that as a generic test/archive failure. Cross-tenant cleanup
also hung well past its 30 s timeout when the SSH child was not killed as a
process group.
"""

import signal
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.ssh_adapter import (  # noqa: E402
    _subprocess_ssh,
    is_ssh_transport_failure,
    ssh_transport_failure_message,
)
from workflows.network_config_workflow import NetworkConfigWorkflow  # noqa: E402
from workflows.vperfsanity_workflow import VperfsanityWorkflow  # noqa: E402
from workflows import WorkflowRegistry  # noqa: E402


class TestSshTransportFailureDetection:
    def test_cant_assign_requested_address(self):
        assert is_ssh_transport_failure(255, "", "Read from remote host 10.0.0.1: Can't assign requested address\n")

    def test_broken_pipe(self):
        assert is_ssh_transport_failure(255, "", "client_loop: send disconnect: Broken pipe\n")

    def test_connection_reset(self):
        assert is_ssh_transport_failure(255, "", "Connection reset by peer\n")

    def test_elbencho_rc_is_not_transport(self):
        assert not is_ssh_transport_failure(1, "elbencho: WRITE failed\n", "")

    def test_message_names_the_symptom(self):
        msg = ssh_transport_failure_message(
            255, "", "Read from remote host X: Can't assign requested address\nBroken pipe\n"
        )
        assert "SSH connection lost" in msg
        assert "Can't assign requested address" in msg or "Broken pipe" in msg


class TestVperfsanityReportsConnectionLost:
    @patch("workflows.vperfsanity_workflow.run_ssh_command")
    def test_step4_transport_drop_is_not_tests_failed(self, mock_ssh):
        wf = VperfsanityWorkflow()
        wf.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pw"})
        wf.set_output_callback(MagicMock())
        wf._step_data = {"vip_pool": "main", "vperf_dir": "/tmp/vperfsanity"}
        mock_ssh.return_value = (
            255,
            "Phase: WRITE  47%\n",
            "Read from remote host 10.0.0.1: Can't assign requested address\n"
            "client_loop: send disconnect: Broken pipe\n",
        )
        result = wf._step_run_tests()
        assert result["success"] is False
        assert "SSH connection lost" in result["message"]
        assert "Tests failed (rc=255)" not in result["message"]


class TestNetworkExtractionLocalCfgError:
    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_ssh_failure_names_transport_not_missing_config(self, mock_ssh):
        wf = NetworkConfigWorkflow()
        wf.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pw"})
        callback = MagicMock()
        wf.set_output_callback(callback)
        mock_ssh.side_effect = [
            (0, "cnode-1\n", ""),  # hostname
            (0, 'NAME="Rocky"\n', ""),  # os-release
            (
                255,
                "",
                "Read from remote host 10.0.0.1: Can't assign requested address\n"
                "client_loop: send disconnect: Broken pipe\n",
            ),
        ]
        result = wf.run_step(1)
        assert result["success"] is True  # still falls back to gateway
        warns = [c.args[1] for c in callback.call_args_list if c.args and c.args[0] == "warn"]
        assert any("SSH" in w and "local.cfg" in w for w in warns)
        assert not any(w == "ClusterShell config not found, using connected node only" for w in warns)


class TestLogBundleDiscoverIncludesVastLog:
    def test_step1_adds_recent_vast_log_bytes_to_total(self):
        wf = WorkflowRegistry.get("log_bundle")
        wf.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pw"})
        runner = MagicMock()
        runner.check_prerequisites.return_value = (True, "OK")

        def _exec(host, user, password, cmd, timeout=60):
            if "du -sh" in cmd and "/var/log/messages" in cmd:
                return MagicMock(success=True, stdout="1.3M\t/var/log/messages", stderr="")
            if "du -sh" in cmd:
                return MagicMock(success=True, stdout=f"0\t{cmd.split()[-1]}", stderr="")
            if "-printf" in cmd and "/vast/log" in cmd:
                return MagicMock(success=True, stdout=str(800 * 1048576), stderr="")
            return MagicMock(success=True, stdout="0", stderr="")

        runner.execute_remote.side_effect = _exec
        wf._script_runner = runner
        result = wf._step_discover_sizes()
        assert result["success"] is True
        assert wf._step_data["total_size_mb"] > 700
        assert "/vast/log" in result["details"]
        assert "recent" in result["details"].lower() or "24" in result["details"]


class TestSubprocessTimeoutKillsProcessGroup:
    @patch("shutil.which", return_value="/usr/bin/sshpass")
    @patch("utils.ssh_adapter.os.killpg")
    @patch("utils.ssh_adapter.subprocess.Popen")
    def test_timeout_kills_process_group(self, mock_popen, mock_killpg, _which):
        proc = MagicMock()
        proc.pid = 4242
        proc.communicate.side_effect = [
            subprocess.TimeoutExpired(cmd="ssh", timeout=2),
            (b"partial-out", b"partial-err"),
        ]
        mock_popen.return_value = proc

        rc, out, err = _subprocess_ssh("host", "user", "pass", "sleep 999", 2, "/dev/null")

        mock_popen.assert_called_once()
        assert mock_popen.call_args.kwargs.get("start_new_session") is True
        mock_killpg.assert_called_once_with(4242, signal.SIGKILL)
        assert rc == 1
        assert "timed out after 2s" in err
        assert "partial-out" in out
