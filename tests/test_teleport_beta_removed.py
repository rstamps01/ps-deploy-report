"""Teleport Mode is out of Beta: no Beta badge or labeling in the current UI or docs registry."""

import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
TEMPLATES = ROOT / "frontend" / "templates"


def test_reporter_has_no_beta_badge():
    source = (TEMPLATES / "reporter.html").read_text()
    assert "beta-badge" not in source
    assert "Beta Feature" not in source
    assert "conn-mode-opt--beta" not in source


def test_tsh_pill_still_anchored_on_teleport_option():
    source = (TEMPLATES / "reporter.html").read_text()
    option = re.search(r'<label class="conn-mode-opt conn-mode-opt--teleport">(.*?)</label>', source, re.S)
    assert option and 'id="reporterTshPill"' in option.group(1)
    assert ".conn-mode-opt--teleport { position: relative; }" in source


def test_teleport_not_labeled_beta_in_ui_or_docs_registry():
    for path in (TEMPLATES / "advanced_config.html", ROOT / "src" / "app.py", ROOT / "docs" / "TELEPORT-MODE.md"):
        assert not re.search(r"Teleport( Mode)? \(Beta\)", path.read_text()), path.name
