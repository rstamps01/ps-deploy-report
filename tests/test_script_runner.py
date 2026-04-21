"""
Unit tests for Script Runner module.

Tests the ScriptRunner class including file operations, remote execution,
and result handling.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from script_runner import FileTransferResult, ScriptResult, ScriptRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def runner():
    """Create a ScriptRunner instance."""
    return ScriptRunner()


# ===================================================================
# TestScriptResult
# ===================================================================


class TestScriptResult:
    def test_create_success_result(self):
        result = ScriptResult(
            success=True,
            returncode=0,
            stdout="Hello World",
            stderr="",
            duration_ms=1500,
        )
        assert result.success is True
        assert result.returncode == 0
        assert result.stdout == "Hello World"
        assert result.duration_ms == 1500

    def test_create_failure_result(self):
        result = ScriptResult(
            success=False,
            returncode=1,
            stdout="",
            stderr="Error occurred",
            duration_ms=500,
        )
        assert result.success is False
        assert result.returncode == 1
        assert "Error" in result.stderr


class TestFileTransferResult:
    def test_create_transfer_result(self):
        result = FileTransferResult(
            success=True,
            local_path="/tmp/file.txt",
            remote_path="/home/user/file.txt",
            size_bytes=1024,
        )
        assert result.success is True
        assert result.size_bytes == 1024


# ===================================================================
# TestScriptRunner
# ===================================================================


class TestScriptRunner:
    def test_runner_initialization(self, runner):
        assert runner is not None

    def test_get_local_dir(self, runner):
        local_dir = runner.get_local_dir()
        assert isinstance(local_dir, Path)


class TestScriptRunnerPrerequisites:
    def test_check_prerequisites_missing_creds(self, runner):
        ok, msg = runner.check_prerequisites("", "", "")
        assert ok is False

    @patch("script_runner.run_ssh_command")
    def test_check_prerequisites_success(self, mock_ssh, runner):
        mock_ssh.return_value = (0, "test-host", "")
        ok, msg = runner.check_prerequisites("10.0.0.1", "user", "pass")
        assert ok is True


class TestScriptRunnerDownload:
    def test_download_to_local_success(self, runner):
        import requests

        with patch.object(requests, "get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.content = b"test content"
            mock_resp.iter_content.return_value = [b"test content"]
            mock_resp.raise_for_status = MagicMock()
            mock_get.return_value = mock_resp

            result = runner.download_to_local("test_script.py", url="https://example.com/script.py")
            assert result.success is True

    def test_download_to_local_failure(self, runner):
        import requests

        with patch.object(requests, "get") as mock_get:
            mock_get.side_effect = Exception("Not found")

            result = runner.download_to_local("missing_script.py", url="https://example.com/missing.py")
            assert result.success is False

    def test_download_to_local_no_url(self, runner):
        # Unknown script without URL should fail
        result = runner.download_to_local("unknown_script.py")
        assert result.success is False


class TestScriptRunnerRemoteExecution:
    @patch("script_runner.run_ssh_command")
    def test_execute_remote_success(self, mock_ssh, runner):
        mock_ssh.return_value = (0, "output", "")
        result = runner.execute_remote("10.0.0.1", "user", "pass", "ls -la")
        assert result.success is True
        assert result.returncode == 0

    @patch("script_runner.run_ssh_command")
    def test_execute_remote_failure(self, mock_ssh, runner):
        mock_ssh.return_value = (1, "", "command not found")
        result = runner.execute_remote("10.0.0.1", "user", "pass", "badcmd")
        assert result.success is False
        assert result.returncode == 1

    @patch("script_runner.run_ssh_command")
    def test_execute_remote_timeout(self, mock_ssh, runner):
        mock_ssh.side_effect = Exception("Connection timed out")
        result = runner.execute_remote("10.0.0.1", "user", "pass", "cmd")
        assert result.success is False


class TestScriptRunnerRedaction:
    """RM-1: verify ``display_command`` redacts sensitive text in log echoes.

    When a caller passes a ``display_command`` that differs from ``command``,
    the real command must still be handed to SSH verbatim, but the operator
    log (and anything downstream: bundles, clipboard copies, UI pane) must
    only ever see the redacted form.  The canonical trigger is the vnetmap
    per-switch password heredoc where ``command`` embeds a JSON map of real
    passwords — those literals must not appear in a single emitted entry.
    """

    @patch("script_runner.run_ssh_command")
    def test_display_command_replaces_echo(self, mock_ssh):
        mock_ssh.return_value = (0, "", "")
        emitted = []

        def cb(level, message, _meta):
            emitted.append((level, message))

        runner = ScriptRunner(output_callback=cb)
        real_cmd = (
            "python3 vnetmap.py -s $MLX_IPS -i $cnodes_ips "
            "--multiple-passwords <<'VAST_PW_MAP'\n"
            '{"10.0.0.1": "Vastdata1!", "10.0.0.2": "SpareLeaf!"}\n'
            "VAST_PW_MAP"
        )
        display_cmd = "python3 vnetmap.py -s $MLX_IPS -i $cnodes_ips --multiple-passwords <redacted>"

        runner.execute_remote("10.0.0.10", "vastdata", "nodepw", real_cmd, display_command=display_cmd)

        # SSH gets the real command, including the secret heredoc.
        called_cmd = mock_ssh.call_args.args[3]
        assert "Vastdata1!" in called_cmd
        assert "SpareLeaf!" in called_cmd

        # The emitted log pane never sees the real passwords.
        joined = "\n".join(m for _, m in emitted)
        assert "Vastdata1!" not in joined
        assert "SpareLeaf!" not in joined
        assert "<redacted>" in joined

    @patch("script_runner.run_ssh_command")
    def test_display_command_default_echoes_command_verbatim(self, mock_ssh):
        """Backwards-compat: when ``display_command`` is omitted, the command
        is echoed as before so ordinary (safe) shell invocations still appear
        in the operator pane."""
        mock_ssh.return_value = (0, "", "")
        emitted = []

        def cb(level, message, _meta):
            emitted.append((level, message))

        runner = ScriptRunner(output_callback=cb)
        runner.execute_remote("10.0.0.10", "vastdata", "nodepw", "ls -la /tmp")

        joined = "\n".join(m for _, m in emitted)
        assert "ls -la /tmp" in joined

    @patch("script_runner.run_ssh_command")
    def test_display_command_respects_working_dir_prefix(self, mock_ssh):
        """When ``working_dir`` is set, both the real and display forms get
        the same ``cd <dir> &&`` prefix so the echoed line remains readable
        without leaking the working directory back into the wrong form."""
        mock_ssh.return_value = (0, "", "")
        emitted = []

        def cb(level, message, _meta):
            emitted.append((level, message))

        runner = ScriptRunner(output_callback=cb)
        runner.execute_remote(
            "10.0.0.10",
            "vastdata",
            "nodepw",
            "python3 vnetmap.py -p 'Vastdata1!'",
            working_dir="/vast/install",
            display_command="python3 vnetmap.py -p '<switch-password>'",
        )

        called_cmd = mock_ssh.call_args.args[3]
        assert called_cmd == "cd /vast/install && python3 vnetmap.py -p 'Vastdata1!'"

        joined = "\n".join(m for _, m in emitted)
        assert "Vastdata1!" not in joined
        assert "cd /vast/install && python3 vnetmap.py -p '<switch-password>'" in joined


class TestScriptRunnerCleanup:
    @patch("script_runner.run_ssh_command")
    def test_cleanup_remote_success(self, mock_ssh, runner):
        mock_ssh.return_value = (0, "", "")
        result = runner.cleanup_remote("10.0.0.1", "user", "pass", ["/tmp/file.txt"])
        assert result is True

    def test_cleanup_remote_empty_list(self, runner):
        result = runner.cleanup_remote("10.0.0.1", "user", "pass", [])
        assert result is True


class TestOutputClassification:
    def test_classify_warning_line(self, runner):
        result = runner._classify_output_line("{ERROR} General exception from data node")
        assert result == "warn"

    def test_classify_normal_line(self, runner):
        result = runner._classify_output_line("Processing node 10.0.0.1")
        assert result == "info"

    def test_classify_traceback_suppressed(self, runner):
        result = runner._classify_output_line("Traceback (most recent call last):")
        assert result is None

    def test_classify_empty_line(self, runner):
        result = runner._classify_output_line("")
        assert result == "info"

    def test_classify_ssh_retry_suppressed(self, runner):
        result = runner._classify_output_line("Try again using SSH_KEY2")
        assert result is None


class TestStderrTracebackClassification:
    """RM-8: a full Python traceback on stderr must render as one
    contiguous [ERROR] block, not a checkerboard of [ERROR]/[WARN].
    The classifier is stateful (per-stream) so indented source lines
    beneath a ``File "...", line N, in foo`` frame inherit ``error``.
    """

    def test_frame_header_classifies_as_error(self, runner):
        line = '  File "/opt/vast/vnetmap.py", line 1234, in main'
        assert runner._classify_stderr_line(line) == "error"

    def test_traceback_header_classifies_as_error(self, runner):
        assert runner._classify_stderr_line("Traceback (most recent call last):") == "error"

    def test_indented_code_snippet_inside_traceback_is_error(self, runner):
        """RM-8 core case: the indented source line between two
        ``File "..."`` frames used to be classified as ``warn``, which
        made tracebacks look like [ERROR][WARN][WARN][ERROR].  After
        RM-8 it must classify as ``error``.
        """
        runner._reset_stderr_classifier_state()
        assert runner._classify_stderr_line("Traceback (most recent call last):") == "error"
        assert runner._classify_stderr_line('  File "vnetmap.py", line 42, in main') == "error"
        assert runner._classify_stderr_line("    return subprocess.check_output(cmd, shell=True)") == "error"
        assert runner._classify_stderr_line('  File "api.py", line 17, in connect') == "error"
        assert runner._classify_stderr_line("    raise ConnectionError('fabric API unreachable')") == "error"
        assert runner._classify_stderr_line("ConnectionError: fabric API unreachable") == "error"

    def test_full_traceback_renders_as_contiguous_error_block(self, runner):
        """End-to-end: feeding the classifier a realistic vnetmap
        traceback (matching what the Test Suite showed) yields every
        line classified as ``error`` — no inline ``warn`` breaks.
        """
        runner._reset_stderr_classifier_state()
        traceback_lines = [
            "Traceback (most recent call last):",
            '  File "/opt/vast/vnetmap.py", line 1234, in main',
            "    topology = build_topology(switches)",
            '  File "/opt/vast/vnetmap.py", line 567, in build_topology',
            "    client.connect(switch_ip)",
            '  File "/opt/vast/api.py", line 99, in connect',
            "    raise Exception(f'Failed to connect to switch {switch_ip}')",
            "Exception: Failed to connect to switch 10.143.11.156",
        ]
        levels = [runner._classify_stderr_line(line) for line in traceback_lines]
        assert all(
            level == "error" for level in levels
        ), f"RM-8: expected every traceback line to classify as 'error', got {levels}"

    def test_blank_line_after_traceback_resets_state(self, runner):
        """A blank line ends the traceback block.  Subsequent indented
        output (unrelated) must not be mis-classified as ``error``.
        """
        runner._reset_stderr_classifier_state()
        runner._classify_stderr_line("Traceback (most recent call last):")
        runner._classify_stderr_line('  File "x.py", line 1, in y')
        runner._classify_stderr_line("    do_thing()")
        # Blank line ends the block.
        assert runner._classify_stderr_line("") == "info"
        # Now an indented line is not part of any traceback; default warn.
        assert runner._classify_stderr_line("    some debug line") == "warn"

    def test_ssh_host_key_warning_stays_info(self, runner):
        """RM-8 must not regress the pre-existing SSH host-key warning
        classification — these are informational, not errors.
        """
        runner._reset_stderr_classifier_state()
        line = "Warning: Permanently added '10.143.11.156' (ED25519) to the list of known hosts."
        assert runner._classify_stderr_line(line) == "info"

    def test_ping_diagnostic_stays_warn(self, runner):
        runner._reset_stderr_classifier_state()
        assert runner._classify_stderr_line("ping: cannot resolve host") == "warn"

    def test_exception_summary_regex_matches_common_exceptions(self, runner):
        """Exception-summary detection must handle the tail of a
        traceback for common exception classes (ValueError, KeyError,
        RuntimeError, TimeoutError, …) so they classify as ``error``
        and reset the traceback-continuation state.
        """
        for exc_line in [
            "ValueError: bad literal",
            "KeyError: 'missing'",
            "RuntimeError: boom",
            "TimeoutError: connection timed out",
            "paramiko.ssh_exception.AuthenticationException: authentication failed",
        ]:
            runner._reset_stderr_classifier_state()
            assert runner._classify_stderr_line(exc_line) == "error", f"expected {exc_line!r} to classify as error"

    def test_unrelated_stderr_after_reset_classifies_as_warn(self, runner):
        """After ``_reset_stderr_classifier_state`` an indented line
        that isn't preceded by a traceback header must default to warn,
        the same as before RM-8.
        """
        runner._reset_stderr_classifier_state()
        assert runner._classify_stderr_line("   some odd stderr line") == "warn"


class TestCopyToRemote:
    @patch("script_runner.run_ssh_command")
    def test_copy_to_remote_success(self, mock_ssh, runner, tmp_path):
        local_file = tmp_path / "test_script.py"
        local_file.write_text("#!/bin/bash\necho hello")

        mock_ssh.return_value = (0, "", "")

        with patch.object(runner, "_subprocess_scp", return_value=True), patch.object(
            runner, "_paramiko_scp", return_value=True
        ):
            result = runner.copy_to_remote(str(local_file), "10.0.0.1", "user", "pass")
            assert result.success is True
            assert result.size_bytes > 0

    @patch("script_runner.run_ssh_command")
    def test_copy_to_remote_file_not_found(self, mock_ssh, runner):
        result = runner.copy_to_remote("/nonexistent/file.py", "10.0.0.1", "user", "pass")
        assert result.success is False
        assert "not found" in result.error.lower()

    @patch("script_runner.run_ssh_command")
    def test_copy_to_remote_set_executable(self, mock_ssh, runner, tmp_path):
        local_file = tmp_path / "script.py"
        local_file.write_text("#!/usr/bin/env python3")

        mock_ssh.return_value = (0, "", "")

        with patch.object(runner, "_subprocess_scp", return_value=True), patch.object(
            runner, "_paramiko_scp", return_value=True
        ):
            result = runner.copy_to_remote(str(local_file), "10.0.0.1", "user", "pass", set_executable=True)
            assert result.success is True
            chmod_calls = [c for c in mock_ssh.call_args_list if "chmod" in str(c)]
            assert len(chmod_calls) > 0


class TestDownloadFromRemote:
    def test_download_from_remote_success(self, runner, tmp_path):
        local_dest = str(tmp_path / "downloaded.txt")

        with patch.object(runner, "_subprocess_download", return_value=True), patch.object(
            runner, "_paramiko_download", return_value=True
        ):
            Path(local_dest).write_text("downloaded content")
            result = runner.download_from_remote("10.0.0.1", "user", "pass", "/remote/file.txt", local_dest)
            assert result.success is True
            assert result.size_bytes > 0

    def test_download_from_remote_failure(self, runner, tmp_path):
        local_dest = str(tmp_path / "downloaded.txt")

        with patch.object(runner, "_subprocess_download", return_value=False), patch.object(
            runner, "_paramiko_download", return_value=False
        ):
            result = runner.download_from_remote("10.0.0.1", "user", "pass", "/remote/file.txt", local_dest)
            assert result.success is False
