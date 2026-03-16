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


if __name__ == "__main__":
    unittest.main()
