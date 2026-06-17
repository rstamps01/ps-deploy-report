"""Unit tests for QP-3 (4): opt-in, anonymous local usage metrics + ROI.

Telemetry is local-only in this release: events are recorded to a JSONL file
under the data directory and surfaced as a local "ROI" summary.  Nothing is
transmitted anywhere.  Recording is gated on explicit opt-in consent.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from usage_metrics import UsageMetrics, TIME_SAVED_MINUTES  # noqa: E402


@pytest.fixture
def metrics(tmp_path):
    return UsageMetrics(base_dir=tmp_path / "telemetry", app_version="9.9.9")


class TestConsentDefaults:
    def test_disabled_by_default_opt_in(self, metrics):
        assert metrics.enabled is False

    def test_install_id_generated_and_stable(self, metrics, tmp_path):
        first = metrics.install_id
        assert first and len(first) >= 8
        # Re-open against the same dir: id must persist (anonymous, stable).
        again = UsageMetrics(base_dir=tmp_path / "telemetry", app_version="9.9.9")
        assert again.install_id == first

    def test_state_file_written_on_init(self, metrics, tmp_path):
        assert (tmp_path / "telemetry" / "telemetry.json").exists()


class TestConsentToggle:
    def test_set_consent_enables_recording(self, metrics):
        metrics.set_consent(True)
        assert metrics.enabled is True

    def test_consent_persists_across_instances(self, metrics, tmp_path):
        metrics.set_consent(True)
        reopened = UsageMetrics(base_dir=tmp_path / "telemetry", app_version="9.9.9")
        assert reopened.enabled is True


class TestRecording:
    def test_no_record_when_disabled(self, metrics, tmp_path):
        assert metrics.record_event("report_generated") is False
        assert not (tmp_path / "telemetry" / "usage.jsonl").exists()

    def test_records_when_enabled(self, metrics, tmp_path):
        metrics.set_consent(True)
        assert metrics.record_event("report_generated", {"operation": "report"}) is True
        events_path = tmp_path / "telemetry" / "usage.jsonl"
        assert events_path.exists()
        rec = json.loads(events_path.read_text().splitlines()[0])
        assert rec["event"] == "report_generated"
        assert rec["app_version"] == "9.9.9"
        assert rec["install_id"] == metrics.install_id
        assert "ts" in rec

    def test_sanitizes_disallowed_properties(self, metrics, tmp_path):
        metrics.set_consent(True)
        metrics.record_event(
            "report_generated",
            {
                "operation": "report",
                "cluster_ip": "192.168.2.2",  # must be dropped
                "cluster_name": "secret-cluster",  # must be dropped
                "password": "hunter2",  # must be dropped
            },
        )
        rec = json.loads((tmp_path / "telemetry" / "usage.jsonl").read_text().splitlines()[0])
        assert rec["properties"] == {"operation": "report"}
        assert "cluster_ip" not in rec["properties"]
        assert "cluster_name" not in rec["properties"]
        assert "password" not in rec["properties"]


class TestRoiSummary:
    def test_empty_summary(self, metrics):
        roi = metrics.roi_summary()
        assert roi["total_events"] == 0
        assert roi["estimated_minutes_saved"] == 0
        assert roi["transmitted"] is False
        assert roi["enabled"] is False

    def test_summary_counts_and_time_saved(self, metrics):
        metrics.set_consent(True)
        metrics.record_event("report_generated")
        metrics.record_event("report_generated")
        metrics.record_event("health_check")
        roi = metrics.roi_summary()
        assert roi["total_events"] == 3
        assert roi["counts"]["report_generated"] == 2
        assert roi["counts"]["health_check"] == 1
        expected = 2 * TIME_SAVED_MINUTES["report_generated"] + TIME_SAVED_MINUTES["health_check"]
        assert roi["estimated_minutes_saved"] == expected
        assert roi["enabled"] is True

    def test_record_never_raises_on_bad_dir(self, tmp_path):
        # A read-only / bogus directory must not crash callers in job paths.
        m = UsageMetrics(base_dir=tmp_path / "telemetry", app_version="1.0")
        m.set_consent(True)
        # Corrupt the events file with junk; summary must still degrade safely.
        (tmp_path / "telemetry" / "usage.jsonl").write_text("not json\n{}\n")
        roi = m.roi_summary()
        assert isinstance(roi["total_events"], int)
