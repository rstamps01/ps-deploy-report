"""
vperfsanity Performance Test Workflow

7-step workflow for running vperfsanity performance validation:
1. Deploy Package - Download/copy vperfsanity tarball to CNode
2. Extract Package - Extract tarball to working directory
3. Prepare Infrastructure - Run vperfsanity_prepare.sh with VIP pool
4. Run Performance Tests - Execute write and read tests
5. Collect Results - Run vperfsanity_results.sh
6. Upload Results - Optionally upload results (if internet access)
7. Cleanup - Delete test data and infrastructure
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from script_runner import ScriptRunner
from utils.ssh_adapter import run_ssh_command
from utils.logger import get_logger

logger = get_logger(__name__)


class VperfsanityWorkflow:
    """vperfsanity performance validation workflow."""

    name = "vperfsanity Performance Test"
    description = "Run vperfsanity for storage performance validation"
    enabled = True
    min_vast_version = "5.0"

    PACKAGE_NAME = "vperfsanity-latest-stable.tar.gz"
    REMOTE_DIR = "/tmp/vast_scripts"
    VPERF_DIR = "/tmp/vast_scripts/vperfsanity"
    DEFAULT_VIP_POOL = "main"
    
    # vperfsanity uses admin credentials
    VPERF_USER = "admin"
    VPERF_PASSWORD = "123456"

    def __init__(self):
        self._output_callback: Optional[Callable[[str, str, Optional[str]], None]] = None
        self._credentials: Dict[str, Any] = {}
        self._script_runner: Optional[ScriptRunner] = None
        self._step_data: Dict[str, Any] = {}

    def set_output_callback(self, callback: Callable[[str, str, Optional[str]], None]) -> None:
        self._output_callback = callback
        if self._script_runner:
            self._script_runner._output_callback = callback

    def set_credentials(self, credentials: Dict[str, Any]) -> None:
        self._credentials = credentials

    def emit(self, level: str, message: str, details: Optional[str] = None) -> None:
        if self._output_callback:
            try:
                self._output_callback(level, message, details)
            except Exception:
                pass

    def get_steps(self) -> List[Dict[str, Any]]:
        return [
            {"id": 1, "name": "Deploy Package", "description": "Download vperfsanity tarball to CNode"},
            {"id": 2, "name": "Extract Package", "description": "Extract tarball to working directory"},
            {"id": 3, "name": "Prepare Infrastructure", "description": "Create test views and directories"},
            {"id": 4, "name": "Run Performance Tests", "description": "Execute write and read tests"},
            {"id": 5, "name": "Collect Results", "description": "Generate result summary"},
            {"id": 6, "name": "Upload Results", "description": "Upload results (requires internet)"},
            {"id": 7, "name": "Cleanup", "description": "Delete test data and infrastructure"},
        ]

    def validate_prerequisites(self) -> tuple[bool, str]:
        required = ["cluster_ip", "node_user", "node_password"]
        missing = [k for k in required if not self._credentials.get(k)]
        if missing:
            return False, "Missing credentials: " + ", ".join(missing)
        return True, "Prerequisites met"

    def run_step(self, step_id: int) -> Dict[str, Any]:
        step_methods = {
            1: self._step_deploy_package,
            2: self._step_extract_package,
            3: self._step_prepare_infrastructure,
            4: self._step_run_tests,
            5: self._step_collect_results,
            6: self._step_upload_results,
            7: self._step_cleanup,
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

    def _step_deploy_package(self) -> Dict[str, Any]:
        """Step 1: Deploy vperfsanity package to CNode using ToolManager."""
        from tool_manager import ToolManager

        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        # Validate credentials
        if not host:
            self.emit("error", "Cluster IP is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Cluster IP is required"}
        if not password:
            self.emit("error", "Node SSH Password is required. Please fill in Connection Settings.")
            return {"success": False, "message": "Node SSH Password is required"}

        self.emit("info", "Deploying vperfsanity package to CNode...")
        self.emit("info", f"Package: {self.PACKAGE_NAME}")
        self.emit("info", f"Target: {user}@{host}:{self.REMOTE_DIR}")
        self.emit("info", "")
        self.emit("info", "Strategy: Internet download first, local cache fallback")
        self.emit("info", "")

        tool_manager = ToolManager(output_callback=self._output_callback)

        # Deploy the package
        success, message = tool_manager.deploy_tool_to_cnode(
            self.PACKAGE_NAME, host, user, password
        )

        if not success:
            self.emit("error", f"Deployment failed: {message}")
            return {"success": False, "message": message}

        self._step_data["package_path"] = f"{self.REMOTE_DIR}/{self.PACKAGE_NAME}"
        self.emit("success", f"Package deployed to {self._step_data['package_path']}")
        return {"success": True, "message": "Package deployed successfully"}

    def _step_extract_package(self) -> Dict[str, Any]:
        """Step 2: Extract tarball to working directory."""
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        package_path = self._step_data.get("package_path", f"{self.REMOTE_DIR}/{self.PACKAGE_NAME}")

        self.emit("info", "Extracting vperfsanity package...")
        self.emit("info", f"$ ssh {user}@{host}")
        
        # Extract to the scripts directory
        extract_cmd = f"cd {self.REMOTE_DIR} && tar xf {self.PACKAGE_NAME}"
        self.emit("info", f"$ {extract_cmd}")
        self.emit("info", "")

        rc, stdout, stderr = run_ssh_command(host, user, password, extract_cmd, timeout=60)

        if rc != 0:
            self.emit("error", f"Extraction failed: {stderr}")
            return {"success": False, "message": f"Failed to extract package: {stderr}"}

        # Verify extraction
        self.emit("info", "Verifying extraction...")
        verify_cmd = f"ls -la {self.VPERF_DIR}/"
        rc, stdout, stderr = run_ssh_command(host, user, password, verify_cmd, timeout=30)

        if rc != 0:
            self.emit("error", f"Verification failed - vperfsanity directory not found")
            return {"success": False, "message": "Extraction verification failed"}

        self.emit("info", "--- Extracted Contents ---")
        for line in stdout.strip().split("\n"):
            self.emit("info", line)

        self._step_data["vperf_dir"] = self.VPERF_DIR
        self.emit("success", f"Package extracted to {self.VPERF_DIR}")
        return {"success": True, "message": "Package extracted successfully", "details": stdout}

    def _api_cleanup_cross_tenant_views(
        self, host: str, user: str, password: str,
        admin_user: str, admin_pass: str,
    ) -> None:
        """Delete any 'vperfsanity' views that exist in OTHER tenants.

        S3 bucket names are globally unique across tenants.  If a prior run
        created a view in a different tenant context, the in-script cleanup
        (which only checks the current tenant) won't find it and the new
        ``prepare`` will fail with HTTP 400 "bucket name already in use".

        This method queries ``GET /api/views/`` for every view whose alias,
        bucket, or path contains 'vperfsanity' and deletes them via the API
        before the script-based cleanup runs.
        """
        self.emit("info", "Checking for stale vperfsanity views across all tenants...")

        find_cmd = (
            f"curl -s -k -u \'{admin_user}:{admin_pass}\' "
            f"\'https://{host}/api/views/\' 2>/dev/null"
        )
        rc, stdout, _ = run_ssh_command(host, user, password, find_cmd, timeout=30)

        if rc != 0 or not stdout.strip():
            self.emit("warn", "  Could not query views API; skipping cross-tenant cleanup")
            return

        import json as _json
        try:
            data = _json.loads(stdout)
            if isinstance(data, dict):
                data = data.get("results", [])
        except Exception:
            self.emit("warn", "  Unexpected API response; skipping cross-tenant cleanup")
            return

        stale_ids = []
        for v in data:
            alias = v.get("alias", "") or ""
            bucket = v.get("bucket", "") or ""
            path = v.get("path", "") or ""
            if alias == "vperfsanity" or bucket == "vperfsanity" or path.rstrip("/").endswith("/vperfsanity"):
                stale_ids.append(v["id"])

        if not stale_ids:
            self.emit("info", "  No stale vperfsanity views found in other tenants")
            return

        for vid in stale_ids:
            self.emit("warn", f"  Deleting stale view ID {vid} (cross-tenant)")
            del_cmd = (
                f"curl -s -k -u \'{admin_user}:{admin_pass}\' "
                f"-X DELETE \'https://{host}/api/views/{vid}/\' 2>/dev/null"
            )
            rc_d, out_d, err_d = run_ssh_command(host, user, password, del_cmd, timeout=30)
            if rc_d == 0:
                self.emit("success", f"  Deleted view {vid}")
            else:
                self.emit("warn", f"  Could not delete view {vid}: {(out_d + err_d).strip()[:200]}")

    def _step_prepare_infrastructure(self) -> Dict[str, Any]:
        """Step 3: Run vperfsanity_prepare.sh to create test infrastructure.

        If a previous run left stale resources (user, view, policy), the prepare
        script may fail with HTTP 400 "bucket name already in use".  To handle
        this we:
          1. Query the VAST API for 'vperfsanity' views across ALL tenants
             and delete any that exist (cross-tenant cleanup).
          2. Run the script's own ``-c`` cleanup for the current tenant.
          3. Run the prepare script.

        Admin credentials are passed via environment variables so the script
        does not fall back to defaults that may not match this cluster.
        """
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        vip_pool = self._credentials.get("vip_pool", self.DEFAULT_VIP_POOL)
        vperf_dir = self._step_data.get("vperf_dir", self.VPERF_DIR)

        admin_user = self._credentials.get("username", self.VPERF_USER)
        admin_pass = self._credentials.get("password", self.VPERF_PASSWORD)

        self.emit("info", "Preparing vperfsanity infrastructure...")
        self.emit("info", f"VIP Pool: {vip_pool}")
        self.emit("info", f"Admin user: {admin_user}")
        self.emit("info", "")

        # --- Cross-tenant API cleanup: delete vperfsanity views in ANY tenant ---
        self._api_cleanup_cross_tenant_views(host, user, password, admin_user, admin_pass)
        self.emit("info", "")

        # --- Script-based cleanup: remove current-tenant resources ---
        self.emit("info", "Cleaning up any stale resources from prior runs...")
        self.emit("info", f"$ ssh {user}@{host}")
        cleanup_cmd = (
            f"cd {vperf_dir} && "
            f" export VAST_VMS=\'{host}\' && "
            f" export ADMIN_USER=\'{admin_user}\' && "
            f" export ADMIN_PASSWORD=\'{admin_pass}\' && "
            f"./vperfsanity_prepare.sh -c {vip_pool}"
        )
        self.emit("info", f"$ cd {vperf_dir} && ./vperfsanity_prepare.sh -c {vip_pool}")

        rc_clean, stdout_clean, stderr_clean = run_ssh_command(
            host, user, password, cleanup_cmd, timeout=120, force_tty=True,
        )
        clean_out = stdout_clean + stderr_clean
        for line in clean_out.strip().split("\n"):
            if line.strip():
                self.emit("info", f"  {line.strip()}")

        if rc_clean == 0:
            self.emit("success", "Pre-cleanup completed")
        else:
            self.emit("info", "Pre-cleanup returned warnings (may be normal for fresh clusters)")
        self.emit("info", "")

        # --- Prepare: create user, view, bucket, deploy elbencho ---
        self.emit("info", f"$ ssh {user}@{host}")
        prepare_cmd = (
            f"cd {vperf_dir} && "
            f" export VAST_VMS=\'{host}\' && "
            f" export ADMIN_USER=\'{admin_user}\' && "
            f" export ADMIN_PASSWORD=\'{admin_pass}\' && "
            f"./vperfsanity_prepare.sh {vip_pool}"
        )
        self.emit("info", f"$ cd {vperf_dir} && ./vperfsanity_prepare.sh {vip_pool}")
        self.emit("info", "")
        self.emit("info", "This may take several minutes...")

        rc, stdout, stderr = run_ssh_command(
            host, user, password, prepare_cmd, timeout=600, force_tty=True,
        )

        output = stdout + stderr
        for line in output.strip().split("\n"):
            if line.strip():
                if "error" in line.lower():
                    self.emit("error", line)
                elif "warning" in line.lower():
                    self.emit("warn", line)
                else:
                    self.emit("info", line)

        self._step_data["vip_pool"] = vip_pool
        self._step_data["prepare_output"] = output

        if rc != 0:
            self.emit("error", f"Prepare script failed with exit code {rc}")
            hint = ""
            ol = output.lower()
            if "403" in output:
                hint = "Admin credentials may be invalid (HTTP 403). Verify API user/password."
            elif "bucket name already in use" in ol or "400" in output:
                hint = "A \'vperfsanity\' view/bucket may exist in another tenant."
            elif "vip" in ol and ("not found" in ol or "error" in ol):
                hint = f"VIP pool \'{vip_pool}\' may not exist. Create it before running."
            if hint:
                self.emit("warn", f"Hint: {hint}")
            return {"success": False, "message": f"Prepare failed (rc={rc})", "details": output[:1000]}

        self.emit("success", "Infrastructure preparation completed")
        return {"success": True, "message": "Infrastructure prepared", "details": output[:500]}

    def _step_run_tests(self) -> Dict[str, Any]:
        """Step 4: Run vperfsanity write and read tests."""
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")
        
        vip_pool = self._step_data.get("vip_pool", self.DEFAULT_VIP_POOL)
        vperf_dir = self._step_data.get("vperf_dir", self.VPERF_DIR)

        self.emit("info", "Running vperfsanity performance tests...")
        self.emit("info", f"VIP Pool: {vip_pool}")
        self.emit("info", "Test: Write (-w) and Read (-r)")
        self.emit("info", "")
        self.emit("info", f"$ ssh {user}@{host}")

        run_cmd = f"cd {vperf_dir} && export VAST_VMS='{host}' && ./vperfsanity_run.sh -w -r {vip_pool}"
        self.emit("info", f"$ {run_cmd}")
        self.emit("info", "")
        self.emit("warn", "This test may take 30+ minutes. Please wait...")
        self.emit("info", "")

        # Long timeout for performance tests, force_tty for interactive output
        rc, stdout, stderr = run_ssh_command(
            host, user, password, run_cmd, timeout=3600, force_tty=True
        )

        output = stdout + stderr
        for line in output.strip().split("\n"):
            if line.strip():
                ll = line.lower()
                if "error" in ll:
                    self.emit("error", line)
                elif "warning" in ll or "warn" in ll:
                    self.emit("warn", line)
                elif "pass" in ll or "success" in ll or "complete" in ll:
                    self.emit("success", line)
                else:
                    self.emit("info", line)

        self._step_data["test_output"] = output
        self._step_data["test_rc"] = rc

        if rc != 0:
            self.emit("error", f"Tests failed with exit code {rc}")
            hint = ""
            ol = output.lower()
            if "no such file or directory" in ol and "elbencho" in ol:
                hint = ("elbencho was not installed on the CNodes. "
                        "This usually means Step 3 (Prepare Infrastructure) "
                        "did not complete successfully. Re-run from Step 3.")
            if hint:
                self.emit("warn", f"Hint: {hint}")
            return {"success": False, "message": f"Tests failed (rc={rc})", "details": output[-1000:]}

        self.emit("success", "Performance tests completed")
        return {"success": True, "message": "Tests completed", "details": output[-1000:]}

    def _step_collect_results(self) -> Dict[str, Any]:
        """Step 5: Run vperfsanity_results.sh to generate summary."""
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")
        
        vperf_dir = self._step_data.get("vperf_dir", self.VPERF_DIR)

        self.emit("info", "Collecting vperfsanity results...")
        self.emit("info", f"$ ssh {user}@{host}")

        results_cmd = f"cd {vperf_dir} && ./vperfsanity_results.sh"
        self.emit("info", f"$ {results_cmd}")
        self.emit("info", "")

        rc, stdout, stderr = run_ssh_command(
            host, user, password, results_cmd, timeout=120, force_tty=True
        )

        output = stdout + stderr

        self.emit("info", "--- Results Summary ---")
        for line in output.strip().split("\n"):
            if line.strip():
                self.emit("info", line)
        self.emit("info", "-" * 40)

        # Save results locally
        local_dir = Path(__file__).parent.parent.parent / "output" / "scripts"
        local_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = local_dir / f"vperfsanity_results_{host}_{timestamp}.txt"
        results_file.write_text(output)

        self._step_data["results_output"] = output
        self._step_data["results_file"] = str(results_file)

        self.emit("success", f"Results saved to: {results_file}")
        return {"success": True, "message": "Results collected", "details": output}

    def _step_upload_results(self) -> Dict[str, Any]:
        """Step 6: Upload results if cluster has internet access."""
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")
        
        vperf_dir = self._step_data.get("vperf_dir", self.VPERF_DIR)

        self.emit("info", "Attempting to upload results...")
        self.emit("info", "(Requires cluster internet access)")
        self.emit("info", "")
        self.emit("info", f"$ ssh {user}@{host}")

        upload_cmd = f"cd {vperf_dir} && ./vperfsanity_results.sh -U"
        self.emit("info", f"$ {upload_cmd}")
        self.emit("info", "")

        rc, stdout, stderr = run_ssh_command(
            host, user, password, upload_cmd, timeout=120, force_tty=True
        )

        output = stdout + stderr

        for line in output.strip().split("\n"):
            if line.strip():
                self.emit("info", line)

        if rc != 0:
            self.emit("warn", "Upload may have failed (no internet access?)")
            self.emit("info", "Results are still available locally from Step 5")
            return {"success": True, "message": "Upload skipped (no internet)", "details": output}

        self.emit("success", "Results uploaded successfully")
        return {"success": True, "message": "Results uploaded", "details": output}

    def _step_cleanup(self) -> Dict[str, Any]:
        """Step 7: Clean up test data and infrastructure."""
        host = self._credentials.get("cluster_ip")
        user = self._credentials.get("node_user", "vastdata")
        password = self._credentials.get("node_password")

        vip_pool = self._step_data.get("vip_pool", self._credentials.get("vip_pool", self.DEFAULT_VIP_POOL))
        vperf_dir = self._step_data.get("vperf_dir", self.VPERF_DIR)
        admin_user = self._credentials.get("username", self.VPERF_USER)
        admin_pass = self._credentials.get("password", self.VPERF_PASSWORD)

        self.emit("info", "Cleaning up vperfsanity test environment...")
        self.emit("info", f"$ ssh {user}@{host}")
        self.emit("info", "")

        # Delete generated test files
        cleanup_run_cmd = f"cd {vperf_dir} && export VAST_VMS='{host}' && ./vperfsanity_run.sh -c {vip_pool}"
        self.emit("info", f"$ {cleanup_run_cmd}")

        rc1, stdout1, stderr1 = run_ssh_command(
            host, user, password, cleanup_run_cmd, timeout=300, force_tty=True,
        )

        output1 = stdout1 + stderr1
        for line in output1.strip().split("\n"):
            if line.strip():
                self.emit("info", line)

        self.emit("info", "")

        # Delete infrastructure (user, view, policy) -- needs admin creds
        cleanup_prep_cmd = (
            f"cd {vperf_dir} && "
            f" export VAST_VMS=\'{host}\' && "
            f" export ADMIN_USER=\'{admin_user}\' && "
            f" export ADMIN_PASSWORD=\'{admin_pass}\' && "
            f"./vperfsanity_prepare.sh -c {vip_pool}"
        )
        self.emit("info", f"$ cd {vperf_dir} && ./vperfsanity_prepare.sh -c {vip_pool}")

        rc2, stdout2, stderr2 = run_ssh_command(
            host, user, password, cleanup_prep_cmd, timeout=300, force_tty=True,
        )

        output2 = stdout2 + stderr2
        for line in output2.strip().split("\n"):
            if line.strip():
                self.emit("info", line)

        # Remove package files
        self.emit("info", "")
        self.emit("info", "Removing package files...")
        rm_cmd = f"rm -rf {self.REMOTE_DIR}/{self.PACKAGE_NAME} {vperf_dir}"
        self.emit("info", f"$ {rm_cmd}")

        run_ssh_command(host, user, password, rm_cmd, timeout=30)

        overall_success = rc1 == 0 and rc2 == 0

        if overall_success:
            self.emit("success", "Cleanup completed successfully")
        else:
            self.emit("warn", "Cleanup completed with some warnings")

        return {
            "success": True,
            "message": "Cleanup completed",
            "details": f"Run cleanup: rc={rc1}\nPrepare cleanup: rc={rc2}",
        }
