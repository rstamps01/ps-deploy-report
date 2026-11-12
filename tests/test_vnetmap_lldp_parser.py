"""Unit tests for VNetMapLLDPParser (NET-7).

Fixtures under ``tests/fixtures/vnetmap_lldp/`` are synthetic: ACME names,
RFC 5737 addresses, shaped like ``vnetmap_lldp.py --operation show-mapping``
output (banner, ``\\r`` progress lines, per-switch tables, final table).
"""

import sys
from pathlib import Path
from typing import List

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from vnetmap_lldp_parser import VNetMapLLDPParser, parse_lldp_text  # noqa: E402
from vnetmap_parser import VNetMapParser  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "vnetmap_lldp"

ROW_KEYS = {
    "hostname",
    "node_hostname",
    "node_ip",
    "node_mgmt_ip",
    "ips",
    "interface",
    "switch_name",
    "switch_ip",
    "port",
    "mac",
    "network",
}

FINAL_HEADERS = ["Hostname", "Node", "Port", "IPs", "Switch", "Switch Port"]


def _table(headers: List[str], rows: List[List[str]]) -> str:
    """Render a table the way vnetmap_lldp.py ``format_table`` does."""
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

    def line(cells: List[str]) -> str:
        return "|" + "".join(f" {c:<{w}} |" for c, w in zip(cells, widths))

    return "\n".join([sep, line(headers), sep] + [line(r) for r in rows] + [sep])


def _final(rows: List[List[str]], headers: List[str] = FINAL_HEADERS) -> str:
    return "\nLLDP Connection Mapping:\n" + _table(headers, rows) + "\n"


def _fixture(name: str) -> str:
    return (FIXTURES / name).read_bytes().decode("utf-8")


def _row(result, hostname: str, interface: str):
    matches = [r for r in result["topology"] if r["hostname"] == hostname and r["interface"] == interface]
    assert len(matches) == 1, matches
    return matches[0]


class TestVNetMapLLDPParserContract:
    """The result must be a drop-in for ``VNetMapParser.parse()``."""

    def test_parse_keys_superset_of_vnetmap_parser(self, tmp_path):
        vnetmap_file = tmp_path / "vnetmap_output.txt"
        vnetmap_file.write_text(
            "Full topology\n" "acme-cn1    192.0.2.1    swp1    198.51.100.11    f0    aa:bb:cc:dd:ee:01    A\n\n"
        )
        legacy = VNetMapParser(str(vnetmap_file)).parse()

        result = VNetMapLLDPParser(str(FIXTURES / "onyx_show_mapping.txt")).parse()

        assert set(legacy) <= set(result)
        assert result["source"] == "lldp"
        assert result["total_connections"] == len(result["topology"])
        assert result["lldp_neighbors"] == []
        assert result["ib_switch_headers"] == []

    def test_parse_missing_file_keys_superset_of_vnetmap_parser(self, tmp_path):
        legacy = VNetMapParser(str(tmp_path / "absent.txt")).parse()

        result = VNetMapLLDPParser(str(tmp_path / "absent.txt")).parse()

        assert set(legacy) <= set(result)

    def test_parse_rows_have_exact_contract_keys(self):
        result = parse_lldp_text(_fixture("onyx_show_mapping.txt"))

        assert result["topology"]
        for row in result["topology"]:
            assert set(row) == ROW_KEYS

    def test_parse_lldp_text_is_static_on_class(self):
        result = VNetMapLLDPParser.parse_lldp_text(_fixture("cumulus_show_mapping.txt"))

        assert result["total_connections"] == 8


