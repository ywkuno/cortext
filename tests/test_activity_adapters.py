import json
import subprocess
import sys
from pathlib import Path

from contextopt.activity import parse_activity_stream
from contextopt.activity_adapters import adapt_tool_jsonl


def test_tool_event_adapter_emits_normalized_jsonl(tmp_path: Path) -> None:
    raw = tmp_path / "tool-events.jsonl"
    raw.write_text(
        '{"ts":"2026-05-03T03:00:00Z","agent":"codex","type":"file_read",'
        '"file":"src/app.py","tokens":80,"duration_ms":120}\n'
        "not json\n",
        encoding="utf-8",
    )
    out = tmp_path / "activity.jsonl"

    result = adapt_tool_jsonl(raw, out)
    events, warnings = parse_activity_stream(out)

    assert result["event_count"] == 1
    assert result["warning_count"] == 1
    assert warnings == []
    assert events[0]["agent_id"] == "codex"
    assert events[0]["event"] == "file_read"
    assert events[0]["path"] == "src/app.py"
    assert events[0]["node_id"] == "file::src/app.py"
    assert events[0]["estimated_tokens"] == 80
    assert events[0]["duration_ms"] == 120


def test_activity_adapt_tool_log_command(tmp_path: Path) -> None:
    raw = tmp_path / "tool-events.jsonl"
    raw.write_text(
        '{"agent_id":"cortext","event":"context_pack_generated","path":"README.md"}\n',
        encoding="utf-8",
    )
    out = tmp_path / "activity.jsonl"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "activity",
            "adapt-tool-log",
            str(raw),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    row = json.loads(out.read_text(encoding="utf-8"))
    assert row["agent_id"] == "cortext"
    assert row["event"] == "context_pack_generated"
    assert row["node_id"] == "file::README.md"
    assert "1 events" in result.stdout
