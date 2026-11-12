"""Remote archive cleanup after a verified download (FR-11).

The log bundle (``/tmp/vast_log_bundle_<ts>.tar.gz`` on the CNode) and the Support Tools
archive (``/userdata/<host>-support_tool_logs_<ts>.tgz`` on the VMS host) were left on the
cluster after download.  Each workflow now removes its own archive, by exact path, once the
local copy is verified, and keeps it when verification fails.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry  # noqa: E402

LOG_ARCHIVE = "/tmp/vast_log_bundle_20261111_204000.tar.gz"
SUPPORT_ARCHIVE_NAME = "acme-cnode1-support_tool_logs_20261111_204000.tgz"
SUPPORT_ARCHIVE = f"/userdata/{SUPPORT_ARCHIVE_NAME}"
ARCHIVE_BYTES = b"fake archive content"
CREDS = {"cluster_ip": "192.0.2.10", "node_user": "vastdata", "node_password": "pw"}


def _exec_result(success=True, stdout="", stderr=""):
    return MagicMock(success=success, stdout=stdout, stderr=stderr, returncode=0 if success else 1)


def _log_bundle(tmp_path, runner, archive_path=LOG_ARCHIVE):
    wf = WorkflowRegistry.get("log_bundle")
    wf.set_credentials(dict(CREDS))
    wf.set_output_callback(MagicMock())
    wf._script_runner = runner
    local = tmp_path / "vast_log_bundle.tar.gz"
    local.write_bytes(ARCHIVE_BYTES)
    wf._step_data = {"archive_path": archive_path, "local_path": str(local), "archive_size": len(ARCHIVE_BYTES)}
    return wf


def _rm_commands(runner):
    return [c.args[3] for c in runner.execute_remote.call_args_list if "rm -f" in c.args[3]]


def _tar_ok():
    return MagicMock(returncode=0, stdout="var/log/messages\nvast/log/a.log\n", stderr="")


class TestLogBundleRemoteCleanup:
    def test_verified_download_removes_exact_remote_archive(self, tmp_path):
        runner = MagicMock()
        runner.execute_remote.return_value = _exec_result()
        wf = _log_bundle(tmp_path, runner)
        with patch("subprocess.run", return_value=_tar_ok()):
            result = wf._step_verify_contents()
        assert result["success"] is True
        assert _rm_commands(runner) == [f"sudo rm -f -- {LOG_ARCHIVE}"]
        assert result["remote_cleanup"] == "removed"

    def test_failed_verification_keeps_archive_and_says_where(self, tmp_path):
        runner = MagicMock()
        wf = _log_bundle(tmp_path, runner)
        with patch("subprocess.run", return_value=MagicMock(returncode=2, stdout="", stderr="unexpected EOF")):
            result = wf._step_verify_contents()
        assert result["success"] is False
        assert _rm_commands(runner) == []
        assert f"192.0.2.10:{LOG_ARCHIVE}" in result["message"]

    def test_missing_local_archive_keeps_remote_archive(self, tmp_path):
        runner = MagicMock()
        wf = _log_bundle(tmp_path, runner)
        Path(wf._step_data["local_path"]).unlink()
        result = wf._step_verify_contents()
        assert result["success"] is False
        assert _rm_commands(runner) == []
        assert LOG_ARCHIVE in result["message"]

    def test_failed_download_keeps_archive_and_says_where(self, tmp_path):
        runner = MagicMock()
        runner.get_local_dir.return_value = tmp_path
        runner.download_from_remote.return_value = MagicMock(success=False, error="connection reset")
        wf = _log_bundle(tmp_path, runner)
        wf._step_data["archive_name"] = Path(LOG_ARCHIVE).name
        result = wf._step_download_to_laptop()
        assert result["success"] is False
        assert _rm_commands(runner) == []
        assert f"192.0.2.10:{LOG_ARCHIVE}" in result["message"]

    def test_stale_local_copy_from_earlier_run_does_not_trigger_cleanup(self, tmp_path):
        runner = MagicMock()
        runner.get_local_dir.return_value = tmp_path
        runner.download_from_remote.return_value = MagicMock(success=False, error="connection reset")
        runner.execute_remote.return_value = _exec_result()
        wf = _log_bundle(tmp_path, runner)
        wf._step_data["archive_name"] = Path(LOG_ARCHIVE).name
        assert wf._step_download_to_laptop()["success"] is False
        with patch("subprocess.run", return_value=_tar_ok()):
            result = wf._step_verify_contents()
        assert result["success"] is False
        assert _rm_commands(runner) == []

    def test_new_archive_discards_previous_download_record(self, tmp_path):
        runner = MagicMock()
        runner.execute_remote.return_value = _exec_result(stdout="1.0G")
        wf = _log_bundle(tmp_path, runner)
        wf._step_data["collection_confirmed"] = True
        wf._step_create_archive()
        assert "local_path" not in wf._step_data

    def test_unrecognised_path_is_refused(self, tmp_path):
        runner = MagicMock()
        runner.execute_remote.return_value = _exec_result()
        wf = _log_bundle(tmp_path, runner, archive_path="/tmp/vast_log_bundle_*.tar.gz")
        with patch("subprocess.run", return_value=_tar_ok()):
            result = wf._step_verify_contents()
        assert result["success"] is True
        assert result["remote_cleanup"] == "skipped"
        assert _rm_commands(runner) == []
        warnings = [c.args[1] for c in wf._output_callback.call_args_list if c.args[0] == "warn"]
        assert any("refusing" in w for w in warnings)

    def test_cleanup_failure_warns_but_step_succeeds(self, tmp_path):
        runner = MagicMock()
        runner.execute_remote.return_value = _exec_result(False, stderr="rm: Operation not permitted")
        wf = _log_bundle(tmp_path, runner)
        with patch("subprocess.run", return_value=_tar_ok()):
            result = wf._step_verify_contents()
        assert result["success"] is True
        assert result["remote_cleanup"] == "failed"
        warnings = [c.args[1] for c in wf._output_callback.call_args_list if c.args[0] == "warn"]
        assert any(LOG_ARCHIVE in w and "Operation not permitted" in w for w in warnings)


class _SupportSsh:
    """Stands in for ``run_ssh_command``: answers ``stat`` and ``rm`` and records commands."""

    def __init__(self, remote_size=len(ARCHIVE_BYTES), rm_rc=0, stat_rc=0):
        self.remote_size = remote_size
        self.rm_rc = rm_rc
        self.stat_rc = stat_rc
        self.commands = []

    def __call__(self, host, user, password, cmd, timeout=30, **kwargs):
        self.commands.append(cmd)
        if cmd.startswith("stat "):
            return (self.stat_rc, f"{self.remote_size}\n" if self.stat_rc == 0 else "", "")
        if "rm -f" in cmd:
            return (self.rm_rc, "", "rm: cannot remove: Permission denied" if self.rm_rc else "")
        return (0, "", "")

    @property
    def rm_commands(self):
        return [c for c in self.commands if "rm -f" in c]


def _run_support_download(tmp_path, ssh, archive_path=SUPPORT_ARCHIVE, write_local=True, scp_error=None):
    wf = WorkflowRegistry.get("support_tool")
    wf.set_credentials(dict(CREDS))
    emitted = []
    wf.set_output_callback(lambda level, msg, details=None: emitted.append((level, msg)))
    runner = MagicMock()
    runner.get_local_dir.return_value = tmp_path
    wf._script_runner = runner
    wf._step_data = {"archive_name": SUPPORT_ARCHIVE_NAME, "archive_path": archive_path}
    if write_local:
        (tmp_path / SUPPORT_ARCHIVE_NAME).write_bytes(ARCHIVE_BYTES)
    scp_module = MagicMock()
    if scp_error is not None:
        scp_module.SCPClient.return_value.__enter__.return_value.get.side_effect = scp_error
    with (
        patch.dict("sys.modules", {"scp": scp_module}),
        patch("paramiko.SSHClient"),
        patch("workflows.support_tool_workflow.run_ssh_command", side_effect=ssh),
    ):
        result = wf._step_download_results()
    return result, emitted


class TestSupportToolRemoteCleanup:
    def test_verified_download_removes_exact_remote_archive(self, tmp_path):
        ssh = _SupportSsh()
        result, _ = _run_support_download(tmp_path, ssh)
        assert result["success"] is True
        assert ssh.rm_commands == [f"sudo rm -f -- {SUPPORT_ARCHIVE}"]
        assert result["remote_cleanup"] == "removed"

    def test_size_mismatch_fails_and_keeps_archive(self, tmp_path):
        ssh = _SupportSsh(remote_size=len(ARCHIVE_BYTES) + 4096)
        result, _ = _run_support_download(tmp_path, ssh)
        assert result["success"] is False
        assert ssh.rm_commands == []
        assert f"192.0.2.10:{SUPPORT_ARCHIVE}" in result["message"]

    def test_scp_failure_keeps_archive_and_says_where(self, tmp_path):
        ssh = _SupportSsh()
        result, _ = _run_support_download(tmp_path, ssh, write_local=False, scp_error=OSError("connection reset"))
        assert result["success"] is False
        assert ssh.rm_commands == []
        assert f"192.0.2.10:{SUPPORT_ARCHIVE}" in result["message"]

    def test_unknown_remote_size_skips_cleanup(self, tmp_path):
        ssh = _SupportSsh(stat_rc=1)
        result, emitted = _run_support_download(tmp_path, ssh)
        assert result["success"] is True
        assert result["remote_cleanup"] == "skipped"
        assert ssh.rm_commands == []
        assert any(level == "warn" and SUPPORT_ARCHIVE in msg for level, msg in emitted)

    def test_unrecognised_path_is_refused(self, tmp_path):
        ssh = _SupportSsh()
        result, emitted = _run_support_download(tmp_path, ssh, archive_path="/userdata/*.tgz")
        assert result["success"] is True
        assert result["remote_cleanup"] == "skipped"
        assert ssh.rm_commands == []
        assert any(level == "warn" and "refusing" in msg for level, msg in emitted)

    def test_cleanup_failure_warns_but_step_succeeds(self, tmp_path):
        ssh = _SupportSsh(rm_rc=1)
        result, emitted = _run_support_download(tmp_path, ssh)
        assert result["success"] is True
        assert result["remote_cleanup"] == "failed"
        assert ssh.rm_commands == [f"sudo rm -f -- {SUPPORT_ARCHIVE}"]
        assert any(level == "warn" and SUPPORT_ARCHIVE in msg for level, msg in emitted)

    def test_cleanup_targets_vms_host_through_jump_in_tech_port_mode(self, tmp_path):
        calls = []
        ssh = _SupportSsh()

        def recording(host, user, password, cmd, timeout=30, **kwargs):
            calls.append((host, cmd, kwargs))
            return ssh(host, user, password, cmd, timeout=timeout, **kwargs)

        wf = WorkflowRegistry.get("support_tool")
        wf.set_credentials({**CREDS, "vms_internal_ip": "192.0.2.20"})
        wf.set_output_callback(MagicMock())
        runner = MagicMock()
        runner.get_local_dir.return_value = tmp_path
        wf._script_runner = runner
        wf._step_data = {"archive_name": SUPPORT_ARCHIVE_NAME, "archive_path": SUPPORT_ARCHIVE}
        (tmp_path / SUPPORT_ARCHIVE_NAME).write_bytes(ARCHIVE_BYTES)
        with (
            patch.dict("sys.modules", {"scp": MagicMock()}),
            patch("paramiko.SSHClient"),
            patch("workflows.support_tool_workflow.run_ssh_command", side_effect=recording),
        ):
            result = wf._step_download_results()
        assert result["remote_cleanup"] == "removed"
        rm_calls = [c for c in calls if "rm -f" in c[1]]
        assert rm_calls[0][0] == "192.0.2.20"
        assert rm_calls[0][2]["jump_host"] == "192.0.2.10"
