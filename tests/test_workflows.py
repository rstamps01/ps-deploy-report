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
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
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
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
        mock_ssh["vperfsanity"].return_value = (0, "[]", "")
        workflow._api_cleanup_cross_tenant_views("10.0.0.1", "vastdata", "pass", "admin", "123456")
        assert mock_ssh["vperfsanity"].call_count == 1

    def test_cleanup_api_unreachable(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
        mock_ssh["vperfsanity"].return_value = (1, "", "connection refused")
        workflow._api_cleanup_cross_tenant_views("10.0.0.1", "vastdata", "pass", "admin", "123456")
        assert mock_ssh["vperfsanity"].call_count == 1

    def test_cleanup_malformed_json(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
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
        workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
                "username": "admin",
                "password": "adminpass",
            }
        )
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (0, "ok", "")
        result = workflow.run_step(3)
        assert "success" in result

    def test_step3_prepare_bucket_conflict(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
                "username": "admin",
                "password": "adminpass",
            }
        )
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (1, "bucket name already in use", "")
        result = workflow.run_step(3)
        assert isinstance(result, dict)

    def test_step4_run_tests_success(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
                "username": "admin",
                "password": "adminpass",
            }
        )
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (0, "PASS", "")
        result = workflow.run_step(4)
        assert isinstance(result, dict)

    def test_step7_cleanup_passes_admin_creds(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
                "username": "admin",
                "password": "adminpass",
            }
        )
        workflow._script_runner = MagicMock()
        mock_ssh["vperfsanity"].return_value = (0, "", "")
        workflow.run_step(7)
        calls_str = str(mock_ssh["vperfsanity"].call_args_list)
        assert "ADMIN" in calls_str or "admin" in calls_str

    def test_step7_cleanup_passes_vast_vms(self, mock_ssh):
        workflow = WorkflowRegistry.get("vperfsanity")
        workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
                "username": "admin",
                "password": "adminpass",
                "vast_vms": "10.0.0.5",
            }
        )
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
        workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            }
        )
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
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
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
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
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
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
        workflow._script_runner = MagicMock()
        workflow._step_data = {"cnode_ip": "10.0.0.2"}
        mock_ssh["support"].return_value = (0, "output", "")
        workflow.run_step(3)
        call_str = str(mock_ssh["support"].call_args_list)
        assert "/vast/data/" in call_str

    def test_step3_requires_force_tty(self, mock_ssh):
        workflow = WorkflowRegistry.get("support_tool")
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
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
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (True, "OK")
        mock_result = MagicMock(success=True, stdout="500M\t/var/log/vast")
        mock_runner.execute_remote.return_value = mock_result
        workflow._script_runner = mock_runner
        result = workflow.run_step(1)
        assert result["success"] is True

    def test_step1_discover_ssh_error(self, mock_ssh):
        workflow = WorkflowRegistry.get("log_bundle")
        workflow.set_credentials({"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"})
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (False, "SSH connection failed")
        workflow._script_runner = mock_runner
        result = workflow.run_step(1)
        assert result["success"] is False


# ===================================================================
# Additional imports for extended workflow tests
# ===================================================================
import requests as _requests_module

# ===================================================================
# TestVnetmapParsing
# ===================================================================


