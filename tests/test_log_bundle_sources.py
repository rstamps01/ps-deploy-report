"""VMS log bundle sources (EBox field report, v1.6.1).

The bundle copied /var/log/vast and /var/log/syslog, which do not exist on 5.x
RHEL CNodes, with ``|| true`` hiding the failure; the "OK" bundle held only
/var/log/messages.  Step 3 now records each source, adds recent /vast/log files
(bounded by age and size), and reports a partial collection honestly.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry  # noqa: E402


def _result(success=True, stdout=""):
    return MagicMock(success=success, stdout=stdout, stderr="")


MB = 1048576


class _FakeRunner:
    """Answers execute_remote by command shape so tests don't depend on call order."""

    def __init__(self, existing, recent_bytes, staged_files=25):
        self.existing = set(existing)
        self.recent_bytes = recent_bytes
        self.staged_files = staged_files
        self.commands = []

    def execute_remote(self, host, user, password, cmd, timeout=60):
        self.commands.append(cmd)
        if cmd.startswith("test -e "):
            path = cmd.split()[2]
            return _result(stdout="COPIED" if path in self.existing else "MISSING")
        if "-printf" in cmd:
            return _result(stdout=str(self.recent_bytes))
        if "cp --parents" in cmd:
            return _result(stdout=f"{self.staged_files}\n")
        return _result(stdout="12M")


def _workflow(runner):
    wf = WorkflowRegistry.get("log_bundle")
    wf.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pw"})
    wf._script_runner = runner
    wf._step_data = {"collection_confirmed": True}
    return wf


class TestLogBundleSources:
    def test_missing_legacy_dirs_are_reported_and_vast_log_added(self):
        runner = _FakeRunner(existing={"/var/log/messages"}, recent_bytes=300 * MB)
        wf = _workflow(runner)
        result = wf._step_create_archive()
        assert result["success"] is True
        sources = wf._step_data["log_sources"]
        assert sources["/var/log/messages"] == "copied"
        assert sources["/var/log/vast"] == "missing"
        assert sources["/vast/log"] == "copied"
        assert any("/vast/log" in c and "cp --parents" in c for c in runner.commands)
        assert "partial" in result["message"].lower()

    def test_oversized_recent_vast_logs_are_skipped_not_copied(self):
        runner = _FakeRunner(existing={"/var/log/messages"}, recent_bytes=999999 * MB)
        wf = _workflow(runner)
        wf._step_create_archive()
        assert wf._step_data["log_sources"]["/vast/log"] == "skipped_too_large"
        assert not any("cp --parents" in c for c in runner.commands)

    def test_complete_collection_is_not_flagged_partial(self):
        runner = _FakeRunner(existing={"/var/log/vast", "/var/log/messages", "/var/log/syslog"}, recent_bytes=10 * MB)
        wf = _workflow(runner)
        result = wf._step_create_archive()
        assert "partial" not in result["message"].lower()

    def test_small_recent_logs_under_one_mb_are_still_copied(self):
        runner = _FakeRunner(existing={"/var/log/messages"}, recent_bytes=800_000)
        wf = _workflow(runner)
        wf._step_create_archive()
        assert wf._step_data["log_sources"]["/vast/log"] == "copied"

    def test_staging_dir_is_reset_before_and_removed_after(self):
        runner = _FakeRunner(existing={"/var/log/messages"}, recent_bytes=MB)
        wf = _workflow(runner)
        wf._step_create_archive()
        bundle_dir = wf.BUNDLE_DIR
        first_cmd = runner.commands[0]
        assert f"rm -rf {bundle_dir}" in first_cmd and f"mkdir -p {bundle_dir}" in first_cmd
        tar_idx = next(i for i, c in enumerate(runner.commands) if "tar -czf" in c)
        assert any(f"rm -rf {bundle_dir}" in c for c in runner.commands[tar_idx + 1 :])

    def test_recent_log_copy_that_stages_nothing_is_reported_partial(self):
        runner = _FakeRunner(
            existing={"/var/log/vast", "/var/log/messages", "/var/log/syslog"}, recent_bytes=10 * MB, staged_files=0
        )
        wf = _workflow(runner)
        result = wf._step_create_archive()
        assert wf._step_data["log_sources"]["/vast/log"] == "copy_failed"
        assert "partial" in result["message"].lower()

    def test_recent_logs_respect_overall_bundle_limit(self):
        runner = _FakeRunner(existing={"/var/log/messages"}, recent_bytes=1500 * MB)
        wf = _workflow(runner)
        wf._step_data["total_size_mb"] = 4000
        wf._step_create_archive()
        assert wf._step_data["log_sources"]["/vast/log"] == "skipped_too_large"
