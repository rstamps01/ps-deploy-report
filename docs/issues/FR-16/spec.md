# FR-16 — vperfsanity output stalls, then a flood of output freezes Chrome

**Type:** Bug · **Priority:** P0 (release blocker) · **Target:** v1.6.3, fixed before the release is cut · **Status:** Planned (logged 2026-10-23; work not started)

## Observed

- During a Test Suite vperfsanity run, Output Results goes quiet after "Please wait..." for the whole
  of Step 4 (write, burst-recovery wait, read). Engineers read this as the test stalling between phases.
- When Step 4 finishes, the whole run's output appears at once and the page stops responding while it
  renders. A field engineer's Chrome tab hung outright (field logs requested 2026-10-23).
- Lab evidence (3-CNode, 1-DBox cluster, 2026-10-23, ops log
  `oneshot_10_143_11_203_20261023_100632_20261023_094600.jsonl`, 13,659 entries):
  - Cluster timeline: write 2m57s, burst-recovery wait 13m27s, read 2m10s; Step 4 total 18m43s.
  - Output Results showed nothing from 16:46:40 to 17:05:22 (UTC), then received about 12,400 lines.
  - The browser took until 17:06:51 to add them, about 90 seconds with the page frozen, for a run that
    had already finished.
  - About 1,500 of the captured frames are elbencho's full-screen progress display (2.2 MB of output).
  - About 2,500 lines are web-server access lines for the page's own status polls, each shown twice.

## Expected

- Output Results shows Step 4 progress while it runs, including the burst-recovery wait.
- The page stays responsive for runs of any length (up to the 4-hour Step 4 budget on large clusters).
- Opening the page in a new tab during or after a long run does not freeze it.

## Root cause (from code reading and the lab log)

1. **No live output from Step 4.** `VperfsanityWorkflow._step_run_tests`
   (`src/workflows/vperfsanity_workflow.py`) calls `run_ssh_command(...)`, which blocks until
   `vperfsanity_run.sh` exits, then `_emit_run_output` emits every captured line at once.
2. **Elbencho screen redraws are captured.** `force_tty=True` makes elbencho run its full-screen live
   view, so every refresh frame becomes output lines.
3. **Quadratic work per output line in the browser.** `OutputPaneCtor.prototype.append` calls
   `_persist()`, which writes `JSON.stringify(this.entries)` (the whole history) to `sessionStorage`, then
   forces a layout with `scrollTop = scrollHeight`, for every line. A batch of N lines costs roughly
   N × (history size). Same code in `frontend/templates/reporter.html` and
   `frontend/templates/advanced_ops.html`. Past Chrome's ~5 MB `sessionStorage` quota, `setItem` throws
   (swallowed) but the serialization is still paid on every line.
4. **Poll noise feeds back into the panel.** The reporter page's ambient `/stream/logs` EventSource
   forwards werkzeug access log lines for its own `/advanced-ops/oneshot/status` and
   `/advanced-ops/output` polls, so the history grows continuously during long runs.
5. **A new tab replays everything.** `hydrateFromBackend` fetches `/advanced-ops/output?since=0` in a
   fresh tab (empty `sessionStorage`) and appends it through the same per-line path.

The 13m27s gap between write and read is `vperfsanity_run.sh` waiting for burst recovery so read
results are valid. That wait is by design and is not part of this bug; only how it is displayed is.

## Why

vperfsanity is the longest Test Suite operation (1–4 hours on large clusters). A silent UI looks like a
hang, and a frozen tab leads engineers to quit the app mid-test, which aborts the run and triggers
cleanup.

## Capabilities

- Step 4 streams `vperfsanity_run.sh` output to Output Results as it arrives (line callback on the SSH
  path), keeping the existing timeout, failure classification and part-limit retry.
- Elbencho redraw frames are collapsed: keep the phase result blocks and emit a periodic one-line progress
  summary (phase, % done, MiB/s) instead of every frame.
- The burst-recovery wait emits a periodic status line (elapsed time, buffer fill %).
- Output pane (both templates): persist once per batch (debounced), add lines with one DOM fragment and
  one scroll per batch, and cap the in-memory and persisted history (oldest lines dropped, with a notice).
- werkzeug access lines are not forwarded to Output Results via `/stream/logs`.
- Fresh-tab hydration appends through the batched path and respects the cap.
- Overlapping polls cannot fetch and append the same output range twice.

## Constraints

- The full, unfiltered Step 4 output still goes to the operation log (`oneshot_*.jsonl`) and bundle, so
  diagnostics keep the raw transcript.
- No change to `vperfsanity_run.sh` behavior, the 4-hour budget (FR-2), or the cleanup contract (FR-3).
- Works on the subprocess (`sshpass`) and paramiko SSH paths, including Teleport and Tech Port.
- Credential sanitization of streamed lines is unchanged.

## Non-goals

- The detached background runner with heartbeat and stall detection (FR-7). FR-16 is the minimum fix
  for the release and must not wait on FR-7.
- Skipping or shortening the burst-recovery wait.
- The general run recorder (HUB-2).

## Acceptance criteria

- GIVEN a Step 4 run that produces output over time WHEN it is running THEN lines appear in Output
  Results within a few seconds of being produced, not only after the script exits.
- GIVEN elbencho full-screen output WHEN it is emitted to Output Results THEN redraw frames are collapsed
  to periodic progress lines and the WRITE/READ result blocks are kept intact.
- GIVEN 15,000 entries arriving in one poll WHEN the output pane appends them THEN `sessionStorage` is
  written at most once for the batch and the page stays responsive (pinned by a UI test that measures
  append time for a large batch).
- GIVEN a history larger than the cap WHEN more lines arrive THEN the oldest lines are dropped and the
  persisted history stays under the cap.
- GIVEN the reporter page is open during a run WHEN it polls status and output THEN no werkzeug access
  lines appear in Output Results.
- GIVEN a long run in progress WHEN the reporter page is opened in a new tab THEN it hydrates without
  freezing.
- Failing-first regression tests: a unit test that Step 4 emits output before the remote command
  returns, and a unit test that the elbencho frame filter keeps the result blocks. Both fail on today's code.
- Lab re-run on a cluster with a full vperfsanity Step 4: no gap in Output Results, no browser freeze,
  results unchanged.

## Success signal

Field engineers see vperfsanity progress throughout the run, including the burst-recovery wait, and no
further Chrome hangs are reported on Test Suite runs.
