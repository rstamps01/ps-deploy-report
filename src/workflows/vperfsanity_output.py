"""Live output filter for ``vperfsanity_run.sh`` (Step 4, FR-16).

Step 4 runs under ``ssh -tt`` so the script's burst-recovery wait prints its status and
elbencho draws its full-screen live view.  Passed through as-is, that view adds about
1,500 redraw frames (2.2 MB) per run to Output Results.  ``VperfsanityOutputFilter``
receives the remote output in arbitrary chunks and produces readable lines:

* elbencho redraw frames are dropped; a one-line progress summary is emitted at the start
  of each phase and then at most every ``PROGRESS_INTERVAL_S`` seconds;
* the WRITE/READ result blocks and all other script output pass through with terminal
  escapes stripped;
* burst-wait updates, which end in a carriage return rather than a newline, are emitted
  as soon as each one is complete.

The unfiltered output goes to an optional raw sink, one line per newline, so the
operation log keeps the full transcript.
"""

import re
import time
from collections import deque
from typing import Callable, Deque, Optional

from utils.ssh_adapter import is_ssh_noise_line, strip_terminal_escapes

_ALT_SCREEN_ON = "\x1b[?1049h"
_ALT_SCREEN_OFF = "\x1b[?1049l"
_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]|\x1b[()][0-9A-Za-z]|\x1b[=>]")
_POSITION_RE = re.compile(r"\x1b\[[0-9;?]*[HfdG]")
_ROW_RE = re.compile(r"^\s*(?:Total|\d+)(?:\s+\d+){3,}")
_PHASE_RE = re.compile(r"Phase:\s*([A-Z][A-Z_-]*)\b.*?Elapsed:\s*(\S+)")
_TOTAL_RE = re.compile(r"\bTotal\s+(\d+)\s+(\d+)\s+(\d+)")
_BURST_RE = re.compile(r"Elapsed time at last status check:\s*(\S+)\s*\[Burst buffer fill:\s*([^\]]*)\]")
_ERROR_RE = re.compile(r"\berror\b", re.IGNORECASE)


def visible_tail(line: str) -> str:
    """Return the text after the last terminal escape in ``line``, stripped.

    Redraw frames end in escapes, so this is empty for them, while a plain line comes back whole and
    a message the terminal appended to an unfinished line comes back on its own.
    """
    last = None
    for last in _ESCAPE_RE.finditer(line):
        pass
    return (line[last.end() :] if last else line).strip()


