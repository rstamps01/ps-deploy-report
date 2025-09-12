"""
Unit tests for VAST As-Built Report Generator logging infrastructure.

This module contains comprehensive unit tests for the logging system,
including configuration loading, handler setup, filtering, and error handling.

Author: Manus AI
Date: September 12, 2025
"""

import unittest
import tempfile
import shutil
import logging
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.logger import (
    setup_logging, 
    get_logger, 
    SensitiveDataFilter,
    _load_logging_config,
    _setup_console_handler,
    _setup_file_handler
)


class TestLoggingInfrastructure(unittest.TestCase):
    """Test cases for logging infrastructure."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "test_config.yaml"
        self.log_file = Path(self.temp_dir) / "test.log"
        
        # Clear any existing handlers
        logging.getLogger().handlers.clear()
    
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir)
        logging.getLogger().handlers.clear()
    
    def test_setup_logging_with_default_config(self):
        """Test logging setup with default configuration."""
        logger = setup_logging()
        
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.level, logging.INFO)
        self.assertGreater(len(logger.handlers), 0)
    
    def test_setup_logging_with_custom_config(self):
        """Test logging setup with custom configuration."""
        config = {
            'logging': {
                'level': 'DEBUG',
                'file_path': str(self.log_file),
                'rotation_size': 1024,
                'backup_count': 3
            }
        }
        
        logger = setup_logging(config=config)
        
        self.assertEqual(logger.level, logging.DEBUG)
        self.assertTrue(self.log_file.parent.exists())
    
    def test_get_logger(self):
        """Test getting logger instances."""
        setup_logging()
        
        logger1 = get_logger("test_module_1")
        logger2 = get_logger("test_module_2")
        logger3 = get_logger("test_module_1")  # Same name
        
        self.assertEqual(logger1.name, "test_module_1")
        self.assertEqual(logger2.name, "test_module_2")
        self.assertIs(logger1, logger3)  # Should be the same instance
    
    def test_sensitive_data_filter(self):
        """Test sensitive data filtering."""
        filter_obj = SensitiveDataFilter()
        
        # Create test log records
        safe_record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User login successful", args=(), exc_info=None
        )
        
        sensitive_record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User password is: secret123", args=(), exc_info=None
        )
        
        # Test filtering
        self.assertTrue(filter_obj.filter(safe_record))
        self.assertEqual(safe_record.msg, "User login successful")
        
        self.assertTrue(filter_obj.filter(sensitive_record))
        self.assertIn("PASSWORD_[REDACTED]", sensitive_record.msg)
        self.assertNotIn("secret123", sensitive_record.msg)
    
    def test_load_logging_config_default(self):
        """Test loading default configuration."""
        config = _load_logging_config("nonexistent_file.yaml")
        
        self.assertIn('logging', config)
        self.assertEqual(config['logging']['level'], 'INFO')
        self.assertIn('console_colors', config['logging'])
    
    def test_load_logging_config_from_file(self):
        """Test loading configuration from YAML file."""
        # Create test config file
        config_content = """
logging:
  level: DEBUG
  file_path: custom_log.log
  console_colors:
    INFO: blue
