from __future__ import annotations


def normalize_path(path: str | None) -> str:
    if not path:
        return ""
    return str(path).replace("\\", "/").strip("/")


def stable_node_id(kind: str, path: str | None, name: str | None) -> str:
    normalized_kind = (kind or "unknown").strip() or "unknown"
    normalized_path = normalize_path(path)
    normalized_name = str(name or normalized_path or normalized_kind)

    if normalized_kind == "folder":
        return f"folder::{normalized_path or '.'}"
    if normalized_kind in {"file", "doc"}:
        return f"{normalized_kind}::{normalized_path}"
    if normalized_kind == "route":
        return f"route::{normalized_name}"
    if normalized_kind == "module":
        return f"module::{normalized_name}"
    return f"{normalized_kind}::{normalized_path}::{normalized_name}"
