import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tool_manager import ToolManager


@pytest.fixture
def tool_manager(tmp_path):
    tm = ToolManager(output_callback=MagicMock())
    tm._local_tools_dir = tmp_path / "tools"
    tm._local_tools_dir.mkdir()
    return tm


@pytest.fixture
def mock_ssh():
    with patch("tool_manager.run_ssh_command") as m:
        m.return_value = (0, "ok", "")
        yield m


class TestToolManagerInit:
    def test_initialization(self):
        tm = ToolManager()
        assert isinstance(tm, ToolManager)
        assert len(ToolManager.TOOLS) == 4

    def test_get_tool_info_known(self, tool_manager):
        info = tool_manager.get_tool_info("vnetmap.py")
        assert info is not None
        assert "url" in info
        assert "description" in info

    def test_get_tool_info_unknown(self, tool_manager):
        assert tool_manager.get_tool_info("nonexistent_tool") is None

    def test_get_all_tools_info(self, tool_manager):
        all_info = tool_manager.get_all_tools_info()
        assert len(all_info) == 4


class TestToolManagerLocalOps:
    def test_get_local_tool_path(self, tool_manager):
        p = tool_manager.get_local_tool_path("vnetmap.py")
        assert p == tool_manager._local_tools_dir / "vnetmap.py"

    @patch("tool_manager.requests.get")
    def test_update_local_tool_success(self, mock_get, tool_manager):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"test"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        ok, msg = tool_manager.update_local_tool("vnetmap.py")
        assert ok is True
        assert "vnetmap.py" in msg
        assert (tool_manager._local_tools_dir / "vnetmap.py").read_bytes() == b"test"

    @patch("tool_manager.requests.get")
    def test_update_local_tool_network_error(self, mock_get, tool_manager):
        mock_get.side_effect = requests.RequestException("fail")

        ok, msg = tool_manager.update_local_tool("vnetmap.py")
        assert ok is False
        assert "fail" in msg or "Download failed" in msg

    @patch("tool_manager.requests.get")
    def test_update_all_tools(self, mock_get, tool_manager):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b"x"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = tool_manager.update_all_tools()
        assert "tools" in result
        assert set(result["tools"].keys()) == set(ToolManager.TOOLS.keys())


class TestToolManagerDeploy:
    def test_deploy_to_cnode_internet_success(self, tool_manager, mock_ssh):
        mock_ssh.side_effect = [(0, "ok", ""), (0, "", ""), (0, "ok", ""), (0, "", "")]

        ok, msg = tool_manager.deploy_tool_to_cnode("vnetmap.py", "host", "user", "pass")
        assert ok is True
        assert "CNode" in msg or "directly" in msg

    @patch("paramiko.SSHClient")
    def test_deploy_to_cnode_internet_fail_local_fallback(self, mock_ssh_client, tool_manager, mock_ssh):
        (tool_manager._local_tools_dir / "vnetmap.py").write_bytes(b"local")

        mock_ssh.side_effect = [(0, "ok", ""), (1, "", "error"), (0, "", "")]

        mock_ssh_inst = MagicMock()
        mock_ssh_client.return_value = mock_ssh_inst
        mock_ssh_inst.get_transport.return_value = MagicMock()

        scp_mod = types.ModuleType("scp")
        mock_scp_class = MagicMock()
        mock_scp_instance = MagicMock()
        mock_scp_class.return_value = mock_scp_instance
        mock_scp_instance.__enter__.return_value = mock_scp_instance
        mock_scp_instance.__exit__.return_value = None
        scp_mod.SCPClient = mock_scp_class

        with patch.dict(sys.modules, {"scp": scp_mod}):
            ok, msg = tool_manager.deploy_tool_to_cnode("vnetmap.py", "host", "user", "pass")

        assert ok is True
        assert "cache" in msg.lower() or "Copied" in msg

    def test_deploy_to_cnode_both_fail(self, tool_manager, mock_ssh):
        mock_ssh.side_effect = [(0, "ok", ""), (1, "", "error")]

        ok, msg = tool_manager.deploy_tool_to_cnode("vnetmap.py", "host", "user", "pass")
        assert ok is False
        assert "cache" in msg.lower() or "local" in msg.lower()

    def test_deploy_ensures_remote_dir(self, tool_manager, mock_ssh):
        mock_ssh.side_effect = [(0, "ok", ""), (1, "", "error")]

        tool_manager.deploy_tool_to_cnode("vnetmap.py", "host", "user", "pass", skip_mkdir=False)
        first_cmd = mock_ssh.call_args_list[0][0][3]
        assert "mkdir -p" in first_cmd

        mock_ssh.reset_mock()
        mock_ssh.side_effect = [(1, "", "error")]

        tool_manager.deploy_tool_to_cnode("vnetmap.py", "host", "user", "pass", skip_mkdir=True)
        first_cmd2 = mock_ssh.call_args_list[0][0][3]
        assert "mkdir" not in first_cmd2
        assert "wget" in first_cmd2
