"""End-to-end check of Wayfarer: start-up, Trips screen, open, save, and text, PNG and PDF exports, on made-up trips.

It opens the real UI in this system's web engine (WebView2, WebKit or WebKitGTK) with the real Python API behind
pywebview's bridge, then drives it the same way a user does. It checks each step's effect on disk, not only the reply.
It only touches the files it makes in the work folder. The Save dialog is replaced by a fixed path in that folder.

This is the one check that proves the bridge starts on each web engine (see GitHub issue #1). It needs the app's own
dependency, pywebview, plus the standard library. On Linux it also needs the GTK packages listed in the README.

Usage, from the project root with the project's Python:
  python scripts/check_e2e.py [--work <new empty folder>]
Leave out --work to use a new temporary folder. A window opens for about 20 s, then closes by itself.
"""

# Template from the tariq-project-standards skill. Wayfarer has no web server, so the checks run through the bridge.
import argparse
import hashlib
import json
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import webview

from wayfarer.app import UI_INDEX, Api

# --- Fill in for this app ----------------------------------------------------------------------------
APP_NAME = "Wayfarer"
# Made-up sample trips. Never real or personal data.
SAMPLE_TRIP = {
    "title": "Alps by rail",
    "subtitle": "Zurich to Milan",
    "notes": "Made-up trip for the end-to-end check.",
    "poster": "route",
    "days": [
        {
            "date": "2027-06-01",
            "label": "Arrive",
            "slots": {
                "morning": [{"type": "plane", "from": "LGW", "to": "ZRH", "duration": "2", "unit": "hrs", "note": ""}],
                "afternoon": [
                    {"type": "train", "from": "Zurich", "to": "Lucerne", "duration": "45", "unit": "mins", "note": ""}
                ],
                "evening": [],
            },
        },
        {
            "date": "2027-06-02",
            "label": "South",
            "slots": {
                "morning": [
                    {"type": "train", "from": "Lucerne", "to": "Lugano", "duration": "2", "unit": "hrs", "note": ""}
                ],
                "afternoon": [
                    {"type": "walk", "from": "Lugano", "to": "Monte Bre", "duration": "90", "unit": "mins", "note": ""}
                ],
                "evening": [
                    {"type": "train", "from": "Lugano", "to": "Milan", "duration": "75", "unit": "mins", "note": ""}
                ],
            },
        },
    ],
}
BOM_TRIP = {"title": "Lakes weekend", "subtitle": "", "days": []}
# -----------------------------------------------------------------------------------------------------

failures = []


def check(name, ok, detail=""):
    """Print PASS or FAIL for one step and remember failures."""
    print(("PASS " if ok else "FAIL ") + name + (f" -- {detail}" if detail and not ok else ""), flush=True)
    if not ok:
        failures.append(name)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_work_folder(path):
    """Use a new temporary folder, or the given one only if it's new or empty, so real files are never touched."""
    if path is None:
        return Path(tempfile.mkdtemp(prefix="check_e2e_"))
    work = Path(path)
    if work.exists() and any(work.iterdir()):
        sys.exit(f"Work folder must be new or empty: {work}")
    work.mkdir(parents=True, exist_ok=True)
    return work


parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("--work", help="New or empty work folder; default is a new temporary folder")
parser.add_argument("--timeout", type=float, default=60, help="Seconds to wait for each step (default 60)")
args = parser.parse_args()

work = make_work_folder(args.work).resolve()
root = work / "WayfarerData"
trips, exports = root / "trips", root / "exports"
trips.mkdir(parents=True)
exports.mkdir()
(trips / "alps-by-rail-0000e2e1.json").write_text(json.dumps(SAMPLE_TRIP, indent=2), encoding="utf-8")
(trips / "lakes-weekend-0000e2e2.json").write_text(json.dumps(BOM_TRIP), encoding="utf-8-sig")  # PowerShell style
(trips / "damaged-0000e2e3.json").write_text("{ not json", encoding="utf-8")
before = {p.name: sha(p) for p in trips.iterdir()}
print(f"Work folder: {work}", flush=True)


def ask_save_path(suggested, kind):
    return str(exports / suggested)


api = Api(root=root, ask_save_path=ask_save_path)


