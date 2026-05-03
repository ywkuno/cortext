from __future__ import annotations
import ast
from pathlib import Path

from .base import Edge, Extraction, Node


def _function_node(item: ast.FunctionDef | ast.AsyncFunctionDef, rel_path: str, kind: str) -> Node:
    meta = {"async": isinstance(item, ast.AsyncFunctionDef)}
    return Node(
        kind=kind,
        path=rel_path,
        name=item.name,
        start_line=getattr(item, "lineno", None),
        end_line=getattr(item, "end_lineno", None),
        meta=meta,
    )


def extract_python(path: Path, rel_path: str) -> Extraction:
    text = path.read_text(encoding="utf-8", errors="replace")
    out = Extraction()
    file_id = f"file:{rel_path}"
    out.nodes.append(Node(kind="file", path=rel_path, name=rel_path, meta={"language": "python"}))
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        out.nodes.append(Node(kind="parse_error", path=rel_path, name=str(exc)))
        return out
    for item in tree.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            out.nodes.append(_function_node(item, rel_path, "function"))
            out.edges.append(Edge(source=file_id, target=f"py:{rel_path}:{item.name}", kind="defines"))
        elif isinstance(item, ast.ClassDef):
            out.nodes.append(
                Node(
                    kind="class",
                    path=rel_path,
                    name=item.name,
                    start_line=getattr(item, "lineno", None),
                    end_line=getattr(item, "end_lineno", None),
                )
            )
            out.edges.append(Edge(source=file_id, target=f"py:{rel_path}:{item.name}", kind="defines"))
            for child in item.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method = _function_node(child, rel_path, "method")
                    method.meta["parent_class"] = item.name
                    out.nodes.append(method)
                    out.edges.append(
                        Edge(source=file_id, target=f"py:{rel_path}:{child.name}", kind="defines")
                    )
        elif isinstance(item, ast.Import):
            for alias in item.names:
                out.edges.append(
                    Edge(source=file_id, target=f"module:{alias.name}", kind="imports")
                )
        elif isinstance(item, ast.ImportFrom) and item.module:
            out.edges.append(Edge(source=file_id, target=f"module:{item.module}", kind="imports"))
    return out
