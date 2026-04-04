"""Tests for the OneShotRunner module."""

import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestOneShotPrevalidation(unittest.TestCase):
    """Pre-validation check tests."""

    def _make_runner(self, ops=None, creds=None, **kwargs):
        from oneshot_runner import OneShotRunner

        return OneShotRunner(
            selected_ops=ops or ["vnetmap"],
            credentials=creds
            or {
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            },
            **kwargs,
        )

    def test_all_pass_scenario(self):
        """All checks pass when credentials are complete and services reachable."""
        runner = self._make_runner()
        with (
            patch("oneshot_runner._requests_lib.get") as mock_get,
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "cnode1", "")),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            mock_get.return_value = MagicMock(status_code=200)
            mock_tm_instance = MagicMock()
            mock_tm_instance.get_all_tools_info.return_value = []
            MockTM.return_value = mock_tm_instance
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            results = runner.run_prevalidation()

        statuses = [r["status"] for r in results]
        self.assertNotIn("fail", statuses)

    def test_missing_cluster_ip(self):
        runner = self._make_runner(
            creds={
                "cluster_ip": "",
                "username": "admin",
                "password": "pass",
            }
        )
        results = runner.run_prevalidation()
        cred_check = next(r for r in results if r["name"] == "Credentials")
        self.assertEqual(cred_check["status"], "fail")
        self.assertIn("Cluster IP", cred_check["message"])

    def test_missing_api_credentials(self):
        runner = self._make_runner(
            creds={
                "cluster_ip": "10.0.0.1",
                "username": "",
                "password": "",
            }
        )
        results = runner.run_prevalidation()
        cred_check = next(r for r in results if r["name"] == "Credentials")
        self.assertEqual(cred_check["status"], "fail")

    def test_missing_node_ssh_for_ssh_ops(self):
        runner = self._make_runner(
            ops=["vnetmap"],
            creds={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_password": "",
            },
        )
        results = runner.run_prevalidation()
        cred_check = next(r for r in results if r["name"] == "Credentials")
        self.assertEqual(cred_check["status"], "fail")
        self.assertIn("Node SSH", cred_check["message"])

    def test_missing_switch_ssh_for_switch_ops(self):
        runner = self._make_runner(
            ops=["switch_config"],
            creds={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_password": "",
            },
        )
        results = runner.run_prevalidation()
        cred_check = next(r for r in results if r["name"] == "Credentials")
        self.assertEqual(cred_check["status"], "fail")
        self.assertIn("Switch SSH", cred_check["message"])

    def test_cluster_api_unreachable(self):
        import requests

        runner = self._make_runner()
        with patch("oneshot_runner._requests_lib.get", side_effect=requests.ConnectionError("timeout")):
            results = runner.run_prevalidation()
        api_check = next(r for r in results if r["name"] == "Cluster API")
        self.assertEqual(api_check["status"], "fail")

    def test_node_ssh_failure_is_warning(self):
        runner = self._make_runner()
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", side_effect=Exception("SSH timeout")),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            results = runner.run_prevalidation()

        node_check = next(r for r in results if r["name"] == "Node SSH")
        self.assertEqual(node_check["status"], "warn")

    def test_internet_check_skipped_for_non_download_ops(self):
        """Internet check not included when only switch_config/network_config selected."""
        runner = self._make_runner(
            ops=["switch_config", "network_config"],
            creds={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            },
        )
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "node1", "")),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            results = runner.run_prevalidation()

        names = [r["name"] for r in results]
        self.assertNotIn("Internet Access", names)

    def test_internet_check_included_for_download_ops(self):
        """Internet check included when vnetmap is selected."""
        runner = self._make_runner(ops=["vnetmap"])
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "HTTP/2 200", "")),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            results = runner.run_prevalidation()

        names = [r["name"] for r in results]
        self.assertIn("Internet Access", names)

    def test_internet_failure_warns(self):
        """Internet access failure produces a warning, not a hard fail."""
        runner = self._make_runner(ops=["vperfsanity"])

        call_count = {"n": 0}

        def ssh_side_effect(*args, **kwargs):
            call_count["n"] += 1
            cmd = args[3] if len(args) > 3 else kwargs.get("command", "")
            if "curl" in str(cmd):
                return (1, "", "Connection refused")
            return (0, "node1", "")

        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", side_effect=ssh_side_effect),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = []
            mock_api_factory.return_value = mock_api

            results = runner.run_prevalidation()

        inet_check = next(r for r in results if r["name"] == "Internet Access")
        self.assertEqual(inet_check["status"], "warn")

    def test_tool_freshness_stale_warns(self):
        """Tools older than 10 days produce a warning."""
        from datetime import datetime, timedelta

        runner = self._make_runner(
            ops=["switch_config", "network_config"],
            creds={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            },
        )
        old_date = (datetime.now() - timedelta(days=15)).isoformat()
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "ok", "")),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = [
                {"name": "vnetmap.py", "cached": True, "cached_date": old_date},
            ]
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            results = runner.run_prevalidation()

        tool_check = next(r for r in results if r["name"] == "Tool Freshness")
        self.assertEqual(tool_check["status"], "warn")
        self.assertIn("15d", tool_check["message"])

    def test_vperfsanity_duration_info(self):
        """Selecting vperfsanity adds an info-level duration notice."""
        runner = self._make_runner(ops=["vperfsanity"])
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "HTTP/2 200", "")),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = []
            mock_api_factory.return_value = mock_api

            results = runner.run_prevalidation()

        perf_check = next(r for r in results if r["name"] == "vperfsanity Duration")
        self.assertEqual(perf_check["status"], "info")
        self.assertIn("30 minutes", perf_check["message"])