def run(window):
    def js(code):
        return window.evaluate_js(code)

    def wait(name, code, timeout=args.timeout):
        """Poll a JavaScript expression until it's truthy. Returns its last value."""
        end, value = time.time() + timeout, None
        while time.time() < end:
            try:
                value = js(code)
            except Exception as e:  # noqa: BLE001 - the page may still be loading.
                value = f"error: {e}"
            if value and not str(value).startswith("error:"):
                return value
            time.sleep(0.25)
        check(name, False, f"timed out, last value {value!r}")
        return None

    try:
        # --- App checks ----------------------------------------------------------------------------
        if wait("Bridge starts and Trips screen loads", "typeof S !== 'undefined' && S.loaded === true"):
            check("Bridge starts and Trips screen loads", True)
        check("No start-up failure message", not js("document.body.innerText.includes('could not start')"))
        check("Version label is shown", bool(js("document.getElementById('version').textContent.trim()")))
        cards = js("document.querySelectorAll('.tripcard').length")
        check("Trips screen lists all 3 trip files", cards == 3, cards)
        check("Damaged trip is listed, not hidden", js("document.querySelectorAll('.tripcard.bad').length") == 1)
        check(
            "Trip saved with a byte-order mark opens as normal",
            bool(js("document.body.innerText.includes('Lakes weekend')")),
        )

        js("document.querySelector('[data-action=open-trip][data-file=\"alps-by-rail-0000e2e1.json\"]').click()")
        if wait("Editor opens the trip", "S.screen === 'trip' && S.trip && S.trip.title === 'Alps by rail'"):
            check("Editor opens the trip", True)

        js(
            "S.trip.title = 'Alps by rail and lake'; setDirty(true); document.querySelector('[data-action=save]').click()"
        )
        wait(
            "Save finishes", "S.dirty === false && document.getElementById('toast').textContent.includes('Trip saved')"
        )
        saved = json.loads((trips / "alps-by-rail-0000e2e1.json").read_text(encoding="utf-8"))
        check("Save writes the new title to the same file", saved.get("title") == "Alps by rail and lake")
        check("Save makes no second file", len(list(trips.glob("*.json"))) == 3)
        check(
            "Save leaves the other trips unchanged",
            all(sha(trips / n) == h for n, h in before.items() if n != "alps-by-rail-0000e2e1.json"),
        )

        for fmt, ext, magic in (
            ("text", "txt", b"ALPS BY RAIL AND LAKE"),
            ("image", "png", b"\x89PNG"),
            ("pdf", "pdf", b"%PDF"),
        ):
            out = exports / f"Alps-by-rail-and-lake.{ext}"
            js("document.querySelector('[data-action=open-export]').click()")
            wait(f"Export dialog opens ({fmt})", "!!document.querySelector('[data-action=run-export]')")
            js(f"document.querySelector('[data-action=export-opt][data-opt=format][data-value={fmt}]').click()")
            js("document.querySelector('[data-action=run-export]').click()")
            if wait(
                f"Export {fmt} finishes",
                "document.getElementById('toast').textContent.includes('Saved to')"
                f" && document.getElementById('toast').textContent.includes('.{ext}')",
                timeout=args.timeout * 2,
            ):
                data = out.read_bytes() if out.exists() else b""
                ok = (magic in data.upper()) if fmt == "text" else data.startswith(magic)
                check(f"Export {fmt} writes a real .{ext} file", ok and len(data) > 100, f"{len(data)} bytes")

        js("pywebview.api.delete_trip('damaged-0000e2e3.json').then(r => window.__e2eDelete = r)")
        r = wait("Delete answers", "window.__e2eDelete")
        check(
            "Delete removes only that trip file",
            bool(r and r.get("ok"))
            and not (trips / "damaged-0000e2e3.json").exists()
            and (trips / "lakes-weekend-0000e2e2.json").exists(),
        )
        check(
            "Data folder holds only trips and exports", sorted(p.name for p in root.iterdir()) == ["exports", "trips"]
        )
        # -------------------------------------------------------------------------------------------
    except Exception as e:  # noqa: BLE001 - report any failure, then close the window.
        check("Check ran to the end", False, repr(e))
    finally:
        api._closing_confirmed = True
        window.destroy()


window = webview.create_window(APP_NAME + " (end-to-end check)", url=str(UI_INDEX), js_api=api, width=1300, height=840)
api._attach(window)
webview.start(run, window, storage_path=str(work / "webview"))

print(f"RESULT: {'FAIL' if failures else 'PASS'} ({len(failures)} failed)", flush=True)
sys.exit(1 if failures else 0)
