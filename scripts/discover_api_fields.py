#!/usr/bin/env python3
"""
API Field Discovery Script for Multi-Rack Support

This script systematically discovers API endpoints and fields that support
multi-rack deployment identification and reporting.

Usage:
    python3 scripts/discover_api_fields.py --cluster <ip> --username <user> --password <pass>
"""

import json
import sys
import argparse
import logging
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.logger import get_logger

# Field discovery keywords
RACK_KEYWORDS = ["rack", "location", "position", "physical", "site"]
SWITCH_KEYWORDS = ["type", "role", "leaf", "spine", "topology"]
TOPOLOGY_KEYWORDS = ["topology", "connection", "connect", "neighbor", "uplink", "downlink"]


def extract_keys(obj, prefix=""):
    """Recursively extract all keys from nested objects."""
    keys = set()
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            if isinstance(value, (dict, list)):
                keys.update(extract_keys(value, full_key))
    elif isinstance(obj, list) and len(obj) > 0:
        keys.update(extract_keys(obj[0], prefix))
    return keys


def categorize_fields(fields):
    """Categorize fields by relevance."""
    rack_fields = []
    switch_fields = []
    topology_fields = []
    other_fields = []

    for field in fields:
        field_lower = field.lower()
        if any(keyword in field_lower for keyword in RACK_KEYWORDS):
            rack_fields.append(field)
        elif any(keyword in field_lower for keyword in SWITCH_KEYWORDS):
            switch_fields.append(field)
        elif any(keyword in field_lower for keyword in TOPOLOGY_KEYWORDS):
            topology_fields.append(field)
        else:
            other_fields.append(field)

    return {
        "rack_fields": sorted(rack_fields),
        "switch_fields": sorted(switch_fields),
        "topology_fields": sorted(topology_fields),
        "other_fields": sorted(other_fields)
    }


