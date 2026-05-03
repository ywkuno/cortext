from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from .graph import GraphStore
from .ids import stable_node_id
from .retrieval import language_for_path
from .token_estimator import estimate_tokens


ReadMode = Literal["map", "signatures", "diff", "full"]
SYMBOL_KINDS = {"class", "function", "heading", "method", "route"}


@dataclass(frozen=True)
class ReadResult:
    mode: ReadMode
    path: str
    content: str
    estimated_tokens: int


class ReadError(ValueError):
    pass


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _normalize_requested_path(root: Path, requested: str) -> str:
    path = Path(requested).expanduser()
    root_resolved = root.resolve()
    if path.is_absolute():
        resolved = path.resolve()
        if not _is_relative_to(resolved, root_resolved):
            raise ReadError(f"path escapes root: {requested}")
        return resolved.relative_to(root_resolved).as_posix()
    normalized = requested.replace("\\", "/").strip()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.strip("/")
    if not normalized:
        raise ReadError("path is required")
    resolved = (root_resolved / normalized).resolve()
    if not _is_relative_to(resolved, root_resolved):
        raise ReadError(f"path escapes root: {requested}")
    return normalized


def _source_path(root: Path, rel_path: str) -> Path:
    path = (root.resolve() / rel_path).resolve()
    if not path.exists():
        raise ReadError(f"source file not found: {rel_path}")
    if not path.is_file():
        raise ReadError(f"path is not a file: {rel_path}")
    return path


def _latest_run_id(store: GraphStore) -> int | None:
    rows = store.rows("SELECT id FROM runs ORDER BY id DESC LIMIT 1")
    return int(rows[0]["id"]) if rows else None


def _node_id(row: dict[str, Any]) -> str:
    return stable_node_id(str(row["kind"]), str(row["path"]), str(row["name"]))


def _nodes_for_path(store: GraphStore, rel_path: str) -> list[dict[str, Any]]:
    run_id = _latest_run_id(store)
    if run_id is None:
        return []
    return [
        dict(row)
        for row in store.rows(
            """
            SELECT * FROM nodes
            WHERE run_id = ? AND path = ?
            ORDER BY
                CASE WHEN start_line IS NULL THEN 0 ELSE start_line END,
                kind,
                name
            """,
            (run_id, rel_path),
        )
    ]


def _line_text(node: dict[str, Any]) -> str:
    start = node.get("start_line")
    end = node.get("end_line")
    if start and end:
        return f" L{start}-{end}"
    if start:
        return f" L{start}"
    return ""


def _map_content(rel_path: str, nodes: list[dict[str, Any]]) -> str:
    lines = ["## Map", ""]
    if not nodes:
        lines.append("- No mapped nodes for this path. Run `codeprism map .` to refresh the graph.")
        return "\n".join(lines) + "\n"
    for node in nodes:
        lines.append(
            f"- `{_node_id(node)}` {node['kind']} {node['name']}{_line_text(node)}"
        )
    lines.append("")
    return "\n".join(lines)


def _signatures_content(rel_path: str, nodes: list[dict[str, Any]]) -> str:
    symbols = [node for node in nodes if node["kind"] in SYMBOL_KINDS]
    lines = ["## Signatures", ""]
    if not symbols:
        lines.append(f"- No mapped symbols for `{rel_path}`.")
        return "\n".join(lines) + "\n"
    for node in symbols:
        lines.append(
            f"- `{_node_id(node)}` {node['kind']} {node['name']}{_line_text(node)}"
        )
    lines.append("")
    return "\n".join(lines)


def _diff_content(root: Path, rel_path: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "diff", "--", rel_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "git diff failed"
        raise ReadError(message)
    diff = result.stdout.rstrip("\n")
    if not diff:
        diff = f"# No working-tree diff for {rel_path}"
    return f"```diff\n{diff}\n```\n"


def _full_content(root: Path, rel_path: str) -> str:
    text = _source_path(root, rel_path).read_text(encoding="utf-8", errors="replace").rstrip("\n")
    return f"```{language_for_path(rel_path)}\n{text}\n```\n"


def read_path(
    *,
    root: Path,
    path: str,
    mode: ReadMode,
    store: GraphStore | None = None,
) -> ReadResult:
    rel_path = _normalize_requested_path(root, path)
    if mode == "diff":
        content = _diff_content(root.resolve(), rel_path)
    elif mode == "full":
        content = _full_content(root, rel_path)
    else:
        nodes = _nodes_for_path(store, rel_path) if store is not None else []
        content = _map_content(rel_path, nodes) if mode == "map" else _signatures_content(rel_path, nodes)

    return ReadResult(
        mode=mode,
        path=rel_path,
        content=content,
        estimated_tokens=estimate_tokens(content),
    )


def format_read_result(result: ReadResult) -> str:
    return "\n".join(
        [
            "# CodePrism Read",
            "",
            f"- Mode: {result.mode}",
            f"- Path: `{result.path}`",
            f"- Estimated tokens: {result.estimated_tokens}",
            "",
            result.content.rstrip("\n"),
            "",
        ]
    )