class TestOneShotExecution(unittest.TestCase):
    """Sequential execution tests."""

    def _make_runner(self, ops=None, include_report=False, cancel_event=None):
        from oneshot_runner import OneShotRunner

        return OneShotRunner(
            selected_ops=ops or ["switch_config"],
            credentials={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            },
            include_report=include_report,
            cancel_event=cancel_event,
        )

    @patch("result_bundler.ResultBundler")
    @patch("workflows.WorkflowRegistry")
    @patch("api_handler.create_vast_api_handler")
    def test_operations_and_bundling_run(self, mock_api_factory, MockWR, MockBundler):
        """Operations and bundling execute in sequence."""
        mock_api = MagicMock()
        mock_api_factory.return_value = mock_api

        mock_wf = MagicMock()
        mock_wf.get_steps.return_value = [{"id": 1, "name": "Step 1"}]
        mock_wf.run_step.return_value = {"success": True, "message": "Done"}
        mock_wf.name = "Switch Config"
        MockWR.get.return_value = mock_wf

        mock_bundler = MagicMock()
        mock_bundler.create_bundle.return_value = Path("/tmp/test.zip")
        MockBundler.return_value = mock_bundler

        runner = self._make_runner(ops=["switch_config"])
        with patch("utils.get_data_dir", return_value=Path("/tmp")):
            result = runner.run_all()

        self.assertEqual(result["status"], "completed")
        MockWR.get.assert_called_with("switch_config")

    @patch("result_bundler.ResultBundler")
    @patch("workflows.WorkflowRegistry")
    @patch("health_checker.HealthChecker")
    @patch("api_handler.create_vast_api_handler")
    def test_operations_run_in_order(self, mock_api_factory, MockHC, MockWR, MockBundler):
        """Operations execute in the order specified."""
        mock_api = MagicMock()
        mock_api_factory.return_value = mock_api
        MockHC.return_value.run_all_checks.return_value = MagicMock(summary={"pass": 1, "fail": 0, "warning": 0})

        order = []

        def make_wf(name):
            wf = MagicMock()
            wf.name = name
            wf.get_steps.return_value = [{"id": 1, "name": "S1"}]
            wf.run_step.side_effect = lambda sid: (order.append(name), {"success": True, "message": "ok"})[1]
            return wf

        MockWR.get.side_effect = lambda wid: make_wf(wid)
        MockBundler.return_value.create_bundle.return_value = Path("/tmp/test.zip")

        runner = self._make_runner(ops=["vnetmap", "switch_config", "network_config"])
        with patch("utils.get_data_dir", return_value=Path("/tmp")):
            runner.run_all()

        self.assertEqual(order, ["vnetmap", "switch_config", "network_config"])

    @patch("result_bundler.ResultBundler")
    @patch("workflows.WorkflowRegistry")
    @patch("health_checker.HealthChecker")
    @patch("api_handler.create_vast_api_handler")
    def test_cancellation_between_operations(self, mock_api_factory, MockHC, MockWR, MockBundler):
        """Cancellation stops execution between operations."""
        mock_api = MagicMock()
        mock_api_factory.return_value = mock_api
        MockHC.return_value.run_all_checks.return_value = MagicMock(summary={"pass": 1, "fail": 0, "warning": 0})

        cancel_event = threading.Event()

        def cancel_after_first(wid):
            wf = MagicMock()
            wf.name = wid
            wf.get_steps.return_value = [{"id": 1, "name": "S1"}]

            def run_and_cancel(sid):
                cancel_event.set()
                return {"success": True, "message": "ok"}

            wf.run_step.side_effect = run_and_cancel
            return wf

        MockWR.get.side_effect = cancel_after_first
        MockBundler.return_value.create_bundle.return_value = Path("/tmp/test.zip")

        runner = self._make_runner(ops=["vnetmap", "switch_config"], cancel_event=cancel_event)
        with patch("utils.get_data_dir", return_value=Path("/tmp")):
            result = runner.run_all()

        self.assertEqual(result["status"], "cancelled")

    @patch("result_bundler.ResultBundler")
    @patch("workflows.WorkflowRegistry")
    @patch("health_checker.HealthChecker")
    @patch("api_handler.create_vast_api_handler")
    def test_bundle_passes_cluster_ip(self, mock_api_factory, MockHC, MockWR, MockBundler):
        """Auto-bundling passes cluster_ip to ResultBundler."""
        mock_api = MagicMock()
        mock_api_factory.return_value = mock_api
        MockHC.return_value.run_all_checks.return_value = MagicMock(summary={"pass": 1, "fail": 0, "warning": 0})

        mock_wf = MagicMock()
        mock_wf.name = "test"
        mock_wf.get_steps.return_value = [{"id": 1, "name": "S1"}]
        mock_wf.run_step.return_value = {"success": True, "message": "ok"}
        MockWR.get.return_value = mock_wf

        mock_bundler = MagicMock()
        mock_bundler.create_bundle.return_value = Path("/tmp/test.zip")
        MockBundler.return_value = mock_bundler

        runner = self._make_runner(ops=["switch_config"])
        with patch("utils.get_data_dir", return_value=Path("/tmp")):
            runner.run_all()

        mock_bundler.collect_results.assert_called_once_with(cluster_ip="10.0.0.1")

    @patch("result_bundler.ResultBundler")
    @patch("report_builder.create_report_builder")
    @patch("data_extractor.create_data_extractor")
    @patch("workflows.WorkflowRegistry")
    @patch("health_checker.HealthChecker")
    @patch("api_handler.create_vast_api_handler")
    def test_report_phase_runs_when_flag_set(self, mock_api_factory, MockHC, MockWR, MockDE, MockRB, MockBundler):
        """Report phase executes when include_report=True."""
        mock_api = MagicMock()
        mock_api.get_all_data.return_value = {"clusters": []}
        mock_api_factory.return_value = mock_api
        MockHC.return_value.run_all_checks.return_value = MagicMock(summary={"pass": 1, "fail": 0, "warning": 0})

        MockWR.get.return_value = None

        mock_extractor = MagicMock()
        mock_extractor.extract_all_data.return_value = {"cluster_summary": {"name": "testcluster"}}
        MockDE.return_value = mock_extractor

        mock_builder = MagicMock()
        mock_builder.generate_pdf_report.return_value = True
        MockRB.return_value = mock_builder

        MockBundler.return_value.create_bundle.return_value = Path("/tmp/test.zip")

        runner = self._make_runner(ops=[], include_report=True)
        with (
            patch("utils.get_data_dir", return_value=Path("/tmp")),
            patch("report_builder.ReportConfig") as MockRC,
        ):
            MockRC.from_yaml.return_value = MagicMock()
            result = runner.run_all()

        self.assertEqual(result["status"], "completed")
        mock_builder.generate_pdf_report.assert_called_once()