class TestVNetMapLLDPParser:
    """Fixture-driven parsing."""

    def test_parse_onyx_fixture(self):
        result = VNetMapLLDPParser(str(FIXTURES / "onyx_show_mapping.txt")).parse()

        assert result["available"] is True
        assert result["total_connections"] == 8
        assert result["switch_names"] == ["ACME-SW-01", "ACME-SW-02"]
        assert result["lldp_service_status"] == {"active": 4, "inactive": 4}
        assert result["table_source"] == "final"
        assert result["operation_failed"] is False
        assert result["no_connections"] is False
        assert {r["port"] for r in result["topology"]} == {"Eth1/1/1", "Eth1/1/2", "Eth1/13/1", "Eth1/13/2"}

    def test_parse_onyx_row_fields(self):
        result = parse_lldp_text(_fixture("onyx_show_mapping.txt"))

        row = _row(result, "acme-cn1", "enp7s0f1")
        assert row == {
            "hostname": "acme-cn1",
            "node_hostname": "acme-cn1",
            "node_ip": "203.0.113.11",
            "node_mgmt_ip": "192.0.2.11",
            "ips": ["192.0.2.11", "203.0.113.11"],
            "interface": "enp7s0f1",
            "switch_name": "ACME-SW-01",
            "switch_ip": "ACME-SW-01",
            "port": "Eth1/1/1",
            "mac": "",
            "network": "B",
        }

    def test_parse_onyx_multi_ip_cell_picks_switch_subnet(self):
        result = parse_lldp_text(_fixture("onyx_show_mapping.txt"))

        row = _row(result, "acme-dn1", "enp3s0f1np1")
        assert row["ips"] == ["198.51.100.250", "203.0.113.21", "192.0.2.21"]
        assert row["node_ip"] == "203.0.113.21"

    def test_parse_cumulus_fixture(self):
        result = parse_lldp_text(_fixture("cumulus_show_mapping.txt"))

        assert result["total_connections"] == 8
        assert result["switch_names"] == ["ACME-SW-01", "ACME-SW-02"]
        assert {r["port"] for r in result["topology"]} == {"swp1s0", "swp1s1", "swp2s0", "swp2s1"}
        assert {r["network"] for r in result["topology"] if r["switch_name"] == "ACME-SW-01"} == {"A"}
        assert {r["network"] for r in result["topology"] if r["switch_name"] == "ACME-SW-02"} == {"B"}
        assert result["cross_connections"] == []

    def test_parse_lldp_text_progress_carriage_returns(self):
        text = _fixture("cumulus_show_mapping.txt")
        assert "\r" in text and "█" in text

        result = parse_lldp_text(text)

        assert result["total_connections"] == 8
        assert not any("Progress" in r["hostname"] for r in result["topology"])

    def test_parse_lldp_text_ansi_codes_and_crlf(self):
        rows = [["acme-cn1", "192.0.2.11", "ens1f0np0", "198.51.100.11", "ACME-SW-01", "swp1s0"]]
        text = "\x1b[1;32mLLDP service status: 1 active, 1 inactive\x1b[0m\n" + _final(rows)
        text = text.replace("| acme-cn1", "| \x1b[33macme-cn1\x1b[0m").replace("\n", "\r\n")

        result = parse_lldp_text(text)

        assert result["lldp_service_status"] == {"active": 1, "inactive": 1}
        assert [r["hostname"] for r in result["topology"]] == ["acme-cn1"]
        assert result["topology"][0]["port"] == "swp1s0"

    def test_parse_lldp_text_box_drawing_table(self):
        text = (
            "LLDP Connection Mapping:\n"
            "┌──────────┬────────────┬───────────┬───────────────┬────────────┬─────────────┐\n"
            "│ Hostname │ Node       │ Port      │ IPs           │ Switch     │ Switch Port │\n"
            "├──────────┼────────────┼───────────┼───────────────┼────────────┼─────────────┤\n"
            "│ acme-cn1 │ 192.0.2.11 │ ens1f0np0 │ 198.51.100.11 │ ACME-SW-01 │ swp1s0      │\n"
            "└──────────┴────────────┴───────────┴───────────────┴────────────┴─────────────┘\n"
        )

        result = parse_lldp_text(text)

        assert result["total_connections"] == 1
        assert result["topology"][0]["switch_name"] == "ACME-SW-01"

    def test_parse_per_switch_only_rebuilds_rows(self):
        full = parse_lldp_text(_fixture("cumulus_show_mapping.txt"))

        rebuilt = parse_lldp_text(_fixture("per_switch_only.txt"))

        assert rebuilt["table_source"] == "per_switch"
        assert rebuilt["available"] is True

        def key(r):
            return tuple(sorted((k, str(v)) for k, v in r.items()))

        assert sorted(map(key, rebuilt["topology"])) == sorted(map(key, full["topology"]))

    def test_parse_no_connections(self):
        result = VNetMapLLDPParser(str(FIXTURES / "no_connections.txt")).parse()

        assert result["available"] is True
        assert result["topology"] == []
        assert result["total_connections"] == 0
        assert result["no_connections"] is True
        assert result["operation_failed"] is False
        assert result["switch_names"] == []
        assert result["table_source"] is None

    def test_parse_operation_failed_keeps_rows(self):
        result = VNetMapLLDPParser(str(FIXTURES / "operation_failed.txt")).parse()

        assert result["available"] is True
        assert result["operation_failed"] is True
        assert result["total_connections"] == 2
        assert result["switch_names"] == ["ACME-SW-02"]
        assert result["lldp_service_status"] == {"active": 2, "inactive": 6}
        assert {r["network"] for r in result["topology"]} == {"A"}

    def test_parse_lldp_text_operation_failed_without_rows(self):
        text = (
            "\nNo connections found. This may indicate a network issue or incorrect switch names.\n"
            "\n" + "=" * 80 + "\nOperation failed - see logs for details\n" + "=" * 80 + "\n"
        )

        result = parse_lldp_text(text)

        assert result["available"] is True
        assert result["topology"] == []
        assert result["operation_failed"] is True
        assert result["no_connections"] is True

    def test_parse_lldp_text_service_status_absent(self):
        result = parse_lldp_text(_final([["acme-cn1", "192.0.2.11", "p0", "198.51.100.11", "ACME-SW-01", "swp1"]]))

        assert result["lldp_service_status"] is None

    def test_parse_lldp_text_extra_column_tolerated(self):
        headers = ["Switch", "Hostname", "Chassis ID", "Node", "Port", "IPs", "Switch Port", "Speed"]
        rows = [
            [
                "ACME-SW-01",
                "acme-cn1",
                "00:00:5e:00:53:01",
                "192.0.2.11",
                "ens1f0np0",
                "198.51.100.11",
                "swp1s0",
                "100G",
            ],
            [
                "ACME-SW-02",
                "acme-cn1",
                "00:00:5e:00:53:02",
                "192.0.2.11",
                "ens1f1np1",
                "203.0.113.11",
                "swp1s0",
                "100G",
            ],
        ]

        result = parse_lldp_text(_final(rows, headers))

        row = _row(result, "acme-cn1", "ens1f1np1")
        assert row["switch_name"] == "ACME-SW-02"
        assert row["port"] == "swp1s0"
        assert row["node_ip"] == "203.0.113.11"
        assert row["node_mgmt_ip"] == "192.0.2.11"
        assert set(row) == ROW_KEYS

    def test_parse_lldp_text_dedupes_identical_rows(self):
        row = ["acme-cn1", "192.0.2.11", "ens1f0np0", "198.51.100.11", "ACME-SW-01", "swp1s0"]

        result = parse_lldp_text(_final([row, row, list(row)]))

        assert result["total_connections"] == 1

    def test_parse_lldp_text_skips_row_without_switch(self):
        rows = [
            ["acme-cn1", "192.0.2.11", "ens1f0np0", "198.51.100.11", "", "swp1s0"],
            ["acme-cn1", "192.0.2.11", "ens1f1np1", "203.0.113.11", "ACME-SW-02", "swp1s0"],
        ]

        result = parse_lldp_text(_final(rows))

        assert [r["switch_name"] for r in result["topology"]] == ["ACME-SW-02"]

    def test_parse_missing_file(self, tmp_path):
        result = VNetMapLLDPParser(str(tmp_path / "absent.txt")).parse()

        assert result["available"] is False
        assert "not found" in result["error"]
        assert result["topology"] == []
        assert result["total_connections"] == 0
        assert result["source"] == "lldp"
        assert result["lldp_service_status"] is None

    def test_parse_unreadable_path(self, tmp_path):
        result = VNetMapLLDPParser(str(tmp_path)).parse()

        assert result["available"] is False
        assert result["error"]

    def test_get_connections_by_switch_after_parse(self):
        parser = VNetMapLLDPParser(str(FIXTURES / "cumulus_show_mapping.txt"))
        parser.parse()

        grouped = parser.get_connections_by_switch()

        assert sorted(grouped) == ["ACME-SW-01", "ACME-SW-02"]
        assert [c["port"] for c in grouped["ACME-SW-01"]] == ["swp1s0", "swp1s1", "swp2s0", "swp2s1"]
        assert parser.get_cross_connection_summary().startswith("No cross-connections")


