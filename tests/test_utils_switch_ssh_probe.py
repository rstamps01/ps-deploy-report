"""Unit tests for :mod:`utils.switch_ssh_probe` — RM-15.

The probe is the shared helper that the Reporter tile now runs in
``_run_report_job`` to populate ``switch_password_by_ip`` *before*
``VnetmapWorkflow`` is invoked, so the workflow engages its native
``--multiple-passwords`` fast path instead of falling back to the
single-``-p`` candidate sweep that can never succeed on heterogeneous
fleets (e.g. two leaves on ``Vastdata1!``, a spare on ``VastData1!``).

The behaviour tested here was previously embedded in
``HealthChecker._probe_switch_password``; it was lifted into
``utils.switch_ssh_probe`` so both the Health Check tile (RM-13) and
the Reporter tile (RM-15) share a single implementation with a single
test surface.  ``HealthChecker._probe_switch_password`` is now a thin
delegator, so the existing health-checker tests continue to pass
through the same underlying code path.
"""

import logging
from unittest.mock import MagicMock, patch

import pytest

from utils.switch_ssh_probe import (
    build_switch_password_by_ip,
    probe_switch_password,
)

# =========================================================================
# probe_switch_password
# =========================================================================


class TestProbeSwitchPassword:
    """Single-IP probe: try each candidate credential, return the winner."""

    def test_returns_none_for_empty_candidate_list(self):
        # An empty candidate list is a legitimate caller state (e.g. autofill
        # disabled, no UI password typed).  The probe must short-circuit
        # without attempting any SSH I/O — network calls would be both
        # wasteful and confusing in the operator log.
        with patch("utils.switch_ssh_probe.run_ssh_command") as mock_ssh:
            with patch("utils.switch_ssh_probe.run_interactive_ssh") as mock_pty:
                result = probe_switch_password("10.0.0.1", "cumulus", [])
        assert result is None
        mock_ssh.assert_not_called()
        mock_pty.assert_not_called()

    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_first_candidate_wins_returns_first(self, mock_ssh):
        # Cumulus-happy path: ``hostname`` authenticates on the first try.
        # ``run_ssh_command`` returns rc=0; probe returns immediately
        # without calling any additional candidates.
        mock_ssh.return_value = (0, "leaf-1.example.com\n", "")
        result = probe_switch_password("10.0.0.1", "cumulus", ["Vastdata1!", "VastData1!", "Cumu1usLinux!"])
        assert result == "Vastdata1!"
        # Only the first combo should have been attempted.
        assert mock_ssh.call_count == 1

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_second_candidate_wins_after_first_denies(self, mock_ssh, mock_pty):
        # Heterogeneous fleet: this switch is on ``VastData1!`` (second
        # candidate).  ``hostname`` returns permission denied on candidate
        # 1, succeeds on candidate 2.
        mock_ssh.side_effect = [
            (255, "", "Permission denied (publickey,password)"),  # Vastdata1!
            (0, "leaf-2.example.com\n", ""),  # VastData1!
        ]
        # Interactive fallback for the denied candidate: also denied
        # (prevents false positive).
        mock_pty.return_value = (255, "", "authentication failed")
        result = probe_switch_password(
            "10.0.0.2",
            "cumulus",
            ["Vastdata1!", "VastData1!"],
        )
        assert result == "VastData1!"
        assert mock_ssh.call_count == 2

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_onyx_falls_back_to_interactive_show_version(self, mock_ssh, mock_pty):
        # Onyx / MLNX-OS restricted shell rejects ``hostname`` with
        # "authentication failed" (or in practice "UNIX shell commands
        # cannot be executed" — the probe only cares that stderr trips
        # the permission-denied / authentication guard).  The probe
        # must then re-run the same combo through ``run_interactive_ssh``
        # with ``show version`` before giving up on that candidate.
        mock_ssh.return_value = (1, "", "authentication failed")
        mock_pty.return_value = (0, "Product name: Onyx\nProduct release: 3.10.4104", "")
        result = probe_switch_password("10.0.0.3", "admin", ["admin"])
        assert result == "admin"
        mock_pty.assert_called_once()
        # The interactive call must reuse the same (user, password) that
        # failed on the SSH-command path; that's the whole point of the
        # fallback.
        args, kwargs = mock_pty.call_args
        assert args[0] == "10.0.0.3"
        assert args[1] == "admin"
        assert args[2] == "admin"
        assert "show version" in args[3]

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_all_candidates_fail_returns_none(self, mock_ssh, mock_pty):
        # Fleet rejects every configured password.  The probe must return
        # ``None`` — NOT raise — so the caller can fall back to the legacy
        # candidate-sweep path and/or surface a single actionable
        # "auth exhausted" error at the pipeline boundary (RM-7).
        mock_ssh.return_value = (255, "", "Permission denied")
        mock_pty.return_value = (255, "", "authentication failed")
        result = probe_switch_password(
            "10.0.0.4",
            "cumulus",
            ["wrong1", "wrong2", "wrong3"],
        )
        assert result is None

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_non_auth_error_does_not_trigger_interactive_fallback(self, mock_ssh, mock_pty):
        # A non-auth ``rc != 0`` (e.g. command-not-found, timeout) must
        # NOT trip the interactive ``show version`` fallback — that
        # fallback exists solely to handle Onyx restricted-shell auth
        # rejections.  Running ``show version`` against a truly
        # unreachable switch wastes 15s per candidate.
        mock_ssh.return_value = (127, "", "command not found")
        result = probe_switch_password("10.0.0.5", "cumulus", ["Vastdata1!"])
        assert result is None
        mock_pty.assert_not_called()

    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_ssh_raises_is_treated_as_failure_for_that_candidate(self, mock_ssh):
        # A transient SSH layer exception (paramiko channel error,
        # connect timeout, DNS hiccup) must not abort the whole probe —
        # we should keep trying remaining candidates.
        mock_ssh.side_effect = [
            OSError("connect timeout"),
            (0, "leaf-3.example.com\n", ""),
        ]
        result = probe_switch_password("10.0.0.6", "cumulus", ["first", "second"])
        assert result == "second"

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_admin_admin_combo_is_tried_via_build_switch_credential_combos(self, mock_ssh, mock_pty):
        # Interactive fallback also mocked — ``stderr="Permission denied"``
        # trips the auth-failure branch which otherwise forkpty()s a real
        # SSH session to the test IP (noisy + slow).
        mock_pty.return_value = (255, "", "authentication failed")
        # The shared ``build_switch_credential_combos`` adds the Onyx
        # factory default ``admin``/``admin`` to the combo set when the
        # primary user is ``cumulus`` — this is documented in
        # ``utils.ssh_adapter.build_switch_credential_combos``.  The
        # probe must use that expanded combo list so a freshly-reset
        # Onyx spare authenticates even when the operator only supplied
        # cumulus passwords.  Asserting by (user, password) tuples makes
        # the contract robust to future re-orderings of the combo list.
        mock_ssh.return_value = (255, "", "Permission denied")
        probe_switch_password("10.0.0.7", "cumulus", ["Vastdata1!"])
        seen = {(call.args[1], call.args[2]) for call in mock_ssh.call_args_list}
        assert ("admin", "admin") in seen, f"admin/admin combo missing from probe attempts: {seen}"

    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_jump_kwargs_are_forwarded(self, mock_ssh):
        # The Reporter-tile probe runs through a bastion (the VAST CNode
        # acts as a proxy-jump host for the operator laptop).  jump_host,
        # jump_user, jump_password must be forwarded to every SSH call.
        mock_ssh.return_value = (0, "hostname-ok\n", "")
        probe_switch_password(
            "10.0.0.8",
            "cumulus",
            ["Vastdata1!"],
            jump_host="172.16.0.1",
            jump_user="vastdata",
            jump_password="node-pw",
        )
        _args, kwargs = mock_ssh.call_args
        assert kwargs.get("jump_host") == "172.16.0.1"
        assert kwargs.get("jump_user") == "vastdata"
        assert kwargs.get("jump_password") == "node-pw"

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_logger_is_used_when_provided(self, mock_ssh, mock_pty):
        # Some callers (HealthChecker) want the probe's diagnostics
        # routed through their module logger so operator SSE streams
        # show the probe progress.  When no logger is supplied we fall
        # back to the module default; when one IS supplied, the probe
        # must use it (verified here via the failure-summary log
        # emitted when every candidate is rejected).
        mock_ssh.return_value = (255, "", "Permission denied")
        mock_pty.return_value = (255, "", "denied")
        logger = MagicMock(spec=logging.Logger)
        result = probe_switch_password("10.0.0.9", "cumulus", ["wrong"], logger=logger)
        assert result is None
        logger.warning.assert_called()