class TestVnetmapParsing:
    """Tests for VnetmapWorkflow parsing and filtering helpers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.workflow = WorkflowRegistry.get("vnetmap")
        self.workflow.set_output_callback(MagicMock())

    def test_convert_ip_format_range(self):
        assert self.workflow._convert_ip_format("10.143.11.[1-4]") == "10.143.11.{1..4}"

    def test_convert_ip_format_single(self):
        assert self.workflow._convert_ip_format("10.0.0.1") == "10.0.0.1"

    def test_convert_ip_format_empty(self):
        assert self.workflow._convert_ip_format("") == ""

    def test_parse_local_cfg_groups(self):
        cfg = "cnodes: 10.0.0.[1-4]\ndnodes: 10.0.1.[1-8]\n"
        cnodes, dnodes = self.workflow._parse_local_cfg(cfg)
        assert cnodes == "10.0.0.[1-4]"
        assert dnodes == "10.0.1.[1-8]"

    def test_parse_local_cfg_at_refs(self):
        cfg = "cnodesub0: 172.16.3.[4-5]\ncnodes: @cnodesub0\ndnodes: 10.0.1.[1-2]\n"
        cnodes, dnodes = self.workflow._parse_local_cfg(cfg)
        assert cnodes == "172.16.3.[4-5]"
        assert dnodes == "10.0.1.[1-2]"

    def test_filter_output_tracebacks(self):
        raw = (
            "normal line 1\n"
            "Traceback (most recent call last):\n"
            '  File "test.py", line 1\n'
            "    raise Exception\n"
            "Exception: error\n"
            "normal line 2\n"
        )
        filtered = self.workflow._filter_vnetmap_output(raw)
        assert "normal line 1" in filtered
        assert "normal line 2" in filtered
        assert "Traceback" not in filtered

    def test_filter_output_clean(self):
        raw = "switch discovery progress: 2/2 switches\nfull topology\npassed: 10 failed: 0\n"
        filtered = self.workflow._filter_vnetmap_output(raw)
        assert "switch discovery progress" in filtered
        assert "full topology" in filtered
        assert "passed: 10" in filtered

    def test_validate_results_partial(self):
        self.workflow._step_data["vnetmap_output"] = (
            "passed: 10 failed: 2\n" "failed nodes:\n" "10.0.0.5: failed to ssh to node\n" "10.0.0.6: timeout\n"
        )
        result = self.workflow._step_validate_results()
        assert result["success"] is True
        validation = self.workflow._step_data["validation_results"]
        assert validation["ports_passed"] == 10
        assert validation["ports_failed"] == 2
        assert len(validation["failed_nodes"]) == 2
        assert len(validation["recommendations"]) >= 1


# ===================================================================
# TestSwitchConfigSteps
# ===================================================================


class TestSwitchConfigSteps:
    """Tests for SwitchConfigWorkflow API and detection methods."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.workflow = WorkflowRegistry.get("switch_config")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "switch_user": "cumulus",
                "switch_password": "switchpass",
            }
        )
        self.workflow.set_output_callback(MagicMock())

    @patch("requests.get")
    def test_get_switch_ips_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"mgmt_ip": "10.0.10.1", "name": "sw1", "model": "MSN2700"},
            {"mgmt_ip": "10.0.10.2", "name": "sw2", "model": "MSN3700"},
        ]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp
        ips, models = self.workflow._get_switch_ips_from_api()
        assert ips == ["10.0.10.1", "10.0.10.2"]
        assert models["10.0.10.1"] == "MSN2700"

    @patch("requests.get")
    def test_get_switch_ips_v1_fallback(self, mock_get):
        first_resp = MagicMock()
        first_resp.raise_for_status.side_effect = _requests_module.exceptions.HTTPError(
            response=MagicMock(status_code=404)
        )

        ok_resp = MagicMock()
        ok_resp.json.return_value = [{"mgmt_ip": "10.0.10.1", "model": "MSN"}]
        ok_resp.raise_for_status.return_value = None

        mock_get.side_effect = [first_resp, ok_resp]
        ips, models = self.workflow._get_switch_ips_from_api()
        assert ips == ["10.0.10.1"]
        assert mock_get.call_count == 2

    @patch("requests.get")
    def test_get_switch_ips_all_fail(self, mock_get):
        mock_get.side_effect = ConnectionError("refused")
        ips, models = self.workflow._get_switch_ips_from_api()
        assert ips == []
        assert models == {}

    def test_detect_switch_type_onyx(self):
        result = self.workflow._detect_switch_type("10.0.0.10", "admin", "pass", "ONYX SN2700", "")
        assert result == "onyx"

    @patch("workflows.switch_config_workflow.run_ssh_command")
    def test_detect_switch_type_cumulus_nvue(self, mock_ssh):
        mock_ssh.return_value = (0, "HAS_NV\nCUMULUS LINUX 5.x", "")
        result = self.workflow._detect_switch_type("10.0.0.10", "cumulus", "pass", "", "")
        assert result == "cumulus_nvue"

    @patch("workflows.switch_config_workflow.run_interactive_ssh")
    @patch("workflows.switch_config_workflow.run_ssh_command")
    def test_detect_switch_type_spectrum_default(self, mock_ssh, mock_interactive):
        mock_ssh.return_value = (1, "", "")
        mock_interactive.return_value = (1, "", "")
        result = self.workflow._detect_switch_type("10.0.0.10", "admin", "pass", "SN1000", "")
        assert result == "mlnx"


# ===================================================================
# TestNetworkConfigParsing
# ===================================================================


