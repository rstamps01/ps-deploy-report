"""
Shared pytest fixtures for the VAST As-Built Report Generator test suite.

Provides reusable mock API data, configuration, and temporary directory
helpers used across unit, integration, and UI tests.
"""

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def sample_raw_data() -> Dict[str, Any]:
    """Minimal raw API data matching the shape returned by VastApiHandler.get_all_data()."""
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
            "name": "Test Cluster",
            "guid": "test-guid-123",
            "version": "5.3.0",
            "state": "active",
            "license": "Enterprise",
            "psnt": "PSNT123456789",
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
                    "rack_position": {"rack": 1, "u_start": 10, "u_height": 2},
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
                    "rack_position": {"rack": 1, "u_start": 5, "u_height": 4},
                },
            ],
            "cboxes": [
                {
                    "id": 1,
                    "name": "cbox-1",
                    "serial_number": "CB001",
                    "model": "CBox",
                    "status": "active",
                },
            ],
            "dboxes": [
                {
                    "id": 1,
                    "name": "dbox-1",
                    "serial_number": "DB001",
                    "model": "DBox",
                    "status": "active",
                },
            ],
        },
        "network": {
            "dns": {"servers": ["8.8.8.8"], "search_domains": ["test.local"], "enabled": True},
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
            "protectionpolicies": [{"name": "retention_30d", "type": "retention", "retention": "30d", "enabled": True}],
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


@pytest.fixture
def sample_cboxes():
    return [
        {"id": 1, "name": "cbox-1", "serial_number": "CB001", "model": "CBox", "status": "active"},
    ]


@pytest.fixture
def sample_dboxes():
    return [
        {"id": 1, "name": "dbox-1", "serial_number": "DB001", "model": "DBox", "status": "active"},
    ]


@pytest.fixture
def sample_cnodes():
    return [
        {"id": 1, "name": "cnode-1", "ip": "10.0.0.1", "mgmt_ip": "10.0.1.1", "status": "active"},
        {"id": 2, "name": "cnode-2", "ip": "10.0.0.2", "mgmt_ip": "10.0.1.2", "status": "active"},
    ]


@pytest.fixture
def sample_dnodes():
    return [
        {"id": 1, "name": "dnode-1", "ip": "10.0.0.11", "status": "active"},
        {"id": 2, "name": "dnode-2", "ip": "10.0.0.12", "status": "active"},
    ]


@pytest.fixture
def sample_switches():
    return [
        {"id": 1, "name": "switch-A", "ip": "10.0.0.101", "model": "SN2100"},
        {"id": 2, "name": "switch-B", "ip": "10.0.0.102", "model": "SN2100"},
    ]


@pytest.fixture
def tmp_output_dir():
    """Temporary directory for test report output, cleaned up automatically."""
    with tempfile.TemporaryDirectory(prefix="vast_test_") as d:
        yield d


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Minimal config dict matching config/config.yaml structure."""
    return {
        "api": {"timeout": 30, "max_retries": 3, "retry_delay": 2, "verify_ssl": False, "version": "v7"},
        "logging": {"level": "WARNING"},
        "report": {
            "organization": "Test Org",
            "template": {
                "page_size": "A4",
                "margin_top": 1.0,
                "margin_bottom": 1.0,
                "margin_left": 1.0,
                "margin_right": 1.0,
            },
            "pdf": {
                "include_toc": True,
                "include_page_numbers": True,
                "font_family": "Helvetica",
                "font_size": 10,
            },
        },
        "output": {
            "default_directory": "./reports",
            "pdf_filename": "vast_report_{cluster_name}_{timestamp}.pdf",
            "json_filename": "vast_data_{cluster_name}_{timestamp}.json",
        },
        "data_collection": {"graceful_degradation": True},
    }


@pytest.fixture
def mock_api_responses_path():
    """Path to shared mock API response fixtures."""
    return Path(__file__).parent / "data" / "mock_api_responses.json"
