"""
Tests for the Flask web UI application (src/app.py).

Covers every route: dashboard, generate, config, reports, SSE stream,
and helper functions — all without a real cluster or browser.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import create_flask_app, _list_reports, _read_config, _write_config, APP_VERSION


class TestFlaskAppFactory(unittest.TestCase):
    """Verify the Flask app is constructed correctly."""

    def test_create_app_returns_flask_instance(self):
        app = create_flask_app()
        self.assertEqual(app.name, "app")

    def test_app_has_secret_key(self):
        app = create_flask_app()
        self.assertIsNotNone(app.secret_key)

    def test_app_config_defaults(self):
        app = create_flask_app()
        self.assertIn("DEFAULT_OUTPUT_DIR", app.config)
        self.assertIn("CONFIG_PATH", app.config)
        self.assertFalse(app.config["JOB_RUNNING"])
        self.assertIsNone(app.config["JOB_RESULT"])

    def test_custom_config_passed_through(self):
        app = create_flask_app(config={"api": {"timeout": 99}})
        self.assertEqual(app.config["REPORT_CONFIG"]["api"]["timeout"], 99)


class TestDashboardRoute(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def test_dashboard_returns_200(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_contains_version(self):
        resp = self.client.get("/")
        self.assertIn(APP_VERSION.encode(), resp.data)

    def test_dashboard_contains_nav_links(self):
        resp = self.client.get("/")
        self.assertIn(b"Dashboard", resp.data)
        self.assertIn(b"Reporter", resp.data)
        self.assertIn(b"Results", resp.data)
        self.assertIn(b"Library", resp.data)
        self.assertIn(b"Docs", resp.data)

    def test_dashboard_quick_start_content(self):
        resp = self.client.get("/")
        self.assertIn(b"Quick Start", resp.data)
        self.assertIn(b"Prerequisites", resp.data)
        self.assertIn(b"Getting Started", resp.data)
        self.assertIn(b"Connection Settings", resp.data)
        self.assertIn(b"Run Report", resp.data)
        self.assertIn(b"Review", resp.data)

    def test_dashboard_status_api(self):
        resp = self.client.get("/api/dashboard/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn("job_status", data)
        self.assertIn("job_active", data)
        self.assertIn("tools_cached", data)
        self.assertIn("tools_total", data)
        self.assertIn("profiles_count", data)
        self.assertIn("total_reports", data)
        self.assertFalse(data["job_active"])


class TestGenerateRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def test_generate_form_returns_200(self):
        resp = self.client.get("/generate")
        self.assertEqual(resp.status_code, 200)

    def test_generate_form_contains_cluster_field(self):
        resp = self.client.get("/generate")
        self.assertIn(b"cluster_ip", resp.data)

    def test_generate_post_missing_ip_returns_400(self):
        resp = self.client.post("/generate", data={"cluster_ip": ""})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)

    def test_generate_post_with_ip_starts_job(self):
        resp = self.client.post(
            "/generate",
            data={
                "cluster_ip": "10.0.0.1",
                "auth_method": "password",
                "username": "support",
                "password": "test",
            },
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "started")

    def test_generate_post_rejects_concurrent_job(self):
        self.app.config["JOB_RUNNING"] = True
        resp = self.client.post("/generate", data={"cluster_ip": "10.0.0.1"})
        self.assertEqual(resp.status_code, 409)

    def test_generate_status_returns_json(self):
        resp = self.client.get("/generate/status")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("running", body)
        self.assertIn("result", body)

    def test_generate_status_reflects_job_result(self):
        self.app.config["JOB_RESULT"] = {"success": True, "pdf": "test.pdf"}
        resp = self.client.get("/generate/status")
        body = json.loads(resp.data)
        self.assertTrue(body["result"]["success"])


class TestGenerateAutofillCandidates(unittest.TestCase):
    """RM-13: the Reporter tile must thread ``use_default_creds`` through
    ``/generate`` so ``_run_report_job`` can expand the single UI
    ``switch_password`` into the full candidate list (UI -> config ->
    env -> built-in VAST/Cumulus defaults).  Without this, ``vnetmap``
    silently auth-fails on any switch using a different published
    default than the one typed in Connection Settings.
    """

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def _post_with(self, use_default_creds: bool):
        """POST to /generate with a captured-params thread patch; return
        the ``params`` dict handed to ``_run_report_job``."""
        captured = {}

        class _FakeThread:
            def __init__(self, target=None, args=(), **_kwargs):
                captured["target"] = target
                captured["args"] = args

            def start(self):
                captured["started"] = True

        form = {
            "cluster_ip": "10.0.0.1",
            "auth_method": "password",
            "username": "support",
            "password": "test",
            "switch_user": "cumulus",
            "switch_password": "UIpw!",
        }
        if use_default_creds:
            form["use_default_creds"] = "on"

        with patch("app.threading.Thread", _FakeThread):
            resp = self.client.post("/generate", data=form)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(captured.get("started"))
        _, params = captured["args"]
        return params

    def test_use_default_creds_on_flag_reaches_params(self):
        params = self._post_with(use_default_creds=True)
        self.assertTrue(params["use_default_creds"])
        self.assertEqual(params["switch_password"], "UIpw!")

    def test_use_default_creds_off_flag_reaches_params(self):
        params = self._post_with(use_default_creds=False)
        self.assertFalse(params["use_default_creds"])


class TestRM15SwitchPreProbe(unittest.TestCase):
    """RM-15: before ``_run_report_job`` hands off to ``VnetmapWorkflow``
    it must pre-probe switches using the resolved candidate list and
    build a ``switch_password_by_ip`` map — mirroring what
    ``OneShotRunner._validate_switch_ssh`` does for the Test Suite
    tile.  Without this map, ``VnetmapWorkflow`` falls back to the
    legacy single-``-p`` candidate sweep which cannot succeed on
    heterogeneous fleets (e.g. two leaves on ``Vastdata1!`` plus a
    spare on ``VastData1!``).

    These tests exercise the extracted helper
    ``_preprobe_switch_passwords_for_job`` directly so the contract is
    testable in isolation.  Call-site integration (feeding the map
    into ``vnetmap_creds["switch_password_by_ip"]`` and
    ``switch_ssh_config["password_by_ip"]``) is a trivial 2-line hand-off
    reviewed by eye.
    """

    def setUp(self):
        from app import _preprobe_switch_passwords_for_job  # noqa: F401 — import probe

        self._probe_helper_import_ok = True

    def _make_api_handler(self, switch_ips):
        """Build a MagicMock that quacks like ``VastAPIHandler`` for the
        purposes of the pre-probe (only ``get_switches_detail`` is
        consumed).  Returns a list of dicts with ``mgmt_ip`` fields
        matching how the real ``/api/switches/`` endpoint shapes its
        payload."""
        handler = MagicMock()
        handler.get_switches_detail.return_value = [{"mgmt_ip": ip} for ip in switch_ips]
        return handler

    def test_skipped_when_no_vnetmap_no_health_check(self):
        # Neither workflow needs per-switch credentials, so skip the
        # probe entirely — zero SSH round-trips, zero API calls.
        from app import _preprobe_switch_passwords_for_job

        handler = self._make_api_handler(["10.0.0.1", "10.0.0.2"])
        with patch("utils.switch_ssh_probe.build_switch_password_by_ip") as mock_build:
            result = _preprobe_switch_passwords_for_job(
                api_handler=handler,
                params={"switch_user": "cumulus"},
                switch_password_candidates=["Vastdata1!", "VastData1!"],
                has_vnetmap=False,
                has_health_switch=False,
            )
        self.assertEqual(result, {})
        mock_build.assert_not_called()
        handler.get_switches_detail.assert_not_called()

    def test_skipped_when_single_candidate(self):
        # One candidate = nothing to probe; the legacy single-``-p``
        # path is trivially correct for homogeneous fleets and runs
        # per-switch SSH anyway.  Skipping here also saves a full
        # ``/api/switches/`` call on clusters that don't use Autofill.
        from app import _preprobe_switch_passwords_for_job

        handler = self._make_api_handler(["10.0.0.1"])
        with patch("utils.switch_ssh_probe.build_switch_password_by_ip") as mock_build:
            result = _preprobe_switch_passwords_for_job(
                api_handler=handler,
                params={"switch_user": "cumulus"},
                switch_password_candidates=["only-one-pw"],
                has_vnetmap=True,
                has_health_switch=True,
            )
        self.assertEqual(result, {})
        mock_build.assert_not_called()

    def test_skipped_when_empty_candidates(self):
        from app import _preprobe_switch_passwords_for_job

        handler = self._make_api_handler(["10.0.0.1"])
        with patch("utils.switch_ssh_probe.build_switch_password_by_ip") as mock_build:
            result = _preprobe_switch_passwords_for_job(
                api_handler=handler,
                params={"switch_user": "cumulus"},
                switch_password_candidates=[],
                has_vnetmap=True,
                has_health_switch=True,
            )
        self.assertEqual(result, {})
        mock_build.assert_not_called()

    def test_skipped_when_no_switches_found(self):
        # InfiniBand cluster or a VMS that hasn't registered its
        # switches yet — ``get_switches_detail`` returns ``[]``.  The
        # probe must short-circuit (not hang or error) and return an
        # empty map so the downstream workflow's Fast-path guard stays
        # deselected.
        from app import _preprobe_switch_passwords_for_job

        handler = self._make_api_handler([])
        with patch("utils.switch_ssh_probe.build_switch_password_by_ip") as mock_build:
            result = _preprobe_switch_passwords_for_job(
                api_handler=handler,
                params={"switch_user": "cumulus"},
                switch_password_candidates=["Vastdata1!", "VastData1!"],
                has_vnetmap=True,
                has_health_switch=True,
            )
        self.assertEqual(result, {})
        mock_build.assert_not_called()

    def test_probes_and_returns_map_when_vnetmap_and_candidates(self):
        # Happy path: Reporter tile has Autofill on with >=2 candidates
        # and vnetmap is selected.  The probe must run and return a
        # per-switch map.  Verify also that the proxy-jump kwargs
        # (cluster IP as bastion + node user/password) are forwarded.
        from app import _preprobe_switch_passwords_for_job

        handler = self._make_api_handler(["10.0.0.1", "10.0.0.2"])
        fake_map = {"10.0.0.1": "Vastdata1!", "10.0.0.2": "VastData1!"}

        with patch(
            "utils.switch_ssh_probe.build_switch_password_by_ip",
            return_value=fake_map,
        ) as mock_build:
            result = _preprobe_switch_passwords_for_job(
                api_handler=handler,
                params={
                    "cluster_ip": "10.0.0.254",
                    "switch_user": "cumulus",
                    "node_user": "vastdata",
                    "node_password": "node-pw",
                    "proxy_jump": True,
                },
                switch_password_candidates=["Vastdata1!", "VastData1!"],
                has_vnetmap=True,
                has_health_switch=False,
            )

        self.assertEqual(result, fake_map)
        mock_build.assert_called_once()
        call_kwargs = mock_build.call_args.kwargs
        # The probe MUST see both switch IPs + both candidates.
        self.assertEqual(list(call_kwargs["switch_ips"]), ["10.0.0.1", "10.0.0.2"])
        self.assertEqual(call_kwargs["switch_user"], "cumulus")
        self.assertEqual(
            list(call_kwargs["candidates"]),
            ["Vastdata1!", "VastData1!"],
        )
        # Proxy-jump wiring: cluster IP is the bastion when proxy_jump is enabled.
        self.assertEqual(call_kwargs.get("jump_host"), "10.0.0.254")
        self.assertEqual(call_kwargs.get("jump_user"), "vastdata")
        self.assertEqual(call_kwargs.get("jump_password"), "node-pw")

    def test_probes_when_only_health_switch_active(self):
        # vnetmap off but health-check Tier-3 wants switches —
        # HealthChecker benefits from the map too (it can skip its
        # in-process RM-13 probe when a pre-resolved map is supplied).
        from app import _preprobe_switch_passwords_for_job

        handler = self._make_api_handler(["10.0.0.1"])
        fake_map = {"10.0.0.1": "Vastdata1!"}

        with patch(
            "utils.switch_ssh_probe.build_switch_password_by_ip",
            return_value=fake_map,
        ) as mock_build:
            result = _preprobe_switch_passwords_for_job(
                api_handler=handler,
                params={
                    "cluster_ip": "10.0.0.254",
                    "switch_user": "cumulus",
                    "node_user": "vastdata",
                    "node_password": "node-pw",
                    "proxy_jump": True,
                },
                switch_password_candidates=["Vastdata1!", "VastData1!"],
                has_vnetmap=False,
                has_health_switch=True,
            )

        self.assertEqual(result, fake_map)
        mock_build.assert_called_once()

    def test_proxy_jump_disabled_forwards_no_jump_host(self):
        # When proxy_jump is explicitly False, the probe runs direct
        # and the jump_host kwarg must NOT be populated — otherwise
        # operators on the same L2 domain as the switches would see a
        # bastion hop they don't need (and that may not even be
        # reachable).
        from app import _preprobe_switch_passwords_for_job

        handler = self._make_api_handler(["10.0.0.1"])
        with patch(
            "utils.switch_ssh_probe.build_switch_password_by_ip",
            return_value={"10.0.0.1": "Vastdata1!"},
        ) as mock_build:
            _preprobe_switch_passwords_for_job(
                api_handler=handler,
                params={
                    "cluster_ip": "10.0.0.254",
                    "switch_user": "cumulus",
                    "node_user": "vastdata",
                    "node_password": "node-pw",
                    "proxy_jump": False,
                },
                switch_password_candidates=["Vastdata1!", "VastData1!"],
                has_vnetmap=True,
                has_health_switch=False,
            )

        call_kwargs = mock_build.call_args.kwargs
        self.assertNotIn("jump_host", call_kwargs)

    def test_api_handler_failure_returns_empty_map(self):
        # /api/switches/ can fail for a host of reasons (VMS still
        # booting, tunnel flap, 401 in the middle of the job).  The
        # pre-probe must never abort the whole report — it swallows
        # the failure, returns an empty map, and the downstream
        # workflows fall back to their legacy paths.
        from app import _preprobe_switch_passwords_for_job

        handler = MagicMock()
        handler.get_switches_detail.side_effect = RuntimeError("VMS unreachable")
        result = _preprobe_switch_passwords_for_job(
            api_handler=handler,
            params={"switch_user": "cumulus", "proxy_jump": False},
            switch_password_candidates=["Vastdata1!", "VastData1!"],
            has_vnetmap=True,
            has_health_switch=True,
        )
        self.assertEqual(result, {})


class TestConfigRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.config_path = os.path.join(self.tmpdir, "config.yaml")
        self.template_path = os.path.join(self.tmpdir, "template.yaml")
        Path(self.config_path).write_text("api:\n  timeout: 30\n")
        Path(self.template_path).write_text("api:\n  timeout: 60\n")
        self.app.config["CONFIG_PATH"] = self.config_path
        self.app.config["CONFIG_TEMPLATE"] = self.template_path

    def test_config_page_returns_200(self):
        resp = self.client.get("/config")
        self.assertEqual(resp.status_code, 200)

    def test_config_page_shows_content(self):
        resp = self.client.get("/config")
        self.assertIn(b"timeout: 30", resp.data)

    def test_config_save_valid_yaml(self):
        resp = self.client.post("/config", data={"config_text": "api:\n  timeout: 99\n"})
        self.assertEqual(resp.status_code, 200)
        saved = Path(self.config_path).read_text()
        self.assertIn("timeout: 99", saved)

    def test_config_save_invalid_yaml_returns_400(self):
        resp = self.client.post("/config", data={"config_text": "{{bad yaml"})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("Invalid YAML", body["error"])

    def test_config_reset_restores_template(self):
        resp = self.client.post("/config/reset")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("timeout: 60", body["config_text"])
        saved = Path(self.config_path).read_text()
        self.assertIn("timeout: 60", saved)


class TestReportsRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.app.config["DEFAULT_OUTPUT_DIR"] = self.tmpdir
        self.app.config["OUTPUT_DIRS"] = {self.tmpdir}
        self.pdf_name = "vast_asbuilt_report_test_20260304_120000.pdf"
        self.json_name = "vast_data_test_20260304_120000.json"
        (Path(self.tmpdir) / self.pdf_name).write_bytes(b"%PDF-fake")
        (Path(self.tmpdir) / self.json_name).write_text('{"test": true}')

    def test_reports_page_returns_200(self):
        resp = self.client.get("/reports")
        self.assertEqual(resp.status_code, 200)

    def test_reports_page_lists_files(self):
        resp = self.client.get("/reports")
        self.assertIn(self.pdf_name.encode(), resp.data)
        self.assertIn(self.json_name.encode(), resp.data)

    def test_reports_download(self):
        resp = self.client.get(f"/reports/download/{self.pdf_name}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"%PDF-fake", resp.data)

    def test_reports_view(self):
        resp = self.client.get(f"/reports/view/{self.json_name}")
        self.assertEqual(resp.status_code, 200)

    def test_reports_delete_existing(self):
        resp = self.client.post(f"/reports/delete/{self.pdf_name}")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse((Path(self.tmpdir) / self.pdf_name).exists())

    def test_reports_delete_missing_returns_404(self):
        resp = self.client.post("/reports/delete/nonexistent.pdf")
        self.assertEqual(resp.status_code, 404)


class TestLibraryRoutes(unittest.TestCase):
    """TSE-1: Library page and API (GET /library, GET/POST/DELETE /api/library) with mocked _load_library/_save_library."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.app.config["LIBRARY_PATH"] = os.path.join(self.tmpdir, "device_library.json")
        self.app.config["USER_IMAGES_DIR"] = os.path.join(self.tmpdir, "images")
        Path(self.app.config["USER_IMAGES_DIR"]).mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        import shutil

        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("app._load_library")
    @patch("app._get_builtin_devices")
    def test_library_page_returns_200(self, mock_builtin, mock_load):
        mock_builtin.return_value = {}
        mock_load.return_value = {}
        resp = self.client.get("/library")
        self.assertEqual(resp.status_code, 200)
        mock_load.assert_called_once_with(self.app.config["LIBRARY_PATH"])

    @patch("app._load_library")
    @patch("app._get_builtin_devices")
    def test_api_library_get_returns_merged_list(self, mock_builtin, mock_load):
        mock_builtin.return_value = {"builtin_1": {"type": "cbox", "height_u": 1}}
        mock_load.return_value = {"user_1": {"type": "dbox", "height_u": 2}}
        resp = self.client.get("/api/library")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIsInstance(data, list)
        keys = [d["key"] for d in data]
        self.assertIn("builtin_1", keys)
        self.assertIn("user_1", keys)

    @patch("app._validate_image")
    @patch("app._save_library")
    @patch("app._load_library")
    def test_api_library_post_adds_entry(self, mock_load, mock_save, mock_validate):
        mock_load.return_value = {}
        mock_validate.return_value = None
        resp = self.client.post(
            "/api/library",
            data={"key": "my_device", "type": "cbox", "height_u": "1", "description": "Test"},
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "added")
        self.assertEqual(body["key"], "my_device")
        mock_save.assert_called_once()
        call_lib = mock_save.call_args[0][1]
        self.assertIn("my_device", call_lib)
        self.assertEqual(call_lib["my_device"]["type"], "cbox")
        self.assertEqual(call_lib["my_device"]["height_u"], 1)

    @patch("app._validate_image")
    @patch("app._save_library")
    @patch("app._load_library")
    def test_api_library_post_missing_key_returns_400(self, mock_load, mock_save, mock_validate):
        mock_load.return_value = {}
        resp = self.client.post("/api/library", data={"type": "cbox"})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)
        mock_save.assert_not_called()

    @patch("app._save_library")
    @patch("app._load_library")
    def test_api_library_delete_removes_entry(self, mock_load, mock_save):
        mock_load.return_value = {"user_device": {"type": "cbox", "height_u": 1}}
        resp = self.client.delete("/api/library/user_device")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "deleted")
        self.assertEqual(body["key"], "user_device")
        mock_save.assert_called_once()
        call_lib = mock_save.call_args[0][1]
        self.assertNotIn("user_device", call_lib)

    @patch("app._load_library")
    def test_api_library_delete_missing_returns_404(self, mock_load):
        mock_load.return_value = {}
        resp = self.client.delete("/api/library/nonexistent")
        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.data)
        self.assertIn("error", body)


