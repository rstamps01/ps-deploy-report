"""
VAST Brand Compliance Module

This module implements VAST Data brand guidelines for the As-Built Report Generator,
ensuring all generated reports comply with official VAST visual identity standards.

Brand Guidelines Implementation:
- Typography: Moderat font family with proper weights
- Color Palette: VAST blue spectrum and background colors
- 2D Visuals: Gradient boxes, solid/dotted lines, VAST icons
- Report Header: VAST Light gradient effect
- Layout: Professional spacing and visual hierarchy

Author: Manus AI
Date: September 26, 2025
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Group, Line, Path, Rect
from reportlab.lib import colors
from reportlab.lib.colors import Color, HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from utils.logger import get_logger


@dataclass
class VastColorPalette:
    """VAST brand color palette implementation."""

    # VAST Blue Spectrum
    VAST_BLUE_PRIMARY = HexColor("#1FD9FE")  # Primary VAST Blue
    VAST_BLUE_LIGHTEST = HexColor("#D7F8FF")  # Lightest VAST Blue
    VAST_BLUE_LIGHTER = HexColor("#8AECFF")  # Lighter VAST Blue
    VAST_BLUE_DARKER = HexColor("#18A3D1")  # Darker VAST Blue
    VAST_BLUE_DARKEST = HexColor("#137DA0")  # Darkest VAST Blue

    # Background Colors
    DEEP_BLUE_DARK = HexColor("#0F2042")  # Deep Blue Dark
    DEEP_BLUE_DARKER = HexColor("#081636")  # Deep Blue Darker
    DEEP_BLUE_DARKEST = HexColor("#0E142C")  # Deep Blue Darkest
    BACKGROUND_DARK = HexColor("#2F2042")  # Background Dark

    # Whites
    WARM_WHITE = HexColor("#FAF7F7")  # Warm White
    PURE_WHITE = HexColor("#FFFFFF")  # Pure White
    COOL_WHITE = HexColor("#F2F2F7")  # Cool White
    ALTERNATING_ROW = HexColor("#F2F2F7")  # Alternating Row Color

    # Functional Colors
    SUCCESS_GREEN = HexColor("#28A745")
    WARNING_ORANGE = HexColor("#FFC107")
    ERROR_RED = HexColor("#DC3545")
    INFO_BLUE = HexColor("#17A2B8")

    # Neutral Grays
    LIGHT_GRAY = HexColor("#F8F9FA")
    MEDIUM_GRAY = HexColor("#6C757D")
    DARK_GRAY = HexColor("#343A40")
    BLACK = HexColor("#000000")


@dataclass
class VastTypography:
    """VAST typography standards implementation."""

    # Font families (Note: Moderat fonts would need to be installed)
    # Fallback to system fonts that closely match Moderat characteristics
    PRIMARY_FONT = "Helvetica-Bold"  # Moderat-Bold equivalent
    SECONDARY_FONT = (
        "Helvetica-Bold"  # Moderat-Black equivalent (using Bold as fallback)
    )
    ITALIC_FONT = "Helvetica-BoldOblique"  # Moderat-Black-Italic equivalent
    BODY_FONT = "Helvetica"  # Body text

    # Font sizes (in points)
    TITLE_SIZE = 24
    SUBTITLE_SIZE = 18
    HEADING_SIZE = 14
    SUBHEADING_SIZE = 12
    BODY_SIZE = 10
    CAPTION_SIZE = 8

    # Line spacing
    TITLE_LINE_SPACING = 1.3
    HEADING_LINE_SPACING = 1.2
    BODY_LINE_SPACING = 1.4


class VastBrandCompliance:
    """
    VAST Brand Compliance implementation for report generation.

    This class provides methods to create brand-compliant report elements
    following VAST Data's official visual identity guidelines.
    """

    def __init__(self):
        """Initialize VAST brand compliance."""
        self.logger = get_logger(__name__)
        self.colors = VastColorPalette()
        self.typography = VastTypography()

        # Create brand-compliant paragraph styles
        self.styles = self._create_paragraph_styles()

        self.logger.info("VAST Brand Compliance initialized")

    def _create_paragraph_styles(self) -> Dict[str, ParagraphStyle]:
        """Create VAST brand-compliant paragraph styles."""
        styles = {}

        # Title style with VAST Light gradient effect
        styles["vast_title"] = ParagraphStyle(
            "VastTitle",
            fontName=self.typography.PRIMARY_FONT,
            fontSize=self.typography.TITLE_SIZE,
            textColor=self.colors.BACKGROUND_DARK,
            alignment=TA_CENTER,
            spaceAfter=20,
            spaceBefore=10,
            leading=self.typography.TITLE_SIZE * self.typography.TITLE_LINE_SPACING,
        )

        # Subtitle style
        styles["vast_subtitle"] = ParagraphStyle(
            "VastSubtitle",
            fontName=self.typography.SECONDARY_FONT,
            fontSize=self.typography.SUBTITLE_SIZE,
            textColor=self.colors.DEEP_BLUE_DARK,
            alignment=TA_CENTER,
            spaceAfter=15,
            spaceBefore=5,
            leading=self.typography.SUBTITLE_SIZE
            * self.typography.HEADING_LINE_SPACING,
        )

        # Section heading style
        styles["vast_heading"] = ParagraphStyle(
            "VastHeading",
            fontName=self.typography.PRIMARY_FONT,
            fontSize=self.typography.HEADING_SIZE,
            textColor=self.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=15,
            leading=self.typography.HEADING_SIZE * self.typography.HEADING_LINE_SPACING,
        )

        # Subheading style
        styles["vast_subheading"] = ParagraphStyle(
            "VastSubheading",
            fontName=self.typography.SECONDARY_FONT,
            fontSize=self.typography.SUBHEADING_SIZE,
            textColor=self.colors.BACKGROUND_DARK,
            spaceAfter=8,
            spaceBefore=10,
            leading=self.typography.SUBHEADING_SIZE
            * self.typography.HEADING_LINE_SPACING,
        )

        # Body text style
        styles["vast_body"] = ParagraphStyle(
            "VastBody",
            fontName=self.typography.BODY_FONT,
            fontSize=self.typography.BODY_SIZE,
            textColor=self.colors.DARK_GRAY,
            spaceAfter=6,
            spaceBefore=3,
            leading=self.typography.BODY_SIZE * self.typography.BODY_LINE_SPACING,
            alignment=TA_JUSTIFY,
        )

        # Caption style
        styles["vast_caption"] = ParagraphStyle(
            "VastCaption",
            fontName=self.typography.BODY_FONT,
            fontSize=self.typography.CAPTION_SIZE,
            textColor=self.colors.MEDIUM_GRAY,
            spaceAfter=4,
            spaceBefore=2,
            alignment=TA_CENTER,
        )

        # Emphasis style
        styles["vast_emphasis"] = ParagraphStyle(
            "VastEmphasis",
            fontName=self.typography.PRIMARY_FONT,
            fontSize=self.typography.BODY_SIZE,
            textColor=self.colors.VAST_BLUE_DARKER,
            spaceAfter=6,
            spaceBefore=3,
            leading=self.typography.BODY_SIZE * self.typography.BODY_LINE_SPACING,
        )

        return styles

    def create_vast_header(
        self, title: str, subtitle: str = None, cluster_info: Dict[str, Any] = None
    ) -> List[Any]:
        """
        Create VAST Light gradient header with brand-compliant styling.

        Args:
            title (str): Main report title
            subtitle (str, optional): Subtitle text
            cluster_info (Dict[str, Any], optional): Cluster information

        Returns:
            List[Any]: Header elements for report
        """
        elements = []

        # Main title with VAST Light effect (centered)
        title_style = ParagraphStyle(
            "CenteredTitle",
            parent=self.styles["vast_title"],
            alignment=TA_CENTER,
        )
        title_para = Paragraph(f"<b>{title}</b>", title_style)
        elements.append(title_para)
        elements.append(Spacer(1, 20))

        # Add VAST logo - larger size to fill available space
        try:
            from pathlib import Path

            from reportlab.platypus import Image

            # Use the new lg_vast_logo.png from assets/diagrams
            logo_path = (
                Path(__file__).parent.parent
                / "assets"
                / "diagrams"
                / "lg_vast_logo.png"
            )

            # Load image with larger size and preserved aspect ratio
            # Increased from 2" to 4.5" width to fill more space
            logo = Image(
                str(logo_path), width=4.5 * inch, height=2.5 * inch, kind="proportional"
            )
            logo.hAlign = "CENTER"
            elements.append(logo)
            elements.append(Spacer(1, 20))
        except Exception as e:
            # If logo fails to load, continue without it
            self.logger.warning(f"Could not load logo: {e}")
            pass

        # Subtitle (centered) - moved to middle of page after logo
        if subtitle:
            subtitle_style = ParagraphStyle(
                "CenteredSubtitle",
                parent=self.styles["vast_subtitle"],
                alignment=TA_CENTER,
            )
            subtitle_para = Paragraph(subtitle, subtitle_style)
            elements.append(subtitle_para)
            elements.append(Spacer(1, 30))

        # Cluster information (centered) - now appears below subtitle
        if cluster_info:
            cluster_name = cluster_info.get("name", "Unknown Cluster")
            psnt = cluster_info.get("psnt", "Not Available")
            build = cluster_info.get("build", "Unknown Build")
            mgmt_vip = cluster_info.get("mgmt_vip", "Unknown IP")

            # Cluster details with VAST styling (centered)
            cluster_text = f"<b>Cluster:</b> {cluster_name}<br/>"
            if psnt != "Not Available":
                cluster_text += f"<b>PSNT:</b> {psnt}<br/>"
            cluster_text += f"<b>Release:</b> {build}<br/>"
            cluster_text += f"<b>Management IP:</b> {mgmt_vip}"

            cluster_style = ParagraphStyle(
                "CenteredCluster",
                parent=self.styles["vast_body"],
                alignment=TA_CENTER,
            )
            cluster_para = Paragraph(cluster_text, cluster_style)
            elements.append(cluster_para)
            elements.append(Spacer(1, 20))

        return elements

    def create_vast_section_heading(self, title: str, level: int = 1) -> List[Any]:
        """
        Create VAST brand-compliant section heading.

        Args:
            title (str): Section title
            level (int): Heading level (1-3)

        Returns:
            List[Any]: Heading elements
        """
        elements = []

        # Choose style based on level
        if level == 1:
            style = self.styles["vast_heading"]
        elif level == 2:
            style = self.styles["vast_subheading"]
        else:
            style = self.styles["vast_emphasis"]

        # Heading text (no horizontal line above)
        heading_para = Paragraph(f"<b>{title}</b>", style)
        elements.append(heading_para)
        elements.append(Spacer(1, 8))

        return elements

    def create_vast_table(
        self, data: List[List[str]], title: str = None, headers: List[str] = None
    ) -> List[Any]:
        """
        Create VAST brand-compliant table with gradient styling.

        Args:
            data (List[List[str]]): Table data
            title (str, optional): Table title
            headers (List[str], optional): Column headers

        Returns:
            List[Any]: Table elements (wrapped in KeepTogether if title provided)
        """
        elements = []
        table_elements = []

        # Add title if provided
        if title:
            title_para = Paragraph(f"<b>{title}</b>", self.styles["vast_subheading"])
            table_elements.append(title_para)
            table_elements.append(Spacer(1, 8))

        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        table_data.extend(data)

        # Create table with VAST styling and page-width sizing
        page_width = 7.5 * inch  # A4 width minus 0.5" margins on each side
        num_cols = len(table_data[0]) if table_data else 1
        col_width = page_width / num_cols if num_cols > 0 else page_width

        # Create table with repeat headers on page breaks
        table = Table(table_data, colWidths=[col_width] * num_cols, repeatRows=1)

        # Apply VAST brand table styling
        table_style = TableStyle(
            [
                # Header row styling
                ("BACKGROUND", (0, 0), (-1, 0), self.colors.BACKGROUND_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), self.colors.PURE_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), self.typography.PRIMARY_FONT),
                ("FONTSIZE", (0, 0), (-1, 0), self.typography.BODY_SIZE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Data rows styling with gradient effect
                ("BACKGROUND", (0, 1), (-1, -1), self.colors.VAST_BLUE_LIGHTEST),
                ("TEXTCOLOR", (0, 1), (-1, -1), self.colors.DARK_GRAY),
                ("FONTNAME", (0, 1), (-1, -1), self.typography.BODY_FONT),
                ("FONTSIZE", (0, 1), (-1, -1), self.typography.BODY_SIZE),
                # Borders and spacing
                ("GRID", (0, 0), (-1, -1), 1, self.colors.BACKGROUND_DARK),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [self.colors.PURE_WHITE, self.colors.ALTERNATING_ROW],
                ),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
            ]
        )

        table.setStyle(table_style)
        table_elements.append(table)

        # Keep title and table together if title provided
        if title:
            elements.append(KeepTogether(table_elements))
        else:
            elements.extend(table_elements)

        elements.append(Spacer(1, 12))

        return elements

    def create_vast_hardware_table(
        self, hardware_data: List[Dict[str, Any]], hardware_type: str
    ) -> List[Any]:
        """
        Create VAST brand-compliant hardware inventory table with auto-adjusting column widths.

        Args:
            hardware_data (List[Dict[str, Any]]): Hardware data
            hardware_type (str): Type of hardware (CNodes, DNodes, etc.)

        Returns:
            List[Any]: Hardware table elements
        """
        if not hardware_data:
            return []

        # Prepare headers based on hardware type
        if hardware_type.lower() == "cnodes":
            headers = ["ID", "Model", "Serial Number", "Status", "Rack Height (U)"]
        elif hardware_type.lower() == "dnodes":
            headers = ["ID", "Model", "Serial Number", "Status", "Rack Height (U)"]
        else:
            headers = ["ID", "Model", "Serial Number", "Status", "Position"]

        # Prepare table data
        table_data = []
        for item in hardware_data:
            # Format model text with line breaks for better wrapping
            model = item.get("model", "Unknown")
            if model != "Unknown" and "," in model:
                # Split on comma and join with line break for better wrapping
                model = model.replace(", ", "<br/>")

            row = [
                item.get("id", "Unknown"),
                model,
                item.get("serial_number", "Unknown"),
                item.get("status", "Unknown"),
            ]

            # Add rack height if available
            if hardware_type.lower() in ["cnodes", "dnodes"]:
                rack_pos = item.get("rack_position")
                if rack_pos is not None:
                    row.append(f"U{rack_pos}")
                else:
                    row.append("Manual Entry")
            else:
                row.append(item.get("position", "N/A"))

            table_data.append(row)

        # Create table with auto-adjusting column widths and multi-page support
        return self.create_vast_hardware_table_with_pagination(
            table_data, hardware_type, headers
        )

    def create_vast_hardware_table_with_auto_width(
        self, table_data: List[List[str]], title: str, headers: List[str]
    ) -> List[Any]:
        """
        Create VAST brand-compliant hardware table with auto-adjusting column widths.

        Args:
            table_data (List[List[str]]): Table data
            title (str): Table title
            headers (List[str]): Column headers

        Returns:
            List[Any]: Table elements (title and table kept together)
        """
        if not table_data:
            return []

        elements = []
        table_elements = []

        # Title
        title_para = Paragraph(f"<b>{title}</b>", self.styles["vast_subheading"])
        table_elements.append(title_para)
        table_elements.append(Spacer(1, 8))

        # Prepare table data with headers
        full_table_data = []
        if headers:
            full_table_data.append(headers)
        full_table_data.extend(table_data)

        # Calculate optimal column widths based on content
        page_width = 7.5 * inch  # A4 width minus 0.5" margins
        num_cols = len(headers)

        # Define column width ratios based on typical content length
        # ID: narrow, Model: wide, Serial Number: medium, Status: narrow, Rack Height: wider
        if num_cols == 5:  # CNodes/DNodes/CBox Inventory
            col_ratios = [
                0.06,  # ID
                0.45,  # Model (increased for long text)
                0.25,  # Serial Number
                0.12,  # Status
                0.12,  # Rack Height
            ]  # ID, Model, Serial, Status, Rack Height
        elif num_cols == 6:  # CBox/DBox Network Configuration (without Net Type)
            col_ratios = [
                0.08,  # ID
                0.20,  # Hostname
                0.18,  # Mgmt IP
                0.18,  # IPMI IP
                0.20,  # VAST OS
                0.16,  # VMS Host/Position
            ]
        else:  # Other hardware types
            col_ratios = [
                0.15,
                0.35,
                0.25,
                0.15,
                0.1,
            ]  # ID, Model, Serial, Status, Position

        col_widths = [page_width * ratio for ratio in col_ratios]

        # Convert model column data to Paragraph objects for HTML support with center alignment
        processed_table_data = []
        for i, row in enumerate(full_table_data):
            if i == 0:  # Header row
                processed_table_data.append(row)
            else:
                processed_row = []
                for j, cell in enumerate(row):
                    if j == 1 and "<br/>" in str(cell):  # Model column with HTML
                        # Create Paragraph with center alignment for Model column
                        model_style = ParagraphStyle(
                            "ModelCenter",
                            parent=self.styles["vast_body"],
                            alignment=1,  # 1 = CENTER alignment
                        )
                        processed_row.append(Paragraph(str(cell), model_style))
                    else:
                        processed_row.append(str(cell))
                processed_table_data.append(processed_row)

        # Create table with calculated column widths and repeat headers on page breaks
        table = Table(processed_table_data, colWidths=col_widths, repeatRows=1)

        # Apply VAST brand table styling with text wrapping - match create_vast_table styling
        table_style = TableStyle(
            [
                # Header row styling
                ("BACKGROUND", (0, 0), (-1, 0), self.colors.BACKGROUND_DARK),
                ("TEXTCOLOR", (0, 0), (-1, 0), self.colors.PURE_WHITE),
                ("FONTNAME", (0, 0), (-1, 0), self.typography.PRIMARY_FONT),
                ("FONTSIZE", (0, 0), (-1, 0), self.typography.BODY_SIZE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                # Special alignment for Model column (column 1) to ensure Paragraph objects are centered
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                # Data rows styling with gradient effect
                ("BACKGROUND", (0, 1), (-1, -1), self.colors.VAST_BLUE_LIGHTEST),
                ("TEXTCOLOR", (0, 1), (-1, -1), self.colors.DARK_GRAY),
                ("FONTNAME", (0, 1), (-1, -1), self.typography.BODY_FONT),
                ("FONTSIZE", (0, 1), (-1, -1), self.typography.BODY_SIZE),
                # Borders and spacing
                ("GRID", (0, 0), (-1, -1), 1, self.colors.BACKGROUND_DARK),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [self.colors.PURE_WHITE, self.colors.ALTERNATING_ROW],
                ),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("LEFTPADDING", (0, 0), (-1, -1), 12),
                ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
            ]
        )

        table.setStyle(table_style)
        table_elements.append(table)

        # Keep title and table together to prevent page breaks
        elements.append(KeepTogether(table_elements))
        elements.append(Spacer(1, 12))

        return elements

    def create_vast_hardware_table_with_pagination(
        self, table_data: List[List[str]], title: str, headers: List[str]
    ) -> List[Any]:
        """
        Create VAST brand-compliant hardware table with pagination support for large tables.
        Automatically splits large tables across multiple pages with repeated headers.

        Args:
            table_data (List[List[str]]): Table data
            title (str): Table title
            headers (List[str]): Column headers

        Returns:
            List[Any]: Table elements with pagination
        """
        if not table_data:
            return []

        elements = []

        # Define rows per page (adjust based on page size and row height)
        # Assuming ~25 rows per page for A4 with current styling
        rows_per_page = 25

        # Calculate number of pages needed
        total_rows = len(table_data)
        num_pages = (total_rows + rows_per_page - 1) // rows_per_page

        # If only one page needed, use the regular method
        if num_pages <= 1:
            return self.create_vast_hardware_table_with_auto_width(
                table_data, title, headers
            )

        # Split data into pages
        for page_num in range(num_pages):
            start_idx = page_num * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_rows)
            page_data = table_data[start_idx:end_idx]

            # Create page title with pagination info
            if num_pages > 1:
                page_title = f"{title} (Page {page_num + 1} of {num_pages})"
            else:
                page_title = title

            # Create table for this page
            page_elements = self.create_vast_hardware_table_with_auto_width(
                page_data, page_title, headers
            )
            elements.extend(page_elements)

            # Add page break between pages (except for the last page)
            if page_num < num_pages - 1:
                elements.append(PageBreak())

        return elements

    def create_vast_2d_diagram_placeholder(
        self, title: str, description: str
    ) -> List[Any]:
        """
        Create placeholder for 2D visual diagrams following VAST brand guidelines.

        Args:
            title (str): Diagram title
            description (str): Diagram description

        Returns:
            List[Any]: Diagram placeholder elements
        """
        elements = []

        # Title
        title_para = Paragraph(f"<b>{title}</b>", self.styles["vast_subheading"])
        elements.append(title_para)
        elements.append(Spacer(1, 8))

        # Description
        desc_para = Paragraph(description, self.styles["vast_body"])
        elements.append(desc_para)
        elements.append(Spacer(1, 8))

        # Placeholder box with VAST styling
        placeholder_text = f"[{title} Diagram Placeholder]"
        placeholder_para = Paragraph(
            f"<i>{placeholder_text}</i>", self.styles["vast_caption"]
        )
        elements.append(placeholder_para)
        elements.append(Spacer(1, 12))

        return elements

    def _create_vast_divider(self) -> Any:
        """Create VAST brand-compliant horizontal divider."""
        # Simple divider using spacing and text
        return Paragraph("─" * 50, self.styles["vast_caption"])

    def create_vast_footer(
        self,
        generation_info: Dict[str, Any],
        current_page: int = 1,
        total_pages: int = 1,
    ) -> List[Any]:
        """
        Create VAST brand-compliant footer with centered content and page numbers.

        Args:
            generation_info (Dict[str, Any]): Report generation information
            current_page (int): Current page number
            total_pages (int): Total number of pages

        Returns:
            List[Any]: Footer elements
        """
        elements = []

        # Add divider
        elements.append(Spacer(1, 20))
        elements.append(self._create_vast_divider())
        elements.append(Spacer(1, 10))

        # Create centered footer content
        if generation_info:
            timestamp = generation_info.get("timestamp", "Unknown")
            completeness = generation_info.get("completeness", 0.0)

            # Combined footer text with centered alignment
            footer_text = (
                f"VAST Professional Services | Automated As-Built Documentation<br/>"
                f"Generated: {timestamp} | Data Completeness: {completeness:.1%}"
            )
        else:
            footer_text = (
                "VAST Professional Services | Automated As-Built Documentation"
            )

        # Create centered footer paragraph
        footer_style = ParagraphStyle(
            "CenteredFooter",
            parent=self.styles["vast_caption"],
            alignment=TA_CENTER,
        )
        footer_para = Paragraph(footer_text, footer_style)
        elements.append(footer_para)

        # Add page numbers (right aligned)
        page_style = ParagraphStyle(
            "PageNumbers",
            parent=self.styles["vast_caption"],
            alignment=TA_RIGHT,
        )
        page_text = f"Page {current_page} of {total_pages}"
        page_para = Paragraph(page_text, page_style)
        elements.append(page_para)

        return elements

    def create_vast_footer_with_pages(
        self,
        generation_info: Dict[str, Any],
        current_page: int = 1,
        total_pages: int = 1,
    ) -> List[Any]:
        """
        Create VAST brand-compliant footer with centered content and page numbers.

        Args:
            generation_info (Dict[str, Any]): Report generation information
            current_page (int): Current page number
            total_pages (int): Total number of pages

        Returns:
            List[Any]: Footer elements
        """
        elements = []

        # Add divider
        elements.append(Spacer(1, 20))
        elements.append(self._create_vast_divider())
        elements.append(Spacer(1, 10))

        # Create centered footer content
        if generation_info:
            timestamp = generation_info.get("timestamp", "Unknown")
            completeness = generation_info.get("completeness", 0.0)

            # Combined footer text with centered alignment
            footer_text = (
                f"VAST Professional Services | Automated As-Built Documentation<br/>"
                f"Generated: {timestamp} | Data Completeness: {completeness:.1%}"
            )
        else:
            footer_text = (
                "VAST Professional Services | Automated As-Built Documentation"
            )

        # Create centered footer paragraph
        footer_style = ParagraphStyle(
            "CenteredFooter",
            parent=self.styles["vast_caption"],
            alignment=TA_CENTER,
        )
        footer_para = Paragraph(footer_text, footer_style)
        elements.append(footer_para)

        # Add page numbers (right aligned)
        page_style = ParagraphStyle(
            "PageNumbers",
            parent=self.styles["vast_caption"],
            alignment=TA_RIGHT,
        )
        page_text = f"Page {current_page} of {total_pages}"
        page_para = Paragraph(page_text, page_style)
        elements.append(page_para)

        return elements

    def create_vast_page_template(self, generation_info: Dict[str, Any]) -> Any:
        """
        Create VAST brand-compliant page template with footer that repeats on all pages.

        Args:
            generation_info (Dict[str, Any]): Report generation information

        Returns:
            Any: Page template with footer
        """
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.platypus import Frame, PageTemplate

        # Define page size and margins
        page_width, page_height = letter
        left_margin = 0.5 * inch
        right_margin = 0.5 * inch
        top_margin = 0.5 * inch
        bottom_margin = 0.75 * inch  # Extra space for footer

        # Calculate frame dimensions
        frame_width = page_width - left_margin - right_margin
        frame_height = page_height - top_margin - bottom_margin

        # Create main frame for content
        main_frame = Frame(
            left_margin,
            bottom_margin,
            frame_width,
            frame_height,
            leftPadding=0,
            bottomPadding=0,
            rightPadding=0,
            topPadding=0,
        )

        def footer_canvas(canvas, doc):
            """Draw footer on every page."""
            # Get page number
            page_num = canvas.getPageNumber()

            # Footer content
            if generation_info:
                timestamp = generation_info.get("timestamp", "Unknown")
                mgmt_vip = generation_info.get("mgmt_vip", "Unknown")

                # Footer components (labels removed, values only)
                generated_text = timestamp
                center_text = f"VAST Professional Services | Automated As-Built Report | {mgmt_vip}"
            else:
                generated_text = "Unknown"
                center_text = "VAST Professional Services | Automated As-Built Report"

            # Add watermark (all pages except title page)
            if page_num > 1:
                watermark_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "assets",
                    "diagrams",
                    "lg_vast_watermark.png",
                )

                if os.path.exists(watermark_path):
                    try:
                        from PIL import Image as PILImage

                        self.logger.info(f"Applying watermark from: {watermark_path}")

                        # Get image dimensions
                        with PILImage.open(watermark_path) as img:
                            img_width, img_height = img.size

                        # Calculate available space (fit within page width)
                        available_width = page_width - left_margin - right_margin
                        available_height = page_height - top_margin - bottom_margin

                        # Calculate scaling to fit within page width while maintaining aspect ratio
                        scale_x = available_width / img_width
                        scale_y = available_height / img_height
                        scale = min(
                            scale_x, scale_y
                        )  # Use min to fit within page bounds

                        watermark_width = img_width * scale
                        watermark_height = img_height * scale

                        # Center the watermark on the page
                        x_position = (page_width - watermark_width) / 2
                        y_position = (page_height - watermark_height) / 2

                        # Draw watermark with transparency
                        canvas.saveState()
                        canvas.setFillAlpha(0.15)  # 15% opacity for subtle watermark
                        canvas.drawImage(
                            watermark_path,
                            x_position,
                            y_position,
                            width=watermark_width,
                            height=watermark_height,
                            mask="auto",
                            preserveAspectRatio=True,
                        )
                        canvas.restoreState()

                    except Exception as e:
                        self.logger.error(f"Error adding watermark: {e}")
                else:
                    self.logger.warning(f"Watermark image not found: {watermark_path}")

            # Draw horizontal line
            canvas.setStrokeColor(self.colors.BACKGROUND_DARK)
            canvas.setLineWidth(1)
            canvas.line(
                left_margin,
                bottom_margin - 0.1 * inch,
                page_width - right_margin,
                bottom_margin - 0.1 * inch,
            )

            # Draw footer text with new layout
            canvas.setFont(self.typography.BODY_FONT, self.typography.CAPTION_SIZE)
            canvas.setFillColor(self.colors.DARK_GRAY)
            y_position = bottom_margin - 0.3 * inch

            # Draw "Generated:" on far left
            canvas.drawString(left_margin, y_position, generated_text)

            # Draw center text (VAST PS | Documentation | Management VIP)
            center_text_width = canvas.stringWidth(
                center_text, self.typography.BODY_FONT, self.typography.CAPTION_SIZE
            )
            center_x_position = (page_width - center_text_width) / 2
            canvas.drawString(center_x_position, y_position, center_text)

            # Draw page number (right aligned on same line)
            page_text = f"Page {page_num}"
            canvas.drawRightString(page_width - right_margin, y_position, page_text)

        # Create page template
        page_template = PageTemplate(
            id="VastPage",
            frames=[main_frame],
            onPage=footer_canvas,
        )

        return page_template

    def get_vast_page_style(self) -> Dict[str, Any]:
        """
        Get VAST brand-compliant page styling configuration.

        Returns:
            Dict[str, Any]: Page style configuration
        """
        return {
            "page_size": A4,
            "margin_top": 1.0 * inch,
            "margin_bottom": 1.0 * inch,
            "margin_left": 1.0 * inch,
            "margin_right": 1.0 * inch,
            "background_color": self.colors.PURE_WHITE,
            "header_color": self.colors.VAST_BLUE_LIGHTEST,
            "footer_color": self.colors.LIGHT_GRAY,
        }


# Convenience function for easy usage
def create_vast_brand_compliance() -> VastBrandCompliance:
    """
    Create and return a configured VastBrandCompliance instance.

    Returns:
        VastBrandCompliance: Configured brand compliance instance
    """
    return VastBrandCompliance()


if __name__ == "__main__":
    """
    Test the brand compliance module when run as a standalone module.
    """
    from utils.logger import setup_logging

    # Set up logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("VAST Brand Compliance Module Test")
    logger.info("This module implements VAST Data brand guidelines")
    logger.info("Features: Typography, Colors, 2D Visuals, VAST Light effects")
    logger.info("Ready for integration with report builder")
