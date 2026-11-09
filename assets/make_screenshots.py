"""Takes the README screenshots from the real app, in light and dark, with made-up sample trips.

Writes assets/screenshots/<view>-light.png and <view>-dark.png for: trips, editor, poster-route, poster-survey,
poster-tickets. Each image is 1120 x 720 px at 2x (2240 x 1440).

How it works: the app runs from source with its data folder in a new temporary folder, so no real trips or
settings load. WebView2 opens a debugging port on 127.0.0.1 only. The script drives the UI and captures the
page content through that port. Nothing goes on the network. The version label shows the newest git tag.

Windows only (WebView2). Run from the project root with the project's Python:
  pip install websocket-client
  python assets/make_screenshots.py
"""

import base64
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "screenshots"
WIDTH, HEIGHT, SCALE = 1120, 720, 2


def entry(type_, from_="", to="", duration="", unit="hrs", note="", **extra):
    return {"type": type_, "from": from_, "to": to, "duration": duration, "unit": unit, "note": note, **extra}


def day(date, label, morning=(), afternoon=(), evening=()):
    return {"date": date, "label": label, "slots": {"morning": list(morning), "afternoon": list(afternoon), "evening": list(evening)}}


# Made-up sample trips. Nothing here comes from a real trip.
MAIN_TRIP = {
    "title": "Japan in spring",
    "subtitle": "Tokyo to Osaka",
    "notes": "Rail pass from day 2. Cash for temples.",
    "poster": "route",
    "days": [
        day("2027-04-02", "Arrive in Tokyo",
            morning=[entry("plane", "LHR", "HND", "14", note="Flight WF 204")],
            afternoon=[entry("train", "Haneda", "Shinjuku", "45", "mins")],
            evening=[entry("walk", "Hotel", "Omoide Yokocho", "20", "mins", note="Dinner")]),
        day("2027-04-03", "Old Tokyo",
            morning=[entry("train", "Shinjuku", "Asakusa", "35", "mins"), entry("note", note="Senso-ji temple")],
            afternoon=[entry("boat", "Asakusa", "Hamarikyu", "40", "mins", note="Sumida river bus")],
            evening=[entry("taxi", "Ginza", "Hotel", "25", "mins")]),
        day("2027-04-04", "Mountains",
            morning=[entry("train", "Shinjuku", "Hakone-Yumoto", "85", "mins")],
            afternoon=[entry("hike", "Hakone-Yumoto", "Lake Ashi", "3")],
            evening=[entry("bus", "Lake Ashi", "Ryokan", "30", "mins", note="Onsen stay")]),
        day("2027-04-05", "Kyoto",
            morning=[entry("train", "Odawara", "Kyoto", "2", note="Shinkansen, seat 7A")],
            afternoon=[entry("cycle", "Kyoto Station", "Fushimi Inari", "30", "mins")],
            evening=[entry("walk", "Gion", "Pontocho", "15", "mins")]),
        day("2027-04-06", "Osaka",
            morning=[entry("train", "Kyoto", "Osaka", "30", "mins")],
            afternoon=[entry("walk", "Namba", "Dotonbori", "10", "mins")],
            evening=[entry("plane", "KIX", "LHR", "15", note="Flight WF 211", overnight=True, spansNights="1")]),
    ],
}
OTHER_TRIPS = [
    {"title": "Scottish Highlands", "subtitle": "Edinburgh to Skye", "days": [
        day("2027-08-14", "Edinburgh", morning=[entry("train", "London", "Edinburgh", "4")]),
        day("2027-08-15", "North", morning=[entry("car", "Edinburgh", "Glencoe", "3")], afternoon=[entry("hike", "Glencoe", "Lost Valley", "3")]),
        day("2027-08-16", "Skye", morning=[entry("car", "Glencoe", "Portree", "3")], evening=[entry("boat", "Portree", "Raasay", "25", "mins")]),
    ]},
    {"title": "Portugal coast", "subtitle": "Lisbon to Porto", "days": [
        day("2027-10-01", "Lisbon", morning=[entry("plane", "LGW", "LIS", "2")], afternoon=[entry("walk", "Baixa", "Alfama", "30", "mins")]),
        day("2027-10-02", "Coast", morning=[entry("bus", "Lisbon", "Nazaré", "2")]),
        day("2027-10-03", "Porto", morning=[entry("bike", "Nazaré", "Porto", "3")]),
    ]},
]


def newest_tag() -> str:
    try:
        tag = subprocess.run(["git", "describe", "--tags", "--abbrev=0"], check=False, cwd=ROOT, capture_output=True, text=True).stdout.strip()
    except OSError:
        tag = ""
    return tag or "v1.0.0"


def run_app(data: Path, version: str) -> None:
    """Child process: the real app with its data folder and version label replaced."""
    sys.path.insert(0, str(ROOT))
    from wayfarer import app, update_check

    app.data_dir = lambda: data
    update_check.display_version = lambda *_: version
    app.main()


