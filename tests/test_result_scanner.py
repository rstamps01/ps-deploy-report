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
from utils.cluster_paths import cluster_paths, write_cluster_marker

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLUSTER_A = "10.143.11.202"
CLUSTER_B = "10.141.200.217"
TECH_PORT_IP = "192.168.2.2"
VMS_HTTPS_IP = "192.0.2.10"
KEY_A = "ACME-A__PSNT0001"
KEY_B = "ACME-B__PSNT0002"
# Public API value of the "Unassigned (legacy)" filter choice.
UNASSIGNED = "__unassigned__"


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


def _write_bundle(path: Path, cluster_ip: str, cluster_name: str) -> None:
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr(
            "manifest.json",
            json.dumps({"metadata": {"cluster_ip": cluster_ip, "cluster_name": cluster_name}, "files": []}),
        )


def _make_cluster_folder(data_dir: Path, key: str, name: str, marker_ip: str, ts: str) -> None:
    """Create a per-cluster folder holding one artifact of each listed kind."""
    cp = cluster_paths(data_dir, key)
    cp.ensure_all()
    write_cluster_marker(cp.root, {"name": name, "cluster_ip": marker_ip, "psnt": key.split("__")[-1]})
    (cp.reports / f"vast_data_{name}_{ts}.json").write_text(
        json.dumps({"cluster_ip": marker_ip, "cluster_summary": {"name": name}})
    )
    (cp.reports / f"vast_asbuilt_report_{name}_{ts}.pdf").write_bytes(b"%PDF-fake")
    (cp.health / f"health_check_{name}_{ts}.json").write_text(json.dumps({"cluster_ip": marker_ip, "results": []}))
    (cp.scripts / f"vperfsanity_results_{marker_ip}_{ts}.txt").write_text(f"perf {name}")
    (cp.scripts / f"vnetmap_results_{marker_ip}_{ts}.json").write_text(json.dumps({"cluster_ip": marker_ip}))
    _write_bundle(cp.bundles / f"validation_bundle_{name}_{ts}.zip", marker_ip, name)


@pytest.fixture
def tech_port_data_dir(data_dir):
    """Two Tech Port clusters sharing 192.168.2.2, a VMS-HTTPS cluster, and legacy flat files."""
    _make_cluster_folder(data_dir, KEY_A, "ACME-A", TECH_PORT_IP, "20260301_120000")
    _make_cluster_folder(data_dir, KEY_B, "ACME-B", TECH_PORT_IP, "20260302_120000")
    _make_cluster_folder(data_dir, "ACME-C__PSNT0003", "ACME-C", VMS_HTTPS_IP, "20260303_120000")

    (data_dir / "reports" / "vast_data_ACME-OLD_20250101_120000.json").write_text(
        json.dumps({"cluster_ip": TECH_PORT_IP, "cluster_summary": {"name": "ACME-OLD"}})
    )
    (data_dir / "output" / "health" / "health_check_old_20250101_120000.json").write_text(
        json.dumps({"cluster_ip": TECH_PORT_IP, "results": []})
    )
    scripts = data_dir / "output" / "scripts"
    (scripts / f"vperfsanity_results_{TECH_PORT_IP}_20250101_120000.txt").write_text("legacy perf")
    _write_bundle(data_dir / "output" / "bundles" / "validation_bundle_old_20250101_120000.zip", TECH_PORT_IP, "old")
    (scripts / f"vperfsanity_results_{VMS_HTTPS_IP}_20250102_120000.txt").write_text("legacy https perf")
    return data_dir


def _all_paths(results):
    return [e["path"] for entries in results.values() for e in entries]


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
# ResultScanner.scan_all(cluster_key=...) — TP-4
# ===================================================================


