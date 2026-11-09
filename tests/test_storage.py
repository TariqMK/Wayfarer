"""Tests for trip file storage: naming, overwrite safety, unsafe names and damaged files."""

import json
import sys
from pathlib import Path

import pytest

from wayfarer.storage import TripNameError, TripStore, data_dir, is_writable, slugify


@pytest.fixture
def store(tmp_path):
    return TripStore(tmp_path / "trips")


def test_two_trips_with_the_same_title_keep_separate_files(store):
    first = store.save({"title": "Portugal", "days": []})
    second = store.save({"title": "Portugal", "days": [{}]})
    assert first != second
    assert len(store.load(first)["days"]) == 0
    assert len(store.load(second)["days"]) == 1


def test_renaming_a_trip_keeps_one_file(store):
    name = store.save({"title": "Old name"})
    assert store.save({"title": "New name"}, name) == name
    assert [t["title"] for t in store.list()] == ["New name"]


def test_title_with_only_symbols_gets_a_usable_name(store):
    assert store.save({"title": "///"}).startswith("trip-")


def test_reserved_windows_name_is_not_used_alone(store):
    assert store.save({"title": "CON"}) != "CON.json"


def test_non_latin_title_stays_readable():
    assert slugify("Zürich à Genève") == "Zürich-à-Genève"


def test_trip_from_the_old_app_loads_and_lists(store):
    store.dir.mkdir(parents=True)
    old = {"title": "Switzerland", "days": [{"date": "2026-08-24", "slots": {"morning": [{"type": "train"}]}}]}
    (store.dir / "Switzerland.json").write_text(json.dumps(old), encoding="utf-8")
    summary = store.list()[0]
    assert summary["filename"] == "Switzerland.json"
    assert summary["modes"] == ["train"]
    assert store.load("Switzerland.json")["title"] == "Switzerland"


@pytest.mark.parametrize("name", ["../evil.json", "..\\evil.json", "C:evil.json", ".json", "..json", "a.txt", "", None])
def test_unsafe_names_are_rejected(store, name):
    with pytest.raises(TripNameError):
        store.load(name)
    with pytest.raises(TripNameError):
        store.delete(name)
    if name:
        with pytest.raises(TripNameError):
            store.save({}, name)


def test_damaged_file_is_listed_not_hidden(store):
    store.dir.mkdir(parents=True)
    (store.dir / "broken.json").write_text("{not json", encoding="utf-8")
    (store.dir / "list.json").write_text("[1, 2]", encoding="utf-8")
    assert all(t["error"] for t in store.list())
    assert len(store.list()) == 2


def test_file_saved_with_a_byte_order_mark_is_not_damaged(store):
    # Regression: a trip edited in a program that adds a byte-order mark was listed as damaged.
    store.dir.mkdir(parents=True)
    (store.dir / "edited.json").write_bytes(b'\xef\xbb\xbf{"title": "Edited"}')
    assert store.list()[0]["title"] == "Edited"
    assert store.load("edited.json")["title"] == "Edited"


def test_save_leaves_no_temporary_files(store):
    store.save({"title": "A"})
    assert [p.suffix for p in store.dir.iterdir()] == [".json"]


def test_list_with_no_folder_is_empty(store):
    assert store.list() == []


def test_delete_removes_the_file(store):
    name = store.save({"title": "A"})
    store.delete(name)
    assert store.list() == []


def freeze(monkeypatch, exe):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))


def test_packaged_app_keeps_data_next_to_the_exe(monkeypatch, tmp_path):
    # Regression: this must be next to the exe, not in PyInstaller's temp folder that is deleted on close.
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "_MEI123"), raising=False)
    freeze(monkeypatch, tmp_path / "Portable" / "Wayfarer.exe")
    assert data_dir() == (tmp_path / "Portable" / "WayfarerData").resolve()


def test_data_dir_ignores_system_data_folders(monkeypatch, tmp_path):
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
    freeze(monkeypatch, tmp_path / "app" / "Wayfarer")
    assert data_dir().parent == (tmp_path / "app").resolve()


def test_macos_data_is_next_to_the_app_bundle_not_inside_it(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "platform", "darwin")
    freeze(monkeypatch, tmp_path / "Apps" / "Wayfarer.app" / "Contents" / "MacOS" / "Wayfarer")
    assert data_dir() == (tmp_path / "Apps" / "WayfarerData").resolve()


def test_source_run_uses_the_project_root():
    assert data_dir() == Path(__file__).resolve().parent.parent / "WayfarerData"


def test_is_writable_creates_the_folder(tmp_path):
    assert is_writable(tmp_path / "a" / "b")
    assert (tmp_path / "a" / "b").is_dir()


def test_is_writable_is_false_when_a_file_blocks_the_folder(tmp_path):
    (tmp_path / "blocked").write_text("x", encoding="utf-8")
    assert not is_writable(tmp_path / "blocked" / "sub")
