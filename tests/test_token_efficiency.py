from __future__ import annotations

import json
from pathlib import Path

from contextopt.graph import GraphStore
from contextopt.gain import compute_gain, format_gain
from contextopt.mapper import map_project
from contextopt.slicer import DEFAULT_SLICE_MAX_TOKENS, SLICE_BRIEF_MAX_TOKENS, export_slice
from contextopt.stats import compute_stats
from contextopt.token_estimator import estimate_tokens


def test_estimate_tokens_is_deterministic_and_conservative() -> None:
    assert estimate_tokens("") == 0
    assert estimate_tokens("abcd") == 1
    assert estimate_tokens("abcde") == 2


def test_compute_stats_reports_repo_and_context_token_estimates(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Demo\n\nSmall project.\n", encoding="utf-8")
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    stats = compute_stats(tmp_path, store)

    assert stats["mapped_files"] == 2
    assert stats["graph_nodes"] >= 4
    assert stats["source_estimated_tokens"] > 0
    assert stats["graph_estimated_tokens"] > 0
    assert stats["context_pack_estimated_tokens"] > 0
    assert stats["estimated_token_ratio"] > 0
    assert stats["freshness"]["status"] == "current"
    assert stats["freshness"]["stale_count"] == 0


def test_compute_stats_reports_stale_map_after_file_change(tmp_path: Path) -> None:
    app = tmp_path / "app.py"
    app.write_text("def main():\n    return 1\n", encoding="utf-8")
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    app.write_text("def main():\n    return 1000\n", encoding="utf-8")

    stats = compute_stats(tmp_path, store)

    assert stats["freshness"]["status"] == "stale"
    assert stats["freshness"]["changed_files"] == ["app.py"]
    assert stats["freshness"]["stale_count"] == 1


def test_compute_gain_reports_source_context_and_slice_savings(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "import helpers\n\ndef main():\n    return helpers.greet()\n",
        encoding="utf-8",
    )
    (tmp_path / "helpers.py").write_text(
        f"def greet():\n    notes = {['verbose source body'] * 120!r}\n    return 'hi'\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)
    out = tmp_path / ".contextopt" / "slices" / "main.md"
    export_slice(store, "main", out)

    gain = compute_gain(tmp_path, store, slice_path=out.with_suffix(".json"))
    text = format_gain(gain)

    assert gain["source_estimated_tokens"] > gain["slice_estimated_tokens"] > 0
    assert gain["source_to_context_saved_tokens"] >= 0
    assert gain["source_to_slice_saved_tokens"] > 0
    assert gain["freshness"]["status"] == "current"
    assert "Source -> slice saving" in text
    assert "Map status: current" in text


def test_export_slice_writes_matching_nodes_and_neighbors(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "import helpers\n\ndef main():\n    return helpers.greet()\n",
        encoding="utf-8",
    )
    (tmp_path / "helpers.py").write_text(
        "def greet():\n    return 'hi'\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "slices" / "main.md"
    result = export_slice(store, "main", out)

    text = out.read_text(encoding="utf-8")
    assert result["matched_nodes"] >= 1
    assert result["written_nodes"] >= result["matched_nodes"]
    assert result["estimated_tokens"] > 0
    assert result["manifest"] == str(out.with_suffix(".json"))
    assert result["full_context_estimated_tokens"] >= result["estimated_tokens"]
    assert 0 < result["estimated_token_ratio"] <= 1
    assert "function::app.py::main" in text
    assert "Direct Edges" in text
    manifest = out.with_suffix(".json").read_text(encoding="utf-8")
    assert '"node_ids"' in manifest
    assert '"full_context_estimated_tokens"' in manifest


def test_export_slice_includes_local_imports_and_related_tests(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "src" / "app.py").write_text(
        "import src.helpers\n\ndef main():\n    return src.helpers.greet()\n",
        encoding="utf-8",
    )
    (tmp_path / "src" / "helpers.py").write_text(
        "def greet():\n    return 'hi'\n",
        encoding="utf-8",
    )
    (tmp_path / "tests" / "test_app.py").write_text(
        "def test_main():\n    assert True\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "slices" / "main.md"
    result = export_slice(store, "main", out)
    text = out.read_text(encoding="utf-8")

    assert "src/helpers.py" in text
    assert "tests/test_app.py" in text
    assert result["file_count"] >= 3
    assert result["symbol_count"] >= 2


def test_export_slice_accepts_seed_paths_for_changed_files(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "feature.py").write_text(
        "def changed_feature():\n    return 1\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "slices" / "changed.md"
    result = export_slice(store, "no textual match", out, seed_paths=["src/feature.py"])

    text = out.read_text(encoding="utf-8")
    assert "src/feature.py" in text
    assert "changed_feature" in text
    assert result["seeded_paths"] == ["src/feature.py"]


def test_export_slice_caps_large_changed_context_by_default(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    for index in range(60):
        (tmp_path / "src" / f"feature_{index}.py").write_text(
            f"def feature_{index}():\n    return {index}\n",
            encoding="utf-8",
        )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "slices" / "large.md"
    result = export_slice(
        store,
        "feature",
        out,
        limit=60,
        seed_paths=[f"src/feature_{index}.py" for index in range(60)],
        max_tokens=350,
    )

    text = out.read_text(encoding="utf-8")
    assert result["truncated"] is True
    assert result["estimated_tokens"] <= 350
    assert result["omitted_node_count"] > 0
    assert "This slice was capped" in text
    assert '"truncated": true' in out.with_suffix(".json").read_text(encoding="utf-8")


def test_default_slice_budget_stays_small_for_agent_context() -> None:
    assert DEFAULT_SLICE_MAX_TOKENS <= 8_000


def test_export_slice_ignores_unmapped_seed_paths(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "feature.py").write_text(
        "def changed_feature():\n    return 1\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "slices" / "changed.md"
    result = export_slice(
        store,
        "no textual match",
        out,
        seed_paths=["src/feature.py", ".contextopt/context.db", "assets/icon.png"],
    )

    assert result["seeded_paths"] == ["src/feature.py"]


def test_export_slice_writes_compaction_safe_brief(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    for index in range(80):
        (tmp_path / "src" / f"feature_{index}.py").write_text(
            f"def feature_{index}():\n    return {index}\n",
            encoding="utf-8",
        )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    out = tmp_path / ".contextopt" / "slices" / "large.md"
    result = export_slice(
        store,
        "feature",
        out,
        limit=80,
        seed_paths=[f"src/feature_{index}.py" for index in range(80)],
        max_tokens=500,
    )

    brief = out.with_name("large.brief.md")
    brief_text = brief.read_text(encoding="utf-8")
    manifest = json.loads(out.with_suffix(".json").read_text(encoding="utf-8"))

    assert brief.exists()
    assert result["brief"] == str(brief)
    assert result["brief_estimated_tokens"] <= SLICE_BRIEF_MAX_TOKENS
    assert manifest["brief"] == str(brief)
    assert manifest["brief_estimated_tokens"] == result["brief_estimated_tokens"]
    assert "# CodePrism Slice Brief" in brief_text
    assert "Do not rerun a broad prime only because the conversation compacted." in brief_text
    assert "Open the full slice only when this brief is insufficient." in brief_text
