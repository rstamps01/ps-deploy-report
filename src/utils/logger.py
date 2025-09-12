"""
VAST As-Built Report Generator - Logging Infrastructure

This module provides comprehensive logging infrastructure for the VAST As-Built Report Generator.
It implements dual-output logging (console with colors + file with rotation), configurable
log levels, and professional formatting suitable for both development and production use.

Features:
- Colored console output for development
- Rotating file logs for production
- Configurable log levels and formats
- Secure handling of sensitive data
- Professional error handling and fallback mechanisms

Author: Manus AI
Date: September 12, 2025
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any
import yaml
import colorlog


class ColoredFormatter(colorlog.ColoredFormatter):
    """
    Custom colored formatter for console output with enhanced formatting.
    
    This formatter provides color-coded log levels for easy visual identification
    during development and debugging.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def format(self, record):
        """Format log record with colors and enhanced information."""
        # Add module and function information for better debugging
        if hasattr(record, 'funcName') and record.funcName != '<module>':
            record.location = f"{record.module}.{record.funcName}"
        else:
            record.location = record.module
        
        return super().format(record)


class SensitiveDataFilter(logging.Filter):
    """
    Filter to prevent sensitive data from being logged.
    
    This filter scans log messages for potential sensitive information
    like passwords, tokens, and API keys, and redacts them before logging.
    """
    
    SENSITIVE_PATTERNS = [
        'password', 'passwd', 'pwd', 'token', 'key', 'secret',
        'auth', 'credential', 'session', 'cookie'
    ]
    
    def filter(self, record):
        """Filter out sensitive data from log records."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            msg_lower = record.msg.lower()
            for pattern in self.SENSITIVE_PATTERNS:
                if pattern in msg_lower:
                    # Find the pattern and replace it with redacted version
                    start_idx = msg_lower.find(pattern)
                    if start_idx != -1:
                        # Replace the pattern and some following characters
                        end_idx = min(start_idx + len(pattern) + 15, len(record.msg))
                        original_part = record.msg[start_idx:end_idx]
                        record.msg = record.msg.replace(original_part, f"{pattern.upper()}_[REDACTED]")
                        break  # Only replace the first occurrence
        return True


def setup_logging(config: Optional[Dict[str, Any]] = None, 
                 config_file: Optional[str] = None) -> logging.Logger:
    """
    Set up comprehensive logging infrastructure for the VAST As-Built Report Generator.
    
    This function configures both console and file logging with appropriate formatters,
    handlers, and security measures. It supports configuration via dictionary or YAML file.
    
    Args:
        config (Dict[str, Any], optional): Logging configuration dictionary
        config_file (str, optional): Path to YAML configuration file
        
    Returns:
        logging.Logger: Configured root logger instance
        
    Raises:
        Exception: If logging setup fails, falls back to basic configuration
    """
    try:
        # Load configuration
        if config is None:
            config = _load_logging_config(config_file)
        
        # Get logging configuration section
        log_config = config.get('logging', {})
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_config.get('level', 'INFO')))
        
        # Clear any existing handlers
        root_logger.handlers.clear()
        
        # Set up console handler with colors
        console_handler = _setup_console_handler(log_config)
        root_logger.addHandler(console_handler)
        
        # Set up file handler with rotation
        file_handler = _setup_file_handler(log_config)
        if file_handler:
            root_logger.addHandler(file_handler)
        
        # Add sensitive data filter to all handlers
        sensitive_filter = SensitiveDataFilter()
        for handler in root_logger.handlers:
            handler.addFilter(sensitive_filter)
        
        # Log successful initialization
        logger = logging.getLogger(__name__)
        logger.info("Logging infrastructure initialized successfully")
        logger.debug(f"Log level: {log_config.get('level', 'INFO')}")
        logger.debug(f"Console colors: {log_config.get('console_colors', {})}")
        logger.debug(f"File logging: {'enabled' if file_handler else 'disabled'}")
        
        return root_logger
        
    except Exception as e:
        # Fallback to basic logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler(sys.stdout)]
        )
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to set up advanced logging, using basic configuration: {e}")
        return logging.getLogger()


def _load_logging_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    Load logging configuration from YAML file or return default configuration.
    
    Args:
        config_file (str, optional): Path to configuration file
        
    Returns:
        Dict[str, Any]: Logging configuration dictionary
    """
    # Default configuration
    default_config = {
        'logging': {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file_path': 'logs/vast_report_generator.log',
            'rotation_size': 10485760,  # 10MB
            'backup_count': 5,
            'console_colors': {
                'DEBUG': 'cyan',
                'INFO': 'green',
                'WARNING': 'yellow',
                'ERROR': 'red',
                'CRITICAL': 'bold_red'
            }
        }
    }
    
    if config_file is None:
        config_file = 'config/config.yaml'
    
    try:
        config_path = Path(config_file)
        if config_path.exists():
            with open(config_path, 'r') as f:
                loaded_config = yaml.safe_load(f)
                # Merge with defaults
                if loaded_config and 'logging' in loaded_config:
                    default_config['logging'].update(loaded_config['logging'])
                return default_config
        else:
            return default_config
    except Exception as e:
        print(f"Warning: Failed to load config file {config_file}: {e}")
        return default_config


