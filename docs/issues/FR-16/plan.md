# FR-16 plan — live vperfsanity Step 4 output, responsive Output Results

Branch: `fix/FR-16-vperfsanity-output-stall` (off `develop` at `3090153`). Spec: [`spec.md`](spec.md).

## Evidence used

- Older lab op log on this machine (`logs/operations/oneshot_10_143_11_203_20260423_001402_*.jsonl`) has real
  elbencho frames, WRITE/READ result blocks and the werkzeug poll lines. The 2026-10-23 log is not local.
- `test_output/vperf_src/vperfsanity/vperfsanity_run.sh` (Sep 2026 copy): the burst wait prints
  `\rElapsed time at last status check: <m:ss> [Burst buffer fill: <pct>]` every 30 s, with a carriage
  return and no newline, and only when stdout is a TTY. So `force_tty` stays and the splitter must treat
  `\r` as a line end.

## Design

1. **SSH streaming (`src/utils/ssh_adapter.py`).** `run_ssh_command(..., on_output=None)`. When set, it is
   called with decoded text chunks (any size, not line-aligned) of remote stdout and stderr as they arrive,
   on both the `sshpass` subprocess path and the paramiko path (Windows, jump host / Tech Port, no
   `sshpass`). Return value, timeout (process-group kill), auth-retry and noise stripping are unchanged.
   Adapter-made messages (timeout notice, connection errors) are only in the returned `stderr`. Callback
   exceptions are swallowed.
2. **Output filter (`src/workflows/vperfsanity_output.py`, new).** `VperfsanityOutputFilter.feed(chunk)` /
   `flush()`. It splits on `\r\n`, `\n` and `\r`, drops elbencho live-view frames (inside the alternate
   screen `ESC[?1049h … ESC[?1049l`, plus `Phase:`/`DoneMiB` lines outside it), and emits one progress line
   per phase start and then at most every 15 s (`WRITE: 12% done, 10772 MiB/s, elapsed 1m10s`). It turns
   burst-wait updates into `Burst recovery wait: 1m:30s elapsed, buffer fill 45.2%` and emits them as soon
   as they arrive. Result blocks and everything else pass through with escapes stripped. Raw `\n` lines go
   to a separate raw sink unchanged.
3. **Workflow (`_step_run_tests`).** Stream through the filter. Visible lines go out through `emit` with
   today's level classification. Raw lines go out as tier `transcript`. If the adapter never called back
   (mocked or failed early), the returned output goes through the same filter after the call, so nothing is
   emitted twice. The part-limit retry gets a fresh filter, and the failure classification still uses the
   full returned output. On the streamed path, returned-stderr lines that never arrived in the stream (the
   adapter's timeout notice, paramiko connection errors) are emitted as errors, minus SSH banner noise.
   Inside the live view only redraw output (cursor positioning `H`/`f`/`d`/`G`, Phase/Total/DoneMiB,
   rank-table rows) is collapsed; plain text such as an ssh drop or a HINT is shown, including text after an
   erase code (`ESC[K`, `ESC[J`). Error text in a frame is split only at cursor moves, so colored errors stay
   whole, and is shown once per run while it stays among the last 32 distinct errors (bounded output when
   errors alternate across frames). An unterminated run is processed once it passes 64 KB. The "already
   streamed" check keeps only each raw line's text after its last escape (`visible_tail`), so frames add no
   memory, and it matches a stderr line that landed on the end of an unfinished stdout line.
4. **Transcript tier (`src/advanced_ops.py`, `src/oneshot_runner.py`, `src/app.py`).** `_emit_output` with
   `log_tier="transcript"` goes to `_transcript_buffer`, never to `_output_buffer`, so `/advanced-ops/output`
   indices and the browser are unaffected. `operation_log()` merges both buffers by timestamp and is used for
   the saved op log (`oneshot_*.jsonl`) and the bundle snapshot. Both buffers are cleared together. The
   step-by-step Advanced Ops path has no op-log writer, so there the transcript stays in memory only (cleared
   with the output on the next start or reset); saving it there is out of scope.
5. **werkzeug access lines.** `utils.logger.is_access_log_record` (logger `werkzeug`, level INFO or lower)
   is dropped by `SSELogHandler` (`/stream/logs`) and `_OneShotLogHandler` (output buffer). werkzeug
   warnings and errors still pass.
6. **Output pane (both templates).** `appendEntries(entries, opts)` uses one `DocumentFragment` and one
   scroll per batch, scheduled with `requestAnimationFrame`. The history is capped at `OUTPUT_MAX_ENTRIES`
   (5,000): the oldest DOM lines and entries are dropped, with one "older lines dropped" notice. Persisting
   is debounced (one `sessionStorage.setItem` per batch or per 500 ms), with a smaller retry on quota
   errors. `append()` becomes a one-entry batch. `_restore` renders through a fragment. All backend polls
   and `hydrateFromBackend` append through `appendEntries` with an in-flight guard, so overlapping
   intervals can't fetch the same range twice. The sync cursor advances only for backend entries, not for
   SSE or local messages.

## Partition (single writer per file)

| Owner | Files |
| --- | --- |
| Worker A (SSH streaming) | `src/utils/ssh_adapter.py`, `tests/test_ssh_streaming.py` (new) |
| Worker B (output pane) | `frontend/templates/reporter.html`, `frontend/templates/advanced_ops.html`, `tests/test_ui.py` |
| Parent | filter module, workflow, `advanced_ops.py`, `oneshot_runner.py`, `utils/logger.py`, `app.py`, their tests, docs |

## Tests

- Failing-first: Step 4 emits a line before the mocked remote command returns. The filter keeps the WRITE
  and READ result blocks from a fixture built from the lab log.
- Filter: frames collapsed and progress throttled; burst status emitted at once; `\r` handling; raw sink
  gets everything.
- Transcript tier excluded from `get_output`, included in `operation_log()` in order; access-log filter in
  both handlers.
- SSH streaming: callback fires before a local subprocess exits; timeout still kills; paramiko channel loop
  mocked.
- UI: 15,000 entries in one batch, at most one `setItem`, append time under budget, cap respected, hydration
  from a large backlog stays under the cap.
