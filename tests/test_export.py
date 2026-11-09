"""Tests for the text itinerary and the PDF writer."""

import re
import struct

import pytest

from wayfarer.export import build_pdf, build_text, count_nights, format_date, format_duration, jpeg_size


def fake_jpeg(width=100, height=141):
    """Return the header bytes of a JPEG, enough for size parsing."""
    app0 = b"\xff\xe0" + struct.pack(">H", 4) + b"\x00\x00"
    sof = b"\xff\xc0" + struct.pack(">HBHH", 11, 8, height, width) + b"\x00" * 6
    return b"\xff\xd8" + app0 + sof + b"\xff\xd9"


TRIP = {
    "title": "Portugal coast",
    "subtitle": "Lisbon to Porto",
    "notes": "Line one\nLine two",
    "days": [
        {
            "date": "2027-05-03",
            "label": "Arrive",
            "slots": {
                "morning": [{"type": "plane", "from": "LHR", "to": "LIS", "duration": "2", "unit": "hrs", "note": "TP1363"}],
                "afternoon": [{"type": "note", "note": "Check in"}],
                "evening": [],
            },
        },
        {
            "date": "2027-05-05",
            "slots": {"evening": [{"type": "bus", "from": "Nazaré", "to": "Porto", "overnight": True, "spansNights": "2"}]},
        },
    ],
}


def test_text_has_the_trip_summary_and_notes():
    text = build_text(TRIP)
    assert text.startswith("Portugal coast\nLisbon to Porto\n2 days, 2 nights\n")
    assert "  Line two" in text


def test_text_entries_show_type_route_duration_and_note():
    text = build_text(TRIP)
    assert "Day 1: Monday 3 May 2027, Arrive" in text
    assert "    Flight: LHR → LIS (2h)\n      TP1363" in text
    assert "    Check in\n" in text
    assert "Bus: Nazaré → Porto (2 nights)" in text


def test_hike_with_no_route_keeps_its_label():
    # Regression: the old export had no label for Hike, so this line was blank.
    text = build_text({"days": [{"slots": {"morning": [{"type": "hike"}]}}]})
    assert "    Hike\n" in text


def test_text_handles_empty_trip_and_missing_fields():
    assert build_text({}) == "Untitled trip\n0 days\n"
    assert "Day 1\n" in build_text({"days": [{}]})


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"duration": "45", "unit": "mins"}, "45m"),
        ({"duration": "1.5", "unit": "hrs"}, "1.5h"),
        ({"duration": "2h 45m", "unit": "hrs"}, "2h 45m"),
        ({"duration": ""}, ""),
        ({}, ""),
    ],
)
def test_format_duration(entry, expected):
    assert format_duration(entry) == expected


def test_nights_ignore_invalid_and_missing_dates():
    assert count_nights([{"date": "2027-05-01"}, {"date": "bad"}, {}, {"date": "2027-05-04"}]) == 3
    assert count_nights([{"date": "2027-05-01"}]) == 0


def test_format_date_rejects_bad_values():
    assert format_date("2027-05-03") == "Monday 3 May 2027"
    assert format_date("03/05/2027") == ""
    assert format_date(None) == ""


def test_jpeg_size_reads_the_frame_header():
    assert jpeg_size(fake_jpeg(1650, 2333)) == (1650, 2333)


@pytest.mark.parametrize("data", [b"", b"\x89PNG\r\n", b"\xff\xd8\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"])
def test_jpeg_size_rejects_other_data(data):
    with pytest.raises(ValueError):
        jpeg_size(data)


def test_pdf_has_one_page_per_image_and_a_valid_xref():
    pdf = build_pdf([fake_jpeg(), fake_jpeg(), fake_jpeg()], "Portugal (coast)")
    assert pdf.startswith(b"%PDF-1.4")
    assert b"/Count 3" in pdf
    assert pdf.count(b"/Type /Page ") == 3
    start = int(re.search(rb"startxref\n(\d+)", pdf).group(1))
    assert pdf[start:start + 4] == b"xref"
    # Every object offset in the table points at that object.
    table = re.findall(rb"(\d{10}) 00000 n", pdf[start:])
    for number, offset in enumerate(table, 1):
        assert pdf[int(offset):].startswith(f"{number} 0 obj".encode())


def test_pdf_title_cannot_break_the_file():
    pdf = build_pdf([fake_jpeg()], "a) /Evil (b\\")
    assert b"/Title (a  /Evil  b )" in pdf


def test_pdf_needs_a_page():
    with pytest.raises(ValueError):
        build_pdf([])