# =========================================================================
# build_switch_password_by_ip
# =========================================================================


class TestBuildSwitchPasswordByIp:
    """Multi-IP orchestrator: iterate switch_ips, probe each, return map."""

    def test_empty_switch_ips_returns_empty_map(self):
        # No switches to probe = nothing to discover.  The probe must
        # not call the SSH layer at all, and must return a literal empty
        # dict (so callers can unconditionally ``if map:`` without a
        # ``None`` guard).
        with patch("utils.switch_ssh_probe.run_ssh_command") as mock_ssh:
            result = build_switch_password_by_ip(
                switch_ips=[],
                switch_user="cumulus",
                candidates=["Vastdata1!"],
            )
        assert result == {}
        mock_ssh.assert_not_called()

    def test_empty_candidates_returns_empty_map(self):
        # Defensive: if caller forgot to supply candidates we treat the
        # probe as a no-op rather than iterating switches and eating a
        # round-trip per IP.
        with patch("utils.switch_ssh_probe.run_ssh_command") as mock_ssh:
            result = build_switch_password_by_ip(
                switch_ips=["10.0.0.1", "10.0.0.2"],
                switch_user="cumulus",
                candidates=[],
            )
        assert result == {}
        mock_ssh.assert_not_called()

    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_homogeneous_fleet_all_ips_map_to_same_password(self, mock_ssh):
        # Two switches on the same password: both authenticate with the
        # first candidate on first try.  Result map has both IPs.
        mock_ssh.return_value = (0, "hostname-ok\n", "")
        result = build_switch_password_by_ip(
            switch_ips=["10.0.0.1", "10.0.0.2"],
            switch_user="cumulus",
            candidates=["Vastdata1!"],
        )
        assert result == {"10.0.0.1": "Vastdata1!", "10.0.0.2": "Vastdata1!"}

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_heterogeneous_fleet_different_passwords_per_switch(self, mock_ssh, mock_pty):
        # The motivating RM-15 case: two leaves on ``Vastdata1!`` and a
        # spare on ``VastData1!``.  Each switch's side_effect list
        # exhausts independently; the final map reflects per-switch
        # winners.
        def ssh_side_effect(host, user, pw, cmd, *a, **kw):
            # 10.0.0.1 and .2 accept Vastdata1!; 10.0.0.3 requires VastData1!
            if host in ("10.0.0.1", "10.0.0.2") and pw == "Vastdata1!":
                return (0, "ok", "")
            if host == "10.0.0.3" and pw == "VastData1!":
                return (0, "ok", "")
            return (255, "", "Permission denied")

        mock_ssh.side_effect = ssh_side_effect
        mock_pty.return_value = (255, "", "denied")

        result = build_switch_password_by_ip(
            switch_ips=["10.0.0.1", "10.0.0.2", "10.0.0.3"],
            switch_user="cumulus",
            candidates=["Vastdata1!", "VastData1!"],
        )
        assert result == {
            "10.0.0.1": "Vastdata1!",
            "10.0.0.2": "Vastdata1!",
            "10.0.0.3": "VastData1!",
        }

    @patch("utils.switch_ssh_probe.run_interactive_ssh")
    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_partial_authentication_some_ips_absent_from_map(self, mock_ssh, mock_pty):
        # One switch is unreachable / rejects every candidate; the other
        # two authenticate.  The returned map must contain only the two
        # that succeeded — the caller uses ``all(ip in map for ip in
        # switch_ips)`` to decide whether the Fast path can engage, so
        # a partial map correctly falls back to the candidate-sweep.
        def ssh_side_effect(host, user, pw, cmd, *a, **kw):
            if host == "10.0.0.99":
                return (255, "", "Permission denied")
            return (0, "ok", "")

        mock_ssh.side_effect = ssh_side_effect
        mock_pty.return_value = (255, "", "denied")

        result = build_switch_password_by_ip(
            switch_ips=["10.0.0.1", "10.0.0.2", "10.0.0.99"],
            switch_user="cumulus",
            candidates=["Vastdata1!"],
        )
        assert "10.0.0.1" in result
        assert "10.0.0.2" in result
        assert "10.0.0.99" not in result

    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_ip_strings_are_preserved_verbatim_as_keys(self, mock_ssh):
        # Callers look up by the same IP string they passed in.
        # Coercing (e.g. ipaddress.ip_address) would break that
        # contract; the returned dict keys must be byte-for-byte
        # identical to the input list entries.
        mock_ssh.return_value = (0, "", "")
        ips = ["10.0.0.001", "10.143.11.156"]  # note leading-zero form
        result = build_switch_password_by_ip(
            switch_ips=ips,
            switch_user="cumulus",
            candidates=["Vastdata1!"],
        )
        assert set(result.keys()) == set(ips)

    @patch("utils.switch_ssh_probe.run_ssh_command")
    def test_jump_kwargs_are_forwarded_to_every_probe(self, mock_ssh):
        # Proxy-jump wiring is per-call: every IP goes through the same
        # bastion.  Verify the kwargs reach every SSH invocation, not
        # just the first.
        mock_ssh.return_value = (0, "", "")
        build_switch_password_by_ip(
            switch_ips=["10.0.0.1", "10.0.0.2"],
            switch_user="cumulus",
            candidates=["Vastdata1!"],
            jump_host="172.16.0.1",
            jump_user="vastdata",
            jump_password="node-pw",
        )
        for call in mock_ssh.call_args_list:
            assert call.kwargs.get("jump_host") == "172.16.0.1"
            assert call.kwargs.get("jump_user") == "vastdata"
            assert call.kwargs.get("jump_password") == "node-pw"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
