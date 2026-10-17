#!/usr/bin/env python3
"""Diagnostic: probe VAST API endpoints for field discovery (DIAG-1).

Dumps keys from endpoints needed by the field-feedback backlog
(HCF-4 license fields, INV-2 MACs, DRV-1 drive firmware) and by
Ross Cooper-Smith follow-ups (drive capacity, RLR/failure domains,
metadata triplication, 1-strip / resiliency flags on clusters and boxes).

Usage:
    python3 scripts/diag_api_fields.py <cluster_ip> <username> <password>

Credentials are CLI-only (never written to output files beyond redaction).
Sample values for sensitive-looking keys are redacted in the JSON dump.
"""

from __future__ import annotations

import json
import os
import re
import sys
import warnings
from typing import Any, Dict, List, Set, Tuple

warnings.filterwarnings("ignore", message="Unverified HTTPS request")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from api_handler import VastApiHandler  # noqa: E402

# Endpoints required by DIAG-1 / field-feedback triage + Ross Cooper-Smith follow-ups.
ENDPOINTS: List[str] = [
    "cnodes/",
    "dnodes/",
    "dboxes/",
    "eboxes/",
    "ssds/",
    "nvrams/",
    "licenses/",
    "clusters/",
]

# Keyword highlights for INV-2 / DRV-1 / HCF-4 / HCF-1 / RCS resiliency + drive size.
HIGHLIGHT_RE = re.compile(
    r"(mac|serial|firmware|fw_version|part_number|vendor|model|"
    r"license|expir|trial|eval|upgrade_state|upgrade|"
    r"capacity|size_tb|size_bytes|size_gb|drive_size|raw_capacity|"
    r"failure_domain|rlr|resilienc|triplicat|strip|erasure|raid|"
    r"wb_raid|schema|dbox_ha|ebox)",
    re.IGNORECASE,
)

SENSITIVE_KEY_RE = re.compile(
    r"(password|token|secret|credential|authorization|api_key)",
    re.IGNORECASE,
)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")


def extract_keys(obj: Any, prefix: str = "", depth: int = 0, max_depth: int = 4) -> Set[str]:
    """Recursively collect dotted keys from nested dict/list structures."""
    keys: Set[str] = set()
    if depth > max_depth:
        return keys
    if isinstance(obj, dict):
        for key, value in obj.items():
            full = f"{prefix}.{key}" if prefix else str(key)
            keys.add(full)
            if isinstance(value, (dict, list)):
                keys.update(extract_keys(value, full, depth + 1, max_depth))
    elif isinstance(obj, list) and obj:
        keys.update(extract_keys(obj[0], prefix, depth + 1, max_depth))
    return keys


def first_item(data: Any) -> Any:
    """Return a representative sample object from an API response."""
    if data is None:
        return None
    if isinstance(data, list):
        return data[0] if data else None
    if isinstance(data, dict):
        if "results" in data and isinstance(data["results"], list):
            results = data["results"]
            return results[0] if results else data
        return data
    return data


def redact_sample(obj: Any, depth: int = 0, max_depth: int = 3) -> Any:
    """Shallow-copy sample data with credential-like values redacted."""
    if depth > max_depth:
        return "<truncated>"
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if SENSITIVE_KEY_RE.search(str(k)):
                out[k] = "<redacted>"
            elif isinstance(v, (dict, list)):
                out[k] = redact_sample(v, depth + 1, max_depth)
            else:
                out[k] = v
        return out
    if isinstance(obj, list):
        return [redact_sample(obj[0], depth + 1, max_depth)] if obj else []
    return obj


def classify_keys(keys: Set[str]) -> Tuple[List[str], List[str]]:
    """Split keys into highlight candidates and the rest."""
    highlighted = sorted(k for k in keys if HIGHLIGHT_RE.search(k))
    other = sorted(k for k in keys if k not in highlighted)
    return highlighted, other


