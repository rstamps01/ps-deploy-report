#!/usr/bin/env python3
"""
Excel Population Demo Script

This script demonstrates how to use the curl commands to populate the Excel file
with specific VAST cluster data, showing the exact process step by step.
"""

import csv
import json
import subprocess
import sys


def run_curl_command(
    cluster_ip: str,
    username: str,
    password: str,
    endpoint: str,
    jq_filter: str,
    api_version: str = "v7",
):
    """Run a curl command and return the CSV output."""
    url = f"https://{cluster_ip}/api/{api_version}/{endpoint}"
    auth = f"{username}:{password}"

    cmd = ["curl", "-k", "-s", "-u", auth, url]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        json_data = json.loads(result.stdout)

        # Apply jq filter manually
        if isinstance(json_data, list) and json_data:
            if "select" in jq_filter:
                # Handle select filters
                if "Cnode" in jq_filter:
                    filtered_data = [
                        item for item in json_data if item.get("node_type") == "Cnode"
                    ]
                elif "Dnode" in jq_filter:
                    filtered_data = [
                        item for item in json_data if item.get("node_type") == "Dnode"
                    ]
                else:
                    filtered_data = json_data
            else:
                filtered_data = json_data

            # Extract fields based on jq filter
            if "clusters" in endpoint:
                cluster = filtered_data[0] if filtered_data else {}
                if "id, .name, .mgmt_vip" in jq_filter:
                    return [
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
                    ]
                elif "state, .ssd_raid_state" in jq_filter:
                    return [
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
                        cluster.get("enable_similarity"),
                        cluster.get("similarity_active"),
                        cluster.get("skip_dedup"),
                        cluster.get("dedup_active"),
                        cluster.get("is_wb_raid_enabled"),
                        cluster.get("wb_raid_layout"),
                        cluster.get("dbox_ha_support"),
                        cluster.get("enable_rack_level_resiliency"),
                        cluster.get("b2b_configuration"),
                        cluster.get("disable_metrics"),
                    ]
                elif "usable_capacity_tb" in jq_filter:
                    return [
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
                    ]
                elif "enable_encryption" in jq_filter:
                    return [
                        cluster.get("enable_encryption"),
                        cluster.get("S3_ENABLE_ONLY_AES_CIPHERS"),
                        cluster.get("encryption_type"),
                        cluster.get("ekm_servers"),
                        cluster.get("ekm_address"),
                        cluster.get("ekm_port"),
                        cluster.get("ekm_auth_domain"),
                        cluster.get("secondary_ekm_address"),
                        cluster.get("secondary_ekm_port"),
                    ]
                elif "management_vips" in jq_filter:
                    return [
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
                    ]
            elif "vms" in endpoint:
                results = []
                for item in filtered_data:
                    if "Cnode" in jq_filter:
                        results.append(
                            [
                                item.get("id"),
                                item.get("hostname"),
                                item.get("mgmt_ip"),
                                item.get("ipmi_ip"),
                                item.get("box_vendor"),
                                item.get("vast_os"),
                                item.get("node_type"),
                                item.get("box_name"),
                                item.get("box_uid"),
                                item.get("is_ceres"),
                                item.get("is_vms_host"),
                                item.get("net_type"),
                            ]
                        )
                    elif "Dnode" in jq_filter:
                        results.append(
                            [
                                item.get("id"),
                                item.get("hostname"),
                                item.get("mgmt_ip"),
                                item.get("ipmi_ip"),
                                item.get("box_vendor"),
                                item.get("vast_os"),
                                item.get("node_type"),
                                item.get("box_name"),
                                item.get("box_uid"),
                                item.get("is_ceres"),
                                item.get("is_vms_host"),
                                item.get("position"),
                                item.get("net_type"),
                            ]
                        )
                return results
            elif "cboxes" in endpoint:
                results = []
                for item in filtered_data:
                    results.append(
                        [
                            item.get("id"),
                            item.get("name"),
                            item.get("url"),
                            item.get("cluster_id"),
                            item.get("cluster"),
                            item.get("guid"),
                            item.get("rack_unit"),
                            item.get("rack_name"),
                            item.get("state"),
                        ]
                    )
                return results
            elif "cnodes" in endpoint:
                results = []
                for item in filtered_data:
                    results.append(
                        [
                            item.get("id"),
                            item.get("name"),
                            item.get("hostname"),
                            item.get("guid"),
                            item.get("cluster"),
                            item.get("cbox_id"),
                            item.get("cbox"),
                            item.get("box_vendor"),
                            item.get("os_version"),
                            item.get("build"),
                            item.get("state"),
                            item.get("display_state"),
                            item.get("sync"),
                            item.get("is_leader"),
                            item.get("is_mgmt"),
                            item.get("vlan"),
                            item.get("mgmt_ip"),
                            item.get("ipmi_ip"),
                            item.get("host_label"),
                            item.get("enabled"),
                            item.get("bmc_state"),
                            item.get("bmc_state_reason"),
                            item.get("bmc_fw_version"),
                        ]
                    )
                return results
            elif "dboxes" in endpoint:
                results = []
                for item in filtered_data:
                    results.append(
                        [
                            item.get("id"),
                            item.get("name"),
                            item.get("url"),
                            item.get("cluster_id"),
                            item.get("cluster"),
                            item.get("guid"),
                            item.get("rack_unit"),
                            item.get("rack_name"),
                            item.get("state"),
                            item.get("sync"),
                            item.get("hardware_type"),
                        ]
                    )
                return results
            elif "dtrays" in endpoint:
                results = []
                for item in filtered_data:
                    results.append(
                        [
                            item.get("id"),
                            item.get("name"),
                            item.get("url"),
                            item.get("guid"),
                            item.get("cluster"),
                            item.get("dbox_id"),
                            item.get("dbox"),
                            item.get("position"),
                            item.get("dnodes"),
                            item.get("hardware_type"),
                            item.get("state"),
                            item.get("sync"),
                            item.get("bmc_ip"),
                            item.get("mcu_state"),
                            item.get("enabled"),
                            item.get("bmc_state"),
                            item.get("bmc_state_reason"),
                            item.get("bmc_fw_version"),
                        ]
                    )
                return results
            elif "dnodes" in endpoint:
                results = []
                for item in filtered_data:
                    results.append(
                        [
                            item.get("id"),
                            item.get("name"),
                            item.get("hostname"),
                            item.get("guid"),
                            item.get("cluster"),
                            item.get("dbox_id"),
                            item.get("dbox"),
                            item.get("position"),
                            item.get("os_version"),
                            item.get("build"),
                            item.get("state"),
                            item.get("sync"),
                            item.get("mgmt_ip"),
                            item.get("ipmi_ip"),
                            item.get("host_label"),
                            item.get("enabled"),
                            item.get("bmc_state"),
                            item.get("bmc_state_reason"),
                            item.get("bmc_fw_version"),
                        ]
                    )
                return results

        return []

    except subprocess.CalledProcessError as e:
        print(f"Error calling API: {e}")
        return []
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return []
    except Exception as e:
        print(f"Unexpected error: {e}")
        return []


