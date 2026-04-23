import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from external_port_mapper import ExternalPortMapper


@pytest.fixture
def mapper(tmp_path):
    with patch("external_port_mapper.VerboseLogger") as mock_vlog_cls, patch(
        "utils.get_data_dir", return_value=tmp_path
    ), patch("builtins.print"):
        mock_vlog_cls.return_value = MagicMock()
        m = ExternalPortMapper(
            cluster_ip="10.0.0.1",
            api_user="admin",
            api_password="pass",
            cnode_ip="10.0.0.2",
            node_user="vastdata",
            node_password="pass",
            switch_ips=["10.0.0.10", "10.0.0.11"],
            switch_user="cumulus",
            switch_password="pass",
        )
    return m


@pytest.fixture
def mapper_with_proxy(tmp_path):
    with patch("external_port_mapper.VerboseLogger") as mock_vlog_cls, patch(
        "utils.get_data_dir", return_value=tmp_path
    ), patch("builtins.print"):
        mock_vlog_cls.return_value = MagicMock()
        m = ExternalPortMapper(
            cluster_ip="10.0.0.1",
            api_user="admin",
            api_password="pass",
            cnode_ip="10.0.0.2",
            node_user="vastdata",
            node_password="nodepass",
            switch_ips=["10.0.0.10"],
            switch_user="cumulus",
            switch_password="switchpass",
            proxy_jump=True,
        )
    return m


class TestExternalPortMapperInit:
    def test_init_stores_config(self, mapper):
        assert mapper.cluster_ip == "10.0.0.1"
        assert mapper.api_user == "admin"
        assert mapper.api_password == "pass"
        assert mapper.cnode_ip == "10.0.0.2"
        assert mapper.node_user == "vastdata"
        assert mapper.node_password == "pass"
        assert mapper.switch_user == "cumulus"
        assert mapper.switch_password == "pass"

    def test_init_multiple_switches(self, mapper):
        assert len(mapper.switch_ips) == 2
        assert mapper.switch_ips == ["10.0.0.10", "10.0.0.11"]


class TestSwitchPasswordCandidates:
    """Verify mixed-case password fallback honors the ordered candidate list."""

    def _make_mapper(self, tmp_path, candidates=None):
        with patch("external_port_mapper.VerboseLogger") as mock_vlog_cls, patch(
            "utils.get_data_dir", return_value=tmp_path
        ), patch("builtins.print"):
            mock_vlog_cls.return_value = MagicMock()
            return ExternalPortMapper(
                cluster_ip="10.0.0.1",
                api_user="support",
                api_password="pw",
                cnode_ip="10.0.0.2",
                node_user="vastdata",
                node_password="nodepw",
                switch_ips=["10.0.0.10"],
                switch_user="cumulus",
                switch_password="Vastdata1!",
                switch_password_candidates=candidates,
            )

    def test_candidates_default_to_single_password(self, tmp_path):
        m = self._make_mapper(tmp_path)
        assert m.switch_password_candidates == ["Vastdata1!"]

    def test_candidates_preserve_order_with_primary_first(self, tmp_path):
        m = self._make_mapper(tmp_path, candidates=["VastData1!", "Vastdata1!"])
        # operator-entered primary is promoted to the front
        assert m.switch_password_candidates[0] == "Vastdata1!"
        assert "VastData1!" in m.switch_password_candidates

    def test_candidates_dedupe(self, tmp_path):
        m = self._make_mapper(tmp_path, candidates=["Vastdata1!", "Vastdata1!", "VastData1!"])
        assert m.switch_password_candidates.count("Vastdata1!") == 1

    def test_detect_falls_back_to_second_password(self, tmp_path):
        m = self._make_mapper(tmp_path, candidates=["Vastdata1!", "VastData1!"])
        with patch("external_port_mapper.run_ssh_command") as mock_ssh, patch(
            "external_port_mapper.run_interactive_ssh"
        ):
            # First attempt with primary password fails auth; second attempt
            # (same user, fallback password) succeeds with Cumulus output.
            mock_ssh.side_effect = [
                (1, "", "Authentication failed for user cumulus"),
                (0, "cumulus linux hostname: leaf-1", ""),
            ]
            os_type, user, pw = m._detect_switch_os("10.0.0.10")

        assert os_type == "cumulus"
        assert user == "cumulus"
        assert pw == "VastData1!"


