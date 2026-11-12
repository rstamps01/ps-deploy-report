"""NET-7: VnetmapLLDPWorkflow steps with mocked SSH (deploy, readiness, show-mapping, validate, save)."""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry  # noqa: E402
from workflows.vnetmap_lldp_workflow import (  # noqa: E402
    LLDP_NOT_RUNNING_MESSAGE,
    MAPPING_FILE,
    MARKER,
    TOOL_COMMAND,
    VnetmapLLDPWorkflow,
    assess_lldp_readiness,
    parse_clush_lines,
    parse_restore_markers,
)

CLUSTER_IP = "192.0.2.10"
NODES = ["192.0.2.11", "192.0.2.12", "192.0.2.13"]


def _row(hostname, interface, switch, port, mgmt="192.0.2.11"):
    return {
        "hostname": hostname,
        "node_ip": "198.51.100.11",
        "node_mgmt_ip": mgmt,
        "interface": interface,
        "switch_name": switch,
        "switch_ip": switch,
        "port": port,
        "mac": "",
        "network": "A",
    }


def _parser_module(result):
    mod = types.ModuleType("vnetmap_lldp_parser")
    mod.parse_lldp_text = MagicMock(return_value=result)
    return mod


def _parsed(rows, operation_failed=False):
    return {
        "available": bool(rows),
        "topology": rows,
        "total_connections": len(rows),
        "switch_names": sorted({r["switch_name"] for r in rows}),
        "lldp_service_status": {"active": 3, "inactive": 3},
        "operation_failed": operation_failed,
    }


@pytest.fixture
def workflow(tmp_path):
    wf = VnetmapLLDPWorkflow()
    wf.set_output_dir(tmp_path)
    wf.set_credentials({"cluster_ip": CLUSTER_IP, "node_user": "vastdata", "node_password": "nodepass"})
    return wf


def _clush(states):
    return "".join(f"{node}: {state}\n" for node, state in states.items())


def _readiness_ssh(lldpd, lldpad, rpm, clush_rc=0):
    def fake(host, user, password, command, timeout=30, **kwargs):
        if command == "which clush":
            return clush_rc, "/usr/bin/clush\n" if clush_rc == 0 else "", ""
        if "is-active lldpd " in command:
            return 0, _clush(lldpd), ""
        if "is-active lldpad " in command:
            return 0, _clush(lldpad), ""
        if "rpm -q " in command:
            return 0, rpm, ""
        return 0, "", ""

    return fake


RPM_BOTH = "".join(f"{n}: lldpad-1.0.1-13.el8.x86_64\n{n}: lldpd-1.0.18-1.el8.x86_64\n" for n in NODES)
RPM_LLDPD_ONLY = "".join(f"{n}: package lldpad is not installed\n{n}: lldpd-1.0.18-1.el8.x86_64\n" for n in NODES)


class TestRegistration:
    def test_registered_as_vnetmap_lldp(self):
        wf = WorkflowRegistry.get("vnetmap_lldp")
        assert isinstance(wf, VnetmapLLDPWorkflow)
        ids = [w["id"] for w in WorkflowRegistry.list_all()]
        assert "vnetmap_lldp" in ids

    def test_steps(self):
        steps = VnetmapLLDPWorkflow().get_steps()
        assert [s["name"] for s in steps] == [
            "Deploy vnetmap_lldp.py",
            "Check LLDP Readiness",
            "Run show-mapping",
            "Validate Results",
            "Save Output",
        ]
        assert "~/logs/vnetmap_<timestamp>.log" in steps[2]["description"]
        assert MAPPING_FILE in steps[2]["description"]

    def test_prerequisites_need_node_credentials_only(self, workflow):
        assert workflow.validate_prerequisites()[0] is True
        wf = VnetmapLLDPWorkflow()
        wf.set_credentials({"cluster_ip": CLUSTER_IP, "switch_user": "cumulus", "switch_password": "x"})
        ok, msg = wf.validate_prerequisites()
        assert ok is False
        assert "node_password" in msg

    def test_invalid_step(self, workflow):
        assert workflow.run_step(99)["success"] is False


