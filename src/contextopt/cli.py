from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from .activity import write_activity_payload
from .activity_adapters import adapt_tool_jsonl
from .artifacts import ARTIFACT_DIR, artifact_path, config_path, resolve_artifact_path
from .benchmark import default_benchmark_path, format_benchmark, run_benchmark
from .config import load_config
from .exporters.dot import export_dot
from .exporters.json_export import export_json
from .exporters.markdown import export_markdown
from .exporters.web import export_web_visualization
from .freshness import compute_freshness
from .gain import compute_gain, format_gain
from .graph import GraphStore
from .integrations import (
    default_claude_home,
    default_codex_home,
    doctor_integrations,
    install_integrations,
)
from .live_trace import append_live_trace_event, live_trace_path
from .mapper import map_project
from .mcp_server import McpDependencyError, mcp_tool_specs, run_mcp_server
from .memory import MemoryError, list_memories, read_memory, write_memory, write_project_memory
from .query import query_graph
from .read_modes import ReadError, format_read_result, read_path
from .references import ReferencesError, find_references, format_references
from .retrieval import RetrievalError, format_retrieved_source, retrieve_source
from .slicer import default_slice_path, export_slice
from .stats import compute_stats, format_stats


PUBLIC_CLI = "codeprism"
LEGACY_CLI = "contextopt"
STALE_CONTEXT_EXIT = 3