class TestSwitchDetection:
    def test_detect_cumulus_switch(self, mapper):
        with patch("external_port_mapper.run_ssh_command") as mock_ssh:
            mock_ssh.return_value = (0, "Cumulus Linux 5.4 hostname: switch-1", "")
            os_type, user, pw = mapper._detect_switch_os("10.0.0.10")
        assert os_type == "cumulus"
        assert user == "cumulus"
        assert pw == "pass"

    def test_detect_onyx_switch(self, mapper):
        with patch("external_port_mapper.run_ssh_command") as mock_ssh, patch(
            "external_port_mapper.run_interactive_ssh"
        ) as mock_issh:
            # Auth-style failure so detection continues to Onyx (not connectivity abort)
            mock_ssh.return_value = (1, "", "Authentication failed for user cumulus")
            mock_issh.return_value = (0, "Product name: Mellanox Onyx", "")
            os_type, user, pw = mapper._detect_switch_os("10.0.0.10")
        assert os_type == "onyx"
        assert user == "admin"
        assert pw == "admin"

    def test_detect_unknown_switch(self, mapper):
        with patch("external_port_mapper.run_ssh_command") as mock_ssh, patch(
            "external_port_mapper.run_interactive_ssh"
        ) as mock_issh:
            mock_ssh.return_value = (1, "", "error")
            mock_issh.return_value = (1, "", "error")
            with pytest.raises(Exception, match="Could not detect OS type"):
                mapper._detect_switch_os("10.0.0.10")

    def test_detect_connectivity_failure_raises_without_second_credential_try(self, mapper):
        with patch("external_port_mapper.run_ssh_command") as mock_ssh, patch(
            "external_port_mapper.run_interactive_ssh"
        ) as mock_issh:
            mock_ssh.return_value = (1, "", "Connection failed for 10.0.0.10: timed out")
            with pytest.raises(Exception, match="Cannot reach switch"):
                mapper._detect_switch_os("10.0.0.10")
            mock_issh.assert_not_called()

    def test_detect_connectivity_message_when_proxy_enabled(self, mapper_with_proxy):
        with patch("external_port_mapper.run_ssh_command") as mock_ssh, patch(
            "external_port_mapper.run_interactive_ssh"
        ):
            mock_ssh.return_value = (1, "", "connection refused")
            with pytest.raises(Exception, match="CNode can reach"):
                mapper_with_proxy._detect_switch_os("10.0.0.10")


