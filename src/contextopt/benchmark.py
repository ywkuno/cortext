from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .artifacts import artifact_path
from .gain import compute_gain
from .graph import GraphStore
from .mapper import map_project
from .slicer import export_slice


class BenchmarkError(Exception):
    """Raised when benchmark fixtures cannot be discovered or executed."""


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-").lower()
    return slug or "benchmark"


def default_benchmark_path(root: Path, query: str) -> Path:
    return artifact_path(root, "benchmarks", f"{_slug(query)}.json")


def default_benchmark_suite_path(root: Path) -> Path:
    return artifact_path(root, "benchmarks", "suite.json")


def run_benchmark(
    root: Path,
    store: GraphStore,
    *,
    query: str,
    out: Path,
    max_file_bytes: int = 500_000,
    ignore_patterns: list[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    map_result = map_project(
        root,
        store,
        max_file_bytes=max_file_bytes,
        ignore_patterns=ignore_patterns,
    )
    slice_path = out.with_suffix(".slice.md")
    slice_result = export_slice(store, query, slice_path)
    gain = compute_gain(
        root,
        store,
        slice_path=Path(slice_result["manifest"]),
        max_file_bytes=max_file_bytes,
        ignore_patterns=ignore_patterns,
    )
    payload = {
        "schema_version": 1,
        "root": str(root),
        "query": query,
        "files_seen": map_result.files_seen,
        "files_reused": map_result.files_reused,
        "files_extracted": map_result.files_extracted,
        "nodes_written": map_result.nodes_written,
        "edges_written": map_result.edges_written,
        "source_estimated_tokens": gain["source_estimated_tokens"],
        "context_pack_estimated_tokens": gain["context_pack_estimated_tokens"],
        "slice_estimated_tokens": gain.get("slice_estimated_tokens", 0),
        "source_to_context_saved_percent": gain["source_to_context_saved_percent"],
        "source_to_slice_saved_percent": gain.get("source_to_slice_saved_percent", 0.0),
        "source_to_slice_saved_tokens": gain.get("source_to_slice_saved_tokens", 0),
        "slice_manifest": slice_result["manifest"],
        "slice_markdown": slice_result["out"],
        "note": "Token counts are local estimates for comparison, not billing-grade metrics.",
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def run_benchmark_suite(
    fixtures_root: Path,
    *,
    out: Path,
    max_file_bytes: int = 500_000,
    ignore_patterns: list[str] | None = None,
) -> dict[str, Any]:
    fixtures_root = fixtures_root.resolve()
    fixtures = discover_benchmark_fixtures(fixtures_root)
    if not fixtures:
        raise BenchmarkError(f"No benchmark fixtures found under {fixtures_root}")

    out.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for fixture in fixtures:
        slug = _slug(fixture["name"])
        fixture_out = out.parent / f"{slug}.json"
        fixture_db = out.parent / f"{slug}.db"
        _reset_benchmark_db(fixture_db)
        result = run_benchmark(
            fixture["root"],
            GraphStore(fixture_db),
            query=fixture["query"],
            out=fixture_out,
            max_file_bytes=max_file_bytes,
            ignore_patterns=ignore_patterns,
        )
        results.append(
            {
                "name": fixture["name"],
                "description": fixture["description"],
                "root": str(fixture["root"]),
                "query": fixture["query"],
                "report": str(fixture_out),
                "files_seen": result["files_seen"],
                "source_estimated_tokens": result["source_estimated_tokens"],
                "context_pack_estimated_tokens": result["context_pack_estimated_tokens"],
                "slice_estimated_tokens": result["slice_estimated_tokens"],
                "source_to_context_saved_percent": result["source_to_context_saved_percent"],
                "source_to_slice_saved_percent": result["source_to_slice_saved_percent"],
            }
        )

    suite = {
        "schema_version": 1,
        "fixtures_root": str(fixtures_root),
        "fixture_count": len(results),
        "fixtures": results,
        "summary": _suite_summary(results),
        "note": "Token counts are local estimates for comparison, not billing-grade metrics.",
    }
    out.write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path = out.with_suffix(".md")
    md_path.write_text(format_benchmark_suite_markdown(suite), encoding="utf-8")
    suite["markdown"] = str(md_path)
    out.write_text(json.dumps(suite, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return suite


def discover_benchmark_fixtures(fixtures_root: Path) -> list[dict[str, Any]]:
    if not fixtures_root.exists():
        raise BenchmarkError(f"Benchmark fixtures root not found: {fixtures_root}")
    fixtures: list[dict[str, Any]] = []
    for child in sorted(path for path in fixtures_root.iterdir() if path.is_dir()):
        files = [path for path in child.rglob("*") if path.is_file()]
        files = [path for path in files if ".codeprism" not in path.parts]
        if not files:
            continue
        config = _read_fixture_config(child)
        fixtures.append(
            {
                "name": str(config.get("name") or child.name),
                "description": str(config.get("description") or ""),
                "query": str(config.get("query") or child.name),
                "root": child.resolve(),
            }
        )
    return fixtures


def format_benchmark(result: dict[str, Any], out: Path) -> str:
    return (
        f"Wrote benchmark {out} "
        f"({result['files_seen']} files, "
        f"{result['source_to_slice_saved_percent']:.2f}% estimated source-to-slice saving).\n"
    )


def format_benchmark_suite(result: dict[str, Any], out: Path) -> str:
    summary = result["summary"]
    markdown = result.get("markdown") or out.with_suffix(".md")
    return (
        f"Wrote benchmark suite {out} "
        f"({result['fixture_count']} fixtures, "
        f"average {summary['average_source_to_slice_saved_percent']:.2f}% "
        f"estimated source-to-slice saving).\n"
        f"Markdown summary: {markdown}\n"
    )


def format_benchmark_suite_markdown(result: dict[str, Any]) -> str:
    lines = [
        "# CodePrism Benchmark Suite",
        "",
        "Token counts are local estimates for comparison, not billing-grade metrics.",
        "",
        "| Fixture | Files | Source tokens | Slice tokens | Source -> slice | Source -> context pack |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for fixture in result["fixtures"]:
        lines.append(
            "| "
            f"{fixture['name']} | "
            f"{fixture['files_seen']} | "
            f"{fixture['source_estimated_tokens']:,} | "
            f"{fixture['slice_estimated_tokens']:,} | "
            f"{fixture['source_to_slice_saved_percent']:.2f}% | "
            f"{fixture['source_to_context_saved_percent']:.2f}% |"
        )
    summary = result["summary"]
    lines.extend(
        [
            "",
            "## Summary",
            "",
            f"- Fixtures: {result['fixture_count']}",
            f"- Average source-to-slice saving: {summary['average_source_to_slice_saved_percent']:.2f}%",
            f"- Minimum source-to-slice saving: {summary['min_source_to_slice_saved_percent']:.2f}%",
            f"- Maximum source-to-slice saving: {summary['max_source_to_slice_saved_percent']:.2f}%",
            "",
        ]
    )
    return "\n".join(lines)


def _read_fixture_config(root: Path) -> dict[str, Any]:
    config_path = root / "benchmark.config.json"
    if not config_path.exists():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkError(f"Invalid benchmark config {config_path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise BenchmarkError(f"Benchmark config must be a JSON object: {config_path}")
    return payload


def _suite_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    savings = [float(result["source_to_slice_saved_percent"]) for result in results]
    return {
        "average_source_to_slice_saved_percent": sum(savings) / len(savings),
        "min_source_to_slice_saved_percent": min(savings),
        "max_source_to_slice_saved_percent": max(savings),
    }


def _reset_benchmark_db(db: Path) -> None:
    for path in [db, db.with_name(f"{db.name}-wal"), db.with_name(f"{db.name}-shm")]:
        if path.exists():
            path.unlink()
