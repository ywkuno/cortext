from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph import GraphStore
from .ids import stable_node_id
from .token_estimator import estimate_tokens


FILE_KINDS = {"file", "doc"}


@dataclass(frozen=True)
class RetrievedSource:
    node_id: str
    kind: str
    path: str
    name: str
    start_line: int | None
    end_line: int | None
    source: str
    estimated_tokens: int
    meta: dict[str, Any]


class RetrievalError(ValueError):
    pass


def _latest_run_id(store: GraphStore) -> int | None:
    rows = store.rows("SELECT id FROM runs ORDER BY id DESC LIMIT 1")
    return int(rows[0]["id"]) if rows else None


def _node_row_id(row: dict[str, Any]) -> str:
    return stable_node_id(str(row["kind"]), str(row["path"]), str(row["name"]))


def _node_by_id(store: GraphStore, node_id: str) -> dict[str, Any] | None:
    run_id = _latest_run_id(store)
    if run_id is None:
        return None
    for row in store.rows("SELECT * FROM nodes WHERE run_id = ? ORDER BY id", (run_id,)):
        node = dict(row)
        if _node_row_id(node) == node_id:
            return node
    return None


def _safe_meta(value: object) -> dict[str, Any]:
    if not isinstance(value, str) or not value:
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _source_path(root: Path, rel_path: str) -> Path:
    normalized = rel_path.replace("\\", "/").strip("/")
    path = (root / normalized).resolve()
    root_resolved = root.resolve()
    if not _is_relative_to(path, root_resolved):
        raise RetrievalError(f"node path escapes root: {rel_path}")
    if not path.exists():
        raise RetrievalError(f"source file not found: {rel_path}")
    if not path.is_file():
        raise RetrievalError(f"node path is not a file: {rel_path}")
    return path


def _line_span(node: dict[str, Any], line_count: int) -> tuple[int, int]:
    if node["kind"] in FILE_KINDS or node.get("start_line") is None:
        return 1, line_count
    start = max(1, int(node["start_line"]))
    end = int(node["end_line"] or start)
    end = max(start, min(end, line_count))
    return start, end


def retrieve_source(store: GraphStore, root: Path, node_id: str) -> RetrievedSource:
    node = _node_by_id(store, node_id)
    if node is None:
        raise RetrievalError(f"node not found: {node_id}")

    path = _source_path(root, str(node["path"]))
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    start, end = _line_span(node, len(lines))
    source = "".join(lines[start - 1 : end])
    if source and not source.endswith("\n"):
        source += "\n"

    return RetrievedSource(
        node_id=node_id,
        kind=str(node["kind"]),
        path=str(node["path"]),
        name=str(node["name"]),
        start_line=start,
        end_line=end,
        source=source,
        estimated_tokens=estimate_tokens(source),
        meta=_safe_meta(node.get("meta_json")),
    )


def language_for_path(path: str) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    return {
        "py": "python",
        "md": "markdown",
        "js": "javascript",
        "jsx": "jsx",
        "ts": "typescript",
        "tsx": "tsx",
        "java": "java",
        "json": "json",
        "toml": "toml",
        "yml": "yaml",
        "yaml": "yaml",
        "ps1": "powershell",
        "sh": "bash",
    }.get(suffix, suffix or "text")


def format_retrieved_source(result: RetrievedSource) -> str:
    return "\n".join(
        [
            "# CodePrism Get",
            "",
            f"- Node: `{result.node_id}`",
            f"- Kind: {result.kind}",
            f"- Path: `{result.path}`",
            f"- Name: `{result.name}`",
            f"- Lines: {result.start_line}-{result.end_line}",
            f"- Estimated tokens: {result.estimated_tokens}",
            "",
            f"```{language_for_path(result.path)}",
            result.source.rstrip("\n"),
            "```",
            "",
        ]
    )
