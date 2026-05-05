from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence


DEFAULT_SCAN_TARGETS = [
    "README.md",
    "AGENTS.md",
    "pyproject.toml",
    ".github",
    "docs",
    "examples",
    "integrations",
    "scripts",
    "src",
    "tests",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a local CodePrism pre-release proof pack."
    )
    parser.add_argument("--outdir", default=".codeprism/pre-release")
    parser.add_argument("--baseline-suite")
    parser.add_argument("--fixtures-root", default="examples/benchmarks")
    parser.add_argument("--session", default="examples/codex-session.sample.jsonl")
    parser.add_argument("--regression-threshold", type=float, default=5.0)
    parser.add_argument("--fail-on-regression", action="store_true")
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--chart-out", default="docs/assets/benchmark-snapshot.svg")
    parser.add_argument("--skip-chart-check", action="store_true")
    parser.add_argument("--scan-target", action="append", default=[])
    parser.add_argument("--hygiene-pattern", action="append", default=[])
    parser.add_argument(
        "--codeprism-command",
        help="Command used to invoke CodePrism. Defaults to this Python running contextopt.cli.",
    )
    args = parser.parse_args(argv)

    root = Path.cwd()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    codeprism = _command_parts(args.codeprism_command, [sys.executable, "-m", "contextopt.cli"])

    results: list[dict[str, object]] = []
    benchmark_dir = outdir / "benchmarks"
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    current_suite = benchmark_dir / "suite.json"
    results.append(
        _run_logged(
            [
                *codeprism,
                "benchmark-suite",
                args.fixtures_root,
                "--out",
                str(current_suite),
            ],
            benchmark_dir / "benchmark-suite.log",
            "benchmark-suite",
        )
    )
    chart_arg_path = Path(args.chart_out)
    chart_path = chart_arg_path if chart_arg_path.is_absolute() else root / chart_arg_path
    chart_artifact = outdir / "benchmark-chart.svg"
    chart_script = Path(__file__).with_name("render_benchmark_chart.py")
    results.append(
        _run_logged(
            [
                sys.executable,
                str(chart_script),
                str(current_suite),
                "--out",
                str(chart_artifact),
            ],
            benchmark_dir / "benchmark-chart.log",
            "benchmark-chart",
        )
    )
    if not args.skip_chart_check:
        results.append(
            _run_logged(
                [
                    sys.executable,
                    str(chart_script),
                    str(current_suite),
                    "--out",
                    str(chart_path),
                    "--check",
                ],
                benchmark_dir / "benchmark-chart-check.log",
                "benchmark-chart-check",
            )
        )

    baseline_suite = Path(args.baseline_suite) if args.baseline_suite else current_suite
    trend_dir = outdir / "benchmark-trends"
    trend_command = [
        sys.executable,
        str(Path(__file__).with_name("benchmark_trend.py")),
        "--baseline-suite",
        str(baseline_suite),
        "--current-suite",
        str(current_suite),
        "--outdir",
        str(trend_dir),
        "--regression-threshold",
        str(args.regression_threshold),
    ]
    if args.fail_on_regression:
        trend_command.append("--fail-on-regression")
    results.append(
        _run_logged(
            trend_command,
            trend_dir / "benchmark-trend.log",
            "benchmark-trend",
        )
    )

    audit_path = outdir / "session-audit.md"
    results.append(
        _run_logged(
            [
                *codeprism,
                "audit-session",
                args.session,
                "--out",
                str(audit_path),
            ],
            outdir / "session-audit.log",
            "session-audit",
        )
    )

    if not args.skip_tests:
        results.append(
            _run_logged(
                [sys.executable, "-m", "pytest"],
                outdir / "pytest.log",
                "pytest",
            )
        )
        results.append(
            _run_logged(
                ["ruff", "check", "."],
                outdir / "ruff.log",
                "ruff",
            )
        )

    patterns = [*_default_hygiene_patterns(), *args.hygiene_pattern]
    scan_targets = args.scan_target or DEFAULT_SCAN_TARGETS
    hygiene_matches = _scan_hygiene(root, scan_targets, patterns)
    hygiene_path = outdir / "hygiene-scan.md"
    _write_hygiene_report(hygiene_path, hygiene_matches)
    results.append(
        {
            "name": "public-hygiene",
            "status": "failed" if hygiene_matches else "passed",
            "returncode": 1 if hygiene_matches else 0,
            "log": str(hygiene_path),
        }
    )

    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    manifest_path = outdir / "manifest.json"
    _write_manifest(
        manifest_path,
        results,
        generated_at=generated_at,
        baseline_suite=baseline_suite,
        current_suite=current_suite,
        trend_report=trend_dir / "comparison.md",
        chart_artifact=chart_artifact,
        chart_check=chart_arg_path if not args.skip_chart_check else None,
        audit_report=audit_path,
        hygiene_report=hygiene_path,
        self_baseline=args.baseline_suite is None,
    )

    summary_path = outdir / "README.md"
    _write_summary(
        summary_path,
        results,
        generated_at=generated_at,
        baseline_suite=baseline_suite,
        current_suite=current_suite,
        trend_report=trend_dir / "comparison.md",
        chart_artifact=chart_artifact,
        chart_check=chart_arg_path if not args.skip_chart_check else None,
        audit_report=audit_path,
        hygiene_report=hygiene_path,
        manifest=manifest_path,
        self_baseline=args.baseline_suite is None,
    )

    failed = [result for result in results if result["returncode"] != 0]
    print(f"Pre-release proof pack: {summary_path}")
    if failed:
        print(f"Failed checks: {', '.join(str(result['name']) for result in failed)}")
        return 1
    print("All pre-release proof checks passed.")
    return 0