class TestGenerateCancel(unittest.TestCase):
    """TSE-2: POST /generate/cancel — no job vs job running."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def test_generate_cancel_no_job_returns_200_no_job(self):
        self.assertFalse(self.app.config["JOB_RUNNING"])
        resp = self.client.post("/generate/cancel")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "no_job")

    def test_generate_cancel_job_running_accepts_cancel(self):
        self.app.config["JOB_RUNNING"] = True
        resp = self.client.post("/generate/cancel")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "cancelled")
        self.assertFalse(self.app.config["JOB_RUNNING"])
        self.assertFalse(self.app.config["JOB_RESULT"]["success"])
        self.assertIn("cancelled", self.app.config["JOB_RESULT"]["error"].lower())


class TestReportsDirsRoutes(unittest.TestCase):
    """TSE-3: GET /reports/dirs and POST /reports/dirs (output-dir behavior)."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.app.config["DEFAULT_OUTPUT_DIR"] = self.tmpdir
        self.app.config["OUTPUT_DIRS"] = {self.tmpdir}

    def tearDown(self):
        import shutil

        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_reports_dirs_get_returns_current_dir(self):
        resp = self.client.get("/reports/dirs")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["dir"], self.tmpdir)

    def test_reports_dirs_post_valid_path_updates_config(self):
        other_dir = tempfile.mkdtemp()
        try:
            resp = self.client.post(
                "/reports/dirs",
                json={"dir": other_dir},
                content_type="application/json",
            )
            self.assertEqual(resp.status_code, 200)
            body = json.loads(resp.data)
            self.assertEqual(body["status"], "updated")
            self.assertEqual(body["dir"], str(Path(other_dir).resolve()))
            self.assertEqual(self.app.config["DEFAULT_OUTPUT_DIR"], str(Path(other_dir).resolve()))
            self.assertIn(str(Path(other_dir).resolve()), self.app.config["OUTPUT_DIRS"])
        finally:
            if os.path.exists(other_dir):
                import shutil

                shutil.rmtree(other_dir, ignore_errors=True)

    def test_reports_dirs_post_empty_dir_returns_400(self):
        resp = self.client.post("/reports/dirs", json={"dir": ""}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)

    def test_reports_dirs_post_nonexistent_dir_returns_400(self):
        resp = self.client.post(
            "/reports/dirs",
            json={"dir": "/nonexistent/path/12345"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)


class TestApiDiscover(unittest.TestCase):
    """TSE-4: POST /api/discover — mocked create_vast_api_handler + RackDiagram (read-only: auth + get_racks + get_switch_inventory)."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.app.config["CONFIG_PATH"] = os.path.join(self.tmpdir, "config.yaml")
        Path(self.app.config["CONFIG_PATH"]).write_text("api:\n  timeout: 30\n")

    def tearDown(self):
        import shutil

        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_api_discover_missing_cluster_ip_returns_400(self):
        resp = self.client.post(
            "/api/discover",
            json={},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)
        self.assertIn("Cluster IP", body["error"])

    @patch("socket.create_connection")
    @patch("rack_diagram.RackDiagram")
    @patch("api_handler.create_vast_api_handler")
    def test_api_discover_auth_failure_returns_401(self, mock_create_handler, mock_rack_diagram, mock_socket):
        mock_socket.return_value = MagicMock()
        mock_handler = MagicMock()
        mock_handler.authenticate.return_value = False
        mock_create_handler.return_value = mock_handler

        resp = self.client.post(
            "/api/discover",
            json={"cluster_ip": "10.0.0.1", "username": "u", "password": "p"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 401)
        body = json.loads(resp.data)
        self.assertIn("error", body)
        mock_handler.authenticate.assert_called_once()
        mock_handler.get_racks.assert_not_called()
        mock_handler.close.assert_not_called()

    @patch("socket.create_connection")
    @patch("rack_diagram.RackDiagram")
    @patch("api_handler.create_vast_api_handler")
    def test_api_discover_success_returns_racks_and_switches(self, mock_create_handler, mock_rack_diagram, mock_socket):
        mock_socket.return_value = MagicMock()
        mock_handler = MagicMock()
        mock_handler.authenticate.return_value = True
        mock_handler.get_racks.return_value = [
            {"id": 1, "name": "Rack-A", "number_of_units": 42},
            {"id": 2, "name": "Rack-B", "number_of_units": 42},
        ]
        mock_handler.get_switch_inventory.return_value = {
            "switches": [
                {"name": "SW1", "model": "msn3700", "serial": "S1"},
                {"name": "SW2", "model": "arista_7050", "serial": "S2"},
            ],
        }
        mock_create_handler.return_value = mock_handler

        mock_rd_instance = MagicMock()
        mock_rd_instance._get_device_height_units.side_effect = lambda m: 1 if "msn" in m else 2
        mock_rack_diagram.return_value = mock_rd_instance

        resp = self.client.post(
            "/api/discover",
            json={"cluster_ip": "10.0.0.1", "username": "u", "password": "p"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("racks", body)
        self.assertIn("switches", body)
        self.assertEqual(len(body["racks"]), 2)
        self.assertEqual(len(body["switches"]), 2)
        mock_handler.get_racks.assert_called_once()
        mock_handler.get_switch_inventory.assert_called_once()
        mock_handler.close.assert_called_once()


class TestProfilesRoutes(unittest.TestCase):
    """TSE-6: GET/POST /profiles and DELETE /profiles/<name> with mocked _load_profiles/_save_profiles."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.app.config["PROFILES_PATH"] = os.path.join(self.tmpdir, "cluster_profiles.json")

    def tearDown(self):
        import shutil

        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("app._load_profiles")
    def test_profiles_get_returns_200_and_json(self, mock_load):
        mock_load.return_value = {}
        resp = self.client.get("/profiles")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIsInstance(data, dict)
        mock_load.assert_called_once_with(self.app.config["PROFILES_PATH"])

    @patch("app._load_profiles")
    def test_profiles_get_returns_saved_profiles(self, mock_load):
        mock_load.return_value = {"profile1": {"cluster_ip": "10.0.0.1"}}
        resp = self.client.get("/profiles")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("profile1", data)
        self.assertEqual(data["profile1"]["cluster_ip"], "10.0.0.1")

    @patch("app._save_profiles")
    @patch("app._load_profiles")
    def test_profiles_post_requires_name(self, mock_load, mock_save):
        mock_load.return_value = {}
        resp = self.client.post(
            "/profiles",
            json={"cluster_ip": "10.0.0.1"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)
        self.assertIn("name", body["error"].lower())
        mock_save.assert_not_called()

    @patch("app._save_profiles")
    @patch("app._load_profiles")
    def test_profiles_post_success(self, mock_load, mock_save):
        mock_load.return_value = {}
        resp = self.client.post(
            "/profiles",
            json={
                "name": "my-cluster",
                "cluster_ip": "10.0.0.5",
                "auth_method": "password",
                "username": "admin",
            },
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body.get("status"), "saved")
        self.assertEqual(body.get("name"), "my-cluster")
        mock_save.assert_called_once()
        call_profiles = mock_save.call_args[0][1]
        self.assertIn("my-cluster", call_profiles)
        self.assertEqual(call_profiles["my-cluster"]["cluster_ip"], "10.0.0.5")

    @patch("app._load_profiles")
    def test_profiles_delete_not_found_returns_404(self, mock_load):
        mock_load.return_value = {}
        resp = self.client.delete("/profiles/nonexistent")
        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.data)
        self.assertIn("error", body)

    @patch("app._save_profiles")
    @patch("app._load_profiles")
    def test_profiles_delete_success(self, mock_load, mock_save):
        mock_load.return_value = {"to-delete": {"cluster_ip": "10.0.0.1"}}
        resp = self.client.delete("/profiles/to-delete")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body.get("status"), "deleted")
        mock_save.assert_called_once()
        call_profiles = mock_save.call_args[0][1]
        self.assertNotIn("to-delete", call_profiles)


