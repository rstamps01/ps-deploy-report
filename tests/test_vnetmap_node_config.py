"""vnetmap on EBox / L3 clusters (field run on a 4-EBox L3/VXLAN cluster, v1.6.2).

vnetmap.py read ``/etc/vast-configure_network.py-params.ini`` on every node,
could not parse it, then crashed with ``IndexError`` (rc=1). The workflow now
checks that file with vnetmap's own rules first, skips with the reason when
vnetmap cannot parse it, passes ``-l3`` on L3 clusters, and lists converged
EBox hosts once in ``-i``.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows import WorkflowRegistry  # noqa: E402

CDBOX_CFG = (
    "cnodesub0: 172.16.128.[4-7]\n"
    "dnodesub0: 172.16.128.[1-3]\n"
    "cnodes: @cnodesub0\n"
    "dnodes: @dnodesub0\n"
    "all: @cnodes,@dnodes\n"
)
EBOX_CFG = (
    "cnodesub0: 172.27.255.[4-7]\n"
    "dnodesub0: 172.27.255.[4-5]\n"
    "dnodesub1: 172.27.255.[6-7]\n"
    "cnodes: @cnodesub0\n"
    "dnodes: @dnodesub0,@dnodesub1\n"
    "all: @cnodes,@dnodes\n"
)
GOOD_INI = "internal_interfaces=enp1s0f0,enp1s0f1\neth_mtu=9000\ndata_vlan=69\n"
L3_INI = GOOD_INI + "l3_network_mode=True\n"
NO_VLAN_INI = "internal_interfaces=enp1s0f0,enp1s0f1\neth_mtu=9000\nl3_network_mode=True\n"


def _workflow():
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
    return wf


def _generate(wf, local_cfg, ini_result, net_type="ETH"):
    def _ssh(host, user, password, command, **kwargs):
        if "configure_network" in command:
            return ini_result
        return (0, local_cfg, "")

    with patch("workflows.vnetmap_workflow.run_ssh_command", side_effect=_ssh), patch.object(
        wf, "_get_switch_ips_from_api", return_value=["10.0.0.10", "10.0.0.11"]
    ), patch.object(wf, "_resolve_network_type", return_value=net_type):
        return wf._step_generate_export_commands()


def test_l2_config_runs_without_l3_flag():
    wf = _workflow()
    result = _generate(wf, CDBOX_CFG, (0, GOOD_INI, ""))
    assert result["success"] is True
    assert " -l3" not in wf._step_data["vnetmap_command"]


def test_l3_config_adds_l3_flag():
    wf = _workflow()
    result = _generate(wf, CDBOX_CFG, (0, L3_INI, ""))
    assert result["success"] is True
    assert wf._step_data["vnetmap_command"].endswith(" -l3")


def test_config_missing_data_vlan_is_skipped_with_reason():
    wf = _workflow()
    result = _generate(wf, CDBOX_CFG, (0, NO_VLAN_INI, ""))
    assert result["success"] is False
    assert result.get("skipped") is True
    assert "data_vlan" in result["message"]
    assert "vnetmap_command" not in wf._step_data


def test_spaced_ini_keys_are_treated_as_unparseable():
    """vnetmap splits on whitespace and looks for ``key=``; ``key = value`` is not found."""
    wf = _workflow()
    result = _generate(wf, CDBOX_CFG, (0, "internal_interfaces = enp1s0f0\neth_mtu = 9000\ndata_vlan = 69\n", ""))
    assert result.get("skipped") is True
    assert "internal_interfaces" in result["message"]


def test_unreadable_config_does_not_block_vnetmap():
    wf = _workflow()
    result = _generate(wf, CDBOX_CFG, (1, "", "sudo: a password is required"))
    assert result["success"] is True
    assert "vnetmap_command" in wf._step_data


def test_ebox_hosts_are_passed_once():
    wf = _workflow()
    result = _generate(wf, EBOX_CFG, (0, GOOD_INI, ""))
    assert result["success"] is True
    assert "-i $cnodes_ips " in wf._step_data["vnetmap_command"]
    assert "$dnodes_ips" not in wf._step_data["vnetmap_command"]


def test_cdbox_keeps_cnodes_and_dnodes():
    wf = _workflow()
    _generate(wf, CDBOX_CFG, (0, GOOD_INI, ""))
    assert "-i $cnodes_ips,$dnodes_ips " in wf._step_data["vnetmap_command"]


def test_ib_config_accepts_ib_mtu():
    wf = _workflow()
    result = _generate(wf, CDBOX_CFG, (0, "internal_interfaces=ib0,ib1\nib_mtu=4092\ndata_vlan=69\n", ""), "IB")
    assert result["success"] is True
