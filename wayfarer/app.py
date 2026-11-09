"""Opens the app window and gives the UI its Python API through pywebview's bridge. There is no web server of ours."""

import base64
import threading
import webbrowser
from pathlib import Path

import webview

from wayfarer import export, update_check
from wayfarer.storage import DATA_FOLDER, TripNameError, TripStore, data_dir, is_writable, slugify

UI_INDEX = Path(__file__).parent / "ui" / "index.html"
FILE_TYPES = {
    "txt": "Text file (*.txt)",
    "png": "PNG image (*.png)",
    "pdf": "PDF document (*.pdf)",
}
MOVE_ADVICE = f"Wayfarer can't write to its {DATA_FOLDER} folder. Move Wayfarer to a folder you can change, then open it again."


class Api:
    """Every public method here can be called from the UI as `pywebview.api.<name>`."""

    def __init__(self, store: TripStore | None = None, ask_save_path=None, root: Path | None = None):
        self._root = Path(root) if root else data_dir()
        self._store = store or TripStore(self._root / "trips")
        self._ask_save_path = ask_save_path or self._native_save_dialog
        self._window = None
        self._dirty = False
        self._closing_confirmed = False

    # Window ---------------------------------------------------------------------------

    def _attach(self, window) -> None:
        self._window = window
        window.events.closing += self._on_closing

    def _on_closing(self):
        """Stop the window closing over unsaved changes, and let the UI ask the user."""
        if self._dirty and not self._closing_confirmed:
            # The window waits for this handler, so calling into the page from here would deadlock.
            self._close_prompt = threading.Thread(target=self._ask_page_to_close, daemon=True)
            self._close_prompt.start()
            return False
        return True

    def _ask_page_to_close(self) -> None:
        self._window.evaluate_js("window.wayfarerRequestClose()")

    def set_dirty(self, dirty) -> None:
        self._dirty = bool(dirty)

    def close_window(self) -> None:
        """Close after the user has confirmed in the UI."""
        self._closing_confirmed = True
        if self._window:
            self._window.destroy()

    def _native_save_dialog(self, suggested: str, kind: str) -> str | None:
        """Open the Save dialog in the exports folder, so exports stay with the app's data by default."""
        exports = self._root / "exports"
        result = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=str(exports) if is_writable(exports) else "",
            save_filename=suggested,
            file_types=(FILE_TYPES[kind],),
        )
        if not result:
            return None
        return result if isinstance(result, str) else result[0]

    # Trips ----------------------------------------------------------------------------

    def get_version(self) -> str:
        return update_check.display_version()

    def get_data_problem(self) -> str | None:
        """Return a message for the user if the data folder can't be written, otherwise nothing."""
        return None if is_writable(self._root) else MOVE_ADVICE

    def list_trips(self) -> list[dict]:
        return self._store.list()

    def load_trip(self, filename) -> dict:
        try:
            return {"ok": True, "trip": self._store.load(filename)}
        except (OSError, ValueError, TripNameError) as e:
            return {"ok": False, "error": f"This trip can't be opened: {e}"}

    def save_trip(self, trip, filename=None) -> dict:
        try:
            return {"ok": True, "filename": self._store.save(trip, filename)}
        except OSError:
            return {"ok": False, "error": f"The trip was not saved. {MOVE_ADVICE}"}
        except ValueError as e:
            return {"ok": False, "error": f"The trip was not saved: {e}"}

    def delete_trip(self, filename) -> dict:
        try:
            self._store.delete(filename)
            return {"ok": True}
        except (OSError, ValueError) as e:
            return {"ok": False, "error": f"The trip was not deleted: {e}"}

    # Exports. Nothing is written until the user confirms a location in the Save dialog -----

    def build_text(self, trip) -> str:
        return export.build_text(trip)

    def export_text(self, trip) -> dict:
        return self._export(trip, "txt", lambda: export.build_text(trip).encode("utf-8"))

    def export_image(self, trip, png_base64) -> dict:
        return self._export(trip, "png", lambda: base64.b64decode(png_base64, validate=True))

    def export_pdf(self, trip, pages_base64) -> dict:
        def build():
            pages = [base64.b64decode(p, validate=True) for p in pages_base64]
            return export.build_pdf(pages, trip.get("title") or "")

        return self._export(trip, "pdf", build)

    def _export(self, trip, kind: str, build) -> dict:
        path = self._ask_save_path(f"{slugify(trip.get('title', ''), 'itinerary')}.{kind}", kind)
        if not path:
            return {"ok": False, "cancelled": True}
        try:
            Path(path).write_bytes(build())
        except (OSError, ValueError) as e:
            return {"ok": False, "error": f"The file was not saved: {e}"}
        return {"ok": True, "path": str(path)}

    # Updates --------------------------------------------------------------------------

    def check_for_updates(self) -> dict:
        return update_check.check()

    def open_release_page(self, url) -> None:
        webbrowser.open(update_check.safe_release_url(url))


def main() -> None:
    root = data_dir()
    api = Api(root=root)
    window = webview.create_window(
        "Wayfarer",
        url=str(UI_INDEX),
        js_api=api,
        width=1300,
        height=840,
        min_size=(960, 640),
        background_color="#141415",
    )
    api._attach(window)
    # Keep the web view's working files with the app's data too. Without a path, Windows puts them in the temp folder.
    # If the folder can't be written, the app still opens and the UI tells the user to move it.
    browser_files = root / "webview"
    webview.start(storage_path=str(browser_files) if is_writable(browser_files) else None)