class TestMacCollection:
    def test_collect_node_macs_via_clush(self, mapper):
        clush_output = (
            "172.16.3.4: 5: enp129s0f0: <BROADCAST> mtu 9000\n"
            "172.16.3.4:     link/ether aa:bb:cc:dd:ee:01 brd ff:ff:ff:ff:ff:ff\n"
        )
        with patch("external_port_mapper.run_ssh_command") as mock_ssh:
            mock_ssh.return_value = (0, clush_output, "")
            result = mapper._collect_node_macs_via_clush()
        assert "172.16.3.4" in result
        assert result["172.16.3.4"]["enp129s0f0"] == "aa:bb:cc:dd:ee:01"

    def test_parse_clush_output(self, mapper):
        output = (
            "172.16.3.4: 5: enp129s0f0: <BROADCAST,MULTICAST,UP> mtu 9000\n"
            "172.16.3.4:     link/ether aa:bb:cc:dd:ee:01 brd ff:ff:ff:ff:ff:ff\n"
            "172.16.3.5: 3: enp129s0f1: <BROADCAST,MULTICAST,UP> mtu 9000\n"
            "172.16.3.5:     link/ether aa:bb:cc:dd:ee:02 brd ff:ff:ff:ff:ff:ff\n"
        )
        result = mapper._parse_clush_output(output)
        assert "172.16.3.4" in result
        assert result["172.16.3.4"]["enp129s0f0"] == "aa:bb:cc:dd:ee:01"
        assert "172.16.3.5" in result
        assert result["172.16.3.5"]["enp129s0f1"] == "aa:bb:cc:dd:ee:02"

    def test_parse_cumulus_mac_table(self, mapper):
        output = (
            "entry-id  MAC address  vlan  interface\n"
            "---  ---  ---  ---\n"
            "1  aa:bb:cc:dd:ee:01  69  swp1\n"
            "2  aa:bb:cc:dd:ee:02  69  swp2\n"
        )
        result = mapper._parse_cumulus_mac_table(output)
        assert "aa:bb:cc:dd:ee:01" in result
        assert result["aa:bb:cc:dd:ee:01"]["port"] == "swp1"
        assert result["aa:bb:cc:dd:ee:01"]["vlan"] == "69"
        assert "aa:bb:cc:dd:ee:02" in result
        assert result["aa:bb:cc:dd:ee:02"]["port"] == "swp2"

    def test_parse_onyx_mac_table(self, mapper):
        output = (
            "VID  MAC Address  Type  Port\n"
            "---  ---  ---  ---\n"
            "69  AA:BB:CC:DD:EE:01  Dynamic  Eth1/5\n"
            "1  AA:BB:CC:DD:EE:02  Dynamic  Eth1/6\n"
        )
        result = mapper._parse_onyx_mac_table(output)
        assert "aa:bb:cc:dd:ee:01" in result
        assert result["aa:bb:cc:dd:ee:01"]["port"] == "swp5"
        assert result["aa:bb:cc:dd:ee:01"]["vlan"] == "69"
        assert "aa:bb:cc:dd:ee:02" in result
        assert result["aa:bb:cc:dd:ee:02"]["port"] == "swp6"

    def test_parse_onyx_mac_table_filters_port_channels(self, mapper):
        """Port-channel (Po*) entries should be excluded; they represent
        learned MACs via the inter-switch link, not direct physical connections."""
        output = (
            "VID  MAC Address  Type  Port\n"
            "---  ---  ---  ---\n"
            "69  AA:BB:CC:DD:EE:01  Dynamic  Eth1/5\n"
            "69  AA:BB:CC:DD:EE:02  Dynamic  Po1\n"
            "69  AA:BB:CC:DD:EE:03  Dynamic  Po2\n"
            "1   AA:BB:CC:DD:EE:04  Dynamic  Eth1/10\n"
        )
        result = mapper._parse_onyx_mac_table(output)
        assert "aa:bb:cc:dd:ee:01" in result
        assert result["aa:bb:cc:dd:ee:01"]["port"] == "swp5"
        assert "aa:bb:cc:dd:ee:02" not in result
        assert "aa:bb:cc:dd:ee:03" not in result
        assert "aa:bb:cc:dd:ee:04" in result
        assert result["aa:bb:cc:dd:ee:04"]["port"] == "swp10"


