from __future__ import annotations

from pathlib import Path
from typing import Any

from .graph import GraphStore
from .scanner import scan_files


def compute_freshness(
    root: Path,
    store: GraphStore,
    *,
    max_file_bytes: int = 500_000,
    ignore_patterns: list[str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    current_files = scan_files(
        root,
        max_file_bytes=max_file_bytes,
        ignore_patterns=ignore_patterns,
    )
    current_by_path = {file.rel_path: file for file in current_files}
    state_rows = store.rows("SELECT rel_path, size, mtime_ns FROM files")
    state_by_path = {str(row["rel_path"]): row for row in state_rows}

    new_files = sorted(set(current_by_path) - set(state_by_path))
    deleted_files = sorted(set(state_by_path) - set(current_by_path))
    changed_files: list[str] = []
    for rel_path in sorted(set(current_by_path) & set(state_by_path)):
        current = current_by_path[rel_path]
        state = state_by_path[rel_path]
        if int(state["size"]) != current.size or int(state["mtime_ns"]) != current.mtime_ns:
            changed_files.append(rel_path)

    run_rows = store.rows("SELECT root, created_at FROM runs ORDER BY id DESC LIMIT 1")
    latest_run = dict(run_rows[0]) if run_rows else None
    root_mismatch = bool(latest_run and str(latest_run["root"]) != str(root))
    stale_count = len(new_files) + len(changed_files) + len(deleted_files)
    status = "stale" if stale_count or root_mismatch or latest_run is None else "current"

    return {
        "status": status,
        "stale_count": stale_count,
        "checked_files": len(current_files),
        "tracked_files": len(state_rows),
        "new_files": new_files,
        "changed_files": changed_files,
        "deleted_files": deleted_files,
        "root_mismatch": root_mismatch,
        "latest_run_root": str(latest_run["root"]) if latest_run else None,
        "latest_run_created_at": str(latest_run["created_at"]) if latest_run else None,
    }
