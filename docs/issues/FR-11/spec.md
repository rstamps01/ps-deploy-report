# FR-11 — Remote archives left on the cluster

**Type:** Bug (hygiene) · **Priority:** P3 · **Size:** S · **Target:** v1.6.3 · **Status:** Planned.

## Observed

After download, `/tmp/vast_log_bundle_<ts>.tar.gz` stays on the CNode (`src/workflows/log_bundle_workflow.py`
L237–240) and `/userdata/<host>-support_tool_logs_<ts>.tgz` stays on the VMS host
(`src/workflows/support_tool_workflow.py` L642–644). These are often several GB on customer systems.

## Change

- Remove the remote archive only after a verified download. For the log bundle, that is after
  `_step_verify_contents` passes. For Support Tools, it is after `_step_download_results` confirms the local
  size matches the remote size.
- Delete the exact recorded path with `rm -f -- <path>`, never a glob. The path must match the workflow's own
  name pattern (`^/tmp/vast_log_bundle_\d{8}_\d{6}\.tar\.gz$`, `^/userdata/[\w.-]+-support_tool_logs_\d{8}_\d{6}\.tgz$`),
  and any other path is refused.
- If the cleanup fails, the step warns and still succeeds. The step result records `remote_cleanup: removed |
  failed | skipped`, and the output pane shows it.
- If verification fails, the archive is kept and the message says where it is.

## Acceptance

- Failing-first: after a mocked verified download, an `rm -f -- <exact path>` command is sent (today none is).
- No removal when the download or verification fails; a non-matching path is refused; a cleanup failure gives a
  warning, not a failed step.