class TestCorrelation:
    def test_correlate_node_to_switch(self, mapper):
        node_inventory = {
            "node-1": {
                "hostname": "node-1",
                "mgmt_ip": "10.0.0.100",
                "node_type": "Cnode",
                "box_vendor": "supermicro",
                "box_name": "cbox-1",
            }
        }
        hostname_to_ip = {"node-1": "172.16.0.1"}
        node_macs = {"172.16.0.1": {"enp129s0f0": "aa:bb:cc:dd:ee:01"}}
        switch_macs = {"10.0.0.10": {"aa:bb:cc:dd:ee:01": {"port": "swp1", "vlan": "1"}}}
        result = mapper._correlate_node_to_switch(node_inventory, hostname_to_ip, node_macs, switch_macs)
        assert len(result) == 1
        assert result[0]["node_hostname"] == "node-1"
        assert result[0]["port"] == "swp1"
        assert result[0]["network"] == "A"

    def test_detect_cross_connections(self, mapper):
        port_map = [
            {
                "node_hostname": "node-1",
                "interface": "enp129s0f0",
                "switch_ip": "10.0.0.10",
                "port": "swp1",
                "network": "B",
            }
        ]
        result = mapper._detect_cross_connections(port_map)
        assert len(result) == 1
        assert result[0]["actual_network"] == "B"
        assert result[0]["expected_network"] == "A"

    def test_collect_port_mapping_integration(self, mapper):
        with patch.object(mapper, "_detect_switch_os") as mock_detect, patch.object(
            mapper, "_collect_node_inventory_basic_auth"
        ) as mock_inv, patch.object(mapper, "_collect_ebox_mapping") as mock_ebox, patch.object(
            mapper, "_collect_hostname_to_ip_mapping"
        ) as mock_host, patch.object(
            mapper, "_collect_node_macs_via_clush"
        ) as mock_macs, patch.object(
            mapper, "_collect_switch_mac_tables"
        ) as mock_switch, patch.object(
            mapper, "_collect_ipl_connections"
        ) as mock_ipl, patch(
            "builtins.print"
        ):
            mock_detect.return_value = ("cumulus", "cumulus", "pass")
            mock_inv.return_value = {
                "node-1": {
                    "hostname": "node-1",
                    "mgmt_ip": "10.0.0.100",
                    "node_type": "Cnode",
                    "box_vendor": "supermicro",
                    "box_name": "cbox-1",
                }
            }
            mock_ebox.return_value = {}
            mock_host.return_value = {"node-1": "172.16.0.1"}
            mock_macs.return_value = {"172.16.0.1": {"enp129s0f0": "aa:bb:cc:dd:ee:01"}}
            mock_switch.return_value = {"10.0.0.10": {"aa:bb:cc:dd:ee:01": {"port": "swp1", "vlan": "1"}}}
            mock_ipl.return_value = []
            result = mapper.collect_port_mapping()
        assert result["available"] is True
        assert len(result["port_map"]) == 1
        assert result["port_map"][0]["node_hostname"] == "node-1"
        assert isinstance(result["cross_connections"], list)
        assert result["total_connections"] == 1


@pytest.fixture
def mapper_with_spine(tmp_path):
    """ExternalPortMapper configured with a three-switch fabric (2 leaves + 1 spine).

    Covers the spine-aware edge classification paths introduced for the
    'no spine-to-leaf mapping in the Logical Network Diagram' fix.
    """
    with patch("external_port_mapper.VerboseLogger") as mock_vlog_cls, patch(
        "utils.get_data_dir", return_value=tmp_path
    ), patch("builtins.print"):
        mock_vlog_cls.return_value = MagicMock()
        m = ExternalPortMapper(
            cluster_ip="10.0.0.1",
            api_user="admin",
            api_password="pass",
            cnode_ip="10.0.0.2",
            node_user="vastdata",
            node_password="pass",
            switch_ips=["10.0.0.153", "10.0.0.154", "10.0.0.156"],
            switch_user="cumulus",
            switch_password="pass",
            switch_hostname_map={
                "se-var-sw-1": "10.0.0.153",
                "se-sw-2": "10.0.0.154",
                "se-client-1-2": "10.0.0.156",
            },
            spine_ips=["10.0.0.156"],
        )
    return m


class TestEdgeClassification:
    """Tag LLDP-discovered switch edges as ipl / spine_uplink / spine_fabric."""

    def test_leaf_to_leaf_is_ipl(self, mapper_with_spine):
        edge = {"switch1_ip": "10.0.0.153", "switch2_ip": "10.0.0.154"}
        classified = mapper_with_spine._classify_edge(edge)
        assert classified["connection_type"] == "ipl"
        assert classified["notes"] == "IPL"

    def test_leaf_to_spine_is_spine_uplink(self, mapper_with_spine):
        edge = {"switch1_ip": "10.0.0.153", "switch2_ip": "10.0.0.156"}
        classified = mapper_with_spine._classify_edge(edge)
        assert classified["connection_type"] == "spine_uplink"
        assert classified["notes"] == "Spine uplink"

    def test_spine_to_spine_is_fabric(self, mapper_with_spine):
        mapper_with_spine.spine_ips = {"10.0.0.156", "10.0.0.157"}
        edge = {"switch1_ip": "10.0.0.156", "switch2_ip": "10.0.0.157"}
        classified = mapper_with_spine._classify_edge(edge)
        assert classified["connection_type"] == "spine_fabric"
        assert classified["notes"] == "Spine fabric"

    def test_no_spine_ips_defaults_to_ipl(self, mapper):
        """Legacy callers (no spine list) must continue to tag every edge as ipl."""
        edge = {"switch1_ip": "10.0.0.10", "switch2_ip": "10.0.0.11"}
        classified = mapper._classify_edge(edge)
        assert classified["connection_type"] == "ipl"

    def test_preserves_existing_connection_type(self, mapper_with_spine):
        edge = {"switch1_ip": "10.0.0.153", "switch2_ip": "10.0.0.156", "connection_type": "ipl"}
        classified = mapper_with_spine._classify_edge(edge)
        assert classified["connection_type"] == "ipl", "Explicit upstream tag must win"


