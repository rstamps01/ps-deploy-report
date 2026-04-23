"""
Unit tests for Result Bundler module.

Tests the ResultBundler class including result collection,
bundle creation, cluster-scoped filtering, and file operations.
"""

import json
import os
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from result_bundler import (
    STATUS_FAILED,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_SKIPPED,
    STATUS_STALE,
    ResultBundler,
    get_result_bundler,
)

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


# ===================================================================
# TestStalenessFilter — since= excludes pre-run files
# ===================================================================


def _age_file(path: Path, seconds_in_past: int) -> None:
    """Backdate file mtime so the bundler sees it as pre-run."""
    past = datetime.now().timestamp() - seconds_in_past
    os.utime(path, (past, past))


class TestStalenessFilter:
    """Regression: bundler must not silently bundle pre-run files."""

    def test_since_excludes_pre_run_vnetmap(self, bundler, mock_results):
        """A vnetmap_results file older than `since` must be excluded and
        reported as ``stale`` instead of being quietly added to the bundle.
        """
        scripts = mock_results / "scripts"
        stale_file = scripts / f"vnetmap_results_{CLUSTER_A_IP}_20260101_120000.json"
        assert stale_file.exists()
        _age_file(stale_file, seconds_in_past=3600)

        since = datetime.now() - timedelta(minutes=5)
        collected = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP, since=since)

        assert "vnetmap" not in collected
        assert bundler._category_status["vnetmap"] == STATUS_STALE
        assert "vnetmap" in bundler._stale_files
        assert bundler._stale_files["vnetmap"] == stale_file

    def test_since_keeps_fresh_results(self, bundler, mock_results):
        """Files newer than `since` are still picked up as ok."""
        scripts = mock_results / "scripts"
        fresh = scripts / f"vperfsanity_results_{CLUSTER_A_IP}_20260101_120000.txt"
        assert fresh.exists()

        since = datetime.now() - timedelta(hours=1)
        collected = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP, since=since)

        assert "vperfsanity" in collected
        assert bundler._category_status["vperfsanity"] == STATUS_OK

    def test_since_none_preserves_legacy_behaviour(self, bundler, mock_results):
        """Omitting `since` must behave exactly like the pre-fix bundler:
        pick the latest file per category regardless of age.
        """
        scripts = mock_results / "scripts"
        old = scripts / f"vnetmap_results_{CLUSTER_A_IP}_20260101_120000.json"
        _age_file(old, seconds_in_past=86400)

        collected = bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP)
        assert "vnetmap" in collected


# ===================================================================
# TestCategoryStatus — operation_status influences manifest categories
# ===================================================================


class TestCategoryStatus:
    def test_failed_operation_marked_failed_when_no_file(self, bundler, tmp_path):
        """If the runner says an op failed and no fresh file exists, the
        category must surface as ``failed`` (not ``missing``).
        """
        bundler.set_metadata("test", CLUSTER_A_IP, "5.0")
        empty = tmp_path / "output"
        empty.mkdir()
        bundler.collect_results(
            empty,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
            operation_status={"vnetmap": "failed"},
        )
        assert bundler._category_status["vnetmap"] == STATUS_FAILED

    def test_skipped_operation_marked_skipped(self, bundler, tmp_path):
        bundler.set_metadata("test", CLUSTER_A_IP, "5.0")
        empty = tmp_path / "output"
        empty.mkdir()
        bundler.collect_results(
            empty,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
            operation_status={"support_tools": "skipped"},
        )
        assert bundler._category_status["support_tools"] == STATUS_SKIPPED

    def test_missing_when_no_status_and_no_file(self, bundler, tmp_path):
        bundler.set_metadata("test", CLUSTER_A_IP, "5.0")
        empty = tmp_path / "output"
        empty.mkdir()
        bundler.collect_results(empty, cluster_ip=CLUSTER_A_IP)
        assert bundler._category_status["vperfsanity"] == STATUS_MISSING


# ===================================================================
# TestManifestAndPlaceholders — bundle reflects category status
# ===================================================================


