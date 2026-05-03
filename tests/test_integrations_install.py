from __future__ import annotations

from pathlib import Path

from contextopt.integrations import install_integrations


def test_install_project_integrations_copies_project_agent_files(tmp_path: Path) -> None:
    result = install_integrations(root=tmp_path, target="project")

    assert (tmp_path / ".claude" / "commands" / "context-map.md").exists()
    assert (tmp_path / ".claude" / "commands" / "context-query.md").exists()
    assert (tmp_path / ".claude" / "commands" / "context-slice.md").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()
    assert result["copied"] == 4


def test_install_global_integrations_copies_codex_and_claude_skills(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    claude_home = tmp_path / "claude-home"

    result = install_integrations(
        root=tmp_path / "project",
        target="global",
        codex_home=codex_home,
        claude_home=claude_home,
    )

    codex_skill = codex_home / "skills" / "cortext" / "SKILL.md"
    claude_skill = claude_home / "skills" / "cortext" / "SKILL.md"
    assert codex_skill.exists()
    assert claude_skill.exists()
    assert "context slices" in codex_skill.read_text(encoding="utf-8")
    assert result["copied"] == 2


def test_install_integrations_dry_run_does_not_write(tmp_path: Path) -> None:
    result = install_integrations(
        root=tmp_path,
        target="all",
        codex_home=tmp_path / "codex-home",
        claude_home=tmp_path / "claude-home",
        dry_run=True,
    )

    assert result["planned"] == 6
    assert result["copied"] == 0
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / "codex-home").exists()