class TestNeighborResolution:
    def test_resolves_by_exact_hostname(self, mapper_with_spine):
        assert mapper_with_spine._resolve_neighbor_to_switch_ip("se-var-sw-1") == "10.0.0.153"

    def test_hostname_match_is_case_insensitive(self, mapper_with_spine):
        assert mapper_with_spine._resolve_neighbor_to_switch_ip("SE-VAR-SW-1") == "10.0.0.153"

    def test_resolves_fqdn_by_short_name(self, mapper_with_spine):
        assert mapper_with_spine._resolve_neighbor_to_switch_ip("se-var-sw-1.lab.example") == "10.0.0.153"

    def test_resolves_by_advertised_mgmt_ip(self, mapper_with_spine):
        """Hostname missing but mgmt-ip advertised -> still resolves."""
        assert mapper_with_spine._resolve_neighbor_to_switch_ip("", remote_mgmt_ip="10.0.0.154") == "10.0.0.154"

    def test_unknown_neighbor_returns_empty(self, mapper_with_spine):
        assert mapper_with_spine._resolve_neighbor_to_switch_ip("some-node-42") == ""


class TestCumulusLldpGeneralizedWalk:
    """Regression coverage for the 'no leaf→spine uplinks' bug.

    The legacy parser only looked at swp29..swp32 and required symmetric
    ports, so spine uplinks on swp1 were silently dropped.  The generalized
    walk must discover them whenever ``switch_hostname_map`` is provided.
    """

    def test_generalized_walk_emits_uplink_from_leaf(self, mapper_with_spine):
        json_output = (
            "{"
            '  "swp1": {'
            '    "lldp": {'
            '      "neighbor": {'
            '        "se-client-1-2": {'
            '          "port": {"name": "swp10"},'
            '          "mgmt-ip": "10.0.0.156"'
            "        }"
            "      }"
            "    }"
            "  },"
            '  "swp29": {'
            '    "lldp": {'
            '      "neighbor": {'
            '        "se-sw-2": {'
            '          "port": {"name": "swp29"}'
            "        }"
            "      }"
            "    }"
            "  }"
            "}"
        )

        edges = mapper_with_spine._parse_cumulus_lldp_for_ipl(json_output, "10.0.0.153")

        remote_ips = {e["switch2_ip"] for e in edges}
        assert "10.0.0.156" in remote_ips, "Spine uplink on swp1 must be detected"
        assert "10.0.0.154" in remote_ips, "IPL on swp29 must still be detected"

        uplink = next(e for e in edges if e["switch2_ip"] == "10.0.0.156")
        assert uplink["switch1_port"] == "swp1"
        assert uplink["switch2_port"] == "swp10"

    def test_generalized_walk_ignores_unknown_hosts(self, mapper_with_spine):
        """Neighbors that aren't cluster switches (e.g. node LLDP) are dropped."""
        json_output = (
            "{"
            '  "swp3": {'
            '    "lldp": {'
            '      "neighbor": {'
            '        "some-compute-node": {"port": {"name": "enp1s0f0"}}'
            "      }"
            "    }"
            "  }"
            "}"
        )
        edges = mapper_with_spine._parse_cumulus_lldp_for_ipl(json_output, "10.0.0.153")
        assert edges == []

    def test_legacy_narrow_scan_when_no_hostname_map(self, mapper):
        """Without a hostname map / spine list, the collector preserves legacy behavior.

        This is the compatibility guarantee so existing 2-leaf deployments
        continue to function without reconfiguration.
        """
        json_output = (
            "{"
            '  "swp1": {'
            '    "lldp": {'
            '      "neighbor": {'
            '        "leaf-b": {"port": {"name": "swp10"}}'
            "      }"
            "    }"
            "  },"
            '  "swp29": {'
            '    "lldp": {'
            '      "neighbor": {'
            '        "leaf-b": {"port": {"name": "swp29"}}'
            "      }"
            "    }"
            "  }"
            "}"
        )
        edges = mapper._parse_cumulus_lldp_for_ipl(json_output, "10.0.0.10")
        # Legacy mode must only pick up the symmetric swp29 peer-link,
        # ignoring the asymmetric swp1 entry.
        assert len(edges) == 1
        assert edges[0]["switch1_port"] == "swp29"


