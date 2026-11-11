# FR-10 — Paramiko SSH path has no overall deadline

**Type:** Bug · **Priority:** P2 · **Size:** S · **Target:** v1.6.3 · **Status:** Planned.

## Observed

On Windows (no `sshpass`) and on jump-host / Tech Port sessions, `run_ssh_command` uses paramiko. On the
non-streaming path, `stdout.channel.recv_exit_status()` (`src/utils/ssh_adapter.py` L1018) blocks with no
deadline. The `exec_command(timeout=...)` value is only a per-read idle timeout, so a remote command that keeps
the channel open hangs the step past its timeout.

## Change

The non-streaming paramiko path reuses `_stream_paramiko_channel` (L1036–1087) with a collecting no-op callback.
That function already enforces a hard deadline, closes the channel on expiry, keeps partial output and returns
`_timeout_stderr`. The return contract (`rc, stdout, stderr`) is unchanged.

## Acceptance

- Failing-first: a mocked channel whose `exit_status_ready()` never turns true returns within `timeout` plus
  one poll interval, with rc 1, the partial stdout, and the timeout notice in stderr (today it blocks).
- Normal completion, stderr capture, auth failure and connection errors behave as before; the existing paramiko
  mocks are reworked to the channel-polling interface.
