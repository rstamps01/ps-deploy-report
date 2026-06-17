"""Tests for the QP-2 WRITE side of per-cluster artifact segmentation.

Complements ``tests/test_cluster_paths.py`` (foundation module) by proving the
writers route artifacts under ``clusters/<key>/`` when
``output.segment_by_cluster`` is enabled and fall back to the legacy flat
layout when it is disabled:

* ``ScriptRunner`` local-dir override (workflow script output base)
* workflow ``set_output_dir`` threading through to the ScriptRunner
* ``report_builder`` cluster-scoped diagram directory
* ``_find_latest_vnetmap_output`` cluster-first then legacy fallback (app +
  one-shot)
* ``main._run_from_json`` report/marker segmentation gate
* the shared ``utils.cluster_output`` helpers
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import utils  # noqa: E402
from utils import cluster_paths as cp  # noqa: E402
from utils import cluster_output as co  # noqa: E402


# ---------------------------------------------------------------------------
# ScriptRunner local-dir override
# ---------------------------------------------------------------------------
class TestScriptRunnerLocalDir:
    def test_override_via_constructor(self, tmp_path):
        from script_runner import ScriptRunner

        target = tmp_path / "clusters" / "c1" / "output" / "scripts"
        runner = ScriptRunner(local_dir=target)
        assert runner.get_local_dir() == target
        assert target.is_dir()

    def test_default_unchanged(self, tmp_path, monkeypatch):
        from script_runner import ScriptRunner

        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        runner = ScriptRunner()
        assert runner.get_local_dir() == tmp_path / "output" / "scripts"

    def test_set_local_dir(self, tmp_path):
        from script_runner import ScriptRunner

        runner = ScriptRunner()
        target = tmp_path / "clusters" / "c1" / "output" / "scripts"
        runner.set_local_dir(target)
        assert runner.get_local_dir() == target

    def test_subdir_composition_matches_cluster_paths(self, tmp_path):
        """switch_config / network_config workflows append a subdir to the base."""
        from script_runner import ScriptRunner

        paths = cp.cluster_paths(tmp_path, "c1")
        runner = ScriptRunner(local_dir=paths.scripts)
        assert runner.get_local_dir() / "switch_configs" == paths.switch_configs
        assert runner.get_local_dir() / "network_configs" == paths.network_configs


# ---------------------------------------------------------------------------
# Workflow set_output_dir threading
# ---------------------------------------------------------------------------
class TestWorkflowOutputDirThreading:
    def test_set_output_dir_updates_existing_runner(self, tmp_path):
        from script_runner import ScriptRunner
        from workflows.vnetmap_workflow import VnetmapWorkflow

        wf = VnetmapWorkflow()
        wf._script_runner = ScriptRunner()
        target = cp.cluster_paths(tmp_path, "c1").scripts
        wf.set_output_dir(target)
        assert wf._script_runner.get_local_dir() == target

    def test_set_output_dir_stored_for_lazy_runner(self, tmp_path):
        from workflows.support_tool_workflow import SupportToolWorkflow

        wf = SupportToolWorkflow()
        target = cp.cluster_paths(tmp_path, "c1").scripts
        wf.set_output_dir(target)
        # Lazy runner picks up the stored override on creation (mirrors run_step).
        from script_runner import ScriptRunner

        wf._script_runner = ScriptRunner(local_dir=wf._output_dir)
        assert wf._script_runner.get_local_dir() == target

    def test_all_workflows_expose_set_output_dir(self):
        from workflows.vnetmap_workflow import VnetmapWorkflow
        from workflows.support_tool_workflow import SupportToolWorkflow
        from workflows.vperfsanity_workflow import VperfsanityWorkflow
        from workflows.switch_config_workflow import SwitchConfigWorkflow
        from workflows.network_config_workflow import NetworkConfigWorkflow
        from workflows.log_bundle_workflow import LogBundleWorkflow

        for cls in (
            VnetmapWorkflow,
            SupportToolWorkflow,
            VperfsanityWorkflow,
            SwitchConfigWorkflow,
            NetworkConfigWorkflow,
            LogBundleWorkflow,
        ):
            assert hasattr(cls(), "set_output_dir")


# ---------------------------------------------------------------------------
# report_builder diagrams dir
# ---------------------------------------------------------------------------
class TestReportBuilderDiagramsDir:
    def _builder(self, segment):
        from report_builder import create_report_builder

        return create_report_builder(segment_by_cluster=segment)

    def test_segmented_diagrams_dir(self, tmp_path, monkeypatch):
        import report_builder

        monkeypatch.setattr(report_builder, "get_data_dir", lambda: tmp_path)
        builder = self._builder(True)
        data = {"cluster_summary": {"name": "lax01", "psnt": "P1"}}
        assert builder._resolve_diagrams_dir(data) == tmp_path / "clusters" / "lax01__P1" / "output" / "diagrams"

    def test_legacy_diagrams_dir(self, tmp_path, monkeypatch):
        import report_builder

        monkeypatch.setattr(report_builder, "get_data_dir", lambda: tmp_path)
        builder = self._builder(False)
        data = {"cluster_summary": {"name": "lax01", "psnt": "P1"}}
        assert builder._resolve_diagrams_dir(data) == tmp_path / "output" / "diagrams"


# ---------------------------------------------------------------------------
# vnetmap finder: cluster-first then legacy
# ---------------------------------------------------------------------------
def _make_vnetmap(scripts_dir: Path, cluster_ip: str, stamp: str) -> Path:
    scripts_dir.mkdir(parents=True, exist_ok=True)
    f = scripts_dir / f"vnetmap_output_{cluster_ip}_{stamp}.txt"
    f.write_text("x")
    return f


class TestFindLatestVnetmapApp:
    def test_prefers_cluster_then_legacy(self, tmp_path, monkeypatch):
        import app

        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        ip = "192.168.2.2"
        key = "lax01__P1"
        legacy = _make_vnetmap(tmp_path / "output" / "scripts", ip, "20260101_000000")
        cluster = _make_vnetmap(cp.cluster_paths(tmp_path, key).scripts, ip, "20260101_010101")

        assert app._find_latest_vnetmap_output(ip, cluster_key=key) == cluster
        assert app._find_latest_vnetmap_output(ip) == legacy

    def test_falls_back_to_legacy_when_cluster_empty(self, tmp_path, monkeypatch):
        import app

        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        ip = "10.0.0.5"
        legacy = _make_vnetmap(tmp_path / "output" / "scripts", ip, "20260101_000000")
        assert app._find_latest_vnetmap_output(ip, cluster_key="lax01__P1") == legacy


class TestFindLatestVnetmapOneShot:
    def _runner(self):
        from oneshot_runner import OneShotRunner

        return OneShotRunner([], {})

    def test_prefers_cluster_then_legacy(self, tmp_path, monkeypatch):
        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        ip = "192.168.2.2"
        key = "lax01__P1"
        _make_vnetmap(tmp_path / "output" / "scripts", ip, "20260101_000000")
        cluster = _make_vnetmap(cp.cluster_paths(tmp_path, key).scripts, ip, "20260101_010101")
        runner = self._runner()
        assert runner._find_latest_vnetmap_output(ip, cluster_key=key) == cluster

    def test_empty_ip_returns_none(self):
        assert self._runner()._find_latest_vnetmap_output("") is None


# ---------------------------------------------------------------------------
# shared cluster_output helpers
# ---------------------------------------------------------------------------
class TestClusterOutputHelpers:
    def test_disabled_returns_none(self, tmp_path):
        config = {"output": {"segment_by_cluster": False}}
        assert co.cluster_paths_if_enabled(config, {"cluster_summary": {"name": "c1"}}, data_dir=tmp_path) is None

    def test_enabled_resolves_paths(self, tmp_path):
        config = {"output": {"segment_by_cluster": True}}
        data = {"cluster_summary": {"name": "lax01", "psnt": "P1"}, "cluster_ip": "192.168.2.2"}
        paths = co.cluster_paths_if_enabled(config, data, data_dir=tmp_path)
        assert paths is not None
        assert paths.reports == tmp_path / "clusters" / "lax01__P1" / "reports"

    def test_default_enabled_when_missing(self, tmp_path):
        data = {"cluster_summary": {"name": "c1"}}
        assert co.cluster_paths_if_enabled(None, data, data_dir=tmp_path) is not None

    def test_build_marker_identity(self):
        data = {"cluster_summary": {"name": "lax01", "psnt": "P1", "guid": "0xabc"}, "cluster_ip": "192.168.2.2"}
        ident = co.build_marker_identity(data, version="9.9")
        assert ident["name"] == "lax01"
        assert ident["psnt"] == "P1"
        assert ident["guid"] == "0xabc"
        assert ident["cluster_ip"] == "192.168.2.2"
        assert ident["version"] == "9.9"

    def test_build_marker_identity_explicit_ip(self):
        ident = co.build_marker_identity({"cluster_summary": {"name": "c1"}}, cluster_ip="10.0.0.9")
        assert ident["cluster_ip"] == "10.0.0.9"


# ---------------------------------------------------------------------------
# main._run_from_json segmentation gate
# ---------------------------------------------------------------------------
class TestRunFromJsonSegmentation:
    """``--from-json`` honors the explicit CLI ``--output-dir`` verbatim.

    QP-2 per-cluster segmentation applies to the app-managed data directory
    flows (web / one-shot / advanced-ops), NOT to an explicit CLI output dir.
    Offline replay writes the regenerated PDF directly into the operator-named
    directory regardless of the ``output.segment_by_cluster`` flag, so the
    documented CI-deterministic replay contract (and ``test_main_from_json``)
    keeps holding.
    """

    def _write_json(self, tmp_path, name="lax01", psnt="P1"):
        data = {"cluster_summary": {"name": name, "psnt": psnt}, "cluster_ip": "192.168.2.2"}
        src = tmp_path / "vast_data_lax01.json"
        src.write_text(json.dumps(data))
        return src

    def _fake_builder_capturing(self, captured):
        def _factory(*args, **kwargs):
            mock = MagicMock()
            captured["segment"] = kwargs.get("segment_by_cluster")

            def _gen(processed, path):
                captured["pdf"] = Path(path)
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text("pdf")
                return True

            mock.generate_pdf_report.side_effect = _gen
            return mock

        return _factory

    def test_writes_to_output_dir_when_flag_enabled(self, tmp_path, monkeypatch):
        """Even with segmentation enabled, an explicit output dir is honored."""
        import main

        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        captured: dict = {}
        monkeypatch.setattr(main, "create_report_builder", self._fake_builder_capturing(captured))
        src = self._write_json(tmp_path)
        out_dir = tmp_path / "given_out"
        rc = main._run_from_json(str(src), str(out_dir), MagicMock(), config={"output": {"segment_by_cluster": True}})

        assert rc == 0
        # PDF lands directly in the operator-named dir — no clusters/ nesting.
        assert captured["pdf"].parent == out_dir
        assert not (tmp_path / "clusters").exists()
        # Replay never opts the builder into diagram segmentation.
        assert not captured["segment"]

    def test_writes_to_output_dir_when_flag_disabled(self, tmp_path, monkeypatch):
        import main

        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        captured: dict = {}
        monkeypatch.setattr(main, "create_report_builder", self._fake_builder_capturing(captured))
        src = self._write_json(tmp_path)
        out_dir = tmp_path / "given_out"
        rc = main._run_from_json(str(src), str(out_dir), MagicMock(), config={"output": {"segment_by_cluster": False}})

        assert rc == 0
        assert captured["pdf"].parent == out_dir
        assert not (tmp_path / "clusters").exists()


# ---------------------------------------------------------------------------
# One-shot operation-phase segmentation (Blocker 1)
# ---------------------------------------------------------------------------
class _RecordingWorkflow:
    """Minimal workflow stand-in that records set_output_dir and writes a file."""

    name = "Recording"

    def __init__(self, holder):
        self._holder = holder
        self._output_dir = None

    def set_output_callback(self, cb):
        pass

    def set_credentials(self, creds):
        pass

    def set_output_dir(self, d):
        self._output_dir = Path(d)
        self._holder["dir"] = Path(d)

    def get_steps(self):
        return [{"id": 1, "name": "save"}]

    def run_step(self, step_id):
        self._output_dir.mkdir(parents=True, exist_ok=True)
        (self._output_dir / "artifact.txt").write_text("x")
        return {"success": True, "message": "ok"}


class TestOneShotOperationSegmentation:
    def test_run_operations_wires_output_dir_and_lands_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        import workflows
        from oneshot_runner import OneShotRunner

        holder: dict = {}
        monkeypatch.setattr(
            workflows.WorkflowRegistry,
            "get",
            classmethod(lambda cls, op: _RecordingWorkflow(holder)),
        )
        runner = OneShotRunner(["vnetmap"], {"cluster_ip": "192.168.2.2"})
        scripts = cp.cluster_paths(tmp_path, "lax01__P1").scripts
        runner._cluster_paths = cp.cluster_paths(tmp_path, "lax01__P1")
        runner._cluster_paths.ensure_all()

        runner._run_operations()

        assert holder["dir"] == scripts
        assert (scripts / "artifact.txt").exists()

    def test_run_operations_flat_when_no_cluster_paths(self, tmp_path, monkeypatch):
        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        import workflows
        from oneshot_runner import OneShotRunner

        holder: dict = {}
        monkeypatch.setattr(
            workflows.WorkflowRegistry,
            "get",
            classmethod(lambda cls, op: _RecordingWorkflow(holder)),
        )
        runner = OneShotRunner(["vnetmap"], {"cluster_ip": "192.168.2.2"})
        # No cluster paths resolved → set_output_dir must NOT be called.
        runner._run_operations()
        assert "dir" not in holder


# ---------------------------------------------------------------------------
# One-shot early identity resolution
# ---------------------------------------------------------------------------
class _FakeInfo:
    name = "lax01"
    psnt = "P1"
    guid = "0xabc"
    version = "5.3"


class _FakeApi:
    def authenticate(self):
        return True

    def get_cluster_info(self):
        return _FakeInfo()

    def close(self):
        pass


class TestOneShotEarlyIdentity:
    def _runner(self, ops, ip):
        from oneshot_runner import OneShotRunner

        return OneShotRunner(ops, {"cluster_ip": ip})

    def test_resolves_key_and_writes_marker(self, tmp_path, monkeypatch):
        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        import api_handler

        monkeypatch.setattr(api_handler, "create_vast_api_handler", lambda **kw: _FakeApi())
        runner = self._runner([], "192.168.2.2")
        monkeypatch.setattr(runner, "_load_config", lambda: {"output": {"segment_by_cluster": True}})

        runner._resolve_cluster_identity_early()

        assert runner._cluster_key == "lax01__P1"
        root = cp.cluster_paths(tmp_path, "lax01__P1").root
        assert (root / "cluster.json").exists()
        marker = cp.read_cluster_marker(root)
        assert marker["psnt"] == "P1"
        assert marker["cluster_ip"] == "192.168.2.2"

    def test_segmentation_off_creates_no_clusters_dir(self, tmp_path, monkeypatch):
        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        runner = self._runner(["vnetmap"], "192.168.2.2")
        monkeypatch.setattr(runner, "_load_config", lambda: {"output": {"segment_by_cluster": False}})

        runner._resolve_cluster_identity_early()

        assert runner._cluster_paths is None
        assert not (tmp_path / "clusters").exists()

    def test_fetch_failure_falls_back_to_ip_key(self, tmp_path, monkeypatch):
        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        import api_handler

        def _boom(**kw):
            raise RuntimeError("no network")

        monkeypatch.setattr(api_handler, "create_vast_api_handler", _boom)
        runner = self._runner([], "10.0.0.9")
        monkeypatch.setattr(runner, "_load_config", lambda: {"output": {"segment_by_cluster": True}})

        runner._resolve_cluster_identity_early()

        assert runner._cluster_key == "10.0.0.9"
        assert runner._cluster_paths is not None


# ---------------------------------------------------------------------------
# Real workflows truly redirect output via set_output_dir
# ---------------------------------------------------------------------------
class TestWorkflowOutputRedirect:
    def test_switch_config_save_lands_in_cluster_dir(self, tmp_path):
        from workflows.switch_config_workflow import SwitchConfigWorkflow

        scripts = cp.cluster_paths(tmp_path, "c1").scripts
        wf = SwitchConfigWorkflow()
        wf.set_output_dir(scripts)
        wf.set_credentials({"cluster_ip": "192.168.2.2"})
        wf._step_data["configs"] = {
            "10.0.0.1": {"type": "cumulus_linux", "hostname": "leaf1", "commands": {"show": "out"}}
        }
        result = wf.run_step(3)
        assert result["success"]
        saved = list((scripts / "switch_configs").glob("switch_leaf1_*.txt"))
        assert saved, "switch config file should land under the cluster scripts dir"

    def test_vnetmap_save_lands_in_cluster_dir(self, tmp_path):
        from workflows.vnetmap_workflow import VnetmapWorkflow

        scripts = cp.cluster_paths(tmp_path, "c1").scripts
        wf = VnetmapWorkflow()
        wf.set_output_dir(scripts)
        # No cluster_ip/password → _fetch_fabric_report short-circuits (no SSH).
        wf.set_credentials({})
        wf._step_data["vnetmap_output"] = "Passed: 4 Failed: 0"
        result = wf.run_step(6)
        assert result["success"]
        saved = list(scripts.glob("vnetmap_output_*.txt"))
        assert saved, "vnetmap output file should land under the cluster scripts dir"


# ---------------------------------------------------------------------------
# vnetmap finder cross-cluster isolation (tech-port shared IP)
# ---------------------------------------------------------------------------
class TestVnetmapCrossClusterIsolation:
    def test_finder_returns_only_keyed_cluster_file(self, tmp_path, monkeypatch):
        import app

        monkeypatch.setattr(utils, "get_data_dir", lambda: tmp_path)
        ip = "192.168.2.2"
        # Two tech-port clusters share the management IP; each segmented.
        _make_vnetmap(cp.cluster_paths(tmp_path, "other__P9").scripts, ip, "20260101_020202")
        mine = _make_vnetmap(cp.cluster_paths(tmp_path, "mine__P1").scripts, ip, "20260101_010101")

        # Even though other__P9's file is newer, the key scopes the search.
        assert app._find_latest_vnetmap_output(ip, cluster_key="mine__P1") == mine


# ---------------------------------------------------------------------------
# Standalone health key shares the report folder (includes PSNT)
# ---------------------------------------------------------------------------
class TestHealthKeyMatchesReport:
    def test_health_identity_shares_report_folder(self, tmp_path):
        config = {"output": {"segment_by_cluster": True}}
        report_data = {
            "cluster_summary": {"name": "lax01", "psnt": "P1", "guid": "0xabc"},
            "cluster_ip": "192.168.2.2",
        }
        health_identity = {
            "cluster_summary": {"name": "lax01", "psnt": "P1", "guid": "0xabc"},
            "cluster_ip": "192.168.2.2",
        }
        report_cp = co.cluster_paths_if_enabled(config, report_data, data_dir=tmp_path)
        health_cp = co.cluster_paths_if_enabled(config, health_identity, data_dir=tmp_path)
        assert report_cp is not None and health_cp is not None
        assert report_cp.root == health_cp.root

    def test_name_only_health_identity_would_split(self, tmp_path):
        config = {"output": {"segment_by_cluster": True}}
        report_data = {
            "cluster_summary": {"name": "lax01", "psnt": "P1"},
            "cluster_ip": "192.168.2.2",
        }
        old_health = {"name": "lax01", "cluster_ip": "192.168.2.2"}
        report_cp = co.cluster_paths_if_enabled(config, report_data, data_dir=tmp_path)
        old_cp = co.cluster_paths_if_enabled(config, old_health, data_dir=tmp_path)
        assert report_cp.root != old_cp.root


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