class TestOnyxLldpGeneralizedWalk:
    """Regression coverage for the Mellanox Onyx parallel to the Cumulus walk.

    Before PMI-4 the Onyx parser only inspected ports Eth1/29..Eth1/32 with a
    symmetric remote-port check, so leaf-to-spine uplinks on arbitrary ports
    were silently dropped on Onyx-only fabrics.  The generalized walk must
    discover them whenever ``switch_hostname_map`` is configured.
    """

    ONYX_OUTPUT = (
        "Local Interface     Chassis ID          Port ID             System Name\n"
        "-----------------   -----------------   -----------------   -----------\n"
        "Eth1/1              f4:02:70:aa:bb:cc   Eth1/10             se-client-1-2\n"
        "Eth1/29             f4:02:70:c1:22:00   Eth1/29             se-sw-2\n"
    )

    def test_generalized_walk_emits_uplink_and_ipl(self, mapper_with_spine):
        edges = mapper_with_spine._parse_onyx_lldp_for_ipl(self.ONYX_OUTPUT, "10.0.0.153")
        remote_ips = {e["switch2_ip"] for e in edges}
        assert "10.0.0.156" in remote_ips, "Spine uplink on Eth1/1 must be detected"
        assert "10.0.0.154" in remote_ips, "MLAG peer-link on Eth1/29 must still be detected"

        uplink = next(e for e in edges if e["switch2_ip"] == "10.0.0.156")
        assert uplink["switch1_port"] == "Eth1/1", "Onyx native naming preserved in generalized mode"
        assert uplink["switch2_port"] == "Eth1/10"
        assert uplink["port_number"] == 1

    def test_generalized_walk_drops_unknown_hosts(self, mapper_with_spine):
        onyx = (
            "Local Interface     Chassis ID          Port ID             System Name\n"
            "-----------------   -----------------   -----------------   -----------\n"
            "Eth1/5              aa:bb:cc:dd:ee:ff   enp1s0f0            compute-node-42\n"
        )
        assert mapper_with_spine._parse_onyx_lldp_for_ipl(onyx, "10.0.0.153") == []

    def test_generalized_walk_skips_self_advertisement(self, mapper_with_spine):
        """A switch that somehow shows up as its own neighbor must not produce a self-edge."""
        onyx = (
            "Local Interface     Chassis ID          Port ID             System Name\n"
            "-----------------   -----------------   -----------------   -----------\n"
            "Eth1/7              f4:02:70:c1:22:00   Eth1/7              se-var-sw-1\n"
        )
        edges = mapper_with_spine._parse_onyx_lldp_for_ipl(onyx, "10.0.0.153")
        assert edges == [], "Self-advertised hostname must not yield a loopback edge"

    def test_legacy_narrow_scan_when_no_hostname_map(self, mapper):
        """Without a hostname map, the Onyx parser must preserve the historical narrow scan."""
        onyx = (
            "Local Interface     Chassis ID          Port ID             System Name\n"
            "-----------------   -----------------   -----------------   -----------\n"
            "Eth1/1              aa:bb:cc:dd:ee:ff   Eth1/10             leaf-b\n"
            "Eth1/29             f4:02:70:c1:22:00   Eth1/29             leaf-b\n"
        )
        edges = mapper._parse_onyx_lldp_for_ipl(onyx, "10.0.0.10")
        assert len(edges) == 1
        # Legacy mode converts Eth1/29 -> swp29 for consistency with the
        # Cumulus narrow scan.  Eth1/1 is asymmetric and must be skipped.
        assert edges[0]["switch1_port"] == "swp29"
        assert edges[0]["port_number"] == 29