def _setup_console_handler(log_config: Dict[str, Any]) -> logging.Handler:
    """
    Set up colored console handler for development-friendly output.
    
    Args:
        log_config (Dict[str, Any]): Logging configuration
        
    Returns:
        logging.Handler: Configured console handler
    """
    console_handler = colorlog.StreamHandler(sys.stdout)
    
    # Get color configuration
    colors = log_config.get('console_colors', {
        'DEBUG': 'cyan',
        'INFO': 'green',
        'WARNING': 'yellow',
        'ERROR': 'red',
        'CRITICAL': 'bold_red'
    })
    
    # Create colored formatter
    color_formatter = ColoredFormatter(
        '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        log_colors=colors,
        reset=True,
        style='%'
    )
    
    console_handler.setFormatter(color_formatter)
    console_handler.setLevel(getattr(logging, log_config.get('level', 'INFO')))
    
    return console_handler


def _setup_file_handler(log_config: Dict[str, Any]) -> Optional[logging.Handler]:
    """
    Set up rotating file handler for persistent logging.
    
    Args:
        log_config (Dict[str, Any]): Logging configuration
        
    Returns:
        Optional[logging.Handler]: Configured file handler or None if setup fails
    """
    try:
        # Get file path and ensure directory exists
        file_path = log_config.get('file_path', 'logs/vast_report_generator.log')
        log_dir = Path(file_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=file_path,
            maxBytes=log_config.get('rotation_size', 10485760),  # 10MB
            backupCount=log_config.get('backup_count', 5),
            encoding='utf-8'
        )
        
        # Create detailed formatter for file output
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(getattr(logging, log_config.get('level', 'INFO')))
        
        return file_handler
        
    except Exception as e:
        print(f"Warning: Failed to set up file logging: {e}")
        return None


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module or component.
    
    This function provides a convenient way to get properly configured
    logger instances throughout the application.
    
    Args:
        name (str): Logger name, typically __name__ from the calling module
        
    Returns:
        logging.Logger: Configured logger instance
        
    Example:
        >>> from src.utils.logger import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("This is an info message")
    """
    return logging.getLogger(name)


def log_function_entry(func):
    """
    Decorator to automatically log function entry and exit.
    
    This decorator is useful for debugging and tracing execution flow
    through the application.
    
    Args:
        func: Function to be decorated
        
    Returns:
        Decorated function with entry/exit logging
        
    Example:
        >>> @log_function_entry
        >>> def my_function(arg1, arg2):
        >>>     return arg1 + arg2
    """
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"Entering {func.__name__} with args={args}, kwargs={kwargs}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func.__name__} with result={result}")
            return result
        except Exception as e:
            logger.error(f"Exception in {func.__name__}: {e}")
            raise
    return wrapper


# Module-level logger for this file
logger = get_logger(__name__)


if __name__ == "__main__":
    """
    Test the logging infrastructure when run as a standalone module.
    """
    # Set up logging
    setup_logging()
    
    # Test different log levels
    test_logger = get_logger("test_module")
    
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    test_logger.critical("This is a critical message")
    
    # Test sensitive data filtering
    test_logger.info("User login successful")  # Safe
    test_logger.info("Password verification failed")  # Should be filtered
    
    print("Logging test completed. Check console output and log file.")

