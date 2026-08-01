"""Regression tests for per-cluster vnetmap segmentation and identity guard.

Reproduces the Tech Port cross-cluster contamination bug: two clusters
connected through the same Tech Port IP (e.g. ``192.168.2.2``) produce
``vnetmap_output_192.168.2.2_*.txt`` files that are indistinguishable by
filename. When the cluster being reported has no vnetmap of its own (e.g.
after a switch-auth failure), the finder must NOT fall back to another
cluster's file, and a parsed vnetmap must be rejected if its node inventory
does not match the cluster being reported.
"""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app import _find_latest_vnetmap_output  # noqa: E402
from vnetmap_parser import vnetmap_matches_cluster  # noqa: E402

TECH_PORT_IP = "192.168.2.2"


def _write_vnetmap(dir_path: Path, ip: str, stamp: str) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    f = dir_path / f"vnetmap_output_{ip}_{stamp}.txt"
    f.write_text("placeholder vnetmap output")
    return f


# ---------------------------------------------------------------------------
# _find_latest_vnetmap_output — authoritative per-cluster segmentation
# ---------------------------------------------------------------------------
class TestFinderSegmentation:
    def test_segmented_finder_does_not_fall_back_to_flat(self, tmp_path):
        """With a cluster key, a missing per-cluster vnetmap must NOT resolve
        to another cluster's file in the shared flat ``output/scripts`` dir."""
        # A different cluster's vnetmap sits in the flat dir under the SAME IP.
        _write_vnetmap(tmp_path / "output" / "scripts", TECH_PORT_IP, "20260615_162541")
        # The current cluster's own per-cluster scripts dir is empty.
        key = "ZOOMNFS01__VA23275720"
        (tmp_path / "clusters" / key / "output" / "scripts").mkdir(parents=True)

        with patch("utils.get_data_dir", return_value=tmp_path):
            result = _find_latest_vnetmap_output(TECH_PORT_IP, cluster_key=key)

        assert result is None, "Segmented lookup must not leak the flat-dir file from another cluster"

    def test_segmented_finder_returns_own_file(self, tmp_path):
        key = "ZOOMNFS01__VA23275720"
        own = _write_vnetmap(tmp_path / "clusters" / key / "output" / "scripts", TECH_PORT_IP, "20260721_114406")
        # A stale flat file must be ignored in favor of the per-cluster file.
        _write_vnetmap(tmp_path / "output" / "scripts", TECH_PORT_IP, "20260615_162541")

        with patch("utils.get_data_dir", return_value=tmp_path):
            result = _find_latest_vnetmap_output(TECH_PORT_IP, cluster_key=key)

        assert result == own

    def test_unsegmented_finder_uses_flat_dir(self, tmp_path):
        """Legacy behavior preserved when segmentation is disabled (no key)."""
        flat = _write_vnetmap(tmp_path / "output" / "scripts", TECH_PORT_IP, "20260615_162541")

        with patch("utils.get_data_dir", return_value=tmp_path):
            result = _find_latest_vnetmap_output(TECH_PORT_IP, cluster_key=None)

        assert result == flat


# ---------------------------------------------------------------------------
# vnetmap_matches_cluster — identity guard (defense-in-depth)
# ---------------------------------------------------------------------------
class TestIdentityGuard:
    def _vnetmap(self, hostnames, ips=None):
        ips = ips or [f"172.16.1.{i}" for i in range(len(hostnames))]
        return {
            "available": True,
            "topology": [{"node_hostname": h, "node_ip": ip} for h, ip in zip(hostnames, ips)],
        }

    def test_rejects_different_cluster_by_hostname(self):
        # vnetmap belongs to the RackP01 cluster; report is for ZOOMNFS01.
        vnetmap = self._vnetmap(["RackP01C02-CB9-U25-CN1", "RackP01C01-CB6-U22-CN1"])
        raw_data = {
            "hardware": {
                "cnodes": [
                    {"hostname": "RackCG.032.002.004-CB1-U6-CN3", "name": "cnode-128-11"},
                    {"hostname": "Rack-CB2-U8-CN1", "name": "cnode-128-12"},
                ],
                "dnodes": [{"hostname": "RackCG.032.002.004-DB3-U21-DN1", "name": "dnode-128-120"}],
            }
        }
        matches, reason = vnetmap_matches_cluster(vnetmap, raw_data)
        assert matches is False
        assert "does not match" in reason

    def test_accepts_matching_cluster_by_hostname(self):
        vnetmap = self._vnetmap(["Rack-CB2-U8-CN1", "RackCG.032.002.004-CB1-U6-CN3"])
        raw_data = {
            "hardware": {
                "cnodes": [
                    {"hostname": "RackCG.032.002.004-CB1-U6-CN3", "name": "cnode-128-11"},
                    {"hostname": "Rack-CB2-U8-CN1", "name": "cnode-128-12"},
                ],
                "dnodes": [],
            }
        }
        matches, _ = vnetmap_matches_cluster(vnetmap, raw_data)
        assert matches is True

    def test_accepts_matching_cluster_by_node_ip(self):
        vnetmap = self._vnetmap(["unknownhostA", "unknownhostB"], ips=["172.16.1.4", "172.16.1.6"])
        raw_data = {
            "hardware": {"cnodes": [{"hostname": "c-128-1"}], "dnodes": []},
            "cnodes_network": [{"ip": "172.16.1.4"}, {"ip": "172.16.1.9"}],
        }
        matches, _ = vnetmap_matches_cluster(vnetmap, raw_data)
        assert matches is True

    def test_accepts_when_identity_insufficient(self):
        """No comparable cluster tokens => accept (never drop a legit run)."""
        vnetmap = self._vnetmap(["RackP01C02-CB9-U25-CN1"])
        raw_data = {"hardware": {"cnodes": [], "dnodes": []}}
        matches, reason = vnetmap_matches_cluster(vnetmap, raw_data)
        assert matches is True
        assert "insufficient" in reason
