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
