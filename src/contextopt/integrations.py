from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, TypedDict


InstallTarget = Literal["project", "global", "all", "codex", "claude"]
DoctorStatus = Literal["current", "missing", "stale"]


class InstallResult(TypedDict):
    planned: int
    copied: int
    skipped: int
    paths: list[str]


class DoctorItem(TypedDict):
    name: str
    path: str
    status: DoctorStatus
    message: str


class DoctorReport(TypedDict):
    ok: bool
    summary: dict[str, int]
    items: list[DoctorItem]


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


def _doctor_item(item: IntegrationCopy) -> DoctorItem:
    name = item.dst.name
    if item.dst.parent.name:
        name = f"{item.dst.parent.name}/{name}"
    if not item.dst.exists():
        return {
            "name": name,
            "path": str(item.dst),
            "status": "missing",
            "message": "not installed",
        }
    try:
        source_bytes = item.src.read_bytes()
        installed_bytes = item.dst.read_bytes()
    except OSError as exc:
        return {
            "name": name,
            "path": str(item.dst),
            "status": "stale",
            "message": f"could not compare files: {exc}",
        }
    if source_bytes == installed_bytes:
        return {
            "name": name,
            "path": str(item.dst),
            "status": "current",
            "message": "installed and current",
        }
    return {
        "name": name,
        "path": str(item.dst),
        "status": "stale",
        "message": "installed file differs from bundled template",
    }


def doctor_integrations(
    *,
    root: Path | str = ".",
    target: InstallTarget = "all",
    codex_home: Path | str | None = None,
    claude_home: Path | str | None = None,
) -> DoctorReport:
    root_path = Path(root)
    codex_home_path = Path(codex_home) if codex_home is not None else default_codex_home()
    claude_home_path = Path(claude_home) if claude_home is not None else default_claude_home()
    copies = planned_integrations(
        root=root_path,
        target=target,
        codex_home=codex_home_path,
        claude_home=claude_home_path,
    )
    items = [_doctor_item(item) for item in copies]
    summary = {"current": 0, "missing": 0, "stale": 0}
    for item in items:
        summary[item["status"]] += 1
    return {
        "ok": summary["missing"] == 0 and summary["stale"] == 0,
        "summary": summary,
        "items": items,
    }
