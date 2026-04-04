"""
Advanced Operations Module

Backend orchestration for the Advanced Operations page, providing step-by-step
workflow execution for complex script-based validations.

This module requires Developer Mode to be enabled (--dev-mode flag).
"""

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)


class StepStatus(Enum):
    """Status of a workflow step."""

    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class StepResult:
    """Result of a workflow step execution."""

    status: StepStatus
    message: str
    details: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    duration_ms: int = 0


@dataclass
class WorkflowState:
    """Current state of a workflow execution."""

    workflow_id: str
    workflow_name: str
    current_step: int = 0
    total_steps: int = 0
    status: str = "idle"  # idle, running, completed, error, cancelled
    steps: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class AdvancedOpsManager:
    """
    Manager for Advanced Operations workflows.

    Handles workflow registration, execution, and state management.
    """

    def __init__(self):
        self._workflows: Dict[str, Dict[str, Any]] = {}
        self._current_state: Optional[WorkflowState] = None
        self._lock = threading.Lock()
        self._cancel_event = threading.Event()
        self._output_buffer: List[Dict[str, Any]] = []
        self._output_callbacks: List[Callable[[str, str, Optional[str]], None]] = []

        # Register built-in workflows
        self._register_builtin_workflows()

    def _register_builtin_workflows(self) -> None:
        """Register the built-in workflow definitions from the workflow registry."""
        try:
            from workflows import WorkflowRegistry

            for wf_info in WorkflowRegistry.list_all():
                wf = WorkflowRegistry.get(wf_info["id"])
                if wf:
                    self._workflows[wf_info["id"]] = {
                        "id": wf_info["id"],
                        "name": wf_info["name"],
                        "description": wf_info["description"],
                        "min_vast_version": wf_info["min_vast_version"],
                        "enabled": wf_info["enabled"],
                        "steps": wf.get_steps(),
                        "_instance": wf,  # Keep a reference to the workflow instance
                    }
        except ImportError:
            logger.warning("Workflow registry not available, using hardcoded definitions")
            self._register_fallback_workflows()

    def _register_fallback_workflows(self) -> None:
        """Fallback workflow definitions if registry is not available."""
        self._workflows = {
            "vnetmap": {
                "id": "vnetmap",
                "name": "vnetmap Validation",
                "description": "Validate network topology using vnetmap.py",
                "min_vast_version": "5.0",
                "enabled": True,
                "steps": [
                    {
                        "id": 1,
                        "name": "Download Scripts to Laptop",
                        "description": "Download vnetmap.py and mlnx_switch_api.py",
                    },
                    {"id": 2, "name": "Copy to CNode", "description": "SCP scripts to CNode and set permissions"},
                    {
                        "id": 3,
                        "name": "Generate Export Commands",
                        "description": "Generate cluster-specific export commands",
                    },
                    {"id": 4, "name": "Execute Export Commands", "description": "Run export commands on CNode"},
                    {"id": 5, "name": "Run vnetmap.py", "description": "Execute vnetmap validation script"},
                    {"id": 6, "name": "Validate Results", "description": "Parse and validate vnetmap output"},
                    {"id": 7, "name": "Save Output", "description": "Save results to local output directory"},
                ],
            },
            "support_tool": {
                "id": "support_tool",
                "name": "VAST Support Tools",
                "description": "Run vast_support_tools.py for diagnostics",
                "min_vast_version": "5.0",
                "enabled": True,
                "steps": [
                    {
                        "id": 1,
                        "name": "Download Script to CNode",
                        "description": "Download vast_support_tools.py to CNode",
                    },
                    {"id": 2, "name": "Run in VAST Container", "description": "Execute script inside VAST container"},
                    {"id": 3, "name": "Validate Results", "description": "Parse and validate script output"},
                    {"id": 4, "name": "Package Output", "description": "Create output archive"},
                    {"id": 5, "name": "Download to Laptop", "description": "SCP results to local system"},
                ],
            },
            "vperfsanity": {
                "id": "vperfsanity",
                "name": "vperfsanity Performance Test",
                "description": "Run vperfsanity performance validation",
                "min_vast_version": "5.0",
                "enabled": True,
                "steps": [
                    {"id": 1, "name": "Download Package", "description": "Download vperfsanity package"},
                    {"id": 2, "name": "Prepare Infrastructure", "description": "Set up test environment"},
                    {"id": 3, "name": "Run Write Test", "description": "Execute write performance test"},
                    {"id": 4, "name": "Run Read Test", "description": "Execute read performance test"},
                    {"id": 5, "name": "Collect Results", "description": "Gather and parse test results"},
                    {"id": 6, "name": "Cleanup", "description": "Clean up test environment"},
                ],
            },
            "log_bundle": {
                "id": "log_bundle",
                "name": "VMS Log Bundle",
                "description": "Collect VMS log bundle for support",
                "min_vast_version": "5.0",
                "enabled": True,
                "steps": [
                    {"id": 1, "name": "Discover Log Sizes", "description": "Check available log sizes"},
                    {"id": 2, "name": "Confirm Collection", "description": "User confirmation for large bundles"},
                    {"id": 3, "name": "Create Archive", "description": "Generate log bundle archive"},
                    {"id": 4, "name": "Download to Laptop", "description": "SCP archive to local system"},
                    {"id": 5, "name": "Verify Contents", "description": "Verify archive integrity"},
                ],
            },
            "switch_config": {
                "id": "switch_config",
                "name": "Switch Configuration Extraction",
                "description": "Extract switch configuration for backup",
                "min_vast_version": "5.0",
                "enabled": True,
                "steps": [
                    {"id": 1, "name": "Discover Switches", "description": "Fetch switch IPs from VAST API and connect"},
                    {
                        "id": 2,
                        "name": "Extract Configuration",
                        "description": "Retrieve running configuration and interface info",
                    },
                    {"id": 3, "name": "Save Configuration", "description": "Save configuration to local files"},
                ],
            },
            "network_config": {
                "id": "network_config",
                "name": "Network Configuration Extraction",
                "description": "Extract configure_network.py commands",
                "min_vast_version": "5.0",
                "enabled": True,
                "steps": [
                    {
                        "id": 1,
                        "name": "Connect & Discover Nodes",
                        "description": "SSH to CNode and discover all node IPs",
                    },
                    {
                        "id": 2,
                        "name": "Collect configure_network",
                        "description": "Collect configure_network commands from all nodes",
                    },
                    {
                        "id": 3,
                        "name": "Extract Network Config",
                        "description": "Collect interface, routing, and bond config from all nodes",
                    },
                    {"id": 4, "name": "Save Output", "description": "Save extracted configuration"},
                ],
            },
        }

    def get_workflows(self) -> List[Dict[str, Any]]:
        """Get list of available workflows."""
        return [
            {
                "id": w["id"],
                "name": w["name"],
                "description": w["description"],
                "step_count": len(w["steps"]),
                "enabled": w["enabled"],
            }
            for w in self._workflows.values()
        ]

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific workflow by ID."""
        return self._workflows.get(workflow_id)

    def get_workflow_steps(self, workflow_id: str) -> List[Dict[str, Any]]:
        """Get the steps for a specific workflow."""
        workflow = self._workflows.get(workflow_id)
        if not workflow:
            return []
        steps: List[Dict[str, Any]] = workflow["steps"]
        return steps

    def get_current_state(self) -> Optional[Dict[str, Any]]:
        """Get the current workflow state."""
        with self._lock:
            if not self._current_state:
                return None
            return {
                "workflow_id": self._current_state.workflow_id,
                "workflow_name": self._current_state.workflow_name,
                "current_step": self._current_state.current_step,
                "total_steps": self._current_state.total_steps,
                "status": self._current_state.status,
                "steps": self._current_state.steps,
                "started_at": self._current_state.started_at.isoformat() if self._current_state.started_at else None,
                "completed_at": (
                    self._current_state.completed_at.isoformat() if self._current_state.completed_at else None
                ),
                "error": self._current_state.error,
            }

    def is_running(self) -> bool:
        """Check if a workflow is currently running."""
        with self._lock:
            return self._current_state is not None and self._current_state.status == "running"

    @property
    def current_workflow_id(self) -> Optional[str]:
        """Return the ID of the currently active workflow, or None."""
        with self._lock:
            return self._current_state.workflow_id if self._current_state else None

    def get_state(self) -> Optional[Dict[str, Any]]:
        """Return the current workflow state dict (alias for get_current_state)."""
        return self.get_current_state()

    def start_workflow(self, workflow_id: str, credentials: Dict[str, Any]) -> bool:
        """Start a workflow execution."""
        with self._lock:
            if self._current_state and self._current_state.status == "running":
                logger.warning("Cannot start workflow - another workflow is running")
                return False

            workflow = self._workflows.get(workflow_id)
            if not workflow:
                logger.error(f"Workflow not found: {workflow_id}")
                return False

            # Initialize state
            self._current_state = WorkflowState(
                workflow_id=workflow_id,
                workflow_name=workflow["name"],
                current_step=0,
                total_steps=len(workflow["steps"]),
                status="running",
                steps=[
                    {"id": s["id"], "name": s["name"], "status": "pending", "result": None} for s in workflow["steps"]
                ],
                started_at=datetime.now(),
            )
            self._cancel_event.clear()
            self._output_buffer.clear()

        logger.info(f"Started workflow: {workflow_id}")
        self._emit_output("info", f"Starting workflow: {workflow['name']}")
        return True

    def run_step(self, step_id: int, credentials: Dict[str, Any]) -> StepResult:
        """Run a specific step of the current workflow."""
        with self._lock:
            if not self._current_state:
                return StepResult(StepStatus.ERROR, "No workflow active")

            if step_id < 1 or step_id > self._current_state.total_steps:
                return StepResult(StepStatus.ERROR, f"Invalid step ID: {step_id}")

            step_idx = step_id - 1
            step = self._current_state.steps[step_idx]
            workflow_id = self._current_state.workflow_id

            # Mark step as running
            step["status"] = "running"
            self._current_state.current_step = step_id

        # Emit step header
        self._emit_output("info", "═" * 65)
        self._emit_output("info", f"STEP {step_id}: {step['name']}")
        self._emit_output("info", "═" * 65)

        start_time = time.time()

        try:
            if self._cancel_event.is_set():
                result = StepResult(StepStatus.SKIPPED, "Cancelled by user")
            else:
                # Get the workflow instance and execute the step
                with self._lock:
                    workflow = self._workflows.get(workflow_id)

                if workflow and "_instance" in workflow:
                    wf_instance = workflow["_instance"]

                    # Configure the workflow with output callback
                    if hasattr(wf_instance, "set_output_callback"):
                        wf_instance.set_output_callback(self._emit_output)
                    if hasattr(wf_instance, "set_credentials"):
                        wf_instance.set_credentials(credentials)

                    # Execute the step
                    self._emit_output("debug", f"Executing workflow step via {type(wf_instance).__name__}")
                    step_result = wf_instance.run_step(step_id)

                    success = step_result.get("success", False)
                    message = step_result.get("message", "")
                    details = step_result.get("details", "")

                    # Emit step details if present
                    if details:
                        self._emit_output("info", f"[DETAILS]\n{details}")

                    if success:
                        result = StepResult(
                            status=StepStatus.DONE,
                            message=message,
                            details=details,
                            duration_ms=int((time.time() - start_time) * 1000),
                        )
                    else:
                        result = StepResult(
                            status=StepStatus.ERROR,
                            message=message,
                            details=details,
                            duration_ms=int((time.time() - start_time) * 1000),
                        )
                else:
                    self._emit_output("warn", "No workflow instance found, using placeholder")
                    result = StepResult(
                        status=StepStatus.ERROR,
                        message="Workflow instance not found",
                        duration_ms=int((time.time() - start_time) * 1000),
                    )

        except Exception as e:
            logger.exception(f"Step {step_id} failed")
            self._emit_output("error", f"[EXCEPTION] {str(e)}")
            result = StepResult(
                status=StepStatus.ERROR,
                message=f"Step {step_id} failed: {str(e)}",
                duration_ms=int((time.time() - start_time) * 1000),
            )

        # Update state
        with self._lock:
            if self._current_state and step_idx < len(self._current_state.steps):
                self._current_state.steps[step_idx]["status"] = result.status.value
                self._current_state.steps[step_idx]["result"] = {
                    "message": result.message,
                    "details": result.details,
                    "duration_ms": result.duration_ms,
                }

        # Emit step completion
        level = (
            "success" if result.status == StepStatus.DONE else "error" if result.status == StepStatus.ERROR else "warn"
        )
        self._emit_output(
            level, f"[STEP {step_id} {result.status.value.upper()}] {result.message} ({result.duration_ms}ms)"
        )
        self._emit_output("info", "─" * 65)

        return result

    def run_all_steps(self, credentials: Dict[str, Any]) -> bool:
        """Run all steps in sequence."""
        with self._lock:
            if not self._current_state:
                return False
            total_steps = self._current_state.total_steps

        for step_id in range(1, total_steps + 1):
            if self._cancel_event.is_set():
                self._emit_output("warn", "Workflow cancelled by user")
                break

            result = self.run_step(step_id, credentials)
            if result.status == StepStatus.ERROR:
                self._complete_workflow(error=result.message)
                return False

        self._complete_workflow()
        return True

    def cancel(self) -> bool:
        """Cancel the current workflow."""
        with self._lock:
            if not self._current_state or self._current_state.status != "running":
                return False
            self._cancel_event.set()

        self._emit_output("warn", "Cancelling workflow...")
        return True

    def reset(self) -> None:
        """Reset the workflow state."""
        with self._lock:
            self._current_state = None
            self._cancel_event.clear()
            self._output_buffer.clear()

    def _complete_workflow(self, error: Optional[str] = None) -> None:
        """Mark the workflow as completed."""
        with self._lock:
            if self._current_state:
                self._current_state.status = "error" if error else "completed"
                self._current_state.completed_at = datetime.now()
                self._current_state.error = error

        status = "with errors" if error else "successfully"
        self._emit_output("info" if not error else "error", f"Workflow completed {status}")

    def _emit_output(self, level: str, message: str, details: Optional[str] = None, log_tier: str = "status") -> None:
        """Emit output to the buffer and callbacks."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "details": details,
            "log_tier": log_tier,
        }
        self._output_buffer.append(entry)

        for callback in self._output_callbacks:
            try:
                callback(level, message, details)
            except Exception:
                pass

    def get_output(self, since: int = 0) -> List[Dict[str, Any]]:
        """Get output entries since a given index."""
        return self._output_buffer[since:]

    def register_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        """Register a callback for output events."""
        self._output_callbacks.append(callback)


# Global manager instance
_manager: Optional[AdvancedOpsManager] = None


def get_advanced_ops_manager() -> AdvancedOpsManager:
    """Get or create the global AdvancedOpsManager instance."""
    global _manager
    if _manager is None:
        _manager = AdvancedOpsManager()
    return _manager
