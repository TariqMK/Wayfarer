"""Tests for the UI page: its content policy must let pywebview's bridge start, or the window stays blank on macOS."""

import re
from pathlib import Path

INDEX = Path(__file__).parent.parent / "wayfarer" / "ui" / "index.html"


def script_sources():
    policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', INDEX.read_text(encoding="utf-8"))
    assert policy, "index.html has no content security policy"
    for directive in policy.group(1).split(";"):
        name, *sources = directive.split()
        if name == "script-src":
            return sources
    raise AssertionError("the content security policy has no script-src")


def test_policy_lets_pywebview_build_its_api():
    # pywebview creates pywebview.api.* with new Function(). macOS WebKit enforces the policy on that call.
    assert "'unsafe-eval'" in script_sources()


def test_policy_still_allows_only_bundled_scripts():
    assert script_sources() == ["'self'", "'unsafe-eval'"]
