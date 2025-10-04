#!/usr/bin/env python3
"""
VAST API Curl Command Generator

This script generates the exact curl commands needed to populate the empty columns
in the API-Summary worksheet, formatted for easy copy-paste into Excel.

Usage:
    python3 generate_curl_commands.py --cluster 10.143.11.204 --username admin --password password
"""

import argparse
import sys


def generate_curl_commands(cluster_ip: str, username: str, password: str):
    """Generate curl commands for each section in the API-Summary worksheet."""

    print("🔧 VAST API CURL COMMAND GENERATOR")
    print("=" * 50)
    print(f"Cluster: {cluster_ip}")
    print(f"Username: {username}")
    print()

    # Authentication string
    auth = f"{username}:{password}"

    print("📋 CURL COMMANDS FOR API-SUMMARY WORKSHEET")
    print("=" * 50)
    print()

    # 1. Cluster Section
    print("1️⃣ CLUSTER SECTION")
    print("-" * 20)
    print("Basic Cluster Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'.[] | [.id, .name, .mgmt_vip, .url, .build, .psnt, .guid, .uptime, .online_start_time, .deployment_time] | @csv\''
    )
    print()
    print("Cluster State Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'.[] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv\''
    )
    print()
    print("Cluster Capacity Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'.[] | [.usable_capacity_tb, .free_usable_capacity_tb, .drr_text, .physical_space_tb, .physical_space_in_use_tb, .free_physical_space_tb, .physical_space_in_use_percent, .logical_space_tb, .logical_space_in_use_tb, .free_logical_space_tb, .logical_space_in_use_percent] | @csv\''
    )
    print()
    print("Cluster Encryption Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'.[] | [.enable_encryption, .S3_ENABLE_ONLY_AES_CIPHERS, .encryption_type, .ekm_servers, .ekm_address, .ekm_port, .ekm_auth_domain, .secondary_ekm_address, .secondary_ekm_port] | @csv\''
    )
    print()

    # 2. Network Section - Cluster
    print("2️⃣ NETWORK SECTION - CLUSTER")
    print("-" * 30)
    print("Cluster Network Configuration (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'.[] | [.management_vips, .external_gateways, .dns, .ntp, .ext_netmask, .auto_ports_ext_iface, .b2b_ipmi, .eth_mtu, .ib_mtu, .ipmi_gateway, .ipmi_netmask] | @csv\''
    )
    print()

    # 3. Network Section - CNodes
    print("3️⃣ NETWORK SECTION - CNODES")
    print("-" * 30)
    print("CNode Network Settings (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/vms/1/network_settings/" | jq -r \'.[] | select(.node_type == "Cnode") | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .net_type] | @csv\''
    )
    print()

    # 4. Network Section - DNodes
    print("4️⃣ NETWORK SECTION - DNODES")
    print("-" * 30)
    print("DNode Network Settings (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/vms/1/network_settings/" | jq -r \'.[] | select(.node_type == "Dnode") | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .position, .net_type] | @csv\''
    )
    print()

    # 5. CBoxes Section
    print("5️⃣ CBOXES SECTION")
    print("-" * 20)
    print("CBox Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v1/cboxes/" | jq -r \'.[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state] | @csv\''
    )
    print()
    print("Specific CBox Details (for IDs 1, 3, 4):")
    for cbox_id in [1, 3, 4]:
        print(
            f'curl -k -u "{auth}" "https://{cluster_ip}/api/v1/cboxes/{cbox_id}" | jq -r \'[.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state] | @csv\''
        )
    print()

    # 6. CNodes Section
    print("6️⃣ CNODES SECTION")
    print("-" * 20)
    print("CNode Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/cnodes/" | jq -r \'.[] | [.id, .name, .hostname, .guid, .cluster, .cbox_id, .cbox, .box_vendor, .os_version, .build, .state, .display_state, .sync, .is_leader, .is_mgmt, .vlan, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv\''
    )
    print()
    print("Specific CNode Details (for IDs 3, 2, 6):")
    for cnode_id in [3, 2, 6]:
        print(
            f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/cnodes/{cnode_id}" | jq -r \'[.id, .name, .hostname, .guid, .cluster, .cbox_id, .cbox, .box_vendor, .os_version, .build, .state, .display_state, .sync, .is_leader, .is_mgmt, .vlan, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv\''
        )
    print()

    # 7. DBoxes Section
    print("7️⃣ DBOXES SECTION")
    print("-" * 20)
    print("DBox Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/dboxes/" | jq -r \'.[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state, .sync, .hardware_type] | @csv\''
    )
    print()

    # 8. DTrays Section
    print("8️⃣ DTRAYS SECTION")
    print("-" * 20)
    print("DTray Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/dtrays/" | jq -r \'.[] | [.id, .name, .url, .guid, .cluster, .dbox_id, .dbox, .position, .dnodes, .hardware_type, .state, .sync, .bmc_ip, .mcu_state, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv\''
    )
    print()

    # 9. DNodes Section
    print("9️⃣ DNODES SECTION")
    print("-" * 20)
    print("DNode Information (CSV format):")
    print(
        f'curl -k -u "{auth}" "https://{cluster_ip}/api/v7/dnodes/" | jq -r \'.[] | [.id, .name, .hostname, .guid, .cluster, .dbox_id, .dbox, .position, .os_version, .build, .state, .sync, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv\''
    )
    print()

    print("📋 USAGE INSTRUCTIONS")
    print("=" * 30)
    print("1. Copy the curl commands above")
    print("2. Run them in your terminal")
    print("3. Copy the CSV output")
    print("4. Paste into Excel in the 'ADD CURL COMMANDS HERE' columns")
    print("5. Use 'Text to Columns' with comma delimiter in Excel")
    print()
    print("💡 TIP: For easier Excel import, save output to files:")
    print("   curl ... > cluster_basic.csv")
    print("   curl ... > cluster_state.csv")
    print("   curl ... > cboxes.csv")
    print("   etc.")
    print()
    print(
        "🔧 ALTERNATIVE: Use the generate_api_data.py script for automated file generation"
    )


def main():
    parser = argparse.ArgumentParser(
        description="Generate curl commands for VAST API data collection"
    )
    parser.add_argument("--cluster", required=True, help="VAST cluster IP address")
    parser.add_argument("--username", required=True, help="VAST username")
    parser.add_argument("--password", required=True, help="VAST password")

    args = parser.parse_args()

    generate_curl_commands(args.cluster, args.username, args.password)


if __name__ == "__main__":
    main()
