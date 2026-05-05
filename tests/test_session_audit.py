from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from contextopt.session_audit import audit_session, format_session_audit


def _write_jsonl(path: Path, rows: list[object | str]) -> None:
    lines = []
    for row in rows:
        if isinstance(row, str):
            lines.append(row)
        else:
            lines.append(json.dumps(row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_audit_session_reports_codeprism_usage_and_savings(tmp_path: Path) -> None:
    log = tmp_path / "rollout-test.jsonl"
    _write_jsonl(
        log,
        [
            {"type": "response_item", "item": {"arguments": {"command": "rg -n TODO src"}}},
            {
                "type": "response_item",
                "item": {
                    "arguments": json.dumps(
                        {"command": 'codeprism prime "billing flow" --changed'}
                    )
                },
            },
            {
                "type": "response_item",
                "item": {
                    "output": (
                        "Source estimate: 100,000 tokens.\n"
                        "Slice estimate: 8,000 tokens.\n"
                        "Estimated saving: 92.00% vs source.\n"
                    )
                },
                "usage": {"input_tokens": 1000, "output_tokens": 50},
            },
        ],
    )

    audit = audit_session(log)
    text = format_session_audit(audit)

    assert audit["shell_commands"] == 2
    assert audit["codeprism_commands"] == 1
    assert audit["codeprism_subcommands"] == {"prime": 1}
    assert audit["search_commands"] == 1
    assert audit["savings_observed"][0]["source_to_slice_saved_percent"] == 92.0
    assert audit["token_usage"]["input_tokens"] == 1000
    assert "Best observed saving: 92.00% source-to-slice" in text


def test_audit_session_skips_malformed_rows_and_flags_large_outputs(tmp_path: Path) -> None:
    log = tmp_path / "rollout-test.jsonl"
    _write_jsonl(
        log,
        [
            "{not-json",
            {"type": "response_item", "item": {"arguments": {"command": "cat src/app.py"}}},
            {"type": "response_item", "item": {"output": "x" * 80}},
            {"type": "event_msg", "message": "Context automatically compacted"},
        ],
    )

    audit = audit_session(log, large_output_chars=64)

    assert audit["malformed_rows"] == 1
    assert audit["raw_read_commands"] == 1
    assert audit["large_outputs"] == 1
    assert audit["compaction_mentions"] == 1
    assert audit["verdict"] == "missing-codeprism"


def test_audit_session_cli_writes_json_report(tmp_path: Path) -> None:
    log = tmp_path / "rollout-019-test.jsonl"
    out = tmp_path / "audit.json"
    _write_jsonl(
        log,
        [
            {
                "type": "response_item",
                "item": {"arguments": {"command": "python -m contextopt.cli read README.md"}},
            }
        ],
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "contextopt.cli",
            "audit-session",
            str(log),
            "--format",
            "json",
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Wrote session audit" in result.stdout
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["codeprism_subcommands"] == {"read": 1}


def test_audit_session_resolves_codex_session_id(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    session_dir = codex_home / "sessions" / "2026" / "05"
    session_dir.mkdir(parents=True)
    log = session_dir / "rollout-2026-05-05T12-00-00-019abc-session.jsonl"
    _write_jsonl(
        log,
        [{"type": "response_item", "item": {"arguments": {"command": "codeprism gain"}}}],
    )

    audit = audit_session("019abc-session", codex_home=codex_home)

    assert audit["session_path"] == str(log.resolve())
    assert audit["codeprism_subcommands"] == {"gain": 1}
