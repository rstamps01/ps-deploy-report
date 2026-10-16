"""Regression tests for SupportToolWorkflow on EBox clusters (EBox field report, v1.6.1).

On EBox the VMS container wrapper lives in the CNode container directory
(``/vast/data/C-4200/vms.sh``), not ``/vast/data/vms.sh``.  v1.6.1 hardcoded the
legacy path, got ``rc=127 No such file or directory`` and still reported Step 3
as completed, so Step 4 failed with a generic "output directory not found".
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry  # noqa: E402

EBOX_WRAPPER = "/vast/data/C-4200/vms.sh"
EBOX_SCRIPT = "/vast/data/C-4200/vast_support_tools.py"


def _workflow(**creds):
    wf = WorkflowRegistry.get("support_tool")
    base = {"cluster_ip": "10.0.0.1", "node_user": "vastdata", "node_password": "pass"}
    base.update(creds)
    wf.set_credentials(base)
    wf._script_runner = MagicMock()
    wf._step_data = {}
    emitted = []
    wf.set_output_callback(lambda level, msg, details=None: emitted.append((level, msg)))
    return wf, emitted


class TestContainerWrapperDiscovery:
    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_discovers_ebox_wrapper_in_container_dir(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.return_value = (0, f"{EBOX_WRAPPER}\n", "")
        wrapper, script, base_dir = wf._resolve_container_paths()
        assert wrapper == EBOX_WRAPPER
        assert script == EBOX_SCRIPT
        assert base_dir == "/vast/data/C-4200"

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_falls_back_to_legacy_wrapper_when_probe_finds_nothing(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.return_value = (0, "", "")
        wrapper, script, base_dir = wf._resolve_container_paths()
        assert wrapper == "/vast/data/vms.sh"
        assert script == "/vast/data/vast_support_tools.py"
        assert base_dir == "/vast/data"

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_discovery_is_cached_across_steps(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.return_value = (0, f"{EBOX_WRAPPER}\n", "")
        wf._resolve_container_paths()
        wf._resolve_container_paths()
        assert mock_ssh.call_count == 1

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_cached_wrapper_not_reused_for_another_cluster(self, mock_ssh):
        """Advanced Ops reuses one workflow instance; a new cluster must be re-probed."""
        wf, _ = _workflow()
        mock_ssh.return_value = (0, f"{EBOX_WRAPPER}\n", "")
        wf._resolve_container_paths()
        wf.set_credentials({"cluster_ip": "10.9.9.9", "node_user": "vastdata", "node_password": "pass"})
        mock_ssh.return_value = (0, "/vast/data/vms.sh\n", "")
        wrapper, _script, _base = wf._resolve_container_paths()
        assert wrapper == "/vast/data/vms.sh"

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_failed_probe_is_not_cached(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.return_value = (0, "", "")
        wf._resolve_container_paths()
        mock_ssh.return_value = (0, f"{EBOX_WRAPPER}\n", "")
        wrapper, _script, _base = wf._resolve_container_paths()
        assert wrapper == EBOX_WRAPPER

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_probe_runs_on_vms_host_in_tech_port_mode(self, mock_ssh):
        wf, _ = _workflow(cluster_ip="192.168.2.2", vms_internal_ip="172.16.128.5")
        mock_ssh.return_value = (0, f"{EBOX_WRAPPER}\n", "")
        wf._resolve_container_paths()
        call = mock_ssh.call_args_list[0]
        assert call.args[0] == "172.16.128.5"
        assert call.kwargs.get("jump_host") == "192.168.2.2"


class TestSetPermissionsUsesContainerDir:
    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_direct_mode_copies_script_into_ebox_container_dir(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.side_effect = [
            (0, f"{EBOX_WRAPPER}\n", ""),  # wrapper probe
            (0, "", ""),  # sudo cp
            (0, "", ""),  # chmod
            (0, f"-rwxr-xr-x 1 vastdata vastdata 1 {EBOX_SCRIPT}", ""),  # verify
        ]
        result = wf._step_set_permissions()
        assert result["success"] is True
        copy_cmd = mock_ssh.call_args_list[1].args[3]
        assert EBOX_SCRIPT in copy_cmd


class TestRunSupportToolsFailureRules:
    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_uses_discovered_ebox_wrapper_and_script(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.side_effect = [(0, f"{EBOX_WRAPPER}\n", ""), (0, "PASSED all checks", "")]
        result = wf._step_run_support_tools()
        assert result["success"] is True
        run_cmd = mock_ssh.call_args_list[-1].args[3]
        assert run_cmd == f"{EBOX_WRAPPER} {EBOX_SCRIPT} inspect"

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_findings_mentioning_timeouts_do_not_fail_step(self, mock_ssh):
        """inspect reports node problems in its output; only the adapter's own marker means timeout."""
        wf, _ = _workflow()
        findings = (
            "ERROR: ssh: connect to host 172.16.128.9 port 22: Connection timed out\n"
            "ERROR: /vast/data/vast_support_tools.py: check nic_state: No such file or directory for enp7s0f2\n"
            "Check summary: 48 passed, 3 failed"
        )
        mock_ssh.side_effect = [(0, "/vast/data/vms.sh\n", ""), (1, findings, "")]
        result = wf._step_run_support_tools()
        assert result["success"] is True

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_no_vms_container_is_a_launch_failure(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.side_effect = [
            (0, "/vast/data/vms.sh\n", ""),
            (1, "Error: No such container: /vast/data/vast_support_tools.py", ""),
        ]
        result = wf._step_run_support_tools()
        assert result["success"] is False

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_missing_wrapper_rc127_fails_step(self, mock_ssh):
        """The exact field-report signature must fail Step 3 instead of reporting success."""
        wf, emitted = _workflow()
        mock_ssh.side_effect = [
            (0, "", ""),  # wrapper probe finds nothing -> legacy path
            (127, "bash: /vast/data/vms.sh: No such file or directory", ""),
        ]
        result = wf._step_run_support_tools()
        assert result["success"] is False
        assert "127" in result["message"]
        assert any("EBox" in msg for _lvl, msg in emitted)

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_timeout_fails_step(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.side_effect = [(0, "/vast/data/vms.sh\n", ""), (1, "", "SSH command timed out after 600s")]
        result = wf._step_run_support_tools()
        assert result["success"] is False
        assert "timed out" in result["message"].lower()

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_nonzero_with_empty_output_fails_step(self, mock_ssh):
        wf, _ = _workflow()
        mock_ssh.side_effect = [(0, "/vast/data/vms.sh\n", ""), (2, "", "")]
        result = wf._step_run_support_tools()
        assert result["success"] is False

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_nonzero_with_findings_still_continues(self, mock_ssh):
        """inspect exits non-zero when it reports findings; those runs must still be archived."""
        wf, _ = _workflow()
        mock_ssh.side_effect = [
            (0, "/vast/data/vms.sh\n", ""),
            (1, "WARNING: NTP not synchronized on 1 node\nCheck summary: 51 passed", ""),
        ]
        result = wf._step_run_support_tools()
        assert result["success"] is True


class TestCreateArchiveEbox:
    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_checks_ebox_container_output_dir_first(self, mock_ssh):
        wf, _ = _workflow()
        wf._step_data = {"container_base_dir": "/vast/data/C-4200"}
        mock_ssh.side_effect = [
            (0, "cnode1", ""),  # hostname
            (0, "exists", ""),  # /vast/data/C-4200/support-checks
            (0, "file1", ""),  # tar
            (0, "-rw-r--r-- 1 root root 1.0M /userdata/x.tgz", ""),  # ls
        ]
        result = wf._step_create_archive()
        assert result["success"] is True
        assert "/vast/data/C-4200/support-checks" in mock_ssh.call_args_list[1].args[3]

    @patch("workflows.support_tool_workflow.run_ssh_command")
    def test_not_found_message_carries_step3_exit_code(self, mock_ssh):
        wf, _ = _workflow()
        wf._step_data = {"support_tools_rc": 127, "support_tools_error": "vms.sh: No such file or directory"}
        mock_ssh.side_effect = [
            (0, "cnode1", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "", ""),
            (0, "total 0", ""),
        ]
        result = wf._step_create_archive()
        assert result["success"] is False
        assert "rc=127" in result["message"]
