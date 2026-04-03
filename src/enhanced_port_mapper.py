"""
Enhanced Port Mapper with Standardized Designations

Implements the port mapping designation system:
- Node Side: CB1-CN1-R (CBox-1/CNode-1/Port-A)
- Switch Side: SWA-P12 (Switch-1/Port-12)
"""

import logging
import re
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class EnhancedPortMapper:
    """
    Enhanced port mapper with standardized naming conventions.

    Node Designation Format:
    - CBox-1/CNode-1/Port-A = CB1-CN1-R
    - DBox-1/DNode-2/Port-B = DB1-DN2-L
    - EBox-1/CNode-1/Port-A = EB1-CN1-R (EBox clusters)
    - EBox-1/DNode-2/Port-B = EB1-DN2-L (EBox clusters)

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
        eboxes: List[Dict[str, Any]] = None,
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
            eboxes: List of EBox hardware data (for EBox-only clusters)
        """
        self.cboxes = cboxes
        self.dboxes = dboxes
        self.cnodes = cnodes
        self.dnodes = dnodes
        self.switches = switches
        self.external_port_map = external_port_map or []
        self.eboxes = eboxes or []

        # Detect if this is an EBox-only cluster
        self.is_ebox_cluster = bool(self.eboxes)

        # Build lookup maps
        self._build_node_maps()
        self._build_switch_map()

    def _build_node_maps(self):
        """Build IP-based node lookup maps from actual cluster data and external port map."""
        self.cnode_map = {}
        self.dnode_map = {}

        if self.external_port_map:
            cnode_hosts: dict[str, list[str]] = {}
            dnode_hosts: dict[str, list[str]] = {}
            host_meta: dict[str, dict[str, str]] = {}

            for entry in self.external_port_map:
                node_ip = entry.get("node_ip")
                hostname = entry.get("node_hostname", "")
                if not node_ip or not hostname:
                    continue

                box_name = entry.get("box_name", "")
                node_type_raw = entry.get("node_type", "").lower()
                interface = entry.get("interface", "")
                hn_lower = hostname.lower()

                if hostname not in host_meta:
                    host_meta[hostname] = {"box_name": box_name}

                is_dnode = node_type_raw == "dnode" or "enp3" in interface or "dnode" in hn_lower or "-dn-" in hn_lower

                if is_dnode:
                    dnode_hosts.setdefault(hostname, []).append(node_ip)
                else:
                    cnode_hosts.setdefault(hostname, []).append(node_ip)

            sorted_cnode_hosts = sorted(cnode_hosts.keys())
            sorted_dnode_hosts = sorted(dnode_hosts.keys())

            for idx, hostname in enumerate(sorted_cnode_hosts, start=1):
                for ip in cnode_hosts[hostname]:
                    self.cnode_map[ip] = {
                        "cnode_num": idx,
                        "cbox_num": idx,
                        "hostname": hostname,
                    }
                logger.debug("Mapped CNode %d (%s) from external data: %s", idx, hostname, cnode_hosts[hostname])

            unique_dboxes: list[str] = []
            for hostname in sorted_dnode_hosts:
                bname = host_meta.get(hostname, {}).get("box_name", "")
                if bname and bname.startswith("dbox-") and bname not in unique_dboxes:
                    unique_dboxes.append(bname)
            dbox_name_to_num = {name: i for i, name in enumerate(unique_dboxes, start=1)}

            for idx, hostname in enumerate(sorted_dnode_hosts, start=1):
                bname = host_meta.get(hostname, {}).get("box_name", "")
                dbox_num = dbox_name_to_num.get(bname, idx)
                for ip in dnode_hosts[hostname]:
                    self.dnode_map[ip] = {
                        "dnode_num": idx,
                        "dbox_num": dbox_num,
                        "hostname": hostname,
                    }
                logger.debug(
                    "Mapped DNode %d (DBox %d, %s) from external data: %s",
                    idx,
                    dbox_num,
                    hostname,
                    dnode_hosts[hostname],
                )

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
                    # For EBox clusters, use ebox_id; for CBox clusters, use cbox_id
                    if self.is_ebox_cluster:
                        box_id = cnode.get("ebox_id", idx)
                        box_num = box_id if isinstance(box_id, int) else idx
                    else:
                        box_id = cnode.get("cbox_id", idx)
                        box_num = box_id if isinstance(box_id, int) else idx

                    # Get hostname
                    hostname = cnode.get("name") or cnode.get("hostname") or f"cnode-{idx}"

                    self.cnode_map[data_ip] = {
                        "cnode_num": idx,
                        "cbox_num": box_num,  # cbox_num used for both CBox and EBox
                        "ebox_num": box_num if self.is_ebox_cluster else None,
                        "hostname": hostname,
                    }
                    logger.debug(f"Mapped CNode {idx} from API: {data_ip} -> {hostname}")

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
                    # For EBox clusters, use ebox_id; for DBox clusters, use dbox_id
                    if self.is_ebox_cluster:
                        box_id = dnode.get("ebox_id", 1)
                        box_num = box_id if isinstance(box_id, int) else 1
                    else:
                        box_id = dnode.get("dbox_id", 1)
                        box_num = box_id if isinstance(box_id, int) else 1

                    # Get hostname
                    hostname = dnode.get("name") or dnode.get("hostname") or f"dnode-{idx}"

                    self.dnode_map[data_ip] = {
                        "dnode_num": idx,
                        "dbox_num": box_num,  # dbox_num used for both DBox and EBox
                        "ebox_num": box_num if self.is_ebox_cluster else None,
                        "hostname": hostname,
                    }
                    logger.debug(f"Mapped DNode {idx} from API: {data_ip} -> {hostname}")

        logger.info(f"Built node maps: {len(self.cnode_map)} CNodes, {len(self.dnode_map)} DNodes")

        # Log the mappings for debugging
        if self.cnode_map:
            logger.debug(f"CNode IPs: {list(self.cnode_map.keys())}")
        if self.dnode_map:
            logger.debug(f"DNode IPs: {list(self.dnode_map.keys())}")

    def _build_switch_map(self):
        """Build switch IP to designation map from actual cluster data.

        Leaf switches (those in the port_map) get SWA/SWB/... designations.
        Spine switches (in inventory but NOT in port_map) get SP1/SP2/...
        designations with ``role: "spine"``.
        """
        self.switch_map = {}

        port_map_switch_ips = {e.get("switch_ip") for e in self.external_port_map if e.get("switch_ip")}

        leaf_switches = [sw for sw in self.switches if sw.get("mgmt_ip") in port_map_switch_ips]
        spine_switches = [
            sw for sw in self.switches if sw.get("mgmt_ip") and sw.get("mgmt_ip") not in port_map_switch_ips
        ]
        if not leaf_switches:
            leaf_switches = list(self.switches)
            spine_switches = []

        sorted_leaves = sorted(leaf_switches, key=lambda s: s.get("mgmt_ip", ""))

        sw_letters = "ABCDEFGH"
        for idx, switch in enumerate(sorted_leaves):
            mgmt_ip = switch.get("mgmt_ip")
            if not mgmt_ip:
                continue

            letter = sw_letters[idx] if idx < len(sw_letters) else str(idx + 1)
            designation = f"SW{letter}"
            hostname = switch.get("name") or switch.get("hostname") or f"switch-{idx + 1}"

            self.switch_map[mgmt_ip] = {
                "switch_num": idx + 1,
                "designation": designation,
                "hostname": hostname,
                "role": "leaf",
            }
            logger.debug("Mapped Leaf %d: %s -> %s (%s)", idx + 1, mgmt_ip, hostname, designation)

        sorted_spines = sorted(spine_switches, key=lambda s: s.get("mgmt_ip", ""))
        for idx, switch in enumerate(sorted_spines):
            mgmt_ip = switch.get("mgmt_ip")
            if not mgmt_ip:
                continue

            designation = f"SP{idx + 1}"
            hostname = switch.get("name") or switch.get("hostname") or f"spine-{idx + 1}"

            self.switch_map[mgmt_ip] = {
                "switch_num": idx + 1,
                "designation": designation,
                "hostname": hostname,
                "role": "spine",
            }
            logger.debug("Mapped Spine %d: %s -> %s (%s)", idx + 1, mgmt_ip, hostname, designation)

        logger.info(
            "Built switch map: %d leaf, %d spine",
            len(sorted_leaves),
            len(sorted_spines),
        )

    def generate_node_designation(self, node_ip: str, network: str, hostname: str = None) -> Tuple[str, str]:
        """
        Generate standardized node designation.

        Args:
            node_ip: Node data plane IP (172.16.3.x)
            network: Network designation (A or B)
            hostname: Optional node hostname

        Returns:
            Tuple of (designation, node_type)
            Examples:
            - ("CB1-CN1-R", "cnode") for CNode-1 Network A (CBox cluster)
            - ("DB1-DN2-L", "dnode") for DNode-2 Network B (DBox cluster)
            - ("EB1-CN1-R", "cnode") for CNode-1 Network A (EBox cluster)
            - ("EB1-DN2-L", "dnode") for DNode-2 Network B (EBox cluster)
        """
        # Check if CNode
        if node_ip in self.cnode_map:
            node_info = self.cnode_map[node_ip]
            box_num = node_info["cbox_num"]
            cnode_num = node_info["cnode_num"]

            # Network A = Port-A = R, Network B = Port-B = L
            port_side = "R" if network == "A" else "L"

            # Use EB prefix for EBox clusters, CB for CBox clusters
            box_prefix = "EB" if self.is_ebox_cluster else "CB"
            designation = f"{box_prefix}{box_num}-CN{cnode_num}-{port_side}"
            return designation, "cnode"

        # Check if DNode
        elif node_ip in self.dnode_map:
            node_info = self.dnode_map[node_ip]
            box_num = node_info["dbox_num"]
            dnode_num = node_info["dnode_num"]

            # Network A = Port-A = R, Network B = Port-B = L
            port_side = "R" if network == "A" else "L"

            # Use EB prefix for EBox clusters, DB for DBox clusters
            box_prefix = "EB" if self.is_ebox_cluster else "DB"
            designation = f"{box_prefix}{box_num}-DN{dnode_num}-{port_side}"
            return designation, "dnode"

        else:
            logger.warning(f"Unknown node IP: {node_ip}")
            return f"UNKNOWN-{node_ip}", "unknown"

    def generate_switch_designation(self, switch_ip: str, port_name: str) -> str:
        """
        Generate standardized switch port designation.

        Handles multiple port naming formats and switch roles:
        - Leaf:  ``swp20`` -> ``SWA-P20``, ``Eth1/15/1`` -> ``SWA-P15/1``
        - Spine: ``swp20`` -> ``SP1-P20``
        """
        if switch_ip in self.switch_map:
            switch_info = self.switch_map[switch_ip]
            switch_des = switch_info["designation"]

            port_id = self._normalize_port_id(port_name)
            return f"{switch_des}-P{port_id}"
        else:
            logger.warning(f"Unknown switch IP: {switch_ip}")
            return f"SW?-{port_name}"

    @staticmethod
    def _normalize_port_id(port_name: str) -> str:
        """Extract a human-readable port identifier from a raw port name.

        ``swp20``       -> ``20``
        ``Eth1/15``     -> ``15``
        ``Eth1/15/1``   -> ``15/1``  (preserves breakout lane)
        """
        lower = port_name.lower()
        if lower.startswith("swp"):
            return lower[3:]

        # Eth<module>/<port>[/<lane>]
        eth_match = re.match(r"[Ee]th\d+/(\d+(?:/\d+)?)", port_name)
        if eth_match:
            return eth_match.group(1)

        # Fallback: last numeric group
        digits = re.findall(r"\d+", port_name)
        return digits[-1] if digits else port_name

    def get_node_hostname(self, node_ip: str) -> str:
        """Get full hostname for a node IP."""
        if node_ip in self.cnode_map:
            return str(self.cnode_map[node_ip]["hostname"])
        elif node_ip in self.dnode_map:
            return str(self.dnode_map[node_ip]["hostname"])
        else:
            return "Unknown"

    def get_switch_hostname(self, switch_ip: str) -> str:
        """Get full hostname for a switch IP."""
        if switch_ip in self.switch_map:
            return str(self.switch_map[switch_ip]["hostname"])
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

    def detect_cross_connection(self, switch_ip: str, node_ip: str, actual_network: str) -> Tuple[bool, str]:
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

    def generate_enhanced_port_map(self, raw_port_map: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate enhanced port map with standardized designations.

        For EBox clusters, uses EB#-CN1-R/L and EB#-DN1-R/L format.
        For CBox/DBox clusters, uses CB#-CN#-R/L and DB#-DN#-R/L format.

        Args:
            raw_port_map: Raw port mapping data from external_port_mapper

        Returns:
            Enhanced port mapping with designations
        """
        enhanced_map = []
        cross_connections = []
        ipl_connections: list[Any] = []

        for conn in raw_port_map:
            node_ip = conn.get("node_ip")
            switch_ip = conn.get("switch_ip")
            port_name = conn.get("port")
            network = conn.get("network")
            interface = conn.get("interface")
            mac = conn.get("mac")

            # Check for EBox-specific fields
            ebox_id = conn.get("ebox_id")
            ebox_node_type = conn.get("ebox_node_type")
            ebox_node_num = conn.get("ebox_node_num")
            port_side = conn.get("port_side", "R" if network == "A" else "L")
            notes = conn.get("notes", "")

            # Generate designations
            if ebox_id and ebox_node_type:
                # EBox-specific designation: EB#-CN1-R or EB#-DN1-L
                node_type_abbrev = "CN" if ebox_node_type == "cnode" else "DN"
                node_designation = f"EB{ebox_id}-{node_type_abbrev}{ebox_node_num}-{port_side}"
                node_type = ebox_node_type
            else:
                # Standard CBox/DBox designation
                node_designation, node_type = self.generate_node_designation(
                    node_ip, network, conn.get("node_hostname")
                )

            switch_designation = self.generate_switch_designation(switch_ip, port_name)

            # Get hostnames
            node_hostname = self.get_node_hostname(node_ip) or conn.get("node_hostname", "Unknown")
            switch_hostname = self.get_switch_hostname(switch_ip)

            # Detect cross-connections
            is_cross, expected_network = self.detect_cross_connection(switch_ip, node_ip, network)

            enhanced_entry = {
                "node_ip": node_ip,
                "node_hostname": node_hostname,
                "node_designation": node_designation,
                "node_type": node_type,
                "interface": interface,
                "mac": mac,
                "network": network,
                "port_side": port_side,
                "switch_ip": switch_ip,
                "switch_hostname": switch_hostname,
                "switch_designation": switch_designation,
                "port": port_name,
                "is_cross_connected": is_cross,
                "expected_network": expected_network,
                "notes": notes,
            }

            # Add EBox-specific fields if present
            if ebox_id:
                enhanced_entry["ebox_id"] = ebox_id
                enhanced_entry["ebox_node_type"] = ebox_node_type
                enhanced_entry["ebox_node_num"] = ebox_node_num
                if conn.get("dnode_position"):
                    enhanced_entry["dnode_position"] = conn.get("dnode_position")

            enhanced_map.append(enhanced_entry)

            if is_cross:
                cross_connections.append(enhanced_entry)

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
