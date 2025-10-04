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
            # Set up document
            page_size = A4 if self.config.page_size == "A4" else letter
            doc = SimpleDocTemplate(
                output_path,
                pagesize=page_size,
                rightMargin=self.config.margin_right * inch,
                leftMargin=self.config.margin_left * inch,
                topMargin=self.config.margin_top * inch,
                bottomMargin=self.config.margin_bottom * inch,
            )

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

            # Add hardware inventory
            story.extend(self._create_hardware_inventory(processed_data))
            story.append(PageBreak())

            # Add network configuration
            story.extend(self._create_network_configuration(processed_data))
            story.append(PageBreak())

            # Add logical configuration
            story.extend(self._create_logical_configuration(processed_data))
            story.append(PageBreak())

            # Add security configuration
            story.extend(self._create_security_configuration(processed_data))
            story.append(PageBreak())

            # Add data protection configuration
            story.extend(self._create_data_protection_configuration(processed_data))
            story.append(PageBreak())

            # Add enhanced features section
            if self.config.include_enhanced_features:
                story.extend(self._create_enhanced_features_section(processed_data))
                story.append(PageBreak())

            # Add appendix
            story.extend(self._create_appendix(processed_data))

            # Build PDF
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

        # Create VAST brand-compliant header
        title = "VAST As-Built Report"
        subtitle = "Customer Deployment Documentation"

        header_elements = self.brand_compliance.create_vast_header(
            title=title, subtitle=subtitle, cluster_info=cluster_info
        )
        content.extend(header_elements)

        # Add generation information with VAST styling
        if self.config.include_timestamp:
            timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
            timestamp_para = Paragraph(
                f"<b>Generated on:</b> {timestamp}",
                self.brand_compliance.styles["vast_body"],
            )
            content.append(timestamp_para)
            content.append(Spacer(1, 10))

        # Add VAST Professional Services footer
        footer_elements = self.brand_compliance.create_vast_footer(
            {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "completeness": data.get("metadata", {}).get(
                    "overall_completeness", 0.0
                ),
            }
        )
        content.extend(footer_elements)

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

        # Cluster overview with VAST styling - resequenced to match screenshot order
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

        overview_text = f"<b>Cluster Overview:</b><br/>"
        overview_text += f"• ID: {cluster_id}<br/>"
        overview_text += f"• Name: {cluster_name}<br/>"
        overview_text += f"• Management VIP: {mgmt_vip}<br/>"
        overview_text += f"• URL: {url}<br/>"
        overview_text += f"• Build: {build}<br/>"
        overview_text += f"• PSNT: {psnt}<br/>"
        overview_text += f"• GUID: {guid}<br/>"
        overview_text += f"• Uptime: {uptime}<br/>"
        overview_text += f"• Online Since: {online_start_time}<br/>"
        overview_text += f"• Deployed: {deployment_time}"

        overview_para = Paragraph(
            overview_text, self.brand_compliance.styles["vast_body"]
        )
        content.append(overview_para)
        content.append(Spacer(1, 12))

        # Hardware summary with VAST styling
        hardware = data.get("hardware_inventory", {})
        total_nodes = hardware.get("total_nodes", 0)
        cnodes = len(hardware.get("cnodes", []))
        dnodes = len(hardware.get("dnodes", []))
        rack_positions = hardware.get("rack_positions_available", False)

        hardware_text = f"<b>Hardware Summary:</b><br/>"
        hardware_text += f"• Total Nodes: {total_nodes}<br/>"
        hardware_text += f"• CNodes: {cnodes}<br/>"
        hardware_text += f"• DNodes: {dnodes}<br/>"
        hardware_text += (
            f"• Rack Positions: {'Available' if rack_positions else 'Not Available'}"
        )

        hardware_para = Paragraph(
            hardware_text, self.brand_compliance.styles["vast_body"]
        )
        content.append(hardware_para)
        content.append(Spacer(1, 12))

        return content

    def _create_cluster_information(self, data: Dict[str, Any]) -> List[Any]:
        """Create VAST brand-compliant cluster information section."""
        content = []

        # Add section heading with VAST styling
        heading_elements = self.brand_compliance.create_vast_section_heading(
            "Cluster Information", level=1
        )
        content.extend(heading_elements)

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
            "Hardware Inventory", level=1
        )
        content.extend(heading_elements)

        hardware = data.get("hardware_inventory", {})

        # Hardware summary with VAST styling
        total_nodes = hardware.get("total_nodes", 0)
        rack_positions = hardware.get("rack_positions_available", False)

        summary_text = f"<b>Summary:</b> {total_nodes} total nodes<br/>"
        summary_text += f"<b>Rack Positioning:</b> {'Available' if rack_positions else 'Not Available'}"

        summary_para = Paragraph(
            summary_text, self.brand_compliance.styles["vast_body"]
        )
        content.append(summary_para)
        content.append(Spacer(1, 12))

        # CNodes table with VAST styling
        cnodes = hardware.get("cnodes", [])
        if cnodes:
            cnode_elements = self.brand_compliance.create_vast_hardware_table(
                cnodes, "CNodes"
            )
            content.extend(cnode_elements)

        # DNodes table with VAST styling
        dnodes = hardware.get("dnodes", [])
        if dnodes:
            dnode_elements = self.brand_compliance.create_vast_hardware_table(
                dnodes, "DNodes"
            )
            content.extend(dnode_elements)

        # Add physical layout diagram placeholder
        if rack_positions:
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

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("Logical Configuration", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get("sections", {})
        logical_config = sections.get("logical_configuration", {}).get("data", {})

        # Tenants
        tenants = logical_config.get("tenants")
        if tenants:
            tenant_list = (
                tenants.get("tenants", []) if isinstance(tenants, dict) else tenants
            )
            tenant_count = len(tenant_list) if isinstance(tenant_list, list) else 0
            content.append(
                Paragraph(
                    f"<b>Tenants:</b> {tenant_count} tenants configured", normal_style
                )
            )
            content.append(Spacer(1, 8))

        # Views
        views = logical_config.get("views")
        if views:
            view_list = views.get("views", []) if isinstance(views, dict) else views
            view_count = len(view_list) if isinstance(view_list, list) else 0
            content.append(
                Paragraph(f"<b>Views:</b> {view_count} views configured", normal_style)
            )
            content.append(Spacer(1, 8))

        # View Policies
        policies = logical_config.get("view_policies")
        if policies:
            policy_list = (
                policies.get("policies", []) if isinstance(policies, dict) else policies
            )
            policy_count = len(policy_list) if isinstance(policy_list, list) else 0
            content.append(
                Paragraph(
                    f"<b>View Policies:</b> {policy_count} policies configured",
                    normal_style,
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

        normal_style = ParagraphStyle(
            "Section_Normal",
            parent=styles["Normal"],
            fontSize=self.config.font_size,
            spaceAfter=8,
        )

        content = []

        content.append(Paragraph("Security & Authentication", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get("sections", {})
        security_config = sections.get("security_configuration", {}).get("data", {})

        # Active Directory
        ad_config = security_config.get("active_directory")
        if ad_config:
            content.append(Paragraph("<b>Active Directory:</b>", normal_style))
            content.append(
                Paragraph(f"• Enabled: {ad_config.get('enabled', False)}", normal_style)
            )
            if ad_config.get("domain"):
                content.append(
                    Paragraph(f"• Domain: {ad_config.get('domain')}", normal_style)
                )
            servers = ad_config.get("servers", [])
            if servers:
                content.append(
                    Paragraph(f"• Servers: {', '.join(servers)}", normal_style)
                )
            content.append(Spacer(1, 8))

        # LDAP
        ldap_config = security_config.get("ldap")
        if ldap_config:
            content.append(Paragraph("<b>LDAP:</b>", normal_style))
            content.append(
                Paragraph(
                    f"• Enabled: {ldap_config.get('enabled', False)}", normal_style
                )
            )
            content.append(Spacer(1, 8))

        # NIS
        nis_config = security_config.get("nis")
        if nis_config:
            content.append(Paragraph("<b>NIS:</b>", normal_style))
            content.append(
                Paragraph(
                    f"• Enabled: {nis_config.get('enabled', False)}", normal_style
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
