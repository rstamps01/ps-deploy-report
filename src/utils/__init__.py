"""
VAST As-Built Report Generator - Utilities Package

This package contains utility modules for the VAST As-Built Report Generator,
including logging infrastructure, configuration management, and helper functions.
"""

from .logger import setup_logging, get_logger

__all__ = ['setup_logging', 'get_logger']

