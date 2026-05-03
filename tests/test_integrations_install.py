from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from contextopt.integrations import doctor_integrations, install_integrations


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


def test_doctor_integrations_reports_missing_and_current_files(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    claude_home = tmp_path / "claude-home"

    missing = doctor_integrations(
        root=tmp_path,
        target="all",
        codex_home=codex_home,
        claude_home=claude_home,
    )

    assert missing["ok"] is False
    assert missing["summary"]["missing"] == 6
    assert missing["summary"]["current"] == 0

    install_integrations(
        root=tmp_path,
        target="all",
        codex_home=codex_home,
        claude_home=claude_home,
    )
    current = doctor_integrations(
        root=tmp_path,
        target="all",
        codex_home=codex_home,
        claude_home=claude_home,
    )

    assert current["ok"] is True
    assert current["summary"]["current"] == 6
    assert current["summary"]["missing"] == 0
    assert all(item["status"] == "current" for item in current["items"])


def test_doctor_integrations_reports_stale_files(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    claude_home = tmp_path / "claude-home"
    install_integrations(
        root=tmp_path,
        target="global",
        codex_home=codex_home,
        claude_home=claude_home,
    )
    (codex_home / "skills" / "cortext" / "SKILL.md").write_text("old skill\n", encoding="utf-8")

    report = doctor_integrations(
        root=tmp_path,
        target="global",
        codex_home=codex_home,
        claude_home=claude_home,
    )

    assert report["ok"] is False
    assert report["summary"]["stale"] == 1
    assert any(item["status"] == "stale" for item in report["items"])


def test_doctor_cli_json_reports_install_health(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    claude_home = tmp_path / "claude-home"
    install_integrations(
        root=tmp_path,
        target="global",
        codex_home=codex_home,
        claude_home=claude_home,
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "doctor",
            "--target",
            "global",
            "--root",
            str(tmp_path),
            "--codex-home",
            str(codex_home),
            "--claude-home",
            str(claude_home),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True
    assert payload["summary"]["current"] == 2


def test_doctor_cli_returns_nonzero_when_install_is_missing(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "doctor",
            "--target",
            "codex",
            "--root",
            str(tmp_path),
            "--codex-home",
            str(tmp_path / "codex-home"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "missing" in result.stdout.lower()


def test_setup_cli_installs_and_verifies_integrations(tmp_path: Path) -> None:
    codex_home = tmp_path / "codex-home"
    claude_home = tmp_path / "claude-home"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "setup",
            "--target",
            "all",
            "--root",
            str(tmp_path),
            "--codex-home",
            str(codex_home),
            "--claude-home",
            str(claude_home),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".claude" / "commands" / "context-slice.md").exists()
    assert (tmp_path / ".github" / "copilot-instructions.md").exists()
    assert (codex_home / "skills" / "cortext" / "SKILL.md").exists()
    assert (claude_home / "skills" / "cortext" / "SKILL.md").exists()
    assert "CodePrism Setup" in result.stdout
    assert "Summary: 6 current, 0 missing, 0 stale." in result.stdout
