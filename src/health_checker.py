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
from datetime import datetime
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

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    @staticmethod
    def _now() -> str:
        return datetime.utcnow().isoformat() + "Z"

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
                        return ip
        except Exception:
            pass
        return None

    def _resolve_switch_ips(self) -> List[str]:
        """Return switch IPs from switch_ssh_config or by querying the API."""
        if self.switch_ssh_config and self.switch_ssh_config.get("switch_ips"):
            return list(self.switch_ssh_config["switch_ips"])
        try:
            switches = self.api_handler._make_api_request("v1/switches/")
            if switches and isinstance(switches, list):
                ips = []
                for sw in switches:
                    ip = sw.get("mgmt_ip") or sw.get("ip")
                    if ip:
                        ips.append(ip)
                return ips
        except Exception:
            pass
        return []

    @staticmethod
    def to_dict(report: HealthCheckReport) -> Dict[str, Any]:
        return asdict(report)

    def save_json(self, report: HealthCheckReport, output_dir: str = "output") -> str:
        health_dir = os.path.join(output_dir, "health")
        os.makedirs(health_dir, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"health_check_{report.cluster_name}_{timestamp}.json"
        filepath = os.path.join(health_dir, filename)
        with open(filepath, "w") as f:
            json.dump(self.to_dict(report), f, indent=2, default=str)
        self.logger.info(f"Health check report saved to {filepath}")
        return filepath

    # ------------------------------------------------------------------
    # Normalise helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _first_item(data: Any) -> Optional[Dict[str, Any]]:
        """Return the first element when *data* is a non-empty list, else *data* itself."""
        if isinstance(data, list):
            return data[0] if data else None
        return data

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
        ]
        results: List[HealthCheckResult] = []
        for i, fn in enumerate(checks, 1):
            self._check_cancel()
            self.logger.info(f"Running API check {i}/{len(checks)}: {fn.__name__}")
            result = fn()
            results.append(result)
            if result.status in ("fail", "error"):
                self.logger.warning(f"Check {fn.__name__} => {result.status}: {result.message}")
        return results

    # --- 1. Cluster RAID Health -------------------------------------------

    def _check_cluster_raid_health(self) -> HealthCheckResult:
        start = time.time()
        try:
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            active = {k: v for k, v in fields.items() if v is not None and v != 0 and v != ""}

            if active:
                return HealthCheckResult(
                    check_name="RAID Rebuild Progress",
                    category="api",
                    status="warning",
                    message=f"RAID rebuild in progress: {active}",
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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

            if str(leader_state).upper() in ("STEADY", "STABLE"):
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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

            if not upgrade_state or str(upgrade_state).upper() in ("", "NONE", "NULL"):
                return HealthCheckResult(
                    check_name="Upgrade State",
                    category="api",
                    status="pass",
                    message="No upgrade in progress",
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
                if str(node.get("status", "")).upper() != "ACTIVE":
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
                if str(node.get("status", "")).upper() != "ACTIVE":
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

            critical_alarms = [
                a for a in data if str(a.get("severity", "")).upper() in ("CRITICAL", "MAJOR") and not a.get("resolved")
            ]
            details = {"total_alarms": len(data), "critical_unresolved": len(critical_alarms)}

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
            data = self.api_handler._make_api_request("events/")
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
            details = {"total_events": len(data), "critical_events": len(critical_events)}

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
                message="No recent critical events",
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
            data = self._first_item(self.api_handler._make_api_request("vms/1/network_settings/"))
            if not data:
                return HealthCheckResult(
                    check_name="Network Settings",
                    category="api",
                    status="error",
                    message="Failed to retrieve network settings",
                    timestamp=self._now(),
                    duration_seconds=time.time() - start,
                )

            dns = data.get("dns_servers") or data.get("dns")
            ntp = data.get("ntp_servers") or data.get("ntp")
            gateway = data.get("gateway") or data.get("default_gateway")
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            cluster = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
            for ip in mgmt_ips:
                rc, _out, _err = run_ssh_command(host, username, password, f"ping -c 1 -W 2 {ip}", timeout=30)
                if rc == 0:
                    reachable.append(ip)
                else:
                    unreachable.append(ip)

            details = {"host": host, "reachable": reachable, "unreachable": unreachable}

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

        cluster_data = self._first_item(self.api_handler._make_api_request("clusters/"))
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
