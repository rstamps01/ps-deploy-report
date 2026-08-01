"""Escalation notifier for the agentic CI/CD pipeline (pipeline §16).

When the bounded ``remediate-failure`` loop exhausts its 3 attempts on a single
issue, the pipeline escalates to a human with a structured report:

    1. failure description (what / where / which gate)
    2. assessment / root-cause hypothesis
    3. actions taken across the attempts
    4. up to 4 ranked next-step options with pros/cons

This module builds that report and delivers it by **SMTP email** (the formal
record). The **Slack** side of the escalation is posted by the agent through the
Slack MCP (an agent can read the threaded reply to drive a 2nd remediation
loop, which an inbound mailbox cannot); this module only renders the Slack
payload text — it never calls Slack or holds a Slack token.

Security (``config-security-11``):
    * SMTP username/password are read from environment variables
      (``SMTP_USERNAME`` / ``SMTP_PASSWORD``) — never from the config file.
    * All free-text fields are redacted through the same
      :class:`~utils.logger.SensitiveDataFilter` contract used for logs, so no
      token/password/secret shaped ``key: value`` leaks into an email or Slack
      message.
    * Delivery failures are returned as a result, never raised into the
      pipeline — an escalation channel outage must not mask the original
      failure.
"""

from __future__ import annotations

import logging
import os
import smtplib
from dataclasses import dataclass, field
from datetime import datetime
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

try:  # Reuse the exact log-redaction contract if available.
    from utils.logger import SensitiveDataFilter

    _CREDENTIAL_RE = SensitiveDataFilter._CREDENTIAL_RE
    _redact_match = SensitiveDataFilter._redact_match
except Exception:  # pragma: no cover - fallback keeps the notifier importable standalone
    import re

    _CREDENTIAL_RE = re.compile(
        r"""(?P<lq>['"]?)\b(?P<key>password|passwd|pwd|token|key|secret|"""
        r"""authori[sz]ation|auth|credential|session|cookie)\b(?P=lq)"""
        r"""\s*[:=]\s*(?:\w+\s+)?['"]?[^\s'",;]+['"]?""",
        re.IGNORECASE | re.VERBOSE,
    )

    def _redact_match(match: "re.Match[str]") -> str:  # type: ignore[no-redef]
        return f"{match.group('key').upper()}_[REDACTED]"


logger = logging.getLogger(__name__)

MAX_OPTIONS = 4


def redact(text: str) -> str:
    """Redact credential-shaped ``key: value`` spans from free text."""
    if not text:
        return text
    return str(_CREDENTIAL_RE.sub(_redact_match, text))


@dataclass
class EscalationOption:
    """One ranked next-step recommendation presented to the human."""

    label: str
    rationale: str = ""

    def render(self, rank: int) -> str:
        line = f"{rank}. {redact(self.label)}"
        if self.rationale:
            line += f"\n   - {redact(self.rationale)}"
        return line


@dataclass
class EscalationReport:
    """Structured escalation payload built after the bounded loop is exhausted."""

    gate: str
    summary: str
    root_cause: str = ""
    actions_taken: List[str] = field(default_factory=list)
    options: List[EscalationOption] = field(default_factory=list)
    item_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        # Cap options at 4 (pipeline contract) keeping the highest-ranked.
        if len(self.options) > MAX_OPTIONS:
            self.options = self.options[:MAX_OPTIONS]

    def subject(self) -> str:
        item = f" [{self.item_id}]" if self.item_id else ""
        line = redact(f"[Pipeline escalation]{item} {self.gate} failed after 3 attempts")
        # Collapse CR/LF so a newline in gate/item_id can never inject an email header.
        return " ".join(line.split())

    def as_text(self) -> str:
        """Render the redacted email/record body."""
        lines = [
            self.subject(),
            "",
            f"When:  {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Gate:  {redact(self.gate)}",
        ]
        if self.item_id:
            lines.append(f"Item:  {self.item_id}")
        lines += ["", "1) Failure description", f"   {redact(self.summary)}"]
        if self.root_cause:
            lines += ["", "2) Assessment / root-cause hypothesis", f"   {redact(self.root_cause)}"]
        if self.actions_taken:
            lines += ["", "3) Actions taken (bounded loop, max 3 attempts)"]
            for i, action in enumerate(self.actions_taken, 1):
                lines.append(f"   {i}. {redact(action)}")
        if self.options:
            lines += ["", "4) Recommended next steps (reply in Slack to choose)"]
            for rank, option in enumerate(self.options, 1):
                lines.append("   " + option.render(rank).replace("\n", "\n   "))
        return "\n".join(lines)

    def as_slack(self) -> str:
        """Render the redacted Slack message (posted by the agent via the MCP)."""
        return self.as_text()


