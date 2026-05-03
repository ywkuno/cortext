from __future__ import annotations

import re
from pathlib import Path

from .base import Edge, Extraction, Node

NAME = r"([A-Za-z_$][\w$]*)"
FUNC_RE = re.compile(rf"(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+{NAME}")
CLASS_RE = re.compile(rf"(?:export\s+)?(?:default\s+)?class\s+{NAME}")
ARROW_RE = re.compile(
    rf"(?:export\s+)?(?:const|let|var)\s+{NAME}\s*(?::[^=]+)?=\s*"
    rf"(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*=>"
)
FUNC_EXPR_RE = re.compile(
    rf"(?:export\s+)?(?:const|let|var)\s+{NAME}\s*(?::[^=]+)?=\s*"
    r"(?:async\s+)?function\b"
)
IMPORT_RE = re.compile(
    r"""(?:import|export)\s+(?:type\s+)?(?:[^'"]*?\s+from\s+)?['"]([^'"]+)['"]"""
    r"""|require\(\s*['"]([^'"]+)['"]\s*\)"""
)
NEXT_ROUTE_FILES = {"page", "route", "layout", "template", "loading", "error", "not-found"}


def _strip_line_comments(text: str) -> str:
    lines: list[str] = []
    in_block = False
    for line in text.splitlines():
        out: list[str] = []
        index = 0
        in_string: str | None = None
        while index < len(line):
            char = line[index]
            next_char = line[index + 1] if index + 1 < len(line) else ""
            if in_block:
                if char == "*" and next_char == "/":
                    in_block = False
                    out.extend("  ")
                    index += 2
                else:
                    out.append(" ")
                    index += 1
                continue
            if in_string:
                out.append(char)
                if char == "\\":
                    if index + 1 < len(line):
                        out.append(line[index + 1])
                        index += 2
                        continue
                elif char == in_string:
                    in_string = None
                index += 1
                continue
            if char in {"'", '"', "`"}:
                in_string = char
                out.append(char)
                index += 1
                continue
            if char == "/" and next_char == "/":
                out.extend(" " * (len(line) - index))
                break
            if char == "/" and next_char == "*":
                in_block = True
                out.extend("  ")
                index += 2
                continue
            out.append(char)
            index += 1
        lines.append("".join(out))
    return "\n".join(lines)


def _route_segment(segment: str) -> str | None:
    if not segment or segment.startswith("(") or segment.startswith("@"):
        return None
    if segment.startswith("[[...") and segment.endswith("]]"):
        return f"*{segment[5:-2]}?"
    if segment.startswith("[...") and segment.endswith("]"):
        return f"*{segment[4:-1]}"
    if segment.startswith("[") and segment.endswith("]"):
        return f":{segment[1:-1]}"
    return segment


def detect_nextjs_route(rel_path: str) -> tuple[str, str] | None:
    parts = rel_path.replace("\\", "/").split("/")
    if len(parts) < 2:
        return None

    filename = parts[-1]
    stem = filename.rsplit(".", maxsplit=1)[0]
    if parts[0] == "app" and stem in NEXT_ROUTE_FILES:
        route_parts = [_route_segment(part) for part in parts[1:-1]]
        route = "/" + "/".join(part for part in route_parts if part)
        return route if route != "/" else "/", "app"

    if parts[0] == "pages":
        page_parts = parts[1:]
        page_parts[-1] = page_parts[-1].split(".", maxsplit=1)[0]
        if page_parts[-1] == "index":
            page_parts = page_parts[:-1]
        route_parts = [_route_segment(part) for part in page_parts]
        route = "/" + "/".join(part for part in route_parts if part)
        return route if route != "/" else "/", "pages"

    return None


def extract_js_ts(path: Path, rel_path: str) -> Extraction:
    text = path.read_text(encoding="utf-8", errors="replace")
    scan_text = _strip_line_comments(text)
    out = Extraction()
    file_id = f"file:{rel_path}"
    language = "typescript" if path.suffix.lower() in {".ts", ".tsx"} else "javascript"
    out.nodes.append(
        Node(
            kind="file",
            path=rel_path,
            name=rel_path,
            meta={"language": language, "parser": "deterministic-js-ts-fallback"},
        )
    )
    route = detect_nextjs_route(rel_path)
    if route:
        route_name, router = route
        out.nodes.append(
            Node(
                kind="route",
                path=rel_path,
                name=route_name,
                meta={"framework": "nextjs", "router": router},
            )
        )
        out.edges.append(Edge(source=file_id, target=f"route:{route_name}", kind="routes"))

    seen_symbols: set[tuple[str, str, int]] = set()
    for i, line in enumerate(scan_text.splitlines(), start=1):
        for regex, syntax in (
            (FUNC_RE, "function"),
            (ARROW_RE, "arrow"),
            (FUNC_EXPR_RE, "function-expression"),
        ):
            for match in regex.finditer(line):
                name = match.group(1)
                key = ("function", name, i)
                if key in seen_symbols:
                    continue
                seen_symbols.add(key)
                out.nodes.append(
                    Node(
                        kind="function",
                        path=rel_path,
                        name=name,
                        start_line=i,
                        meta={"syntax": syntax},
                    )
                )
                out.edges.append(
                    Edge(source=file_id, target=f"js:{rel_path}:{name}", kind="defines")
                )
        for m in CLASS_RE.finditer(line):
            name = m.group(1)
            key = ("class", name, i)
            if key in seen_symbols:
                continue
            seen_symbols.add(key)
            out.nodes.append(Node(kind="class", path=rel_path, name=name, start_line=i))
            out.edges.append(Edge(source=file_id, target=f"js:{rel_path}:{name}", kind="defines"))
        for m in IMPORT_RE.finditer(line):
            target = m.group(1) or m.group(2)
            out.edges.append(Edge(source=file_id, target=f"module:{target}", kind="imports"))
    return out
