"""Active Alarms status policy helpers (HCF-3)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.alarm_policy import (  # noqa: E402
    alarm_check_status,
    alarm_fail_on_from_config,
    alarm_status_from_details,
    count_unresolved_alarms,
    normalize_alarm_fail_on,
)


@pytest.mark.parametrize(
    "critical, major, fail_on, expected",
    [
        (0, 0, "critical", "pass"),
        (1, 0, "critical", "fail"),
        (0, 1, "critical", "warning"),
        (1, 1, "critical", "fail"),
        (0, 1, "major", "fail"),
        (1, 0, "major", "fail"),
        (0, 0, "major", "pass"),
        (1, 1, "none", "warning"),
        (0, 0, "none", "pass"),
    ],
)
def test_alarm_check_status(critical, major, fail_on, expected):
    assert alarm_check_status(critical, major, fail_on) == expected


@pytest.mark.parametrize(
    "config, expected",
    [
        (None, "critical"),
        ({}, "critical"),
        ({"health_check": None}, "critical"),
        ({"health_check": {"alarms": None}}, "critical"),
        ({"health_check": {"alarms": {"fail_on": "MAJOR"}}}, "major"),
        ({"health_check": {"alarms": {"fail_on": " none "}}}, "none"),
    ],
)
def test_alarm_fail_on_from_config(config, expected):
    assert alarm_fail_on_from_config(config) == expected


def test_invalid_value_warns_and_falls_back(caplog):
    with caplog.at_level("WARNING", logger="utils.alarm_policy"):
        assert normalize_alarm_fail_on(False) == "critical"
    assert "health_check.alarms.fail_on" in caplog.text


def test_count_ignores_resolved_and_other_severities():
    alarms = [
        {"severity": "critical"},
        {"severity": "CRITICAL", "resolved": True},
        {"severity": "MAJOR"},
        {"severity": "MINOR"},
        "not-a-dict",
    ]
    assert count_unresolved_alarms(alarms) == (1, 1)


def test_status_from_details_without_severities_is_none():
    assert alarm_status_from_details(None, "critical") is None
    assert alarm_status_from_details({"alarms": []}, "critical") is None
    assert alarm_status_from_details({"alarms": [{"description": "x"}]}, "critical") is None


def test_status_from_details_prefers_split_counts():
    details = {"critical_unresolved": 0, "major_unresolved": 0, "alarms": [{"severity": "CRITICAL"}]}
    assert alarm_status_from_details(details, "critical") == "pass"
