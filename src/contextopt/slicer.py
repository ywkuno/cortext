from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .graph import GraphStore
from .ids import stable_node_id
from .query import query_graph
from .token_estimator import estimate_tokens


FILE_KINDS = {"file", "doc"}
SYMBOL_KINDS = {"class", "function", "heading", "method", "route"}


def _node_row_id(row: dict[str, Any]) -> str:
    return stable_node_id(row["kind"], row["path"], row["name"])


def _latest_run_filter(store: GraphStore) -> tuple[str, tuple[object, ...]]:
    run = store.rows("SELECT id FROM runs ORDER BY id DESC LIMIT 1")
    if not run:
        return "", ()
    return "WHERE run_id = ?", (run[0]["id"],)


def _nodes_by_id(store: GraphStore) -> dict[str, dict[str, Any]]:
    where, params = _latest_run_filter(store)
    rows = store.rows(f"SELECT * FROM nodes {where}", params)
    return {_node_row_id(dict(row)): dict(row) for row in rows}


def _edge_rows(store: GraphStore) -> list[dict[str, Any]]:
    where, params = _latest_run_filter(store)
    return [dict(row) for row in store.rows(f"SELECT * FROM edges {where}", params)]


def _full_context_token_count(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> int:
    payload = {
        "nodes": [
            {
                "kind": node["kind"],
                "path": node["path"],
                "name": node["name"],
                "start_line": node["start_line"],
                "end_line": node["end_line"],
            }
            for node in nodes
        ],
        "edges": [
            {"source": edge["source"], "target": edge["target"], "kind": edge["kind"]}
            for edge in edges
        ],
    }
    return estimate_tokens(json.dumps(payload, sort_keys=True))


def _normalize_rel_path(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized.strip("/")


def _legacy_tokens_for_node(node: dict[str, Any]) -> set[str]:
    tokens = {_node_row_id(node)}
    if node["kind"] in FILE_KINDS:
        tokens.add(f"file:{node['path']}")
    tokens.add(f"py:{node['path']}:{node['name']}")
    tokens.add(f"js:{node['path']}:{node['name']}")
    if node["kind"] == "heading":
        tokens.add(f"heading:{node['path']}:{node['name']}")
    if node["kind"] == "route":
        tokens.add(f"route:{node['name']}")
    if node["kind"] in FILE_KINDS:
        normalized = _normalize_rel_path(str(node["path"]))
        without_suffix = normalized.rsplit(".", 1)[0]
        dotted = without_suffix.replace("/", ".")
        stem = without_suffix.rsplit("/", 1)[-1]
        if dotted:
            tokens.add(f"module:{dotted}")
        if stem:
            tokens.add(f"module:{stem}")
        if normalized.endswith("/__init__.py"):
            package = normalized.removesuffix("/__init__.py").replace("/", ".")
            if package:
                tokens.add(f"module:{package}")
    return tokens


def _resolve_edges(
    edges: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    lookup: dict[str, str] = {}
    for node_id, node in nodes_by_id.items():
        for token in _legacy_tokens_for_node(node):
            lookup[token] = node_id
    resolved: list[dict[str, Any]] = []
    for edge in edges:
        source = lookup.get(edge["source"], edge["source"])
        target = lookup.get(edge["target"], edge["target"])
        resolved.append({**edge, "source": source, "target": target})
    return resolved


def _sanitize_filename(text: str) -> str:
    chars = [char.lower() if char.isalnum() else "-" for char in text.strip()]
    slug = "-".join(part for part in "".join(chars).split("-") if part)
    return slug or "slice"


def default_slice_path(query: str) -> Path:
    return Path(".contextopt") / "slices" / f"{_sanitize_filename(query)}.md"


def _node_ids_for_paths(
    nodes_by_id: dict[str, dict[str, Any]],
    seed_paths: Sequence[str] | None,
) -> set[str]:
    wanted = {_normalize_rel_path(path) for path in seed_paths or [] if path}
    if not wanted:
        return set()
    return {
        node_id
        for node_id, node in nodes_by_id.items()
        if _normalize_rel_path(str(node["path"])) in wanted
    }


def _neighbor_ids(seed_ids: set[str], edges: list[dict[str, Any]]) -> set[str]:
    neighbors: set[str] = set()
    for edge in edges:
        if edge["source"] in seed_ids:
            neighbors.add(edge["target"])
        if edge["target"] in seed_ids:
            neighbors.add(edge["source"])
    return neighbors


def _import_neighbor_ids(seed_ids: set[str], edges: list[dict[str, Any]]) -> set[str]:
    neighbors: set[str] = set()
    for edge in edges:
        if edge["kind"] != "imports":
            continue
        if edge["source"] in seed_ids:
            neighbors.add(edge["target"])
        if edge["target"] in seed_ids:
            neighbors.add(edge["source"])
    return neighbors


def _is_test_path(path: str) -> bool:
    lower = _normalize_rel_path(path).lower()
    basename = lower.rsplit("/", 1)[-1]
    return (
        lower.startswith("tests/")
        or "/tests/" in lower
        or basename.startswith("test_")
        or basename.endswith("_test.py")
        or ".test." in basename
        or ".spec." in basename
    )


def _stem_tokens(path: str) -> set[str]:
    basename = _normalize_rel_path(path).lower().rsplit("/", 1)[-1]
    stem = basename.rsplit(".", 1)[0]
    cleaned = stem.removeprefix("test_").removesuffix("_test")
    parts = [part for part in cleaned.replace("-", "_").split("_") if len(part) >= 2]
    return {*parts, cleaned} if cleaned else set(parts)


def _related_test_ids(
    selected_ids: set[str],
    nodes_by_id: dict[str, dict[str, Any]],
) -> set[str]:
    selected_file_paths = [
        str(nodes_by_id[node_id]["path"])
        for node_id in selected_ids
        if node_id in nodes_by_id and nodes_by_id[node_id]["kind"] in FILE_KINDS
    ]
    source_tokens: set[str] = set()
    for path in selected_file_paths:
        if not _is_test_path(path):
            source_tokens.update(_stem_tokens(path))
    if not source_tokens:
        return set()
    related: set[str] = set()
    for node_id, node in nodes_by_id.items():
        if node["kind"] in FILE_KINDS and _is_test_path(str(node["path"])):
            if source_tokens & _stem_tokens(str(node["path"])):
                related.add(node_id)
    return related


def _contained_symbol_ids(
    selected_ids: set[str],
    edges: list[dict[str, Any]],
    nodes_by_id: dict[str, dict[str, Any]],
) -> set[str]:
    symbols: set[str] = set()
    for edge in edges:
        if edge["kind"] != "contains" or edge["source"] not in selected_ids:
            continue
        target = nodes_by_id.get(edge["target"])
        if target and target["kind"] in SYMBOL_KINDS:
            symbols.add(edge["target"])
    return symbols


def export_slice(
    store: GraphStore,
    query: str,
    out: Path,
    *,
    limit: int = 12,
    seed_paths: Sequence[str] | None = None,
) -> dict[str, Any]:
    matches = query_graph(store, query, limit)
    nodes_by_id = _nodes_by_id(store)
    edges = _resolve_edges(_edge_rows(store), nodes_by_id)
    all_nodes = list(nodes_by_id.values())
    selected_ids = {_node_row_id(match) for match in matches}
    normalized_seed_paths = sorted({_normalize_rel_path(path) for path in seed_paths or [] if path})
    selected_ids.update(_node_ids_for_paths(nodes_by_id, normalized_seed_paths))
    matched_ids = set(selected_ids)

    selected_ids.update(_neighbor_ids(matched_ids, edges))
    selected_ids.update(_import_neighbor_ids(selected_ids, edges))
    selected_ids.update(_related_test_ids(selected_ids, nodes_by_id))
    selected_ids.update(_contained_symbol_ids(selected_ids, edges, nodes_by_id))

    selected_nodes = [
        nodes_by_id[node_id] for node_id in sorted(selected_ids) if node_id in nodes_by_id
    ]
    selected_edges = [
        edge
        for edge in edges
        if edge["source"] in selected_ids or edge["target"] in selected_ids
    ]

    lines = [
        "# Cortext Slice",
        "",
        f"- Query: `{query}`",
        f"- Matched nodes: {len(matched_ids)}",
        f"- Written nodes: {len(selected_nodes)}",
        f"- Direct edges: {len(selected_edges)}",
        f"- Seeded paths: {len(normalized_seed_paths)}",
        "",
        "## Nodes",
        "",
    ]
    for node in selected_nodes:
        node_id = _node_row_id(node)
        loc = f":L{node['start_line']}" if node["start_line"] else ""
        lines.append(f"- `{node_id}` — {node['kind']} `{node['path']}{loc}` **{node['name']}**")

    lines += ["", "## Direct Edges", ""]
    for edge in selected_edges:
        lines.append(f"- `{edge['source']}` --{edge['kind']}--> `{edge['target']}`")

    text = "\n".join(lines) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    estimated_tokens = estimate_tokens(text)
    full_context_tokens = _full_context_token_count(all_nodes, edges)
    ratio = round(estimated_tokens / full_context_tokens, 4) if full_context_tokens else 0
    file_count = sum(1 for node in selected_nodes if node["kind"] in FILE_KINDS)
    symbol_count = sum(1 for node in selected_nodes if node["kind"] in SYMBOL_KINDS)
    manifest_path = out.with_suffix(".json")
    manifest = {
        "schema_version": 1,
        "query": query,
        "markdown": str(out),
        "node_ids": sorted(selected_ids),
        "matched_node_ids": sorted(matched_ids),
        "seeded_paths": normalized_seed_paths,
        "file_count": file_count,
        "symbol_count": symbol_count,
        "edge_count": len(selected_edges),
        "estimated_tokens": estimated_tokens,
        "full_context_estimated_tokens": full_context_tokens,
        "estimated_token_ratio": ratio,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {
        "query": query,
        "matched_nodes": len(matched_ids),
        "written_nodes": len(selected_nodes),
        "file_count": file_count,
        "symbol_count": symbol_count,
        "direct_edges": len(selected_edges),
        "seeded_paths": normalized_seed_paths,
        "estimated_tokens": estimated_tokens,
        "full_context_estimated_tokens": full_context_tokens,
        "estimated_token_ratio": ratio,
        "out": str(out),
        "manifest": str(manifest_path),
    }
