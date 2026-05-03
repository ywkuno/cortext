from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .extractors.base import Extraction, Node
from .extractors.generic import extract_generic, language_for_suffix
from .extractors.java import extract_java
from .extractors.js_ts import extract_js_ts
from .extractors.markdown import extract_markdown
from .extractors.python import extract_python
from .graph import GraphStore
from .ids import stable_node_id
from .scanner import ScannedFile, scan_files

EXTRACTION_CACHE_VERSION = "mvp4-v2"


@dataclass
class MapResult:
    files_seen: int
    nodes_written: int
    edges_written: int
    files_hashed: int = 0
    files_reused: int = 0
    files_extracted: int = 0


def extract_file(path: Path, rel_path: str) -> Extraction:
    suffix = path.suffix.lower()
    if suffix == ".py":
        return extract_python(path, rel_path)
    if suffix in {".md", ".mdx"}:
        return extract_markdown(path, rel_path)
    if suffix == ".java":
        return extract_java(path, rel_path)
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return extract_js_ts(path, rel_path)
    language = language_for_suffix(suffix)
    if language:
        return extract_generic(path, rel_path, language)
    return Extraction(
        nodes=[Node(kind="file", path=rel_path, name=rel_path, meta={"language": "unknown"})]
    )


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_hash(scanned: ScannedFile, store: GraphStore) -> tuple[str, bool]:
    state = store.file_state(scanned.rel_path)
    if (
        state
        and state["size"] == scanned.size
        and state["mtime_ns"] == scanned.mtime_ns
        and state["sha256"]
    ):
        return str(state["sha256"]), False
    return hash_file(scanned.path), True


def _node_rows(extraction: Extraction) -> list[dict[str, object]]:
    return [
        {
            "kind": node.kind,
            "path": node.path,
            "name": node.name,
            "start_line": node.start_line,
            "end_line": node.end_line,
            "meta_json": json.dumps(node.meta, sort_keys=True),
        }
        for node in extraction.nodes
    ]


def _edge_rows(extraction: Extraction) -> list[dict[str, object]]:
    return [
        {
            "source": edge.source,
            "target": edge.target,
            "kind": edge.kind,
            "meta_json": json.dumps(edge.meta, sort_keys=True),
        }
        for edge in extraction.edges
    ]


def _write_rows(
    store: GraphStore,
    run_id: int,
    nodes: list[dict[str, object]],
    edges: list[dict[str, object]],
) -> tuple[int, int]:
    for node in nodes:
        store.add_node(
            run_id,
            kind=str(node["kind"]),
            path=str(node["path"]),
            name=str(node["name"]),
            start_line=node["start_line"] if isinstance(node["start_line"], int) else None,
            end_line=node["end_line"] if isinstance(node["end_line"], int) else None,
            meta_json=str(node["meta_json"]),
        )
    for edge in edges:
        store.add_edge(
            run_id,
            source=str(edge["source"]),
            target=str(edge["target"]),
            kind=str(edge["kind"]),
            meta_json=str(edge["meta_json"]),
        )
    return len(nodes), len(edges)


def _file_like_node(nodes: list[dict[str, object]], rel_path: str) -> dict[str, object] | None:
    for node in nodes:
        if node["path"] == rel_path and node["kind"] in {"file", "doc"}:
            return node
    return None


