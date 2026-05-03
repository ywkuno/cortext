from pathlib import Path
from contextopt.scanner import scan_files


def test_scan_files_ignores_node_modules(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("bad", encoding="utf-8")
    assert [f.rel_path for f in scan_files(tmp_path)] == ["src/app.py"]


def test_scan_files_respects_gitignore_and_extra_patterns(tmp_path: Path):
    (tmp_path / ".gitignore").write_text(
        ".pytest_cache/\n*.egg-info/\n*.txt\n!important.txt\n",
        encoding="utf-8",
    )
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "README.md").write_text("cache", encoding="utf-8")
    (tmp_path / "pkg.egg-info").mkdir()
    (tmp_path / "pkg.egg-info" / "PKG-INFO").write_text("generated", encoding="utf-8")
    (tmp_path / "custom").mkdir()
    (tmp_path / "custom" / "skip.py").write_text("print('skip')", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("skip", encoding="utf-8")
    (tmp_path / "important.txt").write_text("keep", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')", encoding="utf-8")

    rel_paths = [f.rel_path for f in scan_files(tmp_path, ignore_patterns=["custom/"])]

    assert rel_paths == [".gitignore", "important.txt", "src/app.py"]
