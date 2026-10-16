"""Bundles explain their own failures (EBox field report, v1.6.1).

Every ``*_FAILED.txt`` placeholder said "See the operation log for the root cause",
but the operation log was never put in the bundle.  Placeholders now carry the
failing step and error, and the session's operation log ships inside the bundle.
"""

import json
import sys
import zipfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from result_bundler import ResultBundler  # noqa: E402

CIP = "192.168.2.2"


def _bundle(tmp_path, operation_status, operation_details=None, operation_log=None):
    results = tmp_path / "output"
    (results / "health").mkdir(parents=True)
    (results / "health" / "health_check_cluster-x_20260925_183125.json").write_text(
        json.dumps({"cluster_ip": CIP, "cluster_name": "cluster-x", "summary": {}, "results": []})
    )
    bundler = ResultBundler(output_dir=tmp_path / "bundles")
    bundler.set_metadata("cluster-x", CIP, "5.5")
    bundler.collect_results(
        results,
        cluster_ip=CIP,
        since=datetime.now() - timedelta(minutes=5),
        operation_status=operation_status,
        operation_details=operation_details,
    )
    assert "health_check" in bundler._collected_files, "fixture must collect a file so the bundle is self-contained"
    if operation_log is not None:
        bundler.set_operation_log(operation_log)
    path = bundler.create_bundle()
    return zipfile.ZipFile(path, "r")


class TestPlaceholdersCarryReasons:
    def test_failed_placeholder_names_step_and_error(self, tmp_path):
        zf = _bundle(
            tmp_path,
            {"support_tools": "failed"},
            {"support_tools": "Step 3 (Run Support Tools): Support tools did not start (rc=127)"},
        )
        text = zf.read("diagnostics/support_tools_FAILED.txt").decode()
        assert "Step 3 (Run Support Tools)" in text
        assert "rc=127" in text

    def test_skipped_placeholder_explains_why(self, tmp_path):
        zf = _bundle(
            tmp_path,
            {"switch_config": "skipped"},
            {"switch_config": "Step 1 (Discover Switches): No switches registered in VMS"},
        )
        text = zf.read("switches/switch_config_SKIPPED.txt").decode()
        assert "No switches registered in VMS" in text
        assert "not selected" not in text

    def test_skipped_without_reason_keeps_not_selected_wording(self, tmp_path):
        zf = _bundle(tmp_path, {"switch_config": "skipped"})
        assert "not selected" in zf.read("switches/switch_config_SKIPPED.txt").decode()


class TestOperationLogInBundle:
    def test_operation_log_is_bundled_and_listed(self, tmp_path):
        entries = [
            {"timestamp": "2026-09-25T17:29:05", "level": "warn", "message": "Command exited with code 127"},
            {"timestamp": "2026-09-25T18:29:57", "level": "info", "message": "SSH command timed out after 3600s"},
        ]
        zf = _bundle(tmp_path, {"vperfsanity": "failed"}, operation_log=entries)
        names = zf.namelist()
        assert "diagnostics/operation_log.jsonl" in names
        lines = zf.read("diagnostics/operation_log.jsonl").decode().strip().splitlines()
        assert json.loads(lines[1])["message"] == "SSH command timed out after 3600s"
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["files"]["operation_log"] == "operation_log.jsonl"
        assert "operation_log.jsonl" in zf.read("performance/vperfsanity_FAILED.txt").decode()

    def test_operation_details_in_manifest(self, tmp_path):
        zf = _bundle(tmp_path, {"vperfsanity": "failed"}, {"vperfsanity": "Step 4 (Run Performance Tests): timed out"})
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["operation_details"]["vperfsanity"].startswith("Step 4")
