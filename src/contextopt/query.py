from __future__ import annotations

import re

from .graph import GraphStore


KIND_WEIGHTS = {
    "route": 80,
    "class": 70,
    "function": 65,
    "heading": 45,
    "doc": 35,
    "file": 25,
}


def _variants(token: str) -> set[str]:
    variants = {token}
    if len(token) > 3 and token.endswith("s"):
        variants.add(token[:-1])
    if len(token) > 4 and token.endswith("ed"):
        variants.add(token[:-1])
        variants.add(token[:-2])
    if len(token) > 5 and token.endswith("ing"):
        variants.add(token[:-3])
        variants.add(f"{token[:-3]}e")
    return {variant for variant in variants if len(variant) >= 2}


def query_terms(text: str) -> list[str]:
    terms: set[str] = set()
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        terms.update(_variants(token))
    return sorted(terms, key=lambda item: (-len(item), item))


def _score(row: dict, phrase: str, terms: list[str]) -> int:
    name = row["name"].lower()
    path = row["path"].lower()
    meta = row.get("meta_json", "").lower()
    haystack = f"{name} {path} {meta}"
    score = KIND_WEIGHTS.get(row["kind"], 10)
    if name == phrase:
        score += 1000
    elif name.startswith(phrase):
        score += 300
    elif phrase in name:
        score += 150
    if path == phrase:
        score += 500
    elif path.endswith(f"/{phrase}") or path.startswith(phrase):
        score += 180
    elif phrase in path:
        score += 90
    if phrase in meta:
        score += 20
    matched_terms = 0
    for term in terms:
        if term not in haystack:
            continue
        matched_terms += 1
        if term == name:
            score += 180
        elif name.startswith(term):
            score += 90
        elif term in name:
            score += 60
        if term in path:
            score += 35
        if term in meta:
            score += 10
    if matched_terms:
        score += matched_terms * 25
    if row["start_line"] is not None:
        score += 5
    return score


def query_graph(store: GraphStore, text: str, limit: int = 20) -> list[dict]:
    phrase = text.lower().strip()
    terms = query_terms(text)
    if not phrase or not terms:
        return []
    clauses = []
    params: list[str] = []
    for term in terms:
        clauses.append("(lower(path) LIKE ? OR lower(name) LIKE ? OR lower(meta_json) LIKE ?)")
        needle = f"%{term}%"
        params.extend([needle, needle, needle])
    rows = store.rows(
        f"""
        SELECT kind, path, name, start_line, meta_json FROM nodes
        WHERE {" OR ".join(clauses)}
    """,
        params,
    )
    ranked = [dict(row) for row in rows]
    for row in ranked:
        row["score"] = _score(row, phrase, terms)
    return sorted(ranked, key=lambda row: (-row["score"], row["path"], row["name"]))[:limit]
