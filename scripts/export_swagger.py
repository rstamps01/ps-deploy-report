#!/usr/bin/env python3
"""
VAST API Swagger/OpenAPI Exporter

Connects to a VAST cluster and exports the Swagger/OpenAPI specification
to a local JSON file for offline reference and development.

Usage:
    python3 scripts/export_swagger.py --cluster <ip> --username <user> --password <pass>
    python3 scripts/export_swagger.py --cluster <ip> --token <api_token>
    python3 scripts/export_swagger.py --cluster <ip> --username <user> --output docs/api/

Output:
    docs/api/swagger_<cluster_name>_<version>_<date>.json
"""

import argparse
import getpass
import json
import sys
from datetime import datetime
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SWAGGER_PATHS = [
    "/api/swagger.json",
    "/api/?format=openapi",
    "/api/v7/swagger.json",
    "/api/v7/?format=openapi",
    "/docs/swagger.json",
    "/api/schema/",
]

API_VERSIONS = ["v7", "v6", "v5", "v4", "v3", "v2", "v1"]


def detect_api_version(cluster_ip: str, session: requests.Session) -> str:
    """Probe for the highest supported API version."""
    for version in API_VERSIONS:
        url = f"https://{cluster_ip}/api/{version}/vms/"
        try:
            resp = session.get(url, timeout=10, verify=False)
            if resp.status_code == 200:
                print(f"  Detected API version: {version}")
                return version
        except requests.RequestException:
            continue
    print("  WARNING: Could not detect version, defaulting to v7")
    return "v7"


def get_cluster_name(cluster_ip: str, session: requests.Session, version: str) -> str:
    """Retrieve cluster name for output filename."""
    for endpoint in [f"/api/{version}/clusters/", f"/api/{version}/vms/"]:
        url = f"https://{cluster_ip}{endpoint}"
        try:
            resp = session.get(url, timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    return data[0].get("name", "unknown").replace(" ", "_")
                elif isinstance(data, dict):
                    return data.get("name", "unknown").replace(" ", "_")
        except (requests.RequestException, ValueError):
            continue
    return "unknown"


def fetch_swagger(cluster_ip: str, session: requests.Session) -> dict:
    """Try multiple paths to find the Swagger/OpenAPI spec."""
    for path in SWAGGER_PATHS:
        url = f"https://{cluster_ip}{path}"
        try:
            resp = session.get(url, timeout=15, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                if "paths" in data or "swagger" in data or "openapi" in data:
                    print(f"  Found Swagger spec at: {path}")
                    return data
        except (requests.RequestException, ValueError):
            continue
    return {}


def build_endpoint_catalog(cluster_ip: str, session: requests.Session, version: str) -> dict:
    """Build an endpoint catalog by probing known endpoints when Swagger is unavailable."""
    endpoints = [
        "clusters", "vms", "cnodes", "dnodes", "cboxes", "dboxes", "eboxes", "dtrays",
        "dns", "ntps", "vippools", "tenants", "views", "viewpolicies",
        "activedirectory", "ldap", "nis", "snapprograms", "protectionpolicies",
        "snmp", "syslog", "alerts", "racks", "apitokens",
        "alarms", "events", "eventdefinitions", "monitors", "snapshots", "quotas",
    ]

    v1_endpoints = ["switches", "ports"]

    catalog = {
        "info": {
            "title": "VAST API Endpoint Catalog",
            "description": "Auto-discovered endpoints from cluster probe",
            "cluster_ip": cluster_ip,
            "api_version": version,
            "generated": datetime.now().isoformat(),
        },
        "endpoints": {},
    }

    print(f"  Probing {len(endpoints)} v{version} endpoints...")
    for ep in endpoints:
        url = f"https://{cluster_ip}/api/{version}/{ep}/"
        try:
            resp = session.get(url, timeout=10, verify=False)
            status = resp.status_code
            fields = []
            if status == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    fields = sorted(data[0].keys()) if isinstance(data[0], dict) else []
                elif isinstance(data, dict):
                    fields = sorted(data.keys())

            catalog["endpoints"][f"/api/{version}/{ep}/"] = {
                "method": "GET",
                "status": status,
                "available": status == 200,
                "fields": fields,
                "field_count": len(fields),
            }
        except requests.RequestException as e:
            catalog["endpoints"][f"/api/{version}/{ep}/"] = {
                "method": "GET",
                "status": 0,
                "available": False,
                "error": str(e),
            }

    print(f"  Probing {len(v1_endpoints)} v1 endpoints...")
    for ep in v1_endpoints:
        url = f"https://{cluster_ip}/api/v1/{ep}/"
        try:
            resp = session.get(url, timeout=10, verify=False)
            status = resp.status_code
            fields = []
            if status == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    fields = sorted(data[0].keys()) if isinstance(data[0], dict) else []

            catalog["endpoints"][f"/api/v1/{ep}/"] = {
                "method": "GET",
                "status": status,
                "available": status == 200,
                "fields": fields,
                "field_count": len(fields),
            }
        except requests.RequestException as e:
            catalog["endpoints"][f"/api/v1/{ep}/"] = {
                "method": "GET",
                "status": 0,
                "available": False,
                "error": str(e),
            }

    available = sum(1 for e in catalog["endpoints"].values() if e.get("available"))
    print(f"  Discovered {available}/{len(catalog['endpoints'])} available endpoints")

    return catalog


def main():
    parser = argparse.ArgumentParser(
        description="Export VAST API Swagger/OpenAPI specification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python3 scripts/export_swagger.py --cluster 10.0.0.100 --username admin\n"
               "  python3 scripts/export_swagger.py --cluster 10.0.0.100 --token <token> --output docs/api/\n",
    )
    parser.add_argument("--cluster", required=True, help="Cluster management VIP or hostname")
    parser.add_argument("--username", help="Admin username (will prompt for password)")
    parser.add_argument("--password", help="Admin password (or use interactive prompt)")
    parser.add_argument("--token", help="API token (alternative to username/password)")
    parser.add_argument("--output", default="docs/api", help="Output directory (default: docs/api)")
    args = parser.parse_args()

    if not args.token and not args.username:
        parser.error("Provide either --token or --username for authentication")

    session = requests.Session()

    if args.token:
        session.headers["Authorization"] = f"Api-Token {args.token}"
    else:
        password = args.password or getpass.getpass(f"Password for {args.username}: ")
        session.auth = (args.username, password)

    print(f"\nConnecting to cluster: {args.cluster}")

    version = detect_api_version(args.cluster, session)
    cluster_name = get_cluster_name(args.cluster, session, version)
    print(f"  Cluster name: {cluster_name}")

    print("\nAttempting Swagger/OpenAPI export...")
    swagger_data = fetch_swagger(args.cluster, session)

    if not swagger_data:
        print("  Swagger spec not found, building endpoint catalog by probing...")
        swagger_data = build_endpoint_catalog(args.cluster, session, version)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    date_stamp = datetime.now().strftime("%Y%m%d")
    filename = f"swagger_{cluster_name}_{version}_{date_stamp}.json"
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(swagger_data, f, indent=2, default=str)

    print(f"\nExported to: {output_path}")
    print(f"File size: {output_path.stat().st_size:,} bytes")

    if "endpoints" in swagger_data:
        available = sum(1 for e in swagger_data["endpoints"].values() if e.get("available"))
        total = len(swagger_data["endpoints"])
        print(f"Endpoints: {available}/{total} available")
    elif "paths" in swagger_data:
        print(f"Paths documented: {len(swagger_data['paths'])}")

    print("\nDone.")


if __name__ == "__main__":
    main()
