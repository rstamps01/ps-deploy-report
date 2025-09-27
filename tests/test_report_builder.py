"""
Unit tests for VAST As-Built Report Generator Report Builder Module.

This module contains comprehensive unit tests for the report builder,
including PDF generation, report formatting, and error handling.

Author: Manus AI
Date: September 26, 2025
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from report_builder import (
    VastReportBuilder,
    ReportConfig,
    ReportGenerationError,
    create_report_builder
)


class TestReportConfig(unittest.TestCase):
    """Test cases for ReportConfig dataclass."""

    def test_report_config_creation(self):
        """Test ReportConfig creation with default values."""
        config = ReportConfig()

        self.assertEqual(config.page_size, "A4")
        self.assertEqual(config.margin_top, 1.0)
        self.assertEqual(config.margin_bottom, 1.0)
        self.assertEqual(config.margin_left, 1.0)
        self.assertEqual(config.margin_right, 1.0)
        self.assertEqual(config.font_name, "Helvetica")
        self.assertEqual(config.font_size, 10)
        self.assertEqual(config.title_font_size, 16)
        self.assertEqual(config.heading_font_size, 12)
        self.assertEqual(config.line_spacing, 1.2)
        self.assertTrue(config.include_toc)
        self.assertTrue(config.include_timestamp)
        self.assertTrue(config.include_enhanced_features)

    def test_report_config_custom_values(self):
        """Test ReportConfig creation with custom values."""
        config = ReportConfig(
            page_size="Letter",
            margin_top=0.5,
            font_size=12,
            include_toc=False
        )

        self.assertEqual(config.page_size, "Letter")
        self.assertEqual(config.margin_top, 0.5)
        self.assertEqual(config.font_size, 12)
        self.assertFalse(config.include_toc)


class TestVastReportBuilder(unittest.TestCase):
    """Test cases for VastReportBuilder class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = ReportConfig()

        # Sample processed data for testing
        self.sample_data = {
            'metadata': {
                'extraction_timestamp': '2025-09-26T23:00:00',
                'overall_completeness': 0.95,
                'enhanced_features': {
                    'rack_height_supported': True,
                    'psnt_supported': True
                },
                'api_version': 'v7',
                'cluster_version': '5.3.0'
            },
            'cluster_summary': {
                'name': 'Test Cluster',
                'guid': 'test-guid-123',
                'version': '5.3.0',
                'state': 'active',
                'license': 'Enterprise',
                'psnt': 'PSNT123456789'
            },
            'hardware_inventory': {
                'total_nodes': 4,
                'cnodes': [
                    {
                        'id': 'cnode-1',
                        'model': 'CBox-100',
                        'serial_number': 'SN123456',
                        'status': 'active',
                        'rack_position': 5
                    },
                    {
                        'id': 'cnode-2',
                        'model': 'CBox-100',
                        'serial_number': 'SN123457',
                        'status': 'active',
                        'rack_position': 6
                    }
                ],
                'dnodes': [
                    {
                        'id': 'dnode-1',
                        'model': 'DBox-100',
                        'serial_number': 'SN789012',
                        'status': 'active',
                        'rack_position': 10
                    },
                    {
                        'id': 'dnode-2',
                        'model': 'DBox-100',
                        'serial_number': 'SN789013',
                        'status': 'active',
                        'rack_position': 11
                    }
                ],
                'rack_positions_available': True,
                'physical_layout': {
                    'statistics': {
                        'occupied_positions': 4,
                        'min_position': 5,
                        'max_position': 11,
                        'total_cnodes': 2,
                        'total_dnodes': 2
                    }
                }
            },
            'sections': {
                'network_configuration': {
                    'data': {
                        'dns': {
                            'enabled': True,
                            'servers': ['8.8.8.8', '8.8.4.4'],
                            'search_domains': ['example.com']
                        },
                        'ntp': {
                            'enabled': True,
                            'servers': ['pool.ntp.org']
                        },
                        'vippools': {
                            'pools': [{'name': 'default', 'vips': ['192.168.1.10']}]
                        }
                    }
                },
                'logical_configuration': {
                    'data': {
                        'tenants': {
                            'tenants': [{'name': 'tenant1', 'id': 't1', 'state': 'active'}]
                        },
                        'views': {
                            'views': [{'name': 'view1', 'path': '/view1', 'state': 'active'}]
                        },
                        'view_policies': {
                            'policies': [{'name': 'policy1', 'type': 'read-only', 'state': 'active'}]
                        }
                    }
                },
                'security_configuration': {
                    'data': {
                        'active_directory': {
                            'enabled': True,
                            'domain': 'example.com',
                            'servers': ['dc1.example.com']
                        },
                        'ldap': {'enabled': False},
                        'nis': {'enabled': False}
                    }
                },
                'data_protection_configuration': {
                    'data': {
                        'snapshot_programs': {
                            'programs': [{'name': 'daily', 'schedule': '0 2 * * *', 'enabled': True}]
                        },
                        'protection_policies': {
                            'policies': [{'name': 'backup', 'type': 'replication', 'retention': '30d', 'enabled': True}]
                        }
                    }
                }
            }
        }

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test report builder initialization."""
        builder = VastReportBuilder()

        self.assertIsInstance(builder.config, ReportConfig)
        self.assertEqual(builder.config.page_size, "A4")

    def test_initialization_with_config(self):
        """Test report builder initialization with custom config."""
        custom_config = ReportConfig(page_size="Letter", font_size=12)
        builder = VastReportBuilder(custom_config)

        self.assertEqual(builder.config.page_size, "Letter")
        self.assertEqual(builder.config.font_size, 12)

    @patch('report_builder.REPORTLAB_AVAILABLE', False)
    @patch('report_builder.WEASYPRINT_AVAILABLE', False)
    def test_initialization_no_libraries(self):
        """Test initialization when no PDF libraries are available."""
        with self.assertRaises(ReportGenerationError):
            VastReportBuilder()

    @patch('report_builder.REPORTLAB_AVAILABLE', True)
    def test_generate_pdf_report_reportlab(self):
        """Test PDF generation with ReportLab."""
        builder = VastReportBuilder()
        output_path = str(Path(self.temp_dir) / 'test_report.pdf')

        result = builder.generate_pdf_report(self.sample_data, output_path)

        self.assertTrue(result)
        self.assertTrue(Path(output_path).exists())

    @unittest.skip("WeasyPrint requires system dependencies that may not be available")
    @patch('report_builder.REPORTLAB_AVAILABLE', False)
    @patch('report_builder.WEASYPRINT_AVAILABLE', True)
    def test_generate_pdf_report_weasyprint(self):
        """Test PDF generation with WeasyPrint."""
        # Mock WeasyPrint classes
        with patch('weasyprint.HTML') as mock_html, \
             patch('weasyprint.CSS') as mock_css:

            mock_html_doc = MagicMock()
            mock_css_doc = MagicMock()
            mock_html.return_value = mock_html_doc
            mock_css.return_value = mock_css_doc

            builder = VastReportBuilder()
            output_path = str(Path(self.temp_dir) / 'test_report.pdf')

            result = builder.generate_pdf_report(self.sample_data, output_path)

            self.assertTrue(result)
            self.assertTrue(Path(output_path).exists())

    def test_generate_pdf_report_invalid_data(self):
        """Test PDF generation with invalid data."""
        builder = VastReportBuilder()
        output_path = str(Path(self.temp_dir) / 'test_report.pdf')

        result = builder.generate_pdf_report({}, output_path)

        # Should still succeed but with minimal content
        self.assertTrue(result)

    def test_generate_pdf_report_invalid_path(self):
        """Test PDF generation with invalid output path."""
        builder = VastReportBuilder()
        invalid_path = '/invalid/path/that/does/not/exist/test.pdf'

        result = builder.generate_pdf_report(self.sample_data, invalid_path)

        self.assertFalse(result)

    def test_create_title_page(self):
        """Test title page creation."""
        builder = VastReportBuilder()

        content = builder._create_title_page(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_table_of_contents(self):
        """Test table of contents creation."""
        builder = VastReportBuilder()

        content = builder._create_table_of_contents(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_executive_summary(self):
        """Test executive summary creation."""
        builder = VastReportBuilder()

        content = builder._create_executive_summary(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_cluster_information(self):
        """Test cluster information section creation."""
        builder = VastReportBuilder()

        content = builder._create_cluster_information(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_hardware_inventory(self):
        """Test hardware inventory section creation."""
        builder = VastReportBuilder()

        content = builder._create_hardware_inventory(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_network_configuration(self):
        """Test network configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_network_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_logical_configuration(self):
        """Test logical configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_logical_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_security_configuration(self):
        """Test security configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_security_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_data_protection_configuration(self):
        """Test data protection configuration section creation."""
        builder = VastReportBuilder()

        content = builder._create_data_protection_configuration(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_enhanced_features_section(self):
        """Test enhanced features section creation."""
        builder = VastReportBuilder()

        content = builder._create_enhanced_features_section(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_create_appendix(self):
        """Test appendix section creation."""
        builder = VastReportBuilder()

        content = builder._create_appendix(self.sample_data)

        self.assertIsInstance(content, list)
        self.assertGreater(len(content), 0)

    def test_generate_html_content(self):
        """Test HTML content generation."""
        builder = VastReportBuilder()

        html_content = builder._generate_html_content(self.sample_data)

        self.assertIsInstance(html_content, str)
        self.assertIn('VAST As-Built Report', html_content)
        self.assertIn('Test Cluster', html_content)

    def test_generate_css_content(self):
        """Test CSS content generation."""
        builder = VastReportBuilder()

        css_content = builder._generate_css_content()

        self.assertIsInstance(css_content, str)
        self.assertIn('body', css_content)
        self.assertIn('h1', css_content)

    def test_create_report_builder(self):
        """Test convenience function for creating report builder."""
        builder = create_report_builder()

        self.assertIsInstance(builder, VastReportBuilder)

    def test_create_report_builder_with_config(self):
        """Test convenience function with custom config."""
        custom_config = ReportConfig(font_size=14)
        builder = create_report_builder(custom_config)

        self.assertEqual(builder.config.font_size, 14)


class TestReportGenerationError(unittest.TestCase):
    """Test cases for ReportGenerationError exception."""

    def test_report_generation_error_creation(self):
        """Test ReportGenerationError creation."""
        error = ReportGenerationError("Test error message")

        self.assertEqual(str(error), "Test error message")
        self.assertIsInstance(error, Exception)


if __name__ == '__main__':
    unittest.main()