class TestDeploy:
    def test_deploys_vnetmap_lldp_with_skip_mkdir(self, workflow):
        with patch("workflows.vnetmap_lldp_workflow.ToolManager") as tm_cls:
            tm_cls.REMOTE_DIR = "/tmp/vast_scripts"
            tm = tm_cls.return_value
            tm._ensure_remote_dir.return_value = (True, "ok")
            tm.deploy_tool_to_cnode.return_value = (True, "Downloaded")
            result = workflow.run_step(1)
        assert result["success"] is True
        args, kwargs = tm.deploy_tool_to_cnode.call_args
        assert args[0] == "vnetmap_lldp.py"
        assert args[1] == CLUSTER_IP
        assert kwargs["skip_mkdir"] is True
        assert kwargs["port"] == 22

    def test_teleport_host_and_port(self, workflow):
        workflow.set_credentials(
            {
                "cluster_ip": CLUSTER_IP,
                "ssh_host": "127.0.0.1",
                "ssh_port": 40022,
                "node_user": "vastdata",
                "node_password": "nodepass",
            }
        )
        with patch("workflows.vnetmap_lldp_workflow.ToolManager") as tm_cls:
            tm = tm_cls.return_value
            tm._ensure_remote_dir.return_value = (True, "ok")
            tm.deploy_tool_to_cnode.return_value = (True, "ok")
            workflow.run_step(1)
        args, kwargs = tm.deploy_tool_to_cnode.call_args
        assert args[1] == "127.0.0.1"
        assert kwargs["port"] == 40022

    def test_deploy_failure(self, workflow):
        with patch("workflows.vnetmap_lldp_workflow.ToolManager") as tm_cls:
            tm = tm_cls.return_value
            tm._ensure_remote_dir.return_value = (True, "ok")
            tm.deploy_tool_to_cnode.return_value = (False, "Tool not in local cache")
            result = workflow.run_step(1)
        assert result["success"] is False
        assert "vnetmap_lldp.py" in result["message"]

    def test_missing_password(self):
        wf = VnetmapLLDPWorkflow()
        wf.set_credentials({"cluster_ip": CLUSTER_IP, "node_user": "vastdata"})
        assert wf.run_step(1)["success"] is False


class TestReadiness:
    def _run(self, workflow, lldpd, lldpad, rpm=RPM_BOTH, clush_rc=0):
        with patch(
            "workflows.vnetmap_lldp_workflow.run_ssh_command", side_effect=_readiness_ssh(lldpd, lldpad, rpm, clush_rc)
        ):
            return workflow.run_step(2)

    def test_all_nodes_active_passes(self, workflow):
        result = self._run(workflow, {n: "active" for n in NODES}, {n: "inactive" for n in NODES})
        assert result["success"] is True
        assert workflow._step_data["readiness"]["nodes_without_lldp"] == []
        assert "3/3" in result["message"]

    def test_partial_passes_and_lists_nodes_without_lldp(self, workflow):
        lldpd = {NODES[0]: "active", NODES[1]: "inactive", NODES[2]: "inactive"}
        lldpad = {NODES[0]: "inactive", NODES[1]: "active", NODES[2]: "unknown"}
        result = self._run(workflow, lldpd, lldpad)
        assert result["success"] is True
        readiness = workflow._step_data["readiness"]
        assert readiness["active_nodes"] == NODES[:2]
        assert readiness["nodes_without_lldp"] == [NODES[2]]
        assert "1 without LLDP" in result["message"]

    def test_zero_active_fails_with_customer_message(self, workflow):
        result = self._run(workflow, {n: "inactive" for n in NODES}, {n: "inactive" for n in NODES})
        assert result["success"] is False
        assert result["message"] == LLDP_NOT_RUNNING_MESSAGE
        assert "7347404806" in result["message"]

    def test_inactive_is_not_counted_as_active(self, workflow):
        result = self._run(workflow, {n: "inactive" for n in NODES}, {n: "failed" for n in NODES})
        assert result["success"] is False
        assert workflow._step_data["readiness"]["active_nodes"] == []

    def test_no_lldpad_package_fails(self, workflow):
        result = self._run(workflow, {n: "active" for n in NODES}, {n: "inactive" for n in NODES}, rpm=RPM_LLDPD_ONLY)
        assert result["success"] is False
        assert "lldpad package" in result["message"]
        assert "-f" in result["message"]
        assert "never" in result["message"]

    def test_one_node_with_lldpad_package_is_enough(self, workflow):
        rpm = f"{NODES[0]}: lldpad-1.0.1-13.el8.x86_64\n" + RPM_LLDPD_ONLY
        result = self._run(workflow, {n: "active" for n in NODES}, {n: "inactive" for n in NODES}, rpm=rpm)
        assert result["success"] is True

    def test_no_clush_fails(self, workflow):
        result = self._run(workflow, {}, {}, clush_rc=1)
        assert result["success"] is False
        assert "clush" in result["message"]

    def test_no_node_output_fails(self, workflow):
        result = self._run(workflow, {}, {}, rpm="")
        assert result["success"] is False
        assert "Could not read LLDP state" in result["message"]

    def test_commands_are_read_only_and_use_clush_all(self, workflow):
        fake = MagicMock(side_effect=_readiness_ssh({n: "active" for n in NODES}, {}, RPM_BOTH))
        with patch("workflows.vnetmap_lldp_workflow.run_ssh_command", fake):
            workflow.run_step(2)
        commands = [c.args[3] for c in fake.call_args_list]
        assert commands == [
            "which clush",
            "clush -a 'systemctl is-active lldpd || true'",
            "clush -a 'systemctl is-active lldpad || true'",
            "clush -a 'rpm -q lldpad lldpd || true'",
        ]


