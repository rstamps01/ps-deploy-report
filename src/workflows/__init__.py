"""
Workflows Package - Registry of available workflows and their implementations.
"""

from typing import Any, Dict, List, Optional, Tuple, Type

from utils.logger import get_logger

logger = get_logger(__name__)


def get_cleanup_plan(workflow: Any) -> Tuple[Tuple[int, ...], int]:
    """Return a workflow's declared cleanup steps and the step that makes them necessary.

    Workflows that create objects on the cluster declare ``CLEANUP_STEPS`` (step ids that
    remove them) and ``CLEANUP_REQUIRED_AFTER_STEP`` (the first step that may create them).
    Runners execute the cleanup steps after a failure or cancel once that step was reached,
    so an aborted run never leaves test data, views, users or services behind.

    Returns:
        Tuple of (cleanup step ids, first step that requires cleanup); ``((), 0)`` when the
        workflow declares nothing.
    """
    steps = getattr(workflow, "CLEANUP_STEPS", None)
    if not isinstance(steps, (list, tuple)) or not all(isinstance(s, int) for s in steps):
        return (), 0
    required_after = getattr(workflow, "CLEANUP_REQUIRED_AFTER_STEP", 1)
    if not isinstance(required_after, int):
        required_after = 1
    return tuple(steps), required_after


class WorkflowRegistry:
    """Registry of available workflows."""

    _workflows: Dict[str, Type] = {}

    @classmethod
    def register(cls, workflow_id: str, workflow_class: Type) -> None:
        cls._workflows[workflow_id] = workflow_class

    @classmethod
    def get(cls, workflow_id: str) -> Optional[Any]:
        workflow_class = cls._workflows.get(workflow_id)
        return workflow_class() if workflow_class else None

    @classmethod
    def list_all(cls) -> List[Dict[str, Any]]:
        return [
            {
                "id": wid,
                "name": wcls().name,
                "description": wcls().description,
                "step_count": len(wcls().get_steps()),
                "enabled": wcls().enabled,
                "min_vast_version": wcls().min_vast_version,
            }
            for wid, wcls in cls._workflows.items()
        ]


def register_workflows() -> None:
    """Register all available workflows."""
    from workflows.vnetmap_workflow import VnetmapWorkflow
    from workflows.support_tool_workflow import SupportToolWorkflow
    from workflows.vperfsanity_workflow import VperfsanityWorkflow
    from workflows.log_bundle_workflow import LogBundleWorkflow
    from workflows.switch_config_workflow import SwitchConfigWorkflow
    from workflows.network_config_workflow import NetworkConfigWorkflow

    WorkflowRegistry.register("vnetmap", VnetmapWorkflow)
    WorkflowRegistry.register("support_tool", SupportToolWorkflow)
    WorkflowRegistry.register("vperfsanity", VperfsanityWorkflow)
    WorkflowRegistry.register("log_bundle", LogBundleWorkflow)
    WorkflowRegistry.register("switch_config", SwitchConfigWorkflow)
    WorkflowRegistry.register("network_config", NetworkConfigWorkflow)


register_workflows()
