"""
Unit tests for VAST As-Built Report Generator Health Checker Module.

Covers HealthCheckResult, HealthCheckReport, HealthChecker (tier-1 API checks,
orchestration, serialisation), and the Prometheus text-format parser.
"""

import json
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from health_checker import CancelledError, HealthCheckReport, HealthCheckResult, HealthChecker

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_api_handler():
    handler = MagicMock()
    handler.cluster_ip = "10.0.0.1"
    handler._make_api_request = MagicMock(return_value=None)
    handler.get_prometheus_metrics = MagicMock(return_value="")
    return handler


@pytest.fixture
def checker(mock_api_handler):
    return HealthChecker(api_handler=mock_api_handler)


def _cluster_data(**overrides):
    base = {
        "name": "test-cluster",
        "sw_version": "5.3.0",
        "ssd_raid_state": "HEALTHY",
        "nvram_raid_state": "HEALTHY",
        "memory_raid_state": "HEALTHY",
        "state": "ONLINE",
        "enabled": True,
        "leader_state": "STEADY",
        "expansion_state": None,
        "upgrade_state": None,
        "physical_space_in_use_percent": 42.5,
        "used_handles_percent": 15.0,
        "license": "Enterprise",
    }
    base.update(overrides)
    return [base]


# ===================================================================
# TestHealthCheckResult
# ===================================================================


class TestHealthCheckResult:
    def test_create_pass_result(self):
        r = HealthCheckResult(
            check_name="Test Check",
            category="api",
            status="pass",
            message="All good",
        )
        assert r.status == "pass"
        assert r.check_name == "Test Check"
        assert r.category == "api"
        assert r.message == "All good"
        assert r.details is None
        assert r.duration_seconds == 0.0

    def test_create_fail_result(self):
        r = HealthCheckResult(
            check_name="Failing Check",
            category="node_ssh",
            status="fail",
            message="Something went wrong",
            details={"reason": "disk offline"},
        )
        assert r.status == "fail"
        assert r.details == {"reason": "disk offline"}


# ===================================================================
# TestHealthChecker — API check methods
# ===================================================================


