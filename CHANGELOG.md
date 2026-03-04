# Changelog

All notable changes to the VAST As-Built Report Generator will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-03-04

### Added
- **Web UI**: Browser-based GUI with dashboard, report generation form, live progress streaming, report browser, and YAML configuration editor
- **Self-Contained Packaging**: PyInstaller-based builds for macOS (.app/.dmg) and Windows (.exe/.zip) — no Python installation required
- **SSE Log Streaming**: Real-time log output in the browser during report generation via Server-Sent Events
- **Cross-Platform SSH**: New `ssh_adapter.py` using paramiko (Windows) and pexpect (macOS/Linux) for port mapping on all platforms
- **GitHub Actions CI/CD**: Automated cross-platform builds triggered on version tags, with artifacts uploaded to GitHub Releases
- **Development Dependency Split**: `requirements-dev.txt` separates test/lint/optional dependencies from bundled runtime

### Changed
- **Launcher**: `main.py` now defaults to GUI mode (web UI); use `--cli` flag or `--cluster` argument for command-line mode
- **Dependencies**: WeasyPrint and Cairo moved to dev-only (ReportLab is the sole production PDF engine); added Flask, paramiko
- **Packaging**: `.gitignore` updated for PyInstaller artifacts; `packaging/` directory added with spec file and build scripts

### Technical Details
- `src/app.py`: Flask application with routes for dashboard, generate, config, reports, SSE stream
- `src/utils/logger.py`: Added `SSELogHandler`, `get_sse_queue()`, `enable_sse_logging()`
- `src/utils/ssh_adapter.py`: `run_ssh_command()` and `run_interactive_ssh()` with platform detection
- `frontend/`: Jinja2 templates (base, dashboard, generate, config, reports) with VAST-branded CSS and vanilla JS
- `packaging/vast-reporter.spec`: PyInstaller spec with hidden imports, data files, and macOS .app bundle
- `.github/workflows/build-release.yml`: Matrix build (macOS + Windows), test gate, GitHub release creation

## [1.3.0] - 2025-11-12

### Added
- **Installation Script Documentation**: Enhanced installation scripts now document enhanced features during dependency installation
- **Port Mapping Usage Examples**: Added port mapping collection examples to both Mac and Windows installation scripts
- **Enhanced Features Verification**: Installation scripts now verify and confirm installation of enhanced feature dependencies

### Changed
- **Installation Process**: Improved user experience with clear messaging about enhanced features being installed
- **Documentation**: Updated installation scripts to include port mapping usage examples

### Technical Details
- Updated `docs/deployment/install-mac.sh`: Added enhanced features documentation and port mapping examples
- Updated `docs/deployment/install-windows.ps1`: Added enhanced features documentation and port mapping examples

## [1.2.0] - 2025-11-11

### Added
- **Hardware Inventory Node Column**: Replaced ID column with "Node" column showing programmatically generated CNode/DNode names
- **One Row Per Node**: Each CNode and DNode now appears on its own row for detailed tracking
- **Multiple Nodes Per Box Support**: CBoxes and DBoxes with multiple nodes display each node on a separate row with the same Name/Serial Number
- **Port Mapping Collection**: Enhanced port mapping collection via SSH with `--enable-port-mapping` flag
- **Port Mapping Credentials**: Support for switch and node SSH credentials via command-line arguments
- **Network Topology with Connections**: Network diagram now includes port mapping connections when available

### Changed
- **Column Renaming**:
  - "CNode/DNode" → "Node" (more concise)
  - "Position" → "Height" (clearer terminology)
- **Column Width Optimization**:
  - Model column: Increased from 30% to 40% for better readability
  - Rack column: Decreased from 10% to 8%
  - Node column: Decreased from 18% to 12%
  - Height column: Decreased from 10% to 8%
- **Node Name Source**: Now uses programmatically generated `name` field (e.g., `cnode-3-10`, `dnode-3-112`) instead of customer-assigned hostnames
- **Data Collection**: Enhanced CNode and DNode name extraction from API
- **DBox Association**: Improved DNode to DBox association with `dbox_id` field

### Fixed
- **Missing Name Field**: Fixed data extractor to include `name` field in processed hardware inventory data
- **Missing DBox ID**: Fixed DNode data structure to include `dbox_id` for proper DBox association
- **Dataclass Field Order**: Fixed `VastHardwareInfo` dataclass field ordering to resolve Python dataclass initialization errors

### Technical Details
- Updated `src/data_extractor.py`: Added `name` and `dbox_id` fields to `_process_hardware_node` method
- Updated `src/api_handler.py`: Added `hostname` field to `VastHardwareInfo` dataclass and hardware data structures
- Updated `src/report_builder.py`: Modified `_create_consolidated_inventory_table` to create one row per node
- Updated `src/brand_compliance.py`: Adjusted column width ratios for Hardware Inventory table

## [1.1.0] - 2025-10-17

### Added
- Initial production release
- Comprehensive report generation
- Rack positioning support
- PSNT tracking
- Network topology diagrams

## [1.0.0] - 2025-09-27

### Added
- Initial release
- Basic report generation
- API integration
- PDF and JSON output formats

