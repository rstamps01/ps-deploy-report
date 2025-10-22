#!/usr/bin/env python3
"""
VAST As-Built Report Generator - Main CLI Application

This is the main entry point for the VAST As-Built Report Generator.
It provides a command-line interface for connecting to VAST clusters,
collecting data, and generating comprehensive as-built reports.

Features:
- Command-line argument parsing with validation
- Secure credential handling
- Complete workflow orchestration
- Enhanced data collection (80% automation)
- Professional error handling and logging
- Progress reporting and status updates

Author: Manus AI
Date: September 26, 2025
"""

import argparse
import getpass
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from api_handler import VastApiHandler, create_vast_api_handler
from data_extractor import VastDataExtractor, create_data_extractor
from report_builder import VastReportBuilder, create_report_builder
from utils.logger import get_logger, setup_logging


class VastReportGenerator:
    """
    Main VAST As-Built Report Generator application.

    This class orchestrates the complete workflow from API connection
    to report generation, providing a professional command-line interface
    for VAST Professional Services engineers.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the report generator.

        Args:
            config (Dict[str, Any], optional): Configuration dictionary
        """
        self.logger = get_logger(__name__)
        self.config = config or {}
        self.api_handler = None
        self.data_extractor = None
        self.report_builder = None

        self.logger.info("VAST As-Built Report Generator initialized")

    def run(self, args: argparse.Namespace) -> int:
        """
        Run the main application workflow.

        Args:
            args (argparse.Namespace): Parsed command-line arguments

        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
        try:
            self.logger.info("Starting VAST As-Built Report Generator")
            self.logger.info(f"Target cluster: {args.cluster_ip}")
            self.logger.info(f"Output directory: {args.output_dir}")

            # Step 1: Initialize components
            if not self._initialize_components(args):
                return 1

            # Step 2: Connect to VAST cluster
            if not self._connect_to_cluster(args):
                return 1

            # Step 3: Collect data
            raw_data = self._collect_data()
            if not raw_data:
                return 1

            # Step 4: Process data
            processed_data = self._process_data(raw_data)
            if not processed_data:
                return 1

            # Step 5: Generate reports
            if not self._generate_reports(processed_data, args):
                return 1

            # Step 6: Display summary
            self._display_summary(processed_data, args)

            self.logger.info("VAST As-Built Report Generator completed successfully")
            return 0

        except KeyboardInterrupt:
            self.logger.info("Operation cancelled by user")
            return 1
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return 1
        finally:
            self._cleanup()

    def _initialize_components(self, args: argparse.Namespace) -> bool:
        """
        Initialize API handler and data extractor components.

        Args:
            args (argparse.Namespace): Parsed command-line arguments

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Initializing components...")

            # Initialize data extractor
            self.data_extractor = create_data_extractor(self.config)
            self.logger.info("Data extractor initialized")

            # Initialize report builder
            self.report_builder = create_report_builder()
            self.logger.info("Report builder initialized")

            # API handler will be initialized when we have credentials
            self.logger.info("Components initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize components: {e}")
            return False

    def _connect_to_cluster(self, args: argparse.Namespace) -> bool:
        """
        Connect to the VAST cluster.

        Args:
            args (argparse.Namespace): Parsed command-line arguments

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Connecting to VAST cluster...")

            # Get credentials
            username, password, token = self._get_credentials(args)
            if not username and not password and not token:
                self.logger.error("Failed to obtain credentials")
                return False

            # Initialize API handler
            self.api_handler = create_vast_api_handler(
                cluster_ip=args.cluster_ip,
                username=username,
                password=password,
                token=token,
                config=self.config,
            )

            # Authenticate
            if not self.api_handler.authenticate():
                self.logger.error("Failed to authenticate with VAST cluster")
                return False

            self.logger.info("Successfully connected to VAST cluster")
            return True

        except Exception as e:
            self.logger.error(f"Failed to connect to cluster: {e}")
            return False

    def _get_credentials(
        self, args: argparse.Namespace
    ) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Get user credentials from various sources.

        Args:
            args (argparse.Namespace): Parsed command-line arguments

        Returns:
            tuple[Optional[str], Optional[str], Optional[str]]: Username, password, and token
        """
        try:
            # Check for API token first (highest priority)
            token = None

            # Try command-line token argument
            if args.token:
                token = args.token
                self.logger.info("Using API token from command-line argument")
                return None, None, token

            # Try environment variable for token
            token = os.getenv("VAST_TOKEN")
            if token:
                self.logger.info("Using API token from environment variable")
                return None, None, token

            # Fall back to username/password authentication
            # Try environment variables first
            username = os.getenv("VAST_USERNAME")
            password = os.getenv("VAST_PASSWORD")

            if username and password:
                self.logger.info("Using username/password from environment variables")
                return username, password, None

            # Try command-line arguments
            if args.username and args.password:
                self.logger.info("Using username/password from command-line arguments")
                return args.username, args.password, None

            # Prompt for credentials
            self.logger.info("Prompting for credentials...")
            auth_method = input(
                "Authentication method (1=token, 2=username/password) [2]: "
            ).strip()

            if auth_method == "1":
                token = getpass.getpass("VAST API Token: ")
                if not token:
                    self.logger.error("Token cannot be empty")
                    return None, None, None
                return None, None, token
            else:
                username = input("VAST Username: ").strip()
                if not username:
                    self.logger.error("Username cannot be empty")
                    return None, None, None

                password = getpass.getpass("VAST Password: ")
                if not password:
                    self.logger.error("Password cannot be empty")
                    return None, None, None

                return username, password, None

        except Exception as e:
            self.logger.error(f"Failed to get credentials: {e}")
            return None, None, None

    def _collect_data(self) -> Optional[Dict[str, Any]]:
        """
        Collect data from the VAST cluster.

        Returns:
            Optional[Dict[str, Any]]: Raw cluster data or None if failed
        """
        try:
            self.logger.info("Collecting data from VAST cluster...")

            # Collect all data
            raw_data = self.api_handler.get_all_data()
            if not raw_data:
                self.logger.error("Failed to collect data from cluster")
                return None

            # Log collection summary
            cluster_info = raw_data.get("cluster_info", {})
            enhanced_features = raw_data.get("enhanced_features", {})

            self.logger.info(
                f"Data collection completed for cluster: {cluster_info.get('name', 'Unknown')}"
            )
            self.logger.info(
                f"Cluster version: {cluster_info.get('version', 'Unknown')}"
            )
            self.logger.info(
                f"Enhanced features enabled: {enhanced_features.get('rack_height_supported', False)}"
            )
            self.logger.info(
                f"PSNT available: {enhanced_features.get('psnt_supported', False)}"
            )

            return raw_data

        except Exception as e:
            self.logger.error(f"Failed to collect data: {e}")
            return None

    def _process_data(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Process raw data into report-ready format.

        Args:
            raw_data (Dict[str, Any]): Raw cluster data

        Returns:
            Optional[Dict[str, Any]]: Processed report data or None if failed
        """
        try:
            self.logger.info("Processing collected data...")

            # Process data
            processed_data = self.data_extractor.extract_all_data(raw_data)
            if not processed_data:
                self.logger.error("Failed to process data")
                return None

            # Log processing summary
            metadata = processed_data.get("metadata", {})
            overall_completeness = metadata.get("overall_completeness", 0.0)

            self.logger.info(f"Data processing completed")
            self.logger.info(f"Overall data completeness: {overall_completeness:.1%}")

            # Log section status
            sections = processed_data.get("sections", {})
            for section_name, section_data in sections.items():
                status = section_data.get("status", "unknown")
                completeness = section_data.get("completeness", 0.0)
                self.logger.info(f"  {section_name}: {status} ({completeness:.1%})")

            return processed_data

        except Exception as e:
            self.logger.error(f"Failed to process data: {e}")
            return None

    def _generate_reports(
        self, processed_data: Dict[str, Any], args: argparse.Namespace
    ) -> bool:
        """
        Generate JSON and PDF reports.

        Args:
            processed_data (Dict[str, Any]): Processed report data
            args (argparse.Namespace): Parsed command-line arguments

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info("Generating reports...")

            # Ensure output directory exists
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate timestamp for filenames
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cluster_name = processed_data.get("cluster_summary", {}).get(
                "name", "unknown"
            )

            # Generate JSON report
            json_filename = f"vast_data_{cluster_name}_{timestamp}.json"
            json_path = output_dir / json_filename

            if not self.data_extractor.save_processed_data(
                processed_data, str(json_path)
            ):
                self.logger.error("Failed to save JSON report")
                return False

            self.logger.info(f"JSON report saved: {json_path}")

            # Generate PDF report
            pdf_filename = f"vast_asbuilt_report_{cluster_name}_{timestamp}.pdf"
            pdf_path = output_dir / pdf_filename

            if not self.report_builder.generate_pdf_report(
                processed_data, str(pdf_path)
            ):
                self.logger.error("Failed to generate PDF report")
                return False

            self.logger.info(f"PDF report generated: {pdf_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to generate reports: {e}")
            return False

    def _display_summary(
        self, processed_data: Dict[str, Any], args: argparse.Namespace
    ) -> None:
        """
        Display execution summary.

        Args:
            processed_data (Dict[str, Any]): Processed report data
            args (argparse.Namespace): Parsed command-line arguments
        """
        try:
            print("\n" + "=" * 70)
            print("VAST AS-BUILT REPORT GENERATOR - EXECUTION SUMMARY")
            print("=" * 70)

            # Cluster information
            cluster_info = processed_data.get("cluster_summary", {})
            print(f"Cluster Name: {cluster_info.get('name', 'Unknown')}")
            print(f"Cluster Version: {cluster_info.get('version', 'Unknown')}")
            print(f"Cluster State: {cluster_info.get('state', 'Unknown')}")
            print(f"PSNT: {cluster_info.get('psnt', 'Not Available')}")

            # Hardware inventory
            hardware = processed_data.get("hardware_inventory", {})
            print(f"Total Nodes: {hardware.get('total_nodes', 0)}")
            print(f"CNodes: {len(hardware.get('cnodes', []))}")
            print(f"DNodes: {len(hardware.get('dnodes', []))}")
            print(
                f"Rack Positions Available: {hardware.get('rack_positions_available', False)}"
            )

            # Data completeness
            metadata = processed_data.get("metadata", {})
            overall_completeness = metadata.get("overall_completeness", 0.0)
            print(f"Overall Data Completeness: {overall_completeness:.1%}")

            # Enhanced features
            enhanced_features = metadata.get("enhanced_features", {})
            print(
                f"Enhanced Features Enabled: {enhanced_features.get('rack_height_supported', False)}"
            )

            # Output files
            print(f"\nOutput Directory: {args.output_dir}")
            print(f"JSON Report: Generated successfully")
            print(f"PDF Report: Generated successfully")

            print("\n" + "=" * 70)
            print("REPORT GENERATION COMPLETED SUCCESSFULLY")
            print("=" * 70)

        except Exception as e:
            self.logger.error(f"Failed to display summary: {e}")

    def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.api_handler:
                self.api_handler.close()
                self.logger.info("API handler closed")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


def create_argument_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        argparse.ArgumentParser: Configured argument parser
    """
    parser = argparse.ArgumentParser(
        description="VAST As-Built Report Generator - Automated cluster documentation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage with interactive credentials
  python main.py --cluster 192.168.1.100 --output ./reports

  # Using API token (recommended for automation)
  python main.py --cluster 192.168.1.100 --token YOUR_API_TOKEN --output ./reports

  # Using environment variables for credentials
  export VAST_USERNAME=admin
  export VAST_PASSWORD=password
  python main.py --cluster 192.168.1.100 --output ./reports

  # Using command-line credentials (not recommended for production)
  python main.py --cluster 192.168.1.100 --username admin --password password --output ./reports

  # Verbose output for debugging
  python main.py --cluster 192.168.1.100 --output ./reports --verbose
        """,
    )

    # Required arguments
    parser.add_argument(
        "--cluster",
        "--cluster-ip",
        dest="cluster_ip",
        required=True,
        help="IP address of the VAST Management Service",
    )

    parser.add_argument(
        "--output",
        "--output-dir",
        dest="output_dir",
        required=True,
        help="Output directory for generated reports",
    )

    # Optional arguments
    parser.add_argument(
        "--username", "-u", help="VAST username (will prompt if not provided)"
    )

    parser.add_argument(
        "--password", "-p", help="VAST password (will prompt if not provided)"
    )

    parser.add_argument(
        "--token",
        "-t",
        help="VAST API token (alternative to username/password authentication)",
    )

    parser.add_argument(
        "--config",
        "-c",
        help="Path to configuration file (default: config/config.yaml)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    parser.add_argument(
        "--version", action="version", version="VAST As-Built Report Generator 1.0.0"
    )

    return parser


