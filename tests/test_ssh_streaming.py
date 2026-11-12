"""
Tests for live output streaming in the SSH adapter (FR-16).

``run_ssh_command(..., on_output=cb)`` must hand remote output to ``cb`` while
the command is still running, on both the subprocess and paramiko paths,
without changing the returned ``(rc, stdout, stderr)``.
"""

import os
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import ssh_adapter  # noqa: E402

_HANG_GUARD_S = 10.0


def _py(code: str) -> list:
    return [sys.executable, "-c", code]


class _Recorder:
    """on_output callback that records (monotonic time, chunk)."""

    def __init__(self) -> None:
        self.calls: list = []

    def __call__(self, chunk: str) -> None:
        self.calls.append((time.monotonic(), chunk))

    @property
    def text(self) -> str:
        return "".join(chunk for _, chunk in self.calls)


@unittest.skipIf(sys.platform == "win32", "subprocess SSH path (process groups, killpg) is macOS/Linux only")
class TestRunSshPopenStreaming(unittest.TestCase):
    """The subprocess path streams real pipe output through reader threads."""

    def test_run_ssh_popen_streams_stdout_before_exit(self):
        code = (
            "import sys, time\n"
            "sys.stdout.write('first\\n'); sys.stdout.flush()\n"
            "time.sleep(1.5)\n"
            "sys.stdout.write('second\\n'); sys.stdout.flush()\n"
        )
        rec = _Recorder()
        rc, out, err = ssh_adapter._run_ssh_popen(_py(code), timeout=10, env=os.environ.copy(), on_output=rec)
        returned_at = time.monotonic()

        self.assertEqual(rc, 0)
        self.assertEqual(out, "first\nsecond\n")
        self.assertEqual(rec.text, out)
        first_time = next(t for t, chunk in rec.calls if "first" in chunk)
        self.assertGreater(returned_at - first_time, 0.5)

    def test_chunks_after_return_are_not_delivered(self):
        stopped = ssh_adapter.threading.Event()
        rec, parts = _Recorder(), []
        ssh_adapter._deliver_chunk("before", parts, rec, None, stopped)
        stopped.set()
        ssh_adapter._deliver_chunk("after", parts, rec, None, stopped)
        self.assertEqual(rec.text, "before")

    def test_run_ssh_popen_streams_stderr(self):
        code = "import sys\nsys.stderr.write('oops\\n'); sys.stderr.flush()\nsys.exit(3)\n"
        rec = _Recorder()
        rc, out, err = ssh_adapter._run_ssh_popen(_py(code), timeout=10, env=os.environ.copy(), on_output=rec)

        self.assertEqual(rc, 3)
        self.assertEqual(out, "")
        self.assertEqual(err, "oops\n")
        self.assertEqual(rec.text, "oops\n")

    def test_run_ssh_popen_timeout_kills_and_keeps_partial_output(self):
        code = "import sys, time\nsys.stdout.write('started\\n'); sys.stdout.flush()\ntime.sleep(10)\n"
        rec = _Recorder()
        start = time.monotonic()
        rc, out, err = ssh_adapter._run_ssh_popen(_py(code), timeout=1, env=os.environ.copy(), on_output=rec)
        elapsed = time.monotonic() - start

        self.assertEqual(rc, 1)
        self.assertIn("started", out)
        self.assertTrue(err.endswith("SSH command timed out after 1s"))
        self.assertLess(elapsed, 3.0)
        self.assertNotIn("timed out", rec.text)

    def test_run_ssh_popen_raising_callback_does_not_break_command(self):
        code = "print('a'); print('b')"

        def _boom(_chunk: str) -> None:
            raise RuntimeError("callback failure")

        rc, out, err = ssh_adapter._run_ssh_popen(_py(code), timeout=10, env=os.environ.copy(), on_output=_boom)

        self.assertEqual(rc, 0)
        self.assertEqual(out, "a\nb\n")

    def test_run_ssh_popen_decodes_utf8_split_across_reads(self):
        code = (
            "import sys, time\n"
            "data = 'caf\\u00e9\\n'.encode('utf-8')\n"
            "sys.stdout.buffer.write(data[:-2]); sys.stdout.buffer.flush()\n"
            "time.sleep(0.2)\n"
            "sys.stdout.buffer.write(data[-2:]); sys.stdout.buffer.flush()\n"
        )
        rec = _Recorder()
        rc, out, err = ssh_adapter._run_ssh_popen(_py(code), timeout=10, env=os.environ.copy(), on_output=rec)

        self.assertEqual(rc, 0)
        self.assertEqual(out, "caf\u00e9\n")
        self.assertEqual(rec.text, "caf\u00e9\n")
        self.assertNotIn("\ufffd", rec.text)

    @patch("utils.ssh_adapter.subprocess.Popen")
    def test_run_ssh_popen_without_callback_uses_communicate(self, mock_popen):
        proc = MagicMock()
        proc.returncode = 0
        proc.communicate.return_value = (b"out", b"err")
        mock_popen.return_value = proc

        rc, out, err = ssh_adapter._run_ssh_popen(["ssh"], timeout=5, env={})

        proc.communicate.assert_called_once_with(timeout=5)
        proc.wait.assert_not_called()
        self.assertEqual((rc, out, err), (0, "out", "err"))