class TestVNetMapLLDPNetworkAssignment:
    """Network side derived from each switch's canonical /24 (NET-3 rule)."""

    def test_parse_onyx_labels_follow_subnet_not_name(self):
        result = parse_lldp_text(_fixture("onyx_show_mapping.txt"))

        assert result["switch_subnets"] == {"ACME-SW-01": "203.0.113", "ACME-SW-02": "198.51.100"}
        assert result["switch_networks"] == {"ACME-SW-01": "B", "ACME-SW-02": "A"}
        for row in result["topology"]:
            assert row["network"] == result["switch_networks"][row["switch_name"]]

    def test_parse_onyx_miscabled_row_keeps_switch_label(self):
        result = parse_lldp_text(_fixture("onyx_show_mapping.txt"))

        row = _row(result, "acme-dn2", "enp3s0f1np1")
        assert row["switch_name"] == "ACME-SW-01"
        assert row["node_ip"] == "198.51.100.122"
        assert row["network"] == "B"
        assert result["cross_connections"] == [
            {"switch_ip": "ACME-SW-01", "networks": ["198.51.100", "203.0.113"], "network_labels": ["A", "B"]}
        ]

    def test_parse_lldp_text_subnets_ordered_numerically(self):
        # RFC 1918 addresses: lexical order ("10.0.10" < "10.0.9") is the opposite of numeric order.
        rows = [
            ["acme-cn1", "192.0.2.11", "p0", "10.0.10.11", "ACME-SW-01", "swp1"],
            ["acme-cn1", "192.0.2.11", "p1", "10.0.9.11", "ACME-SW-02", "swp1"],
        ]

        result = parse_lldp_text(_final(rows))

        assert result["switch_networks"] == {"ACME-SW-01": "B", "ACME-SW-02": "A"}

    def test_parse_lldp_text_third_switch_gets_label_c(self):
        rows = [
            ["acme-cn1", "192.0.2.11", "p0", "198.51.100.11", "ACME-SW-01", "swp1"],
            ["acme-cn1", "192.0.2.11", "p1", "203.0.113.11", "ACME-SW-02", "swp1"],
            ["acme-cn2", "192.0.2.12", "p0", "192.0.2.112", "ACME-SW-03", "swp1"],
        ]

        result = parse_lldp_text(_final(rows))

        assert result["switch_networks"] == {"ACME-SW-01": "B", "ACME-SW-02": "C", "ACME-SW-03": "A"}

    def test_parse_lldp_text_shared_subnet_shares_label(self):
        rows = [
            ["acme-cn1", "192.0.2.11", "p0", "198.51.100.11", "ACME-SW-01", "swp1"],
            ["acme-cn2", "192.0.2.12", "p0", "198.51.100.12", "ACME-SW-03", "swp1"],
            ["acme-cn1", "192.0.2.11", "p1", "203.0.113.11", "ACME-SW-02", "swp1"],
        ]

        result = parse_lldp_text(_final(rows))

        assert result["switch_networks"] == {"ACME-SW-01": "A", "ACME-SW-02": "B", "ACME-SW-03": "A"}

    def test_parse_lldp_text_switch_without_ipv4_labelled_after_subnets(self):
        rows = [
            ["acme-cn1", "192.0.2.11", "p0", "", "ACME-SW-00", "swp1"],
            ["acme-cn1", "192.0.2.11", "p1", "198.51.100.11", "ACME-SW-01", "swp1"],
        ]

        result = parse_lldp_text(_final(rows))

        assert result["switch_subnets"] == {"ACME-SW-00": None, "ACME-SW-01": "198.51.100"}
        assert result["switch_networks"] == {"ACME-SW-00": "B", "ACME-SW-01": "A"}
        assert _row(result, "acme-cn1", "p0")["node_ip"] == ""

    @pytest.mark.parametrize(
        "ips, expected",
        [
            ("192.0.2.11, 198.51.100.11", "198.51.100.11"),
            ("198.51.100.11/24", "198.51.100.11"),
            ("192.0.2.11", "192.0.2.11"),
        ],
    )
    def test_parse_lldp_text_data_ip_excludes_mgmt(self, ips, expected):
        result = parse_lldp_text(_final([["acme-cn1", "192.0.2.11", "p0", ips, "ACME-SW-01", "swp1"]]))

        assert result["topology"][0]["node_ip"] == expected