class TestHealthChecker:
    # --- Cluster RAID Health -------------------------------------------

    def test_check_cluster_raid_health_pass(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data()
        result = checker._check_cluster_raid_health()
        assert result.status == "pass"
        assert "HEALTHY" in result.message

    def test_check_cluster_raid_health_fail(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(ssd_raid_state="DEGRADED")
        result = checker._check_cluster_raid_health()
        assert result.status == "fail"
        assert "DEGRADED" in result.message

    def test_check_cluster_raid_health_error(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = None
        result = checker._check_cluster_raid_health()
        assert result.status == "error"
        assert "Failed to retrieve" in result.message

    # --- CNode Status --------------------------------------------------

    def test_check_cnode_status_all_active(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"name": "cnode-1", "status": "ACTIVE", "enabled": True},
            {"name": "cnode-2", "status": "ACTIVE", "enabled": True},
        ]
        result = checker._check_cnode_status()
        assert result.status == "pass"
        assert "2 CNodes" in result.message

    def test_check_cnode_status_inactive(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"name": "cnode-1", "status": "ACTIVE", "enabled": True},
            {"name": "cnode-2", "status": "INACTIVE", "enabled": True},
        ]
        result = checker._check_cnode_status()
        assert result.status == "fail"
        assert "cnode-2" in result.message

    # --- Active Alarms -------------------------------------------------

    def test_check_alarms_no_alarms(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = []
        result = checker._check_active_alarms()
        assert result.status == "pass"
        assert "No unresolved" in result.message

    def test_check_alarms_critical(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"severity": "CRITICAL", "resolved": False, "message": "Disk failure"},
        ]
        result = checker._check_active_alarms()
        assert result.status == "fail"
        assert "1 unresolved" in result.message

    def test_check_alarms_404(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = None
        result = checker._check_active_alarms()
        assert result.status == "skipped"
        assert "not available" in result.message

    # --- VIP Pools -----------------------------------------------------

    def test_check_vip_pools_configured(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"name": "pool-1", "enabled": True},
        ]
        result = checker._check_vip_pools()
        assert result.status == "pass"
        assert "1 enabled" in result.message

    def test_check_vip_pools_empty(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = []
        result = checker._check_vip_pools()
        assert result.status == "fail"
        assert "No VIP pools" in result.message

    # --- Capacity ------------------------------------------------------

    def test_check_capacity_ok(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(physical_space_in_use_percent=55.0)
        result = checker._check_capacity()
        assert result.status == "pass"
        assert "55.0%" in result.message

    def test_check_capacity_warning(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(physical_space_in_use_percent=92.3)
        result = checker._check_capacity()
        assert result.status == "warning"
        assert "92.3%" in result.message

    # --- License -------------------------------------------------------

    def test_check_license_present(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(license="Enterprise")
        result = checker._check_license()
        assert result.status == "pass"
        assert "active" in result.message.lower()

    def test_check_license_missing(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(license=None)
        result = checker._check_license()
        assert result.status == "warning"
        assert "No license" in result.message

    # --- DNode Status --------------------------------------------------

    def test_check_dnode_status_active(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"name": "dnode-1", "status": "ACTIVE", "enabled": True},
            {"name": "dnode-2", "status": "ACTIVE", "enabled": True},
        ]
        result = checker._check_dnode_status()
        assert result.status == "pass"
        assert "2 DNodes" in result.message

    # --- Expansion State -----------------------------------------------

    def test_check_expansion_state_active(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(expansion_state="EXPANDING")
        result = checker._check_expansion_state()
        assert result.status == "warning"
        assert "EXPANDING" in result.message

    # ===================================================================
    # Orchestration tests
    # ===================================================================

    def test_run_api_checks_all_pass(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data()
        mock_api_handler.get_prometheus_metrics.return_value = ""
        results = checker.run_api_checks()
        assert len(results) > 0
        for r in results:
            assert isinstance(r, HealthCheckResult)

    def test_run_api_checks_cancel(self, checker, mock_api_handler):
        cancel_event = threading.Event()
        cancel_event.set()
        checker.cancel_event = cancel_event

        with pytest.raises(CancelledError):
            checker.run_api_checks()

    def test_run_all_checks_tier1(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data()
        mock_api_handler.get_prometheus_metrics.return_value = ""
        report = checker.run_all_checks(tiers=[1])
        assert isinstance(report, HealthCheckReport)
        assert 1 in report.tiers_run
        assert 2 not in report.tiers_run
        assert report.cluster_name == "test-cluster"

    def test_run_all_checks_tier12_no_ssh(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data()
        mock_api_handler.get_prometheus_metrics.return_value = ""
        checker.ssh_config = None
        report = checker.run_all_checks(tiers=[1, 2])
        assert 1 in report.tiers_run
        assert 2 in report.tiers_run
        ssh_results = [r for r in report.results if r.category == "node_ssh"]
        assert len(ssh_results) == 0

    # ===================================================================
    # Output / serialisation tests
    # ===================================================================

    def test_save_json(self, checker, tmp_path):
        report = HealthCheckReport(
            cluster_ip="10.0.0.1",
            cluster_name="test-cluster",
            cluster_version="5.3.0",
            timestamp="2026-03-19T00:00:00Z",
            results=[
                HealthCheckResult(
                    check_name="Dummy",
                    category="api",
                    status="pass",
                    message="ok",
                )
            ],
            summary={"pass": 1, "fail": 0, "warning": 0, "skipped": 0, "error": 0},
            manual_checklist=list(HealthChecker.MANUAL_CHECKLIST),
            tiers_run=[1],
        )
        filepath = checker.save_json(report, output_dir=str(tmp_path))
        assert Path(filepath).exists()
        data = json.loads(Path(filepath).read_text())
        assert data["cluster_name"] == "test-cluster"
        assert len(data["results"]) == 1

    def test_manual_checklist_always_present(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data()
        mock_api_handler.get_prometheus_metrics.return_value = ""
        report = checker.run_all_checks(tiers=[1])
        assert len(report.manual_checklist) == len(HealthChecker.MANUAL_CHECKLIST)
        for item in report.manual_checklist:
            assert "item" in item
            assert "description" in item

    def test_to_dict(self, checker):
        report = HealthCheckReport(
            cluster_ip="10.0.0.1",
            cluster_name="test-cluster",
            cluster_version="5.3.0",
            timestamp="2026-03-19T00:00:00Z",
            results=[],
            summary={},
            manual_checklist=[],
            tiers_run=[1],
        )
        d = HealthChecker.to_dict(report)
        assert isinstance(d, dict)
        assert d["cluster_name"] == "test-cluster"
        assert d["tiers_run"] == [1]


# ===================================================================
# TestPrometheusParser
# ===================================================================


class TestPrometheusParser:
    @pytest.fixture
    def parser(self, mock_api_handler):
        return HealthChecker(api_handler=mock_api_handler)

    def test_parse_simple_metric(self, parser):
        text = "metric_name 42.0"
        results = parser._parse_prometheus_metrics(text)
        assert len(results) == 1
        assert results[0]["name"] == "metric_name"
        assert results[0]["value"] == 42.0
        assert results[0]["labels"] == {}

    def test_parse_metric_with_labels(self, parser):
        text = 'metric_name{label="value"} 42.0'
        results = parser._parse_prometheus_metrics(text)
        assert len(results) == 1
        assert results[0]["name"] == "metric_name"
        assert results[0]["labels"] == {"label": "value"}
        assert results[0]["value"] == 42.0

    def test_parse_comments_ignored(self, parser):
        text = "# HELP some_metric A help string\n" "# TYPE some_metric gauge\n" "some_metric 7.0\n"
        results = parser._parse_prometheus_metrics(text)
        assert len(results) == 1
        assert results[0]["name"] == "some_metric"
        assert results[0]["value"] == 7.0

    def test_parse_empty_input(self, parser):
        results = parser._parse_prometheus_metrics("")
        assert results == []


# ===================================================================
# TestRemediationReport
# ===================================================================


class TestRemediationReport:
    @pytest.fixture
    def checker_with_handler(self, mock_api_handler):
        return HealthChecker(api_handler=mock_api_handler)

    def _make_report(self, results, summary=None):
        if summary is None:
            summary = {"pass": 0, "fail": 0, "warning": 0, "skipped": 0, "error": 0}
            for r in results:
                summary[r.status] = summary.get(r.status, 0) + 1
        return HealthCheckReport(
            cluster_ip="10.0.0.1",
            cluster_name="test-cluster",
            cluster_version="5.3.0",
            timestamp="2026-03-19T00:00:00Z",
            results=results,
            summary=summary,
            manual_checklist=list(HealthChecker.MANUAL_CHECKLIST),
            tiers_run=[1],
        )

    def test_generate_remediation_report_with_failures(self, checker_with_handler, tmp_path):
        results = [
            HealthCheckResult(
                check_name="CNode Status",
                category="api",
                status="fail",
                message="1 CNode INACTIVE: cnode-2",
                details={"inactive": ["cnode-2"]},
                timestamp="2026-03-19T00:00:00Z",
            ),
        ]
        report = self._make_report(results)
        filepath = checker_with_handler.generate_remediation_report(report, output_dir=str(tmp_path))
        text = Path(filepath).read_text()
        assert "CRITICAL FINDINGS" in text
        assert "CNode Status" in text
        assert "cnode-2" in text

    def test_generate_remediation_report_all_pass(self, checker_with_handler, tmp_path):
        results = [
            HealthCheckResult(
                check_name="Cluster RAID Health",
                category="api",
                status="pass",
                message="All RAID arrays HEALTHY",
                timestamp="2026-03-19T00:00:00Z",
            ),
        ]
        report = self._make_report(results)
        filepath = checker_with_handler.generate_remediation_report(report, output_dir=str(tmp_path))
        text = Path(filepath).read_text()
        assert "PASSING CHECKS" in text
        assert "END OF REPORT" in text

    def test_remediation_report_includes_severity(self, checker_with_handler, tmp_path):
        results = [
            HealthCheckResult(
                check_name="CNode Status",
                category="api",
                status="fail",
                message="1 CNode INACTIVE",
                timestamp="2026-03-19T00:00:00Z",
            ),
            HealthCheckResult(
                check_name="Capacity",
                category="api",
                status="warning",
                message="Capacity at 92%",
                timestamp="2026-03-19T00:00:00Z",
            ),
        ]
        report = self._make_report(results)
        filepath = checker_with_handler.generate_remediation_report(report, output_dir=str(tmp_path))
        text = Path(filepath).read_text()
        assert "CRITICAL" in text
        assert "Severity:" in text

    def test_remediation_report_includes_timestamps(self, checker_with_handler, tmp_path):
        ts = "2026-03-19T12:34:56Z"
        results = [
            HealthCheckResult(
                check_name="VIP Pools",
                category="api",
                status="fail",
                message="No VIP pools configured",
                timestamp=ts,
            ),
        ]
        report = self._make_report(results)
        filepath = checker_with_handler.generate_remediation_report(report, output_dir=str(tmp_path))
        text = Path(filepath).read_text()
        assert ts in text
        assert "Timestamp:" in text


# ===================================================================
# TestCorrelationEngine
# ===================================================================


class TestCorrelationEngine:
    @pytest.fixture
    def checker_with_handler(self, mock_api_handler):
        return HealthChecker(api_handler=mock_api_handler)

    def test_correlate_cnode_dnode_down(self, checker_with_handler):
        results = [
            HealthCheckResult(
                check_name="CNode Status",
                category="api",
                status="fail",
                message="1 CNode INACTIVE",
                details={"inactive": ["cnode-2"]},
            ),
            HealthCheckResult(
                check_name="DNode Status",
                category="api",
                status="fail",
                message="1 DNode INACTIVE",
                details={"inactive": ["dnode-3"]},
            ),
        ]
        correlations = checker_with_handler._correlate_findings(results)
        assert "CNode Status" in correlations
        assert "DNode Status" in correlations
        assert any("chassis" in c.lower() for c in correlations["CNode Status"])

    def test_correlate_no_findings(self, checker_with_handler):
        results = [
            HealthCheckResult(
                check_name="CNode Status", category="api", status="pass", message="All CNodes ACTIVE"
            ),
            HealthCheckResult(
                check_name="DNode Status", category="api", status="pass", message="All DNodes ACTIVE"
            ),
        ]
        correlations = checker_with_handler._correlate_findings(results)
        assert correlations == {}

    def test_correlate_leader_inactive(self, checker_with_handler):
        results = [
            HealthCheckResult(
                check_name="CNode Status",
                category="api",
                status="fail",
                message="1 CNode INACTIVE",
                details={"inactive": ["cnode-1"]},
            ),
            HealthCheckResult(
                check_name="Leader State",
                category="api",
                status="fail",
                message="Leader cnode-1 is INACTIVE",
                details={"leader_cnode": "cnode-1"},
            ),
        ]
        correlations = checker_with_handler._correlate_findings(results)
        assert "Leader State" in correlations
        assert any("leader" in c.lower() for c in correlations["Leader State"])


# ===================================================================
# TestSSHTier2Checks
# ===================================================================


class TestSSHTier2Checks:
    @pytest.fixture
    def ssh_checker(self, mock_api_handler):
        ssh_config = {"username": "vastdata", "password": "secret", "cnode_ip": "10.0.0.10"}
        return HealthChecker(api_handler=mock_api_handler, ssh_config=ssh_config)

    @patch("health_checker.run_ssh_command")
    def test_management_ping_success(self, mock_ssh, ssh_checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"name": "cnode-1", "ipmi_ip": "10.0.0.50"},
        ]
        mock_ssh.return_value = (0, "PING 10.0.0.50 ... 0% packet loss", "")
        result = ssh_checker._check_management_ping("10.0.0.10", "vastdata", "secret")
        assert result.status == "pass"
        assert result.check_name == "Management Ping"

    @patch("health_checker.run_ssh_command")
    def test_management_ping_timeout(self, mock_ssh, ssh_checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"name": "cnode-1", "ipmi_ip": "10.0.0.50"},
        ]
        mock_ssh.side_effect = Exception("timed out")
        result = ssh_checker._check_management_ping("10.0.0.10", "vastdata", "secret")
        assert result.status == "error"
        assert "timed out" in result.message

    def test_management_ping_respects_cancel(self, ssh_checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [
            {"name": "cnode-1", "ipmi_ip": "10.0.0.50"},
        ]
        ssh_checker.cancel_event = threading.Event()
        ssh_checker.cancel_event.set()
        with pytest.raises(CancelledError):
            ssh_checker.run_node_ssh_checks()

    @patch("health_checker.run_ssh_command")
    def test_node_memory_check_pass(self, mock_ssh, ssh_checker):
        mock_ssh.return_value = (0, "Mem:          32000       8000      20000        500       4000      23000", "")
        result = ssh_checker._check_memory_usage("10.0.0.10", "vastdata", "secret")
        assert result.status == "pass"
        assert result.check_name == "Memory Usage"


# ===================================================================
# TestSSHTier3Checks
# ===================================================================


class TestSSHTier3Checks:
    @pytest.fixture
    def switch_checker(self, mock_api_handler):
        switch_config = {"username": "cumulus", "password": "secret", "switch_ips": ["10.0.1.1"]}
        return HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)

    @patch("health_checker.run_ssh_command")
    def test_mlag_status_pass(self, mock_ssh, switch_checker):
        mlag_output = (
            "peer-alive          : true\n"
            "backup-active       : true\n"
            "mlag-id             : 1\n"
        )
        mock_ssh.return_value = (0, mlag_output, "")
        result = switch_checker._check_mlag_status("10.0.1.1", "cumulus", "secret")
        assert result.status == "pass"
        assert "peer-alive" in result.message

    @patch("health_checker.run_ssh_command")
    def test_mlag_status_fail(self, mock_ssh, switch_checker):
        mlag_output = (
            "peer-alive          : false\n"
            "backup-active       : false\n"
        )
        mock_ssh.return_value = (0, mlag_output, "")
        result = switch_checker._check_mlag_status("10.0.1.1", "cumulus", "secret")
        assert result.status == "fail"
        assert "peer-alive" in result.message

    @patch("health_checker.run_ssh_command")
    def test_switch_ntp_pass(self, mock_ssh, switch_checker):
        ntp_output = (
            "     remote           refid      st t when poll reach   delay   offset  jitter\n"
            "==============================================================================\n"
            "*ntp.ubuntu.com  17.253.34.123    2 u  532 1024  377   12.345   -0.678   1.234\n"
        )
        mock_ssh.return_value = (0, ntp_output, "")
        result = switch_checker._check_switch_ntp("10.0.1.1", "cumulus", "secret")
        assert result.status == "pass"
        assert "NTP peers found" in result.message

    def test_run_switch_checks_no_config(self, mock_api_handler):
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=None)
        results = checker.run_switch_ssh_checks()
        assert results == []