class TestShutdown(unittest.TestCase):
    """TSE-7: POST /shutdown returns 200 and status (shutdown is mocked to avoid process exit)."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    @patch("app.os._exit")
    def test_shutdown_returns_200_and_status(self, mock_os_exit):
        resp = self.client.post("/shutdown")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body.get("status"), "shutting_down")
        mock_os_exit.assert_called_once_with(0)


class TestDocsRoutes(unittest.TestCase):
    """Docs page and doc content; internal .md links are rewritten to /docs#<doc_id>."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def test_docs_page_returns_200(self):
        resp = self.client.get("/docs")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Documentation", resp.data)

    def test_docs_content_returns_200_for_valid_id(self):
        resp = self.client.get("/docs/content/installation")
        self.assertEqual(resp.status_code, 200)

    def test_docs_content_returns_404_for_invalid_id(self):
        resp = self.client.get("/docs/content/nonexistent-doc-id")
        self.assertEqual(resp.status_code, 404)

    def test_docs_content_rewrites_internal_md_links(self):
        # UPDATE-GUIDE.md contains [Installation Guide](INSTALLATION-GUIDE.md) -> should become /docs#installation
        resp = self.client.get("/docs/content/update")
        self.assertEqual(resp.status_code, 200)
        # Rewritten link should point to in-app doc, not raw .md path
        self.assertIn(b'href="/docs#installation"', resp.data)
        # Should not contain raw .md path as href
        self.assertNotIn(b'href="INSTALLATION-GUIDE.md"', resp.data)


