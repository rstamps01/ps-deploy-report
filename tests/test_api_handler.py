"""
Unit tests for VAST As-Built Report Generator API Handler Module.

This module contains comprehensive unit tests for the API handler,
including authentication, data collection, error handling, and enhanced features.

Author: Manus AI
Date: September 12, 2025
"""

import unittest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
import requests
import sys

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from api_handler import (
    VastApiHandler,
    VastClusterInfo,
    VastHardwareInfo,
    VastApiError,
    VastApiVersion,
    create_vast_api_handler
)


class TestVastApiHandler(unittest.TestCase):
    """Test cases for VastApiHandler class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            'api': {
                'timeout': 30,
                'max_retries': 3,
                'retry_delay': 2,
                'verify_ssl': True,
                'version': 'v7'
            }
        }

        self.handler = VastApiHandler(
            cluster_ip='192.168.1.100',
            username='admin',
            password='password',
            config=self.test_config
        )

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        if self.handler.session:
            self.handler.session.close()

    def test_initialization(self):
        """Test API handler initialization."""
        self.assertEqual(self.handler.cluster_ip, '192.168.1.100')
        self.assertEqual(self.handler.username, 'admin')
        self.assertEqual(self.handler.password, 'password')
        self.assertEqual(self.handler.timeout, 30)
        self.assertEqual(self.handler.max_retries, 3)
        self.assertFalse(self.handler.authenticated)

    def test_setup_session(self):
        """Test session setup with retry strategy."""
        session = self.handler._setup_session()

        self.assertIsInstance(session, requests.Session)
        self.assertIn('User-Agent', session.headers)
        self.assertEqual(session.headers['Content-Type'], 'application/json')

    @patch('requests.Session.post')
    def test_successful_authentication(self, mock_post):
        """Test successful authentication."""
        # Mock successful authentication response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'status': 'success'}
        mock_post.return_value = mock_response

        result = self.handler.authenticate()

        self.assertTrue(result)
        self.assertTrue(self.handler.authenticated)
        mock_post.assert_called_once()

    @patch('requests.Session.post')
    def test_failed_authentication(self, mock_post):
        """Test failed authentication."""
        # Mock failed authentication response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Authentication failed'
        mock_post.return_value = mock_response

        result = self.handler.authenticate()

        self.assertFalse(result)
        self.assertFalse(self.handler.authenticated)

    @patch('requests.Session.post')
    def test_authentication_request_exception(self, mock_post):
        """Test authentication with request exception."""
        mock_post.side_effect = requests.exceptions.RequestException("Network error")

        result = self.handler.authenticate()

        self.assertFalse(result)
        self.assertFalse(self.handler.authenticated)

    def test_detect_cluster_capabilities(self):
        """Test cluster capability detection."""
        # Mock cluster info response
        cluster_data = {'version': '5.3.0'}

        with patch.object(self.handler, '_make_api_request', return_value=cluster_data):
            self.handler._detect_cluster_capabilities()

            self.assertEqual(self.handler.cluster_version, '5.3.0')
            self.assertTrue(self.handler.rack_height_supported)
            self.assertTrue(self.handler.psnt_supported)

    def test_determine_supported_features_old_version(self):
        """Test feature detection for older cluster versions."""
        self.handler.cluster_version = "5.1.0"
        self.handler._determine_supported_features()

        self.assertFalse(self.handler.rack_height_supported)
        self.assertFalse(self.handler.psnt_supported)

    def test_determine_supported_features_new_version(self):
        """Test feature detection for newer cluster versions."""
        self.handler.cluster_version = "5.3.0"
        self.handler._determine_supported_features()

        self.assertTrue(self.handler.rack_height_supported)
        self.assertTrue(self.handler.psnt_supported)

    @patch('requests.Session.get')
    def test_make_api_request_success(self, mock_get):
        """Test successful API request."""
        # Set up authenticated handler
        self.handler.authenticated = True
        self.handler.session = self.handler._setup_session()

        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'test': 'data'}
        mock_get.return_value = mock_response

        result = self.handler._make_api_request('test/')

        self.assertEqual(result, {'test': 'data'})
        mock_get.assert_called_once()

    @patch('requests.Session.get')
    def test_make_api_request_unauthorized(self, mock_get):
        """Test API request with 401 response."""
        # Set up authenticated handler
        self.handler.authenticated = True
        self.handler.session = self.handler._setup_session()

        # Mock 401 response
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with patch.object(self.handler, 'authenticate', return_value=False):
            result = self.handler._make_api_request('test/')

            self.assertIsNone(result)

    def test_make_api_request_not_authenticated(self):
        """Test API request without authentication."""
        result = self.handler._make_api_request('test/')

        self.assertIsNone(result)

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_cluster_info_success(self, mock_request):
        """Test successful cluster info retrieval."""
        # Mock cluster data with PSNT
        cluster_data = {
            'name': 'Test Cluster',
            'guid': 'test-guid-123',
            'version': '5.3.0',
            'state': 'active',
            'license': 'Enterprise',
            'psnt': 'PSNT123456'
        }
        mock_request.return_value = cluster_data

        # Set up handler with enhanced features
        self.handler.psnt_supported = True
        self.handler.authenticated = True

        result = self.handler.get_cluster_info()

        self.assertIsInstance(result, VastClusterInfo)
        self.assertEqual(result.name, 'Test Cluster')
        self.assertEqual(result.guid, 'test-guid-123')
        self.assertEqual(result.version, '5.3.0')
        self.assertEqual(result.psnt, 'PSNT123456')

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_cluster_info_no_psnt(self, mock_request):
        """Test cluster info retrieval without PSNT."""
        # Mock cluster data without PSNT
        cluster_data = {
            'name': 'Test Cluster',
            'guid': 'test-guid-123',
            'version': '5.1.0',
            'state': 'active',
            'license': 'Enterprise'
        }
        mock_request.return_value = cluster_data

        # Set up handler without enhanced features
        self.handler.psnt_supported = False
        self.handler.authenticated = True

        result = self.handler.get_cluster_info()

        self.assertIsInstance(result, VastClusterInfo)
        self.assertEqual(result.name, 'Test Cluster')
        self.assertIsNone(result.psnt)

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_cnode_details_success(self, mock_request):
        """Test successful CNode details retrieval."""
        # Mock CNode data with rack positions
        cnodes_data = [
            {
                'id': 'cnode-1',
                'model': 'CBox-100',
                'serial_number': 'SN123456',
                'state': 'active',
                'index_in_rack': 5
            },
            {
                'id': 'cnode-2',
                'model': 'CBox-100',
                'serial_number': 'SN123457',
                'state': 'active',
                'index_in_rack': 6
            }
        ]
        mock_request.return_value = cnodes_data

        # Set up handler with enhanced features
        self.handler.rack_height_supported = True
        self.handler.authenticated = True

        result = self.handler.get_cnode_details()

        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], VastHardwareInfo)
        self.assertEqual(result[0].node_id, 'cnode-1')
        self.assertEqual(result[0].rack_position, 5)
        self.assertEqual(result[1].rack_position, 6)

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_dnode_details_success(self, mock_request):
        """Test successful DNode details retrieval."""
        # Mock DNode data with rack positions
        dnodes_data = [
            {
                'id': 'dnode-1',
                'model': 'DBox-100',
                'serial_number': 'SN789012',
                'state': 'active',
                'index_in_rack': 10
            }
        ]
        mock_request.return_value = dnodes_data

        # Set up handler with enhanced features
        self.handler.rack_height_supported = True
        self.handler.authenticated = True

        result = self.handler.get_dnode_details()

        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], VastHardwareInfo)
        self.assertEqual(result[0].node_id, 'dnode-1')
        self.assertEqual(result[0].rack_position, 10)

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_network_configuration(self, mock_request):
        """Test network configuration retrieval."""
        # Mock network data
        dns_data = {'servers': ['8.8.8.8', '8.8.4.4']}
        ntp_data = {'servers': ['pool.ntp.org']}
        vippool_data = {'pools': [{'name': 'default', 'vips': ['192.168.1.10']}]}

        def side_effect(endpoint):
            if 'dns' in endpoint:
                return dns_data
            elif 'ntp' in endpoint:
                return ntp_data
            elif 'vippool' in endpoint:
                return vippool_data
            return None

        mock_request.side_effect = side_effect
        self.handler.authenticated = True

        result = self.handler.get_network_configuration()

        self.assertIn('dns', result)
        self.assertIn('ntp', result)
        self.assertIn('vippools', result)
        self.assertEqual(result['dns'], dns_data)

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_logical_configuration(self, mock_request):
        """Test logical configuration retrieval."""
        # Mock logical data
        tenants_data = [{'name': 'tenant1', 'id': 't1'}]
        views_data = [{'name': 'view1', 'path': '/view1'}]
        viewpolicies_data = [{'name': 'policy1', 'type': 'read-only'}]

        def side_effect(endpoint):
            if 'tenant' in endpoint:
                return tenants_data
            elif 'view' in endpoint and 'policy' not in endpoint:
                return views_data
            elif 'viewpolicy' in endpoint:
                return viewpolicies_data
            return None

        mock_request.side_effect = side_effect
        self.handler.authenticated = True

        result = self.handler.get_logical_configuration()

        self.assertIn('tenants', result)
        self.assertIn('views', result)
        self.assertIn('viewpolicies', result)
        self.assertEqual(result['tenants'], tenants_data)

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_security_configuration(self, mock_request):
        """Test security configuration retrieval."""
        # Mock security data
        ad_data = {'enabled': True, 'domain': 'example.com'}
        ldap_data = {'enabled': False}
        nis_data = {'enabled': False}

        def side_effect(endpoint):
            if 'activedirectory' in endpoint:
                return ad_data
            elif 'ldap' in endpoint:
                return ldap_data
            elif 'nis' in endpoint:
                return nis_data
            return None

        mock_request.side_effect = side_effect
        self.handler.authenticated = True

        result = self.handler.get_security_configuration()

        self.assertIn('activedirectory', result)
        self.assertIn('ldap', result)
        self.assertIn('nis', result)
        self.assertEqual(result['activedirectory'], ad_data)

    @patch.object(VastApiHandler, '_make_api_request')
    def test_get_data_protection_configuration(self, mock_request):
        """Test data protection configuration retrieval."""
        # Mock protection data
        snapprograms_data = [{'name': 'daily', 'schedule': '0 2 * * *'}]
        protectionpolicies_data = [{'name': 'backup', 'retention': '30d'}]

        def side_effect(endpoint):
            if 'snapprogram' in endpoint:
                return snapprograms_data
            elif 'protectionpolicy' in endpoint:
                return protectionpolicies_data
            return None

        mock_request.side_effect = side_effect
        self.handler.authenticated = True

        result = self.handler.get_data_protection_configuration()

        self.assertIn('snapprograms', result)
        self.assertIn('protectionpolicies', result)
        self.assertEqual(result['snapprograms'], snapprograms_data)

    @patch.object(VastApiHandler, 'get_cluster_info')
    @patch.object(VastApiHandler, 'get_cnode_details')
    @patch.object(VastApiHandler, 'get_dnode_details')
    @patch.object(VastApiHandler, 'get_network_configuration')
    @patch.object(VastApiHandler, 'get_logical_configuration')
    @patch.object(VastApiHandler, 'get_security_configuration')
    @patch.object(VastApiHandler, 'get_data_protection_configuration')
    def test_get_all_data(self, mock_protection, mock_security, mock_logical,
                         mock_network, mock_dnodes, mock_cnodes, mock_cluster):
        """Test comprehensive data collection."""
        # Mock all data collection methods
        mock_cluster.return_value = VastClusterInfo(
            name='Test Cluster', guid='test-guid', version='5.3.0',
            state='active', license='Enterprise', psnt='PSNT123'
        )
        mock_cnodes.return_value = [VastHardwareInfo('cnode-1', 'cnode', 'CBox-100', 'SN123', 5)]
        mock_dnodes.return_value = [VastHardwareInfo('dnode-1', 'dnode', 'DBox-100', 'SN456', 10)]
        mock_network.return_value = {'dns': {'servers': ['8.8.8.8']}}
        mock_logical.return_value = {'tenants': [{'name': 'tenant1'}]}
        mock_security.return_value = {'activedirectory': {'enabled': True}}
        mock_protection.return_value = {'snapprograms': [{'name': 'daily'}]}

        self.handler.authenticated = True
        self.handler.rack_height_supported = True
        self.handler.psnt_supported = True

        result = self.handler.get_all_data()

        self.assertIn('cluster_info', result)
        self.assertIn('hardware', result)
        self.assertIn('network', result)
        self.assertIn('logical', result)
        self.assertIn('security', result)
        self.assertIn('data_protection', result)
        self.assertIn('enhanced_features', result)
        self.assertTrue(result['enhanced_features']['rack_height_supported'])
        self.assertTrue(result['enhanced_features']['psnt_supported'])

    def test_get_all_data_not_authenticated(self):
        """Test get_all_data without authentication."""
        result = self.handler.get_all_data()

        self.assertEqual(result, {})

    def test_close(self):
        """Test session cleanup."""
        self.handler.session = self.handler._setup_session()
        self.handler.authenticated = True

        self.handler.close()

        self.assertFalse(self.handler.authenticated)

    def test_context_manager(self):
        """Test context manager functionality."""
        with patch.object(self.handler, 'close') as mock_close:
            with self.handler as handler:
                self.assertEqual(handler, self.handler)
            mock_close.assert_called_once()

    def test_create_vast_api_handler(self):
        """Test convenience function for creating API handler."""
        handler = create_vast_api_handler('192.168.1.100', 'admin', 'password', self.test_config)

        self.assertIsInstance(handler, VastApiHandler)
        self.assertEqual(handler.cluster_ip, '192.168.1.100')
        self.assertEqual(handler.username, 'admin')


class TestVastClusterInfo(unittest.TestCase):
    """Test cases for VastClusterInfo dataclass."""

    def test_cluster_info_creation(self):
        """Test VastClusterInfo creation."""
        cluster = VastClusterInfo(
            name='Test Cluster',
            guid='test-guid',
            version='5.3.0',
            state='active',
            license='Enterprise',
            psnt='PSNT123456'
        )

        self.assertEqual(cluster.name, 'Test Cluster')
        self.assertEqual(cluster.guid, 'test-guid')
        self.assertEqual(cluster.version, '5.3.0')
        self.assertEqual(cluster.state, 'active')
        self.assertEqual(cluster.license, 'Enterprise')
        self.assertEqual(cluster.psnt, 'PSNT123456')

    def test_cluster_info_without_psnt(self):
        """Test VastClusterInfo creation without PSNT."""
        cluster = VastClusterInfo(
            name='Test Cluster',
            guid='test-guid',
            version='5.1.0',
            state='active',
            license='Enterprise'
        )

        self.assertEqual(cluster.name, 'Test Cluster')
        self.assertIsNone(cluster.psnt)


class TestVastHardwareInfo(unittest.TestCase):
    """Test cases for VastHardwareInfo dataclass."""

    def test_hardware_info_creation(self):
        """Test VastHardwareInfo creation."""
        hardware = VastHardwareInfo(
            node_id='node-1',
            node_type='cnode',
            model='CBox-100',
            serial_number='SN123456',
            rack_position=5,
            status='active'
        )

        self.assertEqual(hardware.node_id, 'node-1')
        self.assertEqual(hardware.node_type, 'cnode')
        self.assertEqual(hardware.model, 'CBox-100')
        self.assertEqual(hardware.serial_number, 'SN123456')
        self.assertEqual(hardware.rack_position, 5)
        self.assertEqual(hardware.status, 'active')

    def test_hardware_info_without_rack_position(self):
        """Test VastHardwareInfo creation without rack position."""
        hardware = VastHardwareInfo(
            node_id='node-1',
            node_type='dnode',
            model='DBox-100',
            serial_number='SN789012'
        )

        self.assertEqual(hardware.node_id, 'node-1')
        self.assertEqual(hardware.node_type, 'dnode')
        self.assertIsNone(hardware.rack_position)
        self.assertEqual(hardware.status, 'unknown')


if __name__ == '__main__':
    unittest.main()
