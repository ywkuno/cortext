from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path


def test_init_writes_default_config(tmp_path: Path):
    result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "init", "--root", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    config = tmp_path / ".contextopt" / "config.toml"
    assert config.read_text(encoding="utf-8") == (
        'max_file_bytes = 500000\nignore = ["node_modules", ".git", "dist", "build", ".next"]\n'
    )


def test_export_json_uses_json_default_output(tmp_path: Path):
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(tmp_path / ".contextopt" / "context.db")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    export_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "export",
            "--format",
            "json",
            "--db",
            str(tmp_path / ".contextopt" / "context.db"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert export_result.returncode == 0, export_result.stderr
    assert (tmp_path / ".contextopt" / "context-pack.json").exists()
    assert not (tmp_path / ".contextopt" / "context-pack.md").exists()
    payload = json.loads((tmp_path / ".contextopt" / "context-pack.json").read_text())
    assert payload["meta"]["schema_version"] == 1


def test_activity_normalize_command_writes_safe_payload(tmp_path: Path):
    activity = tmp_path / "activity.jsonl"
    activity.write_text(
        '{"agent_id":"codex","event":"file_read","path":"app.py","estimated_tokens":42}\n'
        "bad row\n",
        encoding="utf-8",
    )
    out = tmp_path / ".contextopt" / "activity-stream.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "activity",
            "normalize",
            str(activity),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["event_count"] == 1
    assert payload["summary"]["estimated_tokens"] == 42
    assert len(payload["warnings"]) == 1
    assert "1 events" in result.stdout
    assert "1 warnings" in result.stdout


def test_prime_command_maps_and_writes_slice_first_workflow(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "def billing_webhook():\n    return 'ok'\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "prime",
            "billing webhook",
            "--root",
            str(tmp_path),
            "--db",
            str(tmp_path / ".contextopt" / "context.db"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".contextopt" / "slices" / "billing-webhook.md").exists()
    assert (tmp_path / ".contextopt" / "slices" / "billing-webhook.json").exists()
    assert "Read this slice first" in result.stdout
    assert "of full context" in result.stdout


def test_prime_defaults_outputs_under_root_when_called_elsewhere(tmp_path: Path):
    project = tmp_path / "project"
    outside = tmp_path / "outside"
    project.mkdir()
    outside.mkdir()
    (project / "app.py").write_text("def target_symbol():\n    return 1\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "prime",
            "target symbol",
            "--root",
            str(project),
        ],
        cwd=outside,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (project / ".contextopt" / "context.db").exists()
    assert (project / ".contextopt" / "slices" / "target-symbol.md").exists()
    assert not (outside / ".contextopt").exists()