class TestManifestAndPlaceholders:
    def test_manifest_includes_categories_and_stale(self, tmp_path, mock_results):
        """manifest.json must advertise per-category status and stale files
        so downstream consumers can detect silent regressions.

        RM-6: the STALE-placeholder assertion is verified against a
        bundler with ``include_prior_vnetmap=False`` because the default
        is now to rescue prior vnetmap output under a ``_PRIOR_`` arcname
        rather than ship a bare ``_STALE.txt`` note.  The manifest-level
        STATUS_STALE tracking is unchanged either way.
        """
        scripts = mock_results / "scripts"
        stale_file = scripts / f"vnetmap_results_{CLUSTER_A_IP}_20260101_120000.json"
        _age_file(stale_file, seconds_in_past=3600)

        bundler_off = ResultBundler(
            output_dir=tmp_path / "bundles_off",
            include_prior_vnetmap=False,
        )
        bundler_off.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        since = datetime.now() - timedelta(minutes=5)
        bundler_off.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=since,
            operation_status={"support_tools": "failed"},
        )
        bundle_path = bundler_off.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))
            names = zf.namelist()

        assert manifest["version"] >= "1.1"
        assert manifest["categories"]["vnetmap"] == STATUS_STALE
        assert manifest["categories"]["support_tools"] == STATUS_FAILED
        assert manifest["stale"]["vnetmap"] == stale_file.name
        assert manifest["run_started_at"] is not None

        # With the RM-6 opt-out flag off, stale vnetmap still produces a
        # _STALE placeholder rather than the old _NOT_FOUND.
        assert any(n.endswith("vnetmap_STALE.txt") for n in names)
        assert not any(n.endswith("vnetmap_NOT_FOUND.txt") for n in names)
        # Failed category gets a _FAILED placeholder
        assert any(n.endswith("support_tools_FAILED.txt") for n in names)
        # Stale file itself must NOT be bundled (under the opt-out path)
        assert not any(stale_file.name in n for n in names)

    def test_summary_mentions_category_status(self, bundler, mock_results):
        scripts = mock_results / "scripts"
        stale_file = scripts / f"vnetmap_results_{CLUSTER_A_IP}_20260101_120000.json"
        _age_file(stale_file, seconds_in_past=3600)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        summary = bundler.generate_summary()
        assert "Category Status" in summary
        assert "STALE" in summary
        assert "vnetmap" in summary.lower()


# ===================================================================
# TestPriorVperfsanity (RM-5) — stale vperfsanity is shipped as PRIOR
# ===================================================================