class TestProxyJumpConfig:
    def test_proxy_jump_stored_true(self, mapper_with_proxy):
        assert mapper_with_proxy.proxy_jump is True

    def test_proxy_jump_default_true(self, mapper):
        assert mapper.proxy_jump is True

    def test_jump_kwargs_when_proxy_enabled(self, mapper_with_proxy):
        kwargs = mapper_with_proxy._jump_kwargs()
        assert kwargs == {
            "jump_host": "10.0.0.1",
            "jump_user": "vastdata",
            "jump_password": "nodepass",
        }

    def test_jump_kwargs_when_proxy_disabled(self, tmp_path):
        with patch("external_port_mapper.VerboseLogger") as mock_vlog_cls, patch(
            "utils.get_data_dir", return_value=tmp_path
        ), patch("builtins.print"):
            mock_vlog_cls.return_value = MagicMock()
            m = ExternalPortMapper(
                cluster_ip="10.0.0.1",
                api_user="admin",
                api_password="pass",
                cnode_ip="10.0.0.2",
                node_user="vastdata",
                node_password="nodepass",
                switch_ips=["10.0.0.10"],
                switch_user="cumulus",
                switch_password="switchpass",
                proxy_jump=False,
            )
        assert m._jump_kwargs() == {}

    def test_detect_switch_os_passes_jump_params(self, mapper_with_proxy):
        with patch("external_port_mapper.run_ssh_command") as mock_ssh:
            mock_ssh.return_value = (0, "Cumulus Linux hostname: switch-1", "")
            mapper_with_proxy._detect_switch_os("10.0.0.10")
        _, kwargs = mock_ssh.call_args
        assert kwargs.get("jump_host") == "10.0.0.1"
        assert kwargs.get("jump_user") == "vastdata"
        assert kwargs.get("jump_password") == "nodepass"

    def test_onyx_interactive_routes_through_ssh_adapter(self, mapper_with_proxy):
        with patch("external_port_mapper.run_interactive_ssh") as mock_issh:
            mock_issh.return_value = (0, "output", "")
            mapper_with_proxy._run_onyx_interactive_command("10.0.0.10", "admin", "admin", "show version")
        _, kwargs = mock_issh.call_args
        assert kwargs.get("jump_host") == "10.0.0.1"
        assert kwargs.get("jump_user") == "vastdata"
        assert kwargs.get("jump_password") == "nodepass"

    def test_onyx_interactive_uses_pexpect_when_proxy_disabled(self, tmp_path):
        with patch("external_port_mapper.VerboseLogger") as mock_vlog_cls, patch(
            "utils.get_data_dir", return_value=tmp_path
        ), patch("builtins.print"):
            mock_vlog_cls.return_value = MagicMock()
            m = ExternalPortMapper(
                cluster_ip="10.0.0.1",
                api_user="admin",
                api_password="pass",
                cnode_ip="10.0.0.2",
                node_user="vastdata",
                node_password="nodepass",
                switch_ips=["10.0.0.10"],
                switch_user="cumulus",
                switch_password="switchpass",
                proxy_jump=False,
            )
        with patch("external_port_mapper.run_interactive_ssh") as mock_issh, patch("pexpect.spawn") as mock_spawn:
            mock_spawn.return_value = MagicMock()
            mock_spawn.return_value.expect.return_value = 0
            mock_spawn.return_value.before = "output"
            m._run_onyx_interactive_command("10.0.0.10", "admin", "admin", "show version")
        mock_issh.assert_not_called()
