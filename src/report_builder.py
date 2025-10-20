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

    def _create_table_of_contents(self, data: Dict[str, Any]) -> List[Any]:
        """Create table of contents."""
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "TOC_Title",
            parent=styles["Heading1"],
            fontSize=self.config.heading_font_size + 2,
            spaceAfter=20,
            alignment=TA_CENTER,
        )

        toc_style = ParagraphStyle(
            "TOC_Item",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
            leftIndent=20,
        )

        content = []

        content.append(Paragraph("Table of Contents", title_style))
        content.append(Spacer(1, 20))

        # TOC items
        toc_items = [
            "1. Executive Summary",
            "2. Cluster Information",
            "3. Hardware Inventory",
            "4. Network Configuration",
            "5. Logical Configuration",
            "6. Security & Authentication",
            "7. Data Protection",
            "8. Enhanced Features",
            "9. Appendix",
        ]

        for item in toc_items:
            content.append(Paragraph(item, toc_style))

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

        cluster_overview_data = [
            ["ID", cluster_id],
            ["Name", cluster_name],
            ["Management VIP", mgmt_vip],
            ["URL", url],
            ["Build", build],
            ["PSNT", psnt],
            ["GUID", guid],
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

    def _create_cbox_inventory_table(
        self, cboxes: Dict[str, Any], cnodes: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Create CBox Inventory table using data from both cboxes and cnodes APIs.

        Args:
            cboxes: CBox data from /api/v1/cboxes/
            cnodes: CNode data from /api/v7/cnodes/

        Returns:
            List[Any]: Table elements
        """
        if not cboxes or not cnodes:
            return []

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

        # Prepare table data
        table_data = []
        headers = ["ID", "Model", "Name/Serial Number", "Status", "Position"]

        for cbox_name, cbox_data in cboxes.items():
            cbox_id = cbox_data.get("id", "Unknown")
            name = cbox_data.get("name", "Unknown")
            rack_unit = cbox_data.get("rack_unit", "Unknown")

            # Get model and status from cnodes data using cbox_id
            model = cbox_vendor_map.get(cbox_id, "Unknown")
            status = cbox_status_map.get(cbox_id, "Unknown")

            # Create row data
            row = [str(cbox_id), model, name, status, rack_unit]
            table_data.append(row)

        # Sort by ID for consistent ordering
        table_data.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)

        # Create table with VAST styling
        return self.brand_compliance.create_vast_hardware_table_with_pagination(
            table_data, "CBox Inventory (Compute)", headers
        )

    def _create_dbox_inventory_table(self, dboxes: Dict[str, Any]) -> List[Any]:
        """
        Create DBox Inventory table using data from the dboxes API.

        Args:
            dboxes: DBox data from /api/v7/dboxes/

        Returns:
            List[Any]: Table elements
        """
        if not dboxes:
            return []

        # Prepare table data
        table_data = []
        headers = ["ID", "Model", "Name/SN", "Status", "Position"]

        for dbox_name, dbox_data in dboxes.items():
            dbox_id = dbox_data.get("id", "Unknown")
            hardware_type = dbox_data.get("hardware_type", "Unknown")
            name = dbox_data.get("name", "Unknown")
            state = dbox_data.get("state", "Unknown")
            rack_unit = dbox_data.get("rack_unit", "Unknown")

            # Create row data
            row = [str(dbox_id), hardware_type, name, state, rack_unit]
            table_data.append(row)

        # Sort by ID for consistent ordering
        table_data.sort(key=lambda x: int(x[0]) if x[0].isdigit() else 0)

        # Create table with VAST styling
        return self.brand_compliance.create_vast_hardware_table_with_pagination(
            table_data, "DBox Inventory (Data)", headers
        )

    def _create_switch_inventory_table(
        self, switches: List[Dict[str, Any]]
    ) -> List[Any]:
        """
        Create Switch Inventory table using data from the switch inventory API.

        Args:
            switches: Switch data from switch inventory

        Returns:
            List[Any]: Table elements
        """
        if not switches:
            return []

        # Prepare table data
        table_data = []
        headers = ["Switch", "Model", "Serial Number", "Status"]

        for switch in switches:
            switch_name = switch.get("name", "Unknown")
            model = switch.get("model", "Unknown")
            serial = switch.get("serial", "Unknown")

            # Status based on active ports vs total ports
            active_ports = switch.get("active_ports", 0)
            total_ports = switch.get("total_ports", 0)

            if active_ports == total_ports and total_ports > 0:
                status = "HEALTHY"
            elif active_ports > 0:
                status = "PARTIAL"
            else:
                status = "DOWN"

            # Create row data
            row = [switch_name, model, serial, status]
            table_data.append(row)

        # Sort by switch name for consistent ordering
        table_data.sort(key=lambda x: x[0])

        # Create table with VAST styling
        return self.brand_compliance.create_vast_hardware_table_with_pagination(
            table_data, "Switch Inventory", headers
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

            # Usable capacity section
            if cluster_info.get("usable_capacity_tb") is not None:
                storage_data.append(
                    [
                        "Usable Capacity",
                        f"{round(cluster_info.get('usable_capacity_tb', 0))} TB",
                    ]
                )
            if cluster_info.get("free_usable_capacity_tb") is not None:
                storage_data.append(
                    [
                        "Free Usable Capacity",
                        f"{round(cluster_info.get('free_usable_capacity_tb', 0))} TB",
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
                        f"{round(cluster_info.get('physical_space_tb', 0))} TB",
                    ]
                )
            if cluster_info.get("physical_space_in_use_tb") is not None:
                storage_data.append(
                    [
                        "Physical Space In Use",
                        f"{round(cluster_info.get('physical_space_in_use_tb', 0))} TB",
                    ]
                )
            if cluster_info.get("free_physical_space_tb") is not None:
                storage_data.append(
                    [
                        "Free Physical Space",
                        f"{round(cluster_info.get('free_physical_space_tb', 0))} TB",
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
                        f"{round(cluster_info.get('logical_space_tb', 0))} TB",
                    ]
                )
            if cluster_info.get("logical_space_in_use_tb") is not None:
                storage_data.append(
                    [
                        "Logical Space In Use",
                        f"{round(cluster_info.get('logical_space_in_use_tb', 0))} TB",
                    ]
                )
            if cluster_info.get("free_logical_space_tb") is not None:
                storage_data.append(
                    [
                        "Free Logical Space",
                        f"{round(cluster_info.get('free_logical_space_tb', 0))} TB",
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

        # CBox Inventory (Compute) table with VAST styling
        cboxes = hardware.get("cboxes", {})
        cnodes = hardware.get("cnodes", [])
        if cboxes and cnodes:
            cbox_elements = self._create_cbox_inventory_table(cboxes, cnodes)
            content.extend(cbox_elements)

            # Add page break if we have many CBoxes to prevent layout issues
            if len(cboxes) > 10:  # Threshold for large inventories
                content.append(PageBreak())

        # DBox Inventory (Data) table with VAST styling
        dboxes = hardware.get("dboxes", {})
        if dboxes:
            dbox_elements = self._create_dbox_inventory_table(dboxes)
            content.extend(dbox_elements)

            # Add page break if we have many DBoxes to prevent layout issues
            if len(dboxes) > 10:  # Threshold for large inventories
                content.append(PageBreak())

        # Switch Inventory table with VAST styling
        switches = hardware.get("switches", [])
        if switches:
            switch_elements = self._create_switch_inventory_table(switches)
            content.extend(switch_elements)

            # Add page break if we have many switches to prevent layout issues
            if len(switches) > 10:  # Threshold for large inventories
                content.append(PageBreak())

        # Add Physical Rack Layout - force to start at top of Page 6
        rack_positions = hardware.get("rack_positions_available", False)
        if rack_positions:
            # Force page break to move heading to top of Page 6
            content.append(PageBreak())

            # Add section heading at top of new page
            heading_elements = self.brand_compliance.create_vast_section_heading(
                "Physical Rack Layout", level=2
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

                # Get DBox information
                hw_dnodes = hardware.get("dnodes", [])

                for dnode in hw_dnodes:
                    # Prefer hardware_type over model for rack diagram
                    model = dnode.get("hardware_type")
                    if not model or model == "Unknown":
                        model = dnode.get("model", "")

                    dbox_data = {
                        "id": dnode.get("id"),
                        "model": model,
                        "rack_unit": dnode.get(
                            "rack_u", dnode.get("rack_unit", dnode.get("position", ""))
                        ),
                        "state": dnode.get("state", dnode.get("status", "ACTIVE")),
                    }
                    if dbox_data["rack_unit"]:  # Only add if has position
                        dboxes_data.append(dbox_data)

                # Create rack diagram
                if cboxes_data or dboxes_data:
                    rack_gen = RackDiagram()
                    rack_drawing = rack_gen.generate_rack_diagram(
                        cboxes_data, dboxes_data
                    )

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

                    self.logger.info(
                        f"Added rack diagram with {len(cboxes_data)} CBoxes and {len(dboxes_data)} DBoxes"
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

        # Check if network diagram image exists (try PNG first, then JPG)
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
                # Add diagram title
                title_style = ParagraphStyle(
                    "Diagram_Title",
                    parent=styles["Normal"],
                    fontSize=self.config.font_size + 2,
                    textColor=self.brand_compliance.colors.BACKGROUND_DARK,
                    alignment=TA_CENTER,
                    fontName="Helvetica-Bold",
                    spaceAfter=12,
                )
                content.append(Paragraph("Placeholder", title_style))
                content.append(Spacer(1, 8))

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
                f"Network diagram not found at {diagram_path}, " "using placeholder"
            )

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

            # Create port summary table
            if ports:
                # Aggregate ports by state, speed, and MTU
                port_summary = {}

                for port in ports:
                    state = port.get("state", "Unknown").lower()
                    speed = port.get("speed") or "Unconfigured"
                    port_mtu = port.get("mtu", "Unknown")

                    # Create key for grouping
                    if state == "up":
                        key = (state, speed, port_mtu)
                    else:
                        # For down ports, group all together regardless of speed/MTU
                        key = (state, "N/A", "N/A")

                    if key not in port_summary:
                        port_summary[key] = 0
                    port_summary[key] += 1

                # Create summary table
                summary_table_data = []
                headers = ["Port Qty", "State", "Speed", "MTU"]

                # Sort by state (up first), then by speed
                sorted_summary = sorted(
                    port_summary.items(),
                    key=lambda x: (
                        0 if x[0][0] == "up" else 1,  # up ports first
                        (
                            0 if x[0][1] == "200G" else 1 if x[0][1] == "100G" else 2
                        ),  # speed order
                    ),
                )

                for (state, speed, port_mtu), count in sorted_summary:
                    summary_table_data.append(
                        [str(count), state.upper(), speed, port_mtu]
                    )

                # Create port summary table with VAST styling
                port_summary_elements = (
                    self.brand_compliance.create_vast_hardware_table_with_pagination(
                        summary_table_data, f"{switch_name} Port Summary", headers
                    )
                )
                content.extend(port_summary_elements)
                content.append(Spacer(1, 12))

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