def _hierarchy_for_file(
    rel_path: str,
    nodes: list[dict[str, object]],
    seen_folders: set[str],
    seen_edges: set[tuple[str, str, str]],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    extra_nodes: list[dict[str, object]] = []
    extra_edges: list[dict[str, object]] = []
    parts = rel_path.split("/")
    folder_paths = ["/".join(parts[:index]) for index in range(1, len(parts))]

    for folder_path in folder_paths:
        if folder_path not in seen_folders:
            seen_folders.add(folder_path)
            extra_nodes.append(
                {
                    "kind": "folder",
                    "path": folder_path,
                    "name": folder_path.split("/")[-1],
                    "start_line": None,
                    "end_line": None,
                    "meta_json": "{}",
                }
            )

    for parent, child in zip(folder_paths, folder_paths[1:]):
        edge = (
            stable_node_id("folder", parent, parent.split("/")[-1]),
            stable_node_id("folder", child, child.split("/")[-1]),
            "contains",
        )
        if edge not in seen_edges:
            seen_edges.add(edge)
            extra_edges.append(
                {"source": edge[0], "target": edge[1], "kind": edge[2], "meta_json": "{}"}
            )

    file_node = _file_like_node(nodes, rel_path)
    if file_node and folder_paths:
        parent_folder = folder_paths[-1]
        edge = (
            stable_node_id("folder", parent_folder, parent_folder.split("/")[-1]),
            stable_node_id(str(file_node["kind"]), str(file_node["path"]), str(file_node["name"])),
            "contains",
        )
        if edge not in seen_edges:
            seen_edges.add(edge)
            extra_edges.append(
                {"source": edge[0], "target": edge[1], "kind": edge[2], "meta_json": "{}"}
            )

    if file_node:
        file_id = stable_node_id(str(file_node["kind"]), str(file_node["path"]), str(file_node["name"]))
        class_ids = {
            str(node["name"]): stable_node_id(str(node["kind"]), str(node["path"]), str(node["name"]))
            for node in nodes
            if node["kind"] == "class"
        }
        for node in nodes:
            if node is file_node or node["kind"] in {"file", "doc", "parse_error"}:
                continue
            node_id = stable_node_id(str(node["kind"]), str(node["path"]), str(node["name"]))
            edge = (file_id, node_id, "contains")
            if edge not in seen_edges:
                seen_edges.add(edge)
                extra_edges.append(
                    {"source": edge[0], "target": edge[1], "kind": edge[2], "meta_json": "{}"}
                )
            if node["kind"] == "method":
                try:
                    meta = json.loads(str(node["meta_json"] or "{}"))
                except json.JSONDecodeError:
                    meta = {}
                parent_class = meta.get("parent_class")
                if isinstance(parent_class, str) and parent_class in class_ids:
                    edge = (class_ids[parent_class], node_id, "contains")
                    if edge not in seen_edges:
                        seen_edges.add(edge)
                        extra_edges.append(
                            {
                                "source": edge[0],
                                "target": edge[1],
                                "kind": edge[2],
                                "meta_json": "{}",
                            }
                        )

    return extra_nodes, extra_edges


def map_project(
    root: Path,
    store: GraphStore,
    *,
    max_file_bytes: int = 500_000,
    ignore_patterns: list[str] | None = None,
) -> MapResult:
    root = root.resolve()
    created_at = datetime.now(timezone.utc).isoformat()
    files = scan_files(root, max_file_bytes=max_file_bytes, ignore_patterns=ignore_patterns)
    store.clear_graph()
    store.delete_files_not_in({file.rel_path for file in files})
    run_id = store.create_run(str(root), created_at)
    node_count = edge_count = files_hashed = files_reused = files_extracted = 0
    seen_folders: set[str] = set()
    seen_hierarchy_edges: set[tuple[str, str, str]] = set()

    for scanned in files:
        sha256, hashed = _file_hash(scanned, store)
        if hashed:
            files_hashed += 1
        cache_key = f"{sha256}:{EXTRACTION_CACHE_VERSION}"
        cached_nodes = store.cached_nodes(scanned.rel_path, cache_key)
        cached_edges = store.cached_edges(scanned.rel_path, cache_key)
        if cached_nodes:
            nodes = [dict(row) for row in cached_nodes]
            edges = [dict(row) for row in cached_edges]
            files_reused += 1
        else:
            extraction = extract_file(scanned.path, scanned.rel_path)
            nodes = _node_rows(extraction)
            edges = _edge_rows(extraction)
            store.replace_cached_extraction(
                rel_path=scanned.rel_path,
                sha256=cache_key,
                nodes=nodes,
                edges=edges,
            )
            files_extracted += 1

        hierarchy_nodes, hierarchy_edges = _hierarchy_for_file(
            scanned.rel_path,
            nodes,
            seen_folders,
            seen_hierarchy_edges,
        )
        written_nodes, written_edges = _write_rows(
            store,
            run_id,
            [*hierarchy_nodes, *nodes],
            [*edges, *hierarchy_edges],
        )
        node_count += written_nodes
        edge_count += written_edges
        store.upsert_file_state(
            rel_path=scanned.rel_path,
            size=scanned.size,
            mtime_ns=scanned.mtime_ns,
            sha256=sha256,
            updated_at=created_at,
        )

    store.commit()
    return MapResult(
        files_seen=len(files),
        nodes_written=node_count,
        edges_written=edge_count,
        files_hashed=files_hashed,
        files_reused=files_reused,
        files_extracted=files_extracted,
    )