class TestReadinessHelpers:
    def test_parse_clush_lines_skips_meta_and_groups(self):
        out = f"{NODES[0]}: active\nclush: {NODES[1]}: exited with exit code 3\n{NODES[1]}: inactive\n\n"
        assert parse_clush_lines(out) == {NODES[0]: ["active"], NODES[1]: ["inactive"]}

    def test_assess_whole_token(self):
        result = assess_lldp_readiness(
            {NODES[0]: ["inactive"], NODES[1]: ["activating"]},
            {NODES[0]: ["inactive"], NODES[1]: ["inactive"]},
            {NODES[0]: ["lldpad-1.0.1"], NODES[1]: ["lldpad-1.0.1"]},
        )
        assert result["active_nodes"] == []
        assert result["reason"] == "not_running"

    def test_assess_lldpad_vs_lldpd_package_prefix(self):
        result = assess_lldp_readiness(
            {NODES[0]: ["active"]},
            {},
            {NODES[0]: ["package lldpad is not installed", "lldpd-1.0.18-1.el8.x86_64"]},
        )
        assert result["lldpad_package_nodes"] == []
        assert result["lldpd_package_nodes"] == [NODES[0]]
        assert result["reason"] == "no_lldpad_package"

    def test_nodes_sorted_numerically(self):
        result = assess_lldp_readiness({"192.0.2.100": ["active"], "192.0.2.9": ["active"]}, {}, {})
        assert result["nodes"] == ["192.0.2.9", "192.0.2.100"]


class TestShowMapping:
    def _run(self, workflow, stdout, rc=0):
        runner = MagicMock()
        runner.execute_remote.return_value = MagicMock(success=rc == 0, returncode=rc, stdout=stdout, stderr="")
        workflow._script_runner = runner
        return workflow.run_step(3), runner

    def test_runs_one_script_with_backup_and_trap(self, workflow):
        stdout = f"LLDP Connection Mapping:\n{MARKER} backup: saved existing {MAPPING_FILE}\n"
        stdout += f"{MARKER} restore: original {MAPPING_FILE} restored\n"
        result, runner = self._run(workflow, stdout)
        assert result["success"] is True
        assert runner.execute_remote.call_count == 1
        cmd = runner.execute_remote.call_args.kwargs["command"]
        assert "mktemp /tmp/vast_scripts/.switch_mapping_backup.XXXXXX" in cmd
        assert "trap _vlm_restore EXIT" in cmd
        assert cmd.count(TOOL_COMMAND) == 1
        restore = workflow._step_data["switch_mapping_restore"]
        assert restore["confirmed"] is True
        assert workflow._step_data["show_mapping_output"] == stdout

    def test_tool_failure_still_reports_restore(self, workflow):
        stdout = f"Operation failed - see logs for details\n{MARKER} restore: original {MAPPING_FILE} restored\n"
        result, _ = self._run(workflow, stdout, rc=1)
        assert result["success"] is False
        assert "rc=1" in result["message"]
        assert workflow._step_data["switch_mapping_restore"]["confirmed"] is True

    def test_backup_failure_fails_step(self, workflow):
        stdout = f"{MARKER} backup-failed: could not copy {MAPPING_FILE}; show-mapping not run\n"
        result, _ = self._run(workflow, stdout, rc=3)
        assert result["success"] is False
        assert "show-mapping was not run" in result["message"]

    def test_restore_failure_is_reported(self, workflow):
        stdout = (
            f"{MARKER} restore-failed: original {MAPPING_FILE} kept at /tmp/vast_scripts/.switch_mapping_backup.AB12\n"
        )
        result, _ = self._run(workflow, stdout)
        assert result["success"] is True
        assert "manual restore" in result["message"]
        assert workflow._step_data["switch_mapping_restore"]["restore_failed"] is True

    def test_parse_restore_markers_none_existed(self):
        status = parse_restore_markers(
            f"{MARKER} backup: no existing {MAPPING_FILE}\n"
            f"{MARKER} restore: removed {MAPPING_FILE} written by this run (none existed before)\n"
        )
        assert status["backup"].startswith("no existing")
        assert status["restore"].startswith("removed")
        assert status["confirmed"] is True


