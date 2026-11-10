#!/usr/bin/env python3
"""Print a short Markdown summary of a pytest JUnit XML report.

Used by CI to write failures into ``$GITHUB_STEP_SUMMARY`` so the
``ci-investigator`` subagent (and people) read a few lines instead of the raw
job log. Stdlib only.

Usage:
    python scripts/junit_summary.py test-results/junit.xml [--max N] [--lines N]
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple


def summarize(xml_path: Path, max_failures: int = 25, max_lines: int = 12) -> str:
    """Return a Markdown summary of the JUnit report at ``xml_path``.

    Args:
        xml_path: Path to a JUnit XML file written by ``pytest --junitxml``.
        max_failures: Maximum number of failing tests to list.
        max_lines: Maximum message/traceback lines shown per failure.

    Returns:
        str: Markdown text; a one-line note if the file is missing or unreadable.
    """
    if not xml_path.is_file():
        return f"No JUnit report at `{xml_path}` (tests may not have run).\n"
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        return f"Could not parse `{xml_path}`: {exc}\n"

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    totals = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for suite in suites:
        for key in totals:
            totals[key] += int(suite.get(key, 0) or 0)

    failed: List[Tuple[str, str]] = []
    for case in root.iter("testcase"):
        for tag in ("failure", "error"):
            node = case.find(tag)
            if node is None:
                continue
            test_id = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
            text = (node.get("message") or "") + "\n" + (node.text or "")
            lines = [ln for ln in text.strip().splitlines() if ln.strip()]
            failed.append((f"{tag.upper()} {test_id}", "\n".join(lines[-max_lines:])))

    passed = totals["tests"] - totals["failures"] - totals["errors"] - totals["skipped"]
    out = [
        f"### Tests: {passed} passed, {totals['failures']} failed, "
        f"{totals['errors']} errors, {totals['skipped']} skipped\n"
    ]
    if not failed:
        return "".join(out)
    for title, body in failed[:max_failures]:
        out.append(f"\n**{title}**\n\n```text\n{body}\n```\n")
    if len(failed) > max_failures:
        out.append(f"\n... and {len(failed) - max_failures} more failures (see the junit artifact).\n")
    return "".join(out)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("xml", type=Path)
    parser.add_argument("--max", type=int, default=25, dest="max_failures")
    parser.add_argument("--lines", type=int, default=12, dest="max_lines")
    args = parser.parse_args(argv)
    sys.stdout.write(summarize(args.xml, args.max_failures, args.max_lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
