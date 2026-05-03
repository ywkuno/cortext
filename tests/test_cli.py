from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path


def test_cli_help_uses_codeprism_as_public_name():
    result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "usage: codeprism" in result.stdout
    assert "CodePrism" in result.stdout


def test_pyproject_exposes_codeprism_and_contextopt_console_scripts():
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")

    assert 'codeprism = "contextopt.cli:main"' in text
    assert 'contextopt = "contextopt.cli:main"' in text


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


def test_get_command_prints_exact_symbol_source(tmp_path: Path):
    source = (
        "def target():\n"
        "    value = 41\n"
        "    return value + 1\n"
        "\n"
        "def noisy_neighbor():\n"
        "    return 'skip me'\n"
    )
    (tmp_path / "app.py").write_text(source, encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "get",
            "function::app.py::target",
            "--root",
            str(tmp_path),
            "--db",
            str(db),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "- Node: `function::app.py::target`" in result.stdout
    assert "- Lines: 1-3" in result.stdout
    assert "def target():" in result.stdout
    assert "return value + 1" in result.stdout
    assert "noisy_neighbor" not in result.stdout


def test_get_command_returns_nonzero_for_missing_node(tmp_path: Path):
    (tmp_path / "app.py").write_text("def target():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "get",
            "function::app.py::missing",
            "--root",
            str(tmp_path),
            "--db",
            str(db),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "node not found" in result.stderr.lower()


def test_read_map_mode_prints_file_metadata_without_source_body(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "def target():\n"
        "    return 'body should stay hidden'\n",
        encoding="utf-8",
    )
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "read",
            "app.py",
            "--mode",
            "map",
            "--root",
            str(tmp_path),
            "--db",
            str(db),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "# CodePrism Read" in result.stdout
    assert "- Mode: map" in result.stdout
    assert "- Path: `app.py`" in result.stdout
    assert "function::app.py::target" in result.stdout
    assert "body should stay hidden" not in result.stdout


def test_read_signatures_mode_prints_symbols_without_function_bodies(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "class Service:\n"
        "    def run(self):\n"
        "        return 'do not include body'\n"
        "\n"
        "def helper(value):\n"
        "    return value + 1\n",
        encoding="utf-8",
    )
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "read",
            "app.py",
            "--mode",
            "signatures",
            "--root",
            str(tmp_path),
            "--db",
            str(db),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "- `class::app.py::Service` class Service L1-3" in result.stdout
    assert "- `method::app.py::run` method run L2-3" in result.stdout
    assert "- `function::app.py::helper` function helper L5-6" in result.stdout
    assert "do not include body" not in result.stdout
    assert "return value + 1" not in result.stdout


def test_read_diff_mode_prints_git_diff_for_one_path(tmp_path: Path):
    (tmp_path / "app.py").write_text("def target():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True, text=True, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, capture_output=True, text=True, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test User",
            "commit",
            "-m",
            "initial",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    (tmp_path / "app.py").write_text("def target():\n    return 2\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "read",
            "app.py",
            "--mode",
            "diff",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "diff --git" in result.stdout
    assert "-    return 1" in result.stdout
    assert "+    return 2" in result.stdout


def test_read_full_mode_prints_whole_file(tmp_path: Path):
    (tmp_path / "app.py").write_text("def target():\n    return 1\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "read",
            "app.py",
            "--mode",
            "full",
            "--root",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "- Mode: full" in result.stdout
    assert "```python" in result.stdout
    assert "def target():" in result.stdout
    assert "return 1" in result.stdout


def test_gain_command_reports_savings_and_map_freshness(tmp_path: Path):
    app = tmp_path / "app.py"
    app.write_text("def main():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "gain",
            str(tmp_path),
            "--db",
            str(db),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "# CodePrism Gain" in result.stdout
    assert "Source -> context pack saving" in result.stdout
    assert "Map status: current" in result.stdout

    app.write_text("def main():\n    return 1000\n", encoding="utf-8")
    stale_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "gain",
            str(tmp_path),
            "--db",
            str(db),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert stale_result.returncode == 0, stale_result.stderr
    assert "Map status: stale" in stale_result.stdout
    assert "Changed files: 1" in stale_result.stdout


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
    assert "Source estimate:" in result.stdout
    assert "Slice estimate:" in result.stdout
    assert "Estimated saving:" in result.stdout
    assert "Included:" in result.stdout


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


def test_prime_changed_seeds_slice_from_git_changes(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
    (project / "app.py").write_text("def stable():\n    return 1\n", encoding="utf-8")
    (project / "feature.py").write_text("def old_feature():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=project, capture_output=True, text=True, check=True)
    subprocess.run(["git", "add", "."], cwd=project, capture_output=True, text=True, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.com",
            "-c",
            "user.name=Test User",
            "commit",
            "-m",
            "initial",
        ],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    )
    (project / "feature.py").write_text(
        "def changed_feature():\n    return 2\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "prime",
            "unrelated query",
            "--root",
            str(project),
            "--changed",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    slice_text = (project / ".contextopt" / "slices" / "unrelated-query.md").read_text(
        encoding="utf-8"
    )
    assert "feature.py" in slice_text
    assert "changed_feature" in slice_text
    assert "Changed files: 1" in result.stdout


def test_prime_artifact_dir_keeps_outputs_outside_readonly_root(tmp_path: Path):
    project = tmp_path / "project"
    artifacts = tmp_path / "artifacts"
    project.mkdir()
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
            "--artifact-dir",
            str(artifacts),
            "--readonly-root",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (artifacts / "context.db").exists()
    assert (artifacts / "slices" / "target-symbol.md").exists()
    assert (artifacts / "slices" / "target-symbol.json").exists()
    assert not (project / ".contextopt").exists()


def test_prime_readonly_root_rejects_default_outputs_under_root(tmp_path: Path):
    project = tmp_path / "project"
    project.mkdir()
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
            "--readonly-root",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "refusing to write artifacts inside read-only root" in result.stderr.lower()
    assert not (project / ".contextopt").exists()