def discover_fields(endpoint, cluster_ip, username, password, logger):
    """Discover all fields in an API endpoint."""
    base_url = f"https://{cluster_ip}/api/v7"
    url = f"{base_url}{endpoint}"

    try:
        logger.info(f"Accessing: {url}")
        response = requests.get(
            url,
            auth=HTTPBasicAuth(username, password),
            verify=False,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        # Extract all unique keys from response
        if isinstance(data, list) and len(data) > 0:
            keys = set()
            for item in data:
                keys.update(extract_keys(item))
            return list(keys), data, True
        elif isinstance(data, dict):
            keys = extract_keys(data)
            return list(keys), data, True
        else:
            return [], data, True
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Endpoint not found: {endpoint} (404)")
            return [], None, False
        else:
            logger.error(f"HTTP error accessing {endpoint}: {e}")
            return [], None, False
    except requests.exceptions.RequestException as e:
        logger.error(f"Error accessing {endpoint}: {e}")
        return [], None, False


def save_sample_data(endpoint, data, output_dir):
    """Save sample API response data."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize endpoint name for filename
    filename = endpoint.strip("/").replace("/", "_") or "root"
    filepath = output_dir / f"{filename}.json"

    try:
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return filepath
    except Exception as e:
        print(f"Error saving sample data: {e}")
        return None


def main():
    """Main discovery function."""
    parser = argparse.ArgumentParser(
        description="Discover API fields for multi-rack support"
    )
    parser.add_argument(
        "--cluster",
        required=True,
        help="Cluster IP address"
    )
    parser.add_argument(
        "--username",
        required=True,
        help="API username"
    )
    parser.add_argument(
        "--password",
        required=True,
        help="API password"
    )
    parser.add_argument(
        "--output-dir",
        default="logs/api_responses",
        help="Output directory for API responses (default: logs/api_responses)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()
    
    # Setup logger
    logger = get_logger("api_discovery")
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Define endpoints to check
    endpoints = [
        "/cnodes/",
        "/dnodes/",
        "/cboxes/",
        "/dboxes/",
        "/switches/",
        "/racks/",              # Test if exists
        "/topology/",           # Test if exists
        "/network/topology/",   # Test if exists
        "/physical_layout/",    # Test if exists
        "/layout/",             # Test if exists
        "/dtrays/",             # Already known, but check for rack fields
    ]

    results = {}

    print("=" * 80)
    print("API FIELD DISCOVERY FOR MULTI-RACK SUPPORT")
    print("=" * 80)
    print(f"Cluster: {args.cluster}")
    print(f"Output Directory: {args.output_dir}")
    print("=" * 80)

    for endpoint in endpoints:
        print(f"\nChecking: {endpoint}")
        fields, data, available = discover_fields(
            endpoint, args.cluster, args.username, args.password, logger
        )

        if available and fields:
            print(f"  ✓ Available - Found {len(fields)} unique fields")
            categorized = categorize_fields(fields)
            results[endpoint] = {
                "available": True,
                "field_count": len(fields),
                "fields": fields,
                "categorized": categorized,
                "sample_data": data[0] if isinstance(data, list) and len(data) > 0 else data
            }

            # Print categorized fields
            if categorized["rack_fields"]:
                print(f"  • Rack-related fields ({len(categorized['rack_fields'])}):")
                for field in categorized["rack_fields"][:10]:  # Show first 10
                    print(f"    - {field}")
                if len(categorized["rack_fields"]) > 10:
                    print(f"    ... and {len(categorized['rack_fields']) - 10} more")

            if categorized["switch_fields"]:
                print(f"  • Switch-related fields ({len(categorized['switch_fields'])}):")
                for field in categorized["switch_fields"][:10]:
                    print(f"    - {field}")
                if len(categorized["switch_fields"]) > 10:
                    print(f"    ... and {len(categorized['switch_fields']) - 10} more")

            if categorized["topology_fields"]:
                print(f"  • Topology-related fields ({len(categorized['topology_fields'])}):")
                for field in categorized["topology_fields"][:10]:
                    print(f"    - {field}")
                if len(categorized["topology_fields"]) > 10:
                    print(f"    ... and {len(categorized['topology_fields']) - 10} more")

            # Save sample data
            saved_path = save_sample_data(endpoint, data, args.output_dir)
            if saved_path:
                print(f"  • Sample data saved: {saved_path}")
        else:
            print(f"  ✗ Not available or empty")
            results[endpoint] = {"available": False}

    # Save results summary
    results_file = Path("logs/api_field_discovery.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n✓ Results summary saved: {results_file}")
    except Exception as e:
        logger.error(f"Error saving results: {e}")

    # Generate summary report
    print("\n" + "=" * 80)
    print("SUMMARY OF DISCOVERED FIELDS")
    print("=" * 80)

    all_rack_fields = set()
    all_switch_fields = set()
    all_topology_fields = set()

    for endpoint, result in results.items():
        if result.get("available", False) and "categorized" in result:
            cat = result["categorized"]
            all_rack_fields.update(cat["rack_fields"])
            all_switch_fields.update(cat["switch_fields"])
            all_topology_fields.update(cat["topology_fields"])

    if all_rack_fields:
        print(f"\n📦 RACK-RELATED FIELDS FOUND ({len(all_rack_fields)}):")
        for field in sorted(all_rack_fields):
            # Find which endpoints contain this field
            endpoints_with_field = [
                ep for ep, res in results.items()
                if res.get("available", False) and "categorized" in res
                and field in res["categorized"]["rack_fields"]
            ]
            print(f"  • {field}")
            print(f"    Found in: {', '.join(endpoints_with_field)}")

    if all_switch_fields:
        print(f"\n🔌 SWITCH-RELATED FIELDS FOUND ({len(all_switch_fields)}):")
        for field in sorted(all_switch_fields):
            endpoints_with_field = [
                ep for ep, res in results.items()
                if res.get("available", False) and "categorized" in res
                and field in res["categorized"]["switch_fields"]
            ]
            print(f"  • {field}")
            print(f"    Found in: {', '.join(endpoints_with_field)}")

    if all_topology_fields:
        print(f"\n🌐 TOPOLOGY-RELATED FIELDS FOUND ({len(all_topology_fields)}):")
        for field in sorted(all_topology_fields):
            endpoints_with_field = [
                ep for ep, res in results.items()
                if res.get("available", False) and "categorized" in res
                and field in res["categorized"]["topology_fields"]
            ]
            print(f"  • {field}")
            print(f"    Found in: {', '.join(endpoints_with_field)}")

    if not all_rack_fields and not all_switch_fields and not all_topology_fields:
        print("\n⚠️  No rack, switch, or topology fields found in API responses.")
        print("   This may indicate:")
        print("   1. The cluster is a single-rack deployment")
        print("   2. Multi-rack fields are not exposed via API")
        print("   3. Fields use different naming conventions")

    print("\n" + "=" * 80)
    print("Discovery complete!")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
