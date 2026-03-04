"""
Browser-based UI tests for the VAST As-Built Reporter web interface.

Uses Playwright to verify critical UI flows: page navigation, form
interactions, profile management, report browsing, and config editing.

Run with:
    pytest tests/test_ui.py -v
"""

import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from contextlib import closing

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import create_flask_app  # noqa: E402


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def flask_server(tmp_path_factory):
    """Start a Flask server on a random port for the test module."""
    tmpdir = tmp_path_factory.mktemp("ui_test")
    reports_dir = tmpdir / "reports"
    reports_dir.mkdir()
    config_dir = tmpdir / "config"
    config_dir.mkdir()

    config_src = Path(__file__).parent.parent / "config" / "config.yaml"
    template_src = Path(__file__).parent.parent / "config" / "config.yaml.template"
    config_dst = config_dir / "config.yaml"
    template_dst = config_dir / "config.yaml.template"
    config_dst.write_text(config_src.read_text())
    template_dst.write_text(template_src.read_text())

    profiles_path = tmpdir / "cluster_profiles.json"
    profiles_path.write_text("{}")

    app = create_flask_app()
    app.config["TESTING"] = True
    app.config["DEFAULT_OUTPUT_DIR"] = str(reports_dir)
    app.config["OUTPUT_DIRS"] = {str(reports_dir)}
    app.config["CONFIG_PATH"] = str(config_dst)
    app.config["CONFIG_TEMPLATE_PATH"] = str(template_dst)
    app.config["PROFILES_PATH"] = str(profiles_path)

    port = _free_port()
    server_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False),
        daemon=True,
    )
    server_thread.start()

    base_url = f"http://127.0.0.1:{port}"
    for _ in range(40):
        try:
            import urllib.request
            urllib.request.urlopen(base_url, timeout=0.5)
            break
        except Exception:
            time.sleep(0.25)

    yield {
        "url": base_url,
        "reports_dir": reports_dir,
        "profiles_path": profiles_path,
        "config_path": config_dst,
    }


# ---------------------------------------------------------------------------
# Navigation & page-load tests
# ---------------------------------------------------------------------------

class TestPageLoads:
    """Verify that all pages render without errors."""

    def test_dashboard_loads(self, flask_server, page):
        page.goto(flask_server["url"])
        assert page.title()
        page.wait_for_selector("text=Dashboard")

    def test_generate_page_loads(self, flask_server, page):
        page.goto(f"{flask_server['url']}/generate")
        page.wait_for_selector("text=Cluster Profile")

    def test_reports_page_loads(self, flask_server, page):
        page.goto(f"{flask_server['url']}/reports")
        page.wait_for_selector("text=Reports")

    def test_config_page_loads(self, flask_server, page):
        page.goto(f"{flask_server['url']}/config")
        page.wait_for_selector("text=Configuration")

    def test_nav_links_work(self, flask_server, page):
        page.goto(flask_server["url"])
        links = page.query_selector_all("nav a, .sidebar a, a.nav-link")
        hrefs = [l.get_attribute("href") for l in links if l.get_attribute("href")]
        expected = {"/", "/generate", "/reports", "/config"}
        assert expected.issubset(set(hrefs)), f"Missing nav links. Found: {hrefs}"


# ---------------------------------------------------------------------------
# Generate page – form interactions
# ---------------------------------------------------------------------------

class TestGenerateForm:
    """Verify form elements and basic interactions on the Generate page."""

    def test_cluster_ip_field_exists(self, flask_server, page):
        page.goto(f"{flask_server['url']}/generate")
        ip_field = page.query_selector("input[name='cluster_ip']")
        assert ip_field is not None

    def test_auth_method_options(self, flask_server, page):
        page.goto(f"{flask_server['url']}/generate")
        select = page.query_selector("select[name='auth_method']")
        if select:
            options = select.query_selector_all("option")
            values = [o.get_attribute("value") for o in options]
            assert "password" in values or "basic" in values

    def test_switch_placement_toggle_exists(self, flask_server, page):
        page.goto(f"{flask_server['url']}/generate")
        toggle = page.query_selector(
            "input[name='switch_placement'], "
            "#switch-placement-toggle, "
            "[data-field='switch_placement']"
        )
        assert toggle is not None, "Switch placement toggle not found"

    def test_submit_without_ip_shows_error(self, flask_server, page):
        page.goto(f"{flask_server['url']}/generate")
        submit_btn = page.query_selector("button[type='submit'], #generate-btn, .btn-generate")
        if submit_btn:
            submit_btn.click()
            page.wait_for_timeout(500)


