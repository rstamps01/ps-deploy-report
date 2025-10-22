"""
Port Mapping Generator

Generates standardized port designations (CB1-CN1-R, SWA-P12, etc.) and
detects cross-connection issues.
"""

import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class PortMapper:
    """Generate port mappings with standardized designations"""

    def __init__(
        self,
        cboxes: List[Dict[str, Any]],
        dboxes: List[Dict[str, Any]],
        cnodes: List[Dict[str, Any]],
        dnodes: List[Dict[str, Any]],
        switches: List[Dict[str, Any]],
    ):
        """
        Initialize port mapper with cluster hardware.

        Args:
            cboxes: List of CBox data from API
            dboxes: List of DBox data from API
            cnodes: List of CNode data from API
            dnodes: List of DNode data from API
            switches: List of switch data from API
        """
        self.cboxes = sorted(cboxes, key=lambda x: x.get("id", 0))
        self.dboxes = sorted(dboxes, key=lambda x: x.get("id", 0))
        self.cnodes = sorted(cnodes, key=lambda x: self._extract_ip_last_octet(x))
        self.dnodes = sorted(dnodes, key=lambda x: self._extract_ip_last_octet(x))
        self.switches = sorted(switches, key=lambda x: x.get("mgmt_ip", ""))

        # Build lookup tables
        self.cnode_to_cbox = {}
        self.dnode_to_dbox = {}
        self._assign_nodes_to_boxes()

    def _extract_ip_last_octet(self, node: Dict[str, Any]) -> int:
        """Extract last octet from node IP for sorting."""
        # Try multiple IP fields
        ip_fields = ["ip", "mgmt_ip", "ipv4_address", "address"]
        for field in ip_fields:
            ip = node.get(field)
            if ip:
                try:
                    return int(ip.split(".")[-1])
                except (ValueError, AttributeError):
                    continue
        return 999  # Default high value if no IP found

    def _assign_nodes_to_boxes(self):
        """
        Assign CNodes to CBoxes and DNodes to DBoxes based on hardware capacity.

        Logic:
        - Dell/HPE Ice Lake CBox: 4 CNodes per CBox
        - Other CBox models: 1 CNode per CBox
        - Ceres DBox: 4 DNodes per DBox
        - Ceres_v2 DBox: 2 DNodes per DBox
        """
        # Assign CNodes to CBoxes
        cnode_index = 0
        for cbox_num, cbox in enumerate(self.cboxes, start=1):
            cbox_id = f"CB{cbox_num}"
            box_vendor = cbox.get("box_vendor", "").lower()

            # Determine CNode capacity
            if "dell" in box_vendor and "ice" in box_vendor:
                capacity = 4
            elif "hpe" in box_vendor and "ice" in box_vendor:
                capacity = 4
            else:
                capacity = 1

            # Assign CNodes to this CBox
            for _ in range(capacity):
                if cnode_index < len(self.cnodes):
                    cnode_num = cnode_index + 1
                    cnode_id = f"CN{cnode_num}"
                    self.cnode_to_cbox[cnode_id] = cbox_id
                    cnode_index += 1

        # Assign DNodes to DBoxes
        dnode_index = 0
        for dbox_num, dbox in enumerate(self.dboxes, start=1):
            dbox_id = f"DB{dbox_num}"
            hardware_type = dbox.get("hardware_type", "").lower()

            # Determine DNode capacity
            if "ceres_v2" in hardware_type:
                capacity = 2
            elif "ceres" in hardware_type:
                capacity = 4
            else:
                capacity = 2  # Default to ceres_v2 capacity

            # Assign DNodes to this DBox
            for _ in range(capacity):
                if dnode_index < len(self.dnodes):
                    dnode_num = dnode_index + 1
                    dnode_id = f"DN{dnode_num}"
                    self.dnode_to_dbox[dnode_id] = dbox_id
                    dnode_index += 1

        logger.info(
            f"Assigned {cnode_index} CNodes to {len(self.cboxes)} CBoxes, "
            f"{dnode_index} DNodes to {len(self.dboxes)} DBoxes"
        )

    def generate_node_designation(
        self, node_ip: str, network: str, hostname: str = None
    ) -> Tuple[str, str]:
        """
        Generate standardized node-side port designation.

        Args:
            node_ip: Node IP address (e.g., "172.16.1.4")
            network: Network label ("A" or "B")
            hostname: Optional node hostname for validation

        Returns:
            Tuple of (full_designation, node_type)
            Example: ("CB1-CN1-R", "CNode") or ("DB1-DN2-L", "DNode")
        """
        last_octet = int(node_ip.split(".")[-1])

        # Determine port side (R = Port-A, L = Port-B)
        if network == "A":
            port_side = "R"  # Port-A = Right
        else:
            port_side = "L"  # Port-B = Left

        # Determine if CNode or DNode based on IP
        if last_octet >= 100:
            # DNode
            node_type = "DNode"
            # Find which DNode this is (sorted by IP)
            dnode_num = None
            for idx, dnode in enumerate(self.dnodes, start=1):
                dnode_ip_octet = self._extract_ip_last_octet(dnode)
                if dnode_ip_octet == last_octet:
                    dnode_num = idx
                    break

            if dnode_num is None:
                logger.warning(f"Could not find DNode for IP {node_ip}")
                return ("DN?-L", "DNode")

            dnode_id = f"DN{dnode_num}"
            dbox_id = self.dnode_to_dbox.get(dnode_id, "DB?")

            return (f"{dbox_id}-{dnode_id}-{port_side}", "DNode")

        else:
            # CNode
            node_type = "CNode"
            # Find which CNode this is (sorted by IP)
            cnode_num = None
            for idx, cnode in enumerate(self.cnodes, start=1):
                cnode_ip_octet = self._extract_ip_last_octet(cnode)
                if cnode_ip_octet == last_octet:
                    cnode_num = idx
                    break

            if cnode_num is None:
                logger.warning(f"Could not find CNode for IP {node_ip}")
                return ("CN?-R", "CNode")

            cnode_id = f"CN{cnode_num}"
            cbox_id = self.cnode_to_cbox.get(cnode_id, "CB?")

            return (f"{cbox_id}-{cnode_id}-{port_side}", "CNode")

    def generate_switch_designation(self, switch_ip: str, port: str) -> str:
        """
        Generate standardized switch-side port designation.

        Args:
            switch_ip: Switch management IP
            port: Port name (e.g., "swp20")

        Returns:
            Switch designation (e.g., "SWA-P20")
        """
        # Find switch index (sorted by IP)
        switch_letter = None
        for idx, switch in enumerate(self.switches):
            if switch.get("mgmt_ip") == switch_ip:
                # Use A, B, C, D, ... for switch numbering
                switch_letter = chr(65 + idx)  # 65 = 'A'
                break

        if switch_letter is None:
            switch_letter = "?"
            logger.warning(f"Could not find switch for IP {switch_ip}")

        # Extract port number from port name (e.g., "swp20" -> "20")
        port_num = "".join(filter(str.isdigit, port))

        return f"SW{switch_letter}-P{port_num}"

    def detect_cross_connection(
        self, switch_ip: str, node_ip: str, network: str
    ) -> Tuple[bool, str]:
        """
        Detect if a connection is cross-connected (incorrect cabling).

        Expected behavior:
        - Switch-1 (SWA) → Port-A (R) → Network A
        - Switch-2 (SWB) → Port-B (L) → Network B

        Args:
            switch_ip: Switch management IP
            node_ip: Node IP address
            network: Actual network observed ("A" or "B")

        Returns:
            Tuple of (is_cross_connected, expected_network)
        """
        # Determine which switch this is
        switch_num = None
        for idx, switch in enumerate(self.switches):
            if switch.get("mgmt_ip") == switch_ip:
                switch_num = idx + 1
                break

        if switch_num is None:
            return (False, "Unknown")

        # Expected network based on switch number
        # Switch-1 (SWA) should connect to Network A
        # Switch-2 (SWB) should connect to Network B
        if switch_num == 1:
            expected_network = "A"
        elif switch_num == 2:
            expected_network = "B"
        else:
            expected_network = "Unknown"

        # Check if actual matches expected
        is_cross_connected = network != expected_network

        return (is_cross_connected, expected_network)

    def get_port_map_summary(self) -> Dict[str, Any]:
        """
        Get summary of port mapping configuration.

        Returns:
            Dict with node-to-box mapping summary
        """
        return {
            "cboxes": len(self.cboxes),
            "dboxes": len(self.dboxes),
            "cnodes": len(self.cnodes),
            "dnodes": len(self.dnodes),
            "switches": len(self.switches),
            "cnode_to_cbox": self.cnode_to_cbox,
            "dnode_to_dbox": self.dnode_to_dbox,
        }
