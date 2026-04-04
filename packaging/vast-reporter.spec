# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for VAST As-Built Report Generator.

Builds a one-directory bundle containing the embedded Python runtime,
all runtime dependencies, the Flask web UI, and application assets.

Usage:
    pyinstaller packaging/vast-reporter.spec
"""

import platform
from pathlib import Path

block_cipher = None

ROOT = Path(SPECPATH).parent  # project root (one level up from packaging/)

# Platform-specific configuration
IS_MAC = platform.system() == "Darwin"
IS_WIN = platform.system() == "Windows"

# Collect Cairo shared library on macOS (required by cairosvg for SVG diagram rendering)
_extra_binaries = []
if IS_MAC:
    for _cairo_dir in [Path("/opt/homebrew/lib"), Path("/usr/local/lib")]:
        _cairo_dylib = _cairo_dir / "libcairo.2.dylib"
        if _cairo_dylib.exists():
            _extra_binaries.append((str(_cairo_dylib), "."))
            break

APP_NAME = "VAST Reporter"
_icon_mac = ROOT / "packaging" / "icons" / "icon.icns"
_icon_win = ROOT / "packaging" / "icons" / "icon.ico"
ICON_MAC = str(_icon_mac) if _icon_mac.exists() else None
ICON_WIN = str(_icon_win) if _icon_win.exists() else None

# Locate reportlab T1 font files for renderPM PNG support
_rl_font_dir = None
for _candidate in (ROOT / "venv" / "lib").rglob("reportlab/fonts"):
    if _candidate.is_dir():
        _rl_font_dir = _candidate
        break

# Collect all source modules
src_dir = ROOT / "src"
a = Analysis(
    [str(src_dir / "main.py")],
    pathex=[str(src_dir)],
    binaries=_extra_binaries,
    datas=[
        # Frontend templates and static files
        (str(ROOT / "frontend" / "templates"), "frontend/templates"),
        (str(ROOT / "frontend" / "static"), "frontend/static"),
        # Configuration (defaults copied to writable data dir at first launch)
        (str(ROOT / "config" / "config.yaml"), "config"),
        (str(ROOT / "config" / "config.yaml.template"), "config"),
        (str(ROOT / "config" / "device_library.json"), "config"),
        (str(ROOT / "config" / "cluster_profiles.json"), "config"),
        # Assets (hardware images — exclude the large source composite)
        (str(ROOT / "assets" / "diagrams"), "assets/diagrams"),
        # Documentation (Docs page in UI): all _DOC_REGISTRY paths must be in the bundle
        (str(ROOT / "README.md"), "."),
        (str(ROOT / "CHANGELOG.md"), "."),
        (str(ROOT / "docs" / "API-REFERENCE.md"), "docs"),
        (str(ROOT / "docs" / "ADVANCED-OPERATIONS.md"), "docs"),
        (str(ROOT / "docs" / "POST-INSTALL-VALIDATION.md"), "docs"),
        (str(ROOT / "docs" / "api" / "EBOX_API_V7_DISCOVERY.md"), "docs/api"),
        (str(ROOT / "docs" / "deployment"), "docs/deployment"),
    ] + [
        (str(img), "assets/hardware_images")
        for img in (ROOT / "assets" / "hardware_images").iterdir()
        if img.suffix.lower() in (".png", ".jpeg", ".jpg")
        and "image-20251227" not in img.name
    ] + ([(str(_rl_font_dir), "reportlab/fonts")] if _rl_font_dir else []),
    hiddenimports=[
        "flask",
        "jinja2",
        "markupsafe",
        "reportlab",
        "reportlab.graphics",
        "reportlab.graphics.renderPDF",
        "reportlab.graphics.renderPM",
        "reportlab.lib",
        "reportlab.lib.utils",
        "reportlab.pdfbase.pdfmetrics",
        "reportlab.pdfgen",
        "reportlab.platypus",
        "PIL",
        "yaml",
        "colorlog",
        "jsonschema",
        "dateutil",
        "dotenv",
        "paramiko",
        "requests",
        "urllib3",
        "svgwrite",
        "cairosvg",
        "cairocffi",
        "cffi",
        "_cffi_backend",
        "cssselect2",
        "defusedxml",
        "tinycss2",
        "webencodings",
        "fitz",
        "pymupdf",
        "scp",
        "click",
        "markdown",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "weasyprint",
        "tkinter",
        "matplotlib",
        "scipy",
        "numpy",
        "pandas",
        "IPython",
        "notebook",
        "pytest",
        "flake8",
        "black",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="vast-reporter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # keep console for CLI mode output
    icon=ICON_MAC if IS_MAC else ICON_WIN if IS_WIN else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VAST Reporter",
)

# macOS .app bundle
if IS_MAC:
    app = BUNDLE(
        coll,
        name="VAST Reporter.app",
        icon=ICON_MAC,
        bundle_identifier="com.vastdata.asbuilt-reporter",
        info_plist={
            "CFBundleShortVersionString": "1.5.0",
            "CFBundleVersion": "1.5.0",
            "NSHighResolutionCapable": True,
            "NSAppTransportSecurity": {
                "NSAllowsLocalNetworking": True,
            },
        },
    )