class TestValidate:
    def _run(self, workflow, parsed):
        workflow._step_data["show_mapping_output"] = "LLDP Connection Mapping:\n"
        workflow._step_data["readiness"] = {"nodes": NODES}
        mod = _parser_module(parsed)
        with patch.dict(sys.modules, {"vnetmap_lldp_parser": mod}):
            result = workflow.run_step(4)
        mod.parse_lldp_text.assert_called_once_with("LLDP Connection Mapping:\n")
        return result

    def test_two_ports_per_node_passes(self, workflow):
        rows = [
            _row("acme-cn1", "enp7s0f0", "ACME-SW-01", "swp1s0"),
            _row("acme-cn1", "enp7s0f1", "ACME-SW-02", "swp1s0"),
            _row("acme-dn1", "enp7s0f0", "ACME-SW-01", "Eth1/13/1", mgmt="192.0.2.12"),
            _row("acme-dn1", "enp7s0f1", "ACME-SW-02", "Eth1/13/1", mgmt="192.0.2.12"),
        ]
        result = self._run(workflow, _parsed(rows))
        assert result["success"] is True
        validation = workflow._step_data["validation_results"]
        assert validation["total_connections"] == 4
        assert validation["switch_names"] == ["ACME-SW-01", "ACME-SW-02"]
        assert validation["under_mapped_nodes"] == []
        assert validation["warnings"] == []

    def test_node_with_one_port_warns_not_fails(self, workflow):
        rows = [
            _row("acme-cn1", "enp7s0f0", "ACME-SW-01", "swp1s0"),
            _row("acme-cn1", "enp7s0f1", "ACME-SW-02", "swp1s0"),
            _row("acme-cn2", "enp7s0f0", "ACME-SW-01", "swp2s0", mgmt="192.0.2.12"),
        ]
        result = self._run(workflow, _parsed(rows))
        assert result["success"] is True
        assert workflow._step_data["validation_results"]["under_mapped_nodes"] == ["acme-cn2"]
        assert "warning" in result["message"]

    def test_zero_connections_fails(self, workflow):
        result = self._run(workflow, _parsed([]))
        assert result["success"] is False
        assert "No LLDP connections" in result["message"]

    def test_operation_failed_with_rows_warns(self, workflow):
        rows = [
            _row("acme-cn1", "enp7s0f0", "ACME-SW-01", "swp1s0"),
            _row("acme-cn1", "enp7s0f1", "ACME-SW-02", "swp1s0"),
        ]
        result = self._run(workflow, _parsed(rows, operation_failed=True))
        assert result["success"] is True
        assert workflow._step_data["validation_results"]["operation_failed"] is True

    def test_parser_missing_fails_cleanly(self, workflow):
        workflow._step_data["show_mapping_output"] = "x"
        with patch.dict(sys.modules, {"vnetmap_lldp_parser": None}):
            result = workflow.run_step(4)
        assert result["success"] is False
        assert "parser" in result["message"]


class TestSave:
    def test_filenames_and_contents(self, workflow, tmp_path):
        workflow._step_data.update(
            {
                "show_mapping_output": "LLDP Connection Mapping:\n| acme-cn1 | ...",
                "tool_command": TOOL_COMMAND,
                "readiness": {"nodes": NODES},
                "validation_results": {"total_connections": 2},
                "switch_mapping_restore": {"confirmed": True},
            }
        )
        result = workflow.run_step(5)
        assert result["success"] is True
        outputs = list(tmp_path.glob(f"vnetmap_lldp_output_{CLUSTER_IP}_*.txt"))
        results = list(tmp_path.glob(f"vnetmap_lldp_results_{CLUSTER_IP}_*.json"))
        assert len(outputs) == 1 and len(results) == 1
        assert outputs[0].read_text().startswith("LLDP Connection Mapping:")
        data = json.loads(results[0].read_text())
        assert data["source"] == "lldp"
        assert data["tool_command"] == TOOL_COMMAND
        assert data["switch_mapping_restore"] == {"confirmed": True}
        assert "~/logs/vnetmap_<timestamp>.log" in data["remote_log"]
        assert "nodepass" not in results[0].read_text()
        assert not list(tmp_path.glob("vnetmap_output_*"))
