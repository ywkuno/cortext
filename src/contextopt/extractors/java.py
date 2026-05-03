from __future__ import annotations

import re
from pathlib import Path

from .base import Edge, Extraction, Node


PACKAGE_RE = re.compile(r"^\s*package\s+([\w.]+)\s*;", re.MULTILINE)
IMPORT_RE = re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", re.MULTILINE)
TYPE_RE = re.compile(
    r"\b(?:(?:public|protected|private|abstract|final|static|sealed|non-sealed|strictfp)\s+)*"
    r"(class|interface|enum|record)\s+([A-Za-z_]\w*)"
)
METHOD_RE = re.compile(
    r"\b(?:(?:public|protected|private|static|final|abstract|synchronized|native|strictfp|default)\s+)*"
    r"(?:<[^>]+>\s*)?"
    r"(?:[A-Za-z_][\w.$<>\[\], ?&]*\s+)+"
    r"([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:throws\s+[^{]+)?\{?"
)
CONTROL_NAMES = {"if", "for", "while", "switch", "catch", "try", "return", "new", "throw"}


def _package_name(text: str) -> str | None:
    match = PACKAGE_RE.search(text)
    return match.group(1) if match else None


def _line_without_strings(line: str) -> str:
    out: list[str] = []
    in_string: str | None = None
    index = 0
    while index < len(line):
        char = line[index]
        if in_string:
            out.append(" ")
            if char == "\\":
                if index + 1 < len(line):
                    out.append(" ")
                    index += 2
                    continue
            elif char == in_string:
                in_string = None
            index += 1
            continue
        if char in {'"', "'"}:
            in_string = char
            out.append(" ")
            index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _is_entrypoint(line: str, name: str) -> bool:
    compact = " ".join(line.replace("...", "[]").split())
    return name == "main" and "static" in compact and "String[]" in compact


def _file_meta(path: Path, package: str | None) -> dict[str, str]:
    meta = {"language": "java", "parser": "deterministic-java-fallback"}
    if package:
        meta["package"] = package
        meta["module"] = f"{package}.{path.stem}"
    return meta


def extract_java(path: Path, rel_path: str) -> Extraction:
    text = path.read_text(encoding="utf-8", errors="replace")
    package = _package_name(text)
    out = Extraction()
    file_id = f"file:{rel_path}"
    out.nodes.append(Node(kind="file", path=rel_path, name=rel_path, meta=_file_meta(path, package)))

    for match in IMPORT_RE.finditer(text):
        out.edges.append(Edge(source=file_id, target=f"module:{match.group(1)}", kind="imports"))

    brace_depth = 0
    class_stack: list[tuple[str, int]] = []
    seen_symbols: set[tuple[str, str, int]] = set()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = _line_without_strings(raw_line)
        for match in TYPE_RE.finditer(line):
            java_kind, name = match.groups()
            key = ("class", name, line_number)
            if key in seen_symbols:
                continue
            seen_symbols.add(key)
            meta = {"java_kind": java_kind}
            if package:
                meta["package"] = package
                meta["module"] = f"{package}.{name}"
            out.nodes.append(
                Node(kind="class", path=rel_path, name=name, start_line=line_number, meta=meta)
            )
            out.edges.append(Edge(source=file_id, target=f"java:{rel_path}:{name}", kind="defines"))
            class_stack.append((name, brace_depth))

        parent_class = class_stack[-1][0] if class_stack else None
        for match in METHOD_RE.finditer(line):
            name = match.group(1)
            if name in CONTROL_NAMES:
                continue
            key = ("method", name, line_number)
            if key in seen_symbols:
                continue
            seen_symbols.add(key)
            meta: dict[str, object] = {}
            if parent_class:
                meta["parent_class"] = parent_class
            if package:
                meta["package"] = package
            if _is_entrypoint(line, name):
                meta["entrypoint"] = True
            out.nodes.append(
                Node(kind="method", path=rel_path, name=name, start_line=line_number, meta=meta)
            )
            out.edges.append(Edge(source=file_id, target=f"java:{rel_path}:{name}", kind="defines"))

        brace_depth += line.count("{") - line.count("}")
        while class_stack and brace_depth <= class_stack[-1][1]:
            class_stack.pop()

    return out
