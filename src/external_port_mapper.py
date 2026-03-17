"""
External Port Mapper

Collects port mapping data from outside the cluster using:
- VAST REST API for node inventory
- SSH to CNode with clush to get all node MACs
- SSH to switches to get MAC address tables

REQUIRED CREDENTIALS:
- API: support/<PASSWORD> (support user with viewer role)
- Nodes: vastdata/vastdata (default node credentials)
- Switches (Cumulus): cumulus/Vastdata1! (Cumulus Linux default with VAST password)
- Switches (Onyx): admin/admin (Mellanox Onyx default credentials)

SUPPORTED SWITCH OPERATING SYSTEMS:
- Cumulus Linux (auto-detected)
- Mellanox Onyx (auto-detected)
"""

import logging
import os
import platform
import re
import shutil
import subprocess
from typing import Any, Dict, List, Tuple
from datetime import datetime
from pathlib import Path

from utils.ssh_adapter import run_ssh_command, run_interactive_ssh

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"


def _safe_str(s) -> str:
    """Return string safe for logging on Windows (avoids charmap encode errors)."""
    try:
        t = str(s)
        return t.encode("ascii", errors="replace").decode("ascii")
    except Exception:
        return "<encoding error>"


def _subprocess_env() -> dict:
    """Return a subprocess environment with PATH augmented for bundled apps.

    PyInstaller bundles strip the parent shell PATH. Homebrew tools like
    ``sshpass`` live in /opt/homebrew/bin (Apple Silicon) or /usr/local/bin
    (Intel) and must be reachable.
    """
    env = os.environ.copy()
    extra = ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
    existing = env.get("PATH", "")
    for p in extra:
        if p not in existing:
            existing = f"{p}:{existing}"
    env["PATH"] = existing
    return env


