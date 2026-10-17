"""Consolidated health check detail groups for the PDF report (RPT-LAYOUT-1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.health_detail_groups import build_health_detail_groups, humanize_key  # noqa: E402


def _r(name, details, status="pass", message="", category="api"):
    return {"check_name": name, "category": category, "status": status, "message": message, "details": details}


EBOX_RESULTS = [
    _r(
        "Cluster RAID Health",
        {"ssd_raid_state": "HEALTHY", "nvram_raid_state": "HEALTHY", "memory_raid_state": "HEALTHY"},
    ),
    _r(
        "RAID Rebuild Progress",
        {"ssd_raid_rebuild_progress": 0, "nvram_raid_rebuild_progress": 100, "memory_raid_rebuild_progress": 100},
    ),
    _r("Leader State", {"leader_state": "UP", "leader_cnode": "cnode-131-1-4200"}),
    _r("Cluster State", {"state": "ONLINE", "enabled": True}),
    _r("Expansion State", {"expansion_state": "NONE"}),
    _r("Upgrade State", {"upgrade_state": "UNKNOWN"}),
    _r("CNode Status", {"total": 43, "inactive": [], "disabled": [], "mgmt_cnode": "cnode-129-13-4200"}),
    _r("DNode Status", {"total": 86, "inactive": [], "disabled": []}),
    _r("DBox Status", {"total": 43, "inactive": []}),
    _r("CBox Status", {}, status="skipped", message="Not applicable — converged EBox cluster (covered by EBox Status)"),
    _r("EBox Status", {"total": 43, "inactive": []}),
    _r("Firmware Consistency", {}, message="Firmware versions are consistent across all nodes"),
    _r(
        "Active Alarms",
        {
            "total_alarms": 52,
            "critical_unresolved": 2,
            "alarms": [
                {
                    "id": 18,
                    "severity": "MAJOR",
                    "object_type": "VmsAsyncTaskFail",
                    "object_name": "VmsAsyncTaskFail call_home_logs",
                    "description": "Alarm on VmsAsyncTaskFail",
                    "timestamp": "2026-10-15T10:25:01.209952Z",
                },
                {
                    "id": 9,
                    "severity": "MAJOR",
                    "object_type": "License",
                    "object_name": "License-1",
                    "description": "Alarm on License",
                    "timestamp": "2026-10-15T08:42:15.178112Z",
                },
            ],
        },
        status="warning",
    ),
    _r("Recent Events", {"total_events_returned": 1, "critical_events": 0, "events": []}),
    _r("VIP Pools", {"total_pools": 1, "enabled_pools": 1}),
    _r(
        "Network Settings",
        {"dns": ["1.1.1.1", "8.8.8.8"], "ntp": ["192.0.2.123", "192.0.2.124"], "gateway": ["198.51.100.1"]},
    ),
    _r("License", {"license": "Active"}),
    _r("Capacity", {"physical_space_in_use_percent": 0.0, "threshold": 80}),
    _r("Handle Usage", {"used_handles_percent": 12.345, "threshold": 80}),
    _r(
        "Performance Baseline",
        {
            "iops": 7.0,
            "latency": 1530.8358208955226,
            "bw": 1318913.0,
            "rd_iops": 0.0,
            "wr_iops": 7.0,
            "rd_latency": 0.0,
            "wr_latency": 1530.8358208955226,
            "rd_bw": 0.0,
            "wr_bw": 1318913.0,
        },
        category="performance",
    ),
    _r("Replication", {"dr_enabled": None}),
    _r("Snapshots", {"total_snapshots": 0, "failed_snapshots": 0}),
    _r("Quotas", {"total_quotas": 0, "blocked_users": 0}),
    _r("Data Protection", {"total_policies": 0, "active_policies": 0}, status="warning"),
    _r("Device Health (Prometheus)", {"total_metrics": 6692, "failed_device_count": 0, "media_error_count": 0}),
    _r(
        "Call Home Status",
        {
            "call_home_enabled": True,
            "cloud_registered": False,
            "cloud_enabled": False,
            "log_enabled": True,
            "bundle_enabled": True,
            "customer": "Not set",
        },
    ),
    _r(
        "Rack/U-Height Configuration",
        {"rack_count": 0, "cboxes_missing_rack": [], "dboxes_missing_rack": [f"ebox-{i:02d}" for i in range(43)]},
        status="warning",
    ),
    _r("Switches in VMS", {"switch_count": 0, "switches": []}, status="skipped"),
]


def _groups(results=EBOX_RESULTS):
    return {g.key: g for g in build_health_detail_groups(results)}


def _rows(group, table_index=0):
    return group.tables[table_index].rows


def _row_map(group, table_index=0):
    return {row[0]: row[1:] for row in _rows(group, table_index)}


class TestGroupSelection:
    def test_expected_groups_in_order(self):
        keys = [g.key for g in build_health_detail_groups(EBOX_RESULTS)]
        assert keys == [
            "cluster_state",
            "hardware",
            "rack_placement",
            "storage",
            "capacity",
            "network",
            "data_protection",
            "alarms",
        ]

    def test_every_group_has_heading_and_caption(self):
        for group in build_health_detail_groups(EBOX_RESULTS):
            assert group.title.startswith("Health Check Details — ")
            assert group.caption

    def test_group_omitted_when_none_of_its_checks_ran(self):
        results = [r for r in EBOX_RESULTS if r["check_name"] != "Active Alarms" and r["check_name"] != "Recent Events"]
        assert "alarms" not in _groups(results)

    def test_no_results_gives_no_groups(self):
        assert build_health_detail_groups([]) == []

    def test_rows_match_headers(self):
        for group in build_health_detail_groups(EBOX_RESULTS):
            for table in group.tables:
                assert len(table.col_weights) == len(table.headers)
                assert all(len(row) == len(table.headers) for row in table.rows)


class TestClusterState:
    def test_settings_labelled_with_source_check(self):
        rows = _row_map(_groups()["cluster_state"])
        assert rows["Cluster state"] == ["ONLINE", "Cluster State"]
        assert rows["Cluster enabled"] == ["Yes", "Cluster State"]
        assert rows["Leader CNode"] == ["cnode-131-1-4200", "Leader State"]
        assert rows["License status"] == ["Active", "License"]
        assert rows["Firmware versions"] == [
            "Firmware versions are consistent across all nodes",
            "Firmware Consistency",
        ]

    def test_upgrade_state_from_older_results_is_not_shown(self):
        """Saved results from earlier versions still carry the removed Upgrade State check."""
        groups = _groups()
        assert "Upgrade state" not in _row_map(groups["cluster_state"])
        assert "other" not in groups

    def test_firmware_mismatch_lists_versions_and_nodes(self):
        mismatch = _r(
            "Firmware Consistency",
            {"mismatches": {"cnode.os_version": {"12.15.15": ["cnode-1", "cnode-2"], "12.14.15": ["cnode-3"]}}},
            status="warning",
        )
        rows = _rows(_groups([mismatch])["cluster_state"])
        values = [r[1] for r in rows if r[0].startswith("Firmware")]
        assert "12.15.15 on cnode-1, cnode-2" in values
        assert "12.14.15 on cnode-3" in values


class TestHardware:
    def test_one_row_per_component(self):
        rows = _row_map(_groups()["hardware"])
        assert rows["CNodes"] == ["43", "0", "0", "VMS host: cnode-129-13-4200"]
        assert rows["DNodes"] == ["86", "0", "0", ""]
        assert rows["EBoxes"] == ["43", "0", "—", ""]

    def test_skipped_component_shows_reason(self):
        rows = _row_map(_groups()["hardware"])
        assert rows["CBoxes"][0] == "—"
        assert "converged EBox" in rows["CBoxes"][3]

    def test_inactive_names_in_notes(self):
        results = [_r("CBox Status", {"total": 4, "inactive": [{"name": "cbox-2", "state": "FAILED"}]}, "fail")]
        rows = _row_map(_groups(results)["hardware"])
        assert rows["CBoxes"][1] == "1"
        assert "cbox-2 (FAILED)" in rows["CBoxes"][3]


class TestRackPlacement:
    def test_full_list_with_count(self):
        rows = _row_map(_groups()["rack_placement"])
        assert rows["Racks defined"] == ["0"]
        assert rows["CBoxes without a rack"] == ["None"]
        value = rows["DBoxes / EBoxes without a rack"][0]
        assert value.startswith("43 — ebox-00, ebox-01")
        assert value.endswith("ebox-42")


class TestStorage:
    def test_raid_layers(self):
        group = _groups()["storage"]
        assert group.tables[0].headers == ["Layer", "RAID State", "Rebuild Progress (%)"]
        assert _rows(group) == [["SSD", "HEALTHY", "0%"], ["NVRAM", "HEALTHY", "100%"], ["Memory", "HEALTHY", "100%"]]

    def test_device_health_table(self):
        group = _groups()["storage"]
        rows = _row_map(group, 1)
        assert rows["Metrics scanned"] == ["6,692"]
        assert rows["Failed devices"] == ["0"]


class TestCapacity:
    def test_metrics_with_thresholds(self):
        rows = _row_map(_groups()["capacity"])
        assert rows["Physical capacity used"] == ["0.0%", "80%"]
        assert rows["Handle usage"] == ["12.3%", "80%"]
        assert rows["Quotas configured"] == ["0", "—"]
        assert rows["Failed snapshots"] == ["0", "—"]


class TestNetwork:
    def test_lists_are_joined(self):
        rows = _row_map(_groups()["network"])
        assert rows["DNS servers"] == ["1.1.1.1, 8.8.8.8"]
        assert rows["NTP servers"] == ["192.0.2.123, 192.0.2.124"]
        assert rows["Default gateway"] == ["198.51.100.1"]
        assert rows["VIP pools"] == ["1 of 1 enabled"]
        assert rows["Switches registered in VMS"] == ["None"]

    def test_switch_names_and_ips(self):
        sw = _r("Switches in VMS", {"switch_count": 2, "switches": [{"name": "sw-a", "ip": "10.0.0.1"}]})
        rows = _row_map(_groups([sw])["network"])
        assert rows["Switches registered in VMS"] == ["2 — sw-a (10.0.0.1)"]


class TestDataProtection:
    def test_services(self):
        rows = _row_map(_groups()["data_protection"])
        assert rows["Replication (DR)"] == ["Not enabled"]
        assert rows["Protection policies"] == ["0 active of 0"]
        assert rows["Call Home enabled"] == ["Yes"]
        assert rows["Call Home cloud registered"] == ["No"]
        assert rows["Customer name (Call Home)"] == ["Not set"]


class TestAlarms:
    def test_summary_and_alarm_list(self):
        group = _groups()["alarms"]
        summary = _row_map(group, 0)
        assert summary["Total alarms"] == ["52"]
        assert summary["Unresolved critical/major alarms"] == ["2"]
        assert summary["Critical events (recent)"] == ["0"]
        alarms = group.tables[1]
        assert alarms.headers == ["Severity", "Object", "Description", "Raised (UTC)"]
        assert alarms.rows[0] == [
            "MAJOR",
            "VmsAsyncTaskFail call_home_logs",
            "Alarm on VmsAsyncTaskFail",
            "2026-10-15 10:25:01",
        ]

    def test_critical_events_listed(self):
        events = _r(
            "Recent Events",
            {
                "total_events_returned": 5,
                "critical_events": 1,
                "events": [
                    {
                        "severity": "CRITICAL",
                        "event_type": "NodeDown",
                        "object_name": "dnode-1",
                        "description": "Node down",
                        "timestamp": "2026-10-15T01:02:03Z",
                    }
                ],
            },
        )
        group = _groups([events])["alarms"]
        assert group.tables[-1].rows[0] == ["CRITICAL", "dnode-1", "NodeDown: Node down", "2026-10-15 01:02:03"]


class TestPerformance:
    def test_performance_baseline_has_no_details_group(self):
        groups = _groups()
        assert "performance" not in groups
        assert "other" not in groups
        assert not any("Performance Baseline" in g.title for g in groups.values())


class TestSwitchChecks:
    def test_rows_without_raw_output(self):
        results = [
            _r(
                "MLAG Status",
                {"host": "10.0.0.1", "switch_os": "cumulus", "stdout": "x" * 500, "hosts": ["10.0.0.1", "10.0.0.2"]},
                message="MLAG healthy",
                category="switch_ssh",
            ),
            _r(
                "Switch NTP",
                {"host": "10.0.0.1", "switch_os": "cumulus", "stderr": "Authentication failed for cumulus@10.0.0.1"},
                status="error",
                message="SSH authentication failed",
                category="switch_ssh",
            ),
        ]
        group = _groups(results)["switch"]
        rows = _row_map(group)
        assert rows["MLAG Status"] == ["10.0.0.1, 10.0.0.2", "cumulus", "MLAG healthy"]
        assert rows["Switch NTP"][2] == "SSH authentication failed — Authentication failed for cumulus@10.0.0.1"
        assert "other" not in _groups(results)


class TestOtherDetails:
    def test_unmapped_check_uses_readable_labels(self):
        results = [_r("Brand New Check", {"widget_count": 3, "zone_names": ["a", "b"], "ignored": None})]
        group = _groups(results)["other"]
        assert group.tables[0].headers == ["Check", "Item", "Value"]
        assert group.tables[0].rows == [
            ["Brand New Check", "Widget Count", "3"],
            ["Brand New Check", "Zone Names", "a, b"],
        ]

    def test_unmapped_field_of_known_check(self):
        results = [_r("Capacity", {"physical_space_in_use_percent": 50.0, "threshold": 80, "logical_tb": 12})]
        group = _groups(results)["other"]
        assert group.tables[0].rows == [["Capacity", "Logical Tb", "12"]]


def test_humanize_key():
    assert humanize_key("physical_space_in_use_percent") == "Physical Space In Use Percent"