def _run_logged(
    command: Sequence[str], log_path: Path, name: str
) -> dict[str, object]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            list(command),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        text = f"Command not found: {command[0]}\n"
        log_path.write_text(text, encoding="utf-8")
        return {"name": name, "status": "failed", "returncode": 127, "log": str(log_path)}
    log_path.write_text(
        "$ " + " ".join(command) + "\n\n" + result.stdout + result.stderr,
        encoding="utf-8",
    )
    return {
        "name": name,
        "status": "passed" if result.returncode == 0 else "failed",
        "returncode": result.returncode,
        "log": str(log_path),
    }


def _scan_hygiene(root: Path, targets: Sequence[str], patterns: Sequence[str]) -> list[dict[str, object]]:
    matches: list[dict[str, object]] = []
    for path in _iter_scan_files(root, targets):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        rel = path.relative_to(root).as_posix()
        for line_number, line in enumerate(lines, start=1):
            for pattern in patterns:
                if pattern and pattern in line:
                    matches.append(
                        {
                            "path": rel,
                            "line": line_number,
                            "pattern": pattern,
                            "text": line.strip(),
                        }
                    )
    return matches


def _iter_scan_files(root: Path, targets: Sequence[str]) -> list[Path]:
    tracked = _git_tracked_files(root, targets)
    if tracked is not None:
        return tracked

    files: set[Path] = set()
    for target in targets:
        path = root / target
        if not path.exists():
            continue
        if path.is_file():
            files.add(path)
            continue
        for child in path.rglob("*"):
            if not child.is_file():
                continue
            if _skip_scan_path(child):
                continue
            files.add(child)
    return sorted(files)


def _skip_scan_path(path: Path) -> bool:
    ignored = {".git", ".codeprism", ".contextopt", ".venv", "__pycache__"}
    if set(path.parts) & ignored:
        return True
    return any(part.endswith(".egg-info") for part in path.parts)


def _git_tracked_files(root: Path, targets: Sequence[str]) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--", *targets],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    files = []
    for line in result.stdout.splitlines():
        path = root / line
        if path.is_file() and not _skip_scan_path(path):
            files.append(path)
    return sorted(files)


def _write_hygiene_report(path: Path, matches: list[dict[str, object]]) -> None:
    lines = [
        "# Public Hygiene Scan",
        "",
        "Scans tracked public-facing files for known private release markers.",
        "",
    ]
    if not matches:
        lines.append("Result: passed. No configured markers were found.")
    else:
        lines.extend(
            [
                "Result: failed.",
                "",
                "| File | Line | Marker | Text |",
                "| --- | ---: | --- | --- |",
            ]
        )
        for match in matches:
            lines.append(
                "| "
                f"{match['path']} | "
                f"{match['line']} | "
                f"`{match['pattern']}` | "
                f"{str(match['text']).replace('|', '/')[:140]} |"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_summary(
    path: Path,
    results: Sequence[dict[str, object]],
    *,
    generated_at: str,
    baseline_suite: Path,
    current_suite: Path,
    trend_report: Path,
    chart_artifact: Path,
    chart_check: Path | None,
    audit_report: Path,
    hygiene_report: Path,
    manifest: Path,
    self_baseline: bool,
) -> None:
    lines = [
        "# CodePrism Pre-Release Proof Pack",
        "",
        f"Generated: {generated_at}",
        "",
        "## Checks",
        "",
        "| Check | Status | Log |",
        "| --- | --- | --- |",
    ]
    for result in results:
        lines.append(
            f"| {result['name']} | {result['status']} | `{result['log']}` |"
        )
    lines.extend(
        [
            "",
            "## Artifacts",
            "",
            f"- Baseline suite: `{baseline_suite}`",
            f"- Current suite: `{current_suite}`",
            f"- Benchmark trend: `{trend_report}`",
            f"- Benchmark chart: `{chart_artifact}`",
            f"- Session audit: `{audit_report}`",
            f"- Public hygiene scan: `{hygiene_report}`",
            f"- Machine-readable manifest: `{manifest}`",
        ]
    )
    if chart_check is not None:
        lines.append(f"- Checked-in chart: `{chart_check}`")
    if self_baseline:
        lines.extend(
            [
                "",
                "Note: no baseline suite was supplied, so the benchmark trend compares the current suite against itself.",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_manifest(
    path: Path,
    results: Sequence[dict[str, object]],
    *,
    generated_at: str,
    baseline_suite: Path,
    current_suite: Path,
    trend_report: Path,
    chart_artifact: Path,
    chart_check: Path | None,
    audit_report: Path,
    hygiene_report: Path,
    self_baseline: bool,
) -> None:
    payload = {
        "schema_version": 1,
        "generated_at": generated_at,
        "self_baseline": self_baseline,
        "checks": [
            {
                "name": str(result["name"]),
                "status": str(result["status"]),
                "returncode": int(result["returncode"]),
                "log": str(result["log"]),
            }
            for result in results
        ],
        "artifacts": {
            "baseline_suite": str(baseline_suite),
            "current_suite": str(current_suite),
            "benchmark_trend": str(trend_report),
            "benchmark_chart": str(chart_artifact),
            "checked_in_chart": str(chart_check) if chart_check is not None else None,
            "session_audit": str(audit_report),
            "public_hygiene_scan": str(hygiene_report),
        },
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _command_parts(value: str | None, default: Sequence[str]) -> list[str]:
    if not value:
        return list(default)
    return shlex.split(value)


def _default_hygiene_patterns() -> list[str]:
    return [
        "Ko" + "-fi",
        "configured" + " in",
        "can be " + "enabled",
        "Public " + "Launch",
        "cortext" + "-lab",
        "Yong" + " Wei",
        "K:" + "\\CODEX",
        "xenon" + "lim88",
        "g" + "ws",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