class VperfsanityOutputFilter:
    """Turn streamed ``vperfsanity_run.sh`` output into Output Results lines.

    Args:
        emit_line: Called with each visible line (no escapes, no trailing whitespace).
        emit_raw: Optional; called with each raw output line, escapes kept.
        clock: Monotonic time source in seconds, injectable for tests.
    """

    PROGRESS_INTERVAL_S = 15.0
    MAX_PENDING_CHARS = 65536
    RECENT_ERRORS = 32

    def __init__(
        self,
        emit_line: Callable[[str], None],
        emit_raw: Optional[Callable[[str], None]] = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._emit_line = emit_line
        self._emit_raw = emit_raw
        self._clock = clock
        self._pending = ""
        self._raw_pending = ""
        self._in_live_view = False
        self._phase: Optional[str] = None
        self._elapsed = ""
        self._frame_had_total = True
        self._last_progress_phase: Optional[str] = None
        self._last_progress_at = 0.0
        self._recent_frame_errors: Deque[str] = deque(maxlen=self.RECENT_ERRORS)
        self.received = False

    def feed(self, chunk: str) -> None:
        """Process the next chunk of remote output (any size, not line-aligned)."""
        if not chunk:
            return
        self.received = True
        if self._emit_raw is not None:
            self._feed_raw(chunk)
        self._pending += chunk
        segments = re.split(r"\r\n|\n|\r", self._pending)
        self._pending = segments.pop()
        for segment in segments:
            self._process(segment)
        if len(self._pending) > self.MAX_PENDING_CHARS or _BURST_RE.fullmatch(
            strip_terminal_escapes(self._pending).strip()
        ):
            self._process(self._pending)
            self._pending = ""

    def flush(self) -> None:
        """Process any trailing partial line; call once after the command returns."""
        if self._pending:
            self._process(self._pending)
            self._pending = ""
        if self._emit_raw is not None and self._raw_pending.strip():
            self._emit_raw(self._raw_pending.rstrip("\r"))
        self._raw_pending = ""

    def _feed_raw(self, chunk: str) -> None:
        assert self._emit_raw is not None
        self._raw_pending += chunk
        lines = self._raw_pending.split("\n")
        self._raw_pending = lines.pop()
        for line in lines:
            if line.strip():
                self._emit_raw(line.rstrip("\r"))

    def _process(self, segment: str) -> None:
        if _ALT_SCREEN_ON in segment:
            before, _, segment = segment.partition(_ALT_SCREEN_ON)
            self._process_text(before)
            self._in_live_view = True
        if self._in_live_view and _ALT_SCREEN_OFF in segment:
            frame, _, segment = segment.partition(_ALT_SCREEN_OFF)
            self._process_live(frame)
            self._in_live_view = False
        if self._in_live_view:
            self._process_live(segment)
        else:
            self._process_text(segment)

    @staticmethod
    def _is_frame_text(spaced: str) -> bool:
        return bool(_PHASE_RE.search(spaced) or "DoneMiB" in spaced or _TOTAL_RE.search(spaced))

    def _process_live(self, segment: str) -> None:
        """Inside the live view only redraw output is collapsed; plain text (an ssh drop, a HINT) is shown."""
        spaced = _ESCAPE_RE.sub(" ", segment)
        if _POSITION_RE.search(segment) or self._is_frame_text(spaced) or _ROW_RE.match(spaced):
            self._process_frame(segment)
        else:
            self._process_text(segment)

    def _process_text(self, segment: str) -> None:
        spaced = _ESCAPE_RE.sub(" ", segment)
        if self._is_frame_text(spaced):
            self._process_frame(segment)
            return
        text = strip_terminal_escapes(segment).rstrip()
        if not text.strip() or is_ssh_noise_line(text):
            return
        burst = _BURST_RE.search(text)
        if burst:
            self._process_text(text[: burst.start()])
            self._emit_line(f"Burst recovery wait: {burst.group(1)} elapsed, buffer fill {burst.group(2).strip()}")
            self._process_text(text[burst.end() :])
            return
        self._emit_line(text)

    def _process_frame(self, segment: str) -> None:
        spaced = _ESCAPE_RE.sub(" ", segment)
        phase = _PHASE_RE.search(spaced)
        if phase:
            if self._phase == phase.group(1) and not self._frame_had_total:
                self._maybe_emit_progress(f"{self._phase}: elapsed {phase.group(2)}")
            self._phase, self._elapsed = phase.group(1), phase.group(2)
            self._frame_had_total = False
        total = _TOTAL_RE.search(spaced)
        if total and self._phase:
            self._frame_had_total = True
            pct, _done_mib, mib_s = total.groups()
            self._maybe_emit_progress(f"{self._phase}: {pct}% done, {mib_s} MiB/s, elapsed {self._elapsed}")
        for piece in _POSITION_RE.split(segment):
            message = " ".join(_ESCAPE_RE.sub("", piece).split())
            if _ERROR_RE.search(message) and message not in self._recent_frame_errors:
                self._recent_frame_errors.append(message)
                self._emit_line(message)

    def _maybe_emit_progress(self, line: str) -> None:
        now = self._clock()
        new_phase = self._phase != self._last_progress_phase
        if new_phase or now - self._last_progress_at >= self.PROGRESS_INTERVAL_S:
            self._last_progress_phase = self._phase
            self._last_progress_at = now
            self._emit_line(line)
