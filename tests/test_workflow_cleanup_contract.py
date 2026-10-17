"""Guaranteed workflow cleanup after failure or cancel (EBox field report, v1.6.1).

vperfsanity's Step 4 timed out and the one-shot runner broke out of the workflow,
so Step 7 (cleanup) never ran: ~53 TB of test data, the vperfsanity view/policy/user
and elbencho services were left on a customer cluster.  Workflows now declare
cleanup steps that the runners execute whenever infrastructure may exist.
"""

import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry, get_cleanup_plan  # noqa: E402

SEVEN_STEPS = [{"id": i, "name": f"Step {i}"} for i in range(1, 8)]


class _FakeVperf:
    """Minimal stand-in for a workflow that declares a cleanup plan."""

    name = "Fake vperfsanity"
    CLEANUP_STEPS = (7,)
    CLEANUP_REQUIRED_AFTER_STEP = 3

    def __init__(self, fail_at=None, cancel_event=None, cancel_after=None):
        self.calls = []
        self._fail_at = fail_at
        self._cancel_event = cancel_event
        self._cancel_after = cancel_after

    def get_steps(self):
        return SEVEN_STEPS

    def set_output_callback(self, cb):
        pass

    def set_credentials(self, creds):
        pass

    def run_step(self, step_id):
        self.calls.append(step_id)
        if self._cancel_event is not None and step_id == self._cancel_after:
            self._cancel_event.set()
        if step_id == self._fail_at:
            return {"success": False, "message": "SSH command timed out after 3600s"}
        return {"success": True, "message": "ok"}


class TestCleanupPlan:
    def test_vperfsanity_declares_cleanup_step(self):
        steps, required_after = get_cleanup_plan(WorkflowRegistry.get("vperfsanity"))
        assert 7 in steps
        assert required_after == 3

    def test_plain_mock_has_no_cleanup_plan(self):
        assert get_cleanup_plan(MagicMock()) == ((), 0)


def _runner(ops, cancel_event=None):
    from oneshot_runner import OneShotRunner

    return OneShotRunner(
        selected_ops=ops,
        credentials={
            "cluster_ip": "10.0.0.1",
            "username": "admin",
            "password": "pass",
            "node_user": "vastdata",
            "node_password": "pass",
        },
        include_report=False,
        cancel_event=cancel_event,
    )


class TestOneShotRunsCleanup:
    @patch("workflows.WorkflowRegistry")
    def test_cleanup_runs_after_step4_failure(self, MockWR):
        wf = _FakeVperf(fail_at=4)
        MockWR.get.return_value = wf
        runner = _runner(["vperfsanity"])
        runner._run_operations()
        assert wf.calls == [1, 2, 3, 4, 7]
        assert runner._state.operation_results["vperfsanity"] == "failed"

    @patch("workflows.WorkflowRegistry")
    def test_no_cleanup_when_failure_precedes_infrastructure(self, MockWR):
        wf = _FakeVperf(fail_at=1)
        MockWR.get.return_value = wf
        runner = _runner(["vperfsanity"])
        runner._run_operations()
        assert wf.calls == [1]

    @patch("workflows.WorkflowRegistry")
    def test_cleanup_not_duplicated_on_success(self, MockWR):
        wf = _FakeVperf()
        MockWR.get.return_value = wf
        runner = _runner(["vperfsanity"])
        runner._run_operations()
        assert wf.calls == [1, 2, 3, 4, 5, 6, 7]

    @patch("workflows.WorkflowRegistry")
    def test_cleanup_runs_when_cancelled_mid_workflow(self, MockWR):
        from oneshot_runner import _OneShotCancelled

        cancel = threading.Event()
        wf = _FakeVperf(cancel_event=cancel, cancel_after=4)
        MockWR.get.return_value = wf
        runner = _runner(["vperfsanity"], cancel_event=cancel)
        try:
            runner._run_operations()
        except _OneShotCancelled:
            pass
        assert wf.calls == [1, 2, 3, 4, 7]


class TestAdvancedOpsRunsCleanup:
    def _manager_with(self, wf):
        from advanced_ops import AdvancedOpsManager

        manager = AdvancedOpsManager()
        manager._workflows["fake"] = {
            "id": "fake",
            "name": wf.name,
            "description": "fake",
            "steps": wf.get_steps(),
            "enabled": True,
            "_instance": wf,
        }
        assert manager.start_workflow("fake", {}) is True
        return manager

    def test_run_all_failure_runs_cleanup(self):
        wf = _FakeVperf(fail_at=4)
        manager = self._manager_with(wf)
        assert manager.run_all_steps({}) is False
        assert wf.calls == [1, 2, 3, 4, 7]

    def test_run_all_cancel_runs_cleanup(self):
        wf = _FakeVperf(cancel_event=None)
        manager = self._manager_with(wf)
        wf._cancel_event = manager._cancel_event
        wf._cancel_after = 4
        manager.run_all_steps({})
        assert wf.calls == [1, 2, 3, 4, 7]

    def test_cancel_landing_before_last_step_still_cleans_up(self):
        """If run_step skips the final (cleanup) step because cancel was set, cleanup must still run."""
        wf = _FakeVperf(cancel_event=None)
        manager = self._manager_with(wf)
        wf._cancel_event = manager._cancel_event
        original_run_step = manager.run_step

        def run_step_setting_cancel(step_id, credentials):
            if step_id == 7:
                manager._cancel_event.set()
            return original_run_step(step_id, credentials)

        manager.run_step = run_step_setting_cancel
        manager.run_all_steps({})
        assert wf.calls.count(7) == 1
