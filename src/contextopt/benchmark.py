from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .gain import compute_gain
from .graph import GraphStore
from .mapper import map_project
from .slicer import export_slice


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-").lower()
    return slug or "benchmark"


def default_benchmark_path(root: Path, query: str) -> Path:
    return root.resolve() / ".contextopt" / "benchmarks" / f"{_slug(query)}.json"


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


def format_benchmark(result: dict[str, Any], out: Path) -> str:
    return (
        f"Wrote benchmark {out} "
        f"({result['files_seen']} files, "
        f"{result['source_to_slice_saved_percent']:.2f}% estimated source-to-slice saving).\n"
    )
