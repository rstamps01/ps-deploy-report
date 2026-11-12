"""NET-7 guardrails: the vnetmap_lldp workflow never changes node configuration.

Every workflow step runs against mocked SSH while each command string is recorded, and the
workflow module sources are scanned as text. Either surface failing a rule fails the test:
no interface down/up operations, no ``ip link set``, no service state changes, no package
installs, only ``--operation show-mapping``, never ``-f``/``--force`` to the tool. The
``/userdata/switch_mapping.json`` backup/restore script is also executed under ``bash`` to
prove the original is restored (or the new file removed) on success, failure and signals.
"""

import os
import re
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

import pytest

SRC = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(SRC))

from tool_manager import ToolManager  # noqa: E402
from workflows import vnetmap_lldp_workflow as lldp_mod  # noqa: E402
from workflows.vnetmap_lldp_workflow import (  # noqa: E402
    MAPPING_FILE,
    TOOL_COMMAND,
    VnetmapLLDPWorkflow,
    build_show_mapping_script,
)

MODULE_SOURCES = [Path(lldp_mod.__file__), SRC / "workflows" / "topology_source.py"]

FORBIDDEN_PATTERNS: List[Tuple[str, str]] = [
    (r"\bif(?:down|up)\b", "interface down/up operation"),
    (r"\bip\s+link\s+set\b", "ip link set"),
    (
        r"\bsystemctl\s+(?:-\S+\s+)*"
        r"(?:start|stop|restart|try-restart|reload|reload-or-restart|enable|disable|mask|unmask)\b",
        "systemctl state change",
    ),
    (r"\b(?:yum|dnf)\b", "yum/dnf"),
    (
        r"\brpm\s+(?:-[a-zA-Z]*[iUFe][a-zA-Z]*\b|--(?:install|upgrade|freshen|erase|reinstall)\b)",
        "rpm install/upgrade/erase",
    ),
    (r"\bpip3?\s+install\b", "pip install"),
    (r"--force\b", "--force"),
    (r"vnetmap_lldp\.py\b[^;&|\n]*\s-[a-zA-Z]*f\b", "-f passed to vnetmap_lldp.py"),
]

PYTHON_INVOCATION = re.compile(r"\bpython3?\b[^;&|\n\"']*")
OPERATION_ARG = re.compile(r"--operation(?:\s+|=)['\"]?([\w-]+)")

CLUSTER_IP = "192.0.2.10"
NODE_A = "192.0.2.11"
NODE_B = "192.0.2.12"


def _violations(text: str) -> List[str]:
    found = []
    for pattern, label in FORBIDDEN_PATTERNS:
        for m in re.finditer(pattern, text):
            found.append(f"{label}: {m.group(0)!r}")
    for m in OPERATION_ARG.finditer(text):
        if m.group(1) != "show-mapping":
            found.append(f"--operation {m.group(1)!r}")
    for m in PYTHON_INVOCATION.finditer(text):
        if m.group(0).strip() != TOOL_COMMAND:
            found.append(f"python invocation other than show-mapping: {m.group(0)!r}")
    return found


def _fake_parser_module(rows=None) -> types.ModuleType:
    if rows is None:
        rows = [
            {
                "hostname": "acme-cn1",
                "node_ip": "198.51.100.11",
                "node_mgmt_ip": NODE_A,
                "interface": "enp7s0f0",
                "switch_name": "ACME-SW-01",
                "switch_ip": "ACME-SW-01",
                "port": "swp1s0",
                "mac": "",
                "network": "A",
            },
            {
                "hostname": "acme-cn1",
                "node_ip": "203.0.113.11",
                "node_mgmt_ip": NODE_A,
                "interface": "enp7s0f1",
                "switch_name": "ACME-SW-02",
                "switch_ip": "ACME-SW-02",
                "port": "swp1s0",
                "mac": "",
                "network": "B",
            },
        ]
    mod = types.ModuleType("vnetmap_lldp_parser")

    def parse_lldp_text(text):
        return {
            "available": bool(rows),
            "topology": list(rows),
            "total_connections": len(rows),
            "switch_names": sorted({r["switch_name"] for r in rows}),
            "lldp_service_status": {"active": 2, "inactive": 0},
            "operation_failed": False,
        }

    mod.parse_lldp_text = parse_lldp_text
    return mod


class _SSHRecorder:
    """Stand-in for ``run_ssh_command`` that records every command sent."""

    def __init__(self, tool_rc: int = 0, lldpd_state: str = "active"):
        self.commands: List[str] = []
        self.tool_rc = tool_rc
        self.lldpd_state = lldpd_state

    def __call__(self, host, username, password, command, timeout=30, **kwargs):
        self.commands.append(command)
        if command.strip() == "which clush":
            return 0, "/usr/bin/clush\n", ""
        if "is-active lldpd " in command:
            return 0, f"{NODE_A}: {self.lldpd_state}\n{NODE_B}: {self.lldpd_state}\n", ""
        if "is-active lldpad " in command:
            return 0, f"{NODE_A}: inactive\n{NODE_B}: inactive\n", ""
        if "rpm -q " in command:
            return (
                0,
                f"{NODE_A}: lldpad-1.0.1-13.el8.x86_64\n{NODE_A}: lldpd-1.0.18-1.el8.x86_64\n"
                f"{NODE_B}: lldpad-1.0.1-13.el8.x86_64\n{NODE_B}: package lldpd is not installed\n",
                "",
            )
        if "test -s" in command:
            return 0, "ok", ""
        if TOOL_COMMAND in command:
            out = "LLDP Connection Mapping:\n[asbuilt-reporter] restore: original restored\n"
            return self.tool_rc, out, ""
        return 0, "", ""


