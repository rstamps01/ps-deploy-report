"""Rack heights 42-52U: geometry, scale, labels, indicators and artwork (RACK-1, RACK-3)."""

import json
import sys
from pathlib import Path

import pytest
from reportlab.graphics.shapes import Circle, Image as GraphicsImage, String
from reportlab.lib.pagesizes import A4, letter

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from hardware_library import BUILTIN_DEVICES, get_device_height  # noqa: E402
from rack_diagram import HARDWARE_IMAGE_DIR, RackDiagram, blank_edge_bounds  # noqa: E402
from utils.rack_validation import build_rack_spec, empty_status_map, fill_rack_pair  # noqa: E402

HEIGHTS = RackDiagram.SUPPORTED_RACK_HEIGHTS
# Report frame sizes (points) for the default margins: A4 and Letter.
FRAMES = {"A4": (451.28, 698.0), "Letter": (468.0, 648.0)}
LEGACY_42U_PT = {"A4": 13.343, "Letter": 12.214}
NO_ARTWORK = {"ceres_4u"}  # catalogued without an image; renders the generic 2U placeholder


def _frame(page: str):
    from report_builder import VastReportBuilder

    rb = VastReportBuilder()
    c = rb.config
    size = A4 if page == "A4" else letter
    rb.brand_compliance.create_vast_page_template(
        {"timestamp": "t", "completeness": 0, "mgmt_vip": "x"},
        page_size=size,
        margins={
            "margin_left": c.margin_left,
            "margin_right": c.margin_right,
            "margin_top": c.margin_top,
            "margin_bottom": c.margin_bottom,
        },
    )
    em = rb.brand_compliance.effective_margins
    return size[0] - em["left"] - em["right"], size[1] - em["top"] - em["bottom"]


def _render(height_u, rack="A", page="A4", pitch=None):
    fw, fh = _frame(page)
    pitch = pitch or RackDiagram.report_u_height(fw, fh, [height_u])
    rd = RackDiagram(
        page_width=fw,
        page_height=RackDiagram.report_drawing_height(fh),
        rack_height_u=height_u,
        u_height_pt=pitch,
        show_rack_label=False,
    )
    status = empty_status_map()
    placements = fill_rack_pair(height_u)[0 if rack == "A" else 1]
    spec = build_rack_spec(f"T-{height_u}{rack}", height_u, placements, status, {})
    drawing, _ = rd.generate_rack_diagram(
        spec["cboxes"],
        spec["dboxes"],
        spec["switches"],
        rack_name=spec["name"],
        eboxes=spec["eboxes"],
        node_status_map=status,
    )
    return rd, drawing, placements, status


class TestSupportedHeights:
    def test_supported_heights(self):
        assert HEIGHTS == (42, 45, 48, 50, 52)
        for h in HEIGHTS:
            assert RackDiagram.RACK_HEIGHTS[h] == pytest.approx(h * 1.75)

    @pytest.mark.parametrize(
        "requested,drawn",
        [(None, 42), (42, 42), (45, 45), (44, 45), (47, 48), (49, 50), (51, 52), (60, 52), (20, 42), ("bad", 42)],
    )
    def test_normalize_rounds_up(self, requested, drawn):
        assert RackDiagram.normalize_rack_height(requested) == drawn

    def test_device_above_u42_in_45u_rack_is_drawn(self):
        """Regression: a 45U rack used to fall back to 42U and drop devices above U42."""
        rd = RackDiagram(rack_height_u=45)
        rd.generate_rack_diagram([{"id": 1, "model": "supermicro_gen5_cbox", "rack_unit": "U44", "name": "c"}], [])
        assert [d["u_position"] for d in rd.placed_devices] == [44]

    def test_device_crossing_top_is_skipped(self):
        rd = RackDiagram(rack_height_u=45)
        rd.generate_rack_diagram([{"id": 1, "model": "hpe_icelake", "rack_unit": "U45", "name": "c"}], [])
        assert rd.placed_devices == []

    def test_top_units_render(self):
        for h in HEIGHTS:
            rd = RackDiagram(rack_height_u=h)
            rd.generate_rack_diagram(
                [
                    {"id": 1, "model": "supermicro_gen5_cbox", "rack_unit": f"U{h}", "name": "a"},
                    {"id": 2, "model": "hpe_icelake", "rack_unit": f"U{h - 2}", "name": "b"},
                ],
                [],
            )
            assert sorted(d["u_position"] for d in rd.placed_devices) == [h - 2, h]


