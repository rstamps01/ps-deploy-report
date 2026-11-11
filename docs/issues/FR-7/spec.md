# FR-7 — vperfsanity background runner

**Type:** Enhancement · **Priority:** P1 · **Size:** M · **Target:** v1.6.3 · **Status:** Planned. Builds on
FR-16 (PR #49): `run_ssh_command(on_output=...)`, `VperfsanityOutputFilter`, transcript tier.

## Problem

Step 4 (`_step_run_tests`, `src/workflows/vperfsanity_workflow.py` L517–599) holds one SSH session for the
whole write, burst-recovery wait and read sequence (budget `RUN_TIMEOUT_S`, L62). A dropped SSH session or a
sleeping laptop ends the run. Cancel is checked only between steps (`advanced_ops.py` L426–427 and L528–529,
`oneshot_runner.cancel` L2338–2340), so it cannot stop a multi-hour Step 4. Every run uses the full dataset
(4,096 GiB per DBox).

## Change

1. **Detached run.** Step 4 starts the existing command (`./vperfsanity_run.sh -w -r <pool>` plus the part-limit
   retry `-n`) under `setsid nohup script -qfc "<cmd>" <log>` on the CNode, so it keeps a PTY (the burst-wait
   status prints only on a TTY) and survives SSH drops. It writes the PID/PGID and exit code to files in a
   `mktemp -d` run directory under `/tmp/vast_scripts/`.
2. **Polling.** Short SSH calls every `poll_s` (default 10 s) read the log from the last byte offset and feed
   `VperfsanityOutputFilter`, so FR-16's live output and transcript are unchanged. The loop ends when the
   exit-code file appears or the overall budget runs out. A failed poll is retried with backoff. Losing SSH
   does not stop the remote run.
3. **Heartbeat and stall detector.** A heartbeat line is emitted when nothing visible has been emitted for
   60 s: phase, elapsed time, and the last burst fill %. A stall warning comes when the log and the fill %
   have not changed for `stall_warn_s` (default 900 s). It is a warning only; the run is not killed.
4. **Cancel.** The poll loop checks the manager's cancel event. On Cancel it sends `kill -TERM -<pgid>`, and
   then `-KILL` after a 30 s grace period. Then the existing FR-3 cleanup runs (`-c` dataset cleanup when it
   is enabled). Advanced Ops and One-Shot both pass their cancel event to the workflow.
5. **Quick vs Full.** `vperfsanity_mode: full | quick`. Quick adds `-s <quick_dataset_gib>` (default 256 GiB per
   DBox, config `advanced_operations.vperfsanity.quick_dataset_gib`). Full is today's command. The report and
   the saved results record the mode, and Quick results are labelled "Quick run, not a performance sign-off".
6. **Reconnect.** If the app restarts while a run is still going, the run directory on the CNode lets Step 4
   re-attach instead of starting a second run.

## Acceptance

- Unit (mocked SSH): the detached start command contains `setsid`, `nohup`, `script` and the run directory;
  polling resumes from the byte offset; heartbeat and stall timing use a fake clock; Cancel sends the
  group kill and then runs cleanup; Quick adds `-s`; a lost poll is retried and does not fail the step.
- Existing FR-16 tests stay green (the filter sees the same text).
- Lab: a full multi-hour run with one forced SSH drop completes; Cancel during the burst wait stops the
  remote processes within 60 s and leaves no elbencho processes; a Quick run completes.
