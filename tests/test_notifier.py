"""Tests for the escalation notifier (src/utils/notifier.py).

SMTP is fully mocked — no real mail is sent. Covers report rendering, secret
redaction, the 4-option cap, config parsing (incl. env-var credentials), the
Slack payload, and SMTP send success/failure/disabled paths.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.notifier import (
    EmailConfig,
    EscalationOption,
    EscalationReport,
    NotificationConfig,
    Notifier,
    redact,
)


def _report(**kw):
    defaults = dict(
        gate="quality-gate",
        summary="pytest failed in tests/test_widget.py::test_ratio",
        root_cause="off-by-one in the ratio calculation",
        actions_taken=["reverted the guard", "added a boundary test", "rechecked types"],
        options=[EscalationOption("Roll back", "safest"), EscalationOption("Patch forward", "faster")],
        item_id="BUG-042",
    )
    defaults.update(kw)
    return EscalationReport(**defaults)


class TestRedaction(unittest.TestCase):
    def test_redacts_credential_shaped_values(self):
        self.assertIn("PASSWORD_[REDACTED]", redact("switch password: admin123"))
        self.assertIn("TOKEN_[REDACTED]", redact("api token=abc.def.ghi"))

    def test_passes_prose_through(self):
        text = "the primary password failed authentication and we retried"
        self.assertEqual(redact(text), text)

    def test_empty_is_safe(self):
        self.assertEqual(redact(""), "")

    def test_report_body_is_redacted(self):
        report = _report(root_cause="db password: hunter2 was wrong")
        self.assertNotIn("hunter2", report.as_text())
        self.assertIn("PASSWORD_[REDACTED]", report.as_text())


class TestEscalationReport(unittest.TestCase):
    def test_subject_mentions_gate_and_item(self):
        subject = _report().subject()
        self.assertIn("quality-gate", subject)
        self.assertIn("BUG-042", subject)

    def test_subject_strips_newlines_no_header_injection(self):
        # A newline in gate/item_id must never survive into the email Subject
        # header (defense-in-depth against header injection): it is collapsed to
        # a single line, so the "Bcc:" text stays inert body-of-subject, not a header.
        report = _report(gate="ci\r\nBcc: attacker@evil.test", item_id="X\n1")
        subject = report.subject()
        self.assertNotIn("\n", subject)
        self.assertNotIn("\r", subject)
        self.assertEqual(subject, " ".join(subject.split()))

    def test_body_has_four_numbered_sections(self):
        body = _report().as_text()
        for marker in ("1) Failure description", "2) Assessment", "3) Actions taken", "4) Recommended next steps"):
            self.assertIn(marker, body)

    def test_options_capped_at_four(self):
        opts = [EscalationOption(f"opt{i}") for i in range(6)]
        report = _report(options=opts)
        self.assertEqual(len(report.options), 4)
        self.assertNotIn("opt4", report.as_text())

    def test_slack_matches_text(self):
        report = _report()
        self.assertEqual(report.as_slack(), report.as_text())

    def test_minimal_report_renders(self):
        report = EscalationReport(gate="ci", summary="build broke")
        body = report.as_text()
        self.assertIn("build broke", body)
        self.assertIn("1) Failure description", body)


class TestNotificationConfig(unittest.TestCase):
    def test_defaults_when_absent(self):
        cfg = NotificationConfig.from_config({})
        self.assertFalse(cfg.enabled)
        self.assertFalse(cfg.email.enabled)
        self.assertFalse(cfg.email.is_deliverable())

    def test_parses_email_block(self):
        raw = {
            "notifications": {
                "enabled": True,
                "email": {
                    "enabled": True,
                    "smtp_host": "smtp.example.com",
                    "smtp_port": 587,
                    "from_addr": "bot@example.com",
                    "to_addrs": ["eng@example.com"],
                },
                "slack": {"enabled": True, "channel": "#pipeline"},
            }
        }
        cfg = NotificationConfig.from_config(raw)
        self.assertTrue(cfg.enabled)
        self.assertTrue(cfg.email.is_deliverable())
        self.assertTrue(cfg.slack_enabled)
        self.assertEqual(cfg.slack_channel, "#pipeline")

    @patch.dict("os.environ", {"SMTP_USERNAME": "bot", "SMTP_PASSWORD": "s3cr3t"}, clear=False)
    def test_credentials_from_env(self):
        cfg = NotificationConfig.from_config({"notifications": {"email": {"enabled": True}}})
        self.assertEqual(cfg.email.username, "bot")
        self.assertEqual(cfg.email.password, "s3cr3t")

    def test_none_config_is_safe(self):
        cfg = NotificationConfig.from_config(None)
        self.assertFalse(cfg.enabled)


class TestNotifierSend(unittest.TestCase):
    def _deliverable(self):
        return NotificationConfig(
            enabled=True,
            email=EmailConfig(
                enabled=True,
                smtp_host="smtp.example.com",
                smtp_port=587,
                use_tls=True,
                from_addr="bot@example.com",
                to_addrs=["eng@example.com"],
                username="bot",
                password="pw",
            ),
        )

    def test_disabled_returns_not_ok(self):
        result = Notifier(NotificationConfig()).send_email(_report())
        self.assertFalse(result.ok)
        self.assertIn("disabled", result.detail)

    def test_misconfigured_returns_not_ok(self):
        cfg = NotificationConfig(enabled=True, email=EmailConfig(enabled=True))
        result = Notifier(cfg).send_email(_report())
        self.assertFalse(result.ok)
        self.assertIn("misconfigured", result.detail)

    @patch("utils.notifier.smtplib.SMTP")
    def test_send_success_with_starttls(self, mock_smtp):
        server = MagicMock()
        mock_smtp.return_value = server
        result = Notifier(self._deliverable()).send_email(_report())
        self.assertTrue(result.ok)
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("bot", "pw")
        server.send_message.assert_called_once()
        server.quit.assert_called_once()

    @patch("utils.notifier.smtplib.SMTP")
    def test_send_failure_is_swallowed(self, mock_smtp):
        server = MagicMock()
        server.send_message.side_effect = OSError("connection reset")
        mock_smtp.return_value = server
        result = Notifier(self._deliverable()).send_email(_report())
        self.assertFalse(result.ok)
        self.assertIn("send failed", result.detail)
        server.quit.assert_called_once()

    @patch("utils.notifier.smtplib.SMTP_SSL")
    def test_port_465_uses_ssl(self, mock_ssl):
        server = MagicMock()
        mock_ssl.return_value = server
        cfg = self._deliverable()
        cfg.email.smtp_port = 465
        cfg.email.use_tls = False
        result = Notifier(cfg).send_email(_report())
        self.assertTrue(result.ok)
        mock_ssl.assert_called_once()
        server.starttls.assert_not_called()


class TestSlackPayload(unittest.TestCase):
    def test_none_when_disabled(self):
        self.assertIsNone(Notifier(NotificationConfig()).slack_payload(_report()))

    def test_payload_when_enabled(self):
        cfg = NotificationConfig(enabled=True, slack_enabled=True, slack_channel="#pipeline")
        payload = Notifier(cfg).slack_payload(_report())
        self.assertIsNotNone(payload)
        self.assertEqual(payload["channel"], "#pipeline")
        self.assertIn("quality-gate", payload["text"])


if __name__ == "__main__":
    unittest.main()