class TestNetworkConfigParsing:
    """Tests for NetworkConfigWorkflow parsing and node execution."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.workflow = WorkflowRegistry.get("network_config")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
            }
        )
        self.workflow.set_output_callback(MagicMock())

    def test_parse_local_cfg_basic(self):
        result = self.workflow._parse_local_cfg("cnodes: 10.0.0.1 10.0.0.2")
        assert result == {"cnodes": ["10.0.0.1", "10.0.0.2"]}

    def test_parse_local_cfg_comments(self):
        cfg = "# this is a comment\ncnodes: 10.0.0.1"
        result = self.workflow._parse_local_cfg(cfg)
        assert result == {"cnodes": ["10.0.0.1"]}

    def test_parse_local_cfg_at_ref(self):
        cfg = "cnodes: 10.0.0.1\ndnodes: 10.0.0.2\nall: @cnodes @dnodes"
        result = self.workflow._parse_local_cfg(cfg)
        assert result["all"] == ["10.0.0.1", "10.0.0.2"]

    def test_parse_local_cfg_range(self):
        result = self.workflow._parse_local_cfg("cnodes: 10.0.0.[1-3]")
        assert result["cnodes"] == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def test_parse_local_cfg_empty(self):
        result = self.workflow._parse_local_cfg("")
        assert result == {}

    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_run_on_all_nodes_clush(self, mock_ssh):
        self.workflow._step_data = {
            "all_nodes": {"cnode_10.0.0.2": "10.0.0.2", "gateway": "10.0.0.1"},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        mock_ssh.side_effect = [
            (0, "10.0.0.2: some data", ""),
            (0, "gateway data", ""),
        ]
        results = self.workflow._run_on_all_nodes("test", "echo hello")
        assert "cnode_10.0.0.2" in results
        assert results["cnode_10.0.0.2"] == "some data"
        assert "gateway" in results
        assert results["gateway"] == "gateway data"

    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_run_on_all_nodes_gateway_only(self, mock_ssh):
        self.workflow._step_data = {
            "all_nodes": {"gateway": "10.0.0.1"},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        mock_ssh.return_value = (0, "gateway data", "")
        results = self.workflow._run_on_all_nodes("test", "echo hello")
        assert "gateway" in results
        assert results["gateway"] == "gateway data"
        mock_ssh.assert_called_once()

    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_collect_configure_network_empty(self, mock_ssh):
        self.workflow._step_data = {
            "all_nodes": {"gateway": "10.0.0.1"},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        mock_ssh.return_value = (0, "", "")
        self.workflow._script_runner = MagicMock()
        result = self.workflow._step_collect_configure_network()
        assert result["success"] is True
        assert "No configure_network" in result["message"]


# ===================================================================
# TestLogBundleSteps
# ===================================================================


class TestLogBundleSteps:
    """Tests for LogBundleWorkflow discover and confirm steps."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.workflow = WorkflowRegistry.get("log_bundle")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
            }
        )
        self.workflow.set_output_callback(MagicMock())

    def _make_exec_result(self, success, stdout="", stderr=""):
        r = MagicMock()
        r.success = success
        r.stdout = stdout
        r.stderr = stderr
        return r

    def test_discover_sizes_gb(self):
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (True, "OK")
        mock_runner.execute_remote.side_effect = [
            self._make_exec_result(True, "2.5G\t/var/log/vast"),
            self._make_exec_result(True, "0\t/var/log/messages"),
            self._make_exec_result(True, "0\t/var/log/syslog"),
        ]
        self.workflow._script_runner = mock_runner
        result = self.workflow._step_discover_sizes()
        assert result["success"] is True
        assert abs(self.workflow._step_data["total_size_mb"] - 2560) < 10

    def test_discover_sizes_mb(self):
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (True, "OK")
        mock_runner.execute_remote.side_effect = [
            self._make_exec_result(True, "500M\t/var/log/vast"),
            self._make_exec_result(True, "0\t/var/log/messages"),
            self._make_exec_result(True, "0\t/var/log/syslog"),
        ]
        self.workflow._script_runner = mock_runner
        result = self.workflow._step_discover_sizes()
        assert result["success"] is True
        assert abs(self.workflow._step_data["total_size_mb"] - 500) < 10

    def test_discover_sizes_kb(self):
        mock_runner = MagicMock()
        mock_runner.check_prerequisites.return_value = (True, "OK")
        mock_runner.execute_remote.side_effect = [
            self._make_exec_result(True, "100K\t/var/log/vast"),
            self._make_exec_result(True, "0\t/var/log/messages"),
            self._make_exec_result(True, "0\t/var/log/syslog"),
        ]
        self.workflow._script_runner = mock_runner
        result = self.workflow._step_discover_sizes()
        assert result["success"] is True
        assert abs(self.workflow._step_data["total_size_mb"] - (100.0 / 1024)) < 0.05

    def test_confirm_under_threshold(self):
        self.workflow._step_data = {"total_size_mb": 1000}
        self.workflow._script_runner = MagicMock()
        result = self.workflow._step_confirm_collection()
        assert result["success"] is True

    def test_confirm_over_threshold(self):
        self.workflow._step_data = {"total_size_mb": 6000}
        self.workflow._script_runner = MagicMock()
        result = self.workflow._step_confirm_collection()
        assert result["success"] is False

    def test_verify_contents_success(self, tmp_path):
        fake_archive = tmp_path / "test.tar.gz"
        fake_archive.write_text("fake")
        self.workflow._step_data = {"local_path": str(fake_archive)}
        self.workflow._script_runner = MagicMock()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="file1.txt\nfile2.txt\n", stderr="")
            result = self.workflow._step_verify_contents()

        assert result["success"] is True
        assert result["data"]["file_count"] == 2


# ===================================================================
# TestSupportToolSteps
# ===================================================================