def _run_all_steps(tmp_path, recorder: _SSHRecorder) -> List[dict]:
    wf = VnetmapLLDPWorkflow()
    wf.set_output_dir(tmp_path)
    wf.set_credentials({"cluster_ip": CLUSTER_IP, "node_user": "vastdata", "node_password": "nodepass"})
    results = []
    with patch("workflows.vnetmap_lldp_workflow.run_ssh_command", recorder), patch(
        "tool_manager.run_ssh_command", recorder
    ), patch("script_runner.run_ssh_command", recorder), patch.dict(
        sys.modules, {"vnetmap_lldp_parser": _fake_parser_module()}
    ):
        for step in wf.get_steps():
            result = wf.run_step(step["id"])
            results.append(result)
            if not result.get("success"):
                break
    return results


class TestDetector:
    """The detector itself must catch every forbidden form, or the scans below prove nothing."""

    @pytest.mark.parametrize(
        "command",
        [
            "python3 /tmp/vast_scripts/vnetmap_lldp.py --operation ifdown ACME-SW-01",
            "python3 /tmp/vast_scripts/vnetmap_lldp.py --operation=ifup ACME-SW-01",
            "python3 /tmp/vast_scripts/vnetmap_lldp.py --operation dry-run ACME-SW-01",
            "python3 /tmp/vast_scripts/vnetmap_lldp.py --operation show-mapping -f",
            "python3 /tmp/vast_scripts/vnetmap_lldp.py -vf --operation show-mapping",
            "python3 /tmp/vast_scripts/vnetmap_lldp.py --operation show-mapping --force",
            "python3 -c 'import os'",
            "ifdown enp7s0f0",
            "sudo ip link set enp7s0f0 down",
            "clush -a 'sudo systemctl start lldpd'",
            "systemctl --now enable lldpd",
            "clush -a 'systemctl unmask lldpad'",
            "clush -a 'systemctl restart lldpad'",
            "sudo yum install -y lldpd",
            "dnf -y install lldpd",
            "rpm -ivh lldpd.rpm",
            "rpm -Uvh lldpd.rpm",
            "rpm -e lldpad",
            "pip install lldp",
        ],
    )
    def test_flags_forbidden_command(self, command):
        assert _violations(command)

    @pytest.mark.parametrize(
        "command",
        [
            "which clush",
            "clush -a 'systemctl is-active lldpd || true'",
            "clush -a 'rpm -q lldpad lldpd || true'",
            f"rm -f {MAPPING_FILE}",
            f"{TOOL_COMMAND}; exit $?",
        ],
    )
    def test_allows_read_only_command(self, command):
        assert _violations(command) == []


class TestRecordedCommands:
    def test_happy_path_runs_every_step(self, tmp_path):
        recorder = _SSHRecorder()
        results = _run_all_steps(tmp_path, recorder)
        assert len(results) == len(VnetmapLLDPWorkflow().get_steps())
        assert all(r["success"] for r in results), results

    @pytest.mark.parametrize(
        "tool_rc,lldpd_state",
        [(0, "active"), (1, "active"), (0, "inactive")],
        ids=["success", "show-mapping-fails", "lldp-not-running"],
    )
    def test_no_forbidden_command_is_sent(self, tmp_path, tool_rc, lldpd_state):
        recorder = _SSHRecorder(tool_rc=tool_rc, lldpd_state=lldpd_state)
        _run_all_steps(tmp_path, recorder)
        assert recorder.commands
        violations = [v for cmd in recorder.commands for v in _violations(cmd)]
        assert violations == []

    def test_only_python_invocation_is_show_mapping(self, tmp_path):
        recorder = _SSHRecorder()
        _run_all_steps(tmp_path, recorder)
        invocations = [m.group(0).strip() for cmd in recorder.commands for m in PYTHON_INVOCATION.finditer(cmd)]
        assert invocations == [TOOL_COMMAND]
        assert TOOL_COMMAND == f"python3 {ToolManager.REMOTE_DIR}/vnetmap_lldp.py --operation show-mapping"

    def test_no_sudo_or_lldp_client_commands_are_sent(self, tmp_path):
        recorder = _SSHRecorder()
        _run_all_steps(tmp_path, recorder)
        for cmd in recorder.commands:
            assert not re.search(r"\bsudo\b", cmd), cmd
            assert not re.search(r"\blldp(?:cli|tool|ctl)\b", cmd), cmd

    def test_readiness_does_not_run_tool_when_lldp_not_running(self, tmp_path):
        recorder = _SSHRecorder(lldpd_state="inactive")
        results = _run_all_steps(tmp_path, recorder)
        assert results[-1]["success"] is False
        assert not any(TOOL_COMMAND in cmd for cmd in recorder.commands)


