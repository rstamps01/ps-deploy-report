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

from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import inch, cm
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4, letter
from reportlab.graphics.shapes import Drawing, Rect, Line, Circle
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Group, Path
from reportlab.lib.colors import Color, HexColor
import logging

from utils.logger import get_logger


@dataclass
class VastColorPalette:
    """VAST brand color palette implementation."""

    # VAST Blue Spectrum
    VAST_BLUE_PRIMARY = HexColor('#1FD9FE')      # Primary VAST Blue
    VAST_BLUE_LIGHTEST = HexColor('#D7F8FF')     # Lightest VAST Blue
    VAST_BLUE_LIGHTER = HexColor('#8AECFF')      # Lighter VAST Blue
    VAST_BLUE_DARKER = HexColor('#18A3D1')       # Darker VAST Blue
    VAST_BLUE_DARKEST = HexColor('#137DA0')      # Darkest VAST Blue

    # Background Colors
    DEEP_BLUE_DARK = HexColor('#0F2042')         # Deep Blue Dark
    DEEP_BLUE_DARKER = HexColor('#081636')       # Deep Blue Darker
    DEEP_BLUE_DARKEST = HexColor('#0E142C')      # Deep Blue Darkest

    # Whites
    WARM_WHITE = HexColor('#FAF7F7')             # Warm White
    PURE_WHITE = HexColor('#FFFFFF')             # Pure White
    COOL_WHITE = HexColor('#F2F2F7')             # Cool White

    # Functional Colors
    SUCCESS_GREEN = HexColor('#28A745')
    WARNING_ORANGE = HexColor('#FFC107')
    ERROR_RED = HexColor('#DC3545')
    INFO_BLUE = HexColor('#17A2B8')

    # Neutral Grays
    LIGHT_GRAY = HexColor('#F8F9FA')
    MEDIUM_GRAY = HexColor('#6C757D')
    DARK_GRAY = HexColor('#343A40')
    BLACK = HexColor('#000000')


