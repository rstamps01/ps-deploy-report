"""Tests for the in-app update checker (src/updater.py, QP-3 item 2).

Pure version comparison is exercised offline; the network path is exercised
with a mocked ``requests.get`` so no real GitHub call is made.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import updater  # noqa: E402
from updater import (  # noqa: E402
    parse_version,
    is_newer,
    select_latest_release,
    check_for_update,
    get_update_status,
    extract_download_urls,
)


class TestParseVersion(unittest.TestCase):
    def test_plain_semver(self):
        self.assertEqual(parse_version("1.5.8"), (1, 5, 8, 1, ""))

    def test_v_prefix_stripped(self):
        self.assertEqual(parse_version("v1.5.8"), (1, 5, 8, 1, ""))

    def test_prerelease_ranks_below_release(self):
        # is_release flag (4th element) is 0 for pre-releases, 1 for releases.
        self.assertLess(parse_version("1.5.8-beta"), parse_version("1.5.8"))

    def test_missing_minor_patch_default_zero(self):
        self.assertEqual(parse_version("2"), (2, 0, 0, 1, ""))

    def test_unparseable_returns_none(self):
        self.assertIsNone(parse_version("not-a-version"))
        self.assertIsNone(parse_version(""))


class TestIsNewer(unittest.TestCase):
    def test_higher_patch_is_newer(self):
        self.assertTrue(is_newer("1.5.9", "1.5.8"))

    def test_same_version_not_newer(self):
        self.assertFalse(is_newer("1.5.8", "1.5.8"))

    def test_older_not_newer(self):
        self.assertFalse(is_newer("1.5.7", "1.5.8"))

    def test_release_newer_than_own_prerelease(self):
        self.assertTrue(is_newer("1.5.8", "1.5.8-beta"))

    def test_prerelease_not_newer_than_release(self):
        self.assertFalse(is_newer("1.5.8-beta", "1.5.8"))

    def test_garbage_is_not_newer(self):
        self.assertFalse(is_newer("garbage", "1.5.8"))


class TestSelectLatestRelease(unittest.TestCase):
    def _rel(self, tag, prerelease=False, draft=False):
        return {"tag_name": tag, "prerelease": prerelease, "draft": draft, "html_url": "u/" + tag}

    def test_picks_highest_stable(self):
        releases = [self._rel("v1.5.7"), self._rel("v1.5.8"), self._rel("v1.5.6")]
        best = select_latest_release(releases, include_prereleases=False)
        self.assertEqual(best["tag_name"], "v1.5.8")

    def test_excludes_prerelease_on_stable_channel(self):
        releases = [self._rel("v1.5.8"), self._rel("v1.6.0-beta", prerelease=True)]
        best = select_latest_release(releases, include_prereleases=False)
        self.assertEqual(best["tag_name"], "v1.5.8")

    def test_includes_prerelease_when_requested(self):
        releases = [self._rel("v1.5.8"), self._rel("v1.6.0-beta", prerelease=True)]
        best = select_latest_release(releases, include_prereleases=True)
        self.assertEqual(best["tag_name"], "v1.6.0-beta")

    def test_skips_drafts(self):
        releases = [self._rel("v1.9.9", draft=True), self._rel("v1.5.8")]
        best = select_latest_release(releases, include_prereleases=True)
        self.assertEqual(best["tag_name"], "v1.5.8")

    def test_tag_dash_treated_as_prerelease(self):
        # No explicit prerelease flag, but a '-' suffix marks it pre-release.
        releases = [self._rel("v1.6.0-rc1", prerelease=False)]
        self.assertIsNone(select_latest_release(releases, include_prereleases=False))

    def test_empty_returns_none(self):
        self.assertIsNone(select_latest_release([], include_prereleases=True))


class TestExtractDownloadUrls(unittest.TestCase):
    def test_picks_mac_dmg_and_win_zip(self):
        release = {
            "assets": [
                {"name": "VAST-Reporter-v1.6.0-mac.dmg", "browser_download_url": "http://x/mac.dmg"},
                {"name": "VAST-Reporter-v1.6.0-win.zip", "browser_download_url": "http://x/win.zip"},
            ]
        }
        out = extract_download_urls(release)
        self.assertEqual(out["mac"], "http://x/mac.dmg")
        self.assertEqual(out["win"], "http://x/win.zip")
        self.assertEqual(len(out["assets"]), 2)

    def test_mac_zip_fallback(self):
        release = {
            "assets": [
                {"name": "VAST-Reporter-v1.6.0-mac.zip", "browser_download_url": "http://x/mac.zip"},
            ]
        }
        out = extract_download_urls(release)
        self.assertEqual(out["mac"], "http://x/mac.zip")
        self.assertIsNone(out["win"])

    def test_skips_assets_without_url_or_name(self):
        release = {"assets": [{"name": "", "browser_download_url": "http://x/none"}]}
        out = extract_download_urls(release)
        self.assertEqual(out["assets"], [])

    def test_no_assets(self):
        out = extract_download_urls({})
        self.assertEqual(out, {"assets": [], "mac": None, "win": None})


class TestCheckForUpdate(unittest.TestCase):
    def _mock_resp(self, payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.raise_for_status.return_value = None
        return resp

    @patch("requests.get")
    def test_update_available(self, mock_get):
        mock_get.return_value = self._mock_resp(
            [
                {
                    "tag_name": "v1.6.0",
                    "prerelease": False,
                    "draft": False,
                    "html_url": "http://x/1.6.0",
                    "assets": [
                        {"name": "VAST-Reporter-v1.6.0-mac.dmg", "browser_download_url": "http://x/mac.dmg"},
                        {"name": "VAST-Reporter-v1.6.0-win.zip", "browser_download_url": "http://x/win.zip"},
                    ],
                }
            ]
        )
        result = check_for_update("1.5.8", include_prereleases=False)
        self.assertTrue(result["update_available"])
        self.assertEqual(result["latest_version"], "1.6.0")
        self.assertEqual(result["latest_url"], "http://x/1.6.0")
        self.assertEqual(result["release_notes_url"], "http://x/1.6.0")
        self.assertEqual(result["download_url_mac"], "http://x/mac.dmg")
        self.assertEqual(result["download_url_win"], "http://x/win.zip")
        self.assertIsNone(result["error"])

    @patch("requests.get")
    def test_no_update_when_current_is_latest(self, mock_get):
        mock_get.return_value = self._mock_resp(
            [{"tag_name": "v1.5.8", "prerelease": False, "draft": False, "html_url": "u"}]
        )
        result = check_for_update("1.5.8", include_prereleases=False)
        self.assertFalse(result["update_available"])

    @patch("requests.get", side_effect=Exception("network down"))
    def test_network_error_is_graceful(self, mock_get):
        result = check_for_update("1.5.8")
        self.assertFalse(result["update_available"])
        self.assertEqual(result["error"], "network down")

    @patch("requests.get")
    def test_channel_recorded(self, mock_get):
        mock_get.return_value = self._mock_resp([])
        self.assertEqual(check_for_update("1.5.8", include_prereleases=True)["channel"], "prerelease")
        self.assertEqual(check_for_update("1.5.8", include_prereleases=False)["channel"], "stable")


class TestGetUpdateStatusCache(unittest.TestCase):
    def setUp(self):
        updater._CACHE = {"result": None, "at": 0.0}

    @patch("updater.check_for_update")
    def test_caches_successful_result(self, mock_check):
        mock_check.return_value = {"update_available": False, "channel": "stable", "error": None}
        get_update_status("1.5.8")
        get_update_status("1.5.8")
        self.assertEqual(mock_check.call_count, 1)

    @patch("updater.check_for_update")
    def test_force_bypasses_cache(self, mock_check):
        mock_check.return_value = {"update_available": False, "channel": "stable", "error": None}
        get_update_status("1.5.8")
        get_update_status("1.5.8", force=True)
        self.assertEqual(mock_check.call_count, 2)

    @patch("updater.check_for_update")
    def test_errors_not_cached(self, mock_check):
        mock_check.return_value = {"update_available": False, "channel": "stable", "error": "boom"}
        get_update_status("1.5.8")
        get_update_status("1.5.8")
        self.assertEqual(mock_check.call_count, 2)


if __name__ == "__main__":
    unittest.main()
