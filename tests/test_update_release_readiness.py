"""Release-readiness tests for the 1.5.8 -> 1.6.0 in-app update notification.

These lock in the specific requirement that an *already shipped* v1.5.8 install
correctly detects a published v1.6.0 GitHub Release and surfaces the header
"UPDATE AVAILABLE" pill with working download links. Unlike test_updater.py
(which unit-tests the primitives), this exercises the realistic multi-release
GitHub payload — including the actual v1.6.0 artifact names produced by
.github/workflows/build-release.yml — with the network mocked, so it doubles as
the automated "staged dry-run" for the QA phase (no live GitHub call).

It also documents a known caveat: a shipped 1.5.8 client only has a single
``download_url_mac`` slot, so with two mac DMGs (arm64 + x64) it links whichever
DMG GitHub returns first. We can't patch already-installed clients; this test
pins the behavior so it is intentional, not a surprise.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from updater import (  # noqa: E402
    check_for_update,
    select_latest_release,
    extract_download_urls,
    is_newer,
)

# The exact asset names build-release.yml attaches to the v1.6.0 GitHub Release.
V160_ASSETS = [
    {"name": "VAST-Reporter-v1.6.0-mac-arm64.dmg", "browser_download_url": "https://gh/dl/mac-arm64.dmg"},
    {"name": "VAST-Reporter-v1.6.0-mac-x64.dmg", "browser_download_url": "https://gh/dl/mac-x64.dmg"},
    {"name": "VAST-Reporter-v1.6.0-win.zip", "browser_download_url": "https://gh/dl/win.zip"},
]


def _realistic_releases_payload():
    """Mirror what GitHub /releases returns for this repo once v1.6.0 ships.

    Intentionally includes noise a real response carries: a pre-release
    (v1.5.8-beta), a non-version tag (pre-1.5.8-cleanup), and older stable tags.
    """
    return [
        {
            "tag_name": "v1.6.0",
            "prerelease": False,
            "draft": False,
            "html_url": "https://gh/releases/v1.6.0",
            "assets": V160_ASSETS,
        },
        {
            "tag_name": "pre-1.5.8-cleanup",  # non-version safety tag — must be ignored
            "prerelease": False,
            "draft": False,
            "html_url": "https://gh/releases/pre-1.5.8-cleanup",
            "assets": [],
        },
        {
            "tag_name": "v1.5.8",
            "prerelease": False,
            "draft": False,
            "html_url": "https://gh/releases/v1.5.8",
            "assets": [],
        },
        {
            "tag_name": "v1.5.8-beta",
            "prerelease": True,
            "draft": False,
            "html_url": "https://gh/releases/v1.5.8-beta",
            "assets": [],
        },
    ]


def _mock_resp(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


class TestShipped158SeesStable160(unittest.TestCase):
    """The headline requirement: a live 1.5.8 build detects the 1.6.0 release."""

    @patch("requests.get")
    def test_158_client_detects_160(self, mock_get):
        mock_get.return_value = _mock_resp(_realistic_releases_payload())
        result = check_for_update("1.5.8", include_prereleases=False)
        self.assertTrue(result["update_available"], "1.5.8 must see 1.6.0 as newer")
        self.assertEqual(result["latest_version"], "1.6.0")
        self.assertEqual(result["release_notes_url"], "https://gh/releases/v1.6.0")
        self.assertIsNone(result["error"])

    @patch("requests.get")
    def test_download_links_populated_for_both_platforms(self, mock_get):
        mock_get.return_value = _mock_resp(_realistic_releases_payload())
        result = check_for_update("1.5.8", include_prereleases=False)
        self.assertTrue(str(result["download_url_mac"]).endswith(".dmg"))
        self.assertEqual(result["download_url_win"], "https://gh/dl/win.zip")
        # All three published assets are surfaced to the dropdown.
        self.assertEqual(len(result["assets"]), 3)

    @patch("requests.get")
    def test_already_on_160_sees_no_update(self, mock_get):
        """A user who already upgraded must NOT be nagged."""
        mock_get.return_value = _mock_resp(_realistic_releases_payload())
        result = check_for_update("1.6.0", include_prereleases=False)
        self.assertFalse(result["update_available"])


class TestReleaseSelectionRobustness(unittest.TestCase):
    def test_non_version_tag_is_ignored(self):
        best = select_latest_release(_realistic_releases_payload(), include_prereleases=False)
        self.assertEqual(best["tag_name"], "v1.6.0")

    def test_stable_channel_excludes_158_beta(self):
        # Only pre-releases present besides beta -> stable picks the stable 1.6.0.
        best = select_latest_release(_realistic_releases_payload(), include_prereleases=False)
        self.assertNotIn("beta", best["tag_name"])

    def test_is_newer_direct(self):
        self.assertTrue(is_newer("1.6.0", "1.5.8"))
        self.assertFalse(is_newer("1.5.8", "1.6.0"))


class TestMacArchDownloadCaveat(unittest.TestCase):
    """Documents the known dual-DMG limitation for shipped single-slot clients."""

    def test_first_dmg_is_selected_when_two_arches_present(self):
        out = extract_download_urls({"assets": V160_ASSETS})
        # A shipped 1.5.8 client exposes ONE mac URL; it is the first DMG listed.
        self.assertEqual(out["mac"], "https://gh/dl/mac-arm64.dmg")
        self.assertEqual(out["win"], "https://gh/dl/win.zip")

    def test_selected_mac_is_one_of_the_published_dmgs(self):
        out = extract_download_urls({"assets": V160_ASSETS})
        self.assertIn(out["mac"], {"https://gh/dl/mac-arm64.dmg", "https://gh/dl/mac-x64.dmg"})


if __name__ == "__main__":
    unittest.main()
