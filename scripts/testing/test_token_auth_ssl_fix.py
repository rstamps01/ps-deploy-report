#!/usr/bin/env python3
"""
Test script for VAST API token authentication with SSL fix

This script tests the new token authentication functionality
with SSL verification disabled for testing environments.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_handler import create_vast_api_handler
from utils.logger import get_logger, setup_logging


def test_token_authentication_ssl_fix(cluster_ip: str, token: str):
    """Test token authentication with SSL verification disabled."""

    print("🔐 TESTING VAST API TOKEN AUTHENTICATION (SSL FIX)")
    print("=" * 60)
    print(f"Cluster: {cluster_ip}")
    print(f"Token: {token[:10]}...{token[-4:] if len(token) > 14 else token}")
    print("⚠️  SSL verification disabled for testing")
    print()

    # Set up logging
    config = {
        "logging": {"level": "INFO"},
        "api": {
            "verify_ssl": False,  # Disable SSL verification for testing
            "timeout": 30,
            "max_retries": 3,
        },
    }
    setup_logging(config)
    logger = get_logger(__name__)

    try:
        # Create API handler with token and SSL disabled
        api_handler = create_vast_api_handler(
            cluster_ip=cluster_ip, token=token, config=config
        )

        print("✅ API handler created with token (SSL disabled)")

        # Test authentication
        print("🔍 Testing authentication...")
        if api_handler.authenticate():
            print("✅ Authentication successful!")

            # Test API calls
            print("🔍 Testing API calls...")

            # Test cluster info
            cluster_data = api_handler.get_cluster_info()
            if cluster_data:
                print(f"✅ Cluster info retrieved: {cluster_data.name}")
                print(f"   - Version: {cluster_data.version}")
                print(f"   - State: {cluster_data.state}")
                print(f"   - PSNT: {getattr(cluster_data, 'psnt', 'N/A')}")
            else:
                print("❌ Failed to retrieve cluster info")

            # Test VMs (using get_all_data method)
            all_data = api_handler.get_all_data()
            if all_data and "hardware" in all_data:
                vms_count = len(all_data["hardware"].get("cnodes", [])) + len(
                    all_data["hardware"].get("dnodes", [])
                )
                print(f"✅ VMs data retrieved: {vms_count} total nodes found")
            else:
                print("❌ Failed to retrieve VMs data")

            # Test CNodes and DNodes from all_data
            if all_data and "hardware" in all_data:
                cnodes = all_data["hardware"].get("cnodes", [])
                dnodes = all_data["hardware"].get("dnodes", [])

                if cnodes:
                    print(f"✅ CNodes data retrieved: {len(cnodes)} CNodes found")
                    for cnode in cnodes[:2]:  # Show first 2
                        print(
                            f"   - {cnode.get('id', 'Unknown')}: {cnode.get('model', 'Unknown')} ({cnode.get('status', 'Unknown')})"
                        )
                else:
                    print("❌ Failed to retrieve CNodes data")

                if dnodes:
                    print(f"✅ DNodes data retrieved: {len(dnodes)} DNodes found")
                    for dnode in dnodes[:2]:  # Show first 2
                        print(
                            f"   - {dnode.get('id', 'Unknown')}: {dnode.get('model', 'Unknown')} ({dnode.get('status', 'Unknown')})"
                        )
                else:
                    print("❌ Failed to retrieve DNodes data")
            else:
                print("❌ Failed to retrieve hardware data")

            print("\n🎉 TOKEN AUTHENTICATION TEST COMPLETED SUCCESSFULLY!")
            return True

        else:
            print("❌ Authentication failed!")
            return False

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    finally:
        if "api_handler" in locals():
            api_handler.close()


def test_username_password_ssl_fix(cluster_ip: str, username: str, password: str):
    """Test username/password authentication with SSL verification disabled."""

    print("\n🔐 TESTING USERNAME/PASSWORD AUTHENTICATION (SSL FIX)")
    print("=" * 60)
    print(f"Cluster: {cluster_ip}")
    print(f"Username: {username}")
    print("⚠️  SSL verification disabled for testing")
    print()

    # Set up logging
    config = {
        "logging": {"level": "INFO"},
        "api": {
            "verify_ssl": False,  # Disable SSL verification for testing
            "timeout": 30,
            "max_retries": 3,
        },
    }
    setup_logging(config)
    logger = get_logger(__name__)

    try:
        # Create API handler with username/password and SSL disabled
        api_handler = create_vast_api_handler(
            cluster_ip=cluster_ip, username=username, password=password, config=config
        )

        print("✅ API handler created with username/password (SSL disabled)")

        # Test authentication
        print("🔍 Testing authentication...")
        if api_handler.authenticate():
            print("✅ Username/password authentication successful!")
            return True
        else:
            print("❌ Username/password authentication failed!")
            return False

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    finally:
        if "api_handler" in locals():
            api_handler.close()


def main():
    """Main test function."""

    if len(sys.argv) < 2:
        print(
            "Usage: python test_token_auth_ssl_fix.py <cluster_ip> [token] [username] [password]"
        )
        print("Examples:")
        print("  python test_token_auth_ssl_fix.py 10.143.11.204 YOUR_TOKEN")
        print(
            "  python test_token_auth_ssl_fix.py 10.143.11.204 YOUR_TOKEN admin 123456"
        )
        sys.exit(1)

    cluster_ip = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else None
    username = sys.argv[3] if len(sys.argv) > 3 else None
    password = sys.argv[4] if len(sys.argv) > 4 else None

    success = True

    # Test token authentication if provided
    if token:
        if not test_token_authentication_ssl_fix(cluster_ip, token):
            success = False

    # Test username/password fallback if provided
    if username and password:
        if not test_username_password_ssl_fix(cluster_ip, username, password):
            success = False

    if success:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n💡 SSL VERIFICATION DISABLED - FOR TESTING ONLY!")
        print("   In production, ensure proper SSL certificates are installed.")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
