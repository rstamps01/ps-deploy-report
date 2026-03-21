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
        self.assertIn(b"Generate", resp.data)
        self.assertIn(b"Reports", resp.data)
        self.assertIn(b"Configuration", resp.data)

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

class TestConfigRoutes(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app()
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

    @patch("rack_diagram.RackDiagram")
    @patch("api_handler.create_vast_api_handler")
    def test_api_discover_auth_failure_returns_401(self, mock_create_handler, mock_rack_diagram):
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

    @patch("rack_diagram.RackDiagram")
    @patch("api_handler.create_vast_api_handler")
    def test_api_discover_success_returns_racks_and_switches(self, mock_create_handler, mock_rack_diagram):
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
        self.app = create_flask_app()
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


if __name__ == "__main__":
    unittest.main()
