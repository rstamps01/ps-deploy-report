"""
Network Diagram Generator

Generates logical network topology diagrams showing connections between
CBoxes, Switches, and DBoxes based on port mapping data.

Layout:
- CBoxes at the top
- Switches in the middle (SWA on right, SWB on left)
- DBoxes at the bottom

Color coding:
- Green lines: Switch A connections
- Blue lines: Switch B connections
- Purple lines: IPL/MLAG connections between switches
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing, Group
from reportlab.graphics.shapes import Image as RLImage
from reportlab.graphics.shapes import Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)


class NetworkDiagramGenerator:
    """Generate logical network topology diagrams."""

    def __init__(self, assets_path: str = "assets"):
        """
        Initialize the network diagram generator.

        Args:
            assets_path: Path to assets directory containing hardware images
        """
        self.logger = logging.getLogger(__name__)
        self.assets_path = Path(assets_path)
        self.hardware_images_path = self.assets_path / "hardware_images"

        # Colors
        self.switch_a_color = colors.HexColor("#00aa00")  # Green
        self.switch_b_color = colors.HexColor("#0066cc")  # Blue
        self.ipl_color = colors.HexColor("#9933cc")  # Purple

        # Image cache
        self.image_cache = {}

    def load_hardware_image(self, hardware_type: str) -> Optional[str]:
        """
        Load hardware image path for a given hardware type.

        Args:
            hardware_type: Hardware type identifier

        Returns:
            Path to image file or None if not found
        """
        # Map hardware types to image files
        image_map = {
            "supermicro_gen5_cbox": "supermicro_gen5_cbox_1u.png",
            "ceres_v2": "ceres_v2_1u.png",
            "dbox-515": "ceres_v2_1u.png",
            "msn3700-vs2fc": "mellanox_msn3700_1x32p_200g_switch_1u.png",
        }

        # Find matching image
        for key, filename in image_map.items():
            if key.lower() in hardware_type.lower():
                image_path = self.hardware_images_path / filename
                if image_path.exists():
                    return str(image_path)

        self.logger.warning(f"No image found for hardware type: {hardware_type}")
        return None

    def generate_network_diagram(
        self,
        port_mapping_data: Dict[str, Any],
        hardware_data: Dict[str, Any],
        output_path: str,
        drawing_size: Tuple[float, float] = None,
    ) -> Optional[str]:
        """
        Generate logical network topology diagram.

        Args:
            port_mapping_data: Port mapping data from data_extractor
            hardware_data: Hardware inventory data
            output_path: Path to save the diagram
            drawing_size: Optional (width, height) in points

        Returns:
            Path to generated diagram or None if failed
        """
        try:
            self.logger.info("Generating logical network topology diagram")

            # Use letter page size if not specified
            if drawing_size is None:
                page_width, page_height = letter
                drawing_size = (page_width - 72, page_height - 72)  # 1" margins

            width, height = drawing_size

            # Create drawing
            drawing = Drawing(width, height)

            # Extract data
            cboxes = hardware_data.get("cboxes", [])
            dboxes = hardware_data.get("dboxes", [])
            switches = hardware_data.get("switches", [])
            port_map = port_mapping_data.get("port_map", [])
            ipl_ports = port_mapping_data.get("ipl_ports", [])

            self.logger.info(
                f"Hardware: {len(cboxes)} CBoxes, {len(dboxes)} DBoxes, {len(switches)} Switches"
            )
            self.logger.info(
                f"Connections: {len(port_map)} port mappings, {len(ipl_ports)} IPL ports"
            )

            # Layout parameters with dynamic sizing based on device count
            layer_height = (
                height / 4
            )  # Divide into 4 layers (top margin, cbox, switch, dbox)
            
            # Calculate max devices per row to determine sizing
            max_devices = max(len(cboxes), len(dboxes), 2)  # At least 2 for switches
            
            # Dynamic device sizing - scale down as more devices are added
            # Base size for 3 or fewer devices, scale down for more
            if max_devices <= 3:
                device_width = 160
                device_height = 80
                base_spacing = 300
            elif max_devices <= 5:
                device_width = 120
                device_height = 60
                base_spacing = 220
            elif max_devices <= 7:
                device_width = 100
                device_height = 50
                base_spacing = 160
            else:
                # For 8+ devices, calculate to fit all within width
                available_width = width * 0.9  # Use 90% of width
                device_width = min(80, available_width / (max_devices * 1.3))
                device_height = device_width * 0.5
                base_spacing = device_width * 1.2

            # Different spacing for different device types
            cbox_spacing = base_spacing
            switch_spacing = device_width * 1.5  # Slightly more space for switches
            dbox_spacing = base_spacing * 0.9

            # Calculate dynamic font sizes based on device size
            label_font_size = max(8, int(device_width / 8))
            name_font_size = max(6, int(device_width / 11.5))
            
            self.logger.info(
                f"Dynamic sizing: device={device_width:.0f}x{device_height:.0f}, "
                f"fonts={label_font_size}/{name_font_size}"
            )

            # Position layers
            cbox_y = height - layer_height
            switch_y = height - 2 * layer_height
            dbox_y = layer_height

            # Calculate positions for CBoxes (wider spacing)
            cbox_positions = self._calculate_positions(
                len(cboxes), width, cbox_y, device_width, cbox_spacing
            )

            # Calculate switch positions - centered with no border overlap
            # Switches are placed symmetrically around the center
            center_x = width / 2

            # Calculate total width needed for both switches plus gap
            switch_gap = 20  # Minimum gap between switch borders
            total_switch_width = device_width * 2 + switch_gap

            # Position switches symmetrically from center
            # SWB (left): from center minus half of total width
            # SWA (right): from center plus gap/2
            switch_positions = {
                1: (
                    center_x + switch_gap / 2,  # Switch A on right (starts after gap)
                    switch_y,
                ),
                2: (
                    center_x
                    - switch_gap / 2
                    - device_width,  # Switch B on left (ends before gap)
                    switch_y,
                ),
            }

            # Verify equal spacing from edges
            # Left edge to SWB left edge = SWB x-position
            # Right edge to SWA right edge = width - (SWA x-position + device_width)
            swb_x = switch_positions[2][0]
            swa_x = switch_positions[1][0]
            left_margin = swb_x
            right_margin = width - (swa_x + device_width)

            # Adjust if margins are not equal (center the pair)
            if abs(left_margin - right_margin) > 1:
                margin_diff = (right_margin - left_margin) / 2
                switch_positions[1] = (swa_x - margin_diff, switch_y)
                switch_positions[2] = (swb_x + margin_diff, switch_y)

            # Calculate midpoint between switches for DBox alignment
            switch_midpoint_x = center_x

            # Calculate DBox positions
            # If only one DBox, center it at switch midpoint
            if len(dboxes) == 1:
                dbox_positions = [(switch_midpoint_x - device_width / 2, dbox_y)]
            else:
                # Multiple DBoxes - spread them centered on switch midpoint
                dbox_positions = self._calculate_positions(
                    len(dboxes), width, dbox_y, device_width, dbox_spacing
                )

            # Draw connections first (so they appear behind devices)
            connection_group = Group()

            # Draw node-to-switch connections
            for conn in port_map:
                # Skip if not primary interface
                interface = conn.get("interface", "")
                network = conn.get("network", "?")
                node_designation = conn.get("node_designation", "Unknown")

                is_dnode = "DN" in node_designation
                is_cnode = "CN" in node_designation

                is_primary = False
                if is_cnode:
                    if network == "A" and "f0" in interface:
                        is_primary = True
                    elif network == "B" and "f1" in interface:
                        is_primary = True
                elif is_dnode:
                    if network == "A" and "f0" in interface:
                        is_primary = True
                    elif network == "B" and "f2" in interface:
                        is_primary = True

                if not is_primary:
                    continue

                # Determine switch (1 or 2)
                switch_ip = conn.get("switch_ip", "")
                if switch_ip == switches[0].get("mgmt_ip") if switches else None:
                    switch_num = 1
                elif (
                    switch_ip == switches[1].get("mgmt_ip")
                    if len(switches) > 1
                    else None
                ):
                    switch_num = 2
                else:
                    continue

                # Get switch position
                if switch_num not in switch_positions:
                    continue
                switch_x, switch_y_pos = switch_positions[switch_num]

                # Determine node position
                if is_cnode:
                    # Extract CBox number from designation (CB1-CN1-R -> 1)
                    try:
                        cbox_num = int(node_designation.split("-")[0].replace("CB", ""))
                        if cbox_num <= len(cbox_positions):
                            node_x, node_y = cbox_positions[cbox_num - 1]
                        else:
                            continue
                    except (ValueError, IndexError):
                        continue
                elif is_dnode:
                    # Extract DBox number from designation (DB1-DN1-R -> 1)
                    try:
                        dbox_num = int(node_designation.split("-")[0].replace("DB", ""))
                        if dbox_num <= len(dbox_positions):
                            node_x, node_y = dbox_positions[dbox_num - 1]
                        else:
                            continue
                    except (ValueError, IndexError):
                        continue
                else:
                    continue

                # Draw line (doubled stroke width)
                line_color = (
                    self.switch_a_color if switch_num == 1 else self.switch_b_color
                )
                line = Line(
                    node_x + device_width / 2,
                    node_y,
                    switch_x + device_width / 2,
                    switch_y_pos + device_height,
                    strokeColor=line_color,
                    strokeWidth=4,  # Doubled from 2
                )
                connection_group.add(line)

            # Draw IPL/MLAG connections between switches
            if len(switches) >= 2:
                sw1_x, sw1_y = switch_positions[1]
                sw2_x, sw2_y = switch_positions[2]

                # Draw 4 IPL lines (representing swp29-32)
                for i in range(4):
                    offset = (i - 1.5) * 10  # Spread lines vertically (doubled spacing)
                    line = Line(
                        sw1_x,
                        sw1_y + device_height / 2 + offset,
                        sw2_x + device_width,
                        sw2_y + device_height / 2 + offset,
                        strokeColor=self.ipl_color,
                        strokeWidth=4,  # Doubled from 2
                    )
                    connection_group.add(line)

            drawing.add(connection_group)

            # Draw devices on top of connections
            device_group = Group()

            # Draw CBoxes
            for idx, cbox in enumerate(cboxes):
                if idx < len(cbox_positions):
                    x, y = cbox_positions[idx]
                    self._draw_device(
                        device_group,
                        x,
                        y,
                        device_width,
                        device_height,
                        f"CB{idx + 1}",
                        cbox.get("name", "CBox"),
                        "supermicro_gen5_cbox",
                        label_font_size,
                        name_font_size,
                    )

            # Draw Switches
            for switch_num, (x, y) in switch_positions.items():
                if switch_num <= len(switches):
                    switch = switches[switch_num - 1]
                    switch_name = f"SW{'A' if switch_num == 1 else 'B'}"
                    self._draw_device(
                        device_group,
                        x,
                        y,
                        device_width,
                        device_height,
                        switch_name,
                        switch.get("hostname", "Switch"),
                        "msn3700-vs2fc",
                        label_font_size,
                        name_font_size,
                    )

            # Draw DBoxes
            for idx, dbox in enumerate(dboxes):
                if idx < len(dbox_positions):
                    x, y = dbox_positions[idx]
                    self._draw_device(
                        device_group,
                        x,
                        y,
                        device_width,
                        device_height,
                        f"DB{idx + 1}",
                        dbox.get("name", "DBox"),
                        "ceres_v2",
                        label_font_size,
                        name_font_size,
                    )

            drawing.add(device_group)

            # Save diagram
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Save as PDF
            renderPDF.drawToFile(drawing, str(output_path), "Network Topology Diagram")
            self.logger.info(f"Network diagram saved to: {output_path}")

            # Try to also save as PNG for embedding in report
            png_path = output_path.with_suffix(".png")
            try:
                from reportlab.graphics import renderPM

                renderPM.drawToFile(drawing, str(png_path), fmt="PNG", dpi=150)
                self.logger.info(f"Network diagram also saved as PNG: {png_path}")
                return str(png_path)
            except Exception as e:
                self.logger.warning(
                    f"Could not save PNG ({e}). "
                    "Report will use placeholder image. "
                    "For dynamic diagram embedding, install: pip install reportlab[renderPM]"
                )
                # Return None to signal that PNG is not available
                return None

        except Exception as e:
            self.logger.error(f"Error generating network diagram: {e}", exc_info=True)
            return None

    def _calculate_positions(
        self,
        count: int,
        total_width: float,
        y: float,
        device_width: float,
        spacing: float,
    ) -> List[Tuple[float, float]]:
        """
        Calculate evenly-spaced positions for devices.

        Args:
            count: Number of devices
            total_width: Total available width
            y: Y coordinate
            device_width: Width of each device
            spacing: Spacing between devices

        Returns:
            List of (x, y) positions
        """
        if count == 0:
            return []

        # Calculate total width needed
        total_needed = count * device_width + (count - 1) * (spacing - device_width)

        # Center the devices
        start_x = (total_width - total_needed) / 2

        positions = []
        for i in range(count):
            x = start_x + i * spacing
            positions.append((x, y))

        return positions

    def _draw_device(
        self,
        group: Group,
        x: float,
        y: float,
        width: float,
        height: float,
        label: str,
        name: str,
        hardware_type: str,
        label_font_size: int = 20,
        name_font_size: int = 14,
    ):
        """
        Draw a device (box with label).

        Args:
            group: Group to add shapes to
            x: X coordinate
            y: Y coordinate
            width: Device width
            height: Device height
            label: Device label (e.g., "CB1")
            name: Device name
            hardware_type: Hardware type for image lookup
            label_font_size: Font size for main label
            name_font_size: Font size for device name
        """
        # Dynamic stroke width based on device size
        stroke_width = max(2, width / 40)
        
        # Draw box
        box = Rect(
            x,
            y,
            width,
            height,
            strokeColor=colors.HexColor("#2F2042"),
            strokeWidth=stroke_width,
            fillColor=colors.HexColor("#f2f2f7"),
        )
        group.add(box)

        # Try to load hardware image
        image_path = self.load_hardware_image(hardware_type)
        if image_path:
            try:
                from PIL import Image as PILImage

                # Load image to get actual dimensions
                with PILImage.open(image_path) as pil_img:
                    img_width, img_height = pil_img.size
                    aspect_ratio = img_width / img_height

                # Calculate size to fit within box while maintaining aspect ratio
                # Increased image area for larger boxes
                max_img_width = width * 0.85
                max_img_height = height * 0.5

                # Determine which dimension is the limiting factor
                if aspect_ratio > (max_img_width / max_img_height):
                    # Width is limiting
                    final_width = max_img_width
                    final_height = max_img_width / aspect_ratio
                else:
                    # Height is limiting
                    final_height = max_img_height
                    final_width = max_img_height * aspect_ratio

                # Center the image horizontally and position vertically
                img_x = x + (width - final_width) / 2
                img_y = y + height * 0.3

                # Add image inside box with preserved aspect ratio
                img = RLImage(
                    img_x,
                    img_y,
                    final_width,
                    final_height,
                    image_path,
                )
                group.add(img)
            except ImportError:
                # PIL not available, use original method
                img = RLImage(
                    x + width * 0.1,
                    y + height * 0.3,
                    width * 0.8,
                    height * 0.4,
                    image_path,
                )
                group.add(img)
            except Exception as e:
                self.logger.warning(f"Could not load image {image_path}: {e}")

        # Add label with dynamic font size
        label_spacing = max(5, height / 8)
        label_text = String(
            x + width / 2,
            y + height + label_spacing,
            label,
            fontSize=label_font_size,
            fontName="Helvetica-Bold",
            textAnchor="middle",
            fillColor=colors.HexColor("#2F2042"),
        )
        group.add(label_text)

        # Add name with dynamic font size
        name_spacing = max(10, height / 4)
        name_text = String(
            x + width / 2,
            y - name_spacing,
            name,
            fontSize=name_font_size,
            fontName="Helvetica",
            textAnchor="middle",
            fillColor=colors.HexColor("#666666"),
        )
        group.add(name_text)


def create_network_diagram_generator(
    assets_path: str = "assets",
) -> NetworkDiagramGenerator:
    """
    Create and return a NetworkDiagramGenerator instance.

    Args:
        assets_path: Path to assets directory

    Returns:
        NetworkDiagramGenerator instance
    """
    return NetworkDiagramGenerator(assets_path)


if __name__ == "__main__":
    """Test the network diagram generator."""
    import sys

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info("Network Diagram Generator Test")
    logger.info("This module generates logical network topology diagrams")
    logger.info("Ready for integration with report builder")
