"""
Unit tests for Result Scanner module.

Tests the shared helper functions (json_cluster_ip, filename_ip, etc.)
and the ResultScanner class (scan_all, get_known_clusters, resolve_file_path).
"""

import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from result_scanner import (
    OPERATION_KEYS,
    ResultScanner,
    bundle_manifest_ip,
    extract_timestamp,
    filename_ip,
    filename_matches,
    json_cluster_ip,
    json_matches_cluster,
    sidecar_cluster_ip,
    verification_cluster_ip,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLUSTER_A = "10.143.11.202"
CLUSTER_B = "10.141.200.217"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def data_dir(tmp_path):
    """Create the full output directory tree expected by ResultScanner."""
    (tmp_path / "reports").mkdir()
    (tmp_path / "output" / "health").mkdir(parents=True)
    (tmp_path / "output" / "scripts" / "network_configs").mkdir(parents=True)
    (tmp_path / "output" / "scripts" / "switch_configs").mkdir(parents=True)
    (tmp_path / "output" / "bundles").mkdir(parents=True)
    return tmp_path


@pytest.fixture
def populated_data_dir(data_dir):
    """Populate data_dir with mock files for two clusters."""
    # As-built reports (cluster A via JSON content)
    (data_dir / "reports" / "vast_data_mycluster_20260301_120000.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_A, "data": {}})
    )
    (data_dir / "reports" / "vast_asbuilt_report_mycluster_20260301_120000.pdf").write_bytes(b"%PDF-fake")

    # Health checks
    health = data_dir / "output" / "health"
    (health / "health_check_cluster_20260301_120000.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_A, "results": []})
    )
    (health / "health_remediation_20260301_120000.txt").write_text(f"# Cluster: ({CLUSTER_A})\nRemediation steps\n")

    # Network config
    net = data_dir / "output" / "scripts" / "network_configs"
    (net / "network_summary_cn1_20260301_120000.json").write_text(json.dumps({"cluster_ip": CLUSTER_A}))
    (net / "configure_network_commands_all_20260301_120000.txt").write_text(f"# Cluster ({CLUSTER_A})\ndata\n")

    # Switch config
    sw = data_dir / "output" / "scripts" / "switch_configs"
    (sw / "switch_configs_20260301_120000.json").write_text(json.dumps({"cluster_ip": CLUSTER_A, "switches": {}}))
    (sw / "switch_sw1_10_143_11_202_20260301_120000.txt").write_text(f"# Cluster: {CLUSTER_A}\ndata\n")

    # vnetmap (cluster A)
    scripts = data_dir / "output" / "scripts"
    (scripts / f"vnetmap_results_{CLUSTER_A}_20260301_120000.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_A, "timestamp": "20260301_120000"})
    )
    (scripts / f"vnetmap_output_{CLUSTER_A}_20260301_120000.txt").write_text("topology data A")

    # vperfsanity (cluster A and B)
    (scripts / f"vperfsanity_results_{CLUSTER_A}_20260301_120000.txt").write_text("perf A")
    (scripts / f"vperfsanity_results_{CLUSTER_B}_20260201_100000.txt").write_text("perf B")

    # Support tool (cluster B with sidecar)
    tgz = scripts / "20260201_100000_support_tool_logs.tgz"
    tgz.write_bytes(b"\x1f\x8b fake tgz")
    (scripts / f"{tgz.name}.meta.json").write_text(json.dumps({"cluster_ip": CLUSTER_B}))

    # Log bundle (cluster B with verification sidecar)
    log_bundle = scripts / "vast_log_bundle_20260201_100000.tar.gz"
    log_bundle.write_bytes(b"\x1f\x8b fake tar")
    (scripts / "vast_log_bundle_20260201_100000.tar.verification.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_B})
    )

    # ZIP bundle (cluster A with manifest)
    bundle_zip = data_dir / "output" / "bundles" / "validation_bundle_20260301_120000.zip"
    with zipfile.ZipFile(bundle_zip, "w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps({"metadata": {"cluster_ip": CLUSTER_A, "cluster_name": "mycluster"}, "files": []}),
        )

    return data_dir


# ===================================================================
# Helper: json_cluster_ip
# ===================================================================


class TestJsonClusterIp:
    def test_valid_json_with_cluster_ip(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert json_cluster_ip(f) == "10.0.0.1"

    def test_missing_field(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"other_key": "value"}))
        assert json_cluster_ip(f) is None

    def test_invalid_json(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text("not valid json {{{")
        assert json_cluster_ip(f) is None

    def test_empty_cluster_ip(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"cluster_ip": ""}))
        assert json_cluster_ip(f) is None

    def test_whitespace_only_cluster_ip(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"cluster_ip": "   "}))
        assert json_cluster_ip(f) is None

    def test_nonexistent_file(self, tmp_path):
        assert json_cluster_ip(tmp_path / "missing.json") is None

    def test_non_string_cluster_ip(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"cluster_ip": 12345}))
        assert json_cluster_ip(f) is None