"""
        self.config_file.write_text(config_content)
        
        config = _load_logging_config(str(self.config_file))
        
        self.assertEqual(config['logging']['level'], 'DEBUG')
        self.assertEqual(config['logging']['file_path'], 'custom_log.log')
        self.assertEqual(config['logging']['console_colors']['INFO'], 'blue')
    
    def test_console_handler_setup(self):
        """Test console handler setup."""
        config = {
            'level': 'INFO',
            'console_colors': {
                'INFO': 'green',
                'ERROR': 'red'
            }
        }
        
        handler = _setup_console_handler(config)
        
        self.assertIsInstance(handler, logging.Handler)
        self.assertEqual(handler.level, logging.INFO)
        self.assertIsNotNone(handler.formatter)
    
    def test_file_handler_setup(self):
        """Test file handler setup."""
        config = {
            'level': 'DEBUG',
            'file_path': str(self.log_file),
            'rotation_size': 1024,
            'backup_count': 2
        }
        
        handler = _setup_file_handler(config)
        
        self.assertIsInstance(handler, logging.Handler)
        self.assertEqual(handler.level, logging.DEBUG)
        self.assertTrue(self.log_file.parent.exists())
    
    def test_file_handler_setup_failure(self):
        """Test file handler setup with invalid path."""
        config = {
            'file_path': '/invalid/path/that/does/not/exist/test.log'
        }
        
        handler = _setup_file_handler(config)
        
        # Should return None on failure
        self.assertIsNone(handler)
    
    def test_logging_with_exception(self):
        """Test logging with exception information."""
        setup_logging()
        logger = get_logger("test_exception")
        
        try:
            raise ValueError("Test exception")
        except ValueError:
            # This should not raise an exception
            logger.exception("Exception occurred")
    
    def test_multiple_logger_instances(self):
        """Test multiple logger instances work correctly."""
        setup_logging()
        
        loggers = [
            get_logger("module_1"),
            get_logger("module_2"),
            get_logger("module_3")
        ]
        
        # All loggers should work without interference
        for i, logger in enumerate(loggers):
            logger.info(f"Message from logger {i+1}")
    
    @patch('sys.stdout')
    def test_console_output(self, mock_stdout):
        """Test console output functionality."""
        setup_logging()
        logger = get_logger("test_console")
        
        logger.info("Test console message")
        
        # Verify that stdout was called (console handler working)
        self.assertTrue(mock_stdout.write.called)
    
    def test_log_file_creation(self):
        """Test log file creation and writing."""
        config = {
            'logging': {
                'level': 'INFO',
                'file_path': str(self.log_file)
            }
        }
        
        setup_logging(config=config)
        logger = get_logger("test_file")
        
        logger.info("Test file message")
        
        # Verify log file was created and contains content
        self.assertTrue(self.log_file.exists())
        content = self.log_file.read_text()
        self.assertIn("Test file message", content)
    
    def test_error_handling_in_setup(self):
        """Test error handling during setup."""
        # Test with invalid configuration
        with patch('yaml.safe_load', side_effect=Exception("YAML error")):
            logger = setup_logging(config_file="invalid.yaml")
            
            # Should still return a logger (fallback configuration)
            self.assertIsInstance(logger, logging.Logger)


class TestSensitiveDataFilter(unittest.TestCase):
    """Specific tests for sensitive data filtering."""
    
    def setUp(self):
        """Set up test environment."""
        self.filter = SensitiveDataFilter()
    
    def test_password_filtering(self):
        """Test password filtering."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User password: secret123", args=(), exc_info=None
        )
        
        self.filter.filter(record)
        self.assertIn("PASSWORD_[REDACTED]", record.msg)
        self.assertNotIn("secret123", record.msg)
    
    def test_token_filtering(self):
        """Test token filtering."""
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="API token received: abc123def", args=(), exc_info=None
        )
        
        self.filter.filter(record)
        self.assertIn("TOKEN_[REDACTED]", record.msg)
    
    def test_multiple_sensitive_patterns(self):
        """Test filtering multiple sensitive patterns."""
        test_cases = [
            ("password", "PASSWORD_[REDACTED]"),
            ("token", "TOKEN_[REDACTED]"),
            ("secret", "SECRET_[REDACTED]"),
            ("key", "KEY_[REDACTED]"),
            ("auth", "AUTH_[REDACTED]")
        ]
        
        for pattern, expected in test_cases:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=f"The {pattern} is: sensitive_data", args=(), exc_info=None
            )
            
            self.filter.filter(record)
            self.assertIn(expected, record.msg)
    
    def test_safe_messages_unchanged(self):
        """Test that safe messages are not modified."""
        safe_messages = [
            "User login successful",
            "API request completed",
            "Configuration loaded",
            "Report generated successfully"
        ]
        
        for msg in safe_messages:
            record = logging.LogRecord(
                name="test", level=logging.INFO, pathname="", lineno=0,
                msg=msg, args=(), exc_info=None
            )
            
            original_msg = record.msg
            self.filter.filter(record)
            self.assertEqual(record.msg, original_msg)


if __name__ == '__main__':
    unittest.main()

