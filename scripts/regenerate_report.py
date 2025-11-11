#!/usr/bin/env python3
"""
VAST As-Built Report Generator - Report Regeneration Utility

This utility script allows you to regenerate PDF reports from existing JSON data files.
This is useful for working on report formatting without needing cluster access.

Usage:
    python scripts/regenerate_report.py <json_file> [output_file]

Examples:
    # Regenerate from latest JSON file
    python scripts/regenerate_report.py output/vast_data_LAMBDA-VAST-SLC-02_20251106_122547.json

    # Specify custom output file
    python scripts/regenerate_report.py output/vast_data_LAMBDA-VAST-SLC-02_20251106_122547.json output/test_report.pdf

Author: Manus AI
Date: November 6, 2025
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from report_builder import create_report_builder
from utils.logger import get_logger, setup_logging


def load_json_data(json_path: Path) -> Dict[str, Any]:
    """
    Load processed data from JSON file.

    Args:
        json_path (Path): Path to JSON file

    Returns:
        Dict[str, Any]: Processed report data

    Raises:
        FileNotFoundError: If JSON file doesn't exist
        json.JSONDecodeError: If JSON file is invalid
    """
    if not json_path.exists():
        raise FileNotFoundError(f"JSON file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def regenerate_report(
    json_path: Path, output_path: Path, logger
) -> bool:
    """
    Regenerate PDF report from JSON data.

    Args:
        json_path (Path): Path to JSON data file
        output_path (Path): Path for output PDF file
        logger: Logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load JSON data
        logger.info(f"Loading data from: {json_path}")
        processed_data = load_json_data(json_path)

        # Get cluster name for logging
        cluster_name = processed_data.get("cluster_summary", {}).get("name", "unknown")
        logger.info(f"Loaded data for cluster: {cluster_name}")

        # Initialize report builder
        logger.info("Initializing report builder...")
        report_builder = create_report_builder()

        # Generate PDF report
        logger.info(f"Generating PDF report: {output_path}")
        success = report_builder.generate_pdf_report(processed_data, str(output_path))

        if success:
            logger.info(f"✓ Report successfully generated: {output_path}")
            return True
        else:
            logger.error("✗ Failed to generate report")
            return False

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return False
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON file: {e}")
        return False
    except Exception as e:
        logger.error(f"Error regenerating report: {e}", exc_info=True)
        return False


def main():
    """Main entry point for the regeneration utility."""
    parser = argparse.ArgumentParser(
        description="Regenerate PDF report from existing JSON data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate from JSON file (uses default output name)
  python scripts/regenerate_report.py output/vast_data_LAMBDA-VAST-SLC-02_20251106_122547.json

  # Specify custom output file
  python scripts/regenerate_report.py output/vast_data_LAMBDA-VAST-SLC-02_20251106_122547.json output/test_report.pdf

  # Use latest JSON file in output directory
  python scripts/regenerate_report.py output/vast_data_LAMBDA-VAST-SLC-02_20251106_122547.json
        """,
    )

    parser.add_argument(
        "json_file",
        type=str,
        help="Path to JSON data file (e.g., output/vast_data_CLUSTER_TIMESTAMP.json)",
    )

    parser.add_argument(
        "output_file",
        type=str,
        nargs="?",
        default=None,
        help="Optional output PDF file path (default: generates name from JSON file)",
    )

    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Output directory for generated reports (default: output)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()

    # Setup logging
    config = {"logging": {"level": args.log_level}}
    setup_logging(config)
    logger = get_logger(__name__)

    # Resolve paths
    json_path = Path(args.json_file).resolve()
    output_dir = Path(args.output_dir)

    # Determine output path
    if args.output_file:
        output_path = Path(args.output_file).resolve()
    else:
        # Generate output filename from JSON filename
        json_stem = json_path.stem  # e.g., "vast_data_LAMBDA-VAST-SLC-02_20251106_122547"
        # Replace "vast_data" with "vast_asbuilt_report"
        pdf_stem = json_stem.replace("vast_data_", "vast_asbuilt_report_")
        output_path = output_dir / f"{pdf_stem}.pdf"

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 60)
    logger.info("VAST As-Built Report Regeneration Utility")
    logger.info("=" * 60)
    logger.info(f"JSON file: {json_path}")
    logger.info(f"Output file: {output_path}")
    logger.info("")

    # Regenerate report
    success = regenerate_report(json_path, output_path, logger)

    if success:
        logger.info("")
        logger.info("=" * 60)
        logger.info("✓ Report regeneration completed successfully!")
        logger.info("=" * 60)
        sys.exit(0)
    else:
        logger.error("")
        logger.error("=" * 60)
        logger.error("✗ Report regeneration failed!")
        logger.error("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
