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
        image_map = {
            # CBoxes
            "supermicro_gen5_cbox": HARDWARE_IMAGE_DIR / "supermicro_gen5_cbox_1u.png",
            "hpe_genoa_cbox": HARDWARE_IMAGE_DIR / "hpe_genoa_cbox.png",
            "hpe_icelake": HARDWARE_IMAGE_DIR / "hpe_il_cbox_2u.png",
            "dell_icelake": HARDWARE_IMAGE_DIR / "dell_il_cbox_2u.png",
            "dell_turin_cbox": HARDWARE_IMAGE_DIR / "dell_turin_r6715_cbox_1u.png",
            "smc_turin_cbox": HARDWARE_IMAGE_DIR / "smc_turin_cbox_1u.png",
            "broadwell": HARDWARE_IMAGE_DIR / "broadwell_cbox_2u.png",
            "cascadelake": HARDWARE_IMAGE_DIR / "cascadelake_cbox_2u.png",
            # DBoxes
            "ceres_v2": HARDWARE_IMAGE_DIR / "ceres_v2_1u.png",
            "dbox-515": HARDWARE_IMAGE_DIR / "ceres_v2_1u.png",
            "dbox-516": HARDWARE_IMAGE_DIR / "ceres_v2_1u.png",
            "sanmina": HARDWARE_IMAGE_DIR / "maverick_2u.png",
            "maverick_1.5": HARDWARE_IMAGE_DIR / "maverick_2u.png",
            # Switches
            "msn2700": HARDWARE_IMAGE_DIR / "mellanox_msn2700_1x32p_100g_switch_1u.png",
            "msn3700-vs2fc": HARDWARE_IMAGE_DIR / "mellanox_msn3700_1x32p_200g_switch_1u.png",
            "msn2100-cb2f": HARDWARE_IMAGE_DIR / "mellanox_msn2100_2x16p_100g_switch_1u.png",
            "msn4600c": HARDWARE_IMAGE_DIR / "mellanox_msn4600C_1x64p_100g_switch_2u.png",
            "msn4600": HARDWARE_IMAGE_DIR / "mellanox_msn4600_1x64p_200g_switch_2u.png",
            "sn5600": HARDWARE_IMAGE_DIR / "mellanox_sn5600_1x64p_800g_switch_2u.png",
            "arista_7060dx5": HARDWARE_IMAGE_DIR / "arista_7060dx5_1x64p_800g_switch_2u.jpeg",
            "arista_7050cx4": HARDWARE_IMAGE_DIR / "arista_7050cx4_24d_400g_switch_1u.png",
            "arista_7050dx4": HARDWARE_IMAGE_DIR / "arista_7050dx4_32s_400g_switch_1u.png",
            "arista": HARDWARE_IMAGE_DIR / "arista_7060dx5_1x64p_800g_switch_2u.jpeg",
            "n42c-00rb-7c0": HARDWARE_IMAGE_DIR / "mellanox_sn5400_1x64p_400g_switch_2u.png",
            "msn4700-ws2rc": HARDWARE_IMAGE_DIR / "msn4700-ws2rc_1u.png",
            "msn4700": HARDWARE_IMAGE_DIR / "msn4700-ws2rc_1u.png",
            # EBoxes
            "supermicro_gen5_ebox": HARDWARE_IMAGE_DIR / "supermicro_gen5_ebox_1u.png",
            "dell_genoa_ebox": HARDWARE_IMAGE_DIR / "dell_genoa_ebox_1u.png",
        }

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

        Checks built-in patterns first, then the user library.
        """
        one_u_models = [
            "supermicro_gen5_cbox",
            "hpe_genoa_cbox",
            "dell_turin_cbox",
            "smc_turin_cbox",
            "ceres_v2",
            "dbox-515",
            "dbox-516",
            "msn2700",
            "msn3700-vs2fc",
            "msn2100-cb2f",
            "msn4700-ws2rc",
            "msn4700",
            "arista_7050cx4",
            "arista_7050dx4",
        ]
        two_u_models = [
            "supermicro_2u_cbox",
            "hpe_icelake",
            "dell_icelake",
            "broadwell",
            "cascadelake",
            "ceres_4u",
            "sanmina",
            "maverick_1.5",
            "msn4600c",
            "msn4600",
            "sn5600",
            "arista_7060dx5",
            "arista",
            "n42c-00rb-7c0",
        ]

        model_lower = model.lower() if model else ""

        # EBox (enclosure) U height for Physical Rack Layout (default 1U)
        if model_lower and ("ebox" in model_lower or "enclosure" in model_lower):
            return 1

        for pattern in sorted(two_u_models, key=len, reverse=True):
            if pattern in model_lower:
                return 2

        for pattern in sorted(one_u_models, key=len, reverse=True):
            if pattern in model_lower:
                return 1

        user_lib = getattr(self, "_user_library", {}) or {}
        for key in sorted(user_lib, key=len, reverse=True):
            entry = user_lib[key]
            if key in model_lower:
                return cast(int, entry.get("height_u", 1))

        logger.warning(f"Unknown model '{model}', defaulting to 1U")
        return 1

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
    ) -> None:
        """
        Create a visual representation of a device in the rack.
        Uses actual hardware images if available, otherwise falls back to colored rectangles.

        Args:
            drawing: ReportLab Drawing object
            device_type: Type of device ("cbox", "dbox", "switch")
            device_id: Device ID number
            u_position: Top U position where device is mounted
            u_height: Height of device in rack units (1U or 2U)
            model: Hardware model name for image lookup
            status: Device status (ACTIVE, OFFLINE, etc.)
        """
        # Calculate position
        start_x = (self.page_width - self.rack_width) / 2
        start_y = self.margin + 0.5 * inch

        # Device starts at u_position and extends downward for u_height units
        # For 2U device at U17: occupies U17 (top) and U16 (bottom)
        device_bottom_u = u_position - u_height + 1
        device_y = start_y + ((device_bottom_u - 1) * self.u_height)
        device_height = u_height * self.u_height

        # Determine device color and label prefix
        if device_type.lower() == "cbox":
            fill_color = self.CBOX_COLOR
            label_prefix = "CBox"
        elif device_type.lower() == "dbox":
            fill_color = self.DBOX_COLOR
            label_prefix = "DBox"
        elif device_type.lower() == "ebox":
            fill_color = self.DBOX_COLOR  # EBox (enclosure) same as DBox for now
            label_prefix = "EBox"
        elif device_type.lower() == "switch":
            fill_color = self.SWITCH_COLOR
            label_prefix = "Switch"
        else:
            fill_color = colors.gray
            label_prefix = "Device"

        # Check if hardware image is available
        image_path = self._get_hardware_image_path(model) if model else None

        if image_path and image_path.exists():
            # Use hardware image
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
                # Fall back to rectangle if image fails
                self._draw_fallback_device(drawing, start_x, device_y, device_height, fill_color)
        else:
            # Use fallback colored rectangle
            self._draw_fallback_device(drawing, start_x, device_y, device_height, fill_color)

        # Add status indicator (green dot for active)
        if status.upper() == "ACTIVE" or status.upper() == "ONLINE":
            status_dot = Circle(
                start_x + 10,
                device_y + (device_height / 2),
                3,
                fillColor=self.STATUS_ACTIVE,
                strokeColor=self.BRAND_DARK,
                strokeWidth=0.5,
            )
            drawing.add(status_dot)

        # Add label outside rack with connector line
        post_width = 0.08 * self.rack_width
        label_x = start_x + self.rack_width + post_width + 0.15 * inch
        label_y = device_y + (device_height / 2) - 3
        label_text = f"{label_prefix}-{device_id}"

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
                cbox_tops.append(u_pos)
                cbox_bottoms.append(u_pos - u_height + 1)

        dbox_tops = []
        dbox_bottoms = []
        for dbox in dboxes:
            u_pos = self._parse_rack_position(dbox.get("rack_unit", ""))
            if u_pos > 0:
                hw_type = dbox.get("hardware_type", dbox.get("model", ""))
                u_height = self._get_device_height_units(hw_type)
                dbox_tops.append(u_pos)
                dbox_bottoms.append(u_pos - u_height + 1)

        ebox_tops = []
        ebox_bottoms = []
        for ebox in eboxes:
            u_pos = self._parse_rack_position(ebox.get("rack_unit", ""))
            if u_pos > 0:
                model = ebox.get("model", ebox.get("hardware_type", "ebox"))
                u_height = self._get_device_height_units(model)
                ebox_tops.append(u_pos)
                ebox_bottoms.append(u_pos - u_height + 1)

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

    def _try_center_placement(
        self,
        lowest_cbox_bottom: int,
        highest_dbox_top: int,
        switch_height: int,
    ) -> List[int]:
        """
        Strategy A: place switches in the center gap between CBoxes and DBoxes.

        Returns list of [SW1_top, SW2_top] positions or empty list on failure.
        """
        gap_top = lowest_cbox_bottom - 1
        gap_bottom = highest_dbox_top + 1

        if gap_top < gap_bottom:
            logger.info("Strategy A (center): No gap between CBoxes and DBoxes")
            return []

        gap_size = gap_top - gap_bottom + 1
        logger.info(f"Strategy A (center): gap={gap_size}U (U{gap_bottom}–U{gap_top})")

        if switch_height == 2:
            if gap_size < 9:
                logger.info(f"Strategy A (center): gap {gap_size}U too small for 2x 2U switches (need 9U)")
                return []
            sw1_top = gap_bottom + 3
            sw2_top = gap_top - 2
            logger.info(f"Strategy A (center): 2U switches — SW-1 top U{sw1_top}, SW-2 top U{sw2_top}")
            return [sw1_top, sw2_top]

        # 1U switches
        if gap_size < 2:
            logger.info(f"Strategy A (center): gap {gap_size}U too small for 2x 1U switches (need 2U)")
            return []

        if gap_size % 2 == 0:
            center_top = gap_bottom + (gap_size // 2)
            center_bottom = center_top - 1
            logger.info(f"Strategy A (center): even gap — SW-1 at U{center_bottom}, SW-2 at U{center_top}")
            return [center_bottom, center_top]

        center_u = gap_bottom + (gap_size // 2)
        sw_bottom = center_u - 1
        sw_top = center_u + 1
        logger.info(f"Strategy A (center): odd gap — SW-1 at U{sw_bottom}, SW-2 at U{sw_top} (U{center_u} empty)")
        return [sw_bottom, sw_top]

    def _try_above_placement(
        self,
        highest_cbox_top: int,
        switch_height: int,
        rack_height: int,
    ) -> List[int]:
        """
        Strategy B: place switches above the topmost CBox.

        SW-1 sits 1U above the top CBox, SW-2 sits 1U above SW-1.
        Returns list of [SW1_top, SW2_top] positions or empty list if exceeds rack.
        """
        sw1_top = highest_cbox_top + 1 + switch_height  # 1U gap + switch
        sw2_top = sw1_top + 1 + switch_height  # 1U gap + switch

        if sw2_top > rack_height:
            logger.info(f"Strategy B (above CBox): SW-2 would be at U{sw2_top}, " f"exceeds rack height {rack_height}U")
            return []

        logger.info(
            f"Strategy B (above CBox): SW-1 top U{sw1_top}, SW-2 top U{sw2_top} " f"(rack height {rack_height}U)"
        )
        return [sw1_top, sw2_top]

    def _try_below_placement(
        self,
        lowest_dbox_bottom: int,
        switch_height: int,
    ) -> List[int]:
        """
        Strategy C: place switches below the bottommost DBox.

        SW-2 sits 1U below the bottom DBox, SW-1 sits 1U below SW-2.
        Returns list of [SW1_top, SW2_top] positions or empty list if below U1.
        """
        sw2_top = lowest_dbox_bottom - 1 - 1  # 1U gap below DBox, top of SW-2
        sw1_top = sw2_top - switch_height - 1  # 1U gap below SW-2, top of SW-1
        sw1_bottom = sw1_top - switch_height + 1

        if sw1_bottom < 1:
            logger.info(f"Strategy C (below DBox): SW-1 bottom would be at U{sw1_bottom}, " f"below rack floor")
            return []

        logger.info(f"Strategy C (below DBox): SW-1 top U{sw1_top}, SW-2 top U{sw2_top}")
        return [sw1_top, sw2_top]

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
            num_switches: Number of switches to place (currently only supports 2)
            switches: Optional list of switch dictionaries to determine switch height
            rack_height: Rack height in U (defaults to self.rack_height_u)
            eboxes: Optional list of EBox device dictionaries (for ebox clusters)

        Returns:
            List of U positions (top U) for switches, or empty list if all strategies fail
        """
        if num_switches != 2:
            logger.warning(f"Switch placement logic currently only supports 2 switches, got {num_switches}")
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
            )
            if positions:
                logger.info("Using switch placement: above EBox hardware")
                return positions
            positions = self._try_below_placement(
                bounds["lowest_ebox_bottom"],
                switch_height,
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
            )
            if positions:
                return positions

        # Strategy B: above top CBox (requires CBox data)
        if has_cbox:
            positions = self._try_above_placement(
                bounds["highest_cbox_top"],
                switch_height,
                effective_rack_height,
            )
            if positions:
                return positions

        # Strategy C: below bottom DBox (requires DBox data)
        if has_dbox:
            positions = self._try_below_placement(
                bounds["lowest_dbox_bottom"],
                switch_height,
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

        Returns:
            Tuple of:
                - ReportLab Drawing object containing the complete rack diagram
                - Dictionary mapping switch numbers to calculated U positions
        """
        eboxes = eboxes or []
        # Create drawing
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

        # Place CBoxes
        for cbox in cboxes:
            device_id = cbox.get("id", 0)
            model = cbox.get("model", "")
            rack_position = cbox.get("rack_unit", "")
            status = cbox.get("state", "ACTIVE")

            if not rack_position:
                logger.warning(f"CBox-{device_id} has no rack position, skipping")
                continue

            u_position = self._parse_rack_position(rack_position)
            if u_position == 0:
                continue

            u_height = self._get_device_height_units(model)

            self._create_device_representation(drawing, "cbox", device_id, u_position, u_height, model, status)

        # Place DBoxes
        for dbox in dboxes:
            device_id = dbox.get("id", 0)
            model = dbox.get("hardware_type", dbox.get("model", ""))
            rack_position = dbox.get("rack_unit", "")
            status = dbox.get("state", "ACTIVE")

            if not rack_position:
                logger.warning(f"DBox-{device_id} has no rack position, skipping")
                continue

            u_position = self._parse_rack_position(rack_position)
            if u_position == 0:
                continue

            u_height = self._get_device_height_units(model)

            self._create_device_representation(drawing, "dbox", device_id, u_position, u_height, model, status)

        # Place EBoxes (enclosures; use ebox U height in Physical Rack Layout)
        for ebox in eboxes:
            device_id = ebox.get("id", 0)
            model = ebox.get("model", ebox.get("hardware_type", "ebox"))
            rack_position = ebox.get("rack_unit", "")
            status = ebox.get("state", "ACTIVE")

            if not rack_position:
                logger.warning(f"EBox-{device_id} has no rack position, skipping")
                continue

            u_position = self._parse_rack_position(rack_position)
            if u_position == 0:
                continue

            u_height = self._get_device_height_units(model)

            self._create_device_representation(drawing, "ebox", device_id, u_position, u_height, model, status)

        # Place Switches at calculated or explicit positions
        if switches:
            for switch_num, switch in enumerate(switches, start=1):
                model = switch.get("model", "switch")
                status = switch.get("state", "ACTIVE")

                # Check if switch has explicit rack_unit position
                explicit_position = switch.get("rack_unit", "")

                if explicit_position:
                    # Use explicit position for switch
                    u_position = self._parse_rack_position(explicit_position)
                    if u_position > 0:
                        # Get switch height from model
                        switch_height = self._get_device_height_units(model)
                        logger.info(
                            f"Placing switch {switch_num} at explicit position U{u_position} (model: {model}, height: {switch_height}U)"
                        )
                        self._create_device_representation(
                            drawing, "switch", switch_num, u_position, switch_height, model, status
                        )
                elif switch_positions_map and switch_num in switch_positions_map:
                    # Use calculated position
                    u_position = switch_positions_map[switch_num]
                    # Get switch height from model
                    switch_height = self._get_device_height_units(model)
                    logger.info(
                        f"Placing switch {switch_num} (model: {model}) at calculated position U{u_position} "
                        f"(height: {switch_height}U, occupies U{u_position - switch_height + 1}-U{u_position})"
                    )
                    self._create_device_representation(
                        drawing, "switch", switch_num, u_position, switch_height, model, status
                    )
                else:
                    logger.warning(
                        f"Switch {switch_num} (model: {model}) has no position in switch_positions_map. "
                        f"Available positions: {switch_positions_map}"
                    )

        device_count_msg = f"{len(cboxes)} CBoxes, {len(dboxes)} DBoxes"
        if eboxes:
            device_count_msg += f", {len(eboxes)} EBoxes"
        if switches:
            device_count_msg += f", {len(switches)} Switches"
        logger.info(f"Generated rack diagram with {device_count_msg}")

        return drawing, switch_positions_map
