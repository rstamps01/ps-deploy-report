"""Consolidate health check ``details`` into grouped report tables (RPT-LAYOUT-1).

Pure data shaping (no ReportLab): ``build_health_detail_groups`` turns the
``HealthCheckResult`` dicts of a health check run into a short list of
functional groups, each with a heading, a caption describing its rows, and one
or more tables of display-ready strings. Fields no group consumes are collected
in a final "Other Check Details" group so nothing is silently dropped.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Set

NOT_REPORTED = "Not reported"
NOT_APPLICABLE = "—"
_TITLE_PREFIX = "Health Check Details — "

# Checks no longer run; ignored when they appear in results saved by older versions.
RETIRED_CHECKS = frozenset({"Upgrade State"})
# Checks that still run (and appear in Detailed Check Results) but get no details group.
DETAILS_NOT_SHOWN = frozenset({"Performance Baseline"})


@dataclass
class DetailTable:
    """One rendered table: headers, string rows and relative column weights."""

    headers: List[str]
    rows: List[List[str]]
    col_weights: List[float]
    title: str = ""


@dataclass
class DetailGroup:
    """A consolidated group of health check details."""

    key: str
    title: str
    caption: str
    tables: List[DetailTable] = field(default_factory=list)


def humanize_key(key: str) -> str:
    """Turn a snake_case details key into a Title Case label."""
    return " ".join(part.capitalize() for part in str(key).split("_") if part)


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _fmt(value: Any) -> str:
    if value is None:
        return NOT_REPORTED
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, float) and value.is_integer():
        return f"{int(value):,}"
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, dict):
        return "; ".join(f"{humanize_key(k)}: {_fmt(v)}" for k, v in value.items())
    if isinstance(value, (list, tuple)):
        return ", ".join(_fmt(v) for v in value)
    return str(value)


def _fmt_pct(value: Any) -> str:
    try:
        return f"{float(value):.1f}%"
    except (TypeError, ValueError):
        return _fmt(value)


def _fmt_whole_pct(value: Any) -> str:
    try:
        return f"{float(value):g}%"
    except (TypeError, ValueError):
        return _fmt(value)


def _fmt_count_list(items: Any) -> str:
    if not items:
        return "None"
    if not isinstance(items, (list, tuple)):
        return _fmt(items)
    return f"{len(items)} — {_fmt(list(items))}"


def _fmt_timestamp(value: Any) -> str:
    if not value:
        return NOT_REPORTED
    text = str(value).replace("T", " ")
    return text.split(".")[0].rstrip("Z")


def _name_state(item: Any) -> str:
    if isinstance(item, dict):
        name = item.get("name") or item.get("id") or "unknown"
        state = item.get("state") or item.get("status")
        return f"{name} ({state})" if state else str(name)
    return str(item)


class _Checks:
    """Lookup of results by check name that records which details fields were consumed."""

    def __init__(self, results: Iterable[Dict[str, Any]]):
        self.order: List[str] = []
        self.by_name: Dict[str, Dict[str, Any]] = {}
        for result in results:
            name = result.get("check_name")
            if name and name not in self.by_name and name not in RETIRED_CHECKS | DETAILS_NOT_SHOWN:
                self.by_name[name] = result
                self.order.append(name)
        self.used: Dict[str, Set[str]] = defaultdict(set)

    def has(self, *names: str) -> bool:
        return any(name in self.by_name for name in names)

    def result(self, name: str) -> Dict[str, Any]:
        return self.by_name.get(name) or {}

    def details(self, name: str) -> Dict[str, Any]:
        details = self.result(name).get("details")
        return details if isinstance(details, dict) else {}

    def get(self, name: str, key: str, default: Any = None) -> Any:
        self.used[name].add(key)
        return self.details(name).get(key, default)

    def consume(self, name: str, *keys: str) -> None:
        self.used[name].update(keys)


def _setting_row(checks: _Checks, check: str, key: str, label: str, fmt: Callable[[Any], str] = _fmt) -> List[str]:
    return [label, fmt(checks.get(check, key)), check]


def _cluster_state(checks: _Checks) -> Optional[DetailGroup]:
    names = ("Cluster State", "Leader State", "Expansion State", "License", "Firmware Consistency")
    if not checks.has(*names):
        return None
    rows: List[List[str]] = []
    if checks.has("Cluster State"):
        rows.append(_setting_row(checks, "Cluster State", "state", "Cluster state"))
        rows.append(_setting_row(checks, "Cluster State", "enabled", "Cluster enabled"))
    if checks.has("Leader State"):
        rows.append(_setting_row(checks, "Leader State", "leader_state", "Leader state"))
        rows.append(_setting_row(checks, "Leader State", "leader_cnode", "Leader CNode"))
    if checks.has("Expansion State"):
        rows.append(_setting_row(checks, "Expansion State", "expansion_state", "Expansion state"))
    if checks.has("License"):
        rows.append(_setting_row(checks, "License", "license", "License status"))
    if checks.has("Firmware Consistency"):
        mismatches = checks.get("Firmware Consistency", "mismatches")
        if isinstance(mismatches, dict) and mismatches:
            for component, versions in mismatches.items():
                label = f"Firmware mismatch — {component}"
                if isinstance(versions, dict):
                    for version, nodes in versions.items():
                        rows.append([label, f"{version} on {_fmt(nodes)}", "Firmware Consistency"])
                else:
                    rows.append([label, _fmt(versions), "Firmware Consistency"])
        else:
            message = checks.result("Firmware Consistency").get("message") or NOT_REPORTED
            rows.append(["Firmware versions", message, "Firmware Consistency"])
    return DetailGroup(
        "cluster_state",
        _TITLE_PREFIX + "Cluster State & Software",
        "Cluster-wide state, software and license as reported by VMS. Each row is one setting; "
        "the last column names the health check that reported it.",
        [DetailTable(["Setting", "Reported Value", "From Check"], rows, [0.32, 0.43, 0.25])],
    )


_COMPONENTS = (
    ("CNodes", "CNode Status"),
    ("DNodes", "DNode Status"),
    ("DBoxes", "DBox Status"),
    ("CBoxes", "CBox Status"),
    ("EBoxes", "EBox Status"),
)


def _hardware(checks: _Checks) -> Optional[DetailGroup]:
    if not checks.has(*(check for _, check in _COMPONENTS)):
        return None
    rows: List[List[str]] = []
    for label, check in _COMPONENTS:
        if not checks.has(check):
            continue
        details = checks.details(check)
        total = checks.get(check, "total")
        inactive = checks.get(check, "inactive")
        disabled = checks.get(check, "disabled")
        mgmt = checks.get(check, "mgmt_cnode")
        notes: List[str] = []
        if mgmt:
            notes.append(f"VMS host: {mgmt}")
        if inactive:
            notes.append("Inactive: " + ", ".join(_name_state(i) for i in inactive))
        if disabled:
            notes.append("Disabled: " + ", ".join(_name_state(i) for i in disabled))
        if not details:
            notes.append(checks.result(check).get("message") or NOT_REPORTED)
        rows.append(
            [
                label,
                _fmt(total) if total is not None else NOT_APPLICABLE,
                str(len(inactive)) if isinstance(inactive, list) else NOT_APPLICABLE,
                str(len(disabled)) if isinstance(disabled, list) else NOT_APPLICABLE,
                "; ".join(notes),
            ]
        )
    return DetailGroup(
        "hardware",
        _TITLE_PREFIX + "Hardware Components",
        "One row per hardware component type: how many the cluster reports, how many are inactive or "
        "disabled, and the names of any that need attention.",
        [DetailTable(["Component", "Total", "Inactive", "Disabled", "Notes"], rows, [0.16, 0.11, 0.12, 0.12, 0.49])],
    )


def _rack_placement(checks: _Checks) -> Optional[DetailGroup]:
    check = "Rack/U-Height Configuration"
    if not checks.has(check):
        return None
    rows = [
        ["Racks defined", _fmt(checks.get(check, "rack_count"))],
        ["CBoxes without a rack", _fmt_count_list(checks.get(check, "cboxes_missing_rack"))],
        ["DBoxes / EBoxes without a rack", _fmt_count_list(checks.get(check, "dboxes_missing_rack"))],
    ]
    return DetailGroup(
        "rack_placement",
        _TITLE_PREFIX + "Rack Placement",
        "Whether racks are defined in VMS and which enclosures have no rack or U-height assigned "
        "(needed for accurate rack diagrams).",
        [DetailTable(["Item", "Value"], rows, [0.32, 0.68])],
    )


def _metric_list(items: Any) -> str:
    if not items:
        return ""
    parts = []
    for item in items:
        if isinstance(item, dict):
            labels = item.get("labels")
            label_text = _fmt(labels) if isinstance(labels, dict) and labels else ""
            parts.append(f"{item.get('name', 'metric')} {label_text}".strip())
        else:
            parts.append(str(item))
    return " — " + ", ".join(parts)


def _storage(checks: _Checks) -> Optional[DetailGroup]:
    raid_checks = ("Cluster RAID Health", "RAID Rebuild Progress")
    device_check = "Device Health (Prometheus)"
    if not checks.has(*raid_checks, device_check):
        return None
    tables: List[DetailTable] = []
    if checks.has(*raid_checks):
        rows = []
        for label, prefix in (("SSD", "ssd"), ("NVRAM", "nvram"), ("Memory", "memory")):
            state = checks.get("Cluster RAID Health", f"{prefix}_raid_state") if checks.has(raid_checks[0]) else None
            progress = (
                checks.get("RAID Rebuild Progress", f"{prefix}_raid_rebuild_progress")
                if checks.has(raid_checks[1])
                else None
            )
            rows.append([label, _fmt(state), _fmt_whole_pct(progress) if progress is not None else NOT_REPORTED])
        tables.append(DetailTable(["Layer", "RAID State", "Rebuild Progress (%)"], rows, [0.3, 0.35, 0.35]))
    if checks.has(device_check):
        failed = checks.get(device_check, "failed_devices")
        media = checks.get(device_check, "media_errors")
        rows = [
            ["Metrics scanned", _fmt(checks.get(device_check, "total_metrics"))],
            ["Failed devices", _fmt(checks.get(device_check, "failed_device_count")) + _metric_list(failed)],
            ["Media errors", _fmt(checks.get(device_check, "media_error_count")) + _metric_list(media)],
        ]
        tables.append(DetailTable(["Item", "Value"], rows, [0.32, 0.68], title="Device health (Prometheus metrics)"))
    return DetailGroup(
        "storage",
        _TITLE_PREFIX + "Storage & Device Health",
        "RAID state and rebuild progress for each protection layer, then device health from the cluster's "
        "Prometheus metrics. When the RAID state is HEALTHY no rebuild is running; idle progress is reported "
        "as 0% or 100%.",
        tables,
    )


def _capacity(checks: _Checks) -> Optional[DetailGroup]:
    names = ("Capacity", "Handle Usage", "Quotas", "Snapshots")
    if not checks.has(*names):
        return None
    rows: List[List[str]] = []
    if checks.has("Capacity"):
        rows.append(
            [
                "Physical capacity used",
                _fmt_pct(checks.get("Capacity", "physical_space_in_use_percent")),
                _fmt_whole_pct(checks.get("Capacity", "threshold")),
            ]
        )
    if checks.has("Handle Usage"):
        rows.append(
            [
                "Handle usage",
                _fmt_pct(checks.get("Handle Usage", "used_handles_percent")),
                _fmt_whole_pct(checks.get("Handle Usage", "threshold")),
            ]
        )
    if checks.has("Quotas"):
        rows.append(["Quotas configured", _fmt(checks.get("Quotas", "total_quotas")), NOT_APPLICABLE])
        rows.append(["Users blocked by quota", _fmt(checks.get("Quotas", "blocked_users")), NOT_APPLICABLE])
    if checks.has("Snapshots"):
        rows.append(["Snapshots", _fmt(checks.get("Snapshots", "total_snapshots")), NOT_APPLICABLE])
        rows.append(["Failed snapshots", _fmt(checks.get("Snapshots", "failed_snapshots")), NOT_APPLICABLE])
    return DetailGroup(
        "capacity",
        _TITLE_PREFIX + "Capacity & Usage",
        "Current usage against the warning threshold, plus quota and snapshot counts.",
        [DetailTable(["Metric", "Current", "Threshold"], rows, [0.42, 0.29, 0.29])],
    )


def _switch_list(switches: Any, count: Any) -> str:
    if not switches:
        return "None" if not count else _fmt(count)
    names = []
    for sw in switches:
        if isinstance(sw, dict):
            name = sw.get("name") or sw.get("hostname") or "switch"
            ip = sw.get("ip") or sw.get("mgmt_ip")
            names.append(f"{name} ({ip})" if ip else str(name))
        else:
            names.append(str(sw))
    total = count if isinstance(count, int) else len(names)
    return f"{total} — {', '.join(names)}"


def _network(checks: _Checks) -> Optional[DetailGroup]:
    if not checks.has("Network Settings", "VIP Pools", "Switches in VMS"):
        return None
    rows: List[List[str]] = []
    if checks.has("Network Settings"):
        rows.append(["DNS servers", _fmt(checks.get("Network Settings", "dns")) or "None"])
        rows.append(["NTP servers", _fmt(checks.get("Network Settings", "ntp")) or "None"])
        rows.append(["Default gateway", _fmt(checks.get("Network Settings", "gateway")) or "None"])
    if checks.has("VIP Pools"):
        enabled = checks.get("VIP Pools", "enabled_pools")
        total = checks.get("VIP Pools", "total_pools")
        rows.append(["VIP pools", f"{_fmt(enabled)} of {_fmt(total)} enabled"])
    if checks.has("Switches in VMS"):
        switches = checks.get("Switches in VMS", "switches")
        count = checks.get("Switches in VMS", "switch_count")
        rows.append(["Switches registered in VMS", _switch_list(switches, count)])
    return DetailGroup(
        "network",
        _TITLE_PREFIX + "Network & Connectivity",
        "Name resolution, time and routing settings, client-access VIP pools, and the switches registered in VMS.",
        [DetailTable(["Item", "Value"], rows, [0.32, 0.68])],
    )


def _data_protection(checks: _Checks) -> Optional[DetailGroup]:
    if not checks.has("Replication", "Data Protection", "Call Home Status"):
        return None
    rows: List[List[str]] = []
    if checks.has("Replication"):
        rows.append(["Replication (DR)", "Enabled" if checks.get("Replication", "dr_enabled") else "Not enabled"])
    if checks.has("Data Protection"):
        active = checks.get("Data Protection", "active_policies")
        total = checks.get("Data Protection", "total_policies")
        rows.append(["Protection policies", f"{_fmt(active)} active of {_fmt(total)}"])
    if checks.has("Call Home Status"):
        call_home = "Call Home Status"
        rows.append(["Call Home enabled", _fmt(checks.get(call_home, "call_home_enabled"))])
        rows.append(["Call Home cloud registered", _fmt(checks.get(call_home, "cloud_registered"))])
        rows.append(["Call Home cloud enabled", _fmt(checks.get(call_home, "cloud_enabled"))])
        rows.append(["Call Home log upload", _fmt(checks.get(call_home, "log_enabled"))])
        rows.append(["Call Home bundle upload", _fmt(checks.get(call_home, "bundle_enabled"))])
        rows.append(["Customer name (Call Home)", _fmt(checks.get(call_home, "customer"))])
    return DetailGroup(
        "data_protection",
        _TITLE_PREFIX + "Data Protection & Services",
        "Replication, protection policies and Call Home settings.",
        [DetailTable(["Item", "Value"], rows, [0.42, 0.58])],
    )


def _alarms(checks: _Checks) -> Optional[DetailGroup]:
    if not checks.has("Active Alarms", "Recent Events"):
        return None
    summary: List[List[str]] = []
    tables: List[DetailTable] = []
    alarm_rows: List[List[str]] = []
    event_rows: List[List[str]] = []
    if checks.has("Active Alarms"):
        summary.append(["Total alarms", _fmt(checks.get("Active Alarms", "total_alarms"))])
        summary.append(["Unresolved critical/major alarms", _fmt(checks.get("Active Alarms", "critical_unresolved"))])
        for alarm in checks.get("Active Alarms", "alarms") or []:
            if isinstance(alarm, dict):
                alarm_rows.append(
                    [
                        _fmt(alarm.get("severity")),
                        _fmt(alarm.get("object_name") or alarm.get("object_type")),
                        _fmt(alarm.get("description")),
                        _fmt_timestamp(alarm.get("timestamp")),
                    ]
                )
    if checks.has("Recent Events"):
        summary.append(["Recent events checked", _fmt(checks.get("Recent Events", "total_events_returned"))])
        summary.append(["Critical events (recent)", _fmt(checks.get("Recent Events", "critical_events"))])
        for event in checks.get("Recent Events", "events") or []:
            if isinstance(event, dict):
                kind, text = event.get("event_type"), event.get("description")
                description = f"{kind}: {text}" if kind and text else _fmt(kind or text)
                event_rows.append(
                    [
                        _fmt(event.get("severity")),
                        _fmt(event.get("object_name")),
                        description,
                        _fmt_timestamp(event.get("timestamp")),
                    ]
                )
    tables.append(DetailTable(["Item", "Value"], summary, [0.5, 0.5]))
    list_headers = ["Severity", "Object", "Description", "Raised (UTC)"]
    list_weights = [0.13, 0.32, 0.33, 0.22]
    if alarm_rows:
        tables.append(DetailTable(list_headers, alarm_rows, list_weights, title="Unresolved critical/major alarms"))
    if event_rows:
        tables.append(DetailTable(list_headers, event_rows, list_weights, title="Critical events (recent)"))
    return DetailGroup(
        "alarms",
        _TITLE_PREFIX + "Alarms & Events",
        "Alarm and event totals, followed by each unresolved critical or major alarm and any recent critical event.",
        tables,
    )


_SWITCH_CHECKS = ("MLAG Status", "Switch NTP", "Switch Config Readability")
_SWITCH_FLAGS = (
    ("peer_alive", "Peer alive"),
    ("backup_active", "Backup active"),
    ("admin_enabled", "Admin enabled"),
    ("oper_up", "Operational up"),
    ("peer_count", "NTP peers"),
)


def _switch_checks(checks: _Checks) -> Optional[DetailGroup]:
    if not checks.has(*_SWITCH_CHECKS):
        return None
    rows: List[List[str]] = []
    for check in _SWITCH_CHECKS:
        if not checks.has(check):
            continue
        host = checks.get(check, "host")
        hosts = checks.get(check, "hosts") or ([host] if host else [])
        checks.consume(check, "stdout")
        result = checks.result(check).get("message") or NOT_REPORTED
        flags = [
            f"{label}: {_fmt(checks.get(check, key))}" for key, label in _SWITCH_FLAGS if key in checks.details(check)
        ]
        if flags:
            result += " (" + "; ".join(flags) + ")"
        stderr = (checks.get(check, "stderr") or "").strip()
        if stderr:
            result += f" — {stderr[:200]}"
        rows.append([check, _fmt(hosts) or NOT_REPORTED, _fmt(checks.get(check, "switch_os")), result])
    return DetailGroup(
        "switch",
        _TITLE_PREFIX + "Switch Checks (SSH)",
        "Results of the SSH checks run on each switch. Raw command output is omitted; see the switch "
        "configuration output for full details.",
        [DetailTable(["Check", "Switches", "OS", "Result"], rows, [0.22, 0.25, 0.13, 0.40])],
    )


_GROUP_BUILDERS: Sequence[Callable[[_Checks], Optional[DetailGroup]]] = (
    _cluster_state,
    _hardware,
    _rack_placement,
    _storage,
    _capacity,
    _network,
    _data_protection,
    _alarms,
    _switch_checks,
)


def _other_details(checks: _Checks) -> Optional[DetailGroup]:
    rows: List[List[str]] = []
    for name in checks.order:
        for key, value in checks.details(name).items():
            if key in checks.used[name] or _is_empty(value):
                continue
            rows.append([name, humanize_key(key), _fmt(value)])
    if not rows:
        return None
    return DetailGroup(
        "other",
        _TITLE_PREFIX + "Other Check Details",
        "Details reported by checks that are not covered by the groups above.",
        [DetailTable(["Check", "Item", "Value"], rows, [0.28, 0.28, 0.44])],
    )


def build_health_detail_groups(results: Iterable[Dict[str, Any]]) -> List[DetailGroup]:
    """Group health check details into consolidated report tables.

    Args:
        results: ``HealthCheckResult`` dicts (``check_name``, ``status``, ``message``, ``details``).

    Returns:
        List[DetailGroup]: Groups in report order; a group appears only when at least one
        of its checks is present. Unconsumed fields end up in a final "other" group.
    """
    checks = _Checks(results or [])
    groups = [group for group in (build(checks) for build in _GROUP_BUILDERS) if group is not None]
    other = _other_details(checks)
    if other is not None:
        groups.append(other)
    return groups
