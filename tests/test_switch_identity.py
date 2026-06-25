"""Unit tests for src/utils/switch_identity.py.

Covers the duplicate-name designator logic that lets two same-named switches
(e.g. two "Spine-B" at different management IPs) remain distinct end-to-end.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.switch_identity import (  # noqa: E402
    assign_switch_designators,
    designator_suffix,
    switch_identity_key,
)


class TestSwitchIdentityKey(unittest.TestCase):
    def test_prefers_mgmt_ip(self):
        sw = {"name": "Spine-B", "serial": "S1", "mgmt_ip": "10.0.0.5"}
        self.assertEqual(switch_identity_key(sw), "10.0.0.5")

    def test_falls_back_to_serial_then_name(self):
        self.assertEqual(switch_identity_key({"name": "SW1", "serial": "S9"}), "S9")
        self.assertEqual(switch_identity_key({"name": "SW1"}), "SW1")
        self.assertEqual(switch_identity_key({"hostname": "host9"}), "host9")

    def test_ignores_unknown_and_empty(self):
        sw = {"mgmt_ip": "Unknown", "serial": "", "name": "Real"}
        self.assertEqual(switch_identity_key(sw), "Real")

    def test_no_identifier_returns_empty(self):
        self.assertEqual(switch_identity_key({}), "")


class TestDesignatorSuffix(unittest.TestCase):
    def test_letters(self):
        self.assertEqual(designator_suffix(0), "a")
        self.assertEqual(designator_suffix(1), "b")
        self.assertEqual(designator_suffix(25), "z")

    def test_wraps_to_double_letters(self):
        self.assertEqual(designator_suffix(26), "aa")
        self.assertEqual(designator_suffix(27), "ab")


class TestAssignSwitchDesignators(unittest.TestCase):
    def test_duplicate_names_get_letters_by_mgmt_ip(self):
        switches = [
            {"name": "Spine-B", "mgmt_ip": "10.84.214.29"},
            {"name": "Spine-B", "mgmt_ip": "10.84.214.28"},
        ]
        assign_switch_designators(switches)
        by_id = {s["switch_id"]: s for s in switches}
        # (a) -> lower IP (.28), (b) -> higher IP (.29)
        self.assertEqual(by_id["10.84.214.28"]["display_name"], "Spine-B (a)")
        self.assertEqual(by_id["10.84.214.29"]["display_name"], "Spine-B (b)")

    def test_unique_names_unchanged(self):
        switches = [
            {"name": "SW-LF-01", "mgmt_ip": "10.0.0.1"},
            {"name": "SW-LF-02", "mgmt_ip": "10.0.0.2"},
        ]
        assign_switch_designators(switches)
        self.assertEqual(switches[0]["display_name"], "SW-LF-01")
        self.assertEqual(switches[1]["display_name"], "SW-LF-02")
        self.assertEqual(switches[0]["switch_id"], "10.0.0.1")

    def test_missing_mgmt_ip_falls_back_to_serial(self):
        switches = [
            {"name": "Dup", "serial": "SN-2"},
            {"name": "Dup", "serial": "SN-1"},
        ]
        assign_switch_designators(switches)
        by_id = {s["switch_id"]: s for s in switches}
        self.assertEqual(by_id["SN-1"]["display_name"], "Dup (a)")
        self.assertEqual(by_id["SN-2"]["display_name"], "Dup (b)")

    def test_designators_are_stable_across_input_order(self):
        a = [
            {"name": "Spine-B", "mgmt_ip": "10.0.0.29"},
            {"name": "Spine-B", "mgmt_ip": "10.0.0.28"},
        ]
        b = [
            {"name": "Spine-B", "mgmt_ip": "10.0.0.28"},
            {"name": "Spine-B", "mgmt_ip": "10.0.0.29"},
        ]
        assign_switch_designators(a)
        assign_switch_designators(b)
        a_map = {s["switch_id"]: s["display_name"] for s in a}
        b_map = {s["switch_id"]: s["display_name"] for s in b}
        self.assertEqual(a_map, b_map)

    def test_empty_list_returns_empty(self):
        self.assertEqual(assign_switch_designators([]), [])

    def test_returns_same_list_object(self):
        switches = [{"name": "X", "mgmt_ip": "1.1.1.1"}]
        self.assertIs(assign_switch_designators(switches), switches)


if __name__ == "__main__":
    unittest.main()
