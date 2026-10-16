"""vperfsanity runtime budget (EBox field report, v1.6.1).

vperfsanity_run.sh waits up to BURST_WAIT_TIMEOUT_S=7200 for the write buffer to
drain between the write and read phases.  v1.6.1 gave the whole -w -r run 3600s,
so the SSH session was killed during that wait and reads never started.

On large clusters the script's default of one object per thread can exceed the
S3 limit of 10,000 parts per object; it refuses and prints the minimum object
count instead of raising ``-n`` itself.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry  # noqa: E402

SCRIPT_BURST_WAIT_S = 7200


def _workflow(**creds):
    wf = WorkflowRegistry.get("vperfsanity")
    base = {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
    base.update(creds)
    wf.set_credentials(base)
    wf._script_runner = MagicMock()
    wf._step_data = {"vperf_dir": "/tmp/vast_scripts/vperfsanity", "vip_pool": "pool0"}
    return wf


class TestRunTestsTimeoutBudget:
    @patch("workflows.vperfsanity_workflow.run_ssh_command", return_value=(0, "done", ""))
    def test_budget_covers_script_burst_wait(self, mock_ssh):
        _workflow()._step_run_tests()
        timeout = mock_ssh.call_args.kwargs["timeout"]
        assert timeout > SCRIPT_BURST_WAIT_S + 3600

    @patch("workflows.vperfsanity_workflow.run_ssh_command", return_value=(0, "done", ""))
    def test_budget_is_overridable(self, mock_ssh):
        _workflow(vperfsanity_timeout_s=5400)._step_run_tests()
        assert mock_ssh.call_args.kwargs["timeout"] == 5400

    @patch("workflows.vperfsanity_workflow.run_ssh_command")
    def test_timeout_message_names_burst_wait(self, mock_ssh):
        mock_ssh.return_value = (
            1,
            "Waiting for burst / post-burst phase to finish...\n",
            "SSH command timed out after 14400s",
        )
        result = _workflow()._step_run_tests()
        assert result["success"] is False
        assert "burst" in result["message"].lower()


PART_LIMIT_REFUSAL = (
    "Collecting information about the cluster to start run...\r\n"
    "Restarting elbencho service...\r\n"
    "DBoxes: 43 | Files: 512 | Filesize: 344G | Size total: 172T\r\n"
    "ERROR: This configuration would exceed the S3 limit of 10,000 parts per file.\r\n"
    "HINT: Consider increasing the number of objects to: 1128\r\n"
    "Connection to 127.0.0.1 closed.\r\n"
)


class TestS3PartLimitObjectCount:
    """43-EBox field report (v1.6.2): one object per thread overflowed the S3 10,000-part limit."""

    def test_rounds_hint_up_to_whole_objects_per_thread(self):
        wf = WorkflowRegistry.get("vperfsanity")
        assert wf._object_count_for_part_limit(PART_LIMIT_REFUSAL) == 1536

    def test_uses_hint_when_default_file_count_missing(self):
        wf = WorkflowRegistry.get("vperfsanity")
        output = "ERROR: This configuration would exceed the S3 limit of 10,000 parts per file.\n" + (
            "HINT: Consider increasing the number of objects to: 1128\n"
        )
        assert wf._object_count_for_part_limit(output) == 1128

    def test_none_for_unrelated_failure(self):
        wf = WorkflowRegistry.get("vperfsanity")
        assert wf._object_count_for_part_limit("ERROR: Failed to retrieve CNodes from VMS.") is None

    @patch("workflows.vperfsanity_workflow.run_ssh_command")
    def test_reruns_with_object_count_after_part_limit_refusal(self, mock_ssh):
        mock_ssh.side_effect = [(1, PART_LIMIT_REFUSAL, ""), (0, "done", "")]
        result = _workflow()._step_run_tests()

        assert result["success"] is True
        assert mock_ssh.call_count == 2
        first_cmd = mock_ssh.call_args_list[0].args[3]
        retry_cmd = mock_ssh.call_args_list[1].args[3]
        assert " -n " not in first_cmd
        assert "./vperfsanity_run.sh -w -r -n 1536 pool0" in retry_cmd

    @patch("workflows.vperfsanity_workflow.run_ssh_command")
    def test_reruns_only_once(self, mock_ssh):
        mock_ssh.side_effect = [(1, PART_LIMIT_REFUSAL, ""), (1, PART_LIMIT_REFUSAL, "")]
        result = _workflow()._step_run_tests()

        assert result["success"] is False
        assert mock_ssh.call_count == 2

    @patch("workflows.vperfsanity_workflow.run_ssh_command", return_value=(1, "ERROR: boom", ""))
    def test_no_rerun_for_other_failures(self, mock_ssh):
        result = _workflow()._step_run_tests()

        assert result["success"] is False
        assert mock_ssh.call_count == 1


class TestPrevalidationDurationNotice:
    def test_notice_does_not_promise_thirty_minutes(self):
        from oneshot_runner import VPERFSANITY_DURATION_NOTICE

        assert "30 minutes" not in VPERFSANITY_DURATION_NOTICE
        assert "hour" in VPERFSANITY_DURATION_NOTICE
        assert "clean" in VPERFSANITY_DURATION_NOTICE.lower()
