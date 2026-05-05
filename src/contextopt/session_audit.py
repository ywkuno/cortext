from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


class SessionAuditError(Exception):
    """Raised when a session audit input cannot be resolved or read."""


CODEPRISM_COMMAND_RE = re.compile(
    r"\b(?:codeprism|contextopt)(?:\.exe)?\s+([A-Za-z0-9_-]+)"
    r"|\bpython(?:\.\w+)?\s+-m\s+contextopt\.cli\s+([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
RAW_READ_RE = re.compile(r"\b(Get-Content|gc|type|cat|sed\s+-n|nl\s+-ba)\b", re.IGNORECASE)
SEARCH_RE = re.compile(r"\b(rg|grep|findstr|Select-String)\b", re.IGNORECASE)
COMPACTION_RE = re.compile(r"(automatically compact|context automatically compact|compacting context)", re.IGNORECASE)
SOURCE_RE = re.compile(r"Source estimate:\s*([\d,.]+)\s*tokens", re.IGNORECASE)
SLICE_RE = re.compile(r"Slice estimate:\s*([\d,.]+)\s*tokens", re.IGNORECASE)
SAVING_RE = re.compile(r"Estimated saving:\s*([\d.]+)%\s*vs source", re.IGNORECASE)
GAIN_SAVING_RE = re.compile(r"Source\s*->\s*slice:.*?([\d.]+)%", re.IGNORECASE)
COMMAND_KEYS = {"command", "cmd", "script"}
ARGUMENT_KEYS = {"arguments", "args", "parameters", "input"}
TOKEN_KEYS = {
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "total_tokens",
    "prompt_tokens",
    "completion_tokens",
}


def resolve_session_path(session: str | Path, codex_home: Path | None = None) -> Path:
    value = Path(session)
    if value.exists():
        return value.resolve()
    if value.suffix == ".jsonl" and value.parent != Path("."):
        raise SessionAuditError(f"Session log not found: {value}")

    home = codex_home or Path.home() / ".codex"
    sessions_dir = home / "sessions"
    if not sessions_dir.exists():
        raise SessionAuditError(f"Codex sessions directory not found: {sessions_dir}")

    matches = sorted(
        sessions_dir.rglob(f"*{session}*.jsonl"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not matches:
        raise SessionAuditError(f"No Codex session log matched {session!r} under {sessions_dir}")
    return matches[0].resolve()


def audit_session(
    session: str | Path,
    *,
    codex_home: Path | None = None,
    large_output_chars: int = 32_000,
) -> dict[str, Any]:
    path = resolve_session_path(session, codex_home=codex_home)
    rows = 0
    malformed_rows = 0
    shell_commands: list[str] = []
    codeprism_commands: list[str] = []
    codeprism_subcommands: Counter[str] = Counter()
    first_shell_row: int | None = None
    first_codeprism_row: int | None = None
    raw_read_commands = 0
    search_commands = 0
    compaction_mentions = 0
    large_outputs = 0
    max_output_chars = 0
    savings: list[dict[str, Any]] = []
    token_usage: dict[str, int] = {}

    for row_number, row in _iter_jsonl(path):
        rows += 1
        if row is None:
            malformed_rows += 1
            continue

        commands = _extract_commands(row)
        for command in commands:
            shell_commands.append(command)
            if first_shell_row is None:
                first_shell_row = row_number
            subcommands = _codeprism_subcommands(command)
            if subcommands:
                codeprism_commands.append(command)
                if first_codeprism_row is None:
                    first_codeprism_row = row_number
                codeprism_subcommands.update(subcommands)
                continue
            if RAW_READ_RE.search(command):
                raw_read_commands += 1
            if SEARCH_RE.search(command):
                search_commands += 1

        text_parts = list(_strings(row))
        text = "\n".join(text_parts)
        if COMPACTION_RE.search(text):
            compaction_mentions += 1
        for value in text_parts:
            length = len(value)
            if length >= large_output_chars:
                large_outputs += 1
                max_output_chars = max(max_output_chars, length)
        savings.extend(_extract_savings(text, row_number))
        for key, value in _extract_token_usage(row).items():
            token_usage[key] = max(token_usage.get(key, 0), value)

    shell_count = len(shell_commands)
    first_codeprism_command_index = (
        _command_index(shell_commands, codeprism_commands[0]) if codeprism_commands else None
    )
    codeprism_command_count = len(codeprism_commands)
    verdict = _verdict(
        shell_count=shell_count,
        codeprism_command_count=codeprism_command_count,
        first_codeprism_command_index=first_codeprism_command_index,
        raw_read_commands=raw_read_commands,
        search_commands=search_commands,
        compaction_mentions=compaction_mentions,
        large_outputs=large_outputs,
    )
    return {
        "schema_version": 1,
        "session_path": str(path),
        "rows": rows,
        "malformed_rows": malformed_rows,
        "shell_commands": shell_count,
        "codeprism_commands": codeprism_command_count,
        "codeprism_subcommands": dict(sorted(codeprism_subcommands.items())),
        "first_shell_row": first_shell_row,
        "first_codeprism_row": first_codeprism_row,
        "first_codeprism_command_index": first_codeprism_command_index,
        "raw_read_commands": raw_read_commands,
        "search_commands": search_commands,
        "compaction_mentions": compaction_mentions,
        "large_outputs": large_outputs,
        "max_output_chars": max_output_chars,
        "savings_observed": savings,
        "token_usage": dict(sorted(token_usage.items())),
        "verdict": verdict,
        "recommendations": _recommendations(
            verdict=verdict,
            codeprism_command_count=codeprism_command_count,
            raw_read_commands=raw_read_commands,
            search_commands=search_commands,
            compaction_mentions=compaction_mentions,
            large_outputs=large_outputs,
            savings=savings,
        ),
        "note": "Local audit only. Token counts and savings are estimates extracted from session text.",
    }


def format_session_audit(audit: dict[str, Any]) -> str:
    subcommands = audit.get("codeprism_subcommands") or {}
    subcommand_text = ", ".join(f"{name}={count}" for name, count in subcommands.items()) or "none"
    savings = audit.get("savings_observed") or []
    savings_text = "none"
    if savings:
        best = max(savings, key=lambda item: item.get("source_to_slice_saved_percent") or 0)
        percent = best.get("source_to_slice_saved_percent")
        source = best.get("source_estimated_tokens")
        slice_tokens = best.get("slice_estimated_tokens")
        savings_text = f"{percent:.2f}% source-to-slice"
        if source and slice_tokens:
            savings_text += f" ({source:,} -> {slice_tokens:,} estimated tokens)"

    lines = [
        "# CodePrism Session Audit",
        "",
        f"Session: {audit['session_path']}",
        f"Verdict: {audit['verdict']}",
        "",
        "## Signals",
        "",
        f"- Rows parsed: {audit['rows']} ({audit['malformed_rows']} malformed)",
        f"- Shell commands: {audit['shell_commands']}",
        f"- CodePrism commands: {audit['codeprism_commands']} ({subcommand_text})",
        f"- First CodePrism command index: {audit.get('first_codeprism_command_index') or 'none'}",
        f"- Raw read commands: {audit['raw_read_commands']}",
        f"- Search commands: {audit['search_commands']}",
        f"- Compaction mentions: {audit['compaction_mentions']}",
        f"- Large outputs: {audit['large_outputs']} (max {audit['max_output_chars']} chars)",
        f"- Best observed saving: {savings_text}",
    ]
    token_usage = audit.get("token_usage") or {}
    if token_usage:
        usage_text = ", ".join(f"{key}={value:,}" for key, value in token_usage.items())
        lines.append(f"- Max reported token counters: {usage_text}")
    lines.extend(["", "## Recommendations", ""])
    for recommendation in audit.get("recommendations") or ["No recommendations."]:
        lines.append(f"- {recommendation}")
    lines.append("")
    return "\n".join(lines)


def _iter_jsonl(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        for row_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield row_number, json.loads(line)
            except json.JSONDecodeError:
                yield row_number, None


def _extract_commands(value: Any) -> list[str]:
    commands: list[str] = []

    def walk(item: Any) -> None:
        if isinstance(item, dict):
            for key, nested in item.items():
                key_lower = str(key).lower()
                if key_lower in COMMAND_KEYS and isinstance(nested, str):
                    commands.append(nested)
                elif key_lower in ARGUMENT_KEYS:
                    parsed = _parse_jsonish(nested)
                    if parsed is not nested:
                        walk(parsed)
                    elif isinstance(nested, dict):
                        walk(nested)
                elif isinstance(nested, dict | list):
                    walk(nested)
        elif isinstance(item, list):
            for nested in item:
                walk(nested)

    walk(value)
    return list(dict.fromkeys(commands))


def _parse_jsonish(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return value


def _codeprism_subcommands(command: str) -> list[str]:
    subcommands: list[str] = []
    for match in CODEPRISM_COMMAND_RE.finditer(command):
        subcommand = match.group(1) or match.group(2)
        if subcommand:
            subcommands.append(subcommand.lower())
    return subcommands


def _strings(value: Any) -> Any:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for nested in value.values():
            yield from _strings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from _strings(nested)


def _extract_savings(text: str, row_number: int) -> list[dict[str, Any]]:
    source = _int_match(SOURCE_RE.search(text))
    slice_tokens = _int_match(SLICE_RE.search(text))
    percent = _float_match(SAVING_RE.search(text)) or _float_match(GAIN_SAVING_RE.search(text))
    if percent is None and source and slice_tokens and source > 0:
        percent = round(((source - slice_tokens) / source) * 100, 2)
    if percent is None:
        return []
    return [
        {
            "row": row_number,
            "source_estimated_tokens": source,
            "slice_estimated_tokens": slice_tokens,
            "source_to_slice_saved_percent": percent,
        }
    ]


def _extract_token_usage(value: Any) -> dict[str, int]:
    usage: dict[str, int] = {}
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in TOKEN_KEYS and isinstance(nested, int | float):
                usage[key] = max(usage.get(key, 0), int(nested))
            else:
                for nested_key, nested_value in _extract_token_usage(nested).items():
                    usage[nested_key] = max(usage.get(nested_key, 0), nested_value)
    elif isinstance(value, list):
        for nested in value:
            for nested_key, nested_value in _extract_token_usage(nested).items():
                usage[nested_key] = max(usage.get(nested_key, 0), nested_value)
    return usage


def _int_match(match: re.Match[str] | None) -> int | None:
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def _float_match(match: re.Match[str] | None) -> float | None:
    if not match:
        return None
    return float(match.group(1))


def _command_index(shell_commands: list[str], needle: str) -> int | None:
    for index, command in enumerate(shell_commands, start=1):
        if command == needle:
            return index
    return None


def _verdict(
    *,
    shell_count: int,
    codeprism_command_count: int,
    first_codeprism_command_index: int | None,
    raw_read_commands: int,
    search_commands: int,
    compaction_mentions: int,
    large_outputs: int,
) -> str:
    if codeprism_command_count == 0:
        return "missing-codeprism"
    late_threshold = max(6, int(shell_count * 0.4))
    if first_codeprism_command_index and first_codeprism_command_index > late_threshold:
        return "codeprism-used-late"
    if compaction_mentions or large_outputs:
        return "context-risk"
    if raw_read_commands + search_commands > max(8, codeprism_command_count * 4):
        return "too-many-raw-reads"
    return "healthy"


def _recommendations(
    *,
    verdict: str,
    codeprism_command_count: int,
    raw_read_commands: int,
    search_commands: int,
    compaction_mentions: int,
    large_outputs: int,
    savings: list[dict[str, Any]],
) -> list[str]:
    recommendations: list[str] = []
    if codeprism_command_count == 0:
        recommendations.append("Run `codeprism prime \"current task\" --changed` before broad file reads.")
    if verdict == "codeprism-used-late":
        recommendations.append("Move CodePrism earlier in the session, before large `rg` or raw file reads.")
    if raw_read_commands:
        recommendations.append("Replace broad raw reads with `codeprism read --mode signatures`, then `get`.")
    if search_commands:
        recommendations.append("Use `codeprism query` and `references` before repeated shell searches.")
    if compaction_mentions or large_outputs:
        recommendations.append("Keep outputs under the default slice cap and avoid dumping large command output.")
    if not savings:
        recommendations.append("Run `codeprism gain` or `codeprism benchmark` to record estimated savings.")
    if not recommendations:
        recommendations.append("Keep using CodePrism early and follow with targeted retrieval.")
    return recommendations
