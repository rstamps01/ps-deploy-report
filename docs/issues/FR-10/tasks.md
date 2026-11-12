# FR-10 tasks — Paramiko SSH path has no overall deadline

- [x] Failing-first regression test: `TestParamikoNonStreamingDeadline` in `tests/test_ssh_streaming.py` (channel whose `exit_status_ready()` never turns true; blocked in `recv_exit_status()` before the fix).
- [x] Non-streaming `_paramiko_exec` path reuses `_stream_paramiko_channel` (hard deadline, channel closed on expiry, partial output, `_timeout_stderr`); `on_output` is optional.
- [x] Paramiko mocks reworked to the channel-polling interface in `tests/test_ssh_adapter.py`, `tests/test_ssh_streaming.py` and `tests/test_ssh_adapter_proxy.py`; stderr/exit-status capture test added.
- [x] Targeted SSH tests, `pytest -k ssh`, black and flake8 green.
- [x] Changelog fragment (`changelog.md`).
- [ ] Full quality gate (`scripts/quality-gate.sh`) — parent.
- [ ] PR to `develop` — parent.
