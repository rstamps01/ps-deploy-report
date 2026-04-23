"""Shared switch-SSH credential probe — RM-15.

Discovers which password (from an operator-supplied or autofilled
candidate list) actually authenticates against each switch in a
heterogeneous fleet.  The result is a ``switch_password_by_ip`` map that
downstream consumers use to engage credential-aware fast paths:

* :class:`VnetmapWorkflow` checks ``all(ip in switch_password_by_ip for
  ip in switch_ips)`` and, when every switch is covered, invokes
  ``vnetmap.py --multiple-passwords`` via its heredoc wrapper
  (``_build_multiple_passwords_cmd``) so each switch gets exactly the
  password that works for it, instead of brute-forcing the whole run
  with one password at a time.  Without this map, vnetmap.py on a
  heterogeneous fleet (e.g. two leaves on ``Vastdata1!`` and a spare on
  ``VastData1!``) fails with ``Unable to determine suitable switch
  API`` because no single ``-p '<pw>'`` can satisfy every switch.

* :class:`HealthChecker` consumes the map via
  ``switch_ssh_config["password_by_ip"]`` to route each Tier-3 check
  through the correct credential on the first try, avoiding the
  spurious ``Permission denied`` warnings the operator would otherwise
  see in the SSE log.

* :class:`OneShotRunner` (Test Suite tile) has historically populated
  an equivalent map inside ``_validate_switch_ssh``; the Reporter tile
  lacked a parallel path until RM-15 lifted this probe out of
  ``HealthChecker`` into a shared utility that both tiles call.

The probe is deliberately a pair of pure functions (no class state)
so it can be unit-tested without instantiating a full HealthChecker
and so multiple callers share a single test surface.  Every
credential combination is issued via
:func:`utils.ssh_adapter.build_switch_credential_combos` so the probe
ordering matches the downstream workflows byte-for-byte (operator's
primary user × each password first, then the Onyx ``admin``/``admin``
factory default, then ``cumulus`` × each password when the primary
user is neither ``cumulus`` nor ``admin``).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from utils.ssh_adapter import (
    build_switch_credential_combos,
    run_interactive_ssh,
    run_ssh_command,
)

_DEFAULT_LOGGER = logging.getLogger(__name__)


def probe_switch_password(
    switch_ip: str,
    switch_user: str,
    candidates: List[str],
    *,
    logger: Optional[logging.Logger] = None,
    **ssh_kwargs: Any,
) -> Optional[str]:
    """Probe ``switch_ip`` with each credential candidate; return the winner.

    Runs a cheap ``hostname`` over :func:`run_ssh_command` first
    (Cumulus-happy path).  On a permission-denied / authentication
    failure, re-issues the same ``(user, password)`` combo through
    :func:`run_interactive_ssh` with ``show version`` to handle Onyx /
    MLNX-OS restricted shells, which reject raw shell commands even
    when the credentials are valid.  A non-auth failure (rc != 0 for
    reasons like command-not-found or network timeout) does NOT trip
    the interactive fallback — we'd just waste a round-trip on
    definitely-unreachable switches.

    Exceptions from the SSH layer are swallowed per-candidate (a
    transient paramiko channel error on one combo must not abort the
    remaining attempts on the next combo).

    Args:
        switch_ip: Management IP of the switch.
        switch_user: Operator-supplied primary username (typically
            ``cumulus`` for VAST installations; ``admin`` on Onyx).
        candidates: Ordered password list — UI-entered first, then
            site-specific and published defaults appended by
            :func:`utils.switch_password_candidates.resolve_switch_password_candidates`.
        logger: Optional logger for progress / exhaustion diagnostics.
            Callers that want probe progress routed through their
            module logger (e.g. ``HealthChecker.logger``) pass it in;
            otherwise the module default is used.
        **ssh_kwargs: Forwarded verbatim to ``run_ssh_command`` /
            ``run_interactive_ssh`` — typically ``jump_host`` /
            ``jump_user`` / ``jump_password`` so the probe routes
            through the cluster CNode as a bastion.

    Returns:
        The first password from ``candidates`` that authenticates
        against ``switch_ip``, or ``None`` if every candidate is
        rejected / the candidate list is empty.
    """
    log = logger or _DEFAULT_LOGGER

    if not candidates:
        return None
    combos = build_switch_credential_combos(switch_user, list(candidates))
    if not combos:
        return None

    for user, password in combos:
        try:
            rc, _stdout, stderr = run_ssh_command(switch_ip, user, password, "hostname", timeout=15, **ssh_kwargs)
            if rc == 0:
                return str(password)
            # Only fall back to interactive ``show version`` when the
            # failure looks like auth — a rc != 0 with permission-denied
            # / authentication-failed in stderr is the Onyx signature.
            combined = (stderr or "").lower()
            if "permission denied" in combined or "authentication" in combined:
                rc_i, _out_i, _err_i = run_interactive_ssh(
                    switch_ip, user, password, "show version", timeout=15, **ssh_kwargs
                )
                if rc_i == 0:
                    return str(password)
        except Exception as exc:  # noqa: BLE001 - defensive per-candidate trap
            log.debug("Switch %s probe raised %s; trying next candidate", switch_ip, exc)
            continue

    log.warning(
        "Switch %s rejected every candidate password; downstream workflows will fall back to primary password",
        switch_ip,
    )
    return None


def build_switch_password_by_ip(
    switch_ips: List[str],
    switch_user: str,
    candidates: List[str],
    *,
    logger: Optional[logging.Logger] = None,
    **ssh_kwargs: Any,
) -> Dict[str, str]:
    """Probe every IP in ``switch_ips`` and return a ``{ip: password}`` map.

    Only IPs that successfully authenticate appear in the result —
    consumers (notably
    ``VnetmapWorkflow._step_run_vnetmap``'s Fast-path guard
    ``all(ip in switch_password_by_ip for ip in switch_ips)``) use the
    presence / absence of an IP to decide whether the credential-aware
    fast path can engage.  A partial map therefore correctly forces
    fall-back to the legacy candidate-sweep, while an empty or missing
    map short-circuits the fast path entirely — this is the intended
    behaviour on homogeneous fleets where ``candidates`` contains a
    single password (there is nothing to probe).

    The function short-circuits without any SSH I/O when either list
    is empty, so callers can invoke it unconditionally at the top of a
    job without guard-clauses.

    Args:
        switch_ips: Ordered list of switch management IPs to probe.
            Key strings are preserved verbatim in the result map.
        switch_user: See :func:`probe_switch_password`.
        candidates: See :func:`probe_switch_password`.
        logger: See :func:`probe_switch_password`.
        **ssh_kwargs: Forwarded verbatim to every underlying probe
            call (typically ``jump_host`` / ``jump_user`` /
            ``jump_password``).

    Returns:
        Dict mapping each successfully-probed switch IP to the
        password that worked.  Callers MUST handle the empty-dict case
        (common: homogeneous single-candidate deployments).
    """
    if not switch_ips or not candidates:
        return {}

    result: Dict[str, str] = {}
    for ip in switch_ips:
        pw = probe_switch_password(
            str(ip),
            switch_user,
            candidates,
            logger=logger,
            **ssh_kwargs,
        )
        if pw is not None:
            result[str(ip)] = pw
    return result
