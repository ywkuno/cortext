from pathlib import Path
from contextopt.graph import GraphStore
from contextopt.mapper import map_project
from contextopt.exporters.markdown import export_markdown


def test_map_and_export(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        """def hello():
    return 'world'
""",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    result = map_project(tmp_path, store)
    assert result.files_seen >= 1
    assert result.nodes_written >= 1

    out = tmp_path / ".contextopt" / "context-pack.md"
    export_markdown(store, out)
    assert "hello" in out.read_text(encoding="utf-8")
