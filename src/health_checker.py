"""
VAST As-Built Report Generator - Health Checker Module

Standalone module that runs cluster health checks via the VAST REST API.
Produces HealthCheckReport containing HealthCheckResult items consumed by
Data Extractor for optional report injection.

Module boundary: must NOT import report_builder or data_extractor.
"""

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from utils.ssh_adapter import run_ssh_command


class CancelledError(Exception):
    """Raised when a health check run is cancelled by the user."""

    pass


@dataclass
class HealthCheckResult:
    """Single health check outcome."""

    check_name: str
    category: str  # "api" | "node_ssh" | "switch_ssh" | "performance" | "custom"
    status: str  # "pass" | "fail" | "warning" | "skipped" | "error"
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: str = ""
    duration_seconds: float = 0.0


@dataclass
class HealthCheckReport:
    """Aggregate report for a full health check run."""

    cluster_ip: str
    cluster_name: str
    cluster_version: str
    timestamp: str
    results: List[HealthCheckResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    manual_checklist: List[Dict[str, str]] = field(default_factory=list)
    tiers_run: List[int] = field(default_factory=list)


class HealthChecker:
    """Runs tiered health checks against a VAST cluster.

    Tier 1 -- API checks (23 read-only GET calls)
    Tier 2 -- Node SSH checks (placeholder, WP-9)
    Tier 3 -- Switch SSH checks (placeholder, WP-9)
    """

    DEFAULT_THRESHOLDS = {
        "capacity_percent": 80,
        "handle_percent": 80,
    }

    MANUAL_CHECKLIST = [
        {
            "item": "Failover Testing",
            "description": "VMS migration and leader reboot test",
            "status": "Manual Verification Required",
        },
        {
            "item": "VIP Movement / ARP Validation",
            "description": "Mount from client, generate IO, disable CNode, verify recovery",
            "status": "Manual Verification Required",
        },
        {
            "item": "Password Management",
            "description": "Verify default passwords changed for root, vastdata, IPMI admin",
            "status": "Manual Verification Required",
        },
    ]

    HEALTH_CHECK_TIMEOUT = 10
    HEALTH_CHECK_MAX_RETRIES = 1

    def __init__(
        self,
        api_handler: Any,
        ssh_config: Optional[Dict[str, str]] = None,
        switch_ssh_config: Optional[Dict[str, str]] = None,
        cancel_event: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
        thresholds: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.api_handler = api_handler
        self.ssh_config = ssh_config
        self.switch_ssh_config = switch_ssh_config
        self.cancel_event = cancel_event
        self.logger = logger or logging.getLogger(__name__)
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self._cluster_cache: Optional[Dict[str, Any]] = None
        self._original_timeout: Optional[int] = None
        self._original_retries: Optional[int] = None

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.now(tz=None).astimezone().isoformat()

    @staticmethod
    def _summarize(results: List[HealthCheckResult]) -> Dict[str, int]:
        summary: Dict[str, int] = {"pass": 0, "fail": 0, "warning": 0, "skipped": 0, "error": 0}
        for r in results:
            if r.status in summary:
                summary[r.status] += 1
        return summary

    def _check_cancel(self) -> None:
        if self.cancel_event and self.cancel_event.is_set():
            raise CancelledError("Health check cancelled by user")

    def _resolve_cnode_ip(self) -> Optional[str]:
        """Return a CNode IP from ssh_config or by querying the API."""
        if self.ssh_config and self.ssh_config.get("cnode_ip"):
            return self.ssh_config["cnode_ip"]
        try:
            cnodes = self.api_handler._make_api_request("cnodes/")
            if cnodes and isinstance(cnodes, list):
                for node in cnodes:
                    ip = node.get("mgmt_ip") or node.get("ip")
                    if ip:
                        return str(ip)
        except Exception:
            pass
        return None

    def _resolve_switch_ips(self) -> List[str]:
        """Return switch IPs from switch_ssh_config or by querying the API.

        Tries multiple API endpoints and extraction methods:
        1. User-provided switch_ips in config
        2. switches/ endpoint (API v7)
        3. v1/switches/ endpoint (legacy)
        4. Extract from CNode nic_nodes relationships
        """
        # 1. User-provided switch IPs take priority
        if self.switch_ssh_config and self.switch_ssh_config.get("switch_ips"):
            ips = list(self.switch_ssh_config["switch_ips"])
            self.logger.info(f"Using {len(ips)} user-provided switch IP(s)")
            return ips

        ips: List[str] = []

        # 2. Try switches/ endpoint (API v7)
        try:
            switches = self.api_handler._make_api_request("switches/")
            if switches and isinstance(switches, list):
                for sw in switches:
                    ip = sw.get("mgmt_ip") or sw.get("ip") or sw.get("management_ip")
                    if ip and ip not in ips:
                        ips.append(ip)
                if ips:
                    self.logger.info(f"Found {len(ips)} switch IP(s) from switches/ endpoint")
                    return ips
        except Exception as e:
            self.logger.debug(f"switches/ endpoint failed: {e}")

        # 3. Try v1/switches/ endpoint (legacy)
        try:
            switches = self.api_handler._make_api_request("v1/switches/")
            if switches and isinstance(switches, list):
                for sw in switches:
                    ip = sw.get("mgmt_ip") or sw.get("ip") or sw.get("management_ip")
                    if ip and ip not in ips:
                        ips.append(ip)
                if ips:
                    self.logger.info(f"Found {len(ips)} switch IP(s) from v1/switches/ endpoint")
                    return ips
        except Exception as e:
            self.logger.debug(f"v1/switches/ endpoint failed: {e}")

        # 4. Extract switch IPs from CNode nic_nodes relationships
        try:
            cnodes = self.api_handler._make_api_request("cnodes/")
            if cnodes and isinstance(cnodes, list):
                for cnode in cnodes:
                    # Check nic_nodes for switch connections
                    nic_nodes = cnode.get("nic_nodes") or []
                    for nic in nic_nodes:
                        switch_ip = nic.get("switch_ip") or nic.get("remote_ip")
                        if switch_ip and switch_ip not in ips:
                            ips.append(switch_ip)
                if ips:
                    self.logger.info(f"Extracted {len(ips)} switch IP(s) from CNode relationships")
                    return ips
        except Exception as e:
            self.logger.debug(f"CNode switch extraction failed: {e}")

        # 5. Try networkinterfaces/ for switch connections
        try:
            nics = self.api_handler._make_api_request("networkinterfaces/")
            if nics and isinstance(nics, list):
                for nic in nics:
                    switch_ip = nic.get("switch_ip") or nic.get("connected_switch_ip")
                    if switch_ip and switch_ip not in ips:
                        ips.append(switch_ip)
                if ips:
                    self.logger.info(f"Extracted {len(ips)} switch IP(s) from network interfaces")
                    return ips
        except Exception as e:
            self.logger.debug(f"Network interfaces switch extraction failed: {e}")

        if not ips:
            self.logger.warning("No switch IPs found via API - provide switch_ips in config for Tier-3 checks")
        return ips

    @staticmethod
    def to_dict(report: HealthCheckReport) -> Dict[str, Any]:
        return asdict(report)

    def save_json(self, report: HealthCheckReport, output_dir: str = "output") -> str:
        health_dir = os.path.join(output_dir, "health")
        os.makedirs(health_dir, exist_ok=True)
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"health_check_{report.cluster_name}_{timestamp}.json"
        filepath = os.path.join(health_dir, filename)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(report), f, indent=2, default=str)
        self.logger.info(f"Health check report saved to {filepath}")
        return filepath

    # ------------------------------------------------------------------
    # Remediation report generator
    # ------------------------------------------------------------------

    REMEDIATION_GUIDANCE: Dict[str, Dict[str, Any]] = {
        "CNode Status": {
            "severity": "CRITICAL",
            "impact": "Reduced compute capacity; client I/O may be degraded or unavailable if all CNodes are down.",
            "steps": [
                "Check VAST Management UI > CNodes panel for specific node status and error details.",
                "Verify IPMI/BMC console for affected nodes -- confirm power, fans, and network link status.",
                "Review Active Alarms for correlated node-down events with root-cause timestamps.",
                "SSH to the node (if reachable): check 'systemctl status vast-*' services.",
                "Check switch port status for ports connecting this chassis.",
                "If nodes were under maintenance: verify they auto-rejoin after services resume.",
                "Escalate to VAST Support if nodes remain down after physical verification.",
            ],
        },
        "DNode Status": {
            "severity": "CRITICAL",
            "impact": "Reduced data serving capacity; data remains protected by RAID but performance is degraded.",
            "steps": [
                "DNode failures typically share root cause with CNode failures in the same chassis.",
                "Address CNode and DNode issues together -- check chassis power, network, hardware.",
                "Verify DBox status: if DBoxes are still active, data is intact.",
                "Monitor VAST UI for automatic DNode recovery after chassis restoration.",
                "If DNodes remain inactive after CNodes recover: restart VAST services on DNode.",
            ],
        },
        "Active Alarms": {
            "severity": "HIGH",
            "impact": "Unresolved alarms indicate ongoing issues that may affect cluster stability.",
            "steps": [
                "Review each alarm in VAST Management UI > Alarms for severity, component, and timestamp.",
                "Correlate alarm timestamps with node status changes to identify the triggering event.",
                "Address root cause (e.g., inactive nodes) first -- alarms should auto-clear.",
                "For alarms that persist after root cause resolution: acknowledge and investigate individually.",
                "Document alarm IDs and timestamps for VAST Support engagement if needed.",
            ],
        },
        "Recent Events": {
            "severity": "MEDIUM",
            "impact": "Critical events may indicate recent failures, configuration changes, or security incidents.",
            "steps": [
                "Review critical events in VAST Management UI > Events, filtered by severity.",
                "Look for event patterns: repeated events suggest an ongoing or intermittent issue.",
                "Check event timestamps against node failures to establish sequence of events.",
                "If events endpoint timed out: the cluster may be under load; retry during a quieter period.",
            ],
        },
        "Network Settings": {
            "severity": "MEDIUM",
            "impact": "Missing DNS/NTP can cause name resolution failures and log timestamp drift.",
            "steps": [
                "Verify DNS/NTP configuration in VAST Management UI > Network Settings.",
                "If configured at node level but not via VMS: this may be an API coverage gap (informational).",
                "Configure NTP for time synchronization across cluster nodes and log correlation.",
                "Configure DNS for hostname resolution of external resources (syslog, SNMP targets).",
            ],
        },
        "License": {
            "severity": "LOW",
            "impact": "License field may not be populated in all API versions; verify separately.",
            "steps": [
                "Check license status in VAST Management UI > System > License.",
                "Verify license expiration date and capacity limits.",
                "Contact VAST Support if license information is unavailable via API.",
            ],
        },
        "Monitoring Config": {
            "severity": "MEDIUM",
            "impact": "Incomplete monitoring reduces visibility into cluster health events.",
            "steps": [
                "Configure syslog forwarding in VAST Management UI > Monitoring > Syslog.",
                "Point syslog to your organization's central log aggregator (Splunk, ELK, etc.).",
                "Verify SNMP traps are reaching your monitoring platform (Nagios, Zabbix, etc.).",
                "Test alert delivery by generating a test event.",
            ],
        },
        "RAID Rebuild Progress": {
            "severity": "HIGH",
            "impact": "Active RAID rebuilds consume I/O bandwidth and leave data temporarily less protected.",
            "steps": [
                "Monitor rebuild progress in VAST Management UI > Cluster > RAID.",
                "Avoid additional node removals or maintenance during active rebuilds.",
                "Rebuilds at 0% (SSD) mean no rebuild is needed; 100% means rebuild is complete.",
                "If rebuild is stuck (no progress over 30+ minutes): contact VAST Support.",
            ],
        },
        "Leader State": {
            "severity": "HIGH",
            "impact": "Non-steady leader state may indicate recent failover or ongoing leadership election.",
            "steps": [
                "Check VAST Management UI for current leader CNode and state.",
                "Verify the leader CNode is active and healthy (cross-reference with CNode Status).",
                "If leader CNode is inactive: cluster should auto-elect a new leader; monitor progress.",
                "Persistent non-steady states may indicate split-brain: contact VAST Support immediately.",
            ],
        },
        "Upgrade State": {
            "severity": "LOW",
            "impact": "Active upgrades temporarily reduce cluster availability during rolling restarts.",
            "steps": [
                "If upgrade is 'DONE': no action needed; previous upgrade completed successfully.",
                "If upgrade is in progress: monitor VAST Management UI > System > Upgrade for progress.",
                "Do not perform other maintenance operations during an active upgrade.",
            ],
        },
    }

    def generate_remediation_report(self, report: HealthCheckReport, output_dir: str = "output") -> str:
        """Generate a human-readable remediation report from health check results."""
        lines: List[str] = []
        hr = "=" * 80

        lines.append(hr)
        lines.append(f"  VAST CLUSTER HEALTH CHECK -- REMEDIATION REPORT")
        lines.append(hr)
        lines.append(f"  Cluster:  {report.cluster_name} ({report.cluster_ip})")
        lines.append(f"  Version:  {report.cluster_version}")
        lines.append(f"  Scanned:  {report.timestamp}")
        lines.append(f"  Tiers:    {report.tiers_run}")
        lines.append("")

        s = report.summary
        total = sum(s.values())
        lines.append(
            f"  SUMMARY: {total} checks | "
            f"{s.get('fail', 0)} FAIL | {s.get('warning', 0)} WARNING | "
            f"{s.get('error', 0)} ERROR | {s.get('skipped', 0)} SKIPPED | "
            f"{s.get('pass', 0)} PASS"
        )
        lines.append(hr)
        lines.append("")

        failures = [r for r in report.results if r.status == "fail"]
        warnings = [r for r in report.results if r.status == "warning"]
        errors = [r for r in report.results if r.status == "error"]
        skipped = [r for r in report.results if r.status == "skipped"]

        correlations = self._correlate_findings(report.results)

        finding_num = 0

        if failures:
            lines.append("-" * 80)
            lines.append("  CRITICAL FINDINGS (Failures)")
            lines.append("-" * 80)
            lines.append("")
            for r in failures:
                finding_num += 1
                self._format_finding(lines, finding_num, r, correlations)

        if errors:
            lines.append("-" * 80)
            lines.append("  ERRORS (Check Execution Failures)")
            lines.append("-" * 80)
            lines.append("")
            for r in errors:
                finding_num += 1
                self._format_finding(lines, finding_num, r, correlations)

        if warnings:
            lines.append("-" * 80)
            lines.append("  WARNINGS (Attention Required)")
            lines.append("-" * 80)
            lines.append("")
            for r in warnings:
                finding_num += 1
                self._format_finding(lines, finding_num, r, correlations)

        if skipped:
            lines.append("-" * 80)
            lines.append("  SKIPPED CHECKS")
            lines.append("-" * 80)
            lines.append("")
            for r in skipped:
                finding_num += 1
                lines.append(f"  [{finding_num}] {r.check_name}")
                lines.append(f"      Status:    SKIPPED")
                lines.append(f"      Timestamp: {r.timestamp}")
                lines.append(f"      Duration:  {r.duration_seconds:.2f}s")
                lines.append(f"      Message:   {r.message}")
                lines.append("")

        if report.manual_checklist:
            lines.append("-" * 80)
            lines.append("  MANUAL VERIFICATION REQUIRED")
            lines.append("-" * 80)
            lines.append("")
            for item in report.manual_checklist:
                lines.append(f"  [ ] {item['item']}")
                lines.append(f"      {item['description']}")
                lines.append("")

        passing = [r for r in report.results if r.status == "pass"]
        if passing:
            lines.append("-" * 80)
            lines.append(f"  PASSING CHECKS ({len(passing)})")
            lines.append("-" * 80)
            lines.append("")
            for r in passing:
                lines.append(f"  [PASS] {r.check_name}: {r.message}")
            lines.append("")

        lines.append(hr)
        lines.append("  END OF REPORT")
        lines.append(hr)

        report_text = "\n".join(lines)

        health_dir = os.path.join(output_dir, "health")
        os.makedirs(health_dir, exist_ok=True)
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"health_remediation_{report.cluster_name}_{timestamp}.txt"
        filepath = os.path.join(health_dir, filename)
        with open(filepath, "w") as f:
            f.write(report_text)
        self.logger.info(f"Remediation report saved to {filepath}")

        return filepath

    def _correlate_findings(self, results: List[HealthCheckResult]) -> Dict[str, List[str]]:
        """Cross-reference findings to identify related issues."""
        correlations: Dict[str, List[str]] = {}
        status_map = {r.check_name: r for r in results}

        cnode_result = status_map.get("CNode Status")
        dnode_result = status_map.get("DNode Status")
        alarm_result = status_map.get("Active Alarms")
        leader_result = status_map.get("Leader State")

        inactive_cnodes = []
        if cnode_result and cnode_result.details:
            inactive_cnodes = cnode_result.details.get("inactive", [])

        inactive_dnodes = []
        if dnode_result and dnode_result.details:
            inactive_dnodes = dnode_result.details.get("inactive", [])

        if inactive_cnodes and inactive_dnodes:
            msg = (
                f"CNode and DNode failures appear related -- "
                f"{len(inactive_cnodes)} CNodes and {len(inactive_dnodes)} DNodes are inactive. "
                f"Likely a chassis-level issue (power, network, or hardware)."
            )
            correlations["CNode Status"] = correlations.get("CNode Status", [])
            correlations["CNode Status"].append(msg)
            correlations["DNode Status"] = correlations.get("DNode Status", [])
            correlations["DNode Status"].append(msg)

        if inactive_cnodes and leader_result and leader_result.details:
            leader_cnode = leader_result.details.get("leader_cnode")
            if leader_cnode and leader_cnode in inactive_cnodes:
                msg = (
                    f"WARNING: Leader CNode '{leader_cnode}' is listed as INACTIVE. "
                    f"The cluster should auto-elect a new leader; verify in VAST UI."
                )
                correlations["CNode Status"] = correlations.get("CNode Status", [])
                correlations["CNode Status"].append(msg)
                correlations["Leader State"] = correlations.get("Leader State", [])
                correlations["Leader State"].append(msg)

        if (inactive_cnodes or inactive_dnodes) and alarm_result and alarm_result.status == "fail":
            total_inactive = len(inactive_cnodes) + len(inactive_dnodes)
            alarm_count = 0
            if alarm_result.details:
                alarm_count = alarm_result.details.get("critical_unresolved", 0)
            msg = (
                f"{alarm_count} unresolved alarms likely relate to the "
                f"{total_inactive} inactive node(s). Address node issues first; "
                f"alarms should auto-clear."
            )
            correlations["Active Alarms"] = correlations.get("Active Alarms", [])
            correlations["Active Alarms"].append(msg)

        return correlations

    def _format_finding(
        self,
        lines: List[str],
        num: int,
        result: HealthCheckResult,
        correlations: Dict[str, List[str]],
    ) -> None:
        """Format a single finding with guidance and correlations."""
        guidance = self.REMEDIATION_GUIDANCE.get(result.check_name, {})
        severity = guidance.get("severity", "UNKNOWN")

        lines.append(f"  [{num}] {result.check_name}")
        lines.append(f"      Severity:  {severity}")
        lines.append(f"      Status:    {result.status.upper()}")
        lines.append(f"      Timestamp: {result.timestamp}")
        lines.append(f"      Duration:  {result.duration_seconds:.2f}s")
        lines.append(f"      Message:   {result.message}")

        if guidance.get("impact"):
            lines.append(f"      Impact:    {guidance['impact']}")

        if result.details:
            lines.append(f"      Details:")
            for k, v in result.details.items():
                if k == "alarms" and isinstance(v, list):
                    lines.append(f"        {k}:")
                    for alarm in v:
                        desc = alarm.get("description") or alarm.get("object_type") or "N/A"
                        sev = alarm.get("severity", "?")
                        ts = alarm.get("timestamp", "?")
                        obj = alarm.get("object_name", "?")
                        lines.append(f"          - [{sev}] {desc} (object: {obj}, time: {ts})")
                elif k == "events" and isinstance(v, list):
                    lines.append(f"        {k}:")
                    for evt in v:
                        desc = evt.get("description") or evt.get("event_type") or "N/A"
                        ts = evt.get("timestamp", "?")
                        obj = evt.get("object_name", "?")
                        lines.append(f"          - {desc} (object: {obj}, time: {ts})")
                else:
                    lines.append(f"        {k}: {v}")

        corr = correlations.get(result.check_name, [])
        if corr:
            lines.append(f"      Correlated Findings:")
            for c in corr:
                lines.append(f"        * {c}")

        steps = guidance.get("steps", [])
        if steps:
            lines.append(f"      Recommended Actions:")
            for i, step in enumerate(steps, 1):
                lines.append(f"        {i}. {step}")

        lines.append("")

    # ------------------------------------------------------------------
    # Normalise helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_item(data: Any) -> Optional[Dict[str, Any]]:
        """Return the first element when *data* is a non-empty list, else *data* itself."""
        if isinstance(data, list):
            result = data[0] if data else None
            return dict(result) if isinstance(result, dict) else None
        return dict(data) if isinstance(data, dict) else None

    def _get_cluster_data(self) -> Optional[Dict[str, Any]]:
        """Return cached cluster data, fetching once on first call."""
        if self._cluster_cache is None:
            self._cluster_cache = self._first_item(self.api_handler._make_api_request("clusters/"))
        return self._cluster_cache

    def _apply_health_check_timeouts(self) -> None:
        """Temporarily lower API timeout and retries for health checks.

        The retry count is baked into the session's HTTPAdapter, so we
        must re-mount with a new Retry strategy to make the change effective.
        """
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        self._original_timeout = getattr(self.api_handler, "timeout", 30)
        self._original_retries = getattr(self.api_handler, "max_retries", 3)
        self.api_handler.timeout = self.HEALTH_CHECK_TIMEOUT
        self.api_handler.max_retries = self.HEALTH_CHECK_MAX_RETRIES

        retry_strategy = Retry(
            total=self.HEALTH_CHECK_MAX_RETRIES,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "OPTIONS"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = getattr(self.api_handler, "session", None)
        if session:
            session.mount("http://", adapter)
            session.mount("https://", adapter)

        self.logger.info(
            f"Health check API settings: timeout={self.HEALTH_CHECK_TIMEOUT}s, "
            f"max_retries={self.HEALTH_CHECK_MAX_RETRIES} (read-only GET only)"
        )

    def _restore_api_timeouts(self) -> None:
        """Restore original API timeout and retries after health checks."""
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry

        if self._original_timeout is not None:
            self.api_handler.timeout = self._original_timeout
        if self._original_retries is not None:
            self.api_handler.max_retries = self._original_retries
            retry_strategy = Retry(
                total=self._original_retries,
                backoff_factor=getattr(self.api_handler, "retry_delay", 2),
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session = getattr(self.api_handler, "session", None)
            if session:
                session.mount("http://", adapter)
                session.mount("https://", adapter)
        self._cluster_cache = None

    # ------------------------------------------------------------------
    # Tier 1 -- API checks
    # ------------------------------------------------------------------

    def run_api_checks(self) -> List[HealthCheckResult]:
        checks = [
            self._check_cluster_raid_health,
            self._check_raid_rebuild_progress,
            self._check_leader_state,
            self._check_cluster_state,
            self._check_expansion_state,
            self._check_upgrade_state,
            self._check_cnode_status,
            self._check_dnode_status,
            self._check_dbox_status,
            self._check_cbox_status,
            self._check_ebox_status,
            self._check_firmware_consistency,
            self._check_active_alarms,
            self._check_events,
            self._check_vip_pools,
            self._check_network_settings,
            self._check_license,
            self._check_capacity,
            self._check_handle_usage,
            self._check_performance_baseline,
            self._check_replication,
            self._check_snapshots,
            self._check_quotas,
            self._check_data_protection,
            self._check_monitoring_config,
            self._check_device_health,
        ]
        results: List[HealthCheckResult] = []
        self._apply_health_check_timeouts()
        try:
            for i, fn in enumerate(checks, 1):
                self._check_cancel()
                self.logger.info(f"Running API check {i}/{len(checks)}: {fn.__name__}")
                start = time.time()
                try:
                    result = fn()
                except Exception as exc:
                    elapsed = time.time() - start
                    self.logger.error(f"Check {fn.__name__} raised {type(exc).__name__}: {exc}")
                    result = HealthCheckResult(
                        check_name=fn.__name__,
                        category="api",
                        status="error",
                        message=f"Unexpected error: {exc}",
                        timestamp=self._now(),
                        duration_seconds=elapsed,
                    )
                results.append(result)
                if result.status in ("fail", "error"):
                    self.logger.warning(f"Check {fn.__name__} => {result.status}: {result.message}")
        finally:
            self._restore_api_timeouts()
        return results

    # --- 1. Cluster RAID Health -------------------------------------------

    def _check_cluster_raid_health(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Cluster RAID Health",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            fields = {
                "ssd_raid_state": data.get("ssd_raid_state"),
                "nvram_raid_state": data.get("nvram_raid_state"),
                "memory_raid_state": data.get("memory_raid_state"),
            }
            unhealthy = {k: v for k, v in fields.items() if v and str(v).upper() != "HEALTHY"}

            if unhealthy:
                return HealthCheckResult(
                    check_name="Cluster RAID Health",
                    category="api",
                    status="fail",
                    message=f"Unhealthy RAID states: {unhealthy}",
                    details=fields,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Cluster RAID Health",
                category="api",
                status="pass",
                message="All RAID states are HEALTHY",
                details=fields,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Cluster RAID Health",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 2. RAID Rebuild Progress -----------------------------------------

    def _check_raid_rebuild_progress(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="RAID Rebuild Progress",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            fields = {
                "ssd_raid_rebuild_progress": data.get("ssd_raid_rebuild_progress"),
                "nvram_raid_rebuild_progress": data.get("nvram_raid_rebuild_progress"),
                "memory_raid_rebuild_progress": data.get("memory_raid_rebuild_progress"),
            }
            in_progress = {
                k: v
                for k, v in fields.items()
                if v is not None and v != "" and isinstance(v, (int, float)) and 0 < v < 100
            }

            if in_progress:
                return HealthCheckResult(
                    check_name="RAID Rebuild Progress",
                    category="api",
                    status="warning",
                    message=f"RAID rebuild in progress: {in_progress}",
                    details=fields,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="RAID Rebuild Progress",
                category="api",
                status="pass",
                message="No RAID rebuilds in progress",
                details=fields,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="RAID Rebuild Progress",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 3. Leader State --------------------------------------------------

    def _check_leader_state(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Leader State",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            leader_state = data.get("leader_state", "UNKNOWN")
            details = {"leader_state": leader_state, "leader_cnode": data.get("leader_cnode")}

            if str(leader_state).upper() in ("STEADY", "STABLE", "UP"):
                return HealthCheckResult(
                    check_name="Leader State",
                    category="api",
                    status="pass",
                    message=f"Leader state is {leader_state}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Leader State",
                category="api",
                status="warning",
                message=f"Leader state is {leader_state}",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Leader State",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 4. Cluster State -------------------------------------------------

    def _check_cluster_state(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Cluster State",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            state = data.get("state", "UNKNOWN")
            enabled = data.get("enabled")
            details = {"state": state, "enabled": enabled}
            issues: List[str] = []

            if str(state).upper() != "ONLINE":
                issues.append(f"state is {state}")
            if enabled is not True:
                issues.append(f"enabled is {enabled}")

            if issues:
                return HealthCheckResult(
                    check_name="Cluster State",
                    category="api",
                    status="fail",
                    message=f"Cluster not fully operational: {', '.join(issues)}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Cluster State",
                category="api",
                status="pass",
                message="Cluster is ONLINE and enabled",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Cluster State",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 5. Expansion State -----------------------------------------------

    def _check_expansion_state(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Expansion State",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            expansion_state = data.get("expansion_state")
            details = {"expansion_state": expansion_state}

            if not expansion_state or str(expansion_state).upper() in ("", "NONE", "NULL"):
                return HealthCheckResult(
                    check_name="Expansion State",
                    category="api",
                    status="pass",
                    message="No expansion in progress",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Expansion State",
                category="api",
                status="warning",
                message=f"Expansion active: {expansion_state}",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Expansion State",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 6. Upgrade State -------------------------------------------------

    def _check_upgrade_state(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Upgrade State",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            upgrade_state = data.get("upgrade_state")
            details = {"upgrade_state": upgrade_state}

            if not upgrade_state or str(upgrade_state).upper() in (
                "",
                "NONE",
                "NULL",
                "DONE",
            ):
                return HealthCheckResult(
                    check_name="Upgrade State",
                    category="api",
                    status="pass",
                    message=(
                        "No upgrade in progress"
                        if str(upgrade_state).upper() != "DONE"
                        else "Previous upgrade completed successfully"
                    ),
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Upgrade State",
                category="api",
                status="warning",
                message=f"Upgrade active: {upgrade_state}",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Upgrade State",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 7. CNode Status --------------------------------------------------

    def _check_cnode_status(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("cnodes/")
            if not data or not isinstance(data, list):
                return HealthCheckResult(
                    check_name="CNode Status",
                    category="api",
                    status="error",
                    message="Failed to retrieve CNode data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            total = len(data)
            inactive = []
            disabled = []
            for node in data:
                name = node.get("name", node.get("id", "unknown"))
                state = str(node.get("state", node.get("status", ""))).upper()
                if state != "ACTIVE":
                    inactive.append(name)
                if node.get("enabled") is False:
                    disabled.append(name)

            details = {"total": total, "inactive": inactive, "disabled": disabled}
            issues: List[str] = []
            if inactive:
                issues.append(f"inactive: {inactive}")
            if disabled:
                issues.append(f"disabled: {disabled}")

            if issues:
                return HealthCheckResult(
                    check_name="CNode Status",
                    category="api",
                    status="fail",
                    message=f"{len(inactive) + len(disabled)} CNode issue(s): {'; '.join(issues)}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="CNode Status",
                category="api",
                status="pass",
                message=f"All {total} CNodes are ACTIVE and enabled",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="CNode Status",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 8. DNode Status --------------------------------------------------

    def _check_dnode_status(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("dnodes/")
            if not data or not isinstance(data, list):
                return HealthCheckResult(
                    check_name="DNode Status",
                    category="api",
                    status="error",
                    message="Failed to retrieve DNode data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            total = len(data)
            inactive = []
            disabled = []
            for node in data:
                name = node.get("name", node.get("id", "unknown"))
                state = str(node.get("state", node.get("status", ""))).upper()
                if state != "ACTIVE":
                    inactive.append(name)
                if node.get("enabled") is False:
                    disabled.append(name)

            details = {"total": total, "inactive": inactive, "disabled": disabled}
            issues: List[str] = []
            if inactive:
                issues.append(f"inactive: {inactive}")
            if disabled:
                issues.append(f"disabled: {disabled}")

            if issues:
                return HealthCheckResult(
                    check_name="DNode Status",
                    category="api",
                    status="fail",
                    message=f"{len(inactive) + len(disabled)} DNode issue(s): {'; '.join(issues)}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="DNode Status",
                category="api",
                status="pass",
                message=f"All {total} DNodes are ACTIVE and enabled",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="DNode Status",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 9. DBox Status ---------------------------------------------------

    def _check_dbox_status(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("dboxes/")
            if not data or not isinstance(data, list):
                return HealthCheckResult(
                    check_name="DBox Status",
                    category="api",
                    status="error",
                    message="Failed to retrieve DBox data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            total = len(data)
            inactive = []
            for dbox in data:
                name = dbox.get("name", dbox.get("id", "unknown"))
                if str(dbox.get("state", "")).upper() != "ACTIVE":
                    inactive.append(name)

            details = {"total": total, "inactive": inactive}

            if inactive:
                return HealthCheckResult(
                    check_name="DBox Status",
                    category="api",
                    status="fail",
                    message=f"{len(inactive)} DBox(es) not ACTIVE: {inactive}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="DBox Status",
                category="api",
                status="pass",
                message=f"All {total} DBoxes are ACTIVE",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="DBox Status",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 9b. CBox Status ---------------------------------------------------

    def _check_cbox_status(self) -> HealthCheckResult:
        """Check CBox (combined compute/storage box) status."""
        start = time.time()
        try:
            data = self.api_handler._make_api_request("cboxes/")
            if data is None:
                # CBox endpoint may not exist on all clusters
                return HealthCheckResult(
                    check_name="CBox Status",
                    category="api",
                    status="skipped",
                    message="CBox endpoint not available (standard cluster)",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            if not isinstance(data, list):
                data = [data] if data else []

            if not data:
                return HealthCheckResult(
                    check_name="CBox Status",
                    category="api",
                    status="skipped",
                    message="No CBoxes found on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            total = len(data)
            inactive = []
            for cbox in data:
                name = cbox.get("name", cbox.get("id", "unknown"))
                state = str(cbox.get("state", cbox.get("status", ""))).upper()
                if state not in ("ACTIVE", "ONLINE", "HEALTHY", "UNKNOWN"):
                    inactive.append({"name": name, "state": state})

            details = {"total": total, "inactive": inactive}

            # Filter out UNKNOWN state (placeholder/unconfigured CBoxes)
            real_inactive = [i for i in inactive if i.get("state") != "UNKNOWN"]
            unknown_count = len(inactive) - len(real_inactive)

            if real_inactive:
                return HealthCheckResult(
                    check_name="CBox Status",
                    category="api",
                    status="fail",
                    message=f"{len(real_inactive)} CBox(es) not ACTIVE: {[i['name'] for i in real_inactive]}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            msg = f"All {total} CBoxes are ACTIVE"
            if unknown_count > 0:
                msg = f"{total - unknown_count} CBox(es) ACTIVE ({unknown_count} placeholder entries skipped)"
            return HealthCheckResult(
                check_name="CBox Status",
                category="api",
                status="pass",
                message=msg,
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return HealthCheckResult(
                    check_name="CBox Status",
                    category="api",
                    status="skipped",
                    message="CBox endpoint not available (standard cluster)",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="CBox Status",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 9c. EBox Status ---------------------------------------------------

    def _check_ebox_status(self) -> HealthCheckResult:
        """Check EBox (expansion box) status for EBox-only clusters."""
        start = time.time()
        try:
            data = self.api_handler._make_api_request("eboxes/")
            if data is None:
                return HealthCheckResult(
                    check_name="EBox Status",
                    category="api",
                    status="skipped",
                    message="EBox endpoint not available",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            if not isinstance(data, list):
                data = [data] if data else []

            if not data:
                return HealthCheckResult(
                    check_name="EBox Status",
                    category="api",
                    status="skipped",
                    message="No EBoxes found on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            total = len(data)
            inactive = []
            for ebox in data:
                name = ebox.get("name", ebox.get("id", "unknown"))
                state = str(ebox.get("state", ebox.get("status", ""))).upper()
                if state not in ("ACTIVE", "ONLINE", "HEALTHY", "UNKNOWN"):
                    inactive.append({"name": name, "state": state})

            details = {"total": total, "inactive": inactive}

            if inactive:
                return HealthCheckResult(
                    check_name="EBox Status",
                    category="api",
                    status="fail",
                    message=f"{len(inactive)} EBox(es) not ACTIVE: {[i['name'] for i in inactive]}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="EBox Status",
                category="api",
                status="pass",
                message=f"All {total} EBoxes are ACTIVE",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return HealthCheckResult(
                    check_name="EBox Status",
                    category="api",
                    status="skipped",
                    message="EBox endpoint not available",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="EBox Status",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 10. Firmware Consistency -----------------------------------------

    def _check_firmware_consistency(self) -> HealthCheckResult:
        start = time.time()
        try:
            cnodes = self.api_handler._make_api_request("cnodes/")
            dnodes = self.api_handler._make_api_request("dnodes/")

            firmware_fields = ["bios_version", "bmc_version", "os_version", "fw_version", "sw_version"]
            mismatches: Dict[str, Dict[str, List[str]]] = {}

            for node_type, nodes in [("cnode", cnodes), ("dnode", dnodes)]:
                if not nodes or not isinstance(nodes, list):
                    continue
                for fw_field in firmware_fields:
                    versions: Dict[str, List[str]] = {}
                    for node in nodes:
                        val = node.get(fw_field)
                        if val is not None and val != "":
                            versions.setdefault(str(val), []).append(str(node.get("name", node.get("id", "?"))))
                    if len(versions) > 1:
                        mismatches[f"{node_type}.{fw_field}"] = versions

            if not mismatches and not cnodes and not dnodes:
                return HealthCheckResult(
                    check_name="Firmware Consistency",
                    category="api",
                    status="skipped",
                    message="No node data available for firmware comparison",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if mismatches:
                return HealthCheckResult(
                    check_name="Firmware Consistency",
                    category="api",
                    status="warning",
                    message=f"Firmware version mismatches detected in: {list(mismatches.keys())}",
                    details={"mismatches": mismatches},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Firmware Consistency",
                category="api",
                status="pass",
                message="Firmware versions are consistent across all nodes",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Firmware Consistency",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 11. Active Alarms ------------------------------------------------

    def _check_active_alarms(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("alarms/")
            if data is None:
                return HealthCheckResult(
                    check_name="Active Alarms",
                    category="api",
                    status="skipped",
                    message="Alarms endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if not isinstance(data, list):
                data = [data] if data else []

            # Fetch event definitions to enrich alarm descriptions
            # Per VAST API docs, use /api/eventdefinitions/ (alarmdefinitions/ is not documented)
            event_defs: Dict[int, str] = {}
            try:
                defs = self.api_handler._make_api_request("eventdefinitions/")
                if defs and isinstance(defs, list):
                    for d in defs:
                        def_id = d.get("id")
                        # Event definitions may have different field names
                        desc = (
                            d.get("description")
                            or d.get("name")
                            or d.get("event_name")
                            or d.get("message")
                        )
                        if def_id and desc:
                            event_defs[def_id] = desc
            except Exception:
                pass  # Event definitions not critical

            critical_alarms = [
                a for a in data if str(a.get("severity", "")).upper() in ("CRITICAL", "MAJOR") and not a.get("resolved")
            ]

            alarm_summaries = []
            for a in critical_alarms[:20]:
                # Try multiple fields for description
                desc = (
                    a.get("description")
                    or a.get("message")
                    or a.get("text")
                    or a.get("alarm_text")
                    or event_defs.get(a.get("event_definition_id"))
                    or event_defs.get(a.get("definition_id"))
                    or a.get("alarm_type")
                    or a.get("type")
                    or f"Alarm on {a.get('object_type', 'unknown')}"
                )
                alarm_summaries.append(
                    {
                        "id": a.get("id"),
                        "severity": a.get("severity"),
                        "object_type": a.get("object_type") or a.get("alarm_type") or a.get("type"),
                        "object_name": a.get("object_name") or a.get("object_id") or a.get("name"),
                        "description": desc,
                        "timestamp": a.get("timestamp") or a.get("raised_at") or a.get("created"),
                    }
                )

            details = {
                "total_alarms": len(data),
                "critical_unresolved": len(critical_alarms),
                "alarms": alarm_summaries,
            }

            if critical_alarms:
                return HealthCheckResult(
                    check_name="Active Alarms",
                    category="api",
                    status="fail",
                    message=f"{len(critical_alarms)} unresolved critical/major alarm(s)",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Active Alarms",
                category="api",
                status="pass",
                message="No unresolved critical or major alarms",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return HealthCheckResult(
                    check_name="Active Alarms",
                    category="api",
                    status="skipped",
                    message="Alarms endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Active Alarms",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 12. Events -------------------------------------------------------

    def _check_events(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("events/", params={"page_size": 200, "ordering": "-timestamp"})
            if data is None:
                return HealthCheckResult(
                    check_name="Recent Events",
                    category="api",
                    status="skipped",
                    message="Events endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if not isinstance(data, list):
                data = [data] if data else []

            critical_events = [e for e in data if str(e.get("severity", "")).upper() == "CRITICAL"]

            event_summaries = []
            for e in critical_events[:10]:
                event_summaries.append(
                    {
                        "id": e.get("id"),
                        "severity": e.get("severity"),
                        "event_type": e.get("event_type") or e.get("type"),
                        "object_name": e.get("object_name") or e.get("object_id"),
                        "description": e.get("description") or e.get("message"),
                        "timestamp": e.get("timestamp") or e.get("created"),
                    }
                )

            details = {
                "total_events_returned": len(data),
                "critical_events": len(critical_events),
                "events": event_summaries,
            }

            if critical_events:
                return HealthCheckResult(
                    check_name="Recent Events",
                    category="api",
                    status="warning",
                    message=f"{len(critical_events)} recent critical event(s) detected",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Recent Events",
                category="api",
                status="pass",
                message=f"No recent critical events ({len(data)} events checked)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return HealthCheckResult(
                    check_name="Recent Events",
                    category="api",
                    status="skipped",
                    message="Events endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            timeout_keywords = ("timeout", "timed out", "max retries")
            if any(k in str(e).lower() for k in timeout_keywords):
                return HealthCheckResult(
                    check_name="Recent Events",
                    category="api",
                    status="skipped",
                    message="Events endpoint timed out (cluster may be under load)",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Recent Events",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 13. VIP Pools ----------------------------------------------------

    def _check_vip_pools(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("vippools/")
            if not data:
                return HealthCheckResult(
                    check_name="VIP Pools",
                    category="api",
                    status="fail",
                    message="No VIP pools configured",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if not isinstance(data, list):
                data = [data]

            enabled_pools = [p for p in data if p.get("enabled") is not False]
            details = {"total_pools": len(data), "enabled_pools": len(enabled_pools)}

            if not enabled_pools:
                return HealthCheckResult(
                    check_name="VIP Pools",
                    category="api",
                    status="fail",
                    message="No enabled VIP pools found",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="VIP Pools",
                category="api",
                status="pass",
                message=f"{len(enabled_pools)} enabled VIP pool(s) configured",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="VIP Pools",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 14. Network Settings ---------------------------------------------

    def _check_network_settings(self) -> HealthCheckResult:
        start = time.time()
        try:
            raw_response = self.api_handler._make_api_request("vms/1/network_settings/")
            data = self._first_item(raw_response)
            if isinstance(data, dict) and "data" in data:
                data = data.get("data", {})
            if not data:
                return HealthCheckResult(
                    check_name="Network Settings",
                    category="api",
                    status="error",
                    message="Failed to retrieve network settings",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            dns = data.get("dns") or data.get("dns_servers")
            ntp = data.get("ntp") or data.get("ntp_servers")
            gateway = data.get("external_gateways") or data.get("gateway") or data.get("default_gateway")

            if not dns and not ntp and not gateway:
                cluster_data = self._get_cluster_data()
                if cluster_data:
                    dns = dns or cluster_data.get("dns") or cluster_data.get("dns_servers")
                    ntp = ntp or cluster_data.get("ntp") or cluster_data.get("ntp_servers")
                    gateway = gateway or cluster_data.get("external_gateways") or cluster_data.get("gateway")

            details = {"dns": dns, "ntp": ntp, "gateway": gateway}
            missing: List[str] = []

            if not dns:
                missing.append("DNS")
            if not ntp:
                missing.append("NTP")
            if not gateway:
                missing.append("gateway")

            if missing:
                return HealthCheckResult(
                    check_name="Network Settings",
                    category="api",
                    status="warning",
                    message=f"Missing network configuration: {', '.join(missing)}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Network Settings",
                category="api",
                status="pass",
                message="DNS, NTP, and gateway are configured",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Network Settings",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 15. License ------------------------------------------------------

    def _check_license(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="License",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            license_info = data.get("license")
            details = {"license": license_info}

            if not license_info:
                return HealthCheckResult(
                    check_name="License",
                    category="api",
                    status="warning",
                    message="No license information found",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            license_str = str(license_info).upper()
            if "EXPIRED" in license_str or "INVALID" in license_str:
                return HealthCheckResult(
                    check_name="License",
                    category="api",
                    status="fail",
                    message=f"License issue: {license_info}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="License",
                category="api",
                status="pass",
                message="License is present and active",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="License",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 16. Capacity -----------------------------------------------------

    def _check_capacity(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Capacity",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            pct = data.get("physical_space_in_use_percent")
            threshold = self.thresholds.get("capacity_percent", 80)
            details = {"physical_space_in_use_percent": pct, "threshold": threshold}

            if pct is None:
                return HealthCheckResult(
                    check_name="Capacity",
                    category="api",
                    status="warning",
                    message="Capacity utilisation data not available",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            try:
                pct_val = float(pct)
            except (TypeError, ValueError):
                return HealthCheckResult(
                    check_name="Capacity",
                    category="api",
                    status="warning",
                    message=f"Non-numeric capacity value: {pct}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if pct_val >= threshold:
                return HealthCheckResult(
                    check_name="Capacity",
                    category="api",
                    status="warning",
                    message=f"Capacity at {pct_val:.1f}% (threshold {threshold}%)",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Capacity",
                category="api",
                status="pass",
                message=f"Capacity at {pct_val:.1f}% (below {threshold}% threshold)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Capacity",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 17. Handle Usage -------------------------------------------------

    def _check_handle_usage(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Handle Usage",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            pct = data.get("used_handles_percent")
            threshold = self.thresholds.get("handle_percent", 80)
            details = {"used_handles_percent": pct, "threshold": threshold}

            if pct is None:
                return HealthCheckResult(
                    check_name="Handle Usage",
                    category="api",
                    status="skipped",
                    message="Handle usage data not available",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            try:
                pct_val = float(pct)
            except (TypeError, ValueError):
                return HealthCheckResult(
                    check_name="Handle Usage",
                    category="api",
                    status="warning",
                    message=f"Non-numeric handle usage value: {pct}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if pct_val >= threshold:
                return HealthCheckResult(
                    check_name="Handle Usage",
                    category="api",
                    status="warning",
                    message=f"Handle usage at {pct_val:.1f}% (threshold {threshold}%)",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Handle Usage",
                category="api",
                status="pass",
                message=f"Handle usage at {pct_val:.1f}% (below {threshold}% threshold)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Handle Usage",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 18. Performance Baseline -----------------------------------------

    def _check_performance_baseline(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Performance Baseline",
                    category="performance",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            perf_fields = [
                "iops",
                "latency",
                "bw",
                "rd_iops",
                "wr_iops",
                "rd_latency",
                "wr_latency",
                "rd_bw",
                "wr_bw",
            ]
            details = {k: data.get(k) for k in perf_fields if data.get(k) is not None}

            return HealthCheckResult(
                check_name="Performance Baseline",
                category="performance",
                status="pass",
                message="Performance baseline captured (informational)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Performance Baseline",
                category="performance",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 19. Replication --------------------------------------------------

    def _check_replication(self) -> HealthCheckResult:
        start = time.time()
        try:
            cluster = self._get_cluster_data()
            if not cluster:
                return HealthCheckResult(
                    check_name="Replication",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            dr_enabled = cluster.get("dr_enabled") or cluster.get("replication_enabled")
            if not dr_enabled:
                return HealthCheckResult(
                    check_name="Replication",
                    category="api",
                    status="pass",
                    message="DR/Replication is not enabled on this cluster",
                    details={"dr_enabled": dr_enabled},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            policies = self.api_handler._make_api_request("protectionpolicies/")
            if not policies or not isinstance(policies, list):
                return HealthCheckResult(
                    check_name="Replication",
                    category="api",
                    status="warning",
                    message="DR enabled but no protection policies found",
                    details={"dr_enabled": dr_enabled},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            unhealthy = [
                p.get("name", p.get("id", "?"))
                for p in policies
                if str(p.get("status", "")).upper() not in ("HEALTHY", "ACTIVE", "OK", "")
            ]
            details = {"dr_enabled": dr_enabled, "total_policies": len(policies), "unhealthy_policies": unhealthy}

            if unhealthy:
                return HealthCheckResult(
                    check_name="Replication",
                    category="api",
                    status="warning",
                    message=f"{len(unhealthy)} protection policy(ies) not healthy: {unhealthy}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Replication",
                category="api",
                status="pass",
                message=f"DR enabled with {len(policies)} healthy protection policy(ies)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Replication",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 20. Snapshots ----------------------------------------------------

    def _check_snapshots(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("snapshots/")
            if data is None:
                return HealthCheckResult(
                    check_name="Snapshots",
                    category="api",
                    status="skipped",
                    message="Snapshots endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if not isinstance(data, list):
                data = [data] if data else []

            failed = [
                s.get("name", s.get("id", "?")) for s in data if str(s.get("status", "")).upper() in ("FAILED", "ERROR")
            ]
            details = {"total_snapshots": len(data), "failed_snapshots": len(failed)}

            if failed:
                return HealthCheckResult(
                    check_name="Snapshots",
                    category="api",
                    status="warning",
                    message=f"{len(failed)} failed snapshot(s): {failed}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Snapshots",
                category="api",
                status="pass",
                message=f"{len(data)} snapshot(s), none failed",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return HealthCheckResult(
                    check_name="Snapshots",
                    category="api",
                    status="skipped",
                    message="Snapshots endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Snapshots",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 21. Quotas -------------------------------------------------------

    def _check_quotas(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("quotas/")
            if data is None:
                return HealthCheckResult(
                    check_name="Quotas",
                    category="api",
                    status="skipped",
                    message="Quotas endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if not isinstance(data, list):
                data = [data] if data else []

            blocked = [
                q.get("name", q.get("id", "?"))
                for q in data
                if q.get("is_blocked") or str(q.get("state", "")).upper() == "BLOCKED"
            ]
            details = {"total_quotas": len(data), "blocked_users": len(blocked)}

            if blocked:
                return HealthCheckResult(
                    check_name="Quotas",
                    category="api",
                    status="warning",
                    message=f"{len(blocked)} blocked quota user(s): {blocked}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Quotas",
                category="api",
                status="pass",
                message=f"{len(data)} quota(s) configured, none blocked",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            if "404" in str(e) or "not found" in str(e).lower():
                return HealthCheckResult(
                    check_name="Quotas",
                    category="api",
                    status="skipped",
                    message="Quotas endpoint not available on this cluster",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Quotas",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 22. Data Protection ----------------------------------------------

    def _check_data_protection(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self.api_handler._make_api_request("protectionpolicies/")
            if data is None:
                return HealthCheckResult(
                    check_name="Data Protection",
                    category="api",
                    status="skipped",
                    message="Protection policies endpoint not available",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if not isinstance(data, list):
                data = [data] if data else []

            active_policies = [p for p in data if p.get("enabled") is not False]
            details = {"total_policies": len(data), "active_policies": len(active_policies)}

            if not active_policies:
                return HealthCheckResult(
                    check_name="Data Protection",
                    category="api",
                    status="warning",
                    message="No active protection policies configured",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Data Protection",
                category="api",
                status="pass",
                message=f"{len(active_policies)} active protection policy(ies)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Data Protection",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- 23. Monitoring Config --------------------------------------------

    def _check_monitoring_config(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._get_cluster_data()
            if not data:
                return HealthCheckResult(
                    check_name="Monitoring Config",
                    category="api",
                    status="error",
                    message="Failed to retrieve cluster data",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            snmp_fields = ["snmp_server", "snmp_community", "snmp_enabled", "snmp_trap_host"]
            syslog_fields = ["syslog_server", "syslog_enabled", "syslog_host"]

            snmp_configured = any(data.get(f) for f in snmp_fields)
            syslog_configured = any(data.get(f) for f in syslog_fields)

            if not snmp_configured and not syslog_configured:
                monitors = self.api_handler._make_api_request("monitors/")
                if monitors:
                    if isinstance(monitors, list) and monitors:
                        snmp_configured = True
                    elif isinstance(monitors, dict) and monitors:
                        snmp_configured = True

            details = {"snmp_configured": snmp_configured, "syslog_configured": syslog_configured}
            missing: List[str] = []
            if not snmp_configured:
                missing.append("SNMP")
            if not syslog_configured:
                missing.append("Syslog")

            if missing:
                return HealthCheckResult(
                    check_name="Monitoring Config",
                    category="api",
                    status="warning",
                    message=f"Monitoring not fully configured: {', '.join(missing)} not set",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Monitoring Config",
                category="api",
                status="pass",
                message="SNMP and syslog monitoring are configured",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Monitoring Config",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # ------------------------------------------------------------------
    # Prometheus metrics parser and device health (WP-10)
    # ------------------------------------------------------------------

    def _parse_prometheus_metrics(self, text: str) -> List[Dict[str, Any]]:
        """Parse Prometheus text format into list of {name, labels, value} dicts."""
        results: List[Dict[str, Any]] = []
        for line in text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "{" in line:
                name_part, rest = line.split("{", 1)
                labels_part, value_part = rest.rsplit("}", 1)
                labels = {}
                for item in labels_part.split(","):
                    if "=" in item:
                        k, v = item.split("=", 1)
                        labels[k.strip()] = v.strip().strip('"')
                name_part = name_part.strip()
            else:
                parts = line.split()
                name_part = parts[0]
                value_part = parts[1] if len(parts) > 1 else "0"
                labels = {}
            try:
                value = float(value_part.strip())
            except (ValueError, TypeError):
                continue
            results.append({"name": name_part, "labels": labels, "value": value})
        return results

    def _check_device_health(self) -> HealthCheckResult:
        """Check SSD/NVRAM device health via prometheusmetrics/devices."""
        start = time.time()
        try:
            if not hasattr(self.api_handler, "get_prometheus_metrics"):
                return HealthCheckResult(
                    check_name="Device Health (Prometheus)",
                    category="api",
                    status="skipped",
                    message="API handler does not support Prometheus metrics",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            text = self.api_handler.get_prometheus_metrics("devices")
            if not text:
                return HealthCheckResult(
                    check_name="Device Health (Prometheus)",
                    category="api",
                    status="skipped",
                    message="Prometheus devices endpoint unavailable",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            metrics = self._parse_prometheus_metrics(text)
            if not metrics:
                return HealthCheckResult(
                    check_name="Device Health (Prometheus)",
                    category="api",
                    status="skipped",
                    message="No device metrics returned",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            failed_devices = [m for m in metrics if "state" in m["name"].lower() and m["value"] != 1.0]
            media_errors = [m for m in metrics if "media_error" in m["name"].lower() and m["value"] > 0]
            total_metrics = len(metrics)

            details: Dict[str, Any] = {
                "total_metrics": total_metrics,
                "failed_device_count": len(failed_devices),
                "media_error_count": len(media_errors),
            }
            if failed_devices:
                details["failed_devices"] = [
                    {"name": m["name"], "labels": m["labels"], "value": m["value"]} for m in failed_devices[:10]
                ]
            if media_errors:
                details["media_errors"] = [
                    {"name": m["name"], "labels": m["labels"], "value": m["value"]} for m in media_errors[:10]
                ]

            if failed_devices or media_errors:
                issues: List[str] = []
                if failed_devices:
                    issues.append(f"{len(failed_devices)} device(s) in non-healthy state")
                if media_errors:
                    issues.append(f"{len(media_errors)} device(s) with media errors")
                return HealthCheckResult(
                    check_name="Device Health (Prometheus)",
                    category="api",
                    status="fail",
                    message="; ".join(issues),
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Device Health (Prometheus)",
                category="api",
                status="pass",
                message=f"All devices healthy ({total_metrics} metrics scanned)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Device Health (Prometheus)",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # ------------------------------------------------------------------
    # Tier 2 -- Node SSH checks
    # ------------------------------------------------------------------

    def run_node_ssh_checks(self) -> List[HealthCheckResult]:
        if not self.ssh_config:
            self.logger.info("SSH config not provided, skipping node SSH checks")
            return []

        cnode_ip = self._resolve_cnode_ip()
        if not cnode_ip:
            self.logger.warning("No CNode IP available for SSH checks")
            return []

        username = self.ssh_config.get("username", "vastdata")
        password = self.ssh_config.get("password", "")

        checks = [
            self._check_panic_alert_logs,
            self._check_management_ping,
            self._check_memory_usage,
            self._check_disk_space,
            self._check_time_sync,
            self._check_core_dumps,
            self._check_network_interfaces,
            self._check_vast_services,
            self._check_support_tool,
            self._check_vnetmap,
        ]

        results: List[HealthCheckResult] = []
        for i, fn in enumerate(checks, 1):
            self._check_cancel()
            self.logger.info("Running node SSH check %d/%d: %s", i, len(checks), fn.__name__)
            result = fn(cnode_ip, username, password)
            results.append(result)
            if result.status in ("fail", "error"):
                self.logger.warning("Check %s => %s: %s", fn.__name__, result.status, result.message)
        return results

    # --- Node SSH Check: Panic/Alert Logs ---------------------------------

    def _check_panic_alert_logs(self, host: str, username: str, password: str) -> HealthCheckResult:
        start = time.time()
        try:
            cmd = "clush -g cnodes 'dmesg | grep -iE \"PANIC|ALERT|fail\"' 2>/dev/null | tail -20"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            if rc != 0 and not stdout:
                return HealthCheckResult(
                    check_name="Panic/Alert Logs",
                    category="node_ssh",
                    status="error",
                    message=f"SSH command failed: {stderr or 'connection error'}",
                    details={"host": host, "stderr": stderr},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            output = stdout.strip()
            if output:
                return HealthCheckResult(
                    check_name="Panic/Alert Logs",
                    category="node_ssh",
                    status="fail",
                    message="PANIC/ALERT/fail entries found in dmesg",
                    details={"host": host, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Panic/Alert Logs",
                category="node_ssh",
                status="pass",
                message="No PANIC/ALERT/fail entries found in dmesg",
                details={"host": host, "stdout": ""},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Panic/Alert Logs",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: Management Ping ----------------------------------

    def _check_management_ping(self, host: str, username: str, password: str) -> HealthCheckResult:
        start = time.time()
        max_duration = 60
        try:
            mgmt_ips: List[str] = []
            try:
                cnodes = self.api_handler._make_api_request("cnodes/")
                if cnodes and isinstance(cnodes, list):
                    for node in cnodes:
                        for fld in ("ipmi_ip", "mgmt_ip", "bmc_ip"):
                            ip = node.get(fld)
                            if ip and ip not in mgmt_ips:
                                mgmt_ips.append(ip)
            except Exception:
                pass

            if not mgmt_ips:
                return HealthCheckResult(
                    check_name="Management Ping",
                    category="node_ssh",
                    status="skipped",
                    message="No management/IPMI IPs found to ping",
                    details={"host": host},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            reachable: List[str] = []
            unreachable: List[str] = []
            skipped: List[str] = []
            for ip in mgmt_ips:
                self._check_cancel()
                if time.time() - start > max_duration:
                    skipped.extend([i for i in mgmt_ips if i not in reachable and i not in unreachable])
                    break
                rc, _out, _err = run_ssh_command(host, username, password, f"ping -c 1 -W 2 {ip}", timeout=10)
                if rc == 0:
                    reachable.append(ip)
                else:
                    unreachable.append(ip)

            details = {"host": host, "reachable": reachable, "unreachable": unreachable, "skipped": skipped}

            if skipped:
                return HealthCheckResult(
                    check_name="Management Ping",
                    category="node_ssh",
                    status="warning",
                    message=f"Check timed out after {max_duration}s; {len(reachable)} reachable, {len(unreachable)} unreachable, {len(skipped)} skipped",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            if unreachable and not reachable:
                return HealthCheckResult(
                    check_name="Management Ping",
                    category="node_ssh",
                    status="fail",
                    message=f"All {len(unreachable)} management IP(s) unreachable",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            if unreachable:
                return HealthCheckResult(
                    check_name="Management Ping",
                    category="node_ssh",
                    status="warning",
                    message=f"{len(unreachable)} of {len(mgmt_ips)} management IP(s) unreachable: {unreachable}",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Management Ping",
                category="node_ssh",
                status="pass",
                message=f"All {len(reachable)} management IP(s) reachable",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Management Ping",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: VAST Support Tools -------------------------------

    def _check_support_tool(self, host: str, username: str, password: str) -> HealthCheckResult:
        start = time.time()
        try:
            cmd = "vast_support_tools.py --quick-check 2>/dev/null || echo 'Tool not available'"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""
            return HealthCheckResult(
                check_name="VAST Support Tools",
                category="node_ssh",
                status="pass",
                message="Support tools check completed (informational)",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="VAST Support Tools",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: VNet Map -----------------------------------------

    def _check_vnetmap(self, host: str, username: str, password: str) -> HealthCheckResult:
        start = time.time()
        try:
            cmd = "vnetmap.py 2>/dev/null || echo 'vnetmap not available'"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""
            return HealthCheckResult(
                check_name="VNet Map",
                category="node_ssh",
                status="pass",
                message="vnetmap check completed (informational)",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="VNet Map",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: Memory Usage ---------------------------------------

    def _check_memory_usage(self, host: str, username: str, password: str) -> HealthCheckResult:
        """Check memory usage across cluster nodes."""
        start = time.time()
        try:
            cmd = "clush -g cnodes 'free -m | grep Mem' 2>/dev/null | head -10"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            if rc != 0 and not stdout:
                return HealthCheckResult(
                    check_name="Memory Usage",
                    category="node_ssh",
                    status="error",
                    message=f"SSH command failed: {stderr or 'connection error'}",
                    details={"host": host, "stderr": stderr},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            output = stdout.strip() if stdout else ""
            high_usage_nodes = []

            for line in output.split("\n"):
                if "Mem:" in line:
                    parts = line.split()
                    if len(parts) >= 4:
                        try:
                            total = int(parts[1]) if parts[1].isdigit() else int(parts[2])
                            used = int(parts[2]) if parts[2].isdigit() else int(parts[3])
                            pct = (used / total) * 100 if total > 0 else 0
                            if pct > 90:
                                high_usage_nodes.append({"line": line, "usage_pct": round(pct, 1)})
                        except (ValueError, IndexError):
                            pass

            if high_usage_nodes:
                return HealthCheckResult(
                    check_name="Memory Usage",
                    category="node_ssh",
                    status="warning",
                    message=f"{len(high_usage_nodes)} node(s) with >90% memory usage",
                    details={"host": host, "high_usage_nodes": high_usage_nodes, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Memory Usage",
                category="node_ssh",
                status="pass",
                message="Memory usage within normal limits",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Memory Usage",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: Disk Space -----------------------------------------

    def _check_disk_space(self, host: str, username: str, password: str) -> HealthCheckResult:
        """Check disk space on critical filesystems."""
        start = time.time()
        try:
            cmd = "clush -g cnodes 'df -h / /var /tmp 2>/dev/null | grep -v Filesystem' 2>/dev/null | head -20"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            if rc != 0 and not stdout:
                return HealthCheckResult(
                    check_name="Disk Space",
                    category="node_ssh",
                    status="error",
                    message=f"SSH command failed: {stderr or 'connection error'}",
                    details={"host": host, "stderr": stderr},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            output = stdout.strip() if stdout else ""
            high_usage = []

            for line in output.split("\n"):
                if "%" in line:
                    parts = line.split()
                    for part in parts:
                        if part.endswith("%"):
                            try:
                                pct = int(part.rstrip("%"))
                                if pct > 85:
                                    high_usage.append({"line": line.strip(), "usage_pct": pct})
                                    break
                            except ValueError:
                                pass

            if high_usage:
                return HealthCheckResult(
                    check_name="Disk Space",
                    category="node_ssh",
                    status="warning",
                    message=f"{len(high_usage)} filesystem(s) with >85% usage",
                    details={"host": host, "high_usage": high_usage, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Disk Space",
                category="node_ssh",
                status="pass",
                message="Disk space within normal limits",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Disk Space",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: Time Sync ------------------------------------------

    def _check_time_sync(self, host: str, username: str, password: str) -> HealthCheckResult:
        """Check NTP/chrony time synchronization."""
        start = time.time()
        try:
            cmd = "clush -g cnodes 'chronyc tracking 2>/dev/null || ntpq -p 2>/dev/null || timedatectl status' 2>/dev/null | head -30"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""
            output_lower = output.lower()

            if "not synchronized" in output_lower or "no server" in output_lower:
                return HealthCheckResult(
                    check_name="Time Sync",
                    category="node_ssh",
                    status="warning",
                    message="Time sync issues detected",
                    details={"host": host, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Time Sync",
                category="node_ssh",
                status="pass",
                message="Time synchronization check completed",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Time Sync",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: Core Dumps -----------------------------------------

    def _check_core_dumps(self, host: str, username: str, password: str) -> HealthCheckResult:
        """Check for recent core dumps."""
        start = time.time()
        try:
            cmd = 'clush -g cnodes \'ls -la /var/crash/ 2>/dev/null | tail -5; coredumpctl list --since "7 days ago" 2>/dev/null | tail -5\' 2>/dev/null'
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""
            has_cores = False

            for line in output.split("\n"):
                if "core" in line.lower() or ".dump" in line.lower() or "coredump" in line.lower():
                    if "No such file" not in line and "total 0" not in line:
                        has_cores = True
                        break

            if has_cores:
                return HealthCheckResult(
                    check_name="Core Dumps",
                    category="node_ssh",
                    status="warning",
                    message="Core dump files found - investigate recent crashes",
                    details={"host": host, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Core Dumps",
                category="node_ssh",
                status="pass",
                message="No recent core dumps found",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Core Dumps",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: Network Interfaces ---------------------------------

    def _check_network_interfaces(self, host: str, username: str, password: str) -> HealthCheckResult:
        """Check network interface status."""
        start = time.time()
        try:
            cmd = "clush -g cnodes 'ip link show | grep -E \"state DOWN|NO-CARRIER\"' 2>/dev/null | head -10"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""

            # Ignore expected down interfaces and unconfigured interfaces
            down_interfaces = []
            for line in output.split("\n"):
                line = line.strip()
                if line and ("state DOWN" in line or "NO-CARRIER" in line):
                    # Skip virtual/expected interfaces
                    if any(x in line.lower() for x in ["docker", "veth", "br-", "virbr", "lo:"]):
                        continue
                    # Skip unconfigured interfaces (qdisc noop = no driver/config loaded)
                    if "qdisc noop" in line:
                        continue
                    down_interfaces.append(line)

            if down_interfaces:
                return HealthCheckResult(
                    check_name="Network Interfaces",
                    category="node_ssh",
                    status="warning",
                    message=f"{len(down_interfaces)} interface(s) DOWN or NO-CARRIER",
                    details={"host": host, "down_interfaces": down_interfaces, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Network Interfaces",
                category="node_ssh",
                status="pass",
                message="Network interfaces operational",
                details={"host": host, "stdout": output if output else "All interfaces UP"},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Network Interfaces",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Node SSH Check: VAST Services --------------------------------------

    def _check_vast_services(self, host: str, username: str, password: str) -> HealthCheckResult:
        """Check VAST service status."""
        start = time.time()
        try:
            cmd = "clush -g cnodes 'systemctl list-units --state=failed vast* 2>/dev/null || systemctl status vast* 2>/dev/null | grep -E \"Active:|failed\"' 2>/dev/null | head -20"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""
            output_lower = output.lower()

            if "failed" in output_lower and "0 loaded" not in output_lower:
                return HealthCheckResult(
                    check_name="VAST Services",
                    category="node_ssh",
                    status="warning",
                    message="Failed VAST service(s) detected",
                    details={"host": host, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="VAST Services",
                category="node_ssh",
                status="pass",
                message="VAST services check completed",
                details={"host": host, "stdout": output if output else "No failed services"},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="VAST Services",
                category="node_ssh",
                status="error",
                message=f"Check failed: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # ------------------------------------------------------------------
    # Tier 3 -- Switch SSH checks
    # ------------------------------------------------------------------

    def run_switch_ssh_checks(self) -> List[HealthCheckResult]:
        if not self.switch_ssh_config:
            self.logger.info("Switch SSH config not provided, skipping switch SSH checks")
            return []

        switch_ips = self._resolve_switch_ips()
        if not switch_ips:
            self.logger.warning("No switch IPs available for SSH checks")
            return []

        username = self.switch_ssh_config.get("username", "cumulus")
        password = self.switch_ssh_config.get("password", "")

        checks = [
            self._check_mlag_status,
            self._check_switch_ntp,
            self._check_switch_config_backup,
        ]

        results: List[HealthCheckResult] = []
        for switch_ip in switch_ips:
            for i, fn in enumerate(checks, 1):
                self._check_cancel()
                self.logger.info("Running switch SSH check %d/%d on %s: %s", i, len(checks), switch_ip, fn.__name__)
                result = fn(switch_ip, username, password)
                results.append(result)
                if result.status in ("fail", "error"):
                    self.logger.warning(
                        "Check %s on %s => %s: %s", fn.__name__, switch_ip, result.status, result.message
                    )
        return results

    # --- Switch SSH Check: MLAG Status ------------------------------------

    def _check_mlag_status(self, host: str, username: str, password: str) -> HealthCheckResult:
        start = time.time()
        try:
            cmd = "nv show mlag 2>/dev/null || show mlag detail 2>/dev/null || echo 'MLAG command not available'"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            if rc != 0 and not stdout:
                return HealthCheckResult(
                    check_name="MLAG Status",
                    category="switch_ssh",
                    status="error",
                    message=f"SSH command failed on {host}: {stderr or 'connection error'}",
                    details={"host": host, "stderr": stderr},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            output = stdout.strip() if stdout else ""
            output_lower = output.lower()

            if "mlag command not available" in output_lower:
                return HealthCheckResult(
                    check_name="MLAG Status",
                    category="switch_ssh",
                    status="skipped",
                    message=f"MLAG command not available on {host}",
                    details={"host": host, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            peer_alive = False
            backup_active = False
            for line in output.splitlines():
                ll = line.lower().strip()
                if "peer-alive" in ll:
                    peer_alive = "true" in ll or "yes" in ll
                if "backup-active" in ll:
                    backup_active = "true" in ll or "yes" in ll

            details = {"host": host, "stdout": output, "peer_alive": peer_alive, "backup_active": backup_active}

            if peer_alive and backup_active:
                return HealthCheckResult(
                    check_name="MLAG Status",
                    category="switch_ssh",
                    status="pass",
                    message=f"MLAG healthy on {host}: peer-alive and backup-active",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            issues: List[str] = []
            if not peer_alive:
                issues.append("peer-alive not confirmed")
            if not backup_active:
                issues.append("backup-active not confirmed")
            return HealthCheckResult(
                check_name="MLAG Status",
                category="switch_ssh",
                status="fail",
                message=f"MLAG issue on {host}: {', '.join(issues)}",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="MLAG Status",
                category="switch_ssh",
                status="error",
                message=f"Check failed on {host}: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Switch SSH Check: NTP --------------------------------------------

    def _check_switch_ntp(self, host: str, username: str, password: str) -> HealthCheckResult:
        start = time.time()
        try:
            cmd = "ntpq -p 2>/dev/null || echo 'NTP not available'"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""

            if "ntp not available" in output.lower():
                return HealthCheckResult(
                    check_name="Switch NTP",
                    category="switch_ssh",
                    status="warning",
                    message=f"NTP not available on {host}",
                    details={"host": host, "stdout": output},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            lines = output.splitlines()
            peer_lines = [ln for ln in lines if ln.strip() and ln.strip()[0] in ("*", "+", "-", "o", "x", ".", "#")]

            if peer_lines:
                return HealthCheckResult(
                    check_name="Switch NTP",
                    category="switch_ssh",
                    status="pass",
                    message=f"NTP peers found on {host}",
                    details={"host": host, "stdout": output, "peer_count": len(peer_lines)},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Switch NTP",
                category="switch_ssh",
                status="warning",
                message=f"No NTP peers found on {host}",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Switch NTP",
                category="switch_ssh",
                status="error",
                message=f"Check failed on {host}: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # --- Switch SSH Check: Config Backup ----------------------------------

    def _check_switch_config_backup(self, host: str, username: str, password: str) -> HealthCheckResult:
        start = time.time()
        try:
            cmd = "nv config show 2>/dev/null | head -50 || echo 'Config not available'"
            rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30)

            output = stdout.strip() if stdout else ""
            return HealthCheckResult(
                check_name="Switch Config Backup",
                category="switch_ssh",
                status="pass",
                message=f"Switch config captured from {host} (informational)",
                details={"host": host, "stdout": output},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Switch Config Backup",
                category="switch_ssh",
                status="error",
                message=f"Check failed on {host}: {e}",
                details={"host": host},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    def run_custom_scripts(self, scripts: List[Dict[str, str]]) -> List[HealthCheckResult]:
        # Placeholder for future implementation
        return []

    # ------------------------------------------------------------------
    # Orchestrator
    # ------------------------------------------------------------------

    def run_all_checks(self, tiers: Optional[List[int]] = None) -> HealthCheckReport:
        if tiers is None:
            tiers = [1]

        results: List[HealthCheckResult] = []

        if 1 in tiers:
            results.extend(self.run_api_checks())
        if 2 in tiers:
            results.extend(self.run_node_ssh_checks())
        if 3 in tiers:
            results.extend(self.run_switch_ssh_checks())

        cluster_data = self._get_cluster_data()
        cluster_name = "Unknown"
        cluster_version = "Unknown"
        if cluster_data:
            cluster_name = cluster_data.get("name", "Unknown")
            cluster_version = str(cluster_data.get("sw_version", "Unknown"))

        report = HealthCheckReport(
            cluster_ip=getattr(self.api_handler, "cluster_ip", "Unknown"),
            cluster_name=cluster_name,
            cluster_version=cluster_version,
            timestamp=self._now(),
            results=results,
            summary=self._summarize(results),
            manual_checklist=list(self.MANUAL_CHECKLIST),
            tiers_run=tiers,
        )
        return report
