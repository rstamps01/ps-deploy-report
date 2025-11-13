"""
Rack Diagram Generator for VAST As-Built Reports

This module generates visual rack diagrams showing physical hardware placement
in 42U data center racks with proper scaling, positioning, and labeling.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Image
from reportlab.platypus import Image as RLImage
from reportlab.platypus import KeepTogether, Paragraph, Spacer, Table, TableStyle

# Configure logger
logger = logging.getLogger(__name__)

# Hardware image library paths
HARDWARE_IMAGE_DIR = Path(__file__).parent.parent / "assets" / "hardware_images"


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
        42: 73.5,   # 42U rack internal height
        48: 84.0,   # 48U rack internal height
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
        page_width: float = 7.5 * inch,
        page_height: float = 8.5 * inch,
        rack_height_u: int = None
    ):
        """
        Initialize rack diagram generator.

        Args:
            page_width: Available page width in points (default 7.5" for content area)
            page_height: Available page height in points (default 8.5" to maximize space)
            rack_height_u: Number of rack units (U) for this rack (42, 48, etc.).
                         Defaults to 42U for backward compatibility.
        """
        self.page_width = page_width
        self.page_height = page_height

        # Set rack height (default to 42U if not specified)
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
        self.scale = (
            min(width_scale, height_scale) * 0.95
        )  # 95% to maximize rack size while ensuring it fits

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
        Load available hardware images from the assets directory.

        Returns:
            Dictionary mapping model names to image file paths
        """
        image_map = {
            "supermicro_gen5_cbox": HARDWARE_IMAGE_DIR / "supermicro_gen5_cbox_1u.png",
            "hpe_genoa_cbox": HARDWARE_IMAGE_DIR / "hpe_genoa_cbox.png",  # HPE Genoa 1U CBox
            "broadwell": HARDWARE_IMAGE_DIR
            / "broadwell_cbox_2u.png",  # Broadwell 2U CBox
            "cascadelake": HARDWARE_IMAGE_DIR
            / "cascadelake_cbox_2u.png",  # CascadeLake 2U CBox
            "ceres_v2": HARDWARE_IMAGE_DIR / "ceres_v2_1u.png",
            "dbox-515": HARDWARE_IMAGE_DIR
            / "ceres_v2_1u.png",  # Map dbox-515 to ceres_v2 image
            "sanmina": HARDWARE_IMAGE_DIR / "ceres_v2_1u.png",  # Sanmina 1U DBox
            "maverick_1.5": HARDWARE_IMAGE_DIR / "maverick_2u.png",  # Maverick 2U DBox
            "msn3700-vs2fc": HARDWARE_IMAGE_DIR
            / "mellanox_msn3700_1x32p_200g_switch_1u.png",  # Mellanox MSN3700 switch
            "msn2100-cb2f": HARDWARE_IMAGE_DIR
            / "mellanox_msn2100_2x16p_100g_switch_1u.png",  # Mellanox MSN2100 switch
            "arista_7060dx5": HARDWARE_IMAGE_DIR
            / "arista_7060dx5_1x64p_800g_switch_2u.jpeg",  # Arista 7060DX5 2U switch
            "arista": HARDWARE_IMAGE_DIR
            / "arista_7060dx5_1x64p_800g_switch_2u.jpeg",  # Generic Arista switch mapping
            # Add more hardware models as images become available
        }

        # Check which images actually exist
        available_images = {}
        for model, path in image_map.items():
            if path.exists():
                available_images[model] = path
                logger.info(f"Loaded hardware image for {model}: {path}")
            else:
                available_images[model] = None
                logger.debug(
                    f"No image found for {model} at {path}, will use fallback rendering"
                )

        return available_images

    def _get_hardware_image_path(self, model: str) -> Optional[Path]:
        """
        Get the image path for a hardware model.

        Args:
            model: Hardware model name

        Returns:
            Path to image file if available, None otherwise
        """
        model_clean = model.lower().strip()

        # Check for exact match
        if model_clean in self.hardware_images:
            return self.hardware_images[model_clean]

        # Check for partial matches
        for key in self.hardware_images:
            if key in model_clean:
                return self.hardware_images[key]

        return None

    def _get_device_height_units(self, model: str) -> int:
        """
        Determine the height in rack units (U) for a device based on its model.

        Args:
            model: Hardware model name

        Returns:
            Number of rack units (1U or 2U)
        """
        # Map of model patterns to U height
        # 1U devices
        one_u_models = [
            "supermicro_gen5_cbox",
            "hpe_genoa_cbox",  # HPE Genoa 1U CBox
            "ceres_v2",
            "sanmina",  # Sanmina 1U DBox
            "msn3700-vs2fc",  # Mellanox MSN3700 switch
            "msn2100-cb2f",  # Mellanox MSN2100 switch
        ]

        # 2U devices (add patterns as needed)
        two_u_models = [
            "supermicro_2u_cbox",
            "broadwell",  # Broadwell 2U CBox
            "cascadelake",  # CascadeLake 2U CBox
            "ceres_4u",  # Example, may need adjustment
            "maverick_1.5",  # Maverick 2U DBox
            "arista_7060dx5",  # Arista 7060DX5 2U switch
            "arista",  # Generic Arista switch (2U)
        ]

        model_lower = model.lower() if model else ""

        # Check for 2U devices first
        for pattern in two_u_models:
            if pattern in model_lower:
                return 2

        # Default to 1U for known 1U devices
        for pattern in one_u_models:
            if pattern in model_lower:
                return 1

        # Default to 1U if unknown
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
                logger.warning(
                    f"Invalid rack position {position}, must be between U1-U{self.rack_height_u}"
                )
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
                from reportlab.graphics.shapes import Image as GraphicsImage

                # Calculate device width with some padding
                device_width = self.rack_width - 4

                # Create image element scaled to fit the device space
                hw_image = GraphicsImage(
                    start_x + 2,
                    device_y,
                    device_width,
                    device_height - 1,
                    str(image_path),
                )
                drawing.add(hw_image)
                logger.debug(
                    f"Using hardware image for {device_type}-{device_id}: {image_path}"
                )

            except Exception as e:
                logger.warning(
                    f"Failed to load hardware image {image_path}: {e}, using fallback"
                )
                # Fall back to rectangle if image fails
                self._draw_fallback_device(
                    drawing, start_x, device_y, device_height, fill_color
                )
        else:
            # Use fallback colored rectangle
            self._draw_fallback_device(
                drawing, start_x, device_y, device_height, fill_color
            )

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

    def _calculate_switch_positions(
        self,
        cboxes: List[Dict[str, Any]],
        dboxes: List[Dict[str, Any]],
        num_switches: int,
        switches: Optional[List[Dict[str, Any]]] = None,
    ) -> List[int]:
        """
        Calculate optimal switch positions in the rack between CBoxes and DBoxes.

        For 2 switches:
        - 1U switches: If gap is even (2U, 4U, 6U, etc.): Place switches in center-most positions
        - 1U switches: If gap is odd (3U, 5U, 7U, etc.): Place switches in center with 1U gap between them
        - 2U switches: Need at least 4U gap, placed with 1U gap between them

        Args:
            cboxes: List of CBox device dictionaries
            dboxes: List of DBox device dictionaries
            num_switches: Number of switches to place (currently only supports 2)
            switches: Optional list of switch dictionaries to determine switch height

        Returns:
            List of U positions for switches (empty list if cannot calculate)
        """
        if num_switches != 2:
            logger.warning(
                f"Switch placement logic currently only supports 2 switches, got {num_switches}"
            )
            return []

        # Determine switch height (1U or 2U) from first switch model
        switch_height = 1  # Default to 1U
        if switches and len(switches) > 0:
            first_switch_model = switches[0].get("model", "")
            switch_height = self._get_device_height_units(first_switch_model)
            logger.info(f"Switch height determined: {switch_height}U (model: {first_switch_model})")

        # Find the highest CBox position and lowest DBox position
        cbox_positions = []
        for cbox in cboxes:
            rack_pos = cbox.get("rack_unit", "")
            u_pos = self._parse_rack_position(rack_pos)
            if u_pos > 0:
                model = cbox.get("model", "")
                u_height = self._get_device_height_units(model)
                # Record the bottom of the CBox
                bottom_u = u_pos - u_height + 1
                cbox_positions.append(bottom_u)

        dbox_positions = []
        for dbox in dboxes:
            rack_pos = dbox.get("rack_unit", "")
            u_pos = self._parse_rack_position(rack_pos)
            if u_pos > 0:
                dbox_positions.append(u_pos)  # Top of DBox

        if not cbox_positions or not dbox_positions:
            logger.warning(
                "Cannot calculate switch positions: insufficient CBox or DBox data"
            )
            return []

        # Find the gap between the lowest CBox and highest DBox
        lowest_cbox = min(cbox_positions)  # Bottom-most U occupied by any CBox
        highest_dbox = max(dbox_positions)  # Top-most U occupied by any DBox

        # Calculate available gap (inclusive)
        # Gap is from (lowest_cbox - 1) down to (highest_dbox + 1)
        gap_top = lowest_cbox - 1
        gap_bottom = highest_dbox + 1

        if gap_top < gap_bottom:
            logger.warning(
                f"No gap between CBoxes and DBoxes: CBox bottom={lowest_cbox}, DBox top={highest_dbox}"
            )
            return []

        # Calculate gap size
        gap_size = gap_top - gap_bottom + 1  # Inclusive count

        logger.info(
            f"Gap between CBoxes and DBoxes: {gap_size}U (U{gap_bottom} to U{gap_top})"
        )

        # Calculate switch positions based on switch height
        switch_positions = []

        if switch_height == 2:
            # 2U switches: Need at least 9U gap total
            # - 2U gap between top switch and lowest CBox
            # - 2U for top switch (SW-2)
            # - 1U gap between switches
            # - 2U for lower switch (SW-1)
            # - 2U gap between lower switch and top DBox
            # Total: 2 + 2 + 1 + 2 + 2 = 9U minimum
            if gap_size < 9:
                logger.warning(
                    f"Insufficient gap size ({gap_size}U) for 2 switches of 2U each "
                    f"with required spacing (need at least 9U: 2U+2U+1U+2U+2U)"
                )
                return []

            # Place 2U switches with specific spacing requirements:
            # - 2U gap between top switch (SW-2) and lowest CBox
            # - 1U gap between the two switches
            # - 2U gap between lower switch (SW-1) and top DBox

            # Calculate positions from boundaries:
            # gap_bottom = highest_dbox + 1 (first U above top DBox)
            # gap_top = lowest_cbox - 1 (first U below lowest CBox)

            # SW-1 (lower switch): 2U gap above top DBox, then switch at U16 (occupies U15-U16)
            # gap_bottom = highest_dbox + 1 (first U above top DBox)
            # Need 2U gap above DBox, so SW-1 top = gap_bottom + 3
            # Example: If gap_bottom = U13, then SW-1 top = U16 (U13-U14 empty, U15-U16 switch)
            sw1_top = gap_bottom + 3  # 2U gap (gap_bottom, gap_bottom+1) + 1U to start switch
            sw1_bottom = sw1_top - switch_height + 1  # SW-1 occupies U(sw1_bottom) to U(sw1_top)
            
            # SW-2 (top switch): 2U gap below lowest CBox, switch at U19 (occupies U18-U19)
            # gap_top = lowest_cbox - 1 (first U below lowest CBox)
            # Need 2U gap below CBox, so SW-2 top = gap_top - 2
            # Example: If gap_top = U21, then SW-2 top = U19 (U20-U21 empty, U18-U19 switch)
            sw2_top = gap_top - 2  # 2U gap (gap_top-1, gap_top) below CBox
            sw2_bottom = sw2_top - switch_height + 1  # SW-2 occupies U(sw2_bottom) to U(sw2_top)
            
            # Verify 1U gap between switches
            gap_between_switches = sw2_bottom - sw1_top - 1
            if gap_between_switches != 1:
                logger.warning(
                    f"Gap between switches is {gap_between_switches}U, expected 1U. "
                    f"Gap size: {gap_size}U, SW-1 top: U{sw1_top}, SW-2 bottom: U{sw2_bottom}"
                )
                # If gap is not exactly 1U, we may need to adjust, but for now proceed
                # The switches will still be placed, just with different spacing

            # Return top U position for each switch (SW-1 below SW-2)
            switch_positions = [sw1_top, sw2_top]
            logger.info(
                f"2U switches: Placing SW-1 at U{sw1_bottom}-U{sw1_top}, SW-2 at U{sw2_bottom}-U{sw2_top} "
                f"(2U gap to DBox, 1U gap between, 2U gap to CBox)"
            )
        else:
            # 1U switches: Original logic
            if gap_size < 2:
                logger.warning(f"Insufficient gap size ({gap_size}U) for 2 switches")
                return []

            if gap_size % 2 == 0:
                # Even gap: Place switches in center-most positions
                # Example: 4U gap (U19-U22): SW-1 at U20, SW-2 at U21
                center_top = gap_bottom + (gap_size // 2)
                center_bottom = center_top - 1
                # Return lower position first (SW-1 below SW-2)
                switch_positions = [center_bottom, center_top]
                logger.info(
                    f"Even gap ({gap_size}U): Placing SW-1 at U{center_bottom}, SW-2 at U{center_top}"
                )
            else:
                # Odd gap: Place switches in center with 1U gap between them
                # Example: 5U gap (U19-U23): SW-1 at U20, SW-2 at U22 (leaving U21 empty)
                center_u = gap_bottom + (gap_size // 2)
                switch_top = center_u + 1
                switch_bottom = center_u - 1
                # Return lower position first (SW-1 below SW-2)
                switch_positions = [switch_bottom, switch_top]
                logger.info(
                    f"Odd gap ({gap_size}U): Placing SW-1 at U{switch_bottom}, SW-2 at U{switch_top} (U{center_u} empty)"
                )

        return switch_positions

    def generate_rack_diagram(
        self,
        cboxes: List[Dict[str, Any]],
        dboxes: List[Dict[str, Any]],
        switches: Optional[List[Dict[str, Any]]] = None,
        rack_name: Optional[str] = None,
    ) -> Tuple[Drawing, Dict[int, int]]:
        """
        Generate a complete rack diagram with all devices.

        Args:
            cboxes: List of CBox device dictionaries with 'id', 'model', 'rack_unit', 'state'
            dboxes: List of DBox device dictionaries with 'id', 'model', 'rack_unit', 'state'
            switches: Optional list of switch dictionaries with 'id', 'model', 'state'
            rack_name: Optional rack name to display on the diagram

        Returns:
            Tuple of:
                - ReportLab Drawing object containing the complete rack diagram
                - Dictionary mapping switch numbers to calculated U positions
        """
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

        # Calculate switch positions if switches are provided
        switch_positions_map = {}
        if switches and len(switches) > 0:
            calculated_positions = self._calculate_switch_positions(
                cboxes, dboxes, len(switches), switches
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

            self._create_device_representation(
                drawing, "cbox", device_id, u_position, u_height, model, status
            )

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

            self._create_device_representation(
                drawing, "dbox", device_id, u_position, u_height, model, status
            )

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
        if switches:
            device_count_msg += f", {len(switches)} Switches"
        logger.info(f"Generated rack diagram with {device_count_msg}")

        return drawing, switch_positions_map
