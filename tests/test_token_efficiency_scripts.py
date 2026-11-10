"""Tests for the token-efficiency helper scripts (junit_summary, context-pack)."""

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def junit():
    return _load("junit_summary", "junit_summary.py")


@pytest.fixture(scope="module")
def pack():
    return _load("context_pack", "context-pack.py")


JUNIT_XML = """<?xml version="1.0" encoding="utf-8"?>
<testsuites><testsuite name="pytest" tests="4" failures="1" errors="1" skipped="1">
  <testcase classname="tests.test_a" name="test_ok"/>
  <testcase classname="tests.test_a" name="test_bad"><failure message="assert 1 == 2">line1
line2
E   assert 1 == 2</failure></testcase>
  <testcase classname="tests.test_b" name="test_err"><error message="boom">Traceback
RuntimeError: boom</error></testcase>
  <testcase classname="tests.test_b" name="test_skip"><skipped message="n/a"/></testcase>
</testsuite></testsuites>
"""


class TestJunitSummary:
    def test_counts_and_failures(self, junit, tmp_path):
        xml = tmp_path / "junit.xml"
        xml.write_text(JUNIT_XML)
        text = junit.summarize(xml)
        assert "1 passed, 1 failed, 1 errors, 1 skipped" in text
        assert "FAILURE tests.test_a::test_bad" in text
        assert "ERROR tests.test_b::test_err" in text
        assert "E   assert 1 == 2" in text
        assert "test_ok" not in text

    def test_line_and_failure_caps(self, junit, tmp_path):
        xml = tmp_path / "junit.xml"
        xml.write_text(JUNIT_XML)
        text = junit.summarize(xml, max_failures=1, max_lines=1)
        assert "and 1 more failures" in text
        assert "line1" not in text

    def test_all_green_is_one_line(self, junit, tmp_path):
        xml = tmp_path / "junit.xml"
        xml.write_text('<testsuite tests="2" failures="0" errors="0" skipped="0"><testcase name="a"/></testsuite>')
        assert junit.summarize(xml).strip() == "### Tests: 2 passed, 0 failed, 0 errors, 0 skipped"

    def test_missing_and_invalid_files(self, junit, tmp_path):
        assert "No JUnit report" in junit.summarize(tmp_path / "absent.xml")
        bad = tmp_path / "bad.xml"
        bad.write_text("<not-closed")
        assert "Could not parse" in junit.summarize(bad)


class TestContextPack:
    def test_terms_from_spec_ranked_and_filtered(self, pack, tmp_path):
        spec = tmp_path / "spec.md"
        spec.write_text("Use `run_ssh_command` and `run_ssh_command` in `src/x.py`; flag `True` and `42`.")
        terms = pack.terms_from_spec(spec)
        assert terms[0] == "run_ssh_command"
        assert "src/x.py" in terms
        assert "True" not in terms and "42" not in terms
        assert pack.terms_from_spec(tmp_path / "missing.md") == []

    def test_python_spans_and_enclosing(self, pack, tmp_path):
        src = tmp_path / "m.py"
        src.write_text("class A:\n    def f(self):\n        x = 1\n        return x\n\n\ndef g():\n    return 2\n")
        spans = pack.python_spans(src)
        assert (1, 4, "A") in spans and (2, 4, "A.f") in spans
        assert pack.enclosing(spans, 3)[2] == "A.f"
        assert pack.enclosing(spans, 8)[2] == "g"
        assert pack.enclosing(spans, 5) is None

    def test_build_pack_on_repo_is_capped(self, pack):
        root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip())
        text = pack.build_pack(root, "TEST", ["_emit_run_output", "VperfsanityWorkflow"])
        assert text.startswith("# Context pack: TEST")
        assert "src/workflows/vperfsanity_workflow.py" in text
        assert "L" in text
        assert len(text.encode()) <= pack.MAX_BYTES
