from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from contextopt.graph import GraphStore
from contextopt.mapper import map_project
from contextopt.mcp_server import mcp_tool_specs
from contextopt.references import find_references, format_references


def test_references_resolve_local_imports_to_target_file(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "import helpers\n\n"
        "def main():\n"
        "    return helpers.greet()\n",
        encoding="utf-8",
    )
    (tmp_path / "helpers.py").write_text(
        "def greet():\n"
        "    return 'hello'\n",
        encoding="utf-8",
    )
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    map_project(tmp_path, store)

    result = find_references(store, "file::helpers.py")
    text = format_references(result)

    assert result["target_id"] == "file::helpers.py"
    assert result["incoming"][0]["source"] == "file::app.py"
    assert result["incoming"][0]["kind"] == "imports"
    assert "Incoming" in text
    assert "file::app.py --imports--> file::helpers.py" in text


def test_references_deduplicate_identical_edges(tmp_path: Path) -> None:
    store = GraphStore(tmp_path / ".contextopt" / "context.db")
    run_id = store.create_run(str(tmp_path), "now")
    store.add_node(run_id, kind="doc", path="README.md", name="README.md")
    store.add_node(run_id, kind="heading", path="README.md", name="Quick Start")
    store.add_edge(
        run_id,
        source="doc::README.md",
        target="heading::README.md::Quick Start",
        kind="contains",
    )
    store.add_edge(
        run_id,
        source="doc::README.md",
        target="heading::README.md::Quick Start",
        kind="contains",
    )
    store.commit()

    result = find_references(store, "heading::README.md::Quick Start")

    assert len(result["incoming"]) == 1


def test_onboard_writes_local_project_memory_and_memory_read_lists_it(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "onboard",
            str(tmp_path),
            "--db",
            str(db),
            "--notes",
            "Tiny fixture for onboarding.",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    memory_path = tmp_path / ".contextopt" / "memory" / "project.md"
    assert memory_path.exists()
    memory_text = memory_path.read_text(encoding="utf-8")
    assert "# CodePrism Project Memory" in memory_text
    assert "Tiny fixture for onboarding." in memory_text

    list_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "memory",
            "list",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    read_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "memory",
            "read",
            "project",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert list_result.returncode == 0, list_result.stderr
    assert "project.md" in list_result.stdout
    assert read_result.returncode == 0, read_result.stderr
    assert "Tiny fixture for onboarding." in read_result.stdout


def test_benchmark_command_writes_reproducible_savings_report(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "def main():\n"
        f"    notes = {['benchmark body'] * 150!r}\n"
        "    return len(notes)\n",
        encoding="utf-8",
    )
    out = tmp_path / "benchmark.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "benchmark",
            str(tmp_path),
            "--query",
            "main",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["query"] == "main"
    assert payload["files_seen"] == 1
    assert payload["source_estimated_tokens"] > payload["slice_estimated_tokens"] > 0
    assert payload["source_to_slice_saved_percent"] > 0
    assert "Wrote benchmark" in result.stdout


def test_mcp_tool_specs_expose_core_context_tools() -> None:
    tool_names = {tool["name"] for tool in mcp_tool_specs()}

    assert {
        "codeprism_prime",
        "codeprism_gain",
        "codeprism_query",
        "codeprism_read",
        "codeprism_get",
        "codeprism_references",
    } <= tool_names


def test_mcp_list_tools_cli_is_available_without_optional_sdk() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "mcp", "--list-tools"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert any(tool["name"] == "codeprism_prime" for tool in payload["tools"])
