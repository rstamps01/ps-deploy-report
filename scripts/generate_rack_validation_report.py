#!/usr/bin/env python3
"""Generate the full-rack validation report (RACK-2).

Fills two racks of every supported height (42U, 45U, 48U, 50U, 52U) with one of
each hardware-library device, bottom to top in library order, and renders them
through the report's own Physical Rack Layout code. Writes a PDF for visual review
and a JSON manifest of every placement, indicator and page number.

Usage:
    python3 scripts/generate_rack_validation_report.py
    python3 scripts/generate_rack_validation_report.py --page-size Letter --heights 42,52
    python3 scripts/generate_rack_validation_report.py --out output/rack-validation

Output (gitignored): output/rack-validation/rack_validation_<timestamp>.pdf and .json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from report_builder import ReportConfig, VastReportBuilder  # noqa: E402
from utils.rack_validation import build_validation_racks  # noqa: E402


def generate(
    out_dir: Path,
    page_size: str = "A4",
    heights: Optional[List[int]] = None,
    library_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the validation PDF and manifest.

    Args:
        out_dir: Output directory.
        page_size: "A4" or "Letter".
        heights: Rack heights to render (defaults to every supported height).
        library_path: Optional user device_library.json to include user devices.

    Returns:
        Dict[str, Any]: Manifest (also written next to the PDF).
    """
    user_library: Dict[str, Any] = {}
    if library_path and Path(library_path).is_file():
        user_library = json.loads(Path(library_path).read_text(encoding="utf-8")) or {}

    racks, status_map = build_validation_racks(heights, user_library or None)

    config = ReportConfig()
    config.page_size = page_size
    builder = VastReportBuilder(config=config, library_path=library_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pdf_path = out_dir / f"rack_validation_{stamp}.pdf"
    pages = builder.generate_rack_validation_pdf(racks, status_map, str(pdf_path))

    manifest: Dict[str, Any] = {"pdf": str(pdf_path), "page_size": page_size, "racks": []}
    for r in racks:
        name = r["name"]
        manifest["racks"].append(
            {
                "name": name,
                "height_u": r["height_u"],
                "drawn_height_u": r.get("drawn_height_u"),
                "u_height_pt": r.get("u_height_pt"),
                "heading_page": pages.get(f"rack:{name}:heading"),
                "diagram_page": pages.get(f"rack:{name}:diagram"),
                "devices": [
                    {k: v for k, v in d.items() if k not in ("x", "y", "width", "height", "indicator_box")}
                    for d in r.get("placed_devices", [])
                ],
            }
        )
    json_path = pdf_path.with_suffix(".json")
    json_path.write_text(json.dumps(manifest, indent=2, default=str), encoding="utf-8")
    manifest["json"] = str(json_path)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the full-rack validation report.")
    parser.add_argument("--out", default=str(ROOT / "output" / "rack-validation"), help="Output directory")
    parser.add_argument("--page-size", choices=["A4", "Letter"], default="A4")
    parser.add_argument("--heights", default="", help="Comma-separated rack heights (default: all supported)")
    parser.add_argument("--library", default=None, help="Optional user device_library.json to include")
    args = parser.parse_args()

    heights = [int(h) for h in args.heights.split(",") if h.strip()] or None
    manifest = generate(Path(args.out), args.page_size, heights, args.library)

    problems = []
    for r in manifest["racks"]:
        filled = sum(d["u_height"] for d in r["devices"])
        if r["heading_page"] != r["diagram_page"]:
            problems.append(f"{r['name']}: heading on page {r['heading_page']}, rack on page {r['diagram_page']}")
        if filled != r["height_u"]:
            problems.append(f"{r['name']}: {filled}/{r['height_u']}U filled")
        print(f"{r['name']:<12} {r['height_u']}U  {len(r['devices']):>2} devices  {filled}U  page {r['diagram_page']}")
    print(f"PDF:  {manifest['pdf']}\nJSON: {manifest['json']}")
    for p in problems:
        print(f"PROBLEM: {p}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
