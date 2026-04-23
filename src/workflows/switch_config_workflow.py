"""
Switch Configuration Extraction Workflow

3-step workflow for extracting switch configuration:
1. Discover Switches - Fetch switch IPs from VAST API
2. Extract Configuration - SSH to each switch and pull running config
3. Save Configuration - Save extracted config to local files
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from script_runner import ScriptRunner
from utils.logger import get_logger
from utils.ssh_adapter import run_ssh_command, run_interactive_ssh, build_switch_credential_combos

logger = get_logger(__name__)


class SwitchConfigWorkflow:
    """Switch configuration extraction workflow."""

    name = "Switch Extraction"
    description = "Extract and save switch configuration for backup or replacement"
    enabled = True
    min_vast_version = "5.0"

    # Cumulus Linux 3.x/4.x (NCLU - net commands)
    CUMULUS_NCLU_COMMANDS = [
        "net show configuration",
        "net show interface",
        "net show lldp",
    ]

    # Cumulus Linux 5.x+ (NVUE - nv commands) + traditional Linux config files
    CUMULUS_NVUE_COMMANDS = [
        "nv config show",
        "cat /etc/network/interfaces",
        "nv show router bgp --applied -o json",
        "ip -br link show",
        "ip -br addr show",
        "nv show interface --applied -o json",
        "nv show service lldp --applied -o json",
    ]

    # Cumulus Linux fallback (traditional Linux commands, works on any version)
    CUMULUS_LINUX_COMMANDS = [
        "cat /etc/network/interfaces",
        "cat /etc/cumulus/ports.conf",
        "ip -br link show",
        "ip -br addr show",
        "cat /etc/lsb-release",
    ]

    # MLNX-OS / Onyx (interactive enable mode)
    ONYX_CONFIG_COMMANDS = [
        "show running-config",
        "show interfaces status",
        "show lldp interfaces",
    ]

    # Generic MLNX fallback
    MLNX_CONFIG_COMMANDS = [
        "show running-configuration",
        "show interfaces status",
        "show lldp neighbors",
        "show ip interfaces",
    ]

    def __init__(self):
        self._output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._credentials: Dict[str, Any] = {}
        self._script_runner: Optional[ScriptRunner] = None
        self._step_data: Dict[str, Any] = {}

    def set_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        self._output_callback = callback

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

    def _jump_kwargs(self) -> Dict[str, Any]:
        """Return jump-host SSH kwargs when Tech Port mode is active."""
        if self._credentials.get("tunnel_address"):
            return {
                "jump_host": self._credentials.get("cluster_ip"),
                "jump_user": self._credentials.get("node_user", "vastdata"),
                "jump_password": self._credentials.get("node_password"),
            }
        return {}

    _AUTH_FAILURE_INDICATORS = (
        "authentication failed",
        "permission denied",
        "login incorrect",
        "access denied",
    )

    @classmethod
    def _is_auth_failure(cls, stderr: str) -> bool:
        """Return True when ``stderr`` indicates a credential problem rather than
        a connectivity problem.  Used by Step 1 to decide whether to retry with
        the next password candidate or abort early."""
        if not stderr:
            return False
        lowered = stderr.lower()
        return any(token in lowered for token in cls._AUTH_FAILURE_INDICATORS)

    def emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        if self._output_callback:
            try:
                self._output_callback(level, message, details)
            except Exception:
                pass

    def get_steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": 1, "name": "Discover Switches", "description": "Fetch switch IPs from VAST API and connect"},
            {
                "id": 2,
                "name": "Extract Configuration",
                "description": "Retrieve running configuration and interface info",
            },
            {"id": 3, "name": "Save Configuration", "description": "Save configuration to local files"},
        ]

    def validate_prerequisites(self) -> tuple[bool, str]:
        required = ["cluster_ip", "username", "password", "switch_user", "switch_password"]
        missing = [k for k in required if not self._credentials.get(k)]
        if missing:
            return False, "Missing credentials: " + ", ".join(missing)
        return True, "Prerequisites met"

    def run_step(self, step_id: int) -> Dict[str, Any]:
        step_methods = {
            1: self._step_discover_switches,
            2: self._step_extract_config,
            3: self._step_save_config,
        }

        method = step_methods.get(step_id)
        if not method:
            return {"success": False, "message": f"Invalid step ID: {step_id}"}

        if self._script_runner is None:
            self._script_runner = ScriptRunner(output_callback=self._output_callback)

        try:
            return method()
        except Exception as e:
            logger.exception(f"Step {step_id} failed")
            return {"success": False, "message": str(e)}

    def _get_switch_ips_from_api(self) -> tuple[List[str], Dict[str, str]]:
        """Fetch switch management IPs and models from VAST API GET /api/switches/.

        Returns:
            Tuple of (list of IPs, dict mapping IP to model string)
        """
        import requests
        from urllib3.exceptions import InsecureRequestWarning
        import warnings

        warnings.filterwarnings("ignore", category=InsecureRequestWarning)

        api_host = self._credentials.get("tunnel_address") or self._credentials.get("cluster_ip")
        username = self._credentials.get("username", "admin")
        password = self._credentials.get("password")

        # Try /api/switches/ (works on most versions)
        url = f"https://{api_host}/api/switches/"
        self.emit("info", f"$ curl -k -u {username}:*** {url}")

        try:
            # Intentional [B501]: VAST VMS uses self-signed certs; verify_ssl disabled is the documented default.
            response = requests.get(url, auth=(username, password), verify=False, timeout=30)  # nosec B501
            response.raise_for_status()
            switches = response.json()

            ips = []
            models = {}
            self.emit("info", "")
            self.emit("info", "--- API Response ---")
            for switch in switches:
                mgmt_ip = switch.get("mgmt_ip")
                name = switch.get("name", switch.get("hostname", "unknown"))
                model = switch.get("model", "unknown")
                if mgmt_ip:
                    ips.append(mgmt_ip)
                    models[mgmt_ip] = model
                    self.emit("info", f"  Switch: {name} | Model: {model} | mgmt_ip: {mgmt_ip}")

            return ips, models
        except requests.exceptions.HTTPError as e:
            self.emit("warn", f"API returned HTTP {e.response.status_code}")
            # If /api/switches/ fails, try /api/v1/switches/
            url_v1 = f"https://{api_host}/api/v1/switches/"
            self.emit("info", f"Trying fallback: {url_v1}")
            try:
                # Intentional [B501]: VAST VMS uses self-signed certs; verify_ssl disabled is the documented default.
                response = requests.get(url_v1, auth=(username, password), verify=False, timeout=30)  # nosec B501
                response.raise_for_status()
                switches = response.json()
                ips = [s.get("mgmt_ip") for s in switches if s.get("mgmt_ip")]
                models = {s.get("mgmt_ip"): s.get("model", "") for s in switches if s.get("mgmt_ip")}
                return ips, models
            except Exception:
                return [], {}
        except Exception as e:
            self.emit("error", f"API call failed: {e}")
            return [], {}

    def _detect_switch_type(self, ip: str, user: str, password: str, api_model: str, initial_stdout: str) -> str:
        """Detect switch OS type via API model info and SSH command probes.

        Returns one of: 'cumulus_nclu', 'cumulus_nvue', 'cumulus_linux', 'onyx', 'mlnx'
        """
        combined = (api_model + " " + initial_stdout).upper()

        if "MLNX-OS" in combined or "ONYX" in combined:
            return "onyx"

        # Check for Cumulus Linux (standard SSH works, check for net/nv commands)
        # Use login_shell=True to ensure PATH is fully loaded on the switch
        rc, stdout, stderr = run_ssh_command(
            ip,
            user,
            password,
            "which nv 2>/dev/null && echo HAS_NV; which net 2>/dev/null && echo HAS_NET; cat /etc/lsb-release 2>/dev/null || true",
            timeout=10,
            login_shell=True,
            **self._jump_kwargs(),
        )
        if rc == 0 and stdout:
            probe = stdout.upper()
            if "CUMULUS" in probe or "HAS_NV" in probe or "HAS_NET" in probe:
                if "HAS_NV" in probe:
                    self.emit("info", f"  Detected Cumulus Linux (NVUE) on {ip}")
                    return "cumulus_nvue"
                if "HAS_NET" in probe:
                    self.emit("info", f"  Detected Cumulus Linux (NCLU) on {ip}")
                    return "cumulus_nclu"
                self.emit("info", f"  Detected Cumulus Linux (legacy) on {ip}")
                return "cumulus_linux"

        # Probe: 'show version' via interactive SSH for Onyx/MLNX-OS detection
        rc, stdout, stderr = run_interactive_ssh(ip, user, password, "show version", timeout=15, **self._jump_kwargs())
        if rc == 0 and stdout:
            version_upper = stdout.upper()
            if "MLNX-OS" in version_upper or "ONYX" in version_upper:
                return "onyx"

        # MSN/SN model numbers are Spectrum - could be Cumulus or MLNX-OS
        if any(tag in api_model for tag in ["MSN", "SN2", "SN3", "SN4", "SN5", "SPECTRUM"]):
            self.emit("info", f"  Spectrum switch (model: {api_model}), using Linux config extraction")
            return "cumulus_linux"

        return "mlnx"

    def _step_discover_switches(self) -> Dict[str, Any]:
        """Step 1: Discover switch IPs from VAST API and test connectivity."""
        host = self._credentials.get("cluster_ip")
        api_user = self._credentials.get("username", "admin")
        api_pass = self._credentials.get("password")
        switch_user = self._credentials.get("switch_user", "cumulus")
        switch_password = self._credentials.get("switch_password")

        # Validate credentials
        if not host:
            self.emit("error", "Cluster IP is required.")
            return {"success": False, "message": "Cluster IP is required"}
        if not api_pass:
            self.emit("error", "API Password is required to query switch inventory.")
            return {"success": False, "message": "API Password is required"}
        if not switch_password:
            self.emit("error", "Switch SSH Password is required.")
            return {"success": False, "message": "Switch SSH Password is required"}

        self.emit("info", "Discovering switches from VAST API...")
        self.emit("info", f"Cluster: {host}")
        self.emit("info", f"API User: {api_user}")
        self.emit("info", "")

        # Fetch switch IPs and models from API
        switch_ips, api_switch_models = self._get_switch_ips_from_api()

        if not switch_ips:
            self.emit("error", "No switches found via API")
            self.emit("info", "Ensure the cluster has managed switches and API credentials are correct")
            return {"success": False, "message": "No switches found via VAST API"}

        self.emit("info", "")
        self.emit("success", f"Found {len(switch_ips)} switch(es) via API: {', '.join(switch_ips)}")
        self.emit("info", "")

        # Test SSH connectivity to each switch and detect type
        self.emit("info", "Testing SSH connectivity and detecting switch type...")
        connected_switches = []
        failed_switches = []

        # Ordered candidate list (primary first).  Populated by OneShotRunner
        # when autofill is enabled; otherwise a single-entry list containing
        # the operator-entered password.
        raw_candidates = self._credentials.get("switch_password_candidates") or []
        password_candidates: list[str] = []
        if switch_password:
            password_candidates.append(switch_password)
        for pw in raw_candidates:
            if pw and pw not in password_candidates:
                password_candidates.append(pw)

        # Expand into (user, password) combos so Onyx/MLNX-OS switches that
        # require admin instead of cumulus also authenticate.  Order matches
        # ExternalPortMapper._detect_switch_os.
        credential_combos = build_switch_credential_combos(switch_user, password_candidates)
        primary_combo = credential_combos[0] if credential_combos else (switch_user, switch_password)

        for ip in switch_ips:
            model = api_switch_models.get(ip, "").upper()
            self.emit("info", f"$ ssh {switch_user}@{ip} hostname")

            rc = 1
            stdout = ""
            stderr = ""
            winning_user: Optional[str] = None
            winning_password: Optional[str] = None

            for idx, (user, candidate) in enumerate(credential_combos):
                if idx > 0:
                    self.emit(
                        "info",
                        f"  Auth failed with combo {idx}/{len(credential_combos)} — " f"retrying as {user}@{ip}",
                    )

                rc, stdout, stderr = run_ssh_command(ip, user, candidate, "hostname", timeout=15, **self._jump_kwargs())

                if rc != 0:
                    self.emit("info", f"  Standard SSH failed, trying interactive (Onyx) as {user}...")
                    rc, stdout, stderr = run_interactive_ssh(
                        ip, user, candidate, "show version", timeout=15, **self._jump_kwargs()
                    )

                if rc == 0:
                    winning_user, winning_password = user, candidate
                    break

                if not self._is_auth_failure(stderr):
                    # Connectivity-style failure: no point retrying other combos.
                    break

            if rc == 0:
                hostname = stdout.strip().split("\n")[0] if stdout else ip

                switch_type = self._detect_switch_type(
                    ip,
                    winning_user or switch_user,
                    winning_password or switch_password,
                    model,
                    stdout,
                )

                connected_switches.append(
                    {
                        "ip": ip,
                        "type": switch_type,
                        "hostname": hostname,
                        "model": model,
                        "user": winning_user or switch_user,
                        "password": winning_password or switch_password,
                    }
                )
                used_fallback = bool((winning_user, winning_password) != primary_combo and winning_user is not None)
                suffix = f" [using fallback {winning_user}@{ip}]" if used_fallback else ""
                self.emit("success", f"  Connected: {ip} ({switch_type}) - {hostname}{suffix}")
            else:
                error_msg = stderr.strip().split("\n")[-1] if stderr else "Connection failed"
                failed_switches.append({"ip": ip, "error": error_msg})
                self.emit("warn", f"  Failed: {ip} - {error_msg}")

        self._step_data["connected_switches"] = connected_switches
        self._step_data["failed_switches"] = failed_switches
        self._step_data["switch_ips"] = switch_ips

        if not connected_switches:
            return {
                "success": False,
                "message": f"Could not connect to any of {len(switch_ips)} switch(es)",
                "details": "\n".join([f"{s['ip']}: {s['error']}" for s in failed_switches]),
            }

        return {
            "success": True,
            "message": f"Connected to {len(connected_switches)} of {len(switch_ips)} switch(es)",
            "details": "\n".join([f"{s['ip']} ({s['type']}) - {s['hostname']}" for s in connected_switches]),
        }

    def _step_extract_config(self) -> Dict[str, Any]:
        """Step 2: Extract configuration from connected switches."""
        switch_user = self._credentials.get("switch_user", "cumulus")
        switch_password = self._credentials.get("switch_password")
        connected_switches = self._step_data.get("connected_switches", [])

        if not connected_switches:
            self.emit("error", "No connected switches. Run Step 1 first.")
            return {"success": False, "message": "No connected switches. Run Step 1 first."}

        self.emit("info", f"Extracting configuration from {len(connected_switches)} switch(es)...")
        self.emit("info", "")

        configs = {}

        for switch in connected_switches:
            ip = switch["ip"]
            switch_type = switch["type"]
            hostname = switch["hostname"]
            # Reuse the credentials that authenticated in Step 1.  Falls back to
            # credentials-supplied values for legacy callers that don't store them.
            effective_user = switch.get("user") or switch_user
            effective_password = switch.get("password") or switch_password

            self.emit("info", f"--- Switch: {hostname} ({ip}) - Type: {switch_type} ---")

            if switch_type == "cumulus_nclu":
                commands = self.CUMULUS_NCLU_COMMANDS
            elif switch_type == "cumulus_nvue":
                commands = self.CUMULUS_NVUE_COMMANDS
            elif switch_type == "cumulus_linux":
                commands = self.CUMULUS_LINUX_COMMANDS
            elif switch_type == "onyx":
                commands = self.ONYX_CONFIG_COMMANDS
            else:
                commands = self.MLNX_CONFIG_COMMANDS
            switch_config = {"type": switch_type, "hostname": hostname, "commands": {}}

            for cmd in commands:
                self.emit("info", f"$ ssh {effective_user}@{ip} '{cmd}'")

                if switch_type.startswith("cumulus"):
                    rc, stdout, stderr = run_ssh_command(
                        ip, effective_user, effective_password, cmd, timeout=30, **self._jump_kwargs()
                    )
                else:
                    rc, stdout, stderr = run_interactive_ssh(
                        ip, effective_user, effective_password, cmd, timeout=30, **self._jump_kwargs()
                    )
                    if rc != 0:
                        rc, stdout, stderr = run_ssh_command(
                            ip, effective_user, effective_password, cmd, timeout=30, **self._jump_kwargs()
                        )

                if rc == 0 and stdout:
                    switch_config["commands"][cmd] = stdout
                    line_count = len(stdout.strip().split("\n"))
                    self.emit("success", f"  Captured {line_count} lines")
                else:
                    error_msg = stderr.strip().split("\n")[-1] if stderr else "No output"
                    self.emit("warn", f"  No output: {error_msg}")

            configs[ip] = switch_config
            self.emit("info", "")

        self._step_data["configs"] = configs

        total_cmds = sum(len(c["commands"]) for c in configs.values())
        return {
            "success": True,
            "message": f"Extracted {total_cmds} outputs from {len(configs)} switch(es)",
            "details": "\n".join([f"{ip}: {len(cfg['commands'])} command outputs" for ip, cfg in configs.items()]),
        }

    # ------------------------------------------------------------------
    # JSON output formatting — parse raw command output into structured data
    # ------------------------------------------------------------------

    def _parse_command_output(self, cmd: str, raw_output: str) -> Any:
        """Parse a single command's raw output into structured data for JSON export.

        Returns the parsed structure, or the original string if parsing is
        not applicable or fails.
        """
        stripped = raw_output.strip()

        if cmd.endswith("-o json") or cmd.endswith("-o json\n"):
            return self._try_parse_json(stripped)

        if cmd in ("ip -br link show", "ip -br addr show"):
            return self._parse_ip_brief(stripped, addr_mode="addr" in cmd)

        if cmd == "cat /etc/network/interfaces":
            return self._parse_network_interfaces(stripped)

        if cmd == "nv config show":
            return self._try_parse_yaml(stripped)

        return raw_output

    @staticmethod
    def _try_parse_json(text: str) -> Any:
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return text

    @staticmethod
    def _try_parse_yaml(text: str) -> Any:
        try:
            import yaml

            result = yaml.safe_load(text)
            if isinstance(result, (dict, list)):
                return result
        except Exception:
            pass
        return text

    @staticmethod
    def _parse_ip_brief(text: str, addr_mode: bool = False) -> List[Dict[str, Any]]:
        """Parse ``ip -br link show`` or ``ip -br addr show`` into per-interface records."""
        interfaces: List[Dict[str, Any]] = []
        for line in text.splitlines():
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[0].rstrip("@" + parts[0].split("@")[-1]) if "@" in parts[0] else parts[0]
            parent = parts[0].split("@")[1] if "@" in parts[0] else None
            state = parts[1]
            record: Dict[str, Any] = {"name": name, "state": state}
            if parent:
                record["parent"] = parent
            if addr_mode:
                record["addresses"] = parts[2:]
            else:
                mac = parts[2] if len(parts) > 2 else None
                flags_match = re.search(r"<([^>]+)>", line)
                if mac:
                    record["mac"] = mac
                if flags_match:
                    record["flags"] = flags_match.group(1).split(",")
            interfaces.append(record)
        return interfaces

    @staticmethod
    def _parse_network_interfaces(text: str) -> Dict[str, Any]:
        """Parse /etc/network/interfaces into structured stanzas."""
        result: Dict[str, Any] = {"_comments": [], "interfaces": {}}
        current_iface: Optional[str] = None

        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("source "):
                if stripped.startswith("#"):
                    result["_comments"].append(stripped)
                continue
            if stripped.startswith("auto "):
                iface_name = stripped.split()[1]
                result["interfaces"].setdefault(iface_name, {"auto": True, "config": {}})
                continue
            if stripped.startswith("iface "):
                parts = stripped.split()
                iface_name = parts[1]
                method = parts[3] if len(parts) > 3 else "manual"
                family = parts[2] if len(parts) > 2 else "inet"
                current_iface = iface_name
                entry = result["interfaces"].setdefault(iface_name, {"auto": False, "config": {}})
                entry["family"] = family
                entry["method"] = method
                continue
            if current_iface and line.startswith(("    ", "\t")):
                key_val = stripped.split(None, 1)
                key = key_val[0]
                value = key_val[1] if len(key_val) > 1 else True
                result["interfaces"][current_iface]["config"][key] = value

        if not result["_comments"]:
            del result["_comments"]
        return result

    def _build_structured_configs(self, configs: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw command outputs into structured data for JSON export."""
        structured: Dict[str, Any] = {}
        for ip, switch_data in configs.items():
            entry: Dict[str, Any] = {
                "type": switch_data.get("type", "unknown"),
                "hostname": switch_data.get("hostname", ip),
                "commands": {},
            }
            for cmd, raw_output in switch_data.get("commands", {}).items():
                entry["commands"][cmd] = self._parse_command_output(cmd, raw_output)
            structured[ip] = entry
        return structured

    # ------------------------------------------------------------------

    def _step_save_config(self) -> Dict[str, Any]:
        """Step 3: Save configuration to local files."""
        configs = self._step_data.get("configs", {})
        if not configs:
            self.emit("error", "No configurations to save. Run Step 2 first.")
            return {"success": False, "message": "No configurations to save. Run Step 2 first."}

        self.emit("info", "Saving switch configurations...")

        local_dir = self._script_runner.get_local_dir() / "switch_configs"
        local_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = []

        # Save raw text backup files (preserves original SSH output)
        for ip, config in configs.items():
            hostname = config.get("hostname", ip)
            filename = f"switch_{hostname}_{ip.replace('.', '_')}_{timestamp}.txt"
            filepath = local_dir / filename

            cluster_ip = self._credentials.get("cluster_ip", "unknown")
            with open(filepath, "w") as f:
                f.write(f"# Switch Configuration Backup\n")
                f.write(f"# Cluster: {cluster_ip}\n")
                f.write(f"# Hostname: {hostname}\n")
                f.write(f"# IP: {ip}\n")
                f.write(f"# Type: {config['type']}\n")
                f.write(f"# Timestamp: {timestamp}\n")
                f.write("#" + "=" * 70 + "\n\n")

                for cmd, output in config["commands"].items():
                    f.write(f"\n### Command: {cmd}\n")
                    f.write("#" + "-" * 70 + "\n")
                    f.write(output)
                    f.write("\n")

            saved_files.append(str(filepath))
            self.emit("success", f"Saved: {filename}")

        # Save structured JSON (parsed command outputs)
        structured = self._build_structured_configs(configs)
        cluster_ip = self._credentials.get("cluster_ip", "unknown")
        json_file = local_dir / f"switch_configs_{timestamp}.json"
        json_file.write_text(
            json.dumps(
                {"timestamp": timestamp, "cluster_ip": cluster_ip, "switches": structured},
                indent=2,
            )
        )
        saved_files.append(str(json_file))
        self.emit("success", f"Saved: {json_file.name}")

        self.emit("info", "")
        self.emit("info", f"Output directory: {local_dir}")

        return {
            "success": True,
            "message": f"Saved {len(saved_files)} configuration files",
            "details": "\n".join(saved_files),
            "data": {"files": saved_files},
        }
