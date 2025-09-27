"""
Unit tests for VAST As-Built Report Generator Main CLI Application.

This module contains comprehensive unit tests for the main CLI application,
including argument parsing, workflow orchestration, and error handling.

Author: Manus AI
Date: September 26, 2025
"""

import unittest
import tempfile
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock
from io import StringIO
import argparse

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from main import (
    VastReportGenerator,
    create_argument_parser,
    load_configuration,
    main
)


class TestVastReportGenerator(unittest.TestCase):
    """Test cases for VastReportGenerator class."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_config = {
            'api': {
                'timeout': 30,
                'max_retries': 3
            },
            'data_collection': {
                'validate_responses': True,
                'graceful_degradation': True
            }
        }

        self.generator = VastReportGenerator(config=self.test_config)

        # Mock data for testing
        self.mock_raw_data = {
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
                'cnodes': [{'id': 'cnode-1', 'model': 'CBox-100'}],
                'dnodes': [{'id': 'dnode-1', 'model': 'DBox-100'}]
            }
        }

        self.mock_processed_data = {
            'metadata': {
                'extraction_timestamp': '2025-09-26T23:00:00',
                'overall_completeness': 0.95,
                'enhanced_features': {'rack_height_supported': True}
            },
            'cluster_summary': {
                'name': 'Test Cluster',
                'version': '5.3.0',
                'state': 'active',
                'psnt': 'PSNT123456789'
            },
            'hardware_inventory': {
                'total_nodes': 2,
                'cnodes': [{'id': 'cnode-1'}],
                'dnodes': [{'id': 'dnode-1'}],
                'rack_positions_available': True
            },
            'sections': {
                'network_configuration': {'status': 'complete', 'completeness': 1.0},
                'logical_configuration': {'status': 'complete', 'completeness': 1.0}
            }
        }

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        if self.generator.api_handler:
            self.generator.api_handler.close()

    def test_initialization(self):
        """Test generator initialization."""
        self.assertEqual(self.generator.config, self.test_config)
        self.assertIsNone(self.generator.api_handler)
        self.assertIsNone(self.generator.data_extractor)

    @patch('main.create_data_extractor')
    def test_initialize_components(self, mock_create_extractor):
        """Test component initialization."""
        mock_extractor = MagicMock()
        mock_create_extractor.return_value = mock_extractor

        args = argparse.Namespace()

        result = self.generator._initialize_components(args)

        self.assertTrue(result)
        self.assertEqual(self.generator.data_extractor, mock_extractor)
        mock_create_extractor.assert_called_once_with(self.test_config)

    @patch('main.create_data_extractor')
    def test_initialize_components_failure(self, mock_create_extractor):
        """Test component initialization failure."""
        mock_create_extractor.side_effect = Exception("Initialization failed")

        args = argparse.Namespace()

        result = self.generator._initialize_components(args)

        self.assertFalse(result)

    @patch('main.create_vast_api_handler')
    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_connect_to_cluster_success(self, mock_getpass, mock_input, mock_create_handler):
        """Test successful cluster connection."""
        # Mock API handler
        mock_handler = MagicMock()
        mock_handler.authenticate.return_value = True
        mock_create_handler.return_value = mock_handler

        # Mock credential input
        mock_input.return_value = 'admin'
        mock_getpass.return_value = 'password'

        args = argparse.Namespace(cluster_ip='192.168.1.100', username=None, password=None)

        result = self.generator._connect_to_cluster(args)

        self.assertTrue(result)
        self.assertEqual(self.generator.api_handler, mock_handler)
        mock_handler.authenticate.assert_called_once()

    @patch('main.create_vast_api_handler')
    def test_connect_to_cluster_authentication_failure(self, mock_create_handler):
        """Test cluster connection with authentication failure."""
        # Mock API handler
        mock_handler = MagicMock()
        mock_handler.authenticate.return_value = False
        mock_create_handler.return_value = mock_handler

        args = argparse.Namespace(cluster_ip='192.168.1.100', username='admin', password='wrong')

        result = self.generator._connect_to_cluster(args)

        self.assertFalse(result)

    def test_get_credentials_from_args(self):
        """Test getting credentials from command-line arguments."""
        args = argparse.Namespace(username='admin', password='password')

        username, password = self.generator._get_credentials(args)

        self.assertEqual(username, 'admin')
        self.assertEqual(password, 'password')

    @patch.dict(os.environ, {'VAST_USERNAME': 'env_user', 'VAST_PASSWORD': 'env_pass'})
    def test_get_credentials_from_env(self):
        """Test getting credentials from environment variables."""
        args = argparse.Namespace()

        username, password = self.generator._get_credentials(args)

        self.assertEqual(username, 'env_user')
        self.assertEqual(password, 'env_pass')

    @patch('builtins.input')
    @patch('getpass.getpass')
    def test_get_credentials_interactive(self, mock_getpass, mock_input):
        """Test getting credentials interactively."""
        mock_input.return_value = 'admin'
        mock_getpass.return_value = 'password'

        args = argparse.Namespace(username=None, password=None)

        username, password = self.generator._get_credentials(args)

        self.assertEqual(username, 'admin')
        self.assertEqual(password, 'password')
        mock_input.assert_called_once_with("VAST Username: ")
        mock_getpass.assert_called_once_with("VAST Password: ")

    def test_get_credentials_empty_username(self):
        """Test getting credentials with empty username."""
        args = argparse.Namespace(username=None, password=None)

        with patch('builtins.input', return_value=''):
            username, password = self.generator._get_credentials(args)

            self.assertIsNone(username)
            self.assertIsNone(password)

    def test_get_credentials_empty_password(self):
        """Test getting credentials with empty password."""
        args = argparse.Namespace(username=None, password=None)

        with patch('builtins.input', return_value='admin'), \
             patch('getpass.getpass', return_value=''):
            username, password = self.generator._get_credentials(args)

            self.assertIsNone(username)
            self.assertIsNone(password)

    def test_collect_data_success(self):
        """Test successful data collection."""
        # Mock API handler
        mock_handler = MagicMock()
        mock_handler.get_all_data.return_value = self.mock_raw_data
        self.generator.api_handler = mock_handler

        result = self.generator._collect_data()

        self.assertEqual(result, self.mock_raw_data)
        mock_handler.get_all_data.assert_called_once()

    def test_collect_data_failure(self):
        """Test data collection failure."""
        # Mock API handler
        mock_handler = MagicMock()
        mock_handler.get_all_data.return_value = None
        self.generator.api_handler = mock_handler

        result = self.generator._collect_data()

        self.assertIsNone(result)

    def test_process_data_success(self):
        """Test successful data processing."""
        # Mock data extractor
        mock_extractor = MagicMock()
        mock_extractor.extract_all_data.return_value = self.mock_processed_data
        self.generator.data_extractor = mock_extractor

        result = self.generator._process_data(self.mock_raw_data)

        self.assertEqual(result, self.mock_processed_data)
        mock_extractor.extract_all_data.assert_called_once_with(self.mock_raw_data)

    def test_process_data_failure(self):
        """Test data processing failure."""
        # Mock data extractor
        mock_extractor = MagicMock()
        mock_extractor.extract_all_data.return_value = None
        self.generator.data_extractor = mock_extractor

        result = self.generator._process_data(self.mock_raw_data)

        self.assertIsNone(result)

    @patch('main.Path')
    def test_generate_reports_success(self, mock_path):
        """Test successful report generation."""
        # Mock Path operations
        mock_output_dir = MagicMock()
        mock_path.return_value = mock_output_dir
        mock_output_dir.mkdir.return_value = None
        mock_output_dir.__truediv__.return_value = Path('test_output.json')

        # Mock data extractor
        mock_extractor = MagicMock()
        mock_extractor.save_processed_data.return_value = True
        self.generator.data_extractor = mock_extractor

        args = argparse.Namespace(output_dir='./test_output')

        result = self.generator._generate_reports(self.mock_processed_data, args)

        self.assertTrue(result)
        mock_extractor.save_processed_data.assert_called_once()

    def test_generate_reports_save_failure(self):
        """Test report generation with save failure."""
        # Mock data extractor
        mock_extractor = MagicMock()
        mock_extractor.save_processed_data.return_value = False
        self.generator.data_extractor = mock_extractor

        args = argparse.Namespace(output_dir='./test_output')

        result = self.generator._generate_reports(self.mock_processed_data, args)

        self.assertFalse(result)

    @patch('builtins.print')
    def test_display_summary(self, mock_print):
        """Test summary display."""
        args = argparse.Namespace(output_dir='./test_output')

        self.generator._display_summary(self.mock_processed_data, args)

        # Verify print was called multiple times (summary sections)
        self.assertGreater(mock_print.call_count, 5)

    def test_cleanup(self):
        """Test resource cleanup."""
        # Mock API handler
        mock_handler = MagicMock()
        self.generator.api_handler = mock_handler

        self.generator._cleanup()

        mock_handler.close.assert_called_once()

    def test_cleanup_no_handler(self):
        """Test cleanup with no API handler."""
        # Should not raise an exception
        self.generator._cleanup()

    @patch.object(VastReportGenerator, '_initialize_components')
    @patch.object(VastReportGenerator, '_connect_to_cluster')
    @patch.object(VastReportGenerator, '_collect_data')
    @patch.object(VastReportGenerator, '_process_data')
    @patch.object(VastReportGenerator, '_generate_reports')
    @patch.object(VastReportGenerator, '_display_summary')
    @patch.object(VastReportGenerator, '_cleanup')
    def test_run_success(self, mock_cleanup, mock_display, mock_generate,
                        mock_process, mock_collect, mock_connect, mock_init):
        """Test successful application run."""
        # Mock all methods to return success
        mock_init.return_value = True
        mock_connect.return_value = True
        mock_collect.return_value = self.mock_raw_data
        mock_process.return_value = self.mock_processed_data
        mock_generate.return_value = True

        args = argparse.Namespace(cluster_ip='192.168.1.100', output_dir='./test')

        result = self.generator.run(args)

        self.assertEqual(result, 0)
        mock_cleanup.assert_called_once()

    @patch.object(VastReportGenerator, '_initialize_components')
    def test_run_initialization_failure(self, mock_init):
        """Test application run with initialization failure."""
        mock_init.return_value = False

        args = argparse.Namespace(cluster_ip='192.168.1.100', output_dir='./test')

        result = self.generator.run(args)

        self.assertEqual(result, 1)

    @patch.object(VastReportGenerator, '_initialize_components')
    @patch.object(VastReportGenerator, '_connect_to_cluster')
    def test_run_connection_failure(self, mock_connect, mock_init):
        """Test application run with connection failure."""
        mock_init.return_value = True
        mock_connect.return_value = False

        args = argparse.Namespace(cluster_ip='192.168.1.100', output_dir='./test')

        result = self.generator.run(args)

        self.assertEqual(result, 1)

    def test_run_keyboard_interrupt(self):
        """Test application run with keyboard interrupt."""
        args = argparse.Namespace(cluster_ip='192.168.1.100', output_dir='./test')

        with patch.object(self.generator, '_initialize_components', side_effect=KeyboardInterrupt):
            result = self.generator.run(args)

            self.assertEqual(result, 1)

    def test_run_unexpected_error(self):
        """Test application run with unexpected error."""
        args = argparse.Namespace(cluster_ip='192.168.1.100', output_dir='./test')

        with patch.object(self.generator, '_initialize_components', side_effect=Exception("Unexpected error")):
            result = self.generator.run(args)

            self.assertEqual(result, 1)


class TestArgumentParser(unittest.TestCase):
    """Test cases for argument parser."""

    def test_create_argument_parser(self):
        """Test argument parser creation."""
        parser = create_argument_parser()

        self.assertIsInstance(parser, argparse.ArgumentParser)
        # The prog name may vary depending on how the script is run
        self.assertIn('main', parser.prog)

    def test_required_arguments(self):
        """Test required arguments parsing."""
        parser = create_argument_parser()

        # Test with required arguments
        args = parser.parse_args(['--cluster', '192.168.1.100', '--output', './test'])

        self.assertEqual(args.cluster_ip, '192.168.1.100')
        self.assertEqual(args.output_dir, './test')

    def test_optional_arguments(self):
        """Test optional arguments parsing."""
        parser = create_argument_parser()

        args = parser.parse_args([
            '--cluster', '192.168.1.100',
            '--output', './test',
            '--username', 'admin',
            '--password', 'password',
            '--config', 'custom.yaml',
            '--verbose'
        ])

        self.assertEqual(args.username, 'admin')
        self.assertEqual(args.password, 'password')
        self.assertEqual(args.config, 'custom.yaml')
        self.assertTrue(args.verbose)

    def test_version_argument(self):
        """Test version argument."""
        parser = create_argument_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(['--version'])


class TestConfigurationLoading(unittest.TestCase):
    """Test cases for configuration loading."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    def test_load_configuration_file_exists(self):
        """Test loading configuration from existing file."""
        import yaml

        config_data = {'api': {'timeout': 60}, 'logging': {'level': 'DEBUG'}}
        config_file = Path(self.temp_dir) / 'test_config.yaml'

        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        result = load_configuration(str(config_file))

        self.assertEqual(result, config_data)

    def test_load_configuration_file_not_exists(self):
        """Test loading configuration from non-existent file."""
        result = load_configuration('nonexistent.yaml')

        self.assertEqual(result, {})

    def test_load_configuration_invalid_yaml(self):
        """Test loading configuration from invalid YAML file."""
        config_file = Path(self.temp_dir) / 'invalid.yaml'

        with open(config_file, 'w') as f:
            f.write('invalid: yaml: content: [')

        result = load_configuration(str(config_file))

        self.assertEqual(result, {})

    def test_load_configuration_default_path(self):
        """Test loading configuration with default path."""
        result = load_configuration()

        # Should return a dict (may be empty or loaded from config file)
        self.assertIsInstance(result, dict)


