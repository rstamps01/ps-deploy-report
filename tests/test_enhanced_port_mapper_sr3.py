"""SR-3 unit tests for ``EnhancedPortMapper`` GUID-to-mgmt_ip aliasing.

On InfiniBand clusters ``vnetmap`` reports the switch identity in the
"switch_ip" column as a 16-byte GUID (e.g. ``0xb83fd20300e856b8``)
rather than an IP address.  Without an alias map, every port-map entry
falls into the ``Unknown switch IP`` warning branch of
``EnhancedPortMapper.generate_switch_designation`` and renders as
``SW?-<port>`` in the report — and IPL inference returns zero
connections because the LLDP/IPL inference logic also keys on
``switch_ip``.

The fix accepts an ``ib_switch_headers`` parameter (parsed from
``vnetmap_parser._parse_ib_switch_headers``) that pairs each GUID with
the switch hostname.  ``_build_switch_map`` then matches each GUID's
hostname against the API-supplied ``switches`` list (by ``name`` /
``hostname`` / ``host_name``) and adds the GUID as an alias key
pointing at the same record as the matching ``mgmt_ip``.  The result
is that ``generate_switch_designation('0xb83...', '19')`` returns the
correct ``SWA-P19`` designation even though the canonical map entry is
keyed on the mgmt_ip.

Tests below cover:

* GUID alias resolves to the correct ``SWA-P<n>`` designation when the
  switch is in the API inventory under the matching hostname.
* Hostname matching tolerates whichever of ``name`` / ``hostname`` /
  ``host_name`` the API returned (different VAST versions populate
  different fields).
* GUIDs whose hostname can't be matched still fall through to the
  ``Unknown switch IP`` warning — the fix is graceful, not silently
  fabricating.
* Eth clusters (no ``ib_switch_headers``) are completely unaffected.
* The ``switch_hostname`` accessor returns the API hostname for a GUID,
  not the GUID itself, after aliasing.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from enhanced_port_mapper import EnhancedPortMapper  # noqa: E402

# Two IB leaf switches reported by the VAST API.  The ``mgmt_ip`` is
# the operator-visible 10.247.x.x address used everywhere else in the
# pipeline; ``name`` matches the hostname the IB SubnetManager prints
# in the ``Switch MF0;<name>:<model> - <guid> has ...`` header lines.
_IB_API_SWITCHES: List[Dict[str, Any]] = [
    {
        "id": 1,
        "name": "vast-switch1-bot",
        "mgmt_ip": "10.247.2.135",
        "model": "MQM8700-HS2F",
        "role": "leaf",
    },
    {
        "id": 2,
        "name": "vast-switch2-top",
        "mgmt_ip": "10.247.2.137",
        "model": "MQM8700-HS2F",
        "role": "leaf",
    },
]

_IB_SWITCH_HEADERS = [
    {
        "guid": "0xb83fd20300e856b8",
        "hostname": "vast-switch1-bot",
        "model": "MQM8700/U1",
        "internal_subnet": "172.16.0",
    },
    {
        "guid": "0xb83fd20300e85d18",
        "hostname": "vast-switch2-top",
        "model": "MQM8700/U1",
        "internal_subnet": "172.16.64",
    },
]

# Minimal IB topology rows where ``switch_ip`` is a GUID, mirroring
# what ``vnetmap_parser._parse_topology_section`` produces today.
_IB_TOPOLOGY: List[Dict[str, Any]] = [
    {
        "hostname": "c-128-1",
        "node_hostname": "c-128-1",
        "switch_ip": "0xb83fd20300e856b8",
        "port": "19",
        "node_ip": "172.16.0.1",
        "interface": "ib2",
        "mac": "80:00:01:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:80",
        "network": "A",
    },
    {
        "hostname": "c-128-1",
        "node_hostname": "c-128-1",
        "switch_ip": "0xb83fd20300e85d18",
        "port": "19",
        "node_ip": "172.16.64.1",
        "interface": "ib3",
        "mac": "80:00:09:07:fe:80:00:00:00:00:00:00:a0:88:c2:03:00:57:36:81",
        "network": "B",
    },
]


@pytest.fixture
def warning_capture(caplog) -> "logging.LogCaptureFixture":
    """Capture WARNING-level emissions from ``enhanced_port_mapper``."""
    caplog.set_level(logging.WARNING, logger="enhanced_port_mapper")
    return caplog


class TestSR3GuidAliasing:
    def test_constructor_accepts_ib_switch_headers(self):
        """Public API additive change: ``ib_switch_headers`` kwarg."""
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=_IB_API_SWITCHES,
            external_port_map=_IB_TOPOLOGY,
            ib_switch_headers=_IB_SWITCH_HEADERS,
        )
        # The GUIDs from the IB headers must be valid keys in switch_map
        # after aliasing — same record as the canonical mgmt_ip key.
        assert "0xb83fd20300e856b8" in mapper.switch_map
        assert "0xb83fd20300e85d18" in mapper.switch_map
        # And the canonical mgmt_ip keys must still exist (alias is
        # additive, not a replacement).
        assert "10.247.2.135" in mapper.switch_map
        assert "10.247.2.137" in mapper.switch_map

    def test_guid_alias_yields_swa_swb_designations(self):
        """GUID -> switch_map -> ``SWA-P19`` / ``SWB-P19`` (alphabetised by mgmt_ip).

        ``_build_switch_map`` sorts leaf switches by ``mgmt_ip`` before
        assigning A/B/C/... letters.  10.247.2.135 < 10.247.2.137 in
        string sort, so the bot switch (``vast-switch1-bot``,
        ``0xb83fd20300e856b8``) becomes ``SWA``.
        """
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=_IB_API_SWITCHES,
            external_port_map=_IB_TOPOLOGY,
            ib_switch_headers=_IB_SWITCH_HEADERS,
        )
        assert mapper.generate_switch_designation("0xb83fd20300e856b8", "19") == "SWA-P19"
        assert mapper.generate_switch_designation("0xb83fd20300e85d18", "19") == "SWB-P19"

    def test_no_unknown_switch_ip_warning_when_guid_is_aliased(self, warning_capture):
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=_IB_API_SWITCHES,
            external_port_map=_IB_TOPOLOGY,
            ib_switch_headers=_IB_SWITCH_HEADERS,
        )
        warning_capture.clear()
        for row in _IB_TOPOLOGY:
            mapper.generate_switch_designation(row["switch_ip"], row["port"])
        unknown_warns = [r for r in warning_capture.records if "Unknown switch IP" in r.getMessage()]
        assert unknown_warns == []

    def test_unmatched_guid_still_warns_gracefully(self, warning_capture):
        """A GUID with no matching hostname falls through to the existing
        ``Unknown switch IP`` warning — the fix never silently swallows
        unknown identifiers.
        """
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=_IB_API_SWITCHES,
            external_port_map=_IB_TOPOLOGY,
            ib_switch_headers=_IB_SWITCH_HEADERS,
        )
        warning_capture.clear()
        result = mapper.generate_switch_designation("0xdeadbeefdeadbeef", "19")
        assert result == "SW?-19"
        unknown_warns = [r for r in warning_capture.records if "Unknown switch IP" in r.getMessage()]
        assert len(unknown_warns) >= 1

    def test_hostname_match_uses_alternate_api_field(self):
        """Some VAST versions return ``hostname`` instead of ``name``."""
        switches = [
            {"id": 1, "hostname": "vast-switch1-bot", "mgmt_ip": "10.247.2.135", "role": "leaf"},
            {"id": 2, "host_name": "vast-switch2-top", "mgmt_ip": "10.247.2.137", "role": "leaf"},
        ]
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=switches,
            external_port_map=_IB_TOPOLOGY,
            ib_switch_headers=_IB_SWITCH_HEADERS,
        )
        assert "0xb83fd20300e856b8" in mapper.switch_map
        assert "0xb83fd20300e85d18" in mapper.switch_map
        assert mapper.generate_switch_designation("0xb83fd20300e856b8", "19") == "SWA-P19"

    def test_get_switch_hostname_via_guid_returns_api_hostname(self):
        """``get_switch_hostname(GUID)`` must return the human hostname,
        not the GUID itself, after aliasing.
        """
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=_IB_API_SWITCHES,
            external_port_map=_IB_TOPOLOGY,
            ib_switch_headers=_IB_SWITCH_HEADERS,
        )
        assert mapper.get_switch_hostname("0xb83fd20300e856b8") == "vast-switch1-bot"
        assert mapper.get_switch_hostname("0xb83fd20300e85d18") == "vast-switch2-top"

    def test_eth_cluster_unaffected_by_optional_kwarg(self):
        """Ethernet cluster shape: ``ib_switch_headers`` defaults to None,
        all switch_ip values are mgmt IPs — no behaviour change.
        """
        eth_switches = [
            {"id": 1, "name": "leaf-1", "mgmt_ip": "10.128.101.141", "role": "leaf"},
            {"id": 2, "name": "leaf-2", "mgmt_ip": "10.128.101.142", "role": "leaf"},
        ]
        eth_topology = [
            {
                "hostname": "cnode-1",
                "node_hostname": "cnode-1",
                "switch_ip": "10.128.101.141",
                "port": "Eth1/15",
                "node_ip": "10.0.0.1",
                "interface": "f0",
                "mac": "aa:bb:cc:dd:ee:01",
                "network": "A",
            }
        ]
        mapper = EnhancedPortMapper(
            cboxes=[],
            dboxes=[],
            cnodes=[],
            dnodes=[],
            switches=eth_switches,
            external_port_map=eth_topology,
        )
        # Default kwarg behaviour: no IB headers, all entries use mgmt_ip.
        assert "10.128.101.141" in mapper.switch_map
        assert "10.128.101.142" in mapper.switch_map
        # Make sure no spurious GUID-shaped keys appeared.
        guid_keys = [k for k in mapper.switch_map if isinstance(k, str) and k.startswith("0x")]
        assert guid_keys == []
        assert mapper.generate_switch_designation("10.128.101.141", "Eth1/15") == "SWA-P15"
