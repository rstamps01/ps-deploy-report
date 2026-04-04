"""Tests for vnetmap-status helpers and /api/vnetmap-status endpoint."""

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))


# ---------------------------------------------------------------------------
# Import helpers directly from app module
# ---------------------------------------------------------------------------
from app import (
    _extract_hardware_fingerprint,
    _compare_hardware_fingerprints,
    _parse_vnetmap_timestamp,
    _find_report_jsons_for_cluster,
)


# ---------------------------------------------------------------------------
# _extract_hardware_fingerprint
# ---------------------------------------------------------------------------
class TestExtractHardwareFingerprint:
    def test_dict_based_inventory(self):
        report = {
            "hardware_inventory": {
                "cboxes": {"cb1": {"name": "cb1"}, "cb2": {"name": "cb2"}},
                "dboxes": {"db1": {"name": "db1"}},
                "cnodes": {
                    "cn1": {"mgmt_ip": "10.0.0.1"},
                    "cn2": {"mgmt_ip": "10.0.0.2"},
                },
                "dnodes": {"dn1": {"mgmt_ip": "10.0.1.1"}},
                "switches": {
                    "sw1": {"mgmt_ip": "10.0.2.1"},
                    "sw2": {"mgmt_ip": "10.0.2.2"},
                },
                "eboxes": {},
            }
        }
        fp = _extract_hardware_fingerprint(report)
        assert fp["cbox_count"] == 2
        assert fp["dbox_count"] == 1
        assert fp["cnode_count"] == 2
        assert fp["dnode_count"] == 1
        assert fp["switch_count"] == 2
        assert fp["ebox_count"] == 0
        assert fp["cnode_ips"] == ["10.0.0.1", "10.0.0.2"]
        assert fp["switch_ips"] == ["10.0.2.1", "10.0.2.2"]

    def test_list_based_inventory(self):
        report = {
            "hardware_inventory": {
                "cboxes": [{"name": "cb1"}],
                "dboxes": [],
                "cnodes": [{"mgmt_ip": "10.0.0.1"}],
                "dnodes": [{"mgmt_ip": "10.0.1.1"}, {"mgmt_ip": "10.0.1.2"}],
                "switches": [{"mgmt_ip": "10.0.2.1"}],
            }
        }
        fp = _extract_hardware_fingerprint(report)
        assert fp["cbox_count"] == 1
        assert fp["dbox_count"] == 0
        assert fp["cnode_count"] == 1
        assert fp["dnode_count"] == 2
        assert fp["switch_count"] == 1
        assert fp["ebox_count"] == 0

    def test_empty_inventory(self):
        fp = _extract_hardware_fingerprint({})
        assert fp["cbox_count"] == 0
        assert fp["cnode_ips"] == []

    def test_missing_mgmt_ip(self):
        report = {
            "hardware_inventory": {
                "cnodes": [{"name": "cn1"}, {"mgmt_ip": "10.0.0.1"}],
            }
        }
        fp = _extract_hardware_fingerprint(report)
        assert fp["cnode_count"] == 2
        assert fp["cnode_ips"] == ["10.0.0.1"]

    def test_ebox_support(self):
        report = {
            "hardware_inventory": {
                "eboxes": [
                    {"mgmt_ip": "10.0.3.1"},
                    {"mgmt_ip": "10.0.3.2"},
                ],
            }
        }
        fp = _extract_hardware_fingerprint(report)
        assert fp["ebox_count"] == 2
        assert fp["ebox_ips"] == ["10.0.3.1", "10.0.3.2"]


# ---------------------------------------------------------------------------
# _compare_hardware_fingerprints
# ---------------------------------------------------------------------------
class TestCompareHardwareFingerprints:
    def test_identical(self):
        fp = {
            "cbox_count": 2,
            "dbox_count": 1,
            "cnode_count": 2,
            "dnode_count": 2,
            "switch_count": 2,
            "ebox_count": 0,
            "cnode_ips": ["10.0.0.1", "10.0.0.2"],
            "dnode_ips": ["10.0.1.1", "10.0.1.2"],
            "switch_ips": ["10.0.2.1", "10.0.2.2"],
            "ebox_ips": [],
        }
        changed, summary = _compare_hardware_fingerprints(fp, fp)
        assert not changed
        assert summary == []

    def test_count_change(self):
        old = {
            "cbox_count": 2,
            "dbox_count": 1,
            "cnode_count": 2,
            "dnode_count": 2,
            "switch_count": 2,
            "ebox_count": 0,
            "cnode_ips": [],
            "dnode_ips": [],
            "switch_ips": [],
            "ebox_ips": [],
        }
        new = dict(old, cnode_count=4)
        changed, summary = _compare_hardware_fingerprints(old, new)
        assert changed
        assert any("CNode count changed" in s for s in summary)

    def test_ip_added(self):
        old = {
            "cbox_count": 1,
            "dbox_count": 0,
            "cnode_count": 1,
            "dnode_count": 0,
            "switch_count": 1,
            "ebox_count": 0,
            "cnode_ips": ["10.0.0.1"],
            "dnode_ips": [],
            "switch_ips": ["10.0.2.1"],
            "ebox_ips": [],
        }
        new = dict(old, switch_count=2, switch_ips=["10.0.2.1", "10.0.2.2"])
        changed, summary = _compare_hardware_fingerprints(old, new)
        assert changed
        assert any("New Switch detected: 10.0.2.2" in s for s in summary)

    def test_ip_removed(self):
        old = {
            "cbox_count": 2,
            "dbox_count": 0,
            "cnode_count": 2,
            "dnode_count": 0,
            "switch_count": 1,
            "ebox_count": 0,
            "cnode_ips": ["10.0.0.1", "10.0.0.2"],
            "dnode_ips": [],
            "switch_ips": [],
            "ebox_ips": [],
        }
        new = dict(old, cnode_count=1, cnode_ips=["10.0.0.1"])
        changed, summary = _compare_hardware_fingerprints(old, new)
        assert changed
        assert any("CNode removed: 10.0.0.2" in s for s in summary)

    def test_ebox_change(self):
        old = {
            "cbox_count": 0,
            "dbox_count": 0,
            "cnode_count": 0,
            "dnode_count": 0,
            "switch_count": 0,
            "ebox_count": 2,
            "cnode_ips": [],
            "dnode_ips": [],
            "switch_ips": [],
            "ebox_ips": ["10.0.3.1", "10.0.3.2"],
        }
        new = dict(old, ebox_count=3, ebox_ips=["10.0.3.1", "10.0.3.2", "10.0.3.3"])
        changed, summary = _compare_hardware_fingerprints(old, new)
        assert changed
        assert any("EBox count changed" in s for s in summary)
        assert any("New EBox detected: 10.0.3.3" in s for s in summary)


