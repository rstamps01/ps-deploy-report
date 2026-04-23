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

        # collect_results now receives additional kwargs so the bundler can
        # reject pre-run stale files and annotate missing categories.  We
        # only care that cluster_ip is forwarded correctly.
        mock_bundler.collect_results.assert_called_once()
        kwargs = mock_bundler.collect_results.call_args.kwargs
        assert kwargs["cluster_ip"] == "10.0.0.1"
        assert "since" in kwargs
        assert kwargs["operation_status"].get("switch_config") == "success"

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


class TestSwitchPasswordCandidates(unittest.TestCase):
    """Resolve switch password candidate list for mixed-default clusters."""

    def _runner(self, credentials, use_default_creds=False, config_path=None):
        from oneshot_runner import OneShotRunner

        return OneShotRunner(
            selected_ops=["switch_config"],
            credentials=credentials,
            use_default_creds=use_default_creds,
            config_path=config_path,
        )

    def test_manual_mode_returns_single_entry_list(self):
        runner = self._runner({"cluster_ip": "10.0.0.1", "switch_password": "OnlyOne!"}, use_default_creds=False)
        self.assertEqual(runner._switch_password_candidates, ["OnlyOne!"])

    def test_autofill_promotes_entered_password_to_front(self, tmp_path=None):
        import tempfile

        # Config lists Vastdata1! first, but the operator-entered primary should come first.
        cfg_body = "advanced_operations:\n" "  default_switch_passwords:\n" "    - Vastdata1!\n" "    - VastData1!\n"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(cfg_body)
            path = f.name

        runner = self._runner(
            {"cluster_ip": "10.0.0.1", "switch_password": "VastData1!"},
            use_default_creds=True,
            config_path=path,
        )
        self.assertEqual(runner._switch_password_candidates[0], "VastData1!")
        self.assertIn("Vastdata1!", runner._switch_password_candidates)

    def test_autofill_without_config_yields_builtin_defaults(self):
        # RM-12: autofill is the operator-friendly "try the common VAST /
        # Cumulus / MLNX-OS published defaults" mode.  With no
        # ``config/config.yaml`` list and no ``VAST_DEFAULT_SWITCH_PASSWORDS``
        # env var and no UI-entered password, the candidate set must expose
        # the three built-in cumulus-user defaults in documented order
        # (``Vastdata1!`` → ``VastData1!`` → ``Cumu1usLinux!``); the
        # ``(admin, admin)`` factory default is contributed separately by
        # ``build_switch_credential_combos``.
        import os

        prev_env = os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)
        try:
            runner = self._runner(
                {"cluster_ip": "10.0.0.1", "switch_password": ""},
                use_default_creds=True,
            )
            self.assertEqual(
                runner._switch_password_candidates,
                ["Vastdata1!", "VastData1!", "Cumu1usLinux!"],
            )
        finally:
            if prev_env is not None:
                os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = prev_env

    def test_autofill_disabled_does_not_inject_builtin_defaults(self):
        # RM-12: the built-in defaults are gated on
        # ``autofill_default_passwords: true``.  With autofill OFF and
        # a UI-entered password the pool must stay a single-entry list.
        runner = self._runner(
            {"cluster_ip": "10.0.0.1", "switch_password": "OnlyOne!"},
            use_default_creds=False,
        )
        self.assertEqual(runner._switch_password_candidates, ["OnlyOne!"])

    def test_autofill_appends_builtins_after_ui_password(self):
        # RM-12: UI-entered password stays at the head (operator intent),
        # built-in defaults follow, and overlap is deduplicated.
        import os

        prev_env = os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)
        try:
            runner = self._runner(
                {"cluster_ip": "10.0.0.1", "switch_password": "SiteSpecific!"},
                use_default_creds=True,
            )
            self.assertEqual(
                runner._switch_password_candidates,
                ["SiteSpecific!", "Vastdata1!", "VastData1!", "Cumu1usLinux!"],
            )
        finally:
            if prev_env is not None:
                os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = prev_env

    def test_autofill_dedupes_ui_password_against_builtins(self):
        # RM-12: if the UI-entered password is already one of the built-in
        # defaults, it must not appear twice in the candidate list.
        import os

        prev_env = os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)
        try:
            runner = self._runner(
                {"cluster_ip": "10.0.0.1", "switch_password": "Vastdata1!"},
                use_default_creds=True,
            )
            self.assertEqual(
                runner._switch_password_candidates,
                ["Vastdata1!", "VastData1!", "Cumu1usLinux!"],
            )
        finally:
            if prev_env is not None:
                os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = prev_env

    def test_autofill_appends_builtins_after_config_list(self):
        # RM-12: a site-specific entry in ``default_switch_passwords``
        # comes before the built-ins (config is stronger-signal than a
        # generic default); no UI password set.
        import os
        import tempfile

        prev_env = os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)
        cfg_body = "advanced_operations:\n  default_switch_passwords:\n    - SiteSpecific!\n"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(cfg_body)
            path = f.name
        try:
            runner = self._runner(
                {"cluster_ip": "10.0.0.1", "switch_password": ""},
                use_default_creds=True,
                config_path=path,
            )
            self.assertEqual(
                runner._switch_password_candidates,
                ["SiteSpecific!", "Vastdata1!", "VastData1!", "Cumu1usLinux!"],
            )
        finally:
            if prev_env is not None:
                os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = prev_env

    def test_autofill_appends_builtins_after_env_var(self):
        # RM-12: env-var entries also precede the built-ins.
        import os

        prev_env = os.environ.get("VAST_DEFAULT_SWITCH_PASSWORDS", None)
        os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = "EnvPrimary!:EnvSecondary!"
        try:
            runner = self._runner(
                {"cluster_ip": "10.0.0.1", "switch_password": ""},
                use_default_creds=True,
            )
            self.assertEqual(
                runner._switch_password_candidates,
                [
                    "EnvPrimary!",
                    "EnvSecondary!",
                    "Vastdata1!",
                    "VastData1!",
                    "Cumu1usLinux!",
                ],
            )
        finally:
            if prev_env is None:
                os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)
            else:
                os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = prev_env

    def test_autofill_dedupes_builtin_already_in_config(self):
        # RM-12: config listing a built-in must not create a duplicate.
        import os
        import tempfile

        prev_env = os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)
        cfg_body = "advanced_operations:\n  default_switch_passwords:\n    - Cumu1usLinux!\n"
        with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as f:
            f.write(cfg_body)
            path = f.name
        try:
            runner = self._runner(
                {"cluster_ip": "10.0.0.1", "switch_password": ""},
                use_default_creds=True,
                config_path=path,
            )
            self.assertEqual(
                runner._switch_password_candidates,
                ["Cumu1usLinux!", "Vastdata1!", "VastData1!"],
            )
        finally:
            if prev_env is not None:
                os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = prev_env

    def test_explicit_candidates_override_autofill(self):
        runner = self._runner(
            {
                "cluster_ip": "10.0.0.1",
                "switch_password": "anything",
                "switch_password_candidates": ["X1!", "X2!"],
            },
            use_default_creds=True,
        )
        self.assertEqual(runner._switch_password_candidates, ["X1!", "X2!"])

    def test_candidates_propagate_to_workflow_credentials(self):
        runner = self._runner({"cluster_ip": "10.0.0.1", "switch_password": "A!"}, use_default_creds=True)
        creds = runner._get_workflow_credentials("switch_config")
        self.assertIn("switch_password_candidates", creds)
        self.assertEqual(creds["switch_password_candidates"][0], "A!")


