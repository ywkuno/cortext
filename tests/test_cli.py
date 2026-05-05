from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path

from contextopt.config import load_config


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
    config = tmp_path / ".codeprism" / "config.toml"
    assert config.read_text(encoding="utf-8") == (
        'max_file_bytes = 500000\nignore = ["node_modules", ".git", "dist", "build", ".next"]\n'
    )
    assert not (tmp_path / ".contextopt").exists()


def test_load_config_falls_back_to_legacy_contextopt_config(tmp_path: Path):
    legacy_dir = tmp_path / ".contextopt"
    legacy_dir.mkdir()
    (legacy_dir / "config.toml").write_text(
        'max_file_bytes = 123\nignore = ["generated"]\n',
        encoding="utf-8",
    )

    config = load_config(tmp_path)

    assert config.max_file_bytes == 123
    assert config.ignore == ["generated"]


def test_export_json_uses_json_default_output(tmp_path: Path):
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path)],
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
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert export_result.returncode == 0, export_result.stderr
    assert (tmp_path / ".codeprism" / "context.db").exists()
    assert (tmp_path / ".codeprism" / "context-pack.json").exists()
    assert not (tmp_path / ".codeprism" / "context-pack.md").exists()
    payload = json.loads((tmp_path / ".codeprism" / "context-pack.json").read_text())
    assert payload["meta"]["schema_version"] == 1


def test_export_default_reads_legacy_contextopt_db(tmp_path: Path):
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    legacy_db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "map",
            str(tmp_path),
            "--db",
            str(legacy_db),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    export_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "export", "--format", "json"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert export_result.returncode == 0, export_result.stderr
    assert (tmp_path / ".codeprism" / "context-pack.json").exists()