class TestPriorVperfsanity:
    """RM-5: when vperfsanity is STATUS_STALE (skipped this run but a prior
    file exists on disk), the bundler should attach the prior file under
    ``performance/vperfsanity_PRIOR_<name>.txt`` with a banner instead of a
    bare ``_STALE.txt`` placeholder, unless the caller opts out via
    ``include_prior_vperfsanity=False``.
    """

    def _prepare_stale_vperfsanity(self, mock_results):
        """Age the vperfsanity file beyond `since` so it becomes STALE."""
        scripts = mock_results / "scripts"
        stale = scripts / f"vperfsanity_results_{CLUSTER_A_IP}_20260101_120000.txt"
        assert stale.exists()
        stale.write_text("PRIOR_RUN_PERF_DATA\nlatency_ns=12345\n")
        _age_file(stale, seconds_in_past=3600)
        return stale

    def test_prior_vperfsanity_attached_with_banner(self, bundler, mock_results):
        stale_file = self._prepare_stale_vperfsanity(mock_results)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        since = datetime.now() - timedelta(minutes=5)
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP, since=since)
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            prior_arcname = f"performance/vperfsanity_PRIOR_{stale_file.name}"
            assert prior_arcname in names, f"Expected {prior_arcname} in {names}"
            body = zf.read(prior_arcname).decode("utf-8")

            assert not any(n.endswith("vperfsanity_STALE.txt") for n in names), (
                "RM-5: prior-file rescue should replace the bare STALE placeholder, " "not ship alongside it"
            )

        assert "prior vperfsanity output" in body.lower()
        assert f"Source file:    {stale_file.name}" in body
        assert "Do NOT treat these numbers as current-run performance data." in body
        assert "PRIOR_RUN_PERF_DATA" in body
        assert "latency_ns=12345" in body

    def test_manifest_records_prior_source_and_flag(self, bundler, mock_results):
        stale_file = self._prepare_stale_vperfsanity(mock_results)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

        assert manifest["version"] >= "1.2"
        assert manifest["vperfsanity_prior_source"] == stale_file.name
        assert manifest["include_prior_vperfsanity"] is True
        assert manifest["categories"]["vperfsanity"] == STATUS_STALE
        assert manifest["stale"]["vperfsanity"] == stale_file.name

    def test_summary_marks_vperfsanity_as_prior(self, bundler, mock_results):
        stale_file = self._prepare_stale_vperfsanity(mock_results)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        # create_bundle() is what populates _prior_vperfsanity_source;
        # generate_summary() without it would still say "(not included)"
        bundler.create_bundle()
        summary = bundler.generate_summary()

        assert f"vperfsanity_PRIOR_{stale_file.name}" in summary
        assert "included as PRIOR with banner" in summary

    def test_include_prior_vperfsanity_false_falls_back_to_placeholder(self, tmp_path, mock_results):
        """With the opt-out flag off, the bundler must keep the pre-RM-5
        behaviour and ship only the ``_STALE.txt`` placeholder without
        rescuing the prior file.
        """
        bundler_off = ResultBundler(
            output_dir=tmp_path / "bundles_off",
            include_prior_vperfsanity=False,
        )

        stale_file = self._prepare_stale_vperfsanity(mock_results)

        bundler_off.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler_off.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        bundle_path = bundler_off.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))

        assert any(n.endswith("vperfsanity_STALE.txt") for n in names)
        assert not any(f"vperfsanity_PRIOR_{stale_file.name}" in n for n in names)
        assert manifest["vperfsanity_prior_source"] is None
        assert manifest["include_prior_vperfsanity"] is False

    def test_fresh_vperfsanity_does_not_trigger_prior_rescue(self, bundler, mock_results):
        """If vperfsanity ran this run (STATUS_OK), no PRIOR copy and the
        manifest must leave ``vperfsanity_prior_source`` as ``None``.
        """
        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(hours=1),
        )
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))

        assert not any("vperfsanity_PRIOR_" in n for n in names)
        assert manifest["vperfsanity_prior_source"] is None

    def test_factory_propagates_include_prior_flag(self, tmp_path):
        """``get_result_bundler(include_prior_vperfsanity=False)`` must
        produce a bundler configured with the flag off.
        """
        b_on = get_result_bundler(output_dir=tmp_path)
        b_off = get_result_bundler(output_dir=tmp_path, include_prior_vperfsanity=False)

        assert b_on._include_prior_vperfsanity is True
        assert b_off._include_prior_vperfsanity is False


# ===================================================================
# TestPriorVnetmap (RM-6)
# ===================================================================


