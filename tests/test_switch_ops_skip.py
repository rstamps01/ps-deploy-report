"""Switch operations when VMS has no switches (EBox field report, v1.6.1).

With no switches registered in VMS, switch_config failed with "No switches found
via VAST API" and vnetmap ran ``vnetmap.py -s`` with an empty argument, which
argparse rejected (rc=2) and the workflow misreported as a switch-password
failure.  Both now report SKIPPED with guidance instead of FAILED.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry  # noqa: E402

LOCAL_CFG = (
    "cnodesub0: 172.16.128.[4-7]\n"
    "dnodesub0: 172.16.128.[1-3]\n"
    "cnodes: @cnodesub0\n"
    "dnodes: @dnodesub0\n"
    "all: @cnodes,@dnodes\n"
)


class TestSwitchConfigSkipsWithoutSwitches:
    def test_no_api_switches_is_skipped_with_guidance(self):
        wf = WorkflowRegistry.get("switch_config")
        wf.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "username": "support",
                "password": "pw",
                "switch_user": "cumulus",
                "switch_password": "pw",
            }
        )
        wf._script_runner = MagicMock()
        with patch.object(wf, "_get_switch_ips_from_api", return_value=([], {})):
            result = wf._step_discover_switches()
        assert result["success"] is False
        assert result.get("skipped") is True
        assert "VMS" in result["message"]


class TestVnetmapSkipsEthWithoutSwitches:
    @patch("workflows.vnetmap_workflow.run_ssh_command", return_value=(0, LOCAL_CFG, ""))
    def test_eth_without_switches_is_skipped_not_run_with_empty_s(self, _mock_ssh):
        wf = WorkflowRegistry.get("vnetmap")
        wf.set_credentials(
            {
                "cluster_ip": "10.0.0.1",
                "node_user": "vastdata",
                "node_password": "pw",
                "switch_user": "cumulus",
                "switch_password": "pw",
            }
        )
        wf._step_data = {"remote_dir": "/tmp/vast_scripts"}
        wf._script_runner = MagicMock(DEFAULT_REMOTE_DIR="/tmp/vast_scripts")
        with patch.object(wf, "_get_switch_ips_from_api", return_value=[]), patch.object(
            wf, "_resolve_network_type", return_value="ETH"
        ):
            result = wf._step_generate_export_commands()
        assert result["success"] is False
        assert result.get("skipped") is True
        assert "vnetmap_command" not in wf._step_data

    def test_usage_error_is_not_reported_as_auth_failure(self):
        wf = WorkflowRegistry.get("vnetmap")
        assert (
            wf._is_auth_failure(
                "usage: vnetmap.py [-h] -s SWITCH_IPS\nvnetmap.py: error: argument -s/--switch-ips: expected one argument",
                "",
            )
            is False
        )


class _SkipAtStepOne:
    name = "Switch Extraction"

    def __init__(self):
        self.calls = []

    def get_steps(self):
        return [{"id": 1, "name": "Discover Switches"}, {"id": 2, "name": "Extract"}]

    def set_output_callback(self, cb):
        pass

    def set_credentials(self, creds):
        pass

    def run_step(self, step_id):
        self.calls.append(step_id)
        return {"success": False, "skipped": True, "message": "No switches registered in VMS"}


def _runner(ops):
    from oneshot_runner import OneShotRunner

    return OneShotRunner(
        selected_ops=ops,
        credentials={"cluster_ip": "10.0.0.1", "username": "a", "password": "b", "node_password": "c"},
    )


class TestOneShotRecordsSkipped:
    @patch("workflows.WorkflowRegistry")
    def test_skipped_step_records_skipped_with_reason(self, MockWR):
        wf = _SkipAtStepOne()
        MockWR.get.return_value = wf
        runner = _runner(["switch_config"])
        runner._run_operations()
        assert wf.calls == [1]
        assert runner._state.operation_results["switch_config"] == "skipped"
        assert "No switches registered in VMS" in runner._state.operation_details["switch_config"]

    @patch("workflows.WorkflowRegistry")
    def test_vnetmap_status_mirrors_to_raw_output_category(self, MockWR):
        MockWR.get.return_value = _SkipAtStepOne()
        runner = _runner(["vnetmap"])
        runner._run_operations()
        assert runner._state.operation_results["vnetmap"] == "skipped"
        assert runner._state.operation_results["vnetmap_output"] == "skipped"

    @patch("workflows.WorkflowRegistry")
    def test_failed_step_records_step_and_message(self, MockWR):
        wf = MagicMock()
        wf.name = "VAST Support Tools"
        wf.get_steps.return_value = [{"id": 3, "name": "Run Support Tools"}]
        wf.run_step.return_value = {"success": False, "message": "Support tools did not start (rc=127)"}
        MockWR.get.return_value = wf
        runner = _runner(["support_tool"])
        runner._run_operations()
        detail = runner._state.operation_details["support_tools"]
        assert "Step 3" in detail and "Run Support Tools" in detail and "rc=127" in detail