# ===================================================================
# Helper: json_matches_cluster
# ===================================================================


class TestJsonMatchesCluster:
    def test_matching(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert json_matches_cluster(f, "10.0.0.1") is True

    def test_non_matching(self, tmp_path):
        f = tmp_path / "data.json"
        f.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert json_matches_cluster(f, "10.0.0.2") is False


# ===================================================================
# Helper: filename_ip
# ===================================================================


class TestFilenameIp:
    def test_ip_with_dots(self, tmp_path):
        f = tmp_path / "vnetmap_results_10.143.11.202_20260101.json"
        assert filename_ip(f) == "10.143.11.202"

    def test_ip_with_underscores(self, tmp_path):
        f = tmp_path / "switch_10_143_11_202_20260101.txt"
        assert filename_ip(f) == "10.143.11.202"

    def test_no_ip(self, tmp_path):
        f = tmp_path / "some_file_without_ip.txt"
        assert filename_ip(f) is None


# ===================================================================
# Helper: filename_matches
# ===================================================================


class TestFilenameMatches:
    def test_match_with_dots(self, tmp_path):
        f = tmp_path / f"vnetmap_{CLUSTER_A}_20260101.json"
        assert filename_matches(f, CLUSTER_A) is True

    def test_match_with_underscores(self, tmp_path):
        f = tmp_path / f"switch_{CLUSTER_A.replace('.', '_')}_20260101.txt"
        assert filename_matches(f, CLUSTER_A) is True

    def test_non_matching(self, tmp_path):
        f = tmp_path / f"vnetmap_{CLUSTER_A}_20260101.json"
        assert filename_matches(f, CLUSTER_B) is False


# ===================================================================
# Helper: sidecar_cluster_ip
# ===================================================================


class TestSidecarClusterIp:
    def test_with_meta_json(self, tmp_path):
        archive = tmp_path / "logs.tgz"
        archive.write_bytes(b"fake")
        meta = tmp_path / "logs.tgz.meta.json"
        meta.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert sidecar_cluster_ip(archive) == "10.0.0.1"

    def test_without_meta(self, tmp_path):
        archive = tmp_path / "logs.tgz"
        archive.write_bytes(b"fake")
        assert sidecar_cluster_ip(archive) is None

    def test_invalid_meta(self, tmp_path):
        archive = tmp_path / "logs.tgz"
        archive.write_bytes(b"fake")
        meta = tmp_path / "logs.tgz.meta.json"
        meta.write_text("not json!")
        assert sidecar_cluster_ip(archive) is None

    def test_meta_missing_cluster_ip(self, tmp_path):
        archive = tmp_path / "logs.tgz"
        archive.write_bytes(b"fake")
        meta = tmp_path / "logs.tgz.meta.json"
        meta.write_text(json.dumps({"other": "data"}))
        assert sidecar_cluster_ip(archive) is None


# ===================================================================
# Helper: verification_cluster_ip
# ===================================================================


class TestVerificationClusterIp:
    def test_with_verification_json(self, tmp_path):
        archive = tmp_path / "health_check.zip"
        archive.write_bytes(b"fake")
        verify = tmp_path / "health_check.verification.json"
        verify.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert verification_cluster_ip(archive) == "10.0.0.1"

    def test_without_verification(self, tmp_path):
        archive = tmp_path / "health_check.zip"
        archive.write_bytes(b"fake")
        assert verification_cluster_ip(archive) is None

    def test_tar_gz_verification(self, tmp_path):
        archive = tmp_path / "vast_log_bundle.tar.gz"
        archive.write_bytes(b"fake")
        verify = tmp_path / "vast_log_bundle.tar.verification.json"
        verify.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert verification_cluster_ip(archive) == "10.0.0.1"

    def test_invalid_verification_json(self, tmp_path):
        archive = tmp_path / "health_check.zip"
        archive.write_bytes(b"fake")
        verify = tmp_path / "health_check.verification.json"
        verify.write_text("broken json")
        assert verification_cluster_ip(archive) is None


# ===================================================================
# Helper: extract_timestamp
# ===================================================================


class TestExtractTimestamp:
    def test_valid_timestamp(self):
        assert extract_timestamp("network_summary_cn1_20260301_120000.json") == "20260301_120000"

    def test_no_timestamp(self):
        assert extract_timestamp("readme.txt") is None

    def test_multiple_timestamps_returns_first(self):
        assert extract_timestamp("file_20260101_120000_extra_20260202_130000.txt") == "20260101_120000"


# ===================================================================
# Helper: bundle_manifest_ip
# ===================================================================


class TestBundleManifestIp:
    def test_valid_zip_with_manifest(self, tmp_path):
        zp = tmp_path / "bundle.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr(
                "manifest.json",
                json.dumps({"metadata": {"cluster_ip": "10.0.0.1"}, "files": []}),
            )
        assert bundle_manifest_ip(zp) == "10.0.0.1"

    def test_zip_without_manifest(self, tmp_path):
        zp = tmp_path / "bundle.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("data.txt", "hello")
        assert bundle_manifest_ip(zp) is None

    def test_not_a_zip(self, tmp_path):
        f = tmp_path / "fake.zip"
        f.write_bytes(b"not a zip")
        assert bundle_manifest_ip(f) is None

    def test_manifest_missing_metadata(self, tmp_path):
        zp = tmp_path / "bundle.zip"
        with zipfile.ZipFile(zp, "w") as zf:
            zf.writestr("manifest.json", json.dumps({"files": []}))
        assert bundle_manifest_ip(zp) is None