# ---------------------------------------------------------------------------
# _parse_vnetmap_timestamp
# ---------------------------------------------------------------------------
class TestParseVnetmapTimestamp:
    def test_standard_filename(self):
        result = _parse_vnetmap_timestamp("vnetmap_output_10.143.11.63_20260330_030728.txt")
        assert result == "2026-03-30 03:07:28"

    def test_no_match(self):
        assert _parse_vnetmap_timestamp("random_file.txt") == ""


# ---------------------------------------------------------------------------
# _find_report_jsons_for_cluster
# ---------------------------------------------------------------------------
class TestFindReportJsons:
    def test_finds_matching_reports(self, tmp_path):
        for i, ip in enumerate(["10.0.0.1", "10.0.0.1", "10.0.0.2"]):
            p = tmp_path / f"vast_data_test_{i}.json"
            p.write_text(json.dumps({"cluster_ip": ip}))
        results = _find_report_jsons_for_cluster("10.0.0.1", str(tmp_path))
        assert len(results) == 2

    def test_returns_max_2(self, tmp_path):
        for i in range(5):
            p = tmp_path / f"vast_data_test_{i}.json"
            p.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        results = _find_report_jsons_for_cluster("10.0.0.1", str(tmp_path))
        assert len(results) == 2

    def test_empty_dir(self, tmp_path):
        results = _find_report_jsons_for_cluster("10.0.0.1", str(tmp_path))
        assert results == []

    def test_nonexistent_dir(self):
        results = _find_report_jsons_for_cluster("10.0.0.1", "/nonexistent/path")
        assert results == []


# ---------------------------------------------------------------------------
# /api/vnetmap-status route
# ---------------------------------------------------------------------------
class TestVnetmapStatusEndpoint:
    @pytest.fixture()
    def client(self):
        from app import create_flask_app

        app = create_flask_app()
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c

    def test_missing_cluster_ip(self, client):
        resp = client.get("/api/vnetmap-status")
        assert resp.status_code == 400

    def test_no_vnetmap_file(self, client):
        with patch("app._find_latest_vnetmap_output", return_value=None):
            with patch("app._find_report_jsons_for_cluster", return_value=[]):
                resp = client.get("/api/vnetmap-status?cluster_ip=10.0.0.1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["exists"] is False
        assert data["recommended"] is False
        assert data["change_summary"] == []

    def test_vnetmap_exists_no_changes(self, client, tmp_path):
        vnetmap_file = tmp_path / "vnetmap_output_10.0.0.1_20260330_100000.txt"
        vnetmap_file.write_text("test")

        report1 = tmp_path / "report1.json"
        report2 = tmp_path / "report2.json"
        hw = {"hardware_inventory": {"cnodes": [{"mgmt_ip": "10.0.0.1"}], "switches": [{"mgmt_ip": "10.0.2.1"}]}}
        report1.write_text(json.dumps(hw))
        report2.write_text(json.dumps(hw))

        with patch("app._find_latest_vnetmap_output", return_value=vnetmap_file):
            with patch("app._find_report_jsons_for_cluster", return_value=[report1, report2]):
                resp = client.get("/api/vnetmap-status?cluster_ip=10.0.0.1")
        data = resp.get_json()
        assert data["exists"] is True
        assert data["hardware_changed"] is False
        assert data["recommended"] is False
        assert "2026-03-30" in data["created_at"]

    def test_vnetmap_exists_with_changes(self, client, tmp_path):
        vnetmap_file = tmp_path / "vnetmap_output_10.0.0.1_20260330_100000.txt"
        vnetmap_file.write_text("test")

        report_new = tmp_path / "report_new.json"
        report_old = tmp_path / "report_old.json"
        hw_new = {"hardware_inventory": {"cnodes": [{"mgmt_ip": "10.0.0.1"}, {"mgmt_ip": "10.0.0.2"}]}}
        hw_old = {"hardware_inventory": {"cnodes": [{"mgmt_ip": "10.0.0.1"}]}}
        report_new.write_text(json.dumps(hw_new))
        report_old.write_text(json.dumps(hw_old))

        with patch("app._find_latest_vnetmap_output", return_value=vnetmap_file):
            with patch("app._find_report_jsons_for_cluster", return_value=[report_new, report_old]):
                resp = client.get("/api/vnetmap-status?cluster_ip=10.0.0.1")
        data = resp.get_json()
        assert data["exists"] is True
        assert data["hardware_changed"] is True
        assert data["recommended"] is True
        assert len(data["change_summary"]) > 0
