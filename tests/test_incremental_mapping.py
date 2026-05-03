from __future__ import annotations

from pathlib import Path

import contextopt.mapper as mapper
from contextopt.graph import GraphStore


def test_unchanged_file_reuses_cached_extraction(tmp_path: Path, monkeypatch):
    source = tmp_path / "app.py"
    source.write_text("def hello():\n    return 'world'\n", encoding="utf-8")
    store = GraphStore(tmp_path / ".contextopt" / "context.db")

    first = mapper.map_project(tmp_path, store)
    assert first.files_extracted == 1
    assert first.files_reused == 0

    def fail_if_rescanned(path: Path, rel_path: str):  # pragma: no cover - should not run
        raise AssertionError(f"unchanged file was rescanned: {rel_path}")

    monkeypatch.setattr(mapper, "extract_file", fail_if_rescanned)
    second = mapper.map_project(tmp_path, store)

    assert second.files_seen == 1
    assert second.files_extracted == 0
    assert second.files_reused == 1
    assert store.rows("SELECT sha256 FROM files WHERE rel_path = ?", ("app.py",))[0]["sha256"]
    assert (
        store.rows(
            "SELECT name FROM nodes WHERE kind = 'function' AND path = ?",
            ("app.py",),
        )[0]["name"]
        == "hello"
    )


def test_changed_file_is_extracted_and_replaces_previous_nodes(tmp_path: Path):
    source = tmp_path / "app.py"
    source.write_text("def old_name():\n    return 'old'\n", encoding="utf-8")
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    mapper.map_project(tmp_path, store)

    source.write_text("def new_name():\n    return 'new'\n", encoding="utf-8")
    result = mapper.map_project(tmp_path, store)

    assert result.files_extracted == 1
    assert result.files_reused == 0
    names = [
        row["name"]
        for row in store.rows("SELECT name FROM nodes WHERE kind = 'function' ORDER BY name")
    ]
    assert names == ["new_name"]