class TestSSEStream(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def test_stream_logs_returns_event_stream(self):
        resp = self.client.get("/stream/logs")
        self.assertTrue(resp.content_type.startswith("text/event-stream"))


class TestHealthRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()

    def test_health_page_loads(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)

    def test_health_run_missing_ip(self):
        resp = self.client.post("/health/run", data={"cluster_ip": ""})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("message", body)

    def test_health_run_already_running(self):
        self.app.config["HEALTH_JOB_RUNNING"] = True
        resp = self.client.post("/health/run", data={"cluster_ip": "10.0.0.1"})
        self.assertEqual(resp.status_code, 409)

    def test_health_status_no_job(self):
        resp = self.client.get("/health/status")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertFalse(body["running"])

    def test_health_cancel_no_job(self):
        resp = self.client.post("/health/cancel")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "no_job")

    def test_health_results_no_data(self):
        resp = self.client.get("/health/results")
        self.assertEqual(resp.status_code, 404)


class TestHelperFunctions(unittest.TestCase):

    def test_list_reports_empty_dir(self):
        with tempfile.TemporaryDirectory() as d:
            result = _list_reports([d])
            self.assertEqual(result, [])

    def test_list_reports_nonexistent_dir(self):
        result = _list_reports(["/nonexistent/path"])
        self.assertEqual(result, [])

    def test_list_reports_with_files(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "vast_asbuilt_report_a.pdf").write_bytes(b"fake")
            (Path(d) / "vast_data_b.json").write_text("{}")
            (Path(d) / "random.txt").write_text("ignored")
            (Path(d) / "other.pdf").write_bytes(b"ignored")
            result = _list_reports([d])
            names = [r["name"] for r in result]
            self.assertIn("vast_asbuilt_report_a.pdf", names)
            self.assertIn("vast_data_b.json", names)
            self.assertNotIn("random.txt", names)
            self.assertNotIn("other.pdf", names)

    def test_list_reports_sorted_newest_first(self):
        with tempfile.TemporaryDirectory() as d:
            old_path = Path(d) / "vast_asbuilt_report_old.pdf"
            new_path = Path(d) / "vast_asbuilt_report_new.pdf"
            old_path.write_bytes(b"old")
            new_path.write_bytes(b"new")
            os.utime(old_path, (1_000_000, 1_000_000))
            result = _list_reports([d])
            self.assertEqual(result[0]["name"], "vast_asbuilt_report_new.pdf")

    def test_read_config_missing_file(self):
        result = _read_config("/does/not/exist.yaml")
        self.assertIn("not found", result)

    def test_read_write_config_roundtrip(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("original")
            path = f.name
        try:
            _write_config(path, "updated: true\n")
            result = _read_config(path)
            self.assertIn("updated: true", result)
        finally:
            os.unlink(path)


class TestProfileMergeSave(unittest.TestCase):
    """Tests for profile merge-save behavior (POST /profiles)."""

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()
        self.tmpdir = tempfile.mkdtemp()
        self.app.config["PROFILES_PATH"] = os.path.join(self.tmpdir, "profiles.json")

    def tearDown(self):
        import shutil

        if os.path.exists(self.tmpdir):
            shutil.rmtree(self.tmpdir, ignore_errors=True)

    @patch("app._save_profiles")
    @patch("app._load_profiles")
    def test_save_preserves_existing_fields(self, mock_load, mock_save):
        mock_load.return_value = {
            "my-cluster": {
                "cluster_ip": "10.0.0.1",
                "auth_method": "password",
                "username": "admin",
                "password": "secret",
                "token": "",
                "output_dir": "/tmp/reports",
                "enable_port_mapping": True,
                "switch_user": "cumulus",
                "switch_password": "sw_pass",
                "node_user": "vastdata",
                "node_password": "nd_pass",
                "vip_pool": "main",
                "switch_placement": "auto",
                "use_default_creds": True,
            }
        }
        resp = self.client.post(
            "/profiles",
            json={"name": "my-cluster", "cluster_ip": "10.0.0.99"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_save.assert_called_once()
        profile = mock_save.call_args[0][1]["my-cluster"]
        self.assertEqual(profile["cluster_ip"], "10.0.0.99")
        self.assertEqual(profile["username"], "admin")
        self.assertEqual(profile["password"], "secret")
        self.assertEqual(profile["switch_user"], "cumulus")
        self.assertEqual(profile["switch_password"], "sw_pass")
        self.assertTrue(profile["enable_port_mapping"])

    @patch("app._save_profiles")
    @patch("app._load_profiles")
    def test_save_normalizes_api_token_to_token(self, mock_load, mock_save):
        mock_load.return_value = {}
        resp = self.client.post(
            "/profiles",
            json={"name": "tok-cluster", "cluster_ip": "10.0.0.5", "api_token": "my_api_token_123"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_save.assert_called_once()
        profile = mock_save.call_args[0][1]["tok-cluster"]
        self.assertEqual(profile["token"], "my_api_token_123")
        self.assertNotIn("api_token", profile)

    @patch("app._save_profiles")
    @patch("app._load_profiles")
    def test_save_applies_defaults_for_new_profile(self, mock_load, mock_save):
        mock_load.return_value = {}
        resp = self.client.post(
            "/profiles",
            json={"name": "new-cluster", "cluster_ip": "10.0.0.10"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        mock_save.assert_called_once()
        profile = mock_save.call_args[0][1]["new-cluster"]
        self.assertEqual(profile["cluster_ip"], "10.0.0.10")
        self.assertEqual(profile["auth_method"], "password")
        self.assertEqual(profile["switch_user"], "cumulus")
        self.assertEqual(profile["node_user"], "vastdata")
        self.assertEqual(profile["vip_pool"], "main")
        self.assertTrue(profile["use_default_creds"])

    def test_save_without_name_returns_error(self):
        resp = self.client.post(
            "/profiles",
            json={"cluster_ip": "10.0.0.1"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)
        self.assertIn("name", body["error"].lower())


class TestAdvancedOpsRoutes(unittest.TestCase):
    """Tests for Advanced Operations endpoints (/advanced-ops/*)."""

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()

    def test_advanced_ops_page_requires_dev_mode(self):
        app = create_flask_app()
        client = app.test_client()
        resp = client.get("/advanced-ops")
        self.assertEqual(resp.status_code, 403)
        body = json.loads(resp.data)
        self.assertIn("Developer Mode required", body["error"])

    @patch("advanced_ops.get_advanced_ops_manager")
    def test_workflows_list_returns_json(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr.get_workflows.return_value = [
            {"id": "vnetmap", "name": "VAST vnetmap", "description": "Test", "step_count": 7, "enabled": True}
        ]
        mock_get_mgr.return_value = mock_mgr
        resp = self.client.get("/advanced-ops/workflows")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("workflows", body)
        self.assertEqual(len(body["workflows"]), 1)
        self.assertEqual(body["workflows"][0]["id"], "vnetmap")

    @patch("advanced_ops.get_advanced_ops_manager")
    def test_start_workflow_missing_id_returns_error(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr.is_running.return_value = False
        mock_get_mgr.return_value = mock_mgr
        resp = self.client.post("/advanced-ops/start", data={})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)
        self.assertIn("workflow_id", body["error"])

    @patch("advanced_ops.get_advanced_ops_manager")
    def test_run_step_missing_step_id_returns_error(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_get_mgr.return_value = mock_mgr
        resp = self.client.post("/advanced-ops/run-step", data={})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn("error", body)
        self.assertIn("step_id", body["error"])

    @patch("advanced_ops.get_advanced_ops_manager")
    def test_cancel_when_not_running(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr.cancel.return_value = False
        mock_get_mgr.return_value = mock_mgr
        resp = self.client.post("/advanced-ops/cancel")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "no_workflow")

    @patch("advanced_ops.get_advanced_ops_manager")
    def test_reset_clears_state(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_get_mgr.return_value = mock_mgr
        resp = self.client.post("/advanced-ops/reset")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["status"], "reset")
        mock_mgr.reset.assert_called_once()

    @patch("advanced_ops.get_advanced_ops_manager")
    def test_status_returns_json(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr.get_current_state.return_value = None
        mock_mgr.is_running.return_value = False
        mock_get_mgr.return_value = mock_mgr
        resp = self.client.get("/advanced-ops/status")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("state", body)
        self.assertIn("running", body)
        self.assertFalse(body["running"])


class TestAdvancedOpsToolRoutes(unittest.TestCase):
    """Tests for tool management and bundle routes under /advanced-ops/."""

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()

    @patch("tool_manager.ToolManager")
    def test_list_tools_returns_json(self, mock_tm_cls):
        mock_tm = MagicMock()
        mock_tm.get_all_tools_info.return_value = [{"name": "vnetmap.py", "cached": False}]
        mock_tm_cls.return_value = mock_tm
        resp = self.client.get("/advanced-ops/tools")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("tools", body)
        self.assertEqual(len(body["tools"]), 1)

    @patch("advanced_ops.get_advanced_ops_manager")
    @patch("tool_manager.ToolManager")
    def test_update_tools_triggers_download(self, mock_tm_cls, mock_get_mgr):
        mock_get_mgr.return_value = MagicMock()
        mock_tm = MagicMock()
        mock_tm.update_all_tools.return_value = {"updated": 3, "failed": 0}
        mock_tm_cls.return_value = mock_tm
        resp = self.client.post("/advanced-ops/tools/update")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["updated"], 3)
        mock_tm.update_all_tools.assert_called_once()

    @patch("result_bundler.get_result_bundler")
    def test_bundle_list_empty(self, mock_get_bundler):
        mock_bundler = MagicMock()
        mock_bundler.list_bundles.return_value = []
        mock_get_bundler.return_value = mock_bundler
        resp = self.client.get("/advanced-ops/bundles")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("bundles", body)
        self.assertEqual(body["bundles"], [])

    def test_bundle_download_not_found(self):
        resp = self.client.get("/advanced-ops/bundle/download/nonexistent.zip")
        self.assertEqual(resp.status_code, 404)
        body = json.loads(resp.data)
        self.assertIn("error", body)


class TestOneShotLastBundleRoute(unittest.TestCase):
    """Tests for /advanced-ops/bundle/last (Option A direct-download path)."""

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()
        # Disable rehydration by default so the test isn't sensitive to
        # whatever happens to live in the real output/bundles dir.
        self.app.config["ONESHOT_LAST_BUNDLE_REHYDRATED"] = True
        self.app.config["ONESHOT_LAST_BUNDLE"] = {}

    def test_missing_cluster_ip_returns_400(self):
        resp = self.client.get("/advanced-ops/bundle/last")
        self.assertEqual(resp.status_code, 400)

    def test_cluster_without_record_returns_404(self):
        resp = self.client.get("/advanced-ops/bundle/last?cluster_ip=10.0.0.1")
        self.assertEqual(resp.status_code, 404)

    def test_returns_recorded_bundle(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "demo_bundle.zip"
            zip_path.write_bytes(b"PK\x03\x04")  # minimal zip magic
            self.app.config["ONESHOT_LAST_BUNDLE"] = {
                "10.0.0.1": {
                    "bundle_path": str(zip_path),
                    "run_started_at": "2026-03-21T12:00:00",
                    "completed_at": "2026-03-21T12:30:00",
                    "operation_status": {"vnetmap": "success"},
                }
            }
            resp = self.client.get("/advanced-ops/bundle/last?cluster_ip=10.0.0.1")
            self.assertEqual(resp.status_code, 200)
            body = json.loads(resp.data)
            self.assertEqual(body["status"], "ok")
            self.assertEqual(body["name"], "demo_bundle.zip")
            self.assertEqual(body["run_started_at"], "2026-03-21T12:00:00")
            self.assertEqual(body["operation_status"], {"vnetmap": "success"})

    def test_registry_entry_cleared_when_file_missing(self):
        self.app.config["ONESHOT_LAST_BUNDLE"] = {
            "10.0.0.1": {
                "bundle_path": "/does/not/exist.zip",
                "run_started_at": "2026-03-21T12:00:00",
            }
        }
        resp = self.client.get("/advanced-ops/bundle/last?cluster_ip=10.0.0.1")
        self.assertEqual(resp.status_code, 404)
        self.assertNotIn("10.0.0.1", self.app.config["ONESHOT_LAST_BUNDLE"])


class TestBundleCollectFreshness(unittest.TestCase):
    """/advanced-ops/bundle/collect must thread since + operation_status."""

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()
        self.app.config["ONESHOT_LAST_BUNDLE_REHYDRATED"] = True
        self.app.config["ONESHOT_LAST_BUNDLE"] = {
            "10.0.0.1": {
                "bundle_path": "/unused.zip",
                "run_started_at": "2026-03-21T12:00:00",
                "operation_status": {"vnetmap": "failed"},
            }
        }

    @patch("result_bundler.get_result_bundler")
    def test_collect_passes_since_and_operation_status(self, mock_get_bundler):
        from datetime import datetime as _dt

        mock_bundler = MagicMock()
        mock_bundler.collect_results.return_value = {"vnetmap": Path("/tmp/v.json")}
        mock_get_bundler.return_value = mock_bundler
        resp = self.client.post(
            "/advanced-ops/bundle/collect",
            json={"cluster_ip": "10.0.0.1", "cluster_name": "c", "cluster_version": "v"},
        )
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_bundler.collect_results.call_args
        self.assertEqual(kwargs["cluster_ip"], "10.0.0.1")
        self.assertEqual(kwargs["since"], _dt.fromisoformat("2026-03-21T12:00:00"))
        self.assertEqual(kwargs["operation_status"], {"vnetmap": "failed"})

    @patch("result_bundler.get_result_bundler")
    def test_collect_without_registered_cluster_passes_no_since(self, mock_get_bundler):
        mock_bundler = MagicMock()
        mock_bundler.collect_results.return_value = {}
        mock_get_bundler.return_value = mock_bundler
        resp = self.client.post(
            "/advanced-ops/bundle/collect",
            json={"cluster_ip": "10.0.0.9", "cluster_name": "c", "cluster_version": "v"},
        )
        self.assertEqual(resp.status_code, 200)
        _, kwargs = mock_bundler.collect_results.call_args
        self.assertIsNone(kwargs["since"])
        self.assertIsNone(kwargs["operation_status"])


class TestOneShotLastBundleRehydration(unittest.TestCase):
    """Cold-start rehydration must scan output/bundles and only pick one-shot zips."""

    def test_rehydrates_from_one_shot_manifest(self):
        import shutil
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            bundles_dir = data_dir / "output" / "bundles"
            bundles_dir.mkdir(parents=True)

            oneshot_zip = bundles_dir / "validation_bundle_oneshot.zip"
            with zipfile.ZipFile(oneshot_zip, "w") as zf:
                zf.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "run_started_at": "2026-03-21T12:00:00",
                            "created": "2026-03-21T12:30:00",
                            "metadata": {"cluster_ip": "10.0.0.1"},
                            "operation_status": {"vnetmap": "success"},
                        }
                    ),
                )

            rebuild_zip = bundles_dir / "validation_bundle_rebuild.zip"
            with zipfile.ZipFile(rebuild_zip, "w") as zf:
                zf.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "run_started_at": None,
                            "metadata": {"cluster_ip": "10.0.0.1"},
                        }
                    ),
                )
            # Make the rebuild zip newer so a naive implementation would
            # pick it first — the filter must reject it.
            shutil.copystat(oneshot_zip, rebuild_zip)
            os.utime(rebuild_zip, None)

            app = create_flask_app(config={"DEVELOPER_MODE": True})
            client = app.test_client()

            with patch("app.get_data_dir", return_value=data_dir):
                resp = client.get("/advanced-ops/bundle/last?cluster_ip=10.0.0.1")
                self.assertEqual(resp.status_code, 200)
                body = json.loads(resp.data)
                self.assertEqual(Path(body["bundle_path"]).name, "validation_bundle_oneshot.zip")
                self.assertEqual(body["run_started_at"], "2026-03-21T12:00:00")

    def test_rehydration_skips_bundles_without_run_started_at(self):
        import tempfile
        import zipfile

        with tempfile.TemporaryDirectory() as tmp:
            data_dir = Path(tmp)
            bundles_dir = data_dir / "output" / "bundles"
            bundles_dir.mkdir(parents=True)
            bundle = bundles_dir / "ambiguous.zip"
            with zipfile.ZipFile(bundle, "w") as zf:
                zf.writestr(
                    "manifest.json",
                    json.dumps({"metadata": {"cluster_ip": "10.0.0.1"}}),
                )

            app = create_flask_app(config={"DEVELOPER_MODE": True})
            client = app.test_client()
            with patch("app.get_data_dir", return_value=data_dir):
                resp = client.get("/advanced-ops/bundle/last?cluster_ip=10.0.0.1")
            self.assertEqual(resp.status_code, 404)


class TestOneShotLastBundleBackgroundThreadUpdate(unittest.TestCase):
    """Regression test for the 2026-03-21 stale-download bug.

    Symptom (from `import/logs/output-results-0518.txt`):

        12:18:14  Bundle created: validation_bundle_..._20260421_051813.zip
        12:18:26  Downloading last one-shot bundle: ..._20260421_050004.zip

    i.e. the Download button served the *previous* day's bundle even
    though the new one-shot run had just finished.  Root cause:
    ``_record_last_oneshot_bundle`` accesses ``current_app.config`` but
    was invoked from a bare ``threading.Thread`` with no Flask
    application context pushed.  That raised
    ``RuntimeError: Working outside of application context`` which the
    outer ``except Exception: pass`` silently swallowed, so the
    ``ONESHOT_LAST_BUNDLE`` registry was never refreshed and the
    Download button kept serving whatever the cold-start rehydration
    had captured at startup.

    These tests lock in both halves of the fix:

    1. The helper *does* require an app context (regression guard — if
       someone ever removes ``current_app`` from it, this test still
       passes; if the helper regresses to a stateless form, we'll know
       because the no-context call would no longer raise).
    2. Wrapping the call in ``app.app_context()`` makes it succeed and
       updates the registry even from a background thread that never
       saw a request.
    """

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.app.config["ONESHOT_LAST_BUNDLE_REHYDRATED"] = True
        self.app.config["ONESHOT_LAST_BUNDLE"] = {}

    def _fake_runner(self, bundle_path: Path):
        """Minimal runner stub matching the surface ``_record_last_oneshot_bundle`` uses."""
        runner = MagicMock()
        runner.get_state.return_value = {
            "status": "completed",
            "bundle_path": str(bundle_path),
            "started_at": "2026-04-21T05:06:29",
            "completed_at": "2026-04-21T05:18:13",
            "operation_results": {"vnetmap": "success", "support_tools": "success"},
        }
        return runner

    def test_helper_requires_app_context(self):
        """Without an app context, current_app resolution must fail.

        This is the precondition that the background-thread call site
        must satisfy by wrapping the call in ``app.app_context()``.
        """
        import threading

        from app import _record_last_oneshot_bundle

        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "validation_bundle_selab-var-202_20260421_051813.zip"
            zip_path.write_bytes(b"PK\x03\x04")
            runner = self._fake_runner(zip_path)
            credentials = {"cluster_ip": "10.143.11.202"}

            captured: dict = {}

            def _call_from_thread():
                try:
                    _record_last_oneshot_bundle(runner, credentials, {})
                except Exception as exc:  # noqa: BLE001
                    captured["exc"] = exc

            t = threading.Thread(target=_call_from_thread)
            t.start()
            t.join(timeout=5)

            self.assertIn(
                "exc", captured, "Helper must raise without an app context — fix must push one at the call site"
            )
            self.assertIn("application context", str(captured["exc"]).lower())

    def test_background_thread_updates_registry_with_app_context(self):
        """The fix: wrapping the helper in ``app.app_context()`` lets a
        background thread register the newly created bundle, which is
        what /advanced-ops/bundle/last then returns to the Download button.
        """
        import threading

        from app import _record_last_oneshot_bundle

        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "validation_bundle_selab-var-202_20260421_051813.zip"
            zip_path.write_bytes(b"PK\x03\x04")
            runner = self._fake_runner(zip_path)
            credentials = {"cluster_ip": "10.143.11.202"}

            # Simulate a stale cold-start rehydration entry — this is what
            # the user saw: registry already pointed at an older bundle.
            stale_zip = Path(tmp) / "validation_bundle_selab-var-202_20260421_050004.zip"
            stale_zip.write_bytes(b"PK\x03\x04")
            self.app.config["ONESHOT_LAST_BUNDLE"] = {
                "10.143.11.202": {
                    "bundle_path": str(stale_zip),
                    "run_started_at": "2026-04-21T05:00:00",
                    "completed_at": "2026-04-21T05:00:04",
                    "operation_status": {},
                }
            }

            def _run():
                # This mirrors the _run closure in advanced_ops_oneshot_start.
                with self.app.app_context():
                    _record_last_oneshot_bundle(runner, credentials, {})

            t = threading.Thread(target=_run)
            t.start()
            t.join(timeout=5)
            self.assertFalse(t.is_alive(), "Background thread must complete")

            record = self.app.config["ONESHOT_LAST_BUNDLE"].get("10.143.11.202")
            self.assertIsNotNone(record, "Registry must be updated after run_all() completes")
            self.assertEqual(
                Path(record["bundle_path"]).name,
                "validation_bundle_selab-var-202_20260421_051813.zip",
                "Registry must point to the *new* bundle, not the stale cold-start entry",
            )
            self.assertEqual(record["run_started_at"], "2026-04-21T05:06:29")
            self.assertEqual(record["completed_at"], "2026-04-21T05:18:13")

            # And the Download button's endpoint now serves that new bundle.
            client = self.app.test_client()
            resp = client.get("/advanced-ops/bundle/last?cluster_ip=10.143.11.202")
            self.assertEqual(resp.status_code, 200)
            body = json.loads(resp.data)
            self.assertEqual(body["name"], "validation_bundle_selab-var-202_20260421_051813.zip")

    def test_helper_noop_on_incomplete_run(self):
        """If the runner never reached ``completed`` the registry must stay untouched."""
        from app import _record_last_oneshot_bundle

        runner = MagicMock()
        runner.get_state.return_value = {"status": "failed", "bundle_path": None}

        with self.app.app_context():
            _record_last_oneshot_bundle(runner, {"cluster_ip": "10.0.0.1"}, {})

        self.assertEqual(self.app.config["ONESHOT_LAST_BUNDLE"], {})

    def test_helper_noop_when_bundle_file_missing(self):
        """Registry must never point at a nonexistent zip — the download
        endpoint already has a self-healing 404 path, but we prefer to
        never record a broken entry in the first place."""
        from app import _record_last_oneshot_bundle

        runner = MagicMock()
        runner.get_state.return_value = {
            "status": "completed",
            "bundle_path": "/tmp/definitely/does/not/exist.zip",
            "started_at": "2026-04-21T05:06:29",
            "completed_at": "2026-04-21T05:18:13",
            "operation_results": {},
        }

        with self.app.app_context():
            _record_last_oneshot_bundle(runner, {"cluster_ip": "10.0.0.1"}, {})

        self.assertEqual(self.app.config["ONESHOT_LAST_BUNDLE"], {})


class TestStateSnapshotRoute(unittest.TestCase):
    """Tests for /advanced-ops/state-snapshot endpoint."""

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()

    @patch("advanced_ops.get_advanced_ops_manager")
    def test_state_snapshot_returns_json(self, mock_get_mgr):
        mock_mgr = MagicMock()
        mock_mgr._output_buffer = []
        mock_mgr.is_running.return_value = False
        mock_mgr.current_workflow_id = None
        mock_mgr.get_state.return_value = None
        mock_get_mgr.return_value = mock_mgr
        self.app.config["ONESHOT_RUNNING"] = False
        self.app.config["ONESHOT_RUNNER"] = None
        self.app.config["ONESHOT_RESULT"] = None
        resp = self.client.get("/advanced-ops/state-snapshot")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertIn("oneshot", body)
        self.assertIn("workflow", body)
        self.assertIn("output_count", body)
        self.assertFalse(body["oneshot"]["running"])
        self.assertFalse(body["workflow"]["running"])


class TestLogCapacityRoutes(unittest.TestCase):
    """Tests for /advanced-ops/logs/* endpoints."""

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()

    @patch("utils.ops_log_manager.OpsLogManager")
    def test_capacity_returns_stats(self, mock_cls):
        mock_inst = MagicMock()
        mock_inst.check_capacity.return_value = {
            "total_bytes": 500,
            "file_count": 2,
            "max_bytes": 1073741824,
            "over_limit": False,
            "usage_percent": 0.0,
        }
        mock_cls.return_value = mock_inst
        resp = self.client.get("/advanced-ops/logs/capacity")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertFalse(body["over_limit"])

    @patch("utils.ops_log_manager.OpsLogManager")
    def test_purge_returns_result(self, mock_cls):
        mock_inst = MagicMock()
        mock_inst.purge_oldest.return_value = {"purged": 1, "freed_bytes": 1024}
        mock_cls.return_value = mock_inst
        resp = self.client.post("/advanced-ops/logs/purge")
        self.assertEqual(resp.status_code, 200)
        body = json.loads(resp.data)
        self.assertEqual(body["purged"], 1)


class TestOneShotValidateAutofillForwarding(unittest.TestCase):
    """Regression coverage for the Autofill wiring on pre-validation.

    The /advanced-ops/oneshot/validate endpoint must forward
    ``use_default_creds`` and ``config_path`` to ``OneShotRunner`` so the
    Switch SSH probe iterates the full ``default_switch_passwords`` list
    (Vastdata1! -> VastData1! -> Cumu1usLinux! -> admin/admin).  A prior
    regression omitted these kwargs, silently collapsing the probe to just
    the operator-entered password plus ``admin/admin`` (2 combos) even
    though the toggle was on in the UI.
    """

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()

    @patch("oneshot_runner.OneShotRunner")
    def test_validate_forwards_use_default_creds_and_config_path(self, mock_runner_cls):
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner
        payload = {
            "selected_ops": ["switch_config"],
            "include_health": True,
            "use_default_creds": True,
            "cluster_ip": "10.0.0.1",
            "switch_password": "OperatorPw!",
        }
        resp = self.client.post(
            "/advanced-ops/oneshot/validate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        # 200 on success, 409 if another job is already running; either way
        # the runner must have been constructed with the forwarded args.
        self.assertIn(resp.status_code, (200, 409))
        mock_runner_cls.assert_called_once()
        kwargs = mock_runner_cls.call_args.kwargs
        self.assertTrue(kwargs.get("use_default_creds"))
        self.assertEqual(kwargs.get("config_path"), self.app.config.get("CONFIG_PATH"))

    @patch("oneshot_runner.OneShotRunner")
    def test_validate_defaults_use_default_creds_false_when_absent(self, mock_runner_cls):
        mock_runner = MagicMock()
        mock_runner_cls.return_value = mock_runner
        payload = {
            "selected_ops": ["switch_config"],
            "cluster_ip": "10.0.0.1",
        }
        resp = self.client.post(
            "/advanced-ops/oneshot/validate",
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertIn(resp.status_code, (200, 409))
        mock_runner_cls.assert_called_once()
        kwargs = mock_runner_cls.call_args.kwargs
        self.assertFalse(kwargs.get("use_default_creds"))


class TestOneShotStartHandoff(unittest.TestCase):
    """The /advanced-ops/oneshot/start endpoint must carry the per-switch
    password map from the preceding Pre-Validation runner onto the new
    execution runner.  Without this handoff the map is reset to an empty
    dict at construction time and ``VnetmapWorkflow`` falls back to the
    legacy single-password candidate sweep — which is exactly what
    ``import/Assets-2026-0420c/output-results-Output-Results-2026-0420d.txt``
    showed even though Pre-Validation authenticated every switch."""

    def setUp(self):
        self.app = create_flask_app(config={"DEVELOPER_MODE": True})
        self.client = self.app.test_client()

    @patch("oneshot_runner.OneShotRunner")
    def test_start_seeds_new_runner_from_prior_runner(self, mock_runner_cls):
        new_runner = MagicMock()
        mock_runner_cls.return_value = new_runner

        prior_runner = MagicMock()
        prior_runner.switch_password_by_ip = {
            "10.1.1.10": "Vastdata1!",
            "10.1.1.11": "VastData1!",
        }
        prior_runner.switch_user_by_ip = {
            "10.1.1.10": "cumulus",
            "10.1.1.11": "cumulus",
        }

        self.app.config["ONESHOT_RUNNING"] = False
        self.app.config["ONESHOT_RUNNER"] = prior_runner

        payload = {
            "selected_ops": ["vnetmap"],
            "cluster_ip": "10.0.0.1",
            "switch_password": "Vastdata1!",
        }
        resp = self.client.post(
            "/advanced-ops/oneshot/start",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        new_runner.seed_switch_credentials.assert_called_once()
        call_kwargs = new_runner.seed_switch_credentials.call_args.kwargs
        self.assertEqual(
            call_kwargs["switch_password_by_ip"],
            {"10.1.1.10": "Vastdata1!", "10.1.1.11": "VastData1!"},
        )
        self.assertEqual(
            call_kwargs["switch_user_by_ip"],
            {"10.1.1.10": "cumulus", "10.1.1.11": "cumulus"},
        )

    @patch("oneshot_runner.OneShotRunner")
    def test_start_skips_seed_when_no_prior_runner(self, mock_runner_cls):
        """First-launch flow: nothing to hand off, so don't touch the
        setter.  This protects the runtime-fallback path in ``run_all``
        from being shadowed by an empty seed call."""
        new_runner = MagicMock()
        mock_runner_cls.return_value = new_runner

        self.app.config["ONESHOT_RUNNING"] = False
        self.app.config["ONESHOT_RUNNER"] = None

        payload = {
            "selected_ops": ["vnetmap"],
            "cluster_ip": "10.0.0.1",
            "switch_password": "Vastdata1!",
        }
        resp = self.client.post(
            "/advanced-ops/oneshot/start",
            data=json.dumps(payload),
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 200)
        new_runner.seed_switch_credentials.assert_not_called()


if __name__ == "__main__":
    unittest.main()
