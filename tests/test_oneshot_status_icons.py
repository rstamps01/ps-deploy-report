"""Health check status icons in the Test Suite output (HCF-8, EBox field report).

Skipped checks printed as ``[????] CBox Status (10/28)`` because the icon map
had no ``skipped`` entry, and the skip reason was never shown.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from health_checker import HealthCheckResult  # noqa: E402
from oneshot_runner import OneShotRunner  # noqa: E402


def _runner_with_capture():
    runner = OneShotRunner(selected_ops=[], credentials={"cluster_ip": "10.0.0.1"})
    callback = MagicMock()
    runner._output_callback = callback
    return runner, callback


def _lines(callback):
    return [(c.args[0], c.args[1]) for c in callback.call_args_list]


def test_skipped_check_shows_skip_icon_and_reason():
    runner, callback = _runner_with_capture()
    results = [
        HealthCheckResult("CBox Status", "api", "skipped", "No CBoxes found (EBox cluster: CNodes run inside EBoxes)"),
        HealthCheckResult("Cluster RAID Health", "api", "pass", "ok"),
    ]
    runner._emit_health_results(results)
    lines = _lines(callback)
    assert ("info", "  [SKIP] CBox Status (1/2)") in lines
    assert ("info", "        No CBoxes found (EBox cluster: CNodes run inside EBoxes)") in lines
    assert ("success", "  [PASS] Cluster RAID Health (2/2)") in lines
    assert not any("[????]" in msg for _, msg in lines)


def test_every_health_status_has_an_icon():
    runner, callback = _runner_with_capture()
    statuses = ["pass", "fail", "warning", "skipped", "error"]
    runner._emit_health_results([HealthCheckResult(f"c-{s}", "api", s, "m") for s in statuses])
    assert not any("[????]" in msg for _, msg in _lines(callback))


def test_unknown_status_is_named_not_question_marks():
    runner, callback = _runner_with_capture()
    runner._emit_health_results([HealthCheckResult("Odd", "api", "degraded", "")])
    assert ("info", "  [DEGRADED] Odd (1/1)") in _lines(callback)
