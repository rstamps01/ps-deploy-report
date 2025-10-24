"""
VAST As-Built Report Generator - Report Builder Module

This module generates professional PDF reports from processed VAST cluster data.
It creates comprehensive as-built reports with enhanced features including
rack positioning, PSNT tracking, and professional formatting.

Features:
- Professional PDF report generation
- Enhanced data visualization with rack layouts
- PSNT integration for support tracking
- Comprehensive report sections and formatting
- Customizable templates and styling
- Error handling and graceful degradation

Author: Manus AI
Date: September 26, 2025
"""

import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from brand_compliance import VastBrandCompliance, create_vast_brand_compliance

# Import rack diagram module
from rack_diagram import RackDiagram
from utils.logger import get_logger

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, inch
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        BaseDocTemplate,
        Frame,
        Image,
        KeepTogether,
        PageBreak,
        PageTemplate,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import weasyprint
    from weasyprint import CSS, HTML

    WEASYPRINT_AVAILABLE = True
except (ImportError, OSError):
    # OSError can occur when system libraries are missing
    WEASYPRINT_AVAILABLE = False


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    page_size: str = "A4"
    margin_top: float = 1.0
    margin_bottom: float = 1.0
    margin_left: float = 1.0
    margin_right: float = 1.0
    font_name: str = "Helvetica"
    font_size: int = 10
    title_font_size: int = 16
    heading_font_size: int = 12
    line_spacing: float = 1.2
    include_toc: bool = True
    include_timestamp: bool = True
    include_enhanced_features: bool = True


@dataclass
class ReportSection:
    """Data class for report section information."""

    title: str
    content: List[Any]
    level: int = 1
    page_break_before: bool = False


class ReportGenerationError(Exception):
    """Custom exception for report generation errors."""

    pass


