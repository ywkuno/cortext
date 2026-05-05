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
    memory_path = tmp_path / ".codeprism" / "memory" / "project.md"
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


def test_benchmark_suite_writes_json_and_markdown_summary(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    first = fixtures / "python"
    second = fixtures / "typescript"
    first.mkdir(parents=True)
    second.mkdir(parents=True)
    (first / "benchmark.config.json").write_text(
        json.dumps({"name": "Python Fixture", "query": "main"}),
        encoding="utf-8",
    )
    (first / "app.py").write_text(
        "def main():\n"
        f"    notes = {['python body'] * 120!r}\n"
        "    return len(notes)\n",
        encoding="utf-8",
    )
    (second / "benchmark.config.json").write_text(
        json.dumps({"name": "TypeScript Fixture", "query": "handler"}),
        encoding="utf-8",
    )
    (second / "handler.ts").write_text(
        "export function handler() {\n"
        f"  const notes = {['typescript body'] * 120!r};\n"
        "  return notes.length;\n"
        "}\n",
        encoding="utf-8",
    )
    out = tmp_path / "suite.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "benchmark-suite",
            str(fixtures),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    markdown = out.with_suffix(".md").read_text(encoding="utf-8")
    assert payload["fixture_count"] == 2
    assert payload["summary"]["average_source_to_slice_saved_percent"] > 0
    assert {fixture["name"] for fixture in payload["fixtures"]} == {
        "Python Fixture",
        "TypeScript Fixture",
    }
    assert "| Python Fixture |" in markdown
    assert "Markdown summary" in result.stdout


def test_benchmark_chart_renderer_writes_svg(tmp_path: Path) -> None:
    suite = tmp_path / "suite.json"
    out = tmp_path / "benchmark.svg"
    suite.write_text(
        json.dumps(
            {
                "fixtures": [
                    {
                        "name": "Python Fixture",
                        "files_seen": 5,
                        "source_estimated_tokens": 1200,
                        "slice_estimated_tokens": 300,
                        "source_to_slice_saved_percent": 75.0,
                        "source_to_context_saved_percent": 50.0,
                    },
                    {
                        "name": "TypeScript Fixture",
                        "files_seen": 4,
                        "source_estimated_tokens": 1000,
                        "slice_estimated_tokens": 400,
                        "source_to_slice_saved_percent": 60.0,
                        "source_to_context_saved_percent": 25.0,
                    },
                ],
                "summary": {"average_source_to_slice_saved_percent": 67.5},
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts" / "render_benchmark_chart.py"),
            str(suite),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    svg = out.read_text(encoding="utf-8")
    assert "CodePrism Benchmark Snapshot" in svg
    assert "Python Fixture" in svg
    assert "TypeScript Fixture" in svg
    assert "67.50%" in svg
    assert "Token counts are estimates" in svg
    check = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts" / "render_benchmark_chart.py"),
            str(suite),
            "--out",
            str(out),
            "--check",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    out.write_text(svg.replace("67.50%", "66.50%"), encoding="utf-8")
    stale = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts" / "render_benchmark_chart.py"),
            str(suite),
            "--out",
            str(out),
            "--check",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert check.returncode == 0, check.stderr
    assert "Benchmark chart is current" in check.stdout
    assert stale.returncode == 1
    assert "Benchmark chart is stale" in stale.stderr


def test_benchmark_compare_reports_regressions_and_can_fail(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline.json"
    current = tmp_path / "current.json"
    out = tmp_path / "comparison.md"
    baseline.write_text(
        json.dumps(
            {
                "summary": {"average_source_to_slice_saved_percent": 70.0},
                "fixtures": [
                    {
                        "name": "Python Fixture",
                        "source_estimated_tokens": 1000,
                        "slice_estimated_tokens": 300,
                        "source_to_slice_saved_percent": 70.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    current.write_text(
        json.dumps(
            {
                "summary": {"average_source_to_slice_saved_percent": 60.0},
                "fixtures": [
                    {
                        "name": "Python Fixture",
                        "source_estimated_tokens": 1000,
                        "slice_estimated_tokens": 400,
                        "source_to_slice_saved_percent": 60.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "benchmark-compare",
            str(baseline),
            str(current),
            "--out",
            str(out),
            "--regression-threshold",
            "5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    failed = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "benchmark-compare",
            str(baseline),
            str(current),
            "--fail-on-regression",
            "--regression-threshold",
            "5",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Wrote benchmark comparison" in result.stdout
    assert "Python Fixture" in out.read_text(encoding="utf-8")
    assert failed.returncode == 5
    assert "Benchmark regression detected" in failed.stderr


def test_benchmark_trend_script_uses_local_baseline_without_github(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixture = fixtures / "tiny"
    fixture.mkdir(parents=True)
    (fixture / "benchmark.config.json").write_text(
        json.dumps({"name": "Tiny Fixture", "query": "main"}),
        encoding="utf-8",
    )
    (fixture / "app.py").write_text(
        "def main():\n"
        f"    notes = {['trend fixture body'] * 120!r}\n"
        "    return len(notes)\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "summary": {"average_source_to_slice_saved_percent": 50.0},
                "fixtures": [
                    {
                        "name": "Tiny Fixture",
                        "source_estimated_tokens": 1000,
                        "slice_estimated_tokens": 500,
                        "source_to_slice_saved_percent": 50.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "trend"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_trend.py",
            "--baseline-suite",
            str(baseline),
            "--fixtures-root",
            str(fixtures),
            "--outdir",
            str(outdir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Benchmark trend ready." in result.stdout
    assert (outdir / "current-suite.json").exists()
    assert "Tiny Fixture" in (outdir / "comparison.md").read_text(encoding="utf-8")


def test_pre_release_proof_pack_uses_local_checks(tmp_path: Path) -> None:
    fixtures = tmp_path / "fixtures"
    fixture = fixtures / "tiny"
    fixture.mkdir(parents=True)
    (fixture / "benchmark.config.json").write_text(
        json.dumps({"name": "Tiny Fixture", "query": "main"}),
        encoding="utf-8",
    )
    (fixture / "app.py").write_text(
        "def main():\n"
        f"    notes = {['proof fixture body'] * 120!r}\n"
        "    return len(notes)\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "baseline.json"
    baseline.write_text(
        json.dumps(
            {
                "summary": {"average_source_to_slice_saved_percent": 50.0},
                "fixtures": [
                    {
                        "name": "Tiny Fixture",
                        "source_estimated_tokens": 1000,
                        "slice_estimated_tokens": 500,
                        "source_to_slice_saved_percent": 50.0,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    outdir = tmp_path / "proof"
    expected_suite = tmp_path / "expected-suite.json"
    expected_chart = tmp_path / "expected-chart.svg"
    suite_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "benchmark-suite",
            str(fixtures),
            "--out",
            str(expected_suite),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    chart_result = subprocess.run(
        [
            sys.executable,
            "scripts/render_benchmark_chart.py",
            str(expected_suite),
            "--out",
            str(expected_chart),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/pre_release_proof.py",
            "--baseline-suite",
            str(baseline),
            "--fixtures-root",
            str(fixtures),
            "--outdir",
            str(outdir),
            "--skip-tests",
            "--chart-out",
            str(expected_chart),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert suite_result.returncode == 0, suite_result.stderr
    assert chart_result.returncode == 0, chart_result.stderr
    assert result.returncode == 0, result.stderr
    summary = (outdir / "README.md").read_text(encoding="utf-8")
    assert "All pre-release proof checks passed." in result.stdout
    assert "benchmark-trend" in summary
    assert "benchmark-chart" in summary
    assert "benchmark-chart-check" in summary
    assert "Machine-readable manifest" in summary
    assert (outdir / "benchmark-chart.svg").exists()
    assert (outdir / "session-audit.md").exists()
    assert (outdir / "hygiene-scan.md").exists()
    manifest = json.loads((outdir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == 1
    assert manifest["artifacts"]["current_suite"].endswith("suite.json")
    assert {check["name"] for check in manifest["checks"]} >= {
        "benchmark-suite",
        "benchmark-trend",
        "public-hygiene",
    }


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