class Page:
    """A minimal Chrome DevTools Protocol client for the app's one page."""

    def __init__(self, port: int):
        import websocket

        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1) as r:
                    pages = [t for t in json.load(r) if t.get("type") == "page"]
                if pages:
                    break
            except OSError:
                pass
            time.sleep(0.5)
        else:
            sys.exit("The app window did not open.")
        self.ws = websocket.create_connection(pages[0]["webSocketDebuggerUrl"], timeout=30, suppress_origin=True)
        self.next_id = 0

    def call(self, method: str, **params):
        self.next_id += 1
        self.ws.send(json.dumps({"id": self.next_id, "method": method, "params": params}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == self.next_id:
                if "error" in message:
                    raise RuntimeError(f"{method}: {message['error']}")
                return message.get("result", {})

    def js(self, expression: str):
        result = self.call("Runtime.evaluate", expression=expression, awaitPromise=True, returnByValue=True)
        if "exceptionDetails" in result:
            raise RuntimeError(f"Script failed: {expression}\n{result['exceptionDetails']}")
        return result.get("result", {}).get("value")

    def wait_for(self, expression: str, seconds: float = 20):
        end = time.time() + seconds
        while time.time() < end:
            if self.js(expression):
                return
            time.sleep(0.2)
        sys.exit(f"Timed out waiting for: {expression}")

    def capture(self, path: Path) -> None:
        self.js("document.fonts.ready.then(() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))))")
        time.sleep(0.3)
        data = self.call("Page.captureScreenshot", format="png")["data"]
        path.write_bytes(base64.b64decode(data))
        print(f"Wrote {path.relative_to(ROOT)}")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--app":
        run_app(Path(sys.argv[2]), sys.argv[3])
        return 0
    if sys.platform != "win32":
        sys.exit("This script needs Windows (WebView2).")

    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wayfarer-shots-", ignore_cleanup_errors=True) as tmp:
        data = Path(tmp) / "WayfarerData"
        trips = data / "trips"
        trips.mkdir(parents=True)
        # Oldest first, so the main trip is the most recent file.
        for i, trip in enumerate([*OTHER_TRIPS, MAIN_TRIP]):
            path = trips / f"sample-{i}-0000000{i}.json"
            path.write_text(json.dumps(trip, ensure_ascii=False, indent=2), encoding="utf-8")
            os.utime(path, (1_800_000_000 + i * 1000, 1_800_000_000 + i * 1000))
        main_file = f"sample-{len(OTHER_TRIPS)}-0000000{len(OTHER_TRIPS)}.json"

        port = free_port()
        env = {**os.environ, "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS": f"--remote-debugging-port={port} --remote-debugging-address=127.0.0.1"}
        child = subprocess.Popen([sys.executable, __file__, "--app", str(data), newest_tag()], cwd=ROOT, env=env)
        try:
            page = Page(port)
            page.call("Emulation.setDeviceMetricsOverride", width=WIDTH, height=HEIGHT, deviceScaleFactor=SCALE, mobile=False)
            page.wait_for("typeof S !== 'undefined' && S.loaded && S.trips.length === 3")
            for theme in ("light", "dark"):
                page.call("Emulation.setEmulatedMedia", features=[{"name": "prefers-color-scheme", "value": theme}])
                page.wait_for(f"document.documentElement.dataset.theme === '{theme}'")

                page.js("S.screen = 'home'; S.trip = null; S.filename = null; loadTrips()")
                page.wait_for("!!document.querySelector('.tripcard')")
                page.capture(OUT / f"trips-{theme}.png")

                page.js(f"document.querySelector('[data-action=open-trip][data-file=\"{main_file}\"]').click()")
                page.wait_for("S.screen === 'trip' && !!document.querySelector('.ent')")
                # Open one entry for editing, as a user would.
                page.js("document.querySelectorAll('.ent [data-action=select-entry]')[5].click()")
                page.wait_for("!!document.querySelector('.ent.sel')")
                page.js("document.activeElement.blur()")
                page.capture(OUT / f"editor-{theme}.png")

                page.js("S.selected = null; S.tab = 'preview'; render()")
                for key in ("route", "survey", "tickets"):
                    # Set the style directly so the header does not show "Unsaved changes".
                    page.js(f"S.trip.poster = '{key}'; render(); document.querySelector('.scroll').scrollTop = 0")
                    page.wait_for("!!document.querySelector('#poster-slot > *')")
                    page.capture(OUT / f"poster-{key}-{theme}.png")
                page.js("S.trip.poster = 'route'; S.tab = 'editor'; S.screen = 'home'; render()")
            # Close the app. The connection drops with the window, so don't wait for an answer.
            page.ws.send(json.dumps({"id": 0, "method": "Runtime.evaluate", "params": {"expression": "window.pywebview.api.close_window()"}}))
        finally:
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.terminate()
                child.wait(timeout=10)
        # WebView2 helper processes can hold files for a moment after the window closes.
        for _ in range(20):
            shutil.rmtree(tmp, ignore_errors=True)
            if not Path(tmp).exists():
                break
            time.sleep(0.5)
    return 0


if __name__ == "__main__":
    sys.exit(main())
