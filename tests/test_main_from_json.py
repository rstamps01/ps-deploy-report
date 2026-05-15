"""
Unit tests for the ``--from-json`` offline replay CLI flag.

Covers DEV-1 (partial) — durable infrastructure for regenerating PDF
reports from saved ``vast_data_*.json`` intermediates without touching
the API + Data Extractor layers.  Used as the verification rail for
SR-3 / SR-4 fixes when live cluster access is unavailable.

Author: VAST Professional Services
"""

import json
import logging
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import _run_from_json, main, run_from_json  # noqa: E402

# Path to the MVP baseline JSON intermediate (tracked in git via
# reports/MVP/) — used as the real end-to-end fixture so the offline
# replay path is exercised against an actual extracted-cluster shape.
_MVP_FIXTURE = (
    Path(__file__).parent.parent
    / "reports"
    / "MVP"
    / "vast_asbuilt_report_MVP_baseline_selab-var-204"
    / "vast_data_selab-var-204_20251017_084623.json"
)


def _make_logger() -> logging.Logger:
    """Return a quiet logger that doesn't pollute pytest output."""
    logger = logging.getLogger(f"test_from_json.{id(object())}")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    return logger


class TestRunFromJsonErrorPaths(unittest.TestCase):
    """Error-path coverage for the ``_run_from_json`` helper."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="from_json_test_")
        self.tmp_dir = Path(self.tmp.name)
        self.logger = _make_logger()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_missing_json_file_returns_1(self) -> None:
        missing = self.tmp_dir / "does_not_exist.json"
        rc = _run_from_json(str(missing), str(self.tmp_dir), self.logger)
        self.assertEqual(rc, 1)

    def test_malformed_json_returns_1(self) -> None:
        bad = self.tmp_dir / "broken.json"
        bad.write_text("{ this is not valid json")
        rc = _run_from_json(str(bad), str(self.tmp_dir), self.logger)
        self.assertEqual(rc, 1)

    def test_non_dict_root_returns_1(self) -> None:
        # ``processed_data`` must be a dict — a JSON list at the root
        # cannot satisfy the ``cluster_summary.name`` lookup or the
        # report builder contract.
        bad = self.tmp_dir / "list_root.json"
        bad.write_text(json.dumps([{"foo": "bar"}]))
        rc = _run_from_json(str(bad), str(self.tmp_dir), self.logger)
        self.assertEqual(rc, 1)

    def test_report_builder_returns_false_returns_1(self) -> None:
        good = self.tmp_dir / "good.json"
        good.write_text(json.dumps({"cluster_summary": {"name": "test"}}))
        with patch("main.create_report_builder") as builder_factory:
            builder = MagicMock()
            builder.generate_pdf_report.return_value = False
            builder_factory.return_value = builder
            rc = _run_from_json(str(good), str(self.tmp_dir), self.logger)
        self.assertEqual(rc, 1)

    def test_report_builder_raises_returns_1(self) -> None:
        good = self.tmp_dir / "good.json"
        good.write_text(json.dumps({"cluster_summary": {"name": "test"}}))
        with patch("main.create_report_builder") as builder_factory:
            builder = MagicMock()
            builder.generate_pdf_report.side_effect = RuntimeError("boom")
            builder_factory.return_value = builder
            rc = _run_from_json(str(good), str(self.tmp_dir), self.logger)
        self.assertEqual(rc, 1)


class TestRunFromJsonSuccess(unittest.TestCase):
    """Success-path coverage with a mocked report builder."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="from_json_test_")
        self.tmp_dir = Path(self.tmp.name)
        self.logger = _make_logger()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_minimal_processed_data_calls_report_builder_and_returns_0(self) -> None:
        good = self.tmp_dir / "good.json"
        processed = {
            "cluster_summary": {"name": "selab-var-204"},
            "metadata": {"overall_completeness": 1.0},
            "sections": {},
        }
        good.write_text(json.dumps(processed))

        with patch("main.create_report_builder") as builder_factory:
            builder = MagicMock()
            builder.generate_pdf_report.return_value = True
            builder_factory.return_value = builder
            rc = _run_from_json(str(good), str(self.tmp_dir), self.logger)

        self.assertEqual(rc, 0)
        builder.generate_pdf_report.assert_called_once()
        call_args, _kwargs = builder.generate_pdf_report.call_args
        # First positional arg is the loaded processed_data dict
        self.assertEqual(call_args[0]["cluster_summary"]["name"], "selab-var-204")
        # Second positional arg is the absolute output PDF path,
        # under tmp_dir, with the cluster name embedded
        out_path = Path(call_args[1])
        self.assertTrue(str(out_path).startswith(str(self.tmp_dir)))
        self.assertIn("selab-var-204", out_path.name)
        self.assertTrue(out_path.name.endswith(".pdf"))

    def test_creates_output_dir_if_missing(self) -> None:
        good = self.tmp_dir / "good.json"
        good.write_text(json.dumps({"cluster_summary": {"name": "x"}}))
        new_out = self.tmp_dir / "nested" / "out_dir"
        self.assertFalse(new_out.exists())

        with patch("main.create_report_builder") as builder_factory:
            builder = MagicMock()
            builder.generate_pdf_report.return_value = True
            builder_factory.return_value = builder
            rc = _run_from_json(str(good), str(new_out), self.logger)

        self.assertEqual(rc, 0)
        self.assertTrue(new_out.is_dir())

    def test_unknown_cluster_name_falls_back_to_unknown(self) -> None:
        # If cluster_summary is absent or missing 'name', filename must
        # still be deterministic so operators can locate the artifact.
        good = self.tmp_dir / "good.json"
        good.write_text(json.dumps({"sections": {}}))

        with patch("main.create_report_builder") as builder_factory:
            builder = MagicMock()
            builder.generate_pdf_report.return_value = True
            builder_factory.return_value = builder
            rc = _run_from_json(str(good), str(self.tmp_dir), self.logger)

        self.assertEqual(rc, 0)
        out_path = Path(builder.generate_pdf_report.call_args[0][1])
        self.assertIn("unknown", out_path.name)


