"""
VAST As-Built Report Generator - Data Extractor Module

This module processes and organizes data collected from the VAST API for report generation.
It transforms raw API responses into structured, report-ready data with enhanced capabilities
for rack positioning and cluster support tracking integration.

Features:
- Data validation and sanitization
- Enhanced data processing (rack heights, PSNT)
- Report section organization
- Data completeness validation
- Error handling and graceful degradation
- Support for both enhanced and legacy cluster versions

Author: Manus AI
Date: September 26, 2025
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, cast

from utils.logger import get_logger


@dataclass
class ReportSection:
    """Data class for report section information."""

    name: str
    title: str
    data: Dict[str, Any]
    completeness: float  # Percentage of data available
    status: str  # 'complete', 'partial', 'missing', 'error'


@dataclass
class ClusterSummary:
    """Data class for cluster summary information."""

    name: str
    guid: str
    version: str
    state: str
    license: str
    psnt: Optional[str] = None
    enhanced_features: Dict[str, bool] = None
    collection_timestamp: Optional[datetime] = None
    # Additional cluster details from /api/v7/clusters/ endpoint
    cluster_id: Optional[str] = None
    mgmt_vip: Optional[str] = None
    build: Optional[str] = None
    uptime: Optional[str] = None
    online_start_time: Optional[str] = None
    deployment_time: Optional[str] = None
    url: Optional[str] = None
    # Cluster operational states and management details
    ssd_raid_state: Optional[str] = None
    nvram_raid_state: Optional[str] = None
    memory_raid_state: Optional[str] = None
    leader_state: Optional[str] = None
    leader_cnode: Optional[str] = None
    mgmt_cnode: Optional[str] = None
    mgmt_inner_vip: Optional[str] = None
    mgmt_inner_vip_cnode: Optional[str] = None
    # Cluster feature flags and configuration
    enabled: Optional[bool] = None
    enable_similarity: Optional[bool] = None
    is_wb_raid_enabled: Optional[bool] = None
    wb_raid_layout: Optional[str] = None
    dbox_ha_support: Optional[bool] = None
    enable_rack_level_resiliency: Optional[bool] = None
    disable_metrics: Optional[bool] = None
    capacity_base_10: Optional[bool] = None  # Capacity display format (True=TB, False=TiB)
    # Storage capacity and usage metrics
    usable_capacity_tb: Optional[float] = None
    free_usable_capacity_tb: Optional[float] = None
    drr_text: Optional[str] = None
    physical_space_tb: Optional[float] = None
    physical_space_in_use_tb: Optional[float] = None
    free_physical_space_tb: Optional[float] = None
    physical_space_in_use_percent: Optional[float] = None
    logical_space_tb: Optional[float] = None
    logical_space_in_use_tb: Optional[float] = None
    free_logical_space_tb: Optional[float] = None
    logical_space_in_use_percent: Optional[float] = None
    # Encryption configuration
    enable_encryption: Optional[bool] = None
    s3_enable_only_aes_ciphers: Optional[bool] = None
    encryption_type: Optional[str] = None
    ekm_servers: Optional[str] = None
    ekm_address: Optional[str] = None
    ekm_port: Optional[int] = None
    ekm_auth_domain: Optional[str] = None
    secondary_ekm_address: Optional[str] = None
    secondary_ekm_port: Optional[int] = None
    # Network configuration
    management_vips: Optional[str] = None
    external_gateways: Optional[str] = None
    dns: Optional[str] = None
    ntp: Optional[str] = None
    ext_netmask: Optional[str] = None
    auto_ports_ext_iface: Optional[str] = None
    b2b_ipmi: Optional[bool] = None
    eth_mtu: Optional[int] = None
    ib_mtu: Optional[int] = None
    nb_eth_mtu: Optional[int] = None
    ipmi_gateway: Optional[str] = None
    ipmi_netmask: Optional[str] = None


@dataclass
class HardwareInventory:
    """Data class for hardware inventory with enhanced positioning."""

    cnodes: List[Dict[str, Any]]
    dnodes: List[Dict[str, Any]]
    cboxes: Dict[str, Any]
    dboxes: Dict[str, Any]
    total_nodes: int
    rack_positions_available: bool
    physical_layout: Optional[Dict[str, Any]] = None
    switches: Optional[List[Dict[str, Any]]] = None
    eboxes: Dict[str, Any] = field(default_factory=dict)


class DataExtractionError(Exception):
    """Custom exception for data extraction errors."""

    pass


class VastDataExtractor:
    """
    VAST Data Extractor for processing and organizing API data.

    This class transforms raw VAST API responses into structured, report-ready data
    with enhanced capabilities for rack positioning and cluster support tracking.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the data extractor.

        Args:
            config (Dict[str, Any], optional): Configuration dictionary
        """
        self.logger = get_logger(__name__)
        self.config = config or {}

        # Data collection configuration
        self.data_config = self.config.get("data_collection", {})
        self.validate_responses = self.data_config.get("validate_responses", True)
        self.graceful_degradation = self.data_config.get("graceful_degradation", True)

        # Report sections configuration
        self.sections_config = self.data_config.get("sections", {})

        self.logger.info("Data extractor initialized with enhanced processing capabilities")

    def _empty_hardware_inventory(self) -> HardwareInventory:
        """Return a minimal HardwareInventory when the section is disabled."""
        return HardwareInventory(
            cnodes=[],
            dnodes=[],
            cboxes={},
            dboxes={},
            eboxes={},
            total_nodes=0,
            rack_positions_available=False,
            physical_layout={},
            switches=[],
        )

    def extract_cluster_summary(self, raw_data: Dict[str, Any]) -> ClusterSummary:
        """
        Extract and process cluster summary information.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ClusterSummary: Processed cluster summary data
        """
        try:
            self.logger.info("Extracting cluster summary information")

            cluster_info = raw_data.get("cluster_info", {})
            enhanced_features = raw_data.get("enhanced_features", {})

            # Extract basic cluster information
            summary = ClusterSummary(
                name=cluster_info.get("name", "Unknown"),
                guid=cluster_info.get("guid", "Unknown"),
                version=cluster_info.get("version", "Unknown"),
                state=cluster_info.get("state", "Unknown"),
                license=cluster_info.get("license", "Unknown"),
                psnt=cluster_info.get("psnt"),
                enhanced_features=enhanced_features,
                collection_timestamp=(
                    datetime.fromtimestamp(raw_data.get("collection_timestamp", 0))
                    if raw_data.get("collection_timestamp")
                    else None
                ),
                # Additional cluster details from /api/v7/clusters/ endpoint
                cluster_id=str(cluster_info.get("cluster_id", "Unknown")),
                mgmt_vip=cluster_info.get("mgmt_vip", "Unknown"),
                build=cluster_info.get("build", "Unknown"),
                uptime=cluster_info.get("uptime", "Unknown"),
                online_start_time=cluster_info.get("online_start_time", "Unknown"),
                deployment_time=cluster_info.get("deployment_time", "Unknown"),
                url=cluster_info.get("url", "Unknown"),
                # Cluster operational states and management details
                ssd_raid_state=cluster_info.get("ssd_raid_state", "Unknown"),
                nvram_raid_state=cluster_info.get("nvram_raid_state", "Unknown"),
                memory_raid_state=cluster_info.get("memory_raid_state", "Unknown"),
                leader_state=cluster_info.get("leader_state", "Unknown"),
                leader_cnode=cluster_info.get("leader_cnode", "Unknown"),
                mgmt_cnode=cluster_info.get("mgmt_cnode", "Unknown"),
                mgmt_inner_vip=cluster_info.get("mgmt_inner_vip", "Unknown"),
                mgmt_inner_vip_cnode=cluster_info.get("mgmt_inner_vip_cnode", "Unknown"),
                # Cluster feature flags and configuration
                enabled=cluster_info.get("enabled"),
                enable_similarity=cluster_info.get("enable_similarity"),
                is_wb_raid_enabled=cluster_info.get("is_wb_raid_enabled"),
                wb_raid_layout=cluster_info.get("wb_raid_layout", "Unknown"),
                dbox_ha_support=cluster_info.get("dbox_ha_support"),
                enable_rack_level_resiliency=cluster_info.get("enable_rack_level_resiliency"),
                disable_metrics=cluster_info.get("disable_metrics"),
                capacity_base_10=cluster_info.get("capacity_base_10"),
                # Storage capacity and usage metrics
                usable_capacity_tb=cluster_info.get("usable_capacity_tb"),
                free_usable_capacity_tb=cluster_info.get("free_usable_capacity_tb"),
                drr_text=cluster_info.get("drr_text", "Unknown"),
                physical_space_tb=cluster_info.get("physical_space_tb"),
                physical_space_in_use_tb=cluster_info.get("physical_space_in_use_tb"),
                free_physical_space_tb=cluster_info.get("free_physical_space_tb"),
                physical_space_in_use_percent=cluster_info.get("physical_space_in_use_percent"),
                logical_space_tb=cluster_info.get("logical_space_tb"),
                logical_space_in_use_tb=cluster_info.get("logical_space_in_use_tb"),
                free_logical_space_tb=cluster_info.get("free_logical_space_tb"),
                logical_space_in_use_percent=cluster_info.get("logical_space_in_use_percent"),
                # Encryption configuration
                enable_encryption=cluster_info.get("enable_encryption"),
                s3_enable_only_aes_ciphers=cluster_info.get("s3_enable_only_aes_ciphers"),
                encryption_type=cluster_info.get("encryption_type", "Unknown"),
                ekm_servers=cluster_info.get("ekm_servers", "Unknown"),
                ekm_address=cluster_info.get("ekm_address", "Unknown"),
                ekm_port=cluster_info.get("ekm_port"),
                ekm_auth_domain=cluster_info.get("ekm_auth_domain", "Unknown"),
                secondary_ekm_address=cluster_info.get("secondary_ekm_address"),
                secondary_ekm_port=cluster_info.get("secondary_ekm_port"),
                # Network configuration
                management_vips=cluster_info.get("management_vips", "Unknown"),
                external_gateways=cluster_info.get("external_gateways", "Unknown"),
                dns=cluster_info.get("dns", "Unknown"),
                ntp=cluster_info.get("ntp", "Unknown"),
                ext_netmask=cluster_info.get("ext_netmask", "Unknown"),
                auto_ports_ext_iface=cluster_info.get("auto_ports_ext_iface", "Unknown"),
                b2b_ipmi=cluster_info.get("b2b_ipmi"),
                eth_mtu=cluster_info.get("eth_mtu"),
                ib_mtu=cluster_info.get("ib_mtu"),
                nb_eth_mtu=cluster_info.get("nb_eth_mtu"),
                ipmi_gateway=cluster_info.get("ipmi_gateway", "Unknown"),
                ipmi_netmask=cluster_info.get("ipmi_netmask", "Unknown"),
            )

            # Validate data completeness
            completeness = self._calculate_completeness(
                [
                    summary.name != "Unknown",
                    summary.guid != "Unknown",
                    summary.version != "Unknown",
                    summary.state != "Unknown",
                    summary.license != "Unknown",
                    summary.cluster_id != "Unknown",
                    summary.mgmt_vip != "Unknown",
                    summary.build != "Unknown",
                    summary.uptime != "Unknown",
                    summary.online_start_time != "Unknown",
                    summary.deployment_time != "Unknown",
                    summary.ssd_raid_state != "Unknown",
                    summary.nvram_raid_state != "Unknown",
                    summary.memory_raid_state != "Unknown",
                    summary.leader_state != "Unknown",
                    summary.leader_cnode != "Unknown",
                    summary.mgmt_cnode != "Unknown",
                    summary.mgmt_inner_vip != "Unknown",
                    summary.mgmt_inner_vip_cnode != "Unknown",
                    summary.wb_raid_layout != "Unknown",
                ]
            )

            if completeness < 0.8:
                self.logger.warning(f"Cluster summary completeness: {completeness:.1%}")

            self.logger.info(f"Cluster summary extracted: {summary.name} (v{summary.version})")
            return summary

        except Exception as e:
            self.logger.error(f"Error extracting cluster summary: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract cluster summary: {e}")
            return ClusterSummary(
                name="Error",
                guid="Error",
                version="Error",
                state="Error",
                license="Error",
                cluster_id="Error",
                mgmt_vip="Error",
                build="Error",
                uptime="Error",
                online_start_time="Error",
                deployment_time="Error",
                url="Error",
                ssd_raid_state="Error",
                nvram_raid_state="Error",
                memory_raid_state="Error",
                leader_state="Error",
                leader_cnode="Error",
                mgmt_cnode="Error",
                mgmt_inner_vip="Error",
                mgmt_inner_vip_cnode="Error",
                wb_raid_layout="Error",
            )

    @staticmethod
    def _normalize_boxes_to_dict(boxes: Any) -> Dict[str, Any]:
        """Normalize box data to a dict keyed by name. Accepts list or dict."""
        if isinstance(boxes, dict):
            return boxes
        if isinstance(boxes, list):
            return {b.get("name") or str(b.get("id", i)): b for i, b in enumerate(boxes)}
        return {}

    @staticmethod
    def _normalize_to_list(items: Any) -> List[Any]:
        """Normalize to a list. Accepts list or dict (uses values). Ensures safe iteration."""
        if items is None:
            return []
        if isinstance(items, list):
            return items
        if isinstance(items, dict):
            return list(items.values())
        return []

    def extract_hardware_inventory(self, raw_data: Dict[str, Any]) -> HardwareInventory:
        """
        Extract and process hardware inventory with enhanced positioning.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            HardwareInventory: Processed hardware inventory data
        """
        try:
            self.logger.info("Extracting hardware inventory with enhanced positioning")

            hardware_data = raw_data.get("hardware", {}) or {}
            enhanced_features = raw_data.get("enhanced_features", {})

            # Process CNodes (accept list or dict of items)
            cnodes_raw = self._normalize_to_list(hardware_data.get("cnodes"))
            cnodes = []
            for cnode in cnodes_raw:
                if isinstance(cnode, dict):
                    processed_cnode = self._process_hardware_node(cnode, "cnode")
                    cnodes.append(processed_cnode)

            # Process DNodes (accept list or dict of items)
            dnodes_raw = self._normalize_to_list(hardware_data.get("dnodes"))
            dnodes = []
            for dnode in dnodes_raw:
                if isinstance(dnode, dict):
                    processed_dnode = self._process_hardware_node(dnode, "dnode")
                    dnodes.append(processed_dnode)

            # Process CBoxes - enrich with hardware type from CNodes (accept list or dict)
            cboxes = self._normalize_boxes_to_dict(hardware_data.get("cboxes", {}))

            # Build cbox_id to cbox_name mapping
            cbox_id_to_name = {}
            for cbox_name, cbox_data in cboxes.items():
                cbox_id = cbox_data.get("id")
                if cbox_id:
                    cbox_id_to_name[cbox_id] = cbox_name

            # Enrich CBox data with model/hardware_type from first CNode in each CBox
            for cnode in cnodes:
                # Try box_name first, then fall back to cbox_id
                cbox_name = cnode.get("box_name", "")
                if not cbox_name:
                    # Use cbox_id to find the cbox_name
                    cbox_id = cnode.get("cbox_id")
                    if cbox_id and cbox_id in cbox_id_to_name:
                        cbox_name = cbox_id_to_name[cbox_id]

                if cbox_name and cbox_name in cboxes:
                    # Only set if not already set (use first CNode's model for the CBox)
                    if "model" not in cboxes[cbox_name] or not cboxes[cbox_name].get("model"):
                        # Extract model from box_vendor field (e.g., "Broadwell, single dual-port NIC" -> "Broadwell")
                        box_vendor = cnode.get("box_vendor", "")
                        model = box_vendor.split(",")[0].strip() if box_vendor else "Unknown"
                        cboxes[cbox_name]["model"] = model
                        cboxes[cbox_name]["hardware_type"] = model.lower()
                        self.logger.debug(f"Enriched CBox {cbox_name} with model: {model}")

            # Process DBoxes - enrich with hardware type from DNodes (accept list or dict)
            dboxes = self._normalize_boxes_to_dict(hardware_data.get("dboxes", {}))

            # Build dbox_id to dbox_name mapping
            dbox_id_to_name = {}
            for dbox_name, dbox_data in dboxes.items():
                dbox_id = dbox_data.get("id")
                if dbox_id:
                    dbox_id_to_name[dbox_id] = dbox_name

            # Enrich DBox data with model/hardware_type from first DNode in each DBox
            for dnode in dnodes:
                # Try box_name first, then fall back to dbox_id
                dbox_name = dnode.get("box_name", "")
                if not dbox_name:
                    # Use dbox_id to find the dbox_name
                    dbox_id = dnode.get("dbox_id")
                    if dbox_id and dbox_id in dbox_id_to_name:
                        dbox_name = dbox_id_to_name[dbox_id]

                if dbox_name and dbox_name in dboxes:
                    # Only set if not already set (use first DNode's model for the DBox)
                    if "model" not in dboxes[dbox_name] or not dboxes[dbox_name].get("model"):
                        # DBoxes already have hardware_type from API, but ensure model is set
                        if not dboxes[dbox_name].get("hardware_type"):
                            box_vendor = dnode.get("box_vendor", "")
                            model = box_vendor.split(",")[0].strip() if box_vendor else "Unknown"
                            dboxes[dbox_name]["hardware_type"] = model.lower()
                            self.logger.debug(f"Enriched DBox {dbox_name} with hardware_type: {model.lower()}")

            # Process EBoxes (enclosures; may be empty; accept list or dict)
            eboxes = self._normalize_boxes_to_dict(hardware_data.get("eboxes", {}))

            # Process Switches (switch_inventory may be dict or list in fixtures)
            switch_inventory = raw_data.get("switch_inventory", {})
            if isinstance(switch_inventory, dict):
                switches = switch_inventory.get("switches", [])
            else:
                switches = switch_inventory if isinstance(switch_inventory, list) else []

            # Calculate total nodes
            total_nodes = len(cnodes) + len(dnodes)

            # Check if rack positions are available by examining actual data
            # A node has rack position if it has rack_u, rack_unit, or position field
            has_cnode_positions = any(
                node.get("rack_u") or node.get("rack_unit") or node.get("position") for node in cnodes
            )
            has_dbox_positions = any(dbox_info.get("rack_unit") for dbox_info in cboxes.values())

            # Rack positions available if any node has position data
            rack_positions_available = has_cnode_positions or has_dbox_positions

            # Also consider the enhanced features flag as a fallback
            if not rack_positions_available:
                rack_positions_available = enhanced_features.get("rack_height_supported", False)

            # Generate physical layout if rack positions available
            physical_layout = None
            if rack_positions_available:
                physical_layout = self._generate_physical_layout(cnodes, dnodes)

            inventory = HardwareInventory(
                cnodes=cnodes,
                dnodes=dnodes,
                cboxes=cboxes,
                dboxes=dboxes,
                eboxes=eboxes,
                total_nodes=total_nodes,
                rack_positions_available=rack_positions_available,
                physical_layout=physical_layout,
                switches=switches,
            )

            self.logger.info(f"Hardware inventory extracted: {total_nodes} total nodes")
            if rack_positions_available:
                self.logger.info("Rack positioning data included in inventory")

            return inventory

        except Exception as e:
            self.logger.error(f"Error extracting hardware inventory: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract hardware inventory: {e}")
            return HardwareInventory(
                cnodes=[],
                dnodes=[],
                cboxes={},
                dboxes={},
                eboxes={},
                total_nodes=0,
                rack_positions_available=False,
                physical_layout=None,
                switches=[],
            )

    def _process_hardware_node(self, node_data: Dict[str, Any], node_type: str) -> Dict[str, Any]:
        """
        Process individual hardware node data.

        Args:
            node_data (Dict[str, Any]): Raw node data
            node_type (str): Type of node ('cnode' or 'dnode')

        Returns:
            Dict[str, Any]: Processed node data
        """
        processed_node = {
            "id": node_data.get("id", "Unknown"),
            "type": node_type,
            "name": node_data.get("name"),  # Programmatically generated name (e.g., cnode-3-10, dnode-3-112)
            "hostname": node_data.get("hostname"),  # Network hostname
            "model": node_data.get("model", "Unknown"),
            "serial_number": node_data.get("serial_number", node_data.get("sn", "Unknown")),  # sn = Dell Asset Tag
            "status": node_data.get("status", "unknown"),
            "rack_position": node_data.get("rack_position"),
            "rack_position_available": node_data.get("rack_position") is not None,
            "box_vendor": node_data.get("box_vendor", "Unknown"),
            "cbox_id": node_data.get("cbox_id"),
            "ebox_id": node_data.get("ebox_id"),
            # Network configuration fields (from /api/v7/cnodes/ and /api/v7/dnodes/)
            "mgmt_ip": node_data.get("mgmt_ip"),
            "ipmi_ip": node_data.get("ipmi_ip"),
            "os_version": node_data.get("os_version"),
        }

        # For cnodes, capture is_mgmt (VMS Host)
        if node_type == "cnode":
            processed_node["is_mgmt"] = node_data.get("is_mgmt", False)

        # For dnodes, also capture hardware_type, dbox_id, and position for rack diagram
        if node_type == "dnode":
            processed_node["hardware_type"] = node_data.get("hardware_type", "Unknown")
            processed_node["dbox_id"] = node_data.get("dbox_id")
            processed_node["position"] = node_data.get("position") or ""

        # Add enhanced information if available
        if processed_node["rack_position"] is not None:
            processed_node["rack_u"] = f"U{processed_node['rack_position']}"
            processed_node["positioning_note"] = "Automated via API"
        else:
            processed_node["rack_u"] = "Manual Entry Required"
            processed_node["positioning_note"] = "Not available for this cluster version"

        return processed_node

    def _generate_physical_layout(self, cnodes: List[Dict], dnodes: List[Dict]) -> Dict[str, Any]:
        """
        Generate physical rack layout information.

        Args:
            cnodes (List[Dict]): Processed CNode data
            dnodes (List[Dict]): Processed DNode data

        Returns:
            Dict[str, Any]: Physical layout information
        """
        try:
            # Group nodes by rack position
            rack_layout: dict[str, Any] = {}

            # Process CNodes
            for cnode in cnodes:
                if cnode.get("rack_position") is not None:
                    pos = cnode["rack_position"]
                    if pos not in rack_layout:
                        rack_layout[pos] = {"cnodes": [], "dnodes": []}
                    rack_layout[pos]["cnodes"].append(cnode)

            # Process DNodes
            for dnode in dnodes:
                if dnode.get("rack_position") is not None:
                    pos = dnode["rack_position"]
                    if pos not in rack_layout:
                        rack_layout[pos] = {"cnodes": [], "dnodes": []}
                    rack_layout[pos]["dnodes"].append(dnode)

            # Calculate layout statistics
            occupied_positions = len(rack_layout)
            min_position = min(rack_layout.keys()) if rack_layout else 0
            max_position = max(rack_layout.keys()) if rack_layout else 0

            layout_info = {
                "rack_layout": rack_layout,
                "statistics": {
                    "occupied_positions": occupied_positions,
                    "min_position": min_position,
                    "max_position": max_position,
                    "total_cnodes": len(cnodes),
                    "total_dnodes": len(dnodes),
                },
                "generated_timestamp": datetime.now().isoformat(),
            }

            self.logger.debug(f"Physical layout generated: {occupied_positions} occupied positions")
            return layout_info

        except Exception as e:
            self.logger.error(f"Error generating physical layout: {e}")
            return None

    def extract_network_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process network configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed network configuration section
        """
        try:
            self.logger.info("Extracting network configuration")

            network_data = raw_data.get("network", {})

            # Process DNS configuration
            dns_config = self._process_dns_configuration(network_data.get("dns"))

            # Process NTP configuration
            ntp_config = self._process_ntp_configuration(network_data.get("ntp"))

            # Process VIP pools
            vippool_config = self._process_vippool_configuration(network_data.get("vippools"))

            # Combine all network data
            processed_data = {
                "dns": dns_config,
                "ntp": ntp_config,
                "vippools": vippool_config,
                "extraction_timestamp": datetime.now().isoformat(),
            }

            # Calculate completeness
            completeness = self._calculate_completeness(
                [
                    dns_config is not None,
                    ntp_config is not None,
                    vippool_config is not None,
                ]
            )

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name="network_configuration",
                title="Network Configuration",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(f"Network configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting network configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract network configuration: {e}")
            return ReportSection(
                name="network_configuration",
                title="Network Configuration",
                data={},
                completeness=0.0,
                status="error",
            )

    def extract_cluster_network_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process cluster-wide network configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed cluster network configuration section
        """
        try:
            self.logger.info("Extracting cluster network configuration")

            # Get cluster network data from both cluster_network and cluster_summary
            cluster_network_data = raw_data.get("cluster_network", {})
            cluster_summary = raw_data.get("cluster_summary", {})

            # Process cluster network configuration - prioritize cluster_network data from API
            processed_data = {
                "management_vips": self._format_network_value(
                    cluster_network_data.get("management_vips", []),
                    cluster_summary.get("management_vips", "Not Configured"),
                ),
                "external_gateways": self._format_network_value(
                    cluster_network_data.get("external_gateways", []),
                    cluster_summary.get("external_gateways", "Not Configured"),
                ),
                "dns": self._format_network_value(
                    cluster_network_data.get("dns", []),
                    cluster_summary.get("dns", "Not Configured"),
                ),
                "ntp": self._format_network_value(
                    cluster_network_data.get("ntp", []),
                    cluster_summary.get("ntp", "Not Configured"),
                ),
                "mgmt_vip": cluster_summary.get("mgmt_vip", "Not Configured"),
                "mgmt_inner_vip": cluster_summary.get("mgmt_inner_vip", "Not Configured"),
                "mgmt_inner_vip_cnode": cluster_summary.get("mgmt_inner_vip_cnode", "Not Configured"),
                "ext_netmask": cluster_network_data.get(
                    "ext_netmask", cluster_summary.get("ext_netmask", "Not Configured")
                ),
                "auto_ports_ext_iface": cluster_network_data.get(
                    "auto_ports_ext_iface",
                    cluster_summary.get("auto_ports_ext_iface", "Not Configured"),
                ),
                "b2b_ipmi": cluster_network_data.get("b2b_ipmi", cluster_summary.get("b2b_ipmi", False)),
                "eth_mtu": cluster_network_data.get("eth_mtu", cluster_summary.get("eth_mtu", "Not Configured")),
                "ib_mtu": cluster_network_data.get("ib_mtu", cluster_summary.get("ib_mtu", "Not Configured")),
                "nb_eth_mtu": cluster_network_data.get(
                    "nb_eth_mtu", cluster_summary.get("nb_eth_mtu", "Not Configured")
                ),
                "ipmi_gateway": cluster_network_data.get(
                    "ipmi_gateway",
                    cluster_summary.get("ipmi_gateway", "Not Configured"),
                ),
                "ipmi_netmask": cluster_network_data.get(
                    "ipmi_netmask",
                    cluster_summary.get("ipmi_netmask", "Not Configured"),
                ),
                "net_type": cluster_network_data.get("net_type", cluster_summary.get("net_type", "Not Configured")),
                "extraction_timestamp": datetime.now().isoformat(),
            }

            # Calculate completeness based on configured vs not configured
            completeness = self._calculate_completeness(
                [
                    processed_data["management_vips"] != "Not Configured",
                    processed_data["external_gateways"] != "Not Configured",
                    processed_data["dns"] != "Not Configured",
                    processed_data["ntp"] != "Not Configured",
                    processed_data["mgmt_vip"] != "Not Configured",
                    processed_data["ext_netmask"] != "Not Configured",
                    processed_data["eth_mtu"] != "Not Configured",
                    processed_data["ib_mtu"] != "Not Configured",
                ]
            )

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name="cluster_network_configuration",
                title="Cluster Network Configuration",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(f"Cluster network configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting cluster network configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract cluster network configuration: {e}")
            return ReportSection(
                name="cluster_network_configuration",
                title="Cluster Network Configuration",
                data={},
                completeness=0.0,
                status="error",
            )

    def extract_cnodes_network_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process CNodes network configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed CNodes network configuration section
        """
        try:
            self.logger.info("Extracting CNodes network configuration")

            cnodes_network_data = raw_data.get("cnodes_network", [])

            # Process CNodes network configuration
            processed_cnodes = []
            for cnode in cnodes_network_data:
                processed_cnode = {
                    "id": cnode.get("id", "Unknown"),
                    "hostname": cnode.get("hostname", "Unknown"),
                    "mgmt_ip": cnode.get("mgmt_ip", "Unknown"),
                    "ipmi_ip": cnode.get("ipmi_ip", "Unknown"),
                    "box_vendor": cnode.get("box_vendor", "Unknown"),
                    "vast_os": cnode.get("vast_os", "Unknown"),
                    "node_type": cnode.get("node_type", "Unknown"),
                    "box_name": cnode.get("box_name", "Unknown"),
                    "is_vms_host": cnode.get("is_vms_host", False),
                    "tpm_boot_dev_encryption_supported": cnode.get("tpm_boot_dev_encryption_supported", False),
                    "tpm_boot_dev_encryption_enabled": cnode.get("tpm_boot_dev_encryption_enabled", False),
                    "single_nic": cnode.get("single_nic", False),
                    "net_type": cnode.get("net_type", "Unknown"),
                }
                processed_cnodes.append(processed_cnode)

            processed_data = {
                "cnodes": processed_cnodes,
                "total_cnodes": len(processed_cnodes),
                "extraction_timestamp": datetime.now().isoformat(),
            }

            # Calculate completeness
            completeness = self._calculate_completeness(
                [
                    len(processed_cnodes) > 0,
                    all(cnode.get("hostname") != "Unknown" for cnode in processed_cnodes),
                    all(cnode.get("mgmt_ip") != "Unknown" for cnode in processed_cnodes),
                    all(cnode.get("vast_os") != "Unknown" for cnode in processed_cnodes),
                ]
            )

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name="cnodes_network_configuration",
                title="CNodes Network Configuration",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(
                f"CNodes network configuration extracted: {len(processed_cnodes)} CNodes (completeness: {completeness:.1%})"
            )
            return section

        except Exception as e:
            self.logger.error(f"Error extracting CNodes network configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract CNodes network configuration: {e}")
            return ReportSection(
                name="cnodes_network_configuration",
                title="CNodes Network Configuration",
                data={},
                completeness=0.0,
                status="error",
            )

    def extract_dnodes_network_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process DNodes network configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed DNodes network configuration section
        """
        try:
            self.logger.info("Extracting DNodes network configuration")

            dnodes_network_data = raw_data.get("dnodes_network", [])

            # Process DNodes network configuration
            processed_dnodes = []
            for dnode in dnodes_network_data:
                processed_dnode = {
                    "id": dnode.get("id", "Unknown"),
                    "hostname": dnode.get("hostname", "Unknown"),
                    "mgmt_ip": dnode.get("mgmt_ip", "Unknown"),
                    "ipmi_ip": dnode.get("ipmi_ip", "Unknown"),
                    "box_vendor": dnode.get("box_vendor", "Unknown"),
                    "vast_os": dnode.get("vast_os", "Unknown"),
                    "node_type": dnode.get("node_type", "Unknown"),
                    "position": dnode.get("position", "Unknown"),
                    "box_name": dnode.get("box_name", "Unknown"),
                    "is_ceres": dnode.get("is_ceres", False),
                    "is_ceres_v2": dnode.get("is_ceres_v2", False),
                    "net_type": dnode.get("net_type", "Unknown"),
                }
                processed_dnodes.append(processed_dnode)

            processed_data = {
                "dnodes": processed_dnodes,
                "total_dnodes": len(processed_dnodes),
                "extraction_timestamp": datetime.now().isoformat(),
            }

            # Calculate completeness
            completeness = self._calculate_completeness(
                [
                    len(processed_dnodes) > 0,
                    all(dnode.get("hostname") != "Unknown" for dnode in processed_dnodes),
                    all(dnode.get("mgmt_ip") != "Unknown" for dnode in processed_dnodes),
                    all(dnode.get("vast_os") != "Unknown" for dnode in processed_dnodes),
                ]
            )

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name="dnodes_network_configuration",
                title="DNodes Network Configuration",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(
                f"DNodes network configuration extracted: {len(processed_dnodes)} DNodes (completeness: {completeness:.1%})"
            )
            return section

        except Exception as e:
            self.logger.error(f"Error extracting DNodes network configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract DNodes network configuration: {e}")
            return ReportSection(
                name="dnodes_network_configuration",
                title="DNodes Network Configuration",
                data={},
                completeness=0.0,
                status="error",
            )

    def _process_dns_configuration(self, dns_data: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Process DNS configuration data."""
        if not dns_data:
            return None

        # Handle both list and dictionary responses
        if isinstance(dns_data, list):
            dns_data = dns_data[0] if dns_data else None
            if not dns_data:
                return None

        return {
            "servers": dns_data.get("servers", []),
            "search_domains": dns_data.get("search_domains", []),
            "enabled": dns_data.get("enabled", False),
            "source": "API",
        }

    def _process_ntp_configuration(self, ntp_data: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Process NTP configuration data."""
        if not ntp_data:
            return None

        # Handle both list and dictionary responses
        if isinstance(ntp_data, list):
            ntp_data = ntp_data[0] if ntp_data else None
            if not ntp_data:
                return None

        return {
            "servers": ntp_data.get("servers", []),
            "enabled": ntp_data.get("enabled", False),
            "source": "API",
        }

    def _process_vippool_configuration(self, vippool_data: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Process VIP pool configuration data."""
        if not vippool_data:
            return None

        # Handle both list and dictionary responses
        if isinstance(vippool_data, list):
            pools = vippool_data
        else:
            pools = vippool_data.get("pools", [])

        return {"pools": pools, "total_pools": len(pools), "source": "API"}

    def extract_logical_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process logical configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed logical configuration section
        """
        try:
            self.logger.info("Extracting logical configuration")

            logical_data = raw_data.get("logical", {})

            # Process tenants
            tenants = self._process_tenants(logical_data.get("tenants"))

            # Process views
            views = self._process_views(logical_data.get("views"))

            # Process view policies
            view_policies = self._process_view_policies(logical_data.get("viewpolicies"))

            # Combine all logical data
            processed_data = {
                "tenants": tenants,
                "views": views,
                "view_policies": view_policies,
                "extraction_timestamp": datetime.now().isoformat(),
            }

            # Calculate completeness
            completeness = self._calculate_completeness(
                [tenants is not None, views is not None, view_policies is not None]
            )

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name="logical_configuration",
                title="Logical Configuration",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(f"Logical configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting logical configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract logical configuration: {e}")
            return ReportSection(
                name="logical_configuration",
                title="Logical Configuration",
                data={},
                completeness=0.0,
                status="error",
            )

    def _process_tenants(self, tenants_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process tenants data."""
        if not tenants_data:
            return None

        processed_tenants = []
        for tenant in tenants_data:
            processed_tenant = {
                "name": tenant.get("name", "Unknown"),
                "id": tenant.get("id", "Unknown"),
                "state": tenant.get("state", "Unknown"),
                "source": "API",
            }
            processed_tenants.append(processed_tenant)

        return {
            "tenants": processed_tenants,
            "total_count": len(processed_tenants),
            "source": "API",
        }

    def _process_views(self, views_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process views data."""
        if not views_data:
            return None

        processed_views = []
        for view in views_data:
            processed_view = {
                "name": view.get("name", "Unknown"),
                "path": view.get("path", "Unknown"),
                "state": view.get("state", "Unknown"),
                "source": "API",
            }
            processed_views.append(processed_view)

        return {
            "views": processed_views,
            "total_count": len(processed_views),
            "source": "API",
        }

    def _process_view_policies(self, policies_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process view policies data."""
        if not policies_data:
            return None

        processed_policies = []
        for policy in policies_data:
            processed_policy = {
                "name": policy.get("name", "Unknown"),
                "type": policy.get("type", "Unknown"),
                "state": policy.get("state", "Unknown"),
                "source": "API",
            }
            processed_policies.append(processed_policy)

        return {
            "policies": processed_policies,
            "total_count": len(processed_policies),
            "source": "API",
        }

    def extract_security_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process security configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed security configuration section
        """
        try:
            self.logger.info("Extracting security configuration")

            security_data = raw_data.get("security", {})

            # Process Active Directory
            ad_config = self._process_ad_configuration(security_data.get("activedirectory"))

            # Process LDAP
            ldap_config = self._process_ldap_configuration(security_data.get("ldap"))

            # Process NIS
            nis_config = self._process_nis_configuration(security_data.get("nis"))

            # Combine all security data
            processed_data = {
                "active_directory": ad_config,
                "ldap": ldap_config,
                "nis": nis_config,
                "extraction_timestamp": datetime.now().isoformat(),
            }

            # Calculate completeness
            completeness = self._calculate_completeness(
                [ad_config is not None, ldap_config is not None, nis_config is not None]
            )

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name="security_configuration",
                title="Security & Authentication",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(f"Security configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting security configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract security configuration: {e}")
            return ReportSection(
                name="security_configuration",
                title="Security & Authentication",
                data={},
                completeness=0.0,
                status="error",
            )

    def _process_ad_configuration(self, ad_data: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Process Active Directory configuration."""
        if not ad_data:
            return None

        # Handle both list and dictionary responses
        if isinstance(ad_data, list):
            ad_data = ad_data[0] if ad_data else None
            if not ad_data:
                return None

        return {
            "enabled": ad_data.get("enabled", False),
            "domain": ad_data.get("domain", "Unknown"),
            "servers": ad_data.get("servers", []),
            "source": "API",
        }

    def _process_ldap_configuration(self, ldap_data: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Process LDAP configuration."""
        if not ldap_data:
            return None

        # Handle both list and dictionary responses
        if isinstance(ldap_data, list):
            ldap_data = ldap_data[0] if ldap_data else None
            if not ldap_data:
                return None

        return {
            "enabled": ldap_data.get("enabled", False),
            "servers": ldap_data.get("servers", []),
            "base_dn": ldap_data.get("base_dn", "Unknown"),
            "source": "API",
        }

    def _process_nis_configuration(self, nis_data: Optional[Any]) -> Optional[Dict[str, Any]]:
        """Process NIS configuration."""
        if not nis_data:
            return None

        # Handle both list and dictionary responses
        if isinstance(nis_data, list):
            nis_data = nis_data[0] if nis_data else None
            if not nis_data:
                return None

        return {
            "enabled": nis_data.get("enabled", False),
            "servers": nis_data.get("servers", []),
            "domain": nis_data.get("domain", "Unknown"),
            "source": "API",
        }

    def extract_data_protection_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract and process data protection configuration data.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed data protection configuration section
        """
        try:
            self.logger.info("Extracting data protection configuration")

            protection_data = raw_data.get("data_protection", {})

            # Process snapshot programs
            snapshot_config = self._process_snapshot_configuration(protection_data.get("snapprograms"))

            # Process protection policies
            policy_config = self._process_protection_policy_configuration(protection_data.get("protectionpolicies"))

            # Combine all protection data
            processed_data = {
                "snapshot_programs": snapshot_config,
                "protection_policies": policy_config,
                "extraction_timestamp": datetime.now().isoformat(),
            }

            # Calculate completeness
            completeness = self._calculate_completeness([snapshot_config is not None, policy_config is not None])

            status = self._determine_section_status(completeness)

            section = ReportSection(
                name="data_protection_configuration",
                title="Data Protection",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(f"Data protection configuration extracted (completeness: {completeness:.1%})")
            return section

        except Exception as e:
            self.logger.error(f"Error extracting data protection configuration: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract data protection configuration: {e}")
            return ReportSection(
                name="data_protection_configuration",
                title="Data Protection",
                data={},
                completeness=0.0,
                status="error",
            )

    def _process_snapshot_configuration(self, snapshot_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process snapshot programs configuration."""
        if not snapshot_data:
            return None

        processed_snapshots = []
        for snapshot in snapshot_data:
            processed_snapshot = {
                "name": snapshot.get("name", "Unknown"),
                "schedule": snapshot.get("schedule", "Unknown"),
                "enabled": snapshot.get("enabled", False),
                "source": "API",
            }
            processed_snapshots.append(processed_snapshot)

        return {
            "programs": processed_snapshots,
            "total_count": len(processed_snapshots),
            "source": "API",
        }

    def _process_protection_policy_configuration(self, policy_data: Optional[List]) -> Optional[Dict[str, Any]]:
        """Process protection policies configuration."""
        if not policy_data:
            return None

        processed_policies = []
        for policy in policy_data:
            processed_policy = {
                "name": policy.get("name", "Unknown"),
                "type": policy.get("type", "Unknown"),
                "retention": policy.get("retention", "Unknown"),
                "enabled": policy.get("enabled", False),
                "source": "API",
            }
            processed_policies.append(processed_policy)

        return {
            "policies": processed_policies,
            "total_count": len(processed_policies),
            "source": "API",
        }

    def extract_performance_metrics(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract performance metrics and capacity information.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed performance metrics data
        """
        try:
            self.logger.info("Extracting performance metrics")

            performance_data = raw_data.get("performance_metrics", {})

            processed_data = {
                "total_capacity": performance_data.get("total_capacity", "Unknown"),
                "used_capacity": performance_data.get("used_capacity", "Unknown"),
                "available_capacity": performance_data.get("available_capacity", "Unknown"),
                "utilization_percentage": performance_data.get("utilization_percentage", 0.0),
                "iops_rating": performance_data.get("iops_rating", "Unknown"),
                "throughput_rating": performance_data.get("throughput_rating", "Unknown"),
                "latency_metrics": performance_data.get("latency_metrics", {}),
                "performance_tier": performance_data.get("performance_tier", "Unknown"),
                "source": "API",
            }

            # Calculate completeness
            available_fields = sum(1 for v in processed_data.values() if v != "Unknown" and v != {})
            total_fields = len(processed_data) - 1  # Exclude 'source'
            completeness = (available_fields / total_fields) if total_fields > 0 else 0

            status = "complete" if completeness >= 80 else "partial" if completeness >= 50 else "missing"

            return ReportSection(
                name="performance_metrics",
                title="Performance Metrics & Capacity Analysis",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

        except Exception as e:
            self.logger.error(f"Error extracting performance metrics: {e}")
            return ReportSection(
                name="performance_metrics",
                title="Performance Metrics & Capacity Analysis",
                data={"error": str(e)},
                completeness=0.0,
                status="error",
            )

    def extract_licensing_info(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract licensing and compliance information.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed licensing information
        """
        try:
            self.logger.info("Extracting licensing information")

            licensing_data = raw_data.get("licensing_info", {})

            processed_data = {
                "license_type": licensing_data.get("license_type", "Unknown"),
                "license_key": licensing_data.get("license_key", "Unknown"),
                "expiration_date": licensing_data.get("expiration_date", "Unknown"),
                "licensed_features": licensing_data.get("licensed_features", []),
                "compliance_status": licensing_data.get("compliance_status", "Unknown"),
                "support_level": licensing_data.get("support_level", "Unknown"),
                "maintenance_expiry": licensing_data.get("maintenance_expiry", "Unknown"),
                "source": "API",
            }

            # Calculate completeness
            available_fields = sum(1 for v in processed_data.values() if v != "Unknown" and v != [])
            total_fields = len(processed_data) - 1  # Exclude 'source'
            completeness = (available_fields / total_fields) if total_fields > 0 else 0

            status = "complete" if completeness >= 80 else "partial" if completeness >= 50 else "missing"

            return ReportSection(
                name="licensing_info",
                title="Licensing & Compliance Information",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

        except Exception as e:
            self.logger.error(f"Error extracting licensing information: {e}")
            return ReportSection(
                name="licensing_info",
                title="Licensing & Compliance Information",
                data={"error": str(e)},
                completeness=0.0,
                status="error",
            )

    def extract_monitoring_configuration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract monitoring and alerting configuration.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed monitoring configuration
        """
        try:
            self.logger.info("Extracting monitoring configuration")

            monitoring_data = raw_data.get("monitoring_config", {})

            processed_data = {
                "snmp_config": monitoring_data.get("snmp", {}),
                "syslog_config": monitoring_data.get("syslog", {}),
                "alert_policies": monitoring_data.get("alerts", {}),
                "source": "API",
            }

            # Calculate completeness
            available_fields = sum(1 for v in processed_data.values() if v != {} and v != "Unknown")
            total_fields = len(processed_data) - 1  # Exclude 'source'
            completeness = (available_fields / total_fields) if total_fields > 0 else 0

            status = "complete" if completeness >= 80 else "partial" if completeness >= 50 else "missing"

            return ReportSection(
                name="monitoring_config",
                title="Monitoring & Alerting Configuration",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

        except Exception as e:
            self.logger.error(f"Error extracting monitoring configuration: {e}")
            return ReportSection(
                name="monitoring_config",
                title="Monitoring & Alerting Configuration",
                data={"error": str(e)},
                completeness=0.0,
                status="error",
            )

    def extract_customer_integration(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract customer environment integration information.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed customer integration data
        """
        try:
            self.logger.info("Extracting customer integration information")

            integration_data = raw_data.get("customer_integration", {})

            processed_data = {
                "network_topology": integration_data.get("network_topology", "Unknown"),
                "vlan_configuration": integration_data.get("vlan_configuration", {}),
                "firewall_rules": integration_data.get("firewall_rules", []),
                "load_balancer_config": integration_data.get("load_balancer_config", {}),
                "customer_requirements": integration_data.get("customer_requirements", []),
                "integration_timeline": integration_data.get("integration_timeline", "Unknown"),
                "source": "API",
            }

            # Calculate completeness
            available_fields = sum(1 for v in processed_data.values() if v != "Unknown" and v != {} and v != [])
            total_fields = len(processed_data) - 1  # Exclude 'source'
            completeness = (available_fields / total_fields) if total_fields > 0 else 0

            status = "complete" if completeness >= 80 else "partial" if completeness >= 50 else "missing"

            return ReportSection(
                name="customer_integration",
                title="Customer Environment Integration",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

        except Exception as e:
            self.logger.error(f"Error extracting customer integration: {e}")
            return ReportSection(
                name="customer_integration",
                title="Customer Environment Integration",
                data={"error": str(e)},
                completeness=0.0,
                status="error",
            )

    def extract_deployment_timeline(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract deployment timeline and milestones information.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed deployment timeline data
        """
        try:
            self.logger.info("Extracting deployment timeline information")

            timeline_data = raw_data.get("deployment_timeline", {})

            processed_data = {
                "deployment_phases": timeline_data.get("deployment_phases", []),
                "key_milestones": timeline_data.get("key_milestones", []),
                "testing_results": timeline_data.get("testing_results", []),
                "source": "API",
            }

            # Calculate completeness
            available_fields = sum(1 for v in processed_data.values() if v != [] and v != "Unknown")
            total_fields = len(processed_data) - 1  # Exclude 'source'
            completeness = (available_fields / total_fields) if total_fields > 0 else 0

            status = "complete" if completeness >= 80 else "partial" if completeness >= 50 else "missing"

            return ReportSection(
                name="deployment_timeline",
                title="Deployment Timeline & Milestones",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

        except Exception as e:
            self.logger.error(f"Error extracting deployment timeline: {e}")
            return ReportSection(
                name="deployment_timeline",
                title="Deployment Timeline & Milestones",
                data={"error": str(e)},
                completeness=0.0,
                status="error",
            )

    def extract_future_recommendations(self, raw_data: Dict[str, Any]) -> ReportSection:
        """
        Extract future recommendations and roadmap information.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler

        Returns:
            ReportSection: Processed future recommendations data
        """
        try:
            self.logger.info("Extracting future recommendations information")

            recommendations_data = raw_data.get("future_recommendations", {})

            processed_data = {
                "short_term": recommendations_data.get("short_term", []),
                "medium_term": recommendations_data.get("medium_term", []),
                "long_term": recommendations_data.get("long_term", []),
                "source": "API",
            }

            # Calculate completeness
            available_fields = sum(1 for v in processed_data.values() if v != [] and v != "Unknown")
            total_fields = len(processed_data) - 1  # Exclude 'source'
            completeness = (available_fields / total_fields) if total_fields > 0 else 0

            status = "complete" if completeness >= 80 else "partial" if completeness >= 50 else "missing"

            return ReportSection(
                name="future_recommendations",
                title="Future Recommendations & Roadmap",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

        except Exception as e:
            self.logger.error(f"Error extracting future recommendations: {e}")
            return ReportSection(
                name="future_recommendations",
                title="Future Recommendations & Roadmap",
                data={"error": str(e)},
                completeness=0.0,
                status="error",
            )

    def extract_port_mapping(
        self,
        raw_data: Dict[str, Any],
        use_external: bool = False,
        use_vnetmap: bool = False,
    ) -> ReportSection:
        """
        Extract and process port mapping data with enhanced designations.

        Three data sources in priority order:
        1. ``use_vnetmap`` — vnetmap output parsed by ``VNetMapParser``
        2. ``use_external`` — SSH-collected data from ``ExternalPortMapper``
        3. Static ``vnetmap_output.txt`` file (legacy fallback)

        Args:
            raw_data: Raw data from API handler
            use_external: Use external SSH collection
            use_vnetmap: Use vnetmap output parsed in app.py

        Returns:
            ReportSection: Processed port mapping section
        """
        try:
            self.logger.info("Extracting port mapping data with enhanced designations")

            from enhanced_port_mapper import EnhancedPortMapper

            # Shared hardware data for all paths
            cboxes = raw_data.get("cboxes", [])
            dboxes = raw_data.get("dboxes", [])
            cnodes = raw_data.get("cnodes", [])
            dnodes = raw_data.get("dnodes", [])
            eboxes = raw_data.get("eboxes", [])
            switch_inventory = raw_data.get("switch_inventory", {})
            switches = switch_inventory.get("switches", [])

            external_data: Optional[Dict[str, Any]] = None
            parser = None
            data_source = "Unknown"

            # --- Path 1: Vnetmap output (pre-parsed in app.py) ---
            if use_vnetmap and "port_mapping_vnetmap" in raw_data:
                self.logger.info("Using vnetmap output as port mapping source")
                vnetmap_result = raw_data["port_mapping_vnetmap"]
                topology = vnetmap_result.get("topology", [])

                enhanced_mapper = EnhancedPortMapper(
                    cboxes=cboxes,
                    dboxes=dboxes,
                    cnodes=cnodes,
                    dnodes=dnodes,
                    switches=switches,
                    eboxes=eboxes,
                    external_port_map=topology,
                )
                enhanced_data = enhanced_mapper.generate_enhanced_port_map(topology)
                data_source = "vnetmap (VAST Network Map Tool)"

                # Build IPL from vnetmap LLDP neighbors if available
                lldp_neighbors = vnetmap_result.get("lldp_neighbors", [])
                ipl_formatted = self._format_lldp_ipl(lldp_neighbors, enhanced_mapper)

                # Infer IPL when LLDP data is absent but two leaf switches exist
                if not ipl_formatted:
                    ipl_formatted = self._infer_ipl_from_switch_pair(enhanced_mapper)

            # --- Path 2: External SSH collection ---
            elif use_external and "port_mapping_external" in raw_data:
                self.logger.info("Using externally collected port mapping data")
                external_data = raw_data["port_mapping_external"]

                enhanced_mapper = EnhancedPortMapper(
                    cboxes=cboxes,
                    dboxes=dboxes,
                    cnodes=cnodes,
                    dnodes=dnodes,
                    switches=switches,
                    external_port_map=external_data["port_map"],
                    eboxes=eboxes,
                )
                enhanced_data = enhanced_mapper.generate_enhanced_port_map(external_data["port_map"])
                data_source = "External SSH collection (clush + switch CLI)"

                ipl_formatted = []
                if "ipl_connections" in external_data:
                    for ipl in external_data["ipl_connections"]:
                        sw1_designation = enhanced_mapper.generate_switch_designation(
                            ipl["switch1_ip"], ipl["switch1_port"]
                        )
                        sw2_designation = enhanced_mapper.generate_switch_designation(
                            ipl["switch2_ip"], ipl["switch2_port"]
                        )
                        ipl_formatted.append(
                            {
                                "switch_designation": sw1_designation,
                                "node_designation": sw2_designation,
                                "notes": "IPL",
                                "connection_type": "IPL",
                                "switch1_ip": ipl["switch1_ip"],
                                "switch2_ip": ipl["switch2_ip"],
                                "switch1_port": ipl["switch1_port"],
                                "switch2_port": ipl["switch2_port"],
                            }
                        )

            # --- Path 3: Static vnetmap file (legacy fallback) ---
            else:
                from vnetmap_parser import VNetMapParser

                vnetmap_file = Path("vnetmap_output.txt")
                if not vnetmap_file.exists():
                    self.logger.warning("VNetMap output file not found - port mapping unavailable")
                    return ReportSection(
                        name="port_mapping",
                        title="Port Mapping",
                        data={
                            "available": False,
                            "message": "Port mapping data not available. Use --enable-port-mapping to collect.",
                        },
                        completeness=0.0,
                        status="missing",
                    )

                parser = VNetMapParser(str(vnetmap_file))
                vnetmap_data = parser.parse()

                if not vnetmap_data.get("available"):
                    self.logger.warning(f"Failed to parse vnetmap output: {vnetmap_data.get('error')}")
                    return ReportSection(
                        name="port_mapping",
                        title="Port Mapping",
                        data=vnetmap_data,
                        completeness=0.0,
                        status="error",
                    )

                enhanced_mapper = EnhancedPortMapper(
                    cboxes=cboxes,
                    dboxes=dboxes,
                    cnodes=cnodes,
                    dnodes=dnodes,
                    switches=switches,
                    eboxes=eboxes,
                )
                enhanced_data = enhanced_mapper.generate_enhanced_port_map(vnetmap_data["topology"])
                data_source = "vnetmap file (static)"
                ipl_formatted = []

            # Legacy IPL port collection (for backward compatibility)
            ipl_ports: List[Dict[str, Any]] = []
            switch_ports = raw_data.get("switch_ports", [])
            for port in switch_ports:
                port_name = port.get("name", "")
                speed = port.get("speed", "")
                if enhanced_mapper.is_ipl_port(port_name, speed):
                    ipl_ports.append(
                        {
                            "port": port_name,
                            "switch": port.get("switch", "Unknown"),
                            "speed": speed,
                            "state": port.get("state", "Unknown"),
                            "mtu": port.get("mtu", "Unknown"),
                        }
                    )

            # Organize port map by switch
            connections_by_switch: Dict[str, Any] = {}
            if parser:
                connections_by_switch = parser.get_connections_by_switch()
                cross_connection_summary = parser.get_cross_connection_summary()
            else:
                for conn in enhanced_data["port_map"]:
                    switch = conn.get("switch_designation", "Unknown")
                    if switch not in connections_by_switch:
                        connections_by_switch[switch] = []
                    connections_by_switch[switch].append(conn)
                cross_connection_summary = (
                    "No cross-connections detected"
                    if not enhanced_data["has_cross_connections"]
                    else f"{enhanced_data['cross_connection_count']} cross-connections detected"
                )

            total_ipl_connections = (
                external_data.get("total_ipl_connections", 0) if external_data else len(ipl_formatted)
            )
            total_ipl_ports = external_data.get("total_ipl_ports", len(ipl_ports)) if external_data else len(ipl_ports)

            processed_data = {
                "available": True,
                "port_map": enhanced_data["port_map"],
                "connections_by_switch": connections_by_switch,
                "cross_connections": enhanced_data["cross_connections"],
                "has_cross_connections": enhanced_data["has_cross_connections"],
                "cross_connection_summary": cross_connection_summary,
                "cross_connection_count": enhanced_data["cross_connection_count"],
                "total_connections": enhanced_data["total_connections"],
                "ipl_connections": ipl_formatted,
                "ipl_ports": ipl_ports,
                "total_ipl_connections": total_ipl_connections,
                "total_ipl_ports": total_ipl_ports,
                "data_source": data_source,
                "partial": external_data.get("partial", False) if external_data else False,
                "partial_reason": external_data.get("partial_reason", "") if external_data else "",
                "designation_format": {
                    "node_side": "CB1-CN1-R (CBox-1/CNode-1/Port-A)",
                    "switch_side": "SWA-P12 (Switch-1/Port-12)",
                    "port_mapping": "R = Network A (Port-A), L = Network B (Port-B)",
                    "ipl_format": "SWA-P29 / SWB-P29 / IPL",
                },
            }

            completeness = 1.0 if len(enhanced_data["port_map"]) > 0 else 0.0
            status = "complete" if completeness == 1.0 else "partial"

            section = ReportSection(
                name="port_mapping",
                title="Port Mapping",
                data=processed_data,
                completeness=completeness,
                status=status,
            )

            self.logger.info(
                f"Enhanced port mapping extracted: {len(enhanced_data['port_map'])} connections, "
                f"{enhanced_data['cross_connection_count']} cross-connections, "
                f"{total_ipl_connections} IPL connections using {total_ipl_ports} ports"
            )
            return section

        except Exception as e:
            self.logger.error(f"Error extracting port mapping: {e}", exc_info=True)
            return ReportSection(
                name="port_mapping",
                title="Port Mapping",
                data={
                    "available": False,
                    "error": str(e),
                },
                completeness=0.0,
                status="error",
            )

    def _format_lldp_ipl(self, lldp_neighbors: List[Dict[str, Any]], mapper: Any) -> List[Dict[str, Any]]:
        """Format LLDP neighbor data into IPL connection entries."""
        ipl_formatted: List[Dict[str, Any]] = []
        for neighbor in lldp_neighbors:
            sw1_ip = neighbor.get("local_switch_ip", "")
            sw2_ip = neighbor.get("remote_switch_ip", "")
            sw1_port = neighbor.get("local_port", "")
            sw2_port = neighbor.get("remote_port", "")
            if not (sw1_ip and sw2_ip):
                continue
            sw1_des = mapper.generate_switch_designation(sw1_ip, sw1_port)
            sw2_des = mapper.generate_switch_designation(sw2_ip, sw2_port)
            ipl_formatted.append(
                {
                    "switch_designation": sw1_des,
                    "node_designation": sw2_des,
                    "notes": "IPL",
                    "connection_type": "IPL",
                    "switch1_ip": sw1_ip,
                    "switch2_ip": sw2_ip,
                    "switch1_port": sw1_port,
                    "switch2_port": sw2_port,
                }
            )
        return ipl_formatted

    def _infer_ipl_from_switch_pair(self, mapper: Any) -> List[Dict[str, Any]]:
        """Infer switch-to-switch topology when LLDP data is unavailable.

        VAST deployments follow predictable patterns that let us still produce
        something useful when ``vnetmap`` or SSH LLDP fails to return neighbor
        data:

        * Every leaf-switch pair has an MLAG Inter-Peer Link (IPL) — emitted
          with ``connection_type="IPL"``.
        * Every spine is uplinked to every leaf in the same fabric — emitted
          with ``connection_type="spine_uplink"`` so the Logical Network
          Diagram can at least draw a dashed placeholder between each spine
          and leaf even before real port data is collected.

        The emitted entries carry ``notes`` ending in ``"(inferred)"`` so
        downstream rendering can style / caption them differently from
        LLDP-confirmed links.  Ports are left blank.
        """
        sw_map = getattr(mapper, "switch_map", {}) or {}
        if len(sw_map) < 2:
            return []

        leaves: List[Tuple[str, Dict[str, Any]]] = []
        spines: List[Tuple[str, Dict[str, Any]]] = []
        for ip, info in sw_map.items():
            if not ip:
                continue
            if info.get("role") == "spine":
                spines.append((ip, info))
            else:
                leaves.append((ip, info))

        leaves.sort(key=lambda item: item[0])
        spines.sort(key=lambda item: item[0])

        inferred: List[Dict[str, Any]] = []

        # --- Leaf-to-leaf IPL pairs ---
        # One IPL per unordered pair of leaves.  Two leaves -> one entry;
        # four-leaf racks (rare) -> two rack-local IPLs; we don't attempt to
        # guess which leaves are paired, so we emit all combinations.  LLDP
        # data, when available, takes precedence and replaces these entries.
        for i in range(len(leaves)):
            for j in range(i + 1, len(leaves)):
                ip_a, info_a = leaves[i]
                ip_b, info_b = leaves[j]
                inferred.append(
                    {
                        "switch_designation": info_a["designation"],
                        "node_designation": info_b["designation"],
                        "notes": "IPL (inferred)",
                        "connection_type": "IPL",
                        "switch1_ip": ip_a,
                        "switch2_ip": ip_b,
                        "switch1_port": "",
                        "switch2_port": "",
                    }
                )
                self.logger.info(
                    "Inferred IPL between %s (%s) and %s (%s)",
                    info_a["designation"],
                    ip_a,
                    info_b["designation"],
                    ip_b,
                )

        # --- Spine-to-leaf uplinks ---
        # Assume full-mesh spine/leaf connectivity (VAST reference design).
        # Each spine is uplinked to every leaf in the fabric.
        for spine_ip, spine_info in spines:
            for leaf_ip, leaf_info in leaves:
                inferred.append(
                    {
                        "switch_designation": spine_info["designation"],
                        "node_designation": leaf_info["designation"],
                        "notes": "Spine uplink (inferred)",
                        "connection_type": "spine_uplink",
                        "switch1_ip": spine_ip,
                        "switch2_ip": leaf_ip,
                        "switch1_port": "",
                        "switch2_port": "",
                    }
                )
                self.logger.info(
                    "Inferred spine uplink %s (%s) -> %s (%s)",
                    spine_info["designation"],
                    spine_ip,
                    leaf_info["designation"],
                    leaf_ip,
                )

        return inferred

    def extract_all_data(
        self,
        raw_data: Dict[str, Any],
        use_external_port_mapping: bool = False,
        use_vnetmap: bool = False,
    ) -> Dict[str, Any]:
        """
        Extract and process all report data from raw API responses.

        Args:
            raw_data (Dict[str, Any]): Raw data from API handler
            use_external_port_mapping (bool): Use external port mapping data if available
            use_vnetmap (bool): Use vnetmap output as port mapping source

        Returns:
            Dict[str, Any]: Complete processed report data
        """
        try:
            self.logger.info("Starting comprehensive data extraction")

            def _section_enabled(key: str) -> bool:
                return cast(bool, self.sections_config.get(key, True))

            # Extract all sections (respecting config toggles)
            cluster_summary = self.extract_cluster_summary(raw_data)
            hardware_inventory = (
                self.extract_hardware_inventory(raw_data)
                if _section_enabled("hardware_inventory")
                else self._empty_hardware_inventory()
            )
            network_config = self.extract_network_configuration(raw_data)
            cluster_network_config = (
                self.extract_cluster_network_configuration(raw_data)
                if _section_enabled("network_configuration")
                else self.extract_cluster_network_configuration({})
            )
            cnodes_network_config = (
                self.extract_cnodes_network_configuration(raw_data)
                if _section_enabled("network_configuration")
                else self.extract_cnodes_network_configuration({})
            )
            dnodes_network_config = (
                self.extract_dnodes_network_configuration(raw_data)
                if _section_enabled("network_configuration")
                else self.extract_dnodes_network_configuration({})
            )
            logical_config = (
                self.extract_logical_configuration(raw_data)
                if _section_enabled("logical_configuration")
                else self.extract_logical_configuration({})
            )
            security_config = (
                self.extract_security_configuration(raw_data)
                if _section_enabled("security_authentication")
                else self.extract_security_configuration({})
            )
            protection_config = (
                self.extract_data_protection_configuration(raw_data)
                if _section_enabled("data_protection")
                else self.extract_data_protection_configuration({})
            )

            # Extract enhanced sections
            performance_metrics = self.extract_performance_metrics(raw_data)
            licensing_info = self.extract_licensing_info(raw_data)
            monitoring_config = self.extract_monitoring_configuration(raw_data)
            customer_integration = self.extract_customer_integration(raw_data)
            deployment_timeline = self.extract_deployment_timeline(raw_data)
            future_recommendations = self.extract_future_recommendations(raw_data)
            port_mapping = self.extract_port_mapping(
                raw_data, use_external=use_external_port_mapping, use_vnetmap=use_vnetmap
            )

            # Calculate overall completeness
            section_completeness = [
                network_config.completeness,
                cluster_network_config.completeness,
                cnodes_network_config.completeness,
                dnodes_network_config.completeness,
                logical_config.completeness,
                security_config.completeness,
                protection_config.completeness,
                performance_metrics.completeness,
                licensing_info.completeness,
                monitoring_config.completeness,
                customer_integration.completeness,
                deployment_timeline.completeness,
                future_recommendations.completeness,
                port_mapping.completeness,
            ]
            overall_completeness = sum(section_completeness) / len(section_completeness)

            # Compile final report data
            report_data = {
                "metadata": {
                    "extraction_timestamp": datetime.now().isoformat(),
                    "overall_completeness": overall_completeness,
                    "enhanced_features": raw_data.get("enhanced_features", {}),
                    "cluster_version": raw_data.get("cluster_version"),
                    "api_version": raw_data.get("api_version"),
                },
                "cluster_summary": asdict(cluster_summary),
                "hardware_inventory": asdict(hardware_inventory),
                "raw_hardware": raw_data.get("hardware"),  # Fallback for report if extraction missed data
                "raw_switch_inventory": raw_data.get("switch_inventory"),
                "racks": raw_data.get("racks", []),  # Include racks data for rack height information
                "sections": {
                    "network_configuration": asdict(network_config),
                    "cluster_network_configuration": asdict(cluster_network_config),
                    "cnodes_network_configuration": asdict(cnodes_network_config),
                    "dnodes_network_configuration": asdict(dnodes_network_config),
                    "logical_configuration": asdict(logical_config),
                    "security_configuration": asdict(security_config),
                    "data_protection_configuration": asdict(protection_config),
                    "performance_metrics": asdict(performance_metrics),
                    "licensing_info": asdict(licensing_info),
                    "monitoring_configuration": asdict(monitoring_config),
                    "customer_integration": asdict(customer_integration),
                    "deployment_timeline": asdict(deployment_timeline),
                    "future_recommendations": asdict(future_recommendations),
                    "port_mapping": asdict(port_mapping),
                },
            }

            # Health check data (optional -- only present when health check was run)
            health_check_data = raw_data.get("health_check_results")
            if health_check_data:
                report_data["sections"]["health_check"] = asdict(
                    ReportSection(
                        name="health_check",
                        title="Cluster Health Check Results",
                        data=health_check_data,
                        completeness=100.0,
                        status="complete",
                    )
                )

            # Post Deployment Activities — always included (next steps checklist)
            next_steps = [
                {
                    "item": "Configure Call Home w/ Cloud Integration",
                    "description": (
                        "Configure cloud integration to enable remote monitoring and proactive support. "
                        "Ensure Cloud VMS fields match Salesforce records exactly. "
                        "Outbound traffic requires *.cloud.vastdata.com:443."
                    ),
                },
                {
                    "item": "Create VIP",
                    "description": (
                        "Create Virtual IP Pool(s) via VMS GUI or CLI (vcli > vippool create). "
                        "Verify VIPs are setup and listening using showmount -e <VIP>."
                    ),
                },
                {
                    "item": "Test Fail-over Behavior",
                    "description": (
                        "Identify the VMS host node and intentionally reboot it. "
                        "Verify VMS migrates and cluster stays healthy. Repeat for the leader node."
                    ),
                },
                {
                    "item": "Confirm VIP Movement and ARP Updates",
                    "description": (
                        "After MLAG is confirmed, validate that gratuitous ARP updates propagate "
                        "correctly when VIPs move between CNodes. Mount from a client and test "
                        "during a controlled fail-over."
                    ),
                },
                {
                    "item": "Activate License",
                    "description": (
                        "Locate the PSNT asset record in Salesforce and click 'Activate Cluster'. "
                        "Configure the license key in VMS via GUI or CLI. "
                        "License start date is the last day of cluster install."
                    ),
                },
                {
                    "item": "Change Default Passwords",
                    "description": (
                        "Change all default passwords: Linux root, vastdata, and IPMI admin via "
                        "VCLI (cluster set-password). Change VMS admin, support, and root passwords "
                        "via VMS UI. Change switch admin and monitor passwords."
                    ),
                },
            ]

            self._resolve_post_deploy_status(next_steps, report_data)

            report_data["sections"]["post_deployment_activities"] = asdict(
                ReportSection(
                    name="post_deployment_activities",
                    title="Post Deployment Activities",
                    data={"next_steps": next_steps},
                    completeness=100.0,
                    status="complete",
                )
            )

            self.logger.info(f"Data extraction completed (overall completeness: {overall_completeness:.1%})")
            return report_data

        except Exception as e:
            self.logger.error(f"Error during comprehensive data extraction: {e}")
            if not self.graceful_degradation:
                raise DataExtractionError(f"Failed to extract all data: {e}")
            return {
                "error": str(e),
                "metadata": {"extraction_timestamp": datetime.now().isoformat()},
            }

    def _resolve_post_deploy_status(self, next_steps: List[Dict[str, Any]], report_data: Dict[str, Any]) -> None:
        """Resolve status for each post-deployment item from health check results and cluster data.

        Sets ``step["status"]`` to ``Completed``, ``Optional``, or ``Pending``.

        Args:
            next_steps: Mutable list of step dicts to update in place.
            report_data: The assembled report_data dict (sections + cluster_summary).
        """
        hc_results: Dict[str, str] = {}
        hc_section = report_data.get("sections", {}).get("health_check", {})
        for r in hc_section.get("data", {}).get("results", []):
            hc_results[r.get("check_name", "")] = r.get("status", "")

        cluster = report_data.get("cluster_summary", {})
        license_val = str(cluster.get("license", "") or "").strip().lower()

        _AUTO_CHECKS: Dict[str, bool] = {
            "Configure Call Home w/ Cloud Integration": hc_results.get("Call Home Status") == "pass",
            "Create VIP": hc_results.get("VIP Pools") == "pass",
            "Activate License": (
                hc_results.get("License") == "pass"
                or (bool(license_val) and license_val not in ("", "none", "unknown"))
            ),
        }

        _MANUAL_ITEMS = {
            "Test Fail-over Behavior",
            "Confirm VIP Movement and ARP Updates",
            "Change Default Passwords",
        }

        for step in next_steps:
            item = step.get("item", "")
            if item in _MANUAL_ITEMS:
                step["status"] = "Optional"
            elif item in _AUTO_CHECKS:
                step["status"] = "Completed" if _AUTO_CHECKS[item] else "Pending"
            else:
                step["status"] = "Pending"

    def _calculate_completeness(self, conditions: List[bool]) -> float:
        """Calculate data completeness percentage."""
        if not conditions:
            return 0.0
        return sum(conditions) / len(conditions)

    def _format_network_value(self, api_value: Any, fallback_value: Any) -> str:
        """Format network value from API, handling arrays and fallbacks."""
        if api_value and isinstance(api_value, list) and len(api_value) > 0:
            # Return the first value from the array
            return str(api_value[0])
        elif api_value and api_value != "Unknown":
            # Return the value as-is if it's not unknown
            return str(api_value)
        else:
            # Use fallback value
            return str(fallback_value)

    def _determine_section_status(self, completeness: float) -> str:
        """Determine section status based on completeness."""
        if completeness >= 0.9:
            return "complete"
        elif completeness >= 0.5:
            return "partial"
        elif completeness > 0.0:
            return "missing"
        else:
            return "error"

    def save_processed_data(self, data: Dict[str, Any], output_path: str) -> bool:
        """
        Save processed data to JSON file.

        Args:
            data (Dict[str, Any]): Processed report data
            output_path (str): Output file path

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)

            self.logger.info(f"Processed data saved to: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error saving processed data: {e}")
            return False


# Convenience function for easy usage
def create_data_extractor(config: Optional[Dict[str, Any]] = None) -> VastDataExtractor:
    """
    Create and return a configured VastDataExtractor instance.

    Args:
        config (Dict[str, Any], optional): Configuration dictionary

    Returns:
        VastDataExtractor: Configured data extractor instance
    """
    return VastDataExtractor(config)


if __name__ == "__main__":
    """
    Test the data extractor when run as a standalone module.
    """
    import sys
    from pathlib import Path

    # Add src directory to Python path
    sys.path.insert(0, str(Path(__file__).parent))

    from utils.logger import setup_logging

    # Set up logging
    setup_logging()
    logger = get_logger(__name__)

    # Test configuration
    test_config = {
        "data_collection": {
            "validate_responses": True,
            "graceful_degradation": True,
            "sections": {
                "executive_summary": True,
                "hardware_inventory": True,
                "network_configuration": True,
                "logical_configuration": True,
                "security_authentication": True,
                "data_protection": True,
            },
        }
    }

    logger.info("VAST Data Extractor Module Test")
    logger.info("This module processes and organizes API data for report generation")
    logger.info("Enhanced features: rack positioning and PSNT integration")
    logger.info("Ready for integration with report builder")