class TestOneShotStateTracking(unittest.TestCase):
    """Progress state tracking tests."""

    def test_initial_state_is_idle(self):
        from oneshot_runner import OneShotRunner

        runner = OneShotRunner(
            selected_ops=["vnetmap"],
            credentials={"cluster_ip": "10.0.0.1", "username": "admin", "password": "pass"},
        )
        state = runner.get_state()
        self.assertEqual(state["phase"], "idle")
        self.assertEqual(state["status"], "idle")

    def test_state_transitions_during_validation(self):
        from oneshot_runner import OneShotRunner

        runner = OneShotRunner(
            selected_ops=["switch_config"],
            credentials={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            },
        )
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "ok", "")),
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            runner.run_prevalidation()

        state = runner.get_state()
        self.assertIsNotNone(state["validation_results"])
        self.assertGreater(len(state["validation_results"]), 0)

    @patch("result_bundler.ResultBundler")
    @patch("workflows.WorkflowRegistry")
    @patch("health_checker.HealthChecker")
    @patch("api_handler.create_vast_api_handler")
    def test_completed_state(self, mock_api_factory, MockHC, MockWR, MockBundler):
        from oneshot_runner import OneShotRunner

        mock_api = MagicMock()
        mock_api_factory.return_value = mock_api
        MockHC.return_value.run_all_checks.return_value = MagicMock(summary={"pass": 1, "fail": 0, "warning": 0})
        MockWR.get.return_value = None
        MockBundler.return_value.create_bundle.return_value = Path("/tmp/test.zip")

        runner = OneShotRunner(
            selected_ops=[],
            credentials={"cluster_ip": "10.0.0.1", "username": "admin", "password": "pass"},
        )
        with patch("utils.get_data_dir", return_value=Path("/tmp")):
            runner.run_all()

        state = runner.get_state()
        self.assertEqual(state["status"], "completed")
        self.assertIsNotNone(state["started_at"])
        self.assertIsNotNone(state["completed_at"])

    def test_cancel_method(self):
        from oneshot_runner import OneShotRunner

        cancel_event = threading.Event()
        runner = OneShotRunner(
            selected_ops=["vnetmap"],
            credentials={"cluster_ip": "10.0.0.1", "username": "admin", "password": "pass"},
            cancel_event=cancel_event,
        )
        result = runner.cancel()
        self.assertTrue(result)
        self.assertTrue(cancel_event.is_set())


