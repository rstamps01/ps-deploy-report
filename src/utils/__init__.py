"""
VAST As-Built Report Generator - Utilities Package

This package contains utility modules for the VAST As-Built Report Generator,
including logging infrastructure, configuration management, and helper functions.
"""

import sys
from pathlib import Path

from .logger import setup_logging, get_logger


def get_bundle_dir() -> Path:
    """Return the root directory containing bundled assets.

    In a PyInstaller frozen build this is ``sys._MEIPASS`` (the read-only
    directory where bundled data files are extracted).  In a normal dev
    environment it is the project root (one level above ``src/``).
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", ""))
    return Path(__file__).resolve().parent.parent.parent


def get_data_dir() -> Path:
    """Return the writable data directory for user files (reports, config, profiles).

    In a PyInstaller frozen build this is next to the executable (or next to
    the ``.app`` bundle on macOS).  In dev mode it equals :func:`get_bundle_dir`.
    """
    if getattr(sys, "frozen", False):
        app_exe = Path(sys.executable)
        if app_exe.parent.name == "MacOS":
            return app_exe.parent.parent.parent.parent
        return app_exe.parent
    return get_bundle_dir()


__all__ = ["setup_logging", "get_logger", "get_bundle_dir", "get_data_dir"]
