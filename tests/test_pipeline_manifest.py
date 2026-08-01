"""Tests for the project-manifest adapter (scripts/pipeline_manifest.py, pipeline §30).

Covers command/gate resolution, coverage-floor parsing, structural validation
(positive on the real manifest + negative on crafted dicts), and the CLI.
"""

import sys
import unittest
from pathlib import Path

_SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

from pipeline_manifest import (  # noqa: E402
    DEFAULT_MANIFEST,
    ManifestError,
    PipelineManifest,
    main,
)


def _manifest(data) -> PipelineManifest:
    return PipelineManifest(data, Path("/tmp/pipeline.yml"))


_VALID = {
    "schema_version": 1,
    "project": {"name": "demo", "language": "python"},
    "commands": {
        "install": "pip install -r requirements-dev.txt",
        "lint": "flake8 src/",
        "format_check": "black --check src/",
        "typecheck": "mypy src/",
        "test": "pytest",
        "test_cov": "pytest --cov=src --cov-fail-under=60",
    },
    "quality": {"coverage_floor": 60, "blocking_gate": ["version_sync", "lint", "test_cov"]},
    "version": {"source_file": "src/app.py", "sync_check": "bash scripts/check-version-sync.sh"},
}


class TestRealManifestLoads(unittest.TestCase):
    def test_real_manifest_is_valid(self):
        m = PipelineManifest.load(DEFAULT_MANIFEST)
        self.assertEqual(m.validate(), [])

    def test_real_manifest_strict_paths_exist(self):
        m = PipelineManifest.load(DEFAULT_MANIFEST)
        # source_file / release_notes_dir / register all exist in this repo.
        self.assertEqual(m.validate(strict=True), [])

    def test_missing_file_raises(self):
        with self.assertRaises(ManifestError):
            PipelineManifest.load(Path("/tmp/does-not-exist-pipeline.yml"))


class TestCommandResolution(unittest.TestCase):
    def test_command_lookup(self):
        self.assertEqual(_manifest(_VALID).command("lint"), "flake8 src/")

    def test_unknown_command_raises(self):
        with self.assertRaises(ManifestError):
            _manifest(_VALID).command("nope")

    def test_coverage_floor_is_int(self):
        self.assertEqual(_manifest(_VALID).coverage_floor, 60)

    def test_gate_resolves_version_sync_specially(self):
        gate = _manifest(_VALID).gate_commands()
        self.assertEqual(gate[0], "bash scripts/check-version-sync.sh")  # version_sync -> sync_check
        self.assertEqual(gate[1], "flake8 src/")
        self.assertEqual(gate[2], "pytest --cov=src --cov-fail-under=60")

    def test_gate_version_sync_without_sync_check_raises(self):
        data = {**_VALID, "version": {"source_file": "src/app.py"}}  # no sync_check
        with self.assertRaises(ManifestError):
            _manifest(data).gate_commands()


class TestValidation(unittest.TestCase):
    def test_valid_dict_has_no_errors(self):
        self.assertEqual(_manifest(_VALID).validate(), [])

    def test_missing_schema_version(self):
        data = {k: v for k, v in _VALID.items() if k != "schema_version"}
        self.assertTrue(any("schema_version" in e for e in _manifest(data).validate()))

    def test_missing_required_command(self):
        data = {**_VALID, "commands": {k: v for k, v in _VALID["commands"].items() if k != "test_cov"}}
        self.assertTrue(any("test_cov" in e for e in _manifest(data).validate()))

    def test_blocking_gate_unresolvable_step(self):
        data = {**_VALID, "quality": {"coverage_floor": 60, "blocking_gate": ["ghost_step"]}}
        self.assertTrue(any("ghost_step" in e for e in _manifest(data).validate()))

    def test_missing_project_language(self):
        data = {**_VALID, "project": {"name": "demo"}}
        self.assertTrue(any("project.language" in e for e in _manifest(data).validate()))


class TestCli(unittest.TestCase):
    def test_validate_exit_zero_on_real_manifest(self):
        self.assertEqual(main(["validate"]), 0)

    def test_get_exit_zero(self):
        self.assertEqual(main(["get", "lint"]), 0)

    def test_get_unknown_exit_one(self):
        self.assertEqual(main(["get", "nope"]), 1)

    def test_gate_exit_zero(self):
        self.assertEqual(main(["gate"]), 0)

    def test_show_exit_zero(self):
        self.assertEqual(main(["show"]), 0)


if __name__ == "__main__":
    unittest.main()
