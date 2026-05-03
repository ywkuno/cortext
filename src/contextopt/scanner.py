from __future__ import annotations

from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

DEFAULT_IGNORE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".nuxt",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".contextopt",
}
DEFAULT_IGNORE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".db",
    ".sqlite",
    ".lock",
}
DEFAULT_IGNORE_PATTERNS = ["*.egg-info/"]


@dataclass(frozen=True)
class ScannedFile:
    path: Path
    rel_path: str
    size: int
    suffix: str
    mtime_ns: int


@dataclass(frozen=True)
class IgnoreRule:
    pattern: str
    negated: bool = False
    directory_only: bool = False
    root_relative: bool = False


def _load_gitignore(root: Path) -> list[str]:
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return []
    try:
        return gitignore.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []


def _parse_ignore_rule(line: str) -> IgnoreRule | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    negated = stripped.startswith("!")
    if negated:
        stripped = stripped[1:].strip()
    if not stripped:
        return None
    root_relative = stripped.startswith("/")
    stripped = stripped.lstrip("/")
    directory_only = stripped.endswith("/")
    stripped = stripped.rstrip("/")
    if not stripped:
        return None
    return IgnoreRule(stripped.replace("\\", "/"), negated, directory_only, root_relative)


def _matches_rule(rel_path: str, rule: IgnoreRule) -> bool:
    rel_path = rel_path.replace("\\", "/")
    parts = rel_path.split("/")
    pattern = rule.pattern
    has_slash = "/" in pattern

    if rule.directory_only:
        parents = parts[:-1]
        if has_slash or rule.root_relative:
            return rel_path == pattern or rel_path.startswith(f"{pattern}/")
        return any(fnmatch(part, pattern) for part in parents)

    if has_slash or rule.root_relative:
        return fnmatch(rel_path, pattern)

    return fnmatch(parts[-1], pattern) or any(fnmatch(part, pattern) for part in parts)


def _is_ignored_by_patterns(rel_path: str, rules: list[IgnoreRule]) -> bool:
    ignored = False
    for rule in rules:
        if _matches_rule(rel_path, rule):
            ignored = not rule.negated
    return ignored


def scan_files(
    root: Path,
    max_file_bytes: int = 500_000,
    ignore_patterns: list[str] | None = None,
    use_gitignore: bool = True,
) -> list[ScannedFile]:
    root = root.resolve()
    files: list[ScannedFile] = []
    patterns = [*DEFAULT_IGNORE_PATTERNS]
    if use_gitignore:
        patterns.extend(_load_gitignore(root))
    patterns.extend(ignore_patterns or [])
    rules = [rule for line in patterns if (rule := _parse_ignore_rule(line))]

    for path in root.rglob("*"):
        if path.is_dir():
            continue
        rel_parts = path.relative_to(root).parts
        rel_path = str(path.relative_to(root)).replace("\\", "/")
        if any(part in DEFAULT_IGNORE_DIRS for part in rel_parts):
            continue
        if _is_ignored_by_patterns(rel_path, rules):
            continue
        if path.suffix.lower() in DEFAULT_IGNORE_SUFFIXES:
            continue
        try:
            stat = path.stat()
        except OSError:
            continue
        if stat.st_size > max_file_bytes:
            continue
        files.append(
            ScannedFile(
                path=path,
                rel_path=rel_path,
                size=stat.st_size,
                suffix=path.suffix.lower(),
                mtime_ns=stat.st_mtime_ns,
            )
        )
    return sorted(files, key=lambda f: f.rel_path)