class TestPrevalidationSwitchSshFallback(unittest.TestCase):
    """Pre-validation must try every candidate password on every discovered
    switch so a mixed-default cluster (3 switches across 2 factory passwords)
    does not trigger a spurious warning."""

    def _make_runner(self, candidates=None):
        from oneshot_runner import OneShotRunner

        creds = {
            "cluster_ip": "10.0.0.1",
            "username": "support",
            "password": "654321",
            "node_user": "vastdata",
            "node_password": "vastdata",
            "switch_user": "cumulus",
            "switch_password": "Vastdata1!",
        }
        if candidates is not None:
            creds["switch_password_candidates"] = list(candidates)
        return OneShotRunner(
            selected_ops=["switch_config"],
            credentials=creds,
            use_default_creds=True,
        )

    def _mock_api_with_switches(self, ips):
        api = MagicMock()
        api.authenticate.return_value = None
        api._make_api_request.return_value = [{"mgmt_ip": ip} for ip in ips]
        api.close.return_value = None
        return api

    def test_single_password_works_for_all_switches_passes(self):
        runner = self._make_runner(candidates=["Vastdata1!", "VastData1!"])
        api = self._mock_api_with_switches(["10.1.1.10", "10.1.1.11", "10.1.1.12"])
        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "leaf-1", "")),
        ):
            check = runner._validate_switch_ssh()

        self.assertEqual(check.status, "pass")
        self.assertIn("3/3", check.message)
        self.assertNotIn("fallback", check.message)

    def test_mixed_defaults_passes_with_fallback_note(self):
        runner = self._make_runner(candidates=["Vastdata1!", "VastData1!"])
        api = self._mock_api_with_switches(["10.1.1.10", "10.1.1.11", "10.1.1.12"])

        # .10 + .11 authenticate on primary password; .12 fails primary auth
        # then succeeds on the fallback candidate.
        ssh_returns = iter(
            [
                (0, "leaf-1", ""),
                (0, "leaf-2", ""),
                (1, "", "Authentication failed"),
                (0, "leaf-3", ""),
            ]
        )
        interactive_returns = iter([(1, "", "Authentication failed")])

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", side_effect=lambda *a, **k: next(ssh_returns)),
            patch("utils.ssh_adapter.run_interactive_ssh", side_effect=lambda *a, **k: next(interactive_returns)),
        ):
            check = runner._validate_switch_ssh()

        self.assertEqual(check.status, "pass")
        self.assertIn("3/3", check.message)
        self.assertIn("fallback", check.message)

    def test_onyx_reachable_but_command_fails_still_passes(self):
        """Onyx rejects raw ``hostname`` with non-zero rc but no auth error.
        The switch is reachable + authenticated; workflows use interactive SSH
        for Onyx at runtime, so pre-validation must not warn."""
        runner = self._make_runner(candidates=["Vastdata1!"])
        api = self._mock_api_with_switches(["10.1.1.20"])

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(5, "", "Bash commands not supported")),
            patch("utils.ssh_adapter.run_interactive_ssh"),
        ):
            check = runner._validate_switch_ssh()

        self.assertEqual(check.status, "pass")
        self.assertIn("reachable", check.message.lower())

    def test_one_switch_unreachable_warns(self):
        runner = self._make_runner(candidates=["Vastdata1!", "VastData1!"])
        api = self._mock_api_with_switches(["10.1.1.10", "10.1.1.11"])

        ssh_returns = iter(
            [
                (0, "leaf-1", ""),
                (1, "", "connection timed out"),
                (1, "", "connection timed out"),
            ]
        )
        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", side_effect=lambda *a, **k: next(ssh_returns)),
            patch("utils.ssh_adapter.run_interactive_ssh"),
        ):
            check = runner._validate_switch_ssh()

        self.assertEqual(check.status, "warn")
        self.assertIn("1/2", check.message)
        self.assertIn("10.1.1.11", check.message)

    def test_all_passwords_fail_auth_warns(self):
        runner = self._make_runner(candidates=["Vastdata1!", "VastData1!"])
        api = self._mock_api_with_switches(["10.1.1.10"])

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(1, "", "Authentication failed")),
            patch("utils.ssh_adapter.run_interactive_ssh", return_value=(1, "", "Authentication failed")),
        ):
            check = runner._validate_switch_ssh()

        self.assertEqual(check.status, "warn")
        self.assertIn("auth failed", check.message.lower())

    def test_rm7_auth_exhausted_emits_actionable_error(self):
        """RM-7: when all candidate passwords are rejected for a switch,
        pre-validation must emit exactly one ``[ERROR]`` line per switch
        naming the IP, candidate count, usernames tried, and the config
        location to populate — not just a wall of ``[WARN]`` combo lines.
        """
        emitted: list = []

        def capture(level, message, details=None, tier="status"):
            emitted.append((level, message))

        runner = self._make_runner(candidates=["Vastdata1!", "VastData1!"])
        runner._output_callback = capture
        api = self._mock_api_with_switches(["10.143.11.156"])

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(1, "", "Authentication failed")),
            patch("utils.ssh_adapter.run_interactive_ssh", return_value=(1, "", "Authentication failed")),
        ):
            runner._validate_switch_ssh()

        error_lines = [m for lvl, m in emitted if lvl == "error"]
        matching = [m for m in error_lines if "10.143.11.156 auth exhausted" in m]
        self.assertEqual(len(matching), 1, f"expected exactly one actionable RM-7 [ERROR], got: {error_lines}")
        msg = matching[0]
        self.assertIn("credential candidate(s)", msg)
        self.assertIn("config/config.yaml", msg)
        self.assertIn("VAST_DEFAULT_SWITCH_PASSWORDS", msg)
        self.assertIn("advanced_operations.default_switch_passwords", msg)

    def test_rm7_unreachable_does_not_emit_auth_exhausted(self):
        """RM-7 applies to auth exhaustion, not connectivity failure.  A
        switch that times out at the TCP layer is a different class of
        problem — the operator needs firewall/VPN guidance, not
        password-config guidance — so no actionable auth-exhausted
        [ERROR] is emitted for ``unreachable`` results.
        """
        emitted: list = []

        def capture(level, message, details=None, tier="status"):
            emitted.append((level, message))

        runner = self._make_runner(candidates=["Vastdata1!"])
        runner._output_callback = capture
        api = self._mock_api_with_switches(["10.1.1.99"])

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(1, "", "connection timed out")),
            patch("utils.ssh_adapter.run_interactive_ssh"),
        ):
            runner._validate_switch_ssh()

        error_lines = [m for lvl, m in emitted if lvl == "error"]
        self.assertFalse(
            any("auth exhausted" in m for m in error_lines),
            f"RM-7 actionable auth-exhausted line must not fire for unreachable switches: {error_lines}",
        )

    def test_rm7_build_switch_auth_exhausted_message_extracts_users(self):
        """Unit-level coverage of the RM-7 message builder: given the
        per-combo attempt log, the extracted username list must be
        deduplicated and ordered by first appearance (cumulus first,
        then admin), and the message must name the config knob.
        """
        from oneshot_runner import _build_switch_auth_exhausted_message

        attempts = [
            "1. std-ssh cumulus@10.143.11.156: auth failed — Permission denied",
            "2. std-ssh admin@10.143.11.156: auth failed — Permission denied",
            "2. interactive-ssh admin@10.143.11.156: auth failed — ...",
        ]
        msg = _build_switch_auth_exhausted_message(
            switch_ip="10.143.11.156",
            candidate_count=2,
            attempts=attempts,
        )

        self.assertIn("Switch 10.143.11.156 auth exhausted", msg)
        self.assertIn("tried 2 credential candidate(s)", msg)
        self.assertIn("username(s) cumulus, admin", msg)
        self.assertIn("advanced_operations.default_switch_passwords", msg)
        self.assertIn("VAST_DEFAULT_SWITCH_PASSWORDS", msg)

    def test_rm7_build_switch_auth_exhausted_message_handles_empty_log(self):
        """When the attempt log is empty (rare but possible), the builder
        must still produce a useful message with ``username(s) unknown``
        rather than raising.
        """
        from oneshot_runner import _build_switch_auth_exhausted_message

        msg = _build_switch_auth_exhausted_message(
            switch_ip="10.0.0.1",
            candidate_count=0,
            attempts=[],
        )

        self.assertIn("Switch 10.0.0.1 auth exhausted", msg)
        self.assertIn("username(s) unknown", msg)

    def test_tech_port_mode_proxies_switch_ssh_through_cluster_node(self):
        """Regression: Pre-Validation must ProxyJump through a cluster node in
        Tech Port mode, because the Reporter machine typically has no direct L3
        path to the switch management network.  Switches that happen to be
        reachable directly pass either way, but switches only reachable via
        the node fail without the jump host."""
        runner = self._make_runner(candidates=["Vastdata1!"])
        runner._tunnel_address = "127.0.0.1:49458"
        api = self._mock_api_with_switches(["10.1.1.10"])

        captured = []

        def fake_ssh(*args, **kwargs):
            captured.append(dict(kwargs))
            return (0, "leaf-1", "")

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", side_effect=fake_ssh),
            patch("utils.ssh_adapter.run_interactive_ssh"),
        ):
            check = runner._validate_switch_ssh()

        self.assertEqual(check.status, "pass")
        self.assertTrue(captured, "expected run_ssh_command to be called")
        self.assertEqual(captured[0].get("jump_host"), "10.0.0.1")
        self.assertEqual(captured[0].get("jump_user"), "vastdata")
        self.assertEqual(captured[0].get("jump_password"), "vastdata")

    def test_non_tech_port_mode_does_not_use_jump_host(self):
        """When Tech Port mode is not active, the probe must not add jump-host
        kwargs — the Reporter has a direct path to the switch."""
        runner = self._make_runner(candidates=["Vastdata1!"])
        runner._tunnel_address = None
        api = self._mock_api_with_switches(["10.1.1.10"])

        captured = []

        def fake_ssh(*args, **kwargs):
            captured.append(dict(kwargs))
            return (0, "leaf-1", "")

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", side_effect=fake_ssh),
            patch("utils.ssh_adapter.run_interactive_ssh"),
        ):
            runner._validate_switch_ssh()

        self.assertTrue(captured)
        self.assertNotIn("jump_host", captured[0])

    def test_records_per_switch_winning_password_for_workflows(self):
        """Pre-validation must persist the winning password for each switch on
        the runner so workflows (notably vnetmap with ``--multiple-passwords``)
        can drive each switch with the exact credential that authenticated."""
        runner = self._make_runner(candidates=["Vastdata1!", "VastData1!"])
        api = self._mock_api_with_switches(["10.1.1.10", "10.1.1.11", "10.1.1.12"])

        # .10/.11 win on candidate 1; .12 wins on candidate 2 (fallback).
        ssh_returns = iter(
            [
                (0, "leaf-1", ""),
                (0, "leaf-2", ""),
                (1, "", "Authentication failed"),
                (0, "leaf-3", ""),
            ]
        )
        interactive_returns = iter([(1, "", "Authentication failed")])

        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch("utils.ssh_adapter.run_ssh_command", side_effect=lambda *a, **k: next(ssh_returns)),
            patch("utils.ssh_adapter.run_interactive_ssh", side_effect=lambda *a, **k: next(interactive_returns)),
        ):
            runner._validate_switch_ssh()

        self.assertEqual(runner._switch_password_by_ip["10.1.1.10"], "Vastdata1!")
        self.assertEqual(runner._switch_password_by_ip["10.1.1.11"], "Vastdata1!")
        self.assertEqual(runner._switch_password_by_ip["10.1.1.12"], "VastData1!")
        self.assertEqual(runner._switch_user_by_ip["10.1.1.12"], "cumulus")

        workflow_creds = runner._get_workflow_credentials("vnetmap")
        self.assertEqual(
            workflow_creds["switch_password_by_ip"],
            {"10.1.1.10": "Vastdata1!", "10.1.1.11": "Vastdata1!", "10.1.1.12": "VastData1!"},
        )

    def test_does_not_record_passwords_for_unreachable_switches(self):
        """Switches that never authenticate must not leak into the per-switch
        map — otherwise the vnetmap workflow would hand the wrong password to
        ``--multiple-passwords`` and the run would fail silently."""
        runner = self._make_runner(candidates=["Vastdata1!"])
        api = self._mock_api_with_switches(["10.1.1.10", "10.1.1.11"])

        # Returns for every possible ssh_adapter call.  .10 succeeds on its
        # first cumulus/Vastdata1! try.  .11 fails every combo (cumulus/x then
        # admin/admin — the helper always appends admin/admin as a last-ditch
        # try).  Extra auth-fail values are harmless tail values.
        auth_fail = (1, "", "Authentication failed")
        with (
            patch("api_handler.create_vast_api_handler", return_value=api),
            patch(
                "utils.ssh_adapter.run_ssh_command",
                side_effect=[(0, "leaf-1", ""), auth_fail, auth_fail, auth_fail, auth_fail],
            ),
            patch(
                "utils.ssh_adapter.run_interactive_ssh",
                side_effect=[auth_fail, auth_fail, auth_fail, auth_fail],
            ),
        ):
            runner._validate_switch_ssh()

        self.assertIn("10.1.1.10", runner._switch_password_by_ip)
        self.assertNotIn("10.1.1.11", runner._switch_password_by_ip)

    def test_seed_switch_credentials_populates_map_and_workflow_creds(self):
        """``seed_switch_credentials`` must populate the per-switch map so a
        fresh runner (the one created by ``/advanced-ops/oneshot/start``) can
        inherit Pre-Validation's discoveries from the prior runner.  This
        closes the gap reported in
        ``import/Assets-2026-0420c/output-results-Output-Results-2026-0420d.txt``
        where vnetmap fell back to the legacy single-password sweep even
        though Pre-Validation had authenticated every switch."""
        runner = self._make_runner(candidates=["Vastdata1!"])
        runner.seed_switch_credentials(
            switch_user_by_ip={"10.1.1.10": "cumulus", "10.1.1.11": "cumulus"},
            switch_password_by_ip={"10.1.1.10": "Vastdata1!", "10.1.1.11": "VastData1!"},
        )

        self.assertEqual(runner._switch_password_by_ip["10.1.1.10"], "Vastdata1!")
        self.assertEqual(runner._switch_password_by_ip["10.1.1.11"], "VastData1!")
        self.assertEqual(runner._switch_user_by_ip["10.1.1.11"], "cumulus")

        # And the map must flow through to the workflow so VnetmapWorkflow's
        # fast-path guard ``all(ip in switch_password_by_ip for ip in ...)``
        # can fire.
        workflow_creds = runner._get_workflow_credentials("vnetmap")
        self.assertEqual(
            workflow_creds["switch_password_by_ip"],
            {"10.1.1.10": "Vastdata1!", "10.1.1.11": "VastData1!"},
        )
        self.assertEqual(workflow_creds["switch_user_by_ip"]["10.1.1.10"], "cumulus")

    def test_seed_switch_credentials_ignores_empty_entries(self):
        """Blank IPs or passwords must never leak into the per-switch map —
        otherwise ``VnetmapWorkflow`` could shell-quote an empty string
        into the ``--multiple-passwords`` stdin stream."""
        runner = self._make_runner(candidates=["Vastdata1!"])
        runner.seed_switch_credentials(
            switch_user_by_ip={"10.1.1.10": "cumulus", "": "cumulus"},
            switch_password_by_ip={"10.1.1.10": "Vastdata1!", "10.1.1.11": "", "": "secret"},
        )

        self.assertEqual(list(runner._switch_password_by_ip.keys()), ["10.1.1.10"])
        self.assertEqual(list(runner._switch_user_by_ip.keys()), ["10.1.1.10"])

    def test_run_all_reprobes_switches_when_map_empty(self):
        """If the execution runner has no seed (e.g. operator clicked Run
        without Pre-Validation, or the app failed to hand off the map),
        ``run_all`` must silently call ``_validate_switch_ssh`` before
        operations so ``VnetmapWorkflow`` still gets a populated map.

        Regression for
        ``import/Assets-2026-0420c/output-results-Output-Results-2026-0420d.txt``.
        """
        from oneshot_runner import OneShotRunner

        runner = OneShotRunner(
            selected_ops=["vnetmap"],
            credentials={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "Vastdata1!",
            },
        )
        self.assertEqual(runner._switch_password_by_ip, {})

        with (
            patch.object(runner, "_validate_switch_ssh") as mock_probe,
            patch.object(runner, "_run_operations"),
            patch.object(runner, "_run_bundling"),
            patch("utils.get_data_dir", return_value=Path("/tmp")),
        ):
            runner.run_all()

        mock_probe.assert_called_once()

    def test_run_all_skips_reprobe_when_map_already_seeded(self):
        """The runtime fallback must be a pure safety net: seeding from the
        prior runner (the common path) avoids the extra SSH round-trips.
        Without this guard every execution would re-probe the switches."""
        from oneshot_runner import OneShotRunner

        runner = OneShotRunner(
            selected_ops=["vnetmap"],
            credentials={
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "Vastdata1!",
            },
        )
        runner.seed_switch_credentials(
            switch_user_by_ip={"10.1.1.10": "cumulus"},
            switch_password_by_ip={"10.1.1.10": "Vastdata1!"},
        )

        with (
            patch.object(runner, "_validate_switch_ssh") as mock_probe,
            patch.object(runner, "_run_operations"),
            patch.object(runner, "_run_bundling"),
            patch("utils.get_data_dir", return_value=Path("/tmp")),
        ):
            runner.run_all()

        mock_probe.assert_not_called()


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

    def test_prevalidation_runs_switch_ssh_when_only_vnetmap_selected(self):
        """Selecting vnetmap (no switch_config) must still probe switches.

        vnetmap authenticates against every switch in Step 4.  Without the
        Switch SSH pre-validation probe, ``_switch_password_by_ip`` stays
        empty and the workflow falls back to the legacy candidate-sweep,
        which fails on mixed-default clusters.  Regression for the log in
        ``import/Assets-2026-0420c/output-results-d.txt``.
        """
        runner = self._make_runner(ops=["vnetmap"], include_health=False, include_report=False)
        with (
            patch("oneshot_runner._requests_lib.get", return_value=MagicMock(status_code=200)),
            patch("utils.ssh_adapter.run_ssh_command", return_value=(0, "cnode1", "")),
            patch.object(runner, "_validate_switch_ssh", wraps=runner._validate_switch_ssh) as mock_sw,
            patch("tool_manager.ToolManager") as MockTM,
            patch("api_handler.create_vast_api_handler") as mock_api_factory,
        ):
            MockTM.return_value.get_all_tools_info.return_value = []
            mock_api = MagicMock()
            mock_api._make_api_request.return_value = [{"mgmt_ip": "10.0.0.50"}]
            mock_api_factory.return_value = mock_api

            runner.run_prevalidation()

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


