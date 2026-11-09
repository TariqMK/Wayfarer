"""Stores trips as JSON files in the WayfarerData folder next to the app. The app stores user data nowhere else."""

import json
import os
import re
import secrets
import sys
import tempfile
from pathlib import Path

DATA_FOLDER = "WayfarerData"
# One path component ending in .json. This rejects separators, drive prefixes and dot names.
_SAFE_NAME = re.compile(r"^[^/\\:*?\"<>|\x00-\x1f.][^/\\:*?\"<>|\x00-\x1f]*\.json$")


class TripNameError(ValueError):
    """The file name is not a plain trip file name."""


def data_dir() -> Path:
    """Return the data folder: next to the exe, next to the .app on macOS, or in the project root from source."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent / DATA_FOLDER
    exe = Path(sys.executable).resolve()
    if sys.platform == "darwin":
        for parent in exe.parents:
            if parent.suffix == ".app":
                return parent.parent / DATA_FOLDER
    return exe.parent / DATA_FOLDER


def is_writable(folder: Path) -> bool:
    """Return True if the app can create the folder and write files in it."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=folder):
            return True
    except OSError:
        return False


def slugify(title: str, fallback: str = "trip") -> str:
    """Turn a title into a safe, readable file name part."""
    slug = re.sub(r"[^\w-]+", "-", (title or "").strip(), flags=re.UNICODE).strip("-_")
    return slug[:60].rstrip("-_") or fallback


class TripStore:
    """Reads and writes trip files. A trip keeps its file name for life, whatever its title becomes."""

    def __init__(self, root: Path | None = None):
        self.dir = Path(root) if root else data_dir() / "trips"

    def _path(self, filename: str) -> Path:
        if not isinstance(filename, str) or not _SAFE_NAME.match(filename):
            raise TripNameError(f"Not a trip file name: {filename!r}")
        return self.dir / filename

    def list(self) -> list[dict]:
        """Return a summary of each trip. A file that can't be read is listed with `error` set, not hidden."""
        if not self.dir.is_dir():
            return []
        trips = []
        for path in self.dir.glob("*.json"):
            try:
                trips.append(_summary(path.name, json.loads(path.read_text(encoding="utf-8-sig"))))
            except (OSError, ValueError, AttributeError, TypeError):
                trips.append({"filename": path.name, "title": path.name, "error": True})
        return sorted(trips, key=lambda t: str(t["title"]).casefold())

    def load(self, filename: str) -> dict:
        # utf-8-sig also reads files that an editor saved with a byte-order mark.
        data = json.loads(self._path(filename).read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError("A trip file must hold one JSON object")  # noqa: TRY004
        return data

    def save(self, trip: dict, filename: str | None = None) -> str:
        """Write the trip and return its file name. With no file name, create a new file."""
        path = self._path(filename) if filename else self._new_path(trip.get("title", ""))
        self.dir.mkdir(parents=True, exist_ok=True)
        _write_atomic(path, json.dumps(trip, indent=2, ensure_ascii=False))
        return path.name

    def delete(self, filename: str) -> None:
        self._path(filename).unlink(missing_ok=True)

    def _new_path(self, title: str) -> Path:
        # The random part means two trips with the same title can't share a file.
        return self.dir / f"{slugify(title)}-{secrets.token_hex(4)}.json"


def _summary(filename: str, data: dict) -> dict:
    days = data.get("days") or []
    dates = sorted(d["date"] for d in days if d.get("date"))
    modes = [
        entry.get("type", "note")
        for day in days
        for slot in ("morning", "afternoon", "evening")
        for entry in (day.get("slots") or {}).get(slot) or []
    ]
    return {
        "filename": filename,
        "title": data.get("title") or "Untitled trip",
        "subtitle": data.get("subtitle") or "",
        "days": len(days),
        "first": dates[0] if dates else "",
        "last": dates[-1] if dates else "",
        "modes": modes,
    }


def _write_atomic(path: Path, text: str) -> None:
    """Write through a temporary file, so a crash can't leave a half-written trip."""
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".part")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
