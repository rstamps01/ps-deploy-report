"""
Unit tests for VAST As-Built Report Generator Data Extractor Module.

This module contains comprehensive unit tests for the data extractor,
including data processing, validation, enhanced features, and error handling.

Author: Manus AI
Date: September 26, 2025
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime
import sys

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from data_extractor import (
    VastDataExtractor,
    ClusterSummary,
    HardwareInventory,
    ReportSection,
    DataExtractionError,
    create_data_extractor
)


class TestVastDataExtractor(unittest.TestCase):
    """Test cases for VastDataExtractor class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            'data_collection': {
                'validate_responses': True,
                'graceful_degradation': True,
                'sections': {
                    'executive_summary': True,
                    'hardware_inventory': True,
                    'network_configuration': True,
                    'logical_configuration': True,
                    'security_authentication': True,
                    'data_protection': True
                }
            }
        }

        self.extractor = VastDataExtractor(config=self.test_config)

        # Sample raw data for testing
        self.sample_raw_data = {
            'collection_timestamp': 1695672000.0,
            'cluster_ip': '192.168.1.100',
            'api_version': 'v7',
            'cluster_version': '5.3.0',
            'enhanced_features': {
                'rack_height_supported': True,
                'psnt_supported': True
            },
            'cluster_info': {
                'name': 'Test Cluster',
                'guid': 'test-guid-123',
                'version': '5.3.0',
                'state': 'active',
                'license': 'Enterprise',
                'psnt': 'PSNT123456789'
            },
            'hardware': {
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
                    }
                ]
            },
            'network': {
                'dns': {
                    'servers': ['8.8.8.8', '8.8.4.4'],
                    'search_domains': ['example.com'],
                    'enabled': True
                },
                'ntp': {
                    'servers': ['pool.ntp.org'],
                    'enabled': True
                },
                'vippools': {
                    'pools': [{'name': 'default', 'vips': ['192.168.1.10']}]
                }
            },
            'logical': {
                'tenants': [{'name': 'tenant1', 'id': 't1', 'state': 'active'}],
                'views': [{'name': 'view1', 'path': '/view1', 'state': 'active'}],
                'viewpolicies': [{'name': 'policy1', 'type': 'read-only', 'state': 'active'}]
            },
            'security': {
                'activedirectory': {'enabled': True, 'domain': 'example.com', 'servers': ['dc1.example.com']},
                'ldap': {'enabled': False},
                'nis': {'enabled': False}
            },
            'data_protection': {
                'snapprograms': [{'name': 'daily', 'schedule': '0 2 * * *', 'enabled': True}],
                'protectionpolicies': [{'name': 'backup', 'type': 'replication', 'retention': '30d', 'enabled': True}]
            }
        }

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_initialization(self):
        """Test data extractor initialization."""
        self.assertEqual(self.extractor.validate_responses, True)
        self.assertEqual(self.extractor.graceful_degradation, True)
        self.assertIn('executive_summary', self.extractor.sections_config)

    def test_extract_cluster_summary(self):
        """Test cluster summary extraction."""
        summary = self.extractor.extract_cluster_summary(self.sample_raw_data)

        self.assertIsInstance(summary, ClusterSummary)
        self.assertEqual(summary.name, 'Test Cluster')
        self.assertEqual(summary.guid, 'test-guid-123')
        self.assertEqual(summary.version, '5.3.0')
        self.assertEqual(summary.psnt, 'PSNT123456789')
        self.assertTrue(summary.enhanced_features['rack_height_supported'])
        self.assertTrue(summary.enhanced_features['psnt_supported'])

    def test_extract_cluster_summary_missing_data(self):
        """Test cluster summary extraction with missing data."""
        incomplete_data = {
            'cluster_info': {
                'name': 'Test Cluster',
                'guid': 'test-guid-123'
                # Missing version, state, license
            }
        }

        summary = self.extractor.extract_cluster_summary(incomplete_data)

        self.assertEqual(summary.name, 'Test Cluster')
        self.assertEqual(summary.version, 'Unknown')
        self.assertEqual(summary.state, 'Unknown')
        self.assertEqual(summary.license, 'Unknown')

    def test_extract_hardware_inventory(self):
        """Test hardware inventory extraction with enhanced features."""
        inventory = self.extractor.extract_hardware_inventory(self.sample_raw_data)

        self.assertIsInstance(inventory, HardwareInventory)
        self.assertEqual(len(inventory.cnodes), 2)
        self.assertEqual(len(inventory.dnodes), 1)
        self.assertEqual(inventory.total_nodes, 3)
        self.assertTrue(inventory.rack_positions_available)
        self.assertIsNotNone(inventory.physical_layout)

        # Check CNode processing
        cnode = inventory.cnodes[0]
        self.assertEqual(cnode['id'], 'cnode-1')
        self.assertEqual(cnode['rack_position'], 5)
        self.assertEqual(cnode['rack_u'], 'U5')
        self.assertTrue(cnode['rack_position_available'])
        self.assertEqual(cnode['positioning_note'], 'Automated via API')

    def test_extract_hardware_inventory_no_rack_positions(self):
        """Test hardware inventory extraction without rack positions."""
        data_without_rack = self.sample_raw_data.copy()
        data_without_rack['enhanced_features']['rack_height_supported'] = False

        # Remove rack positions from hardware data
        for cnode in data_without_rack['hardware']['cnodes']:
            del cnode['rack_position']
        for dnode in data_without_rack['hardware']['dnodes']:
            del dnode['rack_position']

        inventory = self.extractor.extract_hardware_inventory(data_without_rack)

        self.assertFalse(inventory.rack_positions_available)
        self.assertIsNone(inventory.physical_layout)

        # Check CNode processing without rack positions
        cnode = inventory.cnodes[0]
        self.assertIsNone(cnode['rack_position'])
        self.assertEqual(cnode['rack_u'], 'Manual Entry Required')
        self.assertEqual(cnode['positioning_note'], 'Not available for this cluster version')

    def test_extract_network_configuration(self):
        """Test network configuration extraction."""
        section = self.extractor.extract_network_configuration(self.sample_raw_data)

        self.assertIsInstance(section, ReportSection)
        self.assertEqual(section.name, 'network_configuration')
        self.assertEqual(section.title, 'Network Configuration')
        self.assertIn('dns', section.data)
        self.assertIn('ntp', section.data)
        self.assertIn('vippools', section.data)
        self.assertEqual(section.status, 'complete')

    def test_extract_network_configuration_partial_data(self):
        """Test network configuration extraction with partial data."""
        partial_data = {
            'network': {
                'dns': {'servers': ['8.8.8.8']},
                'ntp': None,
                'vippools': None
            }
        }

        section = self.extractor.extract_network_configuration(partial_data)

        # With only 1 out of 3 data sources available, completeness is 33% which is 'missing'
        self.assertEqual(section.status, 'missing')
        self.assertIsNotNone(section.data['dns'])
        self.assertIsNone(section.data['ntp'])
        self.assertIsNone(section.data['vippools'])

    def test_extract_logical_configuration(self):
        """Test logical configuration extraction."""
        section = self.extractor.extract_logical_configuration(self.sample_raw_data)

        self.assertIsInstance(section, ReportSection)
        self.assertEqual(section.name, 'logical_configuration')
        self.assertEqual(section.title, 'Logical Configuration')
        self.assertIn('tenants', section.data)
        self.assertIn('views', section.data)
        self.assertIn('view_policies', section.data)
        self.assertEqual(section.status, 'complete')

    def test_extract_security_configuration(self):
        """Test security configuration extraction."""
        section = self.extractor.extract_security_configuration(self.sample_raw_data)

        self.assertIsInstance(section, ReportSection)
        self.assertEqual(section.name, 'security_configuration')
        self.assertEqual(section.title, 'Security & Authentication')
        self.assertIn('active_directory', section.data)
        self.assertIn('ldap', section.data)
        self.assertIn('nis', section.data)
        self.assertEqual(section.status, 'complete')

    def test_extract_data_protection_configuration(self):
        """Test data protection configuration extraction."""
        section = self.extractor.extract_data_protection_configuration(self.sample_raw_data)

        self.assertIsInstance(section, ReportSection)
        self.assertEqual(section.name, 'data_protection_configuration')
        self.assertEqual(section.title, 'Data Protection')
        self.assertIn('snapshot_programs', section.data)
        self.assertIn('protection_policies', section.data)
        self.assertEqual(section.status, 'complete')

    def test_extract_all_data(self):
        """Test comprehensive data extraction."""
        report_data = self.extractor.extract_all_data(self.sample_raw_data)

        self.assertIn('metadata', report_data)
        self.assertIn('cluster_summary', report_data)
        self.assertIn('hardware_inventory', report_data)
        self.assertIn('sections', report_data)

        # Check metadata
        metadata = report_data['metadata']
        self.assertIn('extraction_timestamp', metadata)
        self.assertIn('overall_completeness', metadata)
        self.assertIn('enhanced_features', metadata)

        # Check sections
        sections = report_data['sections']
        self.assertIn('network_configuration', sections)
        self.assertIn('logical_configuration', sections)
        self.assertIn('security_configuration', sections)
        self.assertIn('data_protection_configuration', sections)

    def test_extract_all_data_with_errors(self):
        """Test data extraction with graceful error handling."""
        # Test with invalid data - the extract_all_data method always uses
        # graceful degradation to ensure it never crashes
        invalid_data = {'invalid': 'data'}

        result = self.extractor.extract_all_data(invalid_data)

        # Should return a complete structure with error status sections
        self.assertIn('metadata', result)
        self.assertIn('cluster_summary', result)
        self.assertIn('hardware_inventory', result)
        self.assertIn('sections', result)

        # All sections should have error status due to missing data
        sections = result['sections']
        for section_name, section_data in sections.items():
            self.assertEqual(section_data['status'], 'error')

    def test_calculate_completeness(self):
        """Test completeness calculation."""
        # Test with all True
        completeness = self.extractor._calculate_completeness([True, True, True])
        self.assertEqual(completeness, 1.0)

        # Test with mixed values
        completeness = self.extractor._calculate_completeness([True, False, True])
        self.assertEqual(completeness, 2/3)

        # Test with all False
        completeness = self.extractor._calculate_completeness([False, False, False])
        self.assertEqual(completeness, 0.0)

        # Test with empty list
        completeness = self.extractor._calculate_completeness([])
        self.assertEqual(completeness, 0.0)

    def test_determine_section_status(self):
        """Test section status determination."""
        # Complete
        status = self.extractor._determine_section_status(0.95)
        self.assertEqual(status, 'complete')

        # Partial
        status = self.extractor._determine_section_status(0.75)
        self.assertEqual(status, 'partial')

        # Missing
        status = self.extractor._determine_section_status(0.25)
        self.assertEqual(status, 'missing')

        # Error
        status = self.extractor._determine_section_status(0.0)
        self.assertEqual(status, 'error')

    def test_save_processed_data(self):
        """Test saving processed data to file."""
        test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
        output_path = str(Path(self.temp_dir) / 'test_output.json')

        result = self.extractor.save_processed_data(test_data, output_path)

        self.assertTrue(result)
        self.assertTrue(Path(output_path).exists())

        # Verify file contents
        with open(output_path, 'r') as f:
            loaded_data = json.load(f)
        self.assertEqual(loaded_data['test'], 'data')

    def test_save_processed_data_invalid_path(self):
        """Test saving processed data with invalid path."""
        test_data = {'test': 'data'}
        invalid_path = '/invalid/path/that/does/not/exist/test.json'

        result = self.extractor.save_processed_data(test_data, invalid_path)

        self.assertFalse(result)

    def test_process_hardware_node(self):
        """Test individual hardware node processing."""
        node_data = {
            'id': 'test-node',
            'model': 'Test-Model',
            'serial_number': 'SN123456',
            'status': 'active',
            'rack_position': 5
        }

        processed = self.extractor._process_hardware_node(node_data, 'cnode')

        self.assertEqual(processed['id'], 'test-node')
        self.assertEqual(processed['type'], 'cnode')
        self.assertEqual(processed['rack_position'], 5)
        self.assertEqual(processed['rack_u'], 'U5')
        self.assertTrue(processed['rack_position_available'])
        self.assertEqual(processed['positioning_note'], 'Automated via API')

    def test_process_hardware_node_no_rack_position(self):
        """Test hardware node processing without rack position."""
        node_data = {
            'id': 'test-node',
            'model': 'Test-Model',
            'serial_number': 'SN123456',
            'status': 'active'
        }

        processed = self.extractor._process_hardware_node(node_data, 'dnode')

        self.assertEqual(processed['type'], 'dnode')
        self.assertIsNone(processed['rack_position'])
        self.assertEqual(processed['rack_u'], 'Manual Entry Required')
        self.assertFalse(processed['rack_position_available'])
        self.assertEqual(processed['positioning_note'], 'Not available for this cluster version')

    def test_generate_physical_layout(self):
        """Test physical layout generation."""
        cnodes = [
            {'id': 'cnode-1', 'rack_position': 5},
            {'id': 'cnode-2', 'rack_position': 6}
        ]
        dnodes = [
            {'id': 'dnode-1', 'rack_position': 10}
        ]

        layout = self.extractor._generate_physical_layout(cnodes, dnodes)

        self.assertIsNotNone(layout)
        self.assertIn('rack_layout', layout)
        self.assertIn('statistics', layout)
        self.assertEqual(layout['statistics']['occupied_positions'], 3)
        self.assertEqual(layout['statistics']['min_position'], 5)
        self.assertEqual(layout['statistics']['max_position'], 10)
        self.assertEqual(layout['statistics']['total_cnodes'], 2)
        self.assertEqual(layout['statistics']['total_dnodes'], 1)

    def test_generate_physical_layout_empty(self):
        """Test physical layout generation with empty data."""
        layout = self.extractor._generate_physical_layout([], [])

        self.assertIsNotNone(layout)
        self.assertEqual(layout['statistics']['occupied_positions'], 0)

    def test_create_data_extractor(self):
        """Test convenience function for creating data extractor."""
        extractor = create_data_extractor(self.test_config)

        self.assertIsInstance(extractor, VastDataExtractor)
        self.assertEqual(extractor.config, self.test_config)