class TestModuleSource:
    @pytest.mark.parametrize("path", MODULE_SOURCES, ids=lambda p: p.name)
    def test_source_has_no_forbidden_command(self, path):
        assert _violations(path.read_text()) == []

    def test_tool_command_is_the_only_python_literal(self):
        source = Path(lldp_mod.__file__).read_text()
        invocations = [m.group(0).strip() for m in PYTHON_INVOCATION.finditer(source)]
        assert invocations == [TOOL_COMMAND]


class TestSwitchMappingRestoreStructure:
    def test_backup_then_trap_then_tool(self):
        script = build_show_mapping_script()
        backup = script.index(f'cp -p {MAPPING_FILE} "$_VLM_BAK"')
        trap_exit = script.index("trap _vlm_restore EXIT")
        trap_signals = script.index("trap 'exit 1' HUP INT QUIT TERM")
        tool = script.index(TOOL_COMMAND)
        assert backup < trap_exit < tool
        assert trap_signals < tool
        assert script.count(TOOL_COMMAND) == 1

    def test_restore_function_restores_or_removes(self):
        script = build_show_mapping_script()
        body = script[script.index("_vlm_restore() {") : script.index("trap _vlm_restore EXIT")]
        assert f'cp -p "$_VLM_BAK" {MAPPING_FILE}' in body
        assert f"rm -f {MAPPING_FILE}" in body

    def test_backup_failure_aborts_before_tool(self):
        script = build_show_mapping_script()
        abort = script.index("backup-failed: could not copy")
        assert abort < script.index(TOOL_COMMAND)
        assert "exit 3" in script[abort : script.index(TOOL_COMMAND)]


BASH = shutil.which("bash")


@pytest.mark.skipif(BASH is None, reason="bash not available")
class TestSwitchMappingRestoreExecution:
    ORIGINAL = '{"saved": "by support"}\n'

    def _run(self, tmp_path, fake_tool: str, had_original: bool):
        userdata = tmp_path / "userdata"
        scripts = tmp_path / "scripts"
        userdata.mkdir()
        scripts.mkdir()
        mapping = userdata / "switch_mapping.json"
        if had_original:
            mapping.write_text(self.ORIGINAL)
        script = (
            build_show_mapping_script()
            .replace(MAPPING_FILE, str(mapping))
            .replace(ToolManager.REMOTE_DIR, str(scripts))
            .replace(TOOL_COMMAND.replace(ToolManager.REMOTE_DIR, str(scripts)), fake_tool.format(mapping=mapping))
        )
        proc = subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=30)
        return proc, mapping, scripts

    @pytest.mark.parametrize("tool_rc", [0, 1], ids=["tool-succeeds", "tool-fails"])
    def test_original_restored(self, tmp_path, tool_rc):
        proc, mapping, scripts = self._run(
            tmp_path, f"sh -c 'echo NEW > {{mapping}}; exit {tool_rc}'", had_original=True
        )
        assert proc.returncode == tool_rc
        assert mapping.read_text() == self.ORIGINAL
        assert list(scripts.iterdir()) == []
        assert "restore: original" in proc.stdout

    @pytest.mark.parametrize("tool_rc", [0, 1], ids=["tool-succeeds", "tool-fails"])
    def test_new_file_removed_when_none_existed(self, tmp_path, tool_rc):
        proc, mapping, scripts = self._run(
            tmp_path, f"sh -c 'echo NEW > {{mapping}}; exit {tool_rc}'", had_original=False
        )
        assert proc.returncode == tool_rc
        assert not mapping.exists()
        assert list(scripts.iterdir()) == []

    def test_original_restored_when_terminated(self, tmp_path):
        proc, mapping, scripts = self._run(
            tmp_path, "sh -c 'echo NEW > {mapping}; kill -TERM $PPID; exit 0'", had_original=True
        )
        assert proc.returncode != 0
        assert mapping.read_text() == self.ORIGINAL
        assert list(scripts.iterdir()) == []

    @pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root can read mode-000 files")
    def test_unreadable_original_aborts_without_running_tool(self, tmp_path):
        sentinel = tmp_path / "tool_ran"
        userdata = tmp_path / "userdata"
        userdata.mkdir()
        mapping = userdata / "switch_mapping.json"
        mapping.write_text(self.ORIGINAL)
        mapping.chmod(0)
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        script = (
            build_show_mapping_script()
            .replace(MAPPING_FILE, str(mapping))
            .replace(ToolManager.REMOTE_DIR, str(scripts))
            .replace(TOOL_COMMAND.replace(ToolManager.REMOTE_DIR, str(scripts)), f"touch {sentinel}")
        )
        try:
            proc = subprocess.run([BASH, "-c", script], capture_output=True, text=True, timeout=30)
        finally:
            mapping.chmod(0o600)
        assert proc.returncode == 3
        assert not sentinel.exists()
        assert mapping.read_text() == self.ORIGINAL
        assert list(scripts.iterdir()) == []
