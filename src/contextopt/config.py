from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ContextOptConfig:
    max_file_bytes: int = 500_000
    ignore: list[str] = field(default_factory=list)


def load_config(root: Path) -> ContextOptConfig:
    config_path = root.resolve() / ".contextopt" / "config.toml"
    if not config_path.exists():
        return ContextOptConfig()

    max_file_bytes = 500_000
    ignore: list[str] = []
    try:
        lines = config_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ContextOptConfig()

    for line in lines:
        stripped = line.split("#", 1)[0].strip()
        if not stripped or "=" not in stripped:
            continue
        key, raw_value = [part.strip() for part in stripped.split("=", 1)]
        if key == "max_file_bytes":
            try:
                max_file_bytes = int(raw_value)
            except ValueError:
                continue
        elif key == "ignore":
            try:
                value = ast.literal_eval(raw_value)
            except (SyntaxError, ValueError):
                continue
            if isinstance(value, list):
                ignore = [item for item in value if isinstance(item, str)]

    return ContextOptConfig(max_file_bytes=max_file_bytes, ignore=ignore)
