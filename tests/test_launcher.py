"""
Tests for the --gui / --cli mode routing in src/main.py.

Verifies that the main() entry point dispatches to the correct
function based on sys.argv, without actually starting Flask or argparse.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from main import main


class TestMainModeRouting(unittest.TestCase):
    """Verify main() routes to run_gui or run_cli based on arguments."""

    @patch("main.run_gui", return_value=0)
    def test_no_args_launches_gui(self, mock_gui):
        with patch.object(sys, "argv", ["main.py"]):
            result = main()
        mock_gui.assert_called_once()
        self.assertEqual(result, 0)

    @patch("main.run_gui", return_value=0)
    def test_gui_flag_launches_gui(self, mock_gui):
        with patch.object(sys, "argv", ["main.py", "--gui"]):
            result = main()
        mock_gui.assert_called_once()
        self.assertEqual(result, 0)

    @patch("main.run_cli", return_value=0)
    def test_cli_flag_launches_cli(self, mock_cli):
        with patch.object(sys, "argv", ["main.py", "--cli"]):
            result = main()
        mock_cli.assert_called_once()
        self.assertEqual(result, 0)

    @patch("main.run_cli", return_value=0)
    def test_cluster_arg_launches_cli(self, mock_cli):
        with patch.object(sys, "argv", ["main.py", "--cluster", "10.0.0.1", "--output", "./out"]):
            result = main()
        mock_cli.assert_called_once()
        self.assertEqual(result, 0)

    @patch("main.run_cli", return_value=0)
    def test_cluster_ip_arg_launches_cli(self, mock_cli):
        with patch.object(sys, "argv", ["main.py", "--cluster-ip", "10.0.0.1", "--output", "./out"]):
            result = main()
        mock_cli.assert_called_once()

    @patch("main.run_gui", return_value=0)
    def test_unrecognised_args_default_to_gui(self, mock_gui):
        with patch.object(sys, "argv", ["main.py", "--unknown-flag"]):
            result = main()
        mock_gui.assert_called_once()

    @patch("main.run_cli", return_value=1)
    def test_cli_failure_returns_nonzero(self, mock_cli):
        with patch.object(sys, "argv", ["main.py", "--cli"]):
            result = main()
        self.assertEqual(result, 1)


class TestRunGuiFunction(unittest.TestCase):
    """Verify run_gui starts the werkzeug server and opens a browser."""

    @patch("main.webbrowser")
    @patch("main._wait_for_server", return_value=True)
    @patch("werkzeug.serving.make_server")
    @patch("utils.logger.enable_sse_logging")
    @patch("app.create_flask_app")
    @patch("main.setup_logging")
    @patch("main.load_configuration", return_value={})
    def test_run_gui_starts_flask(self, _cfg, _log, mock_create, _sse,
                                  mock_make_server, mock_wait, mock_wb):
        mock_app = MagicMock()
        mock_app.config = {}
        mock_create.return_value = mock_app

        mock_server = MagicMock()
        mock_make_server.return_value = mock_server

        from main import run_gui
        with patch("threading.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread
            mock_thread.join.side_effect = KeyboardInterrupt
            run_gui(port=9999)

        mock_make_server.assert_called_once_with(
            "127.0.0.1", 9999, mock_app, threaded=True
        )
        mock_thread.start.assert_called_once()
        mock_server.shutdown.assert_called_once()


class TestRunCliFunction(unittest.TestCase):
    """Verify run_cli calls argparse and the report generator."""

    @patch("main.VastReportGenerator")
    @patch("main.setup_logging")
    @patch("main.load_configuration", return_value={})
    def test_run_cli_parses_args_and_runs(self, _cfg, _log, mock_gen_cls):
        mock_gen = MagicMock()
        mock_gen.run.return_value = 0
        mock_gen_cls.return_value = mock_gen

        from main import run_cli
        with patch.object(sys, "argv", ["main.py", "--cluster", "1.2.3.4", "--output", "/tmp/out"]):
            result = run_cli()

        self.assertEqual(result, 0)
        mock_gen.run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