class TestMainFunction(unittest.TestCase):
    """Test cases for main function."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)

    @patch('main.VastReportGenerator')
    @patch('main.setup_logging')
    @patch('main.load_configuration')
    @patch('sys.argv', ['main.py', '--cluster', '192.168.1.100', '--output', './test'])
    def test_main_success(self, mock_load_config, mock_setup_logging, mock_generator_class):
        """Test successful main function execution."""
        # Mock configuration
        mock_load_config.return_value = {}

        # Mock generator
        mock_generator = MagicMock()
        mock_generator.run.return_value = 0
        mock_generator_class.return_value = mock_generator

        result = main()

        self.assertEqual(result, 0)
        mock_generator.run.assert_called_once()

    @patch('main.VastReportGenerator')
    @patch('main.setup_logging')
    @patch('main.load_configuration')
    @patch('sys.argv', ['main.py', '--cluster', '192.168.1.100', '--output', './test'])
    def test_main_failure(self, mock_load_config, mock_setup_logging, mock_generator_class):
        """Test main function execution failure."""
        # Mock configuration
        mock_load_config.return_value = {}

        # Mock generator
        mock_generator = MagicMock()
        mock_generator.run.return_value = 1
        mock_generator_class.return_value = mock_generator

        result = main()

        self.assertEqual(result, 1)

    @patch('sys.argv', ['main.py', '--cluster', '192.168.1.100'])
    def test_main_missing_required_args(self):
        """Test main function with missing required arguments."""
        with self.assertRaises(SystemExit) as cm:
            main()

        self.assertEqual(cm.exception.code, 2)

    @patch('sys.argv', ['main.py', '--cluster', '192.168.1.100', '--output', './test'])
    def test_main_keyboard_interrupt(self):
        """Test main function with keyboard interrupt."""
        with patch('main.VastReportGenerator', side_effect=KeyboardInterrupt):
            result = main()

            self.assertEqual(result, 1)

    @patch('sys.argv', ['main.py', '--cluster', '192.168.1.100', '--output', './test'])
    def test_main_unexpected_error(self):
        """Test main function with unexpected error."""
        with patch('main.VastReportGenerator', side_effect=Exception("Unexpected error")):
            result = main()

            self.assertEqual(result, 1)


if __name__ == '__main__':
    unittest.main()
