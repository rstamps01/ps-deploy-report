"""Active Alarms status policy (HCF-3).

Pure helpers that turn unresolved alarm counts and the
``health_check.alarms.fail_on`` setting into a check status. Shared by the
live check (``HealthChecker._check_active_alarms``) and the render-time fixup
(``VastReportBuilder._fixup_health_results``) so a fresh run and a re-rendered
JSON export reach the same status.

``fail_on`` values:

- ``critical`` (default): unresolved CRITICAL alarms fail, MAJOR alarms warn.
- ``major``: unresolved CRITICAL and MAJOR alarms both fail.
- ``none``: unresolved CRITICAL and MAJOR alarms both warn.
"""

import logging
from typing import Any, Iterable, Mapping, Optional, Tuple

ALARM_FAIL_ON_CHOICES = ("critical", "major", "none")
DEFAULT_ALARM_FAIL_ON = "critical"

_LOGGER = logging.getLogger(__name__)


def normalize_alarm_fail_on(value: Any, logger: Optional[logging.Logger] = None) -> str:
    """Return a valid ``fail_on`` value, falling back to the default.

    Args:
        value: Raw setting (``None`` when the key is absent).
        logger: Logger for the invalid-value warning; defaults to this module's logger.

    Returns:
        One of :data:`ALARM_FAIL_ON_CHOICES`. Invalid values log a warning and
        return :data:`DEFAULT_ALARM_FAIL_ON`.
    """
    if value is None:
        return DEFAULT_ALARM_FAIL_ON
    text = str(value).strip().lower()
    if text in ALARM_FAIL_ON_CHOICES:
        return text
    (logger or _LOGGER).warning(
        "Invalid health_check.alarms.fail_on %r (expected one of %s); using %r",
        value,
        ", ".join(ALARM_FAIL_ON_CHOICES),
        DEFAULT_ALARM_FAIL_ON,
    )
    return DEFAULT_ALARM_FAIL_ON


def alarm_fail_on_from_config(config: Optional[Mapping[str, Any]], logger: Optional[logging.Logger] = None) -> str:
    """Read ``health_check.alarms.fail_on`` from a loaded config dict.

    Args:
        config: Parsed ``config.yaml`` (may be ``None`` or missing sections).
        logger: Logger for the invalid-value warning.

    Returns:
        The normalized ``fail_on`` value.
    """
    health_check = (config or {}).get("health_check")
    alarms = health_check.get("alarms") if isinstance(health_check, Mapping) else None
    value = alarms.get("fail_on") if isinstance(alarms, Mapping) else None
    return normalize_alarm_fail_on(value, logger)


def count_unresolved_alarms(alarms: Iterable[Any]) -> Tuple[int, int]:
    """Count unresolved CRITICAL and MAJOR alarms.

    Args:
        alarms: Alarm dicts from ``/api/alarms/`` or saved ``details.alarms``
            summaries. Entries marked ``resolved`` are ignored.

    Returns:
        ``(critical, major)`` counts.
    """
    critical = major = 0
    for alarm in alarms:
        if not isinstance(alarm, Mapping) or alarm.get("resolved"):
            continue
        severity = str(alarm.get("severity", "")).upper()
        if severity == "CRITICAL":
            critical += 1
        elif severity == "MAJOR":
            major += 1
    return critical, major


def alarm_check_status(critical: int, major: int, fail_on: str) -> str:
    """Return the Active Alarms status for the given counts and policy.

    Args:
        critical: Unresolved CRITICAL alarm count.
        major: Unresolved MAJOR alarm count.
        fail_on: Normalized ``fail_on`` value.

    Returns:
        ``"pass"``, ``"warning"`` or ``"fail"``.
    """
    if not critical and not major:
        return "pass"
    if fail_on == "major" or (fail_on == "critical" and critical):
        return "fail"
    return "warning"


def alarm_status_from_details(details: Any, fail_on: str) -> Optional[str]:
    """Recompute the Active Alarms status from saved result ``details``.

    Uses the ``critical_unresolved`` / ``major_unresolved`` counts when both
    are saved (HCF-3 and later); otherwise counts the per-alarm severities in
    ``details.alarms`` (older exports, whose ``critical_unresolved`` combined
    both severities).

    Args:
        details: The saved result's ``details`` value.
        fail_on: Normalized ``fail_on`` value.

    Returns:
        The policy status, or ``None`` when the details carry no per-alarm
        severities (the saved status should be kept).
    """
    if not isinstance(details, Mapping):
        return None
    if "major_unresolved" in details:
        try:
            critical = int(details.get("critical_unresolved") or 0)
            major = int(details.get("major_unresolved") or 0)
        except (TypeError, ValueError):
            pass
        else:
            return alarm_check_status(critical, major, fail_on)
    alarms = details.get("alarms")
    if not isinstance(alarms, list) or not any(isinstance(a, Mapping) and a.get("severity") for a in alarms):
        return None
    critical, major = count_unresolved_alarms(alarms)
    return alarm_check_status(critical, major, fail_on)
