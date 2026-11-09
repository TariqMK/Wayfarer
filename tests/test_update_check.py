"""Tests for the manual update check. The HTTP call is always stubbed, so these never use the network."""

import io
import json
import urllib.error

import pytest

from wayfarer.update_check import RELEASES_URL, check, evaluate, parse_version, safe_release_url


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def answer(body):
    def opener(request, timeout):
        answer.request, answer.timeout = request, timeout
        return Response(body if isinstance(body, bytes) else json.dumps(body).encode())

    return opener


def failing(error):
    def opener(request, timeout):
        raise error

    return opener


def http_error(code):
    return urllib.error.HTTPError("https://x", code, "x", {}, None)


@pytest.mark.parametrize(("text", "expected"), [("v1.2.3", (1, 2, 3)), ("1.2.3", (1, 2, 3)), ("0.0.0.dev0", None), ("v1.2", None), ("nope", None), (None, None)])
def test_parse_version(text, expected):
    assert parse_version(text) == expected


def test_versions_compare_as_numbers():
    result = evaluate({"tag_name": "v0.10.0", "html_url": "https://github.com/x"}, current="0.9.0")
    assert result["status"] == "newer"
    assert result["headline"] == "Wayfarer v0.10.0 is available."
    assert result["detail"] == "You have v0.9.0. Open the release page to download the new version."


def test_up_to_date():
    result = evaluate({"tag_name": "v1.0.0"}, current="1.0.0")
    assert result["headline"] == "Wayfarer is up to date."
    assert result["detail"] == "v1.0.0 is the latest release."
    assert "url" not in result


def test_newer_local_build_is_up_to_date():
    assert evaluate({"tag_name": "v1.0.0"}, current="1.1.0")["status"] == "current"


def test_development_build_is_never_up_to_date_or_older():
    result = evaluate({"tag_name": "v2.5.0", "body": "Notes"}, current="0.0.0.dev0")
    assert result["status"] == "development"
    assert result["detail"] == "You are running v0.0.0.dev0. The latest release is v2.5.0."
    assert result["notes"] == "Notes"


@pytest.mark.parametrize("url", [None, "", "http://github.com/x", "javascript:alert(1)", 5])
def test_unsafe_url_falls_back_to_releases_page(url):
    assert safe_release_url(url) == RELEASES_URL


def test_https_url_is_kept():
    assert safe_release_url("https://github.com/a/b/releases/tag/v1.0.0").endswith("v1.0.0")


def test_request_sends_only_the_expected_headers():
    check(opener=answer({"tag_name": "v1.0.0"}), current="1.0.0")
    assert answer.timeout == 10
    assert answer.request.full_url == "https://api.github.com/repos/TariqMK/Wayfarer/releases/latest"
    assert set(answer.request.headers) == {"User-agent", "Accept"}
    assert answer.request.headers["User-agent"] == "Wayfarer/1.0.0"


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (http_error(404), "No Wayfarer releases are published yet."),
        (http_error(403), "GitHub limits how often it can be checked. Try again in an hour."),
        (http_error(429), "GitHub limits how often it can be checked. Try again in an hour."),
        (http_error(500), "GitHub answered with error 500. Try again later."),
        (urllib.error.URLError("no route"), "Can't reach GitHub: no route. Check the internet connection."),
        (TimeoutError("timed out"), "Can't reach GitHub: timed out. Check the internet connection."),
    ],
)
def test_error_messages(error, message):
    result = check(opener=failing(error), current="1.0.0")
    assert result["status"] == "error"
    assert result["detail"] == message


@pytest.mark.parametrize("body", [b"not json", {"tag_name": "latest"}, {}, [1]])
def test_unreadable_answers(body):
    result = check(opener=answer(body), current="1.0.0")
    assert result["detail"] == "GitHub sent an answer Wayfarer can't read. Try again later."
