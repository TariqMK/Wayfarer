"""Builds export content: the plain text itinerary, and a PDF from JPEG page images."""

import re
import struct
from datetime import date

SLOTS = (("morning", "Morning"), ("afternoon", "Afternoon"), ("evening", "Evening"))
TYPE_LABELS = {
    "plane": "Flight",
    "car": "Drive",
    "train": "Train",
    "bus": "Bus",
    "cycle": "Cycle",
    "bike": "Motorbike",
    "boat": "Boat",
    "walk": "Walk",
    "taxi": "Taxi",
    "hike": "Hike",
    "note": "Stop or note",
}
UNIT_SUFFIX = {"mins": "m", "hrs": "h", "days": "d"}
A4_WIDTH_PT = 595.28


def _parse_date(value) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def format_date(value) -> str:
    """Return 'Monday 3 May 2027', or '' for a missing or invalid date."""
    d = _parse_date(value)
    return f"{d:%A} {d.day} {d:%B %Y}" if d else ""


def format_duration(entry: dict) -> str:
    """Return '45m', or free text such as '2h 45m' unchanged."""
    duration = str(entry.get("duration") or "").strip()
    if re.fullmatch(r"\d+([.,]\d+)?", duration):
        return duration + UNIT_SUFFIX.get(entry.get("unit"), "")
    return duration


def count_nights(days: list[dict]) -> int:
    """Return the calendar gap between the first and last dated days."""
    dates = sorted(d for d in (_parse_date(day.get("date")) for day in days) if d)
    return (dates[-1] - dates[0]).days if len(dates) >= 2 else 0


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _entry_lines(entry: dict) -> list[str]:
    kind = entry.get("type") or "note"
    label = TYPE_LABELS.get(kind, kind.title())
    note = (entry.get("note") or "").strip()
    if kind == "note":
        head = note or label
        note = ""
    else:
        route = " → ".join(p for p in (entry.get("from"), entry.get("to")) if p)
        head = f"{label}: {route}" if route else label
    extras = []
    if duration := format_duration(entry):
        extras.append(duration)
    if entry.get("overnight"):
        spans = str(entry.get("spansNights") or 1)
        extras.append("Overnight" if spans == "1" else f"{spans} nights")
    if extras:
        head += f" ({', '.join(extras)})"
    return [f"    {head}"] + ([f"      {note}"] if note else [])


def build_text(trip: dict) -> str:
    """Return the trip as a plain text itinerary."""
    days = trip.get("days") or []
    lines = [trip.get("title") or "Untitled trip"]
    if trip.get("subtitle"):
        lines.append(trip["subtitle"])
    summary = [_plural(len(days), "day")]
    if nights := count_nights(days):
        summary.append(_plural(nights, "night"))
    lines.append(", ".join(summary))
    if trip.get("notes"):
        lines += ["", "Notes", *(f"  {line}" for line in trip["notes"].splitlines())]
    for number, day in enumerate(days, 1):
        head = [f"Day {number}"]
        if when := format_date(day.get("date")):
            head.append(when)
        if day.get("label"):
            head.append(day["label"])
        lines += ["", ": ".join([head[0], ", ".join(head[1:])]) if len(head) > 1 else head[0]]
        for slot, slot_label in SLOTS:
            entries = (day.get("slots") or {}).get(slot) or []
            if entries:
                lines.append(f"  {slot_label}")
                for entry in entries:
                    lines += _entry_lines(entry)
    return "\n".join(lines) + "\n"


def jpeg_size(data: bytes) -> tuple[int, int]:
    """Return (width, height) from a JPEG's frame header."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("Not a JPEG image")
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            raise ValueError("Damaged JPEG image")
        marker = data[i + 1]
        if marker == 0xFF:  # A marker may have fill bytes before it.
            i += 1
            continue
        if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
            height, width = struct.unpack(">HH", data[i + 5 : i + 9])
            return width, height
        i += 2 + struct.unpack(">H", data[i + 2 : i + 4])[0]
    raise ValueError("Damaged JPEG image")


def build_pdf(pages: list[bytes], title: str = "") -> bytes:
    """Return a PDF with one full-page image per JPEG. Each page is A4 wide and as tall as its image."""
    if not pages:
        raise ValueError("A PDF needs at least one page")
    safe_title = re.sub(r"[()\\\r\n]", " ", title).encode("latin-1", "replace").decode("latin-1")
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        3: f"<< /Title ({safe_title}) /Producer (Wayfarer) >>".encode("latin-1"),
    }
    kids = []
    for n, jpeg in enumerate(pages):
        page_id, image_id, content_id = 4 + n * 3, 5 + n * 3, 6 + n * 3
        width, height = jpeg_size(jpeg)
        page_h = A4_WIDTH_PT * height / width
        content = f"q {A4_WIDTH_PT:.2f} 0 0 {page_h:.2f} 0 0 cm /Im Do Q".encode()
        objects[page_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {A4_WIDTH_PT:.2f} {page_h:.2f}] "
            f"/Contents {content_id} 0 R /Resources << /XObject << /Im {image_id} 0 R >> >> >>"
        ).encode()
        objects[image_id] = (
            f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} /ColorSpace /DeviceRGB "
            f"/BitsPerComponent 8 /Filter /DCTDecode /Length {len(jpeg)} >>\nstream\n"
        ).encode() + jpeg + b"\nendstream"
        objects[content_id] = f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream"
        kids.append(f"{page_id} 0 R")
    objects[2] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>".encode()

    out = bytearray(b"%PDF-1.4\n")
    offsets = {}
    for oid in sorted(objects):
        offsets[oid] = len(out)
        out += f"{oid} 0 obj\n".encode() + objects[oid] + b"\nendobj\n"
    xref = len(out)
    count = max(objects) + 1
    out += f"xref\n0 {count}\n0000000000 65535 f \n".encode()
    for oid in range(1, count):
        out += f"{offsets[oid]:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {count} /Root 1 0 R /Info 3 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return bytes(out)
