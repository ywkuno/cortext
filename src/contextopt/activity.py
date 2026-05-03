from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ActivityEvent = dict[str, Any]


def _normalize_event(raw: dict[str, Any], line_number: int) -> ActivityEvent:
    meta = raw.get("meta", {})
    if not isinstance(meta, dict):
        meta = {"value": meta}
    duration_ms = raw.get("duration_ms")
    if not isinstance(duration_ms, int | float):
        duration_ms = None
    estimated_tokens = raw.get("estimated_tokens")
    if not isinstance(estimated_tokens, int | float):
        estimated_tokens = None
    actual_tokens = raw.get("actual_tokens")
    if not isinstance(actual_tokens, int | float):
        actual_tokens = None
    return {
        "ts": str(raw.get("ts", "")),
        "run_id": str(raw.get("run_id", "")),
        "agent_id": str(raw.get("agent_id", "")),
        "event": str(raw.get("event", "unknown")),
        "node_id": raw.get("node_id") if isinstance(raw.get("node_id"), str) else None,
        "from_node_id": raw.get("from_node_id") if isinstance(raw.get("from_node_id"), str) else None,
        "to_node_id": raw.get("to_node_id") if isinstance(raw.get("to_node_id"), str) else None,
        "path": raw.get("path") if isinstance(raw.get("path"), str) else None,
        "duration_ms": duration_ms,
        "estimated_tokens": estimated_tokens,
        "actual_tokens": actual_tokens,
        "status": raw.get("status") if isinstance(raw.get("status"), str) else "",
        "severity": raw.get("severity") if isinstance(raw.get("severity"), str) else "",
        "meta": meta,
        "line": line_number,
    }


def parse_activity_stream(path: Path) -> tuple[list[ActivityEvent], list[str]]:
    events: list[ActivityEvent] = []
    warnings: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return [], [f"Could not read activity stream {path}: {exc}"]

    for line_number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw = json.loads(stripped)
        except json.JSONDecodeError as exc:
            warnings.append(f"Line {line_number}: invalid JSON ({exc.msg})")
            continue
        if not isinstance(raw, dict):
            warnings.append(f"Line {line_number}: expected JSON object")
            continue
        events.append(_normalize_event(raw, line_number))
    return events, warnings


def summarize_activity(events: list[ActivityEvent]) -> dict[str, Any]:
    agents = sorted({str(event.get("agent_id") or "agent") for event in events})

    def numeric_sum(field: str) -> int:
        total = 0
        for event in events:
            value = event.get(field)
            if isinstance(value, int | float):
                total += int(value)
        return total

    return {
        "event_count": len(events),
        "agent_count": len(agents),
        "agents": agents,
        "estimated_tokens": numeric_sum("estimated_tokens"),
        "actual_tokens": numeric_sum("actual_tokens"),
        "duration_ms": numeric_sum("duration_ms"),
    }


def write_activity_payload(activity_path: Path, out_path: Path) -> dict[str, Any]:
    events, warnings = parse_activity_stream(activity_path)
    payload = {
        "schema_version": 1,
        "source": str(activity_path),
        "summary": summarize_activity(events),
        "events": events,
        "warnings": warnings,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