class TestRunFromJsonEndToEnd(unittest.TestCase):
    """Real-fixture round-trip through the report builder.

    Skipped in environments where the MVP baseline JSON isn't checked
    out (e.g. shallow CI clones), but treated as the canonical
    regression for offline replay against a real extracted shape.
    """

    @unittest.skipUnless(_MVP_FIXTURE.exists(), f"MVP fixture not present: {_MVP_FIXTURE}")
    def test_end_to_end_pdf_generated_from_mvp_baseline(self) -> None:
        with tempfile.TemporaryDirectory(prefix="from_json_e2e_") as out_dir:
            rc = _run_from_json(str(_MVP_FIXTURE), out_dir, _make_logger())
            self.assertEqual(rc, 0, "Offline replay against MVP baseline should succeed")
            pdfs = list(Path(out_dir).glob("*.pdf"))
            self.assertEqual(len(pdfs), 1, f"Expected exactly one PDF, got {pdfs}")
            self.assertGreater(pdfs[0].stat().st_size, 10_000, "PDF should be non-trivial in size")


class TestRunFromJsonArgparseWrapper(unittest.TestCase):
    """``run_from_json`` parses sys.argv and dispatches to ``_run_from_json``."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory(prefix="from_json_arg_")
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_argparse_wrapper_dispatches(self) -> None:
        good = self.tmp_dir / "good.json"
        good.write_text(json.dumps({"cluster_summary": {"name": "wrap"}}))

        argv = ["vast-reporter", "--from-json", str(good), "--output", str(self.tmp_dir)]
        with patch.object(sys, "argv", argv), patch("main._run_from_json") as inner:
            inner.return_value = 0
            rc = run_from_json()

        self.assertEqual(rc, 0)
        inner.assert_called_once()
        called_json, called_out, _called_logger = inner.call_args[0]
        self.assertEqual(called_json, str(good))
        self.assertEqual(called_out, str(self.tmp_dir))


class TestMainRoutesFromJson(unittest.TestCase):
    """Top-level ``main()`` routes ``--from-json`` to the offline replay path."""

    def test_main_routes_from_json_before_gui_or_cli(self) -> None:
        argv = ["vast-reporter", "--from-json", "/tmp/foo.json", "--output", "/tmp/out"]
        with (
            patch.object(sys, "argv", argv),
            patch("main.run_from_json") as replay,
            patch("main.run_gui") as gui,
            patch("main.run_cli") as cli,
        ):
            replay.return_value = 0
            gui.return_value = 99
            cli.return_value = 99
            rc = main()

        self.assertEqual(rc, 0)
        replay.assert_called_once()
        gui.assert_not_called()
        cli.assert_not_called()


if __name__ == "__main__":
    unittest.main()
