"""Tests for QP-2 per-cluster path segmentation (``src/utils/cluster_paths.py``).

Covers cluster-key resolution (PSNT -> GUID -> name -> IP fallback with the
``<name>__<id>`` readable form), filesystem-safe sanitization, the per-cluster
directory tree, the ``cluster.json`` marker round-trip, discovery enumeration,
and the ``segment_by_cluster`` config gate.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import cluster_paths as cp  # noqa: E402


# ---------------------------------------------------------------------------
# sanitize_component
# ---------------------------------------------------------------------------
class TestSanitizeComponent:
    def test_keeps_safe_chars(self):
        assert cp.sanitize_component("LAMBDA-VAST-LAX-01") == "LAMBDA-VAST-LAX-01"

    def test_replaces_unsafe_with_dash(self):
        assert cp.sanitize_component("foo/bar baz:qux") == "foo-bar-baz-qux"

    def test_collapses_runs_and_strips_edges(self):
        assert cp.sanitize_component("  **foo___bar**  ") == "foo___bar"

    def test_none_and_empty_become_empty(self):
        assert cp.sanitize_component(None) == ""
        assert cp.sanitize_component("") == ""
        assert cp.sanitize_component("///") == ""

    def test_truncates_to_max_len(self):
        out = cp.sanitize_component("a" * 200, max_len=32)
        assert len(out) == 32

    def test_no_path_traversal(self):
        out = cp.sanitize_component("../../etc/passwd")
        assert ".." not in out
        assert "/" not in out


# ---------------------------------------------------------------------------
# resolve_cluster_key
# ---------------------------------------------------------------------------
class TestResolveClusterKey:
    def test_name_plus_psnt(self):
        key = cp.resolve_cluster_key(name="LAMBDA-VAST-LAX-01", psnt="PSNT123", guid="0xabc")
        assert key == "LAMBDA-VAST-LAX-01__PSNT123"

    def test_prefers_psnt_over_guid(self):
        key = cp.resolve_cluster_key(name="c1", psnt="PSNT9", guid="0xdead")
        assert key == "c1__PSNT9"

    def test_falls_back_to_guid_when_no_psnt(self):
        key = cp.resolve_cluster_key(name="c1", guid="0xdeadbeef")
        assert key == "c1__0xdeadbeef"

    def test_name_only_when_no_id(self):
        assert cp.resolve_cluster_key(name="c1") == "c1"

    def test_id_only_when_no_name(self):
        assert cp.resolve_cluster_key(psnt="PSNT123") == "PSNT123"
        assert cp.resolve_cluster_key(guid="0xabc") == "0xabc"

    def test_ip_fallback_when_no_name_or_id(self):
        # IP is the last resort; dots are filesystem-safe and preserved
        key = cp.resolve_cluster_key(cluster_ip="192.168.2.2")
        assert key == "192.168.2.2"

    def test_unknown_when_nothing(self):
        assert cp.resolve_cluster_key() == "unknown-cluster"

    def test_ip_not_used_when_identity_present(self):
        key = cp.resolve_cluster_key(name="c1", psnt="P1", cluster_ip="192.168.2.2")
        assert "192.168" not in key
        assert key == "c1__P1"

    def test_sanitizes_messy_name(self):
        key = cp.resolve_cluster_key(name="My Cluster/A", psnt="P 1")
        assert "/" not in key and " " not in key
        assert key == "My-Cluster-A__P-1"


# ---------------------------------------------------------------------------
# resolve_cluster_key_from_summary
# ---------------------------------------------------------------------------
class TestResolveFromSummary:
    def test_reads_cluster_summary_dict(self):
        summary = {"name": "lax01", "psnt": "PSNT5", "guid": "0xabc"}
        assert cp.resolve_cluster_key_from_summary(summary) == "lax01__PSNT5"

    def test_handles_nested_cluster_summary(self):
        data = {"cluster_summary": {"name": "lax01", "guid": "0xabc"}, "cluster_ip": "192.168.2.2"}
        # accepts the top-level processed-report dict and digs into cluster_summary
        assert cp.resolve_cluster_key_from_summary(data) == "lax01__0xabc"

    def test_uses_top_level_cluster_ip_fallback(self):
        data = {"cluster_summary": {}, "cluster_ip": "10.0.0.5"}
        assert cp.resolve_cluster_key_from_summary(data) == "10.0.0.5"

    def test_empty_dict_is_unknown(self):
        assert cp.resolve_cluster_key_from_summary({}) == "unknown-cluster"

    def test_none_is_unknown(self):
        assert cp.resolve_cluster_key_from_summary(None) == "unknown-cluster"


# ---------------------------------------------------------------------------
# ClusterPaths tree
# ---------------------------------------------------------------------------
class TestClusterPaths:
    def test_root_under_clusters_dir(self, tmp_path):
        paths = cp.cluster_paths(tmp_path, "c1__P1")
        assert paths.root == tmp_path / "clusters" / "c1__P1"

    def test_category_dirs_mirror_legacy_layout(self, tmp_path):
        paths = cp.cluster_paths(tmp_path, "c1")
        root = tmp_path / "clusters" / "c1"
        assert paths.reports == root / "reports"
        assert paths.scripts == root / "output" / "scripts"
        assert paths.network_configs == root / "output" / "scripts" / "network_configs"
        assert paths.switch_configs == root / "output" / "scripts" / "switch_configs"
        assert paths.health == root / "output" / "health"
        assert paths.diagrams == root / "output" / "diagrams"
        assert paths.bundles == root / "output" / "bundles"
        assert paths.ops_logs == root / "logs" / "operations"

    def test_ensure_creates_dirs(self, tmp_path):
        paths = cp.cluster_paths(tmp_path, "c1")
        created = paths.ensure("reports", "health")
        assert paths.reports.is_dir()
        assert paths.health.is_dir()
        # unrequested dirs are not created
        assert not paths.bundles.exists()
        assert paths.reports in created

    def test_ensure_all(self, tmp_path):
        paths = cp.cluster_paths(tmp_path, "c1")
        paths.ensure_all()
        for d in (paths.reports, paths.scripts, paths.health, paths.diagrams, paths.bundles, paths.ops_logs):
            assert d.is_dir()


# ---------------------------------------------------------------------------
# cluster.json marker
# ---------------------------------------------------------------------------
class TestClusterMarker:
    def test_write_and_read_round_trip(self, tmp_path):
        root = tmp_path / "clusters" / "c1"
        root.mkdir(parents=True)
        identity = {"name": "lax01", "psnt": "P1", "guid": "0xabc", "cluster_ip": "192.168.2.2"}
        marker = cp.write_cluster_marker(root, identity)
        assert marker == root / cp.CLUSTER_MARKER
        loaded = cp.read_cluster_marker(root)
        assert loaded["name"] == "lax01"
        assert loaded["psnt"] == "P1"
        assert "first_seen" in loaded and "last_seen" in loaded

    def test_first_seen_preserved_on_update(self, tmp_path):
        root = tmp_path / "clusters" / "c1"
        root.mkdir(parents=True)
        cp.write_cluster_marker(root, {"name": "lax01"})
        first = cp.read_cluster_marker(root)["first_seen"]
        cp.write_cluster_marker(root, {"name": "lax01", "version": "5.1"})
        updated = cp.read_cluster_marker(root)
        assert updated["first_seen"] == first
        assert updated["version"] == "5.1"

    def test_read_missing_marker_returns_empty(self, tmp_path):
        assert cp.read_cluster_marker(tmp_path / "nope") == {}

    def test_read_corrupt_marker_returns_empty(self, tmp_path):
        root = tmp_path / "clusters" / "c1"
        root.mkdir(parents=True)
        (root / cp.CLUSTER_MARKER).write_text("{not json")
        assert cp.read_cluster_marker(root) == {}


# ---------------------------------------------------------------------------
# discovery enumeration
# ---------------------------------------------------------------------------
class TestIterClusterRoots:
    def test_lists_only_cluster_subdirs(self, tmp_path):
        (tmp_path / "clusters" / "c1").mkdir(parents=True)
        (tmp_path / "clusters" / "c2").mkdir(parents=True)
        (tmp_path / "reports").mkdir()  # legacy flat dir — must be ignored
        roots = cp.iter_cluster_roots(tmp_path)
        names = sorted(r.name for r in roots)
        assert names == ["c1", "c2"]

    def test_empty_when_no_clusters_dir(self, tmp_path):
        assert cp.iter_cluster_roots(tmp_path) == []

    def test_ignores_files_in_clusters_dir(self, tmp_path):
        (tmp_path / "clusters").mkdir()
        (tmp_path / "clusters" / "stray.txt").write_text("x")
        assert cp.iter_cluster_roots(tmp_path) == []


# ---------------------------------------------------------------------------
# segment_enabled config gate
# ---------------------------------------------------------------------------
class TestSegmentEnabled:
    def test_default_true_when_missing(self):
        assert cp.segment_enabled(None) is True
        assert cp.segment_enabled({}) is True

    def test_reads_dict_config(self):
        assert cp.segment_enabled({"output": {"segment_by_cluster": False}}) is False
        assert cp.segment_enabled({"output": {"segment_by_cluster": True}}) is True

    def test_reads_object_config(self):
        class Out:
            segment_by_cluster = False

        class Cfg:
            output = Out()

        assert cp.segment_enabled(Cfg()) is False

    def test_tolerates_missing_output_attr(self):
        class Cfg:
            pass

        assert cp.segment_enabled(Cfg()) is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
