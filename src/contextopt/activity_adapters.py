from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _string_value(raw: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _number_value(raw: dict[str, Any], *keys: str) -> int | float | None:
    for key in keys:
        value = raw.get(key)
        if isinstance(value, int | float):
            return value
    return None


def adapt_tool_event(raw: dict[str, Any]) -> dict[str, Any]:
    path = _string_value(raw, "path", "file", "target_path")
    node_id = _string_value(raw, "node_id")
    if not node_id and path:
        normalized_path = path.replace("\\", "/")
        node_id = f"file::{normalized_path}"
    event = _string_value(raw, "event", "type", "tool_name") or "tool_event"
    meta = raw.get("meta")
    if not isinstance(meta, dict):
        meta = {}
    if "tool_name" in raw and "tool_name" not in meta:
        meta = {**meta, "tool_name": raw["tool_name"]}
    return {
        "ts": _string_value(raw, "ts", "timestamp", "time") or "",
        "run_id": _string_value(raw, "run_id", "session_id", "task_id") or "",
        "agent_id": _string_value(raw, "agent_id", "agent", "actor") or "",
        "event": event,
        "node_id": node_id,
        "from_node_id": _string_value(raw, "from_node_id"),
        "to_node_id": _string_value(raw, "to_node_id") or node_id,
        "path": path,
        "duration_ms": _number_value(raw, "duration_ms", "elapsed_ms"),
        "estimated_tokens": _number_value(raw, "estimated_tokens", "tokens"),
        "actual_tokens": _number_value(raw, "actual_tokens"),
        "status": _string_value(raw, "status") or "",
        "severity": _string_value(raw, "severity", "level") or "",
        "meta": meta,
    }


def adapt_tool_jsonl(input_path: Path, out_path: Path) -> dict[str, int]:
    event_count = 0
    warning_count = 0
    rows: list[str] = []
    for line_number, line in enumerate(
        input_path.read_text(encoding="utf-8", errors="replace").splitlines(),
        start=1,
    ):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError:
            warning_count += 1
            continue
        if not isinstance(raw, dict):
            warning_count += 1
            continue
        event = adapt_tool_event(raw)
        event["meta"] = {**event.get("meta", {}), "source_line": line_number}
        rows.append(json.dumps(event, sort_keys=True))
        event_count += 1
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")
    return {"event_count": event_count, "warning_count": warning_count}
