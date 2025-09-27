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

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from dataclasses import dataclass
import json

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logger import get_logger

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
    from reportlab.platypus import KeepTogether, Frame, PageTemplate, BaseDocTemplate
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    import weasyprint
    from weasyprint import HTML, CSS
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
            raise ReportGenerationError("Neither ReportLab nor WeasyPrint is available. Please install one of them.")

        self.logger.info("Report builder initialized")

    def generate_pdf_report(self, processed_data: Dict[str, Any], output_path: str) -> bool:
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

    def _generate_with_reportlab(self, processed_data: Dict[str, Any], output_path: str) -> bool:
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
                bottomMargin=self.config.margin_bottom * inch
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

    def _generate_with_weasyprint(self, processed_data: Dict[str, Any], output_path: str) -> bool:
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

            self.logger.info(f"PDF report generated successfully with WeasyPrint: {output_path}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating PDF with WeasyPrint: {e}")
            return False

    def _create_title_page(self, data: Dict[str, Any]) -> List[Any]:
        """Create title page content."""
        styles = getSampleStyleSheet()

        # Title style
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Title'],
            fontSize=self.config.title_font_size + 4,
            spaceAfter=30,
            alignment=TA_CENTER
        )

        # Subtitle style
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=self.config.heading_font_size + 2,
            spaceAfter=20,
            alignment=TA_CENTER
        )

        # Normal style
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=12,
            alignment=TA_CENTER
        )

        content = []

        # Main title
        content.append(Paragraph("VAST As-Built Report", title_style))
        content.append(Spacer(1, 20))

        # Cluster information
        cluster_info = data.get('cluster_summary', {})
        cluster_name = cluster_info.get('name', 'Unknown Cluster')
        cluster_version = cluster_info.get('version', 'Unknown Version')

        content.append(Paragraph(f"Cluster: {cluster_name}", subtitle_style))
        content.append(Paragraph(f"Version: {cluster_version}", subtitle_style))
        content.append(Spacer(1, 30))

        # Generation information
        if self.config.include_timestamp:
            timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
            content.append(Paragraph(f"Generated on: {timestamp}", normal_style))

        # PSNT information
        psnt = cluster_info.get('psnt')
        if psnt:
            content.append(Paragraph(f"PSNT: {psnt}", normal_style))

        # Enhanced features
        enhanced_features = data.get('metadata', {}).get('enhanced_features', {})
        if enhanced_features.get('rack_height_supported'):
            content.append(Paragraph("Enhanced Features: Rack Positioning Available", normal_style))

        content.append(Spacer(1, 50))

        # Footer
        content.append(Paragraph("VAST Professional Services", normal_style))
        content.append(Paragraph("Automated As-Built Documentation", normal_style))

        return content

    def _create_table_of_contents(self, data: Dict[str, Any]) -> List[Any]:
        """Create table of contents."""
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TOC_Title',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size + 2,
            spaceAfter=20,
            alignment=TA_CENTER
        )

        toc_style = ParagraphStyle(
            'TOC_Item',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8,
            leftIndent=20
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
            "9. Appendix"
        ]

        for item in toc_items:
            content.append(Paragraph(item, toc_style))

        return content

    def _create_executive_summary(self, data: Dict[str, Any]) -> List[Any]:
        """Create executive summary section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Executive Summary", heading_style))
        content.append(Spacer(1, 12))

        # Cluster overview
        cluster_info = data.get('cluster_summary', {})
        cluster_name = cluster_info.get('name', 'Unknown')
        cluster_version = cluster_info.get('version', 'Unknown')
        cluster_state = cluster_info.get('state', 'Unknown')

        content.append(Paragraph(f"<b>Cluster Overview:</b>", normal_style))
        content.append(Paragraph(f"• Name: {cluster_name}", normal_style))
        content.append(Paragraph(f"• Version: {cluster_version}", normal_style))
        content.append(Paragraph(f"• State: {cluster_state}", normal_style))
        content.append(Spacer(1, 12))

        # Hardware summary
        hardware = data.get('hardware_inventory', {})
        total_nodes = hardware.get('total_nodes', 0)
        cnodes = len(hardware.get('cnodes', []))
        dnodes = len(hardware.get('dnodes', []))
        rack_positions = hardware.get('rack_positions_available', False)

        content.append(Paragraph(f"<b>Hardware Summary:</b>", normal_style))
        content.append(Paragraph(f"• Total Nodes: {total_nodes}", normal_style))
        content.append(Paragraph(f"• CNodes: {cnodes}", normal_style))
        content.append(Paragraph(f"• DNodes: {dnodes}", normal_style))
        content.append(Paragraph(f"• Rack Positions: {'Available' if rack_positions else 'Not Available'}", normal_style))
        content.append(Spacer(1, 12))

        # Data completeness
        metadata = data.get('metadata', {})
        completeness = metadata.get('overall_completeness', 0.0)

        content.append(Paragraph(f"<b>Data Collection:</b>", normal_style))
        content.append(Paragraph(f"• Overall Completeness: {completeness:.1%}", normal_style))
        content.append(Paragraph(f"• Enhanced Features: {'Enabled' if metadata.get('enhanced_features', {}).get('rack_height_supported') else 'Disabled'}", normal_style))

        return content

    def _create_cluster_information(self, data: Dict[str, Any]) -> List[Any]:
        """Create cluster information section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Cluster Information", heading_style))
        content.append(Spacer(1, 12))

        cluster_info = data.get('cluster_summary', {})

        # Create cluster info table
        cluster_data = [
            ['Property', 'Value'],
            ['Name', cluster_info.get('name', 'Unknown')],
            ['GUID', cluster_info.get('guid', 'Unknown')],
            ['Version', cluster_info.get('version', 'Unknown')],
            ['State', cluster_info.get('state', 'Unknown')],
            ['License', cluster_info.get('license', 'Unknown')],
            ['PSNT', cluster_info.get('psnt', 'Not Available')]
        ]

        table = Table(cluster_data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), self.config.font_size),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        content.append(table)

        return content

    def _create_hardware_inventory(self, data: Dict[str, Any]) -> List[Any]:
        """Create hardware inventory section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Hardware Inventory", heading_style))
        content.append(Spacer(1, 12))

        hardware = data.get('hardware_inventory', {})

        # Hardware summary
        total_nodes = hardware.get('total_nodes', 0)
        rack_positions = hardware.get('rack_positions_available', False)

        content.append(Paragraph(f"<b>Summary:</b> {total_nodes} total nodes", normal_style))
        content.append(Paragraph(f"<b>Rack Positioning:</b> {'Available' if rack_positions else 'Not Available'}", normal_style))
        content.append(Spacer(1, 12))

        # CNodes table
        cnodes = hardware.get('cnodes', [])
        if cnodes:
            content.append(Paragraph("CNodes:", normal_style))
            cnode_data = [['ID', 'Model', 'Serial Number', 'Status', 'Rack Position', 'U Number']]

            for cnode in cnodes:
                rack_pos = cnode.get('rack_position', 'N/A')
                u_number = f"U{rack_pos}" if rack_pos != 'N/A' else 'Manual Entry'
                cnode_data.append([
                    cnode.get('id', 'Unknown'),
                    cnode.get('model', 'Unknown'),
                    cnode.get('serial_number', 'Unknown'),
                    cnode.get('status', 'Unknown'),
                    str(rack_pos),
                    u_number
                ])

            table = Table(cnode_data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), self.config.font_size - 1),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            content.append(table)
            content.append(Spacer(1, 12))

        # DNodes table
        dnodes = hardware.get('dnodes', [])
        if dnodes:
            content.append(Paragraph("DNodes:", normal_style))
            dnode_data = [['ID', 'Model', 'Serial Number', 'Status', 'Rack Position', 'U Number']]

            for dnode in dnodes:
                rack_pos = dnode.get('rack_position', 'N/A')
                u_number = f"U{rack_pos}" if rack_pos != 'N/A' else 'Manual Entry'
                dnode_data.append([
                    dnode.get('id', 'Unknown'),
                    dnode.get('model', 'Unknown'),
                    dnode.get('serial_number', 'Unknown'),
                    dnode.get('status', 'Unknown'),
                    str(rack_pos),
                    u_number
                ])

            table = Table(dnode_data, colWidths=[1*inch, 1.5*inch, 1.5*inch, 0.8*inch, 0.8*inch, 0.8*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), self.config.font_size - 1),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            content.append(table)

        return content

    def _create_network_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create network configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Network Configuration", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get('sections', {})
        network_config = sections.get('network_configuration', {}).get('data', {})

        # DNS Configuration
        dns_config = network_config.get('dns')
        if dns_config:
            content.append(Paragraph("<b>DNS Configuration:</b>", normal_style))
            content.append(Paragraph(f"• Enabled: {dns_config.get('enabled', False)}", normal_style))
            servers = dns_config.get('servers', [])
            if servers:
                content.append(Paragraph(f"• Servers: {', '.join(servers)}", normal_style))
            search_domains = dns_config.get('search_domains', [])
            if search_domains:
                content.append(Paragraph(f"• Search Domains: {', '.join(search_domains)}", normal_style))
            content.append(Spacer(1, 8))

        # NTP Configuration
        ntp_config = network_config.get('ntp')
        if ntp_config:
            content.append(Paragraph("<b>NTP Configuration:</b>", normal_style))
            content.append(Paragraph(f"• Enabled: {ntp_config.get('enabled', False)}", normal_style))
            servers = ntp_config.get('servers', [])
            if servers:
                content.append(Paragraph(f"• Servers: {', '.join(servers)}", normal_style))
            content.append(Spacer(1, 8))

        # VIP Pools
        vippool_config = network_config.get('vippools')
        if vippool_config:
            content.append(Paragraph("<b>VIP Pools:</b>", normal_style))
            pools = vippool_config.get('pools', [])
            for pool in pools:
                content.append(Paragraph(f"• {pool.get('name', 'Unknown')}: {pool.get('vips', [])}", normal_style))

        return content

    def _create_logical_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create logical configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Logical Configuration", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get('sections', {})
        logical_config = sections.get('logical_configuration', {}).get('data', {})

        # Tenants
        tenants = logical_config.get('tenants')
        if tenants:
            content.append(Paragraph("<b>Tenants:</b>", normal_style))
            for tenant in tenants.get('tenants', []):
                content.append(Paragraph(f"• {tenant.get('name', 'Unknown')} (ID: {tenant.get('id', 'Unknown')}) - {tenant.get('state', 'Unknown')}", normal_style))
            content.append(Spacer(1, 8))

        # Views
        views = logical_config.get('views')
        if views:
            content.append(Paragraph("<b>Views:</b>", normal_style))
            for view in views.get('views', []):
                content.append(Paragraph(f"• {view.get('name', 'Unknown')} ({view.get('path', 'Unknown')}) - {view.get('state', 'Unknown')}", normal_style))
            content.append(Spacer(1, 8))

        # View Policies
        policies = logical_config.get('view_policies')
        if policies:
            content.append(Paragraph("<b>View Policies:</b>", normal_style))
            for policy in policies.get('policies', []):
                content.append(Paragraph(f"• {policy.get('name', 'Unknown')} ({policy.get('type', 'Unknown')}) - {policy.get('state', 'Unknown')}", normal_style))

        return content

    def _create_security_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create security configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Security & Authentication", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get('sections', {})
        security_config = sections.get('security_configuration', {}).get('data', {})

        # Active Directory
        ad_config = security_config.get('active_directory')
        if ad_config:
            content.append(Paragraph("<b>Active Directory:</b>", normal_style))
            content.append(Paragraph(f"• Enabled: {ad_config.get('enabled', False)}", normal_style))
            if ad_config.get('domain'):
                content.append(Paragraph(f"• Domain: {ad_config.get('domain')}", normal_style))
            servers = ad_config.get('servers', [])
            if servers:
                content.append(Paragraph(f"• Servers: {', '.join(servers)}", normal_style))
            content.append(Spacer(1, 8))

        # LDAP
        ldap_config = security_config.get('ldap')
        if ldap_config:
            content.append(Paragraph("<b>LDAP:</b>", normal_style))
            content.append(Paragraph(f"• Enabled: {ldap_config.get('enabled', False)}", normal_style))
            content.append(Spacer(1, 8))

        # NIS
        nis_config = security_config.get('nis')
        if nis_config:
            content.append(Paragraph("<b>NIS:</b>", normal_style))
            content.append(Paragraph(f"• Enabled: {nis_config.get('enabled', False)}", normal_style))

        return content

    def _create_data_protection_configuration(self, data: Dict[str, Any]) -> List[Any]:
        """Create data protection configuration section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Data Protection", heading_style))
        content.append(Spacer(1, 12))

        sections = data.get('sections', {})
        protection_config = sections.get('data_protection_configuration', {}).get('data', {})

        # Snapshot Programs
        snapshots = protection_config.get('snapshot_programs')
        if snapshots:
            content.append(Paragraph("<b>Snapshot Programs:</b>", normal_style))
            for snapshot in snapshots.get('programs', []):
                content.append(Paragraph(f"• {snapshot.get('name', 'Unknown')} - {snapshot.get('schedule', 'Unknown')} ({'Enabled' if snapshot.get('enabled') else 'Disabled'})", normal_style))
            content.append(Spacer(1, 8))

        # Protection Policies
        policies = protection_config.get('protection_policies')
        if policies:
            content.append(Paragraph("<b>Protection Policies:</b>", normal_style))
            for policy in policies.get('policies', []):
                content.append(Paragraph(f"• {policy.get('name', 'Unknown')} ({policy.get('type', 'Unknown')}) - {policy.get('retention', 'Unknown')} ({'Enabled' if policy.get('enabled') else 'Disabled'})", normal_style))

        return content

    def _create_enhanced_features_section(self, data: Dict[str, Any]) -> List[Any]:
        """Create enhanced features section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Enhanced Features", heading_style))
        content.append(Spacer(1, 12))

        enhanced_features = data.get('metadata', {}).get('enhanced_features', {})

        # Rack Height Support
        rack_support = enhanced_features.get('rack_height_supported', False)
        content.append(Paragraph("<b>Rack Positioning:</b>", normal_style))
        content.append(Paragraph(f"• Supported: {'Yes' if rack_support else 'No'}", normal_style))
        if rack_support:
            content.append(Paragraph("• Automated U-number generation for hardware positioning", normal_style))
            content.append(Paragraph("• Physical rack layout visualization available", normal_style))
        else:
            content.append(Paragraph("• Manual entry required for rack positions", normal_style))
        content.append(Spacer(1, 8))

        # PSNT Support
        psnt_support = enhanced_features.get('psnt_supported', False)
        content.append(Paragraph("<b>PSNT Tracking:</b>", normal_style))
        content.append(Paragraph(f"• Supported: {'Yes' if psnt_support else 'No'}", normal_style))
        if psnt_support:
            content.append(Paragraph("• Cluster Product Serial Number available for support tracking", normal_style))
            cluster_info = data.get('cluster_summary', {})
            psnt = cluster_info.get('psnt')
            if psnt:
                content.append(Paragraph(f"• PSNT: {psnt}", normal_style))
        else:
            content.append(Paragraph("• PSNT not available for this cluster version", normal_style))

        return content

    def _create_appendix(self, data: Dict[str, Any]) -> List[Any]:
        """Create appendix section."""
        styles = getSampleStyleSheet()

        heading_style = ParagraphStyle(
            'Section_Heading',
            parent=styles['Heading1'],
            fontSize=self.config.heading_font_size,
            spaceAfter=12
        )

        normal_style = ParagraphStyle(
            'Section_Normal',
            parent=styles['Normal'],
            fontSize=self.config.font_size,
            spaceAfter=8
        )

        content = []

        content.append(Paragraph("Appendix", heading_style))
        content.append(Spacer(1, 12))

        # Generation metadata
        metadata = data.get('metadata', {})
        content.append(Paragraph("<b>Report Generation Information:</b>", normal_style))
        content.append(Paragraph(f"• Generated on: {metadata.get('extraction_timestamp', 'Unknown')}", normal_style))
        content.append(Paragraph(f"• Data completeness: {metadata.get('overall_completeness', 0.0):.1%}", normal_style))
        content.append(Paragraph(f"• API version: {metadata.get('api_version', 'Unknown')}", normal_style))
        content.append(Paragraph(f"• Cluster version: {metadata.get('cluster_version', 'Unknown')}", normal_style))
        content.append(Spacer(1, 12))

        # Physical layout information
        hardware = data.get('hardware_inventory', {})
        physical_layout = hardware.get('physical_layout')
        if physical_layout:
            content.append(Paragraph("<b>Physical Rack Layout:</b>", normal_style))
            stats = physical_layout.get('statistics', {})
            content.append(Paragraph(f"• Occupied positions: {stats.get('occupied_positions', 0)}", normal_style))
            content.append(Paragraph(f"• Position range: U{stats.get('min_position', 0)} - U{stats.get('max_position', 0)}", normal_style))
            content.append(Paragraph(f"• Total CNodes: {stats.get('total_cnodes', 0)}", normal_style))
            content.append(Paragraph(f"• Total DNodes: {stats.get('total_dnodes', 0)}", normal_style))

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