def test_activity_normalize_command_writes_safe_payload(tmp_path: Path):
    activity = tmp_path / "activity.jsonl"
    activity.write_text(
        '{"agent_id":"codex","event":"file_read","path":"app.py","estimated_tokens":42}\nbad row\n',
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


def test_get_warns_when_map_is_stale(tmp_path: Path):
    app = tmp_path / "app.py"
    app.write_text("def target():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr
    app.write_text("def target():\n    return 2\n", encoding="utf-8")

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
    assert "Warning: CodePrism map is stale" in result.stderr
    assert "1 changed" in result.stderr


def test_get_strict_fresh_fails_when_map_is_stale(tmp_path: Path):
    app = tmp_path / "app.py"
    app.write_text("def target():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr
    app.write_text("def target():\n    return 2\n", encoding="utf-8")

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
            "--strict-fresh",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 3
    assert "Error: CodePrism map is stale" in result.stderr
    assert "Use --refresh" in result.stderr
    assert result.stdout == ""


def test_read_map_mode_prints_file_metadata_without_source_body(tmp_path: Path):
    (tmp_path / "app.py").write_text(
        "def target():\n    return 'body should stay hidden'\n",
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
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / ".codeprism" / "live-trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert trace_rows[-1]["event"] == "read_map"
    assert trace_rows[-1]["path"] == "app.py"
    assert trace_rows[-1]["estimated_tokens"] > 0


def test_read_refresh_updates_stale_map_before_signatures(tmp_path: Path):
    app = tmp_path / "app.py"
    app.write_text("def old_name():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr
    app.write_text("def new_name():\n    return 2\n", encoding="utf-8")

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
            "--refresh",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "new_name" in result.stdout
    assert "old_name" not in result.stdout
    assert "CodePrism map is stale" not in result.stderr


def test_map_command_fails_cleanly_when_lock_is_held(tmp_path: Path):
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    codeprism = tmp_path / ".codeprism"
    codeprism.mkdir()
    (codeprism / "context.lock").write_text('{"reason":"test"}', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "map",
            str(tmp_path),
            "--lock-timeout",
            "0",
            "--lock-stale-after",
            "60",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert "CodePrism map is locked" in result.stderr
    assert not (tmp_path / ".codeprism" / "context.db").exists()


def test_watch_once_refreshes_stale_map(tmp_path: Path):
    app = tmp_path / "app.py"
    app.write_text("def old_name():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path), "--db", str(db)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr
    app.write_text("def new_name():\n    return 2\n", encoding="utf-8")

    watch_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "watch",
            str(tmp_path),
            "--db",
            str(db),
            "--once",
            "--interval",
            "0",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert watch_result.returncode == 0, watch_result.stderr
    assert "Refreshed CodePrism map" in watch_result.stdout

    read_result = subprocess.run(
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
            "--strict-fresh",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert read_result.returncode == 0, read_result.stderr
    assert "new_name" in read_result.stdout
    assert "old_name" not in read_result.stdout


def test_read_refresh_fails_cleanly_when_map_is_locked(tmp_path: Path):
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    db = tmp_path / ".contextopt" / "context.db"
    db.parent.mkdir()
    (db.parent / "context.lock").write_text('{"reason":"test"}', encoding="utf-8")

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
            "--refresh",
            "--lock-timeout",
            "0",
            "--lock-stale-after",
            "60",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 4
    assert "CodePrism map is locked" in result.stderr
    assert "Traceback" not in result.stderr


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


def test_gain_command_appends_live_trace_freshness_metadata(tmp_path: Path):
    app = tmp_path / "app.py"
    app.write_text("def main():\n    return 1\n", encoding="utf-8")
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr

    result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "gain", str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / ".codeprism" / "live-trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    gain_event = trace_rows[-1]
    assert gain_event["event"] == "gain"
    assert gain_event["meta"]["freshness_status"] == "current"
    assert gain_event["meta"]["changed_files"] == 0
    assert gain_event["meta"]["source_to_context_saved_percent"] >= 0


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
    assert (tmp_path / ".codeprism" / "slices" / "billing-webhook.md").exists()
    assert (tmp_path / ".codeprism" / "slices" / "billing-webhook.brief.md").exists()
    assert (tmp_path / ".codeprism" / "slices" / "billing-webhook.json").exists()
    assert "Read this slice brief first" in result.stdout
    assert "Source estimate:" in result.stdout
    assert "Slice estimate:" in result.stdout
    assert "Estimated saving:" in result.stdout
    assert "Included:" in result.stdout


def test_prime_writes_and_promotes_compaction_safe_brief(tmp_path: Path):
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
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    brief = tmp_path / ".codeprism" / "slices" / "billing-webhook.brief.md"
    assert brief.exists()
    assert "Brief:" in result.stdout
    assert "Read this slice brief first" in result.stdout
    trace_rows = [
        json.loads(line)
        for line in (tmp_path / ".codeprism" / "live-trace.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert trace_rows[-1]["meta"]["brief_path"].endswith("billing-webhook.brief.md")


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
    assert (project / ".codeprism" / "context.db").exists()
    assert (project / ".codeprism" / "slices" / "target-symbol.md").exists()
    assert not (project / ".contextopt").exists()
    assert not (outside / ".codeprism").exists()
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
    slice_text = (project / ".codeprism" / "slices" / "unrelated-query.md").read_text(
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
    trace = artifacts / "live-trace.jsonl"
    assert trace.exists()
    trace_rows = [json.loads(line) for line in trace.read_text(encoding="utf-8").splitlines()]
    assert trace_rows[-1]["event"] == "prime"
    assert trace_rows[-1]["agent_id"] == "CodePrism"
    assert trace_rows[-1]["path"] == "app.py"
    assert trace_rows[-1]["node_id"] == "function::app.py::target_symbol"
    assert trace_rows[-1]["estimated_tokens"] > 0
    assert trace_rows[-1]["meta"]["query"] == "target symbol"
    assert trace_rows[-1]["meta"]["slice_path"].endswith("target-symbol.md")
    assert not (project / ".codeprism").exists()
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
    assert not (project / ".codeprism").exists()
    assert not (project / ".contextopt").exists()


def test_prime_refuses_unsafe_large_slice_budget(tmp_path: Path):
    (tmp_path / "app.py").write_text("def target_symbol():\n    return 1\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "prime",
            "target symbol",
            "--root",
            str(tmp_path),
            "--max-tokens",
            "50000",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "unsafe slice budget" in result.stderr.lower()
    assert not (tmp_path / ".codeprism" / "context.db").exists()


def test_slice_refuses_uncapped_budget_without_explicit_override(tmp_path: Path):
    (tmp_path / "app.py").write_text("def target_symbol():\n    return 1\n", encoding="utf-8")
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path)],
        cwd=tmp_path,
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
            "slice",
            "target symbol",
            "--max-tokens",
            "0",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "unsafe slice budget" in result.stderr.lower()


def test_visualize_auto_loads_live_trace_when_present(tmp_path: Path):
    (tmp_path / "app.py").write_text("def main():\n    return 1\n", encoding="utf-8")
    map_result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "map", str(tmp_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert map_result.returncode == 0, map_result.stderr
    trace = tmp_path / ".codeprism" / "live-trace.jsonl"
    trace.write_text(
        '{"agent_id":"CodePrism","event":"prime","path":"app.py","estimated_tokens":20}\n',
        encoding="utf-8",
    )
    outdir = tmp_path / ".codeprism" / "visual"

    result = subprocess.run(
        [sys.executable, "-m", "contextopt.cli", "visualize", "--outdir", str(outdir)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads((outdir / "activity-stream.json").read_text(encoding="utf-8"))
    assert payload["summary"]["event_count"] == 1
    assert payload["events"][0]["event"] == "prime"