def _program_name(argv0: str | None = None) -> str:
    stem = Path(argv0 or sys.argv[0]).stem.lower()
    if stem in {PUBLIC_CLI, LEGACY_CLI}:
        return stem
    return PUBLIC_CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=_program_name(),
        description="CodePrism maps codebases into focused context slices for AI agents.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help=f"Create {ARTIFACT_DIR} config directory.")
    p_init.add_argument("--root", default=".")
    p_map = sub.add_parser("map", help="Scan and map a project.")
    p_map.add_argument("root", nargs="?", default=".")
    p_map.add_argument("--db")
    p_map.add_argument("--max-file-bytes", type=int)
    p_map.add_argument("--ignore", action="append", default=[])
    p_export = sub.add_parser("export", help="Export a context pack.")
    p_export.add_argument("--db")
    p_export.add_argument("--format", choices=["md", "json", "dot"], default="md")
    p_export.add_argument("--out")
    p_export.add_argument("--max-nodes", type=int, default=5000)
    p_export.add_argument("--max-edges", type=int, default=5000)
    p_export.add_argument("--max-chars", type=int)
    _add_freshness_args(p_export)
    p_query = sub.add_parser("query", help="Query the local project map.")
    p_query.add_argument("text")
    p_query.add_argument("--db")
    p_query.add_argument("--limit", type=int, default=20)
    _add_freshness_args(p_query)
    p_references = sub.add_parser("references", help="Show graph references for a node ID.")
    p_references.add_argument("node_id")
    p_references.add_argument("--db")
    _add_freshness_args(p_references)
    p_get = sub.add_parser("get", help="Print exact source for a mapped node ID.")
    p_get.add_argument("node_id")
    p_get.add_argument("--root", default=".")
    p_get.add_argument("--db")
    _add_freshness_args(p_get)
    p_read = sub.add_parser("read", help="Read a file through token-aware modes.")
    p_read.add_argument("path")
    p_read.add_argument("--mode", choices=["map", "signatures", "diff", "full"], default="map")
    p_read.add_argument("--root", default=".")
    p_read.add_argument("--db")
    _add_freshness_args(p_read)
    p_stats = sub.add_parser("stats", help="Show local token and graph statistics.")
    p_stats.add_argument("root", nargs="?", default=".")
    p_stats.add_argument("--db")
    p_gain = sub.add_parser("gain", help="Report estimated context savings and map freshness.")
    p_gain.add_argument("root", nargs="?", default=".")
    p_gain.add_argument("--db")
    p_gain.add_argument("--slice", help="Optional slice manifest JSON. Defaults to latest local slice.")
    p_gain.add_argument("--max-file-bytes", type=int)
    p_gain.add_argument("--ignore", action="append", default=[])
    p_onboard = sub.add_parser("onboard", help="Map a repo and write local project memory.")
    p_onboard.add_argument("root", nargs="?", default=".")
    p_onboard.add_argument("--db")
    p_onboard.add_argument("--out")
    p_onboard.add_argument("--notes", default="")
    p_onboard.add_argument("--max-file-bytes", type=int)
    p_onboard.add_argument("--ignore", action="append", default=[])
    p_benchmark = sub.add_parser("benchmark", help="Write an honest local token-savings report.")
    p_benchmark.add_argument("root", nargs="?", default=".")
    p_benchmark.add_argument("--query", default="main")
    p_benchmark.add_argument("--db")
    p_benchmark.add_argument("--out")
    p_benchmark.add_argument("--max-file-bytes", type=int)
    p_benchmark.add_argument("--ignore", action="append", default=[])
    p_mcp = sub.add_parser("mcp", help="Run the experimental CodePrism MCP server.")
    p_mcp.add_argument("--root", default=".")
    p_mcp.add_argument("--db")
    p_mcp.add_argument("--transport", choices=["stdio", "streamable-http"], default="stdio")
    p_mcp.add_argument("--list-tools", action="store_true")
    p_memory = sub.add_parser("memory", help="Read and write local CodePrism memory files.")
    memory_sub = p_memory.add_subparsers(dest="memory_cmd", required=True)
    p_memory_list = memory_sub.add_parser("list", help="List local memory files.")
    p_memory_list.add_argument("--root", default=".")
    p_memory_read = memory_sub.add_parser("read", help="Read a local memory file.")
    p_memory_read.add_argument("name")
    p_memory_read.add_argument("--root", default=".")
    p_memory_write = memory_sub.add_parser("write", help="Write a local memory file.")
    p_memory_write.add_argument("name")
    p_memory_write.add_argument("--text", required=True)
    p_memory_write.add_argument("--root", default=".")
    p_prime = sub.add_parser(
        "prime",
        help="Map the repo and write a focused slice for the current task.",
    )
    p_prime.add_argument("query")
    p_prime.add_argument("--root", default=".")
    p_prime.add_argument("--db")
    p_prime.add_argument("--out")
    p_prime.add_argument(
        "--artifact-dir",
        help="Write generated prime artifacts to this directory instead of the project root.",
    )
    p_prime.add_argument(
        "--readonly-root",
        action="store_true",
        help="Refuse to write generated artifacts inside --root.",
    )
    p_prime.add_argument("--limit", type=int, default=12)
    p_prime.add_argument("--max-file-bytes", type=int)
    p_prime.add_argument("--ignore", action="append", default=[])
    p_prime.add_argument(
        "--changed",
        action="store_true",
        help="Seed the slice with changed, staged, and untracked git files.",
    )
    p_slice = sub.add_parser("slice", help="Export a targeted context slice.")
    p_slice.add_argument("query")
    p_slice.add_argument("--db")
    p_slice.add_argument("--out")
    p_slice.add_argument("--limit", type=int, default=12)
    p_slice.add_argument("--path", action="append", default=[], help="Seed the slice with a file path.")
    _add_freshness_args(p_slice)
    p_visualize = sub.add_parser(
        "visualize",
        help="Generate an interactive browser view of the project map.",
    )
    p_visualize.add_argument("--db")
    p_visualize.add_argument("--outdir")
    p_visualize.add_argument("--activity")
    p_visualize.add_argument("--context")
    _add_freshness_args(p_visualize)
    p_setup = sub.add_parser(
        "setup",
        help="Install CodePrism agent integrations and verify them with doctor.",
    )
    p_setup.add_argument("--root", default=".")
    p_setup.add_argument(
        "--target",
        choices=["project", "global", "all", "codex", "claude"],
        default="all",
    )
    p_setup.add_argument("--codex-home", default=str(default_codex_home()))
    p_setup.add_argument("--claude-home", default=str(default_claude_home()))
    p_setup.add_argument("--dry-run", action="store_true")
    p_install = sub.add_parser(
        "install-integrations",
        help="Install local Codex/Claude/Copilot helpers for query-first context use.",
    )
    p_install.add_argument("--root", default=".")
    p_install.add_argument(
        "--target",
        choices=["project", "global", "all", "codex", "claude"],
        default="all",
    )
    p_install.add_argument("--codex-home", default=str(default_codex_home()))
    p_install.add_argument("--claude-home", default=str(default_claude_home()))
    p_install.add_argument("--dry-run", action="store_true")
    p_install.add_argument("--force", action="store_true")
    p_doctor = sub.add_parser(
        "doctor",
        help="Check whether CodePrism CLI and agent integrations are installed and current.",
    )
    p_doctor.add_argument("--root", default=".")
    p_doctor.add_argument(
        "--target",
        choices=["project", "global", "all", "codex", "claude"],
        default="all",
    )
    p_doctor.add_argument("--codex-home", default=str(default_codex_home()))
    p_doctor.add_argument("--claude-home", default=str(default_claude_home()))
    p_doctor.add_argument("--json", action="store_true")
    p_activity = sub.add_parser("activity", help="Work with normalized activity streams.")
    activity_sub = p_activity.add_subparsers(dest="activity_cmd", required=True)
    p_activity_normalize = activity_sub.add_parser(
        "normalize",
        help="Normalize JSONL activity events into inspectable replay JSON.",
    )
    p_activity_normalize.add_argument("input")
    p_activity_normalize.add_argument("--out")
    p_activity_adapt_tool = activity_sub.add_parser(
        "adapt-tool-log",
        help="Convert a simple tool-event JSONL log into CodePrism activity JSONL.",
    )
    p_activity_adapt_tool.add_argument("input")
    p_activity_adapt_tool.add_argument("--out")
    args = parser.parse_args(argv)
    if args.cmd == "init":
        root = Path(args.root).resolve()
        ctx = root / ARTIFACT_DIR
        ctx.mkdir(exist_ok=True)
        config = config_path(root)
        if not config.exists():
            config.write_text(
                "max_file_bytes = 500000\n"
                'ignore = ["node_modules", ".git", "dist", "build", ".next"]\n',
                encoding="utf-8",
            )
        print(f"Initialized {ctx}")
        return 0
    if args.cmd == "map":
        root = Path(args.root).resolve()
        config = load_config(root)
        db = _db_path(root, args.db, write=True)
        db.parent.mkdir(parents=True, exist_ok=True)
        result = map_project(
            root,
            GraphStore(db),
            max_file_bytes=args.max_file_bytes or config.max_file_bytes,
            ignore_patterns=[*config.ignore, *args.ignore],
        )
        print(
            f"Mapped {result.files_seen} files, {result.nodes_written} nodes, "
            f"{result.edges_written} edges. Reused {result.files_reused} unchanged, "
            f"extracted {result.files_extracted}, hashed {result.files_hashed}."
        )
        _trace_event(
            root,
            event="map",
            meta={
                "files_seen": result.files_seen,
                "nodes_written": result.nodes_written,
                "edges_written": result.edges_written,
                "files_reused": result.files_reused,
                "files_extracted": result.files_extracted,
                "files_hashed": result.files_hashed,
            },
        )
        return 0
    if args.cmd == "export":
        default_out = {
            "md": "context-pack.md",
            "json": "context-pack.json",
            "dot": "imports.dot",
        }[args.format]
        root = Path.cwd().resolve()
        out = Path(args.out) if args.out else artifact_path(root, default_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        store = _fresh_context_store(
            root,
            args.db,
            refresh=args.refresh,
            strict_fresh=args.strict_fresh,
        )
        if store is None:
            return STALE_CONTEXT_EXIT
        if args.format == "dot":
            export_dot(store, out, max_edges=args.max_edges)
        elif args.format == "json":
            export_json(store, out)
        else:
            export_markdown(
                store,
                out,
                max_nodes=args.max_nodes,
                max_edges=args.max_edges,
                max_chars=args.max_chars,
            )
        print(f"Wrote {out}")
        _trace_event(
            root,
            event="export",
            path=_relative_trace_path(out, root),
            meta={"format": args.format, "out": str(out)},
        )
        return 0
    if args.cmd == "visualize":
        root = Path.cwd().resolve()
        outdir = Path(args.outdir) if args.outdir else artifact_path(root, "visual")
        activity_path = Path(args.activity) if args.activity else None
        if activity_path is None:
            trace_candidate = live_trace_path(root)
            if trace_candidate.exists():
                activity_path = trace_candidate
        context_path = Path(args.context) if args.context else None
        store = _fresh_context_store(
            root,
            args.db,
            refresh=args.refresh,
            strict_fresh=args.strict_fresh,
        )
        if store is None:
            return STALE_CONTEXT_EXIT
        html_path = export_web_visualization(
            store,
            outdir,
            activity_path=activity_path,
            context_path=context_path,
        )
        print(f"Wrote visualization to {html_path}")
        _trace_event(
            root,
            event="visualize",
            path=_relative_trace_path(html_path, root),
            meta={
                "outdir": str(outdir),
                "activity_path": str(activity_path) if activity_path else "",
                "context_path": str(context_path) if context_path else "",
            },
        )
        return 0
    if args.cmd == "setup":
        print("CodePrism Setup")
        print("")
        install_result = install_integrations(
            root=Path(args.root),
            target=args.target,
            codex_home=Path(args.codex_home),
            claude_home=Path(args.claude_home),
            dry_run=args.dry_run,
            force=True,
        )
        action = "Would install" if args.dry_run else "Installed"
        print(
            f"{action} {install_result['planned']} CodePrism integration files "
            f"({install_result['copied']} copied, {install_result['skipped']} skipped)."
        )
        for path in install_result["paths"]:
            print(path)
        if args.dry_run:
            return 0
        print("")
        report = doctor_integrations(
            root=Path(args.root),
            target=args.target,
            codex_home=Path(args.codex_home),
            claude_home=Path(args.claude_home),
        )
        _print_doctor_report(report)
        if args.target in {"global", "all", "codex", "claude"}:
            print("Restart Codex/Claude to pick up newly installed skills.")
        return 0 if report["ok"] else 1
    if args.cmd == "install-integrations":
        result = install_integrations(
            root=Path(args.root),
            target=args.target,
            codex_home=Path(args.codex_home),
            claude_home=Path(args.claude_home),
            dry_run=args.dry_run,
            force=args.force,
        )
        action = "Would install" if args.dry_run else "Installed"
        print(
            f"{action} {result['planned']} CodePrism integration files "
            f"({result['copied']} copied, {result['skipped']} skipped)."
        )
        for path in result["paths"]:
            print(path)
        if args.target in {"global", "all", "codex", "claude"} and not args.dry_run:
            print("Restart Codex/Claude to pick up newly installed skills.")
        return 0
    if args.cmd == "doctor":
        report = doctor_integrations(
            root=Path(args.root),
            target=args.target,
            codex_home=Path(args.codex_home),
            claude_home=Path(args.claude_home),
        )
        if args.json:
            print(json.dumps(report, indent=2, sort_keys=True))
        else:
            _print_doctor_report(report)
        return 0 if report["ok"] else 1
    if args.cmd == "activity":
        if args.activity_cmd == "normalize":
            out = Path(args.out) if args.out else artifact_path(Path.cwd(), "activity-stream.json")
            payload = write_activity_payload(Path(args.input), out)
            summary = payload["summary"]
            print(
                f"Wrote {out} "
                f"({summary['event_count']} events, {len(payload['warnings'])} warnings, "
                f"~{summary['estimated_tokens']} estimated tokens)."
            )
            return 0
        if args.activity_cmd == "adapt-tool-log":
            out = Path(args.out) if args.out else artifact_path(Path.cwd(), "activity-events.jsonl")
            result = adapt_tool_jsonl(Path(args.input), out)
            print(
                f"Wrote {out} "
                f"({result['event_count']} events, {result['warning_count']} warnings)."
            )
            return 0
    if args.cmd == "query":
        root = Path.cwd().resolve()
        store = _fresh_context_store(
            root,
            args.db,
            refresh=args.refresh,
            strict_fresh=args.strict_fresh,
        )
        if store is None:
            return STALE_CONTEXT_EXIT
        rows = list(query_graph(store, args.text, args.limit))
        for row in rows:
            print(f"{row['kind']:10} {row['path']} {row['name']}")
        _trace_event(root, event="query", meta={"text": args.text, "results": len(rows)})
        return 0
    if args.cmd == "references":
        root = Path.cwd().resolve()
        store = _fresh_context_store(
            root,
            args.db,
            refresh=args.refresh,
            strict_fresh=args.strict_fresh,
        )
        if store is None:
            return STALE_CONTEXT_EXIT
        try:
            result = find_references(store, args.node_id)
        except ReferencesError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(format_references(result), end="")
        _trace_event(root, event="references", node_id=args.node_id)
        return 0
    if args.cmd == "get":
        root = Path(args.root).resolve()
        store = _fresh_context_store(
            root,
            args.db,
            refresh=args.refresh,
            strict_fresh=args.strict_fresh,
        )
        if store is None:
            return STALE_CONTEXT_EXIT
        try:
            result = retrieve_source(
                store,
                root,
                args.node_id,
            )
        except RetrievalError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(format_retrieved_source(result), end="")
        _trace_event(root, event="get", node_id=args.node_id)
        return 0
    if args.cmd == "read":
        root = Path(args.root).resolve()
        try:
            store = (
                _fresh_context_store(
                    root,
                    args.db,
                    refresh=args.refresh,
                    strict_fresh=args.strict_fresh,
                )
                if args.mode in {"map", "signatures"}
                else None
            )
            if store is None and args.mode in {"map", "signatures"}:
                return STALE_CONTEXT_EXIT
            result = read_path(
                root=root,
                path=args.path,
                mode=args.mode,
                store=store,
            )
        except ReadError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(format_read_result(result), end="")
        _trace_event(
            root,
            event=f"read_{args.mode}",
            path=result.path,
            estimated_tokens=result.estimated_tokens,
            meta={"mode": args.mode},
        )
        return 0
    if args.cmd == "stats":
        root = Path(args.root).resolve()
        config = load_config(root)
        stats = compute_stats(
            root,
            GraphStore(_db_path(root, args.db)),
            max_file_bytes=config.max_file_bytes,
            ignore_patterns=config.ignore,
        )
        print(format_stats(stats))
        _trace_event(root, event="stats", estimated_tokens=stats.get("source_estimated_tokens"), meta=stats)
        return 0
    if args.cmd == "gain":
        root = Path(args.root).resolve()
        config = load_config(root)
        gain = compute_gain(
            root,
            GraphStore(_db_path(root, args.db)),
            slice_path=Path(args.slice) if args.slice else None,
            max_file_bytes=args.max_file_bytes or config.max_file_bytes,
            ignore_patterns=[*config.ignore, *args.ignore],
        )
        print(format_gain(gain), end="")
        freshness = gain.get("freshness") if isinstance(gain.get("freshness"), dict) else {}
        _trace_event(
            root,
            event="gain",
            estimated_tokens=gain.get("source_estimated_tokens"),
            meta={
                "freshness_status": freshness.get("status"),
                "changed_files": len(freshness.get("changed_files", [])),
                "new_files": len(freshness.get("new_files", [])),
                "deleted_files": len(freshness.get("deleted_files", [])),
                "source_to_context_saved_percent": gain.get("source_to_context_saved_percent"),
                "source_to_graph_saved_percent": gain.get("source_to_graph_saved_percent"),
                "source_to_slice_saved_percent": gain.get("source_to_slice_saved_percent"),
            },
        )
        return 0
    if args.cmd == "onboard":
        root = Path(args.root).resolve()
        config = load_config(root)
        db = _db_path(root, args.db, write=True)
        db.parent.mkdir(parents=True, exist_ok=True)
        store = GraphStore(db)
        map_project(
            root,
            store,
            max_file_bytes=args.max_file_bytes or config.max_file_bytes,
            ignore_patterns=[*config.ignore, *args.ignore],
        )
        out = Path(args.out) if args.out else None
        path = write_project_memory(root, store, notes=args.notes, out=out)
        print(f"Wrote project memory {path}")
        _trace_event(root, event="onboard", path=_relative_trace_path(path, root))
        return 0
    if args.cmd == "benchmark":
        root = Path(args.root).resolve()
        config = load_config(root)
        out = Path(args.out) if args.out else default_benchmark_path(root, args.query)
        out.parent.mkdir(parents=True, exist_ok=True)
        store = GraphStore(_db_path(root, args.db, write=True))
        result = run_benchmark(
            root,
            store,
            query=args.query,
            out=out,
            max_file_bytes=args.max_file_bytes or config.max_file_bytes,
            ignore_patterns=[*config.ignore, *args.ignore],
        )
        print(format_benchmark(result, out), end="")
        _trace_event(
            root,
            event="benchmark",
            path=_relative_trace_path(out, root),
            meta={"query": args.query, "out": str(out)},
        )
        return 0
    if args.cmd == "memory":
        root = Path(args.root).resolve()
        try:
            if args.memory_cmd == "list":
                for name in list_memories(root):
                    print(name)
                return 0
            if args.memory_cmd == "read":
                print(read_memory(root, args.name), end="")
                return 0
            if args.memory_cmd == "write":
                path = write_memory(root, args.name, args.text)
                print(f"Wrote memory {path}")
                return 0
        except MemoryError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
    if args.cmd == "mcp":
        if args.list_tools:
            print(json.dumps({"tools": mcp_tool_specs()}, indent=2, sort_keys=True))
            return 0
        try:
            run_mcp_server(
                root=Path(args.root).resolve(),
                db=_db_path(Path(args.root).resolve(), args.db),
                transport=args.transport,
            )
        except McpDependencyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        return 0
    if args.cmd == "prime":
        root = Path(args.root).resolve()
        changed_paths = _changed_paths(root) if args.changed else []
        artifact_dir = _resolve_optional_path(args.artifact_dir)
        db = _prime_db_path(root, args.db, artifact_dir)
        out = _prime_out_path(root, args.query, args.out, artifact_dir)
        trace_path = live_trace_path(root, artifact_dir)
        if args.readonly_root and (
            _is_relative_to(db.resolve(), root)
            or _is_relative_to(out.resolve(), root)
            or _is_relative_to(trace_path.resolve(), root)
        ):
            print(
                "Error: refusing to write artifacts inside read-only root. "
                "Use --artifact-dir outside --root, or pass --db/--out outside --root.",
                file=sys.stderr,
            )
            return 2
        db.parent.mkdir(parents=True, exist_ok=True)
        config = load_config(root)
        store = GraphStore(db)
        map_result = map_project(
            root,
            store,
            max_file_bytes=args.max_file_bytes or config.max_file_bytes,
            ignore_patterns=[*config.ignore, *args.ignore],
        )
        slice_result = export_slice(
            store,
            args.query,
            out,
            limit=args.limit,
            seed_paths=changed_paths,
        )
        stats = compute_stats(root, store)
        source_tokens = stats["source_estimated_tokens"]
        slice_tokens = slice_result["estimated_tokens"]
        saving = 1 - (slice_tokens / source_tokens) if source_tokens else 0
        print(
            f"Mapped {map_result.files_seen} files "
            f"({map_result.files_reused} reused, {map_result.files_extracted} extracted)."
        )
        print(f"Wrote slice {slice_result['out']}")
        print(f"Manifest: {slice_result['manifest']}")
        print(f"Source estimate: {source_tokens} tokens.")
        print(f"Full context estimate: {slice_result['full_context_estimated_tokens']} tokens.")
        print(f"Slice estimate: {slice_tokens} tokens.")
        print(f"Estimated saving: {saving:.2%} vs source.")
        print(
            f"Included: {slice_result['file_count']} files, "
            f"{slice_result['symbol_count']} symbols, {slice_result['direct_edges']} edges."
        )
        if args.changed:
            print(f"Changed files: {len(changed_paths)}")
        print("Read this slice first, then open only the raw files it identifies.")
        trace_node_id = _first_trace_node_id(slice_result)
        trace_path_value = _path_from_node_id(trace_node_id) or _relative_trace_path(
            Path(slice_result["out"]),
            root,
        )
        _trace_event(
            root,
            artifact_dir=artifact_dir,
            event="prime",
            path=trace_path_value,
            node_id=trace_node_id,
            estimated_tokens=slice_tokens,
            meta={
                "query": args.query,
                "slice_path": str(slice_result["out"]).replace("\\", "/"),
                "manifest_path": str(slice_result["manifest"]).replace("\\", "/"),
                "source_estimated_tokens": source_tokens,
                "full_context_estimated_tokens": slice_result["full_context_estimated_tokens"],
                "saving": saving,
                "file_count": slice_result["file_count"],
                "symbol_count": slice_result["symbol_count"],
                "direct_edges": slice_result["direct_edges"],
                "changed_files": len(changed_paths),
            },
        )
        return 0
    if args.cmd == "slice":
        out = Path(args.out) if args.out else default_slice_path(args.query)
        root = Path.cwd().resolve()
        store = _fresh_context_store(
            root,
            args.db,
            refresh=args.refresh,
            strict_fresh=args.strict_fresh,
        )
        if store is None:
            return STALE_CONTEXT_EXIT
        result = export_slice(
            store,
            args.query,
            out,
            limit=args.limit,
            seed_paths=args.path,
        )
        print(
            f"Wrote {result['out']} "
            f"({result['written_nodes']} nodes, {result['direct_edges']} edges, "
            f"~{result['estimated_tokens']} tokens, "
            f"{result['estimated_token_ratio']:.2%} of full context). "
            f"Manifest: {result['manifest']}"
        )
        _trace_event(
            root,
            event="slice",
            path=_relative_trace_path(Path(result["out"]), root),
            estimated_tokens=result["estimated_tokens"],
            meta={"query": args.query, "written_nodes": result["written_nodes"]},
        )
        return 0
    return 1


def _git_lines(root: Path, args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _print_doctor_report(report: dict[str, object]) -> None:
    print("CodePrism Doctor")
    print("")
    for item in report["items"]:
        if not isinstance(item, dict):
            continue
        print(f"[{item['status']}] {item['name']} - {item['path']}")
        print(f"  {item['message']}")
    summary = report["summary"]
    if isinstance(summary, dict):
        print("")
        print(
            "Summary: "
            f"{summary.get('current', 0)} current, "
            f"{summary.get('missing', 0)} missing, "
            f"{summary.get('stale', 0)} stale."
        )
    if not report["ok"]:
        print("Run `codeprism setup --target all` to refresh helpers.")


def _add_freshness_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Incrementally refresh the project map before reading context.",
    )
    parser.add_argument(
        "--strict-fresh",
        action="store_true",
        help="Fail if the project map is stale instead of warning.",
    )


def _fresh_context_store(
    root: Path,
    explicit_db: str | None,
    *,
    refresh: bool = False,
    strict_fresh: bool = False,
) -> GraphStore | None:
    config = load_config(root)
    db = _db_path(root, explicit_db, write=refresh)
    store = GraphStore(db)
    if refresh:
        map_project(
            root,
            store,
            max_file_bytes=config.max_file_bytes,
            ignore_patterns=config.ignore,
        )
        return store
    freshness = compute_freshness(
        root,
        store,
        max_file_bytes=config.max_file_bytes,
        ignore_patterns=config.ignore,
    )
    if freshness["status"] == "current":
        return store
    message = _freshness_message(freshness)
    if strict_fresh:
        print(
            f"Error: CodePrism map is stale ({message}). Use --refresh or run `codeprism map .`.",
            file=sys.stderr,
        )
        return None
    print(
        f"Warning: CodePrism map is stale ({message}). Use --refresh or run `codeprism map .`.",
        file=sys.stderr,
    )
    return store


def _freshness_message(freshness: dict[str, object]) -> str:
    def count(name: str) -> int:
        value = freshness.get(name)
        return len(value) if isinstance(value, list) else 0

    parts = [
        f"{count('changed_files')} changed",
        f"{count('new_files')} new",
        f"{count('deleted_files')} deleted",
    ]
    if freshness.get("root_mismatch"):
        parts.append("root mismatch")
    if freshness.get("latest_run_created_at") is None:
        parts.append("no completed map")
    return ", ".join(parts)


def _resolve_optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _db_path(root: Path, explicit_db: str | None, *, write: bool = False) -> Path:
    return resolve_artifact_path(
        root,
        "context.db",
        explicit=explicit_db,
        prefer_existing_legacy=not write,
    )


def _prime_db_path(root: Path, explicit_db: str | None, artifact_dir: Path | None) -> Path:
    if explicit_db:
        db = Path(explicit_db).expanduser()
        return db if db.is_absolute() else root / db
    if artifact_dir:
        return artifact_dir / "context.db"
    return _db_path(root, None, write=True)


def _prime_out_path(
    root: Path,
    query: str,
    explicit_out: str | None,
    artifact_dir: Path | None,
) -> Path:
    if explicit_out:
        out = Path(explicit_out).expanduser()
        return out if out.is_absolute() else root / out
    default_out = default_slice_path(query)
    if artifact_dir:
        return artifact_dir / Path(*default_out.parts[1:])
    return root / default_out


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _changed_paths(root: Path) -> list[str]:
    paths: set[str] = set()
    paths.update(_git_lines(root, ["diff", "--name-only", "--relative"]))
    paths.update(_git_lines(root, ["diff", "--cached", "--name-only", "--relative"]))
    paths.update(_git_lines(root, ["ls-files", "--others", "--exclude-standard"]))
    return sorted(path.replace("\\", "/") for path in paths)


def _relative_trace_path(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _trace_event(root: Path, *, artifact_dir: Path | None = None, **fields: object) -> None:
    append_live_trace_event(live_trace_path(root, artifact_dir), **fields)


def _first_trace_node_id(slice_result: dict[str, object]) -> str | None:
    for key in ("matched_node_ids", "node_ids"):
        values = slice_result.get(key)
        if not isinstance(values, list):
            continue
        for value in values:
            if isinstance(value, str) and not value.startswith("module:"):
                return value
    return None


def _path_from_node_id(node_id: str | None) -> str | None:
    if not node_id:
        return None
    parts = node_id.split("::")
    if len(parts) >= 2 and parts[0] in {
        "class",
        "doc",
        "file",
        "folder",
        "function",
        "heading",
        "method",
    }:
        return parts[1].replace("\\", "/")
    return None


if __name__ == "__main__":
    raise SystemExit(main())
