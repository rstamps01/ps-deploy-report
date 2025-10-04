#!/usr/bin/env python3
"""
VAST Authentication Test Script

This script helps you test different authentication methods and credentials
to find the correct way to access your VAST cluster.
"""

import subprocess
import json
import sys

def test_credentials(cluster_ip: str, username: str, password: str):
    """Test different authentication methods."""
    
    print("🔐 VAST AUTHENTICATION TEST")
    print("=" * 40)
    print(f"Cluster: {cluster_ip}")
    print(f"Username: {username}")
    print()
    
    # Test different API versions
    api_versions = ["v7", "v6", "v5", "v4", "v3", "v2", "v1"]
    
    for version in api_versions:
        print(f"🧪 Testing API version {version}...")
        
        cmd = ["curl", "-k", "-s", "-u", f"{username}:{password}", f"https://{cluster_ip}/api/{version}/clusters/"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            response = result.stdout.strip()
            
            if response:
                try:
                    json_data = json.loads(response)
                    if isinstance(json_data, dict) and "detail" in json_data:
                        print(f"   ❌ {version}: {json_data['detail']}")
                    elif isinstance(json_data, list):
                        print(f"   ✅ {version}: SUCCESS! Found {len(json_data)} cluster(s)")
                        return version
                    else:
                        print(f"   ✅ {version}: SUCCESS! Response: {json_data}")
                        return version
                except json.JSONDecodeError:
                    print(f"   ❌ {version}: Invalid JSON - {response}")
            else:
                print(f"   ❌ {version}: Empty response")
                
        except subprocess.CalledProcessError as e:
            print(f"   ❌ {version}: HTTP Error {e.returncode}")
        except subprocess.TimeoutExpired:
            print(f"   ❌ {version}: Timeout")
        except Exception as e:
            print(f"   ❌ {version}: {e}")
    
    return None

def test_different_endpoints(cluster_ip: str, username: str, password: str, api_version: str):
    """Test different endpoints to find working ones."""
    
    print(f"\n🔍 TESTING ENDPOINTS WITH API {api_version}")
    print("=" * 50)
    
    endpoints = [
        "clusters/",
        "vms/",
        "cboxes/",
        "cnodes/",
        "dboxes/",
        "dtrays/",
        "dnodes/",
        "system/",
        "health/"
    ]
    
    working_endpoints = []
    
    for endpoint in endpoints:
        print(f"🧪 Testing {endpoint}...")
        
        cmd = ["curl", "-k", "-s", "-u", f"{username}:{password}", f"https://{cluster_ip}/api/{api_version}/{endpoint}"]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=10)
            response = result.stdout.strip()
            
            if response:
                try:
                    json_data = json.loads(response)
                    if isinstance(json_data, dict) and "detail" in json_data:
                        print(f"   ❌ {endpoint}: {json_data['detail']}")
                    elif isinstance(json_data, list):
                        print(f"   ✅ {endpoint}: SUCCESS! Found {len(json_data)} items")
                        working_endpoints.append(endpoint)
                    else:
                        print(f"   ✅ {endpoint}: SUCCESS! Response: {json_data}")
                        working_endpoints.append(endpoint)
                except json.JSONDecodeError:
                    print(f"   ❌ {endpoint}: Invalid JSON - {response}")
            else:
                print(f"   ❌ {endpoint}: Empty response")
                
        except subprocess.CalledProcessError as e:
            print(f"   ❌ {endpoint}: HTTP Error {e.returncode}")
        except subprocess.TimeoutExpired:
            print(f"   ❌ {endpoint}: Timeout")
        except Exception as e:
            print(f"   ❌ {endpoint}: {e}")
    
    return working_endpoints

def main():
    if len(sys.argv) != 4:
        print("Usage: python3 test_auth.py <cluster_ip> <username> <password>")
        print("Example: python3 test_auth.py 10.143.11.204 admin password")
        sys.exit(1)
    
    cluster_ip = sys.argv[1]
    username = sys.argv[2]
    password = sys.argv[3]
    
    # Test authentication
    working_version = test_credentials(cluster_ip, username, password)
    
    if working_version:
        print(f"\n🎉 AUTHENTICATION SUCCESSFUL!")
        print(f"✅ Working API version: {working_version}")
        
        # Test endpoints
        working_endpoints = test_different_endpoints(cluster_ip, username, password, working_version)
        
        if working_endpoints:
            print(f"\n📋 WORKING ENDPOINTS:")
            for endpoint in working_endpoints:
                print(f"   ✅ /api/{working_version}/{endpoint}")
            
            print(f"\n💡 NEXT STEPS:")
            print(f"1. Use API version {working_version} for your curl commands")
            print(f"2. The following endpoints are available:")
            for endpoint in working_endpoints:
                print(f"   - https://{cluster_ip}/api/{working_version}/{endpoint}")
            print(f"3. Run the fixed curl commands script:")
            print(f"   python3 fixed_curl_commands.py {cluster_ip} {username} {password}")
        else:
            print(f"\n❌ No working endpoints found")
    else:
        print(f"\n❌ AUTHENTICATION FAILED")
        print(f"\n💡 TROUBLESHOOTING SUGGESTIONS:")
        print(f"1. Verify the cluster IP address: {cluster_ip}")
        print(f"2. Check the username: {username}")
        print(f"3. Verify the password is correct")
        print(f"4. Ensure the cluster is accessible from your network")
        print(f"5. Try accessing the VAST web interface at https://{cluster_ip}")
        print(f"6. Check if there are any firewall rules blocking access")
        print(f"7. Verify the cluster is running and healthy")

if __name__ == "__main__":
    main()
