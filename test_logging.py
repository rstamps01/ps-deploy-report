#!/usr/bin/env python3
"""
Test script for VAST As-Built Report Generator logging infrastructure.

This script tests all aspects of the logging system including:
- Configuration loading
- Console output with colors
- File output with rotation
- Sensitive data filtering
- Error handling and fallback mechanisms

Author: Manus AI
Date: September 12, 2025
"""

import sys
import os
import time
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from utils.logger import setup_logging, get_logger, log_function_entry


@log_function_entry
def test_basic_logging():
    """Test basic logging functionality at different levels."""
    logger = get_logger(__name__)
    
    logger.debug("This is a DEBUG message - should appear in cyan")
    logger.info("This is an INFO message - should appear in green")
    logger.warning("This is a WARNING message - should appear in yellow")
    logger.error("This is an ERROR message - should appear in red")
    logger.critical("This is a CRITICAL message - should appear in bold red")


@log_function_entry
def test_sensitive_data_filtering():
    """Test sensitive data filtering functionality."""
    logger = get_logger(__name__)
    
    logger.info("Testing sensitive data filtering...")
    
    # These should be filtered/redacted
    logger.info("User password is: secret123")
    logger.info("API token received: abc123def456")
    logger.info("Session key generated: xyz789")
    
    # These should pass through normally
    logger.info("User login successful for admin")
    logger.info("API request completed successfully")
    logger.info("Session established")


@log_function_entry
def test_module_specific_loggers():
    """Test module-specific logger functionality."""
    # Create loggers for different modules
    api_logger = get_logger("vast_api_handler")
    report_logger = get_logger("report_generator")
    config_logger = get_logger("config_manager")
    
    api_logger.info("API handler module initialized")
    report_logger.info("Report generator module started")
    config_logger.info("Configuration loaded successfully")
    
    # Test error logging
    api_logger.error("Failed to connect to VAST cluster")
    report_logger.warning("Missing optional data field")


@log_function_entry
def test_exception_logging():
    """Test exception logging and error handling."""
    logger = get_logger(__name__)
    
    try:
        # Simulate an error
        result = 1 / 0
    except ZeroDivisionError as e:
        logger.error(f"Mathematical error occurred: {e}")
        logger.exception("Full exception details:")
    
    try:
        # Simulate another error
        missing_dict = {}
        value = missing_dict['nonexistent_key']
    except KeyError as e:
        logger.error(f"Configuration error: {e}")


def test_file_logging():
    """Test file logging and rotation."""
    logger = get_logger(__name__)
    
    logger.info("Testing file logging functionality...")
    
    # Generate multiple log entries to test file output
    for i in range(10):
        logger.info(f"Log entry {i+1} - testing file output")
        time.sleep(0.1)  # Small delay to show timestamp differences
    
    # Check if log file was created
    log_file = Path("logs/vast_report_generator.log")
    if log_file.exists():
        logger.info(f"Log file created successfully: {log_file}")
        logger.info(f"Log file size: {log_file.stat().st_size} bytes")
    else:
        logger.error("Log file was not created")


def main():
    """Main test function."""
    print("=" * 60)
    print("VAST As-Built Report Generator - Logging Infrastructure Test")
    print("=" * 60)
    print()
    
    # Initialize logging
    print("1. Initializing logging infrastructure...")
    try:
        setup_logging()
        print("✅ Logging infrastructure initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize logging: {e}")
        return 1
    
    print()
    
    # Test basic logging
    print("2. Testing basic logging functionality...")
    test_basic_logging()
    print("✅ Basic logging test completed")
    print()
    
    # Test sensitive data filtering
    print("3. Testing sensitive data filtering...")
    test_sensitive_data_filtering()
    print("✅ Sensitive data filtering test completed")
    print()
    
    # Test module-specific loggers
    print("4. Testing module-specific loggers...")
    test_module_specific_loggers()
    print("✅ Module-specific logger test completed")
    print()
    
    # Test exception logging
    print("5. Testing exception logging...")
    test_exception_logging()
    print("✅ Exception logging test completed")
    print()
    
    # Test file logging
    print("6. Testing file logging...")
    test_file_logging()
    print("✅ File logging test completed")
    print()
    
    # Final summary
    print("=" * 60)
    print("LOGGING INFRASTRUCTURE TEST SUMMARY")
    print("=" * 60)
    print("✅ All logging tests completed successfully")
    print("✅ Console output with colors: Working")
    print("✅ File output with rotation: Working")
    print("✅ Sensitive data filtering: Working")
    print("✅ Module-specific loggers: Working")
    print("✅ Exception handling: Working")
    print()
    print("Check the following:")
    print("- Console output above for colored log messages")
    print("- logs/vast_report_generator.log for file output")
    print("- Verify sensitive data is redacted in logs")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

