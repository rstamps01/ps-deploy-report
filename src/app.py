"""
VAST As-Built Report Generator - Web UI Application

Flask-based web interface providing a browser GUI for generating reports,
browsing output, editing configuration, and streaming live progress.
"""

import json
import os
import queue
import re
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast
from urllib.parse import unquote, urlparse

from flask import (
    Flask,
    Response,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
    send_from_directory,
)

# Ensure src/ is on the path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))

# Ensure Homebrew's shared libraries are discoverable on macOS (needed for cairosvg → libcairo)
if sys.platform == "darwin":
    _brew_lib = Path("/opt/homebrew/lib")
    if _brew_lib.is_dir():
        _dyld = os.environ.get("DYLD_FALLBACK_LIBRARY_PATH", "")
        if str(_brew_lib) not in _dyld:
            os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = f"{_brew_lib}:{_dyld}" if _dyld else str(_brew_lib)

from utils import get_bundle_dir, get_data_dir  # noqa: E402
from utils.logger import enable_sse_logging, get_logger, get_sse_queue  # noqa: E402
from hardware_library import get_builtin_devices_for_ui  # noqa: E402

logger = get_logger(__name__)

APP_VERSION = "1.5.6"

_DOC_REGISTRY = [
    {"id": "overview", "title": "Overview", "category": "Getting Started", "path": "README.md"},
    {
        "id": "installation",
        "title": "Installation Guide",
        "category": "Getting Started",
        "path": "docs/deployment/INSTALLATION-GUIDE.md",
    },
    {
        "id": "permissions",
        "title": "Permissions & Access",
        "category": "Getting Started",
        "path": "docs/deployment/PERMISSIONS-GUIDE.md",
    },
    {
        "id": "port-mapping",
        "title": "Port Mapping Guide",
        "category": "Using the Tool",
        "path": "docs/deployment/PORT-MAPPING-GUIDE.md",
    },
    {"id": "update", "title": "Update & Upgrade", "category": "Maintenance", "path": "docs/deployment/UPDATE-GUIDE.md"},
    {
        "id": "deployment",
        "title": "Production Deployment",
        "category": "Maintenance",
        "path": "docs/deployment/DEPLOYMENT.md",
    },
    {
        "id": "uninstall",
        "title": "Uninstall Guide",
        "category": "Maintenance",
        "path": "docs/deployment/UNINSTALL-GUIDE.md",
    },
    {
        "id": "advanced-operations",
        "title": "Advanced Operations Guide",
        "category": "Using the Tool",
        "path": "docs/ADVANCED-OPERATIONS.md",
    },
    {
        "id": "post-install-validation",
        "title": "Post-Install Validation",
        "category": "Using the Tool",
        "path": "docs/POST-INSTALL-VALIDATION.md",
    },
    {"id": "api-reference", "title": "API Reference", "category": "Reference", "path": "docs/API-REFERENCE.md"},
    {
        "id": "ebox-api-discovery",
        "title": "EBox API (v7) Discovery",
        "category": "Reference",
        "path": "docs/api/EBOX_API_V7_DISCOVERY.md",
    },
    {"id": "changelog", "title": "Changelog", "category": "Reference", "path": "CHANGELOG.md"},
]


def _build_doc_link_map() -> Dict[str, str]:
    """Build map of doc path variants (for link rewriting) to doc_id."""
    link_map = {}
    for doc in _DOC_REGISTRY:
        doc_id = doc["id"]
        path = doc["path"]
        link_map[path] = doc_id
        path_norm = path.replace("\\", "/")
        link_map[path_norm] = doc_id
        parts = path_norm.split("/")
        if parts:
            link_map[parts[-1]] = doc_id
        if len(parts) > 1:
            link_map["/".join(parts[1:])] = doc_id
    return link_map


_DOC_LINK_MAP = _build_doc_link_map()


def _rewrite_doc_links_in_html(html: str) -> str:
    """Rewrite internal doc .md links to /docs#<doc_id> so they open the correct in-app doc."""

    def replace_href(match: re.Match) -> str:
        href = match.group(1)
        if not href or href.startswith("#") or "docs#" in href:
            return str(match.group(0))
        parsed = urlparse(unquote(href))
        path = (parsed.path or "").strip().lstrip("/")
        if path.startswith("./"):
            path = path[2:]
        if not path.endswith(".md"):
            return str(match.group(0))
        doc_id = _DOC_LINK_MAP.get(path) or _DOC_LINK_MAP.get(path.split("/")[-1])
        if doc_id:
            return f'<a href="/docs#{doc_id}"'
        return str(match.group(0))

    return re.sub(r'<a\s+href="([^"]*)"', replace_href, html)


# ---------------------------------------------------------------------------
# Flask application factory
# ---------------------------------------------------------------------------


def create_flask_app(config: Optional[Dict[str, Any]] = None) -> Flask:
    """Build and configure the Flask application."""
    bundle_dir = get_bundle_dir()
    data_dir = get_data_dir()
    template_dir = bundle_dir / "frontend" / "templates"
    static_dir = bundle_dir / "frontend" / "static"

    app = Flask(
        __name__,
        template_folder=str(template_dir),
        static_folder=str(static_dir),
    )
    app.secret_key = os.urandom(24)

    reports_dir = data_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    config_dir = data_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.yaml"
    if not config_path.exists():
        # Bootstrap the user's runtime config from the tracked template.
        # ``config/config.yaml`` itself is gitignored so site-specific values
        # (e.g. default switch passwords) never land in the repo; operators
        # populate them in the copy that lives under the per-install data dir.
        template_src = bundle_dir / "config" / "config.yaml.template"
        if not template_src.exists():
            # Fall back to any legacy ``config.yaml`` shipped next to the
            # template (older bundles) so upgrading installs keep working.
            template_src = bundle_dir / "config" / "config.yaml"
        if template_src.exists():
            config_path.write_text(template_src.read_text())

    app.config["BASE_DIR"] = str(data_dir)
    app.config["BUNDLE_DIR"] = str(bundle_dir)
    app.config["DEFAULT_OUTPUT_DIR"] = str(reports_dir)
    app.config["OUTPUT_DIRS"] = {str(reports_dir)}
    app.config["CONFIG_PATH"] = str(config_path)
    app.config["CONFIG_TEMPLATE"] = str(bundle_dir / "config" / "config.yaml.template")
    app.config["PROFILES_PATH"] = str(config_dir / "cluster_profiles.json")
    app.config["LIBRARY_PATH"] = str(config_dir / "device_library.json")
    user_images_dir = config_dir / "hardware_images"
    user_images_dir.mkdir(parents=True, exist_ok=True)
    app.config["USER_IMAGES_DIR"] = str(user_images_dir)
    app.config["REPORT_CONFIG"] = config or {}

    # Background job state shared across requests
    app.config["JOB_RUNNING"] = False
    app.config["JOB_RESULT"] = None
    app.config["JOB_PROGRESS"] = {"percent": 0, "phase": "", "label": ""}
    app.config["JOB_LOCK"] = threading.Lock()
    app.config["JOB_CANCEL"] = threading.Event()

    # Health check background job state (independent from report job)
    app.config["HEALTH_JOB_RUNNING"] = False
    app.config["HEALTH_JOB_RESULT"] = None
    app.config["HEALTH_JOB_PROGRESS"] = {"percent": 0, "phase": "", "label": ""}
    app.config["HEALTH_JOB_LOCK"] = threading.Lock()
    app.config["HEALTH_JOB_CANCEL"] = threading.Event()

    # One-shot background job state (independent from workflow and report jobs)
    app.config["ONESHOT_RUNNING"] = False
    app.config["ONESHOT_RESULT"] = None
    app.config["ONESHOT_LOCK"] = threading.Lock()
    app.config["ONESHOT_CANCEL"] = threading.Event()
    app.config["ONESHOT_RUNNER"] = None
    # Map cluster_ip -> {"bundle_path": str, "run_started_at": str,
    #                    "operation_status": dict}.  Populated at the end of
    # a successful one-shot run so the Download Results button can hand
    # back the exact bundle the runner produced (with freshness filters
    # applied) instead of rebuilding and silently importing pre-run
    # leftovers.  Rehydrated from disk on first request after a server
    # restart by scanning ``output/bundles/*.zip`` manifests.
    app.config["ONESHOT_LAST_BUNDLE"] = {}
    app.config["ONESHOT_LAST_BUNDLE_LOCK"] = threading.Lock()
    app.config["ONESHOT_LAST_BUNDLE_REHYDRATED"] = False

    # Developer Mode - enables Advanced Operations page
    # Set via --dev-mode flag or VAST_DEV_MODE environment variable
    app.config["DEVELOPER_MODE"] = (
        config.get("DEVELOPER_MODE", False)
        if config
        else os.environ.get("VAST_DEV_MODE", "").lower() in ("1", "true", "yes")
    )

    _register_routes(app)
    return app


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