class TestOnOutputForwarding(unittest.TestCase):
    """run_ssh_command threads on_output through every transport path."""

    def setUp(self) -> None:
        self.cb = MagicMock()

    @patch("utils.ssh_adapter.IS_WINDOWS", False)
    @patch("utils.ssh_adapter._subprocess_ssh", return_value=(0, "", ""))
    def test_run_ssh_command_forwards_on_output_to_subprocess(self, mock_ssh):
        ssh_adapter.run_ssh_command("h", "u", "p", "cmd", on_output=self.cb)
        self.assertIs(mock_ssh.call_args.kwargs["on_output"], self.cb)

    @patch("utils.ssh_adapter.IS_WINDOWS", True)
    @patch("utils.ssh_adapter._paramiko_exec", return_value=(0, "", ""))
    def test_run_ssh_command_forwards_on_output_on_windows(self, mock_exec):
        ssh_adapter.run_ssh_command("h", "u", "p", "cmd", on_output=self.cb)
        self.assertIs(mock_exec.call_args.kwargs["on_output"], self.cb)

    @patch("utils.ssh_adapter.IS_WINDOWS", False)
    @patch("utils.ssh_adapter._paramiko_exec", return_value=(0, "", ""))
    def test_run_ssh_command_forwards_on_output_via_jump_host(self, mock_exec):
        ssh_adapter.run_ssh_command(
            "h", "u", "p", "cmd", jump_host="j", jump_user="ju", jump_password="jp", on_output=self.cb
        )
        self.assertIs(mock_exec.call_args.kwargs["on_output"], self.cb)

    @patch("utils.ssh_adapter.IS_WINDOWS", False)
    @patch("utils.ssh_adapter._subprocess_ssh", return_value=(0, "", ""))
    def test_run_ssh_command_defaults_on_output_to_none(self, mock_ssh):
        ssh_adapter.run_ssh_command("h", "u", "p", "cmd")
        self.assertIsNone(mock_ssh.call_args.kwargs["on_output"])

    @patch("shutil.which", return_value="/usr/bin/sshpass")
    @patch("utils.ssh_adapter._run_ssh_popen", return_value=(0, "ok", ""))
    def test_subprocess_ssh_forwards_on_output_to_popen(self, mock_popen, _which):
        ssh_adapter._subprocess_ssh("h", "u", "p", "cmd", 10, "/dev/null", on_output=self.cb)
        self.assertIs(mock_popen.call_args.kwargs["on_output"], self.cb)

    @patch("shutil.which", return_value=None)
    @patch("utils.ssh_adapter._paramiko_exec", return_value=(0, "ok", ""))
    def test_subprocess_ssh_forwards_on_output_to_paramiko_fallback(self, mock_exec, _which):
        ssh_adapter._subprocess_ssh("h", "u", "p", "cmd", 10, "/dev/null", on_output=self.cb)
        self.assertIs(mock_exec.call_args.kwargs["on_output"], self.cb)

    @patch("utils.ssh_adapter.time.sleep")
    @patch("shutil.which", return_value="/usr/bin/sshpass")
    @patch("utils.ssh_adapter._run_ssh_popen")
    def test_subprocess_ssh_auth_retry_keeps_streaming(self, mock_popen, _which, _sleep):
        mock_popen.side_effect = [
            (255, "", "Received disconnect: Too many authentication failures\n"),
            (0, "ok", ""),
        ]
        rc, out, _err = ssh_adapter._subprocess_ssh("h", "u", "p", "cmd", 10, "/dev/null", on_output=self.cb)

        self.assertEqual((rc, out), (0, "ok"))
        self.assertEqual(mock_popen.call_count, 2)
        for call in mock_popen.call_args_list:
            self.assertIs(call.kwargs["on_output"], self.cb)


