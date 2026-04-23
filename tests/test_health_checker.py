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
        assert result.status == "warning"
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
        assert result.status == "warning"
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

    def test_check_license_via_license_state(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(license=None, license_state="Active")
        result = checker._check_license()
        assert result.status == "pass"
        assert "active" in result.message.lower()

    def test_check_license_via_is_licensed(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(license=None, is_licensed=True)
        result = checker._check_license()
        assert result.status == "pass"

    def test_check_license_via_license_type(self, checker, mock_api_handler):
        mock_api_handler._make_api_request.return_value = _cluster_data(license=None, license_type="Perpetual")
        result = checker._check_license()
        assert result.status == "pass"
        assert "perpetual" in result.message.lower()

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
            HealthCheckResult(check_name="CNode Status", category="api", status="pass", message="All CNodes ACTIVE"),
            HealthCheckResult(check_name="DNode Status", category="api", status="pass", message="All DNodes ACTIVE"),
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


# ===================================================================
# TestSSHTier3Checks
# ===================================================================


class TestSSHTier3Checks:
    @pytest.fixture
    def switch_checker(self, mock_api_handler):
        switch_config = {"username": "cumulus", "password": "secret", "switch_ips": ["10.0.1.1"]}
        return HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)

    @patch("health_checker.run_interactive_ssh")
    def test_mlag_status_pass(self, mock_pty, switch_checker):
        mlag_output = "peer-alive          : true\n" "backup-active       : true\n" "mlag-id             : 1\n"
        mock_pty.return_value = (0, mlag_output, "")
        result = switch_checker._check_mlag_status("10.0.1.1", "cumulus", "secret")
        assert result.status == "pass"
        assert "peer-alive" in result.message

    @patch("health_checker.run_interactive_ssh")
    def test_mlag_status_fail(self, mock_pty, switch_checker):
        mlag_output = "peer-alive          : false\n" "backup-active       : false\n"
        mock_pty.return_value = (0, mlag_output, "")
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


# ===================================================================
# RM-2: per-switch password resolution (password_by_ip)
# ===================================================================


class TestSwitchSSHPerIPPassword:
    """Verify ``run_switch_ssh_checks`` resolves each switch's password from
    the ``password_by_ip`` map when present, and falls back to the primary
    ``password`` when a given IP isn't in the map.

    Background: the one-shot pipeline probes each switch IP with every
    candidate password before launching health checks, and records the
    winning password per IP on ``self._switch_password_by_ip``.  Without
    RM-2 the health checker ignored that map and re-used
    ``switch_ssh_config['password']`` for every check, mis-authenticating
    any switch on a different default (e.g. a spare leaf on ``VastData1!``
    while the pair runs ``Vastdata1!``).
    """

    def _patch_checks(self, checker):
        """Replace the three per-switch check functions with recorders so we
        can assert exactly which (ip, password) tuples were used without
        spinning up fake SSH."""
        seen = []

        def recorder(check_name):
            def _fn(host, username, password, *, switch_os="cumulus", **kwargs):
                seen.append((check_name, host, password))
                return HealthCheckResult(
                    check_name=check_name,
                    category="switch_ssh",
                    status="pass",
                    message=f"{check_name} on {host}",
                    details={"host": host, "switch_os": switch_os},
                    timestamp=checker._now(),
                    duration_seconds=0.0,
                )

            return _fn

        checker._detect_switch_type = lambda *a, **k: "cumulus"
        checker._check_mlag_status = recorder("MLAG Status")
        checker._check_switch_ntp = recorder("Switch NTP")
        checker._check_switch_config_backup = recorder("Switch Config Backup")
        return seen

    def test_password_by_ip_applied_per_switch(self, mock_api_handler):
        switch_config = {
            "username": "cumulus",
            "password": "primary-pw",
            "switch_ips": ["10.0.1.1", "10.0.1.2", "10.0.1.3"],
            "password_by_ip": {
                "10.0.1.1": "alpha-pw",
                "10.0.1.2": "beta-pw",
                # 10.0.1.3 is intentionally omitted -> must fall back.
            },
        }
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        seen = self._patch_checks(checker)
        checker.run_switch_ssh_checks()

        by_host = {host: pw for (_n, host, pw) in seen}
        assert by_host["10.0.1.1"] == "alpha-pw"
        assert by_host["10.0.1.2"] == "beta-pw"
        assert by_host["10.0.1.3"] == "primary-pw"

    def test_no_map_falls_back_to_primary(self, mock_api_handler):
        switch_config = {
            "username": "cumulus",
            "password": "primary-pw",
            "switch_ips": ["10.0.1.1", "10.0.1.2"],
        }
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        seen = self._patch_checks(checker)
        checker.run_switch_ssh_checks()

        assert {pw for (_n, _h, pw) in seen} == {"primary-pw"}

    def test_malformed_map_is_ignored_safely(self, mock_api_handler):
        """A non-dict ``password_by_ip`` (e.g. leftover list from a bad call
        site) must not crash the checker — it should be treated as empty
        and every switch falls back to the primary password."""
        switch_config = {
            "username": "cumulus",
            "password": "primary-pw",
            "switch_ips": ["10.0.1.1"],
            "password_by_ip": ["not", "a", "dict"],
        }
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        seen = self._patch_checks(checker)
        checker.run_switch_ssh_checks()
        assert {pw for (_n, _h, pw) in seen} == {"primary-pw"}


# ===================================================================
# RM-13: password_candidates probing (Reporter tile parity)
# ===================================================================


class TestSwitchSSHPasswordCandidates:
    """Verify ``run_switch_ssh_checks`` probes ``password_candidates`` on
    behalf of the Reporter tile, which hasn't pre-resolved per-switch
    passwords the way the Test Suite tile does.

    The Reporter tile populates ``switch_ssh_config['password_candidates']``
    with the output of :func:`utils.switch_password_candidates.resolve_
    switch_password_candidates` so a switch using a published default
    (e.g. ``Cumu1usLinux!``) authenticates regardless of what the
    operator typed in Connection Settings.
    """

    def _patch_checks(self, checker):
        """Same recorder helper as TestSwitchSSHPerIPPassword."""
        seen = []

        def recorder(check_name):
            def _fn(host, username, password, *, switch_os="cumulus", **kwargs):
                seen.append((check_name, host, password))
                return HealthCheckResult(
                    check_name=check_name,
                    category="switch_ssh",
                    status="pass",
                    message=f"{check_name} on {host}",
                    details={"host": host, "switch_os": switch_os},
                    timestamp=checker._now(),
                    duration_seconds=0.0,
                )

            return _fn

        checker._detect_switch_type = lambda *a, **k: "cumulus"
        checker._check_mlag_status = recorder("MLAG Status")
        checker._check_switch_ntp = recorder("Switch NTP")
        checker._check_switch_config_backup = recorder("Switch Config Backup")
        return seen

    def test_candidates_probe_picks_winning_password_per_switch(self, mock_api_handler):
        """Switch 10.0.1.1 accepts Vastdata1!, 10.0.1.2 accepts VastData1! —
        the probe must map each switch to its winning password."""
        switch_config = {
            "username": "cumulus",
            "password": "primary-pw",
            "switch_ips": ["10.0.1.1", "10.0.1.2"],
            "password_candidates": ["primary-pw", "Vastdata1!", "VastData1!"],
        }
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        seen = self._patch_checks(checker)

        # Simulate the probe: 10.0.1.1 rejects primary-pw, accepts Vastdata1!.
        # 10.0.1.2 rejects primary-pw, rejects Vastdata1!, accepts VastData1!.
        def fake_run_ssh_command(host, user, password, command, timeout=15, **kwargs):
            allow = {
                "10.0.1.1": "Vastdata1!",
                "10.0.1.2": "VastData1!",
            }
            if allow.get(host) == password:
                return 0, host, ""
            return 255, "", "Permission denied (publickey,password)"

        # RM-15: probe SSH I/O was lifted to ``utils.switch_ssh_probe`` so
        # the mocks now target that module.  ``HealthChecker._probe_switch_
        # password`` is a thin delegator as of v1.5.6.
        with patch("utils.switch_ssh_probe.run_ssh_command", side_effect=fake_run_ssh_command), patch(
            "utils.switch_ssh_probe.run_interactive_ssh", return_value=(255, "", "denied")
        ):
            checker.run_switch_ssh_checks()

        by_host = {host: pw for (_n, host, pw) in seen}
        assert by_host["10.0.1.1"] == "Vastdata1!"
        assert by_host["10.0.1.2"] == "VastData1!"

    def test_candidates_fall_back_to_primary_when_all_rejected(self, mock_api_handler):
        """When no candidate authenticates, each check still runs with the
        primary password.  The checks themselves will report ``fail`` but
        the probe must not swallow the whole run."""
        switch_config = {
            "username": "cumulus",
            "password": "primary-pw",
            "switch_ips": ["10.0.1.1"],
            "password_candidates": ["nope1", "nope2"],
        }
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        seen = self._patch_checks(checker)

        # RM-15: probe SSH I/O moved to utils.switch_ssh_probe.
        with patch("utils.switch_ssh_probe.run_ssh_command", return_value=(255, "", "Permission denied")), patch(
            "utils.switch_ssh_probe.run_interactive_ssh", return_value=(255, "", "denied")
        ):
            checker.run_switch_ssh_checks()

        assert {pw for (_n, _h, pw) in seen} == {"primary-pw"}

    def test_candidates_skipped_when_password_by_ip_already_has_entry(self, mock_api_handler):
        """When the caller already pre-resolved a winning password for a
        switch (Test Suite tile path), don't re-probe that switch — the
        pre-resolved value wins and the probe isn't called for it."""
        switch_config = {
            "username": "cumulus",
            "password": "primary-pw",
            "switch_ips": ["10.0.1.1", "10.0.1.2"],
            "password_by_ip": {"10.0.1.1": "preresolved-pw"},
            "password_candidates": ["Vastdata1!", "VastData1!"],
        }
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        seen = self._patch_checks(checker)

        calls: list = []

        def fake_run_ssh_command(host, user, password, command, timeout=15, **kwargs):
            calls.append(host)
            if host == "10.0.1.2" and password == "Vastdata1!":
                return 0, host, ""
            return 255, "", "denied"

        # RM-15: probe SSH I/O moved to utils.switch_ssh_probe.
        with patch("utils.switch_ssh_probe.run_ssh_command", side_effect=fake_run_ssh_command), patch(
            "utils.switch_ssh_probe.run_interactive_ssh", return_value=(255, "", "denied")
        ):
            checker.run_switch_ssh_checks()

        # 10.0.1.1 must not be probed — its password was pre-resolved.
        assert "10.0.1.1" not in calls
        by_host = {host: pw for (_n, host, pw) in seen}
        assert by_host["10.0.1.1"] == "preresolved-pw"
        assert by_host["10.0.1.2"] == "Vastdata1!"

    def test_empty_candidates_noop(self, mock_api_handler):
        """No candidates -> no probe, behaviour identical to RM-2 path."""
        switch_config = {
            "username": "cumulus",
            "password": "primary-pw",
            "switch_ips": ["10.0.1.1"],
            "password_candidates": [],
        }
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        seen = self._patch_checks(checker)

        with patch("health_checker.run_ssh_command") as mock_ssh:
            checker.run_switch_ssh_checks()
            mock_ssh.assert_not_called()

        assert {pw for (_n, _h, pw) in seen} == {"primary-pw"}


# ===================================================================
# WS-B: TestResolveIPs
# ===================================================================


class TestResolveIPs:
    def test_resolve_cnode_ip_from_config(self, mock_api_handler):
        hc = HealthChecker(
            api_handler=mock_api_handler,
            ssh_config={"cnode_ip": "192.168.1.50", "username": "vastdata", "password": "pass"},
        )
        assert hc._resolve_cnode_ip() == "192.168.1.50"
        mock_api_handler._make_api_request.assert_not_called()

    def test_resolve_cnode_ip_from_api(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [{"mgmt_ip": "10.0.0.1"}]
        hc = HealthChecker(
            api_handler=mock_api_handler,
            ssh_config={"username": "vastdata", "password": "pass"},
        )
        assert hc._resolve_cnode_ip() == "10.0.0.1"

    def test_resolve_cnode_ip_api_error(self, mock_api_handler):
        mock_api_handler._make_api_request.side_effect = RuntimeError("API down")
        hc = HealthChecker(
            api_handler=mock_api_handler,
            ssh_config={"username": "vastdata", "password": "pass"},
        )
        assert hc._resolve_cnode_ip() is None

    def test_resolve_switch_ips_from_config(self, mock_api_handler):
        hc = HealthChecker(
            api_handler=mock_api_handler,
            switch_ssh_config={"switch_ips": ["10.0.0.20", "10.0.0.21"], "username": "cumulus", "password": "pass"},
        )
        assert hc._resolve_switch_ips() == ["10.0.0.20", "10.0.0.21"]

    def test_resolve_switch_ips_api_fallback(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [{"mgmt_ip": "10.0.0.10"}]
        hc = HealthChecker(
            api_handler=mock_api_handler,
            switch_ssh_config={"username": "cumulus", "password": "pass"},
        )
        assert hc._resolve_switch_ips() == ["10.0.0.10"]


# ===================================================================
# WS-B: TestAPICheckBranches
# ===================================================================


class TestAPICheckBranches:
    def _make_hc(self, mock_api, cluster_dict):
        hc = HealthChecker(
            api_handler=mock_api,
            ssh_config={"cnode_ip": "10.0.0.1", "username": "vastdata", "password": "pass"},
        )
        hc._cluster_cache = cluster_dict
        return hc

    def test_check_replication_no_dr(self, mock_api_handler):
        hc = self._make_hc(mock_api_handler, {"dr_enabled": False, "name": "c"})
        r = hc._check_replication()
        assert r.status == "pass"
        assert "not enabled" in r.message.lower()

    def test_check_replication_dr_no_policies(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = []
        hc = self._make_hc(mock_api_handler, {"dr_enabled": True, "name": "c"})
        r = hc._check_replication()
        assert r.status == "warning"
        assert "no protection policies" in r.message.lower()

    def test_check_replication_dr_unhealthy(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [{"name": "p1", "status": "DEGRADED"}]
        hc = self._make_hc(mock_api_handler, {"dr_enabled": True, "name": "c"})
        r = hc._check_replication()
        assert r.status == "warning"
        assert "not healthy" in r.message.lower()

    def test_check_snapshots_none(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = None
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_snapshots()
        assert r.status == "skipped"

    def test_check_snapshots_failed(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [{"name": "snap-a", "status": "failed"}]
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_snapshots()
        assert r.status == "warning"
        assert "failed" in r.message.lower()

    def test_check_snapshots_404(self, mock_api_handler):
        mock_api_handler._make_api_request.side_effect = Exception("404 page not found")
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_snapshots()
        assert r.status == "skipped"

    def test_check_quotas_none(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = None
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_quotas()
        assert r.status == "skipped"

    def test_check_quotas_blocked(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = [{"name": "u1", "is_blocked": True}]
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_quotas()
        assert r.status == "warning"
        assert "blocked" in r.message.lower()

    def test_check_call_home_via_callhomeconfigs_registered(self, mock_api_handler):
        """Primary path: callhomeconfigs/ returns cloud_registered=True."""
        cfg = [
            {
                "cloud_registered": True,
                "log_enabled": True,
                "bundle_enabled": False,
                "cloud_enabled": False,
                "customer": "AcmeCo",
            }
        ]
        mock_api_handler._make_api_request.return_value = cfg
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_call_home_status()
        assert r.status == "pass"
        assert "enabled" in r.message.lower()
        assert "cloud registered" in r.message.lower()
        assert "logging active" in r.message.lower()

    def test_check_call_home_via_callhomeconfigs_disabled(self, mock_api_handler):
        """callhomeconfigs/ exists but all flags are False."""
        cfg = [{"cloud_registered": False, "log_enabled": False, "bundle_enabled": False, "cloud_enabled": False}]
        mock_api_handler._make_api_request.return_value = cfg
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_call_home_status()
        assert r.status == "warning"
        assert "not enabled" in r.message.lower()

    def test_check_call_home_enabled(self, mock_api_handler):
        hc = self._make_hc(mock_api_handler, {"call_home_enabled": True, "name": "c"})
        r = hc._check_call_home_status()
        assert r.status == "pass"
        assert "enabled" in r.message.lower()

    def test_check_call_home_ssp_enabled(self, mock_api_handler):
        hc = self._make_hc(mock_api_handler, {"ssp_enabled": True, "name": "c"})
        r = hc._check_call_home_status()
        assert r.status == "pass"
        assert "enabled" in r.message.lower()

    def test_check_call_home_phone_home_enabled(self, mock_api_handler):
        hc = self._make_hc(mock_api_handler, {"phone_home_enabled": True, "name": "c"})
        r = hc._check_call_home_status()
        assert r.status == "pass"
        assert "enabled" in r.message.lower()

    def test_check_call_home_disabled(self, mock_api_handler):
        hc = self._make_hc(mock_api_handler, {"call_home_enabled": False, "name": "c"})
        r = hc._check_call_home_status()
        assert r.status == "warning"
        assert "not enabled" in r.message.lower()

    def test_check_call_home_no_field(self, mock_api_handler):
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_call_home_status()
        assert r.status == "pass"
        assert "not exposed via api" in r.message.lower()

    def test_check_switches_registered_empty(self, mock_api_handler):
        mock_api_handler._make_api_request.return_value = []
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_switches_registered()
        assert r.status == "skipped"
        assert "no switches" in r.message.lower()

    def test_check_device_health_no_metrics(self, mock_api_handler):
        mock_api_handler.get_prometheus_metrics.return_value = None
        hc = self._make_hc(mock_api_handler, {"name": "c"})
        r = hc._check_device_health()
        assert r.status == "skipped"


# ===================================================================
# WS-B: TestSSHNodeChecks
# ===================================================================


# ===================================================================
# WS-C: TestSwitchCheckDispatch
# ===================================================================


class TestSwitchCheckDispatch:
    def test_switch_checks_no_ips(self, mock_api_handler):
        switch_config = {"username": "cumulus", "password": "secret"}
        mock_api_handler._make_api_request.return_value = []
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)
        assert checker.run_switch_ssh_checks() == []

    @patch("health_checker.run_ssh_command")
    @patch("health_checker.run_interactive_ssh")
    def test_switch_checks_with_ips(self, mock_pty, mock_ssh, mock_api_handler):
        switch_config = {"username": "cumulus", "password": "secret", "switch_ips": ["10.0.0.10"]}
        checker = HealthChecker(api_handler=mock_api_handler, switch_ssh_config=switch_config)

        nv_mlag_ok = "peer-alive: Yes\nbackup-active: Yes\n"
        ntp_ok = (
            "     remote           refid      st t when poll reach   delay   offset  jitter\n"
            "==============================================================================\n"
            "*ntp.server.com  17.253.34.123    2 u  532 1024  377   12.345   -0.678   1.234\n"
        )
        cfg_ok = "interface swp1\n"

        mock_pty.return_value = (0, "Cumulus Linux hostname: switch-1", "")
        mock_ssh.side_effect = [
            (0, nv_mlag_ok, ""),
            (0, ntp_ok, ""),
            (0, cfg_ok, ""),
        ]

        results = checker.run_switch_ssh_checks()
        assert len(results) == 3
        assert results[0].status == "pass"
        assert results[1].status == "pass"
        assert results[2].status == "pass"

    def test_switch_checks_cancelled(self, mock_api_handler):
        switch_config = {"username": "cumulus", "password": "secret", "switch_ips": ["10.0.0.10"]}
        cancel_event = threading.Event()
        cancel_event.set()
        checker = HealthChecker(
            api_handler=mock_api_handler,
            switch_ssh_config=switch_config,
            cancel_event=cancel_event,
        )
        with pytest.raises(CancelledError):
            checker.run_switch_ssh_checks()


# ===================================================================
# WS-C: TestSwitchCheckMethods
# ===================================================================


class TestSwitchCheckMethods:
    @pytest.fixture
    def sw_checker(self, mock_api_handler):
        return HealthChecker(
            api_handler=mock_api_handler,
            switch_ssh_config={"username": "cumulus", "password": "secret", "switch_ips": ["10.0.1.1"]},
        )

    # -- Cumulus MLAG tests ------------------------------------------------

    @patch("health_checker.run_ssh_command")
    def test_mlag_healthy(self, mock_ssh, sw_checker):
        mock_ssh.return_value = (0, "peer-alive: Yes\nbackup-active: Yes\n", "")
        r = sw_checker._check_mlag_status("10.0.1.1", "cumulus", "secret", switch_os="cumulus")
        assert r.status == "pass"
        assert "MLAG healthy" in r.message

    @patch("health_checker.run_ssh_command")
    def test_mlag_unhealthy(self, mock_ssh, sw_checker):
        mock_ssh.return_value = (0, "peer-alive: No\nbackup-active: Yes\n", "")
        r = sw_checker._check_mlag_status("10.0.1.1", "cumulus", "secret", switch_os="cumulus")
        assert r.status == "fail"

    @patch("health_checker.run_ssh_command")
    @patch("health_checker.run_interactive_ssh")
    def test_mlag_no_output_warning(self, mock_pty, mock_ssh, sw_checker):
        mock_ssh.return_value = (1, "", "unknown command")
        mock_pty.return_value = (1, "", "unknown command")
        r = sw_checker._check_mlag_status("10.0.1.1", "cumulus", "secret", switch_os="cumulus")
        assert r.status == "warning"
        assert "could not be determined" in r.message

    @patch("health_checker.run_ssh_command")
    @patch("health_checker.run_interactive_ssh")
    def test_mlag_empty_response_warning(self, mock_pty, mock_ssh, sw_checker):
        mock_ssh.return_value = (0, "", "")
        mock_pty.return_value = (0, "", "")
        r = sw_checker._check_mlag_status("10.0.1.1", "cumulus", "secret", switch_os="cumulus")
        assert r.status == "warning"
        assert "could not be determined" in r.message

    # -- Onyx MLAG tests ---------------------------------------------------

    @patch("health_checker.run_interactive_ssh")
    def test_mlag_onyx_format_pass(self, mock_pty, sw_checker):
        onyx_output = (
            "Admin status: Enabled\n"
            "Operational status: Up\n"
            "Reload-delay: 30 sec\n"
            "System-mac: c4:d6:53:1c:d5:d8\n"
            "\n"
            "MLAG IPLs Summary:\n"
            "---\n"
            "1    Po1           4000       Up           10.10.10.2\n"
            "\n"
            "MLAG Members Summary:\n"
            "---\n"
            "System-id           State                        Hostname\n"
            "---\n"
            "90:0A:84:44:6D:88   Up                           SW02\n"
            "90:0A:84:44:72:88   Up                           SW01\n"
        )
        mock_pty.return_value = (0, onyx_output, "")
        r = sw_checker._check_mlag_status("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "pass"
        assert "MLAG healthy" in r.message
        assert "operational status Up" in r.message

    @patch("health_checker.run_interactive_ssh")
    def test_mlag_onyx_oper_down(self, mock_pty, sw_checker):
        onyx_output = "Admin status: Enabled\n" "Operational status: Down\n"
        mock_pty.return_value = (0, onyx_output, "")
        r = sw_checker._check_mlag_status("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "fail"
        assert "operational status not Up" in r.message

    @patch("health_checker.run_interactive_ssh")
    def test_mlag_onyx_admin_disabled(self, mock_pty, sw_checker):
        onyx_output = "Admin status: Disabled\n" "Operational status: Down\n"
        mock_pty.return_value = (0, onyx_output, "")
        r = sw_checker._check_mlag_status("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "fail"
        assert "admin status not Enabled" in r.message

    @patch("health_checker.run_interactive_ssh")
    def test_mlag_onyx_empty(self, mock_pty, sw_checker):
        mock_pty.return_value = (0, "", "")
        r = sw_checker._check_mlag_status("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "warning"
        assert "could not be determined" in r.message

    # -- Cumulus NTP tests -------------------------------------------------

    @patch("health_checker.run_ssh_command")
    def test_switch_ntp_peers(self, mock_ssh, sw_checker):
        ntp_output = (
            "     remote           refid      st t when poll reach   delay   offset  jitter\n"
            "==============================================================================\n"
            "*ntp.server.com  17.253.34.123    2 u  532 1024  377   12.345   -0.678   1.234\n"
        )
        mock_ssh.return_value = (0, ntp_output, "")
        r = sw_checker._check_switch_ntp("10.0.1.1", "cumulus", "secret", switch_os="cumulus")
        assert r.status == "pass"
        assert "NTP peers found" in r.message

    @patch("health_checker.run_ssh_command")
    def test_switch_ntp_cumulus_no_peers(self, mock_ssh, sw_checker):
        mock_ssh.return_value = (0, "NTP not available", "")
        r = sw_checker._check_switch_ntp("10.0.1.1", "cumulus", "secret", switch_os="cumulus")
        assert r.status == "warning"
        assert "not available" in r.message.lower()

    # -- Onyx NTP tests ----------------------------------------------------

    @patch("health_checker.run_interactive_ssh")
    def test_switch_ntp_onyx_enabled_with_server(self, mock_pty, sw_checker):
        onyx_output = (
            "NTP is administratively            : enabled\n"
            "VRF name                           : default\n"
            "NTP Authentication administratively: disabled\n"
            "NTP server role                    : enabled\n"
            "\n"
            "Clock is unsynchronized.\n"
            "\n"
            "Active servers and peers:\n"
            "  10.128.12.18:\n"
            "    Conf Type          : peer\n"
            "    Status             : pending\n"
        )
        mock_pty.return_value = (0, onyx_output, "")
        r = sw_checker._check_switch_ntp("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "pass"
        assert "NTP enabled" in r.message
        assert "active servers" in r.message.lower()

    @patch("health_checker.run_interactive_ssh")
    def test_switch_ntp_onyx_enabled_no_server(self, mock_pty, sw_checker):
        onyx_output = (
            "NTP is administratively            : enabled\n"
            "NTP Authentication administratively: disabled\n"
            "\n"
            "Active servers and peers:\n"
        )
        mock_pty.return_value = (0, onyx_output, "")
        r = sw_checker._check_switch_ntp("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "warning"
        assert "no active servers" in r.message.lower()

    @patch("health_checker.run_interactive_ssh")
    def test_switch_ntp_onyx_disabled(self, mock_pty, sw_checker):
        onyx_output = "NTP is administratively            : disabled\n"
        mock_pty.return_value = (0, onyx_output, "")
        r = sw_checker._check_switch_ntp("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "warning"
        assert "not enabled" in r.message.lower()

    @patch("health_checker.run_interactive_ssh")
    def test_switch_ntp_onyx_empty(self, mock_pty, sw_checker):
        mock_pty.return_value = (0, "", "")
        r = sw_checker._check_switch_ntp("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "warning"

    # -- Onyx Config tests -------------------------------------------------

    @patch("health_checker.run_interactive_ssh")
    def test_switch_config_onyx_readable(self, mock_pty, sw_checker):
        mock_pty.return_value = (0, '## Running database "initial"\nno cli default prefix-mode enabled', "")
        r = sw_checker._check_switch_config_backup("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "pass"
        assert "readable" in r.message.lower()

    @patch("health_checker.run_interactive_ssh")
    def test_switch_config_onyx_empty(self, mock_pty, sw_checker):
        mock_pty.return_value = (0, "", "")
        r = sw_checker._check_switch_config_backup("10.0.1.1", "admin", "secret", switch_os="onyx")
        assert r.status == "warning"
        assert "empty" in r.message.lower()

    # -- Cumulus Config tests -----------------------------------------------

    @patch("health_checker.run_ssh_command")
    def test_switch_config_cumulus_readable(self, mock_ssh, sw_checker):
        mock_ssh.return_value = (0, "interface swp1\n  ip address 10.0.0.1/24", "")
        r = sw_checker._check_switch_config_backup("10.0.1.1", "cumulus", "secret", switch_os="cumulus")
        assert r.status == "pass"
        assert "readable" in r.message.lower()


# ===================================================================
# WS-C: TestMLAGConsolidation
# ===================================================================


class TestSwitchResultConsolidation:
    def test_consolidate_identical_mlag_pass(self):
        results = [
            HealthCheckResult(
                "MLAG Status",
                "switch_ssh",
                "pass",
                "MLAG healthy on 10.0.0.1",
                {"host": "10.0.0.1", "peer_alive": True, "backup_active": True},
                "t",
            ),
            HealthCheckResult(
                "Switch NTP", "switch_ssh", "pass", "NTP peers found on 10.0.0.1", {"host": "10.0.0.1"}, "t"
            ),
            HealthCheckResult(
                "MLAG Status",
                "switch_ssh",
                "pass",
                "MLAG healthy on 10.0.0.2",
                {"host": "10.0.0.2", "peer_alive": True, "backup_active": True},
                "t",
            ),
            HealthCheckResult(
                "Switch NTP", "switch_ssh", "pass", "NTP peers found on 10.0.0.2", {"host": "10.0.0.2"}, "t"
            ),
        ]
        out = HealthChecker._consolidate_switch_results(results)
        mlag_entries = [r for r in out if r.check_name == "MLAG Status"]
        ntp_entries = [r for r in out if r.check_name == "Switch NTP"]
        assert len(mlag_entries) == 1
        assert "10.0.0.1" in mlag_entries[0].message
        assert "10.0.0.2" in mlag_entries[0].message
        assert len(ntp_entries) == 1
        assert len(out) == 2

    def test_consolidate_different_mlag_keeps_both(self):
        results = [
            HealthCheckResult(
                "MLAG Status",
                "switch_ssh",
                "pass",
                "MLAG healthy on 10.0.0.1",
                {"host": "10.0.0.1", "peer_alive": True, "backup_active": True},
                "t",
            ),
            HealthCheckResult(
                "MLAG Status",
                "switch_ssh",
                "fail",
                "MLAG issue on 10.0.0.2",
                {"host": "10.0.0.2", "peer_alive": False, "backup_active": True},
                "t",
            ),
        ]
        out = HealthChecker._consolidate_switch_results(results)
        mlag_entries = [r for r in out if r.check_name == "MLAG Status"]
        assert len(mlag_entries) == 2

    def test_consolidate_single_switch_unchanged(self):
        results = [
            HealthCheckResult(
                "MLAG Status", "switch_ssh", "pass", "MLAG healthy on 10.0.0.1", {"host": "10.0.0.1"}, "t"
            ),
            HealthCheckResult(
                "Switch NTP", "switch_ssh", "warning", "No NTP peers found on 10.0.0.1", {"host": "10.0.0.1"}, "t"
            ),
        ]
        out = HealthChecker._consolidate_switch_results(results)
        assert len(out) == 2

    def test_consolidate_ntp_warning_both_switches(self):
        results = [
            HealthCheckResult(
                "Switch NTP", "switch_ssh", "warning", "No NTP peers found on 10.0.0.1", {"host": "10.0.0.1"}, "t"
            ),
            HealthCheckResult(
                "Switch Config Readability",
                "switch_ssh",
                "pass",
                "Switch config readable on 10.0.0.1",
                {"host": "10.0.0.1"},
                "t",
            ),
            HealthCheckResult(
                "Switch NTP", "switch_ssh", "warning", "No NTP peers found on 10.0.0.2", {"host": "10.0.0.2"}, "t"
            ),
            HealthCheckResult(
                "Switch Config Readability",
                "switch_ssh",
                "pass",
                "Switch config readable on 10.0.0.2",
                {"host": "10.0.0.2"},
                "t",
            ),
        ]
        out = HealthChecker._consolidate_switch_results(results)
        ntp_entries = [r for r in out if r.check_name == "Switch NTP"]
        cfg_entries = [r for r in out if r.check_name == "Switch Config Readability"]
        assert len(ntp_entries) == 1
        assert "10.0.0.1" in ntp_entries[0].message
        assert "10.0.0.2" in ntp_entries[0].message
        assert len(cfg_entries) == 1
        assert len(out) == 2

    def test_consolidate_onyx_mlag_pass(self):
        results = [
            HealthCheckResult(
                "MLAG Status",
                "switch_ssh",
                "pass",
                "MLAG healthy on 10.0.0.1: operational status Up",
                {"host": "10.0.0.1", "switch_os": "onyx", "admin_enabled": True, "oper_up": True},
                "t",
            ),
            HealthCheckResult(
                "MLAG Status",
                "switch_ssh",
                "pass",
                "MLAG healthy on 10.0.0.2: operational status Up",
                {"host": "10.0.0.2", "switch_os": "onyx", "admin_enabled": True, "oper_up": True},
                "t",
            ),
        ]
        out = HealthChecker._consolidate_switch_results(results)
        assert len(out) == 1
        assert "10.0.0.1" in out[0].message
        assert "10.0.0.2" in out[0].message
        assert "operational status Up" in out[0].message


# ===================================================================
# WS-D: TestSwitchOSDetection
# ===================================================================


class TestSwitchOSDetection:
    @pytest.fixture
    def sw_checker(self, mock_api_handler):
        return HealthChecker(
            api_handler=mock_api_handler,
            switch_ssh_config={"username": "admin", "password": "secret", "switch_ips": ["10.0.1.1"]},
        )

    @patch("health_checker.run_interactive_ssh")
    def test_detect_onyx(self, mock_pty, sw_checker):
        mock_pty.return_value = (0, "Product name:      Onyx\nProduct release:   3.10.4104", "")
        os_type = sw_checker._detect_switch_type("10.0.1.1", "admin", "secret")
        assert os_type == "onyx"

    @patch("health_checker.run_interactive_ssh")
    def test_detect_mellanox(self, mock_pty, sw_checker):
        mock_pty.return_value = (0, "Product name:      Mellanox SN2700", "")
        os_type = sw_checker._detect_switch_type("10.0.1.1", "admin", "secret")
        assert os_type == "onyx"

    @patch("health_checker.run_interactive_ssh")
    def test_detect_cumulus_default(self, mock_pty, sw_checker):
        mock_pty.return_value = (0, "Cumulus Linux hostname: switch-1", "")
        os_type = sw_checker._detect_switch_type("10.0.1.1", "cumulus", "secret")
        assert os_type == "cumulus"

    @patch("health_checker.run_interactive_ssh")
    def test_detect_fallback_on_error(self, mock_pty, sw_checker):
        mock_pty.side_effect = Exception("SSH failed")
        os_type = sw_checker._detect_switch_type("10.0.1.1", "admin", "secret")
        assert os_type == "cumulus"


# ===================================================================
# WS-C: TestRemediationEdgeCases
# ===================================================================


class TestRemediationEdgeCases:
    def test_format_finding_with_alarms(self, mock_api_handler, tmp_path):
        checker = HealthChecker(api_handler=mock_api_handler)
        results = [
            HealthCheckResult(
                check_name="Active Alarms",
                category="api",
                status="fail",
                message="Unresolved alarms",
                details={
                    "alarms": [
                        {"severity": "CRITICAL", "description": "disk failure", "object_name": "obj", "timestamp": "t"},
                    ],
                },
                timestamp="2026-03-03T00:00:00Z",
            ),
        ]
        report = HealthCheckReport(
            cluster_ip="10.0.0.1",
            cluster_name="test-cluster",
            cluster_version="5.3.0",
            timestamp="2026-03-03T00:00:00Z",
            results=results,
            summary={"pass": 0, "fail": 1, "warning": 0, "skipped": 0, "error": 0},
            manual_checklist=[],
            tiers_run=[1],
        )
        filepath = checker.generate_remediation_report(report, output_dir=str(tmp_path))
        text = Path(filepath).read_text()
        assert "CRITICAL" in text
        assert "disk failure" in text

    def test_format_finding_unknown_check(self, mock_api_handler, tmp_path):
        checker = HealthChecker(api_handler=mock_api_handler)
        results = [
            HealthCheckResult(
                check_name="Totally Unknown Synthetic Check",
                category="api",
                status="fail",
                message="Something failed",
                timestamp="2026-03-03T00:00:00Z",
            ),
        ]
        report = HealthCheckReport(
            cluster_ip="10.0.0.1",
            cluster_name="test-cluster",
            cluster_version="5.3.0",
            timestamp="2026-03-03T00:00:00Z",
            results=results,
            summary={"pass": 0, "fail": 1, "warning": 0, "skipped": 0, "error": 0},
            manual_checklist=[],
            tiers_run=[1],
        )
        filepath = checker.generate_remediation_report(report, output_dir=str(tmp_path))
        text = Path(filepath).read_text()
        assert "UNKNOWN" in text

    def test_correlate_cnode_dnode_down(self, mock_api_handler):
        checker = HealthChecker(api_handler=mock_api_handler)
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
        correlations = checker._correlate_findings(results)
        assert "CNode Status" in correlations
        assert "DNode Status" in correlations
        assert any("chassis" in c.lower() for c in correlations["CNode Status"])

    def test_remediation_report_all_pass(self, mock_api_handler, tmp_path):
        checker = HealthChecker(api_handler=mock_api_handler)
        results = [
            HealthCheckResult(
                check_name="Cluster RAID Health",
                category="api",
                status="pass",
                message="All RAID states HEALTHY",
                timestamp="2026-03-03T00:00:00Z",
            ),
            HealthCheckResult(
                check_name="CNode Status",
                category="api",
                status="pass",
                message="All CNodes ACTIVE",
                timestamp="2026-03-03T00:00:00Z",
            ),
        ]
        report = HealthCheckReport(
            cluster_ip="10.0.0.1",
            cluster_name="test-cluster",
            cluster_version="5.3.0",
            timestamp="2026-03-03T00:00:00Z",
            results=results,
            summary={"pass": 2, "fail": 0, "warning": 0, "skipped": 0, "error": 0},
            manual_checklist=[],
            tiers_run=[1],
        )
        filepath = checker.generate_remediation_report(report, output_dir=str(tmp_path))
        text = Path(filepath).read_text()
        assert "CRITICAL FINDINGS" not in text
        assert "PASSING CHECKS" in text
        assert "2 PASS" in text
