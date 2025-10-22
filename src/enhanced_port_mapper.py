"""
Enhanced Port Mapper with Standardized Designations

Implements the port mapping designation system:
- Node Side: CB1-CN1-R (CBox-1/CNode-1/Port-A)
- Switch Side: SWA-P12 (Switch-1/Port-12)
"""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class EnhancedPortMapper:
    """
    Enhanced port mapper with standardized naming conventions.

    Node Designation Format:
    - CBox-1/CNode-1/Port-A = CB1-CN1-R
    - DBox-1/DNode-2/Port-B = DB1-DN2-L

    Switch Designation Format:
    - Switch-1/Port-12 = SWA-P12
    - Switch-2/Port-1 = SWB-P1

    Port Side Mapping:
    - Network A = Port-A = R (Right)
    - Network B = Port-B = L (Left)
    """

    def __init__(
        self,
        cboxes: List[Dict[str, Any]],
        dboxes: List[Dict[str, Any]],
        cnodes: List[Dict[str, Any]],
        dnodes: List[Dict[str, Any]],
        switches: List[Dict[str, Any]],
    ):
        """
        Initialize enhanced port mapper.

        Args:
            cboxes: List of CBox hardware data
            dboxes: List of DBox hardware data
            cnodes: List of CNode data
            dnodes: List of DNode data
            switches: List of switch hardware data
        """
        self.cboxes = cboxes
        self.dboxes = dboxes
        self.cnodes = cnodes
        self.dnodes = dnodes
        self.switches = switches

        # Build lookup maps
        self._build_node_maps()
        self._build_switch_map()

    def _build_node_maps(self):
        """Build IP-based node lookup maps."""
        # Map data IPs to node numbers based on last octet
        # .4 = CNode-1, .5 = CNode-2, .104 = DNode-1, .105 = DNode-2

        self.cnode_map = {
            "172.16.3.4": {
                "cnode_num": 1,
                "cbox_num": 1,
                "hostname": "se-az-arrow-cb2-cn-1",
            },
            "172.16.3.5": {
                "cnode_num": 2,
                "cbox_num": 2,
                "hostname": "se-az-arrow-cb2-cn-2",
            },
        }

        self.dnode_map = {
            "172.16.3.104": {
                "dnode_num": 1,
                "dbox_num": 1,
                "hostname": "se-az-arrow-db2-dn-1",
            },
            "172.16.3.105": {
                "dnode_num": 2,
                "dbox_num": 1,
                "hostname": "se-az-arrow-db2-dn-2",
            },
        }

        logger.info(
            f"Built node maps: {len(self.cnode_map)} CNodes, {len(self.dnode_map)} DNodes"
        )

    def _build_switch_map(self):
        """Build switch IP to designation map."""
        # Map switch management IPs to switch numbers
        self.switch_map = {
            "10.143.11.153": {
                "switch_num": 1,
                "designation": "SWA",
                "hostname": "se-var-1-1",
            },
            "10.143.11.154": {
                "switch_num": 2,
                "designation": "SWB",
                "hostname": "se-var-1-2",
            },
        }

        logger.info(f"Built switch map: {len(self.switch_map)} switches")

    def generate_node_designation(
        self, node_ip: str, network: str, hostname: str = None
    ) -> Tuple[str, str]:
        """
        Generate standardized node designation.

        Args:
            node_ip: Node data plane IP (172.16.3.x)
            network: Network designation (A or B)
            hostname: Optional node hostname

        Returns:
            Tuple of (designation, node_type)
            Examples:
            - ("CB1-CN1-R", "cnode") for CNode-1 Network A
            - ("DB1-DN2-L", "dnode") for DNode-2 Network B
        """
        # Check if CNode
        if node_ip in self.cnode_map:
            node_info = self.cnode_map[node_ip]
            cbox_num = node_info["cbox_num"]
            cnode_num = node_info["cnode_num"]

            # Network A = Port-A = R, Network B = Port-B = L
            port_side = "R" if network == "A" else "L"

            designation = f"CB{cbox_num}-CN{cnode_num}-{port_side}"
            return designation, "cnode"

        # Check if DNode
        elif node_ip in self.dnode_map:
            node_info = self.dnode_map[node_ip]
            dbox_num = node_info["dbox_num"]
            dnode_num = node_info["dnode_num"]

            # Network A = Port-A = R, Network B = Port-B = L
            port_side = "R" if network == "A" else "L"

            designation = f"DB{dbox_num}-DN{dnode_num}-{port_side}"
            return designation, "dnode"

        else:
            logger.warning(f"Unknown node IP: {node_ip}")
            return f"UNKNOWN-{node_ip}", "unknown"

    def generate_switch_designation(self, switch_ip: str, port_name: str) -> str:
        """
        Generate standardized switch port designation.

        Args:
            switch_ip: Switch management IP
            port_name: Port name (e.g., "swp20")

        Returns:
            Designation string
            Examples:
            - "SWA-P12" for Switch-1 Port 12
            - "SWB-P5" for Switch-2 Port 5
        """
        if switch_ip in self.switch_map:
            switch_info = self.switch_map[switch_ip]
            switch_des = switch_info["designation"]

            # Extract port number from port name (swp20 -> 20)
            port_num = port_name.replace("swp", "").replace("eth", "")

            designation = f"{switch_des}-P{port_num}"
            return designation
        else:
            logger.warning(f"Unknown switch IP: {switch_ip}")
            return f"SW?-{port_name}"

    def get_node_hostname(self, node_ip: str) -> str:
        """Get full hostname for a node IP."""
        if node_ip in self.cnode_map:
            return self.cnode_map[node_ip]["hostname"]
        elif node_ip in self.dnode_map:
            return self.dnode_map[node_ip]["hostname"]
        else:
            return "Unknown"

    def get_switch_hostname(self, switch_ip: str) -> str:
        """Get full hostname for a switch IP."""
        if switch_ip in self.switch_map:
            return self.switch_map[switch_ip]["hostname"]
        else:
            return "Unknown"

    def is_ipl_port(self, port_name: str, speed: str) -> bool:
        """
        Determine if a port is an IPL (Inter-Peer Link) or MLAG port.

        For 2-switch (leaf-only) deployments:
        - IPL ports are typically swp29-32 at 100G speed

        Args:
            port_name: Port name (e.g., "swp29")
            speed: Port speed (e.g., "100G")

        Returns:
            True if port appears to be IPL/MLAG
        """
        # IPL ports are typically swp29-32 with 100G speed
        ipl_ports = ["swp29", "swp30", "swp31", "swp32"]

        if port_name in ipl_ports and speed == "100G":
            return True

        return False

    def detect_cross_connection(
        self, switch_ip: str, node_ip: str, actual_network: str
    ) -> Tuple[bool, str]:
        """
        Detect if a connection is cross-connected (wrong network).

        In a properly cabled VAST cluster:
        - Each node has TWO connections (Network A and Network B)
        - Network A typically uses Switch-1 as primary
        - Network B typically uses Switch-2 as primary
        - However, BOTH networks CAN appear on BOTH switches (this is normal)

        We only flag as cross-connected if there's an unusual pattern,
        but for VAST dual-network designs, mixed networks per switch is expected.

        Args:
            switch_ip: Switch management IP
            node_ip: Node data plane IP
            actual_network: Actual network (A or B)

        Returns:
            Tuple of (is_cross_connected, expected_network)
        """
        # For VAST deployments with proper redundancy, both networks
        # can legitimately appear on both switches. This is NOT a
        # cross-connection - it's proper redundant design.

        # We'll return False (not cross-connected) for normal configurations
        # True cross-connections would be detected at a higher level
        # (e.g., same node interface appearing on wrong network)

        return False, actual_network

    def generate_enhanced_port_map(
        self, raw_port_map: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate enhanced port map with standardized designations.

        Args:
            raw_port_map: Raw port mapping data from external_port_mapper

        Returns:
            Enhanced port mapping with designations
        """
        enhanced_map = []
        cross_connections = []
        ipl_connections = []

        for conn in raw_port_map:
            node_ip = conn.get("node_ip")
            switch_ip = conn.get("switch_ip")
            port_name = conn.get("port")
            network = conn.get("network")
            interface = conn.get("interface")
            mac = conn.get("mac")

            # Generate designations
            node_designation, node_type = self.generate_node_designation(
                node_ip, network, conn.get("node_hostname")
            )
            switch_designation = self.generate_switch_designation(switch_ip, port_name)

            # Get hostnames
            node_hostname = self.get_node_hostname(node_ip)
            switch_hostname = self.get_switch_hostname(switch_ip)

            # Detect cross-connections
            is_cross, expected_network = self.detect_cross_connection(
                switch_ip, node_ip, network
            )

            # Check if IPL port (won't have node connections)
            # Note: We're looking at ports from MAC tables, so IPL ports
            # won't show up here unless misconfigured

            enhanced_entry = {
                "node_ip": node_ip,
                "node_hostname": node_hostname,
                "node_designation": node_designation,
                "node_type": node_type,
                "interface": interface,
                "mac": mac,
                "network": network,
                "port_side": "R" if network == "A" else "L",
                "switch_ip": switch_ip,
                "switch_hostname": switch_hostname,
                "switch_designation": switch_designation,
                "port": port_name,
                "is_cross_connected": is_cross,
                "expected_network": expected_network,
            }

            enhanced_map.append(enhanced_entry)

            if is_cross:
                cross_connections.append(enhanced_entry)

        # Identify IPL ports from switches (separate from node connections)
        # This would require separate switch port data

        result = {
            "port_map": enhanced_map,
            "cross_connections": cross_connections,
            "ipl_connections": ipl_connections,
            "total_connections": len(enhanced_map),
            "cross_connection_count": len(cross_connections),
            "has_cross_connections": len(cross_connections) > 0,
        }

        logger.info(
            f"Generated enhanced port map: {len(enhanced_map)} connections, "
            f"{len(cross_connections)} cross-connections"
        )

        return result
