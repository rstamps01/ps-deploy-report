#!/usr/bin/env python3
"""
Curl Command Tester for VAST API

This script tests individual curl commands from the Excel spreadsheet
to validate API responses and troubleshoot issues.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


def test_curl_command(curl_command: str, description: str = "") -> Dict[str, Any]:
    """Test a single curl command and return results."""
    print(f"\n🧪 Testing: {description}")
    print(f"Command: {curl_command}")
    print("-" * 80)

    try:
        # Run the curl command
        result = subprocess.run(
            curl_command, shell=True, capture_output=True, text=True, timeout=30
        )

        if result.returncode == 0:
            print("✅ SUCCESS")
            print(f"Output: {result.stdout.strip()}")

            # Try to parse as CSV if it looks like CSV
            if "," in result.stdout:
                csv_data = result.stdout.strip().split("\n")
                print(f"CSV Rows: {len(csv_data)}")
                for i, row in enumerate(csv_data[:3]):  # Show first 3 rows
                    print(f"  Row {i+1}: {row}")
                if len(csv_data) > 3:
                    print(f"  ... and {len(csv_data) - 3} more rows")

            return {
                "status": "SUCCESS",
                "return_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "description": description,
            }
        else:
            print("❌ FAILED")
            print(f"Return code: {result.returncode}")
            print(f"Error: {result.stderr.strip()}")
            print(f"Output: {result.stdout.strip()}")

            return {
                "status": "FAILED",
                "return_code": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "description": description,
            }

    except subprocess.TimeoutExpired:
        print("⏰ TIMEOUT")
        return {
            "status": "TIMEOUT",
            "return_code": -1,
            "stdout": "",
            "stderr": "Command timed out after 30 seconds",
            "description": description,
        }
    except Exception as e:
        print(f"💥 ERROR: {e}")
        return {
            "status": "ERROR",
            "return_code": -1,
            "stdout": "",
            "stderr": str(e),
            "description": description,
        }


def test_all_commands_from_excel(excel_file: str) -> List[Dict[str, Any]]:
    """Test all curl commands from the Excel file."""
    print("🔍 Loading curl commands from Excel file...")

    try:
        # Read the curl commands sheet
        df = pd.read_excel(excel_file, sheet_name="Curl_Commands")

        results = []

        for index, row in df.iterrows():
            section = row["Section"]
            curl_command = row["Curl_Command"]
            api_endpoint = row["API_Endpoint"]
            notes = row["Notes"]

            description = f"{section} ({api_endpoint})"

            result = test_curl_command(curl_command, description)
            result["section"] = section
            result["api_endpoint"] = api_endpoint
            result["notes"] = notes

            results.append(result)

        return results

    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        return []


def test_individual_command(section: str, curl_command: str) -> Dict[str, Any]:
    """Test a single curl command by section name."""
    return test_curl_command(curl_command, section)


def generate_test_report(
    results: List[Dict[str, Any]], output_file: str = "curl_test_report.txt"
) -> None:
    """Generate a test report from the results."""
    print(f"\n📊 Generating test report: {output_file}")

    try:
        with open(output_file, "w") as f:
            f.write("VAST API Curl Command Test Report\n")
            f.write("=" * 50 + "\n\n")

            # Summary
            total_tests = len(results)
            successful_tests = len([r for r in results if r["status"] == "SUCCESS"])
            failed_tests = len([r for r in results if r["status"] == "FAILED"])
            error_tests = len(
                [r for r in results if r["status"] in ["ERROR", "TIMEOUT"]]
            )

            f.write(f"SUMMARY:\n")
            f.write(f"  Total Tests: {total_tests}\n")
            f.write(f"  Successful: {successful_tests}\n")
            f.write(f"  Failed: {failed_tests}\n")
            f.write(f"  Errors/Timeouts: {error_tests}\n")
            f.write(f"  Success Rate: {(successful_tests/total_tests)*100:.1f}%\n\n")

            # Detailed results
            f.write("DETAILED RESULTS:\n")
            f.write("-" * 50 + "\n\n")

            for result in results:
                f.write(f"Section: {result['section']}\n")
                f.write(f"Status: {result['status']}\n")
                f.write(f"Description: {result['description']}\n")
                f.write(f"API Endpoint: {result['api_endpoint']}\n")

                if result["status"] == "SUCCESS":
                    f.write(f"Output: {result['stdout']}\n")
                else:
                    f.write(f"Error: {result['stderr']}\n")
                    f.write(f"Output: {result['stdout']}\n")

                f.write(f"Notes: {result['notes']}\n")
                f.write("-" * 30 + "\n\n")

        print(f"✅ Test report saved: {output_file}")

    except Exception as e:
        print(f"❌ Error generating test report: {e}")


def main():
    """Main function for curl command testing."""
    if len(sys.argv) < 2:
        print("Usage: python curl_command_tester.py <excel_file> [section_name]")
        print("Examples:")
        print("  python curl_command_tester.py vast_data_summary_20250929_123456.xlsx")
        print(
            "  python curl_command_tester.py vast_data_summary_20250929_123456.xlsx 'Cluster Basic Info'"
        )
        sys.exit(1)

    excel_file = sys.argv[1]
    section_name = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(excel_file):
        print(f"❌ Excel file not found: {excel_file}")
        sys.exit(1)

    if section_name:
        # Test individual section
        print(f"🎯 Testing individual section: {section_name}")

        try:
            df = pd.read_excel(excel_file, sheet_name="Curl_Commands")
            section_row = df[df["Section"] == section_name]

            if section_row.empty:
                print(f"❌ Section '{section_name}' not found in Excel file")
                sys.exit(1)

            curl_command = section_row.iloc[0]["Curl_Command"]
            api_endpoint = section_row.iloc[0]["API_Endpoint"]
            notes = section_row.iloc[0]["Notes"]

            result = test_individual_command(section_name, curl_command)
            result["api_endpoint"] = api_endpoint
            result["notes"] = notes

            # Generate individual test report
            report_file = (
                f"curl_test_{section_name.replace(' ', '_').lower()}_report.txt"
            )
            generate_test_report([result], report_file)

        except Exception as e:
            print(f"❌ Error testing individual section: {e}")
            sys.exit(1)
    else:
        # Test all commands
        print("🚀 Testing all curl commands from Excel file...")

        results = test_all_commands_from_excel(excel_file)

        if results:
            # Generate comprehensive test report
            report_file = (
                f"curl_test_report_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )
            generate_test_report(results, report_file)

            # Print summary
            successful = len([r for r in results if r["status"] == "SUCCESS"])
            total = len(results)
            print(
                f"\n📈 Test Summary: {successful}/{total} commands successful ({(successful/total)*100:.1f}%)"
            )

            if successful < total:
                print("\n❌ Failed commands:")
                for result in results:
                    if result["status"] != "SUCCESS":
                        print(f"  - {result['section']}: {result['status']}")
        else:
            print("❌ No commands found to test")
            sys.exit(1)


if __name__ == "__main__":
    main()
