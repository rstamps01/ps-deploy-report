"""Pre-validation of the vperfsanity VIP pool (EBox field run: default 'main' did not exist)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oneshot_runner import OneShotRunner  # noqa: E402

POOLS = [
    {"name": "gateway-1", "role": "REPLICATION"},
    {"name": "vippool-1", "role": "PROTOCOLS"},
    {"name": "vippool-comet", "role": "PROTOCOLS"},
]


def _runner(vip_pool="main", ops=None):
    return OneShotRunner(
        selected_ops=ops or ["vperfsanity"],
        credentials={"cluster_ip": "10.0.0.1", "username": "admin", "password": "pw", "vip_pool": vip_pool},
    )


def _api(vips=None, pools=None):
    api = MagicMock()

    def _request(endpoint, params=None):
        if endpoint.startswith("vips/"):
            return vips
        if endpoint.startswith("vippools/"):
            return pools
        return None

    api._make_api_request.side_effect = _request
    return api


def _check(runner, api):
    with patch("api_handler.create_vast_api_handler", return_value=api):
        return runner._validate_vip_pool()


def test_pool_with_assigned_vips_passes():
    api = _api(vips=[{"ip": "1.1.1.1", "cnode": "cnode-1"}, {"ip": "1.1.1.2", "cnode": "cnode-2"}])
    check = _check(_runner("vippool-1"), api)
    assert check.status == "pass"
    assert "vippool-1" in check.message
    assert "2 CNode" in check.message
    assert api._make_api_request.call_args_list[0].kwargs["params"] == {"vippool__name": "vippool-1"}


def test_missing_pool_fails_and_lists_protocol_pools():
    check = _check(_runner("main"), _api(vips=[], pools=POOLS))
    assert check.status == "fail"
    assert "'main' not found" in check.message
    assert "vippool-1, vippool-comet" in check.message
    assert "gateway-1" not in check.message


def test_pool_without_cnode_assignment_fails():
    check = _check(_runner("vippool-1"), _api(vips=[{"ip": "1.1.1.1", "cnode": None}], pools=POOLS))
    assert check.status == "fail"
    assert "none of its VIPs are assigned to a CNode" in check.message


def test_api_error_is_warning_not_failure():
    check = _check(_runner("main"), _api(vips=None))
    assert check.status == "warn"
    assert "Could not verify" in check.message


def test_blank_pool_falls_back_to_default_name():
    api = _api(vips=[{"cnode": "cnode-1"}])
    _check(_runner(""), api)
    assert api._make_api_request.call_args_list[0].kwargs["params"] == {"vippool__name": "main"}


def test_prevalidation_runs_vip_check_only_for_vperfsanity():
    for ops, expected in ((["vperfsanity"], True), (["support_tool"], False)):
        runner = _runner(ops=ops)
        with (
            patch.object(runner, "_validate_cluster_api", return_value=MagicMock(name="api")),
            patch.object(runner, "_validate_node_ssh", return_value=MagicMock()),
            patch.object(runner, "_validate_internet_access", return_value=MagicMock()),
            patch.object(runner, "_validate_tool_freshness", return_value=MagicMock()),
            patch.object(runner, "_validate_vip_pool") as vip_check,
        ):
            vip_check.return_value = MagicMock(name="vip")
            runner.run_prevalidation()
        assert vip_check.called is expected
