"""Tests for the UI's Python API: exports write only after the Save dialog, and errors come back as messages."""

import base64

import pytest

from wayfarer.app import Api
from wayfarer.storage import TripStore


def make_api(tmp_path, save_path=None):
    calls = []

    def ask(suggested, kind):
        calls.append((suggested, kind))
        return save_path

    api = Api(store=TripStore(tmp_path / "trips"), ask_save_path=ask)
    api.calls = calls
    return api


def test_cancelled_save_dialog_writes_nothing(tmp_path):
    api = make_api(tmp_path, None)
    assert api.export_text({"title": "Trip"}) == {"ok": False, "cancelled": True}
    assert list(tmp_path.iterdir()) == []


def test_text_export_writes_to_the_chosen_path_with_a_suggested_name(tmp_path):
    target = tmp_path / "out.txt"
    api = make_api(tmp_path, str(target))
    assert api.export_text({"title": "Portugal coast"}) == {"ok": True, "path": str(target)}
    assert api.calls == [("Portugal-coast.txt", "txt")]
    assert target.read_text(encoding="utf-8").startswith("Portugal coast")


def test_image_export_decodes_base64(tmp_path):
    target = tmp_path / "out.png"
    api = make_api(tmp_path, str(target))
    assert api.export_image({"title": ""}, base64.b64encode(b"png-bytes").decode())["ok"]
    assert api.calls == [("itinerary.png", "png")]
    assert target.read_bytes() == b"png-bytes"


def test_bad_image_data_is_reported_and_writes_nothing(tmp_path):
    target = tmp_path / "out.png"
    result = make_api(tmp_path, str(target)).export_image({}, "not base64!!")
    assert result["ok"] is False
    assert not target.exists()


def test_bad_pdf_page_is_reported_and_writes_nothing(tmp_path):
    target = tmp_path / "out.pdf"
    result = make_api(tmp_path, str(target)).export_pdf({}, [base64.b64encode(b"nope").decode()])
    assert result["ok"] is False
    assert not target.exists()


def test_trip_round_trip_and_delete(tmp_path):
    api = make_api(tmp_path)
    name = api.save_trip({"title": "A", "poster": "survey"})["filename"]
    assert api.load_trip(name)["trip"]["poster"] == "survey"
    assert api.delete_trip(name) == {"ok": True}
    assert api.list_trips() == []


@pytest.mark.parametrize("call", ["load_trip", "delete_trip"])
def test_unsafe_names_return_a_message(tmp_path, call):
    result = getattr(make_api(tmp_path), call)("../../evil.json")
    assert result["ok"] is False
    assert "error" in result


def test_missing_trip_returns_a_message(tmp_path):
    assert make_api(tmp_path).load_trip("gone.json")["ok"] is False


def test_default_store_and_exports_stay_in_the_data_folder(tmp_path):
    class Window:
        def create_file_dialog(self, kind, directory, save_filename, file_types):
            self.directory, self.name = directory, save_filename
            return (str(tmp_path / "chosen.txt"),)

    api = Api(root=tmp_path / "WayfarerData")
    api._window = Window()
    assert api.save_trip({"title": "A"})["ok"]
    assert len(list((tmp_path / "WayfarerData" / "trips").glob("*.json"))) == 1
    assert api.export_text({"title": "A"})["ok"]
    assert api._window.directory == str(tmp_path / "WayfarerData" / "exports")
    assert api._window.name == "A.txt"


def test_unwritable_data_folder_is_reported(tmp_path):
    (tmp_path / "blocked").write_text("x", encoding="utf-8")
    api = Api(root=tmp_path / "blocked" / "WayfarerData")
    assert "Move Wayfarer" in api.get_data_problem()
    result = api.save_trip({"title": "A"})
    assert result["ok"] is False
    assert "Move Wayfarer" in result["error"]


def test_writable_data_folder_reports_no_problem(tmp_path):
    assert Api(root=tmp_path / "WayfarerData").get_data_problem() is None


def test_closing_is_stopped_only_with_unsaved_changes(tmp_path):
    class Window:
        script = None

        def evaluate_js(self, script):
            self.script = script

    api = make_api(tmp_path)
    api._window = Window()
    assert api._on_closing() is True
    api.set_dirty(True)
    assert api._on_closing() is False
    api._close_prompt.join(timeout=5)
    assert "wayfarerRequestClose" in api._window.script
    api._closing_confirmed = True
    assert api._on_closing() is True