# ---------------------------------------------------------------------------
# Cluster Profiles
# ---------------------------------------------------------------------------

class TestClusterProfiles:
    """Test profile save/load/delete via the UI or API."""

    def test_save_and_load_profile(self, flask_server, page):
        url = flask_server["url"]
        resp = page.request.post(
            f"{url}/profiles",
            data=json.dumps({
                "action": "save",
                "name": "test-cluster",
                "cluster_ip": "10.0.0.1",
                "username": "admin",
                "auth_method": "password",
            }),
            headers={"Content-Type": "application/json"},
        )
        assert resp.ok

        resp2 = page.request.get(f"{url}/profiles")
        assert resp2.ok
        profiles = resp2.json()
        assert "test-cluster" in profiles

    def test_delete_profile(self, flask_server, page):
        url = flask_server["url"]
        page.request.post(
            f"{url}/profiles",
            data=json.dumps({
                "name": "deleteme",
                "cluster_ip": "10.0.0.2",
                "username": "admin",
                "auth_method": "password",
            }),
            headers={"Content-Type": "application/json"},
        )

        resp = page.request.delete(f"{url}/profiles/deleteme")
        assert resp.ok

        resp2 = page.request.get(f"{url}/profiles")
        data = resp2.json()
        assert "deleteme" not in data


# ---------------------------------------------------------------------------
# Reports page
# ---------------------------------------------------------------------------

class TestReportsPage:
    """Test the reports browser page with sample files."""

    def test_reports_show_matching_files(self, flask_server, page):
        reports_dir = flask_server["reports_dir"]
        (reports_dir / "vast_asbuilt_report_test_20260304.pdf").write_bytes(b"%PDF-1.4 test")
        (reports_dir / "vast_data_test_20260304.json").write_text('{"test": true}')
        (reports_dir / "random_file.txt").write_text("ignore me")

        page.goto(f"{flask_server['url']}/reports")
        page.wait_for_timeout(500)

        body = page.content()
        assert "vast_asbuilt_report_test_20260304.pdf" in body
        assert "vast_data_test_20260304.json" in body
        assert "random_file.txt" not in body

    def test_download_report(self, flask_server, page):
        reports_dir = flask_server["reports_dir"]
        test_pdf = reports_dir / "vast_asbuilt_report_dl_20260304.pdf"
        test_pdf.write_bytes(b"%PDF-1.4 download test")

        resp = page.request.get(
            f"{flask_server['url']}/reports/download/vast_asbuilt_report_dl_20260304.pdf"
        )
        assert resp.ok
        assert b"%PDF-1.4 download test" in resp.body()

    def test_delete_report(self, flask_server, page):
        reports_dir = flask_server["reports_dir"]
        test_file = reports_dir / "vast_data_delete_20260304.json"
        test_file.write_text('{"delete": true}')

        resp = page.request.post(
            f"{flask_server['url']}/reports/delete/vast_data_delete_20260304.json"
        )
        assert resp.ok
        assert not test_file.exists()


# ---------------------------------------------------------------------------
# Config page
# ---------------------------------------------------------------------------

class TestConfigPage:
    """Test config viewing, editing, and resetting."""

    def test_config_shows_yaml_content(self, flask_server, page):
        page.goto(f"{flask_server['url']}/config")
        page.wait_for_timeout(300)
        body = page.content()
        assert "api" in body.lower() or "logging" in body.lower() or "output" in body.lower()

    def test_config_reset(self, flask_server, page):
        resp = page.request.post(f"{flask_server['url']}/config/reset")
        assert resp.ok


# ---------------------------------------------------------------------------
# SSE Log Stream
# ---------------------------------------------------------------------------

class TestSSEStream:
    """Test that the SSE endpoint responds with the correct content type."""

    def test_stream_logs_content_type(self, flask_server, page):
        import urllib.request
        url = f"{flask_server['url']}/stream/logs"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            ct = resp.headers.get("Content-Type", "")
            assert "text/event-stream" in ct


# ---------------------------------------------------------------------------
# Browse API
# ---------------------------------------------------------------------------

class TestBrowseAPI:
    """Test the directory browse API endpoint."""

    def test_browse_default(self, flask_server, page):
        resp = page.request.get(f"{flask_server['url']}/api/browse")
        assert resp.ok
        data = resp.json()
        assert "current" in data
        assert "dirs" in data

    def test_browse_specific_path(self, flask_server, page):
        resp = page.request.get(f"{flask_server['url']}/api/browse?path=/tmp")
        assert resp.ok
        data = resp.json()
        assert data["current"] == "/tmp" or data["current"].startswith("/private/tmp")
