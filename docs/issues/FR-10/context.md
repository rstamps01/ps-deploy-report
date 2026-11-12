# Context pack: FR-10

Terms: `run_ssh_command`, `_stream_paramiko_channel`, `recv_exit_status`

## `run_ssh_command` (287 hits)
- `scripts/context-pack.py` L13
- `src/external_port_mapper.py` L30
- `src/external_port_mapper.py` `ExternalPortMapper._detect_switch_os` L392-557
- `src/external_port_mapper.py` `ExternalPortMapper._collect_hostname_to_ip_mapping` L1090-1165
- `src/external_port_mapper.py` `ExternalPortMapper._collect_node_macs_via_clush` L1167-1238
- `src/external_port_mapper.py` `ExternalPortMapper._collect_switch_mac_tables` L1307-1447
- `src/external_port_mapper.py` `ExternalPortMapper._collect_ipl_connections` L1547-1676
- `src/health_checker.py` L22

## `_stream_paramiko_channel` (2 hits)
- `src/utils/ssh_adapter.py` `_paramiko_exec` L893-1033
- `src/utils/ssh_adapter.py` `_stream_paramiko_channel` L1036-1087

## `recv_exit_status` (8 hits)
- `src/utils/ssh_adapter.py` `_paramiko_exec` L893-1033
- `src/utils/ssh_adapter.py` `_stream_paramiko_channel` L1036-1087
- `tests/test_ssh_adapter.py` `TestParamikoExec.test_successful_command` L216-238
- `tests/test_ssh_adapter.py` `TestExplicitPort.test_paramiko_connects_to_explicit_port` L313-334
- `tests/test_ssh_adapter.py` `TestPexpectFallback.test_falls_back_to_paramiko_when_pexpect_missing` L384-416
- `tests/test_ssh_adapter_proxy.py` `_setup_successful_exec` L28-35
- `tests/test_ssh_streaming.py` `_FakeChannel.recv_exit_status` L246-247
- `tests/test_ssh_streaming.py` `TestParamikoStreaming.test_paramiko_exec_without_callback_reads_at_end` L340-357

## Files by relevance
- `src/workflows/support_tool_workflow.py` (15 hits)
- `src/workflows/vperfsanity_workflow.py` (14 hits)
- `src/session_manager.py` (9 hits)
- `src/utils/ssh_adapter.py` (9 hits)
- `src/external_port_mapper.py` (7 hits)
- `src/script_runner.py` (7 hits)
- `src/workflows/network_config_workflow.py` (7 hits)
- `src/oneshot_runner.py` (6 hits)
- `src/tool_manager.py` (6 hits)
- `src/utils/switch_ssh_probe.py` (6 hits)

## Tests to run
`python3 -m pytest tests/test_clustershell_groups.py tests/test_external_port_mapper.py tests/test_health_checker.py tests/test_oneshot_runner.py tests/test_script_runner.py tests/test_ssh_adapter.py tests/test_ssh_adapter_proxy.py tests/test_ssh_auth_rejection.py -x --lf`

## Recent commits on these files
- be4412a 2026-11-10 fix(web): stream vperfsanity Step 4 output and keep Output Results responsive (FR-16)
- b672773 2026-10-16 fix(report): mask credentials in saved ops logs; flag empty /vast/log copies
- 39648ac 2026-10-16 fix(report): mask credentials in the bundled operation log; review follow-ups
- 4c80a0e 2026-10-16 fix(report): health summary total, retire legacy table layout, FR-12, GOV-1 redaction list
- dc7ee14 2026-10-15 fix(report): v1.6.2 field-feedback fixes, wrapped report tables and grouped health details
- e48e581 2026-07-31 feat(release): v1.6.0 development baseline — Teleport tsh discovery + Settings UI, teleport-mode SSH routing, Onyx fixes, cross-cluster vnetmap segmentation
