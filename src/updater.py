"""QP-3 (2): in-app update notifications (phase 2a — notify + download only).

Checks GitHub Releases for a newer version of the app and reports whether an
update is available, along with the release page / download URL.  This module
**only notifies**; it never downloads, applies, or relaunches anything.

Design notes:
    * Pure version comparison (:func:`parse_version`, :func:`is_newer`) is
      dependency-free and unit-testable without network access.
    * :func:`check_for_update` performs the network call and degrades
      gracefully: any error returns ``update_available=False`` with an
      ``error`` string rather than raising.
    * :func:`get_update_status` caches the most recent successful check in
      process memory with a short TTL so the UI can poll cheaply.
"""

import re
import time
from typing import Any, Dict, List, Optional, Tuple

from utils.logger import get_logger

logger = get_logger(__name__)

GITHUB_REPO = "rstamps01/ps-deploy-report"
RELEASES_API = "https://api.github.com/repos/{repo}/releases"
DEFAULT_TIMEOUT = 6.0
# How long a successful check is cached in-process (seconds).
CACHE_TTL = 3600.0

# (major, minor, patch, is_release, prerelease_token)
VersionKey = Tuple[int, int, int, int, str]

_VERSION_RE = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:[-+](.+))?$")


def parse_version(value: str) -> Optional[VersionKey]:
    """Parse ``X.Y.Z`` / ``vX.Y.Z`` / ``X.Y.Z-prerelease`` into a sort key.

    A release sorts above an otherwise-equal pre-release (``1.5.8`` > ``1.5.8-beta``).
    Pre-release tokens are compared lexically, which orders the tokens this
    project uses correctly (``alpha`` < ``beta`` < ``rc``).

    Returns:
        A comparable tuple, or ``None`` if the string is not a recognizable
        version.
    """
    if not value:
        return None
    match = _VERSION_RE.match(value.strip())
    if not match:
        return None
    major = int(match.group(1))
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    pre = (match.group(4) or "").lower()
    # is_release=1 when there's no pre-release suffix so releases outrank pre-releases.
    is_release = 0 if pre else 1
    return (major, minor, patch, is_release, pre)


def is_newer(candidate: str, current: str) -> bool:
    """True if ``candidate`` is a strictly newer version than ``current``."""
    cand_key = parse_version(candidate)
    cur_key = parse_version(current)
    if cand_key is None or cur_key is None:
        return False
    return cand_key > cur_key


def _release_is_prerelease(release: Dict[str, Any]) -> bool:
    """True if a GitHub release object represents a pre-release."""
    if release.get("prerelease"):
        return True
    tag = str(release.get("tag_name", ""))
    # Treat any tag with a pre-release suffix (e.g. v1.5.8-beta) as pre-release.
    return "-" in tag


def extract_download_urls(release: Dict[str, Any]) -> Dict[str, Any]:
    """Pull platform installer download URLs out of a release's assets.

    Recognizes this project's release artifacts (``*-mac.dmg`` / ``*-win.zip``)
    and reasonable fallbacks so the UI can offer a one-click, OS-matched
    download without sending the user to GitHub.

    Returns:
        ``{"assets": [{"name", "url"}, ...], "mac": <url|None>, "win": <url|None>}``
    """
    assets_in = release.get("assets") or []
    assets: List[Dict[str, str]] = []
    mac_url: Optional[str] = None
    win_url: Optional[str] = None
    for asset in assets_in:
        name = str(asset.get("name", ""))
        url = asset.get("browser_download_url")
        if not name or not url:
            continue
        assets.append({"name": name, "url": url})
        lower = name.lower()
        if mac_url is None and (lower.endswith(".dmg") or ("mac" in lower and lower.endswith(".zip"))):
            mac_url = url
        if win_url is None and (("win" in lower and lower.endswith(".zip")) or lower.endswith(".exe")):
            win_url = url
    return {"assets": assets, "mac": mac_url, "win": win_url}


def select_latest_release(
    releases: List[Dict[str, Any]],
    *,
    include_prereleases: bool,
) -> Optional[Dict[str, Any]]:
    """Pick the highest-versioned, non-draft release matching the channel.

    Args:
        releases: GitHub ``/releases`` response objects.
        include_prereleases: When False, pre-releases are excluded.

    Returns:
        The selected release object, or ``None`` if none qualify.
    """
    best: Optional[Dict[str, Any]] = None
    best_key: Optional[VersionKey] = None
    for release in releases or []:
        if release.get("draft"):
            continue
        if not include_prereleases and _release_is_prerelease(release):
            continue
        key = parse_version(str(release.get("tag_name", "")))
        if key is None:
            continue
        if best_key is None or key > best_key:
            best_key = key
            best = release
    return best


def check_for_update(
    current_version: str,
    *,
    include_prereleases: bool = False,
    repo: str = GITHUB_REPO,
    timeout: float = DEFAULT_TIMEOUT,
) -> Dict[str, Any]:
    """Query GitHub Releases and report whether a newer version exists.

    Never raises: network/parse failures return ``update_available=False`` with
    an ``error`` message so callers (and the UI) can degrade gracefully.
    """
    result: Dict[str, Any] = {
        "update_available": False,
        "current_version": current_version,
        "latest_version": None,
        "latest_url": None,
        "release_notes_url": None,
        "download_url_mac": None,
        "download_url_win": None,
        "assets": [],
        "channel": "prerelease" if include_prereleases else "stable",
        "checked_at": time.time(),
        "error": None,
    }
    try:
        import requests

        resp = requests.get(
            RELEASES_API.format(repo=repo),
            headers={"Accept": "application/vnd.github+json"},
            timeout=timeout,
        )
        resp.raise_for_status()
        releases = resp.json()
        if not isinstance(releases, list):
            raise ValueError("unexpected releases payload")
    except Exception as exc:  # noqa: BLE001 — update check must never crash the app
        logger.debug("Update check failed: %s", exc)
        result["error"] = str(exc)
        return result

    latest = select_latest_release(releases, include_prereleases=include_prereleases)
    if not latest:
        return result

    latest_tag = str(latest.get("tag_name", "")).lstrip("v")
    result["latest_version"] = latest_tag
    result["latest_url"] = latest.get("html_url")
    result["release_notes_url"] = latest.get("html_url")
    result["update_available"] = is_newer(latest_tag, current_version)
    downloads = extract_download_urls(latest)
    result["assets"] = downloads["assets"]
    result["download_url_mac"] = downloads["mac"]
    result["download_url_win"] = downloads["win"]
    return result


_CACHE: Dict[str, Any] = {"result": None, "at": 0.0}


def get_update_status(
    current_version: str,
    *,
    include_prereleases: bool = False,
    force: bool = False,
    repo: str = GITHUB_REPO,
) -> Dict[str, Any]:
    """Return a cached update-check result, refreshing past the TTL.

    Args:
        force: Bypass the cache and re-check now.
    """
    now = time.time()
    cached: Optional[Dict[str, Any]] = _CACHE.get("result")
    if (
        not force
        and cached is not None
        and (now - float(_CACHE.get("at", 0.0))) < CACHE_TTL
        and cached.get("channel") == ("prerelease" if include_prereleases else "stable")
    ):
        return cached
    result = check_for_update(current_version, include_prereleases=include_prereleases, repo=repo)
    # Only cache successful checks so a transient outage doesn't suppress
    # notifications for the full TTL.
    if result.get("error") is None:
        _CACHE["result"] = result
        _CACHE["at"] = now
    return result
