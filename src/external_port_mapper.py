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

logger = logging.getLogger(__name__)


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

            # Step 5: Detect cross-connections
            cross_connections = self._detect_cross_connections(port_map)

            return {
                "available": True,
                "node_macs": node_macs,
                "switch_macs": switch_macs,
                "port_map": port_map,
                "cross_connections": cross_connections,
                "total_connections": len(port_map),
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

            # SSH to CNode and run clush to get all node hostnames
            cmd = [
                "sshpass",
                "-p",
                self.node_password,
                "ssh",
                "-o",
                "StrictHostKeyChecking=no",
                "-o",
                "UserKnownHostsFile=/dev/null",
                f"{self.node_user}@{self.cnode_ip}",
                "clush -a hostname",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                raise Exception(f"clush hostname command failed: {result.stderr}")

            # Parse output: "172.16.3.4: se-az-arrow-cb2-cn-1"
            hostname_to_ip = {}
            for line in result.stdout.split("\n"):
                match = re.match(r"^([\d.]+):\s+(.+)$", line.strip())
                if match:
                    data_ip = match.group(1)
                    hostname = match.group(2).strip()
                    hostname_to_ip[hostname] = data_ip
                    self.logger.debug(f"Mapped {hostname} → {data_ip}")

            return hostname_to_ip

        except Exception as e:
            self.logger.error(f"Error collecting hostname to IP mapping: {e}")
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
                "UserKnownHostsFile=/dev/null",
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
                    "UserKnownHostsFile=/dev/null",
                    "-T",  # Disable PTY allocation for non-interactive commands
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

                        # Determine network (A or B) based on interface
                        # Typically: enp*s0f0 = Port-A (Network A)
                        #            enp*s0f1 = Port-B (Network B)
                        network = "A" if interface.endswith("f0") else "B"

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