def _has_sshpass() -> bool:
    """Check whether sshpass is available on PATH (with augmented env)."""
    env = _subprocess_env()
    return shutil.which("sshpass", path=env.get("PATH")) is not None


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
            from utils import get_data_dir

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = get_data_dir() / "logs"
            log_file = str(log_dir / f"external_port_mapper_verbose_{timestamp}.log")

        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Clear existing log (UTF-8 so Windows doesn't raise charmap on Unicode output)
        with open(self.log_file, "w", encoding="utf-8") as f:
            f.write(f"{self.BOLD}{'='*80}{self.RESET}\n")
            f.write(f"{self.BOLD}{self.CYAN}EXTERNAL PORT MAPPER VERBOSE LOG{self.RESET}\n")
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
        with open(self.log_file, "a", encoding="utf-8") as f:
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

    def _safe_log_str(self, s: str) -> str:
        """Return string safe for logging on Windows (cp1252 console/file)."""
        if not s:
            return s
        try:
            return s.encode("utf-8", errors="replace").decode("utf-8")
        except Exception:
            return s.encode("ascii", errors="replace").decode("ascii")

    def log_result(self, result, label: str = "RESULT"):
        """Log subprocess result details with color coding."""
        success = result.returncode == 0
        color = self.GREEN if success else self.RED
        stdout_safe = (result.stdout or "").encode("ascii", errors="replace").decode("ascii")
        stderr_safe = (result.stderr or "").encode("ascii", errors="replace").decode("ascii")

        self.log(f"\n{color}{'-'*80}{self.RESET}")
        self.log(f"📊 {label}", color + self.BOLD)
        self.log(f"  Return code: {result.returncode} {'✓' if success else '✗'}", color)
        self.log(f"  STDOUT length: {len(result.stdout or '')} bytes", color)
        self.log(f"  STDERR length: {len(result.stderr or '')} bytes", color)

        if stdout_safe:
            self.log(f"\n  STDOUT OUTPUT:", self.GREEN + self.BOLD)
            self.log(f"  {'-'*76}", self.GREEN)
            for line in stdout_safe.split("\n")[:100]:  # First 100 lines
                if line.strip():
                    self.log(f"  {line}", self.MAGENTA)
            if len(stdout_safe.split("\n")) > 100:
                self.log(
                    f"  ... ({len(stdout_safe.split(chr(10))) - 100} more lines)",
                    self.GREEN,
                )
            self.log(f"  {'-'*76}", self.GREEN)

        if stderr_safe:
            self.log(f"\n  STDERR OUTPUT:", self.RED + self.BOLD)
            self.log(f"  {'-'*76}", self.RED)
            for line in stderr_safe.split("\n"):
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
            switch_user: SSH username for switches (typically 'cumulus' or 'admin')
            switch_password: SSH password for switches (typically 'Vastdata1!' or 'admin')
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
        from utils import get_data_dir

        self.ssh_dir = get_data_dir() / ".ssh_workspace"
        self.ssh_dir.mkdir(exist_ok=True)
        self.known_hosts_file = self.ssh_dir / "known_hosts"
        self.known_hosts_file.touch(exist_ok=True)
        self.vlog.log(f"SSH known_hosts file: {self.known_hosts_file}")
        print(f"✅ SSH known_hosts file created: {self.known_hosts_file}\n")

        # Detect switch OS types (Cumulus vs Onyx) and store credentials
        self.switch_os_map: dict[str, str] = {}  # {switch_ip: 'cumulus' or 'onyx'}
        self.switch_credentials: dict[str, dict[str, str]] = {}  # {switch_ip: {'user': '', 'password': ''}}

    def _detect_switch_os(self, switch_ip: str) -> Tuple[str, str, str]:
        """
        Detect switch operating system (Cumulus vs Onyx) and determine credentials.

        Tries both credential sets and identifies the OS based on successful authentication
        and command responses. Uses cross-platform SSH adapter (paramiko on Windows,
        sshpass/subprocess on macOS/Linux).

        Args:
            switch_ip: Switch management IP address

        Returns:
            Tuple of (os_type, username, password) where os_type is 'cumulus' or 'onyx'

        Raises:
            Exception if neither credential set works
        """
        self.vlog.log_operation(f"Detecting OS type for switch {switch_ip}")

        # Try Cumulus credentials first (cumulus/Vastdata1!)
        credentials_to_try = [
            ("cumulus", self.switch_password, "cumulus"),  # (user, pass, os_name)
            ("admin", "admin", "onyx"),  # Onyx default credentials
        ]

        # If user provided admin as switch_user, try onyx first
        if self.switch_user == "admin":
            credentials_to_try.reverse()

        for user, password, expected_os in credentials_to_try:
            try:
                self.vlog.log(f"Trying {expected_os} credentials ({user}/***) on {switch_ip}")

                # Try to run a simple command to test authentication and identify OS
                # Cumulus: "nv show system" will work
                # Onyx: "show version" will work
                test_cmd = "nv show system" if expected_os == "cumulus" else "show version"

                # Use cross-platform SSH adapter
                self.vlog.log(f"Running SSH command via adapter: {test_cmd}")

                # For Onyx switches, use interactive SSH (they require PTY)
                if expected_os == "onyx":
                    returncode, stdout, stderr = run_interactive_ssh(switch_ip, user, password, test_cmd, timeout=15)
                else:
                    returncode, stdout, stderr = run_ssh_command(switch_ip, user, password, test_cmd, timeout=15)

                self.vlog.log(f"SSH result: rc={returncode}, stdout_len={len(stdout)}, stderr_len={len(stderr)}")

                # Check both stdout and stderr for OS identification
                output_lower = (stdout + stderr).lower()

                if expected_os == "cumulus":
                    # Cumulus will have specific output format or "cumulus" in response
                    if returncode == 0 and ("cumulus" in output_lower or "hostname" in output_lower):
                        self.vlog.log(
                            f"✓ Detected Cumulus Linux on {switch_ip}",
                            self.vlog.GREEN,
                        )
                        self.logger.info(f"Switch {switch_ip}: Cumulus Linux detected")
                        return ("cumulus", user, password)
                elif expected_os == "onyx":
                    # Onyx detection: Success if we see Onyx/Mellanox identifiers
                    # OR if we get the "UNIX shell commands cannot be executed" message
                    # (which means auth succeeded but account has restricted shell access)
                    onyx_indicators = [
                        "onyx" in output_lower,
                        "mellanox" in output_lower,
                        "product name" in output_lower,
                        "unix shell commands cannot be executed" in output_lower,
                    ]

                    if any(onyx_indicators):
                        self.vlog.log(
                            f"✓ Detected Mellanox Onyx on {switch_ip}",
                            self.vlog.GREEN,
                        )
                        self.logger.info(f"Switch {switch_ip}: Mellanox Onyx detected")
                        return ("onyx", user, password)

            except Exception as e:
                self.vlog.log_warning(f"Error testing {expected_os} on {switch_ip}: {e}")
                continue

        # If we get here, neither credential set worked
        error_msg = f"Could not detect OS type for switch {switch_ip} - authentication failed with both credential sets"
        self.vlog.log_error(error_msg)
        raise Exception(error_msg)

    def _run_onyx_interactive_command(
        self,
        switch_ip: str,
        username: str,
        password: str,
        command: str,
        timeout: int = 30,
    ) -> Tuple[int, str, str]:
        """
        Run a command on an Onyx switch using interactive SSH (pexpect).

        Onyx switches with 'admin' user account cannot execute commands non-interactively.
        This method uses pexpect to:
        1. SSH to the switch
        2. Wait for password prompt
        3. Enter password
        4. Wait for CLI prompt
        5. Send command
        6. Capture output
        7. Exit cleanly

        Args:
            switch_ip: IP address of the switch
            username: SSH username (typically 'admin')
            password: SSH password (typically 'admin')
            command: CLI command to execute (e.g., 'show mac-address-table')
            timeout: Command timeout in seconds

        Returns:
            Tuple of (returncode, stdout, stderr)
            - returncode: 0 for success, non-zero for failure
            - stdout: Command output
            - stderr: Error output (if any)
        """
        try:
            import pexpect

            self.vlog.log_operation(f"Running interactive Onyx command on {switch_ip}: {command}")

            # Build SSH command
            ssh_cmd = (
                f"ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile={self.known_hosts_file} {username}@{switch_ip}"
            )

            self.vlog.log_command([ssh_cmd], "Interactive SSH (pexpect)")

            # Spawn SSH process
            child = pexpect.spawn(ssh_cmd, timeout=timeout, encoding="utf-8")

            # Enable logging to capture all interaction
            child.logfile_read = None  # We'll manually log instead

            # Wait for password prompt
            i = child.expect([r"Password:", r"password:", pexpect.TIMEOUT, pexpect.EOF])

            if i >= 2:  # Timeout or EOF
                error_msg = f"Failed to get password prompt: {child.before}"
                self.vlog.log(error_msg, self.vlog.RED)
                return (1, "", error_msg)

            # Send password
            child.sendline(password)

            # Wait for CLI prompt (Onyx format: "hostname [info] >")
            # Examples: "rack6-1 [r6u35Bonzo99: standby] >"
            i = child.expect([r"\[.*\]\s*>", pexpect.TIMEOUT, pexpect.EOF], timeout=15)

            if i != 0:  # Didn't get prompt
                error_msg = f"Failed to get CLI prompt: {child.before}"
                self.vlog.log(error_msg, self.vlog.RED)
                child.close()
                return (1, "", error_msg)

            # Send command
            child.sendline(command)

            # Wait for command completion (next prompt)
            i = child.expect([r"\[.*\]\s*>", pexpect.TIMEOUT, pexpect.EOF], timeout=timeout)

            if i != 0:  # Command didn't complete
                error_msg = f"Command timeout or connection lost: {child.before}"
                self.vlog.log(error_msg, self.vlog.RED)
                child.close()
                return (1, "", error_msg)

            # Capture output (everything before the final prompt)
            output = child.before

            # Clean up the output
            # Remove the echoed command line (first line)
            lines = output.split("\n")
            if lines and command in lines[0]:
                lines = lines[1:]
            output = "\n".join(lines).strip()

            # Exit cleanly
            child.sendline("exit")
            child.expect(pexpect.EOF, timeout=5)
            child.close()

            self.vlog.log_data("Onyx Command Output", {"lines": len(output.split("\n"))})
            self.vlog.log(f"✅ Command succeeded: {len(output)} chars", self.vlog.GREEN)

            return (0, output, "")

        except ImportError:
            error_msg = "pexpect library not installed. Run: pip install pexpect"
            self.logger.error(error_msg)
            return (1, "", error_msg)
        except Exception as e:
            error_msg = f"Interactive SSH error: {e}"
            self.vlog.log(error_msg, self.vlog.RED)
            self.logger.error(error_msg, exc_info=True)
            return (1, "", error_msg)

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

            # Step 0: Detect switch OS types and credentials
            self.logger.info("Detecting switch operating systems...")
            for switch_ip in self.switch_ips:
                os_type, user, password = self._detect_switch_os(switch_ip)
                self.switch_os_map[switch_ip] = os_type
                self.switch_credentials[switch_ip] = {
                    "user": user,
                    "password": password,
                }
                print(f"✅ Switch {switch_ip}: {os_type.upper()} detected (using {user} credentials)")

            # Step 1: Collect node inventory via Basic Auth API
            node_inventory = self._collect_node_inventory_basic_auth()
            self.logger.info(f"Retrieved inventory for {len(node_inventory)} nodes via Basic Auth")

            # Step 1.5: Detect EBox cluster and collect EBox mappings
            ebox_mapping = self._collect_ebox_mapping()
            is_ebox_cluster = len(ebox_mapping) > 0
            ebox_node_mapping = {}

            if is_ebox_cluster:
                self.logger.info(f"Detected EBox cluster with {len(ebox_mapping)} EBoxes")
                self.vlog.log(f"EBox cluster detected: {len(ebox_mapping)} EBoxes", self.vlog.GREEN)

                # Collect CNode/DNode to EBox mapping
                ebox_node_mapping = self._collect_ebox_node_mapping()
                self.logger.info(f"Collected {len(ebox_node_mapping)} EBox node mappings")

                # Enhance node_inventory with ebox_id
                for hostname, node_info in node_inventory.items():
                    # Find matching entry in ebox_node_mapping
                    if hostname in ebox_node_mapping:
                        node_info["ebox_id"] = ebox_node_mapping[hostname].get("ebox_id")
                        self.logger.debug(f"Added ebox_id {node_info['ebox_id']} to {hostname}")
            else:
                self.logger.info("Standard CBox/DBox cluster (no EBoxes detected)")

            # Step 2: Collect hostname to data IP mapping via clush
            hostname_to_ip = self._collect_hostname_to_ip_mapping()
            self.logger.info(f"Mapped {len(hostname_to_ip)} hostnames to data IPs")

            # Step 3: Collect node MACs via clush
            node_macs = self._collect_node_macs_via_clush()
            self.logger.info(f"Collected MACs for {len(node_macs)} nodes")

            # If no hostname or MAC data at all, cannot build port map
            if not hostname_to_ip and not node_macs:
                self.logger.warning("No hostname or MAC data from clush — port mapping unavailable")
                return {
                    "available": False,
                    "error": "No hostname or MAC data from clush (SSH or all nodes unreachable)",
                    "port_map": [],
                    "cross_connections": [],
                }

            # Diagnostic: Count CNodes vs DNodes by hostname pattern
            # Build reverse mapping for diagnostic
            ip_to_hostname_lookup = {ip: hostname for hostname, ip in hostname_to_ip.items()}
            cnode_count = sum(
                1
                for ip in node_macs.keys()
                if any(
                    "cnode" in hostname.lower() or "cn-" in hostname.lower()
                    for hostname in [ip_to_hostname_lookup.get(ip, "")]
                    if ip_to_hostname_lookup.get(ip)
                )
            )
            dnode_count = sum(
                1
                for ip in node_macs.keys()
                if any(
                    "dnode" in hostname.lower() or "dn-" in hostname.lower()
                    for hostname in [ip_to_hostname_lookup.get(ip, "")]
                    if ip_to_hostname_lookup.get(ip)
                )
            )
            self.logger.info(f"Node breakdown: {cnode_count} CNodes, {dnode_count} DNodes (by hostname pattern)")
            self.vlog.log(f"Node breakdown: {cnode_count} CNodes, {dnode_count} DNodes", self.vlog.CYAN)

            # Step 4: Collect switch MAC tables
            switch_macs = self._collect_switch_mac_tables()
            total_switch_macs = sum(len(mac_table) for mac_table in switch_macs.values())
            self.logger.info(f"Collected MAC tables from {len(switch_macs)} switches ({total_switch_macs} total MACs)")
            self.vlog.log(
                f"Switch MAC tables: {total_switch_macs} total MACs across {len(switch_macs)} switches", self.vlog.CYAN
            )

            # Step 5: Correlate node MACs with switch ports
            port_map = self._correlate_node_to_switch(
                node_inventory,
                hostname_to_ip,
                node_macs,
                switch_macs,
                is_ebox_cluster=is_ebox_cluster,
                ebox_mapping=ebox_mapping,
                ebox_node_mapping=ebox_node_mapping,
            )
            self.logger.info(f"Generated {len(port_map)} port mappings")

            # Diagnostic: Count connections by node type and network
            cnode_connections = sum(1 for conn in port_map if conn.get("node_type", "").lower() == "cnode")
            dnode_connections = sum(1 for conn in port_map if conn.get("node_type", "").lower() == "dnode")
            network_a_connections = sum(1 for conn in port_map if conn.get("network") == "A")
            network_b_connections = sum(1 for conn in port_map if conn.get("network") == "B")

            self.logger.info(
                f"Connection breakdown: {cnode_connections} CNode connections, {dnode_connections} DNode connections"
            )
            self.logger.info(f"Network breakdown: {network_a_connections} Network A, {network_b_connections} Network B")
            self.vlog.log(
                f"Port mapping summary: {cnode_connections} CNode, {dnode_connections} DNode connections",
                self.vlog.GREEN,
            )
            self.vlog.log(
                f"Network distribution: {network_a_connections} Net A, {network_b_connections} Net B", self.vlog.GREEN
            )

            # Step 5: Collect IPL connections between switches
            ipl_connections = self._collect_ipl_connections()

            # Step 6: Detect cross-connections
            cross_connections = self._detect_cross_connections(port_map)

            # Build diagnostic summary
            expected_nodes = len(node_inventory)
            partial = (expected_nodes > 0 and len(node_macs) < expected_nodes) or (
                expected_nodes > 0 and hostname_to_ip and len(hostname_to_ip) < expected_nodes
            )
            diagnostic_summary = {
                "nodes_collected": len(node_macs),
                "cnode_connections": cnode_connections,
                "dnode_connections": dnode_connections,
                "network_a_connections": network_a_connections,
                "network_b_connections": network_b_connections,
                "total_switch_macs": total_switch_macs,
                "switches_queried": len(switch_macs),
            }

            result = {
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
                "diagnostic_summary": diagnostic_summary,
                "is_ebox_cluster": is_ebox_cluster,
                "ebox_mapping": ebox_mapping,
                "ebox_node_mapping": ebox_node_mapping,
            }
            if partial:
                result["partial"] = True
                result["partial_reason"] = (
                    "One or more nodes unreachable via SSH/clush; port map includes only accessible nodes."
                )
                self.logger.info("Port mapping partial: %s", result["partial_reason"])
            return result

        except Exception as e:
            self.logger.error("Error collecting port mapping: %s", _safe_str(e), exc_info=True)
            return {
                "available": False,
                "error": _safe_str(e),
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
                raise Exception(f"API request failed: HTTP {response.status_code} - {response.text}")

            data = response.json()
            node_inventory = {}

            # Parse CNodes and DNodes from CBoxes, DBoxes, and EBoxes
            for box in data.get("data", {}).get("boxes", []):
                box_name = box.get("box_name", "")
                if box_name.startswith("cbox-") or box_name.startswith("dbox-") or box_name.startswith("ebox-"):
                    for host in box.get("hosts", []):
                        hostname = host.get("hostname", "Unknown")
                        node_inventory[hostname] = {
                            "id": host.get("id"),
                            "hostname": hostname,
                            "mgmt_ip": host.get("mgmt_ip"),
                            "ipmi_ip": host.get("ipmi_ip"),
                            "box_vendor": host.get("vast_install_info", {}).get("box_vendor", "Unknown"),
                            "node_type": host.get("vast_install_info", {}).get("node_type", "Unknown"),
                            "box_name": host.get("vast_install_info", {}).get("box_name", "Unknown"),
                        }

            self.logger.info(f"Collected inventory for {len(node_inventory)} nodes")
            return node_inventory

        except Exception as e:
            self.logger.error(f"Error collecting node inventory: {e}")
            return {}

    def _collect_ebox_mapping(self) -> Dict[str, int]:
        """
        Collect EBox GUID to numeric ID mapping from /api/v7/eboxes/.

        Returns:
            Dict mapping EBox GUID (box_name) to numeric ebox_id:
            {'ebox-8a1f17bc-49ed-4d94-8c6b-397b4b2df745': 1}
        """
        try:
            import base64
            import requests

            self.logger.info("Collecting EBox GUID to ID mapping")

            credentials = f"{self.api_user}:{self.api_password}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {"Authorization": f"Basic {b64_credentials}"}

            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            url = f"https://{self.cluster_ip}/api/v7/eboxes/"
            response = requests.get(url, headers=headers, verify=False, timeout=30)

            if response.status_code != 200:
                self.logger.warning(f"Failed to get EBox data: HTTP {response.status_code}")
                return {}

            data = response.json()
            ebox_mapping = {}

            # Handle both list and dict response formats
            eboxes = data if isinstance(data, list) else data.get("results", data.get("data", []))

            for ebox in eboxes:
                ebox_id = ebox.get("id")
                ebox_name = ebox.get("name", "")  # GUID format: ebox-8a1f17bc-...
                if ebox_id and ebox_name:
                    ebox_mapping[ebox_name] = ebox_id
                    self.logger.debug(f"Mapped EBox: {ebox_name} -> ID {ebox_id}")

            self.logger.info(f"Collected {len(ebox_mapping)} EBox GUID mappings")
            return ebox_mapping

        except Exception as e:
            self.logger.error(f"Error collecting EBox mapping: {e}")
            return {}

    def _collect_ebox_node_mapping(self) -> Dict[str, Dict[str, Any]]:
        """
        Collect CNode/DNode to EBox mapping from /api/v7/cnodes/ and /api/v7/dnodes/.

        Returns:
            Dict mapping hostname to node info including ebox_id:
            {
                'v3217en1': {
                    'ebox_id': 1,
                    'node_type': 'cnode',
                    'node_id': 3,
                    'position': None  # or 'virtual' for virtual DNodes
                }
            }
        """
        try:
            import base64
            import requests

            self.logger.info("Collecting CNode/DNode to EBox mapping")

            credentials = f"{self.api_user}:{self.api_password}"
            b64_credentials = base64.b64encode(credentials.encode()).decode()
            headers = {"Authorization": f"Basic {b64_credentials}"}

            import urllib3

            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

            node_mapping = {}

            # Collect CNodes
            url = f"https://{self.cluster_ip}/api/v7/cnodes/"
            response = requests.get(url, headers=headers, verify=False, timeout=30)

            if response.status_code == 200:
                data = response.json()
                cnodes = data if isinstance(data, list) else data.get("results", data.get("data", []))

                for cnode in cnodes:
                    hostname = cnode.get("hostname")
                    if hostname:
                        node_mapping[hostname] = {
                            "ebox_id": cnode.get("ebox_id"),
                            "cbox_id": cnode.get("cbox_id"),
                            "node_type": "cnode",
                            "node_id": cnode.get("id"),
                            "position": None,
                            "mgmt_ip": cnode.get("mgmt_ip"),
                            "name": cnode.get("name", hostname),  # e.g., cnode-128-21-4200
                        }
                        self.logger.debug(f"Mapped CNode: {cnode.get('name')} -> EBox {cnode.get('ebox_id')}")

            # Collect DNodes
            url = f"https://{self.cluster_ip}/api/v7/dnodes/"
            response = requests.get(url, headers=headers, verify=False, timeout=30)

            if response.status_code == 200:
                data = response.json()
                dnodes = data if isinstance(data, list) else data.get("results", data.get("data", []))

                for dnode in dnodes:
                    hostname = dnode.get("hostname")
                    if hostname:
                        # DNodes share hostname with CNode in EBox clusters
                        # Store separately with dnode_ prefix for lookup
                        dnode_key = f"dnode_{dnode.get('id')}_{hostname}"
                        node_mapping[dnode_key] = {
                            "ebox_id": dnode.get("ebox_id"),
                            "dbox_id": dnode.get("dbox_id"),
                            "node_type": "dnode",
                            "node_id": dnode.get("id"),
                            "position": dnode.get("position") or "primary",
                            "mgmt_ip": dnode.get("mgmt_ip"),
                            "hostname": hostname,
                            "name": dnode.get("name", f"dnode-{dnode.get('id')}"),  # e.g., dnode-128-21-4000
                        }
                        self.logger.debug(
                            f"Mapped DNode: {dnode.get('name')} -> EBox {dnode.get('ebox_id')} ({dnode.get('position') or 'primary'})"
                        )

            self.logger.info(f"Collected {len(node_mapping)} node-to-EBox mappings")
            return node_mapping

        except Exception as e:
            self.logger.error(f"Error collecting EBox node mapping: {e}")
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
            clush_cmd = "clush -a hostname"

            # Verbose logging
            self.vlog.log_operation("Collecting hostname to IP mapping via clush")
            self.vlog.log(f"SSH to {self.node_user}@{self.cnode_ip}: {clush_cmd}", self.vlog.BLUE)

            # Use cross-platform SSH adapter
            returncode, stdout, stderr = run_ssh_command(
                self.cnode_ip,
                self.node_user,
                self.node_password,
                clush_cmd,
                timeout=30,
            )

            # Log result
            self.vlog.log(
                f"SSH result: rc={returncode}, stdout_len={len(stdout)}, stderr_len={len(stderr)}",
                self.vlog.GREEN if returncode == 0 else self.vlog.RED,
            )

            # Parse output: "172.16.3.4: se-az-arrow-cb2-cn-1" (even if returncode != 0 for partial)
            self.vlog.log_operation("Parsing hostname to IP mapping from clush output")
            hostname_to_ip = {}
            for line in (stdout or "").split("\n"):
                match = re.match(r"^([\d.]+):\s+(.+)$", line.strip())
                if match:
                    data_ip = match.group(1)
                    hostname = match.group(2).strip()
                    hostname_to_ip[hostname] = data_ip
                    self.logger.debug(f"Mapped {hostname} → {data_ip}")
                    self.vlog.log(f"  Mapped: {hostname} → {data_ip}", self.vlog.MAGENTA)

            if returncode != 0:
                if hostname_to_ip:
                    self.logger.warning(
                        "clush hostname returned non-zero but got %d mappings — using partial data",
                        len(hostname_to_ip),
                    )
                    self.vlog.log_error("clush hostname partial", Exception(stderr))
                else:
                    self.vlog.log_error("clush hostname command failed", Exception(stderr))
                    raise Exception(f"clush hostname command failed: {stderr}")

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
        self.vlog.log_function_enter(
            "_collect_node_macs_via_clush",
            cnode_ip=self.cnode_ip,
            node_user=self.node_user,
        )

        try:
            self.logger.info(f"Collecting node MACs via clush from {self.cnode_ip}")
            self.vlog.log_operation(f"Collecting node MACs via clush from {self.cnode_ip}")

            # SSH to CNode and run clush to get all node interfaces
            # Use /sbin/ip as the 'ip' command may not be in PATH
            clush_cmd = "clush -a '/sbin/ip link show'"

            self.vlog.log(f"SSH to {self.node_user}@{self.cnode_ip}: {clush_cmd}", self.vlog.BLUE)

            # Use cross-platform SSH adapter
            returncode, stdout, stderr = run_ssh_command(
                self.cnode_ip,
                self.node_user,
                self.node_password,
                clush_cmd,
                timeout=60,
            )

            self.vlog.log(
                f"SSH result: rc={returncode}, stdout_len={len(stdout)}, stderr_len={len(stderr)}",
                self.vlog.GREEN if returncode == 0 else self.vlog.RED,
            )

            # Parse clush output (even when returncode != 0, to allow partial port map)
            self.vlog.log_operation("Parsing clush output for node MACs")
            node_macs = self._parse_clush_output(stdout or "")

            if returncode != 0:
                if node_macs:
                    self.logger.warning(
                        "clush ip link returned non-zero but got MACs for %d nodes — using partial data",
                        len(node_macs),
                    )
                    self.vlog.log(f"⚠ Partial node MACs ({len(node_macs)} nodes)", self.vlog.YELLOW)
                else:
                    error_msg = f"clush command failed: {stderr}"
                    self.logger.error(error_msg)
                    self.vlog.log(f"❌ {error_msg}", self.vlog.RED)
                    self.vlog.log_function_exit("_collect_node_macs_via_clush", "FAILED - non-zero return code")
                    raise Exception(error_msg)

            self.vlog.log_data("node_macs", node_macs)
            self.vlog.log_function_exit(
                "_collect_node_macs_via_clush",
                f"Collected MACs for {len(node_macs)} nodes",
            )
            return node_macs

        except Exception as e:
            self.logger.error(f"Error collecting node MACs via clush: {e}")
            self.vlog.log_error("Failed to collect node MACs via clush", e)
            self.vlog.log_function_exit("_collect_node_macs_via_clush", "FAILED")
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
        node_macs: dict[str, dict[str, str]] = {}
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
            # Skip vf (virtual function) lines
            if "vf " in line:
                continue

            mac_match = re.match(r"^[\d.]+:\s+link/ether\s+([0-9a-f:]{17})", line)
            if mac_match and current_node_ip and current_interface:
                mac = mac_match.group(1)

                # Capture physical data interfaces (enp*, ens*, eth*, not bond*, vlan*, eno*, etc.)
                # Skip management interfaces (enp0s25, eno1, eno2 typically used for IPMI/mgmt)
                # Only capture once per interface (first MAC = physical interface MAC)
                is_data_interface = (
                    (current_interface.startswith("enp") and not current_interface.startswith("enp0s25"))
                    or current_interface.startswith("ens")
                    or current_interface.startswith("eth")
                )
                is_mgmt_interface = current_interface.startswith("eno")  # eno1, eno2 are mgmt

                if is_data_interface and not is_mgmt_interface and current_interface not in node_macs[current_node_ip]:
                    # VLAN subinterfaces (e.g., enp3s0f0.69@enp3s0f0) contain "@"
                    # Extract the base interface name for VLAN subinterfaces
                    if "@" in current_interface:
                        # Format: enp3s0f0.69@enp3s0f0
                        # We want to store as "enp3s0f0" (base interface before the dot)
                        base_interface = current_interface.split(".")[0]
                    else:
                        base_interface = current_interface

                    # Only store if we haven't already captured this base interface
                    if base_interface not in node_macs[current_node_ip]:
                        node_macs[current_node_ip][base_interface] = mac
                        self.logger.debug(f"Found MAC: {current_node_ip} {base_interface} = {mac}")
                        self.vlog.log(
                            f"Found MAC: {current_node_ip} {base_interface} = {mac} (from {current_interface})"
                        )

        return node_macs

    def _collect_switch_mac_tables(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Collect MAC address tables from all switches.

        Supports both Cumulus Linux and Mellanox Onyx switches.
        Collects both general MAC table and VLAN 69-specific entries
        to ensure DNode Network B interfaces are captured.

        Returns:
            Dict mapping switch IPs to {mac: {port, vlan}}
            Example: {'10.143.11.153': {'c4:70:bd:fa:45:0a': {port: 'swp20', vlan: 1}}}
        """
        switch_macs = {}

        for switch_ip in self.switch_ips:
            try:
                self.logger.info(f"Collecting MAC table from switch {switch_ip}")
                self.vlog.log_operation(f"Collecting MAC table from {switch_ip}")

                # Get switch OS type and credentials
                os_type = self.switch_os_map.get(switch_ip, "cumulus")
                creds = self.switch_credentials.get(
                    switch_ip,
                    {"user": self.switch_user, "password": self.switch_password},
                )
                user = creds["user"]
                password = creds["password"]

                # Build command based on OS type
                if os_type == "cumulus":
                    mac_cmd = "nv show bridge domain br_default mac-table"
                    vlan69_cmd_str = "nv show bridge domain br_default vlan 69 mac-table"
                else:  # onyx
                    mac_cmd = "show mac-address-table"
                    vlan69_cmd_str = "show mac-address-table vlan 69"

                # Collect general MAC table
                # For Onyx, use interactive SSH; for Cumulus, use direct command
                if os_type == "onyx":
                    # Use interactive SSH for Onyx
                    returncode, stdout, stderr = self._run_onyx_interactive_command(
                        switch_ip, user, password, mac_cmd, timeout=30
                    )
                    result_returncode = returncode
                    result_stdout = stdout
                    result_stderr = stderr
                else:
                    # Use cross-platform SSH adapter for Cumulus
                    self.vlog.log(f"SSH to {user}@{switch_ip}: {mac_cmd}", self.vlog.BLUE)
                    result_returncode, result_stdout, result_stderr = run_ssh_command(
                        switch_ip, user, password, mac_cmd, timeout=30
                    )
                    self.vlog.log(
                        f"SSH result: rc={result_returncode}, stdout_len={len(result_stdout)}",
                        self.vlog.GREEN if result_returncode == 0 else self.vlog.RED,
                    )

                if result_returncode == 0:
                    # Parse based on OS type
                    if os_type == "cumulus":
                        switch_macs[switch_ip] = self._parse_cumulus_mac_table(result_stdout)
                    else:  # onyx
                        switch_macs[switch_ip] = self._parse_onyx_mac_table(result_stdout)

                    general_count = len(switch_macs[switch_ip])
                    self.logger.info(f"Collected {general_count} MACs from {switch_ip} ({os_type}, general table)")
                    self.vlog.log(f"General MAC table: {general_count} entries", self.vlog.GREEN)
                else:
                    self.logger.warning(f"Failed to get MAC table from {switch_ip}: {result_stderr}")
                    switch_macs[switch_ip] = {}

                # Additionally collect VLAN 69-specific MAC table for DNode Network B interfaces
                # This is important for Cumulus; may or may not work on Onyx
                self.vlog.log_operation(f"Collecting VLAN 69 MAC table from {switch_ip}")

                # For Onyx, use interactive SSH; for Cumulus, use direct command
                if os_type == "onyx":
                    # Use interactive SSH for Onyx
                    vlan69_returncode, vlan69_stdout, vlan69_stderr = self._run_onyx_interactive_command(
                        switch_ip, user, password, vlan69_cmd_str, timeout=30
                    )
                else:
                    # Use cross-platform SSH adapter for Cumulus
                    self.vlog.log(f"SSH to {user}@{switch_ip}: {vlan69_cmd_str}", self.vlog.BLUE)
                    vlan69_returncode, vlan69_stdout, vlan69_stderr = run_ssh_command(
                        switch_ip, user, password, vlan69_cmd_str, timeout=30
                    )
                    self.vlog.log(
                        f"VLAN 69 SSH result: rc={vlan69_returncode}, stdout_len={len(vlan69_stdout)}",
                        self.vlog.GREEN if vlan69_returncode == 0 else self.vlog.YELLOW,
                    )

                if vlan69_returncode == 0:
                    # Parse based on OS type
                    if os_type == "cumulus":
                        vlan69_macs = self._parse_cumulus_mac_table(vlan69_stdout)
                    else:  # onyx
                        vlan69_macs = self._parse_onyx_mac_table(vlan69_stdout)

                    # Merge VLAN 69 MACs into the main table
                    before_count = len(switch_macs[switch_ip])
                    for mac, info in vlan69_macs.items():
                        if mac not in switch_macs[switch_ip]:
                            switch_macs[switch_ip][mac] = info

                    added_count = len(switch_macs[switch_ip]) - before_count
                    if added_count > 0:
                        self.logger.info(f"Added {added_count} VLAN 69 MACs from {switch_ip}")
                        self.vlog.log(
                            f"VLAN 69 table: {len(vlan69_macs)} entries, {added_count} new",
                            self.vlog.GREEN,
                        )
                    else:
                        self.vlog.log(
                            f"VLAN 69 table: {len(vlan69_macs)} entries, 0 new (already in general table)",
                            self.vlog.YELLOW,
                        )
                else:
                    self.vlog.log(
                        f"VLAN 69 query failed or not supported: {vlan69_stderr}",
                        self.vlog.YELLOW,
                    )

                self.logger.info(f"Total: Collected {len(switch_macs[switch_ip])} MACs from {switch_ip}")

            except Exception as e:
                self.logger.error(f"Error collecting MAC table from {switch_ip}: {e}")
                self.vlog.log_error(f"MAC collection error for {switch_ip}", e)
                switch_macs[switch_ip] = {}

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

    def _parse_onyx_mac_table(self, output: str) -> Dict[str, Dict[str, Any]]:
        """
        Parse Mellanox Onyx MAC address table output.

        Onyx format from 'show mac-address-table':
        VID    MAC Address           Port              Type
        ----   -------------------   ---------------   -----------
        1      00:00:5E:00:01:01     Eth1/1            Dynamic
        69     7c:8c:09:eb:ec:51     Eth1/5            Dynamic

        Returns:
            Dict mapping MACs to {port, vlan}
        """
        mac_table = {}

        for line in output.split("\n"):
            # Skip header and separator lines
            if "VID" in line or "MAC Address" in line or "---" in line or not line.strip():
                continue

            # Split line into columns
            # Format: Vlan | Mac Address | Type | Port\Next Hop
            parts = line.split()
            if len(parts) >= 4:
                try:
                    vlan = parts[0]
                    mac = parts[1]
                    entry_type = parts[2]  # Dynamic/Static
                    port = parts[3]  # Port is the 4th column

                    # Validate MAC format (Onyx uses colon-separated hex)
                    # Format: 00:00:5E:00:01:01 or lowercase
                    mac_lower = mac.lower()
                    if re.match(r"^[0-9a-f:]{17}$", mac_lower):
                        # Include Eth* and Po* (Port Channel) interfaces
                        # Exclude CPU, management, etc.
                        if port.startswith("Eth") or port.startswith("Po"):
                            # Convert Onyx port naming to swp naming for consistency
                            if port.startswith("Eth") and "/" in port:
                                # Eth1/5 -> swp5
                                port_num = port.split("/")[1]
                                swp_port = f"swp{port_num}"
                            else:
                                # Keep Po1, Po2, etc. as-is for now
                                swp_port = port

                            mac_table[mac_lower] = {
                                "port": swp_port,
                                "vlan": vlan,
                                "original_port": port,  # Keep original for debugging
                            }
                except (IndexError, ValueError) as e:
                    self.logger.debug(f"Could not parse Onyx MAC table line: {line} - {e}")
                    continue

        return mac_table

    def _collect_ipl_connections(self) -> List[Dict[str, Any]]:
        """
        Collect IPL (Inter-Peer Link) connections between switches using LLDP.

        Supports both Cumulus Linux ('nv show interface') and Mellanox Onyx ('show lldp remote').
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

                # Get switch OS type and credentials
                os_type = self.switch_os_map.get(switch_ip, "cumulus")
                creds = self.switch_credentials.get(
                    switch_ip,
                    {"user": self.switch_user, "password": self.switch_password},
                )
                user = creds["user"]
                password = creds["password"]

                # Build command based on OS type
                if os_type == "cumulus":
                    lldp_cmd = "nv show interface --output json"
                else:  # onyx
                    lldp_cmd = "show lldp remote"

                # For Onyx, use interactive SSH; for Cumulus, use direct command
                if os_type == "onyx":
                    # Use interactive SSH for Onyx
                    returncode, stdout, stderr = self._run_onyx_interactive_command(
                        switch_ip, user, password, lldp_cmd, timeout=30
                    )
                else:
                    # Use cross-platform SSH adapter for Cumulus
                    self.vlog.log(f"SSH to {user}@{switch_ip}: {lldp_cmd}", self.vlog.BLUE)
                    returncode, stdout, stderr = run_ssh_command(switch_ip, user, password, lldp_cmd, timeout=30)
                    self.vlog.log(
                        f"IPL/LLDP SSH result: rc={returncode}, stdout_len={len(stdout)}",
                        self.vlog.GREEN if returncode == 0 else self.vlog.RED,
                    )

                if returncode == 0:
                    # Parse based on OS type
                    if os_type == "cumulus":
                        ipl_data = self._parse_cumulus_lldp_for_ipl(stdout, switch_ip)
                    else:  # onyx
                        ipl_data = self._parse_onyx_lldp_for_ipl(stdout, switch_ip)

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
                            self.logger.info(f"Found IPL: {conn['switch1_port']} ↔ {conn['switch2_port']}")
                else:
                    self.logger.warning(f"Failed to get LLDP data from {switch_ip}: {stderr}")

            except Exception as e:
                self.logger.error(f"Error collecting IPL from {switch_ip}: {e}")

        self.logger.info(
            f"Collected {len(ipl_connections)} unique IPL connections " f"({len(ipl_connections) * 2} total ports)"
        )
        return ipl_connections

    def _parse_cumulus_lldp_for_ipl(self, json_output: str, current_switch_ip: str) -> List[Dict[str, Any]]:
        """
        Parse Cumulus 'nv show interface' JSON output to find IPL connections.

        The JSON structure from 'nv show interface --output json' looks like:
        {
          "swp29": {
            "type": "swp",
            "link": {
              "state": {"up": {}}
            },
            "lldp": [{
              "hostname": "se-var-1-1",
              "port": [{"id": "swp29"}]
            }]
          }
        }

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

            self.vlog.log(f"Parsing interface data for IPL discovery on {current_switch_ip}")
            self.vlog.log_data("Interface JSON keys", {"ports": list(data.keys())[:10]})

            # Look for swp29-32 (typical IPL ports)
            for port_name in ["swp29", "swp30", "swp31", "swp32"]:
                if port_name not in data:
                    continue

                port_data = data[port_name]
                self.vlog.log(
                    f"Checking {port_name} for IPL: keys={list(port_data.keys()) if isinstance(port_data, dict) else 'not dict'}"
                )

                if not isinstance(port_data, dict):
                    continue

                # Check for LLDP neighbor data
                # Structure: lldp.neighbor.{hostname}.port.name
                lldp_data = port_data.get("lldp", {})
                if isinstance(lldp_data, dict):
                    neighbor_data = lldp_data.get("neighbor", {})
                    if isinstance(neighbor_data, dict):
                        # Iterate through all neighbors (usually just one)
                        for remote_hostname, neighbor_info in neighbor_data.items():
                            if not isinstance(neighbor_info, dict):
                                continue

                            # Get neighbor port name
                            port_info = neighbor_info.get("port", {})
                            neighbor_port = None
                            if isinstance(port_info, dict):
                                neighbor_port = port_info.get("name", "")

                            self.vlog.log(f"{port_name}: remote_host={remote_hostname}, remote_port={neighbor_port}")

                            # If neighbor port matches local port, it's an IPL
                            if neighbor_port and neighbor_port == port_name:
                                remote_switch_ip = self._get_other_switch_ip(current_switch_ip)
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
                                self.vlog.log(
                                    f"✓ IPL found: {port_name} ↔ {neighbor_port}",
                                    self.vlog.GREEN,
                                )

        except json.JSONDecodeError as e:
            self.logger.warning(f"Failed to parse JSON from nv show interface: {e}")
            self.vlog.log_error("JSON parse failed", e)
        except Exception as e:
            self.logger.error(f"Error parsing LLDP data: {e}")
            self.vlog.log_error("IPL parsing error", e)

        return ipl_connections

    def _parse_onyx_lldp_for_ipl(self, lldp_output: str, current_switch_ip: str) -> List[Dict[str, Any]]:
        """
        Parse Mellanox Onyx 'show lldp remote' output to find IPL connections.

        Onyx format from 'show lldp remote':
        Local Interface     Chassis ID          Port ID             System Name
        -----------------   -----------------   -----------------   -----------
        Eth1/29             f4:02:70:c1:22:00   Eth1/29             switch-2
        Eth1/30             f4:02:70:c1:22:00   Eth1/30             switch-2

        Args:
            lldp_output: Text output from 'show lldp remote'
            current_switch_ip: IP of the switch we're querying

        Returns:
            List of IPL connections found on this switch
        """
        ipl_connections = []

        try:
            self.vlog.log(f"Parsing LLDP data for IPL discovery on {current_switch_ip} (Onyx)")

            # Look for Eth1/29-32 (typical IPL ports on Onyx switches)
            for line in lldp_output.split("\n"):
                # Skip header lines
                if "Local Interface" in line or "---" in line or not line.strip():
                    continue

                # Split line into columns
                parts = line.split()
                if len(parts) >= 4:
                    local_interface = parts[0]  # e.g., "Eth1/29"
                    # chassis_id = parts[1]  # Not used, but available
                    remote_port = parts[2]  # e.g., "Eth1/29"
                    # remote_hostname = parts[3]  # Not used, but available

                    # Check if this is an IPL port (Eth1/29-32)
                    if local_interface.startswith("Eth1/"):
                        try:
                            local_port_num = int(local_interface.split("/")[1])
                        except (IndexError, ValueError):
                            continue

                        # Typical IPL ports are 29-32
                        if 29 <= local_port_num <= 32:
                            # Verify the remote port matches the local port (typical IPL behavior)
                            if remote_port == local_interface:
                                # Convert to swp naming for consistency
                                local_swp = f"swp{local_port_num}"
                                remote_swp = f"swp{local_port_num}"
                                remote_switch_ip = self._get_other_switch_ip(current_switch_ip)

                                ipl_connections.append(
                                    {
                                        "switch1_ip": current_switch_ip,
                                        "switch1_port": local_swp,
                                        "switch2_ip": remote_switch_ip,
                                        "switch2_port": remote_swp,
                                        "port_number": local_port_num,
                                    }
                                )
                                self.vlog.log(
                                    f"✓ IPL found: {local_swp} ↔ {remote_swp} (Onyx: {local_interface} ↔ {remote_port})",
                                    self.vlog.GREEN,
                                )

        except Exception as e:
            self.logger.error(f"Error parsing Onyx LLDP data: {e}")
            self.vlog.log_error("Onyx IPL parsing error", e)

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
        is_ebox_cluster: bool = False,
        ebox_mapping: Dict[str, int] = None,
        ebox_node_mapping: Dict[str, Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Correlate node MACs with switch ports using hostname-based mapping.

        For EBox clusters, generates port mappings for all virtual nodes
        (CNode + DNodes) that share each physical EBox connection.

        Args:
            node_inventory: {hostname: {mgmt_ip, node_type, box_vendor, ...}}
            hostname_to_ip: {hostname: data_ip}
            node_macs: {data_ip: {interface: mac}}
            switch_macs: {switch_ip: {mac: {port, vlan}}}
            is_ebox_cluster: True if this is an EBox cluster
            ebox_mapping: {ebox_guid: ebox_id} mapping
            ebox_node_mapping: {hostname/key: {ebox_id, node_type, position, ...}}

        Returns:
            List of port mappings with node and switch details
        """
        port_map = []
        ebox_mapping = ebox_mapping or {}
        ebox_node_mapping = ebox_node_mapping or {}

        # Determine switch assignments (Switch 1 = Network A, Switch 2 = Network B)
        sorted_switches = sorted(self.switch_ips)
        switch_1 = sorted_switches[0] if len(sorted_switches) > 0 else None
        switch_2 = sorted_switches[1] if len(sorted_switches) > 1 else None

        self.logger.info(
            f"Switch assignments: Switch-1 (Network A) = {switch_1}, " f"Switch-2 (Network B) = {switch_2}"
        )

        if is_ebox_cluster:
            self.logger.info("Using EBox-specific port correlation logic")

        # Build reverse mapping: data_ip -> hostname
        ip_to_hostname = {ip: hostname for hostname, ip in hostname_to_ip.items()}

        # For EBox clusters, build hostname -> ebox_id mapping and get DNodes per EBox
        hostname_to_ebox_id: Dict[str, Any] = {}
        ebox_cnode_names: Dict[Any, str] = {}  # {ebox_id: cnode_name (e.g., cnode-128-21-4200)}
        ebox_dnodes: Dict[Any, List[Dict[str, Any]]] = {}  # {ebox_id: [{node_id, position, hostname, name}, ...]}
        if is_ebox_cluster:
            for key, node_info in ebox_node_mapping.items():
                ebox_id = node_info.get("ebox_id")
                if ebox_id:
                    if node_info.get("node_type") == "cnode":
                        hostname = key
                        hostname_to_ebox_id[hostname] = ebox_id
                        # Get CNode name from API - format: cnode-128-21-4200
                        cnode_name = node_info.get("name", hostname)
                        ebox_cnode_names[ebox_id] = cnode_name
                        self.logger.debug(f"EBox {ebox_id} CNode name: {cnode_name}")
                    elif node_info.get("node_type") == "dnode":
                        hostname = node_info.get("hostname")
                        if ebox_id not in ebox_dnodes:
                            ebox_dnodes[ebox_id] = []
                        # Get DNode name from API - format: dnode-128-21-4000
                        dnode_name = node_info.get("name", f"dnode-{node_info.get('node_id', '')}")
                        ebox_dnodes[ebox_id].append(
                            {
                                "node_id": node_info.get("node_id"),
                                "position": node_info.get("position", "primary"),
                                "hostname": hostname,
                                "name": dnode_name,
                            }
                        )
                        self.logger.debug(
                            f"EBox {ebox_id} DNode name: {dnode_name} ({node_info.get('position', 'primary')})"
                        )

        # Track statistics for diagnostics
        missing_hostname_count = 0
        missing_inventory_count = 0
        missing_mac_count = 0
        found_mac_count = 0

        # Correlate each node MAC with switch ports
        for data_ip, interfaces in node_macs.items():
            # Find hostname for this data IP
            hostname = ip_to_hostname.get(data_ip)
            if not hostname:
                missing_hostname_count += 1
                self.logger.warning(f"No hostname found for data IP {data_ip} (has {len(interfaces)} interfaces)")
                self.vlog.log_warning(f"No hostname for IP {data_ip} - skipping {len(interfaces)} interfaces")
                continue

            # Get node info from inventory
            node_info = node_inventory.get(hostname)
            if not node_info:
                missing_inventory_count += 1
                self.logger.warning(f"No inventory found for hostname {hostname} (IP: {data_ip})")
                self.vlog.log_warning(f"No inventory for {hostname} ({data_ip})")
                continue

            node_type = node_info.get("node_type", "Unknown")
            ebox_id = hostname_to_ebox_id.get(hostname) if is_ebox_cluster else None
            self.vlog.log(
                f"Processing {node_type} {hostname} ({data_ip}): {len(interfaces)} interfaces, EBox ID: {ebox_id}"
            )

            for interface, mac in interfaces.items():
                # Find this MAC in switch tables
                mac_found = False
                for switch_ip, mac_table in switch_macs.items():
                    if mac in mac_table:
                        mac_found = True
                        switch_entry = mac_table[mac]
                        found_mac_count += 1

                        # Determine network (A or B) based on WHICH SWITCH
                        if switch_ip == switch_1:
                            network = "A"
                        elif switch_ip == switch_2:
                            network = "B"
                        else:
                            network = "A" if interface.endswith("f0") else "B"
                            self.logger.warning(f"Unknown switch {switch_ip}, using interface-based network detection")

                        # Determine port side (R=Right=f0=Network B, L=Left=f1=Network A)
                        # Note: Network A connects to SWA (L side), Network B connects to SWB (R side)
                        port_side = "L" if network == "A" else "R"

                        # Determine connection notes based on interface type
                        is_physical_nic = interface.startswith("enp3s0f") and "." not in interface
                        is_bond = "bond" in interface.lower()
                        is_virtual_nic = mac.startswith("be:ef:")

                        # Determine notes based on connection type
                        # Only "Visible Bond0 Path" (physical NIC on Network B/SWB) = Primary
                        # Alt paths = Secondary (not Virtual)
                        if is_physical_nic and network == "B":
                            notes = "Visible Bond0 Path = Primary"
                        elif is_bond or is_virtual_nic:
                            notes = "Alt Bond0 Path = Secondary"
                        else:
                            notes = "Alt Bond0 Path = Secondary"

                        base_entry = {
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
                            "port_side": port_side,
                            "notes": notes,
                        }

                        if is_ebox_cluster and ebox_id:
                            # For EBox clusters, add ebox_id and create entries for virtual nodes
                            base_entry["ebox_id"] = ebox_id

                            # Get CNode name for this EBox
                            cnode_name = ebox_cnode_names.get(ebox_id, f"CNode-{ebox_id}")

                            # Add CNode entry
                            cnode_entry = base_entry.copy()
                            cnode_entry["ebox_node_type"] = "cnode"
                            cnode_entry["ebox_node_num"] = 1  # CN1 per EBox
                            # Use actual CNode name as notes
                            cnode_entry["notes"] = cnode_name
                            cnode_entry["node_name"] = cnode_name
                            port_map.append(cnode_entry)

                            # Add DNode entries for this EBox
                            dnodes = ebox_dnodes.get(ebox_id, [])
                            for idx, dnode in enumerate(dnodes, start=1):
                                dnode_entry = base_entry.copy()
                                dnode_entry["ebox_node_type"] = "dnode"
                                dnode_entry["ebox_node_num"] = idx  # DN1, DN2 per EBox
                                dnode_entry["dnode_position"] = dnode.get("position", "primary")
                                # Use actual DNode name as notes
                                dnode_name = dnode.get("name", f"DNode-{ebox_id}-{idx}")
                                dnode_entry["notes"] = dnode_name
                                dnode_entry["node_name"] = dnode_name
                                port_map.append(dnode_entry)
                        else:
                            # Standard CBox/DBox cluster
                            port_map.append(base_entry)

                # Log if MAC was not found in any switch
                if not mac_found:
                    missing_mac_count += 1
                    self.logger.warning(
                        f"MAC not found in any switch table: {hostname} ({data_ip}) {interface} = {mac}"
                    )
                    self.vlog.log_warning(f"MAC {mac} from {hostname} {interface} not found in switch tables")

        # Log correlation statistics
        self.logger.info(
            f"Correlation complete: {found_mac_count} MACs found, {missing_mac_count} MACs not found in switches"
        )
        self.logger.info(f"Missing hostname: {missing_hostname_count}, Missing inventory: {missing_inventory_count}")
        self.vlog.log(
            f"Correlation stats: {found_mac_count} found, {missing_mac_count} missing MACs, "
            f"{missing_hostname_count} missing hostnames, {missing_inventory_count} missing inventory",
            self.vlog.YELLOW if missing_mac_count > 0 else self.vlog.GREEN,
        )

        return port_map

    def _detect_cross_connections(self, port_map: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
