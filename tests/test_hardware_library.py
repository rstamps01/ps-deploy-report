"""Tests for hardware library model matching.

Device lookups match a model string by substring, longest key first. The
built-in catalog contains deliberately broad keys (``hpe``, ``arista``,
``broadwell``) that act as vendor-wide fallbacks, so a specific entry in the
user's Library must be allowed to out-rank them — otherwise adding a device
to the Library cannot override a vendor default, which is the whole point of
the Library.

Regression: a user-added ``hpe_turin_cbox`` (1U) rendered 2U because the
height lookup consulted the entire built-in catalog before the user library,
letting the bare ``hpe`` key (2U HPE IceLake) claim it. The image lookup used
merged precedence and picked the correct 1U artwork, so the rack diagram drew
the right picture stretched to 1.8x into a 2U slot.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hardware_library import (  # noqa: E402
    BUILTIN_DEVICES,
    get_device_height,
    get_device_image_filename,
)

# Mirrors the entry the Library page writes for an HPE Turin CBox. The key
# contains the built-in "hpe" fallback key as a substring, which is what made
# the original defect reachable.
USER_LIBRARY = {
    "hpe_turin_cbox": {
        "type": "cbox",
        "height_u": 1,
        "image_filename": "hpe_turin_cbox_1u.png",
        "description": "HPE Turin (DL325 Gen11) Single Server CBOX",
    }
}


def _write_placeholder_image(directory: Path, filename: str) -> Path:
    """Create a real 1x1 PNG so existence checks and any image open() succeed."""
    from PIL import Image

    path = directory / filename
    Image.new("RGB", (1, 1)).save(path)
    return path


class TestUserLibraryOutranksBroadBuiltinKey(unittest.TestCase):
    """A specific user entry must win over a shorter, broader built-in key."""

    def test_height_uses_the_user_entry_not_the_vendor_fallback(self):
        height = get_device_height("hpe_turin_cbox", USER_LIBRARY)
        self.assertEqual(
            height,
            1,
            "user library declares 1U; the bare 'hpe' built-in (2U IceLake) must not claim this model",
        )

    def test_height_match_is_case_insensitive(self):
        self.assertEqual(get_device_height("HPE_TURIN_CBOX", USER_LIBRARY), 1)

    def test_image_uses_the_user_entry_not_the_vendor_fallback(self):
        filename = get_device_image_filename("hpe_turin_cbox", USER_LIBRARY)
        self.assertEqual(filename, "hpe_turin_cbox_1u.png")

    def test_user_entry_overrides_a_builtin_with_the_same_key(self):
        """An exact-key collision resolves in the user's favour."""
        builtin_key = "dell_turin_cbox"
        self.assertEqual(BUILTIN_DEVICES[builtin_key]["height_u"], 1)
        override = {builtin_key: {"type": "cbox", "height_u": 2, "image_filename": "custom.png"}}
        self.assertEqual(get_device_height(builtin_key, override), 2)
        self.assertEqual(get_device_image_filename(builtin_key, override), "custom.png")


class TestBuiltinBehaviourUnchanged(unittest.TestCase):
    """The precedence change must not disturb models that already resolved correctly."""

    # The "ebox"/"enclosure" short-circuit in get_device_height returns 1U before
    # any catalog lookup, so these two declare 2U but resolve to 1U. That is a
    # separate defect; excluded here so this suite pins only the precedence fix.
    _EBOX_SHORT_CIRCUIT = {"supermicro_milan_ebox", "smc_milan_ebox"}

    def test_every_builtin_key_resolves_to_its_own_declared_height(self):
        for key, device in BUILTIN_DEVICES.items():
            if key in self._EBOX_SHORT_CIRCUIT:
                continue
            with self.subTest(model=key):
                self.assertEqual(get_device_height(key, USER_LIBRARY), device["height_u"])

    def test_vendor_fallback_still_applies_to_unrecognised_models_of_that_vendor(self):
        """The broad 'hpe' key must keep working where nothing more specific matches."""
        self.assertEqual(get_device_height("hpe_some_unknown_server", USER_LIBRARY), 2)

    def test_unknown_model_defaults_to_1u(self):
        self.assertEqual(get_device_height("totally_unknown_xyz", USER_LIBRARY), 1)

    def test_empty_model_defaults_to_1u(self):
        self.assertEqual(get_device_height("", USER_LIBRARY), 1)

    def test_unknown_model_has_no_image(self):
        self.assertIsNone(get_device_image_filename("totally_unknown_xyz", USER_LIBRARY))


class TestRackDiagramHeightAndImageAgree(unittest.TestCase):
    """The chosen artwork and the chosen U-height must come from the same entry.

    When they disagree the diagram draws a correct image at the wrong size:
    GraphicsImage is given an explicit width and height and does not preserve
    aspect ratio, so the device is stretched to fill its slot.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        images = tmp / "hardware_images"
        images.mkdir()
        _write_placeholder_image(images, "hpe_turin_cbox_1u.png")
        library = tmp / "device_library.json"
        library.write_text(json.dumps(USER_LIBRARY), encoding="utf-8")
        self.images_dir = str(images)
        self.library_path = str(library)

    def tearDown(self):
        self._tmp.cleanup()

    def test_user_device_resolves_to_its_own_image_and_height(self):
        from rack_diagram import RackDiagram

        rack = RackDiagram(library_path=self.library_path, user_images_dir=self.images_dir)
        image = rack._get_hardware_image_path("hpe_turin_cbox")
        height = rack._get_device_height_units("hpe_turin_cbox")

        self.assertIsNotNone(image)
        self.assertEqual(Path(image).name, "hpe_turin_cbox_1u.png")
        self.assertEqual(height, 1, "height must match the artwork that was selected")


class TestNetworkDiagramUsesUserLibrary(unittest.TestCase):
    """The logical network diagram shares the same precedence requirement."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        images = tmp / "hardware_images"
        images.mkdir()
        _write_placeholder_image(images, "hpe_turin_cbox_1u.png")
        library = tmp / "device_library.json"
        library.write_text(json.dumps(USER_LIBRARY), encoding="utf-8")
        self.images_dir = str(images)
        self.library_path = str(library)

    def tearDown(self):
        self._tmp.cleanup()

    def test_user_device_image_beats_vendor_fallback(self):
        from network_diagram import NetworkDiagramGenerator

        generator = NetworkDiagramGenerator(
            library_path=self.library_path,
            user_images_dir=self.images_dir,
        )
        path = generator.load_hardware_image("hpe_turin_cbox")
        self.assertIsNotNone(path)
        self.assertEqual(Path(path).name, "hpe_turin_cbox_1u.png")

    def test_builtin_image_still_wins_for_a_builtin_model(self):
        from network_diagram import NetworkDiagramGenerator

        generator = NetworkDiagramGenerator(
            library_path=self.library_path,
            user_images_dir=self.images_dir,
        )
        path = generator.load_hardware_image("hpe_icelake")
        self.assertIsNotNone(path)
        self.assertEqual(Path(path).name, "hpe_il_cbox_2u.png")


if __name__ == "__main__":
    unittest.main()
