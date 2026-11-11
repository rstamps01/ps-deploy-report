"""vperfsanity Step 4 output filter (FR-16).

elbencho's full-screen live view under ``ssh -tt`` produced about 1,500 redraw frames
(2.2 MB) per run in Output Results.  The filter collapses them to periodic progress
lines, keeps the WRITE/READ result blocks, and turns the burst-recovery wait's
carriage-return status updates into lines as they arrive.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows.vperfsanity_output import VperfsanityOutputFilter, visible_tail  # noqa: E402

FIXTURE = (Path(__file__).parent / "data" / "vperfsanity_step4_tty.txt").read_bytes().decode("utf-8")

WRITE_BLOCK = [
    "WRITE       Elapsed time     :   5m31.501s    7m1.077s",
    "            Objects/s        :           0           0",
    "            IOPS             :         673         622",
    "            Throughput MiB/s :       10772        9960",
    "            Total MiB        :     3571214     4194304",
    "            Objects total    :           1         128",
]
READ_BLOCK = [
    "READ        Elapsed time     :   1m13.424s   1m44.067s",
    "            Objects/s        :           0           1",
    "            IOPS             :        2479        2518",
    "            Throughput MiB/s :       39677       40303",
    "            Total MiB        :     2913305     4194304",
    "            Objects total    :           1         128",
]


class _Clock:
    def __init__(self, start: float = 0.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def _run(text: str, chunk: int = 0, clock=None):
    lines, raw = [], []
    flt = VperfsanityOutputFilter(lines.append, raw.append, clock=clock or _Clock())
    if chunk:
        for i in range(0, len(text), chunk):
            flt.feed(text[i : i + chunk])
    else:
        flt.feed(text)
    flt.flush()
    return lines, raw


def _contains_block(lines, block):
    start = lines.index(block[0])
    return lines[start : start + len(block)] == block


class TestResultBlocks:
    def test_write_and_read_result_blocks_are_kept_intact(self):
        lines, _ = _run(FIXTURE)
        assert _contains_block(lines, WRITE_BLOCK)
        assert _contains_block(lines, READ_BLOCK)

    def test_output_is_independent_of_chunk_boundaries(self):
        whole, _ = _run(FIXTURE)
        for size in (1, 7, 64, 333):
            assert _run(FIXTURE, chunk=size)[0] == whole

    def test_setup_lines_pass_through(self):
        lines, _ = _run(FIXTURE)
        assert "Collecting information about the cluster to start run..." in lines
        assert "DBoxes: 1 | Files: 128 | Filesize: 32G | Size total: 4.0T" in lines


class TestFrameCollapse:
    def test_no_redraw_frames_or_escapes_reach_output(self):
        lines, _ = _run(FIXTURE)
        assert not any("\x1b" in line for line in lines)
        assert not any("DoneMiB" in line or line.startswith("Phase:") for line in lines)

    def test_one_progress_line_per_phase_when_clock_is_still(self):
        lines, _ = _run(FIXTURE)
        progress = [line for line in lines if " done, " in line]
        assert progress == [
            "WRITE: 0% done, 11676 MiB/s, elapsed 2s",
            "READ: 1% done, 28911 MiB/s, elapsed 2s",
        ]

    def test_progress_is_throttled_by_interval(self):
        clock = _Clock()
        lines, raw = [], []
        flt = VperfsanityOutputFilter(lines.append, raw.append, clock=clock)
        for line in FIXTURE.split("\r\n"):
            clock.now += VperfsanityOutputFilter.PROGRESS_INTERVAL_S / 2
            flt.feed(line + "\r\n")
        flt.flush()
        write_progress = [line for line in lines if line.startswith("WRITE: ")]
        # Six WRITE frames, two lines (a full interval) each: one progress line per frame.
        assert len(write_progress) == 6
        assert all(" MiB/s, elapsed " in line for line in write_progress)

    def test_frames_without_alternate_screen_are_still_collapsed(self):
        text = "Phase: WRITE  CPU:  48%  Active: 2  Elapsed: 2s\r\n Rank   %    DoneMiB  MiB/s\r\nTotal   3   140156   13377\r\n"
        lines, _ = _run(text)
        assert lines == ["WRITE: 3% done, 13377 MiB/s, elapsed 2s"]

    def test_errors_inside_live_view_are_not_hidden(self):
        text = (
            "\x1b[?1049h\x1b[H\x1b[2JPhase: WRITE  Elapsed: 2s\r\nERROR: lost connection to service\r\n\x1b[?1049l\r\n"
        )
        lines, _ = _run(text)
        assert "ERROR: lost connection to service" in lines


class TestNothingImportantIsHidden:
    """Review findings: plain text inside the live view, SSH noise, burst+text segments."""

    LIVE = "\x1b[?1049h\x1b[H\x1b[2JPhase: WRITE  CPU:  48%  Active: 2  Elapsed: 2s\r\n"

    def test_transport_drop_inside_live_view_is_shown(self):
        text = (
            self.LIVE + "client_loop: send disconnect: Broken pipe\r\nConnection to 10.0.0.1 closed by remote host.\r\n"
        )
        lines, _ = _run(text)
        assert "client_loop: send disconnect: Broken pipe" in lines
        assert "Connection to 10.0.0.1 closed by remote host." in lines

    def test_hint_after_elbencho_dies_without_leaving_live_view(self):
        text = self.LIVE + "HINT: Consider increasing the number of objects to: 1128\r\n"
        lines, _ = _run(text)
        assert "HINT: Consider increasing the number of objects to: 1128" in lines

    def test_plain_rank_rows_inside_live_view_are_collapsed(self):
        text = self.LIVE + "Total   3   140156   13377   835\r\n    0   3    74111    6961   434\r\n"
        lines, _ = _run(text)
        assert lines == ["WRITE: 3% done, 13377 MiB/s, elapsed 2s"]

    def test_ssh_client_banner_lines_are_hidden_but_kept_raw(self):
        text = "Warning: Permanently added '10.0.0.1' (ECDSA) to the list of known hosts.\r\nhello\r\n"
        lines, raw = _run(text)
        assert lines == ["hello"]
        assert any("Permanently added" in line for line in raw)

    def test_text_after_a_burst_update_in_the_same_segment_is_kept(self):
        text = (
            "\rElapsed time at last status check: 0m:30s [Burst buffer fill: 61.3%]"
            "ERROR: Unable to determine if cluster is bursting.\r\n"
        )
        lines, _ = _run(text)
        assert lines == [
            "Burst recovery wait: 0m:30s elapsed, buffer fill 61.3%",
            "ERROR: Unable to determine if cluster is bursting.",
        ]

    def test_error_redrawn_every_frame_is_shown_once(self):
        frame = "\x1b[H\x1b[2JPhase: WRITE  Elapsed: 2s\r\n\x1b[5;1HERROR: service 172.16.0.8 not responding\r\n"
        lines, _ = _run("\x1b[?1049h" + frame * 50 + "\x1b[?1049l\r\n")
        assert lines.count("ERROR: service 172.16.0.8 not responding") == 1

    def test_alternating_frame_errors_are_shown_once_each(self):
        frame_a = "\x1b[H\x1b[2JPhase: WRITE  Elapsed: 2s\r\n\x1b[5;1HERROR: service 172.16.0.8 not responding\r\n"
        frame_b = "\x1b[H\x1b[2JPhase: WRITE  Elapsed: 3s\r\n\x1b[5;1HERROR: service 172.16.0.9 not responding\r\n"
        lines, _ = _run("\x1b[?1049h" + (frame_a + frame_b) * 50 + "\x1b[?1049l\r\n")
        assert lines.count("ERROR: service 172.16.0.8 not responding") == 1
        assert lines.count("ERROR: service 172.16.0.9 not responding") == 1

    def test_colored_error_in_a_frame_is_kept_whole(self):
        frame = "\x1b[H\x1b[2JPhase: WRITE  Elapsed: 2s\r\n\x1b[5;1H\x1b[31mERROR\x1b[0m: lost connection\r\n"
        lines, _ = _run("\x1b[?1049h" + frame + "\x1b[?1049l\r\n")
        assert "ERROR: lost connection" in lines

    def test_text_after_erase_line_inside_live_view_is_shown(self):
        lines, _ = _run(self.LIVE + "\x1b[KWRITE stopped by user\r\n")
        assert "WRITE stopped by user" in lines

    def test_long_line_without_terminator_does_not_grow_unbounded(self):
        lines = []
        flt = VperfsanityOutputFilter(lines.append, clock=_Clock())
        flt.feed("x" * (VperfsanityOutputFilter.MAX_PENDING_CHARS + 10))
        assert len(flt._pending) <= VperfsanityOutputFilter.MAX_PENDING_CHARS
        assert lines and lines[0].startswith("xxx")


class TestBurstWait:
    def test_burst_status_updates_become_lines(self):
        lines, _ = _run(FIXTURE)
        assert "Burst recovery wait: 0m:30s elapsed, buffer fill 61.3%" in lines
        assert "Burst recovery wait: 1m:00s elapsed, buffer fill 58.9%" in lines
        assert "Cluster finished burst / post-burst phase. (Wait time: 1m:30s)" in lines

    def test_burst_status_is_emitted_before_the_next_carriage_return(self):
        lines = []
        flt = VperfsanityOutputFilter(lines.append, clock=_Clock())
        flt.feed("Waiting for burst / post-burst phase to finish...\r\n")
        flt.feed("\rElapsed time at last status check: 0m:30s [Burst buffer fill: 61.3%]")
        assert lines[-1] == "Burst recovery wait: 0m:30s elapsed, buffer fill 61.3%"
        flt.feed("\rElapsed time at last status check: 1m:00s [Burst buffer fill: N/A]")
        flt.flush()
        assert lines[-1] == "Burst recovery wait: 1m:00s elapsed, buffer fill N/A"
        assert len([line for line in lines if line.startswith("Burst recovery wait")]) == 2


class TestRawTranscript:
    def test_raw_sink_keeps_every_frame(self):
        _, raw = _run(FIXTURE, chunk=50)
        assert sum("Phase: WRITE" in line for line in raw) == 6
        assert any("\x1b[" in line for line in raw)
        assert not any(line.endswith("\r") for line in raw)

    def test_raw_sink_is_optional(self):
        lines = []
        flt = VperfsanityOutputFilter(lines.append)
        flt.feed("hello\r\n")
        flt.flush()
        assert lines == ["hello"]

    def test_visible_tail_keeps_only_text_after_the_last_escape(self):
        assert visible_tail("\x1b[H\x1b[2JPhase: WRITE\x1b[5;1HConnection closed. ") == "Connection closed."
        assert visible_tail("  plain line  ") == "plain line"
        assert visible_tail("\x1b[H\x1b[2J") == ""

    def test_received_reports_whether_anything_was_fed(self):
        flt = VperfsanityOutputFilter(lambda _line: None)
        assert flt.received is False
        flt.feed("x")
        assert flt.received is True
