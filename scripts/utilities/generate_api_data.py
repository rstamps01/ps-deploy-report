#!/usr/bin/env python3
"""
VAST API Data Generator

This script generates curl commands and formats API data for easy import into
spreadsheets or Word documents based on the API-Summary worksheet structure.

Usage:
    python3 generate_api_data.py --cluster 10.143.11.204 --username admin --password password
    python3 generate_api_data.py --cluster 10.143.11.204 --token <API_TOKEN>
"""

import argparse
import csv
import json
import subprocess
import sys
from typing import Any, Dict, List, Optional


class VastApiDataGenerator:
    def __init__(
        self,
        cluster_ip: str,
        username: str = None,
        password: str = None,
        token: str = None,
    ):
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password
        self.token = token
        self.base_url = f"https://{cluster_ip}/api"

    def _get_auth_header(self) -> str:
        """Get authentication header for curl commands."""
        if self.token:
            return f"Api-Token {self.token}"
        elif self.username and self.password:
            return f"{self.username}:{self.password}"
        else:
            raise ValueError("Either token or username/password must be provided")

    def _run_curl(self, endpoint: str, api_version: str = "v7") -> Dict[str, Any]:
        """Run curl command and return JSON response."""
        url = f"{self.base_url}/{api_version}/{endpoint}"

        if self.token:
            cmd = [
                "curl",
                "-k",
                "-s",
                "-H",
                f"Authorization: {self._get_auth_header()}",
                url,
            ]
        else:
            cmd = ["curl", "-k", "-s", "-u", self._get_auth_header(), url]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error calling API: {e}")
            return {}
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}")
            return {}

    def generate_cluster_data(self) -> Dict[str, Any]:
        """Generate cluster data in multiple formats."""
        print("🔍 Generating Cluster Data...")

        data = self._run_curl("clusters/")
        if not data:
            return {}

        cluster = data[0] if isinstance(data, list) else data

        # CSV format for spreadsheet import
        csv_data = {
            "basic_info": [
                [
                    "ID",
                    "Name",
                    "Management VIP",
                    "URL",
                    "Build",
                    "PSNT",
                    "GUID",
                    "Uptime",
                    "Online Start Time",
                    "Deployment Time",
                ],
                [
                    cluster.get("id"),
                    cluster.get("name"),
                    cluster.get("mgmt_vip"),
                    cluster.get("url"),
                    cluster.get("build"),
                    cluster.get("psnt"),
                    cluster.get("guid"),
                    cluster.get("uptime"),
                    cluster.get("online_start_time"),
                    cluster.get("deployment_time"),
                ],
            ],
            "state_info": [
                [
                    "State",
                    "SSD RAID State",
                    "NVRAM RAID State",
                    "Memory RAID State",
                    "Leader State",
                    "Leader CNode",
                    "Management CNode",
                    "Management Inner VIP",
                    "Management Inner VIP CNode",
                    "Enabled",
                ],
                [
                    cluster.get("state"),
                    cluster.get("ssd_raid_state"),
                    cluster.get("nvram_raid_state"),
                    cluster.get("memory_raid_state"),
                    cluster.get("leader_state"),
                    cluster.get("leader_cnode"),
                    cluster.get("mgmt_cnode"),
                    cluster.get("mgmt_inner_vip"),
                    cluster.get("mgmt_inner_vip_cnode"),
                    cluster.get("enabled"),
                ],
            ],
            "capacity_info": [
                [
                    "Usable Capacity (TB)",
                    "Free Usable Capacity (TB)",
                    "DRR Text",
                    "Physical Space (TB)",
                    "Physical Space In Use (TB)",
                    "Free Physical Space (TB)",
                    "Physical Space In Use %",
                    "Logical Space (TB)",
                    "Logical Space In Use (TB)",
                    "Free Logical Space (TB)",
                    "Logical Space In Use %",
                ],
                [
                    cluster.get("usable_capacity_tb"),
                    cluster.get("free_usable_capacity_tb"),
                    cluster.get("drr_text"),
                    cluster.get("physical_space_tb"),
                    cluster.get("physical_space_in_use_tb"),
                    cluster.get("free_physical_space_tb"),
                    cluster.get("physical_space_in_use_percent"),
                    cluster.get("logical_space_tb"),
                    cluster.get("logical_space_in_use_tb"),
                    cluster.get("free_logical_space_tb"),
                    cluster.get("logical_space_in_use_percent"),
                ],
            ],
            "encryption_info": [
                [
                    "Enable Encryption",
                    "S3 Enable Only AES Ciphers",
                    "Encryption Type",
                    "EKM Servers",
                    "EKM Address",
                    "EKM Port",
                    "EKM Auth Domain",
                    "Secondary EKM Address",
                    "Secondary EKM Port",
                ],
                [
                    cluster.get("enable_encryption"),
                    cluster.get("S3_ENABLE_ONLY_AES_CIPHERS"),
                    cluster.get("encryption_type"),
                    cluster.get("ekm_servers"),
                    cluster.get("ekm_address"),
                    cluster.get("ekm_port"),
                    cluster.get("ekm_auth_domain"),
                    cluster.get("secondary_ekm_address"),
                    cluster.get("secondary_ekm_port"),
                ],
            ],
        }

        # Human-readable format for Word document
        human_readable = f"""
CLUSTER INFORMATION
==================
Cluster ID: {cluster.get('id')}
Name: {cluster.get('name')}
Management VIP: {cluster.get('mgmt_vip')}
Build: {cluster.get('build')}
PSNT: {cluster.get('psnt')}
GUID: {cluster.get('guid')}
Uptime: {cluster.get('uptime')}
Online Start Time: {cluster.get('online_start_time')}
Deployment Time: {cluster.get('deployment_time')}

CLUSTER STATE
=============
State: {cluster.get('state')}
SSD RAID State: {cluster.get('ssd_raid_state')}
NVRAM RAID State: {cluster.get('nvram_raid_state')}
Memory RAID State: {cluster.get('memory_raid_state')}
Leader State: {cluster.get('leader_state')}
Leader CNode: {cluster.get('leader_cnode')}
Management CNode: {cluster.get('mgmt_cnode')}

CAPACITY INFORMATION
===================
Usable Capacity: {cluster.get('usable_capacity_tb')} TB
Free Usable Capacity: {cluster.get('free_usable_capacity_tb')} TB
DRR: {cluster.get('drr_text')}
Physical Space: {cluster.get('physical_space_tb')} TB
Physical Space In Use: {cluster.get('physical_space_in_use_tb')} TB ({cluster.get('physical_space_in_use_percent')}%)
Free Physical Space: {cluster.get('free_physical_space_tb')} TB
Logical Space: {cluster.get('logical_space_tb')} TB
Logical Space In Use: {cluster.get('logical_space_in_use_tb')} TB ({cluster.get('logical_space_in_use_percent')}%)
Free Logical Space: {cluster.get('free_logical_space_tb')} TB

ENCRYPTION INFORMATION
=====================
Enable Encryption: {cluster.get('enable_encryption')}
Encryption Type: {cluster.get('encryption_type')}
EKM Address: {cluster.get('ekm_address')}
EKM Port: {cluster.get('ekm_port')}
"""

        return {
            "csv_data": csv_data,
            "human_readable": human_readable,
            "raw_data": cluster,
        }

    def generate_network_data(self) -> Dict[str, Any]:
        """Generate network data in multiple formats."""
        print("🔍 Generating Network Data...")

        # Get cluster network settings
        cluster_data = self._run_curl("clusters/")
        cluster = cluster_data[0] if isinstance(cluster_data, list) else cluster_data

        # Get VM network settings
        vm_data = self._run_curl("vms/1/network_settings/")

        # CSV format for spreadsheet import
        csv_data = {
            "cluster_network": [
                [
                    "Management VIPs",
                    "External Gateways",
                    "DNS",
                    "NTP",
                    "External Netmask",
                    "Auto Ports External Interface",
                    "B2B IPMI",
                    "Ethernet MTU",
                    "InfiniBand MTU",
                    "IPMI Gateway",
                    "IPMI Netmask",
                ],
                [
                    cluster.get("management_vips"),
                    cluster.get("external_gateways"),
                    cluster.get("dns"),
                    cluster.get("ntp"),
                    cluster.get("ext_netmask"),
                    cluster.get("auto_ports_ext_iface"),
                    cluster.get("b2b_ipmi"),
                    cluster.get("eth_mtu"),
                    cluster.get("ib_mtu"),
                    cluster.get("ipmi_gateway"),
                    cluster.get("ipmi_netmask"),
                ],
            ],
            "cnode_network": [
                [
                    "ID",
                    "Hostname",
                    "Management IP",
                    "IPMI IP",
                    "Box Vendor",
                    "VAST OS",
                    "Node Type",
                    "Box Name",
                    "Box UID",
                    "Is Ceres",
                    "Is VMS Host",
                    "Net Type",
                ]
            ],
            "dnode_network": [
                [
                    "ID",
                    "Hostname",
                    "Management IP",
                    "IPMI IP",
                    "Box Vendor",
                    "VAST OS",
                    "Node Type",
                    "Box Name",
                    "Box UID",
                    "Is Ceres",
                    "Is VMS Host",
                    "Position",
                    "Net Type",
                ]
            ],
        }

        # Process VM network settings
        if isinstance(vm_data, list):
            for vm in vm_data:
                if vm.get("node_type") == "Cnode":
                    csv_data["cnode_network"].append(
                        [
                            vm.get("id"),
                            vm.get("hostname"),
                            vm.get("mgmt_ip"),
                            vm.get("ipmi_ip"),
                            vm.get("box_vendor"),
                            vm.get("vast_os"),
                            vm.get("node_type"),
                            vm.get("box_name"),
                            vm.get("box_uid"),
                            vm.get("is_ceres"),
                            vm.get("is_vms_host"),
                            vm.get("net_type"),
                        ]
                    )
                elif vm.get("node_type") == "Dnode":
                    csv_data["dnode_network"].append(
                        [
                            vm.get("id"),
                            vm.get("hostname"),
                            vm.get("mgmt_ip"),
                            vm.get("ipmi_ip"),
                            vm.get("box_vendor"),
                            vm.get("vast_os"),
                            vm.get("node_type"),
                            vm.get("box_name"),
                            vm.get("box_uid"),
                            vm.get("is_ceres"),
                            vm.get("is_vms_host"),
                            vm.get("position"),
                            vm.get("net_type"),
                        ]
                    )

        # Human-readable format
        human_readable = f"""
CLUSTER NETWORK CONFIGURATION
=============================
Management VIPs: {cluster.get('management_vips')}
External Gateways: {cluster.get('external_gateways')}
DNS: {cluster.get('dns')}
NTP: {cluster.get('ntp')}
External Netmask: {cluster.get('ext_netmask')}
Ethernet MTU: {cluster.get('eth_mtu')}
InfiniBand MTU: {cluster.get('ib_mtu')}
IPMI Gateway: {cluster.get('ipmi_gateway')}
IPMI Netmask: {cluster.get('ipmi_netmask')}

CNODE NETWORK SETTINGS
======================
"""

        if isinstance(vm_data, list):
            for vm in vm_data:
                if vm.get("node_type") == "Cnode":
                    human_readable += f"""
CNode ID: {vm.get('id')}
Hostname: {vm.get('hostname')}
Management IP: {vm.get('mgmt_ip')}
IPMI IP: {vm.get('ipmi_ip')}
Box Vendor: {vm.get('box_vendor')}
VAST OS: {vm.get('vast_os')}
Box Name: {vm.get('box_name')}
Box UID: {vm.get('box_uid')}
Is VMS Host: {vm.get('is_vms_host')}
---
"""

        human_readable += "\nDNODE NETWORK SETTINGS\n======================\n"

        if isinstance(vm_data, list):
            for vm in vm_data:
                if vm.get("node_type") == "Dnode":
                    human_readable += f"""
DNode ID: {vm.get('id')}
Hostname: {vm.get('hostname')}
Management IP: {vm.get('mgmt_ip')}
IPMI IP: {vm.get('ipmi_ip')}
Box Vendor: {vm.get('box_vendor')}
VAST OS: {vm.get('vast_os')}
Box Name: {vm.get('box_name')}
Box UID: {vm.get('box_uid')}
Position: {vm.get('position')}
Is Ceres: {vm.get('is_ceres')}
---
"""

        return {
            "csv_data": csv_data,
            "human_readable": human_readable,
            "raw_data": {"cluster": cluster, "vms": vm_data},
        }

    def generate_cbox_data(self) -> Dict[str, Any]:
        """Generate CBox data in multiple formats."""
        print("🔍 Generating CBox Data...")

        data = self._run_curl("cboxes/", "v1")
        if not data:
            return {}

        # CSV format for spreadsheet import
        csv_data = [
            [
                "ID",
                "Name",
                "URL",
                "Cluster ID",
                "Cluster",
                "GUID",
                "Rack Unit",
                "Rack Name",
                "State",
            ]
        ]

        for cbox in data:
            csv_data.append(
                [
                    cbox.get("id"),
                    cbox.get("name"),
                    cbox.get("url"),
                    cbox.get("cluster_id"),
                    cbox.get("cluster"),
                    cbox.get("guid"),
                    cbox.get("rack_unit"),
                    cbox.get("rack_name"),
                    cbox.get("state"),
                ]
            )

        # Human-readable format
        human_readable = "CBOX INFORMATION\n================\n"
        for cbox in data:
            human_readable += f"""
CBox ID: {cbox.get('id')}
Name: {cbox.get('name')}
Rack Unit: {cbox.get('rack_unit')}
Rack Name: {cbox.get('rack_name')}
State: {cbox.get('state')}
GUID: {cbox.get('guid')}
Cluster: {cbox.get('cluster')}
---
"""

        return {
            "csv_data": csv_data,
            "human_readable": human_readable,
            "raw_data": data,
        }

    def generate_cnode_data(self) -> Dict[str, Any]:
        """Generate CNode data in multiple formats."""
        print("🔍 Generating CNode Data...")

        data = self._run_curl("cnodes/")
        if not data:
            return {}

        # CSV format for spreadsheet import
        csv_data = [
            [
                "ID",
                "Name",
                "Hostname",
                "GUID",
                "Cluster",
                "CBox ID",
                "CBox",
                "Box Vendor",
                "OS Version",
                "Build",
                "State",
                "Display State",
                "Sync",
                "Is Leader",
                "Is Management",
                "VLAN",
                "Management IP",
                "IPMI IP",
                "Host Label",
                "Enabled",
                "BMC State",
                "BMC State Reason",
                "BMC FW Version",
            ]
        ]

        for cnode in data:
            csv_data.append(
                [
                    cnode.get("id"),
                    cnode.get("name"),
                    cnode.get("hostname"),
                    cnode.get("guid"),
                    cnode.get("cluster"),
                    cnode.get("cbox_id"),
                    cnode.get("cbox"),
                    cnode.get("box_vendor"),
                    cnode.get("os_version"),
                    cnode.get("build"),
                    cnode.get("state"),
                    cnode.get("display_state"),
                    cnode.get("sync"),
                    cnode.get("is_leader"),
                    cnode.get("is_mgmt"),
                    cnode.get("vlan"),
                    cnode.get("mgmt_ip"),
                    cnode.get("ipmi_ip"),
                    cnode.get("host_label"),
                    cnode.get("enabled"),
                    cnode.get("bmc_state"),
                    cnode.get("bmc_state_reason"),
                    cnode.get("bmc_fw_version"),
                ]
            )

        # Human-readable format
        human_readable = "CNODE INFORMATION\n=================\n"
        for cnode in data:
            human_readable += f"""
CNode ID: {cnode.get('id')}
Name: {cnode.get('name')}
Hostname: {cnode.get('hostname')}
CBox: {cnode.get('cbox')}
OS Version: {cnode.get('os_version')}
State: {cnode.get('state')}
Management IP: {cnode.get('mgmt_ip')}
IPMI IP: {cnode.get('ipmi_ip')}
Is Leader: {cnode.get('is_leader')}
Is Management: {cnode.get('is_mgmt')}
BMC State: {cnode.get('bmc_state')}
---
"""

        return {
            "csv_data": csv_data,
            "human_readable": human_readable,
            "raw_data": data,
        }

    def generate_dbox_data(self) -> Dict[str, Any]:
        """Generate DBox data in multiple formats."""
        print("🔍 Generating DBox Data...")

        data = self._run_curl("dboxes/")
        if not data:
            return {}

        # CSV format for spreadsheet import
        csv_data = [
            [
                "ID",
                "Name",
                "URL",
                "Cluster ID",
                "Cluster",
                "GUID",
                "Rack Unit",
                "Rack Name",
                "State",
                "Sync",
                "Hardware Type",
            ]
        ]

        for dbox in data:
            csv_data.append(
                [
                    dbox.get("id"),
                    dbox.get("name"),
                    dbox.get("url"),
                    dbox.get("cluster_id"),
                    dbox.get("cluster"),
                    dbox.get("guid"),
                    dbox.get("rack_unit"),
                    dbox.get("rack_name"),
                    dbox.get("state"),
                    dbox.get("sync"),
                    dbox.get("hardware_type"),
                ]
            )

        # Human-readable format
        human_readable = "DBOX INFORMATION\n================\n"
        for dbox in data:
            human_readable += f"""
DBox ID: {dbox.get('id')}
Name: {dbox.get('name')}
Rack Unit: {dbox.get('rack_unit')}
Rack Name: {dbox.get('rack_name')}
State: {dbox.get('state')}
Hardware Type: {dbox.get('hardware_type')}
GUID: {dbox.get('guid')}
Cluster: {dbox.get('cluster')}
---
"""

        return {
            "csv_data": csv_data,
            "human_readable": human_readable,
            "raw_data": data,
        }

    def generate_dtray_data(self) -> Dict[str, Any]:
        """Generate DTray data in multiple formats."""
        print("🔍 Generating DTray Data...")

        data = self._run_curl("dtrays/")
        if not data:
            return {}

        # CSV format for spreadsheet import
        csv_data = [
            [
                "ID",
                "Name",
                "URL",
                "GUID",
                "Cluster",
                "DBox ID",
                "DBox",
                "Position",
                "DNodes",
                "Hardware Type",
                "State",
                "Sync",
                "BMC IP",
                "MCU State",
                "Enabled",
                "BMC State",
                "BMC State Reason",
                "BMC FW Version",
            ]
        ]

        for dtray in data:
            csv_data.append(
                [
                    dtray.get("id"),
                    dtray.get("name"),
                    dtray.get("url"),
                    dtray.get("guid"),
                    dtray.get("cluster"),
                    dtray.get("dbox_id"),
                    dtray.get("dbox"),
                    dtray.get("position"),
                    dtray.get("dnodes"),
                    dtray.get("hardware_type"),
                    dtray.get("state"),
                    dtray.get("sync"),
                    dtray.get("bmc_ip"),
                    dtray.get("mcu_state"),
                    dtray.get("enabled"),
                    dtray.get("bmc_state"),
                    dtray.get("bmc_state_reason"),
                    dtray.get("bmc_fw_version"),
                ]
            )

        # Human-readable format
        human_readable = "DTRAY INFORMATION\n=================\n"
        for dtray in data:
            human_readable += f"""
DTray ID: {dtray.get('id')}
Name: {dtray.get('name')}
DBox: {dtray.get('dbox')}
Position: {dtray.get('position')}
State: {dtray.get('state')}
Hardware Type: {dtray.get('hardware_type')}
BMC IP: {dtray.get('bmc_ip')}
MCU State: {dtray.get('mcu_state')}
BMC State: {dtray.get('bmc_state')}
---
"""

        return {
            "csv_data": csv_data,
            "human_readable": human_readable,
            "raw_data": data,
        }

    def generate_dnode_data(self) -> Dict[str, Any]:
        """Generate DNode data in multiple formats."""
        print("🔍 Generating DNode Data...")

        data = self._run_curl("dnodes/")
        if not data:
            return {}

        # CSV format for spreadsheet import
        csv_data = [
            [
                "ID",
                "Name",
                "Hostname",
                "GUID",
                "Cluster",
                "DBox ID",
                "DBox",
                "Position",
                "OS Version",
                "Build",
                "State",
                "Sync",
                "Management IP",
                "IPMI IP",
                "Host Label",
                "Enabled",
                "BMC State",
                "BMC State Reason",
                "BMC FW Version",
            ]
        ]

        for dnode in data:
            csv_data.append(
                [
                    dnode.get("id"),
                    dnode.get("name"),
                    dnode.get("hostname"),
                    dnode.get("guid"),
                    dnode.get("cluster"),
                    dnode.get("dbox_id"),
                    dnode.get("dbox"),
                    dnode.get("position"),
                    dnode.get("os_version"),
                    dnode.get("build"),
                    dnode.get("state"),
                    dnode.get("sync"),
                    dnode.get("mgmt_ip"),
                    dnode.get("ipmi_ip"),
                    dnode.get("host_label"),
                    dnode.get("enabled"),
                    dnode.get("bmc_state"),
                    dnode.get("bmc_state_reason"),
                    dnode.get("bmc_fw_version"),
                ]
            )

        # Human-readable format
        human_readable = "DNODE INFORMATION\n=================\n"
        for dnode in data:
            human_readable += f"""
DNode ID: {dnode.get('id')}
Name: {dnode.get('name')}
Hostname: {dnode.get('hostname')}
DBox: {dnode.get('dbox')}
Position: {dnode.get('position')}
OS Version: {dnode.get('os_version')}
State: {dnode.get('state')}
Management IP: {dnode.get('mgmt_ip')}
IPMI IP: {dnode.get('ipmi_ip')}
BMC State: {dnode.get('bmc_state')}
---
"""

        return {
            "csv_data": csv_data,
            "human_readable": human_readable,
            "raw_data": data,
        }

    def save_csv_data(self, data: Dict[str, Any], filename: str):
        """Save CSV data to file."""
        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            for row in data:
                writer.writerow(row)
        print(f"✅ CSV data saved to {filename}")

    def save_human_readable(self, data: str, filename: str):
        """Save human-readable data to file."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"✅ Human-readable data saved to {filename}")

    def generate_all_data(self, output_dir: str = "api_data_output"):
        """Generate all API data in multiple formats."""
        import os

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        print(f"🚀 Generating VAST API Data for cluster {self.cluster_ip}")
        print(f"📁 Output directory: {output_dir}")
        print("=" * 60)

        # Generate cluster data
        cluster_data = self.generate_cluster_data()
        if cluster_data:
            for key, csv_data in cluster_data["csv_data"].items():
                self.save_csv_data(csv_data, f"{output_dir}/cluster_{key}.csv")
            self.save_human_readable(
                cluster_data["human_readable"], f"{output_dir}/cluster_info.txt"
            )

        # Generate network data
        network_data = self.generate_network_data()
        if network_data:
            for key, csv_data in network_data["csv_data"].items():
                self.save_csv_data(csv_data, f"{output_dir}/network_{key}.csv")
            self.save_human_readable(
                network_data["human_readable"], f"{output_dir}/network_info.txt"
            )

        # Generate CBox data
        cbox_data = self.generate_cbox_data()
        if cbox_data:
            self.save_csv_data(cbox_data["csv_data"], f"{output_dir}/cboxes.csv")
            self.save_human_readable(
                cbox_data["human_readable"], f"{output_dir}/cboxes_info.txt"
            )

        # Generate CNode data
        cnode_data = self.generate_cnode_data()
        if cnode_data:
            self.save_csv_data(cnode_data["csv_data"], f"{output_dir}/cnodes.csv")
            self.save_human_readable(
                cnode_data["human_readable"], f"{output_dir}/cnodes_info.txt"
            )

        # Generate DBox data
        dbox_data = self.generate_dbox_data()
        if dbox_data:
            self.save_csv_data(dbox_data["csv_data"], f"{output_dir}/dboxes.csv")
            self.save_human_readable(
                dbox_data["human_readable"], f"{output_dir}/dboxes_info.txt"
            )

        # Generate DTray data
        dtray_data = self.generate_dtray_data()
        if dtray_data:
            self.save_csv_data(dtray_data["csv_data"], f"{output_dir}/dtrays.csv")
            self.save_human_readable(
                dtray_data["human_readable"], f"{output_dir}/dtrays_info.txt"
            )

        # Generate DNode data
        dnode_data = self.generate_dnode_data()
        if dnode_data:
            self.save_csv_data(dnode_data["csv_data"], f"{output_dir}/dnodes.csv")
            self.save_human_readable(
                dnode_data["human_readable"], f"{output_dir}/dnodes_info.txt"
            )

        print("\n🎉 All data generated successfully!")
        print(f"📁 Check the '{output_dir}' directory for all files")


def main():
    parser = argparse.ArgumentParser(
        description="Generate VAST API data for report generation"
    )
    parser.add_argument("--cluster", required=True, help="VAST cluster IP address")
    parser.add_argument("--username", help="VAST username")
    parser.add_argument("--password", help="VAST password")
    parser.add_argument("--token", help="VAST API token")
    parser.add_argument(
        "--output-dir",
        default="api_data_output",
        help="Output directory for generated files",
    )

    args = parser.parse_args()

    if not args.token and (not args.username or not args.password):
        print(
            "Error: Either --token or both --username and --password must be provided"
        )
        sys.exit(1)

    generator = VastApiDataGenerator(
        cluster_ip=args.cluster,
        username=args.username,
        password=args.password,
        token=args.token,
    )

    generator.generate_all_data(args.output_dir)


if __name__ == "__main__":
    main()