def demonstrate_excel_population(cluster_ip: str, username: str, password: str):
    """Demonstrate how to populate Excel with VAST API data."""

    print("🎯 EXCEL POPULATION DEMONSTRATION")
    print("=" * 50)
    print(f"Cluster: {cluster_ip}")
    print(f"Username: {username}")
    print()

    # Define the sections and their corresponding curl commands
    sections = [
        {
            "name": "1️⃣ CLUSTER - Basic Information",
            "endpoint": "clusters/",
            "jq_filter": "id, .name, .mgmt_vip, .url, .build, .psnt, .guid, .uptime, .online_start_time, .deployment_time",
            "headers": [
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
        },
        {
            "name": "2️⃣ CLUSTER - State Information",
            "endpoint": "clusters/",
            "jq_filter": "state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics",
            "headers": [
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
                "Enable Similarity",
                "Similarity Active",
                "Skip Dedup",
                "Dedup Active",
                "Is WB RAID Enabled",
                "WB RAID Layout",
                "DBox HA Support",
                "Enable Rack Level Resiliency",
                "B2B Configuration",
                "Disable Metrics",
            ],
        },
        {
            "name": "3️⃣ CLUSTER - Capacity Information",
            "endpoint": "clusters/",
            "jq_filter": "usable_capacity_tb, .free_usable_capacity_tb, .drr_text, .physical_space_tb, .physical_space_in_use_tb, .free_physical_space_tb, .physical_space_in_use_percent, .logical_space_tb, .logical_space_in_use_tb, .free_logical_space_tb, .logical_space_in_use_percent",
            "headers": [
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
        },
        {
            "name": "4️⃣ CLUSTER - Encryption Information",
            "endpoint": "clusters/",
            "jq_filter": "enable_encryption, .S3_ENABLE_ONLY_AES_CIPHERS, .encryption_type, .ekm_servers, .ekm_address, .ekm_port, .ekm_auth_domain, .secondary_ekm_address, .secondary_ekm_port",
            "headers": [
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
        },
        {
            "name": "5️⃣ NETWORK - Cluster Configuration",
            "endpoint": "clusters/",
            "jq_filter": "management_vips, .external_gateways, .dns, .ntp, .ext_netmask, .auto_ports_ext_iface, .b2b_ipmi, .eth_mtu, .ib_mtu, .ipmi_gateway, .ipmi_netmask",
            "headers": [
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
        },
        {
            "name": "6️⃣ NETWORK - CNode Settings",
            "endpoint": "vms/1/network_settings/",
            "jq_filter": 'select(.node_type == "Cnode") | .id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .net_type',
            "headers": [
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
            ],
        },
        {
            "name": "7️⃣ NETWORK - DNode Settings",
            "endpoint": "vms/1/network_settings/",
            "jq_filter": 'select(.node_type == "Dnode") | .id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .position, .net_type',
            "headers": [
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
            ],
        },
        {
            "name": "8️⃣ CBOXES",
            "endpoint": "cboxes/",
            "jq_filter": "id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state",
            "headers": [
                "ID",
                "Name",
                "URL",
                "Cluster ID",
                "Cluster",
                "GUID",
                "Rack Unit",
                "Rack Name",
                "State",
            ],
            "api_version": "v1",
        },
        {
            "name": "9️⃣ CNODES",
            "endpoint": "cnodes/",
            "jq_filter": "id, .name, .hostname, .guid, .cluster, .cbox_id, .cbox, .box_vendor, .os_version, .build, .state, .display_state, .sync, .is_leader, .is_mgmt, .vlan, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version",
            "headers": [
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
            ],
        },
        {
            "name": "🔟 DBOXES",
            "endpoint": "dboxes/",
            "jq_filter": "id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state, .sync, .hardware_type",
            "headers": [
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
            ],
        },
        {
            "name": "1️⃣1️⃣ DTRAYS",
            "endpoint": "dtrays/",
            "jq_filter": "id, .name, .url, .guid, .cluster, .dbox_id, .dbox, .position, .dnodes, .hardware_type, .state, .sync, .bmc_ip, .mcu_state, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version",
            "headers": [
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
            ],
        },
        {
            "name": "1️⃣2️⃣ DNODES",
            "endpoint": "dnodes/",
            "jq_filter": "id, .name, .hostname, .guid, .cluster, .dbox_id, .dbox, .position, .os_version, .build, .state, .sync, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version",
            "headers": [
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
            ],
        },
    ]

    # Process each section
    for section in sections:
        print(f"\n{section['name']}")
        print("-" * 50)

        # Get the data
        api_version = section.get("api_version", "v7")
        data = run_curl_command(
            cluster_ip,
            username,
            password,
            section["endpoint"],
            section["jq_filter"],
            api_version,
        )

        if data:
            if isinstance(data[0], list):
                # Multiple rows of data
                print(f"✅ Found {len(data)} records")
                print("📋 Headers:", ", ".join(section["headers"]))
                print("📊 Sample data:")
                for i, row in enumerate(data[:3]):  # Show first 3 rows
                    print(f"   Row {i+1}: {row}")
                if len(data) > 3:
                    print(f"   ... and {len(data) - 3} more rows")
            else:
                # Single row of data
                print("✅ Found 1 record")
                print("📋 Headers:", ", ".join(section["headers"]))
                print("📊 Data:", data)

            # Show the curl command
            print(f"\n🔧 Curl Command:")
            if "select" in section["jq_filter"]:
                print(
                    f'curl -k -u "{username}:password" "https://{cluster_ip}/api/{api_version}/{section["endpoint"]}" | jq -r \'.[] | {section["jq_filter"]} | @csv\''
                )
            else:
                print(
                    f'curl -k -u "{username}:password" "https://{cluster_ip}/api/{api_version}/{section["endpoint"]}" | jq -r \'.[] | [{section["jq_filter"]}] | @csv\''
                )

            # Save to CSV file
            filename = f"excel_data_{section['name'].split(' ')[1].lower().replace('️', '').replace(' ', '_')}.csv"
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(section["headers"])
                if isinstance(data[0], list):
                    for row in data:
                        writer.writerow(row)
                else:
                    writer.writerow(data)
            print(f"💾 Saved to: {filename}")
        else:
            print("❌ No data found (likely due to SSL certificate issues)")
            print(f"🔧 Curl Command:")
            if "select" in section["jq_filter"]:
                print(
                    f'curl -k -u "{username}:password" "https://{cluster_ip}/api/{api_version}/{section["endpoint"]}" | jq -r \'.[] | {section["jq_filter"]} | @csv\''
                )
            else:
                print(
                    f'curl -k -u "{username}:password" "https://{cluster_ip}/api/{api_version}/{section["endpoint"]}" | jq -r \'.[] | [{section["jq_filter"]}] | @csv\''
                )

    print(f"\n🎉 DEMONSTRATION COMPLETE!")
    print("=" * 50)
    print("📋 Next Steps:")
    print("1. Run the curl commands above with your actual cluster")
    print("2. Copy the CSV output")
    print("3. Paste into Excel in the 'ADD CURL COMMANDS HERE' columns")
    print("4. Use 'Text to Columns' with comma delimiter")
    print("5. Verify the data matches your cluster configuration")


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: python3 demo_excel_population.py <cluster_ip> <username> <password>"
        )
        print("Example: python3 demo_excel_population.py 10.143.11.204 admin password")
        sys.exit(1)

    cluster_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]

    demonstrate_excel_population(cluster_ip, username, password)


if __name__ == "__main__":
    main()