class TestOneShotErrorHandling(unittest.TestCase):
    """Error handling during execution."""

    @patch("result_bundler.ResultBundler")
    @patch("workflows.WorkflowRegistry")
    @patch("health_checker.HealthChecker")
    @patch("api_handler.create_vast_api_handler")
    def test_workflow_step_failure_continues_to_next(self, mock_api_factory, MockHC, MockWR, MockBundler):
        """A failed workflow step skips to the next operation, not hard-fail."""
        mock_api = MagicMock()
        mock_api_factory.return_value = mock_api
        MockHC.return_value.run_all_checks.return_value = MagicMock(summary={"pass": 1, "fail": 0, "warning": 0})

        executed = []

        def make_wf(wid):
            wf = MagicMock()
            wf.name = wid
            wf.get_steps.return_value = [{"id": 1, "name": "S1"}, {"id": 2, "name": "S2"}]
            if wid == "vnetmap":
                wf.run_step.return_value = {"success": False, "message": "Connection refused"}
            else:

                def run_ok(sid):
                    executed.append(f"{wid}:{sid}")
                    return {"success": True, "message": "ok"}

                wf.run_step.side_effect = run_ok
            return wf

        MockWR.get.side_effect = make_wf
        MockBundler.return_value.create_bundle.return_value = Path("/tmp/test.zip")

        from oneshot_runner import OneShotRunner

        runner = OneShotRunner(
            selected_ops=["vnetmap", "switch_config"],
            credentials={"cluster_ip": "10.0.0.1", "username": "admin", "password": "pass"},
        )
        with patch("utils.get_data_dir", return_value=Path("/tmp")):
            result = runner.run_all()

        self.assertEqual(result["status"], "completed")
        self.assertIn("switch_config:1", executed)

    @patch("health_checker.HealthChecker")
    @patch("api_handler.create_vast_api_handler")
    def test_health_check_failure_is_non_blocking(self, mock_api_factory, MockHC):
        """Health check failure doesn't prevent operations from running."""
        mock_api = MagicMock()
        mock_api_factory.return_value = mock_api
        MockHC.return_value.run_all_checks.side_effect = Exception("API down")

        from oneshot_runner import OneShotRunner

        runner = OneShotRunner(
            selected_ops=[],
            credentials={"cluster_ip": "10.0.0.1", "username": "admin", "password": "pass"},
        )
        with (
            patch("result_bundler.ResultBundler") as MockBundler,
            patch("utils.get_data_dir", return_value=Path("/tmp")),
        ):
            MockBundler.return_value.create_bundle.return_value = Path("/tmp/test.zip")
            result = runner.run_all()

        self.assertEqual(result["status"], "completed")


