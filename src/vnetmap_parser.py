"""
VNetMap Output Parser

Parses vnetmap.py output files to extract port-to-device mapping information.
"""

import re
from pathlib import Path
from typing import Any, Dict, List


class VNetMapParser:
    """Parser for vnetmap.py output files"""

    def __init__(self, output_file: str):
        """
        Initialize parser with vnetmap output file.

        Args:
            output_file: Path to vnetmap output file
        """
        self.output_file = Path(output_file)
        self.raw_data = []
        self.topology_data = []
        self.cross_connections = []

    def parse(self) -> Dict[str, Any]:
        """
        Parse vnetmap output file and extract topology data.

        Returns:
            Dict containing parsed topology and connectivity information
        """
        if not self.output_file.exists():
            return {
                "available": False,
                "error": f"VNetMap output file not found: {self.output_file}",
                "topology": [],
                "cross_connections": [],
            }

        try:
            with open(self.output_file, "r") as f:
                content = f.read()

            # Extract topology section
            self._parse_topology_section(content)

            # Extract cross-connection warnings
            self._parse_cross_connections(content)

            return {
                "available": True,
                "topology": self.topology_data,
                "cross_connections": self.cross_connections,
                "total_connections": len(self.topology_data),
            }

        except Exception as e:
            return {
                "available": False,
                "error": f"Error parsing vnetmap output: {e}",
                "topology": [],
                "cross_connections": [],
            }

    def _parse_topology_section(self, content: str):
        """
        Parse the 'Full topology' section from vnetmap output.

        Format:
        hostname    switch_ip    port    node_ip    interface    mac    network
        """
        # Find the "Full topology" section
        topology_match = re.search(
            r"Full topology\n(.*?)(?:\n\n|\nConnectivity issue)",
            content,
            re.DOTALL,
        )

        if not topology_match:
            return

        topology_lines = topology_match.group(1).strip().split("\n")

        for line in topology_lines:
            # Split by whitespace (multiple spaces/tabs)
            parts = line.split()

            if len(parts) >= 7:
                connection = {
                    "hostname": parts[0],
                    "switch_ip": parts[1],
                    "port": parts[2],
                    "node_ip": parts[3],
                    "interface": parts[4],
                    "mac": parts[5],
                    "network": parts[6],
                }
                self.topology_data.append(connection)

    def _parse_cross_connections(self, content: str):
        """
        Parse connectivity issue warnings from vnetmap output.
        """
        # Find all "Connectivity issue detected" sections
        issue_pattern = r"Connectivity issue detected, switch ([\d.]+) has more then one internal network"
        matches = re.finditer(issue_pattern, content)

        for match in matches:
            switch_ip = match.group(1)

            # Extract the network details for this switch
            network_pattern = (
                rf"Switch {re.escape(switch_ip)} has {{(.*?)}}, network {{(.*?)}}"
            )
            network_match = re.search(network_pattern, content)

            if network_match:
                networks = network_match.group(1).replace("'", "").split(", ")
                network_labels = network_match.group(2).replace("'", "").split(", ")

                self.cross_connections.append(
                    {
                        "switch_ip": switch_ip,
                        "networks": networks,
                        "network_labels": network_labels,
                    }
                )

    def get_connections_by_switch(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group connections by switch IP.

        Returns:
            Dict mapping switch IPs to list of connections
        """
        connections_by_switch = {}

        for conn in self.topology_data:
            switch_ip = conn["switch_ip"]
            if switch_ip not in connections_by_switch:
                connections_by_switch[switch_ip] = []
            connections_by_switch[switch_ip].append(conn)

        # Sort connections by port number within each switch
        for switch_ip in connections_by_switch:
            connections_by_switch[switch_ip].sort(
                key=lambda x: self._extract_port_number(x["port"])
            )

        return connections_by_switch

    def get_connections_by_node(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Group connections by node hostname.

        Returns:
            Dict mapping node hostnames to list of connections
        """
        connections_by_node = {}

        for conn in self.topology_data:
            hostname = conn["hostname"]
            if hostname not in connections_by_node:
                connections_by_node[hostname] = []
            connections_by_node[hostname].append(conn)

        return connections_by_node

    def get_node_ips(self) -> Dict[str, List[str]]:
        """
        Get all unique node IPs grouped by node type (CNode vs DNode).

        Returns:
            Dict with 'cnodes' and 'dnodes' lists of IPs
        """
        cnode_ips = set()
        dnode_ips = set()

        for conn in self.topology_data:
            node_ip = conn["node_ip"]
            # Extract last octet
            last_octet = int(node_ip.split(".")[-1])

            if last_octet >= 100:
                dnode_ips.add(node_ip)
            else:
                cnode_ips.add(node_ip)

        return {
            "cnodes": sorted(list(cnode_ips), key=lambda ip: int(ip.split(".")[-1])),
            "dnodes": sorted(list(dnode_ips), key=lambda ip: int(ip.split(".")[-1])),
        }

    def _extract_port_number(self, port_name: str) -> int:
        """
        Extract numeric port number from port name.

        Args:
            port_name: Port name (e.g., "swp20", "eth1/1")

        Returns:
            Port number as integer
        """
        # Extract all digits from port name
        digits = re.findall(r"\d+", port_name)
        if digits:
            # Use the last number (handles "eth1/1" -> 1, "swp20" -> 20)
            return int(digits[-1])
        return 0

    def has_cross_connections(self) -> bool:
        """Check if any cross-connections were detected."""
        return len(self.cross_connections) > 0

    def get_cross_connection_summary(self) -> str:
        """
        Get human-readable summary of cross-connection issues.

        Returns:
            Summary string describing cross-connections
        """
        if not self.has_cross_connections():
            return "No cross-connections detected. All cabling is correct."

        summary_parts = []
        for issue in self.cross_connections:
            switch_ip = issue["switch_ip"]
            networks = ", ".join(issue["networks"])
            summary_parts.append(
                f"Switch {switch_ip} has multiple internal networks ({networks})"
            )

        return "; ".join(summary_parts)