class _FakeChannel:
    """Minimal paramiko Channel: replays scripted stdout/stderr chunks, then exits.

    ``exit_first`` reports the exit status as ready from the start, and ``tail_delay_polls``
    holds the last chunk back for that many ``recv_ready`` polls, as a remote PTY that is
    still draining after the process exited would.  With ``never_exits``,
    ``recv_exit_status`` blocks until ``close`` like paramiko's does.
    """

    def __init__(
        self,
        events: list,
        exit_status: int = 0,
        never_exits: bool = False,
        exit_first: bool = False,
        tail_delay_polls: int = 0,
        sends_eof: bool = True,
    ) -> None:
        self._events = list(events)
        self._exit_status = exit_status
        self._never_exits = never_exits
        self._exit_first = exit_first
        self._tail_delay_polls = tail_delay_polls
        self._sends_eof = sends_eof
        self._closed_event = threading.Event()
        self.closed = False

    def _next_is(self, kind: str) -> bool:
        if not self._events or self._events[0][0] != kind:
            return False
        if len(self._events) == 1 and self._tail_delay_polls > 0:
            self._tail_delay_polls -= 1
            return False
        return True

    def recv_ready(self) -> bool:
        return self._next_is("out")

    def recv_stderr_ready(self) -> bool:
        return self._next_is("err")

    def recv(self, _size: int) -> bytes:
        return self._events.pop(0)[1]

    def recv_stderr(self, _size: int) -> bytes:
        return self._events.pop(0)[1]

    def exit_status_ready(self) -> bool:
        if self._never_exits:
            return False
        return self._exit_first or not self._events

    @property
    def eof_received(self) -> bool:
        return self._sends_eof and not self._events and not self._never_exits

    def recv_exit_status(self) -> int:
        if self._never_exits:
            self._closed_event.wait(_HANG_GUARD_S)
            return -1
        return self._exit_status

    def close(self) -> None:
        self.closed = True
        self._closed_event.set()


def _mock_paramiko_with_channel(channel: _FakeChannel):
    mock_paramiko = MagicMock()
    mock_paramiko.AuthenticationException = type("AuthenticationException", (Exception,), {})
    mock_paramiko.SSHException = type("SSHException", (Exception,), {})
    mock_paramiko.AutoAddPolicy.return_value = "policy"
    mock_client = MagicMock()
    mock_paramiko.SSHClient.return_value = mock_client
    mock_stdout = MagicMock()
    mock_stdout.channel = channel
    mock_client.exec_command.return_value = (MagicMock(), mock_stdout, MagicMock())
    return mock_paramiko, mock_client, mock_stdout


