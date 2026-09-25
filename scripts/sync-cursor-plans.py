#!/usr/bin/env python3
"""Copy this project's Cursor plans into docs/plans/, redacted for a public repo.

Cursor keeps plan files in a shared, machine-local directory (~/.cursor/plans/)
that mixes every project. docs/plans/MANIFEST.txt is the allow-list of plans
that belong to this repo; each listed plan is copied here with lab addresses,
credential values, email addresses and known lab/customer names redacted.

Usage:
  python3 scripts/sync-cursor-plans.py            # copy/refresh listed plans
  python3 scripts/sync-cursor-plans.py --check    # report drift, exit 1 if any

--check reports (a) plans in the source directory modified after the
manifest's "last-triaged" date that are not listed, and (b) archived copies
that differ from their redacted source. It never writes.

Stdlib only; exit code 0 = in sync, 1 = drift or missing sources.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = Path.home() / ".cursor" / "plans"
DEST_DIR = REPO_ROOT / "docs" / "plans"
MANIFEST = DEST_DIR / "MANIFEST.txt"

# Addresses that are safe to publish: loopback/any, and the fixed CBox Tech
# Port address that the product documentation already names.
IP_ALLOW = {"127.0.0.1", "0.0.0.0", "192.168.2.2"}

IPV4_RE = re.compile(r"(?<![\w.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?!\.?\d)")
CRED_RE = re.compile(
    r"(?i)\b(\w*?(?:password|passwd|pwd|token|secret|api[_-]?key))\b(\s*[:=]\s*)([\"'`]?)"
    r"(?!<redacted>)([^\s\"'`,;)<>]+)"
)
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# Lab hostnames and customer/site identifiers. Extend when a sync report or
# review turns up a new one; order matters only where patterns overlap.
REDACT_PATTERNS: List[Tuple[str, str]] = [
    (r"(?i)\bselab-[a-z0-9-]+\b", "<lab-cluster>"),
    (r"(?i)\b[a-z0-9-]+\.selab\.vastdata\.com\b", "<lab-host>"),
    (r"(?i)\bstamps-win-\d+\b", "<lab-host>"),
    (r"\bvast_data_[A-Za-z0-9-]+_(\d{8})", r"vast_data_<cluster>_\1"),
    (r"(?<![A-Za-z0-9])[A-Za-z0-9]+-VAST-[A-Za-z0-9-]*[A-Za-z0-9]", "<customer-cluster>"),
    (r"\bLAX-01\b", "<customer-site>"),
    (r"(?<![A-Za-z0-9])(?:Lambda|LAMBDA)(?![a-z])", "<customer>"),
    (r"(?i)\bmammoth\b", "<customer-cluster>"),
    (r"(?i)\bm-pr-xpvast-[a-z0-9]+\b", "<customer-cluster>"),
    (r"(?<![\w])Vastdata1!", "<default-password>"),
    (r"\b123456\b", "<default-password>"),
]

# Unquoted credential "values" that are really code (type hints, variables,
# lookups) and carry no secret; quoted values are always redacted.
_CODE_VALUE_RE = re.compile(r"^(?:str|int|bool|None|True|False|Optional\[?.*|[A-Za-z_]\w*[.(\[].*|[a-z]+_[a-z_]+)$")

LAST_TRIAGED_RE = re.compile(r"^#\s*last-triaged:\s*(\d{4}-\d{2}-\d{2})\s*$")


def redact(text: str) -> Tuple[str, int]:
    """Return (redacted_text, number_of_replacements). Idempotent."""
    count = 0

    def _ip(match: "re.Match[str]") -> str:
        nonlocal count
        ip = match.group(0)
        # A network address with a prefix (10.0.0.0/8) names a range, not a host.
        is_range = ip.endswith(".0") and match.string[match.end() : match.end() + 1] == "/"
        if ip in IP_ALLOW or is_range:
            return ip
        count += 1
        return "<ip>"

    def _cred(match: "re.Match[str]") -> str:
        nonlocal count
        key, quote, value = match.group(1), match.group(3), match.group(4)
        if not quote and (_CODE_VALUE_RE.match(value) or value.lower() == key.lower()):
            return match.group(0)
        count += 1
        return f"{match.group(1)}{match.group(2)}{match.group(3)}<redacted>"

    text = IPV4_RE.sub(_ip, text)
    text = CRED_RE.sub(_cred, text)
    text, n = EMAIL_RE.subn("<email>", text)
    count += n
    for pattern, replacement in REDACT_PATTERNS:
        text, n = re.subn(pattern, replacement, text)
        count += n
    return text, count


def read_manifest(path: Path) -> Tuple[List[str], Optional[date]]:
    """Return (plan filenames, last-triaged date) from MANIFEST.txt."""
    entries: List[str] = []
    last_triaged: Optional[date] = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = LAST_TRIAGED_RE.match(line)
        if m:
            last_triaged = date.fromisoformat(m.group(1))
            continue
        if line.startswith("#"):
            continue
        entries.append(line)
    return entries, last_triaged


def untriaged_plans(source: Path, listed: List[str], last_triaged: Optional[date]) -> List[str]:
    """Plans in the source dir modified after last_triaged and not listed."""
    if last_triaged is None:
        return []
    listed_set = set(listed)
    found = []
    for plan in sorted(source.glob("*.plan.md")):
        modified = datetime.fromtimestamp(plan.stat().st_mtime).date()
        if modified > last_triaged and plan.name not in listed_set:
            found.append(plan.name)
    return found


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Cursor plans directory")
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args(argv)

    if not MANIFEST.is_file():
        print(f"error: manifest not found: {MANIFEST}", file=sys.stderr)
        return 1
    entries, last_triaged = read_manifest(MANIFEST)
    problems = 0

    for name in entries:
        src = args.source / name
        dest = DEST_DIR / name
        if not src.is_file():
            # Source plans can be deleted locally; the archived copy is then the record.
            if not dest.is_file():
                print(f"missing   {name} (no source, no archived copy)")
                problems += 1
            continue
        redacted, hits = redact(src.read_text(encoding="utf-8"))
        current = dest.read_text(encoding="utf-8") if dest.is_file() else None
        if current == redacted:
            continue
        if args.check:
            print(f"drift     {name}")
            problems += 1
        else:
            dest.write_text(redacted, encoding="utf-8")
            print(f"synced    {name} ({hits} redactions)")

    for name in untriaged_plans(args.source, entries, last_triaged):
        print(f"untriaged {name} (newer than last-triaged {last_triaged}; add to MANIFEST.txt or skip)")
        if args.check:
            problems += 1

    if args.check:
        print("plan archive in sync." if problems == 0 else f"{problems} plan archive issue(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
