"""
QP-2 read/discovery tests: per-cluster result segmentation by identity.

Verifies that ResultScanner and ResultBundler discover artifacts under the
per-cluster directory tree (``<data_dir>/clusters/<key>/...``) AND the legacy
flat tree, associate per-cluster files to the folder's ``cluster.json``
IDENTITY (psnt/guid/name/key) rather than to the shared tech-port IP, and keep
pure-legacy installs unchanged.

The core regression these tests guard (QP-2 "Blocker 2"): in tech-port mode
EVERY cluster's ``cluster.json`` marker stores the same management IP
(``192.168.2.2``). Association/de-dup must therefore key on the folder identity,
NOT on ``cluster_ip`` — otherwise two distinct per-cluster folders re-collapse
into one cluster on read and their files intermingle.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from result_bundler import ResultBundler
from result_scanner import ResultScanner
from utils.cluster_paths import cluster_paths, write_cluster_marker

# Real per-cluster management IPs (used by the single-folder / legacy cases).
CLUSTER_A = "10.143.11.202"
CLUSTER_B = "10.141.200.217"
# Shared tech-port management IP that EVERY cluster marker carries in the field.
TECH_PORT_IP = "192.168.2.2"


@pytest.fixture(autouse=True)
def _isolate_data_dir(tmp_path, monkeypatch):
    """Force ``utils.get_data_dir`` to ``tmp_path`` so no real ``clusters/``
    directory is ever created in the repository."""
    import utils

    monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cluster_tree(
    data_dir: Path,
    key: str,
    marker_ip: str,
    name: str,
    ts: str,
    psnt: str = None,
) -> "cluster_paths":
    """Create a per-cluster tree whose files embed the tech-port IP.

    ``marker_ip`` is what the ``cluster.json`` marker records as ``cluster_ip``.
    Pass ``TECH_PORT_IP`` to reproduce live tech-port writers (where every
    marker shares the same IP); pass a real IP for single-folder display tests.
    """
    cp = cluster_paths(data_dir, key)
    cp.ensure_all()
    write_cluster_marker(cp.root, {"name": name, "cluster_ip": marker_ip, "psnt": psnt or key})

    # As-Built JSON/PDF — JSON embeds the tech-port IP, not the marker IP.
    (cp.reports / f"vast_data_{name}_{ts}.json").write_text(
        json.dumps({"cluster_ip": TECH_PORT_IP, "cluster_summary": {"name": name}})
    )
    (cp.reports / f"vast_asbuilt_report_{name}_{ts}.pdf").write_bytes(b"%PDF-fake")

    # Health check — embeds the tech-port IP.
    (cp.health / f"health_check_{name}_{ts}.json").write_text(json.dumps({"cluster_ip": TECH_PORT_IP, "results": []}))

    # Network config.
    (cp.network_configs / f"network_summary_cn1_{ts}.json").write_text(json.dumps({"cluster_ip": TECH_PORT_IP}))

    # vnetmap / vperfsanity under scripts — filenames carry the tech-port IP.
    (cp.scripts / f"vnetmap_results_{TECH_PORT_IP}_{ts}.json").write_text(
        json.dumps({"cluster_ip": TECH_PORT_IP, "timestamp": ts})
    )
    (cp.scripts / f"vperfsanity_results_{TECH_PORT_IP}_{ts}.txt").write_text("perf data")
    return cp


def _make_legacy_tree(data_dir: Path) -> None:
    (data_dir / "reports").mkdir(parents=True, exist_ok=True)
    (data_dir / "output" / "health").mkdir(parents=True, exist_ok=True)
    (data_dir / "output" / "scripts" / "network_configs").mkdir(parents=True, exist_ok=True)
    (data_dir / "output" / "scripts" / "switch_configs").mkdir(parents=True, exist_ok=True)
    (data_dir / "output" / "bundles").mkdir(parents=True, exist_ok=True)


# ===================================================================
# Scanner — per-cluster discovery + association
# ===================================================================


class TestScannerSegmentedDiscovery:
    def test_per_cluster_files_associated_to_marker_identity(self, tmp_path):
        """Files under a per-cluster root use the marker's cluster_ip (display)
        and the folder key (identity), not the tech-port IP embedded in the
        files themselves."""
        _make_cluster_tree(tmp_path, "alpha__PSNTAAA", CLUSTER_A, "alpha", "20260301_120000")

        scanner = ResultScanner(data_dir=tmp_path)
        results = scanner.scan_all()

        all_ips = {e["cluster_ip"] for entries in results.values() for e in entries}
        all_keys = {e["cluster_key"] for entries in results.values() for e in entries}
        assert CLUSTER_A in all_ips
        assert TECH_PORT_IP not in all_ips
        assert all_keys == {"alpha__PSNTAAA"}

    def test_legacy_flat_files_still_discovered(self, tmp_path):
        _make_legacy_tree(tmp_path)
        (tmp_path / "reports" / "vast_data_legacy_20260101_120000.json").write_text(
            json.dumps({"cluster_ip": CLUSTER_B, "cluster_summary": {"name": "legacy"}})
        )
        # Also add a segmented cluster to prove union behaviour.
        _make_cluster_tree(tmp_path, "alpha__PSNTAAA", CLUSTER_A, "alpha", "20260301_120000")

        scanner = ResultScanner(data_dir=tmp_path)
        results = scanner.scan_all()

        all_ips = {e["cluster_ip"] for entries in results.values() for e in entries}
        assert CLUSTER_A in all_ips  # segmented
        assert CLUSTER_B in all_ips  # legacy flat

    def test_two_clusters_shared_tech_port_ip_kept_separate(self, tmp_path):
        """REGRESSION (QP-2 Blocker 2): two clusters whose markers BOTH store
        the shared tech-port IP must stay as two distinct clusters on read,
        identified by their folder key — never collapsed by cluster_ip."""
        _make_cluster_tree(tmp_path, "lax01__P1", TECH_PORT_IP, "lax01", "20260301_120000", psnt="P1")
        _make_cluster_tree(tmp_path, "nyc02__P2", TECH_PORT_IP, "nyc02", "20260202_100000", psnt="P2")

        scanner = ResultScanner(data_dir=tmp_path)
        results = scanner.scan_all()

        # Every file still carries the (shared) tech-port IP for display...
        all_ips = {e["cluster_ip"] for entries in results.values() for e in entries}
        assert all_ips == {TECH_PORT_IP}

        # ...but identity stays folder-unique, so files never cross folders.
        for entries in results.values():
            for e in entries:
                assert e["cluster_key"] in e["path"]
        all_keys = {e["cluster_key"] for entries in results.values() for e in entries}
        assert all_keys == {"lax01__P1", "nyc02__P2"}

        # vperfsanity: exactly one per cluster, attributed to its own folder.
        perf = results["vperfsanity"]
        assert len(perf) == 2
        assert {e["cluster_key"] for e in perf} == {"lax01__P1", "nyc02__P2"}

    def test_get_known_clusters_shared_ip_lists_two_clusters(self, tmp_path):
        """get_known_clusters de-dups by folder identity, so two tech-port
        folders that share the IP surface as TWO clusters, not one."""
        _make_cluster_tree(tmp_path, "lax01__P1", TECH_PORT_IP, "lax01", "20260301_120000", psnt="P1")
        _make_cluster_tree(tmp_path, "nyc02__P2", TECH_PORT_IP, "nyc02", "20260202_100000", psnt="P2")

        scanner = ResultScanner(data_dir=tmp_path)
        clusters = scanner.get_known_clusters()

        keys = {c["cluster_key"] for c in clusters}
        assert keys == {"lax01__P1", "nyc02__P2"}
        # Both legitimately share the tech-port IP for display.
        assert all(c["cluster_ip"] == TECH_PORT_IP for c in clusters)
        assert len(clusters) == 2

    def test_get_known_clusters_surfaces_real_identity(self, tmp_path):
        _make_cluster_tree(tmp_path, "alpha__PSNTAAA", CLUSTER_A, "alpha", "20260301_120000")
        scanner = ResultScanner(data_dir=tmp_path)
        clusters = scanner.get_known_clusters()
        ips = {c["cluster_ip"] for c in clusters}
        assert CLUSTER_A in ips
        assert TECH_PORT_IP not in ips

    def test_no_clusters_dir_is_pure_legacy(self, tmp_path):
        """Without a clusters/ dir the scanner behaves exactly as before."""
        _make_legacy_tree(tmp_path)
        (tmp_path / "reports" / "vast_data_legacy_20260101_120000.json").write_text(
            json.dumps({"cluster_ip": CLUSTER_B, "cluster_summary": {"name": "legacy"}})
        )
        scanner = ResultScanner(data_dir=tmp_path)
        results = scanner.scan_all()
        all_ips = {e["cluster_ip"] for entries in results.values() for e in entries}
        assert all_ips == {CLUSTER_B}

    def test_resolve_file_path_finds_segmented_file(self, tmp_path):
        cp = _make_cluster_tree(tmp_path, "alpha__PSNTAAA", CLUSTER_A, "alpha", "20260301_120000")
        scanner = ResultScanner(data_dir=tmp_path)
        path = scanner.resolve_file_path("health_checks", "health_check_alpha_20260301_120000.json")
        assert path is not None
        assert path.exists()
        assert str(path).startswith(str(cp.health))


# ===================================================================
# Bundler — segmentation-aware collection
# ===================================================================


class TestBundlerSegmentedCollection:
    def test_shared_ip_bundle_resolves_by_identity_not_ip(self, tmp_path):
        """REGRESSION (QP-2 Blocker 2): collect_results must resolve the folder
        by the requested cluster's IDENTITY (its name in metadata), not by the
        shared tech-port IP — otherwise cluster lax01 grabs nyc02's files."""
        _make_legacy_tree(tmp_path)
        _make_cluster_tree(tmp_path, "lax01__P1", TECH_PORT_IP, "lax01", "20260301_120000", psnt="P1")
        _make_cluster_tree(tmp_path, "nyc02__P2", TECH_PORT_IP, "nyc02", "20260202_100000", psnt="P2")

        # Bundle for lax01: identity is the cluster NAME; IP is the shared port.
        bundler_a = ResultBundler(output_dir=tmp_path / "bundles")
        bundler_a.set_metadata("lax01", TECH_PORT_IP, "5.3.0")
        collected_a = bundler_a.collect_results(results_dir=tmp_path / "output", cluster_ip=TECH_PORT_IP)
        assert "vnetmap" in collected_a
        assert "vperfsanity" in collected_a
        for path in collected_a.values():
            assert "lax01__P1" in str(path)
            assert "nyc02" not in str(path)

        # Bundle for nyc02: must pull ONLY nyc02's files (no intermingling).
        bundler_b = ResultBundler(output_dir=tmp_path / "bundles")
        bundler_b.set_metadata("nyc02", TECH_PORT_IP, "5.3.0")
        collected_b = bundler_b.collect_results(results_dir=tmp_path / "output", cluster_ip=TECH_PORT_IP)
        assert "vperfsanity" in collected_b
        for path in collected_b.values():
            assert "nyc02__P2" in str(path)
            assert "lax01" not in str(path)

    def test_prefers_matching_cluster_folder_by_real_ip(self, tmp_path):
        """When folders carry distinct real management IPs, a unique IP match
        still resolves the correct folder even without a name hint."""
        _make_legacy_tree(tmp_path)
        _make_cluster_tree(tmp_path, "alpha__PSNTAAA", CLUSTER_A, "alpha", "20260301_120000")
        _make_cluster_tree(tmp_path, "bravo__PSNTBBB", CLUSTER_B, "bravo", "20260202_100000")

        bundler = ResultBundler(output_dir=tmp_path / "bundles")
        collected = bundler.collect_results(results_dir=tmp_path / "output", cluster_ip=CLUSTER_A)

        assert "vnetmap" in collected
        assert "vperfsanity" in collected
        for path in collected.values():
            assert "bravo" not in str(path)
            assert "alpha__PSNTAAA" in str(path)

    def test_falls_back_to_legacy_when_no_folder_matches(self, tmp_path):
        """When no per-cluster folder matches, legacy flat matching is used
        (latest-by-IP across the flat dir)."""
        _make_legacy_tree(tmp_path)
        scripts = tmp_path / "output" / "scripts"
        (scripts / f"vperfsanity_results_{CLUSTER_A}_20260101_120000.txt").write_text("legacy perf")

        bundler = ResultBundler(output_dir=tmp_path / "bundles")
        collected = bundler.collect_results(results_dir=tmp_path / "output", cluster_ip=CLUSTER_A)

        assert "vperfsanity" in collected
        assert CLUSTER_A in collected["vperfsanity"].name

    def test_no_clusters_dir_unchanged(self, tmp_path):
        """Pure-legacy install: behaviour identical to pre-QP-2."""
        _make_legacy_tree(tmp_path)
        net = tmp_path / "output" / "scripts" / "network_configs"
        (net / "network_summary_cn1_20260101_120000.json").write_text(json.dumps({"cluster_ip": CLUSTER_A}))

        bundler = ResultBundler(output_dir=tmp_path / "bundles")
        collected = bundler.collect_results(results_dir=tmp_path / "output", cluster_ip=CLUSTER_A)
        assert "network_config" in collected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
