"""
Unit tests for Result Bundler module.

Tests the ResultBundler class including result collection,
bundle creation, cluster-scoped filtering, and file operations.
"""

import json
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from result_bundler import ResultBundler, get_result_bundler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

CLUSTER_A_IP = "10.143.11.202"
CLUSTER_B_IP = "10.141.200.217"


@pytest.fixture
def bundler(tmp_path):
    """Create a ResultBundler with temp directory."""
    return ResultBundler(output_dir=tmp_path / "bundles")


@pytest.fixture
def mock_results(tmp_path):
    """Create mock result files for TWO clusters to test filtering."""
    out = tmp_path / "output"

    # -- Health check (cluster A) --
    health_dir = out / "health"
    health_dir.mkdir(parents=True)
    (health_dir / "health_check_test_20260101_120000.json").write_text(
        json.dumps(
            {
                "cluster_ip": CLUSTER_A_IP,
                "cluster_name": "cluster-a",
                "summary": {"pass": 10, "fail": 1, "warning": 2, "skipped": 0, "error": 0},
                "results": [],
            }
        )
    )

    # -- Network config (cluster A) --
    net_dir = out / "scripts" / "network_configs"
    net_dir.mkdir(parents=True)
    (net_dir / "network_summary_cn1_20260101_120000.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_A_IP, "cluster_hostname": "cn1"})
    )
    (net_dir / "configure_network_commands_all_nodes_20260101_120000.txt").write_text(
        f"# Cluster: cn1 ({CLUSTER_A_IP})\ndata"
    )
    (net_dir / "routing_table_all_nodes_20260101_120000.txt").write_text(f"# Cluster: cn1 ({CLUSTER_A_IP})\ndata")

    # -- Network config (cluster B, older) --
    (net_dir / "network_summary_cn2_20250601_100000.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_B_IP, "cluster_hostname": "cn2"})
    )
    (net_dir / "routing_table_all_nodes_20250601_100000.txt").write_text(f"# Cluster: cn2 ({CLUSTER_B_IP})\ndata")

    # -- Switch config (cluster A) --
    sw_dir = out / "scripts" / "switch_configs"
    sw_dir.mkdir(parents=True)
    (sw_dir / "switch_configs_20260101_120000.json").write_text(
        json.dumps({"timestamp": "20260101_120000", "cluster_ip": CLUSTER_A_IP, "switches": {}})
    )
    (sw_dir / "switch_sw1_10_0_0_10_20260101_120000.txt").write_text(
        f"# Cluster: {CLUSTER_A_IP}\n# Hostname: sw1\ndata"
    )

    # -- Switch config (cluster B) --
    (sw_dir / "switch_configs_20250601_100000.json").write_text(
        json.dumps({"timestamp": "20250601_100000", "cluster_ip": CLUSTER_B_IP, "switches": {}})
    )

    # -- vnetmap (cluster A) --
    scripts = out / "scripts"
    (scripts / f"vnetmap_results_{CLUSTER_A_IP}_20260101_120000.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_A_IP, "timestamp": "20260101_120000"})
    )

    # -- vnetmap (cluster B) --
    (scripts / f"vnetmap_results_{CLUSTER_B_IP}_20250601_100000.json").write_text(
        json.dumps({"cluster_ip": CLUSTER_B_IP, "timestamp": "20250601_100000"})
    )

    # -- vperfsanity (cluster A) --
    (scripts / f"vperfsanity_results_{CLUSTER_A_IP}_20260101_120000.txt").write_text("perf data A")

    # -- vperfsanity (cluster B) --
    (scripts / f"vperfsanity_results_{CLUSTER_B_IP}_20250601_100000.txt").write_text("perf data B")

    return out


# ===================================================================
# TestResultBundler
# ===================================================================


class TestResultBundler:
    def test_bundler_initialization(self, bundler):
        assert bundler is not None
        assert bundler._output_dir is not None

    def test_set_metadata(self, bundler):
        bundler.set_metadata("test-cluster", "10.0.0.1", "5.3.0")
        assert bundler._metadata["cluster_name"] == "test-cluster"
        assert bundler._metadata["cluster_ip"] == "10.0.0.1"
        assert bundler._metadata["cluster_version"] == "5.3.0"

    def test_format_size(self, bundler):
        assert bundler._format_size(500) == "500.0 B"
        assert bundler._format_size(1024) == "1.0 KB"
        assert bundler._format_size(1024 * 1024) == "1.0 MB"
        assert bundler._format_size(1024 * 1024 * 1024) == "1.0 GB"