class TestOneShotIncludeHealth(unittest.TestCase):
    """include_health flag behavior for run_all and prevalidation."""

    _CREDS = {
        "cluster_ip": "10.0.0.1",
        "username": "admin",
        "password": "pass",
        "node_user": "vastdata",
        "node_password": "pass",
        "switch_user": "cumulus",
        "switch_password": "pass",
    }

    def _make_runner(self, ops=None, include_health=True, include_report=False):
        from oneshot_runner import OneShotRunner

        if ops is None:
            ops = ["switch_config"]
        return OneShotRunner(
            selected_ops=ops,
            credentials=dict(self._CREDS),
            include_report=include_report,
            include_health=include_health,
        )

    def test_run_all_phases_ops_and_bundling(self):
        """run_all always runs operations and bundling."""
        runner = self._make_runner(ops=["switch_config"], include_health=False)
        with (
            patch.object(runner, "_run_operations") as mock_ops,
            patch.object(runner, "_run_bundling") as mock_bundle,
        ):
            runner.run_all()

        mock_ops.assert_called_once()
        mock_bundle.assert_called_once()

    def test_run_all_with_report_calls_run_report(self):
        """When include_report=True, _run_report is called."""
        runner = self._make_runner(ops=["switch_config"], include_health=True, include_report=True)
        with (
            patch.object(runner, "_run_operations"),
            patch.object(runner, "_run_report") as mock_report,
            patch.object(runner, "_run_bundling"),
        ):
            runner.run_all()

        mock_report.assert_called_once()

    def test_total_operations_without_report(self):
        """total_operations = workflows + bundling when report is off."""
        from oneshot_runner import OneShotRunner

        ops = ["vnetmap", "switch_config"]
        runner = OneShotRunner(
            selected_ops=ops,
            credentials=dict(self._CREDS),
            include_health=False,
            include_report=False,
        )
        with (
            patch.object(runner, "_run_operations"),
            patch.object(runner, "_run_bundling"),
        ):
            runner.run_all()
        self.assertEqual(runner.get_state()["total_operations"], 3)

    def test_total_operations_with_report(self):
        """total_operations = workflows + report + bundling when report is on."""
        from oneshot_runner import OneShotRunner

        ops = ["vnetmap", "switch_config"]
        runner = OneShotRunner(
            selected_ops=ops,
            credentials=dict(self._CREDS),
            include_health=True,
            include_report=True,
        )
        with (
            patch.object(runner, "_run_operations"),
            patch.object(runner, "_run_report"),
            patch.object(runner, "_run_bundling"),
        ):
            runner.run_all()
        self.assertEqual(runner.get_state()["total_operations"], 4)

    def test_prevalidation_skips_ssh_when_no_health_and_no_ssh_ops(self):
        """No node/switch SSH validation when health is off and no SSH-dependent ops."""
        runner = self._make_runner(ops=[], include_health=False)
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch.object(runner, "_validate_node_ssh") as mock_node,
            patch.object(runner, "_validate_switch_ssh") as mock_sw,
            patch("tool_manager.ToolManager") as MockTM,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            runner.run_prevalidation()

        mock_node.assert_not_called()
        mock_sw.assert_not_called()

    def test_prevalidation_includes_ssh_when_health_and_report_selected(self):
        """include_health=True + include_report=True runs node and switch SSH checks."""
        runner = self._make_runner(ops=[], include_health=True, include_report=True)
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "host1", "")),
            patch.object(runner, "_validate_node_ssh", wraps=runner._validate_node_ssh) as mock_node,
            patch.object(runner, "_validate_switch_ssh", wraps=runner._validate_switch_ssh) as mock_sw,
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            runner.run_prevalidation()

        mock_node.assert_called()
        mock_sw.assert_called()


class TestLogTierEmission(unittest.TestCase):
    """Tests for log tier tagging on output entries."""

    def test_emit_sends_status_tier(self):
        from oneshot_runner import OneShotRunner

        collected = []

        def callback(level, msg, details=None, log_tier="status"):
            collected.append({"level": level, "message": msg, "log_tier": log_tier})

        runner = OneShotRunner.__new__(OneShotRunner)
        runner._output_callback = callback
        runner._emit("info", "test status")
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["log_tier"], "status")

    def test_emit_live_sends_live_tier(self):
        from oneshot_runner import OneShotRunner

        collected = []

        def callback(level, msg, details=None, log_tier="status"):
            collected.append({"level": level, "message": msg, "log_tier": log_tier})

        runner = OneShotRunner.__new__(OneShotRunner)
        runner._output_callback = callback
        runner._emit_live("info", "live message")
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["log_tier"], "live")

    def test_emit_debug_sends_debug_tier(self):
        from oneshot_runner import OneShotRunner

        collected = []

        def callback(level, msg, details=None, log_tier="status"):
            collected.append({"level": level, "message": msg, "log_tier": log_tier})

        runner = OneShotRunner.__new__(OneShotRunner)
        runner._output_callback = callback
        runner._emit_debug("info", "debug message")
        self.assertEqual(len(collected), 1)
        self.assertEqual(collected[0]["log_tier"], "debug")


