"""Test Suite page must not start execution when pre-validation returns no results.

Field run (EBox, v1.6.2): pre-validation took ~2.5 min on Switch SSH probes, the
page stopped polling after 120 s, treated the missing result as a pass and
POSTed /advanced-ops/oneshot/start while validation still held the one-shot
lock, which the server rejected with "One-shot execution already running".
"""

import re
from pathlib import Path

REPORTER = Path(__file__).parent.parent / "frontend" / "templates" / "reporter.html"


def _function_body(source: str, name: str) -> str:
    start = source.index(f"async function {name}(")
    nxt = re.compile(r"\n(?:async )?function ").search(source, start + 1)
    return source[start : nxt.start() if nxt else len(source)]


def test_missing_validation_result_stops_before_execution():
    body = _function_body(REPORTER.read_text(), "startOneShot")
    guard = body.index("if (!result || !result.validation)")
    guard_block = body[guard : body.index("}", guard)]
    assert "return;" in guard_block
    assert guard < body.index("_continueOneShotExecution")


def test_validation_poll_waits_longer_than_slow_switch_probes():
    source = REPORTER.read_text()
    match = re.search(r"ONESHOT_VALIDATION_MAX_WAIT_S\s*=\s*(\d+)", source)
    assert match and int(match.group(1)) >= 600
    assert "i < ONESHOT_VALIDATION_MAX_WAIT_S" in _function_body(source, "pollOneShotValidationResult")
