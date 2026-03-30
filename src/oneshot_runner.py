"""
One-Shot Runner for Advanced Operations

Orchestrates sequential execution of multiple Advanced Operations workflows
in a single pass: pre-validation, health checks, selected workflows, optional
As-Built report generation, and automatic result bundling.

Module boundary: may import health_checker, advanced_ops, result_bundler,
workflow registry, and the report pipeline (api_handler -> data_extractor ->
report_builder).  See architecture-03.mdc for full boundary rules.
"""

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import requests as _requests_lib

from utils.logger import get_logger

logger = get_logger(__name__)

DOWNLOAD_DEPENDENT_OPS = frozenset({"vnetmap", "support_tool", "vperfsanity"})
SSH_NODE_OPS = frozenset({"vnetmap", "support_tool", "vperfsanity", "log_bundle", "network_config"})
SSH_SWITCH_OPS = frozenset({"switch_config"})
TOOL_FRESHNESS_WARN_DAYS = 10

# Config override for validation API calls: disable SSL verify, short timeout, single retry
_VALIDATION_API_CONFIG: Dict[str, Any] = {
    "api": {"verify_ssl": False, "timeout": 10, "max_retries": 1, "retry_delay": 1}
}


class _OneShotLogHandler(logging.Handler):
    """Routes Python logger output to the One-Shot output pane."""

    def __init__(self, callback):
        super().__init__(logging.DEBUG)
        self._callback = callback

    def emit(self, record):
        try:
            tier = "debug" if record.levelno <= logging.DEBUG else "live"
            level_map = {
                logging.DEBUG: "info",
                logging.INFO: "info",
                logging.WARNING: "warn",
                logging.ERROR: "error",
                logging.CRITICAL: "error",
            }
            ui_level = level_map.get(record.levelno, "info")
            msg = f"[{record.name}] {record.getMessage()}"
            if self._callback:
                self._callback(ui_level, msg, None, tier)
        except Exception:
            pass


@dataclass
class ValidationCheck:
    """Result of a single pre-validation check."""

    name: str
    status: str  # "pass" | "warn" | "fail" | "info"
    message: str
    category: str = ""  # "credentials" | "connectivity" | "internet" | "tools" | "notice"


@dataclass
class OneShotState:
    """Tracks overall one-shot execution progress."""

    phase: str = (
        "idle"  # idle | validating | health_checks | operations | report | bundling | completed | error | cancelled
    )
    current_operation: str = ""
    operation_index: int = 0
    total_operations: int = 0
    status: str = "idle"  # idle | running | completed | error | cancelled
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    bundle_path: Optional[str] = None
    validation_results: List[Dict[str, str]] = field(default_factory=list)


