"""Tests for the shared switch-SSH password candidate resolver (RM-13).

The Reporter tile (``src.app._run_report_job``) and the Test Suite tile
(``src.oneshot_runner.OneShotRunner``) both call
:func:`utils.switch_password_candidates.resolve_switch_password_candidates`
so a single source of truth governs which passwords are attempted when
"Advanced -> Autofill Password" is ticked.  These tests pin the
precedence rules so a future refactor cannot silently break either
tile's autofill behaviour.
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.switch_password_candidates import (  # noqa: E402
    BUILTIN_AUTOFILL_SWITCH_PASSWORDS,
    resolve_switch_password_candidates,
)


class TestResolveSwitchPasswordCandidates(unittest.TestCase):
    """Precedence, deduplication and autofill-gate tests."""

    def _write_config(self, passwords):
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
        tmp.write("advanced_operations:\n  default_switch_passwords:\n")
        for pw in passwords:
            tmp.write(f"    - '{pw}'\n")
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def setUp(self):
        # Clear env so individual tests opt in explicitly.
        self._saved_env = os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)

    def tearDown(self):
        if self._saved_env is not None:
            os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = self._saved_env
        else:
            os.environ.pop("VAST_DEFAULT_SWITCH_PASSWORDS", None)

    # ------------------------------------------------------------------
    # Autofill OFF
    # ------------------------------------------------------------------

    def test_autofill_off_returns_ui_password_only(self):
        result = resolve_switch_password_candidates(
            user_password="UIpw!",
            config_path=None,
            use_default_creds=False,
        )
        self.assertEqual(result, ["UIpw!"])

    def test_autofill_off_empty_when_no_ui_password(self):
        result = resolve_switch_password_candidates(
            user_password="",
            config_path=None,
            use_default_creds=False,
        )
        self.assertEqual(result, [])

    def test_autofill_off_ignores_config_and_env(self):
        cfg = self._write_config(["SiteSecret!"])
        os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = "EnvSecret!"
        result = resolve_switch_password_candidates(
            user_password="UIpw!",
            config_path=cfg,
            use_default_creds=False,
        )
        self.assertEqual(result, ["UIpw!"])

    # ------------------------------------------------------------------
    # Autofill ON — builtins always appended last
    # ------------------------------------------------------------------

    def test_autofill_on_no_inputs_yields_builtins_only(self):
        result = resolve_switch_password_candidates(
            user_password="",
            config_path=None,
            use_default_creds=True,
        )
        self.assertEqual(result, list(BUILTIN_AUTOFILL_SWITCH_PASSWORDS))

    def test_autofill_on_ui_first_then_builtins(self):
        result = resolve_switch_password_candidates(
            user_password="UIpw!",
            config_path=None,
            use_default_creds=True,
        )
        self.assertEqual(result[0], "UIpw!")
        for pw in BUILTIN_AUTOFILL_SWITCH_PASSWORDS:
            self.assertIn(pw, result)
        # UI stays strictly first.
        self.assertTrue(result.index("UIpw!") < result.index(BUILTIN_AUTOFILL_SWITCH_PASSWORDS[0]))

    def test_autofill_on_precedence_ui_config_env_builtins(self):
        cfg = self._write_config(["SiteA!", "SiteB!"])
        os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = "EnvA!:EnvB!"
        result = resolve_switch_password_candidates(
            user_password="UIpw!",
            config_path=cfg,
            use_default_creds=True,
        )
        expected_head = ["UIpw!", "SiteA!", "SiteB!", "EnvA!", "EnvB!"]
        self.assertEqual(result[: len(expected_head)], expected_head)
        # Builtins tail follows in declared order.
        self.assertEqual(result[len(expected_head) :], list(BUILTIN_AUTOFILL_SWITCH_PASSWORDS))

    def test_autofill_on_dedupes_across_sources(self):
        cfg = self._write_config(["UIpw!", "Vastdata1!"])  # UI dup + builtin dup
        os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = "UIpw!:VastData1!"  # UI + builtin dup
        result = resolve_switch_password_candidates(
            user_password="UIpw!",
            config_path=cfg,
            use_default_creds=True,
        )
        self.assertEqual(result.count("UIpw!"), 1)
        self.assertEqual(result.count("Vastdata1!"), 1)
        self.assertEqual(result.count("VastData1!"), 1)
        # Full contents match the deduped set, in precedence order.
        self.assertEqual(result, ["UIpw!", "Vastdata1!", "VastData1!", "Cumu1usLinux!"])

    def test_autofill_on_env_colon_separated(self):
        os.environ["VAST_DEFAULT_SWITCH_PASSWORDS"] = "First!:Second!"
        result = resolve_switch_password_candidates(
            user_password="",
            config_path=None,
            use_default_creds=True,
        )
        # Env entries land between config (empty here) and builtins.
        self.assertEqual(result[:2], ["First!", "Second!"])

    def test_autofill_on_missing_config_file_is_non_fatal(self):
        result = resolve_switch_password_candidates(
            user_password="UIpw!",
            config_path="/nonexistent/config.yaml",
            use_default_creds=True,
        )
        self.assertEqual(result[0], "UIpw!")
        # Builtins still present.
        for pw in BUILTIN_AUTOFILL_SWITCH_PASSWORDS:
            self.assertIn(pw, result)

    # ------------------------------------------------------------------
    # existing= override
    # ------------------------------------------------------------------

    def test_existing_override_short_circuits(self):
        result = resolve_switch_password_candidates(
            user_password="IgnoredUI!",
            config_path=None,
            use_default_creds=True,
            existing=["Forced1!", "Forced2!"],
        )
        self.assertEqual(result, ["Forced1!", "Forced2!"])

    def test_existing_override_empty_still_resolves_normally(self):
        # ``existing=[]`` is falsy, so the normal resolution path runs.
        result = resolve_switch_password_candidates(
            user_password="UIpw!",
            config_path=None,
            use_default_creds=False,
            existing=[],
        )
        self.assertEqual(result, ["UIpw!"])

    def test_existing_override_dedupes(self):
        result = resolve_switch_password_candidates(
            user_password="",
            config_path=None,
            use_default_creds=False,
            existing=["A!", "A!", "B!"],
        )
        self.assertEqual(result, ["A!", "B!"])


class TestOneShotRunnerDelegates(unittest.TestCase):
    """OneShotRunner must delegate to the shared resolver (RM-13 refactor).

    Regression guard: a future edit to OneShotRunner that inlines its own
    resolution logic would drift the two tiles apart.  We assert the
    shared function is actually called.
    """

    def test_oneshot_runner_calls_shared_resolver(self):
        from oneshot_runner import OneShotRunner

        with patch(
            "oneshot_runner._shared_resolve_switch_password_candidates",
            return_value=["X!", "Y!"],
        ) as mock_resolver:
            runner = OneShotRunner(
                selected_ops=["vnetmap"],
                credentials={
                    "cluster_ip": "10.0.0.1",
                    "switch_user": "cumulus",
                    "switch_password": "UIpw!",
                },
                use_default_creds=True,
            )

        mock_resolver.assert_called_once()
        kwargs = mock_resolver.call_args.kwargs
        self.assertEqual(kwargs["user_password"], "UIpw!")
        self.assertTrue(kwargs["use_default_creds"])
        self.assertEqual(runner._switch_password_candidates, ["X!", "Y!"])


if __name__ == "__main__":
    unittest.main()
