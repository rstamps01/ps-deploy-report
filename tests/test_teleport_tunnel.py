"""
Tests for the Teleport (``tsh``) connection tunnel (src/utils/teleport_tunnel.py).

All subprocess / socket interactions are mocked so no real ``tsh`` session or
network forward is required.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.teleport_tunnel import TeleportTunnel, TeleportError, options_from_config


class TestOptionsFromConfig(unittest.TestCase):
    def test_empty_config_returns_empty(self):
        self.assertEqual(options_from_config(None), {})
        self.assertEqual(options_from_config({}), {})
        self.assertEqual(options_from_config({"teleport": {}}), {})

    def test_extracts_set_keys_only(self):
        cfg = {
            "teleport": {
                "tsh_path": "/opt/tsh",
                "auto_login": False,
                "proxy": "teleport.vastdata.com:443",
                "login_timeout": 90,
            }
        }
        opts = options_from_config(cfg)
        self.assertEqual(opts["tsh_path"], "/opt/tsh")
        self.assertFalse(opts["auto_login"])
        self.assertEqual(opts["proxy"], "teleport.vastdata.com:443")
        self.assertEqual(opts["login_timeout"], 90)

    def test_blank_values_are_skipped(self):
        cfg = {"teleport": {"tsh_path": "", "proxy": ""}}
        self.assertEqual(options_from_config(cfg), {})


class TestPreflight(unittest.TestCase):
    @patch("utils.teleport_tunnel.shutil.which", return_value=None)
    def test_missing_tsh_raises(self, _which):
        tunnel = TeleportTunnel("PDX02-Vast01-c-128-4")
        with self.assertRaises(TeleportError) as ctx:
            tunnel.preflight()
        self.assertIn("not found on PATH", str(ctx.exception))

    @patch("utils.teleport_tunnel.subprocess.run")
    @patch("utils.teleport_tunnel.shutil.which", return_value="/usr/local/bin/tsh")
    def test_no_active_session_raises_when_auto_login_disabled(self, _which, mock_run):
        # auto_login off => fail fast with an actionable message, no tsh login.
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="ERROR: Not logged in")
        tunnel = TeleportTunnel("node", auto_login=False)
        with self.assertRaises(TeleportError) as ctx:
            tunnel.preflight()
        self.assertIn("No active Teleport session", str(ctx.exception))
        # Only `tsh status` should have run — never `tsh login`.
        for call in mock_run.call_args_list:
            self.assertNotIn("login", call.args[0])

    @patch("utils.teleport_tunnel.subprocess.run")
    @patch("utils.teleport_tunnel.shutil.which", return_value="/usr/local/bin/tsh")
    def test_active_session_passes(self, _which, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Profile URL: ...", stderr="")
        tunnel = TeleportTunnel("node")
        tunnel.preflight()  # should not raise

    @patch("utils.teleport_tunnel.subprocess.run")
    @patch("utils.teleport_tunnel.shutil.which", return_value="/usr/local/bin/tsh")
    def test_expired_session_triggers_tsh_login_then_succeeds(self, _which, mock_run):
        # The motivating case: an expired profile.  preflight must run
        # `tsh login` (which opens the SSO browser), then re-check status and
        # proceed once the operator completes login.
        def run_side_effect(cmd, *a, **kw):
            if "status" in cmd:
                # first status fails (expired), second status (post-login) ok
                run_side_effect.status_calls += 1
                if run_side_effect.status_calls == 1:
                    return MagicMock(returncode=1, stdout="", stderr="ERROR: Active profile expired.")
                return MagicMock(returncode=0, stdout="Valid until: ...", stderr="")
            if "login" in cmd:
                return MagicMock(returncode=0, stdout="Logged in as: ray.stamps", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        run_side_effect.status_calls = 0
        mock_run.side_effect = run_side_effect

        tunnel = TeleportTunnel("node")
        tunnel.preflight()  # should NOT raise — login refreshed the session

        commands = [call.args[0] for call in mock_run.call_args_list]
        self.assertTrue(any("login" in c for c in commands), "expected a `tsh login` attempt")
        self.assertEqual(run_side_effect.status_calls, 2, "expected a post-login status re-check")

    @patch("utils.teleport_tunnel.subprocess.run")
    @patch("utils.teleport_tunnel.shutil.which", return_value="/usr/local/bin/tsh")
    def test_login_uses_proxy_when_configured(self, _which, mock_run):
        def run_side_effect(cmd, *a, **kw):
            if "status" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="expired")
            if "login" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="cancelled")
            return MagicMock(returncode=1, stdout="", stderr="")

        mock_run.side_effect = run_side_effect
        tunnel = TeleportTunnel("node", proxy="teleport.vastdata.com:443")
        with self.assertRaises(TeleportError):
            tunnel.preflight()
        login_calls = [call.args[0] for call in mock_run.call_args_list if "login" in call.args[0]]
        self.assertTrue(login_calls)
        self.assertIn("--proxy=teleport.vastdata.com:443", login_calls[0])

    @patch("utils.teleport_tunnel.subprocess.run")
    @patch("utils.teleport_tunnel.shutil.which", return_value="/usr/local/bin/tsh")
    def test_login_failure_still_raises(self, _which, mock_run):
        # tsh login fails (operator cancels / SSO error) => preflight still
        # raises the actionable error, including the latest status detail.
        def run_side_effect(cmd, *a, **kw):
            if "login" in cmd:
                return MagicMock(returncode=1, stdout="", stderr="login error")
            return MagicMock(returncode=1, stdout="", stderr="ERROR: Active profile expired.")

        mock_run.side_effect = run_side_effect
        tunnel = TeleportTunnel("node")
        with self.assertRaises(TeleportError) as ctx:
            tunnel.preflight()
        self.assertIn("No active Teleport session", str(ctx.exception))


class TestBuildCommand(unittest.TestCase):
    def test_label_query_node_uses_explicit_user(self):
        tunnel = TeleportTunnel("hostname=PDX02-Vast01-c-128-4", "vastdata")
        tunnel.api_local_port = 50443
        tunnel.ssh_local_port = 50022
        cmd = tunnel._build_command()
        self.assertEqual(cmd[:2], ["tsh", "ssh"])
        self.assertIn("50443:127.0.0.1:443", cmd)
        self.assertIn("50022:127.0.0.1:22", cmd)
        self.assertIn("-l", cmd)
        self.assertIn("vastdata", cmd)
        self.assertIn("hostname=PDX02-Vast01-c-128-4", cmd)

    def test_user_at_host_node_omits_explicit_user_flag(self):
        tunnel = TeleportTunnel("vastdata@cnode-1")
        tunnel.api_local_port = 50443
        tunnel.ssh_local_port = 50022
        cmd = tunnel._build_command()
        self.assertIn("vastdata@cnode-1", cmd)
        self.assertNotIn("-l", cmd)

    def test_api_remote_host_defaults_to_loopback(self):
        tunnel = TeleportTunnel("node")
        self.assertEqual(tunnel.api_remote_host, "127.0.0.1")

    def test_api_remote_host_forwards_to_vms_vip(self):
        # Pointing the API forward at the VMS management VIP lets the VMS be
        # reached from any node, not just the one that hosts it.
        tunnel = TeleportTunnel("hostname=R0406-CB7-U25-bottom-right", "vastdata", api_remote_host="10.84.214.5")
        tunnel.api_local_port = 50443
        tunnel.ssh_local_port = 50022
        cmd = tunnel._build_command()
        self.assertIn("50443:10.84.214.5:443", cmd)
        # SSH still terminates on the node's own loopback sshd.
        self.assertIn("50022:127.0.0.1:22", cmd)

    def test_blank_api_remote_host_falls_back_to_loopback(self):
        tunnel = TeleportTunnel("node", api_remote_host="")
        self.assertEqual(tunnel.api_remote_host, "127.0.0.1")


class TestAddressHelpers(unittest.TestCase):
    def test_addresses_raise_before_connect(self):
        tunnel = TeleportTunnel("node")
        with self.assertRaises(RuntimeError):
            _ = tunnel.api_local_address
        with self.assertRaises(RuntimeError):
            _ = tunnel.ssh_local_address
        with self.assertRaises(RuntimeError):
            _ = tunnel.ssh_endpoint

    def test_addresses_after_ports_assigned(self):
        tunnel = TeleportTunnel("node")
        tunnel.api_local_port = 51000
        tunnel.ssh_local_port = 51001
        self.assertEqual(tunnel.api_local_address, "127.0.0.1:51000")
        self.assertEqual(tunnel.ssh_local_address, "127.0.0.1:51001")
        self.assertEqual(tunnel.ssh_endpoint, ("127.0.0.1", 51001))


class TestConnect(unittest.TestCase):
    @patch("utils.teleport_tunnel._port_open", return_value=True)
    @patch("utils.teleport_tunnel._alloc_local_port", side_effect=[50443, 50022])
    @patch("utils.teleport_tunnel.subprocess.Popen")
    def test_connect_success(self, mock_popen, _alloc, _port_open):
        proc = MagicMock()
        proc.poll.return_value = None  # process still running
        mock_popen.return_value = proc
        tunnel = TeleportTunnel("node")
        tunnel.preflight = MagicMock()  # bypass real preflight
        tunnel._list_nodes = MagicMock(return_value=None)  # skip resolution

        tunnel.connect()

        self.assertEqual(tunnel.api_local_port, 50443)
        self.assertEqual(tunnel.ssh_local_port, 50022)
        mock_popen.assert_called_once()

    @patch("utils.teleport_tunnel._alloc_local_port", side_effect=[50443, 50022])
    @patch("utils.teleport_tunnel.subprocess.Popen")
    def test_connect_early_exit_raises(self, mock_popen, _alloc):
        proc = MagicMock()
        proc.poll.return_value = 1  # exited immediately
        proc.returncode = 1
        proc.communicate.return_value = ("", "access denied")
        mock_popen.return_value = proc
        tunnel = TeleportTunnel("node")
        tunnel.preflight = MagicMock()
        tunnel._list_nodes = MagicMock(return_value=None)

        with self.assertRaises(TeleportError) as ctx:
            tunnel.connect()
        self.assertIn("exited early", str(ctx.exception))

    @patch("utils.teleport_tunnel.time.sleep", return_value=None)
    @patch("utils.teleport_tunnel._port_open", return_value=False)
    @patch("utils.teleport_tunnel._alloc_local_port", side_effect=[50443, 50022])
    @patch("utils.teleport_tunnel.subprocess.Popen")
    def test_connect_timeout_raises(self, mock_popen, _alloc, _port_open, _sleep):
        proc = MagicMock()
        proc.poll.return_value = None
        mock_popen.return_value = proc
        tunnel = TeleportTunnel("node", timeout=0)
        tunnel.preflight = MagicMock()
        tunnel._list_nodes = MagicMock(return_value=None)

        with self.assertRaises(TeleportError) as ctx:
            tunnel.connect()
        self.assertIn("did not become ready", str(ctx.exception))


class TestNodeResolution(unittest.TestCase):
    """Resolve any operator-entered identifier to a unique ``user@<node-id>``.

    Models the real-world case where four clusters register a node under the
    same hostname ``Rack-CB2-U-bottom-right`` and are only distinguishable by
    their ``cluster_name``/``cluster_psnt`` labels and unique node IDs.
    """

    def setUp(self):
        # Normalized form (what _normalize_nodes produces). Note: the dial-able
        # id (metadata.name) differs from the teleport.internal/resource-id.
        self.nodes = [
            {
                "id": "42c37a40-cb28-48ba-a6cf-13657e87a179",
                "hostname": "Rack-CB2-U-bottom-right",
                "labels": {"Customer": "DigitalOcean", "cluster_psnt": "VA24460573ATL1C01"},
            },
            {
                "id": "5d385cc8-b198-4308-bd3c-7294ab6bed25",
                "hostname": "Rack-CB2-U-bottom-right",
                "labels": {"cluster_name": "CMH2-VAST-01", "cluster_psnt": "VA24180727"},
            },
            {
                "id": "733cb24e-1cfd-45f0-8e8e-f0bf7cf6d199",
                "hostname": "Rack-CB2-U-bottom-right",
                "labels": {
                    "cluster_name": "VAST-PI-01",
                    "cluster_psnt": "VA24129237",
                    "teleport.internal/resource-id": "80460164-2dd2-45f0-935c-e535f52bb357",
                },
            },
            {
                "id": "9a47922c-4541-4351-a758-94e26deb29c6",
                "hostname": "Rack-CB2-U-bottom-right",
                "labels": {"cluster_name": "CLE2-VAST-01", "cluster_psnt": "VA24186166"},
            },
        ]
        self.target_id = "733cb24e-1cfd-45f0-8e8e-f0bf7cf6d199"

    def test_parse_user_prefix(self):
        self.assertEqual(TeleportTunnel._parse_node_input("vastdata@VA24129237"), ("vastdata", "VA24129237"))
        self.assertEqual(TeleportTunnel._parse_node_input("VA24129237"), (None, "VA24129237"))
        self.assertEqual(
            TeleportTunnel._parse_node_input("vastdata@cluster_psnt=VA24129237"),
            ("vastdata", "cluster_psnt=VA24129237"),
        )

    def test_normalize_merges_static_and_cmd_labels(self):
        raw = [
            {
                "metadata": {"name": "uuid-1", "labels": {"cluster_name": "X"}},
                "spec": {"hostname": "h1", "cmd_labels": {"cluster_psnt": {"result": "VA999"}}},
            }
        ]
        nodes = TeleportTunnel._normalize_nodes(raw)
        self.assertEqual(nodes[0]["id"], "uuid-1")
        self.assertEqual(nodes[0]["hostname"], "h1")
        self.assertEqual(nodes[0]["labels"], {"cluster_name": "X", "cluster_psnt": "VA999"})

    def test_resolve_by_cluster_psnt_value(self):
        self.assertEqual(
            TeleportTunnel.resolve_node_target(self.nodes, "VA24129237", "vastdata"),
            f"vastdata@{self.target_id}",
        )

    def test_resolve_by_cluster_name_value(self):
        self.assertEqual(
            TeleportTunnel.resolve_node_target(self.nodes, "VAST-PI-01", "vastdata"),
            f"vastdata@{self.target_id}",
        )

    def test_resolve_by_node_id(self):
        self.assertEqual(
            TeleportTunnel.resolve_node_target(self.nodes, self.target_id, "vastdata"),
            f"vastdata@{self.target_id}",
        )

    def test_resolve_by_label_pair(self):
        self.assertEqual(
            TeleportTunnel.resolve_node_target(self.nodes, "cluster_psnt=VA24129237", "vastdata"),
            f"vastdata@{self.target_id}",
        )

    def test_resolve_by_full_label_blob(self):
        blob = (
            "cluster_name=VAST-PI-01,cluster_psnt=VA24129237,"
            "hostname=Rack-CB2-U-bottom-right,"
            "teleport.internal/resource-id=80460164-2dd2-45f0-935c-e535f52bb357"
        )
        self.assertEqual(
            TeleportTunnel.resolve_node_target(self.nodes, blob, "vastdata"),
            f"vastdata@{self.target_id}",
        )

    def test_resolve_preserves_inline_user(self):
        self.assertEqual(
            TeleportTunnel.resolve_node_target(self.nodes, "support@VA24129237", "vastdata"),
            f"support@{self.target_id}",
        )

    def test_ambiguous_hostname_raises_with_candidates(self):
        with self.assertRaises(TeleportError) as ctx:
            TeleportTunnel.resolve_node_target(self.nodes, "Rack-CB2-U-bottom-right", "vastdata")
        msg = str(ctx.exception)
        self.assertIn("ambiguous", msg)
        self.assertIn("VA24129237", msg)  # candidate list surfaces PSNTs

    def test_no_match_raises_with_available(self):
        with self.assertRaises(TeleportError) as ctx:
            TeleportTunnel.resolve_node_target(self.nodes, "does-not-exist", "vastdata")
        self.assertIn("No Teleport node matched", str(ctx.exception))

    def test_same_cluster_multinode_auto_picks_one(self):
        # A multi-CNode cluster: all nodes share one cluster_psnt. Entering the
        # cluster-level value should auto-pick a single node, not error.
        multinode = [
            {"id": "uuid-c1", "hostname": "VAST-X-CN1", "labels": {"cluster_name": "VAST-X", "cluster_psnt": "VA777"}},
            {"id": "uuid-c2", "hostname": "VAST-X-CN2", "labels": {"cluster_name": "VAST-X", "cluster_psnt": "VA777"}},
            {"id": "uuid-c3", "hostname": "VAST-X-CN3", "labels": {"cluster_name": "VAST-X", "cluster_psnt": "VA777"}},
        ]
        result = TeleportTunnel.resolve_node_target(multinode, "VA777", "vastdata")
        # Deterministic pick = lowest node id.
        self.assertEqual(result, "vastdata@uuid-c1")
        # Same outcome via cluster_name and the key=value label form.
        self.assertEqual(TeleportTunnel.resolve_node_target(multinode, "VAST-X", "vastdata"), "vastdata@uuid-c1")
        self.assertEqual(
            TeleportTunnel.resolve_node_target(multinode, "cluster_psnt=VA777", "vastdata"), "vastdata@uuid-c1"
        )

    def test_matches_across_different_clusters_still_ambiguous(self):
        # The unsafe case: a shared hostname across DIFFERENT clusters must
        # still error so the operator picks the intended cluster.
        with self.assertRaises(TeleportError) as ctx:
            TeleportTunnel.resolve_node_target(self.nodes, "Rack-CB2-U-bottom-right", "vastdata")
        self.assertIn("different clusters", str(ctx.exception))

    def test_resolved_target_used_in_build_command(self):
        tunnel = TeleportTunnel("VA24129237", "vastdata")
        tunnel.api_local_port = 50443
        tunnel.ssh_local_port = 50022
        tunnel._resolved_target = f"vastdata@{self.target_id}"
        cmd = tunnel._build_command()
        self.assertIn(f"vastdata@{self.target_id}", cmd)
        self.assertNotIn("-l", cmd)


class TestClose(unittest.TestCase):
    def test_close_terminates_running_process(self):
        tunnel = TeleportTunnel("node")
        proc = MagicMock()
        proc.poll.return_value = None
        tunnel._proc = proc
        tunnel.close()
        proc.terminate.assert_called_once()

    def test_close_is_idempotent(self):
        tunnel = TeleportTunnel("node")
        tunnel.close()  # no process; should not raise
        self.assertIsNone(tunnel._proc)


if __name__ == "__main__":
    unittest.main()
