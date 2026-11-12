# FR-11 tasks

- [x] T1 Failing-first: after a mocked verified download, assert `sudo rm -f -- <exact path>` is sent (log bundle and Support Tools); confirmed failing before the fix
- [x] T2 Log bundle: `_cleanup_remote_archive` called at the end of a passing `_step_verify_contents`; failure messages in Steps 4 and 5 give the kept archive's location
- [x] T3 Support Tools: `_step_download_results` compares local size with remote `stat -c %s`; a mismatch fails the step and keeps the archive; `_cleanup_remote_archive` runs only after a size match (an unreadable remote size skips cleanup with a warning)
- [x] T4 Exact-path guard (`REMOTE_ARCHIVE_RE` per workflow, `shlex.quote`), `remote_cleanup: removed | failed | skipped` in the step result, warnings and success lines in Output Results
- [x] T5 Tests in `tests/test_log_bundle_support_tool_cleanup.py` (no removal on failed download or verification, refused path, cleanup failure, Tech Port jump routing); existing download tests patch `run_ssh_command`
- [x] T6 Targeted tests, black, flake8, mypy on changed files; changelog fragment
- [ ] T7 `quality-gate` and review (parent)
- [ ] T8 Lab check on a cluster: confirm both archives are removed after a full run (owner; needs cluster access)
