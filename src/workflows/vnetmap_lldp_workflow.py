"""
vnetmap_lldp Workflow (NET-7)

5-step workflow that maps node data ports to switch ports from the LLDP neighbour data on
the nodes, using ``vnetmap_lldp.py --operation show-mapping``. No switch login is needed,
so it covers customer-managed switches where vnetmap.py cannot run.

The workflow only reads LLDP service and package state on the nodes; it never changes
them and never runs any tool operation other than show-mapping
(``tests/test_vnetmap_lldp_guardrails.py`` enforces both).
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from script_runner import ScriptRunner
from tool_manager import ToolManager
from utils.logger import get_logger
from utils.ssh_adapter import run_ssh_command

logger = get_logger(__name__)

TOOL_NAME = "vnetmap_lldp.py"
TOOL_COMMAND = "python3 /tmp/vast_scripts/vnetmap_lldp.py --operation show-mapping"
MAPPING_FILE = "/userdata/switch_mapping.json"
REMOTE_LOG_NOTE = "~/logs/vnetmap_<timestamp>.log"
CONFLUENCE_PAGE = "7347404806"
MARKER = "[asbuilt-reporter]"

LLDP_NOT_RUNNING_MESSAGE = (
    "LLDP is not running on the nodes. Enabling it changes node configuration; "
    f"arrange it with the customer (Confluence {CONFLUENCE_PAGE})."
)
LLDPAD_PACKAGE_MISSING_MESSAGE = (
    "No node has the lldpad package installed. The vnetmap_lldp tool requires lldpad and stops "
    "without it unless forced (-f), and this workflow never forces it. Arrange the package with "
    f"the customer (Confluence {CONFLUENCE_PAGE})."
)


def build_show_mapping_script() -> str:
    """Build the single remote shell command that runs show-mapping safely.

    show-mapping overwrites ``/userdata/switch_mapping.json``, the file a Support engineer
    may have saved for a later interface restore. The script copies any existing file to a
    ``mktemp`` backup first and aborts (exit 3) without running the tool if that copy fails.
    A ``trap`` on EXIT (signals exit through it) then restores the original, or removes the
    new file when none existed, whether the tool succeeds, fails or is interrupted. The
    tool's exit status is preserved. Progress lines start with :data:`MARKER`.

    Returns:
        One-line shell command for ``ScriptRunner.execute_remote``.
    """
    m = MAPPING_FILE
    remote_dir = ToolManager.REMOTE_DIR
    return (
        f"_VLM_BAK=$(mktemp {remote_dir}/.switch_mapping_backup.XXXXXX) || "
        f'{{ echo "{MARKER} backup-failed: mktemp in {remote_dir} failed; show-mapping not run"; exit 3; }}; '
        "_VLM_HAD=0; _VLM_DONE=0; "
        f"if [ -e {m} ]; then "
        f'if cp -p {m} "$_VLM_BAK"; then _VLM_HAD=1; echo "{MARKER} backup: saved existing {m}"; '
        f'else rm -f "$_VLM_BAK"; echo "{MARKER} backup-failed: could not copy {m}; show-mapping not run"; '
        "exit 3; fi; "
        f'else echo "{MARKER} backup: no existing {m}"; fi; '
        "_vlm_restore() { "
        '[ "$_VLM_DONE" = 1 ] && return 0; _VLM_DONE=1; '
        'if [ "$_VLM_HAD" = 1 ]; then '
        f'if cp -p "$_VLM_BAK" {m}; then rm -f "$_VLM_BAK"; echo "{MARKER} restore: original {m} restored"; '
        f'else echo "{MARKER} restore-failed: original {m} kept at $_VLM_BAK"; fi; '
        f'else rm -f "$_VLM_BAK"; if [ -e {m} ]; then rm -f {m}; '
        f'echo "{MARKER} restore: removed {m} written by this run (none existed before)"; '
        f'else echo "{MARKER} restore: no {m} to remove"; fi; fi; '
        "}; "
        "trap _vlm_restore EXIT; trap 'exit 1' HUP INT QUIT TERM; "
        f"{TOOL_COMMAND}; exit $?"
    )


def parse_restore_markers(output: str) -> Dict[str, Any]:
    """Read the backup/restore progress lines written by :func:`build_show_mapping_script`.

    Args:
        output: Remote stdout of the show-mapping script.

    Returns:
        Dict with ``backup`` and ``restore`` (the marker text or ``None``), ``backup_failed``,
        ``restore_failed`` and ``confirmed`` (True when a successful restore line was seen).
    """
    status: Dict[str, Any] = {
        "backup": None,
        "restore": None,
        "backup_failed": False,
        "restore_failed": False,
        "confirmed": False,
    }
    for raw in (output or "").splitlines():
        line = raw.strip()
        if not line.startswith(MARKER):
            continue
        kind, _, text = line[len(MARKER) :].strip().partition(": ")
        if kind == "backup":
            status["backup"] = text
        elif kind == "backup-failed":
            status["backup"] = text
            status["backup_failed"] = True
        elif kind == "restore":
            status["restore"] = text
            status["confirmed"] = True
        elif kind == "restore-failed":
            status["restore"] = text
            status["restore_failed"] = True
    return status


def _node_sort_key(node: str) -> Tuple[Any, ...]:
    parts = node.split(".")
    if len(parts) == 4 and all(p.isdigit() for p in parts):
        return (0, *(int(p) for p in parts))
    return (1, node)


def parse_clush_lines(output: str) -> Dict[str, List[str]]:
    """Group ``clush`` output (``<node>: <line>``) by node, skipping clush's own messages.

    Args:
        output: Combined stdout/stderr of a ``clush -a`` call.

    Returns:
        Mapping of node to its output lines, in order.
    """
    by_node: Dict[str, List[str]] = {}
    for raw in (output or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("clush:"):
            continue
        node, sep, content = line.partition(": ")
        if not sep or not node or " " in node:
            continue
        by_node.setdefault(node, []).append(content.strip())
    return by_node


def assess_lldp_readiness(
    lldpd: Dict[str, List[str]],
    lldpad: Dict[str, List[str]],
    packages: Dict[str, List[str]],
) -> Dict[str, Any]:
    """Decide whether show-mapping can run from read-only per-node LLDP state.

    A service counts as running only when ``systemctl is-active`` printed exactly the token
    ``active`` (``inactive`` contains ``active`` as a substring, which is why the tool's own
    count is inflated).

    Args:
        lldpd: Per-node ``systemctl is-active lldpd`` output.
        lldpad: Per-node ``systemctl is-active lldpad`` output.
        packages: Per-node ``rpm -q lldpad lldpd`` output.

    Returns:
        Dict with per-node lists (``nodes``, ``lldpd_active``, ``lldpad_active``,
        ``active_nodes``, ``nodes_without_lldp``, ``lldpad_package_nodes``,
        ``lldpd_package_nodes``), ``ready`` and ``reason`` (``None``, ``"no_nodes"``,
        ``"not_running"`` or ``"no_lldpad_package"``).
    """

    def _is_active(lines: List[str]) -> bool:
        tokens = lines[0].split() if lines else []
        return bool(tokens) and tokens[0].lower() == "active"

    def _has_package(lines: List[str], name: str) -> bool:
        return any(line.split()[0].startswith(f"{name}-") for line in lines if line.split())

    nodes = sorted(set(lldpd) | set(lldpad) | set(packages), key=_node_sort_key)
    lldpd_active = [n for n in nodes if _is_active(lldpd.get(n, []))]
    lldpad_active = [n for n in nodes if _is_active(lldpad.get(n, []))]
    active = [n for n in nodes if n in lldpd_active or n in lldpad_active]
    lldpad_pkg = [n for n in nodes if _has_package(packages.get(n, []), "lldpad")]
    lldpd_pkg = [n for n in nodes if _has_package(packages.get(n, []), "lldpd")]

    if not nodes:
        reason: Optional[str] = "no_nodes"
    elif not active:
        reason = "not_running"
    elif not lldpad_pkg:
        reason = "no_lldpad_package"
    else:
        reason = None

    return {
        "nodes": nodes,
        "lldpd_active": lldpd_active,
        "lldpad_active": lldpad_active,
        "active_nodes": active,
        "nodes_without_lldp": [n for n in nodes if n not in active],
        "lldpad_package_nodes": lldpad_pkg,
        "lldpd_package_nodes": lldpd_pkg,
        "ready": reason is None,
        "reason": reason,
    }


class VnetmapLLDPWorkflow:
    """Port map from node-side LLDP with vnetmap_lldp.py (node credentials only)."""

    name = "VAST vnetmap (LLDP from nodes)"
    description = "Map node ports to switch ports from LLDP on the nodes with vnetmap_lldp.py (no switch login)"
    enabled = True
    min_vast_version = "5.0"

    REQUIRED_SCRIPTS = [TOOL_NAME]

    def __init__(self):
        self._output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._credentials: Dict[str, Any] = {}
        self._script_runner: Optional[ScriptRunner] = None
        self._output_dir: Optional[Path] = None
        self._step_data: Dict[str, Any] = {}

    def set_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        self._output_callback = callback
        if self._script_runner:
            self._script_runner._output_callback = callback

    def set_output_dir(self, output_dir: Any) -> None:
        """Point local output at a per-cluster scripts dir (QP-2)."""
        self._output_dir = Path(output_dir)
        if self._script_runner is not None:
            self._script_runner.set_local_dir(self._output_dir)

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

    def _ssh_host(self) -> Optional[str]:
        """SSH target: the Teleport-forwarded local endpoint when set, else the cluster IP."""
        host = self._credentials.get("ssh_host") or self._credentials.get("cluster_ip")
        return str(host) if host else None

    def _ssh_port(self) -> int:
        """SSH port: the Teleport-forwarded local port when set, else 22."""
        try:
            return int(self._credentials.get("ssh_port") or 22)
        except (TypeError, ValueError):
            return 22

    def emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        if self._output_callback:
            try:
                self._output_callback(level, message, details)
            except Exception:
                pass

    def get_steps(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": 1,
                "name": "Deploy vnetmap_lldp.py",
                "description": "Deploy vnetmap_lldp.py to the CNode (internet-first, local cache fallback)",
            },
            {
                "id": 2,
                "name": "Check LLDP Readiness",
                "description": (
                    "Read-only: which clush, then systemctl is-active lldpd / lldpad and rpm -q lldpad lldpd "
                    "on every node. LLDP services and packages are never changed."
                ),
            },
            {
                "id": 3,
                "name": "Run show-mapping",
                "description": (
                    f"Run vnetmap_lldp.py --operation show-mapping. {MAPPING_FILE} is backed up first and "
                    "restored afterwards (or removed if none existed), also on failure. The tool's own log "
                    f"{REMOTE_LOG_NOTE} is left on the CNode."
                ),
            },
            {
                "id": 4,
                "name": "Validate Results",
                "description": "Parse the LLDP connection map; nodes with fewer than two mapped ports are warned",
            },
            {
                "id": 5,
                "name": "Save Output",
                "description": "Save vnetmap_lldp output and results to the local output directory",
            },
        ]

    def validate_prerequisites(self) -> tuple[bool, str]:
        required = ["cluster_ip", "node_user", "node_password"]
        missing = [k for k in required if not self._credentials.get(k)]
        if missing:
            return False, "Missing credentials: " + ", ".join(missing)
        return True, "Prerequisites met"

    def run_step(self, step_id: int) -> Dict[str, Any]:
        step_methods = {
            1: self._step_deploy_tool,
            2: self._step_check_readiness,
            3: self._step_run_show_mapping,
            4: self._step_validate_results,
            5: self._step_save_output,
        }

        method = step_methods.get(step_id)
        if not method:
            return {"success": False, "message": f"Invalid step ID: {step_id}"}

        if self._script_runner is None:
            self._script_runner = ScriptRunner(output_callback=self._output_callback, local_dir=self._output_dir)
        self._script_runner.set_ssh_port(self._ssh_port())

        try:
            return method()
        except Exception as e:
            logger.exception(f"Step {step_id} failed")
            return {"success": False, "message": str(e)}

    def _node_ssh(self, command: str, timeout: int = 60, login_shell: bool = False) -> Tuple[int, str, str]:
        user = self._credentials.get("node_user", "vastdata")
        host = self._ssh_host()
        self.emit("info", f"$ ssh {user}@{host} '{command}'")
        rc, stdout, stderr = run_ssh_command(
            host,
            user,
            self._credentials.get("node_password"),
            command,
            timeout=timeout,
            login_shell=login_shell,
            port=self._ssh_port(),
        )
        return int(rc), str(stdout or ""), str(stderr or "")

    def _clush_all(self, node_command: str) -> Dict[str, List[str]]:
        rc, stdout, stderr = self._node_ssh(f"clush -a '{node_command}'", timeout=120, login_shell=True)
        by_node = parse_clush_lines(f"{stdout}\n{stderr}")
        if rc != 0 and not by_node:
            self.emit("warn", f"clush returned rc={rc}: {(stderr or stdout).strip()[:200]}")
        return by_node

    def _step_deploy_tool(self) -> Dict[str, Any]:
        host = self._ssh_host()
        ssh_port = self._ssh_port()
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        if not host:
            self.emit("error", "Cluster IP is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Cluster IP is required"}
        if not password:
            self.emit("error", "Node SSH Password is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Node SSH Password is required"}

        self.emit("info", f"Deploying {TOOL_NAME} to CNode (no switch credentials are used)...")
        self.emit("info", f"Target: {user}@{host}:{ToolManager.REMOTE_DIR}")
        self.emit("info", "Strategy: Internet download first, local cache fallback")
        self.emit("info", "")

        tool_manager = ToolManager(output_callback=self._output_callback)
        dir_ok, dir_msg = tool_manager._ensure_remote_dir(host, user, password, port=ssh_port)
        if not dir_ok:
            self.emit("error", f"Failed to create remote directory: {dir_msg}")
            return {"success": False, "message": f"Failed to create remote directory: {dir_msg}"}

        ok, message = tool_manager.deploy_tool_to_cnode(TOOL_NAME, host, user, password, skip_mkdir=True, port=ssh_port)
        if not ok:
            self.emit("error", f"Deployment failed for {TOOL_NAME}: {message}")
            return {"success": False, "message": f"Failed to deploy {TOOL_NAME}: {message}"}

        remote_path = f"{ToolManager.REMOTE_DIR}/{TOOL_NAME}"
        self._step_data["remote_script"] = remote_path
        return {"success": True, "message": f"Deployed {TOOL_NAME} to CNode", "details": remote_path}

    def _step_check_readiness(self) -> Dict[str, Any]:
        self.emit("info", "Checking LLDP readiness (read-only; no service or package is changed)...")

        rc, stdout, stderr = self._node_ssh("which clush", timeout=30, login_shell=True)
        if rc != 0 or not stdout.strip():
            self.emit("error", "clush is not available on the CNode; vnetmap_lldp.py needs it to reach the nodes.")
            return {"success": False, "message": "clush is not available on the CNode"}
        self.emit("success", f"clush: {stdout.strip().splitlines()[0]}")

        lldpd = self._clush_all("systemctl is-active lldpd || true")
        lldpad = self._clush_all("systemctl is-active lldpad || true")
        packages = self._clush_all("rpm -q lldpad lldpd || true")

        readiness = assess_lldp_readiness(lldpd, lldpad, packages)
        self._step_data["readiness"] = readiness

        self.emit("info", "")
        self.emit("info", "─── LLDP state per node ───")
        for node in readiness["nodes"]:
            pkgs = [p for p in ("lldpad", "lldpd") if node in readiness[f"{p}_package_nodes"]]
            state_lldpd = (lldpd.get(node) or ["?"])[0]
            state_lldpad = (lldpad.get(node) or ["?"])[0]
            level = "info" if node in readiness["active_nodes"] else "warn"
            self.emit(
                level,
                f"  {node}  lldpd={state_lldpd}  lldpad={state_lldpad}  packages={','.join(pkgs) or 'none'}",
            )

        total = len(readiness["nodes"])
        active = len(readiness["active_nodes"])
        reason = readiness["reason"]
        if reason == "no_nodes":
            self.emit("error", "Could not read LLDP state from any node through clush.")
            return {"success": False, "message": "Could not read LLDP state from any node through clush"}
        if reason == "not_running":
            self.emit("error", LLDP_NOT_RUNNING_MESSAGE)
            return {"success": False, "message": LLDP_NOT_RUNNING_MESSAGE, "details": readiness}
        if reason == "no_lldpad_package":
            self.emit("error", LLDPAD_PACKAGE_MISSING_MESSAGE)
            return {"success": False, "message": LLDPAD_PACKAGE_MISSING_MESSAGE, "details": readiness}

        missing = readiness["nodes_without_lldp"]
        if missing:
            self.emit(
                "warn",
                f"LLDP is not active on {len(missing)} node(s): {', '.join(missing)}. "
                "Their ports will be missing from the map; enabling LLDP is arranged with the customer "
                f"(Confluence {CONFLUENCE_PAGE}).",
            )
            message = f"LLDP active on {active}/{total} node(s); {len(missing)} without LLDP"
        else:
            self.emit("success", f"LLDP active on all {total} node(s)")
            message = f"LLDP active on {active}/{total} node(s)"
        return {"success": True, "message": message, "details": readiness}

    def _step_run_show_mapping(self) -> Dict[str, Any]:
        host = self._ssh_host()
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        self.emit("info", "Running vnetmap_lldp.py show-mapping (reads LLDP neighbours on the nodes)...")
        self.emit(
            "info",
            f"{MAPPING_FILE} is backed up first and restored afterwards (removed if none existed), also on failure.",
        )
        self.emit("info", f"The tool writes its own log to {REMOTE_LOG_NOTE} on the CNode; that log is left in place.")

        script = build_show_mapping_script()
        result = self._script_runner.execute_remote(
            host=host,
            username=user,
            password=password,
            command=script,
            timeout=900,
        )
        stdout = result.stdout or ""
        restore = parse_restore_markers(stdout)
        self._step_data["show_mapping_output"] = stdout
        self._step_data["switch_mapping_restore"] = restore
        self._step_data["tool_command"] = TOOL_COMMAND
        self._step_data["remote_log"] = REMOTE_LOG_NOTE

        if restore["backup_failed"]:
            self.emit("error", f"Could not back up {MAPPING_FILE}; show-mapping was not run: {restore['backup']}")
            return {
                "success": False,
                "message": f"Could not back up {MAPPING_FILE}; show-mapping was not run",
                "details": restore["backup"],
            }

        if restore["restore_failed"]:
            self.emit("error", f"{MAPPING_FILE} was not restored automatically: {restore['restore']}")
        elif restore["confirmed"]:
            self.emit("success", f"{MAPPING_FILE}: {restore['restore']}")
        else:
            self.emit("warn", f"Could not confirm that {MAPPING_FILE} was restored; check it on the CNode.")

        if not result.success:
            self.emit("error", f"show-mapping exited with return code: {result.returncode}")
            return {
                "success": False,
                "message": f"vnetmap_lldp show-mapping failed with rc={result.returncode}",
                "details": result.stderr or stdout,
            }

        message = "show-mapping completed"
        if restore["restore_failed"]:
            message += f"; {MAPPING_FILE} needs a manual restore"
        return {"success": True, "message": message, "details": stdout}

    def _step_validate_results(self) -> Dict[str, Any]:
        output = self._step_data.get("show_mapping_output", "")
        self.emit("info", "Parsing vnetmap_lldp output...")
        self.emit("info", f"Output length: {len(output)} characters")

        try:
            from vnetmap_lldp_parser import parse_lldp_text
        except ImportError as exc:
            self.emit("error", f"LLDP output parser is not available: {exc}")
            return {"success": False, "message": "LLDP output parser is not available"}

        parsed = parse_lldp_text(output) or {}
        rows: List[Dict[str, Any]] = list(parsed.get("topology") or [])
        warnings: List[str] = []

        if parsed.get("operation_failed"):
            warnings.append("vnetmap_lldp reported 'Operation failed'; the map may be incomplete")

        status = parsed.get("lldp_service_status") or {}
        if status:
            self.emit(
                "info",
                f"Tool-reported LLDP service status: {status.get('active', 0)} active, "
                f"{status.get('inactive', 0)} inactive (informational; its count also matches 'inactive')",
            )

        ports_by_node: Dict[str, int] = {}
        for row in rows:
            node = str(row.get("hostname") or row.get("node_mgmt_ip") or row.get("node_ip") or "unknown")
            ports_by_node[node] = ports_by_node.get(node, 0) + 1
        under_mapped = {n: c for n, c in sorted(ports_by_node.items()) if c < 2}
        for node, count in under_mapped.items():
            warnings.append(f"Node {node}: {count} port mapped (expected at least 2)")

        switch_names = list(parsed.get("switch_names") or sorted({str(r.get("switch_name")) for r in rows}))
        readiness = self._step_data.get("readiness") or {}

        results = {
            "total_connections": len(rows),
            "nodes_mapped": len(ports_by_node),
            "nodes_checked": len(readiness.get("nodes", [])),
            "ports_by_node": ports_by_node,
            "under_mapped_nodes": sorted(under_mapped),
            "switch_names": switch_names,
            "lldp_service_status": status,
            "operation_failed": bool(parsed.get("operation_failed")),
            "warnings": warnings,
        }
        self._step_data["validation_results"] = results

        self.emit("info", "")
        self.emit("info", "─── Validation Summary ───")
        self.emit("info", f"Connections: {len(rows)}")
        self.emit("info", f"Nodes mapped: {len(ports_by_node)} (LLDP checked on {results['nodes_checked']})")
        self.emit("info", f"Switches (LLDP system names): {', '.join(switch_names) or 'none'}")
        for warning in warnings:
            self.emit("warn", f"  {warning}")

        if not rows:
            self.emit("error", "No LLDP connections found in the show-mapping output.")
            return {"success": False, "message": "No LLDP connections found", "details": "\n".join(warnings)}

        message = f"{len(rows)} connection(s) across {len(ports_by_node)} node(s) and {len(switch_names)} switch(es)"
        if warnings:
            message += f" ({len(warnings)} warning(s))"
        else:
            self.emit("success", message)
        return {"success": True, "message": message, "details": "\n".join(warnings) or None}

    def _step_save_output(self) -> Dict[str, Any]:
        self.emit("info", "Saving vnetmap_lldp results...")
        local_dir = self._script_runner.get_local_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cluster_ip = self._credentials.get("cluster_ip", "unknown")

        output_file = local_dir / f"vnetmap_lldp_output_{cluster_ip}_{timestamp}.txt"
        output_file.write_text(self._step_data.get("show_mapping_output", ""))
        self.emit("info", f"[SAVED] {output_file}")

        results_file = local_dir / f"vnetmap_lldp_results_{cluster_ip}_{timestamp}.json"
        results_data = {
            "timestamp": timestamp,
            "cluster_ip": cluster_ip,
            "source": "lldp",
            "tool_command": self._step_data.get("tool_command", TOOL_COMMAND),
            "readiness": self._step_data.get("readiness", {}),
            "validation": self._step_data.get("validation_results", {}),
            "switch_mapping_restore": self._step_data.get("switch_mapping_restore", {}),
            "remote_log": f"{REMOTE_LOG_NOTE} left on the CNode",
        }
        results_file.write_text(json.dumps(results_data, indent=2))
        self.emit("info", f"[SAVED] {results_file}")

        return {"success": True, "message": "Saved output files", "details": f"{output_file}\n{results_file}"}
