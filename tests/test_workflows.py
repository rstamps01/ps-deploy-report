"""
Unit tests for Workflow modules.

Tests all workflow classes: VnetmapWorkflow, SupportToolWorkflow,
VperfsanityWorkflow, LogBundleWorkflow, SwitchConfigWorkflow,
NetworkConfigWorkflow.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_script_runner():
    """Mock ScriptRunner for workflow tests."""
    runner = MagicMock()
    runner.check_prerequisites.return_value = (True, "OK")
    runner.get_local_dir.return_value = Path("/tmp/test")
    runner.download_to_local.return_value = MagicMock(success=True)
    runner.copy_to_remote.return_value = MagicMock(success=True)
    runner.execute_remote.return_value = MagicMock(success=True, stdout="output", exit_code=0)
    runner.cleanup_remote.return_value = MagicMock(success=True)
    return runner


@pytest.fixture
def mock_ssh():
    """Mock SSH command execution."""
    with patch("workflows.vnetmap_workflow.run_ssh_command") as vnet_mock, patch(
        "workflows.support_tool_workflow.run_ssh_command"
    ) as support_mock, patch("workflows.vperfsanity_workflow.run_ssh_command") as perf_mock, patch(
        "workflows.log_bundle_workflow.run_ssh_command", create=True
    ) as log_mock, patch(
        "workflows.switch_config_workflow.run_ssh_command"
    ) as switch_mock, patch(
        "workflows.network_config_workflow.run_ssh_command"
    ) as net_mock:
        for m in [vnet_mock, support_mock, perf_mock, log_mock, switch_mock, net_mock]:
            m.return_value = (0, "output", "")
        yield {
            "vnetmap": vnet_mock,
            "support": support_mock,
            "vperfsanity": perf_mock,
            "log_bundle": log_mock,
            "switch": switch_mock,
            "network": net_mock,
        }


# ===================================================================
# TestWorkflowRegistry
# ===================================================================


class TestWorkflowRegistry:
    def test_list_all_returns_workflows(self):
        workflows = WorkflowRegistry.list_all()
        assert isinstance(workflows, list)
        assert len(workflows) >= 6

    def test_get_existing_workflow(self):
        workflow = WorkflowRegistry.get("vnetmap")
        assert workflow is not None
        assert hasattr(workflow, "get_steps")

    def test_get_nonexistent_workflow(self):
        workflow = WorkflowRegistry.get("nonexistent")
        assert workflow is None

    def test_all_workflows_have_required_attributes(self):
        for wf_info in WorkflowRegistry.list_all():
            workflow = WorkflowRegistry.get(wf_info["id"])
            assert hasattr(workflow, "name")
            assert hasattr(workflow, "description")
            assert hasattr(workflow, "enabled")
            assert hasattr(workflow, "get_steps")
            assert hasattr(workflow, "run_step")


# ===================================================================
# TestVnetmapWorkflow
# ===================================================================


class TestVnetmapWorkflow:
    def test_get_steps_returns_6_steps(self):
        workflow = WorkflowRegistry.get("vnetmap")
        steps = workflow.get_steps()
        assert len(steps) == 6

    def test_steps_have_required_fields(self):
        workflow = WorkflowRegistry.get("vnetmap")
        for step in workflow.get_steps():
            assert "id" in step
            assert "name" in step
            assert "description" in step

    def test_validate_prerequisites_missing_creds(self):
        workflow = WorkflowRegistry.get("vnetmap")
        workflow.set_credentials({})
        ok, msg = workflow.validate_prerequisites()
        assert ok is False


# ===================================================================
# TestSupportToolWorkflow
# ===================================================================


class TestSupportToolWorkflow:
    def test_get_steps_returns_5_steps(self):
        workflow = WorkflowRegistry.get("support_tool")
        steps = workflow.get_steps()
        assert len(steps) == 5

    def test_name_and_description(self):
        workflow = WorkflowRegistry.get("support_tool")
        assert "support" in workflow.name.lower()

    def test_validate_prerequisites_missing_creds(self):
        workflow = WorkflowRegistry.get("support_tool")
        workflow.set_credentials({})
        ok, msg = workflow.validate_prerequisites()
        assert ok is False


# ===================================================================
# TestVperfsanityWorkflow
# ===================================================================


class TestVperfsanityWorkflow:
    def test_get_steps_returns_7_steps(self):
        workflow = WorkflowRegistry.get("vperfsanity")
        steps = workflow.get_steps()
        assert len(steps) == 7

    def test_name_and_description(self):
        workflow = WorkflowRegistry.get("vperfsanity")
        assert "perf" in workflow.name.lower() or "sanity" in workflow.name.lower()


# ===================================================================
# TestLogBundleWorkflow
# ===================================================================


class TestLogBundleWorkflow:
    def test_get_steps_returns_5_steps(self):
        workflow = WorkflowRegistry.get("log_bundle")
        steps = workflow.get_steps()
        assert len(steps) == 5

    def test_name_contains_log(self):
        workflow = WorkflowRegistry.get("log_bundle")
        assert "log" in workflow.name.lower()


# ===================================================================
# TestSwitchConfigWorkflow
# ===================================================================


class TestSwitchConfigWorkflow:
    def test_get_steps_returns_3_steps(self):
        workflow = WorkflowRegistry.get("switch_config")
        steps = workflow.get_steps()
        assert len(steps) == 3

    def test_name_contains_switch(self):
        workflow = WorkflowRegistry.get("switch_config")
        assert "switch" in workflow.name.lower()


# ===================================================================
# TestNetworkConfigWorkflow
# ===================================================================


class TestNetworkConfigWorkflow:
    def test_get_steps_returns_4_steps(self):
        workflow = WorkflowRegistry.get("network_config")
        steps = workflow.get_steps()
        assert len(steps) == 4

    def test_name_contains_network(self):
        workflow = WorkflowRegistry.get("network_config")
        assert "network" in workflow.name.lower()

    def test_validate_prerequisites_missing_creds(self):
        workflow = WorkflowRegistry.get("network_config")
        workflow.set_credentials({})
        ok, msg = workflow.validate_prerequisites()
        assert ok is False


# ===================================================================
# TestWorkflowStepExecution
# ===================================================================


class TestWorkflowStepExecution:
    @patch("workflows.vnetmap_workflow.ScriptRunner")
    def test_vnetmap_step_1_with_mock(self, mock_runner_class):
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (True, "OK")
        mock_runner.get_local_dir.return_value = Path("/tmp")
        mock_runner.download_to_local.return_value = MagicMock(success=True)
        mock_runner_class.return_value = mock_runner

        workflow = WorkflowRegistry.get("vnetmap")
        workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            }
        )
        workflow._script_runner = mock_runner

        # Step 1 should try to download scripts
        result = workflow.run_step(1)
        assert "success" in result or "error" in result


# ===================================================================
# TestVperfsanityCrossTenantCleanup
# ===================================================================


class TestVperfsanityCrossTenantCleanup:
    """Tests for vperfsanity cross-tenant view cleanup."""

    def test_cleanup_finds_and_deletes_stale_views(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        mock_ssh["vperfsanity"].side_effect = [
            (
                0,
                '[{"name":"vperfsanity_view","id":99,"alias":"vperfsanity","bucket":"","path":""}]',
                "",
            ),
            (0, "", ""),
        ]
        workflow._api_cleanup_cross_tenant_views("10.0.0.1", "vastdata", "pass", "admin", "123456")
        assert mock_ssh["vperfsanity"].call_count == 2
        delete_call_str = str(mock_ssh["vperfsanity"].call_args_list[1])
        assert "DELETE" in delete_call_str

    def test_cleanup_no_stale_views(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        mock_ssh["vperfsanity"].return_value = (0, "[]", "")
        workflow._api_cleanup_cross_tenant_views("10.0.0.1", "vastdata", "pass", "admin", "123456")
        assert mock_ssh["vperfsanity"].call_count == 1

    def test_cleanup_api_unreachable(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        mock_ssh["vperfsanity"].return_value = (1, "", "connection refused")
        workflow._api_cleanup_cross_tenant_views("10.0.0.1", "vastdata", "pass", "admin", "123456")
        assert mock_ssh["vperfsanity"].call_count == 1

    def test_cleanup_malformed_json(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        mock_ssh["vperfsanity"].return_value = (0, "not json", "")
        workflow._api_cleanup_cross_tenant_views("10.0.0.1", "vastdata", "pass", "admin", "123456")
        assert mock_ssh["vperfsanity"].call_count == 1


# ===================================================================
# TestVperfsanityStepExecution
# ===================================================================


class TestVperfsanityStepExecution:
    """Tests for vperfsanity workflow step execution."""

    def test_step3_prepare_success(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials({
            "cluster_ip": "10.0.0.1",
            "node_user": "vastdata",
            "node_password": "pass",
            "username": "admin",
            "password": "adminpass",
        })
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (0, "ok", "")
        result = workflow.run_step(3)
        assert "success" in result

    def test_step3_prepare_bucket_conflict(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials({
            "cluster_ip": "10.0.0.1",
            "node_user": "vastdata",
            "node_password": "pass",
            "username": "admin",
            "password": "adminpass",
        })
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (1, "bucket name already in use", "")
        result = workflow.run_step(3)
        assert isinstance(result, dict)

    def test_step4_run_tests_success(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials({
            "cluster_ip": "10.0.0.1",
            "node_user": "vastdata",
            "node_password": "pass",
            "username": "admin",
            "password": "adminpass",
        })
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (0, "PASS", "")
        result = workflow.run_step(4)
        assert isinstance(result, dict)

    def test_step7_cleanup_passes_admin_creds(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials({
            "cluster_ip": "10.0.0.1",
            "node_user": "vastdata",
            "node_password": "pass",
            "username": "admin",
            "password": "adminpass",
        })
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (0, "", "")
        workflow.run_step(7)
        calls_str = str(mock_ssh["vperfsanity"].call_args_list)
        assert "ADMIN" in calls_str or "admin" in calls_str

    def test_step7_cleanup_passes_vast_vms(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials({
            "cluster_ip": "10.0.0.1",
            "node_user": "vastdata",
            "node_password": "pass",
            "username": "admin",
            "password": "adminpass",
            "vast_vms": "10.0.0.5",
        })
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (0, "", "")
        workflow.run_step(7)
        calls_str = str(mock_ssh["vperfsanity"].call_args_list)
        assert "VAST_VMS" in calls_str


# ===================================================================
# TestSwitchConfigStepExecution
# ===================================================================


class TestSwitchConfigStepExecution:
    """Tests for switch config workflow switch type detection."""

    def test_detect_switch_type_cumulus_nvue(self, mock_ssh):
        workflow = WorkflowRegistry.get("switch_config")
        workflow.set_credentials({
            "cluster_ip": "10.0.0.1",
            "username": "admin",
            "password": "pass",
            "switch_user": "cumulus",
            "switch_password": "pass",
        })
        workflow._step_data = {"switches": [{"ip": "10.0.0.10", "type": "unknown"}]}
        mock_ssh["switch"].return_value = (0, "HAS_NV\nCUMULUS LINUX", "")
        result = workflow._detect_switch_type("10.0.0.10", "cumulus", "pass", "", "")
        assert result == "cumulus_nvue"

    def test_detect_switch_type_cumulus_nclu(self, mock_ssh):
        workflow = WorkflowRegistry.get("switch_config")
        workflow._step_data = {"switches": [{"ip": "10.0.0.10", "type": "unknown"}]}
        mock_ssh["switch"].return_value = (0, "HAS_NET\nCUMULUS LINUX", "")
        result = workflow._detect_switch_type("10.0.0.10", "cumulus", "pass", "", "")
        assert result == "cumulus_nclu"

    def test_detect_switch_type_mellanox(self, mock_ssh):
        workflow = WorkflowRegistry.get("switch_config")
        workflow._step_data = {"switches": [{"ip": "10.0.0.10", "type": "unknown"}]}
        mock_ssh["switch"].return_value = (1, "", "")
        with patch("workflows.switch_config_workflow.run_interactive_ssh") as mock_interactive:
            mock_interactive.return_value = (1, "", "")
            result = workflow._detect_switch_type("10.0.0.10", "admin", "pass", "unknown", "")
        assert result == "mlnx"


# ===================================================================
# TestNetworkConfigStepExecution
# ===================================================================


class TestNetworkConfigStepExecution:
    """Tests for network config workflow step execution."""

    def test_step2_clush_via_gateway(self, mock_ssh):
        workflow = WorkflowRegistry.get("network_config")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        workflow._script_runner = MagicMock()
        workflow._step_data = {
            "all_nodes": {"cnode": "10.0.0.3", "gateway": "10.0.0.1"},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        mock_ssh["network"].return_value = (0, "10.0.0.3: command line output", "")
        result = workflow.run_step(2)
        assert mock_ssh["network"].call_count >= 1
        calls_str = str(mock_ssh["network"].call_args_list)
        assert "clush" in calls_str

    def test_step2_grep_uses_text_flag(self, mock_ssh):
        workflow = WorkflowRegistry.get("network_config")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        workflow._script_runner = MagicMock()
        workflow._step_data = {
            "all_nodes": {"gateway": "10.0.0.1"},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        mock_ssh["network"].return_value = (0, "command line output", "")
        workflow.run_step(2)
        call_str = str(mock_ssh["network"].call_args_list)
        assert "grep -a" in call_str


# ===================================================================
# TestSupportToolStepExecution
# ===================================================================


class TestSupportToolStepExecution:
    """Tests for support tool workflow step execution."""

    def test_step3_uses_container_path(self, mock_ssh):
        workflow = WorkflowRegistry.get("support_tool")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        workflow._script_runner = MagicMock()
        workflow._step_data = {"cnode_ip": "10.0.0.2"}
        mock_ssh["support"].return_value = (0, "output", "")
        workflow.run_step(3)
        call_str = str(mock_ssh["support"].call_args_list)
        assert "/vast/data/" in call_str

    def test_step3_requires_force_tty(self, mock_ssh):
        workflow = WorkflowRegistry.get("support_tool")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        workflow._script_runner = MagicMock()
        workflow._step_data = {"cnode_ip": "10.0.0.2"}
        mock_ssh["support"].return_value = (0, "output", "")
        workflow.run_step(3)
        _, kwargs = mock_ssh["support"].call_args
        assert kwargs.get("force_tty") is True


# ===================================================================
# TestLogBundleStepExecution
# ===================================================================


class TestLogBundleStepExecution:
    """Tests for log bundle workflow step execution."""

    def test_step1_discover_sizes(self, mock_ssh):
        workflow = WorkflowRegistry.get("log_bundle")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (True, "OK")
        mock_result = MagicMock(success=True, stdout="500M\t/var/log/vast")
        mock_runner.execute_remote.return_value = mock_result
        workflow._script_runner = mock_runner
        result = workflow.run_step(1)
        assert result["success"] is True

    def test_step1_discover_ssh_error(self, mock_ssh):
        workflow = WorkflowRegistry.get("log_bundle")
        workflow.set_credentials(
            {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
        )
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (False, "SSH connection failed")
        workflow._script_runner = mock_runner
        result = workflow.run_step(1)
        assert result["success"] is False
