"""NET-7: port-map source selection truth table and the vnetmap ``switch_auth_failed_all`` flag."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows.topology_source import normalize_topology_source, select_topology_source  # noqa: E402
from workflows.vnetmap_workflow import VnetmapWorkflow  # noqa: E402

ALL_FAILED = {"success": False, "switch_auth_failed_all": True}
PARTIAL_AUTH = {"success": False, "switch_auth_failed_all": False}
VNETMAP_OK = {"success": True, "switch_auth_failed_all": False}


class TestSelectTopologySource:
    @pytest.mark.parametrize(
        "requested,has_creds,outcome,expected",
        [
            ("auto", True, None, "vnetmap"),
            ("auto", False, None, "lldp"),
            ("auto", True, ALL_FAILED, "lldp"),
            ("auto", False, ALL_FAILED, "lldp"),
            ("auto", True, PARTIAL_AUTH, None),
            ("auto", True, VNETMAP_OK, None),
            ("auto", True, {"success": False}, None),
            ("vnetmap", True, None, "vnetmap"),
            ("vnetmap", False, None, "vnetmap"),
            ("vnetmap", True, ALL_FAILED, None),
            ("vnetmap", True, PARTIAL_AUTH, None),
            ("vnetmap", True, VNETMAP_OK, None),
            ("lldp", True, None, "lldp"),
            ("lldp", False, None, "lldp"),
            ("lldp", True, ALL_FAILED, "lldp"),
        ],
    )
    def test_truth_table(self, requested, has_creds, outcome, expected):
        assert select_topology_source(requested, has_creds, outcome) == expected

    def test_default_vnetmap_outcome_is_before_run(self):
        assert select_topology_source("auto", True) == "vnetmap"

    @pytest.mark.parametrize("requested", ["", None, "  AUTO ", "Auto"])
    def test_empty_and_case_mean_auto(self, requested):
        assert normalize_topology_source(requested) == "auto"
        assert select_topology_source(requested, False) == "lldp"

    def test_unknown_value_is_auto_with_warning(self, caplog):
        import logging

        with caplog.at_level(logging.WARNING):
            assert select_topology_source("switch-login", True) == "vnetmap"
            assert select_topology_source("switch-login", True, ALL_FAILED) == "lldp"
        assert any("Unknown port map source" in r.getMessage() for r in caplog.records)

    def test_truthy_non_bool_flag_does_not_switch(self):
        assert select_topology_source("auto", True, {"switch_auth_failed_all": "yes"}) is None


SWITCHES = ["192.0.2.101", "192.0.2.102"]


def _vnetmap_workflow(switch_ips=SWITCHES, network_type="ETH"):
    wf = VnetmapWorkflow()
    wf.set_credentials({"cluster_ip": "192.0.2.10", "node_user": "vastdata", "node_password": "nodepass"})
    wf._step_data = {
        "remote_dir": "/tmp/vast_scripts",
        "network_type": network_type,
        "export_commands": ["export MLX_IPS='192.0.2.101,192.0.2.102'"],
        "vnetmap_command": "python3 vnetmap.py -s $MLX_IPS -i $cnodes_ips -u cumulus -p 'pw1'",
        "switch_password": "pw1",
        "switch_password_candidates": ["pw1"],
        "switch_ips": list(switch_ips),
    }
    runner = MagicMock()
    runner.DEFAULT_REMOTE_DIR = "/tmp/vast_scripts"
    wf._script_runner = runner
    return wf, runner


class TestVnetmapSwitchAuthFailedAll:
    def test_every_switch_failed(self):
        wf, runner = _vnetmap_workflow()
        stderr = (
            "WARNING Unable to determine suitable switch API for 192.0.2.101\n"
            "WARNING Unable to determine suitable switch API for 192.0.2.102\n"
            "Exception: Failed to connect to switch 192.0.2.101\n"
        )
        runner.execute_remote.return_value = MagicMock(success=False, returncode=1, stdout="", stderr=stderr)
        result = wf._step_run_vnetmap()
        assert result["success"] is False
        assert result["switch_auth_failed_all"] is True
        assert wf._step_data["switch_auth_failed_all"] is True

    def test_one_switch_failed_is_not_all(self):
        wf, runner = _vnetmap_workflow()
        stderr = "WARNING Unable to determine suitable switch API for 192.0.2.101\n"
        runner.execute_remote.return_value = MagicMock(success=False, returncode=1, stdout="", stderr=stderr)
        assert wf._step_run_vnetmap()["switch_auth_failed_all"] is False

    def test_ip_prefix_does_not_count_as_another_switch(self):
        wf, runner = _vnetmap_workflow(switch_ips=["192.0.2.1", "192.0.2.10"])
        stderr = "Authentication failed for 192.0.2.10\n"
        runner.execute_remote.return_value = MagicMock(success=False, returncode=1, stdout="", stderr=stderr)
        assert wf._step_run_vnetmap()["switch_auth_failed_all"] is False

    def test_single_switch_auth_failure_without_ip(self):
        wf, runner = _vnetmap_workflow(switch_ips=["192.0.2.101"])
        runner.execute_remote.return_value = MagicMock(
            success=False, returncode=1, stdout="", stderr="Authentication failed"
        )
        assert wf._step_run_vnetmap()["switch_auth_failed_all"] is True

    def test_non_auth_failure(self):
        wf, runner = _vnetmap_workflow()
        runner.execute_remote.return_value = MagicMock(success=False, returncode=255, stdout="", stderr="no route")
        assert wf._step_run_vnetmap()["switch_auth_failed_all"] is False

    def test_success(self):
        wf, runner = _vnetmap_workflow()
        runner.execute_remote.return_value = MagicMock(success=True, returncode=0, stdout="ok", stderr="")
        assert wf._step_run_vnetmap()["switch_auth_failed_all"] is False

    def test_infiniband_never_sets_flag(self):
        wf, runner = _vnetmap_workflow(network_type="IB")
        wf._step_data["vnetmap_command"] = "python3 vnetmap.py -i $cnodes_ips -ib"
        runner.execute_remote.return_value = MagicMock(
            success=False, returncode=1, stdout="", stderr="Permission denied"
        )
        assert wf._step_run_vnetmap()["switch_auth_failed_all"] is False

    def test_flag_feeds_selector(self):
        wf, runner = _vnetmap_workflow()
        stderr = "".join(f"Unable to determine suitable switch API for {ip}\n" for ip in SWITCHES)
        runner.execute_remote.return_value = MagicMock(success=False, returncode=1, stdout="", stderr=stderr)
        assert select_topology_source("auto", True, wf._step_run_vnetmap()) == "lldp"
        assert select_topology_source("vnetmap", True, wf._step_run_vnetmap()) is None
