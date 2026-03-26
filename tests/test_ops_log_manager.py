"""Tests for OpsLogManager — persistent operation log storage."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from utils.ops_log_manager import OpsLogManager


class TestOpsLogManagerSave(unittest.TestCase):
    """Test session log saving."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.mgr = OpsLogManager(log_dir=self.tmpdir, max_bytes=10_000)

    def test_save_creates_jsonl_file(self):
        entries = [{"level": "info", "message": "test"}, {"level": "warn", "message": "warning"}]
        path = self.mgr.save_session_log(entries, "sess123", "10.0.0.1")
        self.assertTrue(path.exists())
        self.assertTrue(path.name.endswith(".jsonl"))
        self.assertIn("10_0_0_1", path.name)

        lines = path.read_text().strip().split("\n")
        self.assertEqual(len(lines), 2)
        parsed = json.loads(lines[0])
        self.assertEqual(parsed["message"], "test")

    def test_save_unknown_cluster(self):
        path = self.mgr.save_session_log([{"msg": "a"}], "s1", "")
        self.assertIn("unknown", path.name)


class TestOpsLogManagerCapacity(unittest.TestCase):
    """Test capacity checking and purge."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.mgr = OpsLogManager(log_dir=self.tmpdir, max_bytes=500)

    def _create_fake_log(self, name, size_bytes):
        p = self.tmpdir / name
        p.write_text("x" * size_bytes)
        return p

    def test_check_capacity_empty(self):
        cap = self.mgr.check_capacity()
        self.assertEqual(cap["total_bytes"], 0)
        self.assertEqual(cap["file_count"], 0)
        self.assertFalse(cap["over_limit"])

    def test_check_capacity_over_limit(self):
        self._create_fake_log("a.jsonl", 300)
        self._create_fake_log("b.jsonl", 300)
        cap = self.mgr.check_capacity()
        self.assertTrue(cap["over_limit"])
        self.assertEqual(cap["file_count"], 2)

    def test_purge_oldest_removes_files(self):
        import time

        self._create_fake_log("old.jsonl", 200)
        time.sleep(0.05)
        self._create_fake_log("new.jsonl", 200)
        result = self.mgr.purge_oldest()
        self.assertEqual(result["purged"], 1)
        self.assertFalse((self.tmpdir / "old.jsonl").exists())
        self.assertTrue((self.tmpdir / "new.jsonl").exists())

    def test_purge_empty_dir(self):
        result = self.mgr.purge_oldest()
        self.assertEqual(result["purged"], 0)

    def test_ensure_capacity_triggers_purge(self):
        self._create_fake_log("a.jsonl", 300)
        self._create_fake_log("b.jsonl", 300)
        warnings = []

        def emit_fn(level, msg):
            warnings.append((level, msg))

        purged = self.mgr.ensure_capacity(emit_fn=emit_fn)
        self.assertTrue(purged)
        self.assertTrue(any("Purging" in m for _, m in warnings))

    def test_ensure_capacity_no_purge_needed(self):
        self._create_fake_log("a.jsonl", 100)
        purged = self.mgr.ensure_capacity()
        self.assertFalse(purged)


class TestOpsLogManagerList(unittest.TestCase):
    """Test log listing."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp())
        self.mgr = OpsLogManager(log_dir=self.tmpdir)

    def test_list_logs_empty(self):
        logs = self.mgr.list_logs()
        self.assertEqual(len(logs), 0)

    def test_list_logs_with_files(self):
        (self.tmpdir / "a.jsonl").write_text('{"msg": "a"}\n')
        (self.tmpdir / "b.jsonl").write_text('{"msg": "b"}\n{"msg": "c"}\n')
        logs = self.mgr.list_logs()
        self.assertEqual(len(logs), 2)
        names = [entry["filename"] for entry in logs]
        self.assertIn("a.jsonl", names)
        self.assertIn("b.jsonl", names)
        b_log = next(entry for entry in logs if entry["filename"] == "b.jsonl")
        self.assertEqual(b_log["entry_count"], 2)


if __name__ == "__main__":
    unittest.main()
