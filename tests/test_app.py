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

from app import create_flask_app, _list_reports, _read_config, _write_config


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
        self.assertIn(b"1.4.0", resp.data)

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
        resp = self.client.post("/generate", data={
            "cluster_ip": "10.0.0.1",
            "auth_method": "password",
            "username": "support",
            "password": "test",
        })
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


class TestSSEStream(unittest.TestCase):

    def setUp(self):
        self.app = create_flask_app()
        self.client = self.app.test_client()

    def test_stream_logs_returns_event_stream(self):
        resp = self.client.get("/stream/logs")
        self.assertTrue(resp.content_type.startswith("text/event-stream"))


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
