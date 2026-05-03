from __future__ import annotations

import re
from pathlib import Path

from .base import Edge, Extraction, Node


LANGUAGE_BY_SUFFIX = {
    ".c": "c",
    ".cc": "cpp",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".cxx": "cpp",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".lua": "lua",
    ".m": "objective-c",
    ".mm": "objective-cpp",
    ".php": "php",
    ".ps1": "powershell",
    ".rb": "ruby",
    ".rs": "rust",
    ".scala": "scala",
    ".sh": "shell",
    ".swift": "swift",
}

CLASS_RE = re.compile(
    r"\b(?:pub\s+|public\s+|private\s+|protected\s+|internal\s+|open\s+|final\s+|abstract\s+)*"
    r"(?:class|struct|interface|enum|trait|object)\s+([A-Za-z_]\w*)"
)
GO_TYPE_RE = re.compile(r"\btype\s+([A-Za-z_]\w*)\s+(?:struct|interface)\b")
RUST_TYPE_RE = re.compile(r"\b(?:pub\s+)?(?:struct|enum|trait)\s+([A-Za-z_]\w*)")
FUNCTION_RE = re.compile(
    r"\b(?:pub\s+|public\s+|private\s+|protected\s+|internal\s+|static\s+|async\s+|"
    r"export\s+|final\s+|open\s+|override\s+)*"
    r"(?:fn|func|function|def|sub|proc|procedure)\s+([A-Za-z_]\w*)"
)
C_LIKE_FUNCTION_RE = re.compile(
    r"^\s*(?:public|private|protected|internal|static|virtual|override|async|final|inline|"
    r"extern|constexpr|\s)*"
    r"(?:[A-Za-z_][\w:<>,*&\[\].?]+\s+)+"
    r"([A-Za-z_]\w*)\s*\([^;]*\)\s*(?:\{|=>)"
)
IMPORT_PATTERNS = (
    re.compile(r'^\s*import\s+"([^"]+)"'),
    re.compile(r"^\s*import\s+([A-Za-z_][\w./:-]*)"),
    re.compile(r"^\s*use\s+([^;]+)"),
    re.compile(r"^\s*using\s+([A-Za-z_][\w.]*)"),
    re.compile(r'^\s*require\s+["\']([^"\']+)["\']'),
    re.compile(r"^\s*#include\s+[<\"]([^>\"]+)[>\"]"),
)
CONTROL_NAMES = {"if", "for", "while", "switch", "catch", "return", "sizeof"}


def language_for_suffix(suffix: str) -> str | None:
    return LANGUAGE_BY_SUFFIX.get(suffix.lower())


def _clean_import_target(value: str) -> str:
    return value.strip().strip(";").strip()


def extract_generic(path: Path, rel_path: str, language: str) -> Extraction:
    text = path.read_text(encoding="utf-8", errors="replace")
    out = Extraction()
    file_id = f"file:{rel_path}"
    out.nodes.append(
        Node(
            kind="file",
            path=rel_path,
            name=rel_path,
            meta={"language": language, "parser": "deterministic-generic-fallback"},
        )
    )

    current_class: str | None = None
    seen_symbols: set[tuple[str, str, int]] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for pattern in IMPORT_PATTERNS:
            match = pattern.search(line)
            if match:
                out.edges.append(
                    Edge(
                        source=file_id,
                        target=f"module:{_clean_import_target(match.group(1))}",
                        kind="imports",
                    )
                )
                break

        for pattern in (CLASS_RE, GO_TYPE_RE, RUST_TYPE_RE):
            for match in pattern.finditer(line):
                name = match.group(1)
                key = ("class", name, line_number)
                if key in seen_symbols:
                    continue
                seen_symbols.add(key)
                current_class = name
                out.nodes.append(
                    Node(
                        kind="class",
                        path=rel_path,
                        name=name,
                        start_line=line_number,
                        meta={"language": language},
                    )
                )
                out.edges.append(
                    Edge(source=file_id, target=f"generic:{rel_path}:{name}", kind="defines")
                )

        for pattern in (FUNCTION_RE, C_LIKE_FUNCTION_RE):
            for match in pattern.finditer(line):
                name = match.group(1)
                if name in CONTROL_NAMES:
                    continue
                key = ("function", name, line_number)
                if key in seen_symbols:
                    continue
                seen_symbols.add(key)
                kind = "method" if current_class else "function"
                meta: dict[str, object] = {"language": language}
                if current_class:
                    meta["parent_class"] = current_class
                out.nodes.append(
                    Node(kind=kind, path=rel_path, name=name, start_line=line_number, meta=meta)
                )
                out.edges.append(
                    Edge(source=file_id, target=f"generic:{rel_path}:{name}", kind="defines")
                )

    return out
