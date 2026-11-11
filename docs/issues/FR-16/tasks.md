# FR-16 tasks

- [x] T1 SSH adapter `on_output` streaming, subprocess and paramiko paths (worker A)
- [x] T2 `VperfsanityOutputFilter` (frame collapse, progress throttle, burst status, raw sink) and tests
- [x] T3 `_step_run_tests` streams through the filter; failing-first regression tests
- [x] T4 `transcript` tier: manager buffer, `operation_log()`, op log and bundle snapshot, clears
- [x] T5 Drop werkzeug access lines from `/stream/logs` and the one-shot log handler
- [x] T6 Output pane batching, cap, debounced persist, poll in-flight guard, hydration (worker B)
- [x] T7 Independent review (three reviewers; all findings from the reviews and re-reviews applied), targeted tests, changelog fragment, `quality-gate`
- [ ] T8 Lab re-run on a cluster with a full Step 4 (owner; needs cluster access)
