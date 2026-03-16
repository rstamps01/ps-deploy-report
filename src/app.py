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
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

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

APP_VERSION = "1.4.3"

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
            return match.group(0)
        parsed = urlparse(unquote(href))
        path = (parsed.path or "").strip().lstrip("/")
        if path.startswith("./"):
            path = path[2:]
        if not path.endswith(".md"):
            return match.group(0)
        doc_id = _DOC_LINK_MAP.get(path) or _DOC_LINK_MAP.get(path.split("/")[-1])
        if doc_id:
            return f'<a href="/docs#{doc_id}"'
        return match.group(0)

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
    app.config["JOB_LOCK"] = threading.Lock()
    app.config["JOB_CANCEL"] = threading.Event()

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
# Background report generation
# ---------------------------------------------------------------------------


class _JobCancelled(Exception):
    """Raised when the user cancels a running report job."""


def _check_cancel(app: Flask) -> None:
    """Raise _JobCancelled if the cancel event has been set."""
    if app.config["JOB_CANCEL"].is_set():
        raise _JobCancelled("Cancelled by user")


def _run_report_job(app: Flask, params: Dict[str, Any]) -> None:
    """Execute the report pipeline in a background thread."""
    from api_handler import create_vast_api_handler
    from data_extractor import create_data_extractor
    from report_builder import create_report_builder, ReportConfig
    from utils.logger import setup_logging

    with app.config["JOB_LOCK"]:
        app.config["JOB_RUNNING"] = True
        app.config["JOB_RESULT"] = None

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

        # Build components
        api_handler = create_vast_api_handler(
            cluster_ip=params["cluster_ip"],
            username=username,
            password=password,
            token=token,
            config=config,
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
        job_logger.info("Authenticating with VAST cluster...")
        if not api_handler.authenticate():
            raise RuntimeError("Authentication failed")
        job_logger.info("Authentication successful")

        # Collect data
        _check_cancel(app)
        job_logger.info("Collecting cluster data...")
        raw_data = api_handler.get_all_data()
        if not raw_data:
            raise RuntimeError("Data collection returned empty results")

        # Optional port mapping
        _check_cancel(app)
        if params.get("enable_port_mapping"):
            job_logger.info("Collecting port mapping data via SSH...")
            port_data = _collect_port_mapping_web(params, raw_data, api_handler)
            if port_data:
                raw_data["port_mapping_external"] = port_data
                job_logger.info("Port mapping data collected successfully")
            else:
                job_logger.warning("Port mapping collection failed — check SSH " "credentials and network connectivity")

        # Process data
        _check_cancel(app)
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
        _check_cancel(app)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        cluster_name = processed_data.get("cluster_summary", {}).get("name", "unknown")

        json_path = output_dir / f"vast_data_{cluster_name}_{timestamp}.json"
        data_extractor.save_processed_data(processed_data, str(json_path))
        job_logger.info("JSON saved: %s", json_path.name)

        _check_cancel(app)
        pdf_path = output_dir / f"vast_asbuilt_report_{cluster_name}_{timestamp}.pdf"
        if not report_builder.generate_pdf_report(processed_data, str(pdf_path)):
            raise RuntimeError("PDF generation failed")
        job_logger.info("PDF saved: %s", pdf_path.name)

        api_handler.close()
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
            logger.warning("No switch management IPs found — cannot collect port mapping")
            return None

        cnodes_network = raw_data.get("cnodes_network", [])
        cnode_ips = []
        for cn in cnodes_network:
            ip = cn.get("mgmt_ip") or cn.get("ipmi_ip")
            if ip and ip != "Unknown" and ip not in cnode_ips:
                cnode_ips.append(ip)
        if not cnode_ips:
            logger.warning("No CNode management IP found — cannot collect port mapping")
            return None

        last_error = None
        last_partial = None
        for cnode_ip in cnode_ips:
            try:
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
                if result.get("available"):
                    if result.get("partial"):
                        logger.info(
                            "Port mapping collected (partial) from CNode %s: %d mappings",
                            cnode_ip,
                            len(result.get("port_map", [])),
                        )
                    else:
                        logger.info("Port mapping collection succeeded via CNode %s", cnode_ip)
                    return result
                last_error = result.get("error", "unknown reason")
                if result.get("port_map"):
                    last_partial = result
            except Exception as e:
                last_error = str(e)
                logger.warning("Port mapping via CNode %s failed: %s — trying next CNode", cnode_ip, last_error)

        if last_partial and last_partial.get("port_map"):
            logger.info("Using partial port mapping from last attempt")
            return last_partial
        logger.warning("Port mapping collection failed for all CNodes: %s", last_error or "unknown reason")
        return None
    except Exception as exc:
        logger.error("Port mapping collection failed: %s", exc)
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
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.debug("Failed to load YAML %s: %s", path, exc)
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


def _load_library(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_library(path: str, library: Dict[str, Any]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
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
        w, h = img.size
        if w < 60 or w > 2000:
            return f"Width {w}px out of range (60-2000 px)"
        file_storage.seek(0)
    except Exception as e:
        return f"Cannot read image: {e}"
    return None


def _get_builtin_devices() -> Dict[str, Any]:
    """Return the built-in device map (read-only, from rack_diagram.py)."""
    builtin = {
        # CBoxes
        "supermicro_gen5_cbox": {
            "type": "cbox",
            "height_u": 1,
            "image_filename": "supermicro_gen5_cbox_1u.png",
            "description": "Supermicro Gen5 CBox",
            "source": "built-in",
        },
        "hpe_genoa_cbox": {
            "type": "cbox",
            "height_u": 1,
            "image_filename": "hpe_genoa_cbox.png",
            "description": "HPE Genoa CBox",
            "source": "built-in",
        },
        "hpe_icelake": {
            "type": "cbox",
            "height_u": 2,
            "image_filename": "hpe_il_cbox_2u.png",
            "description": "HPE IceLake 2U CBox",
            "source": "built-in",
        },
        "dell_icelake": {
            "type": "cbox",
            "height_u": 2,
            "image_filename": "dell_il_cbox_2u.png",
            "description": "Dell IceLake 2U CBox",
            "source": "built-in",
        },
        "dell_turin_cbox": {
            "type": "cbox",
            "height_u": 1,
            "image_filename": "dell_turin_r6715_cbox_1u.png",
            "description": "Dell Gen6 Turin CBox (R6715)",
            "source": "built-in",
        },
        "smc_turin_cbox": {
            "type": "cbox",
            "height_u": 1,
            "image_filename": "smc_turin_cbox_1u.png",
            "description": "SMC Gen6 Turin CBox",
            "source": "built-in",
        },
        "broadwell": {
            "type": "cbox",
            "height_u": 2,
            "image_filename": "broadwell_cbox_2u.png",
            "description": "Broadwell 2U CBox",
            "source": "built-in",
        },
        "cascadelake": {
            "type": "cbox",
            "height_u": 2,
            "image_filename": "cascadelake_cbox_2u.png",
            "description": "CascadeLake 2U CBox",
            "source": "built-in",
        },
        # DBoxes
        "ceres_v2": {
            "type": "dbox",
            "height_u": 1,
            "image_filename": "ceres_v2_1u.png",
            "description": "Ceres V2 1U DBox",
            "source": "built-in",
        },
        "dbox-515": {
            "type": "dbox",
            "height_u": 1,
            "image_filename": "ceres_v2_1u.png",
            "description": "Ceres V2 1U DBox",
            "source": "built-in",
        },
        "dbox-516": {
            "type": "dbox",
            "height_u": 1,
            "image_filename": "ceres_v2_1u.png",
            "description": "Ceres V2 1U DBox",
            "source": "built-in",
        },
        "sanmina": {
            "type": "dbox",
            "height_u": 2,
            "image_filename": "maverick_2u.png",
            "description": "Maverick 2U DBox",
            "source": "built-in",
        },
        "maverick_1.5": {
            "type": "dbox",
            "height_u": 2,
            "image_filename": "maverick_2u.png",
            "description": "Maverick/MLK 2U DBox",
            "source": "built-in",
        },
        # Switches
        "msn2100-cb2f": {
            "type": "switch",
            "height_u": 1,
            "image_filename": "mellanox_msn2100_2x16p_100g_switch_1u.png",
            "description": "Mellanox SN2100 100Gb 16pt Switch",
            "source": "built-in",
        },
        "msn2700": {
            "type": "switch",
            "height_u": 1,
            "image_filename": "mellanox_msn2700_1x32p_100g_switch_1u.png",
            "description": "Mellanox SN2700 100Gb 32pt Switch",
            "source": "built-in",
        },
        "msn3700-vs2fc": {
            "type": "switch",
            "height_u": 1,
            "image_filename": "mellanox_msn3700_1x32p_200g_switch_1u.png",
            "description": "Mellanox SN3700 200Gb 32pt Switch",
            "source": "built-in",
        },
        "msn4600c": {
            "type": "switch",
            "height_u": 2,
            "image_filename": "mellanox_msn4600C_1x64p_100g_switch_2u.png",
            "description": "Mellanox SN4600C 100Gb 64pt Switch",
            "source": "built-in",
        },
        "msn4600": {
            "type": "switch",
            "height_u": 2,
            "image_filename": "mellanox_msn4600_1x64p_200g_switch_2u.png",
            "description": "Mellanox SN4600 200Gb 64pt Switch",
            "source": "built-in",
        },
        "sn5600": {
            "type": "switch",
            "height_u": 2,
            "image_filename": "mellanox_sn5600_1x64p_800g_switch_2u.png",
            "description": "Mellanox SN5600 800Gb 64pt Switch",
            "source": "built-in",
        },
        "arista_7060dx5": {
            "type": "switch",
            "height_u": 2,
            "image_filename": "arista_7060dx5_1x64p_800g_switch_2u.jpeg",
            "description": "Arista 7060DX5 800Gb Switch",
            "source": "built-in",
        },
        "arista_7050cx4": {
            "type": "switch",
            "height_u": 1,
            "image_filename": "arista_7050cx4_24d_400g_switch_1u.png",
            "description": "Arista 7050CX4 400Gb Switch",
            "source": "built-in",
        },
        "arista_7050dx4": {
            "type": "switch",
            "height_u": 1,
            "image_filename": "arista_7050dx4_32s_400g_switch_1u.png",
            "description": "Arista 7050DX4 400Gb Switch",
            "source": "built-in",
        },
        "arista": {
            "type": "switch",
            "height_u": 2,
            "image_filename": "arista_7060dx5_1x64p_800g_switch_2u.jpeg",
            "description": "Arista Switch (generic)",
            "source": "built-in",
        },
    }
    return builtin


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
        import markdown as md_lib

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
        ip = profile.get("cluster_ip", "").strip()
        if ip:
            return ip
    return ""
