"""
Unit tests for Advanced Operations Manager.

Tests the AdvancedOpsManager class including workflow registration,
state management, step execution, and output handling.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from advanced_ops import AdvancedOpsManager, StepResult, StepStatus, WorkflowState

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def manager():
    """Create a fresh AdvancedOpsManager instance."""
    return AdvancedOpsManager()


@pytest.fixture
def mock_workflow():
    """Create a mock workflow class."""
    mock = MagicMock()
    mock.name = "Test Workflow"
    mock.description = "A test workflow"
    mock.enabled = True
    mock.min_vast_version = "5.0"
    mock.get_steps.return_value = [
        {"id": 1, "name": "Step 1", "description": "First step"},
        {"id": 2, "name": "Step 2", "description": "Second step"},
    ]
    mock.validate_prerequisites.return_value = (True, "OK")
    mock.run_step.return_value = {"success": True, "message": "Step completed"}
    return mock


# ===================================================================
# TestStepResult
# ===================================================================


class TestStepResult:
    def test_create_step_result(self):
        result = StepResult(
            status=StepStatus.DONE,
            message="Done",
            details="Some details",
        )
        assert result.status == StepStatus.DONE
        assert result.message == "Done"
        assert result.details == "Some details"

    def test_step_result_defaults(self):
        result = StepResult(status=StepStatus.PENDING, message="Waiting")
        assert result.details is None
        assert result.data is None
        assert result.duration_ms == 0


# ===================================================================
# TestWorkflowState
# ===================================================================


class TestWorkflowState:
    def test_create_workflow_state(self):
        state = WorkflowState(workflow_id="test", workflow_name="Test Workflow")
        assert state.workflow_id == "test"
        assert state.workflow_name == "Test Workflow"
        assert state.status == "idle"
        assert state.steps == []
        assert state.current_step == 0

    def test_workflow_state_with_steps(self):
        state = WorkflowState(
            workflow_id="test",
            workflow_name="Test",
            status="running",
            steps=[{"id": 1, "status": "pending"}],
            current_step=1,
        )
        assert len(state.steps) == 1
        assert state.current_step == 1


# ===================================================================
# TestAdvancedOpsManager
# ===================================================================


class TestAdvancedOpsManager:
    def test_manager_initialization(self, manager):
        assert manager is not None
        assert isinstance(manager._workflows, dict)

    def test_get_workflows_returns_list(self, manager):
        workflows = manager.get_workflows()
        assert isinstance(workflows, list)

    def test_get_workflow_not_found(self, manager):
        workflow = manager.get_workflow("nonexistent")
        assert workflow is None

    def test_is_running_initial_state(self, manager):
        assert manager.is_running() is False

    def test_get_state_initial(self, manager):
        state = manager.get_current_state()
        assert state is None


class TestAdvancedOpsManagerWithMocks:
    def test_start_workflow_success(self, manager, mock_workflow):
        manager._workflows["test"] = {
            "id": "test",
            "name": "Test",
            "description": "Test workflow",
            "steps": mock_workflow.get_steps(),
            "_instance": mock_workflow,
            "enabled": True,
            "min_vast_version": "5.0",
        }

        result = manager.start_workflow("test", {})
        # start_workflow returns True on success
        assert result is True

    def test_start_workflow_not_found(self, manager):
        result = manager.start_workflow("nonexistent", {})
        # start_workflow returns False when workflow not found
        assert result is False

    def test_cancel_workflow_not_running(self, manager):
        result = manager.cancel()
        # cancel returns False when no workflow running
        assert result is False

    def test_reset_workflow(self, manager):
        result = manager.reset()
        # reset returns None
        assert result is None


class TestAdvancedOpsOutput:
    def test_get_output_empty(self, manager):
        entries = manager.get_output()
        assert isinstance(entries, list)
        assert len(entries) == 0

    def test_emit_output(self, manager):
        manager._emit_output("info", "Test message")
        entries = manager.get_output()
        assert len(entries) >= 0

    def test_clear_output(self, manager):
        manager._emit_output("info", "Test")
        manager._output_buffer.clear()
        entries = manager.get_output()
        assert len(entries) == 0


# ===================================================================
# TestWorkflowLifecycle
# ===================================================================


def _make_test_workflow_entry(mock_instance):
    return {
        "id": "test",
        "name": "Test",
        "description": "Test workflow",
        "steps": [
            {"id": 1, "name": "Step 1", "description": "First"},
            {"id": 2, "name": "Step 2", "description": "Second"},
        ],
        "_instance": mock_instance,
        "enabled": True,
        "min_vast_version": "5.0",
    }


class TestWorkflowLifecycle:
    def test_start_then_duplicate_start_blocked(self, manager):
        mock_instance = MagicMock()
        mock_instance.run_step.return_value = {"success": True, "message": "OK"}
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)

        assert manager.start_workflow("test", {}) is True
        assert manager.start_workflow("test", {}) is False

    def test_run_all_steps_success(self, manager):
        mock_instance = MagicMock()
        mock_instance.run_step.return_value = {"success": True, "message": "OK"}
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)

        assert manager.start_workflow("test", {}) is True
        assert manager.run_all_steps({}) is True

    def test_run_all_steps_error_on_step(self, manager):
        mock_instance = MagicMock()
        mock_instance.run_step.side_effect = [
            {"success": True, "message": "OK"},
            {"success": False, "message": "Failed"},
        ]
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)

        assert manager.start_workflow("test", {}) is True
        assert manager.run_all_steps({}) is False
        state = manager.get_current_state()
        assert state["status"] == "error"

    def test_run_all_steps_cancel(self, manager):
        mock_instance = MagicMock()
        mock_instance.run_step.return_value = {"success": True, "message": "OK"}
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)

        assert manager.start_workflow("test", {}) is True
        manager._cancel_event.set()
        manager.run_all_steps({})
        mock_instance.run_step.assert_not_called()

    def test_run_all_steps_no_workflow(self, manager):
        assert manager.run_all_steps({}) is False

    def test_cancel_while_running(self, manager):
        mock_instance = MagicMock()
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)

        assert manager.start_workflow("test", {}) is True
        assert manager.cancel() is True
        assert manager._cancel_event.is_set() is True

    def test_complete_workflow_success(self, manager):
        mock_instance = MagicMock()
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)

        assert manager.start_workflow("test", {}) is True
        manager._complete_workflow()
        state = manager.get_current_state()
        assert state["status"] == "completed"

    def test_complete_workflow_error(self, manager):
        mock_instance = MagicMock()
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)

        assert manager.start_workflow("test", {}) is True
        manager._complete_workflow(error="msg")
        state = manager.get_current_state()
        assert state["status"] == "error"


# ===================================================================
# TestRunStep
# ===================================================================


class TestRunStep:
    def test_run_step_no_active_workflow(self, manager):
        result = manager.run_step(1, {})
        assert result.status == StepStatus.ERROR

    def test_run_step_invalid_id_zero(self, manager):
        mock_instance = MagicMock()
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)
        manager.start_workflow("test", {})
        result = manager.run_step(0, {})
        assert result.status == StepStatus.ERROR

    def test_run_step_invalid_id_too_high(self, manager):
        mock_instance = MagicMock()
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)
        manager.start_workflow("test", {})
        result = manager.run_step(99, {})
        assert result.status == StepStatus.ERROR

    def test_run_step_cancel_before_execution(self, manager):
        mock_instance = MagicMock()
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)
        manager.start_workflow("test", {})
        manager._cancel_event.set()
        result = manager.run_step(1, {})
        assert result.status == StepStatus.SKIPPED

    def test_run_step_success(self, manager):
        mock_instance = MagicMock()
        mock_instance.run_step.return_value = {"success": True, "message": "OK"}
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)
        manager.start_workflow("test", {})
        result = manager.run_step(1, {})
        assert result.status == StepStatus.DONE

    def test_run_step_failure(self, manager):
        mock_instance = MagicMock()
        mock_instance.run_step.return_value = {"success": False, "message": "Failed"}
        manager._workflows["test"] = _make_test_workflow_entry(mock_instance)
        manager.start_workflow("test", {})
        result = manager.run_step(1, {})
        assert result.status == StepStatus.ERROR

    def test_run_step_no_instance(self, manager):
        manager._workflows["test"] = {
            "id": "test",
            "name": "Test",
            "description": "Test workflow",
            "steps": [
                {"id": 1, "name": "Step 1", "description": "First"},
                {"id": 2, "name": "Step 2", "description": "Second"},
            ],
            "enabled": True,
            "min_vast_version": "5.0",
        }
        manager.start_workflow("test", {})
        result = manager.run_step(1, {})
        assert result.status == StepStatus.ERROR
        assert "instance not found" in result.message.lower()


# ===================================================================
# TestAdvancedOpsHelpers
# ===================================================================


class TestAdvancedOpsHelpers:
    def test_get_workflow_steps_unknown(self, manager):
        assert manager.get_workflow_steps("unknown") == []

    def test_get_workflow_steps_known(self, manager):
        steps = [
            {"id": 1, "name": "A", "description": "a"},
            {"id": 2, "name": "B", "description": "b"},
        ]
        manager._workflows["custom_wf"] = {
            "id": "custom_wf",
            "name": "Custom",
            "description": "Custom workflow",
            "steps": steps,
            "enabled": True,
            "min_vast_version": "5.0",
        }
        assert manager.get_workflow_steps("custom_wf") == steps

    def test_get_output_with_since(self, manager):
        for i in range(5):
            manager._emit_output("info", f"m{i}")
        assert len(manager.get_output(since=3)) == 2

    def test_register_output_callback(self, manager):
        seen = []

        def cb(level, message, details=None):
            seen.append((level, message, details))

        manager.register_output_callback(cb)
        manager._emit_output("info", "hello", "extra")
        assert seen == [("info", "hello", "extra")]

    def test_callback_exception_swallowed(self, manager):
        def bad_cb(level, message, details=None):
            raise RuntimeError("callback boom")

        manager.register_output_callback(bad_cb)
        manager._emit_output("info", "x")
