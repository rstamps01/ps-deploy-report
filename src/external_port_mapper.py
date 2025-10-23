"""
External Port Mapper

Collects port mapping data from outside the cluster using:
- VAST REST API for node inventory
- SSH to CNode with clush to get all node MACs
- SSH to switches to get MAC address tables

REQUIRED CREDENTIALS:
- API: support/<PASSWORD> (support user with viewer role)
- Nodes: vastdata/vastdata (default node credentials)
- Switches: cumulus/Vastdata1! (Cumulus Linux default with VAST password)
"""

import logging
import re
import subprocess
from typing import Any, Dict, List, Tuple
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class VerboseLogger:
    """Dedicated verbose logger for external port mapper debugging with color-coded output."""

    # ANSI color codes
    BLUE = "\033[94m"  # For operations/commands
    GREEN = "\033[92m"  # For successful responses
    RED = "\033[91m"  # For errors
    YELLOW = "\033[93m"  # For warnings
    CYAN = "\033[96m"  # For function calls
    MAGENTA = "\033[95m"  # For data/responses
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def __init__(self, log_file: str = None):
        if log_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = f"logs/external_port_mapper_verbose_{timestamp}.log"

        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Clear existing log
        with open(self.log_file, "w") as f:
            f.write(f"{self.BOLD}{'='*80}{self.RESET}\n")
            f.write(
                f"{self.BOLD}{self.CYAN}EXTERNAL PORT MAPPER VERBOSE LOG{self.RESET}\n"
            )
            f.write(f"{self.BOLD}Started: {datetime.now().isoformat()}{self.RESET}\n")
            f.write(f"{self.BOLD}{'='*80}{self.RESET}\n\n")
            f.write(f"COLOR LEGEND:\n")
            f.write(f"  {self.CYAN}CYAN    = Function calls and sections{self.RESET}\n")
            f.write(f"  {self.BLUE}BLUE    = Commands and operations{self.RESET}\n")
            f.write(f"  {self.GREEN}GREEN   = Successful responses{self.RESET}\n")
            f.write(f"  {self.MAGENTA}MAGENTA = Data and output{self.RESET}\n")
            f.write(f"  {self.YELLOW}YELLOW  = Warnings{self.RESET}\n")
            f.write(f"  {self.RED}RED     = Errors{self.RESET}\n")
            f.write(f"\n{'='*80}\n\n")

    def log(self, message: str, color: str = ""):
        """Write message to log file with timestamp and optional color."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        with open(self.log_file, "a") as f:
            if color:
                f.write(f"[{timestamp}] {color}{message}{self.RESET}\n")
            else:
                f.write(f"[{timestamp}] {message}\n")

    def log_function_enter(self, function_name: str, **kwargs):
        """Log function entry with parameters."""
        self.log(f"\n{'▶'*40}", self.CYAN)
        self.log(f"ENTERING FUNCTION: {function_name}", self.CYAN + self.BOLD)
        if kwargs:
            self.log(f"Parameters:", self.CYAN)
            for key, value in kwargs.items():
                self.log(f"  {key}: {value}", self.CYAN)
        self.log(f"{'▶'*40}\n", self.CYAN)

    def log_function_exit(self, function_name: str, result_summary: str = None):
        """Log function exit with optional result summary."""
        self.log(f"\n{'◀'*40}", self.CYAN)
        self.log(f"EXITING FUNCTION: {function_name}", self.CYAN + self.BOLD)
        if result_summary:
            self.log(f"Result: {result_summary}", self.CYAN)
        self.log(f"{'◀'*40}\n", self.CYAN)

    def log_operation(self, operation: str):
        """Log an operation being performed."""
        self.log(f"\n>>> OPERATION: {operation}", self.BLUE + self.BOLD)

    def log_command(self, cmd: list, label: str = "COMMAND"):
        """Log command details."""
        self.log(f"\n{self.BLUE}{'-'*80}{self.RESET}")
        self.log(f"🔧 {label}", self.BLUE + self.BOLD)
        self.log(f"  Command array:", self.BLUE)
        for i, elem in enumerate(cmd):
            # Mask passwords
            display_elem = "***MASKED***" if i > 0 and cmd[i - 1] == "-p" else elem
            self.log(f"    [{i}] {display_elem}", self.BLUE)
        # Create full command string with masked password
        cmd_str_parts = []
        for i, elem in enumerate(cmd):
            if i > 0 and cmd[i - 1] == "-p":
                cmd_str_parts.append("***MASKED***")
            else:
                cmd_str_parts.append(elem)
        self.log(f"  Full command: {' '.join(cmd_str_parts)}", self.BLUE)
        self.log(f"{'-'*80}\n", self.BLUE)

    def log_response(self, response_type: str, content: str, success: bool = True):
        """Log a response from target system."""
        color = self.GREEN if success else self.RED
        self.log(f"\n📨 RESPONSE: {response_type}", color + self.BOLD)
        self.log(f"{'='*80}", color)
        for line in content.split("\n")[:50]:  # Limit to first 50 lines
            if line.strip():
                self.log(f"  {line}", self.MAGENTA)
        self.log(f"{'='*80}\n", color)

    def log_result(self, result, label: str = "RESULT"):
        """Log subprocess result details with color coding."""
        success = result.returncode == 0
        color = self.GREEN if success else self.RED

        self.log(f"\n{color}{'-'*80}{self.RESET}")
        self.log(f"📊 {label}", color + self.BOLD)
        self.log(f"  Return code: {result.returncode} {'✓' if success else '✗'}", color)
        self.log(f"  STDOUT length: {len(result.stdout)} bytes", color)
        self.log(f"  STDERR length: {len(result.stderr)} bytes", color)

        if result.stdout:
            self.log(f"\n  STDOUT OUTPUT:", self.GREEN + self.BOLD)
            self.log(f"  {'-'*76}", self.GREEN)
            for line in result.stdout.split("\n")[:100]:  # First 100 lines
                if line.strip():
                    self.log(f"  {line}", self.MAGENTA)
            if len(result.stdout.split("\n")) > 100:
                self.log(
                    f"  ... ({len(result.stdout.split('\n')) - 100} more lines)",
                    self.GREEN,
                )
            self.log(f"  {'-'*76}", self.GREEN)

        if result.stderr:
            self.log(f"\n  STDERR OUTPUT:", self.RED + self.BOLD)
            self.log(f"  {'-'*76}", self.RED)
            for line in result.stderr.split("\n"):
                if line.strip():
                    self.log(f"  {line}", self.RED)
            self.log(f"  {'-'*76}", self.RED)

        self.log(f"{'-'*80}\n", color)

    def log_error(self, error_msg: str, exception: Exception = None):
        """Log an error with details."""
        self.log(f"\n❌ ERROR: {error_msg}", self.RED + self.BOLD)
        if exception:
            self.log(f"Exception type: {type(exception).__name__}", self.RED)
            self.log(f"Exception message: {str(exception)}", self.RED)

    def log_warning(self, warning_msg: str):
        """Log a warning."""
        self.log(f"⚠️  WARNING: {warning_msg}", self.YELLOW)

    def log_data(self, data_type: str, data: dict, max_items: int = 10):
        """Log data structures."""
        self.log(f"\n📦 DATA: {data_type}", self.MAGENTA + self.BOLD)
        self.log(f"  Type: {type(data).__name__}", self.MAGENTA)
        self.log(f"  Size: {len(data)} items", self.MAGENTA)
        if isinstance(data, dict):
            for i, (key, value) in enumerate(list(data.items())[:max_items]):
                self.log(f"  [{key}] = {str(value)[:100]}", self.MAGENTA)
            if len(data) > max_items:
                self.log(f"  ... ({len(data) - max_items} more items)", self.MAGENTA)
        self.log("")


class ExternalPortMapper:
    """
    Collect port mapping data externally using SSH and API calls.

    This approach doesn't require running vnetmap.py from inside the cluster.
    Instead, it collects data via:
    1. VAST API - node IPs and hostnames
    2. clush via SSH - node interface MACs (one connection)
    3. Switch SSH - MAC address tables
    """

    def __init__(
        self,
        cluster_ip: str,
        api_user: str,
        api_password: str,
        cnode_ip: str,
        node_user: str,
        node_password: str,
        switch_ips: List[str],
        switch_user: str,
        switch_password: str,
    ):
        """
        Initialize external port mapper.

        Args:
            cluster_ip: VAST cluster management VIP
            api_user: API username (typically 'support')
            api_password: API password
            cnode_ip: IP of any CNode for clush access
            node_user: SSH username for nodes (typically 'vastdata')
            node_password: SSH password for nodes
            switch_ips: List of switch management IPs
            switch_user: SSH username for switches (typically 'cumulus')
            switch_password: SSH password for switches
        """
        self.cluster_ip = cluster_ip
        self.api_user = api_user
        self.api_password = api_password
        self.cnode_ip = cnode_ip
        self.node_user = node_user
        self.node_password = node_password
        self.switch_ips = switch_ips
        self.switch_user = switch_user
        self.switch_password = switch_password
        self.logger = logging.getLogger(__name__)

        # Initialize verbose logger
        self.vlog = VerboseLogger()
        self.vlog.log(f"ExternalPortMapper initialized")
        self.vlog.log(f"  Cluster IP: {cluster_ip}")
        self.vlog.log(f"  CNode IP: {cnode_ip}")
        self.vlog.log(f"  Node user: {node_user}")
        self.vlog.log(f"  Switch IPs: {switch_ips}")
        self.vlog.log(f"  Switch user: {switch_user}")
        print(f"\n✅ Verbose logging enabled: {self.vlog.log_file}\n")

        # Setup SSH known_hosts file in workspace (writable location)
        self.ssh_dir = Path(".ssh_workspace")
        self.ssh_dir.mkdir(exist_ok=True)
        self.known_hosts_file = self.ssh_dir / "known_hosts"
        self.known_hosts_file.touch(exist_ok=True)
        self.vlog.log(f"SSH known_hosts file: {self.known_hosts_file}")
        print(f"✅ SSH known_hosts file created: {self.known_hosts_file}\n")

    def collect_port_mapping(self) -> Dict[str, Any]:
        """
        Collect complete port mapping data.

        Returns:
            Dict with port mapping data including:
            - node_macs: {node_ip: {interface: mac}}
            - switch_macs: {switch_ip: {mac: {port, vlan}}}
            - port_map: [{node_ip, interface, mac, switch_ip, port, network}]
            - cross_connections: List of detected issues
        """
        try:
            self.logger.info("Starting external port mapping collection")
            self.vlog.log_function_enter("collect_port_mapping")

            # Clear and recreate known_hosts for fresh host key generation
            self.vlog.log_operation("Clearing SSH known_hosts for fresh state")
            if self.known_hosts_file.exists():
                self.known_hosts_file.unlink()
            self.known_hosts_file.touch()
            self.known_hosts_file.chmod(0o600)
            self.vlog.log("SSH known_hosts cleared and recreated", self.vlog.GREEN)

            # Step 1: Collect node inventory via Basic Auth API
            node_inventory = self._collect_node_inventory_basic_auth()
            self.logger.info(
                f"Retrieved inventory for {len(node_inventory)} nodes via Basic Auth"
            )

            # Step 2: Collect hostname to data IP mapping via clush
            hostname_to_ip = self._collect_hostname_to_ip_mapping()
            self.logger.info(f"Mapped {len(hostname_to_ip)} hostnames to data IPs")

            # Step 3: Collect node MACs via clush
            node_macs = self._collect_node_macs_via_clush()
            self.logger.info(f"Collected MACs for {len(node_macs)} nodes")

            # Step 3: Collect switch MAC tables
            switch_macs = self._collect_switch_mac_tables()
            self.logger.info(f"Collected MAC tables from {len(switch_macs)} switches")

            # Step 4: Correlate node MACs with switch ports
            port_map = self._correlate_node_to_switch(
                node_inventory, hostname_to_ip, node_macs, switch_macs
            )
            self.logger.info(f"Generated {len(port_map)} port mappings")

            # Step 5: Collect IPL connections between switches
            ipl_connections = self._collect_ipl_connections()

            # Step 6: Detect cross-connections
            cross_connections = self._detect_cross_connections(port_map)

            return {
                "available": True,
                "node_macs": node_macs,
                "switch_macs": switch_macs,
                "port_map": port_map,
                "ipl_connections": ipl_connections,
                "cross_connections": cross_connections,
                "total_connections": len(port_map),
                "total_ipl_connections": len(ipl_connections),
                "total_ipl_ports": len(ipl_connections) * 2,
                "data_source": "External SSH collection (clush + switch CLI)",
            }

        except Exception as e:
            self.logger.error(f"Error collecting port mapping: {e}", exc_info=True)
            return {
                "available": False,
                "error": str(e),
                "port_map": [],
                "cross_connections": [],
            }

    def _collect_node_inventory_basic_auth(self) -> Dict[str, Dict[str, Any]]:
        """
        Collect node inventory using Basic Auth API (no token required).

        Uses /api/v7/vms/1/network_settings/ endpoint with Basic Auth.

        Returns:
            Dict mapping hostname to node info:
            {
                'se-az-arrow-cb2-cn-1': {
                    'id': 1,
                    'hostname': 'se-az-arrow-cb2-cn-1',
                    'mgmt_ip': '10.143.11.61',
                    'ipmi_ip': '10.143.11.62',
                    'box_vendor': 'supermicro_gen5_cbox',
                    'node_type': 'Cnode',
                    'box_name': 'cbox-S929986X4A20495'
                }
            }
        """
        try:
            import base64

            import requests

            self.logger.info("Collecting node inventory via Basic Auth API")

            # Create Basic Auth header
            credentials = f"{self.api_user}:{self.api_password}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {"Authorization": f"Basic {b64_credentials}"}

            # Disable SSL warnings
            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            # Get CNodes
            url = f"https://{self.cluster_ip}/api/v7/vms/1/network_settings/"
            response = requests.get(url, headers=headers, verify=False, timeout=30)

            if response.status_code != 200:
                raise Exception(
                    f"API request failed: HTTP {response.status_code} - {response.text}"
                )

            data = response.json()
            node_inventory = {}

            # Parse CNodes
            for box in data.get("data", {}).get("boxes", []):
                box_name = box.get("box_name", "")
                if box_name.startswith("cbox-") or box_name.startswith("dbox-"):
                    for host in box.get("hosts", []):
                        hostname = host.get("hostname", "Unknown")
                        node_inventory[hostname] = {
                            "id": host.get("id"),
                            "hostname": hostname,
                            "mgmt_ip": host.get("mgmt_ip"),
                            "ipmi_ip": host.get("ipmi_ip"),
                            "box_vendor": host.get("vast_install_info", {}).get(
                                "box_vendor", "Unknown"
                            ),
                            "node_type": host.get("vast_install_info", {}).get(
                                "node_type", "Unknown"
                            ),
                            "box_name": host.get("vast_install_info", {}).get(
                                "box_name", "Unknown"
                            ),
                        }

            self.logger.info(f"Collected inventory for {len(node_inventory)} nodes")
            return node_inventory

        except Exception as e:
            self.logger.error(f"Error collecting node inventory: {e}")
            return {}

    def _collect_hostname_to_ip_mapping(self) -> Dict[str, str]:
        """
        Collect hostname to data IP mapping via clush.

        Runs: clush -a hostname

        Returns:
            Dict mapping hostname to data IP:
            {'se-az-arrow-cb2-cn-1': '172.16.3.4'}
        """
        try:
            self.logger.info("Collecting hostname to IP mapping via clush")
            self.vlog.log_function_enter(
                "_collect_hostname_to_ip_mapping",
                cnode_ip=self.cnode_ip,
                node_user=self.node_user,
            )

            # SSH to CNode and run clush to get all node hostnames
            cmd = [
                "sshpass",
                "-p",
                self.node_password,
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                f"UserKnownHostsFile={self.known_hosts_file}",
                f"{self.node_user}@{self.cnode_ip}",
                "clush -a hostname",
            ]

            # Verbose logging
            self.vlog.log_operation("Collecting hostname to IP mapping via clush")
            self.vlog.log_command(cmd, "CLUSH HOSTNAME COMMAND")

            # Try with explicit environment to ensure PATH and other vars are available
            import os

            env = os.environ.copy()
            self.vlog.log(
                f"subprocess.run() parameters: capture_output=True, text=True, timeout=30, env={len(env)} vars",
                self.vlog.BLUE,
            )

            self.vlog.log("\nExecuting command...", self.vlog.BLUE)
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30, env=env
            )

            # Log result
            self.vlog.log_result(result, "CLUSH HOSTNAME RESULT")

            if result.returncode != 0:
                self.vlog.log_error(
                    "clush hostname command failed", Exception(result.stderr)
                )
                raise Exception(f"clush hostname command failed: {result.stderr}")

            # Parse output: "172.16.3.4: se-az-arrow-cb2-cn-1"
            self.vlog.log_operation("Parsing hostname to IP mapping from clush output")
            hostname_to_ip = {}
            for line in result.stdout.split("\n"):
                match = re.match(r"^([\d.]+):\s+(.+)$", line.strip())
                if match:
                    data_ip = match.group(1)
                    hostname = match.group(2).strip()
                    hostname_to_ip[hostname] = data_ip
                    self.logger.debug(f"Mapped {hostname} → {data_ip}")
                    self.vlog.log(
                        f"  Mapped: {hostname} → {data_ip}", self.vlog.MAGENTA
                    )

            self.vlog.log_data("hostname_to_ip", hostname_to_ip)
            self.vlog.log_function_exit(
                "_collect_hostname_to_ip_mapping",
                f"Collected {len(hostname_to_ip)} mappings",
            )
            return hostname_to_ip

        except Exception as e:
            self.logger.error(f"Error collecting hostname to IP mapping: {e}")
            self.vlog.log_error("Failed to collect hostname to IP mapping", e)
            self.vlog.log_function_exit("_collect_hostname_to_ip_mapping", "FAILED")
            return {}

    def _collect_node_macs_via_clush(self) -> Dict[str, Dict[str, str]]:
        """
        Collect MAC addresses from all nodes using clush.

        Uses a single SSH connection to a CNode to run:
        clush -a ip link show

        Returns:
            Dict mapping node IPs to {interface: mac}
            Example: {'172.16.3.4': {'enp129s0f0': 'c4:70:bd:fa:45:0a'}}
        """
        try:
            self.logger.info(f"Collecting node MACs via clush from {self.cnode_ip}")

            # SSH to CNode and run clush to get all node interfaces
            cmd = [
                "sshpass",
                "-p",
                self.node_password,
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                f"UserKnownHostsFile={self.known_hosts_file}",
                f"{self.node_user}@{self.cnode_ip}",
                "clush -a 'ip link show'",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode != 0:
                raise Exception(f"clush command failed: {result.stderr}")

            # Parse clush output
            return self._parse_clush_output(result.stdout)

        except Exception as e:
            self.logger.error(f"Error collecting node MACs via clush: {e}")
            raise

    def _parse_clush_output(self, output: str) -> Dict[str, Dict[str, str]]:
        """
        Parse clush output to extract node IPs, interfaces, and MACs.

        Format:
        172.16.3.4: 5: enp129s0f0: <...> mtu 9000 ...
        172.16.3.4:     link/ether c4:70:bd:fa:45:0a brd ff:ff:ff:ff:ff:ff

        Returns:
            Dict mapping node IPs to {interface: mac}
        """
        node_macs = {}
        current_node_ip = None
        current_interface = None

        for line in output.split("\n"):
            # Match node IP and interface line
            # Format: 172.16.3.4: 5: enp129s0f0: <...>
            iface_match = re.match(r"^([\d.]+):\s+\d+:\s+([a-z0-9]+):", line)
            if iface_match:
                current_node_ip = iface_match.group(1)
                current_interface = iface_match.group(2)

                if current_node_ip not in node_macs:
                    node_macs[current_node_ip] = {}
                continue

            # Match MAC address line
            # Format: 172.16.3.4:     link/ether c4:70:bd:fa:45:0a
            mac_match = re.match(r"^[\d.]+:\s+link/ether\s+([0-9a-f:]{17})", line)
            if mac_match and current_node_ip and current_interface:
                mac = mac_match.group(1)

                # Only capture physical data interfaces (enp*, not bond*, vlan*, etc.)
                if current_interface.startswith("enp") and not "@" in line:
                    node_macs[current_node_ip][current_interface] = mac
                    self.logger.debug(
                        f"Found MAC: {current_node_ip} {current_interface} = {mac}"
                    )

        return node_macs

    def _collect_switch_mac_tables(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Collect MAC address tables from all switches.

        Returns:
            Dict mapping switch IPs to {mac: {port, vlan}}
            Example: {'10.143.11.153': {'c4:70:bd:fa:45:0a': {port: 'swp20', vlan: 1}}}
        """
        switch_macs = {}

        for switch_ip in self.switch_ips:
            try:
                self.logger.info(f"Collecting MAC table from switch {switch_ip}")

                # SSH to switch and get MAC table
                # Using Cumulus Linux command (adjust for other vendors)
                cmd = [
                    "sshpass",
                    "-p",
                    self.switch_password,
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    f"UserKnownHostsFile={self.known_hosts_file}",
                    f"{self.switch_user}@{switch_ip}",
                    "nv show bridge domain br_default mac-table",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    switch_macs[switch_ip] = self._parse_cumulus_mac_table(
                        result.stdout
                    )
                    self.logger.info(
                        f"Collected {len(switch_macs[switch_ip])} MACs from {switch_ip}"
                    )
                else:
                    self.logger.warning(
                        f"Failed to get MAC table from {switch_ip}: {result.stderr}"
                    )

            except Exception as e:
                self.logger.error(f"Error collecting MAC table from {switch_ip}: {e}")

        return switch_macs

    def _parse_cumulus_mac_table(self, output: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse Cumulus Linux MAC table output.

        Modern Cumulus format:
        entry-id  MAC address        vlan  interface   remote-dst  src-vni  entry-type  last-update        age
        1         7c:8c:09:eb:ec:51  69    swp1                                         0:00:58            0:03:39

        Returns:
            Dict mapping MACs to {port, vlan, entry_type}
        """
        mac_table = {}

        for line in output.split("\n"):
            # Skip header and separator lines
            if line.startswith("entry-id") or line.startswith("---"):
                continue

            # Match MAC table entries (modern Cumulus format with spaces)
            # Format: entry-id  MAC  vlan  interface  ...
            parts = line.split()
            if len(parts) >= 4:
                try:
                    # Second column is MAC, third is VLAN, fourth is interface
                    entry_id = parts[0]
                    mac = parts[1]
                    vlan = parts[2]
                    interface = parts[3]

                    # Validate MAC format
                    if re.match(r"^[0-9a-f:]{17}$", mac):
                        # Only include swp* interfaces (exclude permanent entries without swp)
                        if interface.startswith("swp"):
                            mac_table[mac] = {
                                "port": interface,
                                "vlan": vlan,
                                "entry_id": entry_id,
                            }
                except (IndexError, ValueError):
                    continue

        return mac_table

    def _collect_ipl_connections(self) -> List[Dict[str, Any]]:
        """
        Collect IPL (Inter-Peer Link) connections between switches using LLDP.

        Uses 'nv show interface' for Cumulus switches or 'show lldp remote' for Onyx.
        Deduplicates connections so each physical link is counted once.

        Returns:
            List of unique IPL connections with format:
            [{
                'switch1_ip': '10.143.11.153',
                'switch1_port': 'swp29',
                'switch2_ip': '10.143.11.154',
                'switch2_port': 'swp29',
                'port_number': 29
            }]
        """
        ipl_connections = []
        seen_connections = set()

        for switch_ip in self.switch_ips:
            try:
                self.logger.info(f"Collecting IPL connections from switch {switch_ip}")

                # Try Cumulus command first
                cmd = [
                    "sshpass",
                    "-p",
                    self.switch_password,
                    "ssh",
                    "-o",
                    "StrictHostKeyChecking=no",
                    "-o",
                    f"UserKnownHostsFile={self.known_hosts_file}",
                    f"{self.switch_user}@{switch_ip}",
                    "nv show interface --output json",
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                if result.returncode == 0:
                    # Parse Cumulus output
                    ipl_data = self._parse_cumulus_lldp_for_ipl(
                        result.stdout, switch_ip
                    )

                    # Deduplicate: only add if we haven't seen the reverse connection
                    for conn in ipl_data:
                        # Create a normalized key (always put lower IP first)
                        sw1_ip = conn["switch1_ip"]
                        sw2_ip = conn["switch2_ip"]
                        port = conn["port_number"]

                        key = tuple(sorted([sw1_ip, sw2_ip]) + [port])

                        if key not in seen_connections:
                            seen_connections.add(key)
                            ipl_connections.append(conn)
                            self.logger.info(
                                f"Found IPL: {conn['switch1_port']} ↔ {conn['switch2_port']}"
                            )
                else:
                    self.logger.warning(
                        f"Failed to get interface data from {switch_ip}: {result.stderr}"
                    )

            except Exception as e:
                self.logger.error(f"Error collecting IPL from {switch_ip}: {e}")

        self.logger.info(
            f"Collected {len(ipl_connections)} unique IPL connections "
            f"({len(ipl_connections) * 2} total ports)"
        )
        return ipl_connections

    def _parse_cumulus_lldp_for_ipl(
        self, json_output: str, current_switch_ip: str
    ) -> List[Dict[str, Any]]:
        """
        Parse Cumulus 'nv show interface' JSON output to find IPL connections.

        Args:
            json_output: JSON output from 'nv show interface'
            current_switch_ip: IP of the switch we're querying

        Returns:
            List of IPL connections found on this switch
        """
        import json

        ipl_connections = []

        try:
            data = json.loads(json_output)

            # Look for swp29-32 (typical IPL ports)
            for port_name in ["swp29", "swp30", "swp31", "swp32"]:
                if port_name in data:
                    port_data = data[port_name]

                    # Check if this port has LLDP neighbor
                    if "lldp" in port_data and port_data["lldp"]:
                        lldp_data = port_data["lldp"]

                        # Look for neighbor information
                        for neighbor_entry in lldp_data:
                            if isinstance(neighbor_entry, dict):
                                neighbor_port = neighbor_entry.get("port", {}).get(
                                    "description", ""
                                )

                                # If neighbor port matches (e.g., swp29 ↔ swp29)
                                # this is likely an IPL connection
                                if neighbor_port == port_name:
                                    # Determine remote switch IP
                                    remote_switch_ip = self._get_other_switch_ip(
                                        current_switch_ip
                                    )

                                    port_num = int(port_name.replace("swp", ""))

                                    ipl_connections.append(
                                        {
                                            "switch1_ip": current_switch_ip,
                                            "switch1_port": port_name,
                                            "switch2_ip": remote_switch_ip,
                                            "switch2_port": neighbor_port,
                                            "port_number": port_num,
                                        }
                                    )

        except json.JSONDecodeError:
            self.logger.warning("Failed to parse JSON from nv show interface")
        except Exception as e:
            self.logger.error(f"Error parsing LLDP data: {e}")

        return ipl_connections

    def _get_other_switch_ip(self, current_switch_ip: str) -> str:
        """Get the IP of the other switch in the pair."""
        for switch_ip in self.switch_ips:
            if switch_ip != current_switch_ip:
                return switch_ip
        return "Unknown"

    def _correlate_node_to_switch(
        self,
        node_inventory: Dict[str, Dict[str, Any]],
        hostname_to_ip: Dict[str, str],
        node_macs: Dict[str, Dict[str, str]],
        switch_macs: Dict[str, Dict[str, Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """
        Correlate node MACs with switch ports using hostname-based mapping.

        Args:
            node_inventory: {hostname: {mgmt_ip, node_type, box_vendor, ...}}
            hostname_to_ip: {hostname: data_ip}
            node_macs: {data_ip: {interface: mac}}
            switch_macs: {switch_ip: {mac: {port, vlan}}}

        Returns:
            List of port mappings with node and switch details
        """
        port_map = []

        # Determine switch assignments (Switch 1 = Network A, Switch 2 = Network B)
        sorted_switches = sorted(self.switch_ips)
        switch_1 = sorted_switches[0] if len(sorted_switches) > 0 else None
        switch_2 = sorted_switches[1] if len(sorted_switches) > 1 else None

        self.logger.info(
            f"Switch assignments: Switch-1 (Network A) = {switch_1}, "
            f"Switch-2 (Network B) = {switch_2}"
        )

        # Build reverse mapping: data_ip -> hostname
        ip_to_hostname = {ip: hostname for hostname, ip in hostname_to_ip.items()}

        # Correlate each node MAC with switch ports
        for data_ip, interfaces in node_macs.items():
            # Find hostname for this data IP
            hostname = ip_to_hostname.get(data_ip)
            if not hostname:
                self.logger.warning(f"No hostname found for data IP {data_ip}")
                continue

            # Get node info from inventory
            node_info = node_inventory.get(hostname)
            if not node_info:
                self.logger.warning(f"No inventory found for hostname {hostname}")
                continue

            for interface, mac in interfaces.items():
                # Find this MAC in switch tables
                for switch_ip, mac_table in switch_macs.items():
                    if mac in mac_table:
                        switch_entry = mac_table[mac]

                        # Determine network (A or B) based on WHICH SWITCH
                        # the MAC is found on. This is the correct way to
                        # determine network assignment:
                        # - Switch 1 (lower IP) = Network A
                        # - Switch 2 (higher IP) = Network B
                        #
                        # The interface name (f0 vs f1) tells us which
                        # physical port on the node, but the NETWORK is
                        # determined by which switch it connects to.
                        if switch_ip == switch_1:
                            network = "A"
                        elif switch_ip == switch_2:
                            network = "B"
                        else:
                            # Fallback to interface-based detection
                            # if switch mapping fails
                            network = "A" if interface.endswith("f0") else "B"
                            self.logger.warning(
                                f"Unknown switch {switch_ip}, using "
                                f"interface-based network detection"
                            )

                        port_map.append(
                            {
                                "node_ip": data_ip,
                                "node_hostname": hostname,
                                "node_type": node_info.get("node_type", "Unknown"),
                                "mgmt_ip": node_info.get("mgmt_ip"),
                                "box_vendor": node_info.get("box_vendor"),
                                "box_name": node_info.get("box_name"),
                                "interface": interface,
                                "mac": mac,
                                "switch_ip": switch_ip,
                                "port": switch_entry["port"],
                                "vlan": switch_entry["vlan"],
                                "network": network,
                            }
                        )

        return port_map

    def _detect_cross_connections(
        self, port_map: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detect cross-connection issues.

        Expected pattern:
        - Switch-1 (first IP) → Network A connections
        - Switch-2 (second IP) → Network B connections

        Returns:
            List of cross-connection warnings
        """
        cross_connections = []

        # Determine which switch is Switch-1 vs Switch-2
        sorted_switches = sorted(self.switch_ips)
        switch_1 = sorted_switches[0] if len(sorted_switches) > 0 else None
        switch_2 = sorted_switches[1] if len(sorted_switches) > 1 else None

        for conn in port_map:
            switch_ip = conn["switch_ip"]
            network = conn["network"]

            # Expected network based on switch
            if switch_ip == switch_1:
                expected_network = "A"
            elif switch_ip == switch_2:
                expected_network = "B"
            else:
                expected_network = "Unknown"

            # Check for mismatch
            if network != expected_network:
                cross_connections.append(
                    {
                        "node": conn["node_hostname"],
                        "interface": conn["interface"],
                        "switch_ip": switch_ip,
                        "port": conn["port"],
                        "actual_network": network,
                        "expected_network": expected_network,
                    }
                )

        return cross_connections
