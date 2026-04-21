"""Shared switch-SSH password candidate resolver.

Both the One-Shot Test Suite runner (``src.oneshot_runner.OneShotRunner``)
and the Reporter tile's ``_run_report_job`` (``src.app``) need to build the
same ordered list of switch SSH passwords to try when the operator has
ticked **Advanced → Autofill Password**.  Keeping the logic here (rather
than inside ``OneShotRunner``) ensures:

  * The Reporter tile's :class:`VnetmapWorkflow`,
    :class:`ExternalPortMapper` and :class:`HealthChecker` see the same
    candidate list that the Test Suite tile does, so a switch using a
    vendor default (e.g. ``Cumu1usLinux!``) authenticates regardless of
    which tile the operator clicked.
  * A single code path owns the precedence rules; adding a new built-in
    default or a new source of site-specific passwords is a one-file
    change.

Precedence (head-first, deduplicated):

  1. ``existing`` — explicit override (programmatic / test).  When
     truthy, skips the rest and returns it verbatim.
  2. ``user_password`` — the Connection Settings Switch Password typed by
     the operator.  Always strongest signal for the primary switch(es)
     they just logged into.
  3. When ``use_default_creds`` is ``True``:
       a. ``advanced_operations.default_switch_passwords`` list from
          ``config/config.yaml`` (site-specific; gitignored).
       b. ``VAST_DEFAULT_SWITCH_PASSWORDS`` environment variable
          (colon-separated) — same role as the config list but
          convenient for CI / ephemeral shells.
       c. :data:`BUILTIN_AUTOFILL_SWITCH_PASSWORDS` — the published VAST
          + Cumulus defaults.  Ship so the "Autofill Password" UI
          checkbox is meaningful on a freshly-initialised cluster whose
          operator hasn't customised ``config.yaml``.  ``(admin,
          admin)`` is *not* in this list; it is contributed separately
          by :func:`utils.ssh_adapter.build_switch_credential_combos`.

When ``use_default_creds`` is ``False`` the caller gets whatever the UI
typed (single entry, or empty).  No built-in defaults are injected on
that path — operators who opt out of autofill get exactly what they
typed.
"""

from __future__ import annotations

import logging
import os
from typing import Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# RM-12: published vendor defaults.  See module docstring and the
# rationale block in ``src/oneshot_runner.py`` for why these are
# source-of-truth for the "Autofill Password" UI affordance and not
# site-specific secrets.
BUILTIN_AUTOFILL_SWITCH_PASSWORDS: Tuple[str, ...] = (
    "Vastdata1!",
    "VastData1!",
    "Cumu1usLinux!",
)


def _load_config_passwords(config_path: Optional[str]) -> List[str]:
    """Return ``advanced_operations.default_switch_passwords`` from YAML, or ``[]``."""
    if not config_path:
        return []
    try:
        import yaml

        with open(config_path, "r", encoding="utf-8") as fh:
            cfg = yaml.safe_load(fh) or {}
    except FileNotFoundError:
        return []
    except Exception as exc:
        logger.debug("Could not load default_switch_passwords from %s: %s", config_path, exc)
        return []

    raw = (cfg.get("advanced_operations") or {}).get("default_switch_passwords") or []
    return [str(pw) for pw in raw if pw]


def _load_env_passwords() -> List[str]:
    """Return passwords from ``VAST_DEFAULT_SWITCH_PASSWORDS`` (colon-separated)."""
    raw = os.environ.get("VAST_DEFAULT_SWITCH_PASSWORDS", "")
    if not raw:
        return []
    return [piece for piece in raw.split(":") if piece]


def resolve_switch_password_candidates(
    *,
    user_password: str = "",
    config_path: Optional[str] = None,
    use_default_creds: bool = False,
    existing: Optional[Iterable[str]] = None,
) -> List[str]:
    """Build the ordered list of switch SSH passwords to try.

    See the module docstring for the full precedence rules.

    Args:
        user_password: The ``switch_password`` entered on Connection
            Settings.  Added first (after ``existing``).
        config_path: Absolute path to the operator's ``config.yaml``.
            If ``None`` the config source is skipped.
        use_default_creds: True when the "Autofill Password" UI checkbox
            is ticked.  Gates the config / env / built-in defaults.
        existing: Optional pre-resolved list (e.g. from a caller that
            has already probed).  When truthy, returned verbatim and
            deduplicated — used by tests and by ``_get_workflow_
            credentials`` to thread the one-shot runner's pre-resolved
            list through to individual workflows.

    Returns:
        A new list of unique non-empty passwords in precedence order.
    """
    if existing:
        seen: List[str] = []
        for pw in existing:
            pw_str = str(pw or "")
            if pw_str and pw_str not in seen:
                seen.append(pw_str)
        if seen:
            return seen

    candidates: List[str] = []

    def _append_unique(pw: str) -> None:
        pw_str = str(pw or "")
        if pw_str and pw_str not in candidates:
            candidates.append(pw_str)

    if user_password:
        _append_unique(user_password)

    if use_default_creds:
        for pw in _load_config_passwords(config_path):
            _append_unique(pw)
        for pw in _load_env_passwords():
            _append_unique(pw)
        for pw in BUILTIN_AUTOFILL_SWITCH_PASSWORDS:
            _append_unique(pw)

    return candidates


__all__ = ["BUILTIN_AUTOFILL_SWITCH_PASSWORDS", "resolve_switch_password_candidates"]
