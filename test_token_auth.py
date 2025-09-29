#!/usr/bin/env python3
"""
Test script for VAST API token authentication

This script tests the new token authentication functionality
in the VAST As-Built Report Generator.
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api_handler import create_vast_api_handler
from utils.logger import get_logger, setup_logging


def test_token_authentication(cluster_ip: str, token: str):
    """Test token authentication with the VAST cluster."""

    print("🔐 TESTING VAST API TOKEN AUTHENTICATION")
    print("=" * 50)
    print(f"Cluster: {cluster_ip}")
    print(f"Token: {token[:10]}...{token[-4:] if len(token) > 14 else token}")
    print()

    # Set up logging
    config = {"logging": {"level": "INFO"}}
    setup_logging(config)
    logger = get_logger(__name__)

    try:
        # Create API handler with token
        api_handler = create_vast_api_handler(
            cluster_ip=cluster_ip, token=token, config=config
        )

        print("✅ API handler created with token")

        # Test authentication
        print("🔍 Testing authentication...")
        if api_handler.authenticate():
            print("✅ Authentication successful!")

            # Test API calls
            print("🔍 Testing API calls...")

            # Test cluster info
            cluster_data = api_handler.get_cluster_info()
            if cluster_data:
                print(
                    f"✅ Cluster info retrieved: {cluster_data.get('name', 'Unknown')}"
                )
            else:
                print("❌ Failed to retrieve cluster info")

            # Test VMs
            vms_data = api_handler.get_vms()
            if vms_data:
                print(f"✅ VMs data retrieved: {len(vms_data)} VMs found")
            else:
                print("❌ Failed to retrieve VMs data")

            # Test CNodes
            cnodes_data = api_handler.get_cnodes()
            if cnodes_data:
                print(f"✅ CNodes data retrieved: {len(cnodes_data)} CNodes found")
            else:
                print("❌ Failed to retrieve CNodes data")

            # Test DNodes
            dnodes_data = api_handler.get_dnodes()
            if dnodes_data:
                print(f"✅ DNodes data retrieved: {len(dnodes_data)} DNodes found")
            else:
                print("❌ Failed to retrieve DNodes data")

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


def test_username_password_fallback(cluster_ip: str, username: str, password: str):
    """Test that username/password still works as fallback."""

    print("\n🔐 TESTING USERNAME/PASSWORD FALLBACK")
    print("=" * 50)
    print(f"Cluster: {cluster_ip}")
    print(f"Username: {username}")
    print()

    # Set up logging
    config = {"logging": {"level": "INFO"}}
    setup_logging(config)
    logger = get_logger(__name__)

    try:
        # Create API handler with username/password
        api_handler = create_vast_api_handler(
            cluster_ip=cluster_ip, username=username, password=password, config=config
        )

        print("✅ API handler created with username/password")

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
            "Usage: python test_token_auth.py <cluster_ip> [token] [username] [password]"
        )
        print("Examples:")
        print("  python test_token_auth.py 10.143.11.204 YOUR_TOKEN")
        print("  python test_token_auth.py 10.143.11.204 YOUR_TOKEN admin 123456")
        sys.exit(1)

    cluster_ip = sys.argv[1]
    token = sys.argv[2] if len(sys.argv) > 2 else None
    username = sys.argv[3] if len(sys.argv) > 3 else None
    password = sys.argv[4] if len(sys.argv) > 4 else None

    success = True

    # Test token authentication if provided
    if token:
        if not test_token_authentication(cluster_ip, token):
            success = False

    # Test username/password fallback if provided
    if username and password:
        if not test_username_password_fallback(cluster_ip, username, password):
            success = False

    if success:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n❌ SOME TESTS FAILED!")
        sys.exit(1)


if __name__ == "__main__":
    main()
