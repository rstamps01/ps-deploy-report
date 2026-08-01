"""Regression tests for switch-config backup filename hygiene.

Onyx/MLNX-OS switches answer the ``hostname`` probe through an interactive
``show version`` shell whose output previously poisoned the backup filename
with raw terminal escapes (``switch_^[[?1h^[=_10_6_160_7_...txt``).  These
tests lock in the sanitization: hostnames are derived from clean text and the
filename slug is always filesystem-safe.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from workflows.switch_config_workflow import SwitchConfigWorkflow


class TestFilenameSlug:
    def test_escape_only_hostname_falls_back_to_ip(self):
        # Terminal escapes should already be stripped upstream, but if a bare
        # escape/control string slips through, the slug must not embed it.
        slug = SwitchConfigWorkflow._filename_slug("\x1b[?1h\x1b=", "10.6.160.7")
        assert slug == "10_6_160_7"

    def test_clean_hostname_preserved(self):
        assert SwitchConfigWorkflow._filename_slug("leaf-01", "10.0.0.1") == "leaf-01"

    def test_unsafe_chars_collapsed(self):
        assert SwitchConfigWorkflow._filename_slug("rack 1/leaf:2", "10.0.0.1") == "rack_1_leaf_2"

    def test_empty_hostname_falls_back_to_ip(self):
        assert SwitchConfigWorkflow._filename_slug("", "10.0.0.5") == "10_0_0_5"


class TestDeriveHostname:
    def test_first_nonempty_line_used(self):
        assert SwitchConfigWorkflow._derive_hostname("\n\n  leaf-01  \n", "10.0.0.1") == "leaf-01"

    def test_empty_output_falls_back_to_ip(self):
        assert SwitchConfigWorkflow._derive_hostname("", "10.0.0.9") == "10.0.0.9"
        assert SwitchConfigWorkflow._derive_hostname("   \n  ", "10.0.0.9") == "10.0.0.9"
