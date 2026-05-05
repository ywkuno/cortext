from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Sequence

from .graph import GraphStore
from .ids import stable_node_id
from .artifacts import ARTIFACT_DIR
from .query import query_graph
from .token_estimator import estimate_tokens


FILE_KINDS = {"file", "doc"}
SYMBOL_KINDS = {"class", "function", "heading", "method", "route"}
DEFAULT_SLICE_MAX_TOKENS = 8_000
MAX_SAFE_SLICE_TOKENS = 16_000
SLICE_BRIEF_MAX_TOKENS = 1_200
SLICE_BRIEF_NODE_LIMIT = 12


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


def _safe_meta(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _legacy_tokens_for_node(node: dict[str, Any]) -> set[str]:
    tokens = {_node_row_id(node)}
    if node["kind"] in FILE_KINDS:
        tokens.add(f"file:{node['path']}")
    tokens.add(f"py:{node['path']}:{node['name']}")
    tokens.add(f"js:{node['path']}:{node['name']}")
    tokens.add(f"java:{node['path']}:{node['name']}")
    tokens.add(f"generic:{node['path']}:{node['name']}")
    if node["kind"] == "heading":
        tokens.add(f"heading:{node['path']}:{node['name']}")
    if node["kind"] == "route":
        tokens.add(f"route:{node['name']}")
    if node["kind"] in FILE_KINDS:
        meta = _safe_meta(node.get("meta_json"))
        module = meta.get("module")
        if isinstance(module, str) and module:
            tokens.add(f"module:{module}")
        normalized = _normalize_rel_path(str(node["path"]))
        without_suffix = normalized.rsplit(".", 1)[0]
        dotted = without_suffix.replace("/", ".")
        stem = without_suffix.rsplit("/", 1)[-1]
        package = meta.get("package")
        if isinstance(package, str) and package and stem:
            tokens.add(f"module:{package}.{stem}")
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
    return Path(ARTIFACT_DIR) / "slices" / f"{_sanitize_filename(query)}.md"


def _brief_path(out: Path) -> Path:
    return out.with_name(f"{out.stem}.brief.md")


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


def _ordered_nodes_for_slice(
    selected_nodes: list[dict[str, Any]],
    matched_ids: set[str],
) -> list[dict[str, Any]]:
    def key(node: dict[str, Any]) -> tuple[int, str, str, str]:
        node_id = _node_row_id(node)
        if node_id in matched_ids:
            priority = 0
        elif node["kind"] in FILE_KINDS:
            priority = 1
        elif node["kind"] in SYMBOL_KINDS:
            priority = 2
        else:
            priority = 3
        return (priority, str(node["path"]), str(node["kind"]), str(node["name"]))

    return sorted(selected_nodes, key=key)


def _slice_lines(
    *,
    query: str,
    matched_count: int,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    seeded_path_count: int,
    omitted_node_count: int = 0,
    omitted_edge_count: int = 0,
    max_tokens: int | None = None,
) -> list[str]:
    lines = [
        "# CodePrism Slice",
        "",
        f"- Query: `{query}`",
        f"- Matched nodes: {matched_count}",
        f"- Written nodes: {len(nodes)}",
        f"- Direct edges: {len(edges)}",
        f"- Seeded paths: {seeded_path_count}",
    ]
    if max_tokens and (omitted_node_count or omitted_edge_count):
        lines.extend(
            [
                f"- Token budget: {max_tokens}",
                f"- Omitted nodes: {omitted_node_count}",
                f"- Omitted edges: {omitted_edge_count}",
            ]
        )
    lines.extend(["", "## Nodes", ""])
    for node in nodes:
        node_id = _node_row_id(node)
        loc = f":L{node['start_line']}" if node["start_line"] else ""
        lines.append(f"- `{node_id}` — {node['kind']} `{node['path']}{loc}` **{node['name']}**")

    lines += ["", "## Direct Edges", ""]
    for edge in edges:
        lines.append(f"- `{edge['source']}` --{edge['kind']}--> `{edge['target']}`")

    if omitted_node_count or omitted_edge_count:
        lines.extend(
            [
                "",
                "## Omitted",
                "",
                (
                    f"This slice was capped to keep agent context small. "
                    f"Omitted {omitted_node_count} nodes and {omitted_edge_count} edges. "
                    "Use `codeprism query`, `codeprism get`, or `codeprism references` for more."
                ),
            ]
        )
    return lines


def _brief_node_line(node: dict[str, Any]) -> str:
    node_id = _node_row_id(node)
    loc = f":L{node['start_line']}" if node["start_line"] else ""
    return f"- `{node_id}` — {node['kind']} `{node['path']}{loc}` **{node['name']}**"


def _slice_brief_lines(
    *,
    query: str,
    out: Path,
    manifest_path: Path,
    matched_count: int,
    nodes: list[dict[str, Any]],
    matched_ids: set[str],
    seeded_paths: list[str],
    file_count: int,
    symbol_count: int,
    edge_count: int,
    estimated_tokens: int,
    full_context_tokens: int,
    max_tokens: int | None,
    truncated: bool,
    omitted_node_count: int,
    omitted_edge_count: int,
    node_limit: int,
) -> list[str]:
    status = (
        "capped; continue with targeted reads instead of raising the budget"
        if truncated
        else "within budget"
    )
    lines = [
        "# CodePrism Slice Brief",
        "",
        f"- Query: `{query}`",
        f"- Full slice: `{out}`",
        f"- Manifest: `{manifest_path}`",
        f"- Status: {status}",
        f"- Matched nodes: {matched_count}",
        f"- Included: {file_count} files, {symbol_count} symbols, {edge_count} edges",
        f"- Slice estimate: {estimated_tokens} tokens",
        f"- Full context estimate: {full_context_tokens} tokens",
    ]
    if max_tokens and max_tokens > 0:
        lines.append(f"- Slice budget: {max_tokens} tokens")
    if omitted_node_count or omitted_edge_count:
        lines.append(
            f"- Omitted from full slice budget: {omitted_node_count} nodes, "
            f"{omitted_edge_count} edges"
        )
    if seeded_paths:
        sample = ", ".join(f"`{path}`" for path in seeded_paths[:8])
        suffix = f", +{len(seeded_paths) - 8} more" if len(seeded_paths) > 8 else ""
        lines.append(f"- Seeded paths: {sample}{suffix}")

    lines.extend(["", "## Start Here", ""])
    ordered_nodes = _ordered_nodes_for_slice(nodes, matched_ids)
    for node in ordered_nodes[:node_limit]:
        lines.append(_brief_node_line(node))
    if len(ordered_nodes) > node_limit:
        lines.append(f"- ... {len(ordered_nodes) - node_limit} more nodes in the full slice.")
    if not ordered_nodes:
        lines.append("- No nodes were written. Narrow the query or refresh the map.")

    lines.extend(
        [
            "",
            "## Safe Next Reads",
            "",
            "- `codeprism get NODE_ID` for exact mapped source.",
            "- `codeprism references NODE_ID` for incoming and outgoing graph edges.",
            "- `codeprism read PATH --mode signatures` before opening a whole file.",
            "- `codeprism read PATH --mode diff` for one-file working-tree changes.",
            "",
            "## Compaction Safety",
            "",
            "Do not rerun a broad prime only because the conversation compacted.",
            "Open the full slice only when this brief is insufficient.",
        ]
    )
    return lines


def _slice_brief_text(
    *,
    query: str,
    out: Path,
    manifest_path: Path,
    matched_count: int,
    nodes: list[dict[str, Any]],
    matched_ids: set[str],
    seeded_paths: list[str],
    file_count: int,
    symbol_count: int,
    edge_count: int,
    estimated_tokens: int,
    full_context_tokens: int,
    max_tokens: int | None,
    truncated: bool,
    omitted_node_count: int,
    omitted_edge_count: int,
) -> tuple[str, int]:
    node_limit = min(SLICE_BRIEF_NODE_LIMIT, len(nodes))
    while node_limit >= 0:
        text = (
            "\n".join(
                _slice_brief_lines(
                    query=query,
                    out=out,
                    manifest_path=manifest_path,
                    matched_count=matched_count,
                    nodes=nodes,
                    matched_ids=matched_ids,
                    seeded_paths=seeded_paths,
                    file_count=file_count,
                    symbol_count=symbol_count,
                    edge_count=edge_count,
                    estimated_tokens=estimated_tokens,
                    full_context_tokens=full_context_tokens,
                    max_tokens=max_tokens,
                    truncated=truncated,
                    omitted_node_count=omitted_node_count,
                    omitted_edge_count=omitted_edge_count,
                    node_limit=node_limit,
                )
            )
            + "\n"
        )
        token_estimate = estimate_tokens(text)
        if token_estimate <= SLICE_BRIEF_MAX_TOKENS or node_limit == 0:
            return text, token_estimate
        node_limit -= 1
    raise AssertionError("unreachable")


def _fit_slice_budget(
    *,
    query: str,
    matched_count: int,
    selected_nodes: list[dict[str, Any]],
    selected_edges: list[dict[str, Any]],
    matched_ids: set[str],
    seeded_path_count: int,
    max_tokens: int | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], bool, int]:
    if not max_tokens or max_tokens <= 0:
        return selected_nodes, selected_edges, False, 0

    full_lines = _slice_lines(
        query=query,
        matched_count=matched_count,
        nodes=selected_nodes,
        edges=selected_edges,
        seeded_path_count=seeded_path_count,
        max_tokens=max_tokens,
    )
    full_estimate = estimate_tokens("\n".join(full_lines) + "\n")
    if full_estimate <= max_tokens:
        return selected_nodes, selected_edges, False, full_estimate

    kept_nodes: list[dict[str, Any]] = []
    for node in _ordered_nodes_for_slice(selected_nodes, matched_ids):
        candidate_nodes = [*kept_nodes, node]
        candidate_node_ids = {_node_row_id(candidate) for candidate in candidate_nodes}
        candidate_edges = [
            edge
            for edge in selected_edges
            if edge["source"] in candidate_node_ids and edge["target"] in candidate_node_ids
        ]
        candidate_lines = _slice_lines(
            query=query,
            matched_count=matched_count,
            nodes=candidate_nodes,
            edges=[],
            seeded_path_count=seeded_path_count,
            omitted_node_count=len(selected_nodes) - len(candidate_nodes),
            omitted_edge_count=len(selected_edges) - len(candidate_edges),
            max_tokens=max_tokens,
        )
        if estimate_tokens("\n".join(candidate_lines) + "\n") > max_tokens:
            if kept_nodes:
                continue
            kept_nodes.append(node)
            break
        kept_nodes = candidate_nodes

    kept_node_ids = {_node_row_id(node) for node in kept_nodes}
    kept_edges: list[dict[str, Any]] = []
    for edge in selected_edges:
        if edge["source"] not in kept_node_ids or edge["target"] not in kept_node_ids:
            continue
        candidate_edges = [*kept_edges, edge]
        candidate_lines = _slice_lines(
            query=query,
            matched_count=matched_count,
            nodes=kept_nodes,
            edges=candidate_edges,
            seeded_path_count=seeded_path_count,
            omitted_node_count=len(selected_nodes) - len(kept_nodes),
            omitted_edge_count=len(selected_edges) - len(candidate_edges),
            max_tokens=max_tokens,
        )
        if estimate_tokens("\n".join(candidate_lines) + "\n") > max_tokens:
            continue
        kept_edges = candidate_edges

    return kept_nodes, kept_edges, True, full_estimate


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
    max_tokens: int | None = DEFAULT_SLICE_MAX_TOKENS,
) -> dict[str, Any]:
    matches = query_graph(store, query, limit)
    nodes_by_id = _nodes_by_id(store)
    edges = _resolve_edges(_edge_rows(store), nodes_by_id)
    all_nodes = list(nodes_by_id.values())
    selected_ids = {_node_row_id(match) for match in matches}
    all_node_paths = {_normalize_rel_path(str(node["path"])) for node in nodes_by_id.values()}
    normalized_seed_paths = sorted(
        {
            normalized
            for path in seed_paths or []
            if (normalized := _normalize_rel_path(path)) in all_node_paths
        }
    )
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
        edge for edge in edges if edge["source"] in selected_ids and edge["target"] in selected_ids
    ]

    original_node_count = len(selected_nodes)
    original_edge_count = len(selected_edges)
    selected_nodes, selected_edges, truncated, untruncated_estimated_tokens = _fit_slice_budget(
        query=query,
        matched_count=len(matched_ids),
        selected_nodes=selected_nodes,
        selected_edges=selected_edges,
        matched_ids=matched_ids,
        seeded_path_count=len(normalized_seed_paths),
        max_tokens=max_tokens,
    )
    selected_ids = {_node_row_id(node) for node in selected_nodes}
    matched_ids = matched_ids & selected_ids
    omitted_node_count = original_node_count - len(selected_nodes)
    omitted_edge_count = original_edge_count - len(selected_edges)
    lines = _slice_lines(
        query=query,
        matched_count=len(matched_ids),
        nodes=selected_nodes,
        edges=selected_edges,
        seeded_path_count=len(normalized_seed_paths),
        omitted_node_count=omitted_node_count,
        omitted_edge_count=omitted_edge_count,
        max_tokens=max_tokens,
    )

    text = "\n".join(lines) + "\n"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    estimated_tokens = estimate_tokens(text)
    full_context_tokens = _full_context_token_count(all_nodes, edges)
    ratio = round(estimated_tokens / full_context_tokens, 4) if full_context_tokens else 0
    file_count = sum(1 for node in selected_nodes if node["kind"] in FILE_KINDS)
    symbol_count = sum(1 for node in selected_nodes if node["kind"] in SYMBOL_KINDS)
    manifest_path = out.with_suffix(".json")
    brief_path = _brief_path(out)
    brief_text, brief_estimated_tokens = _slice_brief_text(
        query=query,
        out=out,
        manifest_path=manifest_path,
        matched_count=len(matched_ids),
        nodes=selected_nodes,
        matched_ids=matched_ids,
        seeded_paths=normalized_seed_paths,
        file_count=file_count,
        symbol_count=symbol_count,
        edge_count=len(selected_edges),
        estimated_tokens=estimated_tokens,
        full_context_tokens=full_context_tokens,
        max_tokens=max_tokens,
        truncated=truncated,
        omitted_node_count=omitted_node_count,
        omitted_edge_count=omitted_edge_count,
    )
    brief_path.write_text(brief_text, encoding="utf-8")
    manifest = {
        "schema_version": 1,
        "query": query,
        "markdown": str(out),
        "brief": str(brief_path),
        "node_ids": sorted(selected_ids),
        "matched_node_ids": sorted(matched_ids),
        "seeded_paths": normalized_seed_paths,
        "file_count": file_count,
        "symbol_count": symbol_count,
        "edge_count": len(selected_edges),
        "estimated_tokens": estimated_tokens,
        "full_context_estimated_tokens": full_context_tokens,
        "estimated_token_ratio": ratio,
        "max_tokens": max_tokens,
        "brief_estimated_tokens": brief_estimated_tokens,
        "brief_max_tokens": SLICE_BRIEF_MAX_TOKENS,
        "truncated": truncated,
        "untruncated_estimated_tokens": untruncated_estimated_tokens,
        "omitted_node_count": omitted_node_count,
        "omitted_edge_count": omitted_edge_count,
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return {
        "query": query,
        "matched_nodes": len(matched_ids),
        "written_nodes": len(selected_nodes),
        "file_count": file_count,
        "symbol_count": symbol_count,
        "direct_edges": len(selected_edges),
        "seeded_paths": normalized_seed_paths,
        "node_ids": sorted(selected_ids),
        "matched_node_ids": sorted(matched_ids),
        "estimated_tokens": estimated_tokens,
        "full_context_estimated_tokens": full_context_tokens,
        "estimated_token_ratio": ratio,
        "max_tokens": max_tokens,
        "brief": str(brief_path),
        "brief_estimated_tokens": brief_estimated_tokens,
        "brief_max_tokens": SLICE_BRIEF_MAX_TOKENS,
        "truncated": truncated,
        "untruncated_estimated_tokens": untruncated_estimated_tokens,
        "omitted_node_count": omitted_node_count,
        "omitted_edge_count": omitted_edge_count,
        "out": str(out),
        "manifest": str(manifest_path),
    }
