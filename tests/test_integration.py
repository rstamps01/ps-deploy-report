"""
Integration tests for the VAST As-Built Report Generator pipeline.

Tests the full flow: raw API data -> VastDataExtractor -> VastReportBuilder,
verifying data consistency, graceful degradation, and end-to-end report generation.
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_extractor import VastDataExtractor  # noqa: E402
from report_builder import VastReportBuilder  # noqa: E402


@pytest.mark.integration
class TestFullPipelineIntegration(unittest.TestCase):
    """Test the complete data extraction -> report generation pipeline."""

    def setUp(self):
        self.extractor = VastDataExtractor()
        self.builder = VastReportBuilder()
        self.raw_data = self._make_raw_data()
        self.tmpdir = tempfile.mkdtemp(prefix="vast_integration_")

    def _make_raw_data(self):
        return {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {
                "rack_height_supported": True,
                "psnt_supported": True,
            },
            "cluster_info": {
                "name": "Integration-Test-Cluster",
                "guid": "integ-guid-001",
                "version": "5.3.0",
                "state": "active",
                "license": "Enterprise",
                "psnt": "PSNT-INTEG-001",
            },
            "racks": [],
            "hardware": {
                "cnodes": [
                    {
                        "id": 1,
                        "name": "cnode-1",
                        "model": "C200",
                        "serial_number": "CN001",
                        "status": "active",
                        "ip": "10.0.0.1",
                        "mgmt_ip": "10.0.1.1",
                    },
                    {
                        "id": 2,
                        "name": "cnode-2",
                        "model": "C200",
                        "serial_number": "CN002",
                        "status": "active",
                        "ip": "10.0.0.2",
                        "mgmt_ip": "10.0.1.2",
                    },
                ],
                "dnodes": [
                    {
                        "id": 1,
                        "name": "dnode-1",
                        "model": "D200",
                        "serial_number": "DN001",
                        "status": "active",
                        "ip": "10.0.0.11",
                    },
                ],
                "cboxes": [
                    {"id": 1, "name": "cbox-1", "serial_number": "CB001", "model": "CBox", "status": "active"},
                    {
                        "id": 2,
                        "name": "cbox-2",
                        "serial_number": "SERIAL123",
                        "model": "dell_turin_cbox",
                        "status": "active",
                    },
                ],
                "dboxes": [
                    {"id": 1, "name": "dbox-1", "serial_number": "DB001", "model": "DBox", "status": "active"},
                ],
                "eboxes": [
                    {
                        "id": 1,
                        "name": "ebox-1",
                        "state": "active",
                        "rack_name": "R1",
                        "rack_unit": "1",
                    },
                ],
            },
            "network": {
                "dns": {"servers": ["8.8.8.8", "8.8.4.4"], "search_domains": ["test.local"], "enabled": True},
                "ntp": {"servers": ["pool.ntp.org"], "enabled": True},
                "vippools": {"pools": [{"name": "default", "vips": ["10.0.2.1", "10.0.2.2"]}]},
            },
            "cluster_network": {},
            "cnodes_network": {},
            "dnodes_network": {},
            "logical": {
                "tenants": [{"name": "default", "id": 1, "state": "active"}],
                "views": [{"name": "main_view", "path": "/", "state": "active"}],
                "viewpolicies": [{"name": "default_policy", "type": "basic", "state": "active"}],
            },
            "security": {
                "activedirectory": {"enabled": False, "domain": "", "servers": []},
                "ldap": {"enabled": False},
                "nis": {"enabled": False},
            },
            "data_protection": {
                "snapprograms": [{"name": "daily_snap", "schedule": "daily", "enabled": True}],
                "protectionpolicies": [
                    {"name": "retention_30d", "type": "retention", "retention": "30d", "enabled": True}
                ],
            },
            "switch_inventory": [],
            "switch_ports": [],
            "performance_metrics": {},
            "licensing_info": {},
            "monitoring_config": {},
            "customer_integration": {},
            "deployment_timeline": {},
            "future_recommendations": {},
        }

    def test_extract_all_data_produces_valid_structure(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        self.assertIn("metadata", processed)
        self.assertIn("cluster_summary", processed)
        self.assertIn("hardware_inventory", processed)
        self.assertIn("sections", processed)

    def test_extracted_metadata_has_completeness(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        self.assertIn("overall_completeness", processed["metadata"])
        self.assertGreater(processed["metadata"]["overall_completeness"], 0)

    def test_cluster_summary_preserves_name(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        self.assertEqual(processed["cluster_summary"]["name"], "Integration-Test-Cluster")

    def test_hardware_inventory_counts_match(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        hw = processed["hardware_inventory"]
        self.assertEqual(len(hw.get("cnodes", [])), 2)
        self.assertEqual(len(hw.get("dnodes", [])), 1)

    def test_all_sections_present(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        expected_sections = [
            "network_configuration",
            "logical_configuration",
            "security_configuration",
            "data_protection_configuration",
        ]
        for section in expected_sections:
            self.assertIn(section, processed["sections"], f"Missing section: {section}")

    def test_full_pipeline_generates_pdf(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        output_path = os.path.join(self.tmpdir, "test_report.pdf")
        result = self.builder.generate_pdf_report(processed, output_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0)

    def test_full_pipeline_pdf_starts_with_magic_bytes(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        output_path = os.path.join(self.tmpdir, "test_report.pdf")
        self.builder.generate_pdf_report(processed, output_path)
        with open(output_path, "rb") as f:
            magic = f.read(5)
        self.assertEqual(magic, b"%PDF-")

    def test_report_content_contains_ebox_and_model_serial(self):
        """TSE-5: EBox + dell_turin_cbox + serial in data; assert intermediate and PDF generation."""
        processed = self.extractor.extract_all_data(self.raw_data)
        hw = processed.get("hardware_inventory", {})
        eboxes = hw.get("eboxes") or {}
        cboxes = hw.get("cboxes") or {}
        self.assertGreater(len(eboxes), 0, "Processed data should include EBox(es)")
        self.assertGreater(len(cboxes), 0, "Processed data should include CBox(es)")
        cbox_models = [c.get("model") or c.get("hardware_type") or "" for c in cboxes.values()]
        self.assertIn("dell_turin_cbox", cbox_models, "Processed data should include dell_turin_cbox model")
        serials = [c.get("serial_number", "") for c in cboxes.values()]
        self.assertIn("SERIAL123", serials, "Processed data should include expected serial")
        output_path = os.path.join(self.tmpdir, "tse5_report.pdf")
        result = self.builder.generate_pdf_report(processed, output_path)
        self.assertTrue(result, "PDF report should be generated")
        self.assertTrue(os.path.exists(output_path))
        self.assertGreater(os.path.getsize(output_path), 0, "Generated PDF should be non-empty")

    def test_save_processed_data_produces_valid_json(self):
        processed = self.extractor.extract_all_data(self.raw_data)
        json_path = os.path.join(self.tmpdir, "test_data.json")
        result = self.extractor.save_processed_data(processed, json_path)
        self.assertTrue(result)
        with open(json_path, encoding="utf-8") as f:
            loaded = json.load(f)
        self.assertEqual(loaded["cluster_summary"]["name"], "Integration-Test-Cluster")


@pytest.mark.integration
class TestGracefulDegradation(unittest.TestCase):
    """Verify the pipeline handles missing or partial data without crashing."""

    def setUp(self):
        self.extractor = VastDataExtractor()
        self.builder = VastReportBuilder()
        self.tmpdir = tempfile.mkdtemp(prefix="vast_degrade_")

    def test_missing_network_section(self):
        raw = {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {"rack_height_supported": False, "psnt_supported": False},
            "cluster_info": {"name": "Degraded", "guid": "d-001", "version": "5.3.0", "state": "active"},
            "hardware": {"cnodes": [], "dnodes": [], "cboxes": [], "dboxes": []},
            "logical": {"tenants": [], "views": [], "viewpolicies": []},
            "security": {"activedirectory": {"enabled": False}, "ldap": {"enabled": False}},
            "data_protection": {"snapprograms": [], "protectionpolicies": []},
        }
        processed = self.extractor.extract_all_data(raw)
        self.assertIn("sections", processed)

    def test_empty_hardware_still_generates_pdf(self):
        raw = {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {"rack_height_supported": False, "psnt_supported": False},
            "cluster_info": {"name": "EmptyHW", "guid": "e-001", "version": "5.3.0", "state": "active"},
            "hardware": {"cnodes": [], "dnodes": [], "cboxes": [], "dboxes": []},
            "logical": {"tenants": [], "views": [], "viewpolicies": []},
            "security": {"activedirectory": {"enabled": False}, "ldap": {"enabled": False}},
            "data_protection": {"snapprograms": [], "protectionpolicies": []},
        }
        processed = self.extractor.extract_all_data(raw)
        output_path = os.path.join(self.tmpdir, "empty_hw_report.pdf")
        result = self.builder.generate_pdf_report(processed, output_path)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(output_path))

    def test_minimal_cluster_info_still_extracts(self):
        raw = {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {"rack_height_supported": False, "psnt_supported": False},
            "cluster_info": {"name": "Minimal"},
            "hardware": {"cnodes": [], "dnodes": [], "cboxes": [], "dboxes": []},
        }
        processed = self.extractor.extract_all_data(raw)
        self.assertEqual(processed["cluster_summary"]["name"], "Minimal")


@pytest.mark.integration
class TestDataConsistency(unittest.TestCase):
    """Verify data flows through the pipeline without corruption."""

    def setUp(self):
        self.extractor = VastDataExtractor()
        self.tmpdir = tempfile.mkdtemp(prefix="vast_consistency_")

    def test_json_roundtrip_preserves_data(self):
        raw = {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {"rack_height_supported": True, "psnt_supported": True},
            "cluster_info": {
                "name": "Roundtrip-Test",
                "guid": "rt-001",
                "version": "5.3.0",
                "state": "active",
                "license": "Enterprise",
                "psnt": "PSNT-RT-001",
            },
            "hardware": {
                "cnodes": [{"id": 1, "name": "cn1", "model": "C200", "serial_number": "S1", "status": "active"}],
                "dnodes": [],
                "cboxes": [],
                "dboxes": [],
            },
            "network": {
                "dns": {"servers": ["1.1.1.1"], "search_domains": ["rt.local"], "enabled": True},
                "ntp": {"servers": ["time.google.com"], "enabled": True},
                "vippools": {"pools": []},
            },
            "logical": {"tenants": [{"name": "t1", "id": 1, "state": "active"}], "views": [], "viewpolicies": []},
            "security": {"activedirectory": {"enabled": False}, "ldap": {"enabled": False}},
            "data_protection": {"snapprograms": [], "protectionpolicies": []},
        }
        processed = self.extractor.extract_all_data(raw)
        json_path = os.path.join(self.tmpdir, "consistency.json")
        self.extractor.save_processed_data(processed, json_path)

        with open(json_path, encoding="utf-8") as f:
            reloaded = json.load(f)

        self.assertEqual(reloaded["cluster_summary"]["name"], "Roundtrip-Test")
        self.assertEqual(reloaded["cluster_summary"]["psnt"], "PSNT-RT-001")
        self.assertEqual(reloaded["metadata"]["cluster_version"], "5.3.0")

    def test_section_completeness_reflects_data_quality(self):
        raw = {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {"rack_height_supported": False, "psnt_supported": False},
            "cluster_info": {"name": "Quality", "guid": "q-001", "version": "5.3.0", "state": "active"},
            "hardware": {
                "cnodes": [
                    {"id": i, "name": f"cn{i}", "model": "C200", "serial_number": f"S{i}", "status": "active"}
                    for i in range(1, 5)
                ],
                "dnodes": [{"id": 1, "name": "dn1", "model": "D200", "serial_number": "D1", "status": "active"}],
                "cboxes": [{"id": 1, "name": "cb1", "model": "CBox", "serial_number": "CB1", "status": "active"}],
                "dboxes": [{"id": 1, "name": "db1", "model": "DBox", "serial_number": "DB1", "status": "active"}],
            },
            "network": {
                "dns": {"servers": ["8.8.8.8"], "search_domains": [], "enabled": True},
                "ntp": {"servers": ["pool.ntp.org"], "enabled": True},
                "vippools": {"pools": [{"name": "pool1", "vips": ["10.0.2.1"]}]},
            },
            "logical": {
                "tenants": [{"name": "default", "id": 1, "state": "active"}],
                "views": [{"name": "v1", "path": "/", "state": "active"}],
                "viewpolicies": [],
            },
            "security": {
                "activedirectory": {"enabled": True, "domain": "ad.local", "servers": ["dc1"]},
                "ldap": {"enabled": False},
            },
            "data_protection": {"snapprograms": [], "protectionpolicies": []},
        }
        processed = self.extractor.extract_all_data(raw)
        completeness = processed["metadata"]["overall_completeness"]
        self.assertGreater(completeness, 0)
        self.assertLessEqual(completeness, 100)

@pytest.mark.integration
class TestHealthCheckIntegration(unittest.TestCase):
    """Verify health check data flows through the extraction pipeline."""

    def setUp(self):
        self.extractor = VastDataExtractor()
        self.tmpdir = tempfile.mkdtemp(prefix="vast_health_")

    def _make_mock_health_report(self):
        """Return a mock HealthCheckReport dict (as from HealthChecker.to_dict)."""
        return {
            "cluster_ip": "192.168.1.100",
            "cluster_name": "Health-Test-Cluster",
            "cluster_version": "5.3.0",
            "timestamp": "2025-03-19T12:00:00",
            "results": [
                {
                    "check_name": "Cluster RAID Health",
                    "category": "api",
                    "status": "pass",
                    "message": "All RAID states are HEALTHY",
                    "details": {"ssd_raid_state": "HEALTHY"},
                    "timestamp": "2025-03-19T12:00:01",
                    "duration_seconds": 0.5,
                },
                {
                    "check_name": "Panic/Alert Logs",
                    "category": "node_ssh",
                    "status": "pass",
                    "message": "No PANIC/ALERT entries found",
                    "details": {},
                    "timestamp": "2025-03-19T12:00:02",
                    "duration_seconds": 1.0,
                },
            ],
            "summary": {"pass": 2, "fail": 0, "warning": 0, "skipped": 0, "error": 0},
            "manual_checklist": [{"item": "Failover Testing", "description": "VMS migration test", "status": "Manual"}],
            "tiers_run": [1, 2],
        }

    def test_health_check_json_in_report_data(self):
        raw = {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {"rack_height_supported": False, "psnt_supported": False},
            "cluster_info": {"name": "Health-Test", "guid": "h-001", "version": "5.3.0", "state": "active"},
            "hardware": {"cnodes": [], "dnodes": [], "cboxes": [], "dboxes": []},
            "logical": {"tenants": [], "views": [], "viewpolicies": []},
            "security": {"activedirectory": {"enabled": False}, "ldap": {"enabled": False}},
            "data_protection": {"snapprograms": [], "protectionpolicies": []},
        }
        raw["health_check_results"] = self._make_mock_health_report()
        processed = self.extractor.extract_all_data(raw)
        self.assertIn("health_check", processed["sections"])
        self.assertIn("post_deployment_validation", processed["sections"])

    def test_health_check_report_section_present(self):
        raw = {
            "collection_timestamp": 1695672000.0,
            "cluster_ip": "192.168.1.100",
            "api_version": "v7",
            "cluster_version": "5.3.0",
            "enhanced_features": {"rack_height_supported": False, "psnt_supported": False},
            "cluster_info": {"name": "Health-Test", "guid": "h-001", "version": "5.3.0", "state": "active"},
            "hardware": {"cnodes": [], "dnodes": [], "cboxes": [], "dboxes": []},
            "logical": {"tenants": [], "views": [], "viewpolicies": []},
            "security": {"activedirectory": {"enabled": False}, "ldap": {"enabled": False}},
            "data_protection": {"snapprograms": [], "protectionpolicies": []},
        }
        raw["health_check_results"] = self._make_mock_health_report()
        processed = self.extractor.extract_all_data(raw)
        health_section = processed["sections"]["health_check"]
        self.assertEqual(health_section["title"], "Cluster Health Check Results")
        self.assertEqual(health_section["completeness"], 100.0)
        self.assertEqual(health_section["status"], "complete")
        pvd_section = processed["sections"]["post_deployment_validation"]
        self.assertEqual(pvd_section["title"], "Post Deployment Validation")
        self.assertEqual(pvd_section["completeness"], 100.0)


if __name__ == "__main__":
    unittest.main()
