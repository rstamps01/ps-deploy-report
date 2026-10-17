"""SSH login rejections on an EBox QA cluster (v1.6.2 field run).

Two of ~40 password logins to the same VMS IP were rejected with
``Permission denied, please try again`` / ``Too many authentication failures``
(rc=255) while the calls around them succeeded. The client offered four keys
before the password, spending the server's MaxAuthTries. vperfsanity reported
"Tests failed (rc=255)" although the tests never started, and the Support Tools
error was mostly SSH banner noise.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.ssh_adapter import (  # noqa: E402
    _subprocess_ssh,
    is_ssh_auth_failure,
    ssh_auth_failure_message,
)
from workflows.vperfsanity_workflow import VperfsanityWorkflow  # noqa: E402

NOISE = (
    "Warning: Permanently added '10.141.200.238' (ECDSA) to the list of known hosts.\r\n"
    "** WARNING: connection is not using a post-quantum key exchange algorithm.\r\n"
    '** This session may be vulnerable to "store now, decrypt later" attacks.\r\n'
    "** The server may need to be upgraded. See https://openssh.com/pq.html\r\n"
)
REJECTED = (
    NOISE + "Permission denied, please try again.\r\n"
    "Received disconnect from 10.141.200.238 port 22:2: Too many authentication failures\r\n"
    "Disconnected from 10.141.200.238 port 22\r\n"
)


def _proc(rc, out=b"", err=b""):
    proc = MagicMock()
    proc.pid = 1
    proc.returncode = rc
    proc.communicate.return_value = (out, err)
    return proc


class TestAuthFailureDetection:
    def test_too_many_authentication_failures(self):
        assert is_ssh_auth_failure(255, "", REJECTED)

    def test_sshpass_wrong_password_rc(self):
        assert is_ssh_auth_failure(5, "", "")

    def test_remote_permission_denied_is_not_login_failure(self):
        assert not is_ssh_auth_failure(1, "", "chmod: changing permissions: Permission denied\n")

    def test_message_names_host_and_symptom(self):
        msg = ssh_auth_failure_message(255, "", REJECTED, host="10.141.200.238")
        assert "SSH login to 10.141.200.238 was rejected" in msg
        assert "Too many authentication failures" in msg


@patch("shutil.which", return_value="/usr/bin/sshpass")
@patch("utils.ssh_adapter.time.sleep")
@patch("utils.ssh_adapter.subprocess.Popen")
class TestSubprocessSshPasswordLogin:
    def test_password_is_tried_before_keys(self, mock_popen, _sleep, _which):
        mock_popen.return_value = _proc(0, b"ok")
        _subprocess_ssh("h", "u", "pw", "true", 10, "/dev/null")
        cmd = mock_popen.call_args.args[0]
        assert "PreferredAuthentications=keyboard-interactive,password,publickey" in cmd

    def test_rejected_login_is_retried_once(self, mock_popen, mock_sleep, _which):
        mock_popen.side_effect = [_proc(255, b"", REJECTED.encode()), _proc(0, b"done")]
        rc, out, _ = _subprocess_ssh("h", "u", "pw", "true", 10, "/dev/null")
        assert (rc, out) == (0, "done")
        assert mock_popen.call_count == 2
        mock_sleep.assert_called_once()

    def test_persistent_rejection_stops_after_one_retry(self, mock_popen, _sleep, _which):
        mock_popen.side_effect = [_proc(255, b"", REJECTED.encode()), _proc(255, b"", REJECTED.encode())]
        rc, _, err = _subprocess_ssh("h", "u", "pw", "true", 10, "/dev/null")
        assert rc == 255
        assert mock_popen.call_count == 2
        assert "Too many authentication failures" in err

    def test_wrong_password_rc5_is_not_retried(self, mock_popen, _sleep, _which):
        """Switch password sweeps rely on a wrong candidate failing fast, once."""
        mock_popen.return_value = _proc(5, b"", b"Permission denied, please try again.\n")
        rc, _, _ = _subprocess_ssh("h", "u", "wrong", "hostname", 10, "/dev/null")
        assert rc == 5
        assert mock_popen.call_count == 1

    def test_remote_command_failure_is_not_retried(self, mock_popen, _sleep, _which):
        mock_popen.return_value = _proc(1, b"", b"No such file or directory\n")
        _subprocess_ssh("h", "u", "pw", "false", 10, "/dev/null")
        assert mock_popen.call_count == 1

    def test_ssh_banner_noise_is_stripped(self, mock_popen, _sleep, _which):
        mock_popen.side_effect = [_proc(255, b"", REJECTED.encode())] * 2
        _, _, err = _subprocess_ssh("h", "u", "pw", "true", 10, "/dev/null")
        assert "Permanently added" not in err
        assert "post-quantum" not in err
        assert "Permission denied, please try again." in err


@patch("workflows.vperfsanity_workflow.run_ssh_command")
def test_vperfsanity_login_rejection_is_not_tests_failed(mock_ssh):
    wf = VperfsanityWorkflow()
    wf.set_credentials({"cluster_ip": "10.141.200.238", "node_user": "vastdata", "node_password": "pw"})
    wf.set_output_callback(MagicMock())
    wf._step_data = {"vip_pool": "vippool-1", "vperf_dir": "/tmp/vperfsanity"}
    mock_ssh.return_value = (255, "", REJECTED)
    result = wf._step_run_tests()
    assert result["success"] is False
    assert "SSH login to 10.141.200.238 was rejected" in result["message"]
    assert "did not start" in result["message"]
    assert "Tests failed" not in result["message"]
