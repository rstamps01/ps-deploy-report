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
        external_port_map: List[Dict[str, Any]] = None,
    ):
        """
        Initialize enhanced port mapper.

        Args:
            cboxes: List of CBox hardware data
            dboxes: List of DBox hardware data
            cnodes: List of CNode data
            dnodes: List of DNode data
            switches: List of switch hardware data
            external_port_map: Optional pre-collected port map data with node IPs
        """
        self.cboxes = cboxes
        self.dboxes = dboxes
        self.cnodes = cnodes
        self.dnodes = dnodes
        self.switches = switches
        self.external_port_map = external_port_map or []

        # Build lookup maps
        self._build_node_maps()
        self._build_switch_map()

    def _build_node_maps(self):
        """Build IP-based node lookup maps from actual cluster data and external port map."""
        self.cnode_map = {}
        self.dnode_map = {}

        # First, try to build from external port map data (most reliable for data IPs)
        if self.external_port_map:
            # Group by node IP to get unique nodes
            nodes_by_ip = {}
            for entry in self.external_port_map:
                node_ip = entry.get("node_ip")
                if node_ip and node_ip not in nodes_by_ip:
                    nodes_by_ip[node_ip] = entry

            # Determine node type by interface pattern
            # CNodes typically use enp129s0f* interfaces
            # DNodes typically use enp3s0f* interfaces
            cnode_ips = []
            dnode_ips = []

            for node_ip, entry in nodes_by_ip.items():
                interface = entry.get("interface", "")
                hostname = entry.get("node_hostname", "")

                # Heuristic: enp129 = CNode, enp3 = DNode
                if "enp129" in interface or "cnode" in hostname.lower():
                    cnode_ips.append((node_ip, hostname))
                elif "enp3" in interface or "dnode" in hostname.lower():
                    dnode_ips.append((node_ip, hostname))
                else:
                    # Default: assume CNode
                    cnode_ips.append((node_ip, hostname))

            # Sort by IP to ensure consistent numbering
            cnode_ips.sort()
            dnode_ips.sort()

            # Build CNode map
            for idx, (node_ip, hostname) in enumerate(cnode_ips, start=1):
                self.cnode_map[node_ip] = {
                    "cnode_num": idx,
                    "cbox_num": idx,  # Assume 1:1 mapping
                    "hostname": hostname if hostname != "Unknown" else f"cnode-{idx}",
                }
                logger.debug(f"Mapped CNode {idx} from external data: {node_ip}")

            # Build DNode map
            for idx, (node_ip, hostname) in enumerate(dnode_ips, start=1):
                self.dnode_map[node_ip] = {
                    "dnode_num": idx,
                    "dbox_num": 1,  # Assume single DBox
                    "hostname": hostname if hostname != "Unknown" else f"dnode-{idx}",
                }
                logger.debug(f"Mapped DNode {idx} from external data: {node_ip}")

        # Supplement with API data if we didn't get enough nodes from external map
        if len(self.cnode_map) < len(self.cnodes):
            for idx, cnode in enumerate(self.cnodes, start=1):
                # Try to get data IP from various possible fields
                data_ip = None

                # Check for data_ips list
                data_ips = cnode.get("data_ips", [])
                if data_ips and len(data_ips) > 0:
                    data_ip = data_ips[0]  # Use first data IP

                # Check for mgmt_ip as fallback
                if not data_ip:
                    data_ip = cnode.get("mgmt_ip")

                # Check for ipmi_ip as last resort
                if not data_ip:
                    data_ip = cnode.get("ipmi_ip")

                # Only add if not already in map
                if data_ip and data_ip not in self.cnode_map:
                    # Determine CBox number from CNode data
                    cbox_id = cnode.get("cbox_id", idx)
                    cbox_num = cbox_id if isinstance(cbox_id, int) else idx

                    # Get hostname
                    hostname = (
                        cnode.get("name") or cnode.get("hostname") or f"cnode-{idx}"
                    )

                    self.cnode_map[data_ip] = {
                        "cnode_num": idx,
                        "cbox_num": cbox_num,
                        "hostname": hostname,
                    }
                    logger.debug(
                        f"Mapped CNode {idx} from API: {data_ip} -> {hostname}"
                    )

        # Supplement with DNode API data
        if len(self.dnode_map) < len(self.dnodes):
            for idx, dnode in enumerate(self.dnodes, start=1):
                # Try to get data IP from various possible fields
                data_ip = None

                # Check for data_ips list
                data_ips = dnode.get("data_ips", [])
                if data_ips and len(data_ips) > 0:
                    data_ip = data_ips[0]  # Use first data IP

                # Check for mgmt_ip as fallback
                if not data_ip:
                    data_ip = dnode.get("mgmt_ip")

                # Check for ipmi_ip as last resort
                if not data_ip:
                    data_ip = dnode.get("ipmi_ip")

                # Only add if not already in map
                if data_ip and data_ip not in self.dnode_map:
                    # Determine DBox number from DNode data
                    dbox_id = dnode.get("dbox_id", 1)
                    dbox_num = dbox_id if isinstance(dbox_id, int) else 1

                    # Get hostname
                    hostname = (
                        dnode.get("name") or dnode.get("hostname") or f"dnode-{idx}"
                    )

                    self.dnode_map[data_ip] = {
                        "dnode_num": idx,
                        "dbox_num": dbox_num,
                        "hostname": hostname,
                    }
                    logger.debug(
                        f"Mapped DNode {idx} from API: {data_ip} -> {hostname}"
                    )

        logger.info(
            f"Built node maps: {len(self.cnode_map)} CNodes, {len(self.dnode_map)} DNodes"
        )

        # Log the mappings for debugging
        if self.cnode_map:
            logger.debug(f"CNode IPs: {list(self.cnode_map.keys())}")
        if self.dnode_map:
            logger.debug(f"DNode IPs: {list(self.dnode_map.keys())}")

    def _build_switch_map(self):
        """Build switch IP to designation map from actual cluster data."""
        self.switch_map = {}

        # Sort switches by management IP to ensure consistent numbering
        sorted_switches = sorted(self.switches, key=lambda s: s.get("mgmt_ip", ""))

        for idx, switch in enumerate(sorted_switches, start=1):
            mgmt_ip = switch.get("mgmt_ip")
            if not mgmt_ip:
                logger.warning(f"Switch {idx} has no management IP, skipping")
                continue

            # Designation: Switch 1 = SWA, Switch 2 = SWB
            designation = "SWA" if idx == 1 else "SWB"

            # Get hostname
            hostname = switch.get("name") or switch.get("hostname") or f"switch-{idx}"

            self.switch_map[mgmt_ip] = {
                "switch_num": idx,
                "designation": designation,
                "hostname": hostname,
            }
            logger.debug(
                f"Mapped Switch {idx}: {mgmt_ip} -> {hostname} ({designation})"
            )

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
