"""Release-readiness tests for the in-app update notification.

These lock in that an *already shipped* install detects the next published
GitHub Release and surfaces the header "UPDATE AVAILABLE" pill with working
download links. Unlike test_updater.py (which unit-tests the primitives), this
exercises a realistic multi-release GitHub payload — including the actual
artifact names produced by .github/workflows/build-release.yml — with the
network mocked, so it doubles as the automated "staged dry-run" for the QA
phase (no live GitHub call).

Two generations are covered:

- 1.5.8 → 1.6.0 (historical; still the installed base that cannot be patched)
- 1.6.0 → 1.6.1 (this release)

It also covers the macOS architecture split. Releases publish two mac DMGs
(arm64 + x64), which the resolver reports under separate keys so the UI can
offer the right one. ``download_url_mac`` survives as a single best-guess slot
because already-installed 1.5.8/1.6.0 clients read only that field and cannot
be patched retroactively — those clients keep getting one working DMG, and the
per-architecture choice reaches users from 1.6.1 onward.
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

# The exact asset names build-release.yml attaches to each GitHub Release.
V160_ASSETS = [
    {"name": "VAST-Reporter-v1.6.0-mac-arm64.dmg", "browser_download_url": "https://gh/dl/v160/mac-arm64.dmg"},
    {"name": "VAST-Reporter-v1.6.0-mac-x64.dmg", "browser_download_url": "https://gh/dl/v160/mac-x64.dmg"},
    {"name": "VAST-Reporter-v1.6.0-win.zip", "browser_download_url": "https://gh/dl/v160/win.zip"},
]

V161_ASSETS = [
    {"name": "VAST-Reporter-v1.6.1-mac-arm64.dmg", "browser_download_url": "https://gh/dl/mac-arm64.dmg"},
    {"name": "VAST-Reporter-v1.6.1-mac-x64.dmg", "browser_download_url": "https://gh/dl/mac-x64.dmg"},
    {"name": "VAST-Reporter-v1.6.1-win.zip", "browser_download_url": "https://gh/dl/win.zip"},
]


def _realistic_releases_payload():
    """Mirror what GitHub /releases returned after v1.6.0 shipped.

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
        self.assertEqual(result["download_url_win"], "https://gh/dl/v160/win.zip")
        # All three published assets are surfaced to the dropdown.
        self.assertEqual(len(result["assets"]), 3)

    @patch("requests.get")
    def test_already_on_160_sees_no_update(self, mock_get):
        """A user who already upgraded must NOT be nagged."""
        mock_get.return_value = _mock_resp(_realistic_releases_payload())
        result = check_for_update("1.6.0", include_prereleases=False)
        self.assertFalse(result["update_available"])


def _post_161_payload():
    """GitHub /releases once v1.6.1 is published (1.6.0 remains as the prior stable)."""
    return [
        {
            "tag_name": "v1.6.1",
            "prerelease": False,
            "draft": False,
            "html_url": "https://gh/releases/v1.6.1",
            "assets": V161_ASSETS,
        },
        *_realistic_releases_payload(),
    ]


class TestShipped160SeesStable161(unittest.TestCase):
    """Headline for this release: a live 1.6.0 (and 1.5.8) build detects 1.6.1."""

    @patch("requests.get")
    def test_160_client_detects_161(self, mock_get):
        mock_get.return_value = _mock_resp(_post_161_payload())
        result = check_for_update("1.6.0", include_prereleases=False)
        self.assertTrue(result["update_available"], "1.6.0 must see 1.6.1 as newer")
        self.assertEqual(result["latest_version"], "1.6.1")
        self.assertEqual(result["release_notes_url"], "https://gh/releases/v1.6.1")
        self.assertIsNone(result["error"])

    @patch("requests.get")
    def test_158_client_also_detects_161(self, mock_get):
        mock_get.return_value = _mock_resp(_post_161_payload())
        result = check_for_update("1.5.8", include_prereleases=False)
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest_version"], "1.6.1")

    @patch("requests.get")
    def test_already_on_161_sees_no_update(self, mock_get):
        mock_get.return_value = _mock_resp(_post_161_payload())
        result = check_for_update("1.6.1", include_prereleases=False)
        self.assertFalse(result["update_available"])

    @patch("requests.get")
    def test_161_download_links_are_architecture_aware(self, mock_get):
        mock_get.return_value = _mock_resp(_post_161_payload())
        result = check_for_update("1.6.0", include_prereleases=False)
        self.assertEqual(result["download_url_mac_arm64"], "https://gh/dl/mac-arm64.dmg")
        self.assertEqual(result["download_url_mac_x64"], "https://gh/dl/mac-x64.dmg")
        self.assertEqual(result["download_url_win"], "https://gh/dl/win.zip")


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
        self.assertTrue(is_newer("1.6.1", "1.6.0"))
        self.assertFalse(is_newer("1.6.0", "1.6.1"))


class TestMacArchDownloads(unittest.TestCase):
    """Each macOS architecture resolves to its own build."""

    def test_each_arch_resolves_to_its_own_dmg(self):
        out = extract_download_urls({"assets": V161_ASSETS})
        self.assertEqual(out["mac_arm64"], "https://gh/dl/mac-arm64.dmg")
        self.assertEqual(out["mac_x64"], "https://gh/dl/mac-x64.dmg")
        self.assertEqual(out["win"], "https://gh/dl/win.zip")

    def test_arch_matching_is_independent_of_asset_order(self):
        # GitHub does not promise asset ordering, and relying on it was the
        # original defect: an Intel Mac could be handed the arm64 build.
        out = extract_download_urls({"assets": list(reversed(V161_ASSETS))})
        self.assertEqual(out["mac_arm64"], "https://gh/dl/mac-arm64.dmg")
        self.assertEqual(out["mac_x64"], "https://gh/dl/mac-x64.dmg")

    def test_single_slot_stays_populated_for_already_shipped_clients(self):
        # 1.5.8/1.6.0 clients read only download_url_mac and cannot be patched.
        out = extract_download_urls({"assets": V161_ASSETS})
        self.assertIn(out["mac"], {"https://gh/dl/mac-arm64.dmg", "https://gh/dl/mac-x64.dmg"})


if __name__ == "__main__":
    unittest.main()
