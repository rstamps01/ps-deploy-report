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
from typing import Any, Dict, List, Optional, cast

from utils.ssh_adapter import run_ssh_command, run_interactive_ssh


class CancelledError(Exception):
    """Raised when a health check run is cancelled by the user."""

    pass


@dataclass
class HealthCheckResult:
    """Single health check outcome."""

    check_name: str
    category: str  # "api" | "switch_ssh" | "performance" | "custom"
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

    Tier 1 -- API checks (read-only GET calls)
    Tier 3 -- Switch SSH checks
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
        progress_callback: Optional[Any] = None,
    ) -> None:
        self.api_handler = api_handler
        self.ssh_config = ssh_config
        self.switch_ssh_config = switch_ssh_config
        self.cancel_event = cancel_event
        self.logger = logger or logging.getLogger(__name__)
        self.thresholds = {**self.DEFAULT_THRESHOLDS, **(thresholds or {})}
        self.progress_callback = progress_callback
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
            user_ips = list(self.switch_ssh_config["switch_ips"])
            self.logger.info(f"Using {len(user_ips)} user-provided switch IP(s)")
            return user_ips

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
            self._check_device_health,
            # Post-install validation checks
            self._check_call_home_status,
            self._check_rack_uheight_config,
            self._check_switches_registered,
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
                if self.progress_callback:
                    self.progress_callback(i, len(checks), fn.__name__)
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
            mgmt_inactive: Optional[str] = None
            for node in data:
                name = node.get("name", node.get("id", "unknown"))
                state = str(node.get("state", node.get("status", ""))).upper()
                if state != "ACTIVE":
                    if node.get("is_mgmt", False):
                        mgmt_inactive = str(name)
                    else:
                        inactive.append(name)
                if node.get("enabled") is False:
                    disabled.append(name)

            details: Dict[str, Any] = {"total": total, "inactive": inactive, "disabled": disabled}
            if mgmt_inactive:
                details["mgmt_cnode"] = mgmt_inactive

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

            if mgmt_inactive:
                return HealthCheckResult(
                    check_name="CNode Status",
                    category="api",
                    status="pass",
                    message=f"All {total} CNodes healthy (VMS on {mgmt_inactive})",
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
                        desc = d.get("description") or d.get("name") or d.get("event_name") or d.get("message")
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
                    status="warning",
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
                    status="warning",
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

            license_info = self._resolve_license(data)
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
                message=f"License is present and active ({license_info})",
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

    def _resolve_license(self, cluster_data: Dict[str, Any]) -> Optional[str]:
        """Resolve license status from cluster data and the licenses/ endpoint.

        The clusters/ endpoint exposes license info under varying field names
        across VAST API versions.  When the primary ``license`` field is empty,
        fall back to alternative fields and then to the ``licenses/`` endpoint.
        """
        _LICENSE_FIELDS = ("license", "license_state", "license_type", "license_status")
        for field_name in _LICENSE_FIELDS:
            val = cluster_data.get(field_name)
            if val and str(val).strip().lower() not in ("", "none", "unknown", "null"):
                return str(val).strip()

        if cluster_data.get("is_licensed") is True:
            return "Licensed"

        try:
            licenses = self.api_handler._make_api_request("licenses/")
            if isinstance(licenses, list) and licenses:
                lic = licenses[0]
                if "license" in str(lic.get("url", "")) or lic.get("license_key") or lic.get("key"):
                    state = lic.get("license_state") or lic.get("license_type")
                    if state:
                        return str(state).strip()
                    return "Active"
            if isinstance(licenses, dict) and licenses:
                if licenses.get("license_key") or licenses.get("key"):
                    state = licenses.get("license_state") or licenses.get("license_type")
                    if state:
                        return str(state).strip()
                    return "Active"
        except Exception:
            pass

        return None

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
    # Post-Install Validation Checks
    # ------------------------------------------------------------------

    def _check_call_home_status(self) -> HealthCheckResult:
        """Check Call Home / Support Contact configuration via ``callhomeconfigs/``.

        Primary source is the dedicated ``callhomeconfigs/`` endpoint (available
        on VAST v5.x+).  Falls back to boolean fields in ``clusters/`` for
        older or non-standard deployments.
        """
        start = time.time()
        try:
            cluster_data = self._get_cluster_data()
            if not cluster_data:
                return HealthCheckResult(
                    check_name="Call Home Status",
                    category="api",
                    status="skipped",
                    message="Unable to retrieve cluster configuration",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            call_home_state = self._resolve_call_home(cluster_data)

            details: Dict[str, Any] = {"call_home_enabled": call_home_state}

            try:
                configs = self.api_handler._make_api_request("callhomeconfigs/")
                cfg = None
                if isinstance(configs, list) and configs:
                    cfg = configs[0]
                elif isinstance(configs, dict) and configs:
                    cfg = configs
                if cfg:
                    details["cloud_registered"] = cfg.get("cloud_registered")
                    details["cloud_enabled"] = cfg.get("cloud_enabled")
                    details["log_enabled"] = cfg.get("log_enabled")
                    details["bundle_enabled"] = cfg.get("bundle_enabled")
                    details["customer"] = cfg.get("customer") or "Not set"
            except Exception:
                pass

            if call_home_state is None:
                return HealthCheckResult(
                    check_name="Call Home Status",
                    category="api",
                    status="pass",
                    message="Call Home status not exposed via API — verify in VMS GUI.",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if not call_home_state:
                return HealthCheckResult(
                    check_name="Call Home Status",
                    category="api",
                    status="warning",
                    message="Call Home is not enabled. Consider enabling for proactive support.",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            parts = []
            if details.get("cloud_registered"):
                parts.append("cloud registered")
            if details.get("log_enabled"):
                parts.append("logging active")
            if details.get("bundle_enabled"):
                parts.append("bundles active")
            suffix = f" ({', '.join(parts)})" if parts else ""

            return HealthCheckResult(
                check_name="Call Home Status",
                category="api",
                status="pass",
                message=f"Call Home is enabled{suffix}",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Call Home Status",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    def _resolve_call_home(self, cluster_data: Dict[str, Any]) -> Optional[bool]:
        """Determine whether Call Home / Phone Home / SSP is enabled.

        Returns ``True`` (enabled), ``False`` (explicitly disabled), or
        ``None`` (field not present in the API — status cannot be determined).

        Primary source is the dedicated ``callhomeconfigs/`` endpoint which
        exposes ``cloud_registered``, ``log_enabled``, ``bundle_enabled``,
        and ``cloud_enabled`` fields.  Falls back to ``clusters/`` fields
        for older API versions.
        """
        try:
            configs = self.api_handler._make_api_request("callhomeconfigs/")
            cfg: Optional[Dict[str, Any]] = None
            if isinstance(configs, list) and configs:
                cfg = configs[0]
            elif isinstance(configs, dict) and configs:
                cfg = configs

            if cfg:
                cloud_registered = cfg.get("cloud_registered", False)
                log_enabled = cfg.get("log_enabled", False)
                bundle_enabled = cfg.get("bundle_enabled", False)
                cloud_enabled = cfg.get("cloud_enabled", False)
                if cloud_registered or log_enabled or bundle_enabled or cloud_enabled:
                    return True
                return False
        except Exception:
            pass

        _BOOL_FIELDS = (
            "ssp_enabled",
            "phone_home_enabled",
            "call_home_enabled",
            "phone_home",
            "call_home",
            "cloud_enabled",
            "support_portal_enabled",
        )
        for field_name in _BOOL_FIELDS:
            val = cluster_data.get(field_name)
            if val is not None:
                return bool(val)

        return None

    def _check_rack_uheight_config(self) -> HealthCheckResult:
        """Check if rack and U-height settings are configured for CBoxes/DBoxes."""
        start = time.time()
        try:
            # Get racks
            racks = self.api_handler._make_api_request("racks/")
            rack_count = len(racks) if isinstance(racks, list) else 0

            # Check CBoxes for rack assignments
            cboxes = self.api_handler._make_api_request("cboxes/")
            dboxes = self.api_handler._make_api_request("dboxes/")

            cboxes_missing_rack = []
            dboxes_missing_rack = []

            if isinstance(cboxes, list):
                for cb in cboxes:
                    if not cb.get("rack") and not cb.get("rack_id"):
                        cboxes_missing_rack.append(cb.get("name", cb.get("id", "Unknown")))

            if isinstance(dboxes, list):
                for db in dboxes:
                    if not db.get("rack") and not db.get("rack_id"):
                        dboxes_missing_rack.append(db.get("name", db.get("id", "Unknown")))

            details = {
                "rack_count": rack_count,
                "cboxes_missing_rack": cboxes_missing_rack,
                "dboxes_missing_rack": dboxes_missing_rack,
            }

            missing_total = len(cboxes_missing_rack) + len(dboxes_missing_rack)

            if rack_count == 0:
                return HealthCheckResult(
                    check_name="Rack/U-Height Configuration",
                    category="api",
                    status="warning",
                    message="No racks defined. Create racks and assign U-height for accurate diagrams.",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            if missing_total > 0:
                return HealthCheckResult(
                    check_name="Rack/U-Height Configuration",
                    category="api",
                    status="warning",
                    message=f"{missing_total} device(s) missing rack assignment. Assign U-height for rack layout diagram.",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            return HealthCheckResult(
                check_name="Rack/U-Height Configuration",
                category="api",
                status="pass",
                message=f"All devices assigned to {rack_count} rack(s)",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Rack/U-Height Configuration",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    def _check_switches_registered(self) -> HealthCheckResult:
        """Check if switches are registered in VMS for port mapping."""
        start = time.time()
        try:
            switches = self.api_handler._make_api_request("switches/")
            switch_count = len(switches) if isinstance(switches, list) else 0

            details = {
                "switch_count": switch_count,
                "switches": [
                    {"name": sw.get("name"), "ip": sw.get("mgmt_ip")}
                    for sw in (switches if isinstance(switches, list) else [])
                ],
            }

            if switch_count == 0:
                return HealthCheckResult(
                    check_name="Switches in VMS",
                    category="api",
                    status="skipped",
                    message="No switches registered",
                    details=details,
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            return HealthCheckResult(
                check_name="Switches in VMS",
                category="api",
                status="pass",
                message=f"{switch_count} switch(es) registered in VMS",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Switches in VMS",
                category="api",
                status="error",
                message=f"Check failed: {e}",
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

    # ------------------------------------------------------------------
    # Tier 3 -- Switch SSH checks
    # ------------------------------------------------------------------

    def _detect_switch_type(self, host: str, username: str, password: str, **ssh_kwargs: Any) -> str:
        """Detect whether a switch runs Onyx or Cumulus Linux.

        Attempts ``show version`` via interactive SSH first — Onyx responds
        with Product/Mellanox identifiers.  The restricted-shell rejection
        message (``UNIX shell commands cannot be executed``) is also treated
        as an Onyx indicator because Cumulus never produces it.

        Returns ``"onyx"`` or ``"cumulus"`` (default).
        """
        _ONYX_INDICATORS = (
            "onyx",
            "mellanox",
            "product name",
            "unix shell commands cannot be executed",
        )
        try:
            rc, stdout, stderr = run_interactive_ssh(host, username, password, "show version", timeout=15, **ssh_kwargs)
            combined = ((stdout or "") + (stderr or "")).lower()
            if any(tag in combined for tag in _ONYX_INDICATORS):
                self.logger.info("Switch %s detected as Onyx", host)
                return "onyx"
        except Exception:
            pass

        self.logger.info("Switch %s treated as Cumulus (default)", host)
        return "cumulus"

    def run_switch_ssh_checks(self) -> List[HealthCheckResult]:
        if not self.switch_ssh_config:
            self.logger.info("Switch SSH config not provided, skipping switch SSH checks")
            return []

        switch_ips = self._resolve_switch_ips()
        if not switch_ips:
            self.logger.warning("No switch IPs available for SSH checks")
            return []

        username = self.switch_ssh_config.get("username", "cumulus")
        primary_password = self.switch_ssh_config.get("password", "")
        # RM-2: when the one-shot pipeline has already proved which password
        # authenticates against which switch IP (see oneshot_runner._resolve_
        # switch_password_candidates), pass that map through here so each
        # check uses the correct credential.  Without this we silently fall
        # back to ``primary_password`` and log spurious auth failures for any
        # switch that uses a different default password (e.g. a spare leaf
        # on ``VastData1!`` while the pair is on ``Vastdata1!``).
        raw_pw_by_ip = self.switch_ssh_config.get("password_by_ip") or {}
        if not isinstance(raw_pw_by_ip, dict):
            raw_pw_by_ip = {}
        password_by_ip: Dict[str, str] = {str(k): str(v) for k, v in raw_pw_by_ip.items() if v}

        def _password_for(switch_ip: str) -> str:
            pw = password_by_ip.get(str(switch_ip))
            if pw:
                return pw
            return primary_password

        jump_kwargs: Dict[str, Any] = {}
        if self.switch_ssh_config.get("proxy_jump"):
            pj = cast(Dict[str, Any], self.switch_ssh_config["proxy_jump"])
            jump_kwargs = {
                "jump_host": pj.get("host"),
                "jump_user": pj.get("username"),
                "jump_password": pj.get("password"),
            }

        checks = [
            self._check_mlag_status,
            self._check_switch_ntp,
            self._check_switch_config_backup,
        ]

        results: List[HealthCheckResult] = []
        total_ssh_checks = len(switch_ips) * len(checks)
        ssh_idx = 0
        for switch_ip in switch_ips:
            self._check_cancel()
            password = _password_for(switch_ip)
            switch_os = self._detect_switch_type(switch_ip, username, password, **jump_kwargs)
            for i, fn in enumerate(checks, 1):
                self._check_cancel()
                ssh_idx += 1
                self.logger.info(
                    "Running switch SSH check %d/%d on %s (%s): %s",
                    i,
                    len(checks),
                    switch_ip,
                    switch_os,
                    fn.__name__,
                )
                result = fn(switch_ip, username, password, switch_os=switch_os, **jump_kwargs)
                results.append(result)
                if self.progress_callback:
                    self.progress_callback(ssh_idx, total_ssh_checks, f"{fn.__name__}@{switch_ip}")
                if result.status in ("fail", "error"):
                    self.logger.warning(
                        "Check %s on %s => %s: %s", fn.__name__, switch_ip, result.status, result.message
                    )

        results = self._consolidate_switch_results(results)
        return results

    @staticmethod
    def _consolidate_switch_results(results: List[HealthCheckResult]) -> List[HealthCheckResult]:
        """Merge switch_ssh results that share the same check name and status.

        When both switches in a pair report identical status for a given
        check, the duplicate is removed and the remaining entry mentions
        both switch IPs.  Checks with differing statuses are kept separate.
        """
        from collections import OrderedDict

        groups: OrderedDict[str, List[int]] = OrderedDict()
        for idx, r in enumerate(results):
            if r.category == "switch_ssh":
                groups.setdefault(r.check_name, []).append(idx)

        skip: set = set()
        replacements: Dict[int, HealthCheckResult] = {}

        for check_name, indices in groups.items():
            if len(indices) <= 1:
                continue

            first = results[indices[0]]
            if not all(results[i].status == first.status for i in indices):
                continue

            hosts = []
            for i in indices:
                r = results[i]
                host = r.details.get("host", "") if r.details else ""
                if host:
                    hosts.append(host)
            host_label = ", ".join(hosts) if hosts else "switches"

            base_msg = first.message
            for h in hosts:
                base_msg = base_msg.replace(h, "").replace("on ,", "on").replace("on  ", "on ")
            base_msg = base_msg.strip().rstrip(":")

            if check_name == "MLAG Status":
                os_type = (first.details or {}).get("switch_os", "cumulus")
                if first.status == "pass":
                    if os_type == "onyx":
                        message = f"MLAG healthy on {host_label}: operational status Up"
                    else:
                        message = f"MLAG healthy on {host_label}: peer-alive and backup-active"
                elif first.status == "fail":
                    if os_type == "onyx":
                        issues = []
                        if not (first.details or {}).get("admin_enabled"):
                            issues.append("admin status not Enabled")
                        if not (first.details or {}).get("oper_up"):
                            issues.append("operational status not Up")
                        message = f"MLAG issue on {host_label}: {', '.join(issues)}" if issues else first.message
                    else:
                        issues = []
                        if not (first.details or {}).get("peer_alive"):
                            issues.append("peer-alive not confirmed")
                        if not (first.details or {}).get("backup_active"):
                            issues.append("backup-active not confirmed")
                        message = f"MLAG issue on {host_label}: {', '.join(issues)}" if issues else first.message
                else:
                    message = f"{base_msg} ({host_label})"
            else:
                if host_label in base_msg:
                    message = base_msg
                else:
                    message = f"{base_msg} ({host_label})"

            combined_details = dict(first.details or {})
            combined_details["hosts"] = hosts

            merged = HealthCheckResult(
                check_name=check_name,
                category="switch_ssh",
                status=first.status,
                message=message,
                details=combined_details,
                timestamp=first.timestamp,
                duration_seconds=first.duration_seconds,
            )
            replacements[indices[0]] = merged
            for i in indices[1:]:
                skip.add(i)

        consolidated = []
        for idx, r in enumerate(results):
            if idx in skip:
                continue
            if idx in replacements:
                consolidated.append(replacements[idx])
            else:
                consolidated.append(r)
        return consolidated

    # --- Switch SSH Check: MLAG Status ------------------------------------

    def _check_mlag_status(
        self, host: str, username: str, password: str, *, switch_os: str = "cumulus", **ssh_kwargs: Any
    ) -> HealthCheckResult:
        start = time.time()
        try:
            if switch_os == "onyx":
                return self._check_mlag_onyx(host, username, password, start, **ssh_kwargs)
            return self._check_mlag_cumulus(host, username, password, start, **ssh_kwargs)
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

    # -- Onyx MLAG ---------------------------------------------------------

    def _check_mlag_onyx(
        self, host: str, username: str, password: str, start: float, **ssh_kwargs: Any
    ) -> HealthCheckResult:
        """Parse ``show mlag`` output from Mellanox Onyx switches.

        Key fields:
            Admin status: Enabled
            Operational status: Up
            MLAG IPLs → Operational State: Up
            MLAG Members → State: Up
        """
        rc, stdout, stderr = run_interactive_ssh(host, username, password, "show mlag", timeout=30, **ssh_kwargs)
        output = (stdout or "").strip()

        if not output:
            if stderr and "authentication failed" in (stderr or "").lower():
                return HealthCheckResult(
                    check_name="MLAG Status",
                    category="switch_ssh",
                    status="error",
                    message=f"SSH authentication failed on {host}",
                    details={"host": host, "stderr": stderr},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="MLAG Status",
                category="switch_ssh",
                status="warning",
                message=f"MLAG status could not be determined on {host} (no output from show mlag)",
                details={"host": host, "stderr": stderr or ""},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

        admin_enabled = False
        oper_up = False
        ipl_up = False
        members_up = False
        found_any = False

        in_ipls = False
        in_members = False

        for line in output.splitlines():
            ll = line.lower().strip()

            if "mlag ipls summary" in ll:
                in_ipls = True
                in_members = False
                continue
            if "mlag members summary" in ll:
                in_members = True
                in_ipls = False
                continue

            if ll.startswith("admin status"):
                found_any = True
                admin_enabled = "enabled" in ll
            elif ll.startswith("operational status"):
                found_any = True
                oper_up = "up" in ll

            if in_ipls and "---" not in ll and ll and not ll.startswith("id"):
                parts = ll.split()
                if any(p == "up" for p in parts):
                    ipl_up = True
                    found_any = True

            if in_members:
                if "---" in ll or ll.startswith("system-id"):
                    continue
                parts = ll.split()
                if any(p == "up" for p in parts):
                    members_up = True
                    found_any = True

        details: Dict[str, Any] = {
            "host": host,
            "switch_os": "onyx",
            "stdout": output,
            "admin_enabled": admin_enabled,
            "oper_up": oper_up,
            "ipl_up": ipl_up,
            "members_up": members_up,
        }

        if not found_any:
            return HealthCheckResult(
                check_name="MLAG Status",
                category="switch_ssh",
                status="warning",
                message=f"MLAG fields not found in output on {host} — verify switch CLI access",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

        if admin_enabled and oper_up:
            return HealthCheckResult(
                check_name="MLAG Status",
                category="switch_ssh",
                status="pass",
                message=f"MLAG healthy on {host}: operational status Up",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

        issues: List[str] = []
        if not admin_enabled:
            issues.append("admin status not Enabled")
        if not oper_up:
            issues.append("operational status not Up")
        return HealthCheckResult(
            check_name="MLAG Status",
            category="switch_ssh",
            status="fail",
            message=f"MLAG issue on {host}: {', '.join(issues)}",
            details=details,
            timestamp=self._now(),
            duration_seconds=time.time() - start,
        )

    # -- Cumulus MLAG ------------------------------------------------------

    def _check_mlag_cumulus(
        self, host: str, username: str, password: str, start: float, **ssh_kwargs: Any
    ) -> HealthCheckResult:
        """Parse ``nv show mlag`` / ``show mlag`` on Cumulus switches."""
        _MLAG_CMDS = [
            ("nv show mlag", False),
            ("show mlag", True),
        ]

        output = ""
        last_stderr = ""
        for cmd, use_pty in _MLAG_CMDS:
            if use_pty:
                rc, stdout, stderr = run_interactive_ssh(host, username, password, cmd, timeout=30, **ssh_kwargs)
            else:
                rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30, **ssh_kwargs)
            last_stderr = stderr or ""
            candidate = (stdout or "").strip()
            if candidate and "unknown command" not in candidate.lower():
                output = candidate
                break

        if not output:
            if last_stderr and "authentication failed" in last_stderr.lower():
                return HealthCheckResult(
                    check_name="MLAG Status",
                    category="switch_ssh",
                    status="error",
                    message=f"SSH authentication failed on {host}",
                    details={"host": host, "stderr": last_stderr},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="MLAG Status",
                category="switch_ssh",
                status="warning",
                message=f"MLAG status could not be determined on {host} (no output from show mlag)",
                details={"host": host, "stderr": last_stderr},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

        peer_alive = False
        backup_active = False
        oper_up = False
        found_any_field = False
        for line in output.splitlines():
            ll = line.lower().strip()
            if "peer-alive" in ll or "peer is alive" in ll or "peer alive" in ll:
                found_any_field = True
                peer_alive = "true" in ll or "yes" in ll
            if "peer state" in ll or "peer-state" in ll:
                found_any_field = True
                peer_alive = peer_alive or "up" in ll
            if "backup-active" in ll or "backup active" in ll:
                found_any_field = True
                backup_active = "true" in ll or "yes" in ll
            if "operational state" in ll or "oper-state" in ll:
                found_any_field = True
                oper_up = "up" in ll

        if oper_up and not backup_active:
            backup_active = True

        details: Dict[str, Any] = {
            "host": host,
            "switch_os": "cumulus",
            "stdout": output,
            "peer_alive": peer_alive,
            "backup_active": backup_active,
        }

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

        if not found_any_field:
            return HealthCheckResult(
                check_name="MLAG Status",
                category="switch_ssh",
                status="warning",
                message=f"MLAG fields not found in output on {host} — verify switch CLI access",
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

    # --- Switch SSH Check: NTP --------------------------------------------

    def _check_switch_ntp(
        self, host: str, username: str, password: str, *, switch_os: str = "cumulus", **ssh_kwargs: Any
    ) -> HealthCheckResult:
        start = time.time()
        try:
            if switch_os == "onyx":
                return self._check_ntp_onyx(host, username, password, start, **ssh_kwargs)
            return self._check_ntp_cumulus(host, username, password, start, **ssh_kwargs)
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

    # -- Onyx NTP ----------------------------------------------------------

    def _check_ntp_onyx(
        self, host: str, username: str, password: str, start: float, **ssh_kwargs: Any
    ) -> HealthCheckResult:
        """Parse ``show ntp`` output from Onyx switches.

        Key fields:
            NTP is administratively: enabled
            Active servers and peers section with server IPs
        """
        rc, stdout, stderr = run_interactive_ssh(host, username, password, "show ntp", timeout=30, **ssh_kwargs)
        output = (stdout or "").strip()

        if not output:
            return HealthCheckResult(
                check_name="Switch NTP",
                category="switch_ssh",
                status="warning",
                message=f"NTP status could not be determined on {host} (no output from show ntp)",
                details={"host": host, "switch_os": "onyx", "stderr": stderr or ""},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

        ntp_enabled = False
        servers_found = False
        in_active_section = False

        for line in output.splitlines():
            ll = line.lower().strip()
            if "ntp is administratively" in ll and "enabled" in ll:
                ntp_enabled = True
            if "active servers and peers" in ll:
                in_active_section = True
                continue
            if in_active_section and ll and not ll.startswith("---"):
                import re

                if re.match(r"\d+\.\d+\.\d+\.\d+", ll.split(":")[0].strip()):
                    servers_found = True

        details: Dict[str, Any] = {
            "host": host,
            "switch_os": "onyx",
            "stdout": output,
            "ntp_enabled": ntp_enabled,
            "servers_found": servers_found,
        }

        if ntp_enabled and servers_found:
            return HealthCheckResult(
                check_name="Switch NTP",
                category="switch_ssh",
                status="pass",
                message=f"NTP enabled with active servers on {host}",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

        if ntp_enabled and not servers_found:
            return HealthCheckResult(
                check_name="Switch NTP",
                category="switch_ssh",
                status="warning",
                message=f"NTP enabled but no active servers found on {host}",
                details=details,
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )

        return HealthCheckResult(
            check_name="Switch NTP",
            category="switch_ssh",
            status="warning",
            message=f"NTP not enabled on {host}",
            details=details,
            timestamp=self._now(),
            duration_seconds=time.time() - start,
        )

    # -- Cumulus NTP -------------------------------------------------------

    def _check_ntp_cumulus(
        self, host: str, username: str, password: str, start: float, **ssh_kwargs: Any
    ) -> HealthCheckResult:
        """Parse ``ntpq -p`` output from Cumulus switches."""
        cmd = "ntpq -p 2>/dev/null || echo 'NTP not available'"
        rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30, **ssh_kwargs)

        output = stdout.strip() if stdout else ""

        if "ntp not available" in output.lower():
            return HealthCheckResult(
                check_name="Switch NTP",
                category="switch_ssh",
                status="warning",
                message=f"NTP not available on {host}",
                details={"host": host, "switch_os": "cumulus", "stdout": output},
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
                details={"host": host, "switch_os": "cumulus", "stdout": output, "peer_count": len(peer_lines)},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        return HealthCheckResult(
            check_name="Switch NTP",
            category="switch_ssh",
            status="warning",
            message=f"No NTP peers found on {host}",
            details={"host": host, "switch_os": "cumulus", "stdout": output},
            timestamp=self._now(),
            duration_seconds=time.time() - start,
        )

    # --- Switch SSH Check: Config Readability ------------------------------

    def _check_switch_config_backup(
        self, host: str, username: str, password: str, *, switch_os: str = "cumulus", **ssh_kwargs: Any
    ) -> HealthCheckResult:
        start = time.time()
        try:
            if switch_os == "onyx":
                rc, stdout, stderr = run_interactive_ssh(
                    host, username, password, "show running-config", timeout=30, **ssh_kwargs
                )
            else:
                cmd = "nv config show 2>/dev/null | head -50 || echo 'Config not available'"
                rc, stdout, stderr = run_ssh_command(host, username, password, cmd, timeout=30, **ssh_kwargs)

            output = (stdout or "").strip()
            if output:
                return HealthCheckResult(
                    check_name="Switch Config Readability",
                    category="switch_ssh",
                    status="pass",
                    message=f"Switch config readable on {host}",
                    details={"host": host, "switch_os": switch_os, "stdout": output[:500]},
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )
            return HealthCheckResult(
                check_name="Switch Config Readability",
                category="switch_ssh",
                status="warning",
                message=f"Switch config returned empty output on {host}",
                details={"host": host, "switch_os": switch_os, "stderr": stderr or ""},
                timestamp=self._now(),
                duration_seconds=time.time() - start,
            )
        except CancelledError:
            raise
        except Exception as e:
            return HealthCheckResult(
                check_name="Switch Config Readability",
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

        api_count = 27 if 1 in tiers else 0
        ssh_count = 0
        if 3 in tiers and self.switch_ssh_config:
            switch_ips = self._resolve_switch_ips()
            ssh_count = len(switch_ips) * 3

        grand_total = api_count + ssh_count
        original_cb = self.progress_callback

        cumulative_offset = [0]

        def _scoped_cb(idx: int, total: int, name: str) -> None:
            if original_cb:
                original_cb(cumulative_offset[0] + idx, grand_total, name)

        self.progress_callback = _scoped_cb

        if 1 in tiers:
            results.extend(self.run_api_checks())
            cumulative_offset[0] = api_count

        if 3 in tiers:
            results.extend(self.run_switch_ssh_checks())

        self.progress_callback = original_cb

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