@dataclass
class EmailConfig:
    """SMTP delivery settings; credentials come from the environment."""

    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    use_tls: bool = True
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)
    username: Optional[str] = None
    password: Optional[str] = None

    def is_deliverable(self) -> bool:
        return bool(self.enabled and self.smtp_host and self.from_addr and self.to_addrs)


@dataclass
class NotificationConfig:
    """Top-level ``notifications:`` config block."""

    enabled: bool = False
    email: EmailConfig = field(default_factory=EmailConfig)
    slack_enabled: bool = False
    slack_channel: str = ""

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> "NotificationConfig":
        """Build from a parsed ``config.yaml`` dict; secrets from env vars."""
        block = (config or {}).get("notifications", {}) or {}
        email_block = block.get("email", {}) or {}
        slack_block = block.get("slack", {}) or {}
        email = EmailConfig(
            enabled=bool(email_block.get("enabled", False)),
            smtp_host=str(email_block.get("smtp_host", "") or ""),
            smtp_port=int(email_block.get("smtp_port", 587) or 587),
            use_tls=bool(email_block.get("use_tls", True)),
            from_addr=str(email_block.get("from_addr", "") or ""),
            to_addrs=list(email_block.get("to_addrs", []) or []),
            username=os.environ.get("SMTP_USERNAME"),
            password=os.environ.get("SMTP_PASSWORD"),
        )
        return cls(
            enabled=bool(block.get("enabled", False)),
            email=email,
            slack_enabled=bool(slack_block.get("enabled", False)),
            slack_channel=str(slack_block.get("channel", "") or ""),
        )


@dataclass
class NotificationResult:
    """Outcome of a delivery attempt (never raised)."""

    ok: bool
    channel: str
    detail: str = ""


class Notifier:
    """Delivers an :class:`EscalationReport`. SMTP only; Slack is agent-driven."""

    def __init__(self, config: NotificationConfig) -> None:
        self.config = config

    def send_email(self, report: EscalationReport) -> NotificationResult:
        """Send the escalation via SMTP. Returns a result; never raises."""
        if not self.config.enabled or not self.config.email.enabled:
            return NotificationResult(ok=False, channel="email", detail="notifications disabled")
        email = self.config.email
        if not email.is_deliverable():
            return NotificationResult(ok=False, channel="email", detail="email misconfigured (host/from/to)")

        message = EmailMessage()
        message["Subject"] = report.subject()
        message["From"] = email.from_addr
        message["To"] = ", ".join(email.to_addrs)
        message.set_content(report.as_text())

        try:
            if email.smtp_port == 465 and not email.use_tls:
                server: smtplib.SMTP = smtplib.SMTP_SSL(email.smtp_host, email.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(email.smtp_host, email.smtp_port, timeout=30)
            try:
                server.ehlo()
                if email.use_tls:
                    server.starttls()
                    server.ehlo()
                if email.username and email.password:
                    server.login(email.username, email.password)
                server.send_message(message)
            finally:
                server.quit()
        except Exception as exc:  # Delivery failure must not mask the original gate failure.
            logger.warning("Escalation email delivery failed: %s", exc)
            return NotificationResult(ok=False, channel="email", detail=f"send failed: {exc}")
        return NotificationResult(ok=True, channel="email", detail=f"sent to {len(email.to_addrs)} recipient(s)")

    def slack_payload(self, report: EscalationReport) -> Optional[Dict[str, str]]:
        """Return ``{channel, text}`` for the agent to post via the Slack MCP.

        Returns ``None`` when Slack escalation is disabled. This module never
        calls Slack itself — the agent owns the MCP call and reads the reply.
        """
        if not self.config.enabled or not self.config.slack_enabled or not self.config.slack_channel:
            return None
        return {"channel": self.config.slack_channel, "text": report.as_slack()}