class TestVnetmapPortMappingInReport(unittest.TestCase):
    """Verify OneShot's As-Built Report prefers vnetmap output over SSH.

    The vnetmap workflow writes ``vnetmap_output_<cluster_ip>_*.txt``
    into ``output/scripts/``.  When ``_run_report`` runs afterwards it
    must find the newest same-cluster file and hand the parsed topology
    to ``data_extractor.extract_all_data(..., use_vnetmap=True)``.  This
    keeps the Port Mapping section consistent with the /generate web
    path, which has used this source since v1.5.0.
    """

    def _make_runner(self, cluster_ip="10.0.0.1"):
        from oneshot_runner import OneShotRunner

        return OneShotRunner(
            selected_ops=["vnetmap"],
            credentials={
                "cluster_ip": cluster_ip,
                "username": "admin",
                "password": "pass",
                "node_user": "vastdata",
                "node_password": "pass",
                "switch_user": "cumulus",
                "switch_password": "pass",
            },
            include_report=True,
            include_health=False,
        )

    def test_find_latest_vnetmap_output_returns_newest_same_cluster(self):
        import tempfile

        runner = self._make_runner(cluster_ip="10.0.0.1")
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            scripts = data_dir / "output" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "vnetmap_output_10.0.0.1_20260101_000000.txt").write_text("old")
            (scripts / "vnetmap_output_10.0.0.1_20260420_120000.txt").write_text("new")
            (scripts / "vnetmap_output_10.0.0.2_20260425_120000.txt").write_text("other cluster")

            with patch("utils.get_data_dir", return_value=data_dir):
                result = runner._find_latest_vnetmap_output("10.0.0.1")

            self.assertIsNotNone(result)
            self.assertEqual(result.name, "vnetmap_output_10.0.0.1_20260420_120000.txt")

    def test_find_latest_vnetmap_output_missing_scripts_dir(self):
        import tempfile

        runner = self._make_runner()
        with tempfile.TemporaryDirectory() as tmp:
            with patch("utils.get_data_dir", return_value=Path(tmp)):
                self.assertIsNone(runner._find_latest_vnetmap_output("10.0.0.1"))

    def test_find_latest_vnetmap_output_no_match_for_cluster(self):
        import tempfile

        runner = self._make_runner()
        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            scripts = data_dir / "output" / "scripts"
            scripts.mkdir(parents=True)
            (scripts / "vnetmap_output_10.9.9.9_20260425_120000.txt").write_text("different cluster")
            with patch("utils.get_data_dir", return_value=data_dir):
                self.assertIsNone(runner._find_latest_vnetmap_output("10.0.0.1"))

    def test_find_latest_vnetmap_output_empty_cluster_ip(self):
        runner = self._make_runner()
        self.assertIsNone(runner._find_latest_vnetmap_output(""))

    def test_run_report_uses_vnetmap_when_available(self):
        """_run_report parses vnetmap output and passes use_vnetmap=True."""
        import tempfile

        runner = self._make_runner(cluster_ip="10.0.0.1")

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            scripts = data_dir / "output" / "scripts"
            scripts.mkdir(parents=True)
            vnetmap_file = scripts / "vnetmap_output_10.0.0.1_20260420_120000.txt"
            vnetmap_file.write_text("fake vnetmap output")

            mock_api = MagicMock()
            mock_api.get_all_data.return_value = {"cluster_summary": {"name": "testcluster"}}

            mock_extractor = MagicMock()
            mock_extractor.extract_all_data.return_value = {"cluster_summary": {"name": "testcluster"}}

            mock_report_builder = MagicMock()
            mock_report_builder.generate_pdf_report.return_value = True

            mock_parser = MagicMock()
            mock_parser.parse.return_value = {
                "available": True,
                "topology": [{"switch": "sw1", "port": "swp1"}],
            }

            with (
                patch("api_handler.create_vast_api_handler", return_value=mock_api),
                patch("data_extractor.create_data_extractor", return_value=mock_extractor),
                patch("report_builder.create_report_builder", return_value=mock_report_builder),
                patch("report_builder.ReportConfig.from_yaml", return_value=MagicMock()),
                patch("utils.get_data_dir", return_value=data_dir),
                patch("vnetmap_parser.VNetMapParser", return_value=mock_parser),
                patch("external_port_mapper.ExternalPortMapper") as MockEPM,
            ):
                runner._run_report()

            mock_extractor.extract_all_data.assert_called_once()
            _, kwargs = mock_extractor.extract_all_data.call_args
            self.assertTrue(
                kwargs.get("use_vnetmap"),
                "use_vnetmap must be True when a vnetmap output file is present",
            )
            self.assertFalse(
                kwargs.get("use_external_port_mapping", False),
                "External SSH path must be skipped when vnetmap data is available",
            )
            MockEPM.assert_not_called()

            raw_arg = mock_extractor.extract_all_data.call_args.args[0]
            self.assertIn("port_mapping_vnetmap", raw_arg)
            self.assertEqual(raw_arg["port_mapping_vnetmap"]["topology"][0]["switch"], "sw1")

    def test_run_report_falls_back_to_ssh_when_no_vnetmap_file(self):
        """No vnetmap file → ExternalPortMapper path runs as before."""
        import tempfile

        runner = self._make_runner(cluster_ip="10.0.0.1")

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            (data_dir / "output" / "scripts").mkdir(parents=True)

            mock_api = MagicMock()
            mock_api.get_all_data.return_value = {
                "cluster_summary": {"name": "testcluster"},
                "switch_inventory": {"switches": [{"mgmt_ip": "10.0.0.100"}]},
                "cnodes_network": [{"mgmt_ip": "10.0.0.50"}],
            }

            mock_extractor = MagicMock()
            mock_extractor.extract_all_data.return_value = {"cluster_summary": {"name": "testcluster"}}

            mock_report_builder = MagicMock()
            mock_report_builder.generate_pdf_report.return_value = True

            mock_epm_instance = MagicMock()
            mock_epm_instance.collect_port_mapping.return_value = {"available": True, "mappings": []}

            with (
                patch("api_handler.create_vast_api_handler", return_value=mock_api),
                patch("data_extractor.create_data_extractor", return_value=mock_extractor),
                patch("report_builder.create_report_builder", return_value=mock_report_builder),
                patch("report_builder.ReportConfig.from_yaml", return_value=MagicMock()),
                patch("utils.get_data_dir", return_value=data_dir),
                patch("external_port_mapper.ExternalPortMapper", return_value=mock_epm_instance) as MockEPM,
            ):
                runner._run_report()

            MockEPM.assert_called()
            _, kwargs = mock_extractor.extract_all_data.call_args
            self.assertFalse(
                kwargs.get("use_vnetmap", False),
                "use_vnetmap must be False when no vnetmap output file exists",
            )
            self.assertTrue(
                kwargs.get("use_external_port_mapping", False),
                "External SSH path must populate use_external_port_mapping=True",
            )


