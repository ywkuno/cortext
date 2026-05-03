from __future__ import annotations

import json
from typing import Any

from .graph import GraphStore
from .ids import stable_node_id


class ReferencesError(ValueError):
    pass


def _latest_run_id(store: GraphStore) -> int | None:
    rows = store.rows("SELECT id FROM runs ORDER BY id DESC LIMIT 1")
    return int(rows[0]["id"]) if rows else None


def _safe_meta(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _node_id(node: dict[str, Any]) -> str:
    return stable_node_id(str(node["kind"]), str(node["path"]), str(node["name"]))


def _legacy_tokens(node: dict[str, Any]) -> set[str]:
    node_id = _node_id(node)
    tokens = {node_id}
    kind = str(node["kind"])
    path = str(node["path"]).replace("\\", "/").strip("/")
    name = str(node["name"])
    if kind in {"file", "doc"}:
        tokens.add(f"file:{path}")
        without_suffix = path.rsplit(".", 1)[0]
        dotted = without_suffix.replace("/", ".")
        stem = without_suffix.rsplit("/", 1)[-1]
        if dotted:
            tokens.add(f"module:{dotted}")
        if stem:
            tokens.add(f"module:{stem}")
        meta = _safe_meta(node.get("meta_json"))
        module = meta.get("module")
        if isinstance(module, str) and module:
            tokens.add(f"module:{module}")
        package = meta.get("package")
        if isinstance(package, str) and package and stem:
            tokens.add(f"module:{package}.{stem}")
    tokens.add(f"py:{path}:{name}")
    tokens.add(f"js:{path}:{name}")
    tokens.add(f"java:{path}:{name}")
    tokens.add(f"generic:{path}:{name}")
    if kind == "heading":
        tokens.add(f"heading:{path}:{name}")
    if kind == "route":
        tokens.add(f"route:{name}")
    return tokens


def _lookup(nodes: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for node in nodes:
        node_id = _node_id(node)
        for token in _legacy_tokens(node):
            lookup[token] = node_id
    return lookup


def find_references(store: GraphStore, node_id: str) -> dict[str, Any]:
    run_id = _latest_run_id(store)
    if run_id is None:
        raise ReferencesError("no map found; run `codeprism map .` first")

    nodes = [
        dict(row)
        for row in store.rows("SELECT * FROM nodes WHERE run_id = ? ORDER BY id", (run_id,))
    ]
    lookup = _lookup(nodes)
    target_id = lookup.get(node_id, node_id)
    target_node = next((node for node in nodes if _node_id(node) == target_id), None)
    edges = [
        dict(row)
        for row in store.rows("SELECT * FROM edges WHERE run_id = ? ORDER BY kind, source, target", (run_id,))
    ]

    incoming: list[dict[str, Any]] = []
    outgoing: list[dict[str, Any]] = []
    seen_incoming: set[tuple[str, str, str]] = set()
    seen_outgoing: set[tuple[str, str, str]] = set()
    for edge in edges:
        source = lookup.get(str(edge["source"]), str(edge["source"]))
        target = lookup.get(str(edge["target"]), str(edge["target"]))
        item = {
            "source": source,
            "target": target,
            "kind": str(edge["kind"]),
            "raw_source": str(edge["source"]),
            "raw_target": str(edge["target"]),
            "meta": _safe_meta(edge.get("meta_json")),
        }
        if target == target_id:
            key = (source, target, item["kind"])
            if key not in seen_incoming:
                seen_incoming.add(key)
                incoming.append(item)
        if source == target_id:
            key = (source, target, item["kind"])
            if key not in seen_outgoing:
                seen_outgoing.add(key)
                outgoing.append(item)

    return {
        "target_id": target_id,
        "node": target_node,
        "incoming": incoming,
        "outgoing": outgoing,
    }


def format_references(result: dict[str, Any]) -> str:
    lines = [
        "# CodePrism References",
        "",
        f"- Node: `{result['target_id']}`",
        f"- Incoming: {len(result['incoming'])}",
        f"- Outgoing: {len(result['outgoing'])}",
        "",
        "## Incoming",
        "",
    ]
    if result["incoming"]:
        for edge in result["incoming"]:
            lines.append(f"- `{edge['source']} --{edge['kind']}--> {edge['target']}`")
    else:
        lines.append("- None")
    lines += ["", "## Outgoing", ""]
    if result["outgoing"]:
        for edge in result["outgoing"]:
            lines.append(f"- `{edge['source']} --{edge['kind']}--> {edge['target']}`")
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"