# ===================================================================
# ResultScanner.scan_all
# ===================================================================


class TestScanAll:
    def test_returns_all_operation_keys(self, data_dir):
        scanner = ResultScanner(data_dir=data_dir)
        results = scanner.scan_all()
        assert set(results.keys()) == set(OPERATION_KEYS)

    def test_empty_directories_return_empty_lists(self, data_dir):
        scanner = ResultScanner(data_dir=data_dir)
        results = scanner.scan_all()
        for key in OPERATION_KEYS:
            assert results[key] == []

    def test_scan_finds_all_files(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        results = scanner.scan_all()

        assert len(results["health_checks"]) >= 1
        assert len(results["network_config"]) >= 1
        assert len(results["switch_config"]) >= 1
        assert len(results["vnetmap"]) >= 1
        assert len(results["vperfsanity"]) == 2
        assert len(results["support_tools"]) == 1
        assert len(results["log_bundles"]) == 1
        assert len(results["bundles"]) == 1

    def test_filter_by_cluster_ip(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        results = scanner.scan_all(cluster_ip=CLUSTER_A)

        for entry in results["vperfsanity"]:
            assert entry["cluster_ip"] == CLUSTER_A
        assert len(results["vperfsanity"]) == 1

        assert len(results["support_tools"]) == 0
        assert len(results["log_bundles"]) == 0

    def test_filter_cluster_b(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        results = scanner.scan_all(cluster_ip=CLUSTER_B)

        assert len(results["support_tools"]) == 1
        assert results["support_tools"][0]["cluster_ip"] == CLUSTER_B
        assert len(results["log_bundles"]) == 1
        assert len(results["vperfsanity"]) == 1

    def test_nonexistent_cluster_returns_empty(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        results = scanner.scan_all(cluster_ip="192.168.99.99")
        total = sum(len(v) for v in results.values())
        assert total == 0

    def test_entries_contain_required_fields(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        results = scanner.scan_all()
        for entries in results.values():
            for entry in entries:
                assert "filename" in entry
                assert "path" in entry
                assert "size" in entry
                assert "modified" in entry
                assert "cluster_ip" in entry
                assert "file_type" in entry
                assert "operation" in entry

    def test_results_sorted_newest_first(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        results = scanner.scan_all()
        for entries in results.values():
            if len(entries) > 1:
                for i in range(len(entries) - 1):
                    assert entries[i]["modified"] >= entries[i + 1]["modified"]

    def test_nonexistent_data_dir(self, tmp_path):
        scanner = ResultScanner(data_dir=tmp_path / "nonexistent")
        results = scanner.scan_all()
        total = sum(len(v) for v in results.values())
        assert total == 0

    def test_asbuilt_report_profile_lookup(self, data_dir):
        """As-built PDF resolves cluster_ip via profile name mapping."""
        profiles = {"mycluster": {"cluster_ip": CLUSTER_A}}
        (data_dir / "reports" / "vast_asbuilt_report_mycluster_20260301_120000.pdf").write_bytes(b"%PDF")
        scanner = ResultScanner(data_dir=data_dir, profiles=profiles)
        results = scanner.scan_all()
        assert len(results["asbuilt_reports"]) == 1
        assert results["asbuilt_reports"][0]["cluster_ip"] == CLUSTER_A

    def test_asbuilt_pdf_resolves_via_sidecar_meta(self, data_dir):
        """PDF with sidecar .meta.json resolves cluster_ip even without profile match."""
        (data_dir / "reports" / "vast_asbuilt_report_apiname_20260301_120000.pdf").write_bytes(b"%PDF")
        meta = {"cluster_ip": CLUSTER_B, "cluster_name": "apiname", "timestamp": "20260301_120000"}
        (data_dir / "reports" / "vast_asbuilt_report_apiname_20260301_120000.meta.json").write_text(json.dumps(meta))
        scanner = ResultScanner(data_dir=data_dir)
        results = scanner.scan_all()
        pdf_entries = [e for e in results["asbuilt_reports"] if e["filename"].endswith(".pdf")]
        assert len(pdf_entries) == 1
        assert pdf_entries[0]["cluster_ip"] == CLUSTER_B

    def test_asbuilt_json_with_cluster_ip_field(self, data_dir):
        """JSON with top-level cluster_ip resolves correctly."""
        (data_dir / "reports" / "vast_data_apicluster_20260301_120000.json").write_text(
            json.dumps({"cluster_ip": CLUSTER_A, "cluster_summary": {"name": "apicluster"}})
        )
        scanner = ResultScanner(data_dir=data_dir)
        results = scanner.scan_all()
        assert len(results["asbuilt_reports"]) == 1
        assert results["asbuilt_reports"][0]["cluster_ip"] == CLUSTER_A

    def test_asbuilt_pdf_resolves_via_api_name_from_json(self, data_dir):
        """PDF resolves cluster_ip via API cluster name learned from existing JSON."""
        (data_dir / "reports" / "vast_data_vast-cluster-1_20260301_120000.json").write_text(
            json.dumps({"cluster_ip": CLUSTER_A, "cluster_summary": {"name": "vast-cluster-1"}})
        )
        (data_dir / "reports" / "vast_asbuilt_report_vast-cluster-1_20260301_120000.pdf").write_bytes(b"%PDF")
        scanner = ResultScanner(data_dir=data_dir)
        results = scanner.scan_all()
        pdf_entries = [e for e in results["asbuilt_reports"] if e["filename"].endswith(".pdf")]
        assert len(pdf_entries) == 1
        assert pdf_entries[0]["cluster_ip"] == CLUSTER_A


# ===================================================================
# ResultScanner.get_known_clusters
# ===================================================================


class TestGetKnownClusters:
    def test_returns_unique_ips_with_counts(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        clusters = scanner.get_known_clusters()

        ips = {c["cluster_ip"] for c in clusters}
        assert CLUSTER_A in ips
        assert CLUSTER_B in ips

        for c in clusters:
            assert "counts" in c
            assert c["counts"]["total"] > 0

    def test_empty_dirs_return_no_clusters(self, data_dir):
        scanner = ResultScanner(data_dir=data_dir)
        clusters = scanner.get_known_clusters()
        assert clusters == []

    def test_profile_name_included(self, populated_data_dir):
        profiles = {"my-cluster-a": {"cluster_ip": CLUSTER_A}}
        scanner = ResultScanner(data_dir=populated_data_dir, profiles=profiles)
        clusters = scanner.get_known_clusters()
        a_entry = next(c for c in clusters if c["cluster_ip"] == CLUSTER_A)
        assert a_entry["profile_name"] == "my-cluster-a"

    def test_no_profile_returns_empty_name(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        clusters = scanner.get_known_clusters()
        for c in clusters:
            assert isinstance(c["profile_name"], str)


# ===================================================================
# ResultScanner.resolve_file_path
# ===================================================================


class TestResolveFilePath:
    def test_resolves_valid_file(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        path = scanner.resolve_file_path("health_checks", "health_check_cluster_20260301_120000.json")
        assert path is not None
        assert path.exists()

    def test_returns_none_for_missing_file(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        path = scanner.resolve_file_path("health_checks", "does_not_exist.json")
        assert path is None

    def test_path_traversal_blocked(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        path = scanner.resolve_file_path("health_checks", "../../../etc/passwd")
        assert path is None

    def test_unknown_operation_returns_none(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        path = scanner.resolve_file_path("nonexistent_op", "somefile.txt")
        assert path is None

    def test_resolves_bundle_zip(self, populated_data_dir):
        scanner = ResultScanner(data_dir=populated_data_dir)
        path = scanner.resolve_file_path("bundles", "validation_bundle_20260301_120000.zip")
        assert path is not None
        assert path.suffix == ".zip"
