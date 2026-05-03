from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from .activity import write_activity_payload
from .activity_adapters import adapt_tool_jsonl
from .config import load_config
from .exporters.dot import export_dot
from .exporters.json_export import export_json
from .exporters.markdown import export_markdown
from .exporters.web import export_web_visualization
from .graph import GraphStore
from .integrations import default_claude_home, default_codex_home, install_integrations
from .mapper import map_project
from .query import query_graph
from .slicer import default_slice_path, export_slice
from .stats import compute_stats, format_stats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="contextopt", description="Map a codebase for AI context optimization."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init", help="Create .contextopt config directory.")
    p_init.add_argument("--root", default=".")
    p_map = sub.add_parser("map", help="Scan and map a project.")
    p_map.add_argument("root", nargs="?", default=".")
    p_map.add_argument("--db", default=".contextopt/context.db")
    p_map.add_argument("--max-file-bytes", type=int)
    p_map.add_argument("--ignore", action="append", default=[])
    p_export = sub.add_parser("export", help="Export a context pack.")
    p_export.add_argument("--db", default=".contextopt/context.db")
    p_export.add_argument("--format", choices=["md", "json", "dot"], default="md")
    p_export.add_argument("--out")
    p_export.add_argument("--max-nodes", type=int, default=5000)
    p_export.add_argument("--max-edges", type=int, default=5000)
    p_export.add_argument("--max-chars", type=int)
    p_query = sub.add_parser("query", help="Query the local project map.")
    p_query.add_argument("text")
    p_query.add_argument("--db", default=".contextopt/context.db")
    p_query.add_argument("--limit", type=int, default=20)
    p_stats = sub.add_parser("stats", help="Show local token and graph statistics.")
    p_stats.add_argument("root", nargs="?", default=".")
    p_stats.add_argument("--db", default=".contextopt/context.db")
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
    p_slice.add_argument("--db", default=".contextopt/context.db")
    p_slice.add_argument("--out")
    p_slice.add_argument("--limit", type=int, default=12)
    p_slice.add_argument("--path", action="append", default=[], help="Seed the slice with a file path.")
    p_visualize = sub.add_parser(
        "visualize",
        help="Generate an interactive browser view of the project map.",
    )
    p_visualize.add_argument("--db", default=".contextopt/context.db")
    p_visualize.add_argument("--outdir", default=".contextopt/visual")
    p_visualize.add_argument("--activity")
    p_visualize.add_argument("--context")
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
    p_activity = sub.add_parser("activity", help="Work with normalized activity streams.")
    activity_sub = p_activity.add_subparsers(dest="activity_cmd", required=True)
    p_activity_normalize = activity_sub.add_parser(
        "normalize",
        help="Normalize JSONL activity events into inspectable replay JSON.",
    )
    p_activity_normalize.add_argument("input")
    p_activity_normalize.add_argument("--out", default=".contextopt/activity-stream.json")
    p_activity_adapt_tool = activity_sub.add_parser(
        "adapt-tool-log",
        help="Convert a simple tool-event JSONL log into Cortext activity JSONL.",
    )
    p_activity_adapt_tool.add_argument("input")
    p_activity_adapt_tool.add_argument("--out", default=".contextopt/activity-events.jsonl")
    args = parser.parse_args(argv)
    if args.cmd == "init":
        root = Path(args.root).resolve()
        ctx = root / ".contextopt"
        ctx.mkdir(exist_ok=True)
        config = ctx / "config.toml"
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
        db = Path(args.db)
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
        return 0
    if args.cmd == "export":
        default_out = {
            "md": ".contextopt/context-pack.md",
            "json": ".contextopt/context-pack.json",
            "dot": ".contextopt/imports.dot",
        }[args.format]
        out = Path(args.out or default_out)
        out.parent.mkdir(parents=True, exist_ok=True)
        store = GraphStore(Path(args.db))
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
        return 0
    if args.cmd == "visualize":
        outdir = Path(args.outdir)
        activity_path = Path(args.activity) if args.activity else None
        context_path = Path(args.context) if args.context else None
        html_path = export_web_visualization(
            GraphStore(Path(args.db)),
            outdir,
            activity_path=activity_path,
            context_path=context_path,
        )
        print(f"Wrote visualization to {html_path}")
        return 0
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
            f"{action} {result['planned']} Cortext integration files "
            f"({result['copied']} copied, {result['skipped']} skipped)."
        )
        for path in result["paths"]:
            print(path)
        if args.target in {"global", "all", "codex", "claude"} and not args.dry_run:
            print("Restart Codex/Claude to pick up newly installed skills.")
        return 0
    if args.cmd == "activity":
        if args.activity_cmd == "normalize":
            out = Path(args.out)
            payload = write_activity_payload(Path(args.input), out)
            summary = payload["summary"]
            print(
                f"Wrote {out} "
                f"({summary['event_count']} events, {len(payload['warnings'])} warnings, "
                f"~{summary['estimated_tokens']} estimated tokens)."
            )
            return 0
        if args.activity_cmd == "adapt-tool-log":
            out = Path(args.out)
            result = adapt_tool_jsonl(Path(args.input), out)
            print(
                f"Wrote {out} "
                f"({result['event_count']} events, {result['warning_count']} warnings)."
            )
            return 0
    if args.cmd == "query":
        for row in query_graph(GraphStore(Path(args.db)), args.text, args.limit):
            print(f"{row['kind']:10} {row['path']} {row['name']}")
        return 0
    if args.cmd == "stats":
        stats = compute_stats(Path(args.root), GraphStore(Path(args.db)))
        print(format_stats(stats))
        return 0
    if args.cmd == "prime":
        root = Path(args.root).resolve()
        changed_paths = _changed_paths(root) if args.changed else []
        artifact_dir = _resolve_optional_path(args.artifact_dir)
        db = _prime_db_path(root, args.db, artifact_dir)
        out = _prime_out_path(root, args.query, args.out, artifact_dir)
        if args.readonly_root and (
            _is_relative_to(db.resolve(), root) or _is_relative_to(out.resolve(), root)
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
        return 0
    if args.cmd == "slice":
        out = Path(args.out) if args.out else default_slice_path(args.query)
        result = export_slice(
            GraphStore(Path(args.db)),
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


def _resolve_optional_path(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value).expanduser()
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _prime_db_path(root: Path, explicit_db: str | None, artifact_dir: Path | None) -> Path:
    if explicit_db:
        db = Path(explicit_db).expanduser()
        return db if db.is_absolute() else root / db
    if artifact_dir:
        return artifact_dir / "context.db"
    return root / ".contextopt" / "context.db"


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


if __name__ == "__main__":
    raise SystemExit(main())