class TestRM16ReportHealthAuthParity(unittest.TestCase):
    """RM-16: ``OneShotRunner._run_report`` must thread the pre-validated
    per-IP password map and resolved candidate list into the HealthChecker
    it embeds so the Test Suite tile's ``switch_ssh`` category authenticates
    against heterogeneous fleets the same way the Reporter tile
    (``_run_report_job`` + RM-15) and the standalone ``_run_health`` phase
    (RM-2) already do.
    """

    def _make_runner(self, cluster_ip="10.0.0.1", tunnel_address=None):
        from oneshot_runner import OneShotRunner

        runner = OneShotRunner(
            selected_ops=[],
            credentials={
                "cluster_ip": cluster_ip,
                "username": "admin",
                "password": "apipw",
                "node_user": "vastdata",
                "node_password": "nodepw",
                "switch_user": "cumulus",
                "switch_password": "primary",
            },
            include_report=True,
            include_health=True,
        )
        if tunnel_address:
            runner._tunnel_address = tunnel_address
        return runner

    def _invoke_run_report(self, runner):
        """Invoke ``_run_report`` with the minimum mocks needed for the
        HealthChecker construction path."""
        mock_api = MagicMock()
        mock_api.get_all_data.return_value = {"cluster_summary": {"name": "cx"}}
        mock_extractor = MagicMock()
        mock_extractor.extract_all_data.return_value = {"cluster_summary": {"name": "cx"}}
        mock_report_builder = MagicMock()
        mock_report_builder.generate_pdf_report.return_value = True

        mock_hc = MagicMock()
        mock_hc.run_all_checks.return_value = MagicMock(results=[], summary={"pass": 0, "fail": 0, "warning": 0})

        with (
            patch("api_handler.create_vast_api_handler", return_value=mock_api),
            patch("data_extractor.create_data_extractor", return_value=mock_extractor),
            patch("report_builder.create_report_builder", return_value=mock_report_builder),
            patch("report_builder.ReportConfig.from_yaml", return_value=MagicMock()),
            patch("utils.get_data_dir", return_value=Path("/tmp")),
            patch("health_checker.HealthChecker", return_value=mock_hc) as MockHC,
            patch("external_port_mapper.ExternalPortMapper"),
        ):
            runner._run_report()
        return MockHC

    def test_run_report_threads_switch_password_by_ip_into_healthchecker(self):
        """``self._switch_password_by_ip`` must land in ``switch_ssh_config``."""
        runner = self._make_runner()
        runner._switch_password_by_ip = {"10.0.0.1": "pw1", "10.0.0.2": "pw2"}

        MockHC = self._invoke_run_report(runner)

        MockHC.assert_called_once()
        sw_cfg = MockHC.call_args.kwargs["switch_ssh_config"]
        self.assertEqual(
            sw_cfg["password_by_ip"],
            {"10.0.0.1": "pw1", "10.0.0.2": "pw2"},
            "per-IP password map must be threaded into HealthChecker",
        )
        self.assertIsNot(
            sw_cfg["password_by_ip"],
            runner._switch_password_by_ip,
            "dict must be copied to avoid shared-state mutation",
        )

    def test_run_report_threads_switch_password_candidates_into_healthchecker(self):
        """``self._switch_password_candidates`` must land in ``switch_ssh_config``."""
        runner = self._make_runner()
        runner._switch_password_candidates = ["primary", "Vastdata1!", "VastData1!"]

        MockHC = self._invoke_run_report(runner)

        MockHC.assert_called_once()
        sw_cfg = MockHC.call_args.kwargs["switch_ssh_config"]
        self.assertEqual(
            sw_cfg["password_candidates"],
            ["primary", "Vastdata1!", "VastData1!"],
            "candidate list must be threaded for HealthChecker's probe fallback",
        )
        self.assertIsNot(
            sw_cfg["password_candidates"],
            runner._switch_password_candidates,
            "list must be copied to avoid shared-state mutation",
        )

    def test_run_report_omits_password_by_ip_when_empty(self):
        """Empty per-IP map must not pollute ``switch_ssh_config``."""
        runner = self._make_runner()
        runner._switch_password_by_ip = {}

        MockHC = self._invoke_run_report(runner)

        MockHC.assert_called_once()
        sw_cfg = MockHC.call_args.kwargs["switch_ssh_config"]
        self.assertNotIn(
            "password_by_ip",
            sw_cfg,
            "empty per-IP map must be omitted, not handed to HealthChecker as {}",
        )

    def test_run_report_preserves_proxy_jump_with_new_keys(self):
        """Tunnel + per-IP map + candidates must coexist in ``switch_ssh_config``."""
        runner = self._make_runner(tunnel_address=("127.0.0.1", 2200))
        runner._switch_password_by_ip = {"10.0.0.1": "pw1"}
        runner._switch_password_candidates = ["primary", "Vastdata1!"]

        MockHC = self._invoke_run_report(runner)

        MockHC.assert_called_once()
        sw_cfg = MockHC.call_args.kwargs["switch_ssh_config"]
        self.assertEqual(sw_cfg["password_by_ip"], {"10.0.0.1": "pw1"})
        self.assertEqual(sw_cfg["password_candidates"], ["primary", "Vastdata1!"])
        self.assertIn("proxy_jump", sw_cfg)
        self.assertEqual(sw_cfg["proxy_jump"]["host"], "10.0.0.1")
        self.assertEqual(sw_cfg["proxy_jump"]["username"], "vastdata")
        self.assertEqual(sw_cfg["proxy_jump"]["password"], "nodepw")


if __name__ == "__main__":
    unittest.main()