class TestClusterSummary(unittest.TestCase):
    """Test cases for ClusterSummary dataclass."""

    def test_cluster_summary_creation(self):
        """Test ClusterSummary creation."""
        summary = ClusterSummary(
            name='Test Cluster',
            guid='test-guid',
            version='5.3.0',
            state='active',
            license='Enterprise',
            psnt='PSNT123456',
            enhanced_features={'rack_height_supported': True},
            collection_timestamp=datetime.now()
        )

        self.assertEqual(summary.name, 'Test Cluster')
        self.assertEqual(summary.psnt, 'PSNT123456')
        self.assertTrue(summary.enhanced_features['rack_height_supported'])


class TestHardwareInventory(unittest.TestCase):
    """Test cases for HardwareInventory dataclass."""

    def test_hardware_inventory_creation(self):
        """Test HardwareInventory creation."""
        inventory = HardwareInventory(
            cnodes=[{'id': 'cnode-1'}],
            dnodes=[{'id': 'dnode-1'}],
            total_nodes=2,
            rack_positions_available=True,
            physical_layout={'test': 'layout'}
        )

        self.assertEqual(inventory.total_nodes, 2)
        self.assertTrue(inventory.rack_positions_available)
        self.assertIsNotNone(inventory.physical_layout)


class TestReportSection(unittest.TestCase):
    """Test cases for ReportSection dataclass."""

    def test_report_section_creation(self):
        """Test ReportSection creation."""
        section = ReportSection(
            name='test_section',
            title='Test Section',
            data={'test': 'data'},
            completeness=0.95,
            status='complete'
        )

        self.assertEqual(section.name, 'test_section')
        self.assertEqual(section.completeness, 0.95)
        self.assertEqual(section.status, 'complete')


if __name__ == '__main__':
    unittest.main()
