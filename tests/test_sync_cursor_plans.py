"""Tests for scripts/sync-cursor-plans.py redaction and manifest handling."""

import importlib.util
import os
import time
from datetime import date
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "sync-cursor-plans.py"


@pytest.fixture(scope="module")
def sync():
    spec = importlib.util.spec_from_file_location("sync_cursor_plans", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestRedact:
    def test_private_ip_redacted(self, sync):
        text, hits = sync.redact("VMS at 10.143.11.202 and 172.16.3.4/16.")
        assert text == "VMS at <ip> and <ip>/16."
        assert hits == 2

    def test_allowed_addresses_kept(self, sync):
        text, hits = sync.redact("bind 127.0.0.1, listen 0.0.0.0, tech port 192.168.2.2")
        assert text == "bind 127.0.0.1, listen 0.0.0.0, tech port 192.168.2.2"
        assert hits == 0

    def test_network_ranges_kept(self, sync):
        text, hits = sync.redact("RFC1918 10.0.0.0/8, 172.16.0.0/12; CGNAT 100.64.0.0/10")
        assert text == "RFC1918 10.0.0.0/8, 172.16.0.0/12; CGNAT 100.64.0.0/10"
        assert hits == 0

    def test_version_strings_not_treated_as_ip(self, sync):
        text, hits = sync.redact("ship v1.6.1 then 1.7.0; build 1.2.3.4.5")
        assert text == "ship v1.6.1 then 1.7.0; build 1.2.3.4.5"
        assert hits == 0

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("password: hunter2", "password: <redacted>"),
            ("api_key=abc123", "api_key=<redacted>"),
            ("TOKEN = 'xyz'", "TOKEN = '<redacted>'"),
            ("secret=`s3cr3t`", "secret=`<redacted>`"),
            ("node_password: 'hunter2'", "node_password: '<redacted>'"),
        ],
    )
    def test_credential_values_redacted(self, sync, raw, expected):
        text, hits = sync.redact(raw)
        assert text == expected
        assert hits == 1

    def test_credential_words_without_values_kept(self, sync):
        raw = "Never log the password or token; prompt with getpass."
        text, hits = sync.redact(raw)
        assert text == raw
        assert hits == 0

    @pytest.mark.parametrize(
        "raw",
        ["password: str", "token=None", "password=password", "token=self._credentials.get(", "password = ssh_password"],
    )
    def test_code_expressions_kept(self, sync, raw):
        text, hits = sync.redact(raw)
        assert text == raw
        assert hits == 0

    def test_email_and_lab_names_redacted(self, sync):
        text, _ = sync.redact("ping someone@example.com about selab-var-202")
        assert text == "ping <email> about <lab-cluster>"

    def test_customer_cluster_names_redacted(self, sync):
        text, _ = sync.redact("replay vast_data_LAMBDA-VAST-LAX-01_20260609_162644.json; mammoth fixtures")
        assert text == "replay vast_data_<cluster>_20260609_162644.json; <customer-cluster> fixtures"
        text, _ = sync.redact("see RCA_LAMBDA-VAST-SLC-02_DBox.md")
        assert text == "see RCA_<customer-cluster>_DBox.md"

    def test_python_lambda_keyword_kept(self, sync):
        text, _ = sync.redact("key=lambda d: d.name")
        assert text == "key=lambda d: d.name"

    def test_idempotent(self, sync):
        once, _ = sync.redact("10.0.0.5 password: x user@example.com selab-var-203")
        twice, hits = sync.redact(once)
        assert twice == once
        assert hits == 0


class TestManifest:
    def test_reads_entries_and_last_triaged(self, sync, tmp_path):
        manifest = tmp_path / "MANIFEST.txt"
        manifest.write_text("# header\n# last-triaged: 2026-09-25\n\na.plan.md\n# note\nb.plan.md\n")
        entries, last = sync.read_manifest(manifest)
        assert entries == ["a.plan.md", "b.plan.md"]
        assert last == date(2026, 9, 25)

    def test_untriaged_only_newer_unlisted_plans(self, sync, tmp_path):
        old = time.mktime((2026, 9, 1, 12, 0, 0, 0, 0, -1))
        new = time.mktime((2026, 9, 30, 12, 0, 0, 0, 0, -1))
        for name, mtime in [("listed.plan.md", new), ("old.plan.md", old), ("new.plan.md", new)]:
            path = tmp_path / name
            path.write_text("x")
            os.utime(path, (mtime, mtime))
        found = sync.untriaged_plans(tmp_path, ["listed.plan.md"], date(2026, 9, 25))
        assert found == ["new.plan.md"]
