from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .graph import GraphStore
from .scanner import scan_files
from .token_estimator import estimate_tokens


def _rows_count(store: GraphStore, table: str) -> int:
    return int(store.rows(f"SELECT count(*) AS count FROM {table}")[0]["count"])


def _source_text_token_count(root: Path) -> tuple[int, int, int]:
    files = scan_files(root)
    byte_count = 0
    token_count = 0
    for scanned in files:
        byte_count += scanned.size
        try:
            text = scanned.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        token_count += estimate_tokens(text)
    return len(files), byte_count, token_count


def _graph_token_count(store: GraphStore) -> int:
    rows = store.rows(
        """
        SELECT kind, path, name, meta_json FROM nodes
        UNION ALL
        SELECT kind, source AS path, target AS name, meta_json FROM edges
        """
    )
    text = "\n".join(
        f"{row['kind']} {row['path']} {row['name']} {row['meta_json']}" for row in rows
    )
    return estimate_tokens(text)


def _context_pack_token_count(store: GraphStore) -> int:
    nodes = store.rows("SELECT kind, path, name, start_line, end_line FROM nodes ORDER BY kind, path, name")
    edges = store.rows("SELECT source, target, kind FROM edges ORDER BY kind, source, target")
    payload = {
        "nodes": [dict(row) for row in nodes],
        "edges": [dict(row) for row in edges],
    }
    return estimate_tokens(json.dumps(payload, sort_keys=True))


def compute_stats(root: Path, store: GraphStore) -> dict[str, Any]:
    root = root.resolve()
    mapped_files, source_bytes, source_tokens = _source_text_token_count(root)
    graph_nodes = _rows_count(store, "nodes")
    graph_edges = _rows_count(store, "edges")
    graph_tokens = _graph_token_count(store)
    context_tokens = _context_pack_token_count(store)
    ratio = round(context_tokens / source_tokens, 4) if source_tokens else 0
    return {
        "root": str(root),
        "mapped_files": mapped_files,
        "source_bytes": source_bytes,
        "source_estimated_tokens": source_tokens,
        "graph_nodes": graph_nodes,
        "graph_edges": graph_edges,
        "graph_estimated_tokens": graph_tokens,
        "context_pack_estimated_tokens": context_tokens,
        "estimated_token_ratio": ratio,
    }


def format_stats(stats: dict[str, Any]) -> str:
    lines = [
        "# CodePrism Stats",
        "",
        f"- Root: `{stats['root']}`",
        f"- Mapped files: {stats['mapped_files']}",
        f"- Source bytes: {stats['source_bytes']}",
        f"- Source estimated tokens: {stats['source_estimated_tokens']}",
        f"- Graph nodes: {stats['graph_nodes']}",
        f"- Graph edges: {stats['graph_edges']}",
        f"- Graph estimated tokens: {stats['graph_estimated_tokens']}",
        f"- Context pack estimated tokens: {stats['context_pack_estimated_tokens']}",
        f"- Context/source token ratio: {stats['estimated_token_ratio']}",
    ]
    return "\n".join(lines)
