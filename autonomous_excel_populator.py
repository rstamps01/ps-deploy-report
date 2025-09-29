#!/usr/bin/env python3
"""
Autonomous Excel Populator for VAST As-Built Report Generator

This script systematically generates filtered API calls to populate the Excel spreadsheet
with real data from the VAST cluster, creating both CSV and Excel outputs.
"""

import csv
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_handler import create_vast_api_handler
from utils.logger import get_logger, setup_logging


class AutonomousExcelPopulator:
    """Autonomous system for populating Excel spreadsheet with VAST API data."""

    def __init__(
        self,
        cluster_ip: str,
        token: str = None,
        username: str = None,
        password: str = None,
    ):
        """Initialize the autonomous populator."""
        self.cluster_ip = cluster_ip
        self.token = token
        self.username = username
        self.password = password

        # Set up logging
        config = {
            "logging": {"level": "INFO"},
            "api": {
                "verify_ssl": False,  # Disable SSL for testing
                "timeout": 30,
                "max_retries": 3,
            },
        }
        setup_logging(config)
        self.logger = get_logger(__name__)

        # Initialize API handler
        self.api_handler = None
        self.authenticated = False

        # Data collection results
        self.collected_data = {}
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def authenticate(self) -> bool:
        """Authenticate with the VAST cluster."""
        try:
            self.api_handler = create_vast_api_handler(
                cluster_ip=self.cluster_ip,
                username=self.username,
                password=self.password,
                token=self.token,
                config={"api": {"verify_ssl": False}},
            )

            if self.api_handler.authenticate():
                self.authenticated = True
                self.logger.info("Successfully authenticated with VAST cluster")
                return True
            else:
                self.logger.error("Failed to authenticate with VAST cluster")
                return False

        except Exception as e:
            self.logger.error(f"Authentication error: {e}")
            return False

    def collect_cluster_basic_info(self) -> Dict[str, Any]:
        """Collect basic cluster information."""
        self.logger.info("Collecting cluster basic information...")

        try:
            cluster_data = self.api_handler.get_cluster_info()
            if not cluster_data:
                return {}

            return {
                "cluster_name": cluster_data.name,
                "cluster_guid": cluster_data.guid,
                "cluster_version": cluster_data.version,
                "cluster_state": cluster_data.state,
                "cluster_psnt": cluster_data.psnt,
                "cluster_uptime": getattr(cluster_data, "uptime", "Unknown"),
                "cluster_build": getattr(cluster_data, "build", "Unknown"),
                "cluster_license": getattr(cluster_data, "license", "Unknown"),
            }
        except Exception as e:
            self.logger.error(f"Error collecting cluster basic info: {e}")
            return {}

    def collect_cluster_state_info(self) -> Dict[str, Any]:
        """Collect cluster state information."""
        self.logger.info("Collecting cluster state information...")

        try:
            # Get cluster state data
            response = self.api_handler._make_api_request("clusters/")
            if not response:
                return {}

            cluster = response[0] if isinstance(response, list) else response

            return {
                "state": cluster.get("state", "Unknown"),
                "ssd_raid_state": cluster.get("ssd_raid_state", "Unknown"),
                "nvram_raid_state": cluster.get("nvram_raid_state", "Unknown"),
                "memory_raid_state": cluster.get("memory_raid_state", "Unknown"),
                "leader_state": cluster.get("leader_state", "Unknown"),
                "leader_cnode": cluster.get("leader_cnode", "Unknown"),
                "mgmt_cnode": cluster.get("mgmt_cnode", "Unknown"),
                "mgmt_inner_vip": cluster.get("mgmt_inner_vip", "Unknown"),
                "mgmt_inner_vip_cnode": cluster.get("mgmt_inner_vip_cnode", "Unknown"),
                "enabled": cluster.get("enabled", False),
                "enable_similarity": cluster.get("enable_similarity", False),
                "similarity_active": cluster.get("similarity_active", False),
                "skip_dedup": cluster.get("skip_dedup", False),
                "dedup_active": cluster.get("dedup_active", False),
                "is_wb_raid_enabled": cluster.get("is_wb_raid_enabled", False),
                "wb_raid_layout": cluster.get("wb_raid_layout", "Unknown"),
                "dbox_ha_support": cluster.get("dbox_ha_support", False),
                "enable_rack_level_resiliency": cluster.get(
                    "enable_rack_level_resiliency", False
                ),
                "b2b_configuration": cluster.get("b2b_configuration", "Unknown"),
                "disable_metrics": cluster.get("disable_metrics", False),
            }
        except Exception as e:
            self.logger.error(f"Error collecting cluster state info: {e}")
            return {}

    def collect_cluster_capacity_info(self) -> Dict[str, Any]:
        """Collect cluster capacity information."""
        self.logger.info("Collecting cluster capacity information...")

        try:
            # Get cluster capacity data
            response = self.api_handler._make_api_request("clusters/")
            if not response:
                return {}

            cluster = response[0] if isinstance(response, list) else response

            return {
                "total_capacity": cluster.get("total_capacity", 0),
                "used_capacity": cluster.get("used_capacity", 0),
                "free_capacity": cluster.get("free_capacity", 0),
                "capacity_utilization": cluster.get("capacity_utilization", 0),
                "dedup_ratio": cluster.get("dedup_ratio", 0),
                "compression_ratio": cluster.get("compression_ratio", 0),
                "effective_capacity": cluster.get("effective_capacity", 0),
            }
        except Exception as e:
            self.logger.error(f"Error collecting cluster capacity info: {e}")
            return {}

    def collect_cluster_encryption_info(self) -> Dict[str, Any]:
        """Collect cluster encryption information."""
        self.logger.info("Collecting cluster encryption information...")

        try:
            # Get encryption configuration
            response = self.api_handler._make_api_request("encryption/")
            if not response:
                return {}

            return {
                "encryption_enabled": response.get("enabled", False),
                "encryption_type": response.get("type", "Unknown"),
                "key_management": response.get("key_management", "Unknown"),
                "encryption_at_rest": response.get("encryption_at_rest", False),
                "encryption_in_transit": response.get("encryption_in_transit", False),
            }
        except Exception as e:
            self.logger.error(f"Error collecting cluster encryption info: {e}")
            return {}

    def collect_cnodes_info(self) -> List[Dict[str, Any]]:
        """Collect CNodes information."""
        self.logger.info("Collecting CNodes information...")

        try:
            cnodes_data = self.api_handler._make_api_request("cnodes/")
            if not cnodes_data:
                return []

            cnodes = []
            for cnode in cnodes_data:
                cnodes.append(
                    {
                        "cnode_id": cnode.get("id", "Unknown"),
                        "cnode_name": cnode.get("name", "Unknown"),
                        "cnode_model": cnode.get("model", "Unknown"),
                        "cnode_serial": cnode.get("serial_number", "Unknown"),
                        "cnode_status": cnode.get("status", "Unknown"),
                        "cnode_rack_position": cnode.get("rack_position", "Unknown"),
                        "cnode_rack_u": cnode.get("rack_u", "Unknown"),
                        "cnode_ip": cnode.get("ip", "Unknown"),
                        "cnode_mac": cnode.get("mac", "Unknown"),
                        "cnode_vendor": cnode.get("box_vendor", "Unknown"),
                        "cnode_firmware": cnode.get("firmware_version", "Unknown"),
                    }
                )

            return cnodes
        except Exception as e:
            self.logger.error(f"Error collecting CNodes info: {e}")
            return []

    def collect_dnodes_info(self) -> List[Dict[str, Any]]:
        """Collect DNodes information."""
        self.logger.info("Collecting DNodes information...")

        try:
            dnodes_data = self.api_handler._make_api_request("dnodes/")
            if not dnodes_data:
                return []

            dnodes = []
            for dnode in dnodes_data:
                dnodes.append(
                    {
                        "dnode_id": dnode.get("id", "Unknown"),
                        "dnode_name": dnode.get("name", "Unknown"),
                        "dnode_model": dnode.get("model", "Unknown"),
                        "dnode_serial": dnode.get("serial_number", "Unknown"),
                        "dnode_status": dnode.get("status", "Unknown"),
                        "dnode_rack_position": dnode.get("rack_position", "Unknown"),
                        "dnode_rack_u": dnode.get("rack_u", "Unknown"),
                        "dnode_ip": dnode.get("ip", "Unknown"),
                        "dnode_mac": dnode.get("mac", "Unknown"),
                        "dnode_vendor": dnode.get("box_vendor", "Unknown"),
                        "dnode_firmware": dnode.get("firmware_version", "Unknown"),
                    }
                )

            return dnodes
        except Exception as e:
            self.logger.error(f"Error collecting DNodes info: {e}")
            return []

    def collect_network_info(self) -> Dict[str, Any]:
        """Collect network information."""
        self.logger.info("Collecting network information...")

        try:
            # Get cluster network configuration
            cluster_network = self.api_handler._make_api_request("cluster_network/")
            cnode_network = self.api_handler._make_api_request("cnode_network/")
            dnode_network = self.api_handler._make_api_request("dnode_network/")

            return {
                "cluster_network": cluster_network if cluster_network else {},
                "cnode_network": cnode_network if cnode_network else {},
                "dnode_network": dnode_network if dnode_network else {},
            }
        except Exception as e:
            self.logger.error(f"Error collecting network info: {e}")
            return {}

    def collect_all_data(self) -> Dict[str, Any]:
        """Collect all required data systematically."""
        self.logger.info("Starting comprehensive data collection...")

        if not self.authenticated:
            self.logger.error("Not authenticated. Cannot collect data.")
            return {}

        # Collect all data sections
        self.collected_data = {
            "metadata": {
                "collection_timestamp": datetime.now().isoformat(),
                "cluster_ip": self.cluster_ip,
                "api_version": getattr(self.api_handler, "api_version", "Unknown"),
            },
            "cluster_basic_info": self.collect_cluster_basic_info(),
            "cluster_state_info": self.collect_cluster_state_info(),
            "cluster_capacity_info": self.collect_cluster_capacity_info(),
            "cluster_encryption_info": self.collect_cluster_encryption_info(),
            "cnodes_info": self.collect_cnodes_info(),
            "dnodes_info": self.collect_dnodes_info(),
            "network_info": self.collect_network_info(),
        }

        self.logger.info("Data collection completed successfully")
        return self.collected_data

    def save_to_csv(self, output_dir: str = "excel_data") -> None:
        """Save collected data to CSV files for Excel import."""
        os.makedirs(output_dir, exist_ok=True)

        self.logger.info(f"Saving data to CSV files in {output_dir}/")

        # Save cluster basic info
        if self.collected_data.get("cluster_basic_info"):
            self._save_dict_to_csv(
                self.collected_data["cluster_basic_info"],
                f"{output_dir}/cluster_basic_info_{self.timestamp}.csv",
            )

        # Save cluster state info
        if self.collected_data.get("cluster_state_info"):
            self._save_dict_to_csv(
                self.collected_data["cluster_state_info"],
                f"{output_dir}/cluster_state_info_{self.timestamp}.csv",
            )

        # Save cluster capacity info
        if self.collected_data.get("cluster_capacity_info"):
            self._save_dict_to_csv(
                self.collected_data["cluster_capacity_info"],
                f"{output_dir}/cluster_capacity_info_{self.timestamp}.csv",
            )

        # Save cluster encryption info
        if self.collected_data.get("cluster_encryption_info"):
            self._save_dict_to_csv(
                self.collected_data["cluster_encryption_info"],
                f"{output_dir}/cluster_encryption_info_{self.timestamp}.csv",
            )

        # Save CNodes info
        if self.collected_data.get("cnodes_info"):
            self._save_list_to_csv(
                self.collected_data["cnodes_info"],
                f"{output_dir}/cnodes_info_{self.timestamp}.csv",
            )

        # Save DNodes info
        if self.collected_data.get("dnodes_info"):
            self._save_list_to_csv(
                self.collected_data["dnodes_info"],
                f"{output_dir}/dnodes_info_{self.timestamp}.csv",
            )

        # Save network info
        if self.collected_data.get("network_info"):
            self._save_dict_to_csv(
                self.collected_data["network_info"],
                f"{output_dir}/network_info_{self.timestamp}.csv",
            )

    def _save_dict_to_csv(self, data: Dict[str, Any], filename: str) -> None:
        """Save dictionary data to CSV file."""
        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Field", "Value"])
                for key, value in data.items():
                    writer.writerow([key, value])
            self.logger.info(f"Saved {filename}")
        except Exception as e:
            self.logger.error(f"Error saving {filename}: {e}")

    def _save_list_to_csv(self, data: List[Dict[str, Any]], filename: str) -> None:
        """Save list of dictionaries to CSV file."""
        try:
            if not data:
                return

            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = data[0].keys()
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    writer.writerow(row)
            self.logger.info(f"Saved {filename}")
        except Exception as e:
            self.logger.error(f"Error saving {filename}: {e}")

    def create_excel_summary(self, output_dir: str = "excel_data") -> None:
        """Create a comprehensive Excel summary file with curl commands."""
        self.logger.info("Creating Excel summary file with curl commands...")

        try:
            excel_file = f"{output_dir}/vast_data_summary_{self.timestamp}.xlsx"

            with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
                # Cluster Basic Info with curl command
                if self.collected_data.get("cluster_basic_info"):
                    basic_data = self.collected_data["cluster_basic_info"].copy()
                    basic_data["curl_command"] = (
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.name, .guid, .version, .state, .psnt, .uptime, .build, .license] | @csv'"
                    )
                    df = pd.DataFrame([basic_data])
                    df.to_excel(writer, sheet_name="Cluster_Basic_Info", index=False)

                # Cluster State Info with curl command
                if self.collected_data.get("cluster_state_info"):
                    state_data = self.collected_data["cluster_state_info"].copy()
                    state_data["curl_command"] = (
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv'"
                    )
                    df = pd.DataFrame([state_data])
                    df.to_excel(writer, sheet_name="Cluster_State_Info", index=False)

                # Cluster Capacity Info with curl command
                if self.collected_data.get("cluster_capacity_info"):
                    capacity_data = self.collected_data["cluster_capacity_info"].copy()
                    capacity_data["curl_command"] = (
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.total_capacity, .used_capacity, .free_capacity, .capacity_utilization, .dedup_ratio, .compression_ratio, .effective_capacity] | @csv'"
                    )
                    df = pd.DataFrame([capacity_data])
                    df.to_excel(writer, sheet_name="Cluster_Capacity_Info", index=False)

                # Cluster Encryption Info with curl command
                if self.collected_data.get("cluster_encryption_info"):
                    encryption_data = self.collected_data[
                        "cluster_encryption_info"
                    ].copy()
                    encryption_data["curl_command"] = (
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/encryption/' | jq -r '[.enabled, .type, .key_management, .encryption_at_rest, .encryption_in_transit] | @csv'"
                    )
                    df = pd.DataFrame([encryption_data])
                    df.to_excel(
                        writer, sheet_name="Cluster_Encryption_Info", index=False
                    )

                # CNodes Info with curl command
                if self.collected_data.get("cnodes_info"):
                    cnodes_data = self.collected_data["cnodes_info"].copy()
                    for i, cnode in enumerate(cnodes_data):
                        cnodes_data[i][
                            "curl_command"
                        ] = f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cnodes/' | jq -r '.[] | [.id, .name, .model, .serial_number, .status, .rack_position, .rack_u, .ip, .mac, .box_vendor, .firmware_version] | @csv'"
                    df = pd.DataFrame(cnodes_data)
                    df.to_excel(writer, sheet_name="CNodes_Info", index=False)

                # DNodes Info with curl command
                if self.collected_data.get("dnodes_info"):
                    dnodes_data = self.collected_data["dnodes_info"].copy()
                    for i, dnode in enumerate(dnodes_data):
                        dnodes_data[i][
                            "curl_command"
                        ] = f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/dnodes/' | jq -r '.[] | [.id, .name, .model, .serial_number, .status, .rack_position, .rack_u, .ip, .mac, .box_vendor, .firmware_version] | @csv'"
                    df = pd.DataFrame(dnodes_data)
                    df.to_excel(writer, sheet_name="DNodes_Info", index=False)

                # Network Info with curl commands
                if self.collected_data.get("network_info"):
                    network_data = self.collected_data["network_info"].copy()
                    network_data["cluster_network_curl"] = (
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cluster_network/' | jq -r '.[] | [.name, .ip, .netmask, .gateway, .vlan_id] | @csv'"
                    )
                    network_data["cnode_network_curl"] = (
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cnode_network/' | jq -r '.[] | [.name, .ip, .netmask, .gateway, .vlan_id] | @csv'"
                    )
                    network_data["dnode_network_curl"] = (
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/dnode_network/' | jq -r '.[] | [.name, .ip, .netmask, .gateway, .vlan_id] | @csv'"
                    )
                    df = pd.DataFrame([network_data])
                    df.to_excel(writer, sheet_name="Network_Info", index=False)

                # Create a dedicated curl commands sheet
                curl_commands_data = {
                    "Section": [
                        "Cluster Basic Info",
                        "Cluster State Info",
                        "Cluster Capacity Info",
                        "Cluster Encryption Info",
                        "CNodes Info",
                        "DNodes Info",
                        "Cluster Network",
                        "CNode Network",
                        "DNode Network",
                    ],
                    "API_Endpoint": [
                        "/api/v1/clusters/",
                        "/api/v1/clusters/",
                        "/api/v1/clusters/",
                        "/api/v1/encryption/",
                        "/api/v1/cnodes/",
                        "/api/v1/dnodes/",
                        "/api/v1/cluster_network/",
                        "/api/v1/cnode_network/",
                        "/api/v1/dnode_network/",
                    ],
                    "Curl_Command": [
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.name, .guid, .version, .state, .psnt, .uptime, .build, .license] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.total_capacity, .used_capacity, .free_capacity, .capacity_utilization, .dedup_ratio, .compression_ratio, .effective_capacity] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/encryption/' | jq -r '[.enabled, .type, .key_management, .encryption_at_rest, .encryption_in_transit] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cnodes/' | jq -r '.[] | [.id, .name, .model, .serial_number, .status, .rack_position, .rack_u, .ip, .mac, .box_vendor, .firmware_version] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/dnodes/' | jq -r '.[] | [.id, .name, .model, .serial_number, .status, .rack_position, .rack_u, .ip, .mac, .box_vendor, .firmware_version] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cluster_network/' | jq -r '.[] | [.name, .ip, .netmask, .gateway, .vlan_id] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cnode_network/' | jq -r '.[] | [.name, .ip, .netmask, .gateway, .vlan_id] | @csv'",
                        f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/dnode_network/' | jq -r '.[] | [.name, .ip, .netmask, .gateway, .vlan_id] | @csv'",
                    ],
                    "Test_Status": [
                        "Ready",
                        "Ready",
                        "Ready",
                        "Ready",
                        "Ready",
                        "Ready",
                        "Ready",
                        "Ready",
                        "Ready",
                    ],
                    "Notes": [
                        "Basic cluster information",
                        "Detailed cluster state and configuration",
                        "Capacity and utilization metrics",
                        "Encryption configuration",
                        "Control node hardware details",
                        "Data node hardware details",
                        "Cluster-level network configuration",
                        "Control node network configuration",
                        "Data node network configuration",
                    ],
                }

                curl_df = pd.DataFrame(curl_commands_data)
                curl_df.to_excel(writer, sheet_name="Curl_Commands", index=False)

            self.logger.info(f"Excel summary created: {excel_file}")

        except Exception as e:
            self.logger.error(f"Error creating Excel summary: {e}")

    def generate_curl_commands(self, output_dir: str = "excel_data") -> None:
        """Generate curl commands for each data section."""
        self.logger.info("Generating curl commands...")

        curl_commands = {
            "cluster_basic_info": f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.name, .guid, .version, .state, .psnt, .uptime, .build, .license] | @csv'",
            "cluster_state_info": f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/clusters/' | jq -r '.[0] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv'",
            "cnodes_info": f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cnodes/' | jq -r '.[] | [.id, .name, .model, .serial_number, .status, .rack_position, .rack_u, .ip, .mac, .box_vendor, .firmware_version] | @csv'",
            "dnodes_info": f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/dnodes/' | jq -r '.[] | [.id, .name, .model, .serial_number, .status, .rack_position, .rack_u, .ip, .mac, .box_vendor, .firmware_version] | @csv'",
            "network_info": f"curl -k -H 'Authorization: Api-Token {self.token}' 'https://{self.cluster_ip}/api/v1/cluster_network/' | jq -r '.[] | [.name, .ip, .netmask, .gateway, .vlan_id] | @csv'",
        }

        curl_file = f"{output_dir}/curl_commands_{self.timestamp}.txt"
        try:
            with open(curl_file, "w") as f:
                f.write("# VAST API Curl Commands for Excel Population\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n")
                f.write(f"# Cluster: {self.cluster_ip}\n\n")

                for section, command in curl_commands.items():
                    f.write(f"# {section.upper()}\n")
                    f.write(f"{command}\n\n")

            self.logger.info(f"Curl commands saved: {curl_file}")

        except Exception as e:
            self.logger.error(f"Error saving curl commands: {e}")

    def run_autonomous_population(self, output_dir: str = "excel_data") -> bool:
        """Run the complete autonomous population process."""
        self.logger.info("Starting autonomous Excel population process...")

        try:
            # Step 1: Authenticate
            if not self.authenticate():
                return False

            # Step 2: Collect all data
            self.collect_all_data()

            # Step 3: Save to CSV files
            self.save_to_csv(output_dir)

            # Step 4: Create Excel summary
            self.create_excel_summary(output_dir)

            # Step 5: Generate curl commands
            self.generate_curl_commands(output_dir)

            # Step 6: Save raw JSON data
            json_file = f"{output_dir}/vast_data_raw_{self.timestamp}.json"
            with open(json_file, "w") as f:
                json.dump(self.collected_data, f, indent=2)

            self.logger.info("Autonomous Excel population completed successfully!")
            self.logger.info(f"Output directory: {output_dir}/")
            self.logger.info(f"Files created:")
            self.logger.info(f"  - CSV files for each data section")
            self.logger.info(
                f"  - Excel summary: vast_data_summary_{self.timestamp}.xlsx"
            )
            self.logger.info(f"  - Curl commands: curl_commands_{self.timestamp}.txt")
            self.logger.info(f"  - Raw JSON: vast_data_raw_{self.timestamp}.json")

            return True

        except Exception as e:
            self.logger.error(f"Error in autonomous population: {e}")
            return False
        finally:
            if self.api_handler:
                self.api_handler.close()


def main():
    """Main function for autonomous Excel population."""
    if len(sys.argv) < 2:
        print(
            "Usage: python autonomous_excel_populator.py <cluster_ip> [token] [username] [password]"
        )
        print("Examples:")
        print("  python autonomous_excel_populator.py 10.143.11.204 YOUR_TOKEN")
        print(
            "  python autonomous_excel_populator.py 10.143.11.204 YOUR_TOKEN admin 123456"
        )
        sys.exit(1)

    cluster_ip = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else None
    username = sys.argv[3] if len(sys.argv) > 3 else None
    password = sys.argv[4] if len(sys.argv) > 4 else None

    # Create autonomous populator
    populator = AutonomousExcelPopulator(
        cluster_ip=cluster_ip, token=token, username=username, password=password
    )

    # Run autonomous population
    success = populator.run_autonomous_population()

    if success:
        print("\n🎉 AUTONOMOUS EXCEL POPULATION COMPLETED SUCCESSFULLY!")
        print("📊 Check the 'excel_data/' directory for all generated files")
        sys.exit(0)
    else:
        print("\n❌ AUTONOMOUS EXCEL POPULATION FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