# ===================================================================
# TestResultCollection — unfiltered (no cluster_ip)
# ===================================================================


class TestResultCollection:
    def test_collect_results_returns_dict(self, bundler, mock_results):
        results = bundler.collect_results(mock_results)
        assert isinstance(results, dict)

    def test_collect_results_with_health_check(self, bundler, mock_results):
        results = bundler.collect_results(mock_results)
        assert "health_check" in results
        assert results["health_check"].exists()

    def test_collect_results_with_network_config(self, bundler, mock_results):
        results = bundler.collect_results(mock_results)
        assert "network_config" in results

    def test_unfiltered_picks_latest(self, bundler, mock_results):
        results = bundler.collect_results(mock_results)
        assert "network_config" in results
        assert results["network_config"].name.startswith("network_summary_")

    def test_unfiltered_collects_both_clusters(self, bundler, mock_results):
        results = bundler.collect_results(mock_results)
        assert "vnetmap" in results
        assert "vperfsanity" in results


# ===================================================================
# TestClusterFiltering — scoped to a specific cluster_ip
# ===================================================================


class TestClusterFiltering:
    def test_filter_health_check(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "health_check" in results
        data = json.loads(results["health_check"].read_text())
        assert data["cluster_ip"] == CLUSTER_A_IP

    def test_filter_excludes_wrong_cluster_health(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_B_IP)
        assert "health_check" not in results

    def test_filter_network_config(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "network_config" in results
        data = json.loads(results["network_config"].read_text())
        assert data["cluster_ip"] == CLUSTER_A_IP

    def test_filter_network_text_files_by_timestamp(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "network_commands" in results
        assert "20260101_120000" in results["network_commands"].name
        assert "network_routing" in results
        assert "20260101_120000" in results["network_routing"].name

    def test_filter_network_config_cluster_b(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_B_IP)
        assert "network_config" in results
        data = json.loads(results["network_config"].read_text())
        assert data["cluster_ip"] == CLUSTER_B_IP
        if "network_routing" in results:
            assert "20250601_100000" in results["network_routing"].name

    def test_filter_switch_config(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "switch_config" in results
        data = json.loads(results["switch_config"].read_text())
        assert data["cluster_ip"] == CLUSTER_A_IP

    def test_filter_switch_config_cluster_b(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_B_IP)
        assert "switch_config" in results
        data = json.loads(results["switch_config"].read_text())
        assert data["cluster_ip"] == CLUSTER_B_IP

    def test_filter_switch_text_included(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "switch_config_txt" in results

    def test_filter_switch_text_excluded(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_B_IP)
        assert "switch_config_txt" not in results

    def test_filter_vnetmap(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "vnetmap" in results
        assert CLUSTER_A_IP in results["vnetmap"].name

    def test_filter_vnetmap_excludes_other(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert CLUSTER_B_IP not in results["vnetmap"].name

    def test_filter_vperfsanity(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "vperfsanity" in results
        assert CLUSTER_A_IP in results["vperfsanity"].name

    def test_filter_vperfsanity_cluster_b(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip=CLUSTER_B_IP)
        assert "vperfsanity" in results
        assert CLUSTER_B_IP in results["vperfsanity"].name

    def test_nonexistent_cluster_returns_no_cluster_files(self, bundler, mock_results):
        results = bundler.collect_results(mock_results, cluster_ip="192.168.99.99")
        assert "health_check" not in results
        assert "network_config" not in results
        assert "switch_config" not in results
        assert "vnetmap" not in results
        assert "vperfsanity" not in results


# ===================================================================
# TestSummaryGeneration
# ===================================================================


class TestSummaryGeneration:
    def test_generate_summary_empty(self, bundler):
        bundler.set_metadata("test", "10.0.0.1", "5.0")
        summary = bundler.generate_summary()
        assert "# Validation Results Summary" in summary
        assert "test" in summary

    def test_generate_summary_with_results(self, bundler, mock_results):
        bundler.set_metadata("test-cluster", CLUSTER_A_IP, "5.0")
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        summary = bundler.generate_summary()
        assert "Health Check Results" in summary or "Included Files" in summary


# ===================================================================
# TestBundleCreation
# ===================================================================


class TestBundleCreation:
    def test_create_bundle_with_results(self, bundler, mock_results):
        bundler.set_metadata("test-cluster", CLUSTER_A_IP, "5.0")
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        bundle_path = bundler.create_bundle()

        assert bundle_path.exists()
        assert bundle_path.suffix == ".zip"

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "SUMMARY.md" in names

    def test_create_bundle_with_custom_name(self, bundler, mock_results):
        bundler.set_metadata("test", CLUSTER_A_IP, "5.0")
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        bundle_path = bundler.create_bundle("custom_bundle")

        assert "custom_bundle.zip" in bundle_path.name

    def test_bundle_only_contains_cluster_files(self, bundler, mock_results):
        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            for name in names:
                assert CLUSTER_B_IP not in name


# ===================================================================
# TestBundleInfo
# ===================================================================


class TestBundleInfo:
    def test_get_bundle_info_not_found(self, bundler, tmp_path):
        info = bundler.get_bundle_info(tmp_path / "nonexistent.zip")
        assert "error" in info

    def test_get_bundle_info_valid(self, bundler, mock_results):
        bundler.set_metadata("test", CLUSTER_A_IP, "5.0")
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        bundle_path = bundler.create_bundle()

        info = bundler.get_bundle_info(bundle_path)
        assert "name" in info
        assert "size" in info
        assert "files" in info

    def test_list_bundles_empty(self, bundler):
        bundles = bundler.list_bundles()
        assert isinstance(bundles, list)

    def test_list_bundles_after_create(self, bundler, mock_results):
        bundler.set_metadata("test", CLUSTER_A_IP, "5.0")
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        bundler.create_bundle()

        bundles = bundler.list_bundles()
        assert len(bundles) >= 1
        assert "name" in bundles[0]


# ===================================================================
# TestHelpers
# ===================================================================


class TestHelpers:
    def test_json_has_cluster_ip_match(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert ResultBundler._json_has_cluster_ip(f, "10.0.0.1") is True

    def test_json_has_cluster_ip_no_match(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text(json.dumps({"cluster_ip": "10.0.0.1"}))
        assert ResultBundler._json_has_cluster_ip(f, "10.0.0.2") is False

    def test_json_has_cluster_ip_invalid_json(self, tmp_path):
        f = tmp_path / "test.json"
        f.write_text("not json")
        assert ResultBundler._json_has_cluster_ip(f, "10.0.0.1") is False

    def test_text_header_has_ip(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("# Cluster: host (10.0.0.1)\ndata\n")
        assert ResultBundler._text_header_has_ip(f, "10.0.0.1") is True

    def test_text_header_missing_ip(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("# Cluster: host (10.0.0.2)\ndata\n")
        assert ResultBundler._text_header_has_ip(f, "10.0.0.1") is False

    def test_filename_has_ip(self, tmp_path):
        f = tmp_path / "vnetmap_results_10.143.11.202_20260101.json"
        assert ResultBundler._filename_has_ip(f, "10.143.11.202") is True

    def test_filename_has_ip_underscores(self, tmp_path):
        f = tmp_path / "switch_sw1_10_143_11_202_20260101.txt"
        assert ResultBundler._filename_has_ip(f, "10.143.11.202") is True

    def test_filename_no_ip(self, tmp_path):
        f = tmp_path / "vnetmap_results_10.143.11.202_20260101.json"
        assert ResultBundler._filename_has_ip(f, "10.141.200.217") is False

    def test_extract_timestamp(self):
        assert ResultBundler._extract_timestamp("network_summary_cn1_20260101_120000.json") == "20260101_120000"
        assert ResultBundler._extract_timestamp("notstamped.json") is None


# ===================================================================
# TestFactoryFunction
# ===================================================================


class TestFactoryFunction:
    def test_get_result_bundler(self, tmp_path):
        bundler = get_result_bundler(output_dir=tmp_path)
        assert isinstance(bundler, ResultBundler)

    def test_get_result_bundler_with_callback(self, tmp_path):
        callback = MagicMock()
        bundler = get_result_bundler(output_dir=tmp_path, output_callback=callback)
        bundler.emit("info", "Test message")
        callback.assert_called()
