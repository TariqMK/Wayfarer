"""Manual update check. Runs only when the user selects the version number, and asks GitHub for the latest release."""

import json
import re
import urllib.error
import urllib.request

from wayfarer._version import __version__

APP_NAME = "Wayfarer"
REPO = "TariqMK/Wayfarer"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases"
TIMEOUT_SECONDS = 10


def parse_version(text) -> tuple[int, int, int] | None:
    """Parse vX.Y.Z or X.Y.Z. Anything else, including a development version, returns None."""
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(text).strip())
    return tuple(int(n) for n in match.groups()) if match else None


def safe_release_url(url) -> str:
    """Return an https:// URL, or the general releases page if the URL is missing or unsafe."""
    return url if isinstance(url, str) and url.startswith("https://") else RELEASES_URL


def display_version(version: str = __version__) -> str:
    return f"v{version}"


def evaluate(release: dict, current: str = __version__) -> dict:
    """Compare a GitHub release answer with the current version and return what to show."""
    latest = parse_version(release.get("tag_name") if isinstance(release, dict) else None)
    if latest is None:
        return _error(f"GitHub sent an answer {APP_NAME} can't read. Try again later.")
    tag = "v{}.{}.{}".format(*latest)
    url = safe_release_url(release.get("html_url"))
    notes = release.get("body") if isinstance(release.get("body"), str) else ""
    mine = parse_version(current)
    if mine is None:
        return {
            "status": "development",
            "headline": "This is a development build.",
            "detail": f"You are running {display_version(current)}. The latest release is {tag}.",
            "latest": tag,
            "url": url,
            "notes": notes,
        }
    if latest > mine:
        return {
            "status": "newer",
            "headline": f"{APP_NAME} {tag} is available.",
            "detail": f"You have {display_version(current)}. Open the release page to download the new version.",
            "latest": tag,
            "url": url,
            "notes": notes,
        }
    return {
        "status": "current",
        "headline": f"{APP_NAME} is up to date.",
        "detail": f"{display_version(current)} is the latest release.",
    }


def _error(message: str) -> dict:
    return {"status": "error", "headline": "Check for updates", "detail": message}


def check(opener=urllib.request.urlopen, current: str = __version__) -> dict:
    """Send one GET to GitHub and return the result. It sends only the required headers."""
    request = urllib.request.Request(
        API_URL,
        headers={
            "User-Agent": f"{APP_NAME}/{current}",
            "Accept": "application/vnd.github+json",
        },
    )
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            release = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return _error(f"No {APP_NAME} releases are published yet.")
        if e.code in (403, 429):
            return _error("GitHub limits how often it can be checked. Try again in an hour.")
        return _error(f"GitHub answered with error {e.code}. Try again later.")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        reason = getattr(e, "reason", None) or e
        return _error(f"Can't reach GitHub: {reason}. Check the internet connection.")
    except ValueError:
        return _error(f"GitHub sent an answer {APP_NAME} can't read. Try again later.")
    return evaluate(release, current)
