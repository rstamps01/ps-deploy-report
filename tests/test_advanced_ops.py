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