def load_configuration(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from file.

    Args:
        config_path (str, optional): Path to configuration file

    Returns:
        Dict[str, Any]: Configuration dictionary
    """
    import yaml

    if config_path is None:
        config_path = "config/config.yaml"

    try:
        config_file = Path(config_path)
        if config_file.exists():
            with open(config_file, "r") as f:
                config = yaml.safe_load(f)
            return config or {}
        else:
            print(
                f"Warning: Configuration file {config_path} not found, using defaults"
            )
            return {}
    except Exception as e:
        print(f"Warning: Failed to load configuration: {e}")
        return {}


def main() -> int:
    """
    Main entry point for the application.

    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    try:
        # Parse command-line arguments
        parser = create_argument_parser()
        args = parser.parse_args()

        # Load configuration
        config = load_configuration(args.config)

        # Set up logging
        log_level = "DEBUG" if args.verbose else "INFO"
        if "logging" not in config:
            config["logging"] = {}
        config["logging"]["level"] = log_level

        setup_logging(config)
        logger = get_logger(__name__)

        # Validate arguments
        if not args.cluster_ip:
            logger.error("Cluster IP address is required")
            return 1

        if not args.output_dir:
            logger.error("Output directory is required")
            return 1

        # Create and run application
        app = VastReportGenerator(config)
        return app.run(args)

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 1
    except Exception as e:
        print(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
