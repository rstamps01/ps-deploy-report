"""
Route tests for the Validation Results page and its results API (TP-4).

Every Tech Port profile stores the same management IP (``192.168.2.2``), so
the page must filter by the per-cluster folder identity (``cluster_key``)
rather than by IP, or one cluster's artifacts are listed under another.
"""

import json
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import create_flask_app  # noqa: E402
from utils.cluster_paths import cluster_paths, write_cluster_marker  # noqa: E402

TECH_PORT_IP = "192.168.2.2"
VMS_HTTPS_IP = "192.0.2.10"
KEY_A = "ACME-A__PSNT0001"
KEY_B = "ACME-B__PSNT0002"
KEY_C = "ACME-C__PSNT0003"


def _make_cluster_folder(data_dir: Path, key: str, name: str, marker_ip: str, ts: str) -> None:
    cp = cluster_paths(data_dir, key)
    cp.ensure_all()
    write_cluster_marker(cp.root, {"name": name, "cluster_ip": marker_ip})
    (cp.reports / f"vast_data_{name}_{ts}.json").write_text(
        json.dumps({"cluster_ip": marker_ip, "cluster_summary": {"name": name}})
    )
    (cp.health / f"health_check_{name}_{ts}.json").write_text(json.dumps({"cluster_ip": marker_ip, "results": []}))
    (cp.scripts / f"vperfsanity_results_{marker_ip}_{ts}.txt").write_text(f"perf {name}")
    with zipfile.ZipFile(cp.bundles / f"validation_bundle_{name}_{ts}.zip", "w") as zf:
        zf.writestr("manifest.json", json.dumps({"metadata": {"cluster_ip": marker_ip}, "files": []}))


@pytest.fixture
def client(tmp_path, monkeypatch):
    import utils

    monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)

    _make_cluster_folder(tmp_path, KEY_A, "ACME-A", TECH_PORT_IP, "20260301_120000")
    _make_cluster_folder(tmp_path, KEY_B, "ACME-B", TECH_PORT_IP, "20260302_120000")
    _make_cluster_folder(tmp_path, KEY_C, "ACME-C", VMS_HTTPS_IP, "20260303_120000")
    health = tmp_path / "output" / "health"
    health.mkdir(parents=True, exist_ok=True)
    (health / "health_check_old_20250101_120000.json").write_text(json.dumps({"cluster_ip": TECH_PORT_IP}))

    profiles_path = tmp_path / "cluster_profiles.json"
    profiles_path.write_text(
        json.dumps(
            {
                "acme-a": {"cluster_ip": TECH_PORT_IP, "tech_port": True},
                "acme-b": {"cluster_ip": TECH_PORT_IP, "tech_port": True},
                "acme-c": {"cluster_ip": VMS_HTTPS_IP},
            }
        )
    )

    app = create_flask_app(config={"DEVELOPER_MODE": True})
    app.config["TESTING"] = True
    app.config["PROFILES_PATH"] = str(profiles_path)
    return app.test_client()


def _entries(resp):
    assert resp.status_code == 200
    return [e for v in resp.get_json()["operations"].values() for e in v]


class TestResultsApiClusterKey:
    def test_tech_port_clusters_never_mix(self, client):
        """REGRESSION (TP-4): ``?cluster_key=`` lists only that cluster's files."""
        for mine, other in ((KEY_A, KEY_B), (KEY_B, KEY_A)):
            entries = _entries(client.get(f"/validation-results/api/results?cluster_key={mine}"))
            ops = {e["operation"] for e in entries}
            assert {"asbuilt_reports", "health_checks", "vperfsanity", "bundles"} <= ops
            assert {e["cluster_key"] for e in entries} == {mine}
            assert not any(other in e["path"] for e in entries)

    def test_unassigned_lists_legacy_tech_port_files(self, client):
        entries = _entries(client.get("/validation-results/api/results?cluster_key=__unassigned__"))
        assert [e["filename"] for e in entries] == ["health_check_old_20250101_120000.json"]

    def test_cluster_ip_still_accepted_for_vms_https(self, client):
        entries = _entries(client.get(f"/validation-results/api/results?cluster_ip={VMS_HTTPS_IP}"))
        assert entries
        assert {e["cluster_key"] for e in entries} == {KEY_C}

    def test_tech_port_ip_bookmark_does_not_mix(self, client):
        entries = _entries(client.get(f"/validation-results/api/results?cluster_ip={TECH_PORT_IP}"))
        assert [e["filename"] for e in entries] == ["health_check_old_20250101_120000.json"]

    def test_no_filter_lists_everything(self, client):
        entries = _entries(client.get("/validation-results/api/results"))
        assert {e["cluster_key"] for e in entries} == {KEY_A, KEY_B, KEY_C, ""}


class TestResultsPageDropdown:
    def test_dropdown_lists_tech_port_clusters_by_key(self, client):
        resp = client.get("/validation-results")
        assert resp.status_code == 200
        html = resp.get_data(as_text=True)
        assert f'data-param="cluster_key" value="{KEY_A}"' in html
        assert f'data-param="cluster_key" value="{KEY_B}"' in html
        assert f"ACME-A — {TECH_PORT_IP}" in html
        assert f'data-param="cluster_ip" value="{VMS_HTTPS_IP}"' in html
        assert 'data-param="cluster_key" value="__unassigned__"' in html
        assert "Unassigned (legacy)" in html
        assert f'value="{TECH_PORT_IP}"' not in html

    def test_dropdown_escapes_cluster_names(self, client, tmp_path):
        _make_cluster_folder(tmp_path, "ACME-X", "ACME-X", TECH_PORT_IP, "20260304_120000")
        write_cluster_marker(cluster_paths(tmp_path, "ACME-X").root, {"name": "<b>ACME-X</b>"})
        html = client.get("/validation-results").get_data(as_text=True)
        assert "<b>ACME-X</b>" not in html
        assert "&lt;b&gt;ACME-X&lt;/b&gt;" in html
