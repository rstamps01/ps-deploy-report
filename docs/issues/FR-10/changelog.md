### Fixed

- SSH commands run through paramiko (Windows, jump-host and Tech Port sessions) now stop at their timeout instead of hanging when the remote command keeps the connection open (FR-10).
- When such a command times out, the output captured so far is kept and the step reports "SSH command timed out after Ns", matching the macOS/Linux behavior.