class TestParamikoStreaming(unittest.TestCase):
    """The paramiko path polls the channel and streams each chunk."""

    def test_paramiko_exec_streams_stdout_then_stderr(self):
        channel = _FakeChannel([("out", b"hello "), ("out", b"world\n"), ("err", b"warn\n")], exit_status=0)
        mock_paramiko, mock_client, mock_stdout = _mock_paramiko_with_channel(channel)
        rec = _Recorder()

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            rc, out, err = ssh_adapter._paramiko_exec("h", "u", "p", "cmd", 10, force_tty=True, on_output=rec)

        self.assertEqual((rc, out, err), (0, "hello world\n", "warn\n"))
        self.assertEqual([chunk for _, chunk in rec.calls], ["hello ", "world\n", "warn\n"])
        self.assertTrue(mock_client.exec_command.call_args.kwargs["get_pty"])
        mock_stdout.read.assert_not_called()
        mock_client.close.assert_called_once()

    def test_paramiko_exec_streams_split_utf8(self):
        data = "caf\u00e9\n".encode("utf-8")
        channel = _FakeChannel([("out", data[:-2]), ("out", data[-2:])], exit_status=0)
        mock_paramiko, _client, _stdout = _mock_paramiko_with_channel(channel)
        rec = _Recorder()

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            rc, out, _err = ssh_adapter._paramiko_exec("h", "u", "p", "cmd", 10, on_output=rec)

        self.assertEqual(out, "caf\u00e9\n")
        self.assertEqual(rec.text, "caf\u00e9\n")

    def test_paramiko_exec_keeps_output_that_arrives_after_exit_status(self):
        channel = _FakeChannel(
            [("out", b"WRITE ...\n"), ("out", b"READ result block\n")], exit_first=True, tail_delay_polls=3
        )
        mock_paramiko, _client, _stdout = _mock_paramiko_with_channel(channel)
        rec = _Recorder()

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}), patch("utils.ssh_adapter.time.sleep"):
            rc, out, _err = ssh_adapter._paramiko_exec("h", "u", "p", "cmd", 10, on_output=rec)

        self.assertEqual(rc, 0)
        self.assertEqual(out, "WRITE ...\nREAD result block\n")
        self.assertEqual(rec.text, out)

    def test_paramiko_exec_ends_after_grace_when_server_never_sends_eof(self):
        channel = _FakeChannel([("out", b"done\n")], exit_status=0, sends_eof=False)
        mock_paramiko, _client, _stdout = _mock_paramiko_with_channel(channel)
        rec = _Recorder()
        ticks = iter(range(10_000))

        with (
            patch.dict("sys.modules", {"paramiko": mock_paramiko}),
            patch("utils.ssh_adapter.time.sleep"),
            patch("utils.ssh_adapter.time.monotonic", side_effect=lambda: next(ticks) * 0.25),
        ):
            rc, out, err = ssh_adapter._paramiko_exec("h", "u", "p", "cmd", 10, on_output=rec)

        self.assertEqual((rc, out, err), (0, "done\n", ""))
        self.assertFalse(channel.closed)
        self.assertEqual(rec.text, "done\n")

    def test_paramiko_exec_stream_timeout_closes_channel(self):
        channel = _FakeChannel([("out", b"partial\n")], never_exits=True)
        mock_paramiko, _client, _stdout = _mock_paramiko_with_channel(channel)
        rec = _Recorder()

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            rc, out, err = ssh_adapter._paramiko_exec("h", "u", "p", "cmd", 0, on_output=rec)

        self.assertEqual(rc, 1)
        self.assertEqual(out, "partial\n")
        self.assertTrue(err.endswith("SSH command timed out after 0s"))
        self.assertTrue(channel.closed)
        self.assertEqual(rec.text, "partial\n")

    def test_paramiko_exec_without_callback_polls_channel(self):
        channel = _FakeChannel([("out", b"done\n"), ("err", b"warn\n")], exit_status=3)
        mock_paramiko, _client, mock_stdout = _mock_paramiko_with_channel(channel)

        with patch.dict("sys.modules", {"paramiko": mock_paramiko}):
            rc, out, err = ssh_adapter._paramiko_exec("h", "u", "p", "cmd", 10)

        self.assertEqual((rc, out, err), (3, "done\n", "warn\n"))
        mock_stdout.read.assert_not_called()
        self.assertFalse(channel.closed)


class TestParamikoNonStreamingDeadline(unittest.TestCase):
    """Without on_output, the paramiko path still treats *timeout* as a hard deadline (FR-10)."""

    def test_paramiko_exec_without_callback_times_out_when_exit_status_never_ready(self):
        timeout = 1
        channel = _FakeChannel([("out", b"partial\n"), ("err", b"warn\n")], never_exits=True)
        mock_paramiko, mock_client, _stdout = _mock_paramiko_with_channel(channel)
        clock = [0.0]
        result: dict = {}

        def _sleep(seconds: float) -> None:
            clock[0] += seconds

        def _call() -> None:
            result["value"] = ssh_adapter._paramiko_exec("h", "u", "p", "cmd", timeout)
            result["returned_at"] = clock[0]

        worker = threading.Thread(target=_call, daemon=True)
        with (
            patch.dict("sys.modules", {"paramiko": mock_paramiko}),
            patch("utils.ssh_adapter.time.sleep", side_effect=_sleep),
            patch("utils.ssh_adapter.time.monotonic", side_effect=lambda: clock[0]),
        ):
            worker.start()
            worker.join(2.0)
            hung = worker.is_alive()
            if hung:
                channel.close()
                worker.join(2.0)

        self.assertFalse(hung, "_paramiko_exec blocked past its timeout waiting for the exit status")
        rc, out, err = result["value"]
        self.assertEqual(rc, 1)
        self.assertEqual(out, "partial\n")
        self.assertEqual(err, "warn\nSSH command timed out after 1s")
        self.assertLessEqual(result["returned_at"], timeout + ssh_adapter._PARAMIKO_POLL_S + 1e-6)
        self.assertTrue(channel.closed)
        mock_client.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
