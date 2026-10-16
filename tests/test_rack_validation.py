"""Full-rack validation harness (RACK-2)."""

import json
import sys
from pathlib import Path

import pymupdf
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from hardware_library import BUILTIN_DEVICES  # noqa: E402
from rack_diagram import RackDiagram  # noqa: E402
from utils.rack_validation import build_validation_racks, fill_rack_pair, library_sequence  # noqa: E402

HEIGHTS = RackDiagram.SUPPORTED_RACK_HEIGHTS
KEYS = list(BUILTIN_DEVICES)


class TestSequencer:
    def test_library_order_matches_catalog(self):
        assert [k for k, _ in library_sequence()] == KEYS

    def test_first_rack_starts_in_library_order(self):
        rack_a, _ = fill_rack_pair(42)
        assert [(p["key"], p["u_position"]) for p in rack_a[:4]] == [
            ("supermicro_gen5_cbox", 1),
            ("hpe_genoa_cbox", 2),
            ("hpe_icelake", 3),
            ("dell_icelake", 5),
        ]

    @pytest.mark.parametrize("height_u", HEIGHTS)
    def test_both_racks_are_full_and_contiguous(self, height_u):
        for rack in fill_rack_pair(height_u):
            next_u = 1
            for p in rack:
                assert p["u_position"] == next_u
                next_u += p["height_u"]
            assert next_u - 1 == height_u

    @pytest.mark.parametrize("height_u", HEIGHTS)
    def test_every_device_appears_across_the_pair(self, height_u):
        rack_a, rack_b = fill_rack_pair(height_u)
        assert {p["key"] for p in rack_a + rack_b} == set(KEYS)
        assert len({p["key"] for p in rack_a}) == len(rack_a)

    @pytest.mark.parametrize("height_u", HEIGHTS)
    def test_second_rack_continues_then_wraps(self, height_u):
        rack_a, rack_b = fill_rack_pair(height_u)
        used = {p["key"] for p in rack_a}
        leftover = [k for k in KEYS if k not in used]
        assert [p["key"] for p in rack_b[: len(leftover)]] == leftover
        assert rack_b[len(leftover)]["key"] == KEYS[0]

    def test_reverse_order_when_library_fits_one_rack(self):
        lib = {k: dict(v) for k, v in list(BUILTIN_DEVICES.items())[:3]}
        from utils import rack_validation as rv

        original = rv.BUILTIN_DEVICES
        try:
            rv.BUILTIN_DEVICES = lib
            rack_a, rack_b = rv.fill_rack_pair(42)
        finally:
            rv.BUILTIN_DEVICES = original
        assert [p["key"] for p in rack_a] == list(lib)
        assert [p["key"] for p in rack_b] == list(reversed(list(lib)))

    def test_milan_eboxes_take_two_units(self):
        rack_a, rack_b = fill_rack_pair(52)
        milan = [p for p in rack_a + rack_b if "milan_ebox" in p["key"]]
        assert milan and all(p["height_u"] == 2 for p in milan)


class TestValidationReport:
    @pytest.mark.parametrize("page_size", ["A4", "Letter"])
    def test_every_rack_fits_on_its_heading_page(self, tmp_path, page_size):
        import generate_rack_validation_report as gen

        manifest = gen.generate(tmp_path, page_size=page_size)
        assert len(manifest["racks"]) == 2 * len(HEIGHTS)
        pitches = {round(r["u_height_pt"], 6) for r in manifest["racks"]}
        assert len(pitches) == 1, "every rack in one report shares one scale"
        for r in manifest["racks"]:
            assert r["heading_page"] == r["diagram_page"], r["name"]
            assert sum(d["u_height"] for d in r["devices"]) == r["height_u"]
        assert Path(manifest["pdf"]).stat().st_size > 0
        data = json.loads(Path(manifest["json"]).read_text())
        assert data["racks"][0]["name"] == "VAL-42U-A"

    def test_generic_placeholder_counts_as_fallback(self, tmp_path):
        import generate_rack_validation_report as gen

        manifest = gen.generate(tmp_path, page_size="A4", heights=[42])
        devices = [d for r in manifest["racks"] for d in r["devices"]]
        ceres_4u = [d for d in devices if d["model"] == "ceres_4u"]
        assert ceres_4u and all(d["image_fallback"] for d in ceres_4u)
        assert not any(d["image_fallback"] for d in devices if d["model"] == "ceres_v2")

        summary = pymupdf.open(manifest["pdf"])[0].get_text()
        assert "ceres_4u" in summary

    def test_build_validation_racks_names_and_status(self):
        racks, status = build_validation_racks([42])
        assert [r["name"] for r in racks] == ["VAL-42U-A", "VAL-42U-B"]
        cbox_counts = {len(v) for v in status["cnodes_by_cbox"].values()}
        assert cbox_counts == {1, 2, 3, 4}
        assert {c["status"] for v in status["cnodes_by_cbox"].values() for c in v} >= {"ACTIVE", "INACTIVE", "STANDBY"}
        assert set(status["switch_in_inventory"].values()) == {"ACTIVE", "OFFLINE"}
