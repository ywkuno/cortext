from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable


class GraphStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
        CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY AUTOINCREMENT, root TEXT NOT NULL, created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS nodes (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, kind TEXT NOT NULL, path TEXT NOT NULL, name TEXT NOT NULL, start_line INTEGER, end_line INTEGER, meta_json TEXT DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS edges (id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL, source TEXT NOT NULL, target TEXT NOT NULL, kind TEXT NOT NULL, meta_json TEXT DEFAULT '{}');
        CREATE TABLE IF NOT EXISTS files (
            rel_path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            sha256 TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS node_cache (
            rel_path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            kind TEXT NOT NULL,
            path TEXT NOT NULL,
            name TEXT NOT NULL,
            start_line INTEGER,
            end_line INTEGER,
            meta_json TEXT DEFAULT '{}',
            PRIMARY KEY (rel_path, sha256, kind, path, name, start_line)
        );
        CREATE TABLE IF NOT EXISTS edge_cache (
            rel_path TEXT NOT NULL,
            sha256 TEXT NOT NULL,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            kind TEXT NOT NULL,
            meta_json TEXT DEFAULT '{}',
            PRIMARY KEY (rel_path, sha256, source, target, kind)
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_lookup ON nodes(kind, path, name);
        CREATE INDEX IF NOT EXISTS idx_edges_lookup ON edges(source, target, kind);
        CREATE INDEX IF NOT EXISTS idx_node_cache_lookup ON node_cache(rel_path, sha256);
        CREATE INDEX IF NOT EXISTS idx_edge_cache_lookup ON edge_cache(rel_path, sha256);
        """
        )
        self.conn.commit()

    def clear(self) -> None:
        self.clear_graph()
        self.conn.execute("DELETE FROM edge_cache")
        self.conn.execute("DELETE FROM node_cache")
        self.conn.execute("DELETE FROM files")
        self.conn.commit()

    def clear_graph(self) -> None:
        self.conn.execute("DELETE FROM edges")
        self.conn.execute("DELETE FROM nodes")
        self.conn.execute("DELETE FROM runs")
        self.conn.commit()

    def create_run(self, root: str, created_at: str) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs(root, created_at) VALUES (?, ?)",
            (root, created_at),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_node(
        self,
        run_id: int,
        *,
        kind: str,
        path: str,
        name: str,
        start_line: int | None = None,
        end_line: int | None = None,
        meta_json: str = "{}",
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO nodes(run_id, kind, path, name, start_line, end_line, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (run_id, kind, path, name, start_line, end_line, meta_json),
        )

    def add_edge(
        self, run_id: int, *, source: str, target: str, kind: str, meta_json: str = "{}"
    ) -> None:
        self.conn.execute(
            "INSERT INTO edges(run_id, source, target, kind, meta_json) VALUES (?, ?, ?, ?, ?)",
            (run_id, source, target, kind, meta_json),
        )

    def file_state(self, rel_path: str) -> sqlite3.Row | None:
        rows = self.rows("SELECT * FROM files WHERE rel_path = ?", (rel_path,))
        return rows[0] if rows else None

    def upsert_file_state(
        self,
        *,
        rel_path: str,
        size: int,
        mtime_ns: int,
        sha256: str,
        updated_at: str,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO files(rel_path, size, mtime_ns, sha256, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(rel_path) DO UPDATE SET
                size = excluded.size,
                mtime_ns = excluded.mtime_ns,
                sha256 = excluded.sha256,
                updated_at = excluded.updated_at
            """,
            (rel_path, size, mtime_ns, sha256, updated_at),
        )

    def delete_files_not_in(self, rel_paths: set[str]) -> None:
        if not rel_paths:
            self.conn.execute("DELETE FROM files")
            self.conn.execute("DELETE FROM node_cache")
            self.conn.execute("DELETE FROM edge_cache")
            return
        placeholders = ",".join("?" for _ in rel_paths)
        params = tuple(sorted(rel_paths))
        self.conn.execute(f"DELETE FROM files WHERE rel_path NOT IN ({placeholders})", params)
        self.conn.execute(f"DELETE FROM node_cache WHERE rel_path NOT IN ({placeholders})", params)
        self.conn.execute(f"DELETE FROM edge_cache WHERE rel_path NOT IN ({placeholders})", params)

    def cached_nodes(self, rel_path: str, sha256: str) -> list[sqlite3.Row]:
        return self.rows(
            """
            SELECT kind, path, name, start_line, end_line, meta_json
            FROM node_cache
            WHERE rel_path = ? AND sha256 = ?
            ORDER BY rowid
            """,
            (rel_path, sha256),
        )

    def cached_edges(self, rel_path: str, sha256: str) -> list[sqlite3.Row]:
        return self.rows(
            """
            SELECT source, target, kind, meta_json
            FROM edge_cache
            WHERE rel_path = ? AND sha256 = ?
            ORDER BY rowid
            """,
            (rel_path, sha256),
        )

    def replace_cached_extraction(
        self,
        *,
        rel_path: str,
        sha256: str,
        nodes: list[dict[str, object]],
        edges: list[dict[str, object]],
    ) -> None:
        self.conn.execute("DELETE FROM node_cache WHERE rel_path = ?", (rel_path,))
        self.conn.execute("DELETE FROM edge_cache WHERE rel_path = ?", (rel_path,))

        unique_nodes: list[dict[str, object]] = []
        seen_nodes: set[tuple[object, ...]] = set()
        for node in nodes:
            key = (node["kind"], node["path"], node["name"], node["start_line"])
            if key in seen_nodes:
                continue
            seen_nodes.add(key)
            unique_nodes.append(node)

        unique_edges: list[dict[str, object]] = []
        seen_edges: set[tuple[object, ...]] = set()
        for edge in edges:
            key = (edge["source"], edge["target"], edge["kind"])
            if key in seen_edges:
                continue
            seen_edges.add(key)
            unique_edges.append(edge)

        self.conn.executemany(
            """
            INSERT INTO node_cache(rel_path, sha256, kind, path, name, start_line, end_line, meta_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    rel_path,
                    sha256,
                    node["kind"],
                    node["path"],
                    node["name"],
                    node["start_line"],
                    node["end_line"],
                    node["meta_json"],
                )
                for node in unique_nodes
            ],
        )
        self.conn.executemany(
            """
            INSERT INTO edge_cache(rel_path, sha256, source, target, kind, meta_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    rel_path,
                    sha256,
                    edge["source"],
                    edge["target"],
                    edge["kind"],
                    edge["meta_json"],
                )
                for edge in unique_edges
            ],
        )

    def rows(self, sql: str, params: Iterable[object] = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(sql, tuple(params)))

    def commit(self) -> None:
        self.conn.commit()
