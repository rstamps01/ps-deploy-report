"""
Shared pytest fixtures for the VAST As-Built Report Generator test suite.

Provides reusable mock API data, configuration, and temporary directory
helpers used across unit, integration, and UI tests.
"""

import errno
import os
import socket
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ---------------------------------------------------------------------------
# Network guard (prevents hung test runs on networked machines)
# ---------------------------------------------------------------------------
# Several unit tests exercise code paths that would otherwise open real TCP
# sockets (e.g. ``oneshot_runner`` building a live ``VastApiHandler`` or SSHing
# to a node/switch).  In CI those targets are unreachable-fast (immediate
# connection refusal), so the tests complete in milliseconds.  On a developer
# machine attached to a routable ``10.0.0.0/8`` fabric, the same SYNs are
# silently dropped and each connect blocks for its full timeout — which made
# the full suite appear to "hang" for minutes.
#
# This autouse guard makes non-loopback outbound connects fail *fast* with
# ``ConnectionRefusedError`` (mirroring CI), so any test that leaks a real
# connection surfaces immediately instead of stalling the run.  Loopback
# traffic (Flask test server, SSE) and AF_UNIX sockets are always allowed, and
# tests marked ``integration`` — or runs with ``VAST_TEST_ALLOW_NETWORK=1`` —
# opt out entirely.

_ALLOWED_INET_FAMILIES = (socket.AF_INET, socket.AF_INET6)


def _is_loopback_address(address: Any) -> bool:
    """True when *address* targets loopback / a non-inet socket (always allowed)."""
    host = address[0] if isinstance(address, (tuple, list)) and address else address
    if not isinstance(host, str):
        # AF_UNIX paths, fds, or anything non-inet — leave untouched.
        return True
    host = host.strip("[]")  # strip IPv6 brackets
    return host in ("::1", "localhost", "") or host.startswith("127.")


@pytest.fixture(autouse=True)
def _block_external_network(request, monkeypatch):
    """Fail non-loopback socket connects fast so leaked network I/O can't hang the suite."""
    if request.node.get_closest_marker("integration") or os.environ.get("VAST_TEST_ALLOW_NETWORK"):
        yield
        return

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex

    def _guarded_connect(self, address, *args, **kwargs):
        if getattr(self, "family", None) in _ALLOWED_INET_FAMILIES and not _is_loopback_address(address):
            raise ConnectionRefusedError(
                errno.ECONNREFUSED,
                f"[test-guard] blocked outbound connection to {address!r}; unit tests must mock "
                "network I/O. Mark the test @pytest.mark.integration or set VAST_TEST_ALLOW_NETWORK=1 "
                "to allow real network access (see tests/conftest.py).",
            )
        return real_connect(self, address, *args, **kwargs)

    def _guarded_connect_ex(self, address, *args, **kwargs):
        if getattr(self, "family", None) in _ALLOWED_INET_FAMILIES and not _is_loopback_address(address):
            return errno.ECONNREFUSED
        return real_connect_ex(self, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
    yield


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
