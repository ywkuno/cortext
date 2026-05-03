from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict


InstallTarget = Literal["project", "global", "all", "codex", "claude"]


class InstallResult(TypedDict):
    planned: int
    copied: int
    skipped: int
    paths: list[str]


@dataclass(frozen=True)
class IntegrationCopy:
    src: Path
    dst: Path


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))


def default_claude_home() -> Path:
    return Path(os.environ.get("CLAUDE_HOME", Path.home() / ".claude"))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _source_path(*parts: str) -> Path:
    return _repo_root().joinpath(*parts)


def planned_integrations(
    *,
    root: Path,
    target: InstallTarget,
    codex_home: Path,
    claude_home: Path,
) -> list[IntegrationCopy]:
    root = root.resolve()
    codex_home = codex_home.resolve()
    claude_home = claude_home.resolve()
    copies: list[IntegrationCopy] = []

    if target in {"project", "all", "claude"}:
        copies.extend(
            [
                IntegrationCopy(
                    _source_path("integrations", "claude-commands", "context-map.md"),
                    root / ".claude" / "commands" / "context-map.md",
                ),
                IntegrationCopy(
                    _source_path("integrations", "claude-commands", "context-query.md"),
                    root / ".claude" / "commands" / "context-query.md",
                ),
                IntegrationCopy(
                    _source_path("integrations", "claude-commands", "context-slice.md"),
                    root / ".claude" / "commands" / "context-slice.md",
                ),
                IntegrationCopy(
                    _source_path("integrations", "copilot", "copilot-instructions.md"),
                    root / ".github" / "copilot-instructions.md",
                ),
            ]
        )

    if target in {"global", "all", "codex"}:
        copies.append(
            IntegrationCopy(
                _source_path("integrations", "claude-skill", "cortext", "SKILL.md"),
                codex_home / "skills" / "cortext" / "SKILL.md",
            )
        )

    if target in {"global", "all", "claude"}:
        copies.append(
            IntegrationCopy(
                _source_path("integrations", "claude-skill", "cortext", "SKILL.md"),
                claude_home / "skills" / "cortext" / "SKILL.md",
            )
        )

    return copies


def install_integrations(
    *,
    root: Path | str = ".",
    target: InstallTarget = "all",
    codex_home: Path | str | None = None,
    claude_home: Path | str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> InstallResult:
    root_path = Path(root)
    codex_home_path = Path(codex_home) if codex_home is not None else default_codex_home()
    claude_home_path = Path(claude_home) if claude_home is not None else default_claude_home()
    copies = planned_integrations(
        root=root_path,
        target=target,
        codex_home=codex_home_path,
        claude_home=claude_home_path,
    )
    result: InstallResult = {"planned": len(copies), "copied": 0, "skipped": 0, "paths": []}

    for item in copies:
        if not item.src.exists():
            raise FileNotFoundError(f"Missing integration template: {item.src}")
        result["paths"].append(str(item.dst))
        if dry_run:
            continue
        if item.dst.exists() and not force:
            result["skipped"] += 1
            continue
        item.dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(item.src, item.dst)
        result["copied"] += 1

    return result