class TestScanAllByClusterKey:
    LISTED_OPS = ("asbuilt_reports", "health_checks", "vperfsanity", "vnetmap", "bundles")

    def test_tech_port_clusters_sharing_ip_never_mix(self, tech_port_data_dir):
        """REGRESSION (TP-4): filtering to one Tech Port cluster lists only its
        artifacts even though every Tech Port cluster reports 192.168.2.2."""
        scanner = ResultScanner(data_dir=tech_port_data_dir)
        for mine, other in ((KEY_A, KEY_B), (KEY_B, KEY_A)):
            results = scanner.scan_all(cluster_key=mine)
            for op in self.LISTED_OPS:
                assert results[op], f"{mine}: no {op} listed"
                assert {e["cluster_key"] for e in results[op]} == {mine}
            paths = _all_paths(results)
            assert all(f"/clusters/{mine}/" in p for p in paths)
            assert not any(other in p for p in paths)

    def test_cluster_key_excludes_legacy_tech_port_files(self, tech_port_data_dir):
        scanner = ResultScanner(data_dir=tech_port_data_dir)
        for key in (KEY_A, KEY_B):
            paths = _all_paths(scanner.scan_all(cluster_key=key))
            assert not any("/clusters/" not in p for p in paths)
            assert not any("ACME-OLD" in p or "_old_" in p or "20250101" in p for p in paths)

    def test_unassigned_lists_only_legacy_tech_port_files(self, tech_port_data_dir):
        scanner = ResultScanner(data_dir=tech_port_data_dir)
        results = scanner.scan_all(cluster_key=UNASSIGNED)
        entries = [e for v in results.values() for e in v]
        assert {e["filename"] for e in entries} == {
            "vast_data_ACME-OLD_20250101_120000.json",
            "health_check_old_20250101_120000.json",
            f"vperfsanity_results_{TECH_PORT_IP}_20250101_120000.txt",
            "validation_bundle_old_20250101_120000.zip",
        }
        assert all(e["cluster_key"] == "" for e in entries)
        assert all(e["cluster_ip"] == TECH_PORT_IP for e in entries)

    def test_unknown_cluster_key_returns_nothing(self, tech_port_data_dir):
        scanner = ResultScanner(data_dir=tech_port_data_dir)
        for key in ("no-such-cluster", "../reports", f"{KEY_A}/../{KEY_B}"):
            results = scanner.scan_all(cluster_key=key)
            assert sum(len(v) for v in results.values()) == 0, key

    def test_cluster_key_wins_over_cluster_ip(self, tech_port_data_dir):
        scanner = ResultScanner(data_dir=tech_port_data_dir)
        results = scanner.scan_all(cluster_ip=TECH_PORT_IP, cluster_key=KEY_A)
        assert {e["cluster_key"] for v in results.values() for e in v} == {KEY_A}

    def test_vms_https_ip_filter_unchanged(self, tech_port_data_dir):
        """A VMS-HTTPS cluster filtered by its real IP still lists its folder
        and its legacy flat files, exactly as before TP-4."""
        scanner = ResultScanner(data_dir=tech_port_data_dir)
        results = scanner.scan_all(cluster_ip=VMS_HTTPS_IP)
        assert all(e["cluster_ip"] == VMS_HTTPS_IP for v in results.values() for e in v)
        perf = {e["filename"] for e in results["vperfsanity"]}
        assert perf == {
            f"vperfsanity_results_{VMS_HTTPS_IP}_20260303_120000.txt",
            f"vperfsanity_results_{VMS_HTTPS_IP}_20250102_120000.txt",
        }
        assert len(results["asbuilt_reports"]) == 2
        assert len(results["bundles"]) == 1

    def test_tech_port_ip_filter_does_not_mix_clusters(self, tech_port_data_dir):
        """An old ``?cluster_ip=192.168.2.2`` bookmark cannot identify a cluster,
        so it falls back to the Unassigned (legacy) set instead of mixing."""
        scanner = ResultScanner(data_dir=tech_port_data_dir)
        by_ip = scanner.scan_all(cluster_ip=TECH_PORT_IP)
        unassigned = scanner.scan_all(cluster_key=UNASSIGNED)
        assert by_ip == unassigned
        assert not any("/clusters/" in p for p in _all_paths(by_ip))

    def test_unassigned_key_constant_matches_api_value(self):
        import result_scanner

        assert result_scanner.UNASSIGNED_LEGACY_KEY == UNASSIGNED


class TestFilterChoices:
    def test_tech_port_clusters_listed_by_key_with_name_and_ip(self, tech_port_data_dir):
        profiles = {
            "acme-a": {"cluster_ip": TECH_PORT_IP, "tech_port": True},
            "acme-b": {"cluster_ip": TECH_PORT_IP, "tech_port": True},
            "acme-c": {"cluster_ip": VMS_HTTPS_IP},
        }
        scanner = ResultScanner(data_dir=tech_port_data_dir, profiles=profiles)
        choices = scanner.get_filter_choices()

        by_value = {(c["param"], c["value"]): c for c in choices}
        assert by_value[("cluster_key", KEY_A)]["label"] == f"ACME-A — {TECH_PORT_IP}"
        assert by_value[("cluster_key", KEY_B)]["label"] == f"ACME-B — {TECH_PORT_IP}"
        assert by_value[("cluster_ip", VMS_HTTPS_IP)]["label"] == f"acme-c — {VMS_HTTPS_IP}"
        assert by_value[("cluster_key", UNASSIGNED)]["label"] == "Unassigned (legacy)"
        assert ("cluster_ip", TECH_PORT_IP) not in by_value
        assert ("cluster_key", "ACME-C__PSNT0003") not in by_value

    def test_no_unassigned_choice_without_legacy_tech_port_files(self, data_dir):
        _make_cluster_folder(data_dir, KEY_A, "ACME-A", TECH_PORT_IP, "20260301_120000")
        scanner = ResultScanner(data_dir=data_dir)
        values = {c["value"] for c in scanner.get_filter_choices()}
        assert values == {KEY_A}

    def test_unsaved_vms_https_folder_listed_by_key(self, data_dir):
        _make_cluster_folder(data_dir, "ACME-C__PSNT0003", "ACME-C", VMS_HTTPS_IP, "20260303_120000")
        scanner = ResultScanner(data_dir=data_dir)
        choices = scanner.get_filter_choices()
        assert choices == [{"param": "cluster_key", "value": "ACME-C__PSNT0003", "label": f"ACME-C — {VMS_HTTPS_IP}"}]

    def test_get_known_clusters_does_not_guess_profile_by_tech_port_ip(self, tech_port_data_dir):
        profiles = {"acme-a": {"cluster_ip": TECH_PORT_IP}}
        scanner = ResultScanner(data_dir=tech_port_data_dir, profiles=profiles)
        clusters = {c["cluster_key"]: c for c in scanner.get_known_clusters()}
        assert clusters[KEY_A]["profile_name"] == ""
        assert clusters[KEY_B]["profile_name"] == ""
        assert clusters[KEY_A]["cluster_name"] == "ACME-A"


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
