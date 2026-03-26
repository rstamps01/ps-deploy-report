"""
vnetmap Validation Workflow

7-step workflow for validating network topology using vnetmap.py.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from script_runner import ScriptRunner
from utils.ssh_adapter import run_ssh_command
from utils.logger import get_logger

logger = get_logger(__name__)


class VnetmapWorkflow:
    """vnetmap validation workflow."""

    name = "vnetmap Validation"
    description = "Validate network topology using vnetmap.py"
    enabled = True
    min_vast_version = "5.0"

    REQUIRED_SCRIPTS = ["vnetmap.py", "mlnx_switch_api.py"]
    LOCAL_CFG_PATH = "/etc/clustershell/groups.d/local.cfg"

    def __init__(self):
        self._output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._credentials: Dict[str, Any] = {}
        self._script_runner: Optional[ScriptRunner] = None
        self._step_data: Dict[str, Any] = {}
        self._remote_dir_created: bool = False

    def set_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        self._output_callback = callback
        if self._script_runner:
            self._script_runner._output_callback = callback

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

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
                "name": "Deploy Scripts to CNode",
                "description": "Deploy vnetmap.py and mlnx_switch_api.py (internet-first, local fallback)",
            },
            {"id": 2, "name": "Generate Export Commands", "description": "Read cluster config and generate exports"},
            {"id": 3, "name": "Execute Export Commands", "description": "Run export commands on CNode"},
            {"id": 4, "name": "Run vnetmap.py", "description": "Execute vnetmap validation script"},
            {"id": 5, "name": "Validate Results", "description": "Parse and validate vnetmap output"},
            {"id": 6, "name": "Save Output", "description": "Save results to local output directory"},
        ]

    def validate_prerequisites(self) -> tuple[bool, str]:
        required = ["cluster_ip", "node_user", "node_password"]
        missing = [k for k in required if not self._credentials.get(k)]
        if missing:
            return False, "Missing credentials: " + ", ".join(missing)
        return True, "Prerequisites met"

    def run_step(self, step_id: int) -> Dict[str, Any]:
        step_methods = {
            1: self._step_deploy_scripts,
            2: self._step_generate_export_commands,
            3: self._step_execute_exports,
            4: self._step_run_vnetmap,
            5: self._step_validate_results,
            6: self._step_save_output,
        }

        method = step_methods.get(step_id)
        if not method:
            return {"success": False, "message": f"Invalid step ID: {step_id}"}

        if self._script_runner is None:
            self._script_runner = ScriptRunner(output_callback=self._output_callback)

        try:
            return method()
        except Exception as e:
            logger.exception(f"Step {step_id} failed")
            return {"success": False, "message": str(e)}

    def _step_deploy_scripts(self) -> Dict[str, Any]:
        from tool_manager import ToolManager

        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        # Validate credentials
        if not host:
            self.emit("error", "Cluster IP is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Cluster IP is required"}
        if not password:
            self.emit("error", "Node SSH Password is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Node SSH Password is required"}

        self.emit("info", "Deploying required scripts to CNode...")
        self.emit("info", f"Required scripts: {', '.join(self.REQUIRED_SCRIPTS)}")
        self.emit("info", f"Target: {user}@{host}:{ToolManager.REMOTE_DIR}")
        self.emit("info", "")
        self.emit("info", "Strategy: Internet download first, local cache fallback")
        self.emit("info", "")

        tool_manager = ToolManager(output_callback=self._output_callback)

        # Create remote directory first (before any downloads)
        dir_success, dir_msg = tool_manager._ensure_remote_dir(host, user, password)
        if not dir_success:
            self.emit("error", f"Failed to create remote directory: {dir_msg}")
            return {"success": False, "message": f"Failed to create remote directory: {dir_msg}"}
        self.emit("info", "")

        deployed = []
        for script in self.REQUIRED_SCRIPTS:
            self.emit("info", f"─── Deploying: {script} ───")
            success, message = tool_manager.deploy_tool_to_cnode(script, host, user, password, skip_mkdir=True)
            if not success:
                self.emit("error", f"Deployment failed for {script}: {message}")
                return {"success": False, "message": f"Failed to deploy {script}: {message}"}
            deployed.append(f"{ToolManager.REMOTE_DIR}/{script}")
            self.emit("info", "")

        self._step_data["remote_scripts"] = deployed
        self._step_data["remote_dir"] = ToolManager.REMOTE_DIR
        self._remote_dir_created = True  # Directory created by ToolManager

        return {
            "success": True,
            "message": f"Deployed {len(deployed)} scripts to CNode",
            "details": "\n".join(deployed),
        }

    def _step_copy_to_cnode(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")
        remote_dir = self._script_runner.DEFAULT_REMOTE_DIR

        self.emit("info", f"Copying scripts to CNode...")
        self.emit("info", f"Target: {user}@{host}:{remote_dir}")

        ok, msg = self._script_runner.check_prerequisites(host, user, password)
        if not ok:
            self.emit("error", f"Prerequisite check failed: {msg}")
            return {"success": False, "message": msg}

        self.emit("success", "SSH connection verified")

        # Create remote directory ONCE
        if not self._remote_dir_created:
            self.emit("info", f"$ ssh {user}@{host} 'mkdir -p {remote_dir}'")
            rc, _, stderr = run_ssh_command(host, user, password, f"mkdir -p {remote_dir}", timeout=10)
            if rc != 0:
                self.emit("error", f"Failed to create directory: {stderr}")
                return {"success": False, "message": f"Failed to create remote directory: {stderr}"}
            self.emit("success", f"Directory ready: {remote_dir}")
            self._remote_dir_created = True

        copied = []
        for script_path in self._step_data.get("downloaded_scripts", []):
            self.emit("info", f"─── Copying: {script_path} ───")
            # Use copy without creating directory again (pass the existing remote_dir)
            result = self._script_runner.copy_to_remote(
                script_path,
                host,
                user,
                password,
                remote_dir=remote_dir,
                set_executable=True,
                skip_mkdir=True,  # Directory already created above
            )
            if not result.success:
                self.emit("error", f"Copy failed: {result.error}")
                return {"success": False, "message": f"Failed to copy {script_path}: {result.error}"}
            self.emit("success", f"Remote path: {result.remote_path}")
            copied.append(result.remote_path)

        self._step_data["remote_scripts"] = copied
        self._step_data["remote_dir"] = remote_dir
        return {"success": True, "message": f"Copied {len(copied)} scripts to {host}", "details": "\n".join(copied)}

    def _convert_ip_format(self, clustershell_format: str) -> str:
        """
        Convert ClusterShell IP format to bash brace expansion format.

        Example: 10.143.11.[1-4] -> 10.143.11.{1..4}
        """
        # Match pattern like xxx.xxx.xxx.[x-x]
        match = re.search(r"^(.+)\[(\d+)-(\d+)\]$", clustershell_format.strip())
        if match:
            prefix = match.group(1)
            start = match.group(2)
            end = match.group(3)
            return f"{prefix}{{{start}..{end}}}"
        # If no range pattern, return as-is (single IP)
        return clustershell_format.strip()

    def _parse_local_cfg(self, cfg_content: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Parse /etc/clustershell/groups.d/local.cfg to extract cnode and dnode IPs.

        Handles group references like:
            cnodesub0: 172.16.3.[4-5]
            cnodes: @cnodesub0

        Resolves @group references to their actual IP ranges.

        Returns:
            Tuple of (cnodes_pattern, dnodes_pattern) in ClusterShell format
        """
        # First pass: build a dictionary of all group definitions
        groups = {}
        cnodes_raw = None
        dnodes_raw = None

        for line in cfg_content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                if key == "cnodes":
                    cnodes_raw = value
                elif key == "dnodes":
                    dnodes_raw = value
                elif key not in ["all"]:  # Store other groups for resolution
                    groups[key] = value

        # Second pass: resolve group references
        def resolve_group_ref(value: str) -> str:
            """Resolve @group references to actual IP patterns."""
            if not value:
                return ""

            resolved_parts = []
            # Handle comma-separated group references (e.g., @cnodesub0,@cnodesub1)
            for part in value.split(","):
                part = part.strip()
                if part.startswith("@"):
                    group_name = part[1:]  # Remove @ prefix
                    if group_name in groups:
                        # Recursively resolve in case of nested references
                        resolved = resolve_group_ref(groups[group_name])
                        resolved_parts.append(resolved)
                    else:
                        # Group not found, keep as-is
                        resolved_parts.append(part)
                else:
                    resolved_parts.append(part)

            return ",".join(resolved_parts)

        cnodes = resolve_group_ref(cnodes_raw) if cnodes_raw else None
        dnodes = resolve_group_ref(dnodes_raw) if dnodes_raw else None

        # Log resolution for debugging
        if cnodes_raw and cnodes_raw != cnodes:
            self.emit("info", f"[RESOLVED] cnodes: {cnodes_raw} -> {cnodes}")
        if dnodes_raw and dnodes_raw != dnodes:
            self.emit("info", f"[RESOLVED] dnodes: {dnodes_raw} -> {dnodes}")

        return cnodes, dnodes

    def _get_switch_ips_from_api(self) -> List[str]:
        """
        Get switch management IPs from the VAST API.

        Returns:
            List of switch management IP addresses
        """
        import requests
        from urllib3.exceptions import InsecureRequestWarning
        import warnings

        warnings.filterwarnings("ignore", category=InsecureRequestWarning)

        host = self._credentials.get("cluster_ip")
        username = self._credentials.get("username", "support")
        password = self._credentials.get("password")
        api_token = self._credentials.get("api_token")

        url = f"https://{host}/api/switches/"

        try:
            if api_token:
                headers = {"Authorization": f"Bearer {api_token}"}
                response = requests.get(url, headers=headers, verify=False, timeout=30)
            else:
                response = requests.get(url, auth=(username, password), verify=False, timeout=30)

            response.raise_for_status()
            switches = response.json()

            # Extract mgmt_ip from each switch
            ips = []
            for switch in switches:
                mgmt_ip = switch.get("mgmt_ip")
                if mgmt_ip:
                    ips.append(mgmt_ip)

            return ips
        except Exception as e:
            logger.error(f"Failed to get switch IPs from API: {e}")
            return []

    def _step_generate_export_commands(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")
        switch_user = self._credentials.get("switch_user", "cumulus")
        switch_password = self._credentials.get("switch_password", "")

        # Store switch credentials for later validation
        self._step_data["switch_user"] = switch_user
        self._step_data["switch_password"] = switch_password

        self.emit("info", "Generating export commands from cluster configuration...")

        # Step 1: Read /etc/clustershell/groups.d/local.cfg from CNode
        self.emit("info", f"$ ssh {user}@{host} 'cat {self.LOCAL_CFG_PATH}'")
        rc, cfg_content, stderr = run_ssh_command(host, user, password, f"cat {self.LOCAL_CFG_PATH}", timeout=30)

        if rc != 0:
            self.emit("error", f"Failed to read local.cfg: {stderr}")
            return {"success": False, "message": f"Failed to read {self.LOCAL_CFG_PATH}: {stderr}"}

        self.emit("info", "─── local.cfg content ───")
        for line in cfg_content.strip().split("\n"):
            self.emit("info", line)
        self.emit("info", "─" * 40)

        # Step 2: Parse cnode and dnode IPs
        cnodes_raw, dnodes_raw = self._parse_local_cfg(cfg_content)

        if not cnodes_raw:
            self.emit("error", "Could not find cnodes in local.cfg")
            return {"success": False, "message": "cnodes not found in local.cfg"}

        self.emit("info", f"[PARSED] cnodes (raw): {cnodes_raw}")
        if dnodes_raw:
            self.emit("info", f"[PARSED] dnodes (raw): {dnodes_raw}")
        else:
            self.emit("warn", "No dnodes found in local.cfg (CNode-only cluster)")
            dnodes_raw = ""

        # Step 3: Convert to bash brace expansion format
        cnodes_export = self._convert_ip_format(cnodes_raw)
        dnodes_export = self._convert_ip_format(dnodes_raw) if dnodes_raw else ""

        self.emit("info", f"[CONVERTED] cnodes_ips format: {cnodes_export}")
        if dnodes_export:
            self.emit("info", f"[CONVERTED] dnodes_ips format: {dnodes_export}")

        # Step 4: Get switch IPs from API
        self.emit("info", "")
        self.emit("info", f"$ curl -k https://{host}/api/switches/")
        switch_ips = self._get_switch_ips_from_api()

        if switch_ips:
            self.emit("success", f"[API] Found {len(switch_ips)} switch(es): {', '.join(switch_ips)}")
            mlx_ips = ",".join(switch_ips)
            network_type = "ETH"  # Ethernet with switches

            # Validate switch credentials for ETH mode
            if not switch_password:
                self.emit("error", "Switch SSH Password is required for ETH networks.")
                self.emit("error", "Please fill in the Switch Password field in Connection Settings.")
                return {"success": False, "message": "Switch SSH Password is required for ETH networks"}
        else:
            self.emit("warn", "[API] No switches found - assuming InfiniBand cluster")
            mlx_ips = ""
            network_type = "IB"

        # Step 5: Generate export commands
        self.emit("info", "")
        self.emit("info", "─── Generated Export Commands ───")

        exports = []
        exports.append(f"export cnodes_ips=`echo {cnodes_export} | sed 's/ /,/g'`")
        self.emit("info", exports[-1])

        if dnodes_export:
            exports.append(f"export dnodes_ips=`echo {dnodes_export} | sed 's/ /,/g'`")
            self.emit("info", exports[-1])
        else:
            exports.append('export dnodes_ips=""')
            self.emit("info", exports[-1])

        if mlx_ips:
            exports.append(f'export MLX_IPS="{mlx_ips}"')
            self.emit("info", exports[-1])

        # Step 6: Generate vnetmap.py command
        self.emit("info", "")
        self.emit("info", "─── Generated vnetmap.py Command ───")

        remote_dir = self._step_data.get("remote_dir", self._script_runner.DEFAULT_REMOTE_DIR)

        if network_type == "ETH":
            # Ethernet command with switches
            if dnodes_export:
                node_ips = "$cnodes_ips,$dnodes_ips"
            else:
                node_ips = "$cnodes_ips"

            # Note: Not passing -k flag - vnetmap will auto-discover the correct SSH key
            vnetmap_cmd = (
                f"python3 vnetmap.py -s $MLX_IPS " f"-i {node_ips} " f"-u {switch_user} " f"-p '{switch_password}'"
            )
        else:
            # InfiniBand command
            if dnodes_export:
                node_ips = "$cnodes_ips,$dnodes_ips"
            else:
                node_ips = "$cnodes_ips"

            # Note: Not passing -k flag - vnetmap will auto-discover the correct SSH key
            vnetmap_cmd = f"python3 vnetmap.py -i {node_ips} -ib"

        self.emit("info", vnetmap_cmd)

        # Store for later steps
        self._step_data["export_commands"] = exports
        self._step_data["vnetmap_command"] = vnetmap_cmd
        self._step_data["network_type"] = network_type
        self._step_data["switch_ips"] = switch_ips
        self._step_data["cnodes_export"] = cnodes_export
        self._step_data["dnodes_export"] = dnodes_export

        details = "\n".join(exports) + "\n\n" + vnetmap_cmd
        return {
            "success": True,
            "message": f"Generated {network_type} configuration with {len(switch_ips)} switch(es)",
            "details": details,
        }

    def _step_execute_exports(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        self.emit("info", "Validating export commands on remote host...")

        exports = self._step_data.get("export_commands", [])
        if not exports:
            return {"success": False, "message": "No export commands generated"}

        # Execute exports and verify they expand correctly
        export_str = " && ".join(exports)
        verify_cmd = f'{export_str} && echo "cnodes_ips=$cnodes_ips" && echo "dnodes_ips=$dnodes_ips"'

        if self._step_data.get("switch_ips"):
            verify_cmd += ' && echo "MLX_IPS=$MLX_IPS"'

        self.emit("info", f"$ ssh {user}@{host}")
        self.emit("info", f"$ {verify_cmd}")

        rc, stdout, stderr = run_ssh_command(host, user, password, verify_cmd, timeout=30)

        if rc != 0:
            self.emit("error", f"Export validation failed: {stderr}")
            return {"success": False, "message": f"Export commands failed: {stderr}"}

        self.emit("info", "")
        self.emit("info", "─── Expanded Values ───")
        for line in stdout.strip().split("\n"):
            self.emit("success", line)

        self._step_data["exports_ready"] = True
        return {"success": True, "message": "Export commands validated successfully", "details": stdout}

    def _step_run_vnetmap(self) -> Dict[str, Any]:
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")
        remote_dir = self._step_data.get("remote_dir", self._script_runner.DEFAULT_REMOTE_DIR)

        self.emit("info", "Executing vnetmap.py validation script...")
        self.emit("info", f"Remote host: {user}@{host}")
        self.emit("info", f"Working directory: {remote_dir}")
        self.emit("info", f"Network type: {self._step_data.get('network_type', 'Unknown')}")

        # Build the full command with exports
        exports = self._step_data.get("export_commands", [])
        vnetmap_cmd = self._step_data.get("vnetmap_command", "python3 vnetmap.py --validate")

        export_str = " && ".join(exports)
        full_cmd = f"cd {remote_dir} && {export_str} && {vnetmap_cmd}"

        self.emit("info", "")
        self.emit("info", "─── Full Command ───")
        self.emit("info", full_cmd)
        self.emit("info", "")

        # Use direct SSH execution
        result = self._script_runner.execute_remote(
            host=host,
            username=user,
            password=password,
            command=full_cmd,
            timeout=600,  # 10 minute timeout
        )

        if not result.success:
            self.emit("error", f"vnetmap exited with return code: {result.returncode}")
            return {
                "success": False,
                "message": f"vnetmap failed with rc={result.returncode}",
                "details": result.stderr or result.stdout,
            }

        self._step_data["vnetmap_output"] = result.stdout
        return {
            "success": True,
            "message": "vnetmap.py completed successfully",
            "details": result.stdout,
        }

    def _step_validate_results(self) -> Dict[str, Any]:
        output = self._step_data.get("vnetmap_output", "")

        self.emit("info", "Parsing vnetmap output for validation results...")
        self.emit("info", f"Output length: {len(output)} characters")

        results: Dict[str, Any] = {
            "errors": [],
            "warnings": [],
            "failed_nodes": [],
            "recommendations": [],
            "ports_passed": 0,
            "ports_failed": 0,
            "switches_found": 0,
            "topology_complete": False,
            "ssh_key_used": None,
        }

        # Parse the output for meaningful validation results
        in_failed_section = False
        for line in output.split("\n"):
            ll = line.lower()

            # Port pass/fail counts
            if "passed:" in ll and "failed:" in ll:
                passed_match = re.search(r"passed:\s*(\d+)", ll)
                failed_match = re.search(r"failed:\s*(\d+)", ll)
                if passed_match:
                    results["ports_passed"] = int(passed_match.group(1))
                if failed_match:
                    results["ports_failed"] = int(failed_match.group(1))

            # Topology completeness
            if "full topology" in ll:
                results["topology_complete"] = True

            # Switch count
            if "switch discovery progress:" in ll:
                switch_match = re.search(r"(\d+)/(\d+) switches", ll)
                if switch_match:
                    results["switches_found"] = int(switch_match.group(2))

            # SSH key that ultimately worked
            if "ssh check" in ll and "works for" in ll:
                key_match = re.search(r"ssh check (\S+) works", line)
                if key_match:
                    results["ssh_key_used"] = key_match.group(1)

            # Track Failed Nodes section
            if "failed nodes:" in ll:
                in_failed_section = True
                continue
            if in_failed_section:
                node_match = re.match(r"(\d+\.\d+\.\d+\.\d+):\s*(.+)", line.strip())
                if node_match:
                    results["failed_nodes"].append(
                        {
                            "ip": node_match.group(1),
                            "reason": node_match.group(2).strip(),
                        }
                    )
                elif line.strip() and not line.strip().startswith("["):
                    continue
                else:
                    in_failed_section = False

        # --- Build recommendations ---
        for node in results["failed_nodes"]:
            ip = node["ip"]
            reason = node["reason"]
            if "failed to ssh" in reason.lower():
                results["recommendations"].append(
                    f"Node {ip}: SSH unreachable. Verify the node is powered on, "
                    f"SSH service is running, and the node is accessible from the gateway CNode."
                )
            elif "permission denied" in reason.lower():
                results["recommendations"].append(
                    f"Node {ip}: SSH permission denied. Check that the SSH key "
                    f"on the gateway CNode is authorized for this node."
                )
            else:
                results["recommendations"].append(f"Node {ip}: {reason}")

        if results.get("ssh_key_used") and "deploy" in results["ssh_key_used"]:
            results["recommendations"].append(
                "SSH key fallback: vnetmap used /vast/deploy/ssh_key.pem instead of "
                "/home/vastdata/.ssh/id_rsa. This is normal for some cluster configurations."
            )

        self._step_data["validation_results"] = results

        # --- Display summary ---
        self.emit("info", "")
        self.emit("info", "\u2500\u2500\u2500 Validation Summary \u2500\u2500\u2500")
        self.emit("info", f"Topology Complete: {'Yes' if results['topology_complete'] else 'No'}")
        self.emit("info", f"Switches Found: {results['switches_found']}")
        self.emit("info", f"Ports Passed: {results['ports_passed']}")
        self.emit("info", f"Ports Failed: {results['ports_failed']}")

        if results["failed_nodes"]:
            self.emit("info", "")
            self.emit("warn", f"\u2500\u2500\u2500 Failed Nodes ({len(results['failed_nodes'])}) \u2500\u2500\u2500")
            for node in results["failed_nodes"]:
                self.emit("warn", f"  {node['ip']}: {node['reason']}")

        if results["recommendations"]:
            self.emit("info", "")
            self.emit("info", "\u2500\u2500\u2500 Recommendations \u2500\u2500\u2500")
            for rec in results["recommendations"]:
                self.emit("info", f"  \u2022 {rec}")

        # --- Determine overall result ---
        total_ports = results["ports_passed"] + results["ports_failed"]
        details_parts = [f"Passed: {results['ports_passed']}, Failed: {results['ports_failed']}"]
        if results["failed_nodes"]:
            details_parts.append("Failed nodes: " + ", ".join(n["ip"] for n in results["failed_nodes"]))
        if results["recommendations"]:
            details_parts.extend(results["recommendations"])
        details = "\n".join(details_parts)

        if results["ports_failed"] > 0 and results["ports_passed"] > 0:
            self.emit("warn", f"Partial success: {results['ports_passed']}/{total_ports} ports validated")
            return {
                "success": True,
                "message": (
                    f"Completed with warnings: {results['ports_passed']}/{total_ports} "
                    f"ports passed, {results['ports_failed']} failed "
                    f"({len(results['failed_nodes'])} node(s) unreachable)"
                ),
                "details": details,
            }

        if results["ports_failed"] > 0 and results["ports_passed"] == 0:
            return {
                "success": False,
                "message": f"Validation failed: all {results['ports_failed']} ports failed",
                "details": details,
            }

        if results["topology_complete"] and results["ports_passed"] > 0:
            self.emit("success", f"All {results['ports_passed']} ports validated successfully")
            return {
                "success": True,
                "message": f"Validation passed \u2013 {results['ports_passed']} ports OK",
                "details": f"Topology complete with {results['switches_found']} switches",
            }

        return {"success": True, "message": "Validation completed \u2013 check output for details"}

    def _filter_vnetmap_output(self, raw_output: str) -> str:
        """
        Filter vnetmap output to remove SSH retry noise and keep meaningful content.

        Removes:
        - SSH key retry error tracebacks
        - CalledProcessError tracebacks

        Keeps:
        - Switch discovery progress
        - Port validation progress
        - Topology output
        - Final status messages
        """
        lines = raw_output.split("\n")
        filtered_lines = []
        skip_until_empty = False

        for i, line in enumerate(lines):
            # Skip traceback blocks (start with "Traceback" or indented "File")
            if line.strip().startswith("Traceback (most recent call last):"):
                skip_until_empty = True
                continue

            # Skip indented traceback lines
            if skip_until_empty:
                if line.strip() == "" or (not line.startswith(" ") and not line.startswith("\t")):
                    skip_until_empty = False
                    # Don't include CalledProcessError lines
                    if "CalledProcessError" in line or "subprocess." in line:
                        continue
                else:
                    continue

            # Skip SSH retry error lines (they're informational, not real errors)
            if "{ERROR}" in line and "ssh" in line.lower() and "sudo /bin/true" in line:
                continue

            # Skip CalledProcessError lines
            if "subprocess.CalledProcessError" in line:
                continue

            # Skip SSH retry info that just shows the key dict
            if line.strip().startswith("{'SSH_KEY"):
                continue

            filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _step_save_output(self) -> Dict[str, Any]:
        self.emit("info", "Saving vnetmap results...")
        local_dir = self._script_runner.get_local_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cluster_ip = self._credentials.get("cluster_ip", "unknown")

        raw_output = self._step_data.get("vnetmap_output", "")

        # Filter output to remove SSH retry noise
        clean_output = self._filter_vnetmap_output(raw_output)

        # Save filtered output
        output_file = local_dir / f"vnetmap_output_{cluster_ip}_{timestamp}.txt"
        output_file.write_text(clean_output)
        self.emit("info", f"[SAVED] {output_file}")
        self.emit("info", f"  Filtered {len(raw_output)} -> {len(clean_output)} chars (removed SSH retry noise)")

        # Save structured results
        results_file = local_dir / f"vnetmap_results_{cluster_ip}_{timestamp}.json"
        results_data = {
            "timestamp": timestamp,
            "cluster_ip": cluster_ip,
            "network_type": self._step_data.get("network_type", "Unknown"),
            "switch_ips": self._step_data.get("switch_ips", []),
            "cnodes_export": self._step_data.get("cnodes_export", ""),
            "dnodes_export": self._step_data.get("dnodes_export", ""),
            "vnetmap_command": self._step_data.get("vnetmap_command", ""),
            "validation": self._step_data.get("validation_results", {}),
        }
        results_file.write_text(json.dumps(results_data, indent=2))
        self.emit("info", f"[SAVED] {results_file}")

        return {"success": True, "message": "Saved output files", "details": f"{output_file}\n{results_file}"}
