"""
Tests for rack diagram generator.

Verifies that when an Identifier Key (model) is not found in the Library,
the generic 1U or 2U shapes are used.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rack_diagram import RackDiagram  # noqa: E402


class TestGenericFallback(unittest.TestCase):
    """Verify generic 1U/2U fallback when identifier key is not in Library."""

    def setUp(self):
        self.rack = RackDiagram(rack_height_u=42, library_path=None)

    def test_unknown_model_uses_generic_1u_by_default(self):
        """When model is not in library and not in built-in list, generic 1U is used."""
        model = "unknown_identifier_key_xyz"
        path = self.rack._get_hardware_image_path(model)
        self.assertIsNotNone(path, "Should return a path (generic fallback)")
        self.assertTrue(path.exists(), f"Generic image should exist: {path}")
        self.assertIn("generic_1u.png", str(path), "Unknown model should fall back to generic 1U")

    def test_unknown_model_height_defaults_to_1u(self):
        """_get_device_height_units returns 1 for unknown model."""
        height = self.rack._get_device_height_units("unknown_xyz")
        self.assertEqual(height, 1, "Unknown model should default to 1U")

    def test_2u_pattern_uses_generic_2u(self):
        """When model matches a 2U pattern but has no image in library, generic 2U is used."""
        # ceres_4u is in two_u_models (2U) but has no entry in built-in image map,
        # so we get height 2 and fall back to generic_2u.png
        model = "ceres_4u"
        height = self.rack._get_device_height_units(model)
        self.assertEqual(height, 2, "ceres_4u is a 2U pattern")
        path = self.rack._get_hardware_image_path(model)
        self.assertIsNotNone(path)
        self.assertIn("generic_2u.png", str(path), "2U model without image should use generic 2U")

    def test_generic_1u_and_2u_files_exist(self):
        """Generic placeholder images exist in assets."""
        from rack_diagram import HARDWARE_IMAGE_DIR

        generic_1u = HARDWARE_IMAGE_DIR / "generic_1u.png"
        generic_2u = HARDWARE_IMAGE_DIR / "generic_2u.png"
        self.assertTrue(generic_1u.exists(), f"generic_1u.png should exist at {generic_1u}")
        self.assertTrue(generic_2u.exists(), f"generic_2u.png should exist at {generic_2u}")


class TestDeviceBoundaries(unittest.TestCase):

    def setUp(self):
        self.rack = RackDiagram(rack_height_u=42, library_path=None)

    def test_gather_boundaries_standard_cluster(self):
        cboxes = [
            {"model": "c100", "rack_unit": "U25"},
            {"model": "c100", "rack_unit": "U26"},
            {"model": "c100", "rack_unit": "U27"},
        ]
        dboxes = [
            {"model": "d100", "rack_unit": "U10"},
            {"model": "d100", "rack_unit": "U11"},
            {"model": "d100", "rack_unit": "U12"},
            {"model": "d100", "rack_unit": "U13"},
        ]
        result = self.rack._gather_device_boundaries(cboxes, dboxes)
        self.assertIsNotNone(result)
        self.assertEqual(result["highest_cbox_top"], 27)
        self.assertEqual(result["lowest_cbox_bottom"], 25)
        self.assertEqual(result["highest_dbox_top"], 13)
        self.assertEqual(result["lowest_dbox_bottom"], 10)
        self.assertIsNone(result["highest_ebox_top"])
        self.assertIsNone(result["lowest_ebox_bottom"])

    def test_gather_boundaries_with_eboxes(self):
        cboxes = [{"model": "c100", "rack_unit": "U20"}]
        dboxes = [{"model": "d100", "rack_unit": "U30"}]
        eboxes = [
            {"model": "ebox", "rack_unit": "U5"},
            {"model": "ebox", "rack_unit": "U6"},
            {"model": "ebox", "rack_unit": "U7"},
            {"model": "ebox", "rack_unit": "U8"},
        ]
        result = self.rack._gather_device_boundaries(cboxes, dboxes, eboxes)
        self.assertIsNotNone(result)
        self.assertEqual(result["highest_ebox_top"], 8)
        self.assertEqual(result["lowest_ebox_bottom"], 5)
        self.assertEqual(result["highest_cbox_top"], 20)
        self.assertEqual(result["highest_dbox_top"], 30)

    def test_gather_boundaries_empty(self):
        result = self.rack._gather_device_boundaries([], [])
        self.assertIsNone(result)

    def test_gather_boundaries_single_device(self):
        cboxes = [{"model": "c100", "rack_unit": "U15"}]
        result = self.rack._gather_device_boundaries(cboxes, [])
        self.assertIsNotNone(result)
        self.assertEqual(result["highest_cbox_top"], 15)
        self.assertEqual(result["lowest_cbox_bottom"], 15)
        self.assertIsNone(result["highest_dbox_top"])
        self.assertIsNone(result["lowest_dbox_bottom"])


class TestSwitchPlacement(unittest.TestCase):

    def setUp(self):
        self.rack = RackDiagram(rack_height_u=42, library_path=None)

    def test_center_placement_success(self):
        positions = self.rack._try_center_placement(lowest_cbox_bottom=25, highest_dbox_top=13, switch_height=1)
        self.assertEqual(len(positions), 2)
        self.assertTrue(all(13 < p < 25 for p in positions))

    def test_center_placement_no_gap(self):
        positions = self.rack._try_center_placement(lowest_cbox_bottom=10, highest_dbox_top=9, switch_height=1)
        self.assertEqual(positions, [])

    def test_above_placement_success(self):
        positions = self.rack._try_above_placement(highest_cbox_top=30, switch_height=1, rack_height=42)
        self.assertEqual(len(positions), 2)
        self.assertTrue(all(p > 30 for p in positions))
        self.assertTrue(all(p <= 42 for p in positions))

    def test_above_placement_at_rack_top(self):
        positions = self.rack._try_above_placement(highest_cbox_top=40, switch_height=1, rack_height=42)
        self.assertEqual(positions, [])

    def test_below_placement_success(self):
        positions = self.rack._try_below_placement(lowest_dbox_bottom=10, switch_height=1)
        self.assertEqual(len(positions), 2)
        self.assertTrue(all(p < 10 for p in positions))
        self.assertTrue(all(p >= 1 for p in positions))

    def test_below_placement_at_rack_bottom(self):
        positions = self.rack._try_below_placement(lowest_dbox_bottom=3, switch_height=1)
        self.assertEqual(positions, [])

    def test_calculate_switch_positions_cascading(self):
        cboxes = [{"model": "c100", "rack_unit": "U10"}]
        dboxes = [{"model": "d100", "rack_unit": "U9"}]
        positions = self.rack._calculate_switch_positions(cboxes, dboxes, 2)
        self.assertEqual(len(positions), 2)
        self.assertTrue(all(p > 10 for p in positions))


class TestRackDiagramGeneration(unittest.TestCase):

    def setUp(self):
        self.rack = RackDiagram(rack_height_u=42, library_path=None)

    def test_generate_returns_drawing(self):
        from reportlab.graphics.shapes import Drawing as DrawingClass

        cboxes = [
            {"id": 1, "model": "c100", "rack_unit": "U25", "state": "ACTIVE"},
            {"id": 2, "model": "c100", "rack_unit": "U26", "state": "ACTIVE"},
        ]
        dboxes = [
            {"id": 1, "model": "d100", "rack_unit": "U10", "state": "ACTIVE"},
            {"id": 2, "model": "d100", "rack_unit": "U11", "state": "ACTIVE"},
        ]
        result = self.rack.generate_rack_diagram(cboxes, dboxes)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        drawing, switch_map = result
        self.assertIsInstance(drawing, DrawingClass)
        self.assertIsInstance(switch_map, dict)

    def test_generate_with_eboxes(self):
        from reportlab.graphics.shapes import Drawing as DrawingClass

        cboxes = [{"id": 1, "model": "c100", "rack_unit": "U20", "state": "ACTIVE"}]
        dboxes = []
        eboxes = [
            {"id": 1, "model": "ebox", "rack_unit": "U5", "state": "ACTIVE"},
            {"id": 2, "model": "ebox", "rack_unit": "U6", "state": "ACTIVE"},
        ]
        drawing, switch_map = self.rack.generate_rack_diagram(cboxes, dboxes, eboxes=eboxes)
        self.assertIsInstance(drawing, DrawingClass)

    def test_get_unrecognized_models(self):
        import rack_diagram as rd

        rd._unrecognized_models.clear()
        unique_model = "totally_unknown_test_device_xyz_9999"
        self.rack._get_hardware_image_path(unique_model)
        unrecognized = rd.get_unrecognized_models()
        self.assertIn(unique_model, unrecognized)


if __name__ == "__main__":
    unittest.main()
