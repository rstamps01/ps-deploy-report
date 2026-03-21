#!/usr/bin/env python3
"""Standalone launcher for the VAST As-Built Reporter web UI."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
os.chdir(os.path.join(os.path.dirname(__file__), "src"))

from main import load_configuration, setup_logging
from app import create_flask_app
from utils.logger import enable_sse_logging

config = load_configuration()
setup_logging(config)
enable_sse_logging()
flask_app = create_flask_app(config)
flask_app.run(host="127.0.0.1", port=5173, threaded=True, use_reloader=False)
