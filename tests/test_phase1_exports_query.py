from __future__ import annotations

from pathlib import Path

from contextopt.exporters.dot import export_dot
from contextopt.exporters.markdown import export_markdown
from contextopt.graph import GraphStore
from contextopt.mapper import map_project
from contextopt.query import query_graph


def test_dot_export_writes_import_graph(tmp_path: Path):
    (tmp_path / "app.py").write_text("import os\n", encoding="utf-8")
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "imports.dot"
    export_dot(store, out)

    text = out.read_text(encoding="utf-8")
    assert "digraph contextopt_imports" in text
    assert '"file:app.py" -> "module:os"' in text


def test_query_ranks_exact_symbol_match_before_path_match(tmp_path: Path):
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    run_id = store.create_run(str(tmp_path), "now")
    store.add_node(run_id, kind="file", path="docs/authentication.md", name="authentication.md")
    store.add_node(run_id, kind="function", path="src/security.py", name="auth")
    store.commit()

    rows = query_graph(store, "auth")

    assert rows[0]["kind"] == "function"
    assert rows[0]["name"] == "auth"
    assert rows[0]["score"] > rows[1]["score"]


def test_query_matches_multi_term_tokens_and_simple_stems(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "ranking.py").write_text(
        "def build_savings_report():\n    return {}\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    rows = query_graph(store, "slice ranking changed files savings", limit=5)

    assert rows
    assert rows[0]["path"] == "src/ranking.py"
    assert any(row["name"] == "build_savings_report" for row in rows)


def test_markdown_export_respects_size_budgets(tmp_path: Path):
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    run_id = store.create_run(str(tmp_path), "now")
    for index in range(3):
        store.add_node(run_id, kind="file", path=f"file{index}.py", name=f"file{index}.py")
    store.add_edge(run_id, source="file:file0.py", target="module:os", kind="imports")
    store.commit()

    out = tmp_path / ".contextopt" / "context-pack.md"
    export_markdown(store, out, max_nodes=2, max_edges=0)

    text = out.read_text(encoding="utf-8")
    assert "- Nodes exported: 2 of 3" in text
    assert "- Edges exported: 0 of 1" in text
    assert "Budget note: output truncated by export limits." in text
    assert "file0.py" in text
    assert "file2.py" not in text
