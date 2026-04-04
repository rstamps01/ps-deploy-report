"""
Network Configuration Extraction Workflow

4-step workflow for extracting network configuration commands:
1. Connect & Discover Nodes - SSH to CNode, parse local.cfg for all node IPs
2. Collect configure_network - Grep configure_network.log on each node
3. Extract Network Config - Collect interface, routing, bond config from each node
4. Save Output - Save extracted configuration to local files

Internal cluster IPs (e.g. 172.16.x.x) are only reachable from within the
cluster.  All commands targeting those nodes are proxied through the gateway
CNode via nested SSH: ``ssh gateway 'ssh <internal_ip> "command"'``.
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from script_runner import ScriptRunner
from utils.logger import get_logger
from utils.ssh_adapter import run_ssh_command

logger = get_logger(__name__)


class NetworkConfigWorkflow:
    """Network configuration extraction workflow."""

    name = "Network Extraction"
    description = "Extract configure_network.py commands for new node provisioning"
    enabled = True
    min_vast_version = "5.0"

    CONFIGURE_NETWORK_LOG = "/vast/log/configure_network/configure_network.log"
    INNER_SSH_KEY = "/home/vastdata/.ssh/id_rsa"

    def __init__(self):
        self._output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._credentials: Dict[str, Any] = {}
        self._script_runner: Optional[ScriptRunner] = None
        self._step_data: Dict[str, Any] = {}

    def set_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        self._output_callback = callback

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
            {"id": 1, "name": "Connect & Discover Nodes", "description": "SSH to CNode and discover all node IPs"},
            {
                "id": 2,
                "name": "Collect configure_network",
                "description": "Collect configure_network commands from all nodes",
            },
            {
                "id": 3,
                "name": "Extract Network Config",
                "description": "Collect interface, routing, and bond config from all nodes",
            },
            {"id": 4, "name": "Save Output", "description": "Save extracted configuration to local files"},
        ]

    def validate_prerequisites(self) -> tuple[bool, str]:
        required = ["cluster_ip", "node_user", "node_password"]
        missing = [k for k in required if not self._credentials.get(k)]
        if missing:
            return False, "Missing credentials: " + ", ".join(missing)
        return True, "Prerequisites met"

    def run_step(self, step_id: int) -> Dict[str, Any]:
        step_methods = {
            1: self._step_connect_and_discover,
            2: self._step_collect_configure_network,
            3: self._step_extract_network_config,
            4: self._step_save_output,
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

    # -- Helpers --

    def _gateway_ssh(self, cmd: str, timeout: int = 30) -> Tuple[int, str, str]:
        """SSH to the gateway CNode (the externally reachable cluster_ip)."""
        host = self._step_data.get("host", self._credentials.get("cluster_ip"))
        user = self._step_data.get("user", self._credentials.get("node_user", "vastdata"))
        password = self._step_data.get("password", self._credentials.get("node_password"))
        result = run_ssh_command(host, user, password, cmd, timeout=timeout)
        return (int(result[0]), str(result[1]), str(result[2]))

    def _parse_local_cfg(self, cfg_text: str) -> Dict[str, List[str]]:
        """Parse /etc/clustershell/groups.d/local.cfg to extract node IPs."""
        groups: Dict[str, str] = {}
        result: Dict[str, List[str]] = {}

        for line in cfg_text.strip().split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, _, value = line.partition(":")
            groups[key.strip()] = value.strip()

        def resolve(value: str) -> List[str]:
            ips = []
            for token in value.split():
                token = token.strip()
                if token.startswith("@"):
                    ref = token[1:]
                    if ref in groups:
                        ips.extend(resolve(groups[ref]))
                elif "[" in token and "-" in token:
                    match = re.match(r"(.+)\[(\d+)-(\d+)\]", token)
                    if match:
                        prefix = match.group(1)
                        start, end = int(match.group(2)), int(match.group(3))
                        for i in range(start, end + 1):
                            ips.append(f"{prefix}{i}")
                else:
                    ips.append(token)
            return ips

        for key, value in groups.items():
            resolved = resolve(value)
            if resolved:
                result[key] = resolved

        return result

    def _run_on_all_nodes(self, description: str, cmd: str, timeout: int = 30) -> Dict[str, str]:
        """Run a command on every discovered node via clush on the gateway.

        Internal cluster IPs (172.16.x.x) are only reachable from within
        the cluster.  We leverage ``clush -w <nodes>`` on the gateway CNode
        to fan out to all internal nodes in a single SSH call.  The gateway
        CNode itself is queried directly.

        ``clush`` output format is ``<node_ip>: <line>`` which we parse to
        build the per-node results dictionary.
        """
        nodes = self._step_data.get("all_nodes", {})
        gateway_ip = self._step_data.get("host", self._credentials.get("cluster_ip"))
        user = self._step_data.get("user")
        password = self._step_data.get("password")
        results: Dict[str, str] = {}

        # Separate gateway vs internal nodes
        internal_nodes = {n: ip for n, ip in nodes.items() if ip != gateway_ip}
        gateway_name = next((n for n, ip in nodes.items() if ip == gateway_ip), None)

        # --- Internal nodes: single clush call through gateway ---
        if internal_nodes:
            node_ips = ",".join(sorted(set(internal_nodes.values())))
            escaped = cmd.replace("'", "'\\''")
            clush_cmd = f"clush -w {node_ips} '{escaped}'"

            self.emit("info", f"  $ ssh {user}@{gateway_ip}")
            self.emit("info", f'    clush -w {node_ips} "{cmd}"')

            rc, stdout, stderr = run_ssh_command(
                gateway_ip,
                user,
                password,
                clush_cmd,
                timeout=max(timeout, 60),
                login_shell=True,
            )

            # Parse clush output: each line is "<ip>: <content>"
            ip_to_name = {ip: name for name, ip in internal_nodes.items()}
            ip_lines: Dict[str, list] = {}
            all_output = (stdout or "") + (stderr or "")

            for line in all_output.strip().split("\n"):
                if not line.strip():
                    continue
                # Skip clush meta-lines like "clush: 172.16.3.4: exited ..."
                if line.startswith("clush:"):
                    continue
                for ip in internal_nodes.values():
                    prefix = f"{ip}: "
                    if line.startswith(prefix):
                        content = line[len(prefix) :]
                        ip_lines.setdefault(ip, []).append(content)
                        break

            for ip, lines in sorted(ip_lines.items()):
                node_name = ip_to_name.get(ip, ip)
                output = "\n".join(lines)
                if output.strip():
                    results[node_name] = output.strip()
                    self.emit("success", f"    [{node_name}] {len(lines)} lines")

            # Report nodes that returned no data
            for name, ip in sorted(internal_nodes.items()):
                if name not in results:
                    self.emit("warn", f"    [{name}] no data returned")

        # --- Gateway node: direct SSH ---
        if gateway_name:
            self.emit("info", f"  $ ssh {user}@{gateway_ip} '{cmd}'")
            rc, stdout, stderr = run_ssh_command(
                gateway_ip,
                user,
                password,
                cmd,
                timeout=timeout,
            )
            if rc == 0 and stdout and stdout.strip():
                results[gateway_name] = stdout.strip()
                line_count = len(stdout.strip().split("\n"))
                self.emit("success", f"    [{gateway_name}] {line_count} lines")
            else:
                err = stderr.strip().split("\n")[-1] if stderr and stderr.strip() else "no output"
                self.emit("warn", f"    [{gateway_name}] {err}")

        return results

    # -- Step 1 --

    def _step_connect_and_discover(self) -> Dict[str, Any]:
        """Step 1: Connect to CNode and discover all node IPs from local.cfg."""
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        if not host:
            self.emit("error", "Cluster IP is required.")
            return {"success": False, "message": "Cluster IP is required"}
        if not password:
            self.emit("error", "Node SSH Password is required.")
            return {"success": False, "message": "Node SSH Password is required"}

        self.emit("info", "Connecting to CNode...")
        self.emit("info", f"$ ssh {user}@{host} hostname")
        rc, stdout, stderr = run_ssh_command(host, user, password, "hostname", timeout=15)
        if rc != 0:
            error_msg = stderr.strip().split("\n")[-1] if stderr else "Connection failed"
            self.emit("error", f"SSH connection failed: {error_msg}")
            return {"success": False, "message": f"SSH failed: {error_msg}"}

        hostname = stdout.strip()
        self.emit("success", f"Connected to {hostname} ({host})")

        self._step_data.update({"host": host, "hostname": hostname, "user": user, "password": password})

        # OS info
        self.emit("info", f"$ ssh {user}@{host} 'cat /etc/os-release | head -2'")
        rc, stdout, _ = run_ssh_command(host, user, password, "cat /etc/os-release | head -2", timeout=10)
        if rc == 0 and stdout:
            for line in stdout.strip().split("\n"):
                self.emit("info", f"  {line}")

        # Discover nodes from ClusterShell local.cfg
        self.emit("info", "")
        self.emit("info", "Discovering cluster nodes...")
        self.emit("info", f"$ ssh {user}@{host} 'cat /etc/clustershell/groups.d/local.cfg'")

        rc, stdout, stderr = run_ssh_command(
            host,
            user,
            password,
            "cat /etc/clustershell/groups.d/local.cfg 2>/dev/null",
            timeout=15,
        )

        all_nodes: Dict[str, str] = {}

        if rc == 0 and stdout and stdout.strip():
            groups = self._parse_local_cfg(stdout)

            # Build node list with meaningful names
            seen_ips = set()
            for group_name in sorted(groups.keys()):
                if group_name in ("all", "adm"):
                    continue
                for ip in groups[group_name]:
                    if ip not in seen_ips:
                        seen_ips.add(ip)
                        all_nodes[f"{group_name}_{ip}"] = ip

            if all_nodes:
                self.emit("info", "")
                self.emit("success", f"Discovered {len(all_nodes)} node(s):")
                for name, ip in sorted(all_nodes.items(), key=lambda x: x[1]):
                    self.emit("info", f"  {name}: {ip}")
        else:
            self.emit("warn", "ClusterShell config not found, using connected node only")

        # Always include connected node (gateway)
        if host not in {v for v in all_nodes.values()}:
            all_nodes[hostname] = host

        self._step_data["all_nodes"] = all_nodes

        self.emit("info", "")
        self.emit("info", f"Gateway node: {hostname} ({host})")
        self.emit("info", "Internal nodes will be reached via gateway (nested SSH)")

        return {
            "success": True,
            "message": f"Connected to {hostname}, discovered {len(all_nodes)} node(s)",
            "details": "\n".join(f"{n}: {ip}" for n, ip in sorted(all_nodes.items(), key=lambda x: x[1])),
        }

    # -- Step 2 --

    def _step_collect_configure_network(self) -> Dict[str, Any]:
        """Step 2: Collect last configure_network command from each node."""
        nodes = self._step_data.get("all_nodes")
        if not nodes:
            self.emit("error", "No nodes discovered. Run Step 1 first.")
            return {"success": False, "message": "Run Step 1 first."}

        self.emit("info", f"Collecting configure_network commands from {len(nodes)} node(s)...")
        self.emit("info", "")

        grep_cmd = f'grep -a "command line" {self.CONFIGURE_NETWORK_LOG} 2>/dev/null | tail -1'
        node_commands = self._run_on_all_nodes("configure_network", grep_cmd)

        all_lines = []
        for node in sorted(node_commands.keys()):
            ip = nodes.get(node, node)
            all_lines.append(f"{node} ({ip}): {node_commands[node]}")

        self._step_data["history_commands"] = all_lines
        self.emit("info", "")

        if not node_commands:
            self.emit("warn", "No configure_network commands found on any node")
            return {"success": True, "message": "No configure_network commands found"}

        self.emit("success", f"Collected commands from {len(node_commands)} of {len(nodes)} node(s)")
        return {
            "success": True,
            "message": f"Collected configure_network from {len(node_commands)} of {len(nodes)} node(s)",
            "details": "\n".join(all_lines),
        }

    # -- Step 3 --

    def _step_extract_network_config(self) -> Dict[str, Any]:
        """Step 3: Extract network config from all nodes via gateway-proxied SSH."""
        nodes = self._step_data.get("all_nodes")
        if not nodes:
            self.emit("error", "No nodes discovered. Run Step 1 first.")
            return {"success": False, "message": "Run Step 1 first."}

        self.emit("info", f"Extracting network configuration from {len(nodes)} node(s)...")
        self.emit("info", "")

        all_node_configs: Dict[str, Dict[str, str]] = {}

        self.emit("info", "--- Interface Configuration ---")
        results = self._run_on_all_nodes("interfaces", "ip addr show 2>/dev/null")
        if results:
            all_node_configs["interface_config"] = results
        self.emit("info", "")

        self.emit("info", "--- Routing Table ---")
        results = self._run_on_all_nodes("routing", "ip route show 2>/dev/null")
        if results:
            all_node_configs["routing_table"] = results
        self.emit("info", "")

        self.emit("info", "--- Bond Configuration ---")
        results = self._run_on_all_nodes("bonds", "cat /proc/net/bonding/bond* 2>/dev/null")
        filtered = {n: v for n, v in results.items() if v.strip()}
        if filtered:
            all_node_configs["bond_config"] = filtered
        else:
            self.emit("info", "  No bond interfaces found on any node")
        self.emit("info", "")

        self._step_data["all_node_configs"] = all_node_configs

        total_nodes: set[str] = set()
        for nd in all_node_configs.values():
            total_nodes.update(nd.keys())

        if not all_node_configs:
            return {"success": False, "message": "Could not extract any network configuration"}

        return {
            "success": True,
            "message": f"Extracted {len(all_node_configs)} config types from {len(total_nodes)} node(s)",
            "details": "\n".join(f"{k}: {len(v)} node(s)" for k, v in all_node_configs.items()),
        }

    # -- Step 4 --

    def _step_save_output(self) -> Dict[str, Any]:
        """Step 4: Save extracted configuration to local files."""
        history_commands = self._step_data.get("history_commands", [])
        all_node_configs = self._step_data.get("all_node_configs", {})
        all_nodes = self._step_data.get("all_nodes", {})
        hostname = self._step_data.get("hostname", "unknown")
        host = self._step_data.get("host", self._credentials.get("cluster_ip", "unknown"))

        if not history_commands and not all_node_configs:
            self.emit("error", "No configuration data to save. Run Steps 2 and 3 first.")
            return {"success": False, "message": "No configuration data to save"}

        self.emit("info", "Saving network configuration files...")

        local_dir = self._script_runner.get_local_dir() / "network_configs"
        local_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []

        if history_commands:
            cmd_file = local_dir / f"configure_network_commands_all_nodes_{timestamp}.txt"
            with open(cmd_file, "w") as f:
                f.write("# configure_network.py - Last Command Line Per Node\n")
                f.write(f"# Cluster: {hostname} ({host})\n")
                f.write(f"# Extracted: {timestamp}\n")
                f.write(f"# Nodes queried: {len(all_nodes)}\n")
                f.write("#" + "=" * 70 + "\n\n")
                for entry in history_commands:
                    f.write(f"{entry}\n")
            saved_files.append(str(cmd_file))
            self.emit("success", f"Saved: {cmd_file.name}")

        config_labels = {
            "interface_config": "interface_config",
            "routing_table": "routing_table",
            "bond_config": "bond_config",
        }
        for config_type, node_data in all_node_configs.items():
            label = config_labels.get(config_type, config_type)
            filename = f"{label}_all_nodes_{timestamp}.txt"
            filepath = local_dir / filename
            with open(filepath, "w") as f:
                f.write(f"# {label} - All Nodes\n")
                f.write(f"# Cluster: {hostname} ({host})\n")
                f.write(f"# Extracted: {timestamp}\n")
                f.write(f"# Nodes: {len(node_data)}\n")
                f.write("#" + "=" * 70 + "\n")
                for node in sorted(node_data.keys()):
                    ip = all_nodes.get(node, node)
                    f.write(f"\n{'#' * 72}\n")
                    f.write(f"### Node: {node} ({ip})\n")
                    f.write(f"{'#' * 72}\n")
                    f.write(node_data[node])
                    f.write("\n")
            saved_files.append(str(filepath))
            self.emit("success", f"Saved: {filename} ({len(node_data)} nodes)")

        summary_file = local_dir / f"network_summary_{hostname}_{timestamp}.json"
        summary_file.write_text(
            json.dumps(
                {
                    "timestamp": timestamp,
                    "cluster_hostname": hostname,
                    "cluster_ip": host,
                    "nodes_discovered": all_nodes,
                    "commands_found": len(history_commands),
                    "config_types": list(all_node_configs.keys()),
                    "files_saved": [Path(f).name for f in saved_files],
                },
                indent=2,
            )
        )
        saved_files.append(str(summary_file))
        self.emit("success", f"Saved: {summary_file.name}")

        self.emit("info", "")
        self.emit("info", f"Output directory: {local_dir}")

        return {
            "success": True,
            "message": f"Saved {len(saved_files)} configuration files",
            "details": "\n".join(saved_files),
            "data": {"files": saved_files},
        }