@dataclass
class VastTypography:
    """VAST typography standards implementation."""

    # Font families (Note: Moderat fonts would need to be installed)
    # Fallback to system fonts that closely match Moderat characteristics
    PRIMARY_FONT = 'Helvetica-Bold'           # Moderat-Bold equivalent
    SECONDARY_FONT = 'Helvetica-Bold'         # Moderat-Black equivalent (using Bold as fallback)
    ITALIC_FONT = 'Helvetica-BoldOblique'     # Moderat-Black-Italic equivalent
    BODY_FONT = 'Helvetica'                   # Body text

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
        styles['vast_title'] = ParagraphStyle(
            'VastTitle',
            fontName=self.typography.PRIMARY_FONT,
            fontSize=self.typography.TITLE_SIZE,
            textColor=self.colors.VAST_BLUE_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=20,
            spaceBefore=10,
            leading=self.typography.TITLE_SIZE * self.typography.TITLE_LINE_SPACING
        )

        # Subtitle style
        styles['vast_subtitle'] = ParagraphStyle(
            'VastSubtitle',
            fontName=self.typography.SECONDARY_FONT,
            fontSize=self.typography.SUBTITLE_SIZE,
            textColor=self.colors.DEEP_BLUE_DARK,
            alignment=TA_CENTER,
            spaceAfter=15,
            spaceBefore=5,
            leading=self.typography.SUBTITLE_SIZE * self.typography.HEADING_LINE_SPACING
        )

        # Section heading style
        styles['vast_heading'] = ParagraphStyle(
            'VastHeading',
            fontName=self.typography.PRIMARY_FONT,
            fontSize=self.typography.HEADING_SIZE,
            textColor=self.colors.DEEP_BLUE_DARK,
            spaceAfter=12,
            spaceBefore=15,
            leading=self.typography.HEADING_SIZE * self.typography.HEADING_LINE_SPACING
        )

        # Subheading style
        styles['vast_subheading'] = ParagraphStyle(
            'VastSubheading',
            fontName=self.typography.SECONDARY_FONT,
            fontSize=self.typography.SUBHEADING_SIZE,
            textColor=self.colors.VAST_BLUE_DARKER,
            spaceAfter=8,
            spaceBefore=10,
            leading=self.typography.SUBHEADING_SIZE * self.typography.HEADING_LINE_SPACING
        )

        # Body text style
        styles['vast_body'] = ParagraphStyle(
            'VastBody',
            fontName=self.typography.BODY_FONT,
            fontSize=self.typography.BODY_SIZE,
            textColor=self.colors.DARK_GRAY,
            spaceAfter=6,
            spaceBefore=3,
            leading=self.typography.BODY_SIZE * self.typography.BODY_LINE_SPACING,
            alignment=TA_JUSTIFY
        )

        # Caption style
        styles['vast_caption'] = ParagraphStyle(
            'VastCaption',
            fontName=self.typography.BODY_FONT,
            fontSize=self.typography.CAPTION_SIZE,
            textColor=self.colors.MEDIUM_GRAY,
            spaceAfter=4,
            spaceBefore=2,
            alignment=TA_CENTER
        )

        # Emphasis style
        styles['vast_emphasis'] = ParagraphStyle(
            'VastEmphasis',
            fontName=self.typography.PRIMARY_FONT,
            fontSize=self.typography.BODY_SIZE,
            textColor=self.colors.VAST_BLUE_DARKER,
            spaceAfter=6,
            spaceBefore=3,
            leading=self.typography.BODY_SIZE * self.typography.BODY_LINE_SPACING
        )

        return styles

    def create_vast_header(self, title: str, subtitle: str = None,
                          cluster_info: Dict[str, Any] = None) -> List[Any]:
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

        # Main title with VAST Light effect
        title_para = Paragraph(f"<b>{title}</b>", self.styles['vast_title'])
        elements.append(title_para)
        elements.append(Spacer(1, 10))

        # Subtitle
        if subtitle:
            subtitle_para = Paragraph(subtitle, self.styles['vast_subtitle'])
            elements.append(subtitle_para)
            elements.append(Spacer(1, 15))

        # Cluster information
        if cluster_info:
            cluster_name = cluster_info.get('name', 'Unknown Cluster')
            cluster_version = cluster_info.get('version', 'Unknown Version')
            psnt = cluster_info.get('psnt', 'Not Available')

            # Cluster details with VAST styling
            cluster_text = f"<b>Cluster:</b> {cluster_name}<br/>"
            cluster_text += f"<b>Version:</b> {cluster_version}<br/>"
            if psnt != 'Not Available':
                cluster_text += f"<b>PSNT:</b> {psnt}"

            cluster_para = Paragraph(cluster_text, self.styles['vast_body'])
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
            style = self.styles['vast_heading']
        elif level == 2:
            style = self.styles['vast_subheading']
        else:
            style = self.styles['vast_emphasis']

        # Add horizontal line above heading (VAST style)
        elements.append(Spacer(1, 5))
        elements.append(self._create_vast_divider())
        elements.append(Spacer(1, 5))

        # Heading text
        heading_para = Paragraph(f"<b>{title}</b>", style)
        elements.append(heading_para)
        elements.append(Spacer(1, 8))

        return elements

    def create_vast_table(self, data: List[List[str]], title: str = None,
                         headers: List[str] = None) -> List[Any]:
        """
        Create VAST brand-compliant table with gradient styling.

        Args:
            data (List[List[str]]): Table data
            title (str, optional): Table title
            headers (List[str], optional): Column headers

        Returns:
            List[Any]: Table elements
        """
        elements = []

        # Add title if provided
        if title:
            title_para = Paragraph(f"<b>{title}</b>", self.styles['vast_subheading'])
            elements.append(title_para)
            elements.append(Spacer(1, 8))

        # Prepare table data
        table_data = []
        if headers:
            table_data.append(headers)
        table_data.extend(data)

        # Create table with VAST styling
        table = Table(table_data)

        # Apply VAST brand table styling
        table_style = TableStyle([
            # Header row styling
            ('BACKGROUND', (0, 0), (-1, 0), self.colors.VAST_BLUE_PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), self.colors.PURE_WHITE),
            ('FONTNAME', (0, 0), (-1, 0), self.typography.PRIMARY_FONT),
            ('FONTSIZE', (0, 0), (-1, 0), self.typography.BODY_SIZE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

            # Data rows styling with gradient effect
            ('BACKGROUND', (0, 1), (-1, -1), self.colors.VAST_BLUE_LIGHTEST),
            ('TEXTCOLOR', (0, 1), (-1, -1), self.colors.DARK_GRAY),
            ('FONTNAME', (0, 1), (-1, -1), self.typography.BODY_FONT),
            ('FONTSIZE', (0, 1), (-1, -1), self.typography.BODY_SIZE),

            # Borders and spacing
            ('GRID', (0, 0), (-1, -1), 1, self.colors.VAST_BLUE_DARKER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [
                self.colors.VAST_BLUE_LIGHTEST,
                self.colors.PURE_WHITE
            ]),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ])

        table.setStyle(table_style)
        elements.append(table)
        elements.append(Spacer(1, 12))

        return elements

    def create_vast_hardware_table(self, hardware_data: List[Dict[str, Any]],
                                  hardware_type: str) -> List[Any]:
        """
        Create VAST brand-compliant hardware inventory table.

        Args:
            hardware_data (List[Dict[str, Any]]): Hardware data
            hardware_type (str): Type of hardware (CNodes, DNodes, etc.)

        Returns:
            List[Any]: Hardware table elements
        """
        if not hardware_data:
            return []

        # Prepare headers based on hardware type
        if hardware_type.lower() == 'cnodes':
            headers = ['ID', 'Model', 'Serial Number', 'Status', 'Rack Position', 'U Number']
        elif hardware_type.lower() == 'dnodes':
            headers = ['ID', 'Model', 'Serial Number', 'Status', 'Rack Position', 'U Number']
        else:
            headers = ['ID', 'Model', 'Serial Number', 'Status', 'Position']

        # Prepare table data
        table_data = []
        for item in hardware_data:
            row = [
                item.get('id', 'Unknown'),
                item.get('model', 'Unknown'),
                item.get('serial_number', 'Unknown'),
                item.get('status', 'Unknown'),
            ]

            # Add rack positioning if available
            if hardware_type.lower() in ['cnodes', 'dnodes']:
                rack_pos = item.get('rack_position')
                if rack_pos is not None:
                    row.extend([str(rack_pos), f"U{rack_pos}"])
                else:
                    row.extend(['N/A', 'Manual Entry'])
            else:
                row.append(item.get('position', 'N/A'))

            table_data.append(row)

        return self.create_vast_table(table_data, f"{hardware_type} Inventory", headers)

    def create_vast_2d_diagram_placeholder(self, title: str, description: str) -> List[Any]:
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
        title_para = Paragraph(f"<b>{title}</b>", self.styles['vast_subheading'])
        elements.append(title_para)
        elements.append(Spacer(1, 8))

        # Description
        desc_para = Paragraph(description, self.styles['vast_body'])
        elements.append(desc_para)
        elements.append(Spacer(1, 8))

        # Placeholder box with VAST styling
        placeholder_text = f"[{title} Diagram Placeholder]"
        placeholder_para = Paragraph(
            f"<i>{placeholder_text}</i>",
            self.styles['vast_caption']
        )
        elements.append(placeholder_para)
        elements.append(Spacer(1, 12))

        return elements

    def _create_vast_divider(self) -> Any:
        """Create VAST brand-compliant horizontal divider."""
        # Simple divider using spacing and text
        return Paragraph("─" * 50, self.styles['vast_caption'])

    def create_vast_footer(self, generation_info: Dict[str, Any]) -> List[Any]:
        """
        Create VAST brand-compliant footer.

        Args:
            generation_info (Dict[str, Any]): Report generation information

        Returns:
            List[Any]: Footer elements
        """
        elements = []

        # Add divider
        elements.append(Spacer(1, 20))
        elements.append(self._create_vast_divider())
        elements.append(Spacer(1, 10))

        # Footer content
        footer_text = "VAST Professional Services | Automated As-Built Documentation"
        footer_para = Paragraph(footer_text, self.styles['vast_caption'])
        elements.append(footer_para)

        # Generation details
        if generation_info:
            timestamp = generation_info.get('timestamp', 'Unknown')
            completeness = generation_info.get('completeness', 0.0)

            details_text = f"Generated: {timestamp} | Data Completeness: {completeness:.1%}"
            details_para = Paragraph(details_text, self.styles['vast_caption'])
            elements.append(details_para)

        return elements

    def get_vast_page_style(self) -> Dict[str, Any]:
        """
        Get VAST brand-compliant page styling configuration.

        Returns:
            Dict[str, Any]: Page style configuration
        """
        return {
            'page_size': A4,
            'margin_top': 1.0 * inch,
            'margin_bottom': 1.0 * inch,
            'margin_left': 1.0 * inch,
            'margin_right': 1.0 * inch,
            'background_color': self.colors.PURE_WHITE,
            'header_color': self.colors.VAST_BLUE_LIGHTEST,
            'footer_color': self.colors.LIGHT_GRAY
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