def _register_routes(app: Flask) -> None:

    # -- Context processor to pass developer_mode to all templates ----------
    @app.context_processor
    def inject_developer_mode():
        return {"developer_mode": app.config.get("DEVELOPER_MODE", False)}

    # -- Route guard for Developer Mode pages --------------------------------
    @app.before_request
    def check_developer_mode_access():
        if request.path in ("/advanced-ops", "/health", "/config"):
            if not app.config.get("DEVELOPER_MODE", False):
                return (
                    jsonify(
                        {
                            "error": "Developer Mode required",
                            "message": "Start the application with --dev-mode flag to access this page",
                        }
                    ),
                    403,
                )

    # -- Dashboard ----------------------------------------------------------

    @app.route("/")
    def dashboard():
        return render_template("dashboard.html", version=APP_VERSION)

    @app.route("/api/dashboard/status")
    def dashboard_status():
        """Lightweight status snapshot for the Dashboard Quick Start panel."""
        from tool_manager import ToolManager

        job_running = app.config["JOB_RUNNING"]
        health_running = app.config.get("HEALTH_JOB_RUNNING", False)
        job_label = "Report Running" if job_running else ("Health Check Running" if health_running else "Idle")

        reports = _list_reports(app.config["OUTPUT_DIRS"])
        last_report = reports[0] if reports else None

        try:
            manager = ToolManager()
            tools = manager.get_all_tools_info()
            cached = sum(1 for t in tools if t and t.get("cached"))
            tools_total = len(tools)
        except Exception:
            cached, tools_total = 0, 0

        profiles = _load_profiles(app.config["PROFILES_PATH"])

        try:
            from result_scanner import ResultScanner

            scanner = ResultScanner(profiles=profiles)
            all_results = scanner.scan_all()
            result_counts = {k: len(v) for k, v in all_results.items()}
        except Exception:
            result_counts = {}

        return jsonify(
            {
                "job_status": job_label,
                "job_active": job_running or health_running,
                "last_report": (
                    {
                        "name": last_report["name"],
                        "modified": last_report["modified"],
                        "type": last_report["type"],
                    }
                    if last_report
                    else None
                ),
                "total_reports": len(reports),
                "tools_cached": cached,
                "tools_total": tools_total,
                "profiles_count": len(profiles),
                "result_counts": result_counts,
            }
        )

    # -- Generate -----------------------------------------------------------

    @app.route("/generate", methods=["GET"])
    def generate_form():
        return render_template(
            "generate.html",
            version=APP_VERSION,
            job_running=app.config["JOB_RUNNING"],
        )

    @app.route("/generate", methods=["POST"])
    def generate_start():
        with app.config["JOB_LOCK"]:
            if app.config["JOB_RUNNING"]:
                return jsonify({"error": "A report is already being generated"}), 409

        form = request.form
        cluster_ip = form.get("cluster_ip", "").strip()
        if not cluster_ip:
            return jsonify({"error": "Cluster IP is required"}), 400

        params = {
            "cluster_ip": cluster_ip,
            "auth_method": form.get("auth_method", "password"),
            "username": form.get("username", ""),
            "password": form.get("password", ""),
            "token": form.get("token", ""),
            "output_dir": app.config["DEFAULT_OUTPUT_DIR"],
            "enable_port_mapping": form.get("enable_port_mapping") == "on",
            "include_health_check": form.get("include_health_check") == "1",
            "switch_user": form.get("switch_user", "cumulus"),
            "switch_password": form.get("switch_password", ""),
            "node_user": form.get("node_user", "vastdata"),
            "node_password": form.get("node_password", ""),
            "verbose": form.get("verbose") == "on",
            "switch_placement": form.get("switch_placement", "auto"),
            "proxy_jump": form.get("proxy_jump") == "on",
            "tech_port": form.get("tech_port") == "on",
            "run_vnetmap": form.get("run_vnetmap") == "1",
            # RM-13: mirror the Test Suite tile so the Reporter tile also
            # honours "Advanced -> Autofill Password".  When ticked, the
            # backend expands the single UI-entered ``switch_password``
            # into a candidate list that includes the operator's config/
            # env entries plus the published VAST + Cumulus defaults, so
            # switches using a different default auth successfully.
            "use_default_creds": form.get("use_default_creds") == "on",
        }

        if params["switch_placement"] == "manual":
            raw_mp = form.get("manual_placements", "[]")
            try:
                params["manual_placements"] = json.loads(raw_mp)
            except (json.JSONDecodeError, TypeError):
                return jsonify({"error": "Invalid manual_placements JSON"}), 400

        app.config["JOB_CANCEL"].clear()
        thread = threading.Thread(target=_run_report_job, args=(app, params), daemon=True)
        thread.start()
        return jsonify({"status": "started"})

    @app.route("/generate/status")
    def generate_status():
        resp = jsonify(
            {
                "running": app.config["JOB_RUNNING"],
                "result": app.config["JOB_RESULT"],
                "progress": app.config["JOB_PROGRESS"],
            }
        )
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["Pragma"] = "no-cache"
        return resp

    @app.route("/generate/cancel", methods=["POST"])
    def generate_cancel():
        with app.config["JOB_LOCK"]:
            if not app.config["JOB_RUNNING"]:
                return jsonify({"status": "no_job"})
            app.config["JOB_CANCEL"].set()
            app.config["JOB_RUNNING"] = False
            app.config["JOB_PROGRESS"] = {"percent": 0, "phase": "", "label": ""}
            app.config["JOB_RESULT"] = {
                "success": False,
                "error": "Report generation cancelled by user",
            }
        return jsonify({"status": "cancelled"})

    # -- Application shutdown ------------------------------------------------

    @app.route("/shutdown", methods=["POST"])
    def shutdown():
        server = app.config.get("_SERVER")
        if server is not None:
            threading.Thread(target=server.shutdown, daemon=True).start()
        else:
            threading.Thread(target=lambda: os._exit(0), daemon=True).start()
        return jsonify({"status": "shutting_down"})

    # -- SSE log stream -----------------------------------------------------

    @app.route("/stream/logs")
    def stream_logs():
        def event_stream():
            log_queue = get_sse_queue()
            while True:
                try:
                    entry = log_queue.get(timeout=1)
                    data = json.dumps(entry)
                    yield f"data: {data}\n\n"
                except queue.Empty:
                    yield ": keepalive\n\n"

        return Response(event_stream(), mimetype="text/event-stream")

    # -- Health Check -------------------------------------------------------

    @app.route("/health")
    def health_page():
        """Health check page."""
        return render_template("health.html", version=APP_VERSION)

    @app.route("/health/run", methods=["POST"])
    def health_run():
        """Start a health check job."""
        with app.config["HEALTH_JOB_LOCK"]:
            if app.config["HEALTH_JOB_RUNNING"]:
                return jsonify({"status": "error", "message": "Health check already running"}), 409
            app.config["HEALTH_JOB_RUNNING"] = True
            app.config["HEALTH_JOB_RESULT"] = None
            app.config["HEALTH_JOB_CANCEL"].clear()

        params = {
            "cluster_ip": request.form.get("cluster_ip", "").strip(),
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", ""),
            "api_token": request.form.get("api_token", "").strip(),
            "tiers": request.form.getlist("tiers", type=int) or [1],
            "node_user": request.form.get("node_user", "").strip(),
            "node_password": request.form.get("node_password", ""),
            "switch_user": request.form.get("switch_user", "").strip(),
            "switch_password": request.form.get("switch_password", ""),
        }
        if not params["cluster_ip"]:
            with app.config["HEALTH_JOB_LOCK"]:
                app.config["HEALTH_JOB_RUNNING"] = False
            return jsonify({"status": "error", "message": "Cluster IP required"}), 400

        thread = threading.Thread(target=_run_health_job, args=(app, params), daemon=True)
        thread.start()
        return jsonify({"status": "started"})

    @app.route("/health/status")
    def health_status():
        """Get health check job status."""
        return jsonify(
            {
                "running": app.config["HEALTH_JOB_RUNNING"],
                "result": app.config["HEALTH_JOB_RESULT"],
                "progress": app.config["HEALTH_JOB_PROGRESS"],
            }
        )

    @app.route("/health/cancel", methods=["POST"])
    def health_cancel():
        """Cancel running health check."""
        if app.config["HEALTH_JOB_RUNNING"]:
            app.config["HEALTH_JOB_CANCEL"].set()
            return jsonify({"status": "cancelled"})
        return jsonify({"status": "no_job"})

    @app.route("/health/results")
    def health_results():
        """Get the latest health check results JSON."""
        result = app.config.get("HEALTH_JOB_RESULT")
        if result and result.get("success"):
            return jsonify(result.get("report", {}))
        return jsonify({"error": "No results available"}), 404

    # -- Reporter (standard UI) -----------------------------------------------

    @app.route("/reporter")
    def reporter_page():
        """Reporter page — future replacement for the Generate page.

        Uses the same Advanced Ops backend infrastructure but is accessible
        in the standard (non-developer) UI.
        """
        config = _load_yaml(app.config["CONFIG_PATH"])
        adv = config.get("advanced_operations", {})
        ssh_cfg = config.get("ssh", {})
        return render_template(
            "reporter.html",
            version=APP_VERSION,
            cfg_proxy_jump=ssh_cfg.get("proxy_jump", True),
            cfg_tech_port=ssh_cfg.get("tech_port_mode", False),
            cfg_default_mode=adv.get("default_mode", "reporter"),
            cfg_switch_placement=adv.get("default_switch_placement", "manual"),
            cfg_autofill_passwords=adv.get("autofill_default_passwords", True),
            cfg_vperfsanity_default=adv.get("vperfsanity_default_selected", False),
        )

    # -- Advanced Operations (Developer Mode) --------------------------------

    @app.route("/advanced-ops")
    def advanced_ops_page():
        """Advanced Operations page for step-by-step script workflows.

        This page is only accessible when Developer Mode is enabled (--dev-mode flag).
        The before_request guard will return 403 if Developer Mode is not enabled.
        """
        config = _load_yaml(app.config["CONFIG_PATH"])
        adv = config.get("advanced_operations", {})
        ssh_cfg = config.get("ssh", {})
        defaults = adv.get("defaults", {})
        return render_template(
            "advanced_ops.html",
            version=APP_VERSION,
            cfg_proxy_jump=ssh_cfg.get("proxy_jump", True),
            cfg_tech_port=ssh_cfg.get("tech_port_mode", False),
            cfg_autofill_passwords=adv.get("autofill_default_passwords", True),
            cfg_defaults=defaults,
        )

    @app.route("/advanced-ops/workflows")
    def advanced_ops_workflows():
        """Get list of available workflows."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        return jsonify({"workflows": manager.get_workflows()})

    @app.route("/advanced-ops/workflows/<workflow_id>")
    def advanced_ops_workflow_detail(workflow_id: str):
        """Get workflow details including steps."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        workflow = manager.get_workflow(workflow_id)
        if not workflow:
            return jsonify({"error": "Workflow not found"}), 404
        # Remove non-serializable _instance before returning
        serializable = {k: v for k, v in workflow.items() if k != "_instance"}
        return jsonify(serializable)

    @app.route("/advanced-ops/start", methods=["POST"])
    def advanced_ops_start():
        """Start a workflow."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        if manager.is_running():
            return jsonify({"error": "A workflow is already running"}), 409

        workflow_id = request.form.get("workflow_id", "").strip()
        if not workflow_id:
            return jsonify({"error": "workflow_id required"}), 400

        credentials = {
            "cluster_ip": request.form.get("cluster_ip", "").strip(),
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", ""),
            "api_token": request.form.get("api_token", "").strip(),
            "node_user": request.form.get("node_user", "").strip(),
            "node_password": request.form.get("node_password", ""),
            "switch_user": request.form.get("switch_user", "").strip(),
            "switch_password": request.form.get("switch_password", ""),
        }

        if not manager.start_workflow(workflow_id, credentials):
            return jsonify({"error": "Failed to start workflow"}), 500

        return jsonify({"status": "started", "workflow_id": workflow_id})

    @app.route("/advanced-ops/run-step", methods=["POST"])
    def advanced_ops_run_step():
        """Run a specific step."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        step_id = request.form.get("step_id", type=int)
        if not step_id:
            return jsonify({"error": "step_id required"}), 400

        credentials = {
            "cluster_ip": request.form.get("cluster_ip", "").strip(),
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", ""),
            "node_user": request.form.get("node_user", "").strip(),
            "node_password": request.form.get("node_password", ""),
            "switch_user": request.form.get("switch_user", "").strip(),
            "switch_password": request.form.get("switch_password", ""),
            "vip_pool": request.form.get("vip_pool", "main").strip(),
        }

        result = manager.run_step(step_id, credentials)
        return jsonify(
            {
                "status": result.status.value,
                "message": result.message,
                "details": result.details,
                "duration_ms": result.duration_ms,
            }
        )

    @app.route("/advanced-ops/run-all", methods=["POST"])
    def advanced_ops_run_all():
        """Run all steps in the current workflow."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        credentials = {
            "cluster_ip": request.form.get("cluster_ip", "").strip(),
            "username": request.form.get("username", "").strip(),
            "password": request.form.get("password", ""),
            "node_user": request.form.get("node_user", "").strip(),
            "node_password": request.form.get("node_password", ""),
            "switch_user": request.form.get("switch_user", "").strip(),
            "switch_password": request.form.get("switch_password", ""),
            "vip_pool": request.form.get("vip_pool", "main").strip(),
        }

        # Run in background thread
        thread = threading.Thread(target=manager.run_all_steps, args=(credentials,), daemon=True)
        thread.start()
        return jsonify({"status": "started"})

    @app.route("/advanced-ops/status")
    def advanced_ops_status():
        """Get current workflow status."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        state = manager.get_current_state()
        return jsonify({"state": state, "running": manager.is_running()})

    @app.route("/advanced-ops/cancel", methods=["POST"])
    def advanced_ops_cancel():
        """Cancel the current workflow."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        if manager.cancel():
            return jsonify({"status": "cancelled"})
        return jsonify({"status": "no_workflow"})

    @app.route("/advanced-ops/reset", methods=["POST"])
    def advanced_ops_reset():
        """Reset the workflow state."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        manager.reset()
        return jsonify({"status": "reset"})

    @app.route("/advanced-ops/output")
    def advanced_ops_output():
        """Get output buffer entries."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        since = request.args.get("since", 0, type=int)
        entries = manager.get_output(since)
        return jsonify({"entries": entries, "count": len(entries)})

    # -- Tool Management -----------------------------------------------------

    @app.route("/advanced-ops/tools")
    def advanced_ops_tools():
        """Get information about all deployment tools."""
        from tool_manager import ToolManager

        manager = ToolManager()
        tools = manager.get_all_tools_info()
        return jsonify({"tools": tools})

    @app.route("/advanced-ops/tools/update", methods=["POST"])
    def advanced_ops_tools_update():
        """Update all deployment tools in local cache."""
        from tool_manager import ToolManager
        from advanced_ops import get_advanced_ops_manager

        ops_manager = get_advanced_ops_manager()
        tool_manager = ToolManager(output_callback=ops_manager._emit_output)

        results = tool_manager.update_all_tools()
        return jsonify(results)

    @app.route("/advanced-ops/tools/deploy", methods=["POST"])
    def advanced_ops_tools_deploy():
        """Deploy tools to CNode."""
        from tool_manager import ToolManager
        from advanced_ops import get_advanced_ops_manager

        data = request.get_json(silent=True) or {}
        host = data.get("host")
        username = data.get("username", "vastdata")
        password = data.get("password")
        tools = data.get("tools")  # Optional list of specific tools

        if not host or not password:
            return jsonify({"success": False, "message": "Missing host or password"}), 400

        ops_manager = get_advanced_ops_manager()
        tool_manager = ToolManager(output_callback=ops_manager._emit_output)

        results = tool_manager.deploy_all_tools_to_cnode(host, username, password, tools)
        return jsonify(results)

    # -- Result Bundling -----------------------------------------------------

    @app.route("/advanced-ops/bundle/collect", methods=["POST"])
    def advanced_ops_bundle_collect():
        """Collect results for bundling, scoped to the selected cluster."""
        from result_bundler import get_result_bundler

        data = request.get_json(silent=True) or {}
        cluster_ip = data.get("cluster_ip", "").strip() or None
        bundler = get_result_bundler()
        bundler.set_metadata(
            cluster_name=data.get("cluster_name", "Unknown"),
            cluster_ip=cluster_ip or "Unknown",
            cluster_version=data.get("cluster_version", "Unknown"),
        )
        since, op_status = _last_bundle_freshness_for(cluster_ip)
        collected = bundler.collect_results(
            cluster_ip=cluster_ip,
            since=since,
            operation_status=op_status,
        )
        return jsonify(
            {
                "status": "collected",
                "files": {k: str(v) for k, v in collected.items()},
                "count": len(collected),
                "cluster_ip": cluster_ip,
            }
        )

    @app.route("/advanced-ops/bundle/create", methods=["POST"])
    def advanced_ops_bundle_create():
        """Create a downloadable bundle scoped to the selected cluster."""
        from result_bundler import get_result_bundler

        data = request.get_json(silent=True) or {}
        cluster_ip = data.get("cluster_ip", "").strip() or None
        bundler = get_result_bundler()
        bundler.set_metadata(
            cluster_name=data.get("cluster_name", "Unknown"),
            cluster_ip=cluster_ip or "Unknown",
            cluster_version=data.get("cluster_version", "Unknown"),
        )
        since, op_status = _last_bundle_freshness_for(cluster_ip)
        bundler.collect_results(
            cluster_ip=cluster_ip,
            since=since,
            operation_status=op_status,
        )
        try:
            bundle_path = bundler.create_bundle(data.get("bundle_name"))
            return jsonify(
                {
                    "status": "created",
                    "path": str(bundle_path),
                    "name": bundle_path.name,
                    "size": bundler._format_size(bundle_path.stat().st_size),
                }
            )
        except ValueError as e:
            return jsonify({"status": "error", "message": str(e)}), 400

    @app.route("/advanced-ops/bundle/last")
    def advanced_ops_bundle_last():
        """Return metadata for the most recent one-shot bundle for a cluster.

        Query params:
          ``cluster_ip`` (required): scopes the lookup to a single cluster.

        On a cold server (no completed one-shot this process yet) the
        registry is rehydrated from ``output/bundles/*.zip`` by reading
        each zip's ``manifest.json`` and picking the newest zip whose
        ``run_started_at`` is non-null and whose ``metadata.cluster_ip``
        matches — this guarantees we only surface bundles that were
        produced by the one-shot path (which applies freshness filters),
        never a rebuild-path zip that may contain stale files.
        """
        cluster_ip = (request.args.get("cluster_ip") or "").strip()
        if not cluster_ip:
            return jsonify({"status": "error", "message": "cluster_ip is required"}), 400
        _rehydrate_oneshot_last_bundle_if_needed()
        with app.config["ONESHOT_LAST_BUNDLE_LOCK"]:
            record = dict(app.config["ONESHOT_LAST_BUNDLE"].get(cluster_ip) or {})
        bundle_path_str = record.get("bundle_path")
        if not bundle_path_str:
            return jsonify({"status": "not_found", "cluster_ip": cluster_ip}), 404
        bundle_path = Path(bundle_path_str)
        if not bundle_path.exists():
            # Registry was valid at one point but the zip was removed on
            # disk; clear the stale entry so the next lookup rehydrates.
            with app.config["ONESHOT_LAST_BUNDLE_LOCK"]:
                app.config["ONESHOT_LAST_BUNDLE"].pop(cluster_ip, None)
            return jsonify({"status": "not_found", "cluster_ip": cluster_ip}), 404
        return jsonify(
            {
                "status": "ok",
                "cluster_ip": cluster_ip,
                "bundle_path": str(bundle_path),
                "name": bundle_path.name,
                "size": bundle_path.stat().st_size,
                "run_started_at": record.get("run_started_at"),
                "operation_status": record.get("operation_status") or {},
            }
        )

    @app.route("/advanced-ops/bundle/download/<path:filename>")
    def advanced_ops_bundle_download(filename: str):
        """Download a bundle file."""
        from utils import get_data_dir

        bundle_dir = get_data_dir() / "output" / "bundles"
        file_path = (bundle_dir / filename).resolve()
        if not str(file_path).startswith(str(bundle_dir.resolve())):
            return jsonify({"error": "Invalid path"}), 400
        if not file_path.exists() or not file_path.is_file():
            return jsonify({"error": "Bundle not found"}), 404
        return send_file(
            file_path,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename,
        )

    @app.route("/advanced-ops/bundles")
    def advanced_ops_bundles_list():
        """List available bundles."""
        from result_bundler import get_result_bundler

        bundler = get_result_bundler()
        bundles = bundler.list_bundles()
        return jsonify({"bundles": bundles})

    # -- One-Shot Mode -------------------------------------------------------

    @app.route("/advanced-ops/oneshot/validate", methods=["POST"])
    def advanced_ops_oneshot_validate():
        """Run pre-validation checks in a background thread."""
        from oneshot_runner import OneShotRunner

        data = request.get_json(silent=True) or {}
        selected_ops = data.get("selected_ops", [])
        include_health = data.get("include_health", True)
        use_default_creds = data.get("use_default_creds", False)
        credentials = _extract_oneshot_credentials(data)

        app.config["ONESHOT_CANCEL"].clear()

        from advanced_ops import get_advanced_ops_manager

        get_advanced_ops_manager()._output_buffer.clear()

        # IMPORTANT: pre-validation must honour the Autofill toggle so the
        # Switch SSH probe iterates the full candidate list (primary entered
        # password + ``advanced_operations.default_switch_passwords``).
        # Without ``config_path`` + ``use_default_creds`` the runner would
        # fall back to a single-password probe and mask clusters that need
        # the Cumu1usLinux!/VastData1! fallbacks to authenticate.
        runner = OneShotRunner(
            selected_ops=selected_ops,
            credentials=credentials,
            include_health=include_health,
            cancel_event=app.config["ONESHOT_CANCEL"],
            output_callback=_get_oneshot_output_callback(),
            config_path=app.config.get("CONFIG_PATH"),
            use_default_creds=use_default_creds,
        )

        with app.config["ONESHOT_LOCK"]:
            if app.config["ONESHOT_RUNNING"]:
                return jsonify({"error": "One-shot operation already running"}), 409
            app.config["ONESHOT_RUNNING"] = True
            app.config["ONESHOT_RESULT"] = None
            app.config["ONESHOT_RUNNER"] = runner

        def _run_validation():
            try:
                results = runner.run_prevalidation()
                with app.config["ONESHOT_LOCK"]:
                    app.config["ONESHOT_RESULT"] = {"validation": results}
            finally:
                with app.config["ONESHOT_LOCK"]:
                    app.config["ONESHOT_RUNNING"] = False

        thread = threading.Thread(target=_run_validation, daemon=True)
        thread.start()
        return jsonify({"status": "validating"})

    @app.route("/advanced-ops/oneshot/start", methods=["POST"])
    def advanced_ops_oneshot_start():
        """Start one-shot execution in a background thread."""
        from oneshot_runner import OneShotRunner

        with app.config["ONESHOT_LOCK"]:
            if app.config["ONESHOT_RUNNING"]:
                return jsonify({"error": "One-shot execution already running"}), 409

        data = request.get_json(silent=True) or {}
        selected_ops = data.get("selected_ops", [])
        include_report = data.get("include_report", False)
        include_health = data.get("include_health", True)
        use_default_creds = data.get("use_default_creds", False)
        credentials = _extract_oneshot_credentials(data)

        if not selected_ops:
            return jsonify({"error": "No operations selected"}), 400

        app.config["ONESHOT_CANCEL"].clear()
        runner = OneShotRunner(
            selected_ops=selected_ops,
            credentials=credentials,
            include_report=include_report,
            include_health=include_health,
            cancel_event=app.config["ONESHOT_CANCEL"],
            output_callback=_get_oneshot_output_callback(),
            config_path=app.config.get("CONFIG_PATH"),
            use_default_creds=use_default_creds,
        )

        # Hand off the per-switch credential map that Pre-Validation
        # discovered on the previous runner (stored in
        # ``ONESHOT_RUNNER`` when /advanced-ops/oneshot/validate ran).
        # Without this handoff the fresh execution runner starts with an
        # empty map, which forces ``VnetmapWorkflow`` back onto the legacy
        # single-password candidate sweep even though we already know
        # which password authenticates against each switch.
        with app.config["ONESHOT_LOCK"]:
            prior_runner = app.config.get("ONESHOT_RUNNER")
            if prior_runner is not None and prior_runner is not runner:
                try:
                    prior_pw_map = getattr(prior_runner, "switch_password_by_ip", {}) or {}
                    prior_user_map = getattr(prior_runner, "switch_user_by_ip", {}) or {}
                    if prior_pw_map:
                        runner.seed_switch_credentials(
                            switch_user_by_ip=prior_user_map,
                            switch_password_by_ip=prior_pw_map,
                        )
                except Exception:
                    # Seeding is a best-effort optimisation; the runtime
                    # fallback in run_all() re-probes if the map is empty.
                    pass
            app.config["ONESHOT_RUNNING"] = True
            app.config["ONESHOT_RESULT"] = None
            app.config["ONESHOT_RUNNER"] = runner

        def _run():
            try:
                result = runner.run_all()
                with app.config["ONESHOT_LOCK"]:
                    app.config["ONESHOT_RESULT"] = result
                # Record the bundle path so the Download button can serve
                # the exact zip the runner produced.  ``_record_last_oneshot_bundle``
                # resolves ``current_app`` internally, so we push an explicit
                # Flask app context onto this background thread — without it,
                # the registry write raises ``RuntimeError: Working outside of
                # application context`` and the Download button keeps serving
                # whatever bundle the first rehydration captured on startup.
                # We log (not silently swallow) any residual failure so future
                # regressions surface immediately instead of masquerading as a
                # "stale download" user report.
                try:
                    with app.app_context():
                        _record_last_oneshot_bundle(runner, credentials, result)
                except Exception as exc:  # noqa: BLE001 - best-effort registry update
                    logger.warning(
                        "Failed to update one-shot last-bundle registry " "(Download button may serve a stale zip): %s",
                        exc,
                    )
            finally:
                with app.config["ONESHOT_LOCK"]:
                    app.config["ONESHOT_RUNNING"] = False

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return jsonify({"status": "started", "operations": selected_ops, "include_report": include_report})

    @app.route("/advanced-ops/oneshot/status")
    def advanced_ops_oneshot_status():
        """Get one-shot execution status."""
        with app.config["ONESHOT_LOCK"]:
            runner = app.config.get("ONESHOT_RUNNER")
            running = app.config["ONESHOT_RUNNING"]
            result = app.config.get("ONESHOT_RESULT")

        state = runner.get_state() if runner else None
        return jsonify({"running": running, "state": state, "result": result})

    @app.route("/advanced-ops/oneshot/cancel", methods=["POST"])
    def advanced_ops_oneshot_cancel():
        """Cancel one-shot execution."""
        with app.config["ONESHOT_LOCK"]:
            runner = app.config.get("ONESHOT_RUNNER")
        if runner and runner.is_running():
            app.config["ONESHOT_CANCEL"].set()
            return jsonify({"status": "cancelling"})
        return jsonify({"status": "not_running"})

    @app.route("/advanced-ops/state-snapshot")
    def advanced_ops_state_snapshot():
        """Return complete backend state for Advanced Ops page hydration."""
        from advanced_ops import get_advanced_ops_manager

        manager = get_advanced_ops_manager()
        runner = app.config.get("ONESHOT_RUNNER")

        oneshot_state = None
        if runner:
            try:
                oneshot_state = runner.get_state()
            except Exception:
                pass

        workflow_state = None
        workflow_id = None
        workflow_running = False
        if hasattr(manager, "is_running"):
            try:
                workflow_running = manager.is_running()
                workflow_id = getattr(manager, "current_workflow_id", None)
                if hasattr(manager, "get_state"):
                    workflow_state = manager.get_state()
            except Exception:
                pass

        return jsonify(
            {
                "oneshot": {
                    "running": app.config.get("ONESHOT_RUNNING", False),
                    "state": oneshot_state,
                    "result": app.config.get("ONESHOT_RESULT"),
                },
                "workflow": {
                    "running": workflow_running,
                    "workflow_id": workflow_id,
                    "state": workflow_state,
                },
                "output_count": len(manager._output_buffer),
            }
        )

    @app.route("/advanced-ops/logs/capacity")
    def advanced_ops_logs_capacity():
        """Get operation log storage capacity stats."""
        manager = _create_ops_log_manager(app.config["CONFIG_PATH"])
        return jsonify(manager.check_capacity())

    @app.route("/advanced-ops/logs/purge", methods=["POST"])
    def advanced_ops_logs_purge():
        """Manually purge oldest operation logs."""
        manager = _create_ops_log_manager(app.config["CONFIG_PATH"])
        result = manager.purge_oldest()
        return jsonify(result)

    # -- Validation Results (Developer Mode) ---------------------------------

    @app.route("/validation-results")
    def validation_results_page():
        """Validation Results page — browse operation results by cluster."""
        profiles = _load_profiles(app.config["PROFILES_PATH"])
        return render_template(
            "validation_results.html",
            version=APP_VERSION,
            profiles=profiles,
            output_dir=app.config["DEFAULT_OUTPUT_DIR"],
        )

    @app.route("/validation-results/api/results")
    def validation_results_api():
        """Return all results grouped by operation, optionally filtered."""
        from result_scanner import ResultScanner

        profiles = _load_profiles(app.config["PROFILES_PATH"])
        cluster_ip = request.args.get("cluster_ip", "").strip() or None
        profile_filter = request.args.get("profile", "").strip()

        scanner = ResultScanner(profiles=profiles)

        if profile_filter == "Unsaved":
            saved_ips = {p.get("cluster_ip", "") for p in profiles.values() if p.get("cluster_ip")}
            all_results = scanner.scan_all()
            for op_key in all_results:
                all_results[op_key] = [e for e in all_results[op_key] if e["cluster_ip"] not in saved_ips]
            return jsonify({"operations": all_results})

        results = scanner.scan_all(cluster_ip=cluster_ip)
        return jsonify({"operations": results})

    @app.route("/validation-results/api/clusters")
    def validation_results_clusters():
        """Return unique cluster IPs found across all result files."""
        from result_scanner import ResultScanner

        profiles = _load_profiles(app.config["PROFILES_PATH"])
        scanner = ResultScanner(profiles=profiles)
        return jsonify({"clusters": scanner.get_known_clusters()})

    @app.route("/validation-results/api/file/<operation>/<path:filename>")
    def validation_results_file(operation, filename):
        """Serve or download an operation result file."""
        from result_scanner import ResultScanner

        scanner = ResultScanner()
        resolved = scanner.resolve_file_path(operation, filename)
        if not resolved:
            return jsonify({"error": "File not found"}), 404
        return send_file(resolved, as_attachment=("download" in request.args))

    @app.route("/validation-results/api/file/<operation>/<path:filename>", methods=["DELETE"])
    def validation_results_file_delete(operation, filename):
        """Delete an operation result file."""
        from result_scanner import ResultScanner

        scanner = ResultScanner()
        resolved = scanner.resolve_file_path(operation, filename)
        if not resolved:
            return jsonify({"error": "File not found"}), 404
        try:
            resolved.unlink()
            return jsonify({"status": "deleted", "filename": filename})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # -- Configuration ------------------------------------------------------

    @app.route("/config", methods=["GET"])
    def config_page():
        config_text = _read_config(app.config["CONFIG_PATH"])
        return render_template(
            "config.html",
            version=APP_VERSION,
            config_text=config_text,
        )

    @app.route("/config", methods=["POST"])
    def config_save():
        new_config = request.form.get("config_text", "")
        try:
            import yaml

            yaml.safe_load(new_config)
        except Exception as exc:
            return jsonify({"error": f"Invalid YAML: {exc}"}), 400
        _write_config(app.config["CONFIG_PATH"], new_config)
        return jsonify({"status": "saved"})

    @app.route("/config/reset", methods=["POST"])
    def config_reset():
        template = _read_config(app.config["CONFIG_TEMPLATE"])
        _write_config(app.config["CONFIG_PATH"], template)
        return jsonify({"status": "reset", "config_text": template})

    # -- Advanced Configuration ---------------------------------------------

    @app.route("/config/advanced")
    def advanced_config_page():
        return render_template("advanced_config.html", version=APP_VERSION)

    @app.route("/config/json", methods=["GET"])
    def config_json_get():
        """Return current config.yaml as a JSON object."""
        return jsonify(_load_yaml(app.config["CONFIG_PATH"]))

    @app.route("/config/json", methods=["POST"])
    def config_json_save():
        """Accept a JSON object and write it back to config.yaml."""
        import yaml

        data = request.get_json(silent=True)
        if data is None:
            return jsonify({"error": "Invalid JSON body"}), 400
        try:
            text = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        except Exception as exc:
            return jsonify({"error": f"YAML serialisation failed: {exc}"}), 400
        _write_config(app.config["CONFIG_PATH"], text)
        return jsonify({"status": "saved"})

    @app.route("/config/template/json", methods=["GET"])
    def config_template_json():
        """Return the default template config as a JSON object."""
        return jsonify(_load_yaml(app.config["CONFIG_TEMPLATE"]))

    @app.route("/config/advanced/json-files", methods=["GET"])
    def config_json_files():
        """List available vast_data_*.json report files for the tuning tool."""
        files = []
        for entry in _list_reports(app.config["OUTPUT_DIRS"]):
            if entry["type"] == "JSON":
                files.append(entry)
        return jsonify({"files": files})

    @app.route("/config/advanced/tune-report", methods=["POST"])
    def config_tune_report():
        """Regenerate a PDF from an existing JSON file using report config overrides."""
        from report_builder import ReportConfig, create_report_builder

        payload = request.get_json(silent=True) or {}
        json_source = payload.get("json_path", "").strip()
        overrides = payload.get("report_overrides", {})

        if not json_source:
            return jsonify({"error": "json_path is required"}), 400

        src = Path(json_source)
        if not src.is_file():
            return jsonify({"error": f"JSON file not found: {json_source}"}), 404

        try:
            with open(src, "r", encoding="utf-8") as fh:
                processed_data = json.load(fh)
        except Exception as exc:
            return jsonify({"error": f"Failed to load JSON: {exc}"}), 400

        base_config = _load_yaml(app.config["CONFIG_PATH"])
        if overrides:
            base_config.setdefault("report", {}).update(
                {k: v for k, v in overrides.items() if k in ("organization", "template", "pdf")}
            )
            if "template" in overrides:
                base_config["report"].setdefault("template", {}).update(overrides["template"])
            if "pdf" in overrides:
                base_config["report"].setdefault("pdf", {}).update(overrides["pdf"])
            if "sections" in overrides:
                base_config.setdefault("data_collection", {})["sections"] = overrides["sections"]

        report_config = ReportConfig.from_yaml(base_config)
        builder = create_report_builder(
            config=report_config,
            library_path=app.config.get("LIBRARY_PATH"),
            user_images_dir=app.config.get("USER_IMAGES_DIR"),
        )

        pdf_name = src.stem.replace("vast_data_", "vast_asbuilt_report_") + "_REGEN.pdf"
        pdf_path = src.parent / pdf_name
        if not builder.generate_pdf_report(processed_data, str(pdf_path)):
            return jsonify({"error": "PDF generation failed"}), 500

        return jsonify({"status": "ok", "pdf_path": str(pdf_path), "pdf_name": pdf_name})

    @app.route("/config/advanced/upload-json", methods=["POST"])
    def config_upload_json():
        """Accept an uploaded JSON file and store it in the default output dir."""
        uploaded = request.files.get("json_file")
        if not uploaded or not uploaded.filename:
            return jsonify({"error": "No file uploaded"}), 400

        out_dir = Path(app.config["DEFAULT_OUTPUT_DIR"])
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / uploaded.filename
        uploaded.save(str(dest))
        return jsonify({"status": "uploaded", "path": str(dest)})

    @app.route("/config/advanced/download/<path:filename>")
    def config_download_file(filename):
        """Serve a regenerated PDF for preview or download."""
        target = Path("/" + filename) if not filename.startswith("/") else Path(filename)
        if not target.is_file():
            return jsonify({"error": "File not found"}), 404
        as_download = "download" in request.args
        return send_file(str(target), as_attachment=as_download)

    # -- Cluster Profiles ---------------------------------------------------

    @app.route("/profiles", methods=["GET"])
    def profiles_list():
        profiles = _load_profiles(app.config["PROFILES_PATH"])
        return jsonify(profiles)

    @app.route("/profiles", methods=["POST"])
    def profiles_save():
        """Save a cluster profile using merge-save: only overwrite fields the
        calling page actually sent so that fields from other pages are preserved.
        This lets Generate, Health Check, and Advanced Ops share one profile store.
        """
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Profile name is required"}), 400

        profiles = _load_profiles(app.config["PROFILES_PATH"])
        existing = profiles.get(name, {})

        ALL_FIELDS = {
            "cluster_ip": "",
            "auth_method": "password",
            "username": "",
            "password": "",
            "token": "",
            "output_dir": "",
            "enable_port_mapping": False,
            "switch_user": "cumulus",
            "switch_password": "",
            "node_user": "vastdata",
            "node_password": "",
            "vip_pool": "main",
            "switch_placement": "auto",
            "use_default_creds": True,
            "manual_placements": [],
            "manual_switch_ips": [],
            "proxy_jump": True,
            "tech_port": False,
            "rpt_pre_validation": True,
            "rpt_run_reporter": True,
            "rpt_health_check": True,
            "rpt_run_vnetmap": True,
        }

        merged = {field: existing.get(field, default) for field, default in ALL_FIELDS.items()}

        for field in ALL_FIELDS:
            if field in data:
                merged[field] = data[field]

        # health.html sends "api_token"; normalize to "token"
        if "api_token" in data and data["api_token"]:
            merged["token"] = data["api_token"]

        profiles[name] = merged
        _save_profiles(app.config["PROFILES_PATH"], profiles)
        return jsonify({"status": "saved", "name": name})

    @app.route("/profiles/<name>", methods=["DELETE"])
    def profiles_delete(name):
        profiles = _load_profiles(app.config["PROFILES_PATH"])
        if name not in profiles:
            return jsonify({"error": "Profile not found"}), 404
        del profiles[name]
        _save_profiles(app.config["PROFILES_PATH"], profiles)
        return jsonify({"status": "deleted"})

    # -- Discovery (for manual switch placement) -----------------------------

    @app.route("/api/discover", methods=["POST"])
    def api_discover():
        """Authenticate and fetch rack + switch data for manual placement UI."""
        import socket

        from api_handler import create_vast_api_handler
        from rack_diagram import RackDiagram

        CONNECT_PROBE_TIMEOUT = 5  # seconds — fast TCP reachability check

        data = request.get_json(silent=True) or {}
        cluster_ip = data.get("cluster_ip", "").strip()
        if not cluster_ip:
            return jsonify({"error": "Cluster IP is required"}), 400

        is_tech_port = bool(data.get("tech_port"))
        probe_port = 22 if is_tech_port else 443

        # --- Fast reachability probe before any API work ---
        try:
            sock = socket.create_connection((cluster_ip, probe_port), timeout=CONNECT_PROBE_TIMEOUT)
            sock.close()
        except OSError:
            label = "SSH (Tech Port)" if is_tech_port else "HTTPS"
            return (
                jsonify(
                    {
                        "error": f"Unable to reach {cluster_ip}:{probe_port} — {label} connection "
                        f"timed out after {CONNECT_PROBE_TIMEOUT}s. Verify "
                        f"the cluster IP is correct and reachable."
                    }
                ),
                504,
            )

        username = password = token = None
        if data.get("auth_method") == "token":
            token = data.get("token")
        else:
            username = data.get("username")
            password = data.get("password")

        tunnel = None
        try:
            config = _load_yaml(app.config["CONFIG_PATH"])
            config.setdefault("api", {})
            config["api"]["timeout"] = 10
            config["api"]["max_retries"] = 0

            tunnel_address = None
            if data.get("tech_port"):
                from utils.vms_tunnel import VMSTunnel

                tunnel = VMSTunnel(
                    cluster_ip,
                    data.get("node_user", "vastdata"),
                    data.get("node_password", "vastdata"),
                )
                tunnel.connect()
                tunnel_address = tunnel.local_bind_address

            handler = create_vast_api_handler(
                cluster_ip=cluster_ip,
                username=username,
                password=password,
                token=token,
                config=config,
                tunnel_address=tunnel_address,
            )
            if not handler.authenticate():
                return jsonify({"error": "Authentication failed"}), 401

            racks_raw = handler.get_racks()
            switch_inv = handler.get_switch_inventory()
            handler.close()

            rd = RackDiagram()
            racks = [
                {
                    "name": r.get("name", f"Rack-{r.get('id')}"),
                    "id": r.get("id"),
                    "height_u": r.get("number_of_units") or 42,
                }
                for r in racks_raw
            ]
            racks.sort(key=lambda r: r["name"])

            switches = []
            for sw in switch_inv.get("switches", []):
                model = sw.get("model", "Unknown")
                switches.append(
                    {
                        "name": sw.get("name", "Unknown"),
                        "model": model,
                        "serial": sw.get("serial", ""),
                        "height_u": rd._get_device_height_units(model),
                    }
                )

            return jsonify({"racks": racks, "switches": switches})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500
        finally:
            if tunnel:
                tunnel.close()

    # -- Filesystem browse (for directory picker) ----------------------------

    @app.route("/api/browse")
    def api_browse():
        """Return subdirectories of the given path for the folder picker."""
        raw = request.args.get("path", "").strip()
        target = Path(raw) if raw else Path.home()
        try:
            target = target.resolve()
        except (OSError, ValueError):
            return jsonify({"error": "Invalid path"}), 400
        if not target.is_dir():
            return jsonify({"error": "Not a directory"}), 400

        subdirs = []
        try:
            for entry in sorted(target.iterdir(), key=lambda e: e.name.lower()):
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    subdirs.append(entry.name)
        except PermissionError:
            pass

        return jsonify(
            {
                "current": str(target),
                "parent": str(target.parent) if target != target.parent else None,
                "dirs": subdirs,
            }
        )

    # -- Hardware Device Library ---------------------------------------------

    @app.route("/library")
    def library_page():
        builtin = _get_builtin_devices()
        user_lib = _load_library(app.config["LIBRARY_PATH"])
        devices = []
        for key, info in builtin.items():
            devices.append({**info, "key": key, "source": "built-in"})
        for key, info in user_lib.items():
            devices.append({**info, "key": key, "source": "user"})
        from rack_diagram import get_unrecognized_models

        unrecognized = get_unrecognized_models()
        return render_template(
            "library.html",
            version=APP_VERSION,
            devices=devices,
            unrecognized=sorted(unrecognized),
        )

    @app.route("/api/library", methods=["GET"])
    def api_library_list():
        builtin = _get_builtin_devices()
        user_lib = _load_library(app.config["LIBRARY_PATH"])
        merged = []
        for key, info in builtin.items():
            merged.append({**info, "key": key, "source": "built-in"})
        for key, info in user_lib.items():
            merged.append({**info, "key": key, "source": "user"})
        return jsonify(merged)

    @app.route("/api/library", methods=["POST"])
    def api_library_add():
        key = request.form.get("key", "").strip().lower().replace(" ", "_")
        if not key:
            return jsonify({"error": "Identifier key is required"}), 400
        device_type = request.form.get("type", "cbox").lower()
        if device_type not in ("cbox", "dbox", "ebox", "switch"):
            return jsonify({"error": "Type must be cbox, dbox, ebox, or switch"}), 400
        try:
            height_u = int(request.form.get("height_u", 1))
        except (ValueError, TypeError):
            height_u = 1
        if height_u not in (1, 2):
            return jsonify({"error": "Height must be 1 or 2"}), 400
        description = request.form.get("description", "").strip()

        image_file = request.files.get("image")
        err = _validate_image(image_file)
        if err:
            return jsonify({"error": err}), 400

        image_filename = None
        if image_file and image_file.filename:
            ext = Path(image_file.filename).suffix.lower()
            image_filename = f"{key}_{height_u}u{ext}"
            dest = Path(app.config["USER_IMAGES_DIR"]) / image_filename
            image_file.save(str(dest))

        library = _load_library(app.config["LIBRARY_PATH"])
        library[key] = {
            "type": device_type,
            "height_u": height_u,
            "image_filename": image_filename,
            "description": description,
            "added": datetime.now().isoformat(),
        }
        _save_library(app.config["LIBRARY_PATH"], library)
        return jsonify({"status": "added", "key": key})

    @app.route("/api/library/<key>", methods=["DELETE"])
    def api_library_delete(key):
        library = _load_library(app.config["LIBRARY_PATH"])
        if key not in library:
            return jsonify({"error": "Device not found in user library"}), 404
        entry = library.pop(key)
        if entry.get("image_filename"):
            img_path = Path(app.config["USER_IMAGES_DIR"]) / entry["image_filename"]
            if img_path.exists():
                img_path.unlink()
        _save_library(app.config["LIBRARY_PATH"], library)
        return jsonify({"status": "deleted", "key": key})

    @app.route("/api/library/unrecognized", methods=["GET"])
    def api_library_unrecognized():
        from rack_diagram import get_unrecognized_models

        return jsonify(sorted(get_unrecognized_models()))

    @app.route("/api/vnetmap-status")
    def api_vnetmap_status():
        """Check whether vnetmap output exists and whether hardware has changed."""
        cluster_ip = request.args.get("cluster_ip", "").strip()
        if not cluster_ip:
            return jsonify({"error": "cluster_ip is required"}), 400

        result = {
            "exists": False,
            "filename": "",
            "created_at": "",
            "hardware_changed": False,
            "change_summary": [],
            "recommended": False,
        }

        try:
            vnetmap_file = _find_latest_vnetmap_output(cluster_ip)
            if vnetmap_file and vnetmap_file.exists():
                result["exists"] = True
                result["filename"] = vnetmap_file.name
                result["created_at"] = _parse_vnetmap_timestamp(vnetmap_file.name)

            reports = _find_report_jsons_for_cluster(cluster_ip, app.config["DEFAULT_OUTPUT_DIR"])
            if len(reports) >= 2:
                import json as _json

                with open(reports[0]) as f:
                    newest = _json.load(f)
                with open(reports[1]) as f:
                    previous = _json.load(f)
                fp_new = _extract_hardware_fingerprint(newest)
                fp_old = _extract_hardware_fingerprint(previous)
                changed, summary = _compare_hardware_fingerprints(fp_old, fp_new)
                result["hardware_changed"] = changed
                result["change_summary"] = summary
                result["recommended"] = changed
        except Exception as exc:
            logger.warning("Error checking vnetmap status: %s", exc)

        return jsonify(result)

    @app.route("/library/images/<path:filename>")
    def library_image(filename):
        return send_from_directory(app.config["USER_IMAGES_DIR"], filename)

    @app.route("/library/builtin-images/<path:filename>")
    def library_builtin_image(filename):
        hw_dir = str(Path(app.config["BUNDLE_DIR"]) / "assets" / "hardware_images")
        return send_from_directory(hw_dir, filename)

    # -- Documentation ------------------------------------------------------

    @app.route("/docs")
    def docs_page():
        categories = _build_doc_categories()
        first_doc = _DOC_REGISTRY[0]
        initial_html = _render_doc_markdown(app.config["BUNDLE_DIR"], first_doc["path"])
        cluster_ip = _get_saved_cluster_ip(app.config["PROFILES_PATH"])
        return render_template(
            "docs.html",
            version=APP_VERSION,
            categories=categories,
            initial_html=initial_html,
            initial_doc_id=first_doc["id"],
            cluster_ip=cluster_ip,
        )

    @app.route("/docs/content/<doc_id>")
    def docs_content(doc_id):
        doc = next((d for d in _DOC_REGISTRY if d["id"] == doc_id), None)
        if not doc:
            return "<p>Document not found.</p>", 404
        return _render_doc_markdown(app.config["BUNDLE_DIR"], doc["path"])

    # -- Reports browser ----------------------------------------------------

    @app.route("/reports")
    def reports_page():
        reports = _list_reports(app.config["OUTPUT_DIRS"])
        return render_template(
            "reports.html",
            version=APP_VERSION,
            reports=reports,
            output_dir=app.config["DEFAULT_OUTPUT_DIR"],
        )

    @app.route("/reports/dirs", methods=["GET"])
    def reports_dirs_list():
        return jsonify({"dir": app.config["DEFAULT_OUTPUT_DIR"]})

    @app.route("/reports/dirs", methods=["POST"])
    def reports_dirs_set():
        """Set the output directory (replaces the current one)."""
        data = request.get_json(silent=True) or {}
        new_dir = data.get("dir", "").strip()
        if not new_dir:
            return jsonify({"error": "Directory path is required"}), 400
        resolved = str(Path(new_dir).resolve())
        if not Path(resolved).is_dir():
            return jsonify({"error": "Directory does not exist"}), 400
        app.config["DEFAULT_OUTPUT_DIR"] = resolved
        app.config["OUTPUT_DIRS"] = {resolved}
        return jsonify({"status": "updated", "dir": resolved})

    @app.route("/reports/download/<path:filename>")
    def reports_download(filename):
        for d in app.config["OUTPUT_DIRS"]:
            if (Path(d) / filename).is_file():
                return send_from_directory(d, filename, as_attachment=True)
        return jsonify({"error": "File not found"}), 404

    @app.route("/reports/view/<path:filename>")
    def reports_view(filename):
        for d in app.config["OUTPUT_DIRS"]:
            if (Path(d) / filename).is_file():
                return send_from_directory(d, filename)
        return jsonify({"error": "File not found"}), 404

    @app.route("/reports/delete/<path:filename>", methods=["POST"])
    def reports_delete(filename):
        for d in app.config["OUTPUT_DIRS"]:
            filepath = Path(d) / filename
            if filepath.exists():
                filepath.unlink()
                return jsonify({"status": "deleted"})
        return jsonify({"error": "File not found"}), 404


# ---------------------------------------------------------------------------
# One-shot helpers
# ---------------------------------------------------------------------------


def _extract_oneshot_credentials(data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract credential dict from one-shot JSON request body."""
    return {
        "cluster_ip": data.get("cluster_ip", "").strip(),
        "username": data.get("username", "").strip(),
        "password": data.get("password", ""),
        "api_token": data.get("api_token", "").strip(),
        "node_user": data.get("node_user", "").strip(),
        "node_password": data.get("node_password", ""),
        "switch_user": data.get("switch_user", "").strip(),
        "switch_password": data.get("switch_password", ""),
        "vip_pool": data.get("vip_pool", "main").strip(),
        "cluster_name": data.get("cluster_name", ""),
        "cluster_version": data.get("cluster_version", ""),
        "proxy_jump": data.get("proxy_jump", True),
        "switch_placement": data.get("switch_placement", "auto"),
        "manual_placements": data.get("manual_placements", []),
        "manual_switch_ips": data.get("manual_switch_ips", []),
        "tech_port": data.get("tech_port", False),
    }


def _get_oneshot_output_callback() -> Callable[[str, str, Optional[str]], None]:
    """Return an output callback that routes to the Advanced Ops output buffer."""
    from advanced_ops import get_advanced_ops_manager

    manager = get_advanced_ops_manager()
    return cast(Callable[[str, str, Optional[str]], None], manager._emit_output)


# ---------------------------------------------------------------------------
# One-shot last-bundle registry helpers: serve the runner's validation
# bundle directly from the Download button (Option A) and thread
# ``since``/``operation_status`` into any rebuild fallback so the UI never
# re-collects stale pre-run output.  Proactive pre-run archiving was
# intentionally removed because it moved historical same-cluster files the
# user wants to keep in place; direct-serve alone is sufficient.
# ---------------------------------------------------------------------------


def _record_last_oneshot_bundle(
    runner: Any,
    credentials: Dict[str, Any],
    result: Optional[Dict[str, Any]],
) -> None:
    """Store the runner's bundle path + freshness metadata by cluster_ip.

    Called on the background thread when ``run_all`` returns.  Only records
    successful runs that actually produced a bundle on disk, so the
    Download button never serves a partial or missing zip.
    """
    cluster_ip = (credentials.get("cluster_ip") or "").strip()
    if not cluster_ip:
        return
    state = runner.get_state() if runner else {}
    status = (state or {}).get("status")
    bundle_path_str = (state or {}).get("bundle_path") or (result or {}).get("bundle_path")
    if status != "completed" or not bundle_path_str:
        return
    bundle_path = Path(bundle_path_str)
    if not bundle_path.exists():
        return
    record = {
        "bundle_path": str(bundle_path),
        "run_started_at": (state or {}).get("started_at"),
        "completed_at": (state or {}).get("completed_at"),
        "operation_status": dict((state or {}).get("operation_results") or {}),
    }
    with current_app.config["ONESHOT_LAST_BUNDLE_LOCK"]:
        current_app.config["ONESHOT_LAST_BUNDLE"][cluster_ip] = record


def _last_bundle_freshness_for(
    cluster_ip: Optional[str],
) -> tuple:
    """Return ``(since, operation_status)`` recorded for *cluster_ip*, if any.

    Threaded through to :meth:`ResultBundler.collect_results` so the rebuild
    fallback path still honours the freshness filter even when Option A's
    direct download isn't used (e.g. the bundle was deleted manually but
    output/ still contains the same-run files).
    """
    from datetime import datetime

    if not cluster_ip:
        return None, None
    _rehydrate_oneshot_last_bundle_if_needed()
    with current_app.config["ONESHOT_LAST_BUNDLE_LOCK"]:
        record = dict(current_app.config["ONESHOT_LAST_BUNDLE"].get(cluster_ip) or {})
    since = None
    started_at = record.get("run_started_at")
    if started_at:
        try:
            since = datetime.fromisoformat(started_at)
        except ValueError:
            since = None
    op_status = record.get("operation_status") or None
    return since, op_status


def _rehydrate_oneshot_last_bundle_if_needed() -> None:
    """Populate ONESHOT_LAST_BUNDLE from disk on first request after restart.

    Scans ``output/bundles/*.zip`` (newest-first) and records the most
    recent zip per cluster whose ``manifest.json`` has a non-null
    ``run_started_at`` — the flag that identifies bundles produced by the
    one-shot path (which applies the freshness filter) as opposed to a
    rebuild-path zip that may contain stale files.  Idempotent; bails out
    after the first successful rehydration.
    """
    import json as _json
    import zipfile as _zipfile

    if current_app.config.get("ONESHOT_LAST_BUNDLE_REHYDRATED"):
        return
    bundle_dir = get_data_dir() / "output" / "bundles"
    if not bundle_dir.exists():
        with current_app.config["ONESHOT_LAST_BUNDLE_LOCK"]:
            current_app.config["ONESHOT_LAST_BUNDLE_REHYDRATED"] = True
        return
    by_cluster: Dict[str, Dict[str, Any]] = {}
    try:
        candidates = sorted(
            bundle_dir.glob("*.zip"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
    except OSError:
        candidates = []
    for zip_path in candidates:
        try:
            with _zipfile.ZipFile(zip_path, "r") as zf:
                if "manifest.json" not in zf.namelist():
                    continue
                manifest = _json.loads(zf.read("manifest.json"))
        except (OSError, _zipfile.BadZipFile, _json.JSONDecodeError):
            continue
        run_started = manifest.get("run_started_at")
        cluster_ip = (manifest.get("metadata") or {}).get("cluster_ip")
        if not run_started or not cluster_ip:
            continue
        if cluster_ip in by_cluster:
            continue
        by_cluster[cluster_ip] = {
            "bundle_path": str(zip_path),
            "run_started_at": run_started,
            "completed_at": manifest.get("created"),
            "operation_status": dict(manifest.get("operation_status") or {}),
        }
    with current_app.config["ONESHOT_LAST_BUNDLE_LOCK"]:
        existing = current_app.config["ONESHOT_LAST_BUNDLE"]
        for cluster_ip, record in by_cluster.items():
            existing.setdefault(cluster_ip, record)
        current_app.config["ONESHOT_LAST_BUNDLE_REHYDRATED"] = True


# ---------------------------------------------------------------------------
# Background report generation
# ---------------------------------------------------------------------------


class _JobCancelled(Exception):
    """Raised when the user cancels a running report job."""


def _check_cancel(app: Flask) -> None:
    """Raise _JobCancelled if the cancel event has been set."""
    if app.config["JOB_CANCEL"].is_set():
        raise _JobCancelled("Cancelled by user")


def _update_progress(app: Flask, key: str, phase: str, percent: int, label: str) -> None:
    """Update a progress dict in app.config under JOB_LOCK / HEALTH_JOB_LOCK."""
    lock_key = "HEALTH_JOB_LOCK" if "HEALTH" in key else "JOB_LOCK"
    with app.config[lock_key]:
        app.config[key] = {"percent": min(percent, 100), "phase": phase, "label": label}


def _preprobe_switch_passwords_for_job(
    api_handler: Any,
    params: Dict[str, Any],
    switch_password_candidates: List[str],
    has_vnetmap: bool,
    has_health_switch: bool,
) -> Dict[str, str]:
    """RM-15: pre-probe every switch once to build a ``{ip: password}`` map.

    The Reporter tile's Fast-path in ``VnetmapWorkflow._step_run_vnetmap``
    engages ``vnetmap.py --multiple-passwords`` only when every switch
    IP has an entry in ``switch_password_by_ip``.  On heterogeneous
    fleets (e.g. two leaves on ``Vastdata1!`` plus a spare on
    ``VastData1!``) this is the *only* path that can succeed — the
    legacy single-``-p '<pw>'`` sweep fails for at least one switch no
    matter which candidate is tried.  ``OneShotRunner._validate_switch_ssh``
    already produces this map for the Test Suite tile; RM-15 gives the
    Reporter tile the same capability without duplicating the probe
    logic — :func:`utils.switch_ssh_probe.build_switch_password_by_ip`
    is the shared implementation.

    Short-circuits (return empty dict, zero network I/O) when:

    * Neither vnetmap nor the Tier-3 switch health-check is selected
      (nobody will consume the map — avoid the ``/api/switches/`` call
      and the per-switch probe I/O).
    * The candidate list is empty or has a single entry (homogeneous
      fleet; probing is wasted work).
    * The VMS API reports no switches (IB cluster or a cluster that
      hasn't registered its switches yet).

    Any failure of ``get_switches_detail`` is swallowed and returns
    ``{}`` — a probe crash must never abort the main report pipeline.
    Downstream workflows simply fall back to their legacy paths when
    the map is empty.

    Args:
        api_handler: Authenticated :class:`api_handler.VastAPIHandler`
            — only ``get_switches_detail`` is consumed.
        params: The same ``params`` dict passed to ``_run_report_job``
            (``cluster_ip`` / ``switch_user`` / ``node_user`` /
            ``node_password`` / ``proxy_jump`` are the keys used here).
        switch_password_candidates: Resolved candidate list from
            :func:`utils.switch_password_candidates.resolve_switch_password_candidates`.
        has_vnetmap: ``params.run_vnetmap`` — whether the vnetmap
            workflow will actually run.
        has_health_switch: ``True`` when Tier-3 switch health checks
            will run (i.e. health-check enabled AND SSH credentials
            configured).

    Returns:
        Mapping of ``{switch_mgmt_ip: winning_password}`` — possibly
        empty.  Callers fan this into ``vnetmap_creds`` and
        ``switch_ssh_config`` unchanged.
    """
    if not (has_vnetmap or has_health_switch):
        return {}
    if not switch_password_candidates or len(switch_password_candidates) < 2:
        return {}

    try:
        switches_detail = api_handler.get_switches_detail() or []
    except Exception:  # noqa: BLE001 — probe failures must not abort the job
        return {}

    switch_ips = [str(s.get("mgmt_ip")) for s in switches_detail if s.get("mgmt_ip")]
    if not switch_ips:
        return {}

    jump_kwargs: Dict[str, Any] = {}
    if params.get("proxy_jump", True):
        jump_kwargs = {
            "jump_host": params.get("cluster_ip", ""),
            "jump_user": params.get("node_user", "vastdata"),
            "jump_password": params.get("node_password", ""),
        }

    from utils.switch_ssh_probe import build_switch_password_by_ip

    try:
        result: Dict[str, str] = build_switch_password_by_ip(
            switch_ips=switch_ips,
            switch_user=params.get("switch_user", "cumulus"),
            candidates=list(switch_password_candidates),
            **jump_kwargs,
        )
        return result
    except Exception:  # noqa: BLE001 — probe failures must not abort the job
        return {}


def _run_report_job(app: Flask, params: Dict[str, Any]) -> None:
    """Execute the report pipeline in a background thread."""
    from api_handler import create_vast_api_handler
    from data_extractor import create_data_extractor
    from report_builder import create_report_builder, ReportConfig
    from utils.logger import setup_logging

    with app.config["JOB_LOCK"]:
        app.config["JOB_RUNNING"] = True
        app.config["JOB_RESULT"] = None
        app.config["JOB_PROGRESS"] = {"percent": 0, "phase": "init", "label": "Initializing..."}

    tunnel = None
    try:
        _check_cancel(app)

        config_path = app.config["CONFIG_PATH"]
        config = _load_yaml(config_path)
        if params.get("verbose"):
            config.setdefault("logging", {})["level"] = "DEBUG"
        setup_logging(config)
        enable_sse_logging()

        job_logger = get_logger("job")
        job_logger.info("Starting report generation for %s", params["cluster_ip"])

        has_health = bool(params.get("include_health_check"))
        has_ports = bool(params.get("enable_port_mapping"))
        has_vnetmap = bool(params.get("run_vnetmap"))

        # RM-13: resolve switch SSH password candidates once and fan out
        # to VnetmapWorkflow, ExternalPortMapper and HealthChecker so the
        # Reporter tile matches the Test Suite tile's autofill behaviour.
        # Empty list when ``use_default_creds`` is off and no UI password
        # was supplied — downstream code falls back to the old single-
        # password path in that case.
        from utils.switch_password_candidates import resolve_switch_password_candidates

        switch_password_candidates: List[str] = resolve_switch_password_candidates(
            user_password=params.get("switch_password", ""),
            config_path=config_path,
            use_default_creds=bool(params.get("use_default_creds")),
        )
        if switch_password_candidates and len(switch_password_candidates) > 1:
            job_logger.info(
                "Switch SSH autofill active: %d candidate password(s) will be tried per switch",
                len(switch_password_candidates),
            )
        # Stash the resolved list on ``params`` so the port-mapping
        # helper (``_collect_port_mapping_web`` -> ``ExternalPortMapper``)
        # can consume it without a cross-cutting signature change.
        params["switch_password_candidates"] = list(switch_password_candidates)
        phase_weights = {
            "auth": 5,
            "vnetmap": 15,
            "data_collection": 15,
            "health_check": 12,
            "port_mapping": 8,
            "data_extraction": 15,
            "json_save": 5,
            "pdf_generation": 25,
        }
        if not has_vnetmap:
            phase_weights["vnetmap"] = 0
            phase_weights["data_collection"] = 20
            phase_weights["data_extraction"] = 20
        if not has_health:
            phase_weights["health_check"] = 0
        if not has_ports:
            phase_weights["port_mapping"] = 0
        total_weight = sum(phase_weights.values())
        cumulative = 0
        phase_start = {}
        for p in [
            "auth",
            "vnetmap",
            "data_collection",
            "health_check",
            "port_mapping",
            "data_extraction",
            "json_save",
            "pdf_generation",
        ]:
            phase_start[p] = int(cumulative * 100 / total_weight)
            cumulative += phase_weights[p]

        output_dir = Path(params["output_dir"])
        output_dir.mkdir(parents=True, exist_ok=True)
        app.config["OUTPUT_DIRS"].add(str(output_dir.resolve()))

        # Resolve credentials
        username = password = token = None
        if params["auth_method"] == "token":
            token = params.get("token")
        else:
            username = params.get("username")
            password = params.get("password")

        _check_cancel(app)

        # Tech Port tunnel (auto-discover VMS and forward API traffic)
        tunnel_address = None
        if params.get("tech_port"):
            from utils.vms_tunnel import VMSTunnel

            job_logger.info("Tech Port mode: discovering VMS via %s ...", params["cluster_ip"])
            tunnel = VMSTunnel(
                params["cluster_ip"],
                params.get("node_user", "vastdata"),
                params.get("node_password", "vastdata"),
            )
            tunnel.connect()
            tunnel_address = tunnel.local_bind_address
            job_logger.info(
                "VMS discovered: internal=%s, management=%s, tunnel=%s",
                tunnel.vms_internal_ip,
                tunnel.vms_management_ip,
                tunnel_address,
            )

        # Build components
        api_handler = create_vast_api_handler(
            cluster_ip=params["cluster_ip"],
            username=username,
            password=password,
            token=token,
            config=config,
            tunnel_address=tunnel_address,
        )
        data_extractor = create_data_extractor(config)
        report_config = ReportConfig.from_yaml(config)
        report_builder = create_report_builder(
            config=report_config,
            library_path=app.config.get("LIBRARY_PATH"),
            user_images_dir=app.config.get("USER_IMAGES_DIR"),
        )

        # Authenticate
        _check_cancel(app)
        _update_progress(app, "JOB_PROGRESS", "auth", phase_start["auth"], "Authenticating...")
        job_logger.info("Authenticating with VAST cluster...")
        if not api_handler.authenticate():
            raise RuntimeError("Authentication failed")
        job_logger.info("Authentication successful")

        # RM-15: pre-probe switches once so the Fast path of
        # ``VnetmapWorkflow`` (``vnetmap.py --multiple-passwords``) can
        # engage on heterogeneous fleets (e.g. two leaves on
        # ``Vastdata1!`` and a spare on ``VastData1!``) — this is the
        # Reporter-tile parallel of what
        # ``OneShotRunner._validate_switch_ssh`` does for the Test
        # Suite tile.  The map is also handed to ``HealthChecker`` so
        # Tier-3 checks skip their in-process RM-13 probe.  Any
        # failure here is non-fatal and falls back to the legacy
        # single-``-p`` candidate sweep.
        has_health_switch_preprobe = bool(
            has_health and params.get("enable_port_mapping", False) and params.get("switch_password", "")
        )
        switch_password_by_ip: Dict[str, str] = _preprobe_switch_passwords_for_job(
            api_handler=api_handler,
            params=params,
            switch_password_candidates=switch_password_candidates,
            has_vnetmap=has_vnetmap,
            has_health_switch=has_health_switch_preprobe,
        )
        if switch_password_by_ip:
            job_logger.info(
                "RM-15: pre-probed %d switch(es); vnetmap --multiple-passwords fast path will engage",
                len(switch_password_by_ip),
            )

        # Optional: run vnetmap workflow before data collection
        if has_vnetmap:
            _check_cancel(app)
            _update_progress(app, "JOB_PROGRESS", "vnetmap", phase_start["vnetmap"], "Running Vnetmap workflow...")
            job_logger.info("Starting Vnetmap workflow (6 steps)...")
            try:
                import logging as _logging
                from workflows.vnetmap_workflow import VnetmapWorkflow

                vnetmap_wf = VnetmapWorkflow()
                vnetmap_wf.set_output_callback(
                    lambda level, msg, details=None: job_logger.log(
                        getattr(_logging, level.upper(), _logging.INFO), msg
                    )
                )
                vnetmap_creds: Dict[str, Any] = {
                    "cluster_ip": params["cluster_ip"],
                    "node_user": params.get("node_user", "vastdata"),
                    "node_password": params.get("node_password", ""),
                    "switch_user": params.get("switch_user", ""),
                    "switch_password": params.get("switch_password", ""),
                    "username": params.get("username", ""),
                    "password": params.get("password", ""),
                    "api_token": params.get("token", ""),
                }
                # RM-13: feed the resolved candidate list so
                # ``vnetmap.py --multiple-passwords`` gets every published
                # default when Autofill Password is active.
                if switch_password_candidates:
                    vnetmap_creds["switch_password_candidates"] = list(switch_password_candidates)
                # RM-15: when the pre-probe built a per-switch map,
                # hand it through so ``VnetmapWorkflow`` engages its
                # Fast path (``--multiple-passwords`` via heredoc
                # wrapper) instead of the legacy candidate sweep.
                if switch_password_by_ip:
                    vnetmap_creds["switch_password_by_ip"] = dict(switch_password_by_ip)
                vnetmap_wf.set_credentials(vnetmap_creds)
                ok, prereq_msg = vnetmap_wf.validate_prerequisites()
                if not ok:
                    job_logger.warning("Vnetmap prerequisites not met (%s) — skipping", prereq_msg)
                else:
                    for step_id in range(1, 7):
                        _check_cancel(app)
                        step_result = vnetmap_wf.run_step(step_id)
                        if not step_result.get("success"):
                            job_logger.warning(
                                "Vnetmap step %d failed: %s — continuing without fresh vnetmap",
                                step_id,
                                step_result.get("message"),
                            )
                            break
                    else:
                        job_logger.info("Vnetmap workflow completed — fresh output available")
            except Exception as vn_exc:
                job_logger.warning("Vnetmap workflow failed (%s) — continuing with existing data", vn_exc)

        # Collect data
        _check_cancel(app)
        _update_progress(
            app, "JOB_PROGRESS", "data_collection", phase_start["data_collection"], "Collecting cluster data..."
        )
        job_logger.info("Collecting cluster data...")
        raw_data = api_handler.get_all_data()
        if not raw_data:
            raise RuntimeError("Data collection returned empty results")

        # Optional health check - tiers depend on Port Mapping settings
        _check_cancel(app)
        _update_progress(app, "JOB_PROGRESS", "health_check", phase_start["health_check"], "Running health checks...")
        if params.get("include_health_check"):
            try:
                from health_checker import HealthChecker

                hc_start = phase_start["health_check"]
                hc_width = int(phase_weights["health_check"] * 100 / total_weight)

                def _inline_hc_progress(check_idx: int, total: int, check_name: str) -> None:
                    sub_pct = int(check_idx * 100 / max(total, 1))
                    overall = hc_start + int(sub_pct * hc_width / 100)
                    _update_progress(app, "JOB_PROGRESS", "health_check", overall, f"Health: {check_name}")

                enable_ssh = params.get("enable_port_mapping", False)
                node_pw = params.get("node_password", "")
                switch_pw = params.get("switch_password", "")

                if enable_ssh and switch_pw:
                    tiers = [1, 3]
                    job_logger.info("Running health checks (Tier 1 API + Tier 3 Switch SSH)...")

                    ssh_config = {
                        "username": params.get("node_user", "vastdata"),
                        "password": params.get("node_password", ""),
                    }
                    switch_ssh_config = {
                        "username": params.get("switch_user", "cumulus"),
                        "password": switch_pw,
                    }
                    # RM-13: hand the resolved candidate list through so
                    # ``HealthChecker.run_switch_ssh_checks`` probes each
                    # switch once and picks the password that actually
                    # works, instead of silently 401'ing on any switch
                    # that uses a different default.
                    if switch_password_candidates:
                        switch_ssh_config["password_candidates"] = list(switch_password_candidates)
                    # RM-15: if the pre-probe already built the map, hand
                    # it through directly so ``run_switch_ssh_checks``
                    # skips its own in-process RM-13 probe (saves a
                    # second round-trip per switch when vnetmap ran).
                    if switch_password_by_ip:
                        switch_ssh_config["password_by_ip"] = dict(switch_password_by_ip)
                    if params.get("proxy_jump", True):
                        switch_ssh_config["proxy_jump"] = {
                            "host": params["cluster_ip"],
                            "username": params.get("node_user", "vastdata"),
                            "password": params.get("node_password", ""),
                        }

                    checker = HealthChecker(
                        api_handler=api_handler,
                        ssh_config=ssh_config,
                        switch_ssh_config=switch_ssh_config,
                        cancel_event=app.config["JOB_CANCEL"],
                        progress_callback=_inline_hc_progress,
                    )
                else:
                    tiers = [1]
                    job_logger.info("Running health check (Tier 1 API only)...")
                    checker = HealthChecker(
                        api_handler=api_handler,
                        cancel_event=app.config["JOB_CANCEL"],
                        progress_callback=_inline_hc_progress,
                    )

                health_report = checker.run_all_checks(tiers=tiers)
                raw_data["health_check_results"] = checker.to_dict(health_report)

                tier_desc = "Tier 1 & 3" if 3 in tiers else "Tier 1"
                job_logger.info("Health check completed (%s) — results will be included in report", tier_desc)
            except Exception as hc_exc:
                job_logger.warning("Health check failed (non-blocking): %s", hc_exc)

        # Optional port mapping — prefer vnetmap output, fall back to SSH
        _check_cancel(app)
        _update_progress(
            app, "JOB_PROGRESS", "port_mapping", phase_start["port_mapping"], "Collecting port mapping data..."
        )
        use_vnetmap = False
        if params.get("enable_port_mapping"):
            vnetmap_file = _find_latest_vnetmap_output(params["cluster_ip"])
            if vnetmap_file:
                job_logger.info("Found vnetmap output: %s — using as port mapping source", vnetmap_file.name)
                try:
                    from vnetmap_parser import VNetMapParser

                    parser = VNetMapParser(str(vnetmap_file))
                    vnetmap_result = parser.parse()
                    if vnetmap_result.get("available") and vnetmap_result.get("topology"):
                        raw_data["port_mapping_vnetmap"] = vnetmap_result
                        use_vnetmap = True
                        job_logger.info("Vnetmap data parsed: %d connections", len(vnetmap_result["topology"]))
                    else:
                        job_logger.warning(
                            "Vnetmap file found but parsing failed: %s — falling back to SSH",
                            vnetmap_result.get("error", "no topology data"),
                        )
                except Exception as vn_exc:
                    job_logger.warning("Failed to parse vnetmap output (%s) — falling back to SSH", vn_exc)

            if not use_vnetmap:
                job_logger.info("Collecting port mapping data via SSH...")
                port_data = _collect_port_mapping_web(params, raw_data, api_handler)
                if port_data:
                    raw_data["port_mapping_external"] = port_data
                    job_logger.info("Port mapping data collected successfully")
                else:
                    job_logger.warning(
                        "Port mapping collection failed — check SSH credentials and network connectivity"
                    )

        # Process data
        _check_cancel(app)
        _update_progress(
            app, "JOB_PROGRESS", "data_extraction", phase_start["data_extraction"], "Processing collected data..."
        )
        job_logger.info("Processing collected data...")
        use_ext = bool(not use_vnetmap and params.get("enable_port_mapping") and "port_mapping_external" in raw_data)
        processed_data = data_extractor.extract_all_data(
            raw_data, use_external_port_mapping=use_ext, use_vnetmap=use_vnetmap
        )
        if not processed_data:
            raise RuntimeError("Data processing failed")

        # Inject manual switch placements if provided
        if params.get("switch_placement") == "manual" and params.get("manual_placements"):
            processed_data["manual_switch_placements"] = params["manual_placements"]
            job_logger.info(
                "Using manual switch placement (%d assignments)",
                len(params["manual_placements"]),
            )

        # Generate reports
        _check_cancel(app)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cluster_name = processed_data.get("cluster_summary", {}).get("name", "unknown")

        cluster_ip = params["cluster_ip"]
        processed_data["cluster_ip"] = cluster_ip

        _update_progress(app, "JOB_PROGRESS", "json_save", phase_start["json_save"], "Saving JSON data...")
        json_path = output_dir / f"vast_data_{cluster_name}_{timestamp}.json"
        data_extractor.save_processed_data(processed_data, str(json_path))
        job_logger.info("JSON saved: %s", json_path.name)

        _check_cancel(app)
        _update_progress(
            app, "JOB_PROGRESS", "pdf_generation", phase_start["pdf_generation"], "Generating PDF report..."
        )
        pdf_path = output_dir / f"vast_asbuilt_report_{cluster_name}_{timestamp}.pdf"
        if not report_builder.generate_pdf_report(processed_data, str(pdf_path)):
            raise RuntimeError("PDF generation failed")
        job_logger.info("PDF saved: %s", pdf_path.name)

        import json as json_mod

        meta = {"cluster_ip": cluster_ip, "cluster_name": cluster_name, "timestamp": timestamp}
        meta_path = pdf_path.parent / (pdf_path.stem + ".meta.json")
        meta_path.write_text(json_mod.dumps(meta))

        api_handler.close()
        _update_progress(app, "JOB_PROGRESS", "complete", 100, "Complete")
        job_logger.info("Report generation completed successfully")

        with app.config["JOB_LOCK"]:
            if not app.config["JOB_CANCEL"].is_set():
                app.config["JOB_RESULT"] = {
                    "success": True,
                    "pdf": pdf_path.name,
                    "json": json_path.name,
                    "cluster": cluster_name,
                }

    except _JobCancelled:
        job_logger = get_logger("job")
        job_logger.info("Report generation cancelled by user")
    except Exception as exc:
        err_logger = get_logger("job")
        err_logger.error("Report generation failed: %s", exc)
        with app.config["JOB_LOCK"]:
            if not app.config["JOB_CANCEL"].is_set():
                app.config["JOB_RESULT"] = {"success": False, "error": str(exc)}
    finally:
        if tunnel is not None:
            try:
                tunnel.close()
            except Exception:
                pass
        with app.config["JOB_LOCK"]:
            app.config["JOB_RUNNING"] = False


def _extract_hardware_fingerprint(report_json: dict) -> dict:
    """Extract a comparable hardware fingerprint from a report JSON."""
    hw = report_json.get("hardware_inventory", {})

    def _to_list(obj):
        if isinstance(obj, dict):
            return list(obj.values())
        return obj if isinstance(obj, list) else []

    cnodes = _to_list(hw.get("cnodes", []))
    dnodes = _to_list(hw.get("dnodes", []))
    switches = _to_list(hw.get("switches", []))
    cboxes = _to_list(hw.get("cboxes", []))
    dboxes = _to_list(hw.get("dboxes", []))
    eboxes = _to_list(hw.get("eboxes", []))

    return {
        "cbox_count": len(cboxes),
        "dbox_count": len(dboxes),
        "cnode_count": len(cnodes),
        "dnode_count": len(dnodes),
        "switch_count": len(switches),
        "ebox_count": len(eboxes),
        "cnode_ips": sorted(n.get("mgmt_ip", "") for n in cnodes if n.get("mgmt_ip")),
        "dnode_ips": sorted(n.get("mgmt_ip", "") for n in dnodes if n.get("mgmt_ip")),
        "switch_ips": sorted(s.get("mgmt_ip", "") for s in switches if s.get("mgmt_ip")),
        "ebox_ips": sorted(e.get("mgmt_ip", "") for e in eboxes if e.get("mgmt_ip")),
    }


def _compare_hardware_fingerprints(
    old: dict,
    new: dict,
) -> tuple:
    """Compare two hardware fingerprints and return (changed, summary_list)."""
    changes: list = []
    for key, label in [
        ("cbox_count", "CBox"),
        ("dbox_count", "DBox"),
        ("cnode_count", "CNode"),
        ("dnode_count", "DNode"),
        ("switch_count", "Switch"),
        ("ebox_count", "EBox"),
    ]:
        if old.get(key) != new.get(key):
            changes.append(f"{label} count changed: {old.get(key)} \u2192 {new.get(key)}")
    for key, label in [
        ("cnode_ips", "CNode"),
        ("dnode_ips", "DNode"),
        ("switch_ips", "Switch"),
        ("ebox_ips", "EBox"),
    ]:
        added = set(new.get(key, [])) - set(old.get(key, []))
        removed = set(old.get(key, [])) - set(new.get(key, []))
        for ip in sorted(added):
            changes.append(f"New {label} detected: {ip}")
        for ip in sorted(removed):
            changes.append(f"{label} removed: {ip}")
    return (bool(changes), changes)


def _find_report_jsons_for_cluster(cluster_ip: str, output_dir: str) -> list:
    """Return up to 2 most recent report JSON paths for a cluster, newest first."""
    out = Path(output_dir)
    if not out.is_dir():
        return []
    candidates = []
    for f in out.glob("vast_data_*.json"):
        try:
            with open(f) as fh:
                head = fh.read(4096)
            if f'"{cluster_ip}"' in head:
                candidates.append(f)
        except (OSError, UnicodeDecodeError):
            continue
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[:2]


def _parse_vnetmap_timestamp(filename: str) -> str:
    """Extract human-readable timestamp from vnetmap filename.

    ``vnetmap_output_10.143.11.63_20260330_030728.txt``
    -> ``2026-03-30 03:07:28``
    """
    import re as _re

    m = _re.search(r"_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})", filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)} {m.group(4)}:{m.group(5)}:{m.group(6)}"
    return ""


def _find_latest_vnetmap_output(cluster_ip: str) -> Optional[Path]:
    """Find the most recent vnetmap output file for a given cluster IP.

    Scans ``output/scripts/`` for files matching
    ``vnetmap_output_{cluster_ip}_*.txt``.  Does NOT fall back to
    files from other clusters to avoid cross-contamination of port
    mapping data.
    """
    from utils import get_data_dir

    scripts_dir = get_data_dir() / "output" / "scripts"
    if not scripts_dir.is_dir():
        return None

    exact = sorted(scripts_dir.glob(f"vnetmap_output_{cluster_ip}_*.txt"), reverse=True)
    if exact:
        return Path(exact[0])

    logger.info("No vnetmap output file found for cluster %s", cluster_ip)
    return None


def _collect_port_mapping_web(
    params: Dict[str, Any],
    raw_data: Dict[str, Any],
    api_handler: Any,
) -> Optional[Dict[str, Any]]:
    """Thin wrapper around ExternalPortMapper for the web UI context."""
    try:
        from external_port_mapper import ExternalPortMapper, _safe_str

        switch_inventory = raw_data.get("switch_inventory", {})
        switches = switch_inventory.get("switches", [])
        switch_ips = [sw.get("mgmt_ip") for sw in switches if sw.get("mgmt_ip")]
        if not switch_ips:
            logger.warning("No switch management IPs found — cannot collect port mapping")
            return None

        # Build hostname->mgmt_ip map and spine IP set so the collector can
        # resolve LLDP neighbors back to known switches and classify leaf-to-
        # spine uplinks correctly.  Without these the collector falls back to
        # the legacy narrow IPL heuristic (symmetric swp29..swp32 only).
        switch_hostname_map: Dict[str, str] = {}
        spine_ips_web: List[str] = []
        for sw in switches:
            ip = sw.get("mgmt_ip")
            if not ip:
                continue
            for host_field in ("hostname", "name", "host_name"):
                host = sw.get(host_field)
                if host:
                    switch_hostname_map[str(host)] = ip
                    break
            role = (sw.get("role") or sw.get("switch_type") or "").lower()
            if "spine" in role:
                spine_ips_web.append(ip)

        # Try cnodes_network first, then fall back to raw cnodes data (for EBox clusters)
        cnodes_network = raw_data.get("cnodes_network", [])
        cnode_ips = []
        for cn in cnodes_network:
            ip = cn.get("mgmt_ip") or cn.get("ipmi_ip")
            if ip and ip != "Unknown" and ip not in cnode_ips:
                cnode_ips.append(ip)

        # Fallback: check hardware.cnodes data (from /api/v7/cnodes/)
        if not cnode_ips:
            hardware = raw_data.get("hardware", {})
            raw_cnodes = hardware.get("cnodes", [])
            for cn in raw_cnodes:
                ip = cn.get("mgmt_ip") or cn.get("ipmi_ip")
                if ip and ip != "Unknown" and ip not in cnode_ips:
                    cnode_ips.append(ip)
            if cnode_ips:
                logger.info(f"Found {len(cnode_ips)} CNode IPs from hardware data: {cnode_ips}")

        if not cnode_ips:
            logger.warning("No CNode management IP found — cannot collect port mapping")
            return None

        MAX_CNODE_ATTEMPTS = 3
        last_error = None
        last_partial = None
        attempts = 0
        for cnode_ip in cnode_ips:
            if attempts >= MAX_CNODE_ATTEMPTS:
                logger.warning(
                    "Port mapping failed on %d CNodes — skipping remaining %d",
                    MAX_CNODE_ATTEMPTS,
                    len(cnode_ips) - MAX_CNODE_ATTEMPTS,
                )
                break
            attempts += 1
            try:
                tunnel_addr = getattr(api_handler, "_api_host", None)
                if tunnel_addr == params["cluster_ip"]:
                    tunnel_addr = None
                # RM-13: the ``switch_password_candidates`` list is
                # populated by ``_run_report_job`` when Autofill Password
                # is active, so ``ExternalPortMapper._detect_switch_os``
                # can probe each switch with every published default
                # instead of auth-failing on the first rejection.
                raw_candidates = params.get("switch_password_candidates") or []
                if isinstance(raw_candidates, (list, tuple)):
                    pw_candidates = [str(p) for p in raw_candidates if str(p)] or None
                else:
                    pw_candidates = None
                mapper = ExternalPortMapper(
                    cluster_ip=params["cluster_ip"],
                    api_user=api_handler.username or "support",
                    api_password=api_handler.password or "",
                    cnode_ip=cnode_ip,
                    node_user=params.get("node_user", "vastdata"),
                    node_password=params.get("node_password", ""),
                    switch_ips=switch_ips,
                    switch_user=params.get("switch_user", "cumulus"),
                    switch_password=params.get("switch_password", ""),
                    switch_password_candidates=pw_candidates,
                    proxy_jump=bool(params.get("proxy_jump", True)),
                    tunnel_address=tunnel_addr,
                    switch_hostname_map=switch_hostname_map or None,
                    spine_ips=spine_ips_web or None,
                )
                result = mapper.collect_port_mapping()
                if result.get("available"):
                    if result.get("partial"):
                        logger.info(
                            "Port mapping collected (partial) from CNode %s: %d mappings",
                            cnode_ip,
                            len(result.get("port_map", [])),
                        )
                    else:
                        logger.info("Port mapping collection succeeded via CNode %s", cnode_ip)
                    return cast(Optional[Dict[str, Any]], result)
                last_error = result.get("error", "unknown reason")
                if result.get("port_map"):
                    last_partial = result
                if "cannot reach switch" in (last_error or "").lower():
                    logger.warning("Switch unreachable from CNode %s — not retrying remaining CNodes", cnode_ip)
                    break
            except Exception as e:
                last_error = _safe_str(e)
                logger.warning("Port mapping via CNode %s failed: %s — trying next CNode", cnode_ip, last_error)
                if "cannot reach switch" in last_error.lower():
                    logger.warning("Switch connectivity issue — not retrying remaining CNodes")
                    break

        if last_partial and last_partial.get("port_map"):
            logger.info("Using partial port mapping from last attempt")
            return cast(Optional[Dict[str, Any]], last_partial)
        logger.warning("Port mapping collection failed for all CNodes: %s", last_error or "unknown reason")
        return None
    except Exception as exc:
        try:
            safe_msg = _safe_str(exc)
        except NameError:
            safe_msg = str(exc).encode("ascii", errors="replace").decode("ascii")
        logger.error("Port mapping collection failed: %s", safe_msg)
        return None


def _run_health_job(app: Flask, params: Dict[str, Any]) -> None:
    """Execute the health check pipeline in a background thread."""
    from api_handler import create_vast_api_handler
    from health_checker import HealthChecker
    from utils.logger import setup_logging

    with app.config["HEALTH_JOB_LOCK"]:
        app.config["HEALTH_JOB_PROGRESS"] = {"percent": 0, "phase": "init", "label": "Initializing..."}

    try:
        config_path = app.config["CONFIG_PATH"]
        config = _load_yaml(config_path)
        setup_logging(config)
        enable_sse_logging()
        job_logger = get_logger("health_job")
        job_logger.info("Starting health check for %s", params["cluster_ip"])

        _update_progress(app, "HEALTH_JOB_PROGRESS", "auth", 5, "Authenticating...")

        username = password = token = None
        if params.get("api_token"):
            token = params["api_token"]
        else:
            username = params.get("username")
            password = params.get("password")

        api_handler = create_vast_api_handler(
            cluster_ip=params["cluster_ip"],
            username=username,
            password=password,
            token=token,
            config=config,
        )

        job_logger.info("Authenticating with VAST cluster...")
        if not api_handler.authenticate():
            raise RuntimeError("Authentication failed")
        job_logger.info("Authentication successful")

        _update_progress(app, "HEALTH_JOB_PROGRESS", "setup", 10, "Preparing health checks...")

        ssh_config = None
        if params.get("node_user") and params.get("node_password"):
            ssh_config = {"username": params["node_user"], "password": params["node_password"]}
        switch_ssh_config = None
        if params.get("switch_user") and params.get("switch_password"):
            switch_ssh_config = {"username": params["switch_user"], "password": params["switch_password"]}
            if ssh_config and params.get("proxy_jump", True):
                switch_ssh_config["proxy_jump"] = {
                    "host": params["cluster_ip"],
                    "username": params["node_user"],
                    "password": params["node_password"],
                }

        def _health_progress_callback(check_idx: int, total: int, check_name: str) -> None:
            pct = 10 + int(check_idx * 85 / max(total, 1))
            _update_progress(
                app, "HEALTH_JOB_PROGRESS", "checks", min(pct, 95), f"Check {check_idx}/{total}: {check_name}"
            )

        checker = HealthChecker(
            api_handler=api_handler,
            ssh_config=ssh_config,
            switch_ssh_config=switch_ssh_config,
            cancel_event=app.config["HEALTH_JOB_CANCEL"],
            progress_callback=_health_progress_callback,
        )
        report = checker.run_all_checks(tiers=params.get("tiers", [1]))
        report_dict = checker.to_dict(report)

        _update_progress(app, "HEALTH_JOB_PROGRESS", "save", 96, "Saving results...")

        output_dir = config.get("output", {}).get("directory", "output")
        json_path = checker.save_json(report, output_dir)
        remediation_path = checker.generate_remediation_report(report, output_dir)

        _update_progress(app, "HEALTH_JOB_PROGRESS", "complete", 100, "Complete")

        with app.config["HEALTH_JOB_LOCK"]:
            app.config["HEALTH_JOB_RESULT"] = {
                "success": True,
                "report": report_dict,
                "json_path": json_path,
                "remediation_path": remediation_path,
                "cluster": report.cluster_name,
            }
        job_logger.info("Health check completed successfully")

    except Exception as exc:
        err_logger = get_logger("health_job")
        err_logger.error("Health check failed: %s", exc)
        with app.config["HEALTH_JOB_LOCK"]:
            app.config["HEALTH_JOB_RESULT"] = {"success": False, "error": str(exc)}
    finally:
        with app.config["HEALTH_JOB_LOCK"]:
            app.config["HEALTH_JOB_RUNNING"] = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPORT_PATTERNS = ("vast_asbuilt_report_*.pdf", "vast_data_*.json")


def _list_reports(output_dirs) -> list:
    """List only VAST-generated PDF/JSON reports from all known output directories."""
    seen = set()
    files = []
    for output_dir in output_dirs:
        out = Path(output_dir)
        if not out.exists():
            continue
        for pattern in _REPORT_PATTERNS:
            for f in out.glob(pattern):
                try:
                    if not f.is_file():
                        continue
                    abs_path = str(f.resolve())
                    if abs_path in seen:
                        continue
                    seen.add(abs_path)
                    st = f.stat()
                    files.append(
                        {
                            "name": f.name,
                            "dir": str(out),
                            "size": st.st_size,
                            "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                            "type": f.suffix[1:].upper(),
                        }
                    )
                except (PermissionError, OSError):
                    continue
    files.sort(key=lambda x: str(x["modified"]), reverse=True)
    return files


def _read_config(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return "# Configuration file not found"


def _write_config(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def _load_yaml(path: str) -> Dict[str, Any]:
    import yaml

    try:
        with open(path, "r", encoding="utf-8") as f:
            return cast(Dict[str, Any], yaml.safe_load(f) or {})
    except (OSError, yaml.YAMLError) as exc:
        logger.debug("Failed to load YAML %s: %s", path, exc)
        return {}


def _create_ops_log_manager(config_path: str) -> Any:
    """Create an OpsLogManager wired to YAML config values."""
    from utils.ops_log_manager import OpsLogManager

    cfg = _load_yaml(config_path).get("logging", {})
    log_dir = cfg.get("ops_log_dir")
    max_bytes = int(cfg.get("ops_log_max_bytes", OpsLogManager.DEFAULT_MAX_BYTES))
    purge_fraction = float(cfg.get("ops_log_purge_fraction", OpsLogManager.DEFAULT_PURGE_FRACTION))

    kw: Dict[str, Any] = {"max_bytes": max_bytes, "purge_fraction": purge_fraction}
    if log_dir:
        from utils import get_data_dir

        kw["log_dir"] = get_data_dir() / log_dir
    return OpsLogManager(**kw)


def _load_profiles(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return cast(Dict[str, Any], json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_profiles(path: str, profiles: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(profiles, f, indent=2)


def _load_library(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return cast(Dict[str, Any], json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_library(path: str, library: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(library, f, indent=2)


_ALLOWED_IMAGE_EXT = {".png", ".jpg", ".jpeg"}
_MAX_IMAGE_BYTES = 1 * 1024 * 1024  # 1 MB


def _validate_image(file_storage) -> Optional[str]:
    """Validate an uploaded image file. Returns error message or None."""
    if not file_storage or not file_storage.filename:
        return None  # no file is OK (generic image used)
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in _ALLOWED_IMAGE_EXT:
        return f"Invalid format '{ext}'. Allowed: PNG, JPG, JPEG"
    file_storage.seek(0, 2)
    size = file_storage.tell()
    file_storage.seek(0)
    if size > _MAX_IMAGE_BYTES:
        return f"File too large ({size / 1024:.0f} KB). Max: 1 MB"
    try:
        from PIL import Image as PILImage

        img = PILImage.open(file_storage)
        w, _ = img.size
        if w < 60 or w > 2000:
            return f"Width {w}px out of range (60-2000 px)"
        file_storage.seek(0)
    except Exception as e:
        return f"Cannot read image: {e}"
    return None


def _get_builtin_devices() -> Dict[str, Any]:
    """Return the built-in device map (read-only, from hardware_library.py)."""
    return cast(Dict[str, Any], get_builtin_devices_for_ui())


def _build_doc_categories():
    """Group the doc registry by category, preserving insertion order."""
    categories = []
    cat_map: Dict[str, list] = {}
    for doc in _DOC_REGISTRY:
        cat = doc["category"]
        if cat not in cat_map:
            doc_list: list = []
            cat_map[cat] = doc_list
            categories.append((cat, doc_list))
        cat_map[cat].append({"id": doc["id"], "title": doc["title"]})
    return categories


def _render_doc_markdown(bundle_dir: str, rel_path: str) -> str:
    """Read a markdown file relative to bundle_dir and return rendered HTML."""
    file_path = _find_doc_file(bundle_dir, rel_path)
    if file_path is None:
        return f'<p class="text-muted">Document not found: {rel_path}</p>'

    md_text = file_path.read_text(encoding="utf-8")

    try:
        import markdown as md_lib  # type: ignore[import-untyped]

        html = md_lib.markdown(
            md_text,
            extensions=["tables", "fenced_code", "toc", "sane_lists"],
            extension_configs={"toc": {"permalink": False}},
        )
        return _rewrite_doc_links_in_html(html)
    except ImportError:
        from markupsafe import escape

        return f"<pre>{escape(md_text)}</pre>"


def _find_doc_file(bundle_dir: str, rel_path: str) -> Optional[Path]:
    """Locate a doc file in the bundle dir or project root."""
    bundle_path = Path(bundle_dir) / rel_path
    if bundle_path.exists():
        return bundle_path
    project_root = Path(__file__).resolve().parent.parent
    root_path = project_root / rel_path
    if root_path.exists():
        return root_path
    return None


def _get_saved_cluster_ip(profiles_path: str) -> str:
    """Return the first cluster IP found in saved profiles, or empty string."""
    profiles = _load_profiles(profiles_path)
    for profile in profiles.values():
        ip = profile.get("cluster_ip", "")
        if isinstance(ip, str) and ip.strip():
            return ip.strip()
    return ""
