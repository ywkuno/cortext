from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..graph import GraphStore
from ..ids import stable_node_id


SCHEMA_VERSION = 1


PACKAGE_FILES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pyproject.toml",
    "poetry.lock",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
    "uv.lock",
}

REPO_CONTROL_FILES = {
    ".gitattributes",
    ".gitignore",
    ".gitmodules",
    ".pre-commit-config.yaml",
}

AGENT_FILES = {
    "agents.md",
    "agent.md",
    "claude.md",
    "skill.md",
    "copilot-instructions.md",
}


def _safe_meta(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def classify_node_role(kind: str, path: str, name: str, meta: dict[str, Any] | None = None) -> str:
    meta = meta or {}
    normalized_path = path.replace("\\", "/").strip("/")
    lower_path = normalized_path.lower()
    lower_name = name.lower()
    basename = lower_path.rsplit("/", 1)[-1] if lower_path else lower_name

    if kind == "module" or meta.get("external"):
        return "dependency"
    if lower_path.startswith(".contextopt/") or "/.contextopt/" in lower_path:
        return "generated"
    if basename in AGENT_FILES or "/claude-skill/" in lower_path or lower_path.startswith(
        ("integrations/claude", "integrations/codex", "integrations/copilot", ".claude/")
    ):
        return "agent"
    if basename in REPO_CONTROL_FILES or lower_path.startswith(".github/"):
        return "repo"
    if basename in PACKAGE_FILES:
        return "package"
    if lower_path.startswith("tests/") or "/tests/" in lower_path or basename.startswith("test_"):
        return "test"
    if lower_path.startswith("examples/"):
        return "example"
    if lower_path.startswith("docs/") or basename.endswith(".md"):
        return "doc"
    if lower_path.startswith(("src/", "apps/", "scripts/")) or basename.endswith(
        (".py", ".js", ".jsx", ".ts", ".tsx", ".rs", ".go", ".java", ".cs", ".php", ".rb")
    ):
        return "source"
    return "project"


def _node_payload(row) -> dict[str, Any]:
    meta = _safe_meta(row["meta_json"])
    meta.setdefault("role", classify_node_role(row["kind"], row["path"], row["name"], meta))
    return {
        "id": stable_node_id(row["kind"], row["path"], row["name"]),
        "kind": row["kind"],
        "path": row["path"],
        "name": row["name"],
        "label": row["name"],
        "start_line": row["start_line"],
        "end_line": row["end_line"],
        "meta": meta,
    }


def _legacy_lookup(nodes: list[dict[str, Any]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for node in nodes:
        node_id = node["id"]
        lookup[node_id] = node_id
        if node["kind"] in {"file", "doc"}:
            lookup[f"file:{node['path']}"] = node_id
            module = node["meta"].get("module")
            if isinstance(module, str) and module:
                lookup[f"module:{module}"] = node_id
            package = node["meta"].get("package")
            stem = node["path"].replace("\\", "/").rsplit("/", 1)[-1].rsplit(".", 1)[0]
            if isinstance(package, str) and package and stem:
                lookup[f"module:{package}.{stem}"] = node_id
        lookup[f"py:{node['path']}:{node['name']}"] = node_id
        lookup[f"js:{node['path']}:{node['name']}"] = node_id
        lookup[f"java:{node['path']}:{node['name']}"] = node_id
        lookup[f"generic:{node['path']}:{node['name']}"] = node_id
        if node["kind"] == "heading":
            lookup[f"heading:{node['path']}:{node['name']}"] = node_id
        if node["kind"] == "route":
            lookup[f"route:{node['name']}"] = node_id
    return lookup


def _resolve_endpoint(
    value: str,
    lookup: dict[str, str],
    synthetic_modules: dict[str, dict[str, Any]],
) -> str:
    if value in lookup:
        return lookup[value]
    if value.startswith("module:"):
        name = value.removeprefix("module:")
        node_id = stable_node_id("module", "", name)
        synthetic_modules.setdefault(
            node_id,
            {
                "id": node_id,
                "kind": "module",
                "path": "",
                "name": name,
                "label": name,
                "start_line": None,
                "end_line": None,
                "meta": {"external": True, "role": "dependency"},
            },
        )
        return node_id
    return value


def export_json(store: GraphStore, out: Path) -> None:
    run = store.rows("SELECT * FROM runs ORDER BY id DESC LIMIT 1")
    run_filter = "WHERE run_id = ?" if run else ""
    params = (run[0]["id"],) if run else ()
    node_rows = store.rows(
        f"SELECT * FROM nodes {run_filter} ORDER BY kind, path, name LIMIT 100000",
        params,
    )
    edge_rows = store.rows(
        f"SELECT * FROM edges {run_filter} ORDER BY kind, source, target LIMIT 200000",
        params,
    )
    nodes = [_node_payload(row) for row in node_rows]
    lookup = _legacy_lookup(nodes)
    synthetic_modules: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    seen_edges: set[tuple[str, str, str]] = set()

    for row in edge_rows:
        source = _resolve_endpoint(row["source"], lookup, synthetic_modules)
        target = _resolve_endpoint(row["target"], lookup, synthetic_modules)
        key = (source, target, row["kind"])
        if key in seen_edges:
            continue
        seen_edges.add(key)
        edges.append(
            {
                "source": source,
                "target": target,
                "kind": row["kind"],
                "meta": _safe_meta(row["meta_json"]),
            }
        )

    nodes.extend(synthetic_modules[node_id] for node_id in sorted(synthetic_modules))

    payload = {
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "root": run[0]["root"] if run else "",
            "created_at": run[0]["created_at"] if run else "",
            "node_count": len(nodes),
            "edge_count": len(edges),
        },
        "nodes": nodes,
        "edges": edges,
    }
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
