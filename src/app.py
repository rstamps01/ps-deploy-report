"""
VAST As-Built Report Generator - Web UI Application

Flask-based web interface providing a browser GUI for generating reports,
browsing output, editing configuration, and streaming live progress.
"""

import json
import os
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from flask import (
    Flask,
    Response,
    jsonify,
    render_template,
    request,
    send_from_directory,
)

# Ensure src/ is on the path for sibling imports
sys.path.insert(0, str(Path(__file__).parent))

from utils import get_bundle_dir, get_data_dir
from utils.logger import enable_sse_logging, get_logger, get_sse_queue

logger = get_logger(__name__)

APP_VERSION = "1.4.0"

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
    app.config["REPORT_CONFIG"] = config or {}

    # Background job state shared across requests
    app.config["JOB_RUNNING"] = False
    app.config["JOB_RESULT"] = None
    app.config["JOB_LOCK"] = threading.Lock()

    _register_routes(app)
    return app


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------

def _register_routes(app: Flask) -> None:

    # -- Dashboard ----------------------------------------------------------

    @app.route("/")
    def dashboard():
        reports = _list_reports(app.config["OUTPUT_DIRS"])
        return render_template(
            "dashboard.html",
            version=APP_VERSION,
            reports=reports[:10],
            job_running=app.config["JOB_RUNNING"],
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
            "switch_user": form.get("switch_user", "cumulus"),
            "switch_password": form.get("switch_password", ""),
            "node_user": form.get("node_user", "vastdata"),
            "node_password": form.get("node_password", ""),
            "verbose": form.get("verbose") == "on",
            "switch_placement": form.get("switch_placement", "auto"),
        }

        if params["switch_placement"] == "manual":
            raw_mp = form.get("manual_placements", "[]")
            try:
                params["manual_placements"] = json.loads(raw_mp)
            except (json.JSONDecodeError, TypeError):
                return jsonify({"error": "Invalid manual_placements JSON"}), 400

        thread = threading.Thread(
            target=_run_report_job, args=(app, params), daemon=True
        )
        thread.start()
        return jsonify({"status": "started"})

    @app.route("/generate/status")
    def generate_status():
        return jsonify({
            "running": app.config["JOB_RUNNING"],
            "result": app.config["JOB_RESULT"],
        })

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

    # -- Cluster Profiles ---------------------------------------------------

    @app.route("/profiles", methods=["GET"])
    def profiles_list():
        profiles = _load_profiles(app.config["PROFILES_PATH"])
        return jsonify(profiles)

    @app.route("/profiles", methods=["POST"])
    def profiles_save():
        data = request.get_json(silent=True) or {}
        name = data.get("name", "").strip()
        if not name:
            return jsonify({"error": "Profile name is required"}), 400
        profiles = _load_profiles(app.config["PROFILES_PATH"])
        profiles[name] = {
            "cluster_ip": data.get("cluster_ip", ""),
            "auth_method": data.get("auth_method", "password"),
            "username": data.get("username", ""),
            "password": data.get("password", ""),
            "token": data.get("token", ""),
            "output_dir": data.get("output_dir", ""),
            "enable_port_mapping": data.get("enable_port_mapping", False),
            "switch_user": data.get("switch_user", "cumulus"),
            "switch_password": data.get("switch_password", ""),
            "node_user": data.get("node_user", "vastdata"),
            "node_password": data.get("node_password", ""),
        }
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
        from api_handler import create_vast_api_handler
        from rack_diagram import RackDiagram

        data = request.get_json(silent=True) or {}
        cluster_ip = data.get("cluster_ip", "").strip()
        if not cluster_ip:
            return jsonify({"error": "Cluster IP is required"}), 400

        username = password = token = None
        if data.get("auth_method") == "token":
            token = data.get("token")
        else:
            username = data.get("username")
            password = data.get("password")

        try:
            config = _load_yaml(app.config["CONFIG_PATH"])
            handler = create_vast_api_handler(
                cluster_ip=cluster_ip,
                username=username,
                password=password,
                token=token,
                config=config,
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
                switches.append({
                    "name": sw.get("name", "Unknown"),
                    "model": model,
                    "serial": sw.get("serial", ""),
                    "height_u": rd._get_device_height_units(model),
                })

            return jsonify({"racks": racks, "switches": switches})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

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

        return jsonify({
            "current": str(target),
            "parent": str(target.parent) if target != target.parent else None,
            "dirs": subdirs,
        })

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
# Background report generation
# ---------------------------------------------------------------------------

def _run_report_job(app: Flask, params: Dict[str, Any]) -> None:
    """Execute the report pipeline in a background thread."""
    from api_handler import create_vast_api_handler
    from data_extractor import create_data_extractor
    from report_builder import create_report_builder
    from utils.logger import setup_logging

    with app.config["JOB_LOCK"]:
        app.config["JOB_RUNNING"] = True
        app.config["JOB_RESULT"] = None

    try:
        config_path = app.config["CONFIG_PATH"]
        config = _load_yaml(config_path)
        if params.get("verbose"):
            config.setdefault("logging", {})["level"] = "DEBUG"
        setup_logging(config)
        enable_sse_logging()

        job_logger = get_logger("job")
        job_logger.info("Starting report generation for %s", params["cluster_ip"])

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

        # Build components
        api_handler = create_vast_api_handler(
            cluster_ip=params["cluster_ip"],
            username=username,
            password=password,
            token=token,
            config=config,
        )
        data_extractor = create_data_extractor(config)
        report_builder = create_report_builder()

        # Authenticate
        job_logger.info("Authenticating with VAST cluster...")
        if not api_handler.authenticate():
            raise RuntimeError("Authentication failed")
        job_logger.info("Authentication successful")

        # Collect data
        job_logger.info("Collecting cluster data...")
        raw_data = api_handler.get_all_data()
        if not raw_data:
            raise RuntimeError("Data collection returned empty results")

        # Optional port mapping
        if params.get("enable_port_mapping"):
            job_logger.info("Collecting port mapping data...")
            port_data = _collect_port_mapping_web(params, raw_data, api_handler)
            if port_data:
                raw_data["port_mapping_external"] = port_data

        # Process data
        job_logger.info("Processing collected data...")
        use_ext = params.get("enable_port_mapping") and "port_mapping_external" in raw_data
        processed_data = data_extractor.extract_all_data(raw_data, use_external_port_mapping=use_ext)
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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cluster_name = processed_data.get("cluster_summary", {}).get("name", "unknown")

        json_path = output_dir / f"vast_data_{cluster_name}_{timestamp}.json"
        data_extractor.save_processed_data(processed_data, str(json_path))
        job_logger.info("JSON saved: %s", json_path.name)

        pdf_path = output_dir / f"vast_asbuilt_report_{cluster_name}_{timestamp}.pdf"
        if not report_builder.generate_pdf_report(processed_data, str(pdf_path)):
            raise RuntimeError("PDF generation failed")
        job_logger.info("PDF saved: %s", pdf_path.name)

        api_handler.close()
        job_logger.info("Report generation completed successfully")

        with app.config["JOB_LOCK"]:
            app.config["JOB_RESULT"] = {
                "success": True,
                "pdf": pdf_path.name,
                "json": json_path.name,
                "cluster": cluster_name,
            }

    except Exception as exc:
        err_logger = get_logger("job")
        err_logger.error("Report generation failed: %s", exc)
        with app.config["JOB_LOCK"]:
            app.config["JOB_RESULT"] = {"success": False, "error": str(exc)}
    finally:
        with app.config["JOB_LOCK"]:
            app.config["JOB_RUNNING"] = False


def _collect_port_mapping_web(
    params: Dict[str, Any],
    raw_data: Dict[str, Any],
    api_handler: Any,
) -> Optional[Dict[str, Any]]:
    """Thin wrapper around ExternalPortMapper for the web UI context."""
    try:
        from external_port_mapper import ExternalPortMapper

        switch_inventory = raw_data.get("switch_inventory", {})
        switches = switch_inventory.get("switches", [])
        switch_ips = [sw.get("mgmt_ip") for sw in switches if sw.get("mgmt_ip")]
        if not switch_ips:
            return None

        cnodes_network = raw_data.get("cnodes_network", [])
        cnode_ip = None
        for cn in cnodes_network:
            cnode_ip = cn.get("mgmt_ip") or cn.get("ipmi_ip")
            if cnode_ip and cnode_ip != "Unknown":
                break
        if not cnode_ip:
            return None

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
        )
        result = mapper.collect_port_mapping()
        return result if result.get("available") else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

import fnmatch

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
                    files.append({
                        "name": f.name,
                        "dir": str(out),
                        "size": st.st_size,
                        "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
                        "type": f.suffix[1:].upper(),
                    })
                except (PermissionError, OSError):
                    continue
    files.sort(key=lambda x: x["modified"], reverse=True)
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
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {}


def _load_profiles(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_profiles(path: str, profiles: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(profiles, f, indent=2)