class OneShotRunner:
    """Orchestrates one-shot execution of multiple Advanced Operations workflows."""

    def __init__(
        self,
        selected_ops: List[str],
        credentials: Dict[str, Any],
        include_report: bool = False,
        include_health: bool = True,
        cancel_event: Optional[threading.Event] = None,
        output_callback: Optional[Callable[..., None]] = None,
        config_path: Optional[str] = None,
        use_default_creds: bool = False,
    ):
        self._selected_ops = selected_ops
        self._credentials = credentials
        self._include_report = include_report
        self._include_health = include_health
        self._cancel_event = cancel_event or threading.Event()
        self._output_callback = output_callback
        self._config_path = config_path
        self._use_default_creds = use_default_creds
        self._state = OneShotState()
        self._lock = threading.Lock()
        self._tunnel = None
        self._tunnel_address: Optional[str] = None

    _SUPPORT_CREDS = {"username": "support", "password": "654321"}
    _ADMIN_CREDS = {"username": "admin", "password": "123456"}

    def _get_api_creds(self, phase: str) -> Dict[str, str]:
        """Return API credentials appropriate for the given phase.

        When default credentials are active the support account is used
        everywhere except vperfsanity, which requires admin.
        """
        if self._use_default_creds:
            if phase == "vperfsanity":
                return dict(self._ADMIN_CREDS)
            return dict(self._SUPPORT_CREDS)
        return {
            "username": self._credentials.get("username", ""),
            "password": self._credentials.get("password", ""),
        }

    def _get_workflow_credentials(self, op_id: str) -> Dict[str, Any]:
        """Build the credential dict handed to a workflow's set_credentials().

        For vperfsanity with default creds, the API username/password are
        overridden to admin while the SSH credentials remain unchanged.
        """
        creds = dict(self._credentials)
        if self._use_default_creds and op_id == "vperfsanity":
            creds["username"] = self._ADMIN_CREDS["username"]
            creds["password"] = self._ADMIN_CREDS["password"]
        if self._tunnel_address:
            creds["tunnel_address"] = self._tunnel_address
        if self._tunnel:
            if self._tunnel.vms_internal_ip:
                creds["vms_internal_ip"] = self._tunnel.vms_internal_ip
            if self._tunnel.vms_management_ip:
                creds["vms_management_ip"] = self._tunnel.vms_management_ip
        return creds

    # ------------------------------------------------------------------
    # Output helper
    # ------------------------------------------------------------------

    def _emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        if self._output_callback:
            try:
                self._output_callback(level, message, details, "status")
            except Exception:
                pass
        logger.info("[%s] %s", level, message)

    def _emit_live(self, level: str, message: str, details: Optional[str] = None) -> None:
        if self._output_callback:
            try:
                self._output_callback(level, message, details, "live")
            except Exception:
                pass

    def _emit_debug(self, level: str, message: str, details: Optional[str] = None) -> None:
        if self._output_callback:
            try:
                self._output_callback(level, message, details, "debug")
            except Exception:
                pass

    def _check_cancel(self) -> None:
        if self._cancel_event.is_set():
            with self._lock:
                self._state.status = "cancelled"
                self._state.phase = "cancelled"
                self._state.completed_at = datetime.now().isoformat()
            self._emit("warn", "One-shot execution cancelled by user")
            raise _OneShotCancelled("Cancelled by user")

    # ------------------------------------------------------------------
    # State access
    # ------------------------------------------------------------------

    def get_state(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "phase": self._state.phase,
                "current_operation": self._state.current_operation,
                "operation_index": self._state.operation_index,
                "total_operations": self._state.total_operations,
                "status": self._state.status,
                "started_at": self._state.started_at,
                "completed_at": self._state.completed_at,
                "error": self._state.error,
                "bundle_path": self._state.bundle_path,
                "validation_results": list(self._state.validation_results),
            }

    def is_running(self) -> bool:
        with self._lock:
            return self._state.status == "running" or self._state.phase == "validating"

    # ------------------------------------------------------------------
    # Pre-validation
    # ------------------------------------------------------------------

    def run_prevalidation(self) -> List[Dict[str, str]]:
        """Run pre-validation checks and return structured results.

        Returns:
            List of dicts with keys: name, status (pass/warn/fail/info), message, category.
        """
        checks: List[ValidationCheck] = []

        with self._lock:
            self._state.phase = "validating"
            self._state.status = "running"

        self._emit("info", "=" * 65)
        self._emit("info", "ONE-SHOT PRE-VALIDATION")
        self._emit("info", "=" * 65)

        try:
            if self._credentials.get("tech_port"):
                self._setup_tunnel()

            self._check_cancel()
            checks.append(self._validate_credentials())
            self._check_cancel()
            checks.append(self._validate_cluster_api())

            health_needs_ssh = self._include_health and self._include_report
            needs_node_ssh = bool(set(self._selected_ops) & SSH_NODE_OPS) or health_needs_ssh
            needs_switch_ssh = bool(set(self._selected_ops) & SSH_SWITCH_OPS) or health_needs_ssh
            needs_internet = bool(set(self._selected_ops) & DOWNLOAD_DEPENDENT_OPS)

            if needs_node_ssh:
                self._check_cancel()
                checks.append(self._validate_node_ssh())
            if needs_switch_ssh:
                self._check_cancel()
                checks.append(self._validate_switch_ssh())
            if needs_internet:
                self._check_cancel()
                checks.append(self._validate_internet_access())

            self._check_cancel()
            checks.append(self._validate_tool_freshness())

            if "vperfsanity" in self._selected_ops:
                checks.append(
                    ValidationCheck(
                        name="vperfsanity Duration",
                        status="info",
                        message="vperfsanity performance test may take up to 30 minutes to complete.",
                        category="notice",
                    )
                )
        except _OneShotCancelled:
            checks.append(ValidationCheck("Cancelled", "fail", "Pre-validation cancelled by user.", ""))
        finally:
            self._teardown_tunnel()

        results = [{"name": c.name, "status": c.status, "message": c.message, "category": c.category} for c in checks]

        with self._lock:
            self._state.validation_results = results
            if self._state.status != "cancelled":
                self._state.status = "idle"
                self._state.phase = "idle"

        for c in checks:
            icon = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]", "info": "[INFO]"}.get(c.status, "[????]")
            level = {"pass": "success", "warn": "warn", "fail": "error", "info": "info"}.get(c.status, "info")
            self._emit(level, f"{icon} {c.name}: {c.message}")

        self._emit("info", "-" * 65)
        return results

    def _validate_credentials(self) -> ValidationCheck:
        cluster_ip = self._credentials.get("cluster_ip", "").strip()
        username = self._credentials.get("username", "").strip()
        password = self._credentials.get("password", "")

        if not cluster_ip:
            return ValidationCheck("Credentials", "fail", "Cluster IP is required.", "credentials")
        if not username or not password:
            api_token = self._credentials.get("api_token", "").strip()
            if not api_token:
                return ValidationCheck(
                    "Credentials", "fail", "API username/password or API token required.", "credentials"
                )

        needs_node = bool(set(self._selected_ops) & SSH_NODE_OPS)
        needs_switch = bool(set(self._selected_ops) & SSH_SWITCH_OPS)
        if needs_node and not self._credentials.get("node_password"):
            return ValidationCheck(
                "Credentials", "fail", "Node SSH password required for selected operations.", "credentials"
            )
        if needs_switch and not self._credentials.get("switch_password"):
            return ValidationCheck(
                "Credentials", "fail", "Switch SSH password required for selected operations.", "credentials"
            )

        return ValidationCheck("Credentials", "pass", "All required credentials provided.", "credentials")

    def _validate_cluster_api(self) -> ValidationCheck:
        cluster_ip = self._credentials.get("cluster_ip", "").strip()
        if not cluster_ip:
            return ValidationCheck("Cluster API", "fail", "No cluster IP to test.", "connectivity")

        if self._credentials.get("tech_port"):
            return self._validate_tech_port_discovery(cluster_ip)

        try:
            url = f"https://{cluster_ip}/api/clusters/"
            resp = _requests_lib.get(url, timeout=10, verify=False)  # noqa: S501
            if resp.status_code in (200, 401, 403):
                return ValidationCheck(
                    "Cluster API", "pass", f"Cluster API reachable (HTTP {resp.status_code}).", "connectivity"
                )
            return ValidationCheck(
                "Cluster API", "warn", f"Cluster responded with HTTP {resp.status_code}.", "connectivity"
            )
        except Exception as exc:
            return ValidationCheck("Cluster API", "fail", f"Cannot reach cluster API: {exc}", "connectivity")

    def _validate_tech_port_discovery(self, cluster_ip: str) -> "ValidationCheck":
        """In Tech Port mode, verify VMS discovery instead of direct API access."""
        if self._tunnel and self._tunnel_address:
            return ValidationCheck(
                "Cluster API", "pass",
                f"Tech Port: VMS discovered (internal={self._tunnel.vms_internal_ip}, "
                f"management={self._tunnel.vms_management_ip}), tunnel={self._tunnel_address}.",
                "connectivity",
            )
        node_user = self._credentials.get("node_user", "vastdata")
        node_password = self._credentials.get("node_password", "")
        if not node_password:
            return ValidationCheck(
                "Cluster API", "fail",
                "Tech Port mode requires Node SSH password for VMS discovery.",
                "connectivity",
            )
        try:
            from utils.vms_tunnel import discover_vms_management_ip

            vms_internal, vms_mgmt = discover_vms_management_ip(
                cluster_ip, node_user, node_password, timeout=15,
            )
            return ValidationCheck(
                "Cluster API", "pass",
                f"Tech Port: VMS discovered (internal={vms_internal}, management={vms_mgmt}).",
                "connectivity",
            )
        except Exception as exc:
            return ValidationCheck(
                "Cluster API", "fail",
                f"Tech Port: VMS discovery failed: {exc}",
                "connectivity",
            )

    def _validate_node_ssh(self) -> ValidationCheck:
        cluster_ip = self._credentials.get("cluster_ip", "").strip()
        node_user = self._credentials.get("node_user", "vastdata")
        node_password = self._credentials.get("node_password", "")

        if not node_password:
            return ValidationCheck("Node SSH", "fail", "Node SSH password not provided.", "connectivity")

        try:
            from utils.ssh_adapter import run_ssh_command

            rc, stdout, _stderr = run_ssh_command(cluster_ip, node_user, node_password, "hostname", timeout=15)
            if rc == 0:
                hostname = stdout.strip() if stdout else "unknown"
                return ValidationCheck("Node SSH", "pass", f"Node SSH connected ({hostname}).", "connectivity")
            return ValidationCheck(
                "Node SSH",
                "warn",
                f"SSH connected but command failed (rc={rc}). Health check SSH tiers may be limited.",
                "connectivity",
            )
        except Exception as exc:
            return ValidationCheck(
                "Node SSH",
                "warn",
                f"Cannot SSH to node ({exc}). Health check Tiers 2-3 and SSH-dependent operations may fail. Fix credentials/network or proceed with limitations.",
                "connectivity",
            )

    def _validate_switch_ssh(self) -> ValidationCheck:
        cluster_ip = self._credentials.get("cluster_ip", "").strip()
        switch_user = self._credentials.get("switch_user", "cumulus")
        switch_password = self._credentials.get("switch_password", "")

        if not switch_password:
            return ValidationCheck("Switch SSH", "fail", "Switch SSH password not provided.", "connectivity")

        try:
            from api_handler import create_vast_api_handler

            api = create_vast_api_handler(
                cluster_ip=cluster_ip,
                username=self._credentials.get("username"),
                password=self._credentials.get("password"),
                token=self._credentials.get("api_token"),
                config=_VALIDATION_API_CONFIG,
                tunnel_address=self._tunnel_address,
            )
            api.authenticate()
            switches = api._make_api_request("switches/") or []
            api.close()

            if not switches:
                return ValidationCheck(
                    "Switch SSH", "warn", "No switches found via API; switch operations may be skipped.", "connectivity"
                )

            first_ip = switches[0].get("mgmt_ip", "")
            if not first_ip:
                return ValidationCheck(
                    "Switch SSH", "warn", "Switch found but no mgmt_ip; cannot test SSH.", "connectivity"
                )

            from utils.ssh_adapter import run_ssh_command

            rc, stdout, _ = run_ssh_command(first_ip, switch_user, switch_password, "hostname", timeout=15)
            if rc == 0:
                return ValidationCheck(
                    "Switch SSH",
                    "pass",
                    f"Switch SSH connected ({stdout.strip() if stdout else first_ip}).",
                    "connectivity",
                )
            return ValidationCheck(
                "Switch SSH",
                "warn",
                f"Switch SSH connected but command failed (rc={rc}). Switch operations may encounter issues.",
                "connectivity",
            )
        except Exception as exc:
            return ValidationCheck(
                "Switch SSH",
                "warn",
                f"Cannot verify switch SSH ({exc}). Switch configuration extraction and Tier-3 health checks may fail.",
                "connectivity",
            )

    def _validate_internet_access(self) -> ValidationCheck:
        """Check if the cluster has outbound internet access (required for tool downloads)."""
        cluster_ip = self._credentials.get("cluster_ip", "").strip()
        node_user = self._credentials.get("node_user", "vastdata")
        node_password = self._credentials.get("node_password", "")

        if not node_password:
            return ValidationCheck(
                "Internet Access",
                "warn",
                "Cannot verify internet access without node SSH credentials. Tool downloads may fail.",
                "internet",
            )

        try:
            from utils.ssh_adapter import run_ssh_command

            rc, stdout, _ = run_ssh_command(
                cluster_ip,
                node_user,
                node_password,
                "curl -sI --max-time 10 https://github.com 2>&1 | head -1",
                timeout=20,
            )
            if rc == 0 and stdout and ("200" in stdout or "301" in stdout or "HTTP" in stdout):
                return ValidationCheck("Internet Access", "pass", "Cluster has outbound internet access.", "internet")
            return ValidationCheck(
                "Internet Access",
                "warn",
                "Cluster may not have outbound internet access. Selected operations (vnetmap, support tools, vperfsanity) download files directly to the cluster and may fail.",
                "internet",
            )
        except Exception as exc:
            return ValidationCheck(
                "Internet Access",
                "warn",
                f"Cannot verify internet access ({exc}). Tool downloads to cluster may fail.",
                "internet",
            )

    def _validate_tool_freshness(self) -> ValidationCheck:
        try:
            from tool_manager import ToolManager

            tm = ToolManager()
            tools = tm.get_all_tools_info()
            stale: List[str] = []
            for t in tools:
                if not t:
                    continue
                cached_date = t.get("cached_date")
                if not cached_date:
                    continue
                age_days = (datetime.now() - datetime.fromisoformat(cached_date)).days
                if age_days > TOOL_FRESHNESS_WARN_DAYS:
                    stale.append(f"{t['name']} ({age_days}d)")

            if stale:
                return ValidationCheck(
                    "Tool Freshness",
                    "warn",
                    f"Tools older than {TOOL_FRESHNESS_WARN_DAYS} days: {', '.join(stale)}. Consider updating before running.",
                    "tools",
                )
            return ValidationCheck("Tool Freshness", "pass", "All cached tools are up to date.", "tools")
        except Exception as exc:
            return ValidationCheck("Tool Freshness", "warn", f"Cannot check tool freshness: {exc}", "tools")

    # ------------------------------------------------------------------
    # Main execution
    # ------------------------------------------------------------------

    def run_all(self) -> Dict[str, Any]:
        """Execute the full one-shot sequence.

        Order: Selected Operations -> Optional Report (with optional Health Checks) -> Bundle.

        Returns:
            Dict with status, bundle_path, and any errors.
        """
        with self._lock:
            self._state.status = "running"
            self._state.started_at = datetime.now().isoformat()
            total = len(self._selected_ops)
            if self._include_report:
                total += 1
            total += 1  # bundling
            self._state.total_operations = total

        health_label = " (w/ Health Checks)" if self._include_health else ""
        report_label = f" + As-Built Report{health_label}" if self._include_report else ""
        self._emit("info", "=" * 65)
        self._emit("info", "ONE-SHOT EXECUTION STARTED")
        self._emit(
            "info",
            f"Operations: {len(self._selected_ops)} workflows{report_label}",
        )
        self._emit("info", "=" * 65)

        log_handler = _OneShotLogHandler(self._output_callback)
        logging.getLogger().addHandler(log_handler)

        try:
            if self._credentials.get("tech_port"):
                self._setup_tunnel()

            # Phase 1: Selected Operations
            self._run_operations()

            # Phase 2: Optional Report (health checks run inside when selected)
            if self._include_report:
                self._run_report()

            # Phase 3: Bundle
            self._run_bundling()

            with self._lock:
                self._state.status = "completed"
                self._state.phase = "completed"
                self._state.completed_at = datetime.now().isoformat()

            # Save operation log to disk
            try:
                from utils.ops_log_manager import OpsLogManager
                from advanced_ops import get_advanced_ops_manager

                mgr = get_advanced_ops_manager()
                log_manager = OpsLogManager()
                log_manager.ensure_capacity(emit_fn=self._emit)
                session_id = (
                    self._state.started_at.replace(":", "").replace("-", "").replace("T", "_")[:15]
                    if self._state.started_at
                    else "unknown"
                )
                cluster_ip = self._credentials.get("cluster_ip", "unknown")
                log_manager.save_session_log(mgr._output_buffer[:], session_id, cluster_ip)
                self._emit("info", "Operation log saved to disk.")
            except Exception as log_exc:
                self._emit("warn", f"Failed to save operation log: {log_exc}")

            self._emit("success", "=" * 65)
            self._emit("success", "ONE-SHOT EXECUTION COMPLETED SUCCESSFULLY")
            self._emit("success", "=" * 65)

            return {"status": "completed", "bundle_path": self._state.bundle_path}

        except _OneShotCancelled:
            # Save operation log to disk on cancellation
            try:
                from utils.ops_log_manager import OpsLogManager
                from advanced_ops import get_advanced_ops_manager

                mgr = get_advanced_ops_manager()
                log_manager = OpsLogManager()
                log_manager.ensure_capacity(emit_fn=self._emit)
                session_id = (
                    self._state.started_at.replace(":", "").replace("-", "").replace("T", "_")[:15]
                    if self._state.started_at
                    else "unknown"
                )
                cluster_ip = self._credentials.get("cluster_ip", "unknown")
                log_manager.save_session_log(mgr._output_buffer[:], session_id, cluster_ip)
                self._emit("info", "Operation log saved to disk.")
            except Exception as log_exc:
                self._emit("warn", f"Failed to save operation log: {log_exc}")
            return {"status": "cancelled"}
        except Exception as exc:
            logger.exception("One-shot execution failed")
            with self._lock:
                self._state.status = "error"
                self._state.phase = "error"
                self._state.error = str(exc)
                self._state.completed_at = datetime.now().isoformat()
            self._emit("error", f"One-shot execution failed: {exc}")
            # Save operation log to disk on error
            try:
                from utils.ops_log_manager import OpsLogManager
                from advanced_ops import get_advanced_ops_manager

                mgr = get_advanced_ops_manager()
                log_manager = OpsLogManager()
                log_manager.ensure_capacity(emit_fn=self._emit)
                session_id = (
                    self._state.started_at.replace(":", "").replace("-", "").replace("T", "_")[:15]
                    if self._state.started_at
                    else "unknown"
                )
                cluster_ip = self._credentials.get("cluster_ip", "unknown")
                log_manager.save_session_log(mgr._output_buffer[:], session_id, cluster_ip)
                self._emit("info", "Operation log saved to disk.")
            except Exception as log_exc:
                self._emit("warn", f"Failed to save operation log: {log_exc}")
            return {"status": "error", "error": str(exc)}
        finally:
            self._teardown_tunnel()
            logging.getLogger().removeHandler(log_handler)

    def _setup_tunnel(self) -> None:
        """Establish the VMS tunnel for Tech Port mode."""
        from utils.vms_tunnel import VMSTunnel

        cluster_ip = self._credentials["cluster_ip"]
        node_user = self._credentials.get("node_user", "vastdata")
        node_password = self._credentials.get("node_password", "vastdata")
        self._emit("info", f"Tech Port mode: discovering VMS via {cluster_ip}...")
        self._tunnel = VMSTunnel(cluster_ip, node_user, node_password)
        self._tunnel.connect()
        self._tunnel_address = self._tunnel.local_bind_address
        self._emit(
            "info",
            f"VMS discovered: internal={self._tunnel.vms_internal_ip}, "
            f"management={self._tunnel.vms_management_ip}, tunnel={self._tunnel_address}",
        )

    def _teardown_tunnel(self) -> None:
        if self._tunnel is not None:
            try:
                self._tunnel.close()
            except Exception:
                pass
            self._tunnel = None
            self._tunnel_address = None

    # ------------------------------------------------------------------
    # Phase: Health Checks
    # ------------------------------------------------------------------

    def _run_health_checks(self) -> None:
        self._check_cancel()

        with self._lock:
            self._state.phase = "health_checks"
            self._state.current_operation = "Health Checks (Tiers 1-3)"
            self._state.operation_index = 1

        self._emit("info", "")
        self._emit("info", "=" * 65)
        self._emit("info", "PHASE: HEALTH CHECKS (Tiers 1-3)")
        self._emit("info", "=" * 65)

        try:
            from api_handler import create_vast_api_handler
            from health_checker import HealthChecker

            config = self._load_config()
            config.setdefault("api", {})["verify_ssl"] = False

            api_creds = self._get_api_creds("health_checks")
            api = create_vast_api_handler(
                cluster_ip=self._credentials["cluster_ip"],
                username=api_creds["username"],
                password=api_creds["password"],
                token=self._credentials.get("api_token"),
                config=config,
                tunnel_address=self._tunnel_address,
            )
            api.authenticate()

            ssh_config = None
            switch_ssh_config = None
            tiers = [1]

            node_pw = self._credentials.get("node_password", "")
            switch_pw = self._credentials.get("switch_password", "")

            if node_pw:
                ssh_config = {
                    "username": self._credentials.get("node_user", "vastdata"),
                    "password": node_pw,
                }
                tiers.append(2)
            if switch_pw:
                switch_ssh_config = {
                    "username": self._credentials.get("switch_user", "cumulus"),
                    "password": switch_pw,
                }
                if self._tunnel_address:
                    switch_ssh_config["proxy_jump"] = {
                        "host": self._credentials.get("cluster_ip"),
                        "username": self._credentials.get("node_user", "vastdata"),
                        "password": self._credentials.get("node_password"),
                    }
                tiers.append(3)

            checker = HealthChecker(
                api_handler=api,
                ssh_config=ssh_config,
                switch_ssh_config=switch_ssh_config,
                cancel_event=self._cancel_event,
            )

            tier_desc = f"Tier {', '.join(str(t) for t in tiers)}"
            self._emit("info", f"Running health checks ({tier_desc})...")

            report = checker.run_all_checks(tiers=tiers)

            # Emit per-check progress
            total_checks = len(report.results)
            for idx, result in enumerate(report.results, start=1):
                icon = {"pass": "[PASS]", "warning": "[WARN]", "fail": "[FAIL]", "error": "[ERR]"}.get(
                    result.status, "[????]"
                )
                level = {"pass": "success", "warning": "warn", "fail": "error", "error": "error"}.get(
                    result.status, "info"
                )
                self._emit(level, f"  {icon} {result.check_name} ({idx}/{total_checks})")
                if result.status in ("fail", "error", "warning") and result.message:
                    self._emit(level, f"        {result.message}")

            summary = report.summary

            self._emit(
                "info",
                f"Health checks complete: {summary.get('pass', 0)} pass, {summary.get('fail', 0)} fail, {summary.get('warning', 0)} warning",
            )

            # Save results
            from utils import get_data_dir

            output_dir = str(get_data_dir() / "output")
            checker.save_json(report, output_dir=output_dir)
            checker.generate_remediation_report(report, output_dir=output_dir)

            self._emit("success", "Health check results saved.")

            api.close()
        except _OneShotCancelled:
            raise
        except Exception as exc:
            self._emit("error", f"Health checks failed (non-blocking): {exc}")
            logger.warning("Health checks failed: %s", exc)

    # ------------------------------------------------------------------
    # Phase: Operations
    # ------------------------------------------------------------------

    def _run_operations(self) -> None:
        self._check_cancel()

        with self._lock:
            self._state.phase = "operations"

        self._emit("info", "")
        self._emit("info", "=" * 65)
        self._emit("info", f"PHASE: OPERATIONS ({len(self._selected_ops)} selected)")
        self._emit("info", "=" * 65)

        from workflows import WorkflowRegistry

        for idx, op_id in enumerate(self._selected_ops, start=1):
            self._check_cancel()

            with self._lock:
                self._state.operation_index = idx
                self._state.current_operation = op_id

            wf_instance = WorkflowRegistry.get(op_id)
            if not wf_instance:
                self._emit("warn", f"Workflow '{op_id}' not found in registry, skipping.")
                continue

            self._emit("info", "")
            self._emit(
                "info", f"--- Operation {idx}/{len(self._selected_ops)}: {getattr(wf_instance, 'name', op_id)} ---"
            )

            if hasattr(wf_instance, "set_output_callback"):
                wf_instance.set_output_callback(self._output_callback or (lambda *a: None))
            if hasattr(wf_instance, "set_credentials"):
                wf_instance.set_credentials(self._get_workflow_credentials(op_id))

            steps = wf_instance.get_steps()
            for step in steps:
                self._check_cancel()
                step_id = step.get("id", 0)
                step_name = step.get("name", f"Step {step_id}")
                self._emit("info", f"  Step {step_id}: {step_name}")

                start = time.time()
                try:
                    result = wf_instance.run_step(step_id)
                    elapsed = int((time.time() - start) * 1000)
                    success = result.get("success", False)
                    msg = result.get("message", "")
                    if success:
                        self._emit("success", f"  [DONE] {msg} ({elapsed}ms)")
                    else:
                        self._emit("error", f"  [ERROR] {msg} ({elapsed}ms)")
                        self._emit("warn", f"  Workflow '{op_id}' step {step_id} failed; continuing to next operation.")
                        break
                except Exception as step_exc:
                    elapsed = int((time.time() - start) * 1000)
                    self._emit("error", f"  [EXCEPTION] {step_exc} ({elapsed}ms)")
                    self._emit("warn", f"  Workflow '{op_id}' aborted; continuing to next operation.")
                    break

            self._emit("info", f"--- {getattr(wf_instance, 'name', op_id)} complete ---")

    # ------------------------------------------------------------------
    # Phase: Report
    # ------------------------------------------------------------------

    def _run_report(self) -> None:
        self._check_cancel()

        with self._lock:
            base_idx = len(self._selected_ops) + 1
            self._state.phase = "report"
            self._state.operation_index = base_idx
            self._state.current_operation = "As-Built Report"

        self._emit("info", "")
        self._emit("info", "=" * 65)
        self._emit("info", "PHASE: AS-BUILT REPORT GENERATION")
        self._emit("info", "=" * 65)

        try:
            from api_handler import create_vast_api_handler
            from data_extractor import create_data_extractor
            from report_builder import ReportConfig, create_report_builder
            from utils import get_data_dir

            config = self._load_config()
            config.setdefault("api", {})["verify_ssl"] = False

            api_creds = self._get_api_creds("report")
            api = create_vast_api_handler(
                cluster_ip=self._credentials["cluster_ip"],
                username=api_creds["username"],
                password=api_creds["password"],
                token=self._credentials.get("api_token"),
                config=config,
                tunnel_address=self._tunnel_address,
            )
            self._emit("info", "Authenticating with cluster API...")
            api.authenticate()
            self._emit("info", "Collecting cluster data...")
            raw_data = api.get_all_data()
            self._emit("info", f"Data collected: {len(raw_data)} sections")
            if not raw_data:
                self._emit("error", "Data collection returned empty results, skipping report.")
                api.close()
                return

            # Include health check in report data (only when selected)
            use_ext_port_mapping = False
            node_pw = self._credentials.get("node_password", "")
            switch_pw = self._credentials.get("switch_password", "")

            if self._include_health:
                self._check_cancel()
                try:
                    from health_checker import HealthChecker

                    tiers = [1]
                    ssh_cfg = None
                    sw_cfg = None
                    if node_pw:
                        ssh_cfg = {
                            "username": self._credentials.get("node_user", "vastdata"),
                            "password": node_pw,
                        }
                        tiers.append(2)
                    if switch_pw:
                        sw_cfg = {
                            "username": self._credentials.get("switch_user", "cumulus"),
                            "password": switch_pw,
                        }
                        if self._tunnel_address:
                            sw_cfg["proxy_jump"] = {
                                "host": self._credentials.get("cluster_ip"),
                                "username": self._credentials.get("node_user", "vastdata"),
                                "password": self._credentials.get("node_password"),
                            }
                        tiers.append(3)

                    tier_desc = f"Tier {', '.join(str(t) for t in tiers)}"
                    self._emit("info", f"Running health checks ({tier_desc})...")

                    checker = HealthChecker(
                        api_handler=api, ssh_config=ssh_cfg, switch_ssh_config=sw_cfg, cancel_event=self._cancel_event
                    )
                    hc_report = checker.run_all_checks(tiers=tiers)

                    total_checks = len(hc_report.results)
                    for idx, result in enumerate(hc_report.results, start=1):
                        icon = {"pass": "[PASS]", "warning": "[WARN]", "fail": "[FAIL]", "error": "[ERR]"}.get(
                            result.status, "[????]"
                        )
                        level = {"pass": "success", "warning": "warn", "fail": "error", "error": "error"}.get(
                            result.status, "info"
                        )
                        self._emit(level, f"  {icon} {result.check_name} ({idx}/{total_checks})")
                        if result.status in ("fail", "error", "warning") and result.message:
                            self._emit(level, f"        {result.message}")

                    raw_data["health_check_results"] = checker.to_dict(hc_report)

                    try:
                        from utils import get_data_dir

                        checker.save_json(hc_report, output_dir=str(get_data_dir() / "output"))
                    except Exception as save_exc:
                        self._emit("warn", f"Could not save standalone health JSON: {save_exc}")

                    summary = hc_report.summary
                    self._emit(
                        "info",
                        f"Health checks complete: {summary.get('pass', 0)} pass, "
                        f"{summary.get('fail', 0)} fail, {summary.get('warning', 0)} warning",
                    )
                    self._emit("info", "Health check data included in report.")
                except Exception as hc_exc:
                    self._emit("warn", f"Health check for report failed (non-blocking): {hc_exc}")
            else:
                self._emit("info", "Health checks not selected — skipping.")

            # Port mapping collection (when both node and switch credentials are present)
            self._check_cancel()
            if node_pw and switch_pw:
                self._emit("info", "Collecting port mapping data via SSH...")
                try:
                    from external_port_mapper import ExternalPortMapper

                    switch_inventory = raw_data.get("switch_inventory", {})
                    switches = switch_inventory.get("switches", [])
                    switch_ips = [sw.get("mgmt_ip") for sw in switches if sw.get("mgmt_ip")]

                    if self._tunnel_address:
                        entry_ip = self._credentials.get("cluster_ip")
                        cnode_ips = [entry_ip] if entry_ip else []
                        self._emit("info", f"Tech Port mode: using entry CNode {entry_ip} for port mapping")
                    else:
                        cnodes_network = raw_data.get("cnodes_network", [])
                        cnode_ips = []
                        for cn in cnodes_network:
                            ip = cn.get("mgmt_ip") or cn.get("ipmi_ip")
                            if ip and ip != "Unknown" and ip not in cnode_ips:
                                cnode_ips.append(ip)
                        if not cnode_ips:
                            hardware = raw_data.get("hardware", {})
                            for cn in hardware.get("cnodes", []):
                                ip = cn.get("mgmt_ip") or cn.get("ipmi_ip")
                                if ip and ip != "Unknown" and ip not in cnode_ips:
                                    cnode_ips.append(ip)

                    if switch_ips and cnode_ips:
                        for cnode_ip in cnode_ips:
                            try:
                                mapper = ExternalPortMapper(
                                    cluster_ip=self._credentials["cluster_ip"],
                                    api_user=api_creds["username"],
                                    api_password=api_creds["password"],
                                    cnode_ip=cnode_ip,
                                    node_user=self._credentials.get("node_user", "vastdata"),
                                    node_password=node_pw,
                                    switch_ips=switch_ips,
                                    switch_user=self._credentials.get("switch_user", "cumulus"),
                                    switch_password=switch_pw,
                                    proxy_jump=bool(self._credentials.get("proxy_jump", True)),
                                    tunnel_address=self._tunnel_address,
                                )
                                result = mapper.collect_port_mapping()
                                if result.get("available"):
                                    raw_data["port_mapping_external"] = result
                                    use_ext_port_mapping = True
                                    self._emit("info", "Port mapping data collected successfully.")
                                    break
                            except Exception as pm_node_exc:
                                logger.warning("Port mapping via CNode %s failed: %s", cnode_ip, pm_node_exc)
                        if not use_ext_port_mapping:
                            self._emit("warn", "Port mapping collection failed for all CNodes.")
                    else:
                        if not switch_ips:
                            self._emit("warn", "No switch management IPs found — skipping port mapping.")
                        if not cnode_ips:
                            self._emit("warn", "No CNode management IPs found — skipping port mapping.")
                except Exception as pm_exc:
                    self._emit("warn", f"Port mapping collection failed (non-blocking): {pm_exc}")

            self._check_cancel()
            self._emit("info", "Processing and extracting report data...")
            data_extractor = create_data_extractor(config)
            processed = data_extractor.extract_all_data(raw_data, use_external_port_mapping=use_ext_port_mapping)
            if not processed:
                self._emit("error", "Data processing failed, skipping report.")
                api.close()
                return

            self._check_cancel()
            report_config = ReportConfig.from_yaml(config)
            report_builder = create_report_builder(config=report_config)

            output_dir = get_data_dir() / "reports"
            output_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cluster_name = processed.get("cluster_summary", {}).get("name", "unknown")
            self._resolved_cluster_name = cluster_name

            processed["cluster_ip"] = self._credentials.get("cluster_ip", "")

            if self._credentials.get("switch_placement") == "manual" and self._credentials.get("manual_placements"):
                processed["manual_switch_placements"] = self._credentials["manual_placements"]
                self._emit(
                    "info",
                    f"Using manual switch placement ({len(self._credentials['manual_placements'])} assignments)",
                )

            json_path = output_dir / f"vast_data_{cluster_name}_{timestamp}.json"
            data_extractor.save_processed_data(processed, str(json_path))
            self._emit("info", f"JSON saved: {json_path.name}")

            pdf_path = output_dir / f"vast_asbuilt_report_{cluster_name}_{timestamp}.pdf"
            self._emit("info", "Generating PDF report...")
            if report_builder.generate_pdf_report(processed, str(pdf_path)):
                self._emit("success", f"PDF saved: {pdf_path.name}")
            else:
                self._emit("error", "PDF generation failed.")

            import json as json_mod

            meta = {
                "cluster_ip": self._credentials.get("cluster_ip", ""),
                "cluster_name": cluster_name,
                "timestamp": timestamp,
            }
            meta_path = pdf_path.parent / (pdf_path.stem + ".meta.json")
            meta_path.write_text(json_mod.dumps(meta))

            api.close()
        except _OneShotCancelled:
            raise
        except Exception as exc:
            self._emit("error", f"Report generation failed (non-blocking): {exc}")
            logger.warning("Report generation failed: %s", exc)

    # ------------------------------------------------------------------
    # Phase: Bundle
    # ------------------------------------------------------------------

    def _run_bundling(self) -> None:
        self._check_cancel()

        with self._lock:
            self._state.phase = "bundling"
            self._state.operation_index = self._state.total_operations
            self._state.current_operation = "Bundling Results"

        self._emit("info", "")
        self._emit("info", "=" * 65)
        self._emit("info", "PHASE: BUNDLING RESULTS")
        self._emit("info", "=" * 65)

        try:
            from result_bundler import ResultBundler

            cluster_ip = self._credentials.get("cluster_ip", "").strip()
            resolved_name = getattr(self, "_resolved_cluster_name", None) or cluster_ip or "Unknown"
            bundler = ResultBundler(output_callback=self._output_callback)
            bundler.set_metadata(
                cluster_name=resolved_name,
                cluster_ip=cluster_ip or "Unknown",
                cluster_version=self._credentials.get("cluster_version", "Unknown"),
            )
            bundler.collect_results(cluster_ip=cluster_ip or None)
            bundle_path = bundler.create_bundle()

            with self._lock:
                self._state.bundle_path = str(bundle_path)

            self._emit("success", f"Bundle created: {bundle_path.name}")
        except _OneShotCancelled:
            raise
        except Exception as exc:
            self._emit("error", f"Bundling failed: {exc}")
            logger.warning("Bundling failed: %s", exc)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _load_config(self) -> Dict[str, Any]:
        """Load YAML config from the configured path."""
        import yaml

        if self._config_path:
            p = Path(self._config_path)
            if p.exists():
                with open(p, encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
        default = Path(__file__).parent.parent / "config" / "config.yaml"
        if default.exists():
            with open(default, encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    def cancel(self) -> bool:
        """Signal cancellation."""
        self._cancel_event.set()
        return True


class _OneShotCancelled(Exception):
    """Raised internally when one-shot execution is cancelled."""