def probe_endpoint(handler: VastApiHandler, endpoint: str) -> Dict[str, Any]:
    """GET one endpoint and summarize field availability."""
    raw = handler._make_api_request(endpoint)
    if raw is None:
        return {
            "endpoint": endpoint,
            "available": False,
            "item_count": 0,
            "keys": [],
            "highlighted_keys": [],
            "sample": None,
        }

    if isinstance(raw, list):
        item_count = len(raw)
    elif isinstance(raw, dict) and isinstance(raw.get("results"), list):
        item_count = len(raw["results"])
    else:
        item_count = 1

    sample = first_item(raw)
    keys = extract_keys(sample) if sample is not None else set()
    highlighted, _other = classify_keys(keys)

    return {
        "endpoint": endpoint,
        "available": True,
        "item_count": item_count,
        "keys": sorted(keys),
        "highlighted_keys": highlighted,
        "sample": redact_sample(sample) if sample is not None else None,
    }


def print_report(result: Dict[str, Any]) -> None:
    """Print a human-readable per-endpoint summary."""
    ep = result["endpoint"]
    print(f"\n{'=' * 70}")
    print(f"  ENDPOINT: /api/.../{ep}")
    if not result["available"]:
        print("  Available: NO (404 / error / empty)")
        print(f"{'=' * 70}")
        return

    print(f"  Available: YES  |  items={result['item_count']}  |  keys={len(result['keys'])}")
    print(f"{'=' * 70}")

    highlighted = result["highlighted_keys"]
    if highlighted:
        print(f"\n  --- Highlighted (MAC / serial / firmware / license / upgrade) ({len(highlighted)}) ---")
        for key in highlighted:
            print(f"  ** {key}")

    print(f"\n  All keys ({len(result['keys'])}):")
    for key in result["keys"]:
        marker = " **" if key in highlighted else ""
        print(f"    {key}{marker}")


def main() -> int:
    if len(sys.argv) < 4:
        print("Usage: python3 scripts/diag_api_fields.py <cluster_ip> <username> <password>")
        print("\nProbes: " + ", ".join(ENDPOINTS))
        return 1

    cluster_ip, username, password = sys.argv[1], sys.argv[2], sys.argv[3]
    config = {"api": {"timeout": 30, "max_retries": 2, "retry_delay": 2, "verify_ssl": False}}

    handler = VastApiHandler(cluster_ip=cluster_ip, username=username, password=password, config=config)
    print(f"Authenticating with {cluster_ip}...")
    if not handler.authenticate():
        print("ERROR: Authentication failed.")
        return 1
    print("Authenticated.\n")

    os.makedirs(REPORTS_DIR, exist_ok=True)

    results: List[Dict[str, Any]] = []
    for endpoint in ENDPOINTS:
        result = probe_endpoint(handler, endpoint)
        results.append(result)
        print_report(result)

    summary_path = os.path.join(REPORTS_DIR, "diag_api_fields_summary.json")
    with open(summary_path, "w") as fh:
        json.dump(
            {
                "cluster_ip": cluster_ip,
                "cluster_version": getattr(handler, "cluster_version", None),
                "endpoints": results,
            },
            fh,
            indent=2,
            default=str,
        )

    available = [r for r in results if r["available"]]
    missing = [r["endpoint"] for r in results if not r["available"]]

    print(f"\n{'=' * 70}")
    print("  DISCOVERY SUMMARY")
    print(f"{'=' * 70}")
    print(f"\n  Available ({len(available)}):")
    for r in available:
        print(
            f"    {r['endpoint']:12s}  items={r['item_count']:>4}  "
            f"keys={len(r['keys']):>3}  highlighted={len(r['highlighted_keys']):>2}"
        )
    if missing:
        print(f"\n  Unavailable ({len(missing)}):")
        for ep in missing:
            print(f"    {ep}")

    all_highlighted: Set[str] = set()
    for r in available:
        for key in r["highlighted_keys"]:
            all_highlighted.add(f"{r['endpoint']}::{key}")
    if all_highlighted:
        print(f"\n  Cross-endpoint highlighted fields ({len(all_highlighted)}):")
        for item in sorted(all_highlighted):
            print(f"    {item}")

    print(f"\n  Summary written to: {os.path.abspath(summary_path)}")
    print("  (reports/ is gitignored — do not commit lab dumps)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
