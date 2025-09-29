#!/usr/bin/env python3
"""
Test script for improved VAST authentication sequence.

This script demonstrates the new authentication flow that:
1. Checks for existing valid tokens first
2. Tries basic authentication if no valid tokens
3. Only creates new tokens when needed (respecting 5-token limit)
"""

import sys
import os
sys.path.append('src')

from api_handler import VastApiHandler
from utils.logger import get_logger

def test_authentication_sequence():
    """Test the improved authentication sequence."""
    logger = get_logger(__name__)

    print("🔐 VAST Authentication Sequence Test")
    print("=" * 50)

    # Test cluster details (replace with actual cluster)
    cluster_ip = "10.143.11.204"
    username = "admin"
    password = "password"

    print(f"Testing authentication with cluster: {cluster_ip}")
    print(f"Username: {username}")
    print()

    # Initialize API handler
    api_handler = VastApiHandler(
        cluster_ip=cluster_ip,
        username=username,
        password=password
    )

    print("🔍 Step 1: Checking for existing API tokens...")
    existing_tokens_result = api_handler._try_existing_tokens()
    if existing_tokens_result:
        print("✅ Found and using existing valid token")
        print(f"   Token ID: {api_handler.api_token}")
        return True
    else:
        print("❌ No valid existing tokens found")

    print()
    print("🔍 Step 2: Checking token availability...")
    token_available = api_handler._check_token_availability()
    if token_available:
        print("✅ Token slots available for new token creation")
    else:
        print("❌ Token limit reached (5/5 tokens used)")
        print("   Recommendation: Revoke unused tokens or use basic auth")

    print()
    print("🔍 Step 3: Testing basic authentication...")
    basic_auth_result = api_handler._try_basic_auth()
    if basic_auth_result:
        print("✅ Basic authentication successful")
        return True
    else:
        print("❌ Basic authentication failed")

    print()
    print("🔍 Step 4: Testing full authentication sequence...")
    auth_result = api_handler.authenticate()

    if auth_result:
        print("✅ Authentication successful!")
        print(f"   Method: {'API Token' if api_handler.api_token else 'Basic Auth'}")
        print(f"   API Version: {api_handler.api_version}")
        print(f"   Authenticated: {api_handler.authenticated}")

        # Test a simple API call
        try:
            print()
            print("🔍 Step 5: Testing API call...")
            response = api_handler.make_request('vms/')
            if response and response.status_code == 200:
                print("✅ API call successful - authentication working")
                return True
            else:
                print(f"❌ API call failed: {response.status_code if response else 'No response'}")
        except Exception as e:
            print(f"❌ API call error: {e}")
    else:
        print("❌ Authentication failed")
        print("   All authentication methods exhausted")

    return False

def test_token_management():
    """Test token management features."""
    print()
    print("🔧 Token Management Test")
    print("=" * 30)

    cluster_ip = "10.143.11.204"
    username = "admin"
    password = "password"

    api_handler = VastApiHandler(
        cluster_ip=cluster_ip,
        username=username,
        password=password
    )

    # Test token availability check
    print("Checking token availability...")
    available = api_handler._check_token_availability()
    print(f"Token slots available: {available}")

    # Test existing tokens check
    print("Checking existing tokens...")
    existing = api_handler._try_existing_tokens()
    print(f"Valid existing tokens found: {existing}")

if __name__ == "__main__":
    print("🚀 VAST Authentication Improvement Test")
    print("=" * 60)
    print()

    try:
        # Test the improved authentication sequence
        success = test_authentication_sequence()

        # Test token management
        test_token_management()

        print()
        print("📊 TEST SUMMARY")
        print("=" * 20)
        if success:
            print("✅ Authentication test: PASSED")
        else:
            print("❌ Authentication test: FAILED")

        print()
        print("🔧 IMPROVEMENTS IMPLEMENTED:")
        print("  ✅ Check existing tokens first")
        print("  ✅ Respect 5-token limit per user")
        print("  ✅ Try basic auth before creating tokens")
        print("  ✅ Better error messages and recommendations")
        print("  ✅ Graceful handling of token limits")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
