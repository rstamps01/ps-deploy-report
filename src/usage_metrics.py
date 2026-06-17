"""QP-3 (4): opt-in, anonymous, local usage metrics with an ROI surface.

This module records coarse, anonymous usage events to a local JSONL file and
derives a local "return on investment" (ROI) summary from them.  It is
**local-only** in this release: nothing is transmitted anywhere.  A central
receiver may be added later — see ``docs/development/TELEMETRY.md`` for the
wire format/spec — at which point the recorded events become the payload.

Privacy guarantees:
    * Recording is OFF by default and only happens after explicit opt-in
      consent (:meth:`UsageMetrics.set_consent`).
    * Only an anonymous, randomly generated install id is stored — never a
      hostname, username, cluster IP/name/PSNT, or any credential.
    * Event properties are filtered through a strict allowlist
      (:data:`_ALLOWED_PROPS`) so identifying fields can never leak into the
      usage log, even if a caller passes them by mistake.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.logger import get_logger

logger = get_logger(__name__)

# Coarse, deliberately conservative "minutes saved vs. doing this by hand"
# estimates used only for the LOCAL ROI surface.  Not transmitted.
TIME_SAVED_MINUTES: Dict[str, int] = {
    "report_generated": 45,
    "health_check": 20,
    "oneshot_run": 30,
    "vnetmap_run": 15,
    "switch_config": 15,
    "support_bundle": 20,
}

# Strict allowlist of event property keys that may be persisted.  Anything
# else is dropped before writing so cluster identity / credentials can never
# end up in the usage log.
_ALLOWED_PROPS = frozenset(
    {
        "operation",
        "duration_seconds",
        "sections",
        "success",
        "tier_count",
        "tool_count",
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UsageMetrics:
    """Local, opt-in usage recorder + ROI summarizer.

    Args:
        base_dir: Directory for the consent state and event log.  Defaults to
            ``<data_dir>/telemetry``.  Tests pass a temp dir.
        app_version: Version string stamped onto each recorded event.
    """

    def __init__(self, base_dir: Optional[Path] = None, app_version: str = "unknown") -> None:
        self._dir = Path(base_dir) if base_dir is not None else _default_dir()
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - defensive
            logger.warning("Telemetry dir unavailable (%s); metrics disabled", exc)
        self._state_path = self._dir / "telemetry.json"
        self._events_path = self._dir / "usage.jsonl"
        self._app_version = app_version
        self._state = self._load_state()

    # -- consent / identity -------------------------------------------------

    def _load_state(self) -> Dict[str, Any]:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data.get("install_id"):
                    return data
            except (OSError, ValueError):
                logger.debug("Telemetry state unreadable; regenerating")
        state = {"install_id": uuid.uuid4().hex, "enabled": False, "created": _now_iso()}
        self._write_state(state)
        return state

    def _write_state(self, state: Dict[str, Any]) -> None:
        try:
            self._state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except OSError as exc:  # pragma: no cover - defensive
            logger.warning("Could not persist telemetry state: %s", exc)

    @property
    def enabled(self) -> bool:
        return bool(self._state.get("enabled"))

    @property
    def install_id(self) -> str:
        return str(self._state.get("install_id", ""))

    def set_consent(self, enabled: bool) -> None:
        """Persist the operator's opt-in/opt-out choice."""
        self._state["enabled"] = bool(enabled)
        self._state["consent_at"] = _now_iso()
        self._write_state(self._state)

    # -- recording ----------------------------------------------------------

    def _sanitize(self, properties: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not properties:
            return {}
        return {k: v for k, v in properties.items() if k in _ALLOWED_PROPS}

    def record_event(self, event: str, properties: Optional[Dict[str, Any]] = None) -> bool:
        """Append one anonymous event to the local log if consent is granted.

        Returns:
            True if an event was written; False if disabled or on error.
            Never raises — safe to call from job/finally paths.
        """
        if not self.enabled:
            return False
        record = {
            "ts": _now_iso(),
            "install_id": self.install_id,
            "app_version": self._app_version,
            "event": event,
            "properties": self._sanitize(properties),
        }
        try:
            with open(self._events_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(record) + "\n")
            return True
        except OSError as exc:  # pragma: no cover - defensive
            logger.debug("Telemetry write failed: %s", exc)
            return False

    # -- ROI ----------------------------------------------------------------

    def _read_events(self) -> List[Dict[str, Any]]:
        if not self._events_path.exists():
            return []
        events: List[Dict[str, Any]] = []
        try:
            lines = self._events_path.read_text(encoding="utf-8").splitlines()
        except OSError:  # pragma: no cover - defensive
            return []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
        return events

    def roi_summary(self) -> Dict[str, Any]:
        """Compute the local ROI summary from recorded events."""
        events = self._read_events()
        counts: Dict[str, int] = {}
        minutes = 0
        for event in events:
            name = event.get("event", "")
            counts[name] = counts.get(name, 0) + 1
            minutes += TIME_SAVED_MINUTES.get(name, 0)
        return {
            "enabled": self.enabled,
            "install_id": self.install_id,
            "total_events": len(events),
            "counts": counts,
            "estimated_minutes_saved": minutes,
            "estimated_hours_saved": round(minutes / 60.0, 1),
            "first_event": events[0].get("ts") if events else None,
            "last_event": events[-1].get("ts") if events else None,
            # Local-only in this release; flips to True once a central
            # receiver is wired up (see docs/development/TELEMETRY.md).
            "transmitted": False,
        }


def _default_dir() -> Path:
    from utils import get_data_dir

    return Path(get_data_dir()) / "telemetry"


_SINGLETON: Optional[UsageMetrics] = None


def get_usage_metrics(app_version: str = "unknown") -> UsageMetrics:
    """Return the process-wide :class:`UsageMetrics` singleton."""
    global _SINGLETON
    if _SINGLETON is None:
        _SINGLETON = UsageMetrics(app_version=app_version)
    return _SINGLETON