class VastReportBuilder:
    """
    VAST As-Built Report Builder for generating professional PDF reports.

    This class creates comprehensive PDF reports from processed VAST cluster data
    with enhanced features for rack positioning and PSNT tracking.
    """

    def __init__(self, config: Optional[ReportConfig] = None):
        """
        Initialize the report builder.

        Args:
            config (ReportConfig, optional): Report configuration
        """
        self.logger = get_logger(__name__)
        self.config = config or ReportConfig()
        self.switch_positions = {}  # Will store calculated switch U positions

        # Check for required libraries
        if not REPORTLAB_AVAILABLE and not WEASYPRINT_AVAILABLE:
            raise ReportGenerationError(
                "Neither ReportLab nor WeasyPrint is available. Please install one of them."
            )

        # Initialize VAST brand compliance
        self.brand_compliance = create_vast_brand_compliance()

        self.logger.info("Report builder initialized with VAST brand compliance")

    def generate_pdf_report(
        self, processed_data: Dict[str, Any], output_path: str
    ) -> bool:
        """
        Generate a professional PDF report from processed data.

        Args:
            processed_data (Dict[str, Any]): Processed cluster data
            output_path (str): Output file path for the PDF

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Generating PDF report: {output_path}")

            # Create output directory if it doesn't exist
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            if REPORTLAB_AVAILABLE:
                return self._generate_with_reportlab(processed_data, str(output_file))
            elif WEASYPRINT_AVAILABLE:
                return self._generate_with_weasyprint(processed_data, str(output_file))
            else:
                self.logger.error("No PDF generation library available")
                return False

        except Exception as e:
            self.logger.error(f"Error generating PDF report: {e}")
            return False

    def _generate_with_reportlab(
        self, processed_data: Dict[str, Any], output_path: str
    ) -> bool:
        """Generate PDF using ReportLab."""
        try:
            # Set up document with page template
            page_size = A4 if self.config.page_size == "A4" else letter

            # Create page template with footer
            generation_info = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "completeness": processed_data.get("metadata", {}).get(
                    "overall_completeness", 0.0
                ),
            }
            page_template = self.brand_compliance.create_vast_page_template(
                generation_info
            )

            # Create document with page template
            from reportlab.platypus import BaseDocTemplate

            doc = BaseDocTemplate(
                output_path,
                pagesize=page_size,
                rightMargin=0.5 * inch,
                leftMargin=0.5 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.75 * inch,  # Extra space for footer
            )

            # Add page template to document
            doc.addPageTemplates([page_template])

            # Build story (content)
            story = []

            # Add title page
            story.extend(self._create_title_page(processed_data))
            story.append(PageBreak())

            # Add table of contents
            if self.config.include_toc:
                story.extend(self._create_table_of_contents(processed_data))
                story.append(PageBreak())

            # Add executive summary
            story.extend(self._create_executive_summary(processed_data))
            story.append(PageBreak())

            # Add cluster information
            story.extend(self._create_cluster_information(processed_data))
            story.append(PageBreak())

            # Add hardware inventory (includes Physical Rack Layout on Page 6)
            story.extend(self._create_hardware_inventory(processed_data))
            # Note: PageBreak is handled within hardware inventory for rack layout
            # Do not add extra PageBreak here to keep rack on Page 6

            # Add comprehensive network configuration (consolidated)
            story.extend(
                self._create_comprehensive_network_configuration(processed_data)
            )
            story.append(PageBreak())

            # Add switch configuration section
            story.extend(self._create_switch_configuration(processed_data))
            story.append(PageBreak())

            # Add logical network diagram (Page 8)
            story.extend(self._create_logical_network_diagram(processed_data))
            story.append(PageBreak())

            # Add logical configuration
            story.extend(self._create_logical_configuration(processed_data))
            story.append(PageBreak())

            # Add security configuration
            story.extend(self._create_security_configuration(processed_data))
            story.append(PageBreak())

            # Build PDF with page template
            from reportlab.platypus import NextPageTemplate

            # Start with the page template
            story.insert(0, NextPageTemplate("VastPage"))
            doc.build(story)

            self.logger.info(f"PDF report generated successfully: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating PDF with ReportLab: {e}")
            return False

    def _generate_with_weasyprint(
        self, processed_data: Dict[str, Any], output_path: str
    ) -> bool:
        """Generate PDF using WeasyPrint."""
        try:
            # Generate HTML content
            html_content = self._generate_html_content(processed_data)

            # Generate CSS
            css_content = self._generate_css_content()

            # Create HTML document
            html_doc = HTML(string=html_content)
            css_doc = CSS(string=css_content)

            # Generate PDF
            html_doc.write_pdf(output_path, stylesheets=[css_doc])

            self.logger.info(
                f"PDF report generated successfully with WeasyPrint: {output_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error generating PDF with WeasyPrint: {e}")
            return False

    def _create_title_page(self, data: Dict[str, Any]) -> List[Any]:
        """Create VAST brand-compliant title page content."""
        content = []

        # Get cluster information
        cluster_info = data.get("cluster_summary", {})

        # Get hardware information from hardware inventory
        hardware_inventory = data.get("hardware_inventory", {})
        cnodes = hardware_inventory.get("cnodes", [])
        dnodes = hardware_inventory.get("dnodes", [])

        # Create VAST brand-compliant header
        title = "VAST As-Built Report"
        subtitle = "Customer Deployment Documentation"

        header_elements = self.brand_compliance.create_vast_header(
            title=title, subtitle=subtitle, cluster_info=cluster_info
        )
        content.extend(header_elements)

        # Add hardware information
        if cnodes or dnodes:
            hardware_text = ""

            # CBox Hardware (from CNode data using box_vendor)
            if cnodes:
                cbox_vendors = set()
                cbox_ids = set()

                for cnode in cnodes:
                    # Get box_vendor from the cnode data
                    box_vendor = cnode.get("box_vendor", "Unknown")
                    if box_vendor and box_vendor != "Unknown":
                        cbox_vendors.add(box_vendor)

                    cbox_id = cnode.get("id")
                    if cbox_id:
                        cbox_ids.add(str(cbox_id))

                if cbox_vendors:
                    hardware_text += (
                        f"<b>CBox Hardware:</b> {', '.join(sorted(cbox_vendors))}<br/>"
                    )

                hardware_text += f"<b>CBox Quantity:</b> {len(cbox_ids)}<br/>"

            # DBox Hardware (from DBox data using hardware_type)
            dboxes = hardware_inventory.get("dboxes", {})
            if dboxes:
                dbox_hardware_types = set()
                dbox_ids = set()

                for dbox_name, dbox_data in dboxes.items():
                    hardware_type = dbox_data.get("hardware_type")
                    if hardware_type and hardware_type != "Unknown":
                        dbox_hardware_types.add(hardware_type)

                    dbox_id = dbox_data.get("id")
                    if dbox_id:
                        dbox_ids.add(str(dbox_id))

                if dbox_hardware_types:
                    hardware_text += f"<b>DBox Hardware:</b> {', '.join(sorted(dbox_hardware_types))}<br/>"

                hardware_text += f"<b>DBox Quantity:</b> {len(dbox_ids)}<br/>"

            # Switch Hardware (from switch inventory)
            switches = hardware_inventory.get("switches", [])
            if switches:
                switch_models = set()
                switch_count = len(switches)

                for switch in switches:
                    model = switch.get("model", "Unknown")
                    if model and model != "Unknown":
                        switch_models.add(model)

                if switch_models:
                    hardware_text += f"<b>Switch Hardware:</b> {', '.join(sorted(switch_models))}<br/>"

                hardware_text += f"<b>Switch Quantity:</b> {switch_count}"

            if hardware_text:
                # Create centered hardware information
                hardware_style = ParagraphStyle(
                    "CenteredHardware",
                    parent=self.brand_compliance.styles["vast_body"],
                    alignment=TA_CENTER,
                )
                hardware_para = Paragraph(hardware_text, hardware_style)
                content.append(hardware_para)
                content.append(Spacer(1, 20))

        # Remove the "Generated on" line as requested
        # Footer is now handled by page template

        return content

    def _create_table_of_contents_from_excel(self, excel_path: str) -> List[Any]:
        """Create table of contents from Excel file."""
        try:
            import openpyxl
            from reportlab.pdfbase.pdfmetrics import stringWidth
        except ImportError:
            self.logger.error("openpyxl not available for Excel import")
            return []

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "TOC_Title",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size + 2,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            fontName="Helvetica-Bold",
        )

        content = []
        content.append(Paragraph("Table of Contents (from Excel)", title_style))
        content.append(Spacer(1, 8))

        # Load Excel file
        try:
            wb = openpyxl.load_workbook(excel_path)
            ws = wb["Report-TOC"]
        except Exception as e:
            self.logger.error(f"Error loading Excel file: {e}")
            content.append(
                Paragraph(f"Error loading Excel file: {e}", styles["Normal"])
            )
            return content

        # Read TOC data from Excel (A1:C60)
        available_width = 7.5 * inch
        toc_table_data = []

        for row in range(1, 61):
            # Read values from columns A, B, C
            text_cell = ws[f"A{row}"]
            page_cell = ws[f"C{row}"]

            text = str(text_cell.value).strip() if text_cell.value else ""
            page_num = str(page_cell.value).strip() if page_cell.value else ""

            # Skip empty rows or header row
            if not text or text.lower() == "contents":
                continue

            # Determine indentation level by counting leading spaces
            # Support multiple indentation levels (each 4-5 spaces = 1 level)
            indent_level = 0
            original_text = str(text_cell.value) if text_cell.value else ""

            # Count leading spaces to determine indent level
            leading_spaces = len(original_text) - len(original_text.lstrip())
            if leading_spaces > 0:
                # Each 4-5 spaces = 1 indent level
                indent_level = (leading_spaces + 2) // 4  # Round to nearest level
                text = text.strip()

            # Read Excel cell formatting (bold, font size, color, alignment)
            # Default values
            is_bold_excel = False
            is_italic_excel = False
            text_size_excel = None
            text_color_excel = None
            text_alignment = TA_LEFT  # Default left alignment

            # Check if cell has font formatting
            if text_cell.font:
                is_bold_excel = text_cell.font.bold or False
                is_italic_excel = text_cell.font.italic or False

                # Get font size from Excel (convert from points)
                if text_cell.font.size:
                    text_size_excel = text_cell.font.size

                # Get font color from Excel
                if text_cell.font.color:
                    if text_cell.font.color.rgb:
                        # RGB format: "AARRGGBB" or "RRGGBB"
                        rgb = text_cell.font.color.rgb
                        if isinstance(rgb, str):
                            # Remove alpha channel if present
                            if len(rgb) == 8:
                                rgb = rgb[2:]  # Remove "AA" prefix
                            text_color_excel = colors.HexColor(f"#{rgb}")

            # Read cell alignment from Excel
            if text_cell.alignment:
                horizontal = text_cell.alignment.horizontal
                if horizontal == "center":
                    text_alignment = TA_CENTER
                elif horizontal == "right":
                    text_alignment = TA_RIGHT
                elif horizontal == "left":
                    text_alignment = TA_LEFT
                # Note: 'general' or None defaults to TA_LEFT

            # Determine if bold from Excel or fallback to page number logic
            is_bold = is_bold_excel if text_cell.font else bool(page_num)

            # Set font properties (use Excel formatting if available)
            if is_bold:
                text_font = "Helvetica-Bold"
                text_color = (
                    text_color_excel
                    if text_color_excel
                    else self.brand_compliance.colors.BACKGROUND_DARK
                )
                text_size = (
                    text_size_excel if text_size_excel else (self.config.font_size - 1)
                )
                page_font = "Helvetica-Bold"
                page_color = (
                    text_color
                    if text_color
                    else self.brand_compliance.colors.BACKGROUND_DARK
                )
                page_size = text_size
                extra_space = 3
            else:
                text_font = "Helvetica-Oblique" if is_italic_excel else "Helvetica"
                text_color = (
                    text_color_excel if text_color_excel else colors.HexColor("#000000")
                )
                text_size = (
                    text_size_excel if text_size_excel else (self.config.font_size - 2)
                )
                page_font = text_font
                page_color = text_color
                page_size = text_size
                extra_space = 0

            # Check column B for special formatting (lines/separators)
            sep_cell = ws[f"B{row}"]
            separator_text = str(sep_cell.value).strip() if sep_cell.value else ""

            # Format text with indentation (only if not center/right aligned)
            if text_alignment == TA_LEFT:
                # Use 4 spaces per indent level for better visibility
                indent_space = "    " * indent_level if indent_level > 0 else ""
                full_text = f"{indent_space}{text}"
            else:
                full_text = text

            # Calculate dots if page number exists AND alignment is left
            # Center/right aligned entries don't get dots
            if page_num and text_alignment == TA_LEFT:
                text_width = stringWidth(full_text, text_font, text_size)
                page_width = stringWidth(page_num, page_font, page_size)

                spacing_buffer = 0.1 * inch
                available_for_dots = (
                    available_width - text_width - page_width - spacing_buffer
                )

                dot_width = stringWidth(".", "Helvetica", text_size - 1)
                if dot_width > 0:
                    num_dots = int(available_for_dots / dot_width)
                    num_dots = max(3, num_dots)
                else:
                    num_dots = 30

                dots = '<font color="#CCCCCC">' + ("." * num_dots) + "</font>"
                text_with_dots = f"{full_text} {dots}"
            elif page_num and text_alignment == TA_CENTER:
                # Center-aligned with page number: text on left, number on right, centered line between
                if separator_text and separator_text in ["─", "-", "—", "_"]:
                    # Use separator character from column B
                    text_with_dots = f"{full_text} {separator_text * 80}"
                else:
                    # Default to dots but will be centered
                    text_with_dots = f"{full_text} {'.' * 80}"
            elif page_num and text_alignment == TA_RIGHT:
                # Right-aligned with page number
                text_with_dots = full_text
            else:
                text_with_dots = full_text

            # Create paragraph styles with Excel alignment
            text_style = ParagraphStyle(
                f"TOC_Text_{len(toc_table_data)}",
                parent=styles["Normal"],
                fontSize=text_size,
                fontName=text_font,
                textColor=text_color,
                alignment=text_alignment,  # Use Excel alignment
                spaceBefore=extra_space,
                spaceAfter=0.5,
                leading=text_size + 2,
            )

            # Page number alignment matches text alignment for center, otherwise right
            page_alignment = text_alignment if text_alignment == TA_CENTER else TA_RIGHT

            page_style = ParagraphStyle(
                f"TOC_Page_{len(toc_table_data)}",
                parent=styles["Normal"],
                fontSize=page_size,
                fontName=page_font,
                textColor=page_color,
                alignment=page_alignment,
                spaceBefore=extra_space,
                spaceAfter=0.5,
                leading=page_size + 2,
            )

            # Create paragraphs
            text_para = Paragraph(text_with_dots, text_style)
            if page_num:
                page_para = Paragraph(page_num, page_style)
            else:
                page_para = Paragraph("", page_style)

            toc_table_data.append([text_para, page_para])

        # Create table
        text_col_width = available_width - 0.5 * inch
        page_col_width = 0.5 * inch

        from reportlab.platypus import Table as RLTable

        toc_table = RLTable(toc_table_data, colWidths=[text_col_width, page_col_width])
        toc_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        content.append(toc_table)
        return content

    def _create_table_of_contents(self, data: Dict[str, Any]) -> List[Any]:
        """Create enhanced table of contents with dot leaders and perfect alignment."""
        from reportlab.platypus import Table as RLTable

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "TOC_Title",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size + 2,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            fontName="Helvetica-Bold",
        )

        content = []

        content.append(Paragraph("Table of Contents", title_style))
        content.append(Spacer(1, 8))

        # TOC structure with sections, subsections, and page numbers
        # Format: (text, indent_level, page_num, is_bold)
        # Structure: Parent section first, then its subsections indented below
        toc_structure = [
            # Executive Summary section
            ("Executive Summary", 0, "3", True),
            ("Cluster Overview", 1, None, False),
            ("Hardware Overview", 1, None, False),
            # Cluster Information section
            ("Cluster Information", 0, "4", True),
            ("Cluster Details", 1, None, False),
            ("Operational Status", 1, None, False),
            ("Feature Configuration", 1, None, False),
            # Hardware Summary section
            ("Hardware Summary", 0, "5", True),
            ("Storage Capacity", 1, None, False),
            ("CBox Inventory", 1, None, False),
            ("DBox Inventory", 1, None, False),
            # Physical Rack Layout section (no subsections)
            ("Physical Rack Layout", 0, "6", True),
            # Network Configuration section
            ("Network Configuration", 0, "7", True),
            ("Cluster Network", 1, None, False),
            ("CNode Network", 1, None, False),
            ("DNode Network", 1, None, False),
            # Switch Configuration section
            ("Switch Configuration", 0, "8", True),
            ("Switch Details", 1, None, False),
            ("Port Summary", 1, None, False),
            # Port Mapping section
            ("Port Mapping", 0, "10", True),
            ("Device Mapping", 1, None, False),
            # Logical Network Diagram section (no subsections)
            ("Logical Network Diagram", 0, "11", True),
            # Logical Configuration section
            ("Logical Configuration", 0, "12", True),
            ("Tenants & Views", 1, None, False),
            ("Protection Policies", 1, None, False),
            # Security & Authentication section
            ("Security & Authentication", 0, "13", True),
            ("Encryption Configuration", 1, None, False),
            ("Authentication Services", 1, None, False),
        ]

        # Build TOC table with calculated dot leaders for perfect alignment
        from reportlab.pdfbase.pdfmetrics import stringWidth

        available_width = 7.5 * inch  # Page width minus margins
        toc_table_data = []

        # List of subsections that should have extra space after them (to separate section groups)
        subsections_with_space_after = [
            "Hardware Overview",
            "Feature Configuration",
            "DBox Inventory",
            "Physical Rack Layout",
            "DNode Network",
            "Port Summary",
            "Device Mapping",
            "Logical Network Diagram",
            "Protection Policies",
        ]

        for idx, (text, indent_level, page_num, is_bold) in enumerate(toc_structure):
            # Calculate indentation using spaces (smaller indent for compact view)
            indent_space = "  " * indent_level if indent_level > 0 else ""
            full_text = f"{indent_space}{text}"

            # Create styles for text and page number
            if is_bold:
                text_font = "Helvetica-Bold"
                text_color = self.brand_compliance.colors.BACKGROUND_DARK
                text_size = (
                    self.config.font_size - 1
                )  # Slightly smaller for compact view
                page_font = "Helvetica-Bold"
                page_color = self.brand_compliance.colors.BACKGROUND_DARK
                page_size = self.config.font_size - 1
                # More space before main sections (except first one) to separate from subsections above
                extra_space = 0 if idx == 0 else 12
            else:
                text_font = "Helvetica"
                text_color = colors.HexColor("#000000")
                text_size = self.config.font_size - 2  # Smaller for subsections
                page_font = "Helvetica"
                page_color = colors.HexColor("#000000")
                page_size = self.config.font_size - 2
                extra_space = 0

            # Add extra space after specific subsections to separate section groups
            if text in subsections_with_space_after:
                extra_space_after = 8  # Extra space after these subsections
            else:
                extra_space_after = 0.5

            # Only add dots and page numbers for entries that have page numbers
            if page_num:
                # Custom dot leader lengths for specific sections
                if text == "Executive Summary":
                    dot_leader_length = 5.0 * inch
                elif text == "Cluster Information":
                    dot_leader_length = 5.0 * inch
                elif text == "Hardware Summary":
                    dot_leader_length = 5.0 * inch
                elif text == "Physical Rack Layout":
                    dot_leader_length = 4.92 * inch
                elif text == "Network Configuration":
                    dot_leader_length = 4.87 * inch
                elif text == "Switch Configuration":
                    dot_leader_length = 4.95 * inch
                elif text == "Port Mapping":
                    dot_leader_length = 5.4 * inch
                elif text == "Logical Network Diagram":
                    dot_leader_length = 4.78 * inch
                elif text == "Logical Configuration":
                    dot_leader_length = 4.95 * inch
                else:
                    dot_leader_length = 4.75 * inch  # Default for all other entries

                # Calculate how many dots fit in the specified space
                dot_width = stringWidth(".", "Helvetica", text_size - 1)
                if dot_width > 0:
                    num_dots = int(dot_leader_length / dot_width)
                    num_dots = max(3, num_dots)  # Minimum 3 dots
                else:
                    num_dots = 150  # Fallback for 5 inches

                dots = '<font color="#CCCCCC">' + ("." * num_dots) + "</font>"
                text_with_dots = f"{full_text} {dots}"
            else:
                # Subsections without page numbers - no dots needed
                text_with_dots = full_text

            text_style = ParagraphStyle(
                f"TOC_Text_{len(toc_table_data)}",
                parent=styles["Normal"],
                fontSize=text_size,
                fontName=text_font,
                textColor=text_color,
                alignment=TA_LEFT,
                spaceBefore=extra_space,
                spaceAfter=extra_space_after,  # Variable spacing based on subsection
                leading=text_size + 2,  # Compact line spacing
            )

            page_style = ParagraphStyle(
                f"TOC_Page_{len(toc_table_data)}",
                parent=styles["Normal"],
                fontSize=page_size,
                fontName=page_font,
                textColor=page_color,
                alignment=TA_RIGHT,
                spaceBefore=extra_space,
                spaceAfter=extra_space_after,  # Variable spacing based on subsection
                leading=page_size + 2,
            )

            # Create paragraphs
            text_para = Paragraph(text_with_dots, text_style)
            if page_num:
                page_para = Paragraph(page_num, page_style)
            else:
                page_para = Paragraph("", page_style)  # Empty for subsections

            toc_table_data.append([text_para, page_para])

        # Create a 2-column table: text+dots | page number
        # The text column should be wide, page column narrow
        # Page numbers positioned close to dot leaders (0.15" from right edge)
        text_col_width = available_width - 0.15 * inch
        page_col_width = 0.15 * inch

        toc_table = RLTable(toc_table_data, colWidths=[text_col_width, page_col_width])
        toc_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),  # Text column left-aligned
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),  # Page column right-aligned
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),  # Align to baseline
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        content.append(toc_table)

        return content

    def _create_executive_summary(self, data: Dict[str, Any]) -> List[Any]:
        """Create VAST brand-compliant executive summary section."""
        content = []

        # Add section heading with VAST styling
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Executive Summary", level=1
        )
        content.extend(heading_elements)

        # Section Overview
        styles = getSampleStyleSheet()
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "This VAST As-Built Report provides a comprehensive technical documentation of the deployed VAST Data cluster infrastructure, configuration, and operational status. The report serves as a critical reference for system administrators, storage engineers, and technical stakeholders to understand the current state of the cluster deployment, validate configuration compliance, and support ongoing operations and troubleshooting. The Executive Summary consolidates key operational metrics, hardware inventory, and cluster health indicators into high-level overview tables that enable rapid assessment of cluster status and capacity utilization.",
                overview_style,
            )
        )
        content.append(Spacer(1, 8))

        # Cluster overview table - resequenced to match screenshot order
        cluster_info = data.get("cluster_summary", {})
        cluster_id = cluster_info.get("cluster_id", "Unknown")
        cluster_name = cluster_info.get("name", "Unknown")
        mgmt_vip = cluster_info.get("mgmt_vip", "Unknown")
        url = cluster_info.get("url", "Unknown")
        build = cluster_info.get("build", "Unknown")
        psnt = cluster_info.get("psnt", "Unknown")
        guid = cluster_info.get("guid", "Unknown")
        uptime = cluster_info.get("uptime", "Unknown")
        online_start_time = cluster_info.get("online_start_time", "Unknown")
        deployment_time = cluster_info.get("deployment_time", "Unknown")

        # Get capacity display format
        capacity_base_10 = cluster_info.get("capacity_base_10", None)
        if capacity_base_10 is True:
            capacity_format = "True (TB - Base 10)"
        elif capacity_base_10 is False:
            capacity_format = "False (TiB - Base 2)"
        else:
            capacity_format = "Unknown"
        
        cluster_overview_data = [
            ["ID", cluster_id],
            ["Name", cluster_name],
            ["Management VIP", mgmt_vip],
            ["URL", url],
            ["Build", build],
            ["PSNT", psnt],
            ["GUID", guid],
            ["Capacity-Base 10", capacity_format],
            ["Uptime", uptime],
            ["Online Since", online_start_time],
            ["Deployed", deployment_time],
        ]

        # Create cluster overview table with same style as Cluster Information
        cluster_table_elements = self._create_cluster_info_table(
            cluster_overview_data, "Cluster Overview"
        )
        content.extend(cluster_table_elements)
        content.append(Spacer(1, 12))

        # Hardware overview table
        hardware = data.get("hardware_inventory", {})
        total_nodes = hardware.get("total_nodes", 0)
        cnodes = len(hardware.get("cnodes", []))
        dnodes = len(hardware.get("dnodes", []))
        cboxes = len(hardware.get("cboxes", []))
        dboxes = len(hardware.get("dboxes", []))
        switches_list = hardware.get("switches", [])
        total_switches = len(switches_list)

        # Calculate leaf and spine switches
        # Logic: If 2 switches = 2 leaf, if 4 = 2 leaf + 2 spine, if >4 = 2 spine + rest are leaf
        if total_switches == 2:
            leaf_switches = 2
            spine_switches = 0
        elif total_switches == 4:
            leaf_switches = 2
            spine_switches = 2
        elif total_switches > 4:
            spine_switches = 2
            leaf_switches = total_switches - 2
        else:
            leaf_switches = total_switches
            spine_switches = 0

        hardware_overview_data = [
            ["CBoxes", str(cboxes)],
            ["CNodes", str(cnodes)],
            ["", ""],  # Empty line
            ["DBoxes", str(dboxes)],
            ["DNodes", str(dnodes)],
            ["", ""],  # Empty line
            ["Switches", str(total_switches)],
            ["Leaf", str(leaf_switches)],
            ["Spine", str(spine_switches)],
        ]

        # Create hardware overview table with same style as Cluster Information
        hardware_table_elements = self._create_cluster_info_table(
            hardware_overview_data, "Hardware Overview"
        )
        content.extend(hardware_table_elements)
        content.append(Spacer(1, 12))

        return content

    def _create_cluster_info_table(
        self, table_data: List[List[str]], title: str
    ) -> List[Any]:
        """Create a cluster information style table with VAST branding."""
        content = []

        # Create table with VAST styling
        table_elements = self.brand_compliance.create_vast_table(
            table_data, title, ["Description", "Value"]
        )
        content.extend(table_elements)

        return content

    def _create_consolidated_inventory_table(
        self,
        cboxes: Dict[str, Any],
        cnodes: List[Dict[str, Any]],
        dboxes: Dict[str, Any],
        switches: List[Dict[str, Any]],
    ) -> List[Any]:
        """
        Create consolidated hardware inventory table with CBoxes, DBoxes, and Switches.

        Args:
            cboxes: CBox data from /api/v1/cboxes/
            cnodes: CNode data from /api/v7/cnodes/
            dboxes: DBox data from /api/v7/dboxes/
            switches: Switch data from switch inventory

        Returns:
            List[Any]: Table elements
        """
        # Prepare table data
        table_data = []
        headers = ["ID", "Model", "Name/Serial Number", "Status", "Position"]

        # Add CBoxes
        if cboxes and cnodes:
            # Create a mapping of cbox_id to box_vendor and status from cnodes
            cbox_vendor_map = {}
            cbox_status_map = {}
            for cnode in cnodes:
                cbox_id = cnode.get("cbox_id")
                box_vendor = cnode.get("box_vendor", "Unknown")
                status = cnode.get("status", "Unknown")
                if cbox_id:
                    cbox_vendor_map[cbox_id] = box_vendor
                    cbox_status_map[cbox_id] = status

            cbox_rows = []
            for cbox_name, cbox_data in cboxes.items():
                cbox_id = cbox_data.get("id", "Unknown")
                name = cbox_data.get("name", "Unknown")
                rack_unit = cbox_data.get("rack_unit", "Unknown")

                # Get model and status from cnodes data using cbox_id
                model = cbox_vendor_map.get(cbox_id, "Unknown")
                status = cbox_status_map.get(cbox_id, "Unknown")

                # Create row data with CB- prefix
                row = [f"CB-{cbox_id}", model, name, status, rack_unit]
                cbox_rows.append((cbox_id, row))

            # Sort by numeric ID
            cbox_rows.sort(key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)
            table_data.extend([row for _, row in cbox_rows])

        # Add DBoxes
        if dboxes:
            dbox_rows = []
            for dbox_name, dbox_data in dboxes.items():
                dbox_id = dbox_data.get("id", "Unknown")
                hardware_type = dbox_data.get("hardware_type", "Unknown")
                name = dbox_data.get("name", "Unknown")
                state = dbox_data.get("state", "Unknown")
                rack_unit = dbox_data.get("rack_unit", "Unknown")

                # Create row data with DB- prefix
                row = [f"DB-{dbox_id}", hardware_type, name, state, rack_unit]
                dbox_rows.append((dbox_id, row))

            # Sort by numeric ID
            dbox_rows.sort(key=lambda x: int(x[0]) if str(x[0]).isdigit() else 0)
            table_data.extend([row for _, row in dbox_rows])

        # Add Switches
        if switches:
            switch_rows = []
            for switch_num, switch in enumerate(switches, start=1):
                switch_name = switch.get("name", "Unknown")
                hostname = switch.get("hostname", switch_name)
                model = switch.get("model", "Unknown")
                serial = switch.get("serial", "Unknown")
                state = switch.get("state", "Unknown")

                # Get calculated position from rack diagram (if available)
                position = ""
                if (
                    hasattr(self, "switch_positions")
                    and switch_num in self.switch_positions
                ):
                    u_pos = self.switch_positions[switch_num]
                    position = f"U{u_pos}"

                # Create row data with SW- prefix using switch number
                row = [f"SW-{switch_num}", model, serial, state, position]
                switch_rows.append((hostname, row))

            # Sort by hostname before numbering
            switch_rows.sort(key=lambda x: x[0])

            # Re-number switches sequentially after sorting and update positions
            for idx, (hostname, row) in enumerate(switch_rows, start=1):
                row[0] = f"SW-{idx}"
                # Update position if available for this switch number
                if hasattr(self, "switch_positions") and idx in self.switch_positions:
                    u_pos = self.switch_positions[idx]
                    row[4] = f"U{u_pos}"  # Position is at index 4

            table_data.extend([row for _, row in switch_rows])

        if not table_data:
            return []

        # Create table with VAST styling
        return self.brand_compliance.create_vast_hardware_table_with_pagination(
            table_data, "Hardware Inventory", headers
        )

    def _create_cluster_information(self, data: Dict[str, Any]) -> List[Any]:
        """Create VAST brand-compliant cluster information section."""
        content = []

        # Add section heading with VAST styling
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Cluster Information", level=1
        )
        content.extend(heading_elements)

        # Section Overview
        styles = getSampleStyleSheet()
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Cluster Information section provides detailed operational status and configuration parameters for the VAST Data cluster. This section captures essential cluster metadata including cluster identification, operational state, management network configuration, and feature flags that define the cluster's capabilities and current operational mode. The information presented here is critical for understanding the cluster's current operational status, validating proper configuration, and supporting troubleshooting activities. This data is collected directly from the cluster's management API and represents the real-time operational state of the system.",
                overview_style,
            )
        )
        content.append(Spacer(1, 8))

        cluster_info = data.get("cluster_summary", {})

        # Create cluster info table with VAST styling - reorganized per requirements
        cluster_name = cluster_info.get("name", "Unknown")
        cluster_data = [
            ["State", cluster_info.get("state", "Unknown")],
            ["SSD RAID State", cluster_info.get("ssd_raid_state", "Unknown")],
            ["NVRAM RAID State", cluster_info.get("nvram_raid_state", "Unknown")],
            ["Memory RAID State", cluster_info.get("memory_raid_state", "Unknown")],
            ["Leader State", cluster_info.get("leader_state", "Unknown")],
            ["Leader CNode", cluster_info.get("leader_cnode", "Unknown")],
            ["Management CNode", cluster_info.get("mgmt_cnode", "Unknown")],
            ["Management Inner VIP", cluster_info.get("mgmt_inner_vip", "Unknown")],
            [
                "Management Inner VIP CNode",
                cluster_info.get("mgmt_inner_vip_cnode", "Unknown"),
            ],
            [
                "Enabled",
                (
                    "Yes"
                    if cluster_info.get("enabled")
                    else (
                        "No" if cluster_info.get("enabled") is not None else "Unknown"
                    )
                ),
            ],
            [
                "Similarity Enabled",
                (
                    "Yes"
                    if cluster_info.get("enable_similarity")
                    else (
                        "No"
                        if cluster_info.get("enable_similarity") is not None
                        else "Unknown"
                    )
                ),
            ],
            [
                "Deduplication Active",
                (
                    "Yes"
                    if cluster_info.get("dedup_active")
                    else (
                        "No"
                        if cluster_info.get("dedup_active") is not None
                        else "Unknown"
                    )
                ),
            ],
            [
                "Write-Back RAID Enabled",
                (
                    "Yes"
                    if cluster_info.get("is_wb_raid_enabled")
                    else (
                        "No"
                        if cluster_info.get("is_wb_raid_enabled") is not None
                        else "Unknown"
                    )
                ),
            ],
            [
                "Write-Back RAID Layout",
                cluster_info.get("wb_raid_layout", "Unknown"),
            ],
            [
                "DBox HA Support",
                (
                    "Yes"
                    if cluster_info.get("dbox_ha_support")
                    else (
                        "No"
                        if cluster_info.get("dbox_ha_support") is not None
                        else "Unknown"
                    )
                ),
            ],
            [
                "Rack Level Resiliency",
                (
                    "Yes"
                    if cluster_info.get("enable_rack_level_resiliency")
                    else (
                        "No"
                        if cluster_info.get("enable_rack_level_resiliency") is not None
                        else "Unknown"
                    )
                ),
            ],
            [
                "Metrics Disabled",
                (
                    "Yes"
                    if cluster_info.get("disable_metrics")
                    else (
                        "No"
                        if cluster_info.get("disable_metrics") is not None
                        else "Unknown"
                    )
                ),
            ],
        ]

        table_elements = self.brand_compliance.create_vast_table(
            cluster_data, f"Cluster Name: {cluster_name}", ["Function", "Status"]
        )
        content.extend(table_elements)

        return content

    def _create_hardware_inventory(self, data: Dict[str, Any]) -> List[Any]:
        """Create VAST brand-compliant hardware inventory section."""
        content = []

        # Add section heading with VAST styling
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Hardware Summary", level=1
        )
        content.extend(heading_elements)

        # Section Overview
        styles = getSampleStyleSheet()
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Hardware Summary section provides comprehensive inventory and operational status of all physical hardware components within the VAST Data cluster. This section includes detailed information about storage capacity utilization, compute nodes (CNodes), data nodes (DNodes), and their respective hardware specifications, operational status, and physical rack positioning. The capacity metrics show both logical and physical storage utilization, enabling capacity planning and performance optimization. Hardware inventory data is essential for understanding cluster scale, identifying hardware failures, planning maintenance windows, and ensuring proper rack organization for optimal cooling and cable management.",
                overview_style,
            )
        )
        content.append(Spacer(1, 8))

        hardware = data.get("hardware_inventory", {})

        # Add storage capacity section
        cluster_info = data.get("cluster_summary", {})
        if any(
            cluster_info.get(field) is not None
            for field in [
                "usable_capacity_tb",
                "free_usable_capacity_tb",
                "drr_text",
                "physical_space_tb",
                "physical_space_in_use_tb",
                "free_physical_space_tb",
                "physical_space_in_use_percent",
                "logical_space_tb",
                "logical_space_in_use_tb",
                "free_logical_space_tb",
                "logical_space_in_use_percent",
            ]
        ):
            # Storage capacity table
            storage_data = []
            
            # Determine capacity unit based on capacity_base_10 setting
            capacity_unit = "TB" if cluster_info.get("capacity_base_10", True) else "TiB"

            # Usable capacity section
            if cluster_info.get("usable_capacity_tb") is not None:
                storage_data.append(
                    [
                        "Usable Capacity",
                        f"{round(cluster_info.get('usable_capacity_tb', 0))} {capacity_unit}",
                    ]
                )
            if cluster_info.get("free_usable_capacity_tb") is not None:
                storage_data.append(
                    [
                        "Free Usable Capacity",
                        f"{round(cluster_info.get('free_usable_capacity_tb', 0))} {capacity_unit}",
                    ]
                )
            if (
                cluster_info.get("drr_text")
                and cluster_info.get("drr_text") != "Unknown"
            ):
                storage_data.append(
                    [
                        "Data Reduction Ratio (DRR)",
                        cluster_info.get("drr_text", "Unknown"),
                    ]
                )

            # Physical space section
            if cluster_info.get("physical_space_tb") is not None:
                storage_data.append(
                    [
                        "Physical Space",
                        f"{round(cluster_info.get('physical_space_tb', 0))} {capacity_unit}",
                    ]
                )
            if cluster_info.get("physical_space_in_use_tb") is not None:
                storage_data.append(
                    [
                        "Physical Space In Use",
                        f"{round(cluster_info.get('physical_space_in_use_tb', 0))} {capacity_unit}",
                    ]
                )
            if cluster_info.get("free_physical_space_tb") is not None:
                storage_data.append(
                    [
                        "Free Physical Space",
                        f"{round(cluster_info.get('free_physical_space_tb', 0))} {capacity_unit}",
                    ]
                )
            if cluster_info.get("physical_space_in_use_percent") is not None:
                storage_data.append(
                    [
                        "Physical Space In Use %",
                        f"{round(cluster_info.get('physical_space_in_use_percent', 0))}%",
                    ]
                )

            # Logical space section
            if cluster_info.get("logical_space_tb") is not None:
                storage_data.append(
                    [
                        "Logical Space",
                        f"{round(cluster_info.get('logical_space_tb', 0))} {capacity_unit}",
                    ]
                )
            if cluster_info.get("logical_space_in_use_tb") is not None:
                storage_data.append(
                    [
                        "Logical Space In Use",
                        f"{round(cluster_info.get('logical_space_in_use_tb', 0))} {capacity_unit}",
                    ]
                )
            if cluster_info.get("free_logical_space_tb") is not None:
                storage_data.append(
                    [
                        "Free Logical Space",
                        f"{round(cluster_info.get('free_logical_space_tb', 0))} {capacity_unit}",
                    ]
                )
            if cluster_info.get("logical_space_in_use_percent") is not None:
                storage_data.append(
                    [
                        "Logical Space In Use %",
                        f"{round(cluster_info.get('logical_space_in_use_percent', 0))}%",
                    ]
                )

            if storage_data:
                storage_table_elements = self.brand_compliance.create_vast_table(
                    storage_data, "Storage Capacity", ["Metric", "Value"]
                )
                content.extend(storage_table_elements)
                content.append(Spacer(1, 12))

            # Calculate switch positions early (before creating inventory table)
            # This allows us to populate the Position column for switches
            cboxes = hardware.get("cboxes", {})
            cnodes = hardware.get("cnodes", [])
            dboxes = hardware.get("dboxes", {})
            switches = hardware.get("switches", [])

            # Pre-calculate switch positions for rack diagram
            if switches and len(switches) == 2:
                # Prepare CBox and DBox data for calculation
                temp_rack_gen = RackDiagram()

                # Build CBox data for switch calculation
                cboxes_data = []
                hw_cnodes = hardware.get("cnodes", [])
                for cnode in hw_cnodes:
                    cbox_data = {
                        "id": cnode.get("id"),
                        "model": cnode.get("model", cnode.get("box_vendor", "")),
                        "rack_unit": cnode.get(
                            "rack_u", cnode.get("rack_unit", cnode.get("position", ""))
                        ),
                        "state": cnode.get("state", cnode.get("status", "ACTIVE")),
                    }
                    if cbox_data["rack_unit"]:  # Only add if has position
                        cboxes_data.append(cbox_data)

                # Build DBox data for switch calculation
                # Use dboxes (physical chassis) not dnodes (individual nodes)
                dboxes_data = []
                hw_dboxes = hardware.get("dboxes", {})
                for dbox_name, dbox_info in hw_dboxes.items():
                    rack_unit = dbox_info.get("rack_unit", "")
                    if rack_unit:
                        dbox_data = {
                            "id": dbox_info.get("id"),
                            "model": dbox_info.get("hardware_type", "Unknown"),
                            "rack_unit": rack_unit,
                            "state": dbox_info.get("state", "ACTIVE"),
                        }
                        dboxes_data.append(dbox_data)

                # Calculate switch positions
                calculated_positions = temp_rack_gen._calculate_switch_positions(
                    cboxes_data, dboxes_data, len(switches)
                )
                if calculated_positions:
                    self.switch_positions = {
                        idx: u_pos
                        for idx, u_pos in enumerate(calculated_positions, start=1)
                    }
                    self.logger.info(
                        f"Pre-calculated switch positions: {self.switch_positions}"
                    )

        # Consolidated Hardware Inventory table with VAST styling
        if cboxes or dboxes or switches:
            inventory_elements = self._create_consolidated_inventory_table(
                cboxes, cnodes, dboxes, switches
            )
            content.extend(inventory_elements)

            # Add page break if we have many devices to prevent layout issues
            total_devices = len(cboxes) + len(dboxes) + len(switches)
            if total_devices > 15:  # Threshold for large inventories
                content.append(PageBreak())

        # Add Physical Rack Layout - force to start at top of Page 6
        rack_positions = hardware.get("rack_positions_available", False)
        if rack_positions:
            # Force page break to move heading to top of Page 6
            content.append(PageBreak())

            # Add section heading at top of new page
            heading_elements = self.brand_compliance.create_vast_section_heading(
                "Physical Rack Layout", level=1
            )
            content.extend(heading_elements)

            # Add spacer after heading before diagram
            content.append(Spacer(1, 0.3 * inch))

            # Generate rack diagram
            try:
                # Extract CBox and DBox data for rack diagram
                cboxes_data = []
                dboxes_data = []

                # Get CBox information
                sections = data.get("sections", {})
                cnodes = (
                    sections.get("cnodes_network_configuration", {})
                    .get("data", {})
                    .get("cnodes", [])
                )

                # Also check hardware inventory for CBox data
                hw_cnodes = hardware.get("cnodes", [])

                # Combine data from both sources, prefer hardware inventory
                for cnode in hw_cnodes:
                    cbox_data = {
                        "id": cnode.get("id"),
                        "model": cnode.get("model", cnode.get("box_vendor", "")),
                        "rack_unit": cnode.get(
                            "rack_u", cnode.get("rack_unit", cnode.get("position", ""))
                        ),
                        "state": cnode.get("state", cnode.get("status", "ACTIVE")),
                    }
                    if cbox_data["rack_unit"]:  # Only add if has position
                        cboxes_data.append(cbox_data)

                # Get DBox information (physical chassis, not individual nodes)
                hw_dboxes = hardware.get("dboxes", {})

                for dbox_name, dbox_info in hw_dboxes.items():
                    rack_unit = dbox_info.get("rack_unit", "")
                    if rack_unit:
                        dbox_data = {
                            "id": dbox_info.get("id"),
                            "model": dbox_info.get("hardware_type", "Unknown"),
                            "rack_unit": rack_unit,
                            "state": dbox_info.get("state", "ACTIVE"),
                        }
                        dboxes_data.append(dbox_data)

                # Get switch data for rack diagram
                switches_data = []
                switches = hardware.get("switches", [])
                for switch in switches:
                    switch_data = {
                        "id": switch.get("name", "Unknown"),  # Use name as ID
                        "model": switch.get("model", "switch"),
                        "state": switch.get("state", "ACTIVE"),
                    }
                    switches_data.append(switch_data)

                # Create rack diagram
                if cboxes_data or dboxes_data:
                    rack_gen = RackDiagram()
                    rack_drawing, switch_positions_map = rack_gen.generate_rack_diagram(
                        cboxes_data,
                        dboxes_data,
                        switches_data if switches_data else None,
                    )

                    # Store switch positions for use in inventory table
                    self.switch_positions = switch_positions_map

                    # Center the rack diagram on the page using a table
                    from reportlab.platypus import Table as RLTable

                    # Use letter page width (8.5 inches)
                    page_width = 8.5 * inch
                    rack_table = RLTable(
                        [[rack_drawing]],
                        colWidths=[
                            page_width - (2 * 0.5 * inch)
                        ],  # Page width minus margins
                    )
                    rack_table.setStyle(
                        TableStyle(
                            [
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ]
                        )
                    )
                    content.append(rack_table)

                    switch_msg = (
                        f", {len(switches_data)} Switches" if switches_data else ""
                    )
                    self.logger.info(
                        f"Added rack diagram with {len(cboxes_data)} CBoxes, {len(dboxes_data)} DBoxes{switch_msg}"
                    )
                else:
                    # Fallback to placeholder if no position data
                    layout_elements = (
                        self.brand_compliance.create_vast_2d_diagram_placeholder(
                            "Physical Rack Layout",
                            "Rack position data not available for this cluster.",
                        )
                    )
                    content.extend(layout_elements)
                    self.logger.warning("No rack position data available for diagram")

            except Exception as e:
                self.logger.error(f"Error generating rack diagram: {e}", exc_info=True)
                # Fallback to placeholder on error
                layout_elements = self.brand_compliance.create_vast_2d_diagram_placeholder(
                    "Physical Rack Layout",
                    "Visual representation of hardware positioning in the rack with U-number assignments.",
                )
                content.extend(layout_elements)

        return content

    def _create_network_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create network configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("Network Configuration", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get("sections", {})
        network_config = sections.get("network_configuration", {}).get("data", {})

        # DNS Configuration
        dns_config = network_config.get("dns")
        if dns_config:
            content.append(Paragraph("<b>DNS Configuration:</b>", normal_style))
            content.append(
                Paragraph(
                    f"• Enabled: {dns_config.get('enabled', False)}", normal_style
                )
            )
            servers = dns_config.get("servers", [])
            if servers:
                content.append(
                    Paragraph(f"• Servers: {', '.join(servers)}", normal_style)
                )
            search_domains = dns_config.get("search_domains", [])
            if search_domains:
                content.append(
                    Paragraph(
                        f"• Search Domains: {', '.join(search_domains)}", normal_style
                    )
                )
            content.append(Spacer(1, 8))

        # NTP Configuration
        ntp_config = network_config.get("ntp")
        if ntp_config:
            content.append(Paragraph("<b>NTP Configuration:</b>", normal_style))
            content.append(
                Paragraph(
                    f"• Enabled: {ntp_config.get('enabled', False)}", normal_style
                )
            )
            servers = ntp_config.get("servers", [])
            if servers:
                content.append(
                    Paragraph(f"• Servers: {', '.join(servers)}", normal_style)
                )
            content.append(Spacer(1, 8))

        # VIP Pools
        vippool_config = network_config.get("vippools")
        if vippool_config:
            pools = vippool_config.get("pools", [])
            pool_count = len(pools) if isinstance(pools, list) else 0
            content.append(
                Paragraph(
                    f"<b>VIP Pools:</b> {pool_count} pools configured", normal_style
                )
            )
            content.append(Spacer(1, 8))

        # Cluster Network Configuration
        cluster_summary = data.get("cluster_summary", {})
        if cluster_summary:
            content.append(
                Paragraph("<b>Cluster Network Configuration:</b>", normal_style)
            )

            # Management and Gateway Configuration - Always show placeholders
            management_vips = cluster_summary.get("management_vips")
            management_vips_display = (
                management_vips
                if management_vips and management_vips != "Unknown"
                else "Not Configured"
            )
            content.append(
                Paragraph(f"• Management VIPs: {management_vips_display}", normal_style)
            )

            external_gateways = cluster_summary.get("external_gateways")
            external_gateways_display = (
                external_gateways
                if external_gateways and external_gateways != "Unknown"
                else "Not Configured"
            )
            content.append(
                Paragraph(
                    f"• External Gateways: {external_gateways_display}", normal_style
                )
            )

            # DNS and NTP Configuration - Always show placeholders
            dns = cluster_summary.get("dns")
            dns_display = dns if dns and dns != "Unknown" else "Not Configured"
            content.append(Paragraph(f"• DNS Server: {dns_display}", normal_style))

            ntp = cluster_summary.get("ntp")
            ntp_display = ntp if ntp and ntp != "Unknown" else "Not Configured"
            content.append(Paragraph(f"• NTP Server: {ntp_display}", normal_style))

            # Network Interface Configuration - Always show placeholders
            ext_netmask = cluster_summary.get("ext_netmask")
            ext_netmask_display = (
                ext_netmask
                if ext_netmask and ext_netmask != "Unknown"
                else "Not Configured"
            )
            content.append(
                Paragraph(f"• External Netmask: {ext_netmask_display}", normal_style)
            )

            auto_ports_ext_iface = cluster_summary.get("auto_ports_ext_iface")
            auto_ports_ext_iface_display = (
                auto_ports_ext_iface
                if auto_ports_ext_iface and auto_ports_ext_iface != "Unknown"
                else "Not Configured"
            )
            content.append(
                Paragraph(
                    f"• Auto Ports External Interface: {auto_ports_ext_iface_display}",
                    normal_style,
                )
            )

            # IPMI Configuration - Always show placeholders
            b2b_ipmi = cluster_summary.get("b2b_ipmi")
            b2b_ipmi_display = b2b_ipmi if b2b_ipmi is not None else "Not Configured"
            content.append(Paragraph(f"• B2B IPMI: {b2b_ipmi_display}", normal_style))

            ipmi_gateway = cluster_summary.get("ipmi_gateway")
            ipmi_gateway_display = (
                ipmi_gateway
                if ipmi_gateway and ipmi_gateway != "Unknown"
                else "Not Configured"
            )
            content.append(
                Paragraph(f"• IPMI Gateway: {ipmi_gateway_display}", normal_style)
            )

            ipmi_netmask = cluster_summary.get("ipmi_netmask")
            ipmi_netmask_display = (
                ipmi_netmask
                if ipmi_netmask and ipmi_netmask != "Unknown"
                else "Not Configured"
            )
            content.append(
                Paragraph(f"• IPMI Netmask: {ipmi_netmask_display}", normal_style)
            )

            # MTU Configuration - Always show placeholders
            eth_mtu = cluster_summary.get("eth_mtu")
            eth_mtu_display = eth_mtu if eth_mtu is not None else "Not Configured"
            content.append(
                Paragraph(f"• Ethernet MTU: {eth_mtu_display}", normal_style)
            )

            ib_mtu = cluster_summary.get("ib_mtu")
            ib_mtu_display = ib_mtu if ib_mtu is not None else "Not Configured"
            content.append(
                Paragraph(f"• InfiniBand MTU: {ib_mtu_display}", normal_style)
            )

        return content

    def _create_cluster_network_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create cluster-wide network configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("Cluster Network Configuration", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get("sections", {})
        cluster_network_config = sections.get("cluster_network_configuration", {}).get(
            "data", {}
        )

        if cluster_network_config:
            # Management VIPs
            management_vips = cluster_network_config.get(
                "management_vips", "Not Configured"
            )
            if management_vips != "Not Configured":
                content.append(
                    Paragraph(f"• Management VIPs: {management_vips}", normal_style)
                )
            else:
                content.append(
                    Paragraph("• Management VIPs: Not Configured", normal_style)
                )

            # Management VIP (single)
            mgmt_vip = cluster_network_config.get("mgmt_vip", "Not Configured")
            if mgmt_vip != "Not Configured":
                content.append(Paragraph(f"• Management VIP: {mgmt_vip}", normal_style))

            # Management Inner VIP
            mgmt_inner_vip = cluster_network_config.get(
                "mgmt_inner_vip", "Not Configured"
            )
            if mgmt_inner_vip != "Not Configured":
                content.append(
                    Paragraph(f"• Management Inner VIP: {mgmt_inner_vip}", normal_style)
                )

            # Management Inner VIP CNode
            mgmt_inner_vip_cnode = cluster_network_config.get(
                "mgmt_inner_vip_cnode", "Not Configured"
            )
            if mgmt_inner_vip_cnode != "Not Configured":
                content.append(
                    Paragraph(
                        f"• Management Inner VIP CNode: {mgmt_inner_vip_cnode}",
                        normal_style,
                    )
                )

            # External Gateways
            external_gateways = cluster_network_config.get(
                "external_gateways", "Not Configured"
            )
            if external_gateways != "Not Configured":
                content.append(
                    Paragraph(f"• External Gateways: {external_gateways}", normal_style)
                )
            else:
                content.append(
                    Paragraph("• External Gateways: Not Configured", normal_style)
                )

            # DNS Servers
            dns = cluster_network_config.get("dns", "Not Configured")
            if dns != "Not Configured":
                content.append(Paragraph(f"• DNS Servers: {dns}", normal_style))
            else:
                content.append(Paragraph("• DNS Servers: Not Configured", normal_style))

            # NTP Servers
            ntp = cluster_network_config.get("ntp", "Not Configured")
            if ntp != "Not Configured":
                content.append(Paragraph(f"• NTP Servers: {ntp}", normal_style))
            else:
                content.append(Paragraph("• NTP Servers: Not Configured", normal_style))

            # Network Interface Configuration
            ext_netmask = cluster_network_config.get("ext_netmask", "Unknown")
            ext_netmask_display = (
                ext_netmask if ext_netmask != "Unknown" else "Not Configured"
            )
            content.append(
                Paragraph(f"• External Netmask: {ext_netmask_display}", normal_style)
            )

            auto_ports_ext_iface = cluster_network_config.get(
                "auto_ports_ext_iface", "Unknown"
            )
            auto_ports_ext_iface_display = (
                auto_ports_ext_iface
                if auto_ports_ext_iface != "Unknown"
                else "Not Configured"
            )
            content.append(
                Paragraph(
                    f"• Auto Ports External Interface: {auto_ports_ext_iface_display}",
                    normal_style,
                )
            )

            # IPMI Configuration
            b2b_ipmi = cluster_network_config.get("b2b_ipmi", False)
            content.append(Paragraph(f"• B2B IPMI: {b2b_ipmi}", normal_style))

            # MTU Configuration
            eth_mtu = cluster_network_config.get("eth_mtu", "Unknown")
            eth_mtu_display = eth_mtu if eth_mtu != "Unknown" else "Not Configured"
            content.append(
                Paragraph(f"• Ethernet MTU: {eth_mtu_display}", normal_style)
            )

            ib_mtu = cluster_network_config.get("ib_mtu", "Unknown")
            ib_mtu_display = ib_mtu if ib_mtu != "Unknown" else "Not Configured"
            content.append(
                Paragraph(f"• InfiniBand MTU: {ib_mtu_display}", normal_style)
            )

            # IPMI Gateway and Netmask
            ipmi_gateway = cluster_network_config.get("ipmi_gateway", "Unknown")
            ipmi_gateway_display = (
                ipmi_gateway if ipmi_gateway != "Unknown" else "Not Configured"
            )
            content.append(
                Paragraph(f"• IPMI Gateway: {ipmi_gateway_display}", normal_style)
            )

            ipmi_netmask = cluster_network_config.get("ipmi_netmask", "Unknown")
            ipmi_netmask_display = (
                ipmi_netmask if ipmi_netmask != "Unknown" else "Not Configured"
            )
            content.append(
                Paragraph(f"• IPMI Netmask: {ipmi_netmask_display}", normal_style)
            )

        return content

    def _create_cnodes_network_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create CNodes network configuration section with scale-out support."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("CNodes Network Configuration", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get("sections", {})
        cnodes_network_config = sections.get("cnodes_network_configuration", {}).get(
            "data", {}
        )

        cnodes = cnodes_network_config.get("cnodes", [])
        total_cnodes = cnodes_network_config.get("total_cnodes", 0)

        if cnodes:
            content.append(
                Paragraph(f"<b>Total CNodes:</b> {total_cnodes}", normal_style)
            )
            content.append(Spacer(1, 12))

            # Create table for CNodes with scale-out support
            table_data = [
                [
                    "ID",
                    "Hostname",
                    "Mgmt IP",
                    "IPMI IP",
                    "Box Vendor",
                    "VAST OS",
                    "VMS Host",
                    "TPM Support",
                    "Single NIC",
                    "Net Type",
                ]
            ]

            for cnode in cnodes:
                table_data.append(
                    [
                        str(cnode.get("id", "Unknown")),
                        cnode.get("hostname", "Unknown"),
                        cnode.get("mgmt_ip", "Unknown"),
                        cnode.get("ipmi_ip", "Unknown"),
                        (
                            cnode.get("box_vendor", "Unknown")[:30] + "..."
                            if len(cnode.get("box_vendor", "")) > 30
                            else cnode.get("box_vendor", "Unknown")
                        ),
                        cnode.get("vast_os", "Unknown"),
                        "Yes" if cnode.get("is_vms_host", False) else "No",
                        (
                            "Yes"
                            if cnode.get("tpm_boot_dev_encryption_supported", False)
                            else "No"
                        ),
                        "Yes" if cnode.get("single_nic", False) else "No",
                        cnode.get("net_type", "Unknown"),
                    ]
                )

            # Create table with page-width sizing (A4 width - 1" margins = 7.5")
            page_width = 7.5 * inch  # A4 width minus 0.5" margins on each side
            table = Table(
                table_data,
                colWidths=[
                    page_width * 0.08,  # ID
                    page_width * 0.18,  # Hostname
                    page_width * 0.12,  # Mgmt IP
                    page_width * 0.12,  # IPMI IP
                    page_width * 0.20,  # Box Vendor
                    page_width * 0.12,  # VAST OS
                    page_width * 0.06,  # VMS Host
                    page_width * 0.06,  # TPM Support
                    page_width * 0.06,  # Single NIC
                    page_width * 0.10,  # Net Type
                ],
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("FONTSIZE", (0, 1), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                    ]
                )
            )

            content.append(table)
        else:
            content.append(
                Paragraph(
                    "No CNodes network configuration data available", normal_style
                )
            )

        return content

    def _create_dnodes_network_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create DNodes network configuration section with scale-out support."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("DNodes Network Configuration", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get("sections", {})
        dnodes_network_config = sections.get("dnodes_network_configuration", {}).get(
            "data", {}
        )

        dnodes = dnodes_network_config.get("dnodes", [])
        total_dnodes = dnodes_network_config.get("total_dnodes", 0)

        if dnodes:
            content.append(
                Paragraph(f"<b>Total DNodes:</b> {total_dnodes}", normal_style)
            )
            content.append(Spacer(1, 12))

            # Create table for DNodes with scale-out support
            table_data = [
                [
                    "ID",
                    "Hostname",
                    "Mgmt IP",
                    "IPMI IP",
                    "Box Vendor",
                    "VAST OS",
                    "Position",
                    "Ceres",
                    "Ceres v2",
                    "Net Type",
                ]
            ]

            for dnode in dnodes:
                table_data.append(
                    [
                        str(dnode.get("id", "Unknown")),
                        dnode.get("hostname", "Unknown"),
                        dnode.get("mgmt_ip", "Unknown"),
                        dnode.get("ipmi_ip", "Unknown"),
                        (
                            dnode.get("box_vendor", "Unknown")[:30] + "..."
                            if len(dnode.get("box_vendor", "")) > 30
                            else dnode.get("box_vendor", "Unknown")
                        ),
                        dnode.get("vast_os", "Unknown"),
                        dnode.get("position", "Unknown"),
                        "Yes" if dnode.get("is_ceres", False) else "No",
                        "Yes" if dnode.get("is_ceres_v2", False) else "No",
                        dnode.get("net_type", "Unknown"),
                    ]
                )

            # Create table with page-width sizing (A4 width - 1" margins = 7.5")
            page_width = 7.5 * inch  # A4 width minus 0.5" margins on each side
            table = Table(
                table_data,
                colWidths=[
                    page_width * 0.08,  # ID
                    page_width * 0.18,  # Hostname
                    page_width * 0.12,  # Mgmt IP
                    page_width * 0.12,  # IPMI IP
                    page_width * 0.20,  # Box Vendor
                    page_width * 0.12,  # VAST OS
                    page_width * 0.06,  # Position
                    page_width * 0.06,  # Ceres
                    page_width * 0.06,  # Ceres v2
                    page_width * 0.10,  # Net Type
                ],
            )
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
                        ("FONTSIZE", (0, 1), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                    ]
                )
            )

            content.append(table)
        else:
            content.append(
                Paragraph(
                    "No DNodes network configuration data available", normal_style
                )
            )

        return content

    def _create_comprehensive_network_configuration(
        self, data: Dict[str, Any]
    ) -> List[Any]:
        """Create comprehensive network configuration section consolidating all network data."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        subheading_style = ParagraphStyle(
            "Subsection_Heading",
            parent=styles["Heading2"],
            fontSize=self.config.heading_font_size - 2,
            spaceAfter=8,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        # Start on new page (Page 7)
        content.append(PageBreak())

        # Add section heading with VAST styling
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Network Configuration", level=1
        )
        content.extend(heading_elements)

        # Section Overview
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Network Configuration section provides comprehensive documentation of all network-related settings and connectivity parameters for the VAST Data cluster. This section includes cluster-wide network configuration, individual node network settings for both compute nodes (CNodes) and data nodes (DNodes), and network service configurations such as DNS and NTP. The network configuration data is essential for understanding cluster connectivity, troubleshooting network issues, validating network security settings, and ensuring proper network segmentation. This information supports network administrators in maintaining optimal network performance and security posture for the storage infrastructure.",
                overview_style,
            )
        )
        content.append(Spacer(1, 8))

        sections = data.get("sections", {})

        # Add Network Configuration summary table (similar to Storage Capacity)
        cluster_network_config = sections.get("cluster_network_configuration", {}).get(
            "data", {}
        )
        if cluster_network_config:
            network_summary_data = []

            # Management and Gateway settings
            if (
                cluster_network_config.get("management_vips")
                and cluster_network_config.get("management_vips") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "Management VIPs",
                        cluster_network_config.get("management_vips", "Not Configured"),
                    ]
                )
            if (
                cluster_network_config.get("external_gateways")
                and cluster_network_config.get("external_gateways") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "External Gateways",
                        cluster_network_config.get(
                            "external_gateways", "Not Configured"
                        ),
                    ]
                )

            # DNS and NTP settings
            if (
                cluster_network_config.get("dns")
                and cluster_network_config.get("dns") != "Not Configured"
            ):
                network_summary_data.append(
                    ["DNS Servers", cluster_network_config.get("dns", "Not Configured")]
                )
            if (
                cluster_network_config.get("ntp")
                and cluster_network_config.get("ntp") != "Not Configured"
            ):
                network_summary_data.append(
                    ["NTP Servers", cluster_network_config.get("ntp", "Not Configured")]
                )

            # Network interface settings
            if (
                cluster_network_config.get("ext_netmask")
                and cluster_network_config.get("ext_netmask") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "External Netmask",
                        cluster_network_config.get("ext_netmask", "Not Configured"),
                    ]
                )
            if (
                cluster_network_config.get("auto_ports_ext_iface")
                and cluster_network_config.get("auto_ports_ext_iface")
                != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "Auto Ports Ext Interface",
                        cluster_network_config.get(
                            "auto_ports_ext_iface", "Not Configured"
                        ),
                    ]
                )

            # MTU settings
            if (
                cluster_network_config.get("eth_mtu")
                and cluster_network_config.get("eth_mtu") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "Ethernet MTU",
                        str(cluster_network_config.get("eth_mtu", "Not Configured")),
                    ]
                )
            if (
                cluster_network_config.get("ib_mtu")
                and cluster_network_config.get("ib_mtu") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "InfiniBand MTU",
                        str(cluster_network_config.get("ib_mtu", "Not Configured")),
                    ]
                )

            # IPMI settings
            if (
                cluster_network_config.get("ipmi_gateway")
                and cluster_network_config.get("ipmi_gateway") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "IPMI Gateway",
                        cluster_network_config.get("ipmi_gateway", "Not Configured"),
                    ]
                )
            if (
                cluster_network_config.get("ipmi_netmask")
                and cluster_network_config.get("ipmi_netmask") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "IPMI Netmask",
                        cluster_network_config.get("ipmi_netmask", "Not Configured"),
                    ]
                )

            # B2B IPMI setting
            if cluster_network_config.get("b2b_ipmi") is not None:
                network_summary_data.append(
                    ["B2B IPMI", str(cluster_network_config.get("b2b_ipmi", False))]
                )

            # Net Type setting
            if (
                cluster_network_config.get("net_type")
                and cluster_network_config.get("net_type") != "Not Configured"
            ):
                network_summary_data.append(
                    [
                        "Net Type",
                        cluster_network_config.get("net_type", "Not Configured"),
                    ]
                )

            if network_summary_data:
                network_table_elements = self.brand_compliance.create_vast_table(
                    network_summary_data, "Network Configuration", ["Setting", "Value"]
                )
                content.extend(network_table_elements)
                content.append(Spacer(1, 16))

        # 1. CNodes Network Configuration
        cnodes_network_config = sections.get("cnodes_network_configuration", {}).get(
            "data", {}
        )
        cnodes = cnodes_network_config.get("cnodes", [])
        total_cnodes = cnodes_network_config.get("total_cnodes", 0)

        if cnodes:

            # Create table for CNodes with scale-out support
            headers = [
                "ID",
                "Hostname",
                "Mgmt IP",
                "IPMI IP",
                "VAST OS",
                "VMS Host",
            ]

            table_data = []
            for cnode in cnodes:
                table_data.append(
                    [
                        cnode.get("id", "Unknown"),
                        cnode.get("hostname", "Unknown"),
                        cnode.get("mgmt_ip", "Unknown"),
                        cnode.get("ipmi_ip", "Unknown"),
                        cnode.get("vast_os", "Unknown"),
                        str(cnode.get("is_vms_host", False)),
                    ]
                )

            # Create table with pagination support
            table_elements = (
                self.brand_compliance.create_vast_hardware_table_with_pagination(
                    table_data, "CNode Network Configuration", headers
                )
            )
            content.extend(table_elements)
            content.append(Spacer(1, 16))

        # 2. DNodes Network Configuration
        dnodes_network_config = sections.get("dnodes_network_configuration", {}).get(
            "data", {}
        )
        dnodes = dnodes_network_config.get("dnodes", [])

        if dnodes:
            # Create table for DNodes with scale-out support
            headers = [
                "ID",
                "Hostname",
                "Mgmt IP",
                "IPMI IP",
                "VAST OS",
                "Position",
            ]

            table_data = []
            for dnode in dnodes:
                table_data.append(
                    [
                        dnode.get("id", "Unknown"),
                        dnode.get("hostname", "Unknown"),
                        dnode.get("mgmt_ip", "Unknown"),
                        dnode.get("ipmi_ip", "Unknown"),
                        dnode.get("vast_os", "Unknown"),
                        dnode.get("position", "Unknown"),
                    ]
                )

            # Create table with pagination support
            table_elements = (
                self.brand_compliance.create_vast_hardware_table_with_pagination(
                    table_data, "DNode Network Configuration", headers
                )
            )
            content.extend(table_elements)
            content.append(Spacer(1, 16))

        return content

    def _create_logical_network_diagram(self, data: Dict[str, Any]) -> List[Any]:
        """
        Create logical network diagram section.

        Args:
            data: Processed cluster data

        Returns:
            List of reportlab flowables for the section
        """
        content = []

        # Add section heading with VAST styling
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Logical Network Diagram", level=1
        )
        content.extend(heading_elements)

        # Section Overview
        styles = getSampleStyleSheet()
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Logical Network Diagram provides a visual "
                "representation of the cluster's network topology, "
                "illustrating the connectivity between compute nodes "
                "(CBoxes), data nodes (DBoxes), network switches, "
                "and the customer network. This diagram shows the "
                "redundant network paths, switch interconnections, "
                "and how data flows through the storage infrastructure. "
                "Understanding the logical network topology "
                "is essential for network planning, troubleshooting "
                "connectivity issues, validating redundancy "
                "configurations, and ensuring optimal network performance "
                "across the storage cluster.",
                overview_style,
            )
        )
        content.append(Spacer(1, 16))

        # Generate network diagram dynamically
        try:
            from network_diagram import NetworkDiagramGenerator

            # Get required data
            port_mapping_section = data.get("sections", {}).get("port_mapping", {})
            port_mapping_data = (
                port_mapping_section.get("data", {})
                if isinstance(port_mapping_section, dict)
                else {}
            )

            # Prepare hardware data from hardware_inventory
            hardware_inventory = data.get("hardware_inventory", {})

            # Convert cboxes/dboxes from dict to list if needed
            cboxes_data = hardware_inventory.get("cboxes", [])
            dboxes_data = hardware_inventory.get("dboxes", [])
            switches_data = hardware_inventory.get("switches", [])

            # If cboxes/dboxes are dicts (keyed by name), convert to list of values
            cboxes_list = (
                list(cboxes_data.values())
                if isinstance(cboxes_data, dict)
                else cboxes_data
            )
            dboxes_list = (
                list(dboxes_data.values())
                if isinstance(dboxes_data, dict)
                else dboxes_data
            )
            switches_list = switches_data if isinstance(switches_data, list) else []

            hardware_data = {
                "cboxes": cboxes_list,
                "dboxes": dboxes_list,
                "switches": switches_list,
            }

            self.logger.info(
                f"Hardware data for diagram: {len(hardware_data['cboxes'])} CBoxes, "
                f"{len(hardware_data['dboxes'])} DBoxes, {len(hardware_data['switches'])} Switches"
            )

            # Create output directory
            diagrams_dir = Path(__file__).parent.parent / "output" / "diagrams"
            diagrams_dir.mkdir(parents=True, exist_ok=True)

            # Generate diagram
            diagram_generator = NetworkDiagramGenerator(
                assets_path=str(Path(__file__).parent.parent / "assets")
            )

            diagram_path = diagrams_dir / "network_topology.pdf"

            # Use standard width but reduce height to fit on page 11
            # Width: standard letter - margins, Height: reduced to fit
            target_diagram_width = 6.5 * inch
            target_diagram_height = 6.0 * inch  # Reduced from ~9" to fit on page

            generated_path = diagram_generator.generate_network_diagram(
                port_mapping_data=port_mapping_data,
                hardware_data=hardware_data,
                output_path=str(diagram_path),
                drawing_size=(target_diagram_width, target_diagram_height),
            )

            # Add color legend
            legend_style = ParagraphStyle(
                "Diagram_Legend",
                parent=styles["Normal"],
                fontSize=self.config.font_size - 1,
                textColor=colors.HexColor("#666666"),
                alignment=TA_CENTER,
                spaceAfter=12,
            )
            content.append(
                Paragraph(
                    "<font color='#00aa00'><b>■</b> Green</font> = Switch A connections | "
                    "<font color='#0066cc'><b>■</b> Blue</font> = Switch B connections | "
                    "<font color='#9933cc'><b>■</b> Purple</font> = IPL/MLAG connections",
                    legend_style,
                )
            )
            content.append(Spacer(1, 12))

            if generated_path and Path(generated_path).exists():
                self.logger.info(f"Network diagram generated: {generated_path}")

                # Embed the generated diagram (PNG)
                try:
                    # Calculate available space on page
                    if self.config.page_size == "Letter":
                        page_width = 8.5 * inch
                        page_height = 11 * inch
                    else:  # A4
                        page_width = 8.27 * inch
                        page_height = 11.69 * inch

                    # Account for margins and header/footer
                    available_width = page_width - (2 * 0.5 * inch)
                    available_height = page_height - (
                        2 * 0.75 * inch
                    )  # Top and bottom margins

                    # Reserve space for heading and spacing (approximately 1 inch)
                    max_diagram_height = available_height - 1.5 * inch

                    # Get actual image dimensions to calculate aspect ratio
                    from PIL import Image as PILImage

                    with PILImage.open(str(generated_path)) as pil_img:
                        img_width, img_height = pil_img.size
                        aspect_ratio = img_width / img_height

                    # Calculate dimensions to fit within available space while maintaining aspect ratio
                    # Try fitting by width first
                    target_width = available_width * 0.95  # Use 95% of available width
                    target_height = target_width / aspect_ratio

                    # If height exceeds available space, scale by height instead
                    if target_height > max_diagram_height:
                        target_height = max_diagram_height
                        target_width = target_height * aspect_ratio

                    self.logger.info(
                        f"Network diagram sizing: original={img_width}x{img_height}, "
                        f"target={target_width:.1f}x{target_height:.1f}, "
                        f"available={available_width:.1f}x{max_diagram_height:.1f}"
                    )

                    # Load and add the dynamically generated diagram with calculated dimensions
                    img = Image(
                        str(generated_path),
                        width=target_width,
                        height=target_height,
                    )

                    # Center the image using a table
                    from reportlab.platypus import Table as RLTable

                    image_table = RLTable(
                        [[img]],
                        colWidths=[available_width],
                    )
                    image_table.setStyle(
                        TableStyle(
                            [
                                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                            ]
                        )
                    )
                    content.append(image_table)

                    self.logger.info(f"Embedded dynamically generated network diagram")

                    # Skip loading static placeholder since we have the dynamic one
                    return content

                except Exception as e:
                    self.logger.error(
                        f"Error embedding generated diagram: {e}", exc_info=True
                    )
                    # Fall through to try static placeholder

            else:
                self.logger.warning(
                    "Network diagram PNG not available. Using placeholder. "
                    "For dynamic diagrams, install: pip install reportlab[renderPM]"
                )

        except Exception as e:
            self.logger.error(f"Error generating network diagram: {e}", exc_info=True)

        # Check if static network diagram image exists (try PNG first, then JPG)
        diagram_path_png = (
            Path(__file__).parent.parent
            / "assets"
            / "diagrams"
            / "network_topology_placeholder.png"
        )
        diagram_path_jpg = (
            Path(__file__).parent.parent
            / "assets"
            / "diagrams"
            / "network_topology_placeholder.jpg"
        )

        diagram_path = None
        if diagram_path_png.exists():
            diagram_path = diagram_path_png
        elif diagram_path_jpg.exists():
            diagram_path = diagram_path_jpg

        if diagram_path:
            try:
                # Calculate image size to fit on page
                # A4 width in points
                if self.config.page_size == "Letter":
                    page_width = 8.5 * inch
                else:
                    page_width = 595.27

                available_width = page_width - (2 * 0.5 * inch)
                max_height = 5.5 * inch

                # Load and add the network diagram image
                img = Image(
                    str(diagram_path),
                    width=available_width * 0.9,
                    height=max_height,
                    kind="proportional",
                )

                # Center the image using a table
                from reportlab.platypus import Table as RLTable

                image_table = RLTable(
                    [[img]],
                    colWidths=[available_width],
                )
                image_table.setStyle(
                    TableStyle(
                        [
                            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ]
                    )
                )
                content.append(Spacer(1, 12))
                content.append(image_table)

                self.logger.info(f"Added network topology diagram from {diagram_path}")

            except Exception as e:
                self.logger.error(f"Error loading network diagram: {e}", exc_info=True)
                # Add placeholder text if image fails to load
                content.append(
                    Paragraph(
                        "<i>[Network topology diagram placeholder - "
                        "Image failed to load]</i>",
                        styles["Normal"],
                    )
                )
        else:
            # Add placeholder if image doesn't exist
            placeholder_elements = (
                self.brand_compliance.create_vast_2d_diagram_placeholder(
                    "Network Topology Diagram",
                    "Visual representation of cluster network connectivity "
                    "showing CBoxes, DBoxes, switches, and customer network "
                    "connections.",
                )
            )
            content.extend(placeholder_elements)
            self.logger.info(
                "Network diagram placeholder shown - static image not found"
            )

        return content

    def _classify_port_purpose(
        self, port_name: str, speed: str, total_switches: int
    ) -> str:
        """
        Classify port purpose based on speed, port number, and cluster topology.

        Args:
            port_name: Port name (e.g., "swp1", "eth1/1")
            speed: Port speed (e.g., "200G", "100G", None)
            total_switches: Total number of switches in cluster

        Returns:
            Port classification string
        """
        # Extract port number from name (handles swp1, eth1/1, etc.)
        try:
            port_num = int("".join(filter(str.isdigit, port_name)))
        except (ValueError, TypeError):
            port_num = 0

        # Classification logic based on speed and port position
        if speed == "200G":
            # 200G ports are typically data plane connections
            if 1 <= port_num <= 14:
                return "Data Plane (CNode)"
            elif 15 <= port_num <= 28:
                return "Data Plane (DNode)"
            else:
                return "Data Plane"

        elif speed == "100G":
            # 100G ports are typically IPLs, uplinks, or standard data plane
            if port_num in [29, 30]:
                # Ports 29-30 typically used for MLAG IPL (Inter-Peer Link)
                return "IPL (Inter-Peer Link)" if total_switches > 1 else "Reserved"
            elif port_num in [31, 32]:
                # Ports 31-32 typically used for uplinks to spine/core
                return "Uplink (Spine/Core)"
            else:
                return "Data Plane"

        elif speed == "Unconfigured" or not speed:
            # Unconfigured ports are unused or reserved
            return "Unused/Reserved"

        else:
            # Other speeds (40G, 10G, etc.)
            return "Data Plane"

    def _create_port_mapping_section(
        self, port_mapping_data: Dict[str, Any], switches: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Create port mapping section with detailed port-to-device mappings.

        Args:
            port_mapping_data: Port mapping data from data extractor
            switches: List of switch hardware data

        Returns:
            List of ReportLab elements for port mapping section
        """
        content = []
        styles = getSampleStyleSheet()

        # Add section heading
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Port Mapping", level=1
        )
        content.extend(heading_elements)

        # Section Overview
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Port Mapping section provides detailed connectivity information showing which switch ports connect to which cluster nodes. This information is critical for troubleshooting network issues, validating cabling, and planning maintenance activities. The mapping uses standardized designations to clearly identify each connection point on both the switch side and node side.",
                overview_style,
            )
        )
        content.append(Spacer(1, 12))

        # Get port map organized by switch
        port_map = port_mapping_data.get("port_map", [])
        has_cross_connections = port_mapping_data.get("has_cross_connections", False)

        if not port_map:
            content.append(
                Paragraph("No port mapping data available", styles["Normal"])
            )
            return content

        # Group ports by switch
        ports_by_switch = {}
        for entry in port_map:
            switch_ip = entry["switch_ip"]
            if switch_ip not in ports_by_switch:
                ports_by_switch[switch_ip] = []
            ports_by_switch[switch_ip].append(entry)

        # Sort ports within each switch by port number
        for switch_ip in ports_by_switch:
            ports_by_switch[switch_ip].sort(
                key=lambda x: (
                    int("".join(filter(str.isdigit, x["port"])))
                    if any(c.isdigit() for c in x["port"])
                    else 0
                )
            )

        # Find switch info from switches list to get switch numbers
        switch_ip_to_number = {}
        for idx, switch in enumerate(switches, start=1):
            switch_ip_to_number[switch.get("mgmt_ip")] = idx

        # Create port map table for each switch
        for switch_ip, connections in ports_by_switch.items():
            switch_num = switch_ip_to_number.get(switch_ip, "?")

            # Build table data - filter to show only primary physical connections
            table_data = []
            headers = ["Switch Port", "Node Connection", "Network", "Speed", "Notes"]

            # Track which ports we've already added to avoid duplicates
            # Key: (switch_designation, node_designation, network)
            seen_connections = set()

            for conn in connections:
                # Smart filtering: show one primary interface per network per node
                # CNodes: f0 = Net A (primary), f1 = Net B (primary), f2/f3 = bonded
                # DNodes: f0 = Net A (primary), f2/f3 = Net B (primary - different than CNodes!)

                interface = conn.get("interface", "")
                network = conn.get("network", "?")
                node_designation = conn.get("node_designation", "Unknown")

                # Determine if this is a DNode or CNode
                is_dnode = "DN" in node_designation
                is_cnode = "CN" in node_designation
                is_unknown = "UNKNOWN" in node_designation.upper()

                # Primary interface logic (simplified):
                # Show ONLY f0 and f1 interfaces - these are the primary physical ports
                # f0 = First physical NIC port
                # f1 = Second physical NIC port
                # f2/f3 = Bonded/virtual interfaces (skip these)
                #
                # Network assignment (A or B) is already correctly determined
                # by which switch the connection is on, so we don't need to
                # make assumptions about which interface goes to which network.

                is_primary = False
                if "f0" in interface or "f1" in interface:
                    # This is a primary physical interface
                    is_primary = True

                # Skip non-primary interfaces (f2, f3, bonds, VLANs, etc.)
                if not is_primary:
                    continue

                # Use enhanced switch designation (e.g., SWA-P20)
                port_display = conn.get("switch_designation", conn["port"])

                # Use node designation (already have it from above)
                node_display = node_designation

                # Create unique key for this connection
                conn_key = (port_display, node_designation, network)

                # Skip if we've already added this connection
                if conn_key in seen_connections:
                    continue
                seen_connections.add(conn_key)

                speed = "200G"  # Default, would need to get from switch port data

                # Simple notes - all primary connections are correct
                notes_str = "Primary"

                table_data.append(
                    [port_display, node_display, network, speed, notes_str]
                )

            # Add IPL/MLAG connections to this switch's table
            # Use the new deduplicated ipl_connections format
            ipl_connections = port_mapping_data.get("ipl_connections", [])
            if ipl_connections:
                # Add IPL connections for this switch
                for ipl_conn in ipl_connections:
                    # ipl_conn format (stored from Switch 1's perspective):
                    # {
                    #   'switch_designation': 'SWA-P29',  (always Switch 1)
                    #   'node_designation': 'SWB-P29',     (always Switch 2)
                    #   'notes': 'IPL',
                    #   'connection_type': 'IPL',
                    #   ...
                    # }

                    # Check which switch this is and format accordingly
                    switch_des = ipl_conn.get("switch_designation", "")
                    node_des = ipl_conn.get("node_designation", "")

                    # Extract switch letter from designation (SWA-P29 -> A, SWB-P29 -> B)
                    if "SWA" in switch_des and switch_num == 1:
                        # This is Switch 1: show SWA-P29 → SWB-P29
                        table_data.append(
                            [
                                switch_des,  # SWA-P29
                                node_des,  # SWB-P29
                                "A/B",  # Network (both)
                                "100G",  # Speed
                                ipl_conn.get("notes", "IPL"),  # IPL
                            ]
                        )
                    elif "SWB" in node_des and switch_num == 2:
                        # This is Switch 2: swap the columns to show SWB-P29 → SWA-P29
                        table_data.append(
                            [
                                node_des,  # SWB-P29 (was in node_designation)
                                switch_des,  # SWA-P29 (was in switch_designation)
                                "A/B",  # Network (both)
                                "100G",  # Speed
                                ipl_conn.get("notes", "IPL"),  # IPL
                            ]
                        )

            # Create table
            table_title = f"Switch {switch_num} Port-to-Device Mapping"
            table_elements = self.brand_compliance.create_vast_table(
                table_data, table_title, headers
            )
            content.extend(table_elements)
            content.append(Spacer(1, 12))

        # Note: Cross-connection detection disabled - VAST dual-network design
        # naturally has both Network A and B on both switches for redundancy
        # Add cross-connection summary if any issues detected
        if False and has_cross_connections:  # Disabled
            content.append(Spacer(1, 12))

            warning_heading = self.brand_compliance.create_vast_section_heading(
                "⚠️ Network Configuration Issues Detected", level=2
            )
            content.extend(warning_heading)

            cross_connections = port_mapping_data.get("cross_connections", [])
            cross_summary = port_mapping_data.get("cross_connection_summary", "")

            issue_style = ParagraphStyle(
                "Issue_Style",
                parent=styles["Normal"],
                fontSize=self.config.font_size,
                textColor=colors.HexColor("#d62728"),  # Red warning color
                spaceAfter=8,
                spaceBefore=8,
                leftIndent=20,
                rightIndent=20,
            )

            content.append(
                Paragraph(
                    f"<b>Summary:</b> {cross_summary}",
                    issue_style,
                )
            )
            content.append(Spacer(1, 8))

            # List specific cross-connection issues
            issue_list_data = []
            issue_headers = [
                "Switch Port",
                "Node",
                "Actual Network",
                "Expected Network",
            ]

            for issue in cross_connections:
                issue_list_data.append(
                    [
                        issue.get("port", "Unknown"),
                        issue.get("node", issue.get("node_designation", "Unknown")),
                        f"Network {issue.get('actual_network', '?')}",
                        f"Network {issue.get('expected_network', '?')}",
                    ]
                )

            issue_table_elements = self.brand_compliance.create_vast_table(
                issue_list_data, "Cross-Connection Details", issue_headers
            )
            content.extend(issue_table_elements)
            content.append(Spacer(1, 12))

        # IPL/MLAG ports are now integrated into switch port tables above
        # No separate section needed

        return content

    def _create_switch_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create switch configuration section with port details."""
        content = []

        # Add section heading with VAST styling
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Switch Configuration", level=1
        )
        content.extend(heading_elements)

        # Section Overview
        styles = getSampleStyleSheet()
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Switch Configuration section provides detailed information about the network switches that form the fabric interconnecting the VAST cluster nodes. This section documents switch hardware specifications, port configurations, operational status, and connectivity details. Understanding the switch topology is critical for network troubleshooting, capacity planning, and validating proper network segmentation. The port-level details enable network administrators to trace physical connectivity, identify unused ports, and plan for cluster expansion.",
                overview_style,
            )
        )
        content.append(Spacer(1, 8))

        # Get switch data
        hardware = data.get("hardware_inventory", {})
        switches = hardware.get("switches", [])

        if not switches:
            content.append(Paragraph("No switch data available", styles["Normal"]))
            return content

        # For each switch, create a detailed port configuration table on separate page
        for switch_num, switch in enumerate(switches, start=1):
            # Add page break before each switch (except the first)
            if switch_num > 1:
                content.append(PageBreak())

            # Add "Switch # Details" heading
            switch_details_heading = self.brand_compliance.create_vast_section_heading(
                f"Switch {switch_num} Details", level=2
            )
            content.extend(switch_details_heading)

            switch_name = switch.get("name", "Unknown")
            hostname = switch.get("hostname", "Unknown")
            model = switch.get("model", "Unknown")
            serial = switch.get("serial", "Unknown")
            firmware_version = switch.get("firmware_version", "Unknown")
            mgmt_ip = switch.get("mgmt_ip", "Unknown")
            switch_type = switch.get("switch_type", "Unknown")
            state = switch.get("state", "Unknown")
            configured = switch.get("configured", False)
            role = switch.get("role", "Unknown")
            total_ports = switch.get("total_ports", 0)
            active_ports = switch.get("active_ports", 0)
            mtu = switch.get("mtu", "Unknown")
            port_speeds = switch.get("port_speeds", {})
            ports = switch.get("ports", [])

            # Capitalize switch type for display
            if switch_type.lower() == "cumulus":
                switch_type_display = "Cumulus Linux"
            else:
                switch_type_display = switch_type

            # Format configuration status
            config_status = "Configured" if configured else "Not Configured"

            # Switch header info
            switch_info_data = [
                ["Hostname", hostname],
                ["Model", model],
                ["Serial Number", serial],
                ["Firmware Version", firmware_version],
                ["Management IP", mgmt_ip],
                ["Switch Type", switch_type_display],
                ["State", state],
                ["Configuration Status", config_status],
                ["Role", role if role else "Not Assigned"],
                ["Total Ports", str(total_ports)],
                ["Active Ports", str(active_ports)],
                ["Port MTU", mtu],
            ]

            # Create switch info table
            switch_info_elements = self._create_cluster_info_table(
                switch_info_data, f"{switch_name} Configuration"
            )
            content.extend(switch_info_elements)
            content.append(Spacer(1, 12))

            # Create port summary table with port numbers
            if ports:
                # Aggregate ports by speed, collecting port names
                port_summary = {}

                for port in ports:
                    speed = port.get("speed")
                    if not speed or speed == "":
                        speed = "Unconfigured"

                    port_name = port.get("name", "Unknown")

                    if speed not in port_summary:
                        port_summary[speed] = []
                    port_summary[speed].append(port_name)

                # Create summary table with port count and port numbers
                summary_table_data = []
                headers = ["Port Count", "Speed", "Port Numbers"]

                # Sort by speed (200G, 100G, Unconfigured, then others)
                speed_order = {"200G": 0, "100G": 1, "Unconfigured": 2}
                sorted_summary = sorted(
                    port_summary.items(), key=lambda x: speed_order.get(x[0], 3)
                )

                for speed, port_list in sorted_summary:
                    # Sort port names naturally (swp1, swp2, ..., swp10, swp11, ...)
                    try:
                        sorted_ports = sorted(
                            port_list,
                            key=lambda x: (
                                int("".join(filter(str.isdigit, x)))
                                if any(c.isdigit() for c in x)
                                else 0
                            ),
                        )
                    except:
                        sorted_ports = sorted(port_list)

                    # Join ports with comma separation
                    ports_str = ", ".join(sorted_ports)

                    # Use Paragraph for port numbers to enable text wrapping
                    port_style = ParagraphStyle(
                        "PortNumbers",
                        parent=styles["Normal"],
                        fontSize=9,
                        alignment=0,  # Left alignment
                        wordWrap="CJK",  # Enable word wrapping
                    )
                    port_para = Paragraph(ports_str, port_style)

                    # Count ports for this speed
                    port_count = len(port_list)

                    summary_table_data.append([str(port_count), speed, port_para])

                # Create custom port summary table with specific column widths
                # Port Count: 15%, Speed: 15%, Port Numbers: 70%
                page_width = 7.5 * inch
                col_widths = [
                    page_width * 0.15,  # Port Count (matches Speed column)
                    page_width * 0.15,  # Speed (reduced by 50%)
                    page_width * 0.70,  # Port Numbers (reduced slightly)
                ]

                # Add title
                table_title = f"{switch_name} Port Summary"
                title_para = Paragraph(
                    f"<b>{table_title}</b>",
                    self.brand_compliance.styles["vast_subheading"],
                )
                content.append(title_para)
                content.append(Spacer(1, 8))

                # Prepare table data with headers
                full_table_data = [headers] + summary_table_data

                # Create table with custom column widths
                port_table = Table(full_table_data, colWidths=col_widths, repeatRows=1)

                # Apply VAST brand table styling
                table_style = TableStyle(
                    [
                        # Header row styling
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            self.brand_compliance.colors.BACKGROUND_DARK,
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            self.brand_compliance.colors.PURE_WHITE,
                        ),
                        (
                            "FONTNAME",
                            (0, 0),
                            (-1, 0),
                            self.brand_compliance.typography.PRIMARY_FONT,
                        ),
                        (
                            "FONTSIZE",
                            (0, 0),
                            (-1, 0),
                            self.brand_compliance.typography.BODY_SIZE,
                        ),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        # Data rows styling
                        (
                            "BACKGROUND",
                            (0, 1),
                            (-1, -1),
                            self.brand_compliance.colors.VAST_BLUE_LIGHTEST,
                        ),
                        (
                            "TEXTCOLOR",
                            (0, 1),
                            (-1, -1),
                            self.brand_compliance.colors.DARK_GRAY,
                        ),
                        (
                            "FONTNAME",
                            (0, 1),
                            (-1, -1),
                            self.brand_compliance.typography.BODY_FONT,
                        ),
                        (
                            "FONTSIZE",
                            (0, 1),
                            (-1, -1),
                            self.brand_compliance.typography.BODY_SIZE,
                        ),
                        # Borders and spacing
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            1,
                            self.brand_compliance.colors.BACKGROUND_DARK,
                        ),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [
                                self.brand_compliance.colors.PURE_WHITE,
                                self.brand_compliance.colors.ALTERNATING_ROW,
                            ],
                        ),
                        ("PADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 12),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
                        ("WORDWRAP", (0, 0), (-1, -1), "CJK"),
                    ]
                )

                port_table.setStyle(table_style)
                content.append(port_table)
                content.append(Spacer(1, 12))

        # Add port mapping section if available
        port_mapping_section = data.get("sections", {}).get("port_mapping", {})
        port_mapping_data = port_mapping_section.get("data", {})

        if port_mapping_data.get("available"):
            content.append(PageBreak())
            port_mapping_content = self._create_port_mapping_section(
                port_mapping_data, switches
            )
            content.extend(port_mapping_content)

        return content

    def _create_logical_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create logical configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        content = []

        content.append(Paragraph("Logical Configuration", heading_style))
        content.append(Spacer(1, 12))

        # Section Overview
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Logical Configuration section documents the logical organization and data protection policies configured within the VAST Data cluster. This section provides visibility into tenant configurations, data views, access policies, VIP pools, and data protection settings including snapshot programs and protection policies. Understanding the logical configuration is crucial for data governance, access control validation, backup and recovery planning, and ensuring compliance with organizational data protection requirements. This information enables administrators to verify proper data isolation, validate backup schedules, and ensure that data protection policies align with business continuity objectives.",
                overview_style,
            )
        )
        content.append(Spacer(1, 8))

        sections = data.get("sections", {})
        logical_config = sections.get("logical_configuration", {}).get("data", {})

        # Prepare table data
        table_data = []

        # Tenants
        tenants = logical_config.get("tenants")
        if tenants:
            tenant_list = (
                tenants.get("tenants", []) if isinstance(tenants, dict) else tenants
            )
            tenant_count = len(tenant_list) if isinstance(tenant_list, list) else 0
            table_data.append(["Tenants", f"{tenant_count} tenants configured"])

        # Views
        views = logical_config.get("views")
        if views:
            view_list = views.get("views", []) if isinstance(views, dict) else views
            view_count = len(view_list) if isinstance(view_list, list) else 0
            table_data.append(["Views", f"{view_count} views configured"])

        # View Policies
        policies = logical_config.get("view_policies")
        if policies:
            policy_list = (
                policies.get("policies", []) if isinstance(policies, dict) else policies
            )
            policy_count = len(policy_list) if isinstance(policy_list, list) else 0
            table_data.append(["View Policies", f"{policy_count} policies configured"])

        # Protection Policies
        protection_policies = logical_config.get("protection_policies")
        if protection_policies:
            protection_policy_list = (
                protection_policies.get("policies", [])
                if isinstance(protection_policies, dict)
                else protection_policies
            )
            protection_policy_count = (
                len(protection_policy_list)
                if isinstance(protection_policy_list, list)
                else 0
            )
            table_data.append(
                [
                    "Protection Policies",
                    f"{protection_policy_count} policies configured",
                ]
            )

        # Network Services (VIP Pools, DNS and NTP from network configuration)
        network_config = sections.get("network_configuration", {}).get("data", {})
        if network_config:
            # VIP Pools
            vippools = network_config.get("vippools")
            if vippools:
                vippool_list = (
                    vippools.get("pools", [])
                    if isinstance(vippools, dict)
                    else vippools
                )
                vippool_count = (
                    len(vippool_list) if isinstance(vippool_list, list) else 0
                )
                table_data.append(["VIP Pools", f"{vippool_count} pools configured"])
            # DNS Configuration
            dns = network_config.get("dns")
            if dns:
                dns_list = dns.get("dns_servers", []) if isinstance(dns, dict) else dns
                if dns_list:
                    dns_servers = (
                        ", ".join(dns_list)
                        if isinstance(dns_list, list)
                        else str(dns_list)
                    )
                    table_data.append(["DNS Servers", dns_servers])

            # NTP Configuration
            ntp = network_config.get("ntp")
            if ntp:
                ntp_list = ntp.get("ntp_servers", []) if isinstance(ntp, dict) else ntp
                if ntp_list:
                    ntp_servers = (
                        ", ".join(ntp_list)
                        if isinstance(ntp_list, list)
                        else str(ntp_list)
                    )
                    table_data.append(["NTP Servers", ntp_servers])

        # Data Protection information
        protection_config = sections.get("data_protection_configuration", {}).get(
            "data", {}
        )

        # Snapshot Programs
        snapshots = protection_config.get("snapshot_programs")
        if snapshots:
            snapshot_list = (
                snapshots.get("programs", [])
                if isinstance(snapshots, dict)
                else snapshots
            )
            snapshot_count = (
                len(snapshot_list) if isinstance(snapshot_list, list) else 0
            )
            table_data.append(
                ["Snapshot Programs", f"{snapshot_count} programs configured"]
            )

        # Data Protection Protection Policies (from data protection configuration)
        data_protection_policies = protection_config.get("protection_policies")
        if data_protection_policies:
            data_protection_policy_list = (
                data_protection_policies.get("policies", [])
                if isinstance(data_protection_policies, dict)
                else data_protection_policies
            )
            data_protection_policy_count = (
                len(data_protection_policy_list)
                if isinstance(data_protection_policy_list, list)
                else 0
            )
            table_data.append(
                [
                    "Data Protection Policies",
                    f"{data_protection_policy_count} policies configured",
                ]
            )

        # Create table if we have data
        if table_data:
            table_elements = self.brand_compliance.create_vast_table(
                table_data, None, ["Resource", "Value"]
            )
            content.extend(table_elements)
        else:
            # Fallback if no data
            content.append(
                Paragraph(
                    "No logical configuration data available.",
                    ParagraphStyle(
                        "Normal",
                        parent=styles["Normal"],
                        fontSize=self.config.font_size,
                    ),
                )
            )

        return content

    def _create_security_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create security configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        content = []

        content.append(Paragraph("Security & Authentication", heading_style))
        content.append(Spacer(1, 12))

        # Section Overview
        overview_style = ParagraphStyle(
            "Section_Overview",
            parent=styles["Normal"],
            fontSize=self.config.font_size - 1,
            textColor=self.brand_compliance.colors.BACKGROUND_DARK,
            spaceAfter=12,
            spaceBefore=8,
            leftIndent=12,
            rightIndent=12,
        )

        content.append(
            Paragraph(
                "The Security & Authentication section provides comprehensive documentation of all security-related configurations and authentication mechanisms implemented within the VAST Data cluster. This section covers authentication services including Active Directory, LDAP, and NIS integration, as well as security features such as data encryption settings, external key management (EKM) configuration, and security policy enforcement. Understanding the security configuration is essential for compliance auditing, security posture assessment, access control validation, and ensuring that the storage infrastructure meets organizational security requirements and industry best practices. This information supports security administrators in maintaining a robust security framework for the storage environment.",
                overview_style,
            )
        )
        content.append(Spacer(1, 8))

        sections = data.get("sections", {})
        security_config = sections.get("security_configuration", {}).get("data", {})

        # Prepare table data
        table_data = []

        # Active Directory
        ad_config = security_config.get("active_directory")
        if ad_config:
            table_data.append(
                [
                    "Authentication",
                    "Active Directory",
                    "Enabled",
                    str(ad_config.get("enabled", False)),
                ]
            )
            if ad_config.get("domain"):
                table_data.append(
                    [
                        "Authentication",
                        "Active Directory",
                        "Domain",
                        ad_config.get("domain"),
                    ]
                )
            servers = ad_config.get("servers", [])
            if servers:
                table_data.append(
                    [
                        "Authentication",
                        "Active Directory",
                        "Servers",
                        ", ".join(servers),
                    ]
                )

        # LDAP
        ldap_config = security_config.get("ldap")
        if ldap_config:
            table_data.append(
                [
                    "Authentication",
                    "LDAP",
                    "Enabled",
                    str(ldap_config.get("enabled", False)),
                ]
            )

        # NIS
        nis_config = security_config.get("nis")
        if nis_config:
            table_data.append(
                [
                    "Authentication",
                    "NIS",
                    "Enabled",
                    str(nis_config.get("enabled", False)),
                ]
            )

        # Encryption Configuration
        cluster_summary = data.get("cluster_summary", {})
        if cluster_summary:
            # Basic encryption settings
            enable_encryption = cluster_summary.get("enable_encryption")
            enable_encryption_display = (
                enable_encryption if enable_encryption is not None else "Not Configured"
            )
            table_data.append(
                ["Security", "Encryption", "Enabled", str(enable_encryption_display)]
            )

            encryption_type = cluster_summary.get("encryption_type")
            encryption_type_display = (
                encryption_type
                if encryption_type and encryption_type != "Unknown"
                else "Not Configured"
            )
            table_data.append(
                ["Security", "Encryption", "Type", encryption_type_display]
            )

            s3_aes_ciphers = cluster_summary.get("s3_enable_only_aes_ciphers")
            s3_aes_ciphers_display = (
                s3_aes_ciphers if s3_aes_ciphers is not None else "Not Configured"
            )
            table_data.append(
                [
                    "Security",
                    "Encryption",
                    "S3 AES Ciphers Only",
                    str(s3_aes_ciphers_display),
                ]
            )

            # External Key Management (EKM) settings
            ekm_servers = cluster_summary.get("ekm_servers")
            ekm_servers_display = (
                ekm_servers
                if ekm_servers and ekm_servers != "Unknown" and ekm_servers != ""
                else "Not Configured"
            )
            table_data.append(["Security", "EKM", "Servers", ekm_servers_display])

            ekm_address = cluster_summary.get("ekm_address")
            ekm_address_display = (
                ekm_address
                if ekm_address and ekm_address != "Unknown" and ekm_address != ""
                else "Not Configured"
            )
            table_data.append(["Security", "EKM", "Address", ekm_address_display])

            ekm_port = cluster_summary.get("ekm_port")
            ekm_port_display = ekm_port if ekm_port is not None else "Not Configured"
            table_data.append(["Security", "EKM", "Port", str(ekm_port_display)])

            ekm_auth_domain = cluster_summary.get("ekm_auth_domain")
            ekm_auth_domain_display = (
                ekm_auth_domain
                if ekm_auth_domain
                and ekm_auth_domain != "Unknown"
                and ekm_auth_domain != ""
                else "Not Configured"
            )
            table_data.append(
                ["Security", "EKM", "Auth Domain", ekm_auth_domain_display]
            )

            # Secondary EKM settings
            secondary_ekm_address = cluster_summary.get("secondary_ekm_address")
            secondary_ekm_address_display = (
                secondary_ekm_address
                if secondary_ekm_address and secondary_ekm_address != "null"
                else "Not Configured"
            )
            table_data.append(
                ["Security", "Secondary EKM", "Address", secondary_ekm_address_display]
            )

            secondary_ekm_port = cluster_summary.get("secondary_ekm_port")
            secondary_ekm_port_display = (
                secondary_ekm_port
                if secondary_ekm_port is not None
                else "Not Configured"
            )
            table_data.append(
                ["Security", "Secondary EKM", "Port", str(secondary_ekm_port_display)]
            )

        # Create table if we have data
        if table_data:
            table_elements = self.brand_compliance.create_vast_table(
                table_data,
                None,
                ["Type", "Description", "Function", "Value"],
            )
            content.extend(table_elements)
        else:
            # Fallback if no data
            content.append(
                Paragraph(
                    "No security configuration data available.",
                    ParagraphStyle(
                        "Normal",
                        parent=styles["Normal"],
                        fontSize=self.config.font_size,
                    ),
                )
            )

        return content

    def _create_data_protection_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create data protection configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("Data Protection", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get("sections", {})
        protection_config = sections.get("data_protection_configuration", {}).get(
            "data", {}
        )

        # Snapshot Programs
        snapshots = protection_config.get("snapshot_programs")
        if snapshots:
            content.append(Paragraph("<b>Snapshot Programs:</b>", normal_style))
            for snapshot in snapshots.get("programs", []):
                content.append(
                    Paragraph(
                        f"• {snapshot.get('name', 'Unknown')} - {snapshot.get('schedule', 'Unknown')} ({'Enabled' if snapshot.get('enabled') else 'Disabled'})",
                        normal_style,
                    )
                )
            content.append(Spacer(1, 8))

        # Protection Policies
        policies = protection_config.get("protection_policies")
        if policies:
            policy_list = (
                policies.get("policies", []) if isinstance(policies, dict) else policies
            )
            policy_count = len(policy_list) if isinstance(policy_list, list) else 0
            content.append(
                Paragraph(
                    f"<b>Protection Policies:</b> {policy_count} policies configured",
                    normal_style,
                )
            )

        return content

    def _create_enhanced_features_section(self, data: Dict[str, Any]) -> List[Any]:
        """Create enhanced features section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("Enhanced Features", heading_style))
        content.append(Spacer(1, 12))

        enhanced_features = data.get("metadata", {}).get("enhanced_features", {})

        # Rack Height Support
        rack_support = enhanced_features.get("rack_height_supported", False)
        content.append(Paragraph("<b>Rack Positioning:</b>", normal_style))
        content.append(
            Paragraph(f"• Supported: {'Yes' if rack_support else 'No'}", normal_style)
        )
        if rack_support:
            content.append(
                Paragraph(
                    "• Automated U-number generation for hardware positioning",
                    normal_style,
                )
            )
            content.append(
                Paragraph(
                    "• Physical rack layout visualization available", normal_style
                )
            )
        else:
            content.append(
                Paragraph("• Manual entry required for rack positions", normal_style)
            )
        content.append(Spacer(1, 8))

        # PSNT Support
        psnt_support = enhanced_features.get("psnt_supported", False)
        content.append(Paragraph("<b>PSNT Tracking:</b>", normal_style))
        content.append(
            Paragraph(f"• Supported: {'Yes' if psnt_support else 'No'}", normal_style)
        )
        if psnt_support:
            content.append(
                Paragraph(
                    "• Cluster Product Serial Number available for support tracking",
                    normal_style,
                )
            )
            cluster_info = data.get("cluster_summary", {})
            psnt = cluster_info.get("psnt")
            if psnt:
                content.append(Paragraph(f"• PSNT: {psnt}", normal_style))
        else:
            content.append(
                Paragraph("• PSNT not available for this cluster version", normal_style)
            )

        return content

    def _create_appendix(self, data: Dict[str, Any]) -> List[Any]:
        """Create appendix section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            "Section_Heading",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size,
            spaceAfter=12,
        )

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("Appendix", heading_style))
        content.append(Spacer(1, 12))

        # Generation metadata
        metadata = data.get("metadata", {})
        content.append(Paragraph("<b>Report Generation Information:</b>", normal_style))
        content.append(
            Paragraph(
                f"• Generated on: {metadata.get('extraction_timestamp', 'Unknown')}",
                normal_style,
            )
        )
        content.append(
            Paragraph(
                f"• Data completeness: {metadata.get('overall_completeness', 0.0):.1%}",
                normal_style,
            )
        )
        content.append(
            Paragraph(
                f"• API version: {metadata.get('api_version', 'Unknown')}", normal_style
            )
        )
        content.append(
            Paragraph(
                f"• Cluster version: {metadata.get('cluster_version', 'Unknown')}",
                normal_style,
            )
        )
        content.append(Spacer(1, 12))

        # Physical layout information
        hardware = data.get("hardware_inventory", {})
        physical_layout = hardware.get("physical_layout")
        if physical_layout:
            content.append(Paragraph("<b>Physical Rack Layout:</b>", normal_style))
            stats = physical_layout.get("statistics", {})
            content.append(
                Paragraph(
                    f"• Occupied positions: {stats.get('occupied_positions', 0)}",
                    normal_style,
                )
            )
            content.append(
                Paragraph(
                    f"• Position range: U{stats.get('min_position', 0)} - U{stats.get('max_position', 0)}",
                    normal_style,
                )
            )
            content.append(
                Paragraph(
                    f"• Total CNodes: {stats.get('total_cnodes', 0)}", normal_style
                )
            )
            content.append(
                Paragraph(
                    f"• Total DNodes: {stats.get('total_dnodes', 0)}", normal_style
                )
            )

        return content

    def _generate_html_content(self, data: Dict[str, Any]) -> str:
        """Generate HTML content for WeasyPrint."""
        # This is a simplified HTML generator
        # In a full implementation, this would generate comprehensive HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>VAST As-Built Report</title>
        </head>
        <body>
            <h1>VAST As-Built Report</h1>
            <p>This is a placeholder for HTML content generation.</p>
            <p>Cluster: {data.get('cluster_summary', {}).get('name', 'Unknown')}</p>
        </body>
        </html>
        """
        return html

    def _generate_css_content(self) -> str:
        """Generate CSS content for WeasyPrint."""
        # This is a simplified CSS generator
        css = """
        body {
            font-family: Arial, sans-serif;
            margin: 40px;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        """
        return css


# Convenience function for easy usage
def create_report_builder(config: Optional[ReportConfig] = None) -> VastReportBuilder:
    """
    Create and return a configured VastReportBuilder instance.

    Args:
        config (ReportConfig, optional): Report configuration

    Returns:
        VastReportBuilder: Configured report builder instance
    """
    return VastReportBuilder(config)


if __name__ == "__main__":
    """
    Test the report builder when run as a standalone module.
    """
    from utils.logger import setup_logging

    # Set up logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("VAST Report Builder Module Test")
    logger.info("This module generates professional PDF reports from processed data")
    logger.info("Enhanced features: rack positioning and PSNT integration")
    logger.info("Ready for integration with main CLI application")
