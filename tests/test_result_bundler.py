"""
Unit tests for Result Bundler module.

Tests the ResultBundler class including result collection,
bundle creation, and file operations.
"""

import json
import os
import sys
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from result_bundler import ResultBundler, get_result_bundler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def bundler(tmp_path):
    """Create a ResultBundler with temp directory."""
    return ResultBundler(output_dir=tmp_path / "bundles")


@pytest.fixture
def mock_results(tmp_path):
    """Create mock result files."""
    # Health check
    health_dir = tmp_path / "output" / "health"
    health_dir.mkdir(parents=True)
    health_file = health_dir / "health_check_test_20260101_120000.json"
    health_file.write_text(
        json.dumps(
            {
                "cluster_name": "test-cluster",
                "summary": {"pass": 10, "fail": 1, "warning": 2, "skipped": 0, "error": 0},
                "results": [],
            }
        )
    )

    # Network config
    network_dir = tmp_path / "output" / "advanced_ops" / "network_configs"
    network_dir.mkdir(parents=True)
    (network_dir / "network_summary_test_20260101.json").write_text('{"hostname": "test"}')

    return tmp_path / "output"


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


class TestSummaryGeneration:
    def test_generate_summary_empty(self, bundler):
        bundler.set_metadata("test", "10.0.0.1", "5.0")
        summary = bundler.generate_summary()
        assert "# Validation Results Summary" in summary
        assert "test" in summary

    def test_generate_summary_with_results(self, bundler, mock_results):
        bundler.set_metadata("test-cluster", "10.0.0.1", "5.0")
        bundler.collect_results(mock_results)
        summary = bundler.generate_summary()
        assert "Health Check Results" in summary or "Included Files" in summary


class TestBundleCreation:
    def test_create_bundle_with_results(self, bundler, mock_results):
        bundler.set_metadata("test-cluster", "10.0.0.1", "5.0")
        bundler.collect_results(mock_results)
        bundle_path = bundler.create_bundle()

        assert bundle_path.exists()
        assert bundle_path.suffix == ".zip"

        # Verify ZIP contents
        with zipfile.ZipFile(bundle_path, "r") as zf:
            names = zf.namelist()
            assert "manifest.json" in names
            assert "SUMMARY.md" in names

    def test_create_bundle_with_custom_name(self, bundler, mock_results):
        bundler.set_metadata("test", "10.0.0.1", "5.0")
        bundler.collect_results(mock_results)
        bundle_path = bundler.create_bundle("custom_bundle")

        assert "custom_bundle.zip" in bundle_path.name


class TestBundleInfo:
    def test_get_bundle_info_not_found(self, bundler, tmp_path):
        info = bundler.get_bundle_info(tmp_path / "nonexistent.zip")
        assert "error" in info

    def test_get_bundle_info_valid(self, bundler, mock_results):
        bundler.set_metadata("test", "10.0.0.1", "5.0")
        bundler.collect_results(mock_results)
        bundle_path = bundler.create_bundle()

        info = bundler.get_bundle_info(bundle_path)
        assert "name" in info
        assert "size" in info
        assert "files" in info

    def test_list_bundles_empty(self, bundler):
        bundles = bundler.list_bundles()
        assert isinstance(bundles, list)

    def test_list_bundles_after_create(self, bundler, mock_results):
        bundler.set_metadata("test", "10.0.0.1", "5.0")
        bundler.collect_results(mock_results)
        bundler.create_bundle()

        bundles = bundler.list_bundles()
        assert len(bundles) >= 1
        assert "name" in bundles[0]


class TestFactoryFunction:
    def test_get_result_bundler(self, tmp_path):
        bundler = get_result_bundler(output_dir=tmp_path)
        assert isinstance(bundler, ResultBundler)

    def test_get_result_bundler_with_callback(self, tmp_path):
        callback = MagicMock()
        bundler = get_result_bundler(output_dir=tmp_path, output_callback=callback)
        bundler.emit("info", "Test message")
        callback.assert_called()