class TestScale:
    @pytest.mark.parametrize("page", ["A4", "Letter"])
    def test_42u_only_report_keeps_todays_pitch(self, page):
        fw, fh = _frame(page)
        assert RackDiagram.report_u_height(fw, fh, [42, 42]) == pytest.approx(LEGACY_42U_PT[page], abs=0.01)

    @pytest.mark.parametrize("page", ["A4", "Letter"])
    def test_pitch_by_height(self, page):
        fw, fh = _frame(page)
        legacy = RackDiagram.report_u_height(fw, fh, [42])
        for h, floor in ((45, 0.999), (48, 0.995), (50, 0.95), (52, 0.92)):
            pitch = RackDiagram.report_u_height(fw, fh, [h])
            assert floor * legacy <= pitch <= legacy + 1e-6, (h, pitch)

    @pytest.mark.parametrize("page", ["A4", "Letter"])
    def test_every_height_fits_drawing(self, page):
        fw, fh = _frame(page)
        pitch = RackDiagram.report_u_height(fw, fh, list(HEIGHTS))
        for h in HEIGHTS:
            rd = RackDiagram(fw, RackDiagram.report_drawing_height(fh), h, u_height_pt=pitch, show_rack_label=False)
            assert rd.u_height == pytest.approx(pitch)
            assert rd.rack_bottom + rd.rack_height <= rd.page_height + 1e-6
            assert rd.page_height <= RackDiagram.report_drawing_height(fh) + 1e-6

    def test_mixed_report_shares_one_scale(self):
        fw, fh = _frame("A4")
        pitch = RackDiagram.report_u_height(fw, fh, [42, 52])
        widths = {
            round(RackDiagram(fw, fh, h, u_height_pt=pitch, show_rack_label=False).rack_width, 6) for h in (42, 52)
        }
        assert len(widths) == 1

    def test_oversized_pitch_is_clamped_to_fit(self):
        rd = RackDiagram(page_width=400, page_height=300, rack_height_u=52, u_height_pt=40)
        assert rd.rack_bottom + rd.rack_height <= 300 + 1e-6

    def test_overlays_never_grow_and_pill_fits_1u(self):
        for h in HEIGHTS:
            for page in FRAMES:
                rd, _, _, _ = _render(h, page=page)
                assert rd.overlay_scale <= 1.0
                for d in rd.placed_devices:
                    box = d["indicator_box"]
                    if box and d["u_height"] == 1:
                        assert box[3] <= rd.u_height, (h, page, d["model"])


@pytest.mark.parametrize("height_u", HEIGHTS)
@pytest.mark.parametrize("rack", ["A", "B"])
class TestGeometryContract:
    def test_devices_fill_width_and_stack_without_gaps(self, height_u, rack):
        rd, _, placements, _ = _render(height_u, rack)
        start_x = (rd.page_width - rd.rack_width) / 2
        devices = sorted(rd.placed_devices, key=lambda d: d["u_position"])
        assert len(devices) == len(placements)
        for d in devices:
            assert d["x"] == pytest.approx(start_x)
            assert d["width"] == pytest.approx(rd.rack_width)
            assert d["y"] == pytest.approx(rd.rack_bottom + (d["u_position"] - 1) * rd.u_height)
            assert d["height"] == pytest.approx(d["u_height"] * rd.u_height)
        for below, above in zip(devices, devices[1:]):
            assert below["y"] + below["height"] == pytest.approx(above["y"], abs=0.01)
        assert devices[0]["y"] == pytest.approx(rd.rack_bottom)
        assert devices[-1]["y"] + devices[-1]["height"] == pytest.approx(rd.rack_bottom + rd.rack_height, abs=0.01)

    def test_device_images_span_the_slot(self, height_u, rack):
        rd, drawing, _, _ = _render(height_u, rack)
        images = [s for s in drawing.contents if isinstance(s, GraphicsImage)]
        assert images
        for img in images:
            assert img.width == pytest.approx(rd.rack_width)

    def test_every_u_is_labelled(self, height_u, rack):
        rd, drawing, _, _ = _render(height_u, rack)
        labels = {s.text: s for s in drawing.contents if isinstance(s, String) and s.text.startswith("U")}
        expected = {f"U{u}" for u in range(1, height_u + 1)}
        assert expected <= set(labels)
        for u in range(1, height_u + 1):
            centre = rd.rack_bottom + (u - 0.5) * rd.u_height
            label = labels[f"U{u}"]
            assert abs(label.y + label.fontSize * 0.35 - centre) < 0.5

    def test_every_device_has_one_right_label_and_none_overlap(self, height_u, rack):
        rd, drawing, _, _ = _render(height_u, rack)
        device_labels = [d["label"] for d in rd.placed_devices]
        texts = [s.text for s in drawing.contents if isinstance(s, String)]
        for label in device_labels:
            assert texts.count(label) == 1, label
        ys = sorted(d["label_y"] for d in rd.placed_devices)
        font = rd.placed_devices[0]["label_font"]
        assert all(b - a >= font for a, b in zip(ys, ys[1:]))
        assert all(0 <= y <= rd.page_height for y in ys)

    def test_indicators_match_status_map(self, height_u, rack):
        rd, _, _, status = _render(height_u, rack)
        colours = {"ACTIVE": "0x06d69f", "INACTIVE": "0xff9800", "MGMT": "0x1a6fb5"}

        def cnode_colour(c):
            if c["status"] == "ACTIVE":
                return colours["ACTIVE"]
            return colours["MGMT"] if c.get("is_mgmt") else colours["INACTIVE"]

        for d in rd.placed_devices:
            got = [(i["shape"], i["color"].lower()) for i in d["indicators"]]
            n = d["id"]
            if d["type"] == "cbox":
                want = [("dot", cnode_colour(c)) for c in status["cnodes_by_cbox"][n]]
            elif d["type"] == "dbox":
                want = [("square", colours[x["status"]]) for x in status["dnodes_by_dbox"][n]]
            elif d["type"] == "ebox":
                want = [("dot", cnode_colour(status["cnode_by_ebox"][n]))]
                want += [("square", colours[x["status"]]) for x in status["dnodes_by_ebox"][n]]
            else:
                state = status["switch_in_inventory"][d["label"]]
                want = [("dot", colours["ACTIVE"] if state == "ACTIVE" else colours["INACTIVE"])]
            assert got == want, d["label"]
            box = d["indicator_box"]
            assert d["y"] <= box[1] and box[1] + box[3] <= d["y"] + d["height"] + 1e-6

    def test_legend_drawn_once(self, height_u, rack):
        _, drawing, _, _ = _render(height_u, rack)
        assert sum(1 for s in drawing.contents if isinstance(s, String) and s.text == "Status Indicators") == 1