class TestPriorVnetmap:
    """RM-6: when ``vnetmap`` is STATUS_STALE (the run couldn't complete —
    typically because a switch failed SSH/API auth — but a prior
    ``vnetmap_results_*.json`` and/or ``vnetmap_output_*.txt`` exists on
    disk), the bundler must attach the prior file(s) under
    ``topology/vnetmap_PRIOR_<name>.json`` / ``topology/vnetmap_output_PRIOR_<name>.txt``
    with a banner, unless the caller opts out via
    ``include_prior_vnetmap=False``.
    """

    def _prepare_stale_vnetmap(self, mock_results):
        """Age the vnetmap JSON + raw TXT so the bundler treats them as STALE.

        Also creates the paired ``vnetmap_output_*.txt`` that the bundler's
        ``_record`` path expects, since the ``mock_results`` fixture only
        creates the JSON.
        """
        scripts = mock_results / "scripts"
        stale_json = scripts / f"vnetmap_results_{CLUSTER_A_IP}_20260101_120000.json"
        stale_txt = scripts / f"vnetmap_output_{CLUSTER_A_IP}_20260101_120000.txt"

        assert stale_json.exists()
        stale_json.write_text(json.dumps({"cluster_ip": CLUSTER_A_IP, "nodes": ["cn1", "cn2"], "links": []}))
        stale_txt.write_text("PRIOR_RUN_VNETMAP_RAW\nlldp neighbor sw1 eth0 <-> cn1 eth0\n")

        _age_file(stale_json, seconds_in_past=3600)
        _age_file(stale_txt, seconds_in_past=3600)
        return stale_json, stale_txt

    def test_prior_vnetmap_json_attached_with_banner(self, bundler, mock_results):
        stale_json, _ = self._prepare_stale_vnetmap(mock_results)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        since = datetime.now() - timedelta(minutes=5)
        bundler.collect_results(mock_results, cluster_ip=CLUSTER_A_IP, since=since)
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            arcname = f"topology/vnetmap_PRIOR_{stale_json.name}"
            assert arcname in names, f"Expected {arcname} in {names}"
            body = zf.read(arcname).decode("utf-8")

            assert not any(n.endswith("vnetmap_STALE.txt") for n in names), (
                "RM-6: prior-file rescue should replace the bare vnetmap " "STALE placeholder, not ship alongside it"
            )

        assert "prior vnetmap output" in body.lower()
        assert f"Source file:    {stale_json.name}" in body
        assert "Do NOT treat this LLDP map" in body
        assert "cluster_ip" in body

    def test_prior_vnetmap_raw_output_attached_with_banner(self, bundler, mock_results):
        """Raw ``vnetmap_output_*.txt`` gets its own PRIOR arcname separate
        from the JSON half so consumers that only look at the text dump
        aren't silently left with a STALE note.
        """
        _, stale_txt = self._prepare_stale_vnetmap(mock_results)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            arcname = f"topology/vnetmap_output_PRIOR_{stale_txt.name}"
            assert arcname in names, f"Expected {arcname} in {names}"
            body = zf.read(arcname).decode("utf-8")

        assert "prior vnetmap raw output" in body.lower()
        assert "PRIOR_RUN_VNETMAP_RAW" in body

    def test_manifest_records_vnetmap_prior_sources_and_flag(self, bundler, mock_results):
        stale_json, stale_txt = self._prepare_stale_vnetmap(mock_results)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            manifest = json.loads(zf.read("manifest.json"))

        assert manifest["version"] >= "1.3"
        assert manifest["vnetmap_prior_source"] == stale_json.name
        assert manifest["vnetmap_output_prior_source"] == stale_txt.name
        assert manifest["include_prior_vnetmap"] is True
        assert manifest["categories"]["vnetmap"] == STATUS_STALE
        assert manifest["stale"]["vnetmap"] == stale_json.name

    def test_summary_marks_vnetmap_as_prior(self, bundler, mock_results):
        stale_json, _ = self._prepare_stale_vnetmap(mock_results)

        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        bundler.create_bundle()
        summary = bundler.generate_summary()

        assert f"vnetmap_PRIOR_{stale_json.name}" in summary
        assert "included as PRIOR with banner" in summary

    def test_include_prior_vnetmap_false_falls_back_to_placeholder(self, tmp_path, mock_results):
        """With the opt-out flag off, the bundler ships a bare
        ``vnetmap_STALE.txt`` placeholder and records
        ``vnetmap_prior_source`` as ``None`` in the manifest.
        """
        bundler_off = ResultBundler(
            output_dir=tmp_path / "bundles_off",
            include_prior_vnetmap=False,
        )

        stale_json, _ = self._prepare_stale_vnetmap(mock_results)

        bundler_off.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler_off.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(minutes=5),
        )
        bundle_path = bundler_off.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))

        assert any(n.endswith("vnetmap_STALE.txt") for n in names)
        assert not any(f"vnetmap_PRIOR_{stale_json.name}" in n for n in names)
        assert manifest["vnetmap_prior_source"] is None
        assert manifest["vnetmap_output_prior_source"] is None
        assert manifest["include_prior_vnetmap"] is False

    def test_fresh_vnetmap_does_not_trigger_prior_rescue(self, bundler, mock_results):
        """If vnetmap ran this run (STATUS_OK), no PRIOR copy should land
        in the archive and the manifest fields must stay ``None``.
        """
        bundler.set_metadata("cluster-a", CLUSTER_A_IP, "5.0")
        bundler.collect_results(
            mock_results,
            cluster_ip=CLUSTER_A_IP,
            since=datetime.now() - timedelta(hours=1),
        )
        bundle_path = bundler.create_bundle()

        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            manifest = json.loads(zf.read("manifest.json"))

        assert not any("vnetmap_PRIOR_" in n for n in names)
        assert manifest["vnetmap_prior_source"] is None
        assert manifest["vnetmap_output_prior_source"] is None

    def test_factory_propagates_include_prior_vnetmap_flag(self, tmp_path):
        """The factory must forward ``include_prior_vnetmap`` to the bundler."""
        b_on = get_result_bundler(output_dir=tmp_path)
        b_off = get_result_bundler(output_dir=tmp_path, include_prior_vnetmap=False)

        assert b_on._include_prior_vnetmap is True
        assert b_off._include_prior_vnetmap is False
