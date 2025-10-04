#!/usr/bin/env python3
"""
Fixed Curl Commands for VAST API

This script provides corrected curl commands that handle authentication errors
and provide better debugging information.
"""

import subprocess
import json
import sys

def test_authentication(cluster_ip: str, username: str, password: str):
    """Test authentication and provide debugging information."""
    print("🔐 TESTING AUTHENTICATION")
    print("=" * 40)
    
    # Test basic connectivity
    cmd = ["curl", "-k", "-s", "-u", f"{username}:{password}", f"https://{cluster_ip}/api/v7/clusters/"]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        response = result.stdout.strip()
        
        print(f"✅ Connection successful to {cluster_ip}")
        print(f"📊 Response length: {len(response)} characters")
        
        # Try to parse as JSON
        try:
            json_data = json.loads(response)
            if isinstance(json_data, dict) and "detail" in json_data:
                print(f"❌ Authentication error: {json_data['detail']}")
                return False
            elif isinstance(json_data, list):
                print(f"✅ Authentication successful! Found {len(json_data)} cluster(s)")
                return True
            else:
                print(f"✅ Authentication successful! Response: {json_data}")
                return True
        except json.JSONDecodeError:
            print(f"❌ Invalid JSON response: {response}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Connection failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def generate_fixed_curl_commands(cluster_ip: str, username: str, password: str):
    """Generate fixed curl commands with proper error handling."""
    
    print("🔧 FIXED CURL COMMANDS FOR VAST API")
    print("=" * 50)
    print(f"Cluster: {cluster_ip}")
    print(f"Username: {username}")
    print()
    
    # Test authentication first
    if not test_authentication(cluster_ip, username, password):
        print("\n❌ AUTHENTICATION FAILED")
        print("Please check your credentials and try again.")
        print("\n💡 TROUBLESHOOTING TIPS:")
        print("1. Verify the cluster IP address is correct")
        print("2. Check that the username and password are correct")
        print("3. Ensure the cluster is accessible from your network")
        print("4. Try using the VAST web interface to verify credentials")
        return
    
    print("\n✅ AUTHENTICATION SUCCESSFUL - GENERATING COMMANDS")
    print("=" * 60)
    
    # Generate commands with proper error handling
    commands = [
        {
            "name": "1️⃣ CLUSTER - Basic Information",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'if type == "array" then .[] | [.id, .name, .mgmt_vip, .url, .build, .psnt, .guid, .uptime, .online_start_time, .deployment_time] | @csv else "Error: " + .detail end\'',
            "description": "Basic cluster information (ID, Name, VIP, Build, etc.)"
        },
        {
            "name": "2️⃣ CLUSTER - State Information", 
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'if type == "array" then .[] | [.state, .ssd_raid_state, .nvram_raid_state, .memory_raid_state, .leader_state, .leader_cnode, .mgmt_cnode, .mgmt_inner_vip, .mgmt_inner_vip_cnode, .enabled, .enable_similarity, .similarity_active, .skip_dedup, .dedup_active, .is_wb_raid_enabled, .wb_raid_layout, .dbox_ha_support, .enable_rack_level_resiliency, .b2b_configuration, .disable_metrics] | @csv else "Error: " + .detail end\'',
            "description": "Cluster state and configuration information"
        },
        {
            "name": "3️⃣ CLUSTER - Capacity Information",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'if type == "array" then .[] | [.usable_capacity_tb, .free_usable_capacity_tb, .drr_text, .physical_space_tb, .physical_space_in_use_tb, .free_physical_space_tb, .physical_space_in_use_percent, .logical_space_tb, .logical_space_in_use_tb, .free_logical_space_tb, .logical_space_in_use_percent] | @csv else "Error: " + .detail end\'',
            "description": "Storage capacity and space information"
        },
        {
            "name": "4️⃣ CLUSTER - Encryption Information",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'if type == "array" then .[] | [.enable_encryption, .S3_ENABLE_ONLY_AES_CIPHERS, .encryption_type, .ekm_servers, .ekm_address, .ekm_port, .ekm_auth_domain, .secondary_ekm_address, .secondary_ekm_port] | @csv else "Error: " + .detail end\'',
            "description": "Encryption configuration and EKM settings"
        },
        {
            "name": "5️⃣ NETWORK - Cluster Configuration",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/clusters/" | jq -r \'if type == "array" then .[] | [.management_vips, .external_gateways, .dns, .ntp, .ext_netmask, .auto_ports_ext_iface, .b2b_ipmi, .eth_mtu, .ib_mtu, .ipmi_gateway, .ipmi_netmask] | @csv else "Error: " + .detail end\'',
            "description": "Cluster network configuration (VIPs, gateways, DNS, etc.)"
        },
        {
            "name": "6️⃣ NETWORK - CNode Settings",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/vms/1/network_settings/" | jq -r \'if type == "array" then .[] | select(.node_type == "Cnode") | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .net_type] | @csv else "Error: " + .detail end\'',
            "description": "CNode network settings and hardware information"
        },
        {
            "name": "7️⃣ NETWORK - DNode Settings",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/vms/1/network_settings/" | jq -r \'if type == "array" then .[] | select(.node_type == "Dnode") | [.id, .hostname, .mgmt_ip, .ipmi_ip, .box_vendor, .vast_os, .node_type, .box_name, .box_uid, .is_ceres, .is_vms_host, .position, .net_type] | @csv else "Error: " + .detail end\'',
            "description": "DNode network settings and hardware information"
        },
        {
            "name": "8️⃣ CBOXES",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v1/cboxes/" | jq -r \'if type == "array" then .[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state] | @csv else "Error: " + .detail end\'',
            "description": "CBox hardware information with rack positioning"
        },
        {
            "name": "9️⃣ CNODES",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/cnodes/" | jq -r \'if type == "array" then .[] | [.id, .name, .hostname, .guid, .cluster, .cbox_id, .cbox, .box_vendor, .os_version, .build, .state, .display_state, .sync, .is_leader, .is_mgmt, .vlan, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv else "Error: " + .detail end\'',
            "description": "CNode hardware information with management details"
        },
        {
            "name": "🔟 DBOXES",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/dboxes/" | jq -r \'if type == "array" then .[] | [.id, .name, .url, .cluster_id, .cluster, .guid, .rack_unit, .rack_name, .state, .sync, .hardware_type] | @csv else "Error: " + .detail end\'',
            "description": "DBox hardware information with rack positioning"
        },
        {
            "name": "1️⃣1️⃣ DTRAYS",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/dtrays/" | jq -r \'if type == "array" then .[] | [.id, .name, .url, .guid, .cluster, .dbox_id, .dbox, .position, .dnodes, .hardware_type, .state, .sync, .bmc_ip, .mcu_state, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv else "Error: " + .detail end\'',
            "description": "DTray hardware information with BMC details"
        },
        {
            "name": "1️⃣2️⃣ DNODES",
            "command": f'curl -k -u "{username}:{password}" "https://{cluster_ip}/api/v7/dnodes/" | jq -r \'if type == "array" then .[] | [.id, .name, .hostname, .guid, .cluster, .dbox_id, .dbox, .position, .os_version, .build, .state, .sync, .mgmt_ip, .ipmi_ip, .host_label, .enabled, .bmc_state, .bmc_state_reason, .bmc_fw_version] | @csv else "Error: " + .detail end\'',
            "description": "DNode hardware information with management details"
        }
    ]
    
    print("📋 FIXED CURL COMMANDS WITH ERROR HANDLING")
    print("=" * 60)
    print()
    
    for i, cmd_info in enumerate(commands, 1):
        print(f"{cmd_info['name']}")
        print("-" * 50)
        print(f"Description: {cmd_info['description']}")
        print()
        print("Command:")
        print(cmd_info['command'])
        print()
        
        # Test the command
        print("🧪 Testing command...")
        try:
            result = subprocess.run(cmd_info['command'], shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                output = result.stdout.strip()
                if "Error:" in output:
                    print(f"❌ {output}")
                else:
                    print(f"✅ Success! Output length: {len(output)} characters")
                    if output:
                        lines = output.split('\n')
                        print(f"📊 Found {len(lines)} line(s) of data")
                        if len(lines) <= 3:
                            print(f"📋 Sample output: {output}")
                        else:
                            print(f"📋 Sample output (first 3 lines):")
                            for line in lines[:3]:
                                print(f"   {line}")
            else:
                print(f"❌ Command failed with return code {result.returncode}")
                print(f"Error: {result.stderr}")
        except subprocess.TimeoutExpired:
            print("❌ Command timed out")
        except Exception as e:
            print(f"❌ Error running command: {e}")
        
        print()
        print("=" * 60)
        print()

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 fixed_curl_commands.py <cluster_ip> <username> <password>")
        print("Example: python3 fixed_curl_commands.py 10.143.11.204 admin password")
        sys.exit(1)
    
    cluster_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    generate_fixed_curl_commands(cluster_ip, username, password)

if __name__ == "__main__":
    main()
