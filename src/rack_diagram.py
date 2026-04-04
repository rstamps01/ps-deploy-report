"""
Rack Diagram Generator for VAST As-Built Reports

This module generates visual rack diagrams showing physical hardware placement
in 42U data center racks with proper scaling, positioning, and labeling.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, cast

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Group, Image as GraphicsImage, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Image as RLImage
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

from utils import get_bundle_dir
from hardware_library import BUILTIN_DEVICES, get_device_height, build_image_map

HARDWARE_IMAGE_DIR = get_bundle_dir() / "assets" / "hardware_images"

_unrecognized_models: Set[str] = set()


def get_unrecognized_models() -> Set[str]:
    """Return the set of model identifiers encountered but not matched."""
    return set(_unrecognized_models)


def _load_user_library(library_path: Optional[str]) -> Dict[str, Any]:
    if not library_path:
        return {}
    try:
        with open(library_path, "r", encoding="utf-8") as f:
            return cast(Dict[str, Any], json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


class RackDiagram:
    """Generate visual rack diagrams for VAST hardware deployments."""

    # Physical rack dimensions (in inches)
    RACK_INTERNAL_WIDTH = 19.0  # inches
    RACK_EXTERNAL_HEIGHT = 79.0  # inches
    RACK_EXTERNAL_WIDTH = 24.0  # inches
    U_HEIGHT = 1.75  # inches per U

    # Rack height configurations (internal height in inches)
    # Standard 42U rack: 42 * 1.75 = 73.5 inches
    # Standard 48U rack: 48 * 1.75 = 84.0 inches
    RACK_HEIGHTS = {
        42: 73.5,  # 42U rack internal height
        48: 84.0,  # 48U rack internal height
    }

    DEFAULT_RACK_HEIGHT = 42  # Default to 42U for backward compatibility

    # VAST brand colors
    BRAND_DARK = HexColor("#2F2042")
    BRAND_PRIMARY = HexColor("#1BA3D1")
    CBOX_COLOR = HexColor("#1BA3D1")  # Blue for compute
    DBOX_COLOR = HexColor("#7B68A6")  # Purple for storage
    SWITCH_COLOR = HexColor("#808080")  # Gray for switches
    STATUS_ACTIVE = HexColor("#06d69f")  # Vivid green for active status
    STATUS_INACTIVE = HexColor("#FF9800")  # Orange for inactive
    STATUS_MGMT = HexColor("#1A6FB5")  # Blue for management CNode (VMS)
    EMPTY_RACK_COLOR = HexColor("#F2F2F7")  # Light gray for empty space

    # Label sizing
    LABEL_MAX_HEIGHT = 1.5  # inches (less than 1U)
    LABEL_FONT_SIZE = 8  # points

    def __init__(
        self,
        page_width: float = 7.27 * inch,
        page_height: float = 8.5 * inch,
        rack_height_u: int = None,
        library_path: Optional[str] = None,
        user_images_dir: Optional[str] = None,
    ):
        """
        Initialize rack diagram generator.

        Args:
            page_width: Available page width in points (default 7.5" for content area)
            page_height: Available page height in points (default 8.5" to maximize space)
            rack_height_u: Number of rack units (U) for this rack (42, 48, etc.).
                         Defaults to 42U for backward compatibility.
            library_path: Path to user device_library.json file.
            user_images_dir: Path to directory with user-uploaded hardware images.
        """
        self.page_width = page_width
        self.page_height = page_height
        self.library_path = library_path
        self.user_images_dir = user_images_dir

        if rack_height_u is None:
            rack_height_u = self.DEFAULT_RACK_HEIGHT

        # Validate rack height
        if rack_height_u not in self.RACK_HEIGHTS:
            logger.warning(
                f"Unsupported rack height {rack_height_u}U, defaulting to {self.DEFAULT_RACK_HEIGHT}U. "
                f"Supported heights: {list(self.RACK_HEIGHTS.keys())}"
            )
            rack_height_u = self.DEFAULT_RACK_HEIGHT

        self.rack_height_u = rack_height_u
        self.rack_internal_height = self.RACK_HEIGHTS[rack_height_u]

        # Calculate scaling to fit rack on page with margins
        self.margin = 0.3 * inch  # Reduced margins for larger diagram
        self.available_width = page_width - (2 * self.margin)
        self.available_height = page_height - (0.5 * inch)  # Minimal space for labels

        # Calculate scale factor to fit rack on page
        # Use internal dimensions for the main rack area
        width_scale = self.available_width / (self.RACK_INTERNAL_WIDTH * inch)
        height_scale = self.available_height / (self.rack_internal_height * inch)
        self.scale = min(width_scale, height_scale) * 0.95  # 95% to maximize rack size while ensuring it fits

        # Scaled dimensions
        self.rack_width = self.RACK_INTERNAL_WIDTH * inch * self.scale
        self.rack_height = self.rack_internal_height * inch * self.scale
        self.u_height = self.U_HEIGHT * inch * self.scale

        logger.info(
            f"Rack diagram initialized: {rack_height_u}U rack, scale={self.scale:.3f}, "
            f"rack_size={self.rack_width:.1f}x{self.rack_height:.1f}pts, "
            f"drawing_size={self.page_width:.1f}x{self.page_height:.1f}pts"
        )

        # Initialize hardware image cache
        self.hardware_images = self._load_hardware_images()

    def _load_hardware_images(self) -> Dict[str, Optional[Path]]:
        """
        Load available hardware images from built-in assets and user library.

        Returns:
            Dictionary mapping model names to image file paths
        """
        # Build image map from centralized hardware library
        image_map = build_image_map(HARDWARE_IMAGE_DIR)

        available_images: Dict[str, Optional[Path]] = {}
        for model, path in image_map.items():
            if path.exists():
                available_images[model] = path
                logger.info(f"Loaded hardware image for {model}: {path}")
            else:
                available_images[model] = None
                logger.debug(f"No image found for {model} at {path}")

        user_lib = _load_user_library(self.library_path)
        if user_lib and self.user_images_dir:
            udir = Path(self.user_images_dir)
            for key, entry in user_lib.items():
                if key in available_images:
                    continue
                fname = entry.get("image_filename")
                if fname:
                    img_path = udir / fname
                    if img_path.exists():
                        available_images[key] = img_path
                        logger.info(f"Loaded user library image for {key}: {img_path}")
                    else:
                        available_images[key] = None
                        logger.debug(f"User library image missing for {key}: {img_path}")
                else:
                    available_images[key] = None

        self._user_library = user_lib
        return available_images

    def _get_hardware_image_path(self, model: str) -> Optional[Path]:
        """
        Get the image path for a hardware model using a three-tier cascade:
        1. Built-in + user library (exact then partial match)
        2. Generic fallback (generic_1u.png / generic_2u.png)

        Unrecognized models are tracked for the Library page.
        """
        model_clean = model.lower().strip()

        if model_clean in self.hardware_images:
            return self.hardware_images[model_clean]

        for key in sorted(self.hardware_images, key=len, reverse=True):
            if key in model_clean:
                return self.hardware_images[key]

        _unrecognized_models.add(model_clean)
        height_u = self._get_device_height_units(model)
        generic = HARDWARE_IMAGE_DIR / f"generic_{height_u}u.png"
        if generic.exists():
            logger.warning(
                f"No image for model '{model}' — using generic {height_u}U placeholder. "
                f"Add this device to the Library to improve diagram accuracy."
            )
            return cast(Optional[Path], generic)

        logger.warning(f"No image found for hardware type: {model}")
        return None

    def _get_device_height_units(self, model: str) -> int:
        """
        Determine the height in rack units (U) for a device based on its model.

        Uses the centralized hardware_library for lookups.
        """
        user_lib = getattr(self, "_user_library", {}) or {}
        height = get_device_height(model, user_lib)

        # Log warning for unknown models (not in library)
        if model and height == 1:
            model_lower = model.lower()
            found = False
            for key in BUILTIN_DEVICES:
                if key in model_lower:
                    found = True
                    break
            if not found and "ebox" not in model_lower and "enclosure" not in model_lower:
                for key in user_lib:
                    if key in model_lower:
                        found = True
                        break
            if not found:
                logger.warning(f"Unknown model '{model}', defaulting to 1U")

        return int(height)

    def _parse_rack_position(self, position: str) -> int:
        """
        Parse rack position string (e.g., "U17", "17") to integer.

        Args:
            position: Rack position string

        Returns:
            Rack unit number (1 to rack_height_u)
        """
        if not position:
            return 0

        # Remove 'U' prefix if present
        pos_str = position.upper().replace("U", "").strip()

        try:
            u_number = int(pos_str)
            if 1 <= u_number <= self.rack_height_u:
                return u_number
            else:
                logger.warning(f"Invalid rack position {position}, must be between U1-U{self.rack_height_u}")
                return 0
        except ValueError:
            logger.warning(f"Could not parse rack position: {position}")
            return 0

    def _create_empty_rack_background(self, drawing: Drawing) -> None:
        """
        Create the empty rack template with U divisions and numbering.

        Args:
            drawing: ReportLab Drawing object to add elements to
        """
        # Starting position (centered horizontally, from bottom)
        start_x = (self.page_width - self.rack_width) / 2
        start_y = self.margin + 0.5 * inch

        # Draw rack frame with posts (darker gray on sides)
        post_width = 0.08 * self.rack_width

        # Left post
        left_post = Rect(
            start_x - post_width,
            start_y,
            post_width,
            self.rack_height,
            strokeColor=self.BRAND_DARK,
            strokeWidth=1,
            fillColor=HexColor("#4A4A4A"),
        )
        drawing.add(left_post)

        # Right post
        right_post = Rect(
            start_x + self.rack_width,
            start_y,
            post_width,
            self.rack_height,
            strokeColor=self.BRAND_DARK,
            strokeWidth=1,
            fillColor=HexColor("#4A4A4A"),
        )
        drawing.add(right_post)

        # Draw main rack frame (inner area)
        rack_frame = Rect(
            start_x,
            start_y,
            self.rack_width,
            self.rack_height,
            strokeColor=self.BRAND_DARK,
            strokeWidth=2,
            fillColor=colors.white,
        )
        drawing.add(rack_frame)

        # Draw U divisions (horizontal lines for each U)
        for u in range(1, self.rack_height_u + 1):  # U1 to U{rack_height_u}
            y_pos = start_y + ((u - 1) * self.u_height)

            # Horizontal line for U division
            u_line = Line(
                start_x,
                y_pos,
                start_x + self.rack_width,
                y_pos,
                strokeColor=self.EMPTY_RACK_COLOR,
                strokeWidth=0.5,
            )
            drawing.add(u_line)

            # U number label on the left side
            if u % 2 == 1:  # Label every other U to avoid crowding
                label_x = start_x - post_width - 0.15 * inch
                label_y = y_pos + (self.u_height / 2) - 3  # Center vertically

                u_label = String(
                    label_x,
                    label_y,
                    f"U{u}",
                    fontSize=7,
                    fillColor=self.BRAND_DARK,
                    textAnchor="end",
                    fontName="Helvetica-Bold",
                )
                drawing.add(u_label)

            # Add mounting holes on left and right (every U)
            hole_radius = 1.5
            hole_color = HexColor("#333333")

            # Left mounting holes
            left_hole = Circle(
                start_x + 0.05 * self.rack_width,
                y_pos + (self.u_height / 2),
                hole_radius,
                fillColor=hole_color,
                strokeColor=self.BRAND_DARK,
                strokeWidth=0.3,
            )
            drawing.add(left_hole)

            # Right mounting holes
            right_hole = Circle(
                start_x + self.rack_width - (0.05 * self.rack_width),
                y_pos + (self.u_height / 2),
                hole_radius,
                fillColor=hole_color,
                strokeColor=self.BRAND_DARK,
                strokeWidth=0.3,
            )
            drawing.add(right_hole)

        # Draw top border line
        top_line = Line(
            start_x,
            start_y + self.rack_height,
            start_x + self.rack_width,
            start_y + self.rack_height,
            strokeColor=self.BRAND_DARK,
            strokeWidth=2,
        )
        drawing.add(top_line)

    def _create_device_representation(
        self,
        drawing: Drawing,
        device_type: str,
        device_id: int,
        u_position: int,
        u_height: int,
        model: str = "",
        status: str = "ACTIVE",
        annotation: str = "",
        label_override: str = "",
        indicators: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        Create a visual representation of a device in the rack.
        Uses actual hardware images if available, otherwise falls back to colored rectangles.

        Args:
            drawing: ReportLab Drawing object
            device_type: Type of device ("cbox", "dbox", "ebox", "switch")
            device_id: Device ID number
            u_position: Base (bottom) U position where device is mounted; device extends upward
            u_height: Height of device in rack units (1U or 2U)
            model: Hardware model name for image lookup
            status: Device status (ACTIVE, OFFLINE, etc.)
            annotation: Optional text rendered below the label (e.g. placement note)
            label_override: Override the default label text
            indicators: List of status indicator specs [{"shape": "dot"|"square", "color": HexColor}]
        """
        start_x = (self.page_width - self.rack_width) / 2
        start_y = self.margin + 0.5 * inch

        device_bottom_u = u_position
        device_y = start_y + ((device_bottom_u - 1) * self.u_height)
        device_height = u_height * self.u_height

        if device_type.lower() == "cbox":
            fill_color = self.CBOX_COLOR
            label_prefix = "CBox"
        elif device_type.lower() == "dbox":
            fill_color = self.DBOX_COLOR
            label_prefix = "DBox"
        elif device_type.lower() == "ebox":
            fill_color = self.DBOX_COLOR
            label_prefix = "EBox"
        elif device_type.lower() == "switch":
            fill_color = self.SWITCH_COLOR
            label_prefix = "Switch"
        else:
            fill_color = colors.gray
            label_prefix = "Device"

        image_path = self._get_hardware_image_path(model) if model else None

        if image_path and image_path.exists():
            try:
                hw_image = GraphicsImage(
                    start_x,
                    device_y,
                    self.rack_width,
                    device_height,
                    str(image_path),
                )
                drawing.add(hw_image)
                logger.debug(f"Using hardware image for {device_type}-{device_id}: {image_path}")
            except Exception as e:
                logger.warning(f"Failed to load hardware image {image_path}: {e}, using fallback")
                self._draw_fallback_device(drawing, start_x, device_y, device_height, fill_color)
        else:
            self._draw_fallback_device(drawing, start_x, device_y, device_height, fill_color)

        if indicators is not None:
            self._draw_status_indicators(drawing, indicators, start_x, device_y, device_height)

        # Add label outside rack with connector line
        post_width = 0.08 * self.rack_width
        label_x = start_x + self.rack_width + post_width + 0.15 * inch
        label_y = device_y + (device_height / 2) - 3
        label_text = label_override if label_override else f"{label_prefix}-{device_id}"

        # Connector line from device to label
        line_start_x = start_x + self.rack_width
        line_start_y = device_y + (device_height / 2)
        line_end_x = label_x - 0.05 * inch

        connector_line = Line(
            line_start_x,
            line_start_y,
            line_end_x,
            label_y + 3,
            strokeColor=self.BRAND_DARK,
            strokeWidth=0.5,
            strokeDashArray=[2, 2],
        )
        drawing.add(connector_line)

        # Label text
        label = String(
            label_x,
            label_y,
            label_text,
            fontSize=self.LABEL_FONT_SIZE,
            fillColor=self.BRAND_DARK,
            textAnchor="start",
        )
        drawing.add(label)

        if annotation:
            ann_label = String(
                label_x,
                label_y - self.LABEL_FONT_SIZE,
                annotation,
                fontSize=self.LABEL_FONT_SIZE - 2,
                fillColor=colors.HexColor("#B85C00"),
                textAnchor="start",
            )
            drawing.add(ann_label)

    def _draw_fallback_device(
        self,
        drawing: Drawing,
        start_x: float,
        device_y: float,
        device_height: float,
        fill_color: HexColor,
    ) -> None:
        """
        Draw fallback device representation (colored rectangle with icon).

        Args:
            drawing: ReportLab Drawing object
            start_x: X position of rack start
            device_y: Y position of device
            device_height: Height of device in points
            fill_color: Color for device background
        """
        # Draw device rectangle
        device_rect = Rect(
            start_x + 2,
            device_y,
            self.rack_width - 4,
            device_height - 1,
            strokeColor=self.BRAND_DARK,
            strokeWidth=1,
            fillColor=fill_color,
            fillOpacity=0.3,
        )
        drawing.add(device_rect)

        # Add simple text icon
        icon_x = start_x + (self.rack_width / 2)
        icon_y = device_y + (device_height / 2) - 4

        device_icon = String(
            icon_x,
            icon_y,
            "HW",
            fontSize=8,
            fillColor=colors.white,
            textAnchor="middle",
            fontName="Helvetica-Bold",
        )
        drawing.add(device_icon)

    def _draw_status_indicators(
        self,
        drawing: Drawing,
        indicators: List[Dict[str, Any]],
        start_x: float,
        device_y: float,
        device_height: float,
    ) -> None:
        """Draw a row of status indicator shapes (circles/squares) at the left edge of a device.

        Args:
            drawing: ReportLab Drawing object
            indicators: List of dicts with keys "shape" ("dot"|"square") and "color" (HexColor)
            start_x: X position of the rack left edge
            device_y: Y position of device bottom
            device_height: Height of device slot in points
        """
        if not indicators:
            return
        radius = 2.5
        spacing = 2
        pad_x = 3
        pad_y = 2.5
        total_width = len(indicators) * (radius * 2) + (len(indicators) - 1) * spacing
        cx_start = start_x + 8 + 0.25 * inch - total_width / 2 + radius
        cy = device_y + (device_height / 2)

        bg_w = total_width + pad_x * 2
        bg_h = radius * 2 + pad_y * 2
        bg_r = bg_h / 2
        bg = Rect(
            cx_start - radius - pad_x,
            cy - radius - pad_y,
            bg_w,
            bg_h,
            fillColor=HexColor("#1a1a1a"),
            fillOpacity=0.75,
            strokeWidth=0,
            rx=bg_r,
            ry=bg_r,
        )
        drawing.add(bg)

        cx = cx_start
        for ind in indicators:
            col = ind.get("color", self.STATUS_ACTIVE)
            if ind.get("shape") == "square":
                side = radius * 1.6
                sq = Rect(
                    cx - side / 2,
                    cy - side / 2,
                    side,
                    side,
                    fillColor=col,
                    strokeWidth=0,
                )
                drawing.add(sq)
            else:
                dot = Circle(
                    cx,
                    cy,
                    radius,
                    fillColor=col,
                    strokeWidth=0,
                )
                drawing.add(dot)
            cx += radius * 2 + spacing

    def _draw_status_legend(
        self,
        drawing: Drawing,
    ) -> None:
        """Draw a status indicator legend tile to the left of the rack diagram, centered vertically."""
        rack_left = (self.page_width - self.rack_width) / 2
        start_y = self.margin + 0.5 * inch

        title_fs = 7
        row_fs = 6.5
        dot_r = 2.5
        sq_side = 4
        line_h = 11
        legend_w = 105
        legend_h = 8 * line_h + 6

        legend_x_right = rack_left - 10 - 1 * inch
        legend_x = legend_x_right - legend_w
        legend_y = start_y + (self.rack_height - legend_h) / 2 + legend_h

        bg = Rect(
            legend_x - 4,
            legend_y - legend_h,
            legend_w,
            legend_h,
            fillColor=HexColor("#FAFAFA"),
            strokeColor=HexColor("#CCCCCC"),
            strokeWidth=0.5,
            rx=4,
            ry=4,
        )
        drawing.add(bg)

        cy = legend_y - 10
        drawing.add(
            String(
                legend_x,
                cy,
                "Status Indicators",
                fontSize=title_fs,
                fillColor=self.BRAND_DARK,
                fontName="Helvetica-Bold",
            )
        )
        cy -= 2
        drawing.add(
            Line(legend_x - 2, cy, legend_x + legend_w - 8, cy, strokeColor=HexColor("#CCCCCC"), strokeWidth=0.4)
        )

        rows = [
            ("dot", self.STATUS_ACTIVE, "Active"),
            ("dot", self.STATUS_INACTIVE, "Inactive"),
            ("dot", self.STATUS_MGMT, "Management (VMS)"),
            ("square", self.STATUS_ACTIVE, "Active"),
            ("square", self.STATUS_INACTIVE, "Inactive"),
        ]

        labels_section = [
            (True, "CNode / Switch"),
            (False, None),
            (False, None),
            (True, "DNode"),
            (False, None),
        ]

        for i, ((shape, col, label), (is_header, header_text)) in enumerate(zip(rows, labels_section)):
            if is_header:
                cy -= line_h
                drawing.add(
                    String(
                        legend_x + 2,
                        cy,
                        str(header_text),
                        fontSize=6,
                        fillColor=HexColor("#666666"),
                        fontName="Helvetica-Oblique",
                    )
                )

            cy -= line_h
            ix = legend_x + 6
            if shape == "dot":
                drawing.add(Circle(ix, cy + 2, dot_r, fillColor=col, strokeColor=self.BRAND_DARK, strokeWidth=0.3))
            else:
                drawing.add(
                    Rect(
                        ix - sq_side / 2,
                        cy + 2 - sq_side / 2,
                        sq_side,
                        sq_side,
                        fillColor=col,
                        strokeColor=self.BRAND_DARK,
                        strokeWidth=0.3,
                    )
                )
            drawing.add(
                String(ix + 8, cy - 1, label, fontSize=row_fs, fillColor=HexColor("#333333"), fontName="Helvetica")
            )

    def _gather_device_boundaries(
        self,
        cboxes: List[Dict[str, Any]],
        dboxes: List[Dict[str, Any]],
        eboxes: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Dict[str, Optional[int]]]:
        """
        Parse CBox/DBox/EBox positions and return boundary U values needed for placement.

        Returns dict with keys: lowest_cbox_bottom, highest_cbox_top,
        highest_dbox_top, lowest_dbox_bottom, highest_ebox_top, lowest_ebox_bottom.
        Returns None only when CBox, DBox, and EBox data are all missing.
        """
        eboxes = eboxes or []
        cbox_tops = []
        cbox_bottoms = []
        for cbox in cboxes:
            u_pos = self._parse_rack_position(cbox.get("rack_unit", ""))
            if u_pos > 0:
                model = cbox.get("model", "")
                u_height = self._get_device_height_units(model)
                cbox_tops.append(u_pos + u_height - 1)
                cbox_bottoms.append(u_pos)

        dbox_tops = []
        dbox_bottoms = []
        for dbox in dboxes:
            u_pos = self._parse_rack_position(dbox.get("rack_unit", ""))
            if u_pos > 0:
                hw_type = dbox.get("hardware_type", dbox.get("model", ""))
                u_height = self._get_device_height_units(hw_type)
                dbox_tops.append(u_pos + u_height - 1)
                dbox_bottoms.append(u_pos)

        ebox_tops = []
        ebox_bottoms = []
        for ebox in eboxes:
            u_pos = self._parse_rack_position(ebox.get("rack_unit", ""))
            if u_pos > 0:
                model = ebox.get("model", ebox.get("hardware_type", "ebox"))
                u_height = self._get_device_height_units(model)
                ebox_tops.append(u_pos + u_height - 1)
                ebox_bottoms.append(u_pos)

        if not cbox_tops and not dbox_tops and not ebox_tops:
            logger.warning("Cannot calculate switch positions: no CBox, DBox, or EBox position data")
            return None

        return {
            "highest_cbox_top": max(cbox_tops) if cbox_tops else None,
            "lowest_cbox_bottom": min(cbox_bottoms) if cbox_bottoms else None,
            "highest_dbox_top": max(dbox_tops) if dbox_tops else None,
            "lowest_dbox_bottom": min(dbox_bottoms) if dbox_bottoms else None,
            "highest_ebox_top": max(ebox_tops) if ebox_tops else None,
            "lowest_ebox_bottom": min(ebox_bottoms) if ebox_bottoms else None,
        }

    @staticmethod
    def _total_switch_span(num_switches: int, switch_height: int) -> int:
        """Total U needed for *num_switches* stacked with 1U gaps between them."""
        return num_switches * switch_height + (num_switches - 1)

    def _try_center_placement(
        self,
        lowest_cbox_bottom: int,
        highest_dbox_top: int,
        switch_height: int,
        num_switches: int = 2,
    ) -> List[int]:
        """Strategy A: place switches centered in the gap between CBoxes and DBoxes."""
        gap_top = lowest_cbox_bottom - 1
        gap_bottom = highest_dbox_top + 1

        if gap_top < gap_bottom:
            logger.info("Strategy A (center): No gap between CBoxes and DBoxes")
            return []

        gap_size = gap_top - gap_bottom + 1
        needed = self._total_switch_span(num_switches, switch_height)
        logger.info(f"Strategy A (center): gap={gap_size}U (U{gap_bottom}–U{gap_top}), need {needed}U")

        if gap_size < needed:
            logger.info(f"Strategy A (center): gap {gap_size}U too small for {num_switches}x {switch_height}U switches")
            return []

        start = gap_bottom + (gap_size - needed) // 2
        positions = []
        for i in range(num_switches):
            positions.append(start + i * (switch_height + 1))
        logger.info(f"Strategy A (center): placed {num_switches} switches at U{positions}")
        return positions

    def _try_above_placement(
        self,
        highest_device_top: int,
        switch_height: int,
        rack_height: int,
        num_switches: int = 2,
    ) -> List[int]:
        """Strategy B: stack switches above the topmost device."""
        positions = []
        base = highest_device_top + 2
        for i in range(num_switches):
            sw_base = base + i * (switch_height + 1)
            positions.append(sw_base)

        top_u = positions[-1] + switch_height - 1
        if top_u > rack_height:
            logger.info(f"Strategy B (above): top switch reaches U{top_u}, exceeds rack height {rack_height}U")
            return []

        logger.info(f"Strategy B (above): placed {num_switches} switches at U{positions}")
        return positions

    def _try_below_placement(
        self,
        lowest_device_bottom: int,
        switch_height: int,
        num_switches: int = 2,
    ) -> List[int]:
        """Strategy C: stack switches below the bottommost device."""
        positions = []
        for i in range(num_switches):
            sw_top = lowest_device_bottom - 2 - i * (switch_height + 1)
            sw_base = sw_top - switch_height + 1
            positions.append(sw_base)

        if positions[-1] < 1:
            logger.info(f"Strategy C (below): lowest switch base U{positions[-1]} below rack floor")
            return []

        positions.reverse()
        logger.info(f"Strategy C (below): placed {num_switches} switches at U{positions}")
        return positions

    def _calculate_switch_positions(
        self,
        cboxes: List[Dict[str, Any]],
        dboxes: List[Dict[str, Any]],
        num_switches: int,
        switches: Optional[List[Dict[str, Any]]] = None,
        rack_height: Optional[int] = None,
        eboxes: Optional[List[Dict[str, Any]]] = None,
    ) -> List[int]:
        """
        Calculate optimal switch positions using cascading placement strategies.

        For ebox clusters: tries above ebox hardware then below ebox hardware first.
        Then: A) Center gap between CBoxes and DBoxes, B) Above top CBox, C) Below bottom DBox.

        Args:
            cboxes: List of CBox device dictionaries
            dboxes: List of DBox device dictionaries
            num_switches: Number of switches to place
            switches: Optional list of switch dictionaries to determine switch height
            rack_height: Rack height in U (defaults to self.rack_height_u)
            eboxes: Optional list of EBox device dictionaries (for ebox clusters)

        Returns:
            List of U positions (base U) for switches, or empty list if all strategies fail
        """
        if num_switches < 1:
            return []

        eboxes = eboxes or []
        switch_height = 1
        if switches and len(switches) > 0:
            first_switch_model = switches[0].get("model", "")
            switch_height = self._get_device_height_units(first_switch_model)
            logger.info(f"Switch height determined: {switch_height}U (model: {first_switch_model})")

        bounds = self._gather_device_boundaries(cboxes, dboxes, eboxes)
        if bounds is None:
            return []

        effective_rack_height = rack_height or self.rack_height_u

        has_ebox = bounds.get("highest_ebox_top") is not None
        has_cbox = bounds["lowest_cbox_bottom"] is not None
        has_dbox = bounds["highest_dbox_top"] is not None

        # EBox cluster: try above ebox then below ebox first
        if has_ebox:
            positions = self._try_above_placement(
                bounds["highest_ebox_top"],
                switch_height,
                effective_rack_height,
                num_switches,
            )
            if positions:
                logger.info("Using switch placement: above EBox hardware")
                return positions
            positions = self._try_below_placement(
                bounds["lowest_ebox_bottom"],
                switch_height,
                num_switches,
            )
            if positions:
                logger.info("Using switch placement: below EBox hardware")
                return positions

        # Strategy A: center gap (requires both CBox and DBox)
        if has_cbox and has_dbox:
            positions = self._try_center_placement(
                bounds["lowest_cbox_bottom"],
                bounds["highest_dbox_top"],
                switch_height,
                num_switches,
            )
            if positions:
                return positions

        # Strategy B: above top CBox (requires CBox data)
        if has_cbox:
            positions = self._try_above_placement(
                bounds["highest_cbox_top"],
                switch_height,
                effective_rack_height,
                num_switches,
            )
            if positions:
                return positions

        # Strategy C: below bottom DBox (requires DBox data)
        if has_dbox:
            positions = self._try_below_placement(
                bounds["lowest_dbox_bottom"],
                switch_height,
                num_switches,
            )
            if positions:
                return positions

        logger.warning(
            "All auto switch placement strategies exhausted — "
            "switches will not appear in the rack diagram. Use Manual placement."
        )
        return []

    def generate_rack_diagram(
        self,
        cboxes: List[Dict[str, Any]],
        dboxes: List[Dict[str, Any]],
        switches: Optional[List[Dict[str, Any]]] = None,
        rack_name: Optional[str] = None,
        eboxes: Optional[List[Dict[str, Any]]] = None,
        node_status_map: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Drawing, Dict[int, int]]:
        """
        Generate a complete rack diagram with all devices.

        For ebox clusters, pass eboxes (with ebox U height); dboxes may be empty
        so that Physical Rack Layout uses ebox positions only.

        Args:
            cboxes: List of CBox device dictionaries with 'id', 'model', 'rack_unit', 'state'
            dboxes: List of DBox device dictionaries with 'id', 'model', 'rack_unit', 'state'
            switches: Optional list of switch dictionaries with 'id', 'model', 'state'
            rack_name: Optional rack name to display on the diagram
            eboxes: Optional list of EBox device dictionaries (use ebox U height in diagram)
            node_status_map: Optional dict with CNode/DNode status data for indicators

        Returns:
            Tuple of:
                - ReportLab Drawing object containing the complete rack diagram
                - Dictionary mapping switch numbers to calculated U positions
        """
        eboxes = eboxes or []
        nsm = node_status_map or {}

        drawing = Drawing(self.page_width, self.page_height)

        # Create empty rack background
        self._create_empty_rack_background(drawing)

        # Add rack name label at the top of the diagram
        if rack_name and rack_name != "Unknown":
            start_x = (self.page_width - self.rack_width) / 2
            start_y = self.margin + 0.5 * inch
            rack_label_y = start_y + self.rack_height + 0.1 * inch

            rack_label = String(
                start_x + (self.rack_width / 2),
                rack_label_y,
                f"Rack: {rack_name}",
                textAnchor="middle",
                fontSize=12,
                fillColor=self.BRAND_DARK,
                fontName="Helvetica-Bold",
            )
            drawing.add(rack_label)

        # Calculate switch positions if switches are provided (uses ebox boundaries when eboxes present)
        switch_positions_map = {}
        if switches and len(switches) > 0:
            calculated_positions = self._calculate_switch_positions(
                cboxes, dboxes, len(switches), switches, eboxes=eboxes
            )
            if calculated_positions:
                # Map switch number to U position
                for idx, u_pos in enumerate(calculated_positions, start=1):
                    switch_positions_map[idx] = u_pos

        # Place CBoxes — label with box name/serial from Hardware Inventory
        cnodes_by_cbox = nsm.get("cnodes_by_cbox", {})
        for cbox in cboxes:
            device_id = cbox.get("id", 0)
            model = cbox.get("model", "")
            rack_position = cbox.get("rack_unit", "")
            status = cbox.get("state", "ACTIVE")
            box_name = cbox.get("name", "")

            if not rack_position:
                logger.warning(f"CBox-{device_id} has no rack position, skipping")
                continue

            u_position = self._parse_rack_position(rack_position)
            if u_position == 0:
                continue

            u_height = self._get_device_height_units(model)

            indicators: Optional[List[Dict[str, Any]]] = None
            cn_list = cnodes_by_cbox.get(device_id, [])
            if cn_list:
                indicators = []
                for cn in cn_list:
                    cn_st = str(cn.get("status", "")).upper()
                    if cn_st == "ACTIVE":
                        indicators.append({"shape": "dot", "color": self.STATUS_ACTIVE})
                    elif cn.get("is_mgmt") and cn_st != "ACTIVE":
                        indicators.append({"shape": "dot", "color": self.STATUS_MGMT})
                    else:
                        indicators.append({"shape": "dot", "color": self.STATUS_INACTIVE})

            self._create_device_representation(
                drawing,
                "cbox",
                device_id,
                u_position,
                u_height,
                model,
                status,
                label_override=box_name,
                indicators=indicators,
            )

        # Place DBoxes — label with box name/serial; deduplicate at same U position
        dnodes_by_dbox = nsm.get("dnodes_by_dbox", {})
        dbox_seen_u: set = set()
        for dbox in dboxes:
            device_id = dbox.get("id", 0)
            model = dbox.get("hardware_type", dbox.get("model", ""))
            rack_position = dbox.get("rack_unit", "")
            status = dbox.get("state", "ACTIVE")
            box_name = dbox.get("name", "")

            if not rack_position:
                logger.warning(f"DBox-{device_id} has no rack position, skipping")
                continue

            u_position = self._parse_rack_position(rack_position)
            if u_position == 0:
                continue

            if u_position in dbox_seen_u:
                continue
            dbox_seen_u.add(u_position)

            u_height = self._get_device_height_units(model)

            indicators = None
            dn_list = dnodes_by_dbox.get(device_id, [])
            if dn_list:
                indicators = []
                for dn in dn_list:
                    dn_st = str(dn.get("status", "")).upper()
                    if dn_st == "ACTIVE":
                        indicators.append({"shape": "square", "color": self.STATUS_ACTIVE})
                    else:
                        indicators.append({"shape": "square", "color": self.STATUS_INACTIVE})

            self._create_device_representation(
                drawing,
                "dbox",
                device_id,
                u_position,
                u_height,
                model,
                status,
                label_override=box_name,
                indicators=indicators,
            )

        # Place EBoxes — 1 CNode dot + 2 DNode squares per EBox
        cnode_by_ebox = nsm.get("cnode_by_ebox", {})
        dnodes_by_ebox = nsm.get("dnodes_by_ebox", {})
        for ebox in eboxes:
            device_id = ebox.get("id", 0)
            model = ebox.get("model", ebox.get("hardware_type", "ebox"))
            rack_position = ebox.get("rack_unit", "")
            status = ebox.get("state", "ACTIVE")
            box_name = ebox.get("name", "")

            if not rack_position:
                logger.warning(f"EBox-{device_id} has no rack position, skipping")
                continue

            u_position = self._parse_rack_position(rack_position)
            if u_position == 0:
                continue

            u_height = self._get_device_height_units(model)

            indicators = None
            cn_entry = cnode_by_ebox.get(device_id)
            dn_entries = dnodes_by_ebox.get(device_id, [])
            if cn_entry or dn_entries:
                indicators = []
                if cn_entry:
                    cn_st = str(cn_entry.get("status", "")).upper()
                    if cn_st == "ACTIVE":
                        indicators.append({"shape": "dot", "color": self.STATUS_ACTIVE})
                    elif cn_entry.get("is_mgmt") and cn_st != "ACTIVE":
                        indicators.append({"shape": "dot", "color": self.STATUS_MGMT})
                    else:
                        indicators.append({"shape": "dot", "color": self.STATUS_INACTIVE})
                for dn in dn_entries:
                    dn_st = str(dn.get("status", "")).upper()
                    if dn_st == "ACTIVE":
                        indicators.append({"shape": "square", "color": self.STATUS_ACTIVE})
                    else:
                        indicators.append({"shape": "square", "color": self.STATUS_INACTIVE})

            self._create_device_representation(
                drawing,
                "ebox",
                device_id,
                u_position,
                u_height,
                model,
                status,
                label_override=box_name,
                indicators=indicators,
            )

        # Place Switches at calculated or explicit positions
        switch_inv = nsm.get("switch_in_inventory", {})
        if switches:
            for switch_num, switch in enumerate(switches, start=1):
                model = switch.get("model", "switch")
                status = switch.get("state", "ACTIVE")
                sw_name = str(switch.get("id") or switch.get("name") or "").strip()

                # Build indicator: only for switches in Hardware Inventory
                sw_indicators: Optional[List[Dict[str, Any]]] = None
                if sw_name and sw_name in switch_inv:
                    inv_state = switch_inv[sw_name]
                    if inv_state in ("ACTIVE", "ONLINE", "OK"):
                        sw_indicators = [{"shape": "dot", "color": self.STATUS_ACTIVE}]
                    else:
                        sw_indicators = [{"shape": "dot", "color": self.STATUS_INACTIVE}]

                explicit_position = switch.get("rack_unit", "")

                if explicit_position:
                    u_position = self._parse_rack_position(explicit_position)
                    if u_position > 0:
                        switch_height = self._get_device_height_units(model)
                        logger.info(
                            f"Placing switch {switch_num} at explicit position U{u_position} (model: {model}, height: {switch_height}U)"
                        )
                        self._create_device_representation(
                            drawing,
                            "switch",
                            switch_num,
                            u_position,
                            switch_height,
                            model,
                            status,
                            indicators=sw_indicators,
                        )
                elif switch_positions_map and switch_num in switch_positions_map:
                    u_position = switch_positions_map[switch_num]
                    switch_height = self._get_device_height_units(model)
                    logger.info(
                        f"Placing switch {switch_num} (model: {model}) at calculated position U{u_position} "
                        f"(height: {switch_height}U, occupies U{u_position}-U{u_position + switch_height - 1})"
                    )
                    self._create_device_representation(
                        drawing,
                        "switch",
                        switch_num,
                        u_position,
                        switch_height,
                        model,
                        status,
                        annotation="Unverified - Auto Switch Placement",
                        indicators=sw_indicators,
                    )
                else:
                    logger.warning(
                        f"Switch {switch_num} (model: {model}) has no position in switch_positions_map. "
                        f"Available positions: {switch_positions_map}"
                    )

        if nsm:
            self._draw_status_legend(drawing)

        device_count_msg = f"{len(cboxes)} CBoxes, {len(dboxes)} DBoxes"
        if eboxes:
            device_count_msg += f", {len(eboxes)} EBoxes"
        if switches:
            device_count_msg += f", {len(switches)} Switches"
        logger.info(f"Generated rack diagram with {device_count_msg}")

        return drawing, switch_positions_map