class TestDeviceMatrix:
    @pytest.mark.parametrize("height_u", HEIGHTS)
    def test_every_library_device_renders_with_artwork(self, height_u):
        rd = RackDiagram(rack_height_u=height_u)
        for key, entry in BUILTIN_DEVICES.items():
            kind = entry["type"]
            device = {"id": 1, "model": key, "hardware_type": key, "rack_unit": "U1", "name": key, "state": "ACTIVE"}
            args = {"cbox": ([device], []), "dbox": ([], [device])}.get(kind, ([], []))
            rd.generate_rack_diagram(
                *args,
                switches=[{**device, "id": key}] if kind == "switch" else None,
                eboxes=[device] if kind == "ebox" else None,
            )
            placed = rd.placed_devices
            assert len(placed) == 1, key
            assert placed[0]["u_height"] == entry["height_u"], key
            if key not in NO_ARTWORK:
                assert placed[0]["image"] and "generic" not in placed[0]["image"], key

    def test_user_library_device_renders_at_every_height(self, tmp_path):
        from PIL import Image

        img_dir = tmp_path / "images"
        img_dir.mkdir()
        Image.new("RGB", (626, 58), (40, 40, 40)).save(img_dir / "acme_2u_box_2u.png")
        lib = {"acme_2u_box": {"type": "cbox", "height_u": 2, "image_filename": "acme_2u_box_2u.png"}}
        lib_path = tmp_path / "device_library.json"
        lib_path.write_text(json.dumps(lib))
        for h in HEIGHTS:
            rd = RackDiagram(rack_height_u=h, library_path=str(lib_path), user_images_dir=str(img_dir))
            rd.generate_rack_diagram([{"id": 1, "model": "acme_2u_box", "rack_unit": f"U{h - 1}", "name": "x"}], [])
            assert rd.placed_devices[0]["image"] == "acme_2u_box_2u.png"
            assert rd.placed_devices[0]["u_height"] == 2


class TestArtwork:
    """Images are stretched to fill their slot, so the artwork itself must suit it."""

    def _images(self):
        seen = {}
        for key, entry in BUILTIN_DEVICES.items():
            name = entry.get("image_filename")
            if name and name not in seen:
                seen[name] = (key, entry["height_u"])
        return seen

    def test_aspect_ratio_close_to_slot(self):
        from PIL import Image

        for name, (key, height_u) in self._images().items():
            w, h = Image.open(HARDWARE_IMAGE_DIR / name).size
            ideal = 19 / (1.75 * height_u)
            assert abs(w / h - ideal) / ideal <= 0.15, f"{name}: {w}x{h} is far from {height_u}U ({key})"

    def test_trimmed_artwork_has_no_blank_edges(self):
        from PIL import Image

        from rack_diagram import trimmed_device_image

        for name in self._images():
            trimmed = trimmed_device_image(HARDWARE_IMAGE_DIR / name)
            im = Image.open(trimmed) if isinstance(trimmed, str) else trimmed
            assert blank_edge_bounds(im) == (0, 0, im.size[0], im.size[1]), name

    def test_blank_edge_bounds_crops_padding(self):
        from PIL import Image

        im = Image.new("RGBA", (100, 20), (0, 0, 0, 0))
        im.paste((50, 50, 50, 255), (0, 2, 100, 18))
        assert blank_edge_bounds(im) == (0, 2, 100, 18)

    def test_library_heights_resolve_from_catalog(self):
        for key, entry in BUILTIN_DEVICES.items():
            assert get_device_height(key) == entry["height_u"], key