class TestOneShotLogHandler(unittest.TestCase):
    """Tests for the _OneShotLogHandler routing."""

    def test_handler_routes_info_as_live(self):
        import logging

        from oneshot_runner import _OneShotLogHandler

        collected = []

        def cb(level, msg, details=None, log_tier="status"):
            collected.append({"level": level, "log_tier": log_tier, "msg": msg})

        handler = _OneShotLogHandler(cb)
        test_logger = logging.getLogger("test_handler_routes")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        test_logger.info("info message")
        test_logger.debug("debug message")
        test_logger.warning("warn message")

        test_logger.removeHandler(handler)

        live_entries = [e for e in collected if e["log_tier"] == "live"]
        debug_entries = [e for e in collected if e["log_tier"] == "debug"]
        self.assertTrue(len(live_entries) >= 2)
        self.assertTrue(len(debug_entries) >= 1)


class TestCredentialRouting(unittest.TestCase):
    """Tests for per-phase credential routing with default creds.

    Default behaviour: support/654321 everywhere except vperfsanity
    which gets admin/123456.
    """

    def _make_runner(self, use_default_creds=False, creds=None):
        from oneshot_runner import OneShotRunner

        default_creds = {
            "cluster_ip": "10.0.0.1",
            "username": "support",
            "password": "654321",
            "node_user": "vastdata",
            "node_password": "vastdata",
            "switch_user": "cumulus",
            "switch_password": "Vastdata1!",
        }
        return OneShotRunner(
            selected_ops=["vnetmap"],
            credentials=creds or default_creds,
            use_default_creds=use_default_creds,
        )

    def test_default_creds_health_uses_support(self):
        runner = self._make_runner(use_default_creds=True)
        creds = runner._get_api_creds("health_checks")
        self.assertEqual(creds["username"], "support")
        self.assertEqual(creds["password"], "654321")

    def test_default_creds_report_uses_support(self):
        runner = self._make_runner(use_default_creds=True)
        creds = runner._get_api_creds("report")
        self.assertEqual(creds["username"], "support")
        self.assertEqual(creds["password"], "654321")

    def test_default_creds_vperfsanity_uses_admin(self):
        runner = self._make_runner(use_default_creds=True)
        creds = runner._get_api_creds("vperfsanity")
        self.assertEqual(creds["username"], "admin")
        self.assertEqual(creds["password"], "123456")

    def test_default_creds_other_ops_use_support(self):
        runner = self._make_runner(use_default_creds=True)
        for phase in ("operations", "vnetmap", "switch_config"):
            creds = runner._get_api_creds(phase)
            self.assertEqual(creds["username"], "support")
            self.assertEqual(creds["password"], "654321")

    def test_no_default_creds_uses_provided(self):
        runner = self._make_runner(use_default_creds=False)
        for phase in ("health_checks", "report", "vperfsanity"):
            creds = runner._get_api_creds(phase)
            self.assertEqual(creds["username"], "support")
            self.assertEqual(creds["password"], "654321")

    def test_custom_creds_not_overridden(self):
        custom = {
            "cluster_ip": "10.0.0.1",
            "username": "myuser",
            "password": "mypass",
        }
        runner = self._make_runner(use_default_creds=False, creds=custom)
        for phase in ("health_checks", "report", "vperfsanity"):
            creds = runner._get_api_creds(phase)
            self.assertEqual(creds["username"], "myuser")

    def test_workflow_creds_vperfsanity_override(self):
        runner = self._make_runner(use_default_creds=True)
        wf_creds = runner._get_workflow_credentials("vperfsanity")
        self.assertEqual(wf_creds["username"], "admin")
        self.assertEqual(wf_creds["password"], "123456")
        self.assertEqual(wf_creds["node_user"], "vastdata")

    def test_workflow_creds_other_op_unchanged(self):
        runner = self._make_runner(use_default_creds=True)
        wf_creds = runner._get_workflow_credentials("vnetmap")
        self.assertEqual(wf_creds["username"], "support")
        self.assertEqual(wf_creds["password"], "654321")


if __name__ == "__main__":
    unittest.main()