class TestSupportToolSteps:
    """Tests for SupportToolWorkflow run and archive steps."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.workflow = WorkflowRegistry.get("support_tool")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
            }
        )
        self.emitted = []
        self.workflow.set_output_callback(lambda level, msg, details=None: self.emitted.append((level, msg)))

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_run_support_tools_output_classification(self, mock_ssh):
        mock_ssh.return_value = (
            0,
            "ERROR: disk check failed\nWARNING: low memory\nPASSED: network check\ngeneral info line\n",
            "",
        )
        self.workflow._script_runner = MagicMock()
        result = self.workflow._step_run_support_tools()
        assert result["success"] is True

        error_emits = [(lv, msg) for lv, msg in self.emitted if "disk check" in msg]
        warn_emits = [(lv, msg) for lv, msg in self.emitted if "low memory" in msg]
        success_emits = [(lv, msg) for lv, msg in self.emitted if "network check" in msg]
        assert error_emits[0][0] == "error"
        assert warn_emits[0][0] == "warn"
        assert success_emits[0][0] == "success"

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_run_support_tools_empty_output(self, mock_ssh):
        mock_ssh.return_value = (0, "", "")
        self.workflow._script_runner = MagicMock()
        result = self.workflow._step_run_support_tools()
        assert result["success"] is True

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_dir_found(self, mock_ssh):
        self.workflow._script_runner = MagicMock()
        mock_ssh.side_effect = [
            (0, "cnode1", ""),
            (0, "exists", ""),
            (0, "file1\nfile2", ""),
            (0, "-rw-r--r-- 1 root root 1.0M /userdata/cnode1-support_tool_logs.tgz", ""),
        ]
        result = self.workflow._step_create_archive()
        assert result["success"] is True

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_find_fallback(self, mock_ssh):
        self.workflow._script_runner = MagicMock()
        responses = [
            (0, "cnode1", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "/tmp/vast_support_output", ""),
            (0, "file1", ""),
            (0, "-rw-r--r-- 1 root root 500K /userdata/cnode1-support_tool_logs.tgz", ""),
        ]
        mock_ssh.side_effect = responses
        result = self.workflow._step_create_archive()
        assert result["success"] is True

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_no_dir(self, mock_ssh):
        self.workflow._script_runner = MagicMock()
        responses = [
            (0, "cnode1", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "total 0", ""),
        ]
        mock_ssh.side_effect = responses
        result = self.workflow._step_create_archive()
        assert result["success"] is False

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_tar_failure(self, mock_ssh):
        self.workflow._script_runner = MagicMock()
        mock_ssh.side_effect = [
            (0, "cnode1", ""),
            (0, "exists", ""),
            (1, "", "No such file or directory"),
        ]
        result = self.workflow._step_create_archive()
        assert result["success"] is False

    def test_download_results_success(self, tmp_path):
        mock_scp_module = MagicMock()

        with patch.dict("sys.modules", {"scp": mock_scp_module}):
            with patch("paramiko.SSHClient") as mock_ssh_class:
                mock_ssh = MagicMock()
                mock_ssh_class.return_value = mock_ssh

                mock_runner = MagicMock()
                mock_runner.get_local_dir.return_value = tmp_path
                self.workflow._script_runner = mock_runner
                self.workflow._step_data = {
                    "archive_name": "test.tgz",
                    "archive_path": "/userdata/test.tgz",
                }

                (tmp_path / "test.tgz").write_bytes(b"fake archive content")

                result = self.workflow._step_download_results()
                assert result["success"] is True
                assert "test.tgz" in result["message"]


# ===================================================================
# WS-D: TestVnetmapParsing
# ===================================================================


class TestVnetmapParsing:
    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        self.workflow = WorkflowRegistry.get("vnetmap")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            }
        )
        self.workflow._output_callback = MagicMock()

    def test_convert_ip_format_range(self):
        assert self.workflow._convert_ip_format("10.0.0.[1-4]") == "10.0.0.{1..4}"

    def test_convert_ip_format_single(self):
        assert self.workflow._convert_ip_format("10.0.0.1") == "10.0.0.1"

    def test_convert_ip_format_empty(self):
        assert self.workflow._convert_ip_format("") == ""

    def test_parse_local_cfg_groups(self):
        cfg = "cnodes: 10.0.0.[1-4]\ndnodes: 10.0.1.[1-8]\n"
        cnodes, dnodes = self.workflow._parse_local_cfg(cfg)
        assert cnodes == "10.0.0.[1-4]"
        assert dnodes == "10.0.1.[1-8]"

    def test_parse_local_cfg_at_refs(self):
        cfg = "cnodesub0: 10.0.0.[1-2]\ncnodesub1: 10.0.0.[3-4]\ncnodes: @cnodesub0,@cnodesub1\n"
        cnodes, dnodes = self.workflow._parse_local_cfg(cfg)
        assert cnodes == "10.0.0.[1-2],10.0.0.[3-4]"
        assert dnodes is None

    def test_filter_output_tracebacks(self):
        raw = (
            "Starting vnetmap...\n"
            "Traceback (most recent call last):\n"
            '  File "foo.py", line 1\n'
            "subprocess.CalledProcessError: ...\n"
            "Switch discovery progress: 2/2 switches\n"
        )
        filtered = self.workflow._filter_vnetmap_output(raw)
        assert "Traceback" not in filtered
        assert "Switch discovery" in filtered

    def test_filter_output_clean(self):
        raw = "Switch discovery progress: 2/2 switches\npassed: 10 failed: 0\n"
        filtered = self.workflow._filter_vnetmap_output(raw)
        assert "passed: 10" in filtered

    def test_validate_results_partial(self):
        self.workflow._step_data = {
            "vnetmap_output": (
                "passed: 10 failed: 2\n"
                "failed nodes:\n"
                "10.0.0.5: failed to ssh to node\n"
                "10.0.0.6: permission denied\n"
            ),
        }
        result = self.workflow._step_validate_results()
        assert result["success"] is True
        data = self.workflow._step_data["validation_results"]
        assert data["ports_passed"] == 10
        assert data["ports_failed"] == 2
        assert len(data["failed_nodes"]) == 2
        assert len(data["recommendations"]) >= 2


# ===================================================================
# WS-D: TestSwitchConfigSteps
# ===================================================================


class TestSwitchConfigSteps:
    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        self.workflow = WorkflowRegistry.get("switch_config")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            }
        )
        self.workflow._output_callback = MagicMock()

    @patch("requests.get")
    def test_get_switch_ips_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"mgmt_ip": "10.0.0.10", "name": "sw1", "model": "SN2700"},
            {"mgmt_ip": "10.0.0.11", "name": "sw2", "model": "SN2700"},
        ]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ips, models = self.workflow._get_switch_ips_from_api()
        assert ips == ["10.0.0.10", "10.0.0.11"]
        assert models["10.0.0.10"] == "SN2700"

    @patch("requests.get")
    def test_get_switch_ips_v1_fallback(self, mock_get):
        from requests.exceptions import HTTPError

        err_response = MagicMock()
        err_response.status_code = 404
        first_error = HTTPError(response=err_response)

        ok_resp = MagicMock()
        ok_resp.json.return_value = [{"mgmt_ip": "10.0.0.10", "model": "SN2700"}]
        ok_resp.raise_for_status = MagicMock()

        mock_get.side_effect = [first_error, ok_resp]

        ips, models = self.workflow._get_switch_ips_from_api()
        assert ips == ["10.0.0.10"]

    @patch("requests.get")
    def test_get_switch_ips_all_fail(self, mock_get):
        mock_get.side_effect = ConnectionError("unreachable")

        ips, models = self.workflow._get_switch_ips_from_api()
        assert ips == []
        assert models == {}

    @patch("workflows.switch_config_workflow.run_interactive_ssh")
    @patch("workflows.switch_config_workflow.run_ssh_command")
    def test_detect_switch_type_onyx(self, mock_ssh, mock_issh):
        result = self.workflow._detect_switch_type("10.0.0.10", "admin", "pass", "ONYX SN2700", "")
        assert result == "onyx"
        mock_ssh.assert_not_called()

    @patch("workflows.switch_config_workflow.run_interactive_ssh")
    @patch("workflows.switch_config_workflow.run_ssh_command")
    def test_detect_switch_type_cumulus_nvue(self, mock_ssh, mock_issh):
        mock_ssh.return_value = (0, "/usr/bin/nv\nHAS_NV\nCUMULUS\n", "")
        result = self.workflow._detect_switch_type("10.0.0.10", "cumulus", "pass", "SN2700", "")
        assert result == "cumulus_nvue"

    @patch("workflows.switch_config_workflow.run_interactive_ssh")
    @patch("workflows.switch_config_workflow.run_ssh_command")
    def test_detect_switch_type_spectrum_default(self, mock_ssh, mock_issh):
        mock_ssh.return_value = (1, "", "")
        mock_issh.return_value = (1, "", "")
        result = self.workflow._detect_switch_type("10.0.0.10", "cumulus", "pass", "MSN2700", "")
        assert result == "cumulus_linux"


# ===================================================================
# WS-D: TestNetworkConfigParsing
# ===================================================================


class TestNetworkConfigParsing:
    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        self.workflow = WorkflowRegistry.get("network_config")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
            }
        )
        self.workflow._output_callback = MagicMock()

    def test_parse_local_cfg_basic(self):
        cfg = "cnodes: 10.0.0.1 10.0.0.2\ndnodes: 10.0.1.1\n"
        result = self.workflow._parse_local_cfg(cfg)
        assert result["cnodes"] == ["10.0.0.1", "10.0.0.2"]
        assert result["dnodes"] == ["10.0.1.1"]

    def test_parse_local_cfg_comments(self):
        cfg = "# This is a comment\ncnodes: 10.0.0.1\n# Another comment\n"
        result = self.workflow._parse_local_cfg(cfg)
        assert result["cnodes"] == ["10.0.0.1"]

    def test_parse_local_cfg_at_ref(self):
        cfg = "cnodesub0: 10.0.0.1 10.0.0.2\ncnodes: @cnodesub0\n"
        result = self.workflow._parse_local_cfg(cfg)
        assert result["cnodes"] == ["10.0.0.1", "10.0.0.2"]

    def test_parse_local_cfg_range(self):
        cfg = "cnodes: 10.0.0.[1-3]\n"
        result = self.workflow._parse_local_cfg(cfg)
        assert result["cnodes"] == ["10.0.0.1", "10.0.0.2", "10.0.0.3"]

    def test_parse_local_cfg_empty(self):
        result = self.workflow._parse_local_cfg("")
        assert result == {}

    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_run_on_all_nodes_clush(self, mock_ssh):
        self.workflow._step_data = {
            "all_nodes": {"cnode1": "172.16.3.4", "cnode2": "172.16.3.5"},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        mock_ssh.return_value = (
            0,
            "172.16.3.4: some data line1\n172.16.3.4: some data line2\n172.16.3.5: other data\n",
            "",
        )
        results = self.workflow._run_on_all_nodes("test cmd", "hostname")
        assert "cnode1" in results
        assert "cnode2" in results

    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_run_on_all_nodes_gateway_only(self, mock_ssh):
        self.workflow._step_data = {
            "all_nodes": {"gw": "10.0.0.1"},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        mock_ssh.return_value = (0, "gateway data", "")
        results = self.workflow._run_on_all_nodes("test cmd", "hostname")
        assert "gw" in results
        assert results["gw"] == "gateway data"

    @patch("workflows.network_config_workflow.run_ssh_command")
    def test_collect_configure_network_empty(self, mock_ssh):
        self.workflow._step_data = {
            "all_nodes": {},
            "host": "10.0.0.1",
            "user": "vastdata",
            "password": "pass",
        }
        results = self.workflow._run_on_all_nodes("collect cfg", "cat /etc/configure_network.py")
        assert results == {}


# ===================================================================
# WS-D: TestLogBundleSteps
# ===================================================================


class TestLogBundleSteps:
    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        self.workflow = WorkflowRegistry.get("log_bundle")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
            }
        )
        self.workflow._output_callback = MagicMock()
        self.workflow._script_runner = MagicMock()

    def test_discover_sizes_gb(self):
        result_mock = MagicMock(success=True, stdout="2.5G\t/var/log/vast")
        self.workflow._script_runner.check_prerequisites.return_value = (True, "OK")
        self.workflow._script_runner.execute_remote.return_value = result_mock

        result = self.workflow._step_discover_sizes()
        assert result["success"] is True
        total = self.workflow._step_data["total_size_mb"]
        assert abs(total - 7680) < 100  # ~2.5G * 3 dirs = ~7680MB

    def test_discover_sizes_mb(self):
        result_mock = MagicMock(success=True, stdout="500M\t/var/log/vast")
        self.workflow._script_runner.check_prerequisites.return_value = (True, "OK")
        self.workflow._script_runner.execute_remote.return_value = result_mock

        result = self.workflow._step_discover_sizes()
        assert result["success"] is True
        total = self.workflow._step_data["total_size_mb"]
        assert total >= 500  # at least 500MB (x3 dirs)

    def test_discover_sizes_kb(self):
        result_mock = MagicMock(success=True, stdout="100K\t/var/log/vast")
        self.workflow._script_runner.check_prerequisites.return_value = (True, "OK")
        self.workflow._script_runner.execute_remote.return_value = result_mock

        result = self.workflow._step_discover_sizes()
        assert result["success"] is True
        total = self.workflow._step_data["total_size_mb"]
        assert total < 1  # 100K * 3 dirs ~ 0.3MB

    def test_confirm_under_threshold(self):
        self.workflow._step_data["total_size_mb"] = 1000
        result = self.workflow._step_confirm_collection()
        assert result["success"] is True
        assert self.workflow._step_data["collection_confirmed"] is True

    def test_confirm_over_threshold(self):
        self.workflow._step_data["total_size_mb"] = 6000
        result = self.workflow._step_confirm_collection()
        assert result["success"] is False
        assert "too large" in result["message"].lower()

    @patch("subprocess.run")
    def test_verify_contents_success(self, mock_run, tmp_path):
        archive = tmp_path / "test.tar.gz"
        archive.write_bytes(b"fake")
        self.workflow._step_data["local_path"] = str(archive)

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "file1.log\nfile2.log\nfile3.log\n"
        mock_run.return_value = mock_result

        result = self.workflow._step_verify_contents()
        assert result["success"] is True
        assert "3 files" in result["message"]


# ===================================================================
# WS-D: TestSupportToolSteps
# ===================================================================


class TestSupportToolSteps:
    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        self.workflow = WorkflowRegistry.get("support_tool")
        self.workflow.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pass",
            }
        )
        self.emitted = []

        def capture_emit(level, message, details=None):
            self.emitted.append((level, message))

        self.workflow._output_callback = capture_emit
        self.workflow._script_runner = MagicMock()
        self.workflow._script_runner.get_local_dir.return_value = Path("/tmp/test")

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_run_support_tools_output_classification(self, mock_ssh):
        mock_ssh.return_value = (
            0,
            "ERROR: disk check failed\nWARNING: low memory\nPASSED all network checks\ninfo line\n",
            "",
        )
        result = self.workflow._step_run_support_tools()
        assert result["success"] is True
        levels = [e[0] for e in self.emitted]
        assert "error" in levels
        assert "warn" in levels
        assert "success" in levels

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_run_support_tools_empty_output(self, mock_ssh):
        mock_ssh.return_value = (0, "", "")
        result = self.workflow._step_run_support_tools()
        assert result["success"] is True

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_dir_found(self, mock_ssh):
        mock_ssh.side_effect = [
            (0, "cnode1", ""),  # hostname
            (0, "exists", ""),  # first dir check succeeds
            (0, "file1\nfile2", ""),  # tar output
            (0, "-rw-r--r-- 1 root root 1.5M archive.tgz", ""),  # verify
        ]
        result = self.workflow._step_create_archive()
        assert result["success"] is True

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_find_fallback(self, mock_ssh):
        mock_ssh.side_effect = [
            (0, "cnode1", ""),  # hostname
            (1, "", ""),  # dir check 1 fails
            (1, "", ""),  # dir check 2 fails
            (1, "", ""),  # dir check 3 fails
            (1, "", ""),  # dir check 4 fails
            (0, "/vast/data/support-found\n", ""),  # find succeeds
            (0, "file1", ""),  # tar output
            (0, "-rw-r--r-- 1 root root 500K archive.tgz", ""),  # verify
        ]
        result = self.workflow._step_create_archive()
        assert result["success"] is True

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_no_dir(self, mock_ssh):
        mock_ssh.side_effect = [
            (0, "cnode1", ""),  # hostname
            (1, "", ""),  # dir check 1 fails
            (1, "", ""),  # dir check 2 fails
            (1, "", ""),  # dir check 3 fails
            (1, "", ""),  # dir check 4 fails
            (0, "", ""),  # find returns nothing
            (0, "", ""),  # ls /vast/data
        ]
        result = self.workflow._step_create_archive()
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_create_archive_tar_failure(self, mock_ssh):
        mock_ssh.side_effect = [
            (0, "cnode1", ""),  # hostname
            (0, "exists", ""),  # dir check succeeds
            (1, "", "No such file or directory"),  # tar fails
        ]
        result = self.workflow._step_create_archive()
        assert result["success"] is False

    def test_download_results_success(self, tmp_path):
        mock_scp_module = MagicMock()

        with patch.dict("sys.modules", {"scp": mock_scp_module}):
            with patch("paramiko.SSHClient") as mock_ssh_class:
                mock_ssh = MagicMock()
                mock_ssh_class.return_value = mock_ssh

                mock_runner = MagicMock()
                mock_runner.get_local_dir.return_value = tmp_path
                self.workflow._script_runner = mock_runner
                self.workflow._step_data = {
                    "archive_name": "test.tgz",
                    "archive_path": "/userdata/test.tgz",
                }

                (tmp_path / "test.tgz").write_bytes(b"fake archive content")

                result = self.workflow._step_download_results()
                assert result["success"] is True
                assert "test.tgz" in result["message"]


# ===================================================================
# TestSwitchConfigJsonParsing — structured output formatting
# ===================================================================


class TestSwitchConfigJsonParsing:
    """Tests for _parse_command_output and helper methods that
    transform raw SSH output into structured JSON."""

    @pytest.fixture(autouse=True)
    def setup_workflow(self):
        from workflows.switch_config_workflow import SwitchConfigWorkflow

        self.wf = SwitchConfigWorkflow()

    # -- _try_parse_json --

    def test_parse_json_valid(self):
        raw = '{"enable": "off"}\n'
        result = self.wf._try_parse_json(raw.strip())
        assert result == {"enable": "off"}

    def test_parse_json_array(self):
        raw = '[{"name": "swp1"}, {"name": "swp2"}]'
        result = self.wf._try_parse_json(raw)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_parse_json_invalid_returns_string(self):
        raw = "not json at all"
        result = self.wf._try_parse_json(raw)
        assert result == raw

    # -- _try_parse_yaml --

    def test_parse_yaml_dict(self):
        raw = "bridge:\n  domain:\n    br_default:\n      vlan:\n        69: {}\n"
        result = self.wf._try_parse_yaml(raw)
        assert isinstance(result, dict)
        assert "bridge" in result

    def test_parse_yaml_list(self):
        raw = "- header:\n    model: msn3700\n- set:\n    bridge: {}\n"
        result = self.wf._try_parse_yaml(raw)
        assert isinstance(result, list)
        assert len(result) == 2

    def test_parse_yaml_invalid_returns_string(self):
        raw = "[unclosed bracket"
        result = self.wf._try_parse_yaml(raw)
        assert isinstance(result, str)

    def test_parse_yaml_plain_scalar_returns_string(self):
        raw = "just a plain string"
        result = self.wf._try_parse_yaml(raw)
        assert result == raw

    # -- _parse_ip_brief (link mode) --

    def test_parse_ip_brief_link(self):
        raw = (
            "lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>\n"
            "eth0             UP             aa:bb:cc:dd:ee:ff <BROADCAST,MULTICAST,UP,LOWER_UP>\n"
            "swp1             DOWN           11:22:33:44:55:66 <BROADCAST,MULTICAST>\n"
        )
        result = self.wf._parse_ip_brief(raw, addr_mode=False)
        assert len(result) == 3
        assert result[0]["name"] == "lo"
        assert result[0]["state"] == "UNKNOWN"
        assert result[0]["mac"] == "00:00:00:00:00:00"
        assert "LOOPBACK" in result[0]["flags"]
        assert result[1]["name"] == "eth0"
        assert result[1]["state"] == "UP"

    def test_parse_ip_brief_link_with_parent(self):
        raw = "vlan69@br_default UP  aa:bb:cc:dd:ee:ff <BROADCAST,MULTICAST,UP>\n"
        result = self.wf._parse_ip_brief(raw, addr_mode=False)
        assert len(result) == 1
        assert result[0]["parent"] == "br_default"

    def test_parse_ip_brief_skips_blank_and_short_lines(self):
        raw = "\n\nlo\n\neth0 UP aa:bb:cc:dd:ee:ff\n"
        result = self.wf._parse_ip_brief(raw, addr_mode=False)
        assert len(result) == 1
        assert result[0]["name"] == "eth0"

    # -- _parse_ip_brief (addr mode) --

    def test_parse_ip_brief_addr(self):
        raw = (
            "lo               UNKNOWN        127.0.0.1/8 ::1/128\n"
            "eth0             UP             10.0.0.10/24 fe80::1/64\n"
        )
        result = self.wf._parse_ip_brief(raw, addr_mode=True)
        assert len(result) == 2
        assert result[0]["addresses"] == ["127.0.0.1/8", "::1/128"]
        assert result[1]["addresses"] == ["10.0.0.10/24", "fe80::1/64"]

    # -- _parse_network_interfaces --

    def test_parse_network_interfaces(self):
        raw = (
            "# This file describes the network interfaces\n"
            "auto lo\n"
            "iface lo inet loopback\n"
            "\n"
            "auto eth0\n"
            "iface eth0 inet static\n"
            "    address 10.0.0.10/24\n"
            "    gateway 10.0.0.1\n"
        )
        result = self.wf._parse_network_interfaces(raw)
        assert "interfaces" in result
        assert "lo" in result["interfaces"]
        assert "eth0" in result["interfaces"]
        eth0 = result["interfaces"]["eth0"]
        assert eth0["method"] == "static"
        assert eth0["config"]["address"] == "10.0.0.10/24"
        assert eth0["config"]["gateway"] == "10.0.0.1"

    def test_parse_network_interfaces_no_comments(self):
        raw = "auto lo\niface lo inet loopback\n"
        result = self.wf._parse_network_interfaces(raw)
        assert "_comments" not in result

    # -- _parse_command_output (dispatch) --

    def test_dispatch_json_command(self):
        result = self.wf._parse_command_output("nv show router bgp --applied -o json", '{"enable": "on"}')
        assert result == {"enable": "on"}

    def test_dispatch_yaml_command(self):
        result = self.wf._parse_command_output("nv config show", "bridge:\n  domain: {}\n")
        assert isinstance(result, dict)
        assert "bridge" in result

    def test_dispatch_ip_link(self):
        result = self.wf._parse_command_output("ip -br link show", "eth0 UP aa:bb:cc:dd:ee:ff\n")
        assert isinstance(result, list)
        assert result[0]["name"] == "eth0"

    def test_dispatch_ip_addr(self):
        result = self.wf._parse_command_output("ip -br addr show", "eth0 UP 10.0.0.1/24\n")
        assert isinstance(result, list)
        assert result[0]["addresses"] == ["10.0.0.1/24"]

    def test_dispatch_etc_interfaces(self):
        raw = "auto lo\niface lo inet loopback\n"
        result = self.wf._parse_command_output("cat /etc/network/interfaces", raw)
        assert isinstance(result, dict)
        assert "lo" in result["interfaces"]

    def test_dispatch_unknown_command_returns_raw(self):
        raw = "some output\nmore lines\n"
        result = self.wf._parse_command_output("net show configuration", raw)
        assert result == raw

    # -- _build_structured_configs (end-to-end) --

    def test_build_structured_configs(self):
        configs = {
            "10.0.0.10": {
                "type": "cumulus_nvue",
                "hostname": "switch1",
                "commands": {
                    "nv show router bgp --applied -o json": '{"enable": "off"}',
                    "ip -br link show": "eth0 UP aa:bb:cc:dd:ee:ff\n",
                    "nv config show": "bridge:\n  domain: {}\n",
                },
            }
        }
        result = self.wf._build_structured_configs(configs)
        sw = result["10.0.0.10"]
        assert sw["hostname"] == "switch1"
        assert sw["commands"]["nv show router bgp --applied -o json"] == {"enable": "off"}
        assert isinstance(sw["commands"]["ip -br link show"], list)
        assert isinstance(sw["commands"]["nv config show"], dict)
