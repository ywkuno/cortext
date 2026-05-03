from __future__ import annotations

from pathlib import Path

from ..graph import GraphStore


def _exported_count(selected: int, total: int) -> str:
    return str(selected) if selected == total else f"{selected} of {total}"


def export_markdown(
    store: GraphStore,
    out: Path,
    *,
    max_nodes: int = 5000,
    max_edges: int = 5000,
    max_chars: int | None = None,
) -> None:
    run = store.rows("SELECT * FROM runs ORDER BY id DESC LIMIT 1")
    run_filter = "WHERE run_id = ?" if run else ""
    params = (run[0]["id"],) if run else ()
    total_nodes = store.rows(f"SELECT count(*) AS count FROM nodes {run_filter}", params)[0][
        "count"
    ]
    total_edges = store.rows(f"SELECT count(*) AS count FROM edges {run_filter}", params)[0][
        "count"
    ]
    nodes = store.rows(
        f"SELECT * FROM nodes {run_filter} ORDER BY kind, path, name LIMIT ?",
        (*params, max_nodes),
    )
    edges = store.rows(
        f"SELECT * FROM edges {run_filter} ORDER BY kind, source, target LIMIT ?",
        (*params, max_edges),
    )
    truncated = len(nodes) < total_nodes or len(edges) < total_edges
    lines: list[str] = ["# Context Pack", ""]
    if run:
        lines += [f"- Root: `{run[0]['root']}`", f"- Created: `{run[0]['created_at']}`"]
    lines += [
        f"- Nodes exported: {_exported_count(len(nodes), total_nodes)}",
        f"- Edges exported: {_exported_count(len(edges), total_edges)}",
        "",
        "## File and Symbol Index",
        "",
    ]
    current_kind = None
    for row in nodes:
        if row["kind"] != current_kind:
            current_kind = row["kind"]
            lines += [f"### {current_kind}", ""]
        loc = f":L{row['start_line']}" if row["start_line"] else ""
        lines.append(f"- `{row['path']}{loc}` — **{row['name']}**")
    lines += ["", "## Relationship Edges", ""]
    for row in edges:
        lines.append(f"- `{row['source']}` --{row['kind']}--> `{row['target']}`")
    if truncated:
        lines += ["", "Budget note: output truncated by export limits."]
    lines += [
        "",
        "## Agent Usage",
        "",
        "Start with this pack, then read only the files related to the user's task.",
    ]
    text = "\n".join(lines)
    if max_chars is not None and len(text) > max_chars:
        truncated_text = text[: max(0, max_chars - 75)].rstrip()
        text = f"{truncated_text}\n\nBudget note: output truncated by character limit."
    out.write_text(text, encoding="utf-8")
