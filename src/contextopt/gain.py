from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .graph import GraphStore
from .stats import compute_stats


def _percent_saved(before: int, after: int) -> float:
    if not before:
        return 0.0
    return max(round((1 - (after / before)) * 100, 2), 0.0)


def _saved_tokens(before: int, after: int) -> int:
    return max(before - after, 0)


def _latest_slice_manifest(root: Path) -> Path | None:
    slice_dir = root.resolve() / ".contextopt" / "slices"
    if not slice_dir.exists():
        return None
    manifests = [path for path in slice_dir.glob("*.json") if path.is_file()]
    if not manifests:
        return None
    return max(manifests, key=lambda path: path.stat().st_mtime_ns)


def _load_slice_manifest(root: Path, slice_path: Path | None) -> dict[str, Any] | None:
    manifest_path = slice_path or _latest_slice_manifest(root)
    if manifest_path is None:
        return None
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "path": str(manifest_path),
            "error": "could not read slice manifest",
        }
    if not isinstance(payload, dict):
        return {
            "path": str(manifest_path),
            "error": "slice manifest is not a JSON object",
        }
    payload["path"] = str(manifest_path)
    return payload


def compute_gain(
    root: Path,
    store: GraphStore,
    *,
    slice_path: Path | None = None,
    max_file_bytes: int = 500_000,
    ignore_patterns: list[str] | None = None,
) -> dict[str, Any]:
    stats = compute_stats(
        root,
        store,
        max_file_bytes=max_file_bytes,
        ignore_patterns=ignore_patterns,
    )
    source_tokens = int(stats["source_estimated_tokens"])
    context_tokens = int(stats["context_pack_estimated_tokens"])
    graph_tokens = int(stats["graph_estimated_tokens"])
    slice_manifest = _load_slice_manifest(root, slice_path)

    gain: dict[str, Any] = {
        "root": stats["root"],
        "source_estimated_tokens": source_tokens,
        "graph_estimated_tokens": graph_tokens,
        "context_pack_estimated_tokens": context_tokens,
        "source_to_context_saved_tokens": _saved_tokens(source_tokens, context_tokens),
        "source_to_context_saved_percent": _percent_saved(source_tokens, context_tokens),
        "source_to_graph_saved_tokens": _saved_tokens(source_tokens, graph_tokens),
        "source_to_graph_saved_percent": _percent_saved(source_tokens, graph_tokens),
        "freshness": stats["freshness"],
        "slice": slice_manifest,
    }
    if slice_manifest and "error" not in slice_manifest:
        slice_tokens = int(slice_manifest.get("estimated_tokens") or 0)
        full_context_tokens = int(slice_manifest.get("full_context_estimated_tokens") or 0)
        gain.update(
            {
                "slice_estimated_tokens": slice_tokens,
                "slice_full_context_estimated_tokens": full_context_tokens,
                "source_to_slice_saved_tokens": _saved_tokens(source_tokens, slice_tokens),
                "source_to_slice_saved_percent": _percent_saved(source_tokens, slice_tokens),
                "context_to_slice_saved_tokens": _saved_tokens(full_context_tokens, slice_tokens),
                "context_to_slice_saved_percent": _percent_saved(full_context_tokens, slice_tokens),
            }
        )
    return gain


def _line_count(label: str, values: list[str]) -> str:
    return f"- {label}: {len(values)}"


def format_gain(gain: dict[str, Any]) -> str:
    freshness = gain["freshness"]
    lines = [
        "# CodePrism Gain",
        "",
        f"- Root: `{gain['root']}`",
        f"- Source estimated tokens: {gain['source_estimated_tokens']}",
        f"- Graph estimated tokens: {gain['graph_estimated_tokens']}",
        f"- Context pack estimated tokens: {gain['context_pack_estimated_tokens']}",
        (
            "- Source -> context pack saving: "
            f"{gain['source_to_context_saved_tokens']} tokens "
            f"({gain['source_to_context_saved_percent']:.2f}%)"
        ),
        (
            "- Source -> graph saving: "
            f"{gain['source_to_graph_saved_tokens']} tokens "
            f"({gain['source_to_graph_saved_percent']:.2f}%)"
        ),
        f"- Map status: {freshness['status']}",
        f"- Checked files: {freshness['checked_files']}",
        _line_count("Changed files", freshness["changed_files"]),
        _line_count("New files", freshness["new_files"]),
        _line_count("Deleted files", freshness["deleted_files"]),
    ]
    if freshness["status"] == "stale":
        lines.append("- Recommendation: run `codeprism map .` or `codeprism prime <task>` before trusting old graph output.")
    slice_manifest = gain.get("slice")
    if slice_manifest:
        lines += ["", "## Slice", ""]
        if "error" in slice_manifest:
            lines.append(f"- Slice: `{slice_manifest['path']}`")
            lines.append(f"- Warning: {slice_manifest['error']}")
        else:
            lines += [
                f"- Slice: `{slice_manifest['path']}`",
                f"- Query: `{slice_manifest.get('query', '')}`",
                f"- Slice estimated tokens: {gain['slice_estimated_tokens']}",
                (
                    "- Source -> slice saving: "
                    f"{gain['source_to_slice_saved_tokens']} tokens "
                    f"({gain['source_to_slice_saved_percent']:.2f}%)"
                ),
                (
                    "- Full context -> slice saving: "
                    f"{gain['context_to_slice_saved_tokens']} tokens "
                    f"({gain['context_to_slice_saved_percent']:.2f}%)"
                ),
            ]
    return "\n".join(lines) + "\n"
